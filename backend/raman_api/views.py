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
            from django.db.models import Q
            qs = qs.filter(
                Q(patient__name__icontains=search) | 
                Q(patient__id__icontains=search) |
                Q(file_path__icontains=search)
            )
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
                # Fix for headerless single-row files:
                # If read as header-only (empty df) but has columns, treat as data row
                if df.empty and len(df.columns) > 1:
                    file_obj.seek(0)
                    df = pd.read_csv(file_obj, header=None)
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
            
            # --- New Logic for 1801 Spectral Points ---
            # Assume first 1801 columns are spectral data (400-2200)
            # Subsequent columns are metadata
            
            # Auto-generate standard wavenumbers for the first 1801 points
            standard_wavenumbers = list(range(400, 2201)) # 400 to 2200 inclusive = 1801 points
            
            if len(df.columns) >= 1801:
                # Wide format (1 row = 1 sample)
                # Map first 1801 columns to standard wavenumbers
                spectral_x = standard_wavenumbers
                
                # Take the first row's first 1801 columns as Y data
                # Ensure numeric
                row_series = df.iloc[0, :1801]
                spectral_y = pd.to_numeric(row_series, errors='coerce').fillna(0).tolist()
                
                # Process Metadata (columns after 1801)
                metadata = {}
                if len(df.columns) > 1801:
                    meta_cols = df.columns[1801:]
                    for idx, col_name in enumerate(meta_cols):
                        val = df.iloc[0, 1801 + idx]
                        # Store as string in metadata
                        if pd.notna(val):
                            metadata[str(col_name)] = str(val)
                            
                # Pass metadata to save logic (will need to update save block below)
                
            else:
                # Fallback to old logic or Long format if columns < 1801
                # (Keep existing logic for 2-column format)
                if df.shape[1] >= 2 and df.shape[1] < 100:
                     # Long format (col1=x, col2=y)
                     # Assume first column is X, second is Y
                     # Need to ensure they are numeric
                     df_clean = df.iloc[:, [0, 1]].dropna()
                     # Try to convert to numeric, coerce errors
                     df_clean[df.columns[0]] = pd.to_numeric(df_clean[df.columns[0]], errors='coerce')
                     df_clean[df.columns[1]] = pd.to_numeric(df_clean[df.columns[1]], errors='coerce')
                     df_clean = df_clean.dropna()
                     
                     spectral_x = df_clean.iloc[:, 0].tolist()
                     spectral_y = df_clean.iloc[:, 1].tolist()
                     metadata = {}
                else:
                     raise ValueError(f"Unknown file format. Expected 1801+ columns or 2 columns. Got {len(df.columns)}")
                     
        except Exception as e:
             return Response({"error": f"Data parsing error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Inference and Save
        try:
            # Inference using MLEngine
            diagnosis, confidence, predictions = MLEngine.predict(spectral_x, spectral_y)
            
            # Save predictions to metadata
            if 'metadata' not in locals():
                metadata = {}
            if predictions:
                metadata['predicted_markers'] = predictions

            # Create Patient
            patient_id = request.data.get('patient_id')
            if patient_id:
                try:
                    patient = Patient.objects.get(id=patient_id)
                except Patient.DoesNotExist:
                    # Try finding by name/id logic if needed, or just create new
                    patient = Patient.objects.create(name=f"Patient-{patient_id}", age=0, gender='F')
            else:
                # Try to get patient info from metadata if available
                if 'metadata' in locals() and metadata:
                     # Try to find common name fields
                     p_name = metadata.get('姓名') or metadata.get('Name') or metadata.get('PatientID') or "Anonymous"
                     # Use filter().first() to avoid MultipleObjectsReturned
                     patient = Patient.objects.filter(name=p_name).first()
                     if not patient:
                         patient = Patient.objects.create(name=p_name, age=50, gender='F')
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
                spectral_data=spectral_data,
                metadata=metadata if 'metadata' in locals() else {}
            )

            serializer = SpectrumRecordDetailSerializer(record)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": f"Processing error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                                        diagnosis, confidence, predictions = MLEngine.predict(x, y)
                                        
                                        # Metadata with predictions
                                        meta = {'predicted_markers': predictions} if predictions else {}

                                        SpectrumRecord.objects.create(
                                            patient=patient,
                                            file_path=filename,
                                            diagnosis_result=diagnosis,
                                            confidence_score=confidence,
                                            uploaded_by=request.user,
                                            spectral_data={'x': x, 'y': y},
                                            metadata=meta,
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
                                elif '良恶性0：良性1.恶性' in metadata:
                                    diagnosis_col_val = str(metadata['良恶性0：良性1.恶性'])
                                elif 'Label' in metadata: # Sometimes Label implies diagnosis
                                    diagnosis_col_val = str(metadata['Label'])
                                
                                if diagnosis_col_val is not None:
                                    val_str = diagnosis_col_val.strip()
                                    # Strict Check: 0 or 1
                                    if val_str == '0' or val_str == '0.0' or '良' in val_str or 'Benign' in val_str:
                                        diagnosis = 'Benign'
                                    elif val_str == '1' or val_str == '1.0' or '恶' in val_str or 'Malignant' in val_str:
                                        diagnosis = 'Malignant'
                                
                                # If diagnosis not found in metadata, predict it
                                confidence = 0.0
                                if not diagnosis:
                                    # Fallback: only predict if no label is present
                                    # diagnosis, confidence = MLEngine.predict(wavenumbers, y)
                                    # As requested: do NOT predict during import if label is missing/ambiguous
                                    diagnosis = 'Unknown'
                                    confidence = 0.0
                                else:
                                    # If provided, set confidence to 1.0
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
