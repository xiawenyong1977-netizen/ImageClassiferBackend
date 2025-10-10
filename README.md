# 图片分类后端系统

基于大模型的图片分类服务，支持8种预定义分类类别，具有智能缓存和成本优化功能。

## 🎯 核心特性

- ✅ **8种预定义分类**：社交活动、宠物萌照、单人照片、美食记录、旅行风景、手机截图、证件照、其它
- ✅ **智能缓存**：SHA-256哈希去重，避免重复调用大模型
- ✅ **带宽优化**：支持哈希预查询，节省90%上传带宽
- ✅ **成本优化**：全局缓存机制，大幅降低API调用成本
- ✅ **统计分析**：完整的请求日志和统计功能
- ✅ **隐私保护**：不存储原始图片

## 📋 系统要求

- Python 3.10+
- MySQL 8.0+
- 大模型API（OpenAI GPT-4 Vision 或 Claude Vision）

## 🚀 快速开始

### 1. 安装依赖

```bash
# 激活conda环境
conda activate wechat-classifier

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑.env文件，配置数据库和大模型API
# 必须配置：
# - MYSQL_*: MySQL数据库连接信息
# - LLM_API_KEY: 大模型API密钥
```

### 3. 初始化数据库

```bash
# 使用MySQL客户端执行初始化脚本
mysql -u root -p < sql/init.sql
```

### 4. 启动服务

**开发环境：**

```bash
# 使用Uvicorn启动（支持热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**生产环境：**

```bash
# 使用Gunicorn启动（多进程）
gunicorn -c gunicorn_config.py app.main:app
```

### 5. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/api/v1/health

## 📚 API接口

### 1. 检查缓存

```http
POST /api/v1/classify/check-cache
Content-Type: application/json

{
  "image_hash": "abc123...",
  "user_id": "device_uuid_xxx"
}
```

### 2. 图片分类

```http
POST /api/v1/classify
Content-Type: multipart/form-data

image: <File>
image_hash: <String> (可选)
X-User-ID: <String> (Header, 可选)
```

### 3. 统计接口

- `GET /api/v1/stats/today` - 今日统计
- `GET /api/v1/stats/cache-efficiency` - 缓存效率
- `GET /api/v1/stats/category-distribution` - 分类分布

### 4. 健康检查

```http
GET /api/v1/health
```

## 🗂️ 项目结构

```
ImageClassifierBackend/
├── app/
│   ├── api/                    # API路由
│   │   ├── classify.py         # 分类接口
│   │   ├── stats.py            # 统计接口
│   │   └── health.py           # 健康检查
│   ├── services/               # 服务层
│   │   ├── classifier.py       # 分类服务
│   │   ├── cache_service.py    # 缓存服务
│   │   ├── model_client.py     # 大模型客户端
│   │   └── stats_service.py    # 统计服务
│   ├── models/                 # 数据模型
│   │   └── schemas.py          # Pydantic模型
│   ├── utils/                  # 工具类
│   │   ├── id_generator.py     # ID生成器
│   │   ├── hash_utils.py       # 哈希工具
│   │   └── image_utils.py      # 图片工具
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   └── main.py                 # 应用入口
├── sql/
│   └── init.sql                # 数据库初始化脚本
├── requirements.txt            # Python依赖
├── gunicorn_config.py          # Gunicorn配置
├── env.example                 # 环境变量模板
├── DESIGN.md                   # 详细设计文档
└── README.md                   # 本文件
```

## 🔧 配置说明

主要配置项（.env文件）：

```ini
# MySQL数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=image_classifier

# 大模型API
LLM_PROVIDER=openai              # openai / claude
LLM_API_KEY=sk-your-api-key
LLM_MODEL=gpt-4-vision-preview

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
MAX_IMAGE_SIZE_MB=10
```

## 📊 8种分类类别

| 类别Key | 中文名称 | 说明 |
|---------|---------|------|
| `social_activities` | 社交活动 | 聚会、合影等 |
| `pets` | 宠物萌照 | 猫、狗等宠物 |
| `single_person` | 单人照片 | 个人照、自拍 |
| `foods` | 美食记录 | 美食、餐饮 |
| `travel_scenery` | 旅行风景 | 旅游、风景 |
| `screenshot` | 手机截图 | 屏幕截图 |
| `idcard` | 证件照 | 身份证等证件 |
| `other` | 其它 | 其他类型 |

## 💰 成本优化

通过全局缓存机制，大幅降低成本：

```
示例：
- 无缓存：10000次请求 × 0.01元 = 100元/天
- 有缓存(30%命中)：7000次 × 0.01元 = 70元/天
- 月节省：900元
```

## 🔍 监控与调试

### 查看日志

```bash
# 实时日志
tail -f /var/log/image-classifier/error.log

# Gunicorn访问日志
tail -f /var/log/image-classifier/access.log
```

### 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

### 查看统计

```bash
# 今日统计
curl http://localhost:8000/api/v1/stats/today

# 缓存效率
curl http://localhost:8000/api/v1/stats/cache-efficiency
```

## 📦 生产环境部署

详见 [DESIGN.md](DESIGN.md) 中的"Web容器实现与部署方案"章节。

### 使用Docker

```bash
docker-compose up -d
```

### 使用Systemd

```bash
# 配置服务
sudo cp image-classifier.service /etc/systemd/system/

# 启动服务
sudo systemctl start image-classifier
sudo systemctl enable image-classifier
```

## 📖 详细文档

完整的系统设计文档请查看：[DESIGN.md](DESIGN.md)

包含：
- 系统架构设计
- 接口详细说明
- 数据库表结构
- 部署方案
- 性能优化建议

## 🤝 开发指南

### 添加新的分类类别

1. 修改 `app/config.py` 中的 `CATEGORIES` 列表
2. 修改 `app/services/model_client.py` 中的提示词
3. 更新数据库（如需要）
4. 更新客户端的分类映射表

### 运行测试

```bash
pytest tests/
```

## 📝 版本历史

- v1.0.0 (2025-10-10) - 初始版本
  - 支持8种预定义分类
  - 实现智能缓存机制
  - 带宽优化和成本优化

## 📄 许可证

本项目供内部使用。

## 👥 团队

ImageClassifier Team

---

**需要帮助？** 查看 [DESIGN.md](DESIGN.md) 或联系开发团队。

