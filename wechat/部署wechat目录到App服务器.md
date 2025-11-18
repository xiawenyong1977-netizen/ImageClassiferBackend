# 部署wechat目录到App服务器

## 📋 部署目标

将 `wechat` 目录部署到 App 服务器的 `/opt/ImageClassifierBackend/wechat/`

---

## 🚀 部署步骤

### 方法1：使用 scp 命令（推荐）

```bash
# 从本地部署到App服务器
scp -r wechat root@47.98.167.63:/opt/ImageClassifierBackend/

# 如果需要指定SSH密钥
scp -r -i ~/.ssh/id_rsa wechat root@47.98.167.63:/opt/ImageClassifierBackend/
```

### 方法2：使用 rsync 命令（推荐，支持增量同步）

```bash
# 同步wechat目录到App服务器（排除不需要的文件）
rsync -avz --exclude='*.md' --exclude='imageclassify.png' wechat/ root@47.98.167.63:/opt/ImageClassifierBackend/wechat/

# 或者同步所有文件
rsync -avz wechat/ root@47.98.167.63:/opt/ImageClassifierBackend/wechat/
```

### 方法3：使用 Git（如果App服务器已配置Git）

```bash
# 在App服务器上执行
ssh root@47.98.167.63 "cd /opt/ImageClassifierBackend && git pull"
```

---

## ✅ 部署后验证

### 1. 检查文件是否部署成功

```bash
# 检查wechat目录是否存在
ssh root@47.98.167.63 "ls -la /opt/ImageClassifierBackend/wechat/"

# 检查关键文件
ssh root@47.98.167.63 "ls -lh /opt/ImageClassifierBackend/wechat/*.html"
```

### 2. 检查文件权限

```bash
# 确保文件权限正确（如果需要）
ssh root@47.98.167.63 "chown -R root:root /opt/ImageClassifierBackend/wechat"
ssh root@47.98.167.63 "chmod -R 755 /opt/ImageClassifierBackend/wechat"
```

### 3. 验证文件内容

```bash
# 检查member.html是否存在
ssh root@47.98.167.63 "head -20 /opt/ImageClassifierBackend/wechat/member.html"

# 检查credits.html是否存在
ssh root@47.98.167.63 "head -20 /opt/ImageClassifierBackend/wechat/credits.html"
```

---

## 📝 需要部署的文件

以下文件需要部署到App服务器：

- ✅ `member.html` - 开通会员页面
- ✅ `credits.html` - 购买额度页面
- ✅ `credits_info.html` - 额度信息页面
- ✅ `pay-test.html` - 支付测试页面（可选）
- ✅ `README.md` - 说明文档（可选）
- ❌ `*.md` - 其他文档文件（可选，建议不部署）
- ❌ `imageclassify.png` - 图片文件（较大，可选）

---

## 🔧 配置FastAPI静态文件服务

部署完成后，需要在 `app/main.py` 中配置静态文件服务：

```python
from fastapi.staticfiles import StaticFiles
import os

# 配置微信页面静态文件服务
wechat_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wechat")
if os.path.exists(wechat_path):
    app.mount("/wechat", StaticFiles(directory=wechat_path), name="wechat")
    logger.info(f"微信页面静态文件服务已启用: {wechat_path}")
```

---

## 🧪 测试访问

部署完成后，测试页面是否可以正常访问：

```bash
# 测试member.html
curl http://47.98.167.63:8000/wechat/member.html

# 测试credits.html
curl http://47.98.167.63:8000/wechat/credits.html

# 测试credits_info.html
curl http://47.98.167.63:8000/wechat/credits_info.html
```

---

## 📋 部署检查清单

- [ ] 确认App服务器IP地址：`47.98.167.63`
- [ ] 确认部署路径：`/opt/ImageClassifierBackend/wechat/`
- [ ] 执行部署命令（scp或rsync）
- [ ] 检查文件是否部署成功
- [ ] 检查文件权限
- [ ] 配置FastAPI静态文件服务（如果需要）
- [ ] 重启FastAPI服务（如果已运行）
- [ ] 测试页面访问

---

## ⚠️ 注意事项

1. **文件权限**：确保文件权限正确，FastAPI服务可以读取
2. **路径配置**：确保FastAPI配置的静态文件路径正确
3. **服务重启**：如果FastAPI服务已运行，配置静态文件后需要重启服务
4. **HTTPS配置**：如果通过Nginx/lighttpd提供静态文件，需要配置HTTPS

---

## 🔄 更新部署

如果需要更新文件，可以：

```bash
# 使用rsync增量同步（推荐）
rsync -avz wechat/ root@47.98.167.63:/opt/ImageClassifierBackend/wechat/

# 或使用scp覆盖
scp -r wechat root@47.98.167.63:/opt/ImageClassifierBackend/
```

---

**最后更新**: 2024-11-18  
**维护者**: ImageClassifier Team

