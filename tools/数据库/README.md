# MySQL数据库工具

## 主从复制配置

### 快速开始

```bash
# 1. 进入数据库工具目录
cd tools/数据库

# 2. 配置防火墙（重要！必须先执行）
chmod +x setup-firewall-for-replication.sh
bash setup-firewall-for-replication.sh

# 3. 确保脚本有执行权限
chmod +x setup-mysql-replication.sh

# 4. 执行自动化配置脚本
bash setup-mysql-replication.sh
```

### 脚本说明

- **setup-firewall-for-replication.sh**: 防火墙配置脚本，在主库开放3306端口（**必须先执行**）
- **setup-mysql-replication.sh**: 自动化配置脚本，一键完成主从复制配置
- **setup-mysql-master.sh**: 主库配置脚本（手动配置时使用）
- **setup-mysql-slave.sh**: 从库配置脚本（手动配置时使用）

### 配置要求

- 主库：root@app 服务器
- 从库：root@web 服务器
- SSH证书已配置，可以无密码登录
- 两个服务器的MySQL root密码相同（或已知）
- **防火墙已配置，主库3306端口已开放**（使用 `setup-firewall-for-replication.sh` 配置）

### 重要提示

⚠️ **主从复制需要从库能够连接到主库的MySQL端口（3306），因此必须：**
1. 在主库开放3306端口（使用防火墙配置脚本）
2. 确保MySQL监听外部连接（bind-address = 0.0.0.0）
3. 如果使用云服务器，还需要在云控制台配置安全组规则

### Windows用户注意

⚠️ **Windows PowerShell无法直接运行bash脚本！**

如果您在Windows环境下，请查看 [Windows使用说明.md](./Windows使用说明.md) 了解如何在Windows上使用这些脚本。

**推荐方式**：直接在Linux服务器上运行脚本（最简单可靠）。

### 详细说明

- [主从复制配置说明.md](./主从复制配置说明.md) - 详细配置步骤和故障排查指南
- [Windows使用说明.md](./Windows使用说明.md) - Windows环境下的使用方法
- [MySQL用户和密码说明.md](./MySQL用户和密码说明.md) - MySQL用户和密码相关问题解答

