from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from sklearn.decomposition import PCA
from .models import SpectrumRecord
from .preprocessing import RamanPreprocessor
import numpy as np

class PCAAnalysisView(APIView):
    """
    PCA 降维分析接口
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # 1. 获取所有带有光谱数据的记录
        records = SpectrumRecord.objects.filter(is_training_data=True).select_related('patient')
        
        if not records.exists():
            return Response({'error': 'No data available for PCA'}, status=status.HTTP_404_NOT_FOUND)

        X = []
        labels = []
        ids = []
        
        for record in records:
            if not record.spectral_data or 'y' not in record.spectral_data:
                continue
                
            # Preprocess data (Important for PCA!)
            raw_y = record.spectral_data['y']
            wavenumbers = record.spectral_data.get('x', [])
            
            # Use a lighter preprocessing config for speed
            processed_y = RamanPreprocessor.process_pipeline(
                wavenumbers, 
                raw_y, 
                config={'smooth': True, 'baseline': True, 'normalize': True, 'baseline_method': 'poly'}
            )
            
            X.append(processed_y)
            labels.append(record.diagnosis_result) # Benign / Malignant
            ids.append(record.id)

        if len(X) < 2:
            return Response({'error': 'Not enough data points for PCA (need at least 2)'}, status=status.HTTP_400_BAD_REQUEST)

        X = np.array(X)
        
        # 2. Perform PCA (2 components for 2D plot)
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X)
        
        # 3. Format result
        data_points = []
        for i in range(len(X)):
            data_points.append({
                'id': ids[i],
                'x': float(X_pca[i, 0]),
                'y': float(X_pca[i, 1]),
                'category': labels[i]
            })
            
        return Response({
            'explained_variance': pca.explained_variance_ratio_.tolist(),
            'data': data_points
        })
