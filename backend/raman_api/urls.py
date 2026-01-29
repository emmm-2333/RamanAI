from django.urls import path, include
from .views import RegisterView, UploadView, MeView, DeviceView, ModelManageView, FeedbackView, SpectrumRecordViewSet
from .analysis_views import PCAAnalysisView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'records', SpectrumRecordViewSet, basename='record')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='auth_me'),
    path('upload/', UploadView.as_view(), name='upload_spectrum'),
    path('device/', DeviceView.as_view(), name='device_control'),
    path('models/', ModelManageView.as_view(), name='model_manage'),
    path('feedback/', FeedbackView.as_view(), name='diagnosis_feedback'),
    path('analysis/pca/', PCAAnalysisView.as_view(), name='analysis_pca'),
    path('', include(router.urls)),
]
