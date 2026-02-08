# 多任务学习与分子分型预测实现文档

## 1. 概述 (Overview)

为了充分利用临床数据中的免疫组化指标（ER, PR, HER2, Ki67），本项目引入了 **多任务学习 (Multi-Task Learning, MTL)** 机制。通过构建一个共享骨干网络的卷积神经网络 (CNN)，模型不仅能进行良恶性诊断（主任务），还能同时预测分子分型（辅助任务）。

这种方法不仅提供了额外的临床辅助信息，还通过强制模型学习分子生物学特征与光谱特征的关联，提升了主任务的泛化能力和鲁棒性。

## 2. 模型架构 (Model Architecture)

新实现的 `MultiTaskRamanCNN` 模型位于 `backend/raman_api/cnn.py`。

### 2.1 核心结构
*   **输入层**: 接收长度为 1801 的一维拉曼光谱数据。
*   **共享骨干网 (Shared Backbone)**:
    *   3 层 1D 卷积层 (Conv1d)，配合 BatchNorm 和 ReLU 激活函数。
    *   最大池化层 (MaxPool1d) 用于下采样。
    *   全局平均池化 (AdaptiveAvgPool1d) 提取核心特征向量。
*   **共享全连接层**: 进一步融合特征。
*   **多头输出 (Multi-Heads)**:
    1.  **Diagnosis Head**: 输出良恶性概率 (Benign vs Malignant)。
    2.  **ER Head**: 输出雌激素受体状态 (Positive/Negative)。
    3.  **PR Head**: 输出孕激素受体状态 (Positive/Negative)。
    4.  **HER2 Head**: 输出人表皮生长因子受体2状态 (Positive/Negative)。
    5.  **Ki67 Head**: 输出细胞增殖指数状态 (High/Low)。

## 3. 数据处理与增强 (Data Processing)

### 3.1 元数据解析 (`backend/raman_api/utils/dataset.py`)
为了处理数据库中非标准化的文本数据，我们实现了 `MetadataParser`：
*   **ER/PR**: 识别 "Positive", "+", "阳性" 为 1.0；"Negative", "-", "阴性" 为 0.0。
*   **HER2**: 识别 "3+", "Positive" 为 1.0；"0", "1+", "Negative" 为 0.0。
*   **Ki67**: 提取百分比数值，以 14% 为阈值，>=14% 标记为 High (1.0)，否则为 Low (0.0)。
*   **缺失值处理**: 任何无法解析或缺失的数据标记为 `-1.0`。

### 3.2 训练策略 (`backend/raman_api/ml_engine.py`)
*   **掩码损失函数 (Masked Loss)**: 
    *   在计算辅助任务的 Loss 时，自动忽略标记为 `-1.0` (缺失) 的样本。
    *   这使得模型可以利用不完整的数据集进行训练，而不会被缺失值误导。
*   **联合损失优化**:
    *   `Total Loss = Loss_Diagnosis + 0.2 * (Loss_ER + Loss_PR + Loss_HER2 + Loss_Ki67)`
    *   主任务权重最高，辅助任务作为正则化项引导特征学习。

## 4. 前端展示与汉化 (Frontend)

### 4.1 界面更新
*   **Dashboard (`Dashboard.vue`)**: 新增“分子分型预测”区域，实时展示上传光谱的 AI 分析结果。
*   **RecordDetail (`RecordDetail.vue`)**: 在历史记录详情页展示完整的分子分型预测报告。

### 4.2 汉化映射
为了符合国内医疗场景，所有英文术语均已汉化：
*   **指标**:
    *   ER → ER (雌激素受体)
    *   PR → PR (孕激素受体)
    *   HER2 → HER2 (人表皮生长因子受体2)
    *   Ki67 → Ki67 (细胞增殖指数)
*   **状态**:
    *   Positive → 阳性
    *   Negative → 阴性
    *   High → 高表达
    *   Low → 低表达

## 5. API 变更 (API Changes)

*   **MLEngine.predict**:
    *   旧签名: `predict(x, y) -> (diagnosis, confidence)`
    *   新签名: `predict(x, y) -> (diagnosis, confidence, predictions_dict)`
*   **数据持久化**:
    *   预测结果自动存储在 `SpectrumRecord.metadata['predicted_markers']` 字段中，确保历史可追溯。

---
*文档生成时间: 2026-02-07*
