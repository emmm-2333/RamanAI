import os
import joblib
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from django.conf import settings
from pathlib import Path
import datetime

from .models import ModelVersion, SpectrumRecord
from .preprocessing import RamanPreprocessor
from .cnn import MultiTaskRamanCNN
from .utils.dataset import RamanDataset

class MLEngine:
    """
    机器学习引擎: 负责模型加载、推理和训练触发
    Machine Learning Engine: Handles model loading, inference, and training
    """
    
    _current_model = None
    _model_type = None # 'sklearn' or 'torch'
    _model_version = None
    _model_config = {}

    @classmethod
    def load_active_model(cls):
        """
        加载当前激活的模型
        Load the currently active model
        """
        try:
            active_model_record = ModelVersion.objects.filter(is_active=True).last()
            if not active_model_record:
                print("No active model found.")
                return None
            
            model_path = active_model_record.file_path
            if not os.path.exists(model_path):
                print(f"Model file not found: {model_path}")
                return

            if model_path.endswith('.pth'):
                # Load PyTorch Model
                try:
                    checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
                    # Check if checkpoint is dict with config
                    if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
                        state_dict = checkpoint['state_dict']
                        cls._model_config = checkpoint.get('config', {})
                    else:
                        state_dict = checkpoint
                        cls._model_config = {}
                        
                    input_len = cls._model_config.get('input_length', 1801)
                    cls._current_model = MultiTaskRamanCNN(input_length=input_len)
                    cls._current_model.load_state_dict(state_dict)
                    cls._current_model.eval()
                    cls._model_type = 'torch'
                except Exception as e:
                    print(f"Error loading torch model: {e}")
                    return
            else:
                # Load Sklearn Model (Legacy)
                cls._current_model = joblib.load(model_path)
                cls._model_type = 'sklearn'

            cls._model_version = active_model_record.version
            print(f"Loaded model version: {cls._model_version} ({cls._model_type})")

        except Exception as e:
            print(f"Error loading model: {e}")

    @classmethod
    def predict(cls, spectral_data_x, spectral_data_y):
        """
        推理接口
        :param spectral_data_x: 波数
        :param spectral_data_y: 强度
        :return: (diagnosis, confidence)
        """
        # 1. Preprocessing
        processed_y = RamanPreprocessor.process_pipeline(spectral_data_x, spectral_data_y)
        
        if not cls._current_model:
             return "Unknown", 0.0

        # 2. Inference
        if cls._model_type == 'torch':
            # PyTorch Inference
            # Interpolate to 1801 if needed
            target_len = 1801
            if len(processed_y) != target_len:
                 # Simple interpolation
                 from scipy import interpolate
                 current_x = np.linspace(0, 1, len(processed_y))
                 target_x = np.linspace(0, 1, target_len)
                 f = interpolate.interp1d(current_x, processed_y, kind='linear', fill_value="extrapolate")
                 processed_y = f(target_x)

            tensor_x = torch.tensor(processed_y, dtype=torch.float32).view(1, 1, -1) # (1, 1, L)
            
            with torch.no_grad():
                outputs = cls._current_model(tensor_x)
                # Main diagnosis
                logits_diag = outputs['diagnosis']
                prob_malignant = torch.sigmoid(logits_diag).item()
                
                # We can also log or use aux outputs here if needed
                # e.g., print(f"ER Prob: {torch.sigmoid(outputs['ER']).item()}")
                
                diagnosis = "Malignant" if prob_malignant > 0.5 else "Benign"
                confidence = prob_malignant if diagnosis == "Malignant" else (1 - prob_malignant)
                return diagnosis, confidence

        else:
            # Sklearn Inference (Legacy)
            X = processed_y.reshape(1, -1)
            # ... (Reuse existing resampling logic if strictly needed, but assuming data is consistent)
            try:
                if hasattr(cls._current_model, 'n_features_in_'):
                    if X.shape[1] != cls._current_model.n_features_in_:
                         # Resample logic (simplified)
                         from scipy import interpolate
                         current_x = np.linspace(0, 1, X.shape[1])
                         target_x = np.linspace(0, 1, cls._current_model.n_features_in_)
                         f = interpolate.interp1d(current_x, processed_y, kind='linear', fill_value="extrapolate")
                         X = f(target_x).reshape(1, -1)
                
                prob = cls._current_model.predict_proba(X)[0]
                prediction = cls._current_model.predict(X)[0]
                diagnosis = "Malignant" if prediction == 1 else "Benign"
                confidence = prob[prediction]
                return diagnosis, confidence
            except Exception as e:
                print(f"Inference error: {e}")
                return "Error", 0.0

    @classmethod
    def train_new_version(cls, version_name=None, description=""):
        """
        触发新模型训练 (CNN Multi-Task)
        Trigger new model training
        """
        print("Starting CNN training pipeline...")
        
        # 1. Fetch data
        records = SpectrumRecord.objects.filter(is_training_data=True)
        if not records.exists():
            return {"status": "error", "message": "No training data found"}

        X_data = []
        y_data = []
        metadata_list = []
        
        for record in records:
            if not record.spectral_data or 'y' not in record.spectral_data:
                continue
            
            # Preprocess
            raw_y = record.spectral_data['y']
            wavenumbers = record.spectral_data.get('x', [])
            processed_y = RamanPreprocessor.process_pipeline(wavenumbers, raw_y)
            
            # Ensure fixed length 1801
            if len(processed_y) != 1801:
                 from scipy import interpolate
                 current_x = np.linspace(0, 1, len(processed_y))
                 target_x = np.linspace(0, 1, 1801)
                 f = interpolate.interp1d(current_x, processed_y, kind='linear', fill_value="extrapolate")
                 processed_y = f(target_x)

            X_data.append(processed_y)
            label = 1.0 if record.diagnosis_result == 'Malignant' else 0.0
            y_data.append(label)
            metadata_list.append(record.metadata or {})

        # 2. Dataset & DataLoader
        dataset = RamanDataset(X_data, y_data, metadata_list)
        train_size = int(0.8 * len(dataset))
        test_size = len(dataset) - train_size
        train_ds, test_ds = random_split(dataset, [train_size, test_size])
        
        train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
        test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)
        
        # 3. Model Setup
        model = MultiTaskRamanCNN(input_length=1801)
        optimizer = optim.Adam(model.parameters(), lr=1e-3)
        
        # 4. Training Loop
        epochs = 10 # Keep it small for demo/fast feedback, usually 50+
        model.train()
        
        def masked_loss(pred, target):
            # Target shape: (Batch, 1)
            # Mask: 1 where target != -1, else 0
            mask = (target != -1.0).float()
            # BCEWithLogitsLoss (per element)
            criterion = nn.BCEWithLogitsLoss(reduction='none')
            loss = criterion(pred, target)
            loss = loss * mask
            # Avoid division by zero
            return loss.sum() / (mask.sum() + 1e-6)

        for epoch in range(epochs):
            total_loss = 0
            for X_batch, y_batch, aux_batch in train_loader:
                optimizer.zero_grad()
                outputs = model(X_batch)
                
                # Main Task Loss
                l_diag = nn.BCEWithLogitsLoss()(outputs['diagnosis'], y_batch.unsqueeze(1))
                
                # Aux Task Losses (ER, PR, HER2, Ki67)
                # aux_batch shape: (Batch, 4) -> [ER, PR, HER2, Ki67]
                l_er = masked_loss(outputs['ER'], aux_batch[:, 0:1])
                l_pr = masked_loss(outputs['PR'], aux_batch[:, 1:2])
                l_her2 = masked_loss(outputs['HER2'], aux_batch[:, 2:3])
                l_ki67 = masked_loss(outputs['Ki67'], aux_batch[:, 3:4])
                
                loss = l_diag + 0.2 * (l_er + l_pr + l_her2 + l_ki67)
                
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(train_loader):.4f}")

        # 5. Evaluate (Simple Accuracy on Main Task)
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for X_batch, y_batch, _ in test_loader:
                outputs = model(X_batch)
                preds = torch.sigmoid(outputs['diagnosis']) > 0.5
                correct += (preds.float() == y_batch.unsqueeze(1)).sum().item()
                total += y_batch.size(0)
        
        acc = correct / total if total > 0 else 0.0
        
        # 6. Save
        if not version_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
            version_name = f"v{timestamp}_cnn"
            
        models_dir = Path(settings.BASE_DIR) / "models_storage"
        models_dir.mkdir(exist_ok=True)
        model_path = models_dir / f"{version_name}.pth"
        
        save_dict = {
            'state_dict': model.state_dict(),
            'config': {'input_length': 1801}
        }
        torch.save(save_dict, model_path)
        
        # 7. Register
        ModelVersion.objects.create(
            version=version_name,
            file_path=str(model_path),
            accuracy=acc,
            metrics={'accuracy': acc},
            is_active=True,
            description=description or "Multi-Task CNN Model"
        )
        
        # Deactivate others
        ModelVersion.objects.exclude(version=version_name).update(is_active=False)
        
        # Reload
        cls.load_active_model()
        
        return {"status": "success", "version": version_name, "accuracy": acc}
