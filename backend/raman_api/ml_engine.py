import os
import logging
import threading
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

logger = logging.getLogger(__name__)

# 默认预处理配置，随 checkpoint 一起保存，确保训练/推理一致性
DEFAULT_PREPROCESSING_CONFIG = {
    'smooth': True,
    'smooth_window': 11,
    'smooth_polyorder': 3,
    'baseline': True,
    'baseline_method': 'poly',
    'baseline_degree': 5,
    'normalize': True,
    'normalize_method': 'minmax',
    'derivative': 0,
}

TARGET_INPUT_LENGTH = 1801


def _interpolate_to_length(y, target_len=TARGET_INPUT_LENGTH):
    """将光谱插值到目标长度"""
    if len(y) == target_len:
        return y
    from scipy import interpolate
    current_x = np.linspace(0, 1, len(y))
    target_x = np.linspace(0, 1, target_len)
    f = interpolate.interp1d(current_x, y, kind='linear', fill_value='extrapolate')
    return f(target_x)


class MLEngine:
    """
    机器学习引擎：负责模型加载、推理和训练。
    训练通过 start_training_async() 异步触发，不阻塞 HTTP 请求。
    """

    _current_model = None
    _model_type = None       # 'sklearn' or 'torch'
    _model_version = None
    _model_config = {}
    _preprocessing_config = DEFAULT_PREPROCESSING_CONFIG.copy()

    # 异步训练状态
    _training_lock = threading.Lock()
    _training_status = {
        'running': False,
        'version': None,
        'progress': '',
        'result': None,
        'error': None,
    }

    # -------------------------------------------------------------------------
    # 模型加载
    # -------------------------------------------------------------------------

    @classmethod
    def load_active_model(cls):
        """加载当前激活的模型"""
        try:
            active_model_record = ModelVersion.objects.filter(is_active=True).last()
            if not active_model_record:
                logger.warning("No active model found in database.")
                return

            model_path = active_model_record.file_path
            if not os.path.exists(model_path):
                logger.error("Model file not found: %s", model_path)
                return

            if model_path.endswith('.pth'):
                checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
                if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
                    state_dict = checkpoint['state_dict']
                    cls._model_config = checkpoint.get('config', {})
                    # 加载随 checkpoint 保存的预处理配置
                    cls._preprocessing_config = checkpoint.get(
                        'preprocessing', DEFAULT_PREPROCESSING_CONFIG.copy()
                    )
                else:
                    state_dict = checkpoint
                    cls._model_config = {}
                    cls._preprocessing_config = DEFAULT_PREPROCESSING_CONFIG.copy()

                input_len = cls._model_config.get('input_length', TARGET_INPUT_LENGTH)
                cls._current_model = MultiTaskRamanCNN(input_length=input_len)
                cls._current_model.load_state_dict(state_dict)
                cls._current_model.eval()
                cls._model_type = 'torch'
            else:
                cls._current_model = joblib.load(model_path)
                cls._model_type = 'sklearn'
                cls._preprocessing_config = DEFAULT_PREPROCESSING_CONFIG.copy()

            cls._model_version = active_model_record.version
            logger.info("Loaded model version: %s (%s)", cls._model_version, cls._model_type)

        except Exception:
            logger.exception("Failed to load active model.")

    # -------------------------------------------------------------------------
    # 推理
    # -------------------------------------------------------------------------

    @classmethod
    def predict(cls, spectral_data_x, spectral_data_y):
        """
        推理接口
        :return: (diagnosis, confidence, predictions_dict)
        """
        # 使用与训练时相同的预处理配置
        preprocess_cfg = cls._preprocessing_config or DEFAULT_PREPROCESSING_CONFIG
        processed_y = RamanPreprocessor.process_pipeline(
            spectral_data_x, spectral_data_y, preprocess_cfg
        )

        if not cls._current_model:
            logger.warning("Predict called but no model is loaded.")
            return "Unknown", 0.0, {}

        if cls._model_type == 'torch':
            processed_y = _interpolate_to_length(processed_y, TARGET_INPUT_LENGTH)
            tensor_x = torch.tensor(processed_y, dtype=torch.float32).view(1, 1, -1)

            with torch.no_grad():
                outputs = cls._current_model(tensor_x)
                prob_malignant = torch.sigmoid(outputs['diagnosis']).item()

                diagnosis = "Malignant" if prob_malignant > 0.5 else "Benign"
                confidence = prob_malignant if diagnosis == "Malignant" else (1 - prob_malignant)

                predictions = {
                    'ER':   'Positive' if torch.sigmoid(outputs['ER']).item() > 0.5 else 'Negative',
                    'PR':   'Positive' if torch.sigmoid(outputs['PR']).item() > 0.5 else 'Negative',
                    'HER2': 'Positive' if torch.sigmoid(outputs['HER2']).item() > 0.5 else 'Negative',
                    'Ki67': 'High'     if torch.sigmoid(outputs['Ki67']).item() > 0.5 else 'Low',
                }

            return diagnosis, confidence, predictions

        else:
            # Sklearn 遗留模型
            X = _interpolate_to_length(processed_y, cls._current_model.n_features_in_
                                       if hasattr(cls._current_model, 'n_features_in_') else len(processed_y))
            X = X.reshape(1, -1)
            try:
                prob = cls._current_model.predict_proba(X)[0]
                prediction = cls._current_model.predict(X)[0]
                diagnosis = "Malignant" if prediction == 1 else "Benign"
                confidence = prob[prediction]
                return diagnosis, confidence, {}
            except Exception:
                logger.exception("Sklearn inference failed.")
                return "Error", 0.0, {}

    # -------------------------------------------------------------------------
    # 异步训练入口（P1-3）
    # -------------------------------------------------------------------------

    @classmethod
    def start_training_async(cls, version_name=None, description=""):
        """
        在后台线程中触发训练，立即返回状态信息，不阻塞 HTTP 请求。
        """
        with cls._training_lock:
            if cls._training_status['running']:
                return {
                    'status': 'already_running',
                    'message': '已有训练任务正在进行，请稍后再试',
                    'version': cls._training_status['version'],
                }
            cls._training_status.update({
                'running': True,
                'version': version_name,
                'progress': '已排队',
                'result': None,
                'error': None,
            })

        thread = threading.Thread(
            target=cls._training_worker,
            args=(version_name, description),
            daemon=True,
        )
        thread.start()

        return {
            'status': 'queued',
            'message': '训练任务已在后台启动，可通过 /api/v1/models/train_status/ 查询进度',
        }

    @classmethod
    def get_training_status(cls):
        """返回当前训练状态快照"""
        with cls._training_lock:
            return dict(cls._training_status)

    @classmethod
    def _training_worker(cls, version_name, description):
        """后台线程实际执行的训练逻辑"""
        try:
            result = cls.train_new_version(version_name=version_name, description=description)
            with cls._training_lock:
                cls._training_status.update({
                    'running': False,
                    'progress': '完成',
                    'result': result,
                    'error': None,
                })
        except Exception as exc:
            logger.exception("Background training failed.")
            with cls._training_lock:
                cls._training_status.update({
                    'running': False,
                    'progress': '失败',
                    'result': None,
                    'error': str(exc),
                })

    # -------------------------------------------------------------------------
    # 训练核心（P1-4/5/6/8）
    # -------------------------------------------------------------------------

    @classmethod
    def train_new_version(cls, version_name=None, description=""):
        """
        训练新版本 CNN 模型。
        改进点：
          - 预处理配置随 checkpoint 序列化（P1-8）
          - 类别不平衡加权损失（P1-6）
          - 早停 + ReduceLROnPlateau（P1-4）
          - 医疗级评估指标（P1-5）
        """
        logger.info("Starting CNN training pipeline...")

        # 1. 准备数据
        records = SpectrumRecord.objects.filter(is_training_data=True)
        if not records.exists():
            return {"status": "error", "message": "No training data found"}

        preprocess_cfg = DEFAULT_PREPROCESSING_CONFIG.copy()

        X_data, y_data, metadata_list = [], [], []
        for record in records:
            if not record.spectral_data or 'y' not in record.spectral_data:
                continue
            raw_y = record.spectral_data['y']
            wavenumbers = record.spectral_data.get('x', [])
            processed_y = RamanPreprocessor.process_pipeline(wavenumbers, raw_y, preprocess_cfg)
            processed_y = _interpolate_to_length(processed_y, TARGET_INPUT_LENGTH)
            X_data.append(processed_y)
            y_data.append(1.0 if record.diagnosis_result == 'Malignant' else 0.0)
            metadata_list.append(record.metadata or {})

        if not X_data:
            return {"status": "error", "message": "No valid spectral data found in training records"}

        # 统计类别分布（P1-6）
        labels_arr = np.array(y_data)
        n_malignant = int(labels_arr.sum())
        n_benign = len(labels_arr) - n_malignant
        logger.info("Training data: %d total | %d malignant | %d benign",
                    len(labels_arr), n_malignant, n_benign)
        cls._training_status['progress'] = f"数据准备完成 ({len(labels_arr)} 条)"

        # 2. Dataset & DataLoader
        dataset = RamanDataset(X_data, y_data, metadata_list)
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_ds, val_ds = random_split(dataset, [train_size, val_size])

        train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)

        # 3. 模型与优化器
        model = MultiTaskRamanCNN(input_length=TARGET_INPUT_LENGTH)
        optimizer = optim.Adam(model.parameters(), lr=1e-3)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', patience=10, factor=0.5, min_lr=1e-6
        )

        # 类别不平衡权重（P1-6）
        pos_weight = None
        if n_benign > 0 and n_malignant > 0:
            pos_weight = torch.tensor([n_benign / n_malignant], dtype=torch.float32)
            logger.info("Using pos_weight=%.3f for imbalanced classes", pos_weight.item())

        def masked_loss(pred, target):
            mask = (target != -1.0).float()
            criterion = nn.BCEWithLogitsLoss(reduction='none')
            loss = criterion(pred, target)
            return (loss * mask).sum() / (mask.sum() + 1e-6)

        # 4. 训练循环（P1-4：100 epochs + 早停）
        max_epochs = 100
        patience = 15
        best_val_loss = float('inf')
        no_improve_count = 0
        best_state = None

        for epoch in range(max_epochs):
            model.train()
            train_loss = 0.0
            for X_batch, y_batch, aux_batch in train_loader:
                optimizer.zero_grad()
                outputs = model(X_batch)

                criterion_main = (
                    nn.BCEWithLogitsLoss(pos_weight=pos_weight)
                    if pos_weight is not None
                    else nn.BCEWithLogitsLoss()
                )
                l_diag = criterion_main(outputs['diagnosis'], y_batch.unsqueeze(1))
                l_er   = masked_loss(outputs['ER'],   aux_batch[:, 0:1])
                l_pr   = masked_loss(outputs['PR'],   aux_batch[:, 1:2])
                l_her2 = masked_loss(outputs['HER2'], aux_batch[:, 2:3])
                l_ki67 = masked_loss(outputs['Ki67'], aux_batch[:, 3:4])

                loss = l_diag + 0.2 * (l_er + l_pr + l_her2 + l_ki67)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            train_loss /= len(train_loader)

            # 验证损失（用于调度器和早停）
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for X_batch, y_batch, aux_batch in val_loader:
                    outputs = model(X_batch)
                    criterion_main = (
                        nn.BCEWithLogitsLoss(pos_weight=pos_weight)
                        if pos_weight is not None
                        else nn.BCEWithLogitsLoss()
                    )
                    l_diag = criterion_main(outputs['diagnosis'], y_batch.unsqueeze(1))
                    l_er   = masked_loss(outputs['ER'],   aux_batch[:, 0:1])
                    l_pr   = masked_loss(outputs['PR'],   aux_batch[:, 1:2])
                    l_her2 = masked_loss(outputs['HER2'], aux_batch[:, 2:3])
                    l_ki67 = masked_loss(outputs['Ki67'], aux_batch[:, 3:4])
                    val_loss += (l_diag + 0.2 * (l_er + l_pr + l_her2 + l_ki67)).item()
            val_loss /= len(val_loader)

            scheduler.step(val_loss)
            logger.info("Epoch %d/%d | train_loss=%.4f | val_loss=%.4f",
                        epoch + 1, max_epochs, train_loss, val_loss)
            cls._training_status['progress'] = (
                f"训练中 Epoch {epoch + 1}/{max_epochs} "
                f"[train={train_loss:.4f} val={val_loss:.4f}]"
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                no_improve_count = 0
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
            else:
                no_improve_count += 1
                if no_improve_count >= patience:
                    logger.info("Early stopping at epoch %d (no improvement for %d epochs).",
                                epoch + 1, patience)
                    break

        # 使用验证集上最优 checkpoint
        if best_state is not None:
            model.load_state_dict(best_state)

        # 5. 评估（P1-5：医疗级指标）
        model.eval()
        all_probs, all_preds, all_labels = [], [], []
        with torch.no_grad():
            for X_batch, y_batch, _ in val_loader:
                outputs = model(X_batch)
                probs = torch.sigmoid(outputs['diagnosis']).squeeze(1)
                preds = (probs > 0.5).float()
                all_probs.extend(probs.tolist())
                all_preds.extend(preds.tolist())
                all_labels.extend(y_batch.tolist())

        metrics = _compute_medical_metrics(all_labels, all_preds, all_probs)
        logger.info("Evaluation metrics: %s", metrics)

        # 6. 保存 checkpoint（含预处理配置）
        if not version_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
            version_name = f"v{timestamp}_cnn"

        models_dir = Path(settings.BASE_DIR) / "models_storage"
        models_dir.mkdir(exist_ok=True)
        model_path = models_dir / f"{version_name}.pth"

        torch.save({
            'state_dict': model.state_dict(),
            'config': {'input_length': TARGET_INPUT_LENGTH},
            'preprocessing': preprocess_cfg,   # P1-8：版本化预处理配置
        }, model_path)

        # 7. 注册到数据库
        ModelVersion.objects.create(
            version=version_name,
            file_path=str(model_path),
            accuracy=metrics.get('accuracy', 0.0),
            metrics=metrics,
            is_active=True,
            description=description or "Multi-Task CNN Model",
        )
        ModelVersion.objects.exclude(version=version_name).update(is_active=False)

        # 重新加载新模型
        cls.load_active_model()

        return {"status": "success", "version": version_name, "metrics": metrics}


def _compute_medical_metrics(y_true, y_pred, y_prob):
    """计算临床诊断必需的评估指标（P1-5）"""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_prob = np.array(y_prob)

    tp = ((y_pred == 1) & (y_true == 1)).sum()
    tn = ((y_pred == 0) & (y_true == 0)).sum()
    fp = ((y_pred == 1) & (y_true == 0)).sum()
    fn = ((y_pred == 0) & (y_true == 1)).sum()

    accuracy    = (tp + tn) / (tp + tn + fp + fn + 1e-9)
    sensitivity = tp / (tp + fn + 1e-9)   # 召回率 / 灵敏度（恶性不漏诊率）
    specificity = tn / (tn + fp + 1e-9)   # 特异度（良性不误诊率）
    ppv         = tp / (tp + fp + 1e-9)   # 阳性预测值
    npv         = tn / (tn + fn + 1e-9)   # 阴性预测值
    f1          = 2 * tp / (2 * tp + fp + fn + 1e-9)

    metrics = {
        'accuracy':    round(float(accuracy), 4),
        'sensitivity': round(float(sensitivity), 4),
        'specificity': round(float(specificity), 4),
        'ppv':         round(float(ppv), 4),
        'npv':         round(float(npv), 4),
        'f1':          round(float(f1), 4),
        'tp': int(tp), 'tn': int(tn), 'fp': int(fp), 'fn': int(fn),
    }

    # AUC-ROC（需要 sklearn）
    try:
        from sklearn.metrics import roc_auc_score
        if len(np.unique(y_true)) > 1:
            metrics['auc_roc'] = round(float(roc_auc_score(y_true, y_prob)), 4)
    except Exception:
        pass

    return metrics
