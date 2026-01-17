from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from .serializers import UserSerializer, SpectrumRecordSerializer
from .models import SpectrumRecord, Patient
import os
import random

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

        # 1. 简单的文件保存逻辑 (实际应保存到 MEDIA_ROOT)
        # 这里为了演示，暂时不真正保存到磁盘，而是直接读取内容模拟处理
        # 实际项目中应使用 default_storage.save()
        
        # 2. 模拟数据处理和推理
        # TODO: 集成 PyTorch 模型进行真实推理
        # 模拟结果：
        is_malignant = random.choice([True, False])
        diagnosis = "Malignant" if is_malignant else "Benign"
        confidence = round(random.uniform(0.7, 0.99), 4)

        # 3. 创建关联的 Patient (如果不存在则创建，这里简化为每次创建新病人或查找特定ID)
        # 实际逻辑应从请求中获取 patient_id 或 patient info
        # 这里为了简化流程，如果未提供 patient_id，则创建一个匿名/临时病人
        patient_id = request.data.get('patient_id')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                 return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # 创建一个演示用病人
            patient = Patient.objects.create(name="Anonymous", age=50, gender='F')

        # 4. 保存记录
        record = SpectrumRecord.objects.create(
            patient=patient,
            file_path=file_obj.name, # 仅保存文件名作为演示
            processed_path=f"processed_{file_obj.name}.json",
            diagnosis_result=diagnosis,
            confidence_score=confidence,
            uploaded_by=request.user
        )

        serializer = SpectrumRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
