# 乳腺癌拉曼光谱智能诊断系统 - 项目进度报告

**项目名称**：RamanAI - 拉曼光谱智能诊断系统  
**报告日期**：2026年1月17日  
**项目版本**：v0.1.0 (Alpha)  
**项目状态**：进行中 (In Progress)

---

## 📋 目录

1. [已完成工作](#1-已完成工作-completed-work)
2. [待完成工作](#2-待完成工作-pending-work)
3. [项目状态总结](#3-项目状态总结-project-summary)
4. [技术架构概览](#4-技术架构概览-technical-architecture)

---

## 1. 已完成工作 (Completed Work)

本阶段主要完成了系统核心框架的搭建，实现了基础的前后端连通、用户认证体系及数据模型设计。项目已建立完整的开发环境，并实现了核心业务流程的原型。

### 1.1 后端开发 (Backend Development)

#### 1.1.1 项目架构与环境配置

**完成日期**：2026-01-15  
**版本**：Django 6.0 + Django REST Framework 3.x

| 模块          | 功能点            | 实现细节                                                                                                                                         | 相关代码路径                                          |
| :------------ | :---------------- | :----------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------- |
| **项目框架**  | Django + DRF      | 初始化 Django 6.0 项目，集成 Django REST Framework 用于 RESTful API 开发                                                                         | `backend/raman_backend/settings.py`                   |
| **依赖管理**  | Requirements 配置 | 完成核心依赖配置：django>=4.2, djangorestframework, djangorestframework-simplejwt, django-cors-headers, mysqlclient, pandas, numpy, scipy, torch | `backend/requirements.txt`, `backend/environment.yml` |
| **环境隔离**  | Conda 环境        | 创建独立 Python 3.11 环境，使用 conda + pip 混合管理依赖                                                                                         | `backend/environment.yml`                             |
| **CORS 配置** | 跨域支持          | 集成 `django-cors-headers` 中间件，支持前后端分离开发                                                                                            | `backend/raman_backend/settings.py` (MIDDLEWARE)      |

**技术说明**：

- 使用 `django-environ` 管理环境变量，支持 `.env` 文件配置
- 配置了 REST Framework 的全局认证类为 `JWTAuthentication`
- 设置 `ALLOWED_HOSTS` 和 `DEBUG` 模式用于开发环境

#### 1.1.2 数据库设计与配置

**完成日期**：2026-01-16  
**数据库**：MySQL 9.4

| 模块           | 功能点         | 实现细节                                                                                                                          | 相关代码路径                                    |
| :------------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------- |
| **数据库驱动** | PyMySQL 适配   | 解决 MySQL 9.x 与 `mysqlclient` 的 `caching_sha2_password` 认证兼容性问题，改用纯 Python 实现的 `pymysql` 驱动并进行 Monkey Patch | `backend/raman_backend/__init__.py`             |
| **数据库连接** | MySQL 配置     | 使用环境变量配置数据库连接参数 (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)                                                  | `backend/raman_backend/settings.py` (DATABASES) |
| **数据迁移**   | Migration 管理 | 完成初始数据库迁移 `0001_initial.py`，建立核心业务表                                                                              | `backend/raman_api/migrations/0001_initial.py`  |

**数据模型设计**：

##### UserProfile 模型

- **目的**：扩展 Django 内置 User 模型，存储用户角色信息
- **字段**：
  - `user`: OneToOneField (关联 Django User)
  - `role`: CharField (admin/doctor，默认 doctor)
- **代码路径**：`backend/raman_api/models.py` (Line 7-18)

##### Patient 模型

- **目的**：存储病患基本信息
- **字段**：
  - `name`: CharField (加密后的病患姓名，待实现加密)
  - `age`: IntegerField (年龄)
  - `gender`: CharField (M/F 性别)
  - `created_at`: DateTimeField (自动记录创建时间)
- **代码路径**：`backend/raman_api/models.py` (Line 20-30)
- **安全性注意**：当前姓名字段为明文存储，生产环境需实现字段级加密

##### SpectrumRecord 模型

- **目的**：存储拉曼光谱记录及诊断结果
- **字段**：
  - `patient`: ForeignKey (关联 Patient)
  - `file_path`: CharField (原始光谱文件路径，最长 500 字符)
  - `processed_path`: CharField (预处理后数据路径，可空)
  - `diagnosis_result`: CharField (诊断结果：Benign/Malignant，可空)
  - `confidence_score`: FloatField (置信度 0.0-1.0，可空)
  - `created_at`: DateTimeField (自动记录上传时间)
  - `is_reviewed`: BooleanField (是否经医生复核，默认 False)
  - `uploaded_by`: ForeignKey (关联上传医生 User)
- **代码路径**：`backend/raman_api/models.py` (Line 32-51)

#### 1.1.3 认证与授权系统

**完成日期**：2026-01-16  
**认证方案**：JWT (JSON Web Token) using SimpleJWT

| 模块           | 功能点              | 实现细节                                                                                          | 相关代码路径                                                    |
| :------------- | :------------------ | :------------------------------------------------------------------------------------------------ | :-------------------------------------------------------------- |
| **JWT 集成**   | SimpleJWT           | 集成 `djangorestframework-simplejwt`，实现无状态认证                                              | `backend/requirements.txt`, `backend/raman_backend/settings.py` |
| **用户注册**   | RegisterView (POST) | 实现用户注册接口 `/api/v1/auth/register/`，支持用户名、密码、邮箱注册，自动创建关联的 UserProfile | `backend/raman_api/views.py` (Line 9-17)                        |
| **用户登录**   | TokenObtainPairView | 使用 SimpleJWT 提供的登录接口 `/api/v1/auth/login/`，返回 access 和 refresh token                 | `backend/raman_api/urls.py` (Line 9)                            |
| **Token 刷新** | TokenRefreshView    | 提供 Token 刷新接口 `/api/v1/auth/refresh/`                                                       | `backend/raman_api/urls.py` (Line 10)                           |
| **用户信息**   | MeView (GET)        | 实现获取当前用户信息接口 `/api/v1/auth/me/`，需要 JWT 认证                                        | `backend/raman_api/views.py` (Line 19-28)                       |
| **序列化器**   | UserSerializer      | 实现用户数据序列化，支持密码写入保护 (write_only)，自动创建 UserProfile                           | `backend/raman_api/serializers.py` (Line 6-27)                  |

**JWT 配置详情**：

- Access Token 有效期：默认 5 分钟（可在 settings.py 配置）
- Refresh Token 有效期：默认 1 天
- 算法：HS256
- 认证头格式：`Authorization: Bearer <token>`

**错误处理优化**：

- 注册时如用户名已存在，返回详细错误信息
- 登录失败返回明确的错误提示
- 前端已适配后端返回的 JSON 错误结构

#### 1.1.4 业务接口实现

**完成日期**：2026-01-17  
**接口类型**：文件上传与诊断

| 模块         | 功能点                   | 实现细节                                                                                | 相关代码路径                                    |
| :----------- | :----------------------- | :-------------------------------------------------------------------------------------- | :---------------------------------------------- |
| **文件上传** | UploadView (POST)        | 实现光谱文件上传接口 `/api/v1/upload/`，支持 multipart/form-data 格式                   | `backend/raman_api/views.py` (Line 30-76)       |
| **诊断模拟** | Mock 诊断逻辑            | 当前使用随机数模拟诊断结果 (Benign/Malignant) 和置信度 (0.7-0.99)，**待替换为真实模型** | `backend/raman_api/views.py` (Line 49-53)       |
| **病患关联** | Patient 自动创建         | 支持通过 `patient_id` 参数关联已有病患，未提供时自动创建匿名病患                        | `backend/raman_api/views.py` (Line 55-65)       |
| **记录存储** | SpectrumRecord 创建      | 将上传文件信息和诊断结果存入数据库，关联上传医生                                        | `backend/raman_api/views.py` (Line 67-74)       |
| **序列化器** | SpectrumRecordSerializer | 实现光谱记录序列化，包含关联的病患姓名和上传医生用户名                                  | `backend/raman_api/serializers.py` (Line 33-43) |

**当前限制**：

- 文件仅存储文件名，未真正保存到磁盘 (需配置 `MEDIA_ROOT` 和 `FileField`)
- 未实现文件格式验证 (.txt/.csv)
- 未实现文件大小限制
- 诊断逻辑为模拟数据，**TODO: 集成 PyTorch 模型** (Line 49)

### 1.2 前端开发 (Frontend Development)

#### 1.2.1 项目架构与构建工具

**完成日期**：2026-01-15  
**版本**：Vue 3.5.24 + Vite 7.2.4

| 模块            | 功能点            | 实现细节                                                                       | 相关代码路径                                                |
| :-------------- | :---------------- | :----------------------------------------------------------------------------- | :---------------------------------------------------------- |
| **项目框架**    | Vue 3 SPA         | 使用 Vue 3 Composition API 构建单页应用                                        | `frontend/src/main.js`                                      |
| **构建工具**    | Vite 7.x          | 使用 Vite 作为开发服务器和构建工具，支持热更新 (HMR)                           | `frontend/vite.config.js`                                   |
| **UI 组件库**   | Element Plus 2.13 | 集成 Element Plus 提供完整的 UI 组件支持，包括图标库 `@element-plus/icons-vue` | `frontend/package.json`, `frontend/src/main.js`             |
| **CSS 框架**    | Tailwind CSS 4.1  | 集成 Tailwind CSS 4.x 进行原子化 CSS 开发，配置了医疗主题色系和暗色模式        | `frontend/tailwind.config.js`, `frontend/postcss.config.js` |
| **路由管理**    | Vue Router 4.6    | 实现基于 History 模式的前端路由，支持路由守卫                                  | `frontend/src/router/index.js`                              |
| **状态管理**    | Pinia 3.0         | 使用 Pinia 作为 Vue 3 官方推荐的状态管理库                                     | `frontend/src/stores/auth.js`                               |
| **HTTP 客户端** | Axios 1.13        | 集成 Axios 用于 API 请求，支持拦截器和自动添加认证头                           | `frontend/package.json`                                     |

**项目结构**：

```
frontend/src/
├── assets/          # 静态资源
├── components/      # 公共组件
│   ├── HelloWorld.vue
│   └── ThemeToggle.vue
├── views/           # 页面组件
│   ├── Dashboard.vue
│   ├── Login.vue
│   └── Register.vue
├── router/          # 路由配置
│   └── index.js
├── stores/          # 状态管理
│   └── auth.js
├── App.vue          # 根组件
├── main.js          # 应用入口
└── style.css        # 全局样式
```

#### 1.2.2 用户认证模块

**完成日期**：2026-01-16  
**功能**：完整的用户注册、登录、注销流程

##### 登录页面 (Login.vue)

- **路由**：`/login`
- **功能**：
  - 用户名和密码输入表单
  - 表单验证（非空检查）
  - 登录状态加载指示器
  - 错误信息友好提示
  - 导航到注册页面链接
  - 医疗主题 UI 设计（蓝色主题，圆角卡片）
- **技术实现**：
  - 使用 Element Plus 的 `el-input`, `el-button` 组件
  - 集成 Element Icons (`User`, `Lock`, `FirstAidKit`)
  - 使用 Tailwind CSS 实现渐变背景和响应式布局
  - 暗色模式支持 (dark:bg-gray-800)
  - 医疗主题色系 (border-t-4 border-medical-primary)
  - 调用 `authStore.login()` 方法
  - 成功后跳转到 Dashboard (`/`)
- **代码路径**：`frontend/src/views/Login.vue`

##### 注册页面 (Register.vue)

- **路由**：`/register`
- **功能**：
  - 用户名、邮箱、密码、确认密码输入
  - 表单验证（非空检查、密码一致性）
  - 错误信息精准回显（字段级错误展示）
  - 注册成功后跳转到登录页
  - 医疗主题 UI 设计，与登录页一致的视觉风格
- **技术实现**：
  - 使用 `reactive` 管理表单状态
  - 使用 Tailwind CSS 实现渐变背景 (from-gray-50 to-gray-200)
  - 支持暗色模式切换 (dark:from-gray-900 dark:to-gray-800)
  - 圆角卡片设计 (rounded-xl shadow-lg)
  - 优化错误处理逻辑，显示后端返回的详细错误（如 `error.username[0]`）
  - 调用 `authStore.register()` 方法
- **代码路径**：`frontend/src/views/Register.vue`
- **错误处理优化**：实现字段级错误回显

##### 路由守卫

- **功能**：保护需要认证的路由（如 Dashboard）
- **实现**：
  - 在 `router.beforeEach` 中检查路由的 `meta.requiresAuth` 标志
  - 未认证用户自动重定向到 `/login`
- **代码路径**：`frontend/src/router/index.js` (Line 30-39)

#### 1.2.3 状态管理 (Pinia Store)

**完成日期**：2026-01-16  
**Store**：authStore

##### 状态 (State)

- `accessToken`: 存储 JWT access token，初始化时从 localStorage 读取
- `refreshToken`: 存储 JWT refresh token
- `user`: 存储当前用户信息对象

##### Getters

- `isAuthenticated`: 计算属性，判断用户是否已登录（基于 accessToken 是否存在）

##### Actions

| 方法                                  | 功能                                                    | 参数                      | 返回值           |
| :------------------------------------ | :------------------------------------------------------ | :------------------------ | :--------------- |
| `login(username, password)`           | 用户登录，获取 JWT token 并存储到 state 和 localStorage | username, password        | Promise<boolean> |
| `fetchUser()`                         | 获取当前用户信息，调用 `/api/v1/auth/me/`               | 无                        | Promise<void>    |
| `register(username, password, email)` | 用户注册，调用 `/api/v1/auth/register/`                 | username, password, email | Promise<boolean> |
| `logout()`                            | 登出，清除 state 和 localStorage 中的认证信息           | 无                        | void             |

**持久化策略**：

- Token 和用户信息存储在 `localStorage`
- 页面刷新时自动从 localStorage 恢复状态
- 代码路径：`frontend/src/stores/auth.js` (Line 1-103)

**安全性考虑**：

- Token 存储在 localStorage（需注意 XSS 风险，后续可考虑 httpOnly cookie）
- 未实现 Token 自动刷新逻辑（需在 Axios 拦截器中添加）

#### 1.2.4 数据可视化模块

**完成日期**：2026-01-17  
**组件**：Dashboard.vue

##### ECharts 集成

- **功能**：
  - 实现拉曼光谱数据的折线图展示
  - 支持图表交互（Zoom、Pan、SaveAsImage、Restore）
  - 支持深色/浅色主题自动切换
  - 模拟光谱数据展示（波长 400-500nm，强度 0-1000）
  - 渐变面积填充效果（areaStyle with LinearGradient）
  - 专业的科学坐标轴标注（cm⁻¹, a.u.）
- **技术实现**：
  - 集成 ECharts 6.0.0
  - 使用 `echarts.init()` 初始化图表
  - 配置 `dataZoom` 组件支持缩放和平移 (inside + slider 双模式)
  - 监听窗口 resize 事件自动调整图表大小
  - 渐变色填充：使用 `echarts.graphic.LinearGradient` 实现从上到下的透明度渐变
  - 医疗主题配色：良性使用绿色 (#28a745)，恶性使用红色 (#FF0000)
  - 动态标题更新：根据诊断结果显示置信度
- **代码路径**：`frontend/src/views/Dashboard.vue`

##### 文件上传功能

- **功能**：
  - 使用 Element Plus 的 `el-upload` 组件实现文件选择
  - 可选输入 `patient_id` 关联已有病患
  - 上传后展示诊断结果（诊断结论、置信度）
  - **TODO: 使用返回的实际数据更新图表** (Line 131)
- **代码路径**：`frontend/src/views/Dashboard.vue` (Line 107-145)

##### 主题切换

- **功能**：
  - 一键切换深色/浅色模式
  - 图表自动适配当前主题
  - 使用 `@vueuse/core` 的 `useDark` 和 `useToggle`
- **组件**：`ThemeToggle.vue` (使用 `el-switch` + Element Icons)
- **实现**：
  - 监听 `isDark` 变化，dispose 旧图表并重新初始化
  - 代码路径：`frontend/src/components/ThemeToggle.vue`, `frontend/src/views/Dashboard.vue` (Line 86-92)

**当前限制**：

- 图表数据为模拟数据（随机生成）
- 未实现真实光谱文件解析
- 未实现原始/处理后光谱对比展示（双曲线对比）
- 未实现特征峰标注功能
- 上传结果仅更新图表颜色和标题，未展示真实光谱数据

### 1.3 UI/UX 设计系统

**完成日期**：2026-01-17  
**设计风格**：现代医疗主题

#### 1.3.1 Tailwind CSS 集成

| 模块         | 功能点         | 实现细节                                                                    | 相关代码路径                  |
| :----------- | :------------- | :-------------------------------------------------------------------------- | :---------------------------- |
| **CSS 框架** | Tailwind CSS 4 | 集成 Tailwind CSS 4.1.18，使用 `@tailwindcss/postcss` 插件                  | `frontend/tailwind.config.js` |
| **PostCSS**  | 配置处理器     | 配置 PostCSS 支持 Tailwind 和 Autoprefixer                                  | `frontend/postcss.config.js`  |
| **主题定义** | 医疗配色方案   | 定义医疗主题色系：primary (#0072C6), success (#28a745), danger (#FF0000) 等 | `frontend/src/style.css`      |
| **暗色模式** | Dark Mode      | 使用 `class` 策略实现暗色模式，配置 `dark:` 变体支持                        | `frontend/tailwind.config.js` |

**医疗主题色系定义**：

```css
--color-medical-primary: #0072c6 // 医疗蓝
  --color-medical-secondary: #e6f3ff // 浅蓝
  --color-medical-success: #28a745 // 良性/成功绿
  --color-medical-warning: #ffc107 // 警告黄
  --color-medical-danger: #ff0000 // 恶性/危险红
  --color-medical-text-primary: #333 // 主文本色
  --color-medical-text-secondary: #666 // 次要文本色
  --color-medical-bg: #f5f7fa; // 背景色
```

#### 1.3.2 UI 组件优化

**登录/注册页面视觉设计**：

- 渐变背景：`bg-gradient-to-br from-gray-50 to-gray-200`
- 圆角卡片：`rounded-xl shadow-lg`
- 顶部彩色边框：`border-t-4 border-medical-primary`
- 医疗图标：`FirstAidKit` 图标作为品牌标识
- 大号按钮：`!h-12 !text-lg` 提升可点击性
- 暗色模式适配：`dark:bg-gray-800 dark:text-gray-400`

**Dashboard 图表设计**：

- 透明背景：与页面主题无缝融合
- 渐变面积填充：良性绿色 / 恶性红色渐变
- 专业坐标轴：使用科学记号（cm⁻¹, a.u.）
- 工具栏图标：保存、缩放、恢复等操作
- 主题自适应：图表颜色随暗色模式切换

### 1.4 项目管理与配置

**完成日期**：2026-01-15  
**版本控制**：Git

| 模块         | 功能点          | 实现细节                                                                                                   | 相关代码路径             |
| :----------- | :-------------- | :--------------------------------------------------------------------------------------------------------- | :----------------------- |
| **版本控制** | Git 仓库初始化  | 初始化 Git 仓库，配置 `.gitignore` 排除敏感文件和依赖目录                                                  | `.gitignore`             |
| **忽略规则** | .gitignore 配置 | 排除 Python `__pycache__`、Node `node_modules`、环境变量文件 `.env`、数据库文件 `db.sqlite3`、编辑器配置等 | `.gitignore` (Line 1-64) |
| **文档管理** | docs 目录       | 创建项目文档目录，存放进度报告等文档                                                                       | `docs/`                  |

---

## 2. 待完成工作 (Pending Work)

以下任务按优先级和预计完成时间排序，标注了技术难点和风险评估。

### 2.1 核心功能开发

| 任务项               | 优先级 | 当前进度 | 剩余工作量                                                                                                                                                                    | 预计完成时间 | 风险/难点                                                                                                      |
| :------------------- | :----- | :------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------- | :------------------------------------------------------------------------------------------------------------- |
| **深度学习模型集成** | **P0** | 0%       | 需加载 `.pth/.onnx` 模型文件，实现 `backend/utils/inference.py` 模块，替换 Mock 数据。集成 PyTorch 推理引擎，实现批量预测接口。                                               | 2026-01-20   | **高风险**：模型推理性能优化（需要 GPU 支持或 CPU 多线程优化）；PyTorch 在生产环境的内存管理；模型版本兼容性。 |
| **光谱数据预处理**   | **P0** | 10%      | 实现 `backend/utils/preprocess.py` 模块，包含去基线 (Baseline Removal - 多项式拟合或 asymmetric least squares)、平滑 (Savitzky-Golay Filter)、归一化 (Min-Max/Z-score) 算法。 | 2026-01-19   | **中风险**：预处理算法的参数调优直接影响诊断准确率；需要验证算法在不同光谱仪数据上的泛化性。                   |
| **文件存储服务**     | **P1** | 20%      | 配置 Django `MEDIA_ROOT` 和 `MEDIA_URL`，实现本地文件存储。或接入对象存储服务 (MinIO/AWS S3/阿里云 OSS)。修改 `SpectrumRecord.file_path` 为 `FileField`。                     | 2026-01-21   | **低风险**：大文件上传的断点续传（如需要）；存储空间管理和清理策略。                                           |
| **光谱文件解析**     | **P1** | 0%       | 实现多格式光谱文件读取器 (.txt, .csv, .spc, .dx 等)，解析波长和强度数据，转换为标准 JSON 格式。                                                                               | 2026-01-21   | **中风险**：不同光谱仪厂商的文件格式差异；需要处理损坏或格式错误的文件。                                       |
| **后台数据管理**     | **P2** | 0%       | 配置 Django Admin 后台，注册 `Patient`, `SpectrumRecord`, `UserProfile` 模型。或开发自定义管理页面（Vue + Element Plus 表格组件）。                                           | 2026-01-22   | **低风险**：需要权限控制（仅管理员可访问）。                                                                   |

### 2.2 前端优化

| 任务项             | 优先级 | 当前进度 | 剩余工作量                                                                               | 预计完成时间 | 风险/难点                                                                                            |
| :----------------- | :----- | :------- | :--------------------------------------------------------------------------------------- | :----------- | :--------------------------------------------------------------------------------------------------- |
| **图表高级交互**   | **P1** | 30%      | 实现多光谱曲线对比叠加显示，特征峰自动标注（基于峰值检测算法），图例管理。               | 2026-01-23   | **中风险**：大量数据点渲染时的前端性能优化（虚拟滚动或数据抽样）；特征峰识别算法前端实现或后端计算。 |
| **数据表格展示**   | **P2** | 0%       | 在 Dashboard 中添加历史记录表格，展示所有诊断记录，支持分页、排序、筛选。                | 2026-01-23   | **低风险**                                                                                           |
| **病患管理页面**   | **P2** | 0%       | 创建独立的病患管理页面 (`/patients`)，支持添加、编辑、删除病患信息，查看关联的光谱记录。 | 2026-01-24   | **低风险**                                                                                           |
| **Token 自动刷新** | **P1** | 0%       | 在 Axios 拦截器中实现 Token 过期自动刷新逻辑（401 响应时调用 refresh token 接口）。      | 2026-01-20   | **中风险**：需要避免刷新 Token 的并发请求导致的竞态条件。                                            |
| **响应式设计优化** | **P2** | 60%      | 优化移动端和平板设备的页面布局，调整图表和表单的响应式断点。                             | 2026-01-24   | **低风险**                                                                                           |

### 2.3 测试与质量保证

| 任务项           | 优先级 | 当前进度 | 剩余工作量                                                                      | 预计完成时间 | 风险/难点                                              |
| :--------------- | :----- | :------- | :------------------------------------------------------------------------------ | :----------- | :----------------------------------------------------- |
| **后端单元测试** | **P1** | 0%       | 使用 Django TestCase 编写模型、视图、序列化器的单元测试，覆盖率目标 80%+。      | 2026-01-23   | **低风险**：需要配置测试数据库。                       |
| **前端组件测试** | **P2** | 0%       | 使用 Vitest + Vue Test Utils 编写组件测试（Login, Register, Dashboard）。       | 2026-01-25   | **低风险**：需要熟悉 Composition API 测试写法。        |
| **集成测试**     | **P1** | 0%       | 编写端到端测试（Cypress/Playwright），覆盖用户注册、登录、上传、诊断全流程。    | 2026-01-25   | **中风险**：需要搭建测试环境和 CI/CD 流程。            |
| **安全性审计**   | **P0** | 0%       | 检查 SQL 注入、XSS、CSRF 防护；实现敏感数据加密存储（病患姓名等）；配置 HTTPS。 | 2026-01-26   | **高风险**：涉及医疗数据，需要符合 GDPR/HIPAA 等法规。 |

### 2.4 部署与运维

| 任务项             | 优先级 | 当前进度 | 剩余工作量                                                                  | 预计完成时间 | 风险/难点                          |
| :----------------- | :----- | :------- | :-------------------------------------------------------------------------- | :----------- | :--------------------------------- |
| **Docker 容器化**  | **P1** | 0%       | 编写 `Dockerfile` 和 `docker-compose.yml`，实现前后端和数据库的容器化部署。 | 2026-01-22   | **低风险**                         |
| **生产环境配置**   | **P1** | 0%       | 配置 Gunicorn + Nginx (后端)，Nginx 静态文件服务 (前端)，配置 SSL 证书。    | 2026-01-25   | **中风险**：需要域名和服务器资源。 |
| **日志与监控**     | **P2** | 0%       | 集成日志系统（Sentry/ELK），实现错误追踪和性能监控。                        | 2026-01-26   | **低风险**                         |
| **数据库备份策略** | **P2** | 0%       | 配置 MySQL 自动备份脚本（cron + mysqldump），实现灾难恢复方案。             | 2026-01-27   | **低风险**                         |

### 2.5 待定需求

以下功能需要进一步明确需求或等待资源配置：

- **多用户协作**：实现多医生协作审核光谱记录，添加评论和修改诊断结果功能
- **报告导出**：生成 PDF 格式的诊断报告，包含光谱图和结论
- **统计分析**：实现诊断准确率统计、ROC 曲线绘制、混淆矩阵展示
- **模型训练平台**：开发简易的模型重训练界面（上传新数据集、调参、评估）
- **国际化支持**：前端多语言支持（中文/英文切换）

---

## 3. 项目状态总结 (Project Summary)

### 3.1 总体进度

- **总体完成度**: **40%** ⬆️ (+5%)
- **后端框架**: 90% (基础架构稳固，API 接口已通)
- **前端框架**: 85% ⬆️ (页面流程跑通，UI 设计优化，Tailwind CSS 集成)
- **UI/UX 设计**: 75% ⬆️ (医疗主题色系，暗色模式，响应式布局)
- **核心算法**: 5% (暂未集成真实模型)

### 3.2 关键里程碑

- [x] **M1: 框架搭建 (2026-01-17)** - 前后端项目初始化，数据库连通，环境配置完成。
- [x] **M2: 认证流程 (2026-01-17)** - 完成用户注册、登录、JWT 鉴权全流程。
- [ ] **M3: 核心功能 (预计 2026-01-20)** - 实现真实光谱数据的上传、预处理与模型推理。
- [ ] **M4: 系统交付 (预计 2026-01-25)** - 完成所有 UI 细节优化与测试，部署上线。

### 3.3 遇到的问题与解决方案

1. **MySQL 9.x 兼容性问题**:
   - _问题_: `mysqlclient` 无法处理 MySQL 9.4 的 `caching_sha2_password` 认证，导致 `OperationalError: 1045`。
   - _解决_: 切换至纯 Python 实现的 `pymysql` 驱动，并在 Django 启动时进行 Monkey Patch。
2. **前端错误提示笼统**:
   - _问题_: 注册失败时仅提示"可能用户名已存在"，无法反馈具体字段错误。
   - _解决_: 切换至纯 Python 实现的 `pymysql` 驱动，并在 Django 启动时进行 Monkey Patch。
2. **前端错误提示笼统**:
    - _问题_: 注册失败时仅提示"可能用户名已存在"，无法反馈具体字段错误。
    - _解决_: 优化 Axios 错误捕获逻辑，解析后端返回的详细 JSON 错误并在 UI 上精准回显。

### 3.4 下一步工作计划

1. **模型接入**: 将训练好的 PyTorch 模型文件部署到 `backend/ml_models/` 目录，并编写推理服务类。
2. **数据处理**: 完善 `backend/utils/preprocess.py`，实现真实的拉曼光谱去噪逻辑。
3. **图表优化**: 根据预处理结果，在前端 ECharts 中展示"原始光谱"与"处理后光谱"的对比视图。
4. **Token 刷新**: 在 Axios 拦截器中实现 Token 自动刷新机制。
5. **测试编写**: 启动单元测试和集成测试的编写工作。

---

## 4. 技术架构概览 (Technical Architecture)

### 4.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│                    (Chrome/Firefox/Edge)                    │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    前端层 (Frontend)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Vue 3 + Vite + Element Plus                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │ Login.vue  │  │Register.vue│  │Dashboard   │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │       Pinia Store (State Management)       │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │   Axios (HTTP Client + Interceptors)      │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │      ECharts 6.0 (Data Visualization)     │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API (JSON)
                     │ JWT Bearer Token
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   后端层 (Backend API)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       Django 6.0 + Django REST Framework             │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │          API Endpoints (views.py)          │     │  │
│  │  │  • /api/v1/auth/register/                  │     │  │
│  │  │  • /api/v1/auth/login/                     │     │  │
│  │  │  • /api/v1/auth/refresh/                   │     │  │
│  │  │  • /api/v1/auth/me/                        │     │  │
│  │  │  • /api/v1/upload/                         │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │       JWT Authentication Layer             │     │  │
│  │  │     (djangorestframework-simplejwt)        │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │         Serializers (DRF)                  │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │      业务逻辑层 (Business Logic)           │     │  │
│  │  │  • utils/preprocess.py (待实现)            │     │  │
│  │  │  • utils/inference.py (待实现)             │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ ORM (Django Models)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据层 (Data Layer)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  MySQL 9.4 数据库                     │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │   User     │  │UserProfile │  │  Patient   │     │  │
│  │  │ (Django)   │  │   (扩展)   │  │  (病患)    │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  ┌──────────────────────────────────────┐           │  │
│  │  │       SpectrumRecord (光谱记录)      │           │  │
│  │  └──────────────────────────────────────┘           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               机器学习层 (ML Layer - 待集成)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              PyTorch 推理引擎                         │  │
│  │  • 模型加载 (.pth/.onnx)                             │  │
│  │  • 预处理算法 (去基线、平滑、归一化)                  │  │
│  │  • 特征提取与分类                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 技术栈详细说明

#### 前端技术栈

| 技术/库                     | 版本  | 用途                   | 选型理由                                       |
| :-------------------------- | :---- | :--------------------- | :--------------------------------------------- |
| **Vue.js**                  | 3.5.x | 渐进式 JavaScript 框架 | Composition API 提供更好的类型推断和逻辑复用   |
| **Vite**                    | 7.2.x | 前端构建工具           | 极速的开发服务器启动和热更新，原生 ES 模块支持 |
| **Element Plus**            | 2.13  | UI 组件库              | 完整的企业级组件生态，与 Vue 3 深度集成        |
| **Pinia**                   | 3.0   | 状态管理               | Vue 3 官方推荐，比 Vuex 更简洁的 API           |
| **Vue Router**              | 4.6   | 路由管理               | Vue 3 官方路由，支持路由守卫和懒加载           |
| **Axios**                   | 1.13  | HTTP 客户端            | 支持拦截器、请求/响应转换、自动 JSON 转换      |
| **ECharts**                 | 6.0   | 数据可视化             | 功能强大的图表库，支持主题定制和丰富的交互     |
| **@vueuse/core**            | 14.1  | Vue Composition 工具集 | 提供 useDark 等常用组合式 API，减少重复代码    |
| **Sass**                    | 1.97  | CSS 预处理器           | 支持变量、嵌套、混入等高级 CSS 特性            |
| **@element-plus/icons-vue** | 2.3   | 图标库                 | Element Plus 官方图标，开箱即用                |

#### 后端技术栈

| 技术/库                           | 版本 | 用途             | 选型理由                                             |
| :-------------------------------- | :--- | :--------------- | :--------------------------------------------------- |
| **Django**                        | 6.0  | Web 框架         | 成熟稳定的 Python Web 框架，ORM 强大，Admin 开箱即用 |
| **Django REST Framework**         | 3.x  | RESTful API 框架 | 提供序列化器、视图集、认证等完整的 API 开发工具      |
| **djangorestframework-simplejwt** | -    | JWT 认证         | 无状态认证，适合前后端分离架构                       |
| **django-cors-headers**           | -    | CORS 跨域支持    | 解决开发环境跨域问题                                 |
| **PyMySQL**                       | -    | MySQL 数据库驱动 | 纯 Python 实现，兼容 MySQL 8.0+/9.x 的新认证方式     |
| **django-environ**                | -    | 环境变量管理     | 安全管理敏感配置，支持 .env 文件                     |
| **pandas**                        | -    | 数据处理         | 强大的数据分析库，用于光谱数据预处理                 |
| **numpy**                         | -    | 科学计算         | 高性能数组运算，光谱数据计算基础库                   |
| **scipy**                         | -    | 科学计算工具集   | 提供信号处理算法（如 Savitzky-Golay 滤波）           |
| **PyTorch**                       | -    | 深度学习框架     | 灵活的动态图模型，广泛应用于医疗影像和光谱分析       |

#### 数据库

| 技术      | 版本 | 说明                                             |
| :-------- | :--- | :----------------------------------------------- |
| **MySQL** | 9.4  | 生产级关系型数据库，支持事务、外键约束、全文索引 |

#### 开发工具

| 工具                 | 用途            |
| :------------------- | :-------------- |
| **Git**              | 版本控制        |
| **VS Code**          | 代码编辑器      |
| **Conda**            | Python 环境管理 |
| **npm/yarn**         | 前端包管理      |
| **Postman/Insomnia** | API 测试        |

### 4.3 核心数据流

#### 4.3.1 用户认证流程

```
1. 用户在前端输入用户名和密码
   ↓
2. 前端发送 POST /api/v1/auth/login/ 请求
   ↓
3. Django REST Framework 验证用户名和密码
   ↓
4. SimpleJWT 生成 access_token 和 refresh_token
   ↓
5. 前端接收 Token 并存储到 localStorage
   ↓
6. 前端使用 access_token 调用 /api/v1/auth/me/ 获取用户信息
   ↓
7. 后续所有请求在 HTTP Header 中携带 Authorization: Bearer <token>
   ↓
8. Django 中间件自动验证 Token 有效性
```

#### 4.3.2 光谱上传与诊断流程 (当前实现 + 待实现)

```
用户上传光谱文件
   ↓
前端: Dashboard.vue 调用 handleUpload()
   ↓
POST /api/v1/upload/ (multipart/form-data)
   • file: 光谱文件
   • patient_id (可选): 关联病患ID
   ↓
后端: UploadView 接收请求
   ↓
[待实现] 1. 解析光谱文件 (utils/parser.py)
   • 读取 .txt/.csv 文件
   • 提取波长和强度数据
   ↓
[待实现] 2. 数据预处理 (utils/preprocess.py)
   • 去基线 (Baseline Removal)
   • Savitzky-Golay 平滑
   • Min-Max 归一化
   ↓
[待实现] 3. 模型推理 (utils/inference.py)
   • 加载 PyTorch 模型
   • 输入预处理后的数据
   • 获取分类结果和置信度
   ↓
[当前] 4. 存储结果到数据库
   • 创建 SpectrumRecord 记录
   • 关联 Patient 和 User
   ↓
返回 JSON 响应
{
  "id": 1,
  "diagnosis_result": "Benign",
  "confidence_score": 0.95,
  "file_path": "spectrum_001.txt",
  ...
}
   ↓
前端: 更新 UI
   • 显示诊断结果
   • 更新 ECharts 图表
   • [待实现] 展示原始/处理后光谱对比
```

### 4.4 安全性设计

#### 4.4.1 认证与授权

- **JWT 无状态认证**: 每个请求携带 Token，服务器无需维护 Session
- **Token 过期机制**: Access Token 短期有效（5分钟），Refresh Token 长期有效（1天）
- **权限控制**: 基于 Django 的 `IsAuthenticated` 权限类，未登录用户无法访问核心 API

#### 4.4.2 数据安全（待完善）

- **HTTPS 传输加密**: 生产环境强制 HTTPS，防止中间人攻击
- **SQL 注入防护**: Django ORM 自动参数化查询
- **XSS 防护**: 前端使用 Vue 的模板语法自动转义
- **CSRF 防护**: Django 内置 CSRF 中间件
- **敏感数据加密**: 待实现病患姓名等字段的加密存储

#### 4.4.3 输入验证

- **前端验证**: Element Plus 表单验证（非空、格式检查）
- **后端验证**: DRF Serializer 自动验证字段类型和长度
- **文件上传限制**: 待实现文件大小、格式、MIME 类型检查

### 4.5 性能优化策略

#### 4.5.1 前端优化

- **代码分割**: Vue Router 懒加载，减少首屏加载时间
- **资源压缩**: Vite 生产构建自动压缩 JS/CSS
- **图表性能**: ECharts 数据抽样和虚拟渲染（待实现）
- **缓存策略**: 静态资源设置长期缓存

#### 4.5.2 后端优化

- **数据库索引**: 待添加常用查询字段索引（如 `created_at`, `uploaded_by`）
- **查询优化**: 使用 `select_related()` 和 `prefetch_related()` 减少 SQL 查询次数
- **异步任务**: 待集成 Celery 处理耗时的模型推理任务
- **API 分页**: 历史记录列表使用分页，避免一次加载大量数据

#### 4.5.3 模型推理优化（待实现）

- **模型量化**: PyTorch Dynamic Quantization 减少内存和推理时间
- **ONNX 转换**: 使用 ONNX Runtime 提升推理速度
- **批量推理**: 积累多个请求后批量推理
- **模型缓存**: 模型加载后缓存在内存中，避免重复加载

### 4.6 可扩展性设计

#### 4.6.1 水平扩展

- **无状态 API**: JWT 认证使服务器无状态，便于负载均衡
- **数据库读写分离**: 未来可配置 MySQL 主从复制
- **对象存储**: 文件存储可迁移到 S3/MinIO，支持分布式存储

#### 4.6.2 功能扩展

- **插件化模型**: 预留模型版本管理接口，支持多模型切换
- **多租户支持**: 可扩展为多医院/多组织的 SaaS 系统
- **国际化**: 前端支持 i18n，后端 API 支持多语言错误信息

### 4.7 部署架构（规划）

#### 开发环境

```
前端: npm run dev (Vite Dev Server, Port 5173)
后端: python manage.py runserver (Django Dev Server, Port 8000)
数据库: MySQL 9.4 (localhost:3306)
```

#### 生产环境（规划）

```
┌─────────────┐
│   Nginx     │ (反向代理 + 静态文件服务)
└──────┬──────┘
       │
       ├─► 前端静态文件 (Port 80/443)
       │
       └─► Gunicorn (WSGI Server, Port 8000)
              │
              └─► Django Application (多进程/多线程)
                     │
                     └─► MySQL 9.4 (数据库连接池)

Docker 容器化:
- frontend: nginx + 编译后的静态文件
- backend: gunicorn + django
- database: mysql:9.4
```

---

## 5. 附录 (Appendix)

### 5.1 关键代码片段

#### JWT 认证配置 (settings.py)

```python
from datetime import timedelta

# JWT 配置
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

#### Axios 拦截器配置 (auth.js)

```javascript
// 请求拦截器：自动添加 Token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// 响应拦截器：处理 401 错误（待实现 Token 刷新）
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // TODO: 尝试刷新 Token
      // 如果刷新失败，跳转到登录页
    }
    return Promise.reject(error);
  },
);
```

### 5.2 数据库表结构

#### User (Django 内置)

| 字段        | 类型         | 说明     |
| :---------- | :----------- | :------- |
| id          | int          | 主键     |
| username    | varchar(150) | 用户名   |
| password    | varchar(128) | 哈希密码 |
| email       | varchar(254) | 邮箱     |
| is_active   | boolean      | 是否激活 |
| date_joined | datetime     | 注册时间 |

#### UserProfile

| 字段    | 类型        | 说明         |
| :------ | :---------- | :----------- |
| id      | int         | 主键         |
| user_id | int (FK)    | 关联 User    |
| role    | varchar(10) | admin/doctor |

#### Patient

| 字段       | 类型         | 说明     |
| :--------- | :----------- | :------- |
| id         | int          | 主键     |
| name       | varchar(255) | 姓名     |
| age        | int          | 年龄     |
| gender     | varchar(10)  | M/F      |
| created_at | datetime     | 创建时间 |

#### SpectrumRecord

| 字段             | 类型         | 说明             |
| :--------------- | :----------- | :--------------- |
| id               | int          | 主键             |
| patient_id       | int (FK)     | 关联 Patient     |
| uploaded_by_id   | int (FK)     | 关联 User        |
| file_path        | varchar(500) | 文件路径         |
| processed_path   | varchar(500) | 预处理后路径     |
| diagnosis_result | varchar(50)  | Benign/Malignant |
| confidence_score | float        | 置信度 (0.0-1.0) |
| is_reviewed      | boolean      | 是否复核         |
| created_at       | datetime     | 上传时间         |

### 5.3 API 接口文档摘要

| 方法 | 端点                   | 认证 | 说明             |
| :--- | :--------------------- | :--- | :--------------- |
| POST | /api/v1/auth/register/ | ❌   | 用户注册         |
| POST | /api/v1/auth/login/    | ❌   | 用户登录         |
| POST | /api/v1/auth/refresh/  | ❌   | 刷新 Token       |
| GET  | /api/v1/auth/me/       | ✅   | 获取当前用户信息 |
| POST | /api/v1/upload/        | ✅   | 上传光谱文件     |

---

## 6. 总结与展望

本项目在过去3天内完成了从零到原型的快速开发，建立了完整的前后端架构和用户认证体系。目前项目处于 **Alpha 阶段（35%完成度）**，核心框架已稳固，但缺少最关键的深度学习模型集成。

**优势**：

- ✅ 技术选型现代且成熟（Vue 3 + Django 6.0）
- ✅ 前后端分离架构，便于团队协作
- ✅ JWT 无状态认证，适合分布式部署
- ✅ 代码结构清晰，易于维护和扩展

**挑战**：

- ⚠️ 模型推理性能优化（CPU vs GPU）
- ⚠️ 医疗数据安全合规（加密、审计）
- ⚠️ 多格式光谱文件解析

**下一步重点**：

1. **本周（1月17-23日）**: 集成深度学习模型，打通完整诊断流程
2. **下周（1月24-30日）**: 测试、安全审计、性能优化、部署

预计在 **2026年1月底** 完成系统的首个可用版本（Beta），并进行小规模试点测试。

---

**报告编制**: GitHub Copilot AI Assistant  
**最后更新**: 2026年1月17日  
**项目仓库**: `d:\studio\RamanAI`  
**联系方式**: 项目负责人（待补充）

---

_本报告基于代码静态分析和项目结构自动生成，涵盖已完成工作、待办事项、技术架构和风险评估。_

**报告编制**: GitHub Copilot AI Assistant  
**最后更新**: 2026年1月17日  
**项目仓库**: `d:\studio\RamanAI`  
**联系方式**: 项目负责人（待补充）

---

_本报告基于代码静态分析和项目结构自动生成，涵盖已完成工作、待办事项、技术架构和风险评估。_
