# Admin管理后台部署说明

## 📋 部署概述

**部署时间**: 2025-11-18  
**部署位置**: `root@web:/var/www/xintuxiangce/admin`  
**Web服务器**: Lighttpd

## 📁 部署文件

已部署以下文件到 `/var/www/xintuxiangce/admin/`：

- ✅ `index.html` - 管理后台主页面
- ✅ `login.html` - 登录页面
- ✅ `app.js` - JavaScript文件（83KB）
- ✅ `imagenet_classes.json` - ImageNet分类数据（23KB）
- ✅ `imagenet_classes.txt` - ImageNet分类数据（11KB）
- ✅ `imageclassify.png` - 应用图标（1.1MB）
- ✅ `README.md` - 使用说明

**总大小**: 约 1.2MB  
**文件数量**: 7个文件

## 🔐 文件权限

- **所有者**: `lighttpd:lighttpd`
- **目录权限**: `755` (drwxr-xr-x)
- **文件权限**: `755` (rwxr-xr-x)

## 🌐 访问路径

### 通过Lighttpd访问

如果Lighttpd配置了 `/var/www/xintuxiangce` 作为文档根目录，访问路径为：

- **主页面**: `http://域名/admin/index.html` 或 `http://域名/admin/`
- **登录页面**: `http://域名/admin/login.html`

### 配置示例

**Lighttpd配置** (`/etc/lighttpd/lighttpd.conf`):

```lighttpd
server.document-root = "/var/www/xintuxiangce"

# 或者使用别名
alias.url = (
    "/admin" => "/var/www/xintuxiangce/admin"
)
```

## 🔧 部署命令

### 手动部署（使用scp）

```bash
# 1. 创建目录
ssh root@web "mkdir -p /var/www/xintuxiangce/admin"

# 2. 上传文件
scp admin/index.html root@web:/var/www/xintuxiangce/admin/
scp admin/login.html root@web:/var/www/xintuxiangce/admin/
scp admin/app.js root@web:/var/www/xintuxiangce/admin/
scp admin/imagenet_classes.json root@web:/var/www/xintuxiangce/admin/
scp admin/imagenet_classes.txt root@web:/var/www/xintuxiangce/admin/
scp admin/imageclassify.png root@web:/var/www/xintuxiangce/admin/
scp admin/README.md root@web:/var/www/xintuxiangce/admin/

# 3. 设置权限
ssh root@web "chown -R lighttpd:lighttpd /var/www/xintuxiangce/admin"
ssh root@web "chmod -R 755 /var/www/xintuxiangce/admin"
```

### 使用rsync（推荐，如果可用）

```bash
rsync -avz --delete admin/ root@web:/var/www/xintuxiangce/admin/
ssh root@web "chown -R lighttpd:lighttpd /var/www/xintuxiangce/admin"
```

## ✅ 部署验证

### 1. 检查文件

```bash
ssh root@web "ls -lh /var/www/xintuxiangce/admin/"
```

应该看到7个文件。

### 2. 检查权限

```bash
ssh root@web "ls -ld /var/www/xintuxiangce/admin"
```

应该显示 `lighttpd:lighttpd` 所有者和 `755` 权限。

### 3. 测试访问

在浏览器中访问：
- `http://web服务器IP/admin/index.html`
- `http://web服务器IP/admin/login.html`

### 4. 检查文件内容

```bash
ssh root@web "head -5 /var/www/xintuxiangce/admin/index.html"
```

## 🔄 更新部署

当需要更新管理后台文件时：

### 方式1：重新上传单个文件

```bash
scp admin/index.html root@web:/var/www/xintuxiangce/admin/
```

### 方式2：重新上传所有文件

```bash
# 使用scp逐个上传
scp admin/* root@web:/var/www/xintuxiangce/admin/

# 或使用rsync（推荐）
rsync -avz --delete admin/ root@web:/var/www/xintuxiangce/admin/
```

### 方式3：创建部署脚本

创建 `tools/部署/deploy-admin.sh`:

```bash
#!/bin/bash
rsync -avz --delete admin/ root@web:/var/www/xintuxiangce/admin/
ssh root@web "chown -R lighttpd:lighttpd /var/www/xintuxiangce/admin"
echo "Admin管理后台部署完成"
```

## ⚠️ 注意事项

1. **文件路径**: 页面中的静态资源路径使用 `/static/` 绝对路径，需要确保Web服务器正确配置
2. **API地址**: `app.js` 中的API地址需要指向正确的后端服务器
3. **HTTPS**: 如果使用HTTPS，需要确保所有资源都通过HTTPS加载
4. **CORS**: 如果前后端分离部署，需要配置CORS允许跨域访问

## 🔗 相关文档

- 管理后台使用说明: `admin/README.md`
- Web目录拆分说明: `docs/部署/web目录拆分说明.md`

---

**部署完成时间**: 2025-11-18  
**维护者**: ImageClassifier Team

