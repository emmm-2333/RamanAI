from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    """
    用户档案模型，扩展 Django 内置 User。
    存储用户角色信息。
    """
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='doctor', help_text="用户角色")

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Patient(models.Model):
    """
    病患信息模型。
    敏感信息（如姓名）在实际生产中应加密存储。
    """
    name = models.CharField(max_length=255, help_text="加密后的病患姓名")
    age = models.IntegerField(help_text="年龄")
    gender = models.CharField(max_length=10, choices=(('M', 'Male'), ('F', 'Female')), help_text="性别")
    created_at = models.DateTimeField(auto_now_add=True, help_text="创建时间")

    def __str__(self):
        return f"Patient {self.id} ({self.gender}, {self.age})"

class SpectrumRecord(models.Model):
    """
    拉曼光谱记录模型。
    存储原始文件、处理结果及诊断信息。
    """
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='records', help_text="关联病患")
    # 实际开发中应配置 MEDIA_ROOT
    file_path = models.CharField(max_length=500, help_text="原始光谱文件路径")
    processed_path = models.CharField(max_length=500, blank=True, null=True, help_text="预处理后数据路径")
    
    diagnosis_result = models.CharField(max_length=50, blank=True, null=True, help_text="诊断结果 (Benign/Malignant)")
    confidence_score = models.FloatField(blank=True, null=True, help_text="置信度 (0.0 - 1.0)")
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="上传时间")
    is_reviewed = models.BooleanField(default=False, help_text="是否经医生复核")
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="上传医生")

    # 新增字段用于存储原始数据和元数据
    spectral_data = models.JSONField(blank=True, null=True, help_text="光谱数据 {'x': [], 'y': []}")
    metadata = models.JSONField(blank=True, null=True, help_text="元数据 (ER, HER2, etc)")
    is_training_data = models.BooleanField(default=False, help_text="是否作为训练集")

    def __str__(self):
        return f"Record {self.id} - {self.diagnosis_result}"

class ModelVersion(models.Model):
    """
    模型版本管理
    """
    version = models.CharField(max_length=50, unique=True, help_text="版本号 (e.g. v1.0.0)")
    file_path = models.CharField(max_length=500, help_text="模型文件路径 (.pkl/.pth)")
    accuracy = models.FloatField(blank=True, null=True, help_text="验证集准确率")
    metrics = models.JSONField(blank=True, null=True, help_text="详细指标 (Precision, Recall)")
    is_active = models.BooleanField(default=False, help_text="是否为当前生产模型")
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Model {self.version} ({'Active' if self.is_active else 'Inactive'})"

class DiagnosisFeedback(models.Model):
    """
    医生反馈/修正记录 (Human-in-the-loop)
    """
    record = models.ForeignKey(SpectrumRecord, on_delete=models.CASCADE, related_name='feedbacks')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    original_diagnosis = models.CharField(max_length=50)
    corrected_diagnosis = models.CharField(max_length=50)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback on {self.record.id} by {self.doctor.username}"
