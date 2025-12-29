# 使用Docker运行MySQL测试数据库

## 前提条件

### 1. 安装Docker Desktop（如果还没有安装）

**Windows:**
- 下载地址：https://www.docker.com/products/docker-desktop
- 安装后启动Docker Desktop
- 确保Docker Desktop正在运行（系统托盘会有Docker图标）

**验证安装：**
```powershell
docker --version
docker-compose --version
```

## 快速开始

### 方式1：使用启动脚本（推荐）

```powershell
# 启动MySQL容器
.\tests\docker-mysql-start.ps1

# 停止MySQL容器
.\tests\docker-mysql-stop.ps1
```

### 方式2：使用Docker Compose命令

```powershell
# 启动MySQL容器
docker-compose -f docker-compose.test.yml up -d

# 查看容器状态
docker ps

# 停止容器
docker-compose -f docker-compose.test.yml down

# 停止并删除数据卷（清理所有数据）
docker-compose -f docker-compose.test.yml down -v
```

## 数据库连接信息

启动容器后，使用以下信息连接：

```
Host:     localhost
Port:     3307
User:     root
Password: test_password
Database: image_classifier_test
```

## 环境变量配置

确保 `.env` 文件中包含以下配置：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=test_password
MYSQL_DATABASE=image_classifier_test
```

## 运行测试

启动MySQL容器后，运行测试：

```powershell
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_health.py -v
python -m pytest tests/test_location_v2.py -v
```

## 常见问题

### 1. 端口冲突

如果3307端口被占用，可以修改 `docker-compose.test.yml` 中的端口映射：

```yaml
ports:
  - "3308:3306"  # 改为其他端口，如3308
```

同时更新 `.env` 文件中的 `MYSQL_PORT=3308`

### 2. 容器无法启动

检查Docker Desktop是否正在运行：
- Windows：查看系统托盘是否有Docker图标
- 确保Docker Desktop已完全启动

### 3. 数据库连接失败

等待几秒钟让数据库完全启动，然后重试。

### 4. 清理所有数据

如果想重新开始（删除所有测试数据）：

```powershell
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
```

## 注意事项

- 容器使用端口 **3307**（避免与本地MySQL的3306冲突）
- 数据会持久化在Docker卷中，停止容器不会丢失数据
- 使用 `-v` 参数会删除所有数据卷，请谨慎使用



