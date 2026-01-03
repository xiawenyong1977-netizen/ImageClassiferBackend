# Systemd 服务配置说明

## 概述

本文档说明如何为 Image Classifier Backend 配置 systemd 服务，以便在生产环境中使用 systemd 管理服务生命周期。

## 自动配置（推荐）

使用 `scripts/deploy-versioned.sh` 部署脚本时，会自动检查并创建 systemd 服务配置文件。如果服务文件不存在，脚本会自动创建。

## 手动配置

如果需要手动配置 systemd 服务，请按照以下步骤操作：

### 1. 创建服务文件

创建文件 `/etc/systemd/system/image-classifier.service`：

```bash
sudo nano /etc/systemd/system/image-classifier.service
```

### 2. 服务文件内容

根据你的部署目录结构，使用以下配置：

#### 版本化部署（使用 `current` 符号链接）

```ini
[Unit]
Description=Image Classifier Backend API Service
Documentation=https://github.com/xiawenyong1977-netizen/ImageClassiferBackend
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/ICBackend/current
Environment="PATH=/opt/ICBackend/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
# 加载环境变量文件（如果存在）
EnvironmentFile=-/opt/ICBackend/.env
EnvironmentFile=-/opt/ICBackend/.env.secrets

# 使用 gunicorn 启动应用
ExecStart=/opt/ICBackend/venv/bin/gunicorn -c gunicorn_config.py app.main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# 资源限制
LimitNOFILE=65535
LimitNPROC=4096

# 安全设置
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/image-classifier /var/run/image-classifier.pid
NoNewPrivileges=true

# 重启策略
Restart=on-failure
RestartSec=10s
StartLimitInterval=300
StartLimitBurst=5

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=image-classifier

[Install]
WantedBy=multi-user.target
```

#### 传统部署（固定目录）

如果你的部署目录是固定的（例如 `/opt/ImageClassifierBackend`），使用以下配置：

```ini
[Unit]
Description=Image Classifier Backend API Service
Documentation=https://github.com/xiawenyong1977-netizen/ImageClassiferBackend
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/ImageClassifierBackend
Environment="PATH=/opt/ImageClassifierBackend/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=-/opt/ImageClassifierBackend/.env
EnvironmentFile=-/opt/ImageClassifierBackend/.env.secrets

ExecStart=/opt/ImageClassifierBackend/venv/bin/gunicorn -c gunicorn_config.py app.main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

LimitNOFILE=65535
LimitNPROC=4096

PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/image-classifier /var/run/image-classifier.pid
NoNewPrivileges=true

Restart=on-failure
RestartSec=10s
StartLimitInterval=300
StartLimitBurst=5

StandardOutput=journal
StandardError=journal
SyslogIdentifier=image-classifier

[Install]
WantedBy=multi-user.target
```

### 3. 创建日志目录

```bash
sudo mkdir -p /var/log/image-classifier
sudo chown -R root:root /var/log/image-classifier
```

### 4. 重新加载 systemd 配置

```bash
sudo systemctl daemon-reload
```

### 5. 启用服务（开机自启）

```bash
sudo systemctl enable image-classifier
```

### 6. 启动服务

```bash
sudo systemctl start image-classifier
```

### 7. 检查服务状态

```bash
sudo systemctl status image-classifier
```

## 配置说明

### 关键配置项

1. **WorkingDirectory**: 
   - 版本化部署：`/opt/ICBackend/current`（指向当前版本的符号链接）
   - 传统部署：`/opt/ImageClassifierBackend`（固定目录）

2. **ExecStart**: 
   - 使用 gunicorn 启动应用
   - 路径指向共享虚拟环境：`/opt/ICBackend/venv/bin/gunicorn`

3. **EnvironmentFile**: 
   - 使用 `-` 前缀表示文件不存在时不报错
   - 加载 `.env` 和 `.env.secrets` 文件

4. **Restart**: 
   - `on-failure`: 仅在失败时重启
   - `RestartSec=10s`: 重启前等待 10 秒
   - `StartLimitInterval=300`: 5 分钟内最多重启 5 次

5. **安全设置**:
   - `PrivateTmp=true`: 使用私有临时目录
   - `ProtectSystem=strict`: 保护系统目录
   - `NoNewPrivileges=true`: 禁止提升权限

## 常用命令

### 服务管理

```bash
# 启动服务
sudo systemctl start image-classifier

# 停止服务
sudo systemctl stop image-classifier

# 重启服务
sudo systemctl restart image-classifier

# 重新加载配置（不重启服务）
sudo systemctl reload image-classifier

# 查看服务状态
sudo systemctl status image-classifier

# 启用开机自启
sudo systemctl enable image-classifier

# 禁用开机自启
sudo systemctl disable image-classifier
```

### 日志查看

```bash
# 查看实时日志
sudo journalctl -u image-classifier -f

# 查看最近 100 行日志
sudo journalctl -u image-classifier -n 100

# 查看今天的日志
sudo journalctl -u image-classifier --since today

# 查看错误日志
sudo journalctl -u image-classifier -p err

# 查看应用日志文件（如果配置了文件日志）
tail -f /var/log/image-classifier/app.log
```

### 服务检查

```bash
# 检查服务是否运行
systemctl is-active image-classifier

# 检查服务是否启用
systemctl is-enabled image-classifier

# 检查服务是否失败
systemctl is-failed image-classifier
```

## 故障排查

### 服务启动失败

1. **检查服务状态**:
   ```bash
   sudo systemctl status image-classifier
   ```

2. **查看详细日志**:
   ```bash
   sudo journalctl -u image-classifier -n 50 --no-pager
   ```

3. **检查配置文件**:
   ```bash
   # 检查服务文件语法
   sudo systemctl cat image-classifier
   
   # 检查 gunicorn 配置
   cat /opt/ICBackend/current/gunicorn_config.py
   ```

4. **检查权限**:
   ```bash
   # 检查工作目录权限
   ls -la /opt/ICBackend/current
   
   # 检查虚拟环境权限
   ls -la /opt/ICBackend/venv/bin/gunicorn
   ```

5. **手动测试启动**:
   ```bash
   cd /opt/ICBackend/current
   /opt/ICBackend/venv/bin/gunicorn -c gunicorn_config.py app.main:app
   ```

### 常见问题

1. **服务无法启动 - 找不到 gunicorn**:
   - 检查虚拟环境路径是否正确
   - 确认虚拟环境已安装 gunicorn: `source /opt/ICBackend/venv/bin/activate && pip list | grep gunicorn`

2. **服务无法启动 - 找不到配置文件**:
   - 检查 `WorkingDirectory` 是否正确
   - 确认 `gunicorn_config.py` 文件存在

3. **服务启动后立即退出**:
   - 查看日志: `sudo journalctl -u image-classifier -n 50`
   - 检查数据库连接是否正常
   - 检查环境变量是否正确加载

4. **端口被占用**:
   ```bash
   # 检查端口占用
   sudo netstat -tlnp | grep 8000
   # 或
   sudo ss -tlnp | grep 8000
   ```

## 版本化部署的优势

使用版本化部署时，systemd 服务配置的优势：

1. **无需修改服务文件**: `WorkingDirectory` 指向 `current` 符号链接，版本切换时自动指向新版本
2. **快速回滚**: 只需切换符号链接，然后重启服务
3. **版本隔离**: 每个版本独立目录，互不影响

## 参考

- [Systemd Service 文档](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Gunicorn 部署文档](https://docs.gunicorn.org/en/stable/deploy.html)
- [项目部署文档](../部署方案总览.md)

