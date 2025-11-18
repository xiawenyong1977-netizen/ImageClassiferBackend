# Member页面改动说明

## 📋 当前流程分析

### Member页面的完整流程

```
1. 用户通过微信公众号菜单进入
   ↓
2. 微信授权回调，URL参数包含code
   ↓
3. 前端调用 GET /api/v1/auth/wechat?code=xxx
   - 后端调用微信API获取openid
   - 后端创建/更新用户到数据库
   ↓
4. 前端调用 GET /api/v1/user/credits (Header: X-WeChat-OpenID)
   - 查询用户会员状态和额度
   ↓
5. 用户点击"立即开通"
   ↓
6. 前端调用 POST /api/v1/payment/create-order
   - 后端创建订单到数据库
   - 后端调用微信支付API统一下单
   - 返回支付参数
   ↓
7. 前端调起微信支付
   ↓
8. 用户完成支付
   ↓
9. 微信回调 POST /api/v1/payment/notify
   - 后端更新订单状态
   - 后端更新用户会员状态和额度
```

---

## 🔄 新架构下的改动

### 1. 网页授权接口改动

**当前实现** (`app/api/auth.py` - `GET /api/v1/auth/wechat`):
```python
# 1. 调用微信API获取openid
token_response = requests.get("https://api.weixin.qq.com/sns/oauth2/access_token", ...)
openid = token_response['openid']

# 2. 直接操作数据库创建/更新用户
async with db.get_connection() as conn:
    # 创建或更新用户
    await cursor.execute("INSERT INTO wechat_users ...")
```

**新架构实现** (App服务器):
- **无需改动**：接口直接迁移到App服务器
- App服务器调用微信API获取openid
- App服务器直接操作数据库创建/更新用户
- **不需要通过内部接口调用**

**说明**：
- 网页授权接口迁移到App服务器
- App服务器直接调用微信API和操作数据库
- 代码逻辑保持不变，只是部署位置改变

---

### 2. 查询用户信息接口（无需改动）

**当前实现** (`app/api/user.py` - `GET /api/v1/user/credits`):
- 已经在App服务器
- 只查询数据库，不调用微信API
- **无需改动**

---

### 3. 创建订单接口改动

**当前实现** (`app/api/payment.py` - `POST /api/v1/payment/create-order`):
```python
# 1. 创建订单到数据库
await cursor.execute("INSERT INTO payment_orders ...")

# 2. 调用微信支付API统一下单
payment_params = call_wechat_pay_unifiedorder(order_no, openid, amount, description)

# 3. 返回支付参数
return {"success": True, "payment_params": payment_params}
```

**新架构实现** (App服务器):
```python
# 1. 创建订单到数据库
await cursor.execute("INSERT INTO payment_orders ...")

# 2. 调用微信支付API统一下单（在App服务器上）
payment_params = call_wechat_pay_unifiedorder(order_no, openid, amount, "会员开通")

# 3. 返回支付参数
return {
    "success": True,
    "payment_params": payment_params
}
```

**前端改动** (`member.html`):
- **无需改动**：前端仍然调用 `POST /api/v1/payment/create-order`
- 接口已迁移到App服务器，但URL路径不变（通过Nginx路由）
- App服务器内部完成：创建订单 + 统一下单 + 返回支付参数

**说明**：
- 创建订单和统一下单都在App服务器完成
- 不需要拆分，因为都是我们主动调用微信API
- 前端代码无需修改

---

### 4. 支付回调接口改动

**当前实现** (`app/api/payment.py` - `POST /api/v1/payment/notify`):
```python
# 1. 解析微信回调数据
# 2. 更新订单状态
await cursor.execute("UPDATE payment_orders SET status = 'paid' ...")

# 3. 更新用户会员状态和额度
await cursor.execute("UPDATE wechat_users SET is_member = 1 ...")
```

**新架构实现** (Web服务器):
```python
# 1. 解析微信回调数据
transaction_id = root.find('transaction_id').text
out_trade_no = root.find('out_trade_no').text
total_fee = int(root.find('total_fee').text) / 100
openid = root.find('openid').text

# 2. 调用App服务器的内部接口更新订单和用户
app_server_url = settings.APP_SERVER_URL
response = requests.put(
    f"{app_server_url}/api/v1/internal/payment/order/update",
    json={
        "order_no": out_trade_no,
        "transaction_id": transaction_id,
        "amount": total_fee,
        "openid": openid,
        "status": "paid"
    },
    headers={"X-Internal-Auth": settings.INTERNAL_API_KEY}
)

# 3. 返回SUCCESS给微信
return PlainTextResponse(content="<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>")
```

**App服务器需要提供的新接口** (`app/api/internal.py`):
```python
@router.put("/internal/payment/order/update")
async def update_order(request: OrderUpdateRequest):
    """更新订单状态（内部接口）"""
    # 验证内部接口认证
    if request.headers.get("X-Internal-Auth") != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="内部接口认证失败")
    
    order_no = request.order_no
    transaction_id = request.transaction_id
    amount = request.amount
    openid = request.openid
    
    async with db.get_connection() as conn:
        # 1. 查询订单
        # 2. 更新订单状态
        # 3. 根据订单类型更新用户（会员或额度）
        # 4. 如果是会员订单，更新会员状态和赠送额度
        # 5. 如果是额度订单，增加用户额度
    
    return {"success": True}
```

**安全考虑**：
- 内部接口需要配置API Key认证
- 建议使用IP白名单限制访问来源
- 考虑使用签名机制（时间戳+签名）防止重放攻击

---

## 📝 改动清单

### Web服务器需要改动

1. **保留 `GET /api/v1/auth/wechat/verify` 接口**（服务器配置验证）
   - 无需改动：只做服务器验证，不访问数据库

2. **修改 `POST /api/v1/auth/wechat/verify` 接口**（消息推送）
   - 保留：接收微信消息推送
   - 修改：调用App服务器内部接口保存用户和更新绑定

3. **修改 `POST /api/v1/payment/notify` 接口**（支付回调）
   - 保留：接收微信回调
   - 修改：调用App服务器内部接口更新订单和用户，而不是直接操作数据库

### App服务器需要改动

1. **迁移 `GET /api/v1/auth/wechat` 接口**（网页授权）
   - 从Web服务器迁移到App服务器
   - 调用微信API获取openid
   - 直接操作数据库创建/更新用户

2. **迁移 `POST /api/v1/auth/wechat/qrcode` 接口**（生成二维码）
   - 从Web服务器迁移到App服务器
   - 调用微信API生成二维码
   - 直接操作数据库插入绑定记录

3. **迁移 `POST /api/v1/payment/unifiedorder` 接口**（支付统一下单）
   - 从Web服务器迁移到App服务器（如果之前存在）
   - 或者合并到 `POST /api/v1/payment/create-order` 接口中
   - 调用微信支付API统一下单

4. **新增内部接口模块** (`app/api/internal.py`)
   - `POST /api/v1/internal/user/create-or-update` - 创建或更新用户（供Web服务器调用）
   - `POST /api/v1/internal/binding/create` - 创建绑定记录（供Web服务器调用）
   - `PUT /api/v1/internal/binding/update` - 更新绑定记录（供Web服务器调用）
   - `PUT /api/v1/internal/payment/order/update` - 更新订单状态（供Web服务器调用）

5. **修改 `POST /api/v1/payment/create-order` 接口**
   - 保留：创建订单到数据库
   - 保留：调用微信支付API统一下单的逻辑
   - 返回：支付参数（前端无需改动）

### 前端需要改动

1. **无需改动**：`member.html` 的 `createOrder()` 函数保持不变
   - 仍然调用 `POST /api/v1/payment/create-order`
   - 接口已迁移到App服务器，但URL路径不变（通过Nginx路由）
   - App服务器内部完成：创建订单 + 统一下单 + 返回支付参数

---

## 🔄 完整流程对比

### 当前流程
```
前端 → App服务器创建订单（包含统一下单） → 返回支付参数 → 调起支付
```

### 新架构流程
```
前端 → App服务器创建订单（包含统一下单） → 返回支付参数 → 调起支付
```

**说明**：
- 流程保持不变，因为创建订单和统一下单都在App服务器完成
- 前端代码无需修改
- 只有支付回调需要Web服务器调用App服务器的内部接口

---

## ⚠️ 注意事项

1. **内部接口认证**：App服务器的内部接口需要配置认证机制（API Key）
   - 建议使用签名机制（时间戳+签名）防止重放攻击
   - 建议使用IP白名单限制访问来源
2. **错误处理**：Web服务器调用App服务器接口失败时的处理
   - 支付回调失败时，需要记录日志并重试
   - 消息推送失败时，需要记录日志
3. **超时设置**：Web服务器调用App服务器接口的超时设置
   - 建议设置合理的超时时间（如5秒）
4. **日志记录**：记录服务间调用的日志，便于排查问题
5. **微信配置**：App服务器需要配置微信API相关配置（APPID、SECRET等）

---

**最后更新**: 2024-11-18  
**维护者**: ImageClassifier Team

