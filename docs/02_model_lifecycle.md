# 模型生命周期管理与持续学习 (Model Lifecycle)

## 1. 核心概念

系统采用“持续学习”机制，模型的生命周期不仅仅是“训练-部署”，而是一个闭环：

1.  **数据采集**: 临床采集或批量导入 (`SpectrumRecord`).
2.  **诊断**: 使用当前激活模型 (`ModelVersion` is_active=True).
3.  **反馈**: 医生复核诊断结果 (`DiagnosisFeedback`).
4.  **增量训练**: 结合新数据和反馈数据，训练新模型版本.
5.  **发布**: 评估新模型指标，替换旧模型.

## 2. 数据库设计

### ModelVersion (模型版本)
*   **Version**: v1.0, v1.1
*   **Metrics**: Accuracy, Precision, Recall
*   **File**: 存储 `.pkl` (sklearn) 或 `.pth` (PyTorch) 文件.

### DiagnosisFeedback (反馈)
*   记录医生对某条 `SpectrumRecord` 的修正意见.
*   字段: `original_diagnosis`, `corrected_diagnosis`.

## 3. 持续学习流程

1.  **触发条件**:
    *   新增有效标注数据 > 100 条.
    *   或者管理员手动点击“重新训练”.

2.  **训练流程 (Backend Job)**:
    *   加载 `is_training_data=True` 的所有 `SpectrumRecord`.
    *   提取 `spectral_data` (X) 和 `diagnosis_result` (Y).
    *   应用预处理 (Baseline, Smoothing).
    *   训练分类器 (SVM/RF).
    *   在验证集上评估.
    *   保存为新版本 `ModelVersion`.

3.  **模型切换**:
    *   API 请求 `/predict` 时，`MLEngine` 动态加载 `is_active=True` 的最新模型.

## 4. API 接口 (规划中)

*   `POST /api/model/train`: 触发训练.
*   `POST /api/feedback`: 提交诊断反馈.
*   `GET /api/model/history`: 查看历史版本.
