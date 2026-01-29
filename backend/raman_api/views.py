from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from .serializers import UserSerializer, SpectrumRecordSerializer, SpectrumRecordDetailSerializer, ModelVersionSerializer, DiagnosisFeedbackSerializer
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
    # Default serializer
    serializer_class = SpectrumRecordSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        # Use DetailSerializer for retrieve/update/create to show full data
        # Use simplified Serializer for list to avoid loading huge JSON
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return SpectrumRecordDetailSerializer
        return SpectrumRecordSerializer

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

from django.db import transaction

# ... (imports)

from django.db import transaction

# ... (imports)

class BatchImportView(APIView):
    """
    批量导入数据集接口。
    支持 .zip (包含多个光谱文件) 或 .xlsx (宽表格式)。
    """
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        import zipfile
        import io

        success_count = 0
        errors = []

        try:
            if file_obj.name.endswith('.zip'):
                try:
                    with zipfile.ZipFile(file_obj) as z:
                        for filename in z.namelist():
                            if filename.endswith('.txt') or filename.endswith('.csv'):
                                sample_id = filename.split('/')[-1].split('.')[0]
                                with z.open(filename) as f:
                                    try:
                                        df = pd.read_csv(f, sep=None, engine='python')
                                        if df.shape[1] < 2:
                                            errors.append(f"{filename}: Not enough columns")
                                            continue
                                        df = df.apply(pd.to_numeric, errors='coerce').dropna()
                                        x = df.iloc[:, 0].tolist()
                                        y = df.iloc[:, 1].tolist()
                                        
                                        patient, _ = Patient.objects.get_or_create(name=sample_id, defaults={'age': 0, 'gender': 'F'})
                                        diagnosis, confidence = MLEngine.predict(x, y)
                                        
                                        SpectrumRecord.objects.create(
                                            patient=patient,
                                            file_path=filename,
                                            diagnosis_result=diagnosis,
                                            confidence_score=confidence,
                                            uploaded_by=request.user,
                                            spectral_data={'x': x, 'y': y},
                                            is_training_data=True
                                        )
                                        success_count += 1
                                    except Exception as e:
                                        errors.append(f"{filename}: {str(e)}")
                except Exception as e:
                    return Response({"error": f"Zip processing failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            elif file_obj.name.endswith('.xlsx'):
                    try:
                        df = pd.read_excel(file_obj)
                        header = list(df.columns)
                        
                        # 1. Identify Spectral Columns (400-2200) vs Metadata Columns
                        spectral_cols_map = {} # wavenumber_float -> col_name
                        metadata_cols = []
                        
                        for col in header:
                            is_spectral = False
                            try:
                                val = float(str(col))
                                if 400 <= val <= 2200:
                                    spectral_cols_map[val] = col
                                    is_spectral = True
                            except:
                                pass
                            
                            if not is_spectral:
                                metadata_cols.append(col)
                        
                        wavenumbers = sorted(spectral_cols_map.keys())
                        sorted_spectral_cols = [spectral_cols_map[w] for w in wavenumbers]
                        
                        if len(wavenumbers) < 10:
                             return Response({"error": "No valid spectral data found (columns 400-2200)"}, status=status.HTTP_400_BAD_REQUEST)

                        print(f"Found {len(wavenumbers)} spectral points and {len(metadata_cols)} metadata columns.")
                        print(f"Start processing {len(df)} rows...")
                        
                        records_to_create = []
                        
                        for idx, row in df.iterrows():
                            try:
                                # Extract Spectral Data
                                y_series = row[sorted_spectral_cols].infer_objects().fillna(0)
                                y = y_series.tolist()
                                
                                # Extract Metadata
                                metadata = {}
                                for meta_col in metadata_cols:
                                    val = row[meta_col]
                                    if pd.notna(val):
                                        metadata[str(meta_col)] = val
                                
                                # Determine Patient Info
                                # Priority: '姓名' -> '病历号' -> 'Label' -> Generated
                                patient_name = None
                                if '姓名' in metadata:
                                    patient_name = str(metadata['姓名'])
                                elif '病历号' in metadata:
                                    patient_name = str(metadata['病历号'])
                                elif 'Label' in metadata:
                                    patient_name = str(metadata['Label'])
                                else:
                                    patient_name = f"Batch_{file_obj.name}_{idx}"
                                
                                patient_age = 0
                                if '年龄' in metadata:
                                    try:
                                        patient_age = int(metadata['年龄'])
                                    except:
                                        pass

                                # Determine Diagnosis
                                # Logic: '良恶性' column: 0/良性 -> Benign, 1/恶性 -> Malignant
                                diagnosis = None
                                diagnosis_col_val = None
                                
                                if '良恶性' in metadata:
                                    diagnosis_col_val = str(metadata['良恶性'])
                                elif 'Label' in metadata: # Sometimes Label implies diagnosis
                                    diagnosis_col_val = str(metadata['Label'])
                                
                                if diagnosis_col_val:
                                    val_str = diagnosis_col_val
                                    if '0' in val_str or '良' in val_str or 'Benign' in val_str:
                                        diagnosis = 'Benign'
                                    elif '1' in val_str or '恶' in val_str or 'Malignant' in val_str:
                                        diagnosis = 'Malignant'
                                
                                # If diagnosis not found in metadata, predict it
                                confidence = 0.0
                                if not diagnosis:
                                    diagnosis, confidence = MLEngine.predict(wavenumbers, y)
                                else:
                                    # If provided, set high confidence? Or re-verify? 
                                    # Let's set confidence to 1.0 if manually provided, or still run predict to compare?
                                    # For now, trust the label.
                                    confidence = 1.0 

                                # Create/Get Patient
                                patient, _ = Patient.objects.get_or_create(
                                    name=patient_name, 
                                    defaults={'age': patient_age, 'gender': 'F'} # Gender unknown
                                )
                                
                                records_to_create.append(SpectrumRecord(
                                    patient=patient,
                                    file_path=f"{file_obj.name}_row{idx}",
                                    diagnosis_result=diagnosis,
                                    confidence_score=confidence,
                                    uploaded_by=request.user,
                                    spectral_data={'x': wavenumbers, 'y': y},
                                    metadata=metadata,
                                    is_training_data=True
                                ))
                                
                                success_count += 1
                                if idx % 100 == 0:
                                    print(f"Processed {idx} rows...")
                                    
                            except Exception as e:
                                errors.append(f"Row {idx}: {str(e)}")
                                
                        print("Bulk inserting records...")
                        SpectrumRecord.objects.bulk_create(records_to_create, batch_size=100)
                        print("Bulk insert finished.")

                    except Exception as e:
                        return Response({"error": f"Excel processing failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             return Response({"error": f"Transaction failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'success', 
            'imported': success_count, 
            'errors': errors[:10]
        })

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
