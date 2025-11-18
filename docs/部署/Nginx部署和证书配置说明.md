# Nginx部署和Let's Encrypt证书配置说明

## 📋 当前状态

### ✅ 已完成
1. Nginx 已安装并启动
2. Nginx 配置文件已创建：`/etc/nginx/conf.d/api-aifuture.conf`
3. 防火墙端口已开放（80, 443）
4. certbot 已安装

### ⚠️ 待解决问题

**证书获取失败原因：**
Let's Encrypt 无法访问服务器的 80 端口进行验证，可能原因：
1. **DNS解析问题**：`api.aifuture.net.cn` 未解析到服务器IP `47.98.167.63`
2. **云服务器安全组**：阿里云安全组未开放 80 端口（最可能）
3. **网络问题**：服务器无法从外网访问

## 🔧 解决方案

### 方案1：检查并配置云服务器安全组（推荐）

**阿里云安全组配置：**
1. 登录阿里云控制台
2. 进入 ECS 实例管理
3. 找到对应的服务器实例
4. 点击"安全组" → "配置规则"
5. 添加入站规则：
   - **端口范围**：80/80
   - **协议类型**：TCP
   - **授权对象**：0.0.0.0/0
   - **描述**：HTTP for Let's Encrypt
6. 添加入站规则：
   - **端口范围**：443/443
   - **协议类型**：TCP
   - **授权对象**：0.0.0.0/0
   - **描述**：HTTPS

### 方案2：检查DNS解析

确保 `api.aifuture.net.cn` 的A记录指向服务器IP `47.98.167.63`：

```bash
# 检查DNS解析
nslookup api.aifuture.net.cn
# 或
dig api.aifuture.net.cn

# 应该返回：47.98.167.63
```

### 方案3：使用standalone模式（临时方案）

如果安全组暂时无法配置，可以使用standalone模式（需要临时停止Nginx）：

```bash
# 1. 临时停止Nginx
systemctl stop nginx

# 2. 使用standalone模式获取证书
certbot certonly --standalone -d api.aifuture.net.cn --non-interactive --agree-tos --email admin@aifuture.net.cn

# 3. 启动Nginx
systemctl start nginx

# 4. 手动配置HTTPS（见下方）
```

## 🚀 重新获取证书

### 方法1：自动配置（推荐，需要安全组开放80端口）

```bash
# 确保DNS和安全组配置正确后，执行：
certbot --nginx -d api.aifuture.net.cn --non-interactive --agree-tos --email admin@aifuture.net.cn --redirect
```

### 方法2：standalone模式（临时方案）

```bash
# 1. 停止Nginx
systemctl stop nginx

# 2. 获取证书
certbot certonly --standalone -d api.aifuture.net.cn --non-interactive --agree-tos --email admin@aifuture.net.cn

# 3. 启动Nginx
systemctl start nginx

# 4. 手动配置HTTPS（见下方手动配置部分）
```

## 📝 手动配置HTTPS（如果使用standalone模式）

如果使用standalone模式获取证书，需要手动配置Nginx的HTTPS：

编辑 `/etc/nginx/conf.d/api-aifuture.conf`：

```nginx
# 上游FastAPI服务
upstream fastapi_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP服务器（重定向到HTTPS）
server {
    listen 80;
    server_name api.aifuture.net.cn;
    
    # 重定向所有HTTP请求到HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS服务器
server {
    listen 443 ssl http2;
    server_name api.aifuture.net.cn;

    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/api.aifuture.net.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.aifuture.net.cn/privkey.pem;
    
    # SSL配置（推荐配置）
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 日志
    access_log /var/log/nginx/api-aifuture-access.log;
    error_log /var/log/nginx/api-aifuture-error.log;

    # 客户端上传大小限制
    client_max_body_size 50M;

    # 代理到FastAPI
    location / {
        proxy_pass http://fastapi_backend;
        proxy_http_version 1.1;
        
        # 请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # WebSocket支持
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件服务（images目录）
    location /images/ {
        alias /opt/ImageClassifierBackend/app/images/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        
        # 如果文件不存在，回退到FastAPI
        try_files $uri $uri/ @fastapi;
    }
    
    location @fastapi {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

然后测试并重载配置：

```bash
# 测试配置
nginx -t

# 重载配置
systemctl reload nginx
```

## 🔄 配置证书自动续期

Let's Encrypt 证书有效期 90 天，需要定期续期。certbot 会自动创建 systemd timer，通常无需手动配置。

### 检查自动续期配置

```bash
# 检查certbot timer状态
systemctl status certbot.timer

# 查看续期任务
systemctl list-timers | grep certbot

# 测试续期（不实际续期）
certbot renew --dry-run
```

### 手动续期（如果需要）

```bash
# 手动续期所有证书
certbot renew

# 续期后重载Nginx
systemctl reload nginx
```

### 确保自动续期正常工作

certbot 安装时会自动创建 systemd timer，通常位于：
- `/etc/systemd/system/certbot.timer`
- `/etc/systemd/system/certbot.service`

验证：

```bash
# 检查timer是否启用
systemctl is-enabled certbot.timer

# 如果未启用，启用它
systemctl enable certbot.timer
systemctl start certbot.timer
```

## ✅ 验证配置

### 1. 检查证书

```bash
# 查看证书信息
certbot certificates

# 检查证书有效期
openssl x509 -in /etc/letsencrypt/live/api.aifuture.net.cn/cert.pem -noout -dates
```

### 2. 测试HTTPS访问

```bash
# 从服务器本地测试
curl -I https://api.aifuture.net.cn/

# 从外网测试（需要DNS和安全组配置正确）
curl -I https://api.aifuture.net.cn/
```

### 3. 测试反向代理

```bash
# 测试API端点
curl https://api.aifuture.net.cn/docs
curl https://api.aifuture.net.cn/api/v1/health
```

### 4. 测试HTTP到HTTPS重定向

```bash
# 应该自动重定向到HTTPS
curl -I http://api.aifuture.net.cn/
# 应该返回 301 重定向
```

## 📊 当前配置状态

### Nginx配置位置
- 主配置：`/etc/nginx/nginx.conf`
- 站点配置：`/etc/nginx/conf.d/api-aifuture.conf`

### 证书位置（获取成功后）
- 证书：`/etc/letsencrypt/live/api.aifuture.net.cn/fullchain.pem`
- 私钥：`/etc/letsencrypt/live/api.aifuture.net.cn/privkey.pem`
- 证书链：`/etc/letsencrypt/live/api.aifuture.net.cn/chain.pem`

### 日志位置
- Nginx访问日志：`/var/log/nginx/api-aifuture-access.log`
- Nginx错误日志：`/var/log/nginx/api-aifuture-error.log`
- Certbot日志：`/var/log/letsencrypt/letsencrypt.log`

## 🎯 下一步操作

1. **配置云服务器安全组**（最重要）
   - 开放 80 端口（HTTP，用于Let's Encrypt验证）
   - 开放 443 端口（HTTPS）

2. **确认DNS解析**
   - 确保 `api.aifuture.net.cn` 解析到 `47.98.167.63`

3. **重新获取证书**
   ```bash
   certbot --nginx -d api.aifuture.net.cn --non-interactive --agree-tos --email admin@aifuture.net.cn --redirect
   ```

4. **验证HTTPS访问**
   - 浏览器访问：`https://api.aifuture.net.cn/docs`
   - 检查证书有效性

---

**文档版本**: v1.0  
**创建日期**: 2025-01-XX  
**维护者**: ImageClassifier Team

