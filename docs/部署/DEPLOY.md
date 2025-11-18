# 阿里云轻量应用服务器部署指南

## 📋 部署准备清单

### 服务器要求
- **操作系统**：Ubuntu 20.04/22.04 或 CentOS 7/8
- **配置**：建议 2核4GB 以上
- **网络**：公网IP，开放端口8000（或80/443）

### 需要准备的信息
- [ ] 服务器公网IP
- [ ] SSH登录密码或密钥
- [ ] MySQL密码
- [ ] 大模型API密钥（OpenAI或Claude）

---

## 🚀 部署步骤

### 步骤1：连接到服务器

**Windows用户（PowerShell）：**
```powershell
# 使用SSH连接
ssh root@你的服务器IP

# 如果使用密钥
ssh -i "你的密钥.pem" root@你的服务器IP
```

**提示**：首次连接会要求确认指纹，输入 `yes`

---

### 步骤2：安装基础环境

#### 2.1 更新系统（Ubuntu）

```bash
# 更新软件包列表
sudo apt update && sudo apt upgrade -y

# 安装必要工具
sudo apt install -y git curl wget vim build-essential
```

#### 2.2 安装Python 3.10

```bash
# 添加deadsnakes PPA（Ubuntu）
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 安装Python 3.10
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 设置Python 3.10为默认版本
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# 安装pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

# 验证安装
python3 --version  # 应显示 Python 3.10.x
pip3 --version
```

#### 2.3 安装MySQL

```bash
# 安装MySQL 8.0
sudo apt install -y mysql-server

# 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql

# 安全配置（重要！）
sudo mysql_secure_installation
```

**MySQL安全配置提示**：
1. 设置root密码（记住这个密码！）
2. 移除匿名用户：Y
3. 禁止root远程登录：Y
4. 移除test数据库：Y
5. 重新加载权限表：Y

#### 2.4 配置MySQL

```bash
# 登录MySQL
sudo mysql -u root -p

# 在MySQL命令行中执行：
CREATE DATABASE image_classifier DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'classifier'@'localhost' IDENTIFIED BY '设置一个强密码';
GRANT ALL PRIVILEGES ON image_classifier.* TO 'classifier'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

### 步骤3：上传代码到服务器

#### 方案1：使用Git（推荐）

**在本地：**
```bash
# 如果还没有Git仓库，先创建
cd d:\ImageClassifierBackend
git init
git add .
git commit -m "Initial commit"

# 推送到GitHub/Gitee（需要先创建仓库）
git remote add origin https://github.com/你的用户名/ImageClassifierBackend.git
git push -u origin main
```

**在服务器上：**
```bash
# 克隆代码
cd /opt
sudo git clone https://github.com/你的用户名/ImageClassifierBackend.git
cd ImageClassifierBackend

# 设置权限
sudo chown -R $USER:$USER /opt/ImageClassifierBackend
```

#### 方案2：使用SCP直接上传

**在本地（PowerShell）：**
```powershell
# 打包代码
cd d:\ImageClassifierBackend
tar -czf project.tar.gz --exclude='.git' --exclude='__pycache__' .

# 上传到服务器
scp project.tar.gz root@你的服务器IP:/opt/

# 在服务器上解压
ssh root@你的服务器IP
cd /opt
mkdir ImageClassifierBackend
tar -xzf project.tar.gz -C ImageClassifierBackend
cd ImageClassifierBackend
```

#### 方案3：使用WinSCP（GUI工具）

1. 下载WinSCP：https://winscp.net/
2. 连接到服务器
3. 将整个项目文件夹拖拽到 `/opt/ImageClassifierBackend`

---

### 步骤4：配置Python环境

```bash
cd /opt/ImageClassifierBackend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 验证安装
pip list
```

---

### 步骤5：配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑配置文件
vim .env
# 或使用nano编辑器
nano .env
```

**配置内容（.env）：**
```ini
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=classifier
MYSQL_PASSWORD=你在步骤2.4设置的密码
MYSQL_DATABASE=image_classifier

# 大模型配置
LLM_PROVIDER=openai
LLM_API_KEY=sk-你的OpenAI密钥
LLM_MODEL=gpt-4-vision-preview

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
APP_ENV=production

# 图片配置
MAX_IMAGE_SIZE_MB=10

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/image-classifier/app.log
```

**保存并退出**：
- vim: 按 `ESC`，输入 `:wq`，回车
- nano: 按 `Ctrl+O`，回车，`Ctrl+X`

---

### 步骤6：初始化数据库

```bash
# 执行初始化脚本
mysql -u classifier -p image_classifier < sql/init.sql

# 输入密码后，应该看到表创建成功的消息

# 验证表是否创建
mysql -u classifier -p -e "USE image_classifier; SHOW TABLES;"
```

应该看到两张表：
- `image_classification_cache`
- `request_log`

---

### 步骤7：配置防火墙

```bash
# 检查防火墙状态
sudo ufw status

# 如果防火墙未启用，启用它
sudo ufw enable

# 开放SSH端口（重要！否则会断开连接）
sudo ufw allow 22/tcp

# 开放应用端口
sudo ufw allow 8000/tcp

# 如果要用80/443端口（需要Nginx）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 重新加载防火墙
sudo ufw reload

# 查看状态
sudo ufw status
```

**⚠️ 重要**：在阿里云控制台也要开放端口！
1. 登录阿里云控制台
2. 找到你的轻量应用服务器
3. 进入"防火墙"设置
4. 添加规则：
   - 端口：8000
   - 协议：TCP
   - 策略：允许

---

### 步骤8：创建日志目录

```bash
# 创建日志目录
sudo mkdir -p /var/log/image-classifier

# 设置权限
sudo chown -R $USER:$USER /var/log/image-classifier
```

---

### 步骤9：测试运行

```bash
cd /opt/ImageClassifierBackend

# 激活虚拟环境
source venv/bin/activate

# 测试启动（前台运行）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**看到以下信息表示成功**：
```
INFO:     Started server process
INFO:     Waiting for application startup.
图片分类后端服务启动中...
数据库连接成功
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**测试访问**：
- 在浏览器打开：`http://你的服务器IP:8000/docs`
- 应该能看到API文档页面

**停止测试**：按 `Ctrl+C`

---

### 步骤10：配置Systemd服务（后台运行）

#### 10.1 创建服务文件

```bash
sudo vim /etc/systemd/system/image-classifier.service
```

**内容：**
```ini
[Unit]
Description=Image Classifier API Service
After=network.target mysql.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/ImageClassifierBackend
Environment="PATH=/opt/ImageClassifierBackend/venv/bin"
ExecStart=/opt/ImageClassifierBackend/venv/bin/gunicorn -c gunicorn_config.py app.main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

#### 10.2 启动服务

```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start image-classifier

# 查看状态
sudo systemctl status image-classifier

# 设置开机自启
sudo systemctl enable image-classifier

# 查看日志
sudo journalctl -u image-classifier -f
```

---

### 步骤11：验证部署

#### 11.1 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

应该返回：
```json
{
  "status": "healthy",
  "database": "connected",
  "model_api": "available"
}
```

#### 11.2 测试分类接口

```bash
# 准备一张测试图片
curl -X POST "http://你的服务器IP:8000/api/v1/classify" \
  -H "accept: application/json" \
  -F "image=@test.jpg"
```

#### 11.3 查看统计

```bash
curl http://你的服务器IP:8000/api/v1/stats/today
```

---

## 🔧 常用运维命令

### 服务管理

```bash
# 启动服务
sudo systemctl start image-classifier

# 停止服务
sudo systemctl stop image-classifier

# 重启服务
sudo systemctl restart image-classifier

# 查看状态
sudo systemctl status image-classifier

# 查看实时日志
sudo journalctl -u image-classifier -f

# 查看最近100行日志
sudo journalctl -u image-classifier -n 100
```

### 代码更新

```bash
# 停止服务
sudo systemctl stop image-classifier

# 拉取最新代码
cd /opt/ImageClassifierBackend
git pull

# 更新依赖（如果requirements.txt有变化）
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo systemctl start image-classifier
```

### 数据库维护

```bash
# 查看缓存统计
mysql -u classifier -p -e "
USE image_classifier;
SELECT COUNT(*) as total_cached_images, SUM(hit_count) as total_hits 
FROM image_classification_cache;
"

# 查看今日请求数
mysql -u classifier -p -e "
USE image_classifier;
SELECT COUNT(*) as today_requests 
FROM request_log 
WHERE created_date = CURDATE();
"

# 清理30天前的日志
mysql -u classifier -p -e "
USE image_classifier;
DELETE FROM request_log 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
"
```

---

## 🔍 故障排查

### 问题1：服务无法启动

```bash
# 查看详细错误日志
sudo journalctl -u image-classifier -n 50 --no-pager

# 检查端口占用
sudo netstat -tlnp | grep 8000

# 手动测试
cd /opt/ImageClassifierBackend
source venv/bin/activate
python -c "from app.main import app"
```

### 问题2：数据库连接失败

```bash
# 测试MySQL连接
mysql -u classifier -p -h localhost image_classifier

# 检查MySQL服务
sudo systemctl status mysql

# 查看MySQL错误日志
sudo tail -f /var/log/mysql/error.log
```

### 问题3：API调用失败

```bash
# 检查防火墙
sudo ufw status

# 测试端口连通性
curl http://localhost:8000/api/v1/health

# 从外网测试
curl http://你的服务器IP:8000/api/v1/health
```

### 问题4：大模型API调用失败

```bash
# 检查API密钥配置
cd /opt/ImageClassifierBackend
cat .env | grep LLM_API_KEY

# 测试网络连接
curl -I https://api.openai.com

# 查看应用日志
tail -f /var/log/image-classifier/app.log
```

---

## 🔒 安全加固（可选但推荐）

### 1. 配置Nginx反向代理

```bash
# 安装Nginx
sudo apt install -y nginx

# 创建配置文件
sudo vim /etc/nginx/sites-available/image-classifier
```

**Nginx配置：**
```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**启用配置：**
```bash
sudo ln -s /etc/nginx/sites-available/image-classifier /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. 配置HTTPS（使用Let's Encrypt）

```bash
# 安装certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d 你的域名

# 证书会自动续期
sudo certbot renew --dry-run
```

### 3. 限制SSH访问

```bash
# 修改SSH配置
sudo vim /etc/ssh/sshd_config

# 修改以下内容：
# Port 2222  # 改变SSH端口
# PermitRootLogin no  # 禁止root登录
# PasswordAuthentication no  # 仅使用密钥登录

# 重启SSH
sudo systemctl restart sshd
```

---

## 📊 监控与日志

### 安装监控工具

```bash
# 安装htop（进程监控）
sudo apt install -y htop

# 安装ncdu（磁盘使用分析）
sudo apt install -y ncdu

# 查看系统资源
htop

# 查看磁盘使用
ncdu /opt
```

### 设置日志轮转

```bash
# 创建logrotate配置
sudo vim /etc/logrotate.d/image-classifier
```

**内容：**
```
/var/log/image-classifier/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        systemctl reload image-classifier > /dev/null 2>&1 || true
    endscript
}
```

---

## ✅ 部署检查清单

完成后请检查：

- [ ] Python 3.10安装成功
- [ ] MySQL服务运行正常
- [ ] 数据库和表创建成功
- [ ] 代码上传到服务器
- [ ] Python依赖安装完成
- [ ] 环境变量配置正确
- [ ] 防火墙端口已开放
- [ ] Systemd服务配置并启动
- [ ] 健康检查接口返回正常
- [ ] 可以从外网访问API文档
- [ ] 测试分类接口工作正常

---

## 🎉 部署完成！

现在您可以：

1. **访问API文档**：`http://你的服务器IP:8000/docs`
2. **测试接口**：使用Postman或curl
3. **查看统计**：`http://你的服务器IP:8000/api/v1/stats/today`

**重要链接**：
- API文档：http://你的服务器IP:8000/docs
- 健康检查：http://你的服务器IP:8000/api/v1/health
- 服务器日志：`sudo journalctl -u image-classifier -f`

---

## 📞 获取帮助

遇到问题？

1. 查看日志：`sudo journalctl -u image-classifier -f`
2. 检查健康状态：`curl http://localhost:8000/api/v1/health`
3. 参考故障排查章节
4. 查看DESIGN.md了解更多细节

---

**祝您部署顺利！🚀**

