# ImageClassifierBackend - AI智能图片分类后端服务

[![Website](https://img.shields.io/badge/website-https://www.xintuxiangce.top-blue.svg)](https://www.xintuxiangce.top/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green.svg)](https://fastapi.tiangolo.com)
[![AI](https://img.shields.io/badge/AI-90%25%2B%20Accuracy-brightgreen.svg)](https://www.xintuxiangce.top/)
[![GitHub Stars](https://img.shields.io/github/stars/xiawenyong1977-netizen/ImageClassiferBackend?style=social)](https://github.com/xiawenyong1977-netizen/ImageClassiferBackend)

## 📖 项目简介

**ImageClassifierBackend** 是一款基于大模型技术的智能图片分类后端服务，为客户端提供高精度、低成本的图片分类API。系统采用FastAPI异步框架，支持8种预定义分类，通过智能缓存机制显著降低大模型调用成本，是AI照片分类、图像识别、批量图片处理的理想解决方案。

### ✨ 核心特性

- 🤖 **AI智能分类** - 基于大模型技术，准确率高达90%以上，支持8大照片类别
- 💰 **成本优化** - 智能SHA-256哈希缓存机制，节省60-80%的API调用成本
- ⚡ **高性能** - FastAPI全异步架构，支持100+ QPS高并发处理
- 🔄 **混合推理** - 支持远程大模型推理和本地ONNX模型降级，确保服务高可用
- 🔒 **安全可靠** - 用户数据隔离、完整请求日志、JWT认证保护
- 📊 **统计分析** - 详细的性能监控、成本统计、缓存命中率分析
- 🌍 **地理位置** - 集成EXIF GPS解析，支持拍摄城市识别
- 🛠️ **管理后台** - 提供Web管理界面，方便运维和数据分析
- 📱 **多格式支持** - 支持JPG、PNG、WebP、GIF、MPO等主流图片格式

## 🎯 适用场景

- 📸 **照片分类管理** - 为照片管理应用提供AI分类API服务
- 🗂️ **批量图片处理** - 支持批量上传和分类，提高处理效率
- 💾 **智能相册整理** - 为相册应用提供智能分类能力
- 🔍 **图像内容识别** - 识别照片类型、场景、物体等
- 📱 **移动应用后端** - 为iOS/Android应用提供图片分类服务
- 🌐 **SaaS服务** - 为多租户提供图片分类API服务
- 🏢 **企业级应用** - 支持高并发、高可用的企业级图片处理需求

## 🚀 快速开始

### 系统要求

- **Python**: 3.8 或更高版本
- **MySQL**: 8.0 或更高版本
- **内存**: 4GB 以上（推荐8GB）
- **存储**: 1GB 可用磁盘空间
- **网络**: 可访问大模型API（阿里云通义千问/OpenAI/Claude）

### 安装部署

#### 1. 克隆项目

```bash
git clone https://github.com/xiawenyong1977-netizen/ImageClassiferBackend.git
cd ImageClassiferBackend
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
cp env.example .env
# 编辑 .env 文件，配置数据库和API密钥
```

主要配置项：
```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=image_classifier

# 大模型API配置（支持阿里云/OpenAI/Claude）
LLM_PROVIDER=aliyun
LLM_API_KEY=your-dashscope-api-key
LLM_MODEL=qwen-vl-plus
```

#### 4. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE image_classifier;"

# 导入数据库结构
mysql -u root -p image_classifier < tools/数据库/init.sql
```

#### 5. 启动服务

```bash
# 开发模式（带热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式（使用Gunicorn）
gunicorn -c gunicorn_config.py app.main:app
```

### API使用示例

#### 单张图片分类

```bash
curl -X POST "http://localhost:8000/api/v1/classify" \
  -H "X-User-ID: your-user-id" \
  -F "image=@photo.jpg"
```

#### 批量图片分类（最多20张）

```bash
curl -X POST "http://localhost:8000/api/v1/classify/batch" \
  -H "X-User-ID: your-user-id" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg"
```

#### 缓存查询（节省API成本）

```bash
curl -X POST "http://localhost:8000/api/v1/classify/check-cache" \
  -H "Content-Type: application/json" \
  -d '{"image_hash": "your-image-hash", "user_id": "your-user-id"}'
```

## 📊 分类效果与性能

### 支持的8大分类类别

| 分类类型 | 准确率 | 说明 | 应用场景 |
|---------|--------|------|---------|
| 📱 手机截图 | 98%+ | 手机屏幕截图、应用界面 | 截图管理、应用分析 |
| 🪪 证件照片 | 85%+ | 身份证、护照、驾照等 | 证件管理、隐私保护 |
| 👤 单人照片 | 92%+ | 个人照、自拍、肖像 | 人物相册、个人管理 |
| 👥 社交活动 | 95%+ | 聚会、合影、多人互动 | 社交相册、活动记录 |
| 🏞️ 旅行风景 | 90%+ | 旅游景点、自然风光 | 旅行相册、风景整理 |
| 🍔 美食记录 | 88%+ | 食物、餐饮、烹饪相关 | 美食相册、生活记录 |
| 🐱 宠物萌照 | 90%+ | 猫、狗等宠物照片 | 宠物相册、萌宠管理 |
| 📦 其它 | 80%+ | 无法归类到上述类别 | 通用分类 |

### 性能指标

| 指标 | 数据 | 说明 |
|------|------|------|
| **分类准确率** | **90%+** | 基于大模型的高精度分类 |
| **支持分类类别** | **8大类** | 覆盖常见照片场景 |
| **缓存命中率** | **60-80%** | 智能缓存大幅降低成本 |
| **API响应时间** | **<2秒** | 包含大模型推理时间 |
| **并发处理能力** | **100+ QPS** | FastAPI异步架构 |
| **成本节省** | **60-80%** | 通过缓存机制实现 |
| **支持图片格式** | **JPG/PNG/WebP/GIF/MPO** | 主流格式全覆盖 |
| **最大图片大小** | **10MB** | 可配置 |

## 🛠️ 技术架构

### 后端技术栈

- **FastAPI** - 现代、快速的Python Web框架，自动生成API文档
- **MySQL 8.0** - 高性能关系型数据库，存储分类结果和缓存
- **aiomysql** - 异步MySQL驱动，支持高并发数据库操作
- **Pydantic** - 数据验证和序列化，确保API数据安全
- **Uvicorn/Gunicorn** - ASGI服务器，支持生产环境部署

### AI技术栈

- **阿里云通义千问** - 大模型Vision API，提供高精度图像理解
- **OpenAI GPT-4 Vision** - 可选的大模型提供商
- **Claude Vision** - 可选的大模型提供商
- **ONNX Runtime** - 本地模型推理引擎，支持降级处理
- **YOLOv8** - 物体检测模型，用于证件照等特殊场景识别
- **MobileNetV3** - 轻量级图像分类模型，本地快速推理

### 核心优化策略

- **异步处理** - 全异步架构，充分利用I/O等待时间
- **连接池管理** - 数据库连接池，避免频繁建立连接
- **智能缓存** - SHA-256哈希去重，全局共享缓存
- **批量处理** - 支持批量API调用，提高吞吐量
- **分层处理** - 截图检测→缓存查询→远程推理→本地降级
- **混合推理** - 大模型失败时自动降级到本地模型

## 📁 项目结构

```
ImageClassifierBackend/
├── app/                          # 应用核心代码
│   ├── api/                     # API路由层
│   │   ├── classify.py          # 图片分类API
│   │   ├── auth.py                # 认证授权
│   │   ├── stats.py             # 统计分析
│   │   ├── location.py          # 地理位置
│   │   └── image_edit.py        # 图像编辑
│   ├── services/                # 业务服务层
│   │   ├── classifier.py        # 分类服务核心
│   │   ├── cache_service.py    # 缓存服务
│   │   ├── model_client.py      # 大模型客户端
│   │   ├── local_model_inference.py  # 本地推理
│   │   └── stats_service.py     # 统计服务
│   ├── models/                  # 数据模型
│   │   ├── schemas.py           # Pydantic模型
│   │   └── *.onnx               # AI模型文件
│   ├── utils/                   # 工具函数
│   │   ├── image_utils.py       # 图片处理工具
│   │   ├── hash_utils.py        # 哈希计算
│   │   └── id_generator.py     # ID生成器
│   ├── config.py                # 配置管理
│   ├── database.py              # 数据库连接
│   └── main.py                  # 应用入口
├── docs/                        # 📚 项目文档
├── tools/                       # 🔧 工具脚本
│   ├── 数据库/                  # 数据库脚本
│   ├── 部署/                    # 部署脚本
│   └── 测试/                    # 测试工具
├── web/                         # Web管理界面
├── requirements.txt             # Python依赖
└── env.example                  # 环境变量示例
```

## 🔧 配置说明

### 环境变量配置

完整的环境变量配置请参考 `env.example` 文件，主要配置包括：

- **数据库配置** - MySQL连接信息
- **大模型API配置** - 支持阿里云/OpenAI/Claude
- **应用配置** - 端口、调试模式等
- **图片配置** - 最大大小、支持格式
- **日志配置** - 日志级别、文件路径
- **分类提示词** - 可自定义分类规则

### 分类提示词自定义

系统支持自定义分类提示词，可在环境变量中配置 `CLASSIFICATION_PROMPT` 来优化分类效果。

## 📚 API文档

启动服务后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要API端点

- `POST /api/v1/classify` - 单张图片分类
- `POST /api/v1/classify/batch` - 批量图片分类（最多20张）
- `POST /api/v1/classify/check-cache` - 查询缓存
- `POST /api/v1/classify/batch-check-cache` - 批量查询缓存
- `GET /api/v1/stats/requests` - 请求统计
- `GET /api/v1/stats/cache` - 缓存统计
- `GET /api/v1/health` - 健康检查

## 🔐 安全特性

- ✅ **用户隔离** - 基于用户ID的数据隔离，保护用户隐私
- ✅ **请求日志** - 完整的API调用审计日志
- ✅ **JWT认证** - 管理后台使用JWT token认证
- ✅ **输入验证** - 严格的Pydantic数据验证
- ✅ **文件类型检查** - 支持格式白名单，防止恶意文件
- ✅ **大小限制** - 图片大小限制，防止资源滥用

## 📦 部署说明

### Docker部署

```bash
# 构建镜像
docker build -t image-classifier-backend .

# 运行容器
docker run -d -p 8000:8000 \
  -e MYSQL_HOST=your-mysql-host \
  -e MYSQL_PASSWORD=your-password \
  -e LLM_API_KEY=your-api-key \
  image-classifier-backend
```

### 生产环境部署

```bash
# 使用Gunicorn部署
gunicorn -c gunicorn_config.py app.main:app

# 使用systemd服务
sudo systemctl start image-classifier
sudo systemctl enable image-classifier
```

### 监控和运维

- **健康检查**: `curl http://localhost:8000/api/v1/health`
- **性能监控**: 访问 `/api/v1/stats/requests` 查看请求统计
- **日志查看**: `tail -f /var/log/image-classifier/app.log`

## 🤝 贡献指南

我们欢迎各种形式的贡献！

- 🐛 **报告Bug** - 在[GitHub Issues](https://github.com/xiawenyong1977-netizen/ImageClassiferBackend/issues)中提交问题
- 💡 **功能建议** - 提出新功能想法和改进建议
- 📝 **文档改进** - 完善使用说明和开发文档
- 🔧 **提交代码** - 修复Bug或添加新功能
- 🌟 **Star支持** - 给项目点星，支持项目发展

### 贡献步骤

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📚 相关资源

- 🌐 **官方网站**: https://www.xintuxiangce.top/ - 软件下载和使用指南
- 📖 **使用教程**: https://www.xintuxiangce.top/blog.html - 详细的使用教程
- 🔬 **技术博客**: https://www.xintuxiangce.top/blog.html - AI照片分类技术解析
- 📄 **API文档**: http://localhost:8000/docs - 完整的API交互式文档
- 📋 **更新日志**: [GitHub Releases](https://github.com/xiawenyong1977-netizen/ImageClassiferBackend/releases) - 版本更新记录

## 📄 许可证

本项目采用 **MIT 许可证** - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 🌐 **官网**: https://www.xintuxiangce.top/
- 📧 **邮箱**: contact@xintuxiangce.top
- 💬 **问题反馈**: [GitHub Issues](https://github.com/xiawenyong1977-netizen/ImageClassiferBackend/issues)
- 📱 **技术支持**: 通过官网联系表单

## 🙏 致谢

感谢所有使用和支持 ImageClassifierBackend 的用户！

特别感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 优秀的Python Web框架
- [阿里云通义千问](https://dashscope.aliyun.com/) - 强大的大模型Vision API
- [ONNX Runtime](https://onnxruntime.ai/) - 高性能模型推理引擎
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - 先进的物体检测模型
- 所有为开源社区做出贡献的开发者

---

⭐ **如果这个项目对您有帮助，请给我们一个Star！**

**© 2025 ImageClassifierBackend. 让AI分类更智能，让API调用更经济**
