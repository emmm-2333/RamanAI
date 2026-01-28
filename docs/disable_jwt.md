# 临时关闭 JWT 教程（开发调试用）

本教程介绍如何在 Django + DRF 项目中临时关闭 JWT 认证，以便在前期联调时快速放行接口。完成调试后请务必恢复 JWT。

## 方法一：全局关闭认证（最快）
- 目标：所有 DRF 接口默认无需认证即可访问
- 修改文件：`backend/raman_backend/settings.py`

```python
# REST Framework 配置
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (),  # 关闭所有认证（包括 JWT）
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",  # 全局放行
    ),
}
```

- 重启后端：
```bash
cd backend
python manage.py runserver
```

- 说明：
  - 适用于「仅调试上传、列表、诊断等接口」的阶段
  - 访问需要用户对象的接口（如“当前用户信息”）时，`request.user` 将为匿名用户，可能不适配现有序列化器

## 方法二：仅放开指定接口（更安全）
- 目标：只放开需要快速联调的接口，其他接口继续要求登录
- 修改文件：`backend/raman_api/views.py`

在需要放开的视图上设置：
```python
from rest_framework import permissions

class UploadView(APIView):
    permission_classes = (permissions.AllowAny,)  # 临时放行上传接口
    ...
```

保留需要登录的视图，例如：
```python
class MeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)  # 保持登录要求
    ...
```

## 前端联调建议
- 上传接口目前会带上 `Authorization: Bearer <token>` 头（见 [Dashboard.vue](file:///d:/studio/RamanAI/frontend/src/views/Dashboard.vue#L154-L166)）。在后端全局关闭认证时，即使携带该头也不会影响访问；无需改前端。
- 若将“当前用户信息”接口（`/me`）也放开权限，需要同时修改其返回逻辑以兼容匿名用户，否则可能序列化失败。

## 恢复 JWT（上线前务必恢复）
- 恢复 `settings.py`：
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # 可按需恢复或移除全局权限设置
}
```
- 恢复各视图的 `permission_classes` 为 `IsAuthenticated`：
```python
from rest_framework import permissions
permission_classes = (permissions.IsAuthenticated,)
```
- 重启后端并验证登录流程（登录—获取 token—携带 Bearer 访问接口）

## 验证示例
- 无认证上传（方法一或方法二生效时）：
```bash
curl -X POST http://127.0.0.1:8000/api/v1/upload/ \
  -F "file=@example.csv" \
  -F "patient_id=1"
```
- 恢复 JWT 后上传：
```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -X POST http://127.0.0.1:8000/api/v1/upload/ \
  -F "file=@example.csv" \
  -F "patient_id=1"
```

## 相关文件参考
- 后端配置：[settings.py](file:///d:/studio/RamanAI/backend/raman_backend/settings.py#L144-L159)
- 上传视图：[views.py](file:///d:/studio/RamanAI/backend/raman_api/views.py#L31-L79)
