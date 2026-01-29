from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Patient, SpectrumRecord, ModelVersion, DiagnosisFeedback

class UserSerializer(serializers.ModelSerializer):
    """
    用户序列化器，用于注册和显示用户信息。
    """
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name', 'role')

    def create(self, validated_data):
        """
        创建用户时同步创建 UserProfile。
        """
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        # 默认角色为医生
        UserProfile.objects.create(user=user, role='doctor')
        return user

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'

class SpectrumRecordSerializer(serializers.ModelSerializer):
    """
    光谱记录序列化器 (列表视图优化版)。
    """
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = SpectrumRecord
        exclude = ('spectral_data',) # 列表接口不返回巨大的光谱数据字段
        read_only_fields = ('diagnosis_result', 'confidence_score', 'processed_path', 'created_at', 'uploaded_by', 'metadata')

class SpectrumRecordDetailSerializer(serializers.ModelSerializer):
    """
    光谱记录详情序列化器 (包含完整数据)。
    """
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = SpectrumRecord
        fields = '__all__'
        read_only_fields = ('diagnosis_result', 'confidence_score', 'processed_path', 'created_at', 'uploaded_by', 'metadata')

class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = '__all__'

class DiagnosisFeedbackSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.username', read_only=True)

    class Meta:
        model = DiagnosisFeedback
        fields = '__all__'
        read_only_fields = ('doctor', 'created_at')
