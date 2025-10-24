# 图片分类后端系统 - AI智能照片分类服务

[![Website](https://img.shields.io/badge/website-https://www.xintuxiangce.top-blue.svg)](https://www.xintuxiangce.top/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com)
[![AI](https://img.shields.io/badge/AI-90%25%2B%20Accuracy-brightgreen.svg)](https://www.xintuxiangce.top/)

## 📖 项目简介

**图片分类后端系统**是基于大模型技术的智能照片分类服务，为客户端提供高精度的图片分类API，支持8种预定义分类和智能缓存机制，显著降低大模型调用成本。

### 核心优势

- 🤖 **AI智能分类** - 采用先进的深度学习技术，准确率高达90%以上
- 💰 **成本优化** - 智能缓存机制，避免重复调用大模型，节省API成本
- ⚡ **高性能** - FastAPI异步框架，支持高并发处理
- 🔒 **安全可靠** - 支持用户隔离，保护用户隐私数据
- 📊 **统计分析** - 完整的请求统计和性能监控
- 🔄 **混合推理** - 支持远程推理和本地推理，确保服务可用性
- 🌍 **地理位置** - 集成地理位置API，支持城市分类
- 🛠️ **管理后台** - 提供Web管理界面，方便运维管理

## ✨ 核心功能

### 📋 智能分类

支持8大预定义分类类别：

- 📱 **手机截图** (screenshot) - 手机屏幕截图、应用界面
- 🪪 **证件照片** (idcard) - 身份证、护照、驾照等重要证件
- 👤 **单人照片** (single_person) - 个人照、自拍、肖像照片
- 👥 **社交活动** (social_activities) - 聚会、合影、多人互动场景
- 🏞️ **旅行风景** (travel_scenery) - 旅游景点、山川湖海、自然风光
- 🍔 **美食记录** (foods) - 食物、餐饮、烹饪相关照片
- 🐱 **宠物萌照** (pets) - 猫、狗等宠物照片
- 📦 **其它** (other) - 无法归类到上述类别的照片

### 💾 智能缓存

- **SHA-256哈希去重** - 基于图片内容的智能缓存
- **全局共享缓存** - 多用户共享缓存，最大化成本节省
- **缓存统计** - 详细的缓存命中率统计
- **手动管理** - 支持手动删除特定用户缓存

### 🌍 地理位置服务

- **EXIF解析** - 自动解析照片GPS信息
- **城市识别** - 基于坐标识别拍摄城市
- **中文地名** - 支持中文城市名称映射

### 📊 统计分析

- **请求日志** - 完整的API调用记录
- **性能监控** - 处理时间、成功率等指标
- **成本统计** - API调用成本分析
- **用户行为** - 用户使用模式分析

## 🚀 快速开始

### 系统要求

- **Python**: 3.8 或更高版本
- **MySQL**: 8.0 或更高版本
- **内存**: 4GB 以上（推荐8GB）
- **存储**: 1GB 可用磁盘空间

### 环境配置

1. **克隆项目**
```bash
git clone https://github.com/your-username/ImageClassifierBackend.git
cd ImageClassifierBackend
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp env.example .env
# 编辑 .env 文件，配置数据库和API密钥
```

4. **初始化数据库**
```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE image_classifier;"

# 导入数据库结构
mysql -u root -p image_classifier < sql/init.sql
```

5. **启动服务**
```bash
# 开发模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
gunicorn -c gunicorn_config.py app.main:app
```

### 使用方式

#### API调用示例

```bash
# 单张图片分类
curl -X POST "http://localhost:8000/api/v1/classify" \
  -H "X-User-ID: your-user-id" \
  -F "image=@photo.jpg"

# 批量图片分类
curl -X POST "http://localhost:8000/api/v1/classify/batch" \
  -H "X-User-ID: your-user-id" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg"

# 缓存查询
curl -X POST "http://localhost:8000/api/v1/classify/check-cache" \
  -H "Content-Type: application/json" \
  -d '{"image_hash": "your-image-hash", "user_id": "your-user-id"}'
```

## 📊 性能指标

| 指标 | 数据 |
|------|------|
| 分类准确率 | **90%+** |
| 支持分类类别 | **8大类** |
| 缓存命中率 | **60-80%** |
| API响应时间 | **<2秒** |
| 并发处理能力 | **100+ QPS** |
| 成本节省 | **60-80%** |

## 🛠️ 技术架构

### 后端技术栈

- **FastAPI** - 现代、快速的Web框架
- **MySQL 8.0** - 关系型数据库
- **aiomysql** - 异步MySQL驱动
- **Pydantic** - 数据验证和序列化
- **Uvicorn** - ASGI服务器

### AI技术

- **阿里云通义千问** - 大模型推理服务
- **ONNX Runtime** - 本地模型推理引擎
- **YOLOv8** - 物体检测模型
- **MobileNetV3** - 图像分类模型

### 性能优化

- **异步处理** - 全异步架构，支持高并发
- **连接池** - 数据库连接池管理
- **智能缓存** - SHA-256哈希缓存机制
- **批量处理** - 批量API调用优化
- **分层处理** - 截图检测→缓存查询→远程推理→本地降级

## 📁 项目结构

```
ImageClassifierBackend/
├── app/                    # 应用核心代码
│   ├── api/               # API路由
│   │   ├── auth.py        # 认证相关
│   │   ├── classify.py    # 分类API
│   │   ├── health.py      # 健康检查
│   │   ├── local_classify.py  # 本地推理
│   │   ├── location.py    # 地理位置
│   │   ├── release.py     # 版本发布
│   │   └── stats.py       # 统计分析
│   ├── models/            # 数据模型
│   │   ├── schemas.py     # Pydantic模型
│   │   └── *.onnx         # AI模型文件
│   ├── services/          # 业务服务
│   │   ├── cache_service.py      # 缓存服务
│   │   ├── classifier.py         # 分类服务
│   │   ├── local_model_inference.py  # 本地推理
│   │   ├── model_client.py       # 模型客户端
│   │   └── stats_service.py      # 统计服务
│   ├── utils/             # 工具函数
│   │   ├── hash_utils.py  # 哈希工具
│   │   ├── id_generator.py # ID生成器
│   │   └── image_utils.py  # 图片工具
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库连接
│   └── main.py           # 应用入口
├── docs/                  # 📚 项目文档
├── tools/                 # 🔧 工具脚本
│   ├── delete_user_cache.py  # 缓存管理
│   ├── check_user_data.py    # 数据查询
│   └── test_local_inference.py # 测试工具
├── sql/                   # 数据库脚本
├── web/                   # Web管理界面
├── requirements.txt       # Python依赖
└── env.example           # 环境变量示例
```

## 🔧 配置说明

### 环境变量配置

```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=image_classifier

# 大模型API配置
LLM_PROVIDER=aliyun
LLM_API_KEY=your-dashscope-api-key
LLM_MODEL=qwen-vl-plus

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
```

### 分类配置

系统支持自定义分类提示词，可在环境变量中配置：

```bash
CLASSIFICATION_PROMPT="请对这张图片进行分类。你必须从以下8个类别中选择一个：..."
```

## 📚 文档导航

- **新手入门**：[快速使用手册](./docs/快速使用手册.md) | [README](./docs/README.md)
- **系统架构**：[设计文档](./docs/DESIGN.md) | [架构说明](./docs/架构说明_服务器与客户端职责分离.md)
- **部署配置**：[部署指南](./docs/DEPLOY.md) | [阿里云配置](./docs/ALIYUN_SETUP.md)
- **模型推理**：[本地推理](./docs/本地模型推理使用说明.md) | [混合推理](./docs/混合推理策略说明.md)
- **工具脚本**：[工具说明](./tools/README.md) - 数据管理、测试工具等

## 🔐 安全特性

- ✅ **用户隔离** - 基于用户ID的数据隔离
- ✅ **请求日志** - 完整的API调用审计
- ✅ **权限控制** - 管理后台权限验证
- ✅ **数据加密** - 敏感数据加密存储
- ✅ **输入验证** - 严格的输入数据验证

## 🔧 开发指南

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements.txt

# 启动开发服务器
python -m uvicorn app.main:app --reload

# 运行测试
python tools/test_local_inference.py
```

### API文档

启动服务后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 工具脚本

```bash
# 删除用户缓存
python tools/delete_user_cache.py <user_id> [--confirm]

# 检查用户数据
python tools/check_user_data.py <user_id>

# 测试本地推理
python tools/test_local_inference.py
```

## 📦 部署说明

### Docker部署

```bash
# 构建镜像
docker build -t image-classifier-backend .

# 运行容器
docker run -d -p 8000:8000 \
  -e MYSQL_HOST=your-mysql-host \
  -e MYSQL_PASSWORD=your-password \
  image-classifier-backend
```

### 生产部署

```bash
# 使用Gunicorn部署
gunicorn -c gunicorn_config.py app.main:app

# 使用systemd服务
sudo systemctl start image-classifier
sudo systemctl enable image-classifier
```

## 📊 监控和运维

### 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

### 性能监控

- **请求统计**: `/api/v1/stats/requests`
- **缓存统计**: `/api/v1/stats/cache`
- **系统状态**: `/api/v1/health`

### 日志管理

```bash
# 查看应用日志
tail -f /var/log/image-classifier/app.log

# 查看错误日志
grep "ERROR" /var/log/image-classifier/app.log
```

## 🤝 贡献指南

我们欢迎各种形式的贡献：

- 🐛 **报告Bug** - 在[Issues](https://github.com/your-username/ImageClassifierBackend/issues)中提交问题
- 💡 **功能建议** - 提出新功能想法和改进建议
- 📝 **文档改进** - 完善使用说明和开发文档
- 🔧 **提交代码** - 修复Bug或添加新功能
- 🌟 **Star支持** - 给项目点星，支持项目发展

### 贡献步骤

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📚 相关资源

- [官方网站](https://www.xintuxiangce.top/) - 软件下载和使用指南
- [使用教程](https://www.xintuxiangce.top/blog.html) - 详细的使用教程
- [技术博客](https://www.xintuxiangce.top/blog.html) - AI照片分类技术解析
- [API文档](http://localhost:8000/docs) - 完整的API文档
- [更新日志](https://github.com/your-username/ImageClassifierBackend/releases) - 版本更新记录

## 🔄 更新日志

查看 [CHANGELOG](CHANGELOG.md) 了解版本更新详情。

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 🌐 **官网**：https://www.xintuxiangce.top/
- 📧 **邮箱**：contact@xintuxiangce.top
- 💬 **问题反馈**：[GitHub Issues](https://github.com/your-username/ImageClassifierBackend/issues)
- 📱 **技术支持**：通过官网联系表单

## 🙏 致谢

感谢所有使用和支持图片分类后端系统的用户！

特别感谢：
- FastAPI 团队提供的优秀Web框架
- 阿里云通义千问团队提供的大模型服务
- ONNX Runtime 团队提供的高性能推理引擎
- Ultralytics 团队的YOLOv8模型
- 所有开源项目的贡献者

## 🌟 Star History

如果这个项目对您有帮助，请给我们一个Star！⭐

---

**© 2025 图片分类后端系统. 保留所有权利.**

*让AI分类更智能，让API调用更经济*