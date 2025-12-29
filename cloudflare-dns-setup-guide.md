# Cloudflare DNS 托管配置指南（不需要转移域名）

## 重要说明

**配置 Worker 自定义域名只需要 DNS 托管，不需要转移域名！**

- ✅ **DNS 托管**：只将 DNS 解析交给 Cloudflare（免费，域名注册商不变）
- ❌ **Transfer 转移**：将域名注册商转移到 Cloudflare（需要费用，改变注册商）

## 配置步骤

### 步骤 1：将域名添加到 Cloudflare（DNS 托管）

1. **登录 Cloudflare Dashboard**
   - 访问：https://dash.cloudflare.com/
   - 如果没有账号，先注册（免费）

2. **添加站点（多种方式）**

   **方式 1：从首页添加**
   - 登录后，在 Dashboard 首页
   - 找到左侧菜单栏，点击 **Websites**（网站）
   - 在页面右上角或中间位置，点击 **Add a Site**（添加站点）按钮
   - 或者直接访问：https://dash.cloudflare.com/add-site

   **方式 2：从左侧菜单添加**
   - 点击左侧菜单的 **Websites**（网站）
   - 如果还没有添加任何站点，页面中间会显示 **Add a Site** 按钮
   - 点击该按钮

   **方式 3：直接输入 URL**
   - 直接访问：https://dash.cloudflare.com/add-site

3. **输入域名**
   - 在输入框中输入你的域名（例如：`yourdomain.com`）
   - 注意：**只输入主域名，不要带 `www` 或子域名**
   - 点击 **Add site**（添加站点）按钮

4. **选择计划**
   - 选择 **Free**（免费版即可）
   - 点击 **Continue**（继续）

5. **扫描 DNS 记录**
   - Cloudflare 会自动扫描你当前的 DNS 记录
   - 确认记录是否正确（A 记录、CNAME 记录等）
   - 如果记录正确，点击 **Continue**（继续）
   - 如果有遗漏的记录，可以手动添加

6. **获取 DNS 服务器地址**
   - Cloudflare 会显示两个 DNS 服务器地址，例如：
     ```
     alice.ns.cloudflare.com
     bob.ns.cloudflare.com
     ```
   - **重要：记下这两个地址**（复制保存）
   - 这两个地址会在下一步使用

### 步骤 2：在域名注册商处修改 DNS 服务器

**以阿里云为例：**

1. **登录阿里云控制台**
   - 访问：https://dc.console.aliyun.com/
   - 进入 **域名** → **域名列表**

2. **找到你的域名**
   - 点击域名进入管理页面

3. **修改 DNS 服务器**
   - 找到 **DNS 修改** 或 **DNS 服务器设置**
   - 点击 **修改 DNS 服务器**
   - 删除原有的 DNS 服务器地址
   - 添加 Cloudflare 提供的两个 DNS 服务器地址：
     ```
     alice.ns.cloudflare.com
     bob.ns.cloudflare.com
     ```
   - 点击 **确认** 或 **保存**

4. **等待生效**
   - DNS 修改通常需要几分钟到几小时生效
   - 可以在 Cloudflare Dashboard 中查看状态

**其他注册商（腾讯云、GoDaddy 等）：**
- 步骤类似，找到域名管理 → DNS 设置 → 修改 DNS 服务器地址

### 步骤 3：在 Cloudflare 中配置 Worker 自定义域名

1. **确认域名已激活**
   - 回到 Cloudflare Dashboard
   - 确认域名状态为 **Active**（激活）

2. **配置 Worker 自定义域名**
   - 进入 **Workers & Pages** → 选择你的 Worker（`nominatim-proxy`）
   - 点击 **Settings** → **Triggers**
   - 在 **Custom Domains** 部分，点击 **Add Custom Domain**
   - 输入子域名，例如：`nominatim-api.yourdomain.com`
   - Cloudflare 会自动创建 CNAME 记录
   - 等待 DNS 生效（通常几分钟）

### 步骤 4：更新后端配置

修改服务器上的 `.env` 文件：

```bash
# 将 NOMINATIM_API_URL 改为你的自定义域名
NOMINATIM_API_URL=https://nominatim-api.yourdomain.com/reverse
```

### 步骤 5：重启服务并测试

```bash
# 重启服务
sudo systemctl restart image-classifier

# 测试连接
curl -v https://nominatim-api.yourdomain.com/reverse?lat=-8.829694444444444&lon=115.08498333333333&format=json
```

## 找不到 "Add a Site" 按钮？

如果找不到 "Add a Site" 按钮，可以尝试：

1. **直接访问添加站点页面**
   - 访问：https://dash.cloudflare.com/add-site
   - 这是添加站点的直接链接

2. **检查账号状态**
   - 确保已登录 Cloudflare 账号
   - 如果未登录，先登录：https://dash.cloudflare.com/login

3. **从左侧菜单进入**
   - 点击左侧菜单的 **Websites**（网站）
   - 在网站列表页面，点击右上角的 **Add a Site** 按钮

4. **使用搜索功能**
   - 在 Cloudflare Dashboard 顶部搜索框
   - 输入 "add site" 或 "添加站点"

5. **检查浏览器**
   - 清除浏览器缓存
   - 尝试使用 Chrome 或 Firefox 浏览器
   - 确保浏览器已更新到最新版本

## 常见问题

### Q: 修改 DNS 服务器会影响网站访问吗？

A: 如果网站已经在运行：
- **如果网站使用 Cloudflare CDN**：修改 DNS 服务器后，网站会继续正常访问
- **如果网站不使用 Cloudflare**：需要先在 Cloudflare 中添加网站的 DNS 记录（A 记录、CNAME 等），然后再修改 DNS 服务器

### Q: 域名注册商不变，只是 DNS 托管，安全吗？

A: 是的，非常安全：
- 域名所有权仍在原注册商
- 只是 DNS 解析交给 Cloudflare 管理
- 可以随时改回原来的 DNS 服务器

### Q: 需要费用吗？

A: DNS 托管是免费的，Cloudflare Free 计划即可。

### Q: 如果不想修改 DNS 服务器，有其他方法吗？

A: 可以尝试：
1. **只添加 CNAME 记录**（如果域名注册商支持）：
   - 在域名注册商处添加 CNAME 记录：
     ```
     名称：nominatim-api
     值：nominatim-proxy.xiawenyong1977.workers.dev
     ```
   - 但这种方法可能无法使用 Cloudflare CDN 的优势

2. **使用其他代理服务**：如 Vercel、Netlify Functions 等

## 验证 DNS 是否生效

```bash
# 检查 DNS 解析
nslookup nominatim-api.yourdomain.com

# 应该看到 Cloudflare 的 IP 地址
```

## 总结

- ✅ **只需要 DNS 托管**：将 DNS 服务器改为 Cloudflare 的地址
- ❌ **不需要转移域名**：域名注册商可以保持不变
- 💰 **完全免费**：Cloudflare DNS 托管是免费的
- 🔒 **安全可靠**：可以随时改回原来的 DNS 服务器

