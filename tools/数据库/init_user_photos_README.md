# 用户照片关系表初始化说明

## 表说明

`user_photos` 表用于v2版本分类接口，记录用户分类的照片关系。

### 表结构

- `user_id`: 用户ID/设备ID
- `image_hash`: 图片SHA-256哈希（后端主要使用）
- `image_uri`: 图片URI（客户端传入，用于客户端查询和对账）
- `classify_count`: 该用户分类这张照片的次数
- `first_seen_at`: 首次分类时间
- `last_seen_at`: 最后分类时间

### 索引

- `uk_user_image`: 用户和图片的唯一组合索引
- `idx_user_id`: 用户ID索引
- `idx_image_hash`: 图片哈希索引
- `idx_image_uri`: 图片URI索引（用于客户端查询）
- `idx_last_seen_at`: 最后分类时间索引

## 初始化方法

### 方法1：使用初始化脚本（推荐）

#### Linux服务器：

```bash
# 1. 进入数据库工具目录
cd tools/数据库

# 2. 设置执行权限（如果需要）
chmod +x init_user_photos.sh

# 3. 设置环境变量（可选）
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=image_classifier

# 4. 执行初始化脚本
bash init_user_photos.sh
```

#### Windows PowerShell：

```powershell
# 1. 进入数据库工具目录
cd tools\数据库

# 2. 设置环境变量（可选）
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "your_password"
$env:MYSQL_DATABASE = "image_classifier"

# 3. 执行初始化脚本
.\init_user_photos.ps1
```

### 方法2：直接执行SQL脚本

#### Linux/Mac：

```bash
cd tools/数据库
mysql -h localhost -u root -p image_classifier < create_user_photos.sql
```

#### Windows PowerShell：

```powershell
cd tools\数据库
Get-Content create_user_photos.sql | mysql -h localhost -u root -p image_classifier
```

### 方法3：在MySQL客户端中执行

```sql
-- 连接到MySQL
mysql -h localhost -u root -p

-- 选择数据库
USE image_classifier;

-- 执行SQL文件
SOURCE tools/数据库/create_user_photos.sql;
```

## 验证表是否创建成功

```sql
-- 查看表结构
DESCRIBE user_photos;

-- 查看表信息
SHOW CREATE TABLE user_photos;

-- 查看表是否存在
SHOW TABLES LIKE 'user_photos';
```

## 注意事项

1. **数据库权限**：确保MySQL用户有CREATE TABLE权限
2. **数据库名称**：默认使用 `image_classifier`，如果不同请修改环境变量或SQL脚本
3. **主从复制**：如果配置了主从复制，需要在主库执行，会自动同步到从库
4. **表已存在**：如果表已存在，脚本不会报错（使用了 `CREATE TABLE IF NOT EXISTS`）

## 回滚（删除表）

如果需要删除表（谨慎操作）：

```sql
USE image_classifier;
DROP TABLE IF EXISTS user_photos;
```

## 相关文件

- `create_user_photos.sql`: SQL创建脚本
- `init_user_photos.sh`: Linux初始化脚本
- `init_user_photos.ps1`: Windows PowerShell初始化脚本

