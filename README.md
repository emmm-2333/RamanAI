# RamanAI 医疗平台 - 项目使用简明教程

本项目是一个基于深度学习的乳腺癌拉曼光谱智能诊断系统，采用前后端分离架构。

## 1. 环境准备 (Prerequisites)

在开始之前，请确保您的系统已安装以下软件：

*   **Anaconda / Miniconda**: 用于管理 Python 环境。
*   **Node.js (v18+)**: 用于运行前端项目。
*   **MySQL (8.0+)**: 数据库服务。

## 2. 后端部署 (Backend)

后端采用 **Django** + **Django REST Framework**。

### 步骤 1: 创建并激活虚拟环境

在项目根目录下打开终端（PowerShell 或 CMD）：

```bash
# 1. 进入后端目录
cd backend

# 2. 创建 Conda 环境 (仅首次需要)
conda env create -f environment.yml

# 3. 激活环境
conda activate raman_ai_backend
```

### 步骤 2: 数据库配置与初始化

1.  确保本地 MySQL 服务已启动。
2.  默认数据库配置（如需修改，请编辑 `backend/raman_backend/settings.py`）：
    *   **数据库名**: `raman_db`
    *   **用户**: `root`
    *   **密码**: `7355608` (请根据实际情况修改)
    *   **端口**: `3306`
3.  执行数据库迁移：

```bash
# 确保在 backend 目录下且环境已激活
python manage.py migrate
```

### 步骤 3: 启动后端服务

```bash
python manage.py runserver
```

*   后端 API 地址: `http://127.0.0.1:8000`

---

## 3. 前端部署 (Frontend)

前端采用 **Vue 3** + **Vite** + **Tailwind CSS 4.0** + **Element Plus**。

### 步骤 1: 安装依赖

打开一个新的终端窗口：

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖 (仅首次或 package.json 变动时需要)
npm install
```

### 步骤 2: 启动前端服务

```bash
npm run dev
```

*   访问地址: `http://localhost:5173` (如果端口被占用，可能会自动分配到 5174 等)

---

## 4. 快速使用指南

1.  **打开浏览器**: 访问前端地址（通常是 `http://localhost:5173`）。
2.  **注册账号**: 点击登录页面的 "注册账号"，输入用户名、邮箱和密码创建医生账户。
3.  **登录**: 使用注册的账号登录系统。
4.  **仪表盘功能**:
    *   **主题切换**: 点击右上角的月亮/太阳图标切换 深色/浅色 模式。
    *   **数据录入**: 在左侧面板输入 "患者ID"，并拖拽上传光谱数据文件（支持 .txt/.csv）。
    *   **智能诊断**: 上传后系统会自动调用模型进行分析，并在左侧显示 "良性/恶性" 诊断结果及置信度。
    *   **可视化**: 中间区域会展示拉曼光谱数据的波形图。

## 5. 常见问题

*   **样式丢失/混乱**: 确保前端已正确安装依赖并重启服务（Tailwind CSS 需要编译）。
*   **数据库连接失败**: 请检查 `settings.py` 中的数据库密码是否与本地 MySQL 匹配。
*   **登录报错 401**: 检查后端服务是否正常运行。
