"""
Django settings for raman_backend project.
拉曼光谱诊断系统后端配置文件

由 'django-admin startproject' 使用 Django 6.0.1 生成。

关于此文件的更多信息，请参阅：
https://docs.djangoproject.com/en/6.0/topics/settings/

所有配置项及其值的完整列表，请参阅：
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

from pathlib import Path
from datetime import timedelta
import environ
import os

# 初始化环境变量管理器
env = environ.Env()
# 读取 .env 配置文件（若不存在则忽略）
env_file = os.path.join(Path(__file__).resolve().parent.parent, '.env')
if os.path.exists(env_file):
    environ.Env.read_env(env_file)

# 构建项目内部路径，例如：BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent


# 快速开发配置 - 不适用于生产环境
# 参阅部署检查清单：https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# 安全警告：请在生产环境中保密 SECRET_KEY！
SECRET_KEY = env('SECRET_KEY', default='django-insecure-$dlq@i-vt23j2n$q*k=mam)g2ad$kc20ji+v1bx9lo*a+1lo#+')

# 安全警告：不要在生产环境中开启 DEBUG 模式！
DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = []


# 应用定义

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 第三方应用
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # 本地应用
    "raman_api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS 跨域中间件
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "raman_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "raman_backend.wsgi.application"


# 数据库配置
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'raman_db',
        'USER': 'root',
        'PASSWORD': '7355608',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}


# 密码验证
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# 国际化配置
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# 静态文件配置 (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"

# 默认主键字段类型
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework 配置
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# JWT 配置
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS 跨域配置
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite 默认端口
    "http://127.0.0.1:5173",
    "http://localhost:5174",  # Vite 备用端口
    "http://127.0.0.1:5174",
]
