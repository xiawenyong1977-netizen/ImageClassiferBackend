# 微信公众号页面说明

## 📱 页面列表

### 1. 开通会员页面 (`member.html`)

**功能**：
- 微信授权登录
- 查看会员套餐
- 开通会员（微信支付）

**访问路径**：
- `/wechat/member.html`
- 或通过微信公众号菜单访问

**参数**：
- `code`: 微信授权码（从公众号菜单进入时自动获取）

### 2. 购买额度页面 (`credits.html`)

**功能**：
- 微信授权登录
- 选择额度套餐
- 购买额度（微信支付）

**访问路径**：
- `/wechat/credits.html`
- 或通过微信公众号菜单访问

**参数**：
- `code`: 微信授权码（从公众号菜单进入时自动获取）

### 3. 额度信息页面 (`credits_info.html`)

**功能**：
- 微信授权登录
- 查看当前额度
- 查看使用记录

**访问路径**：
- `/wechat/credits_info.html`
- 或通过微信公众号菜单访问

**参数**：
- `code`: 微信授权码（从公众号菜单进入时自动获取）

### 4. 支付测试页面 (`pay-test.html`)

**功能**：
- 支付功能测试
- 调试支付流程

**访问路径**：
- `/wechat/pay-test.html`

## 🔐 微信授权流程

1. 用户通过微信公众号菜单进入页面
2. 页面获取URL参数中的 `code`
3. 调用 `/api/v1/auth/wechat?code=xxx` 获取 `openid`
4. 使用 `openid` 进行后续API调用

## 💰 支付流程

1. 用户选择套餐/额度
2. 调用 `/api/v1/payment/create` 创建订单
3. 获取支付参数
4. 调起微信支付
5. 支付成功后跳转到结果页面

## 🔗 API接口

所有页面使用以下API接口：

- **微信授权**: `GET /api/v1/auth/wechat?code=xxx`
- **创建订单**: `POST /api/v1/payment/create`
- **查询订单**: `GET /api/v1/payment/query/{order_id}`
- **查询额度**: `GET /api/v1/user/credits`
- **查询会员**: `GET /api/v1/user/member`

## 📝 注意事项

1. **微信授权**：必须通过微信公众号菜单访问，才能获取有效的 `code`
2. **支付环境**：需要在微信内置浏览器中打开才能调起支付
3. **域名配置**：需要在微信公众平台配置JS安全域名
4. **HTTPS要求**：支付相关页面必须使用HTTPS

## 🚀 部署说明

### 通过Nginx服务静态文件

```nginx
location /wechat/ {
    alias /opt/ImageClassifierBackend/wechat/;
}
```

### 通过FastAPI服务静态文件

在 `app/main.py` 中添加：

```python
wechat_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wechat")
if os.path.exists(wechat_path):
    app.mount("/wechat", StaticFiles(directory=wechat_path), name="wechat")
```

---

**维护者**: ImageClassifier Team

