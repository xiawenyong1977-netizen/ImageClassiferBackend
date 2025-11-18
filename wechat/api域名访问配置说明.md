# api.aifuture.net.cn/wechat 域名访问配置说明

## 📋 目标

将微信页面配置为通过 `https://api.aifuture.net.cn/wechat/` 访问

---

## ✅ 当前状态

### 已完成的配置

1. ✅ **wechat目录已部署到App服务器**
   - 部署路径：`/opt/ImageClassifierBackend/wechat/`

2. ✅ **FastAPI已配置静态文件服务**
   - 配置路径：`/wechat` → `/opt/ImageClassifierBackend/wechat/`
   - 代码位置：`app/main.py`

3. ✅ **api.aifuture.net.cn域名已配置**
   - 根据文档，`api.aifuture.net.cn` 已经配置并指向App服务器
   - Nginx配置：`/etc/nginx/conf.d/api-aifuture.conf`

---

## 🔧 需要配置的内容

### 1. 确认Nginx配置（如果使用Nginx）

如果App服务器使用Nginx作为反向代理，需要确认Nginx配置：

```nginx
# /etc/nginx/conf.d/api-aifuture.conf
server {
    listen 80;
    server_name api.aifuture.net.cn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.aifuture.net.cn;

    ssl_certificate /etc/letsencrypt/live/api.aifuture.net.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.aifuture.net.cn/privkey.pem;

    # 反向代理到FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态文件可以直接由Nginx提供（可选，性能更好）
    # location /wechat/ {
    #     alias /opt/ImageClassifierBackend/wechat/;
    #     try_files $uri $uri/ =404;
    # }
}
```

**说明**：
- 如果Nginx配置了 `location /` 反向代理到FastAPI，那么 `/wechat/` 也会被代理到FastAPI
- FastAPI已经配置了静态文件服务，所以可以直接访问
- 如果想提高性能，可以让Nginx直接提供静态文件（注释中的配置）

### 2. 更新wechat页面中的API地址

需要将wechat页面中的 `API_BASE_URL` 更新为 `https://api.aifuture.net.cn/api/v1`

**需要更新的文件**：
- `member.html`
- `credits.html`
- `credits_info.html`

**当前配置**：
```javascript
const API_BASE_URL = 'https://www.xintuxiangce.top/api/v1';
```

**需要改为**：
```javascript
const API_BASE_URL = 'https://api.aifuture.net.cn/api/v1';
```

---

## 📝 配置步骤

### 步骤1：更新wechat页面API地址

```bash
# 在本地更新文件
# member.html, credits.html, credits_info.html
# 将 API_BASE_URL 改为 'https://api.aifuture.net.cn/api/v1'
```

### 步骤2：重新部署wechat目录

```bash
# 使用rsync同步更新后的文件
rsync -avz wechat/ root@app:/opt/ImageClassifierBackend/wechat/
```

### 步骤3：确认Nginx配置（如果使用Nginx）

```bash
# 检查Nginx配置
ssh root@app "cat /etc/nginx/conf.d/api-aifuture.conf"

# 如果配置正确，重启Nginx
ssh root@app "nginx -t && systemctl reload nginx"
```

### 步骤4：测试访问

```bash
# 测试页面访问
curl -I https://api.aifuture.net.cn/wechat/member.html
curl -I https://api.aifuture.net.cn/wechat/credits.html
curl -I https://api.aifuture.net.cn/wechat/credits_info.html

# 测试API调用
curl https://api.aifuture.net.cn/api/v1/health
```

---

## 🎯 访问地址

配置完成后，可以通过以下地址访问：

- **会员页面**：`https://api.aifuture.net.cn/wechat/member.html`
- **购买额度**：`https://api.aifuture.net.cn/wechat/credits.html`
- **额度信息**：`https://api.aifuture.net.cn/wechat/credits_info.html`
- **支付测试**：`https://api.aifuture.net.cn/wechat/pay-test.html`

---

## ⚠️ 注意事项

### 1. 微信平台配置

如果使用 `api.aifuture.net.cn/wechat/` 访问，需要：

1. **JS安全域名配置**：
   - 微信公众平台 → 设置 → 公众号设置 → 功能设置 → JS接口安全域名
   - 添加：`api.aifuture.net.cn`

2. **授权回调域名配置**：
   - 微信公众平台 → 开发 → 接口权限 → 网页授权获取用户基本信息
   - 添加：`api.aifuture.net.cn`

3. **支付授权目录配置**：
   - 微信支付商户平台 → 产品中心 → 开发配置 → JSAPI支付 → 支付授权目录
   - 添加：`https://api.aifuture.net.cn/wechat/`

### 2. HTTPS要求

- ✅ `api.aifuture.net.cn` 已经配置了HTTPS证书
- ✅ 微信要求支付相关页面必须使用HTTPS

### 3. 域名一致性

- ✅ 页面域名：`api.aifuture.net.cn`
- ✅ API域名：`api.aifuture.net.cn`
- ✅ 同一域名，避免跨域问题

---

## 🔄 两种方案对比

### 方案1：使用 api.aifuture.net.cn（推荐）✅

**优势**：
- ✅ 域名统一，API和页面同一域名
- ✅ 避免跨域问题
- ✅ 配置简单
- ✅ 已有HTTPS证书

**访问地址**：
- 页面：`https://api.aifuture.net.cn/wechat/member.html`
- API：`https://api.aifuture.net.cn/api/v1/...`

### 方案2：使用 www.xintuxiangce.top

**优势**：
- ✅ 不需要修改微信平台配置
- ✅ 保持现有配置

**劣势**：
- ❌ 需要通过Web服务器反向代理
- ❌ 增加一层转发

---

## 📋 配置检查清单

- [ ] 更新 `member.html` 中的 `API_BASE_URL`
- [ ] 更新 `credits.html` 中的 `API_BASE_URL`
- [ ] 更新 `credits_info.html` 中的 `API_BASE_URL`
- [ ] 重新部署wechat目录到App服务器
- [ ] 确认Nginx配置（如果使用Nginx）
- [ ] 测试页面访问
- [ ] 测试API调用
- [ ] 配置微信平台JS安全域名（如果需要）
- [ ] 配置微信平台授权回调域名（如果需要）
- [ ] 配置微信支付授权目录（如果需要）

---

**最后更新**: 2024-11-18  
**维护者**: ImageClassifier Team

