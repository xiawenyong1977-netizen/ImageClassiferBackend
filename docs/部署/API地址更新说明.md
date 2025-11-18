# API地址更新说明

## 📋 更新概述

**更新时间**: 2025-11-18  
**更新内容**: 将admin管理后台的API调用地址从 `http://123.57.68.4:8000` 更新为 `https://api.aifuture.net.cn`

## ✅ 已更新的文件

### 1. `admin/app.js`

**更新前**:
```javascript
let currentConfig = {
    apiUrl: 'http://123.57.68.4:8000',
    ...
};
```

**更新后**:
```javascript
let currentConfig = {
    apiUrl: 'https://api.aifuture.net.cn',
    ...
};
```

### 2. `admin/index.html`

**更新前**:
```html
<input type="text" id="api-url" placeholder="http://123.57.68.4:8000">
```

**更新后**:
```html
<input type="text" id="api-url" placeholder="https://api.aifuture.net.cn">
```

### 3. `admin/login.html`

**更新前**:
```javascript
const API_URL = window.location.origin;
```

**更新后**:
```javascript
// 使用固定的API地址，确保无论管理后台部署在哪里都能正确调用API
const API_URL = 'https://api.aifuture.net.cn';
```

## 🔄 更新原因

1. **统一域名**: 使用HTTPS域名 `api.aifuture.net.cn` 替代IP地址
2. **安全性**: 使用HTTPS协议，提高数据传输安全性
3. **可维护性**: 使用域名便于后续服务器迁移和负载均衡
4. **稳定性**: 避免直接使用IP地址，减少因IP变更导致的问题

## 📍 API地址说明

### 新API地址

- **HTTPS**: `https://api.aifuture.net.cn`
- **API基础路径**: `https://api.aifuture.net.cn/api/v1`

### 主要API端点

- **健康检查**: `GET https://api.aifuture.net.cn/api/v1/health`
- **登录**: `POST https://api.aifuture.net.cn/api/v1/auth/login`
- **统计数据**: `GET https://api.aifuture.net.cn/api/v1/stats/today`
- **图片分类**: `POST https://api.aifuture.net.cn/api/v1/classify`
- **配置管理**: `GET/POST https://api.aifuture.net.cn/api/v1/config/inference`

## 🔧 部署更新

### 本地文件已更新

所有本地文件已更新为新的API地址。

### 服务器部署

已重新部署以下文件到 `root@web:/var/www/xintuxiangce/admin/`:

- ✅ `app.js`
- ✅ `index.html`
- ✅ `login.html`

### 验证部署

```bash
# 检查服务器上的API地址配置
ssh root@web "grep 'apiUrl:' /var/www/xintuxiangce/admin/app.js"
ssh root@web "grep 'API_URL' /var/www/xintuxiangce/admin/login.html"
```

## ⚠️ 注意事项

1. **HTTPS要求**: 新API地址使用HTTPS，确保服务器SSL证书配置正确
2. **CORS配置**: 如果管理后台和API在不同域名，需要配置CORS允许跨域访问
3. **缓存清理**: 更新后建议清理浏览器缓存，确保加载最新版本
4. **配置覆盖**: 用户可以在管理后台的配置页面手动修改API地址（保存在localStorage）

## 🔗 相关文档

- Admin管理后台部署说明: `docs/部署/admin管理后台部署说明.md`
- Nginx部署完成报告: `docs/部署/Nginx部署完成报告.md`

---

**更新完成时间**: 2025-11-18  
**维护者**: ImageClassifier Team

