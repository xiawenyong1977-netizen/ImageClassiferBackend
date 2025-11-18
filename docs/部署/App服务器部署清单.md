# App服务器部署清单

## 📋 概述

根据前后端分离部署方案，App服务器（www.aifuture.net.cn）只需要部署后端API服务，不需要部署前端页面。

## ✅ 必须部署的文件和目录

### 1. 核心应用代码
- **`app/`** - 应用核心代码目录（必须）
  - 包含所有API路由、服务、工具等

### 2. 配置文件
- **`.env`** - 环境变量配置文件（必须）
  - 包含数据库配置、API密钥等敏感信息
  - 注意：不要提交到Git，只在服务器上存在

### 3. 依赖和启动配置
- **`requirements.txt`** - Python依赖文件（必须）
  - 用于安装Python包：`pip install -r requirements.txt`
  
- **`gunicorn_config.py`** - Gunicorn配置文件（必须）
  - 用于生产环境启动服务：`gunicorn -c gunicorn_config.py app.main:app`

### 4. 图像存储目录
- **`app/images/`** - 图像编辑结果存储目录（必须）
  - 用于存储图像编辑功能生成的图片
  - FastAPI会挂载 `/images` 路径提供图片服务
  - 注意：images目录在app目录下，不需要单独的web目录

## ❌ 不需要部署的文件和目录

### 前端文件（在旧服务器）
- `web/*.html` - 前端HTML页面（不需要）
- `web/app.js` - 前端JavaScript（不需要）
- `web/*.json` - 前端配置文件（不需要）
- `web/*.txt` - 前端数据文件（不需要）

### 文档和工具（可选）
- `docs/` - 项目文档（不需要，但保留也无妨）
- `tools/` - 工具脚本（不需要，但保留便于运维）

### 其他文件
- `README.md` - 项目说明（不需要）
- `env.example` - 环境变量示例（不需要，但保留便于参考）

## 📁 最小化部署结构

```
/opt/ImageClassifierBackend/
├── app/                    # ✅ 必须
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── utils/
│   └── ...
├── web/                    # ✅ 只需要images目录
│   └── images/             # ✅ 必须（图像编辑结果存储）
│       └── edited/         # 自动创建
├── .env                    # ✅ 必须（环境变量）
├── requirements.txt        # ✅ 必须（Python依赖）
└── gunicorn_config.py      # ✅ 必须（Gunicorn配置）
```

## 🔍 代码依赖分析

### web/images目录的必要性

1. **图像编辑功能需要**
   ```python
   # app/services/image_editor.py:283
   save_dir = "/opt/ImageClassifierBackend/web/images/edited"
   ```
   - 图像编辑功能会将处理后的图片保存到此目录

2. **静态文件服务需要**
   ```python
   # app/main.py:118-120
   images_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "images")
   if os.path.exists(images_path):
       app.mount("/images", StaticFiles(directory=images_path), name="images")
   ```
   - FastAPI会挂载 `/images` 路径，提供图片访问服务
   - 返回的URL格式：`https://api.aifuture.net.cn/images/edited/xxx.png`

## 📦 部署建议

### 方案1：最小化部署（推荐）

只部署必要的文件：

```bash
# 需要部署的内容
app/
  └── images/        # 只需要这个子目录，可以创建空目录
.env
requirements.txt
gunicorn_config.py
```

### 方案2：完整部署（便于运维）

部署所有文件，但前端文件不会被使用：

```bash
# 部署整个项目
app/
web/                 # 完整目录（但只使用images子目录）
docs/                # 文档（可选）
tools/               # 工具脚本（可选）
.env
requirements.txt
gunicorn_config.py
README.md
env.example
```

## ⚠️ 注意事项

1. **web/images目录必须存在**
   - 即使目录为空，也必须创建
   - 应用启动时会检查目录是否存在
   - 图像编辑功能会自动创建 `web/images/edited/` 子目录

2. **.env文件安全**
   - 包含敏感信息（数据库密码、API密钥等）
   - 不要提交到Git
   - 确保文件权限：`chmod 600 .env`

3. **requirements.txt必须**
   - 用于安装Python依赖
   - 部署时必须执行：`pip install -r requirements.txt`

4. **gunicorn_config.py必须**
   - 生产环境启动服务需要
   - 如果使用systemd管理服务，也需要此文件

## 🚀 快速部署命令

```bash
# 1. 创建必要目录
mkdir -p /opt/ImageClassifierBackend/web/images

# 2. 部署代码（只部署必要文件）
# 方式1：使用rsync（推荐）
rsync -avz --exclude='docs' --exclude='tools' \
    app/ .env requirements.txt gunicorn_config.py \
    root@app:/opt/ImageClassifierBackend/

# 方式2：使用scp
scp -r app/ root@app:/opt/ImageClassifierBackend/
scp requirements.txt gunicorn_config.py root@app:/opt/ImageClassifierBackend/
ssh root@app "mkdir -p /opt/ImageClassifierBackend/app/images"

# 3. 安装依赖
ssh root@app "cd /opt/ImageClassifierBackend && pip install -r requirements.txt"

# 4. 启动服务
ssh root@app "cd /opt/ImageClassifierBackend && gunicorn -c gunicorn_config.py app.main:app"
```

## 📊 总结

**最小化部署需要：**
- ✅ `app/` 目录（包含images子目录）
- ✅ `.env` 文件
- ✅ `requirements.txt` 文件
- ✅ `gunicorn_config.py` 文件

**不需要：**
- ❌ `web/` 目录（已删除，images已移到app目录下）
- ❌ `docs/` 文档目录（可选）
- ❌ `tools/` 工具目录（可选）

---

**文档版本**: v1.0  
**创建日期**: 2025-01-XX  
**维护者**: ImageClassifier Team

