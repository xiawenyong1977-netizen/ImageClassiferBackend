# 配置微信公众号IP白名单

## 问题
服务器调用微信API获取`access_token`时失败，错误信息：
```
invalid ip 123.57.68.4 ipv6 ::ffff:123.57.68.4, not in whitelist
```

## 原因
微信公众号要求调用接口的服务器IP必须在白名单中，否则会拒绝请求。

## 解决步骤

### 1. 登录微信公众平台
访问：https://mp.weixin.qq.com

### 2. 进入基本配置页面
- 左侧菜单：**开发** → **基本配置**

### 3. 添加IP白名单
找到 **IP白名单** 配置项，点击 **修改** 或 **设置**：

**需要添加的IP地址：**
```
123.57.68.4
```

### 4. 保存配置
点击 **保存**，配置会立即生效。

## 注意事项

1. **IPv4和IPv6**：如果服务器同时支持IPv4和IPv6，可能需要添加两个地址
2. **生效时间**：配置保存后立即生效，无需等待
3. **安全建议**：只添加必要的服务器IP，不要添加客户端IP

## 测试验证

配置完成后，客户端再次点击"生成二维码"按钮，应该能成功生成二维码。

## 参考文档

微信官方文档：https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Getting_the_Global_Retrieve_Access_Token.html
