# MySQL用户和密码说明

## 问题：不记得MySQL root密码怎么办？

### 方法1：检查MySQL root是否有密码

```bash
# 在App服务器上测试
ssh root@app

# 尝试无密码连接
mysql -u root

# 如果成功，说明root没有密码
# 如果失败，说明root有密码，需要输入密码或重置
```

### 方法2：使用sudo连接（Ubuntu/Debian系统）

如果MySQL使用socket认证，可以使用sudo：

```bash
# 在App服务器上
ssh root@app
sudo mysql

# 在MySQL中查看用户信息
SELECT user, host, plugin FROM mysql.user WHERE user='root';
```

### 方法3：重置MySQL root密码

如果忘记了密码，可以重置：

```bash
# 1. 停止MySQL服务
sudo systemctl stop mysql
# 或
sudo systemctl stop mysqld

# 2. 以安全模式启动MySQL（跳过权限检查）
sudo mysqld_safe --skip-grant-tables &

# 3. 连接MySQL（无需密码）
mysql -u root

# 4. 重置密码
ALTER USER 'root'@'localhost' IDENTIFIED BY '新密码';
FLUSH PRIVILEGES;
exit;

# 5. 重启MySQL服务
sudo systemctl restart mysql
```

## 使用非root用户配置主从复制

### 方案1：使用现有的MySQL管理员用户

如果您的MySQL有其他的管理员用户（不是root），可以修改脚本配置：

```bash
# 编辑脚本
vim setup-mysql-replication.sh

# 修改第19行
MYSQL_ADMIN_USER="your_admin_user"  # 改为您的MySQL管理员用户名
```

### 方案2：创建一个新的MySQL管理员用户

如果您想创建一个专门用于主从复制配置的用户：

```bash
# 1. 使用root或sudo连接MySQL
mysql -u root
# 或
sudo mysql

# 2. 创建新用户（替换 'your_password' 为实际密码）
CREATE USER 'replication_admin'@'localhost' IDENTIFIED BY 'your_password';
CREATE USER 'replication_admin'@'%' IDENTIFIED BY 'your_password';

# 3. 授予必要的权限
GRANT CREATE USER ON *.* TO 'replication_admin'@'localhost';
GRANT CREATE USER ON *.* TO 'replication_admin'@'%';
GRANT REPLICATION SLAVE ON *.* TO 'replication_admin'@'localhost';
GRANT REPLICATION SLAVE ON *.* TO 'replication_admin'@'%';
GRANT RELOAD ON *.* TO 'replication_admin'@'localhost';
GRANT RELOAD ON *.* TO 'replication_admin'@'%';
GRANT PROCESS ON *.* TO 'replication_admin'@'localhost';
GRANT PROCESS ON *.* TO 'replication_admin'@'%';
GRANT SELECT ON *.* TO 'replication_admin'@'localhost';
GRANT SELECT ON *.* TO 'replication_admin'@'%';

# 4. 刷新权限
FLUSH PRIVILEGES;

# 5. 退出
exit;

# 6. 测试新用户
mysql -u replication_admin -p
# 输入密码，确认可以连接

# 7. 修改脚本配置
vim setup-mysql-replication.sh
# 修改第19行
MYSQL_ADMIN_USER="replication_admin"
```

### 方案3：使用空密码（不推荐，仅用于测试）

如果MySQL root用户没有密码，在脚本提示输入密码时直接按回车即可。

## 脚本配置说明

脚本支持以下配置（在脚本开头）：

```bash
# MySQL配置
MYSQL_ADMIN_USER="root"     # MySQL管理员用户名（默认root）
MYSQL_ADMIN_PASSWORD=""     # MySQL管理员密码（为空时脚本会提示输入）
```

### 使用示例

1. **使用root用户，有密码**：
   ```bash
   # 保持默认配置，运行脚本时会提示输入密码
   ./setup-mysql-replication.sh
   ```

2. **使用root用户，无密码**：
   ```bash
   # 保持默认配置，运行脚本时直接按回车
   ./setup-mysql-replication.sh
   # 提示输入密码时，直接按回车
   ```

3. **使用其他用户**：
   ```bash
   # 编辑脚本，修改MYSQL_ADMIN_USER
   vim setup-mysql-replication.sh
   # 修改为：MYSQL_ADMIN_USER="your_user"
   
   # 运行脚本
   ./setup-mysql-replication.sh
   ```

## 权限要求

用于配置主从复制的MySQL用户需要以下权限：

- `CREATE USER` - 创建复制用户
- `REPLICATION SLAVE` - 配置主从复制
- `RELOAD` - 重新加载配置
- `PROCESS` - 查看进程状态
- `SELECT` - 查询数据库状态

root用户默认拥有所有权限，可以直接使用。

## 常见问题

### Q: 如何检查MySQL用户是否有足够权限？

```bash
mysql -u root -p
SHOW GRANTS FOR 'your_user'@'localhost';
```

### Q: 如果两个服务器的MySQL root密码不同怎么办？

脚本假设两个服务器使用相同的MySQL管理员密码。如果不同，需要：

1. 统一两个服务器的MySQL root密码
2. 或者分别配置主库和从库（使用手动配置方式）

### Q: MySQL 8.0使用caching_sha2_password认证怎么办？

如果遇到认证问题，可以修改认证方式：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_password';
FLUSH PRIVILEGES;
```

## 推荐做法

1. **生产环境**：使用专门的MySQL管理员用户，不要使用root
2. **测试环境**：可以使用root用户，但建议设置强密码
3. **安全考虑**：定期更换密码，限制管理员用户的访问来源

