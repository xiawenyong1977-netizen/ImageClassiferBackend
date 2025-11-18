# HTTP前端 + HTTPS接口配置说明

## 配置方案

- **前端页面**: HTTP (`http://admin.xintuxiangce.top`)
- **API接口**: HTTPS (`https://api.aifuture.net.cn`)

## 混合内容说明

### 什么是混合内容？

混合内容（Mixed Content）分为两种：

1. **被动混合内容**（Passive Mixed Content）
   - HTTP页面加载HTTPS图片、视频等
   - 浏览器通常允许，但可能显示警告

2. **主动混合内容**（Active Mixed Content）
   - HTTP页面加载HTTPS脚本、AJAX请求等
   - 现代浏览器通常允许，但会显示警告

### 我们的情况

- **前端**: HTTP页面
- **API调用**: HTTPS AJAX请求（主动混合内容）

**浏览器行为**：
- ✅ 请求会被执行（不会被阻止）
- ⚠️ 浏览器可能显示"不安全"警告
- ✅ API调用是加密的（HTTPS）

## 配置位置

### 1. `admin/app.js`
```javascript
let currentConfig = {
    apiUrl: 'https://api.aifuture.net.cn',  // 使用HTTPS API
    // ...
};
```

### 2. `admin/login.html`
```javascript
const API_URL = 'https://api.aifuture.net.cn';
```

### 3. `admin/index.html`
```html
<input type="text" id="api-url" placeholder="https://api.aifuture.net.cn">
```

## 优势

1. **API调用加密**: 所有API请求都通过HTTPS加密传输
2. **简单配置**: 前端无需SSL证书
3. **灵活性**: 可以随时切换API地址

## 注意事项

1. **浏览器警告**: 浏览器可能显示"此页面包含不安全的内容"警告
2. **CORS配置**: 确保API服务器允许来自 `http://admin.xintuxiangce.top` 的跨域请求
3. **安全性**: 虽然API调用是加密的，但前端页面本身不加密，登录凭据在HTTP传输

## 更好的方案（可选）

如果希望完全避免混合内容警告，可以考虑：

1. **前端也配置HTTPS**: 为 `admin.xintuxiangce.top` 配置SSL证书
2. **使用同源策略**: 前端和API使用同一域名和协议

## 当前配置状态

- ✅ 前端: HTTP (`http://admin.xintuxiangce.top`)
- ✅ API: HTTPS (`https://api.aifuture.net.cn`)
- ✅ 配置已更新并部署

