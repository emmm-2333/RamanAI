import os
import joblib
import numpy as np
from django.conf import settings
from .models import ModelVersion, SpectrumRecord
from .preprocessing import RamanPreprocessor

class MLEngine:
    """
    机器学习引擎: 负责模型加载、推理和训练触发
    """
    
    _current_model = None
    _model_version = None

    @classmethod
    def load_active_model(cls):
        """
        加载当前激活的模型
        """
        try:
            active_model_record = ModelVersion.objects.filter(is_active=True).last()
            if not active_model_record:
                print("No active model found.")
                return None
            
            model_path = active_model_record.file_path
            if os.path.exists(model_path):
                cls._current_model = joblib.load(model_path)
                cls._model_version = active_model_record.version
                print(f"Loaded model version: {cls._model_version}")
            else:
                print(f"Model file not found: {model_path}")
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
        
        # 2. Inference
        if cls._current_model:
            # Reshape for sklearn (1, n_features)
            X = processed_y.reshape(1, -1)
            
            # Feature alignment Check
            expected_features = cls._current_model.n_features_in_
            if X.shape[1] != expected_features:
                print(f"Feature mismatch: Model expects {expected_features}, got {X.shape[1]}. Resampling...")
                try:
                    from scipy import interpolate
                    # Assume standard wavenumbers 400-2200 for model (length 1801)
                    # Or generate indices if x is not consistent
                    
                    # Target wavenumbers (Model was trained on 400-2200 usually, or 0-1800 indices)
                    # Since we don't know exact x used in training, we assume standard range if count matches 1801
                    if expected_features == 1801:
                         target_x = np.linspace(400, 2200, 1801)
                    else:
                         # Fallback: simple interpolation to match count
                         target_x = np.linspace(spectral_data_x[0], spectral_data_x[-1], expected_features)
                    
                    # Current x
                    if len(spectral_data_x) == len(processed_y):
                        current_x = np.array(spectral_data_x)
                    else:
                        current_x = np.arange(len(processed_y))
                        
                    # Interpolate
                    f = interpolate.interp1d(current_x, processed_y, kind='linear', fill_value="extrapolate")
                    resampled_y = f(target_x)
                    X = resampled_y.reshape(1, -1)
                    
                except Exception as e:
                    print(f"Resampling failed: {e}")
                    # Let it fail naturally in predict below or return error
            
            # Assuming model predicts 0 (Benign) or 1 (Malignant)
            prob = cls._current_model.predict_proba(X)[0]
            prediction = cls._current_model.predict(X)[0]
            
            diagnosis = "Malignant" if prediction == 1 else "Benign"
            confidence = prob[prediction]
            return diagnosis, confidence
        else:
            # Fallback / Dummy Logic for now
            # E.g. simple rule: high intensity at specific peak?
            # Random for demo if no model
            return "Unknown", 0.0

    @classmethod
    def train_new_version(cls, version_name=None, description=""):
        """
        触发新模型训练
        """
        from .models import SpectrumRecord, ModelVersion
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, classification_report
        import joblib
        from pathlib import Path
        import datetime

        print("Starting training pipeline...")
        
        # 1. Fetch data
        records = SpectrumRecord.objects.filter(is_training_data=True)
        if not records.exists():
            return {"status": "error", "message": "No training data found"}

        X = []
        y = []
        
        for record in records:
            if not record.spectral_data or 'y' not in record.spectral_data:
                continue
            
            # Preprocess
            raw_y = record.spectral_data['y']
            wavenumbers = record.spectral_data.get('x', [])
            processed_y = RamanPreprocessor.process_pipeline(wavenumbers, raw_y)
            
            X.append(processed_y)
            label = 1 if record.diagnosis_result == 'Malignant' else 0
            y.append(label)

        X = np.array(X)
        y = np.array(y)
        
        # 2. Train
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)
        
        # 3. Evaluate
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # 4. Save
        if not version_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
            version_name = f"v{timestamp}"
            
        models_dir = Path(settings.BASE_DIR) / "models_storage"
        models_dir.mkdir(exist_ok=True)
        model_path = models_dir / f"rf_{version_name}.pkl"
        
        joblib.dump(clf, model_path)
        
        # 5. Register
        ModelVersion.objects.create(
            version=version_name,
            file_path=str(model_path),
            accuracy=acc,
            metrics=report,
            is_active=True, # Auto activate
            description=description or "Auto-trained model"
        )
        
        # Deactivate others
        ModelVersion.objects.exclude(version=version_name).update(is_active=False)
        
        # Reload current model
        cls.load_active_model()
        
        return {"status": "success", "version": version_name, "accuracy": acc}
