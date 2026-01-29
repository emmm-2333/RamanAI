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
    def train_new_version(cls, version_name, description=""):
        """
        触发新模型训练 (Placeholder)
        """
        # 1. Fetch data from SpectrumRecord where is_training_data=True
        # 2. Train sklearn model
        # 3. Save .pkl
        # 4. Create ModelVersion record
        pass
