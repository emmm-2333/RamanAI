# RamanAI 项目改进路线图

> 基于对项目全代码库的系统性审查，整理出当前存在的问题及对应的改进建议。
> 按优先级分为三个层级：**P0（阻塞上线）**、**P1（上线前强烈建议）**、**P2（中长期优化）**。

---

## P0 — 安全漏洞（必须修复，否则不应上线）

### 1. 数据库密码与 SECRET_KEY 硬编码在源码中

**位置**: `backend/raman_backend/settings.py`

**现状**:

```python
DATABASES = {
    'default': {
        'PASSWORD': '7355608',   # 裸密码直接暴露
    }
}
SECRET_KEY = 'django-insecure-...'  # 开发默认值未替换
DEBUG = True                         # 生产环境应为 False
```

**风险**: 一旦代码仓库被公开或泄漏，数据库和整个 Django 框架都会立刻暴露。

**修复方案**: 使用已安装的 `django-environ` 从 `.env` 文件中读取所有敏感值，并确保 `.env` 被 `.gitignore` 忽略（当前 `.gitignore` 已有 `.env` 条目，但 `settings.py` 尚未对接）。

```python
# settings.py
import environ
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
DATABASES = {'default': env.db()}   # DATABASE_URL=mysql://user:pass@host/db
```

---

### 2. JWT Refresh Token 有效期异常短

**位置**: `backend/raman_backend/settings.py`

**现状**: Refresh Token 仅 1 天，Access Token 60 分钟。对于临床使用场景，医生在夜班期间 token 会过期，造成不必要的重新登录。

**建议**:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
```

---

## P1 — 核心功能与稳定性问题

### 3. 模型训练阻塞 HTTP 请求（最高优先级功能问题）

**位置**: `backend/raman_api/views.py` → 触发训练的端点
**位置**: `backend/raman_api/ml_engine.py` → `train_new_version()`

**现状**: 训练在 API 请求的同步调用链中执行。1370 条样本 × 10 epoch 在 CPU 上需要数十秒，极易导致：

- Nginx/Gunicorn 超时（默认 30s）
- 客户端收到 502/504
- 请求进程被 killed，但训练子进程仍在后台悬空

**建议**: 引入 Celery + Redis/RabbitMQ 异步任务队列。

```python
# tasks.py (新建)
from celery import shared_task
from .ml_engine import train_new_version

@shared_task(bind=True)
def train_model_task(self, record_ids):
    return train_new_version(record_ids)

# views.py
result = train_model_task.delay(record_ids)
return Response({'task_id': result.id, 'status': 'queued'})
```

前端可轮询 `/api/v1/tasks/{task_id}/status/` 展示训练进度。

---

### 4. 训练轮数严重不足，缺少必要的训练策略

**位置**: `backend/raman_api/ml_engine.py`

**现状**:

```python
epochs = 10      # 仅用于快速演示，无法收敛到有效精度
optimizer = Adam(lr=1e-3)   # 无学习率调度
# 无早停 (Early Stopping)
# 无验证损失监控
```

**建议**:

```python
# 推荐训练配置
epochs = 100
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, mode='min', patience=10, factor=0.5
)
# 早停：验证损失连续 15 轮不下降时停止
# 保存验证集上 loss 最低的 checkpoint（而非最后一轮）
```

---

### 5. 医疗场景下的评估指标严重不足

**位置**: `backend/raman_api/ml_engine.py` → 训练结束后的评估段

**现状**: 仅计算整体 Accuracy，这在癌症诊断场景中是不够的——一个总是预测"良性"的模型也能达到 70%+ Accuracy。

**建议**，训练结束后计算并写入 `ModelVersion.metrics`:

| 指标                                        | 说明                           |
| ------------------------------------------- | ------------------------------ |
| `AUC-ROC`                                   | 综合判别能力，医学论文标准指标 |
| `Sensitivity (Recall)`                      | 恶性漏诊率，临床最关键         |
| `Specificity`                               | 良性误诊为恶性率               |
| `PPV / NPV`                                 | 阳性/阴性预测值                |
| `F1-Score`                                  | 综合精确率和召回率             |
| 每个辅助任务 (ER/PR/HER2/Ki67) 的各上述指标 |

```python
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix

metrics = {
    'auc_roc': roc_auc_score(y_true, y_prob),
    'sensitivity': recall_score(y_true, y_pred),
    'specificity': tn / (tn + fp),
    'f1': f1_score(y_true, y_pred),
    'confusion_matrix': cm.tolist(),
}
```

---

### 6. 类别不平衡问题未处理

**位置**: `backend/raman_api/ml_engine.py`

**现状**: 训练时直接使用 `BCEWithLogitsLoss()`，未考虑良恶性样本比例。如果恶性样本显著少于良性，模型会倾向于预测多数类。

**建议**:

1. 训练前统计类别分布并记录到日志
2. 使用带权重的损失函数：

```python
# 自动计算权重
from sklearn.utils.class_weight import compute_class_weight
weights = compute_class_weight('balanced', classes=[0,1], y=labels)
pos_weight = torch.tensor([weights[1] / weights[0]])
criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
```

---

### 7. 测试覆盖完全缺失

**位置**: `backend/raman_api/tests.py`（空文件）

**现状**: 无任何单元测试或集成测试。代码重构或依赖升级时风险极高。

**建议**，优先为以下模块补充测试：

```
tests/
├── test_preprocessing.py   # 预处理管线各步骤的输入输出验证
├── test_ml_engine.py       # predict() mock 模型推理端到端测试
├── test_views.py           # API 端点集成测试（上传、训练触发、反馈）
└── test_models.py          # 数据库模型约束测试
```

最低目标：核心推理路径（上传→预处理→预测→返回）有集成测试覆盖。

---

### 8. 预处理参数无版本化，存在训练/推理漂移风险

**位置**: `backend/raman_api/preprocessing.py` + `ml_engine.py`

**现状**: `RamanPreprocessor` 中使用的平滑窗口大小、多项式阶数等参数是代码内硬编码的全局默认值。若日后修改了预处理参数，旧模型在推理时将使用新参数，导致输入分布与训练时不一致。

**建议**: 将预处理配置与模型 checkpoint 一同保存：

```python
# 保存 checkpoint 时
checkpoint = {
    'model_state': model.state_dict(),
    'config': {
        'input_length': 1801,
        'preprocessing': {
            'smooth': True,
            'smooth_window': 11,
            'smooth_polyorder': 3,
            'baseline_method': 'poly',
            'baseline_degree': 5,
            'normalize_method': 'minmax',
        }
    }
}

# 推理时从 checkpoint 读取预处理参数
preprocessor = RamanPreprocessor(**checkpoint['config']['preprocessing'])
```

---

## P2 — 代码质量与长期可维护性

### 9. 前端翻译函数重复定义

**位置**: `frontend/src/views/Dashboard.vue` 和 `frontend/src/views/record/RecordDetail.vue`

**现状**: `translateMarker()` 和 `translateStatus()` 两个翻译函数在两个文件中各定义了一次，内容相同，违反 DRY 原则。

**建议**: 抽取为 Vue composable：

```javascript
// src/composables/useTranslations.js
export function useTranslations() {
  const markerMap = {
    ER: "ER受体",
    PR: "PR受体",
    HER2: "HER2",
    Ki67: "Ki67增殖",
  };
  const statusMap = {
    Positive: "阳性",
    Negative: "阴性",
    Malignant: "恶性",
    Benign: "良性",
  };

  const translateMarker = (key) => markerMap[key] ?? key;
  const translateStatus = (val) => statusMap[val] ?? val;

  return { translateMarker, translateStatus };
}
```

在两个组件中统一导入使用：

```javascript
import { useTranslations } from "@/composables/useTranslations";
const { translateMarker, translateStatus } = useTranslations();
```

---

### 10. 大型视图文件缺乏组件拆分

**位置**: `frontend/src/views/Dashboard.vue`（约 438 行）和 `views.py`（约 540 行）

**现状**: `Dashboard.vue` 在一个文件中混合了文件上传逻辑、光谱图绘制、诊断结果展示、患者信息录入等多种职责。

**建议**，拆分为子组件：

```
components/
├── spectrum/
│   ├── SpectrumChart.vue        # ECharts 光谱图（独立、可复用）
│   ├── UploadDropzone.vue       # 文件拖拽上传
│   └── DiagnosisResultCard.vue  # 诊断结果 + 分子分型展示
```

后端 `views.py` 中也可将上传逻辑、训练逻辑、反馈逻辑分拆到独立的 ViewSet 类中。

---

### 11. `views.py` 中部分裸露异常处理

**位置**: `backend/raman_api/views.py`

**现状**: 部分 try-except 块捕获了宽泛的 `Exception` 后不记录详情或直接忽略，导致线上排查困难。

**建议**:

```python
import logging
logger = logging.getLogger(__name__)

try:
    result = ml_engine.predict(...)
except Exception as e:
    logger.exception("推理失败: record_id=%s", record_id)
    return Response({'error': '模型推理失败，请联系管理员'}, status=500)
```

并在 `settings.py` 中配置 Django Logging 将 ERROR 级别日志写入文件或发送到监控平台。

---

### 12. 旧版 RandomForest 模型文件残留

**位置**: `backend/models_storage/`

**现状**: 有 3 个旧版 `.pkl` RandomForest 模型文件（rf_v1.0.0、rf_v202601、rf_v202601311947），其中最新版已切换为 CNN。这些文件占用空间且可能造成混淆。

**建议**:

- 将无用的 `.pkl` 文件从 Git 历史中清理（`git rm --cached`），避免仓库膨胀
- 在 `ModelVersion` 数据库记录中标记已废弃的版本，而非保留文件

---

### 13. 数据原始文件不应纳入 Git 管理

**位置**: `data/data.xlsx`（21.5MB）、`data/data_full.csv`（21.5MB）、`data/csv/`（约 1371 个文件）

**现状**: 共约 43MB+ 的原始数据集被直接纳入 git 仓库，将导致：

- 仓库体积膨胀，克隆变慢
- 患者数据合规风险（应存储在安全的数据存储服务中）

**建议**:

1. 将 `data/` 加入 `.gitignore`
2. 使用 DVC（Data Version Control）或专用数据存储（OSS/S3）管理数据集
3. 确保原始患者数据的访问受权限控制

---

### 14. CNN 模型文件（`.pth`）不应纳入 Git 管理

**位置**: `backend/models_storage/v202602072317_cnn.pth`（58KB，未来会增大）

**现状**: 当前模型文件较小，但随着模型迭代，模型文件将越来越大。模型文件属于二进制大文件，不适合 Git 管理。

**建议**:

- 将 `backend/models_storage/*.pth` 和 `*.pkl` 加入 `.gitignore`
- 使用 Git LFS 或对象存储管理模型文件，在部署时从远程拉取活跃模型

---

### 15. 缺少 API 参数校验与输入约束

**位置**: `backend/raman_api/serializers.py` 和 `views.py`

**现状**: 部分 API 端点对输入数据的校验不够严格，例如批量导入时未对 Excel 列名进行强制校验，光谱数据长度未做上下限约束。

**建议**:

```python
# 在 serializer 中增加字段校验
class SpectrumDataSerializer(serializers.Serializer):
    x = serializers.ListField(child=serializers.FloatField(), min_length=100, max_length=5000)
    y = serializers.ListField(child=serializers.FloatField(), min_length=100, max_length=5000)

    def validate(self, data):
        if len(data['x']) != len(data['y']):
            raise serializers.ValidationError("x 和 y 数组长度必须一致")
        return data
```

---

## 汇总优先级表

| #   | 问题                   | 优先级 | 复杂度 | 影响范围   |
| --- | ---------------------- | ------ | ------ | ---------- |
| 1   | 密码/SECRET_KEY 硬编码 | P0     | 低     | 安全       |
| 2   | JWT 有效期配置         | P0     | 低     | 安全/体验  |
| 3   | 训练阻塞请求线程       | P1     | 高     | 稳定性     |
| 4   | 训练轮数/策略不足      | P1     | 中     | 模型质量   |
| 5   | 医疗评估指标缺失       | P1     | 中     | 模型可信度 |
| 6   | 类别不平衡未处理       | P1     | 低     | 模型质量   |
| 7   | 测试覆盖缺失           | P1     | 高     | 维护性     |
| 8   | 预处理无版本化         | P1     | 中     | 模型一致性 |
| 9   | 前端翻译函数重复       | P2     | 低     | 可维护性   |
| 10  | 大型文件未拆分         | P2     | 中     | 可维护性   |
| 11  | 裸露异常处理           | P2     | 低     | 可观测性   |
| 12  | 旧模型文件残留         | P2     | 低     | 整洁度     |
| 13  | 数据文件纳入 Git       | P2     | 低     | 合规/性能  |
| 14  | 模型文件纳入 Git       | P2     | 低     | 合规/性能  |
| 15  | API 输入校验不足       | P2     | 中     | 健壮性     |

---

_文档生成时间: 2026-03-14_
_基于代码库 commit: 5ba546f_ | 模型可信度 |
| 6 | 类别不平衡未处理 | P1 | 低 | 模型质量 |
| 7 | 测试覆盖缺失 | P1 | 高 | 维护性 |
| 8 | 预处理无版本化 | P1 | 中 | 模型一致性 |
| 9 | 前端翻译函数重复 | P2 | 低 | 可维护性 |
| 10 | 大型文件未拆分 | P2 | 中 | 可维护性 |
| 11 | 裸露异常处理 | P2 | 低 | 可观测性 |
| 12 | 旧模型文件残留 | P2 | 低 | 整洁度 |
| 13 | 数据文件纳入 Git | P2 | 低 | 合规/性能 |
| 14 | 模型文件纳入 Git | P2 | 低 | 合规/性能 |
| 15 | API 输入校验不足 | P2 | 中 | 健壮性 |

---

*文档生成时间: 2026-03-14*
*基于代码库 commit: 5ba546f*
