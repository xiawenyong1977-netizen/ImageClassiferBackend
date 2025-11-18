# FastAPI HTTPS 配置方案

## 📋 概述

本文档说明如何为 FastAPI 应用配置 HTTPS，包括直接配置和反向代理两种方案。

## ❓ 常见问题

### Q1: FastAPI 可以配置 HTTPS 吗？

**答案：可以，但不推荐直接配置。**

FastAPI 本身（基于 Uvicorn）支持直接配置 HTTPS，但生产环境不推荐：

```bash
# Uvicorn 直接配置 HTTPS（不推荐生产环境）
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 443 \
    --ssl-keyfile /path/to/key.pem \
    --ssl-certfile /path/to/cert.pem
```

**为什么不推荐？**
- ❌ 缺少负载均衡和反向代理功能
- ❌ 静态文件服务性能差
- ❌ SSL/TLS 终止处理效率低
- ❌ 缺少请求限流、缓存等高级功能
- ❌ 证书管理复杂
- ❌ 难以处理 HTTP 到 HTTPS 的重定向

### Q2: 配置 HTTPS 一定要上反向代理吗？

**答案：不一定，但强烈推荐！**

## 🎯 方案对比

### 方案1：直接配置 HTTPS（不推荐）

**优点：**
- ✅ 配置简单，无需额外软件
- ✅ 适合开发/测试环境

**缺点：**
- ❌ 性能较差
- ❌ 缺少反向代理功能
- ❌ 静态文件服务效率低
- ❌ 证书管理复杂
- ❌ 难以扩展

**适用场景：**
- 开发/测试环境
- 小型内部服务
- 快速原型验证

### 方案2：Nginx 反向代理（强烈推荐）⭐

**优点：**
- ✅ 性能优秀（Nginx 专为高并发设计）
- ✅ 完整的反向代理功能
- ✅ 静态文件服务高效
- ✅ SSL/TLS 终止处理高效
- ✅ 支持负载均衡
- ✅ 请求限流、缓存等高级功能
- ✅ 证书管理简单（Let's Encrypt）
- ✅ HTTP 到 HTTPS 自动重定向
- ✅ 更好的安全性和稳定性

**缺点：**
- ⚠️ 需要额外安装和配置 Nginx
- ⚠️ 配置稍复杂

**适用场景：**
- ✅ 生产环境（强烈推荐）
- ✅ 需要高性能的场景
- ✅ 需要静态文件服务
- ✅ 需要负载均衡

## 🚀 推荐方案：Nginx + FastAPI/Gunicorn

### 架构图

```
客户端
  ↓ HTTPS (443)
Nginx (反向代理 + SSL终止)
  ↓ HTTP (8000)
Gunicorn + FastAPI
```

### 配置步骤

#### 1. 安装 Nginx

```bash
# CentOS/RHEL
sudo yum install nginx

# Ubuntu/Debian
sudo apt-get install nginx

# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### 2. 获取 SSL 证书

**方式1：Let's Encrypt（免费，推荐）**

```bash
# 安装 certbot
sudo yum install certbot python3-certbot-nginx  # CentOS
sudo apt-get install certbot python3-certbot-nginx  # Ubuntu

# 自动配置（推荐）
sudo certbot --nginx -d api.aifuture.net.cn

# 或手动获取证书
sudo certbot certonly --standalone -d api.aifuture.net.cn
```

**方式2：商业证书**

上传证书文件到服务器：
- `cert.pem` - 证书文件
- `key.pem` - 私钥文件

#### 3. 配置 Nginx

创建配置文件：`/etc/nginx/conf.d/image-classifier.conf`

```nginx
# 上游 FastAPI 服务
upstream fastapi_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP 服务器（重定向到 HTTPS）
server {
    listen 80;
    server_name api.aifuture.net.cn;
    
    # 重定向所有 HTTP 请求到 HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name api.aifuture.net.cn;

    # SSL 证书配置
    ssl_certificate /etc/letsencrypt/live/api.aifuture.net.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.aifuture.net.cn/privkey.pem;
    
    # SSL 配置（推荐配置）
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
    access_log /var/log/nginx/image-classifier-access.log;
    error_log /var/log/nginx/image-classifier-error.log;

    # 客户端上传大小限制
    client_max_body_size 50M;

    # 代理到 FastAPI
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
        
        # WebSocket 支持（如果需要）
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件服务（可选，如果 Nginx 直接服务静态文件）
    location /images/ {
        alias /opt/ImageClassifierBackend/app/images/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        
        # 如果文件不存在，回退到 FastAPI
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

#### 4. 测试并重载 Nginx

```bash
# 测试配置
sudo nginx -t

# 重载配置
sudo systemctl reload nginx
```

#### 5. 配置防火墙

```bash
# 开放 80 和 443 端口
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# 或使用 iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

#### 6. 自动续期证书（Let's Encrypt）

Let's Encrypt 证书有效期 90 天，需要定期续期：

```bash
# 测试续期
sudo certbot renew --dry-run

# 手动续期
sudo certbot renew

# 设置自动续期（cron）
# certbot 会自动创建 systemd timer，通常无需手动配置
```

## 📊 性能对比

| 指标 | 直接 HTTPS | Nginx 反向代理 |
|------|-----------|---------------|
| 并发处理能力 | 中等 | 优秀 |
| SSL/TLS 性能 | 中等 | 优秀 |
| 静态文件服务 | 差 | 优秀 |
| 内存占用 | 低 | 中等 |
| 配置复杂度 | 简单 | 中等 |
| 扩展性 | 差 | 优秀 |

## 🔒 安全建议

1. **使用强 SSL 配置**
   - 仅支持 TLS 1.2+
   - 使用强加密套件

2. **安全头设置**
   - HSTS（强制 HTTPS）
   - X-Frame-Options
   - X-Content-Type-Options

3. **证书管理**
   - 使用 Let's Encrypt 自动续期
   - 定期检查证书有效期

4. **防火墙配置**
   - 仅开放必要端口（80, 443）
   - 限制管理端口访问

## 🎯 总结

**推荐方案：Nginx 反向代理 + FastAPI/Gunicorn**

- ✅ 生产环境标准配置
- ✅ 性能优秀
- ✅ 功能完整
- ✅ 易于维护

**不推荐：直接配置 HTTPS**

- ❌ 仅适合开发/测试环境
- ❌ 生产环境性能差
- ❌ 缺少必要功能

---

**文档版本**: v1.0  
**创建日期**: 2025-01-XX  
**维护者**: ImageClassifier Team

