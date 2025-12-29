# Cloudflare Worker 部署指南

## 功能说明

这个 Cloudflare Worker 用于代理 Nominatim API 请求，解决服务器无法直接访问 Nominatim API 的问题。

## 部署步骤

### 1. 登录 Cloudflare Dashboard

访问 https://dash.cloudflare.com/ 并登录

### 2. 创建 Worker

1. 进入 **Workers & Pages**
2. 点击 **Create application**
3. 选择 **Create Worker**
4. 输入 Worker 名称（例如：`nominatim-proxy`）
5. 点击 **Deploy**

### 3. 配置 Worker 代码

1. 点击创建的 Worker
2. 点击 **Edit code**
3. 删除默认代码
4. 复制 `cloudflare-worker-nominatim.js` 文件中的所有代码
5. 粘贴到编辑器中
6. 点击 **Save and deploy**

### 4. 获取 Worker URL

部署成功后，你会看到一个 URL，格式类似：
```
https://nominatim-proxy.your-subdomain.workers.dev
```

### 5. 配置后端

在服务器的 `.env` 文件中，将 `NOMINATIM_API_URL` 设置为：

```bash
NOMINATIM_API_URL=https://nominatim-proxy.your-subdomain.workers.dev/reverse
```

**注意**：URL 末尾需要加上 `/reverse`，因为 Worker 会转发 `/reverse` 路径的请求。

### 6. 重启服务

```bash
systemctl restart image-classifier
```

## 测试 Worker

部署后，可以通过以下命令测试：

```bash
curl "https://nominatim-proxy.your-subdomain.workers.dev/reverse?lat=-8.83&lon=115.08&format=json&addressdetails=1" \
  -H "User-Agent: ImageClassifierBackend/1.0"
```

如果返回 JSON 数据，说明 Worker 工作正常。

## 注意事项

1. **免费额度**：Cloudflare Workers 免费版每天有 100,000 次请求限制
2. **超时时间**：Worker 默认超时是 30 秒，代码中设置为 25 秒
3. **CORS**：Worker 已配置 CORS，允许跨域请求
4. **速率限制**：Nominatim API 要求每秒不超过 1 次请求，Worker 不会改变这个限制

## 故障排查

如果 Worker 无法工作：

1. 检查 Worker 日志：在 Cloudflare Dashboard 中查看 Worker 的日志
2. 测试 Nominatim API 是否可访问：从你的电脑直接访问 Nominatim API
3. 检查 Worker URL 是否正确：确保 URL 末尾有 `/reverse`
4. 检查后端配置：确保 `.env` 文件中的 URL 正确

