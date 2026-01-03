# Vercel Nominatim API 代理

使用 Vercel Serverless Function 代理 Nominatim API 请求，解决服务器无法访问外网的问题。

## 部署步骤

### 方法 1：通过 Vercel Dashboard（推荐）

1. **登录 Vercel**
   - 访问：https://vercel.com/
   - 登录你的账号

2. **创建新项目**
   - 点击 **Add New** → **Project**
   - 如果项目已存在，直接进入项目

3. **上传文件**
   - 将 `api/reverse.js` 文件上传到项目的 `api` 目录
   - 将 `vercel.json` 文件上传到项目根目录
   - 或者使用 Git 连接，直接推送代码

4. **部署**
   - Vercel 会自动检测并部署
   - 等待部署完成

5. **获取 URL**
   - 部署完成后，会显示项目 URL，例如：
     ```
     https://your-project.vercel.app/api/reverse
     ```
   - 或者使用自定义域名：
     ```
     https://nominatim-api.yourdomain.com/api/reverse
     ```

### 方法 2：通过 Vercel CLI

```bash
# 安装 Vercel CLI
npm i -g vercel

# 进入项目目录
cd vercel-nominatim-proxy

# 登录 Vercel
vercel login

# 部署（预览环境）
vercel deploy

# 部署到生产环境
vercel deploy --prod
```

## 配置自定义域名（可选）

如果你的域名已经在 Vercel 上：

1. 进入 Vercel 项目设置
2. 点击 **Domains**
3. 添加子域名，例如：`nominatim-api.yourdomain.com`
4. Vercel 会自动配置 DNS 记录

## 更新后端配置

修改服务器上的 `.env` 文件：

```bash
# 使用 Vercel 部署的 URL
NOMINATIM_API_URL=https://your-project.vercel.app/api/reverse

# 或者使用自定义域名
NOMINATIM_API_URL=https://nominatim-api.yourdomain.com/api/reverse
```

## 测试

```bash
# 测试 API
curl "https://your-project.vercel.app/api/reverse?lat=-8.829694444444444&lon=115.08498333333333&format=json"
```

## 优势

- ✅ 国内可以访问（已验证）
- ✅ 不需要转移域名
- ✅ 免费版支持 Serverless Functions
- ✅ 自动 HTTPS
- ✅ 全球 CDN

## 注意事项

- Vercel 免费版函数超时限制是 10 秒
- 代码中设置了 8 秒超时，留出缓冲时间
- 如果使用付费版，可以增加超时时间



