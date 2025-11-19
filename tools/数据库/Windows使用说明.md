# Windows环境下使用MySQL主从复制脚本

## 问题说明

在Windows PowerShell中无法直接运行bash脚本，因为Windows默认没有bash命令。

## 解决方案

### 方案1：直接在Linux服务器上运行（推荐）

这是最简单直接的方法，因为脚本本身就是为Linux服务器设计的。

```bash
# 1. 将脚本上传到Linux服务器（可以使用scp或直接在服务器上git clone）
scp -r tools/数据库 root@your-server:/root/mysql-replication/

# 2. SSH登录到服务器
ssh root@your-server

# 3. 进入目录并执行
cd /root/mysql-replication
chmod +x setup-firewall-for-replication.sh
chmod +x setup-mysql-replication.sh

# 4. 先配置防火墙
bash setup-firewall-for-replication.sh

# 5. 再配置主从复制
bash setup-mysql-replication.sh
```

### 方案2：使用WSL（Windows Subsystem for Linux）

如果已安装WSL，可以在WSL中运行：

```powershell
# 在PowerShell中启动WSL
wsl

# 进入项目目录（WSL中的路径）
cd /mnt/d/ImageClassifierBackend/tools/数据库

# 执行脚本
bash setup-firewall-for-replication.sh
bash setup-mysql-replication.sh
```

### 方案3：使用Git Bash

如果安装了Git for Windows，可以使用Git Bash：

1. 右键点击项目文件夹
2. 选择 "Git Bash Here"
3. 执行命令：
```bash
cd tools/数据库
bash setup-firewall-for-replication.sh
bash setup-mysql-replication.sh
```

### 方案4：使用SSH远程执行

如果可以从Windows直接SSH到服务器，可以远程执行：

```powershell
# 在PowerShell中使用SSH执行远程命令
ssh root@app "bash -s" < setup-firewall-for-replication.sh
ssh root@app "bash -s" < setup-mysql-replication.sh
```

但这种方式需要先修改脚本，因为脚本中使用了SSH命令。

## 推荐方案

**推荐使用方案1**：直接在Linux服务器上运行脚本，因为：
1. 脚本本身就是为Linux环境设计的
2. 不需要在Windows上安装额外工具
3. 执行环境与目标环境一致，避免兼容性问题

## 快速操作步骤

### 方法A：使用SCP上传脚本

```powershell
# 在PowerShell中，使用scp上传整个目录
scp -r tools/数据库 root@app:/root/
scp -r tools/数据库 root@web:/root/

# 然后SSH到服务器执行
ssh root@app
cd /root/数据库
bash setup-firewall-for-replication.sh
bash setup-mysql-replication.sh
```

### 方法B：直接在服务器上克隆项目

```powershell
# SSH到服务器
ssh root@app

# 如果服务器上有git，直接克隆
git clone <your-repo-url>
cd ImageClassifierBackend/tools/数据库
bash setup-firewall-for-replication.sh
bash setup-mysql-replication.sh
```

### 方法C：使用VS Code Remote SSH

如果使用VS Code，可以：
1. 安装 "Remote - SSH" 扩展
2. 连接到Linux服务器
3. 在服务器上直接打开项目目录
4. 在VS Code的终端中执行脚本

## 注意事项

1. 确保脚本有执行权限：`chmod +x *.sh`
2. 确保SSH证书已配置，可以无密码登录
3. 脚本需要在能够SSH连接到app和web服务器的环境中运行

