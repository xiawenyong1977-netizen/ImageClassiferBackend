# Cloudflare Worker 自定义域名配置指南

## 为什么使用自定义域名？

如果服务器无法访问 `*.workers.dev` 域名（被防火墙阻止），可以通过配置自定义域名来解决：
- 自定义域名使用 Cloudflare CDN IP，通常更容易通过防火墙
- 可以使用自己的域名，更专业
- 免费版 Cloudflare Worker 支持自定义域名

## 重要说明：Transfer vs DNS 托管

**不需要转移（Transfer）域名！** 只需要将域名的 **DNS 托管** 到 Cloudflare：

- **Transfer（转移）**：将域名的注册商从当前注册商（如阿里云、腾讯云）转移到 Cloudflare
  - ❌ **不需要**：配置 Worker 自定义域名不需要转移域名
  - 转移域名会改变域名注册商，通常需要额外费用

- **DNS 托管**：只将域名的 DNS 解析服务交给 Cloudflare 管理
  - ✅ **只需要这个**：配置 Worker 自定义域名只需要 DNS 托管
  - 域名注册商保持不变，免费
  - 只需要修改域名的 DNS 服务器地址

## 配置步骤

### 1. 准备域名（DNS 托管到 Cloudflare）

**如果域名还没有添加到 Cloudflare：**

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 点击 **Add a Site**（添加站点）
3. 输入你的域名（例如：`yourdomain.com`）
4. 选择 **Free** 计划（免费版即可）
5. Cloudflare 会扫描你当前的 DNS 记录
6. 确认 DNS 记录后，Cloudflare 会提供两个 DNS 服务器地址，例如：
   - `alice.ns.cloudflare.com`
   - `bob.ns.cloudflare.com`
7. **在你的域名注册商处修改 DNS 服务器**：
   - 登录你的域名注册商（阿里云、腾讯云等）
   - 找到域名管理 → DNS 设置
   - 将 DNS 服务器改为 Cloudflare 提供的地址
   - 等待 DNS 生效（通常几分钟到几小时）

**如果域名已经在 Cloudflare：**
- 直接跳到步骤 2

### 2. 在 Cloudflare Worker 中配置自定义域名

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Workers & Pages** → 选择你的 Worker（`nominatim-proxy`）
3. 点击 **Settings** → **Triggers**
4. 在 **Custom Domains** 部分，点击 **Add Custom Domain**
5. 输入你想要使用的子域名，例如：
   - `nominatim-api.yourdomain.com`
   - `api-proxy.yourdomain.com`
   - `nominatim.yourdomain.com`
6. Cloudflare 会自动配置 DNS 记录（CNAME）
7. 等待 DNS 生效（通常几分钟到几小时）

### 3. 更新后端配置

修改后端 `.env` 文件中的 `NOMINATIM_API_URL`：

```bash
# 原来的配置（workers.dev 域名）
# NOMINATIM_API_URL=https://nominatim-proxy.xiawenyong1977.workers.dev/reverse

# 新的配置（自定义域名）
NOMINATIM_API_URL=https://nominatim-api.yourdomain.com/reverse
```

### 4. 测试连接

在服务器上测试新域名：

```bash
# 测试 DNS 解析
nslookup nominatim-api.yourdomain.com

# 测试 HTTPS 连接
curl -v https://nominatim-api.yourdomain.com/reverse?lat=-8.829694444444444&lon=115.08498333333333&format=json
```

### 5. 重启后端服务

```bash
sudo systemctl restart image-classifier
```

## 注意事项

1. **DNS 生效时间**：DNS 记录可能需要几分钟到几小时才能生效
2. **SSL 证书**：Cloudflare 会自动为自定义域名配置 SSL 证书（免费）
3. **域名要求**：域名必须托管在 Cloudflare，或者可以添加 CNAME 记录
4. **免费版限制**：免费版 Worker 支持自定义域名，但有一些限制（如请求数限制）

## 验证配置

配置完成后，检查日志确认使用新域名：

```bash
# 查看后端日志
tail -f /var/log/image-classifier/app.log | grep Nominatim
```

应该看到类似日志：
```
Nominatim API准备调用: URL=https://nominatim-api.yourdomain.com/reverse, 坐标=(...)
```

## 故障排查

如果自定义域名仍然无法访问：

1. **检查 DNS 解析**：
   ```bash
   nslookup nominatim-api.yourdomain.com
   ```

2. **检查 Cloudflare DNS 设置**：
   - 确保 DNS 记录类型是 CNAME
   - 确保代理状态是"已代理"（橙色云朵）

3. **检查防火墙规则**：
   - 确保允许访问 Cloudflare CDN IP 段
   - Cloudflare IP 段：https://www.cloudflare.com/ips/

4. **测试 Cloudflare CDN IP**：
   ```bash
   # 获取域名对应的 IP
   dig nominatim-api.yourdomain.com
   
   # 测试直接访问 IP（需要 Host 头）
   curl -H "Host: nominatim-api.yourdomain.com" https://<IP>/reverse?lat=-8.829694444444444&lon=115.08498333333333&format=json
   ```

## 替代方案

如果无法配置自定义域名，可以考虑：

1. **使用 Cloudflare Tunnel**：通过 Cloudflare Tunnel 建立内网穿透
2. **使用其他代理服务**：如 Vercel、Netlify Functions 等
3. **直接使用 Nominatim API**：如果防火墙允许访问 `nominatim.openstreetmap.org`

