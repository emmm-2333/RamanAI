from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Patient, SpectrumRecord, ModelVersion, DiagnosisFeedback


class SpectralDataSerializer(serializers.Serializer):
    """
    光谱数据输入校验器。
    用于接收 x/y 数组时，确保格式和长度合法。
    """
    x = serializers.ListField(
        child=serializers.FloatField(),
        min_length=100,
        max_length=5000,
        help_text="波数数组，100~5000 个点"
    )
    y = serializers.ListField(
        child=serializers.FloatField(),
        min_length=100,
        max_length=5000,
        help_text="强度数组，长度须与 x 一致"
    )

    def validate(self, data):
        if len(data['x']) != len(data['y']):
            raise serializers.ValidationError("x 和 y 数组长度必须一致")
        return data


class PreprocessConfigSerializer(serializers.Serializer):
    """
    预处理参数校验器，用于 /records/{id}/preprocess/ 接口。
    """
    smooth          = serializers.BooleanField(required=False, default=True)
    baseline        = serializers.BooleanField(required=False, default=True)
    baseline_method = serializers.ChoiceField(
        choices=['poly', 'als'], required=False, default='poly'
    )
    normalize        = serializers.BooleanField(required=False, default=True)
    normalize_method = serializers.ChoiceField(
        choices=['minmax', 'snv'], required=False, default='minmax'
    )
    derivative = serializers.ChoiceField(
        choices=[0, 1, 2], required=False, default=0
    )


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
