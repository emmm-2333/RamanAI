from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from .serializers import UserSerializer, SpectrumRecordSerializer, ModelVersionSerializer, DiagnosisFeedbackSerializer
from .models import SpectrumRecord, Patient, ModelVersion, DiagnosisFeedback
from .ml_engine import MLEngine
from .preprocessing import RamanPreprocessor
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

class SpectrumRecordViewSet(viewsets.ModelViewSet):
    """
    光谱记录管理接口：
    - GET /records/ : 获取记录列表 (支持分页, search=name/id, diagnosis=Malignant)
    - GET /records/{id}/ : 获取记录详情
    - POST /upload/ : 上传记录 (保留 UploadView 逻辑，或迁移至此)
    """
    queryset = SpectrumRecord.objects.all().order_by('-created_at')
    serializer_class = SpectrumRecordSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        diagnosis = self.request.query_params.get('diagnosis')
        
        if search:
            qs = qs.filter(patient__name__icontains=search) | qs.filter(patient__id__icontains=search)
        if diagnosis:
            qs = qs.filter(diagnosis_result=diagnosis)
            
        return qs

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
             return Response({'error': 'No ids provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only admin should be able to delete? Or authenticated users can delete their own?
        # For MVP, allow authenticated users to delete any
        deleted_count, _ = SpectrumRecord.objects.filter(id__in=ids).delete()
        return Response({'status': 'success', 'deleted_count': deleted_count})

    @action(detail=False, methods=['post'])
    def batch_add_to_training(self, request):
        ids = request.data.get('ids', [])
        if not ids:
             return Response({'error': 'No ids provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = SpectrumRecord.objects.filter(id__in=ids).update(is_training_data=True)
        return Response({'status': 'success', 'updated_count': updated_count})

    @action(detail=True, methods=['post'])
    def preprocess(self, request, pk=None):
        """
        对单条记录进行预处理并返回处理后的数据
        """
        record = self.get_object()
        if not record.spectral_data or 'y' not in record.spectral_data:
            return Response({'error': 'No spectral data found'}, status=status.HTTP_400_BAD_REQUEST)
            
        config = request.data.get('config', {})
        # Default config if not provided
        # config example: {'smooth': True, 'baseline': True, 'normalize': True, 'baseline_method': 'poly', 'derivative': 0}
        
        wavenumbers = record.spectral_data.get('x', [])
        raw_y = record.spectral_data['y']
        
        try:
            processed_y = RamanPreprocessor.process_pipeline(wavenumbers, raw_y, config)
            # Ensure JSON serializable (numpy array to list)
            if hasattr(processed_y, 'tolist'):
                processed_y = processed_y.tolist()
                
            return Response({
                'x': wavenumbers,
                'y': processed_y
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

        # Check file size (limit 30MB)
        if file_obj.size > 30 * 1024 * 1024:
            return Response({"error": "File size exceeds 30MB limit"}, status=status.HTTP_400_BAD_REQUEST)

        # Parse file content
        try:
            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            elif file_obj.name.endswith('.xlsx'):
                df = pd.read_excel(file_obj, engine='openpyxl')
            else:
                # Default to tab-delimited or try auto-detection
                try:
                    df = pd.read_csv(file_obj, delimiter='\t')
                except:
                    # If parsing fails, try read_excel as fallback if extension was missing but format is excel
                    # But better to rely on extension. Let's just return error if not matched above or generic read failed.
                    return Response({"error": "Unsupported file format. Please upload .csv, .xlsx, or .txt"}, status=status.HTTP_400_BAD_REQUEST)
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
            # Some excel columns might be read as floats or strings, try to convert
            cols = []
            valid_cols_map = {} # map valid int col to original col name
            
            for c in df.columns:
                try:
                    # Convert to float then int to handle '400.0'
                    val = int(float(str(c)))
                    if val > 0: # spectral data usually positive wavenumbers
                        cols.append(val)
                        valid_cols_map[val] = c
                except:
                    continue
            
            if len(cols) > 100:
                 # Wide format (1 row = 1 sample)
                 # Sort columns by wavenumber
                 cols.sort()
                 spectral_x = cols
                 # Use the mapped original column names to fetch data
                 original_cols = [valid_cols_map[c] for c in cols]
                 # Take the first row
                 spectral_y = df.iloc[0][original_cols].fillna(0).tolist()
            else:
                 # Long format (col1=x, col2=y)
                 if df.shape[1] >= 2:
                     # Assume first column is X, second is Y
                     # Need to ensure they are numeric
                     df_clean = df.iloc[:, [0, 1]].dropna()
                     # Try to convert to numeric, coerce errors
                     df_clean[df.columns[0]] = pd.to_numeric(df_clean[df.columns[0]], errors='coerce')
                     df_clean[df.columns[1]] = pd.to_numeric(df_clean[df.columns[1]], errors='coerce')
                     df_clean = df_clean.dropna()
                     
                     spectral_x = df_clean.iloc[:, 0].tolist()
                     spectral_y = df_clean.iloc[:, 1].tolist()
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
            try:
                result = MLEngine.train_new_version(
                    description=request.data.get('description', 'Manual trigger')
                )
                return Response(result)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
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
