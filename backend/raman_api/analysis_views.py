from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from .models import SpectrumRecord
from .preprocessing import RamanPreprocessor
import numpy as np

class AnalysisMixin:
    def get_data(self):
        records = SpectrumRecord.objects.filter(is_training_data=True).select_related('patient')
        if not records.exists():
            return None, None, None, "No data available"

        X = []
        labels = []
        ids = []
        
        for record in records:
            if not record.spectral_data or 'y' not in record.spectral_data:
                continue
            
            raw_y = record.spectral_data['y']
            wavenumbers = record.spectral_data.get('x', [])
            
            processed_y = RamanPreprocessor.process_pipeline(
                wavenumbers, 
                raw_y, 
                config={'smooth': True, 'baseline': True, 'normalize': True, 'baseline_method': 'poly'}
            )
            
            X.append(processed_y)
            labels.append(record.diagnosis_result)
            ids.append(record.id)

        if len(X) < 2:
            return None, None, None, "Not enough data points (need at least 2)"

        return np.array(X), labels, ids, None

class PCAAnalysisView(APIView, AnalysisMixin):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        X, labels, ids, error = self.get_data()
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X)
        
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

class ClusteringAnalysisView(APIView, AnalysisMixin):
    """
    K-Means 聚类分析接口
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        n_clusters = int(request.data.get('n_clusters', 2))
        
        X, labels, ids, error = self.get_data()
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. Reduce dimension first for better clustering (optional but recommended for high-dim data)
        pca = PCA(n_components=5) # Keep top 5 components for clustering
        X_reduced = pca.fit_transform(X)
        
        # 2. KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(X_reduced)
        
        # 3. For visualization, we still need 2D PCA
        X_vis = X_reduced[:, :2] # First 2 components
        
        data_points = []
        for i in range(len(X)):
            data_points.append({
                'id': ids[i],
                'x': float(X_vis[i, 0]),
                'y': float(X_vis[i, 1]),
                'cluster': int(clusters[i]),
                'true_label': labels[i]
            })
            
        return Response({
            'data': data_points
        })
