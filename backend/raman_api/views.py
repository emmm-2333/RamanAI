from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from .serializers import UserSerializer, SpectrumRecordSerializer, ModelVersionSerializer, DiagnosisFeedbackSerializer
from .models import SpectrumRecord, Patient, ModelVersion, DiagnosisFeedback
from .ml_engine import MLEngine
from .device_driver import MockSpectrometer
import pandas as pd
import random

# Initialize ML Engine
MLEngine.load_active_model()

class RegisterView(generics.CreateAPIView):
    """
    用户注册接口。
    无需认证即可访问。
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

class MeView(APIView):
    """
    获取当前登录用户信息的接口。
    需要 JWT 认证。
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class UploadView(APIView):
    """
    光谱文件上传与诊断接口。
    接收 .txt/.csv 文件，返回诊断结果。
    """
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # Parse file content
        try:
            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            else:
                df = pd.read_csv(file_obj, delimiter='\t')
        except Exception as e:
            return Response({"error": f"Failed to read file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Assume file format: columns are wavenumbers, first row is intensities
        # Or standard Raman format: col1=Wavenumber, col2=Intensity
        # For simplicity, let's assume the uploaded file is a standard 2-column format
        # or similar to the training data structure.
        # Fallback: if it matches training data columns (400-2200), use that.
        
        spectral_x = []
        spectral_y = []

        try:
            # Check if columns are integers (like training data)
            cols = [c for c in df.columns if str(c).isdigit()]
            if len(cols) > 100:
                 # Wide format (1 row = 1 sample)
                 cols.sort(key=int)
                 spectral_x = [int(c) for c in cols]
                 spectral_y = df.iloc[0][cols].tolist()
            else:
                 # Long format (col1=x, col2=y)
                 if df.shape[1] >= 2:
                     spectral_x = df.iloc[:, 0].tolist()
                     spectral_y = df.iloc[:, 1].tolist()
                 else:
                     raise ValueError("Unknown file format")
        except Exception as e:
             return Response({"error": f"Data parsing error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Inference using MLEngine
        diagnosis, confidence = MLEngine.predict(spectral_x, spectral_y)

        # Create Patient
        patient_id = request.data.get('patient_id')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                 # Try finding by name/id logic if needed, or just create new
                 patient = Patient.objects.create(name=f"Patient-{patient_id}", age=0, gender='F')
        else:
            patient = Patient.objects.create(name="Anonymous", age=50, gender='F')

        # Save Record
        spectral_data = {'x': spectral_x, 'y': spectral_y}
        
        record = SpectrumRecord.objects.create(
            patient=patient,
            file_path=file_obj.name,
            diagnosis_result=diagnosis,
            confidence_score=confidence,
            uploaded_by=request.user,
            spectral_data=spectral_data
        )

        serializer = SpectrumRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class DeviceView(APIView):
    """
    光谱仪设备接口
    """
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        action = request.data.get('action')
        
        if action == 'capture':
            try:
                # Use Mock Driver for now
                driver = MockSpectrometer()
                driver.open_device()
                wavelengths, intensities = driver.capture_spectrum()
                driver.close_device()
                
                return Response({
                    'status': 'success',
                    'data': {
                        'x': wavelengths,
                        'y': intensities
                    }
                })
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

class ModelManageView(generics.ListCreateAPIView):
    """
    模型版本管理接口
    """
    queryset = ModelVersion.objects.all().order_by('-created_at')
    serializer_class = ModelVersionSerializer
    permission_classes = (permissions.IsAuthenticated,) # Should be Admin only

    def post(self, request, *args, **kwargs):
        # Custom logic to trigger training
        action = request.data.get('action')
        if action == 'train':
            # Trigger async task (celery recommended, but sync for now)
            # MLEngine.train_new_version(...)
            return Response({'status': 'Training started (simulated)'})
        return super().post(request, *args, **kwargs)

class FeedbackView(generics.CreateAPIView):
    """
    诊断反馈接口
    """
    queryset = DiagnosisFeedback.objects.all()
    serializer_class = DiagnosisFeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user)
