# 数据结构与数据库设计 (Data Schema)

本文档描述了系统的数据模型及 `data.xlsx` 数据集的导入策略。

## 1. 原始数据集 (`data.xlsx`)

*   **总样本数**: 1370
*   **特征维度**: ~1800 (波数范围: 400 - 2200 cm⁻¹)
*   **目标变量**: `良恶性0：良性1.恶性` (0=Benign, 1=Malignant)
*   **元数据**:
    *   `ER`, `HER2`, `Ki67`, `PR`: 免疫组化指标
    *   `分型`: 分子分型
    *   `姓名`, `病历号`: 患者标识

## 2. 数据库模型 (`models.py`)

系统使用 `SpectrumRecord` 存储光谱数据，不仅包含文件路径，还存储了结构化的光谱数据以支持机器学习。

### SpectrumRecord 模型

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `patient` | ForeignKey | 关联患者 (Patient) |
| `spectral_data` | JSONField | 核心数据，格式见下文 |
| `metadata` | JSONField | 临床元数据 (ER, HER2等) |
| `diagnosis_result` | CharField | 诊断结果 (Benign/Malignant) |
| `confidence_score` | FloatField | 置信度 (1.0 for Ground Truth) |
| `is_training_data` | BooleanField | 是否为训练集 (True for Imported Data) |

### JSON 数据格式

**`spectral_data` 结构:**

```json
{
  "x": [400, 401, 402, ...],  // 波数 (Wavenumbers)
  "y": [123.4, 456.7, ...]    // 强度 (Intensities)
}
```

**`metadata` 结构:**

```json
{
  "ER": "90%强+",
  "HER2": "1+",
  "Ki67": "10%+",
  "Label": "L-B",
  "RecordNo": "12514525"
}
```

## 3. 数据导入

使用脚本 `backend/scripts/import_data.py` 将 Excel 数据导入数据库。
该脚本会自动：
1. 创建或匹配 `Patient` (根据姓名)。
2. 提取光谱列（整数列名）存入 `spectral_data`。
3. 提取非光谱列存入 `metadata`。
4. 将 `良恶性` 映射为 Benign/Malignant。
