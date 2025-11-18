# Web目录拆分说明

## 📋 拆分概述

**拆分时间**: 2025-11-18  
**拆分原因**: 将管理后台页面和微信公众号页面分离，便于管理和维护  
**更新**: 2025-11-18 - 将 `admin` 和 `wechat` 目录提升到项目根目录，删除 `web` 目录

## 📁 拆分前结构

```
web/
├── index.html          # 管理后台主页面
├── login.html          # 登录页面
├── app.js              # 管理后台JS
├── member.html         # 微信公众号-会员页面
├── credits.html        # 微信公众号-购买额度
├── credits_info.html   # 微信公众号-额度信息
├── pay-test.html       # 支付测试
├── imagenet_classes.json
├── imagenet_classes.txt
├── imageclassify.png
└── README.md
```

## 📁 最终结构（项目根目录）

```
ImageClassifierBackend/
├── admin/              # 管理后台目录
│   ├── index.html
│   ├── login.html
│   ├── app.js
│   ├── imagenet_classes.json
│   ├── imagenet_classes.txt
│   ├── imageclassify.png
│   └── README.md
├── wechat/             # 微信公众号目录
│   ├── member.html
│   ├── credits.html
│   ├── credits_info.html
│   ├── pay-test.html
│   ├── imageclassify.png
│   └── README.md
├── app/                # 后端应用
├── docs/               # 文档
└── tools/              # 工具脚本
```

## ✅ 拆分完成情况

### 管理后台文件（admin/）

- ✅ `index.html` - 主页面
- ✅ `login.html` - 登录页面
- ✅ `app.js` - JavaScript文件
- ✅ `imagenet_classes.json` - 分类数据
- ✅ `imagenet_classes.txt` - 分类数据
- ✅ `imageclassify.png` - 图标
- ✅ `README.md` - 使用说明

### 微信公众号文件（wechat/）

- ✅ `member.html` - 开通会员页面
- ✅ `credits.html` - 购买额度页面
- ✅ `credits_info.html` - 额度信息页面
- ✅ `pay-test.html` - 支付测试页面
- ✅ `imageclassify.png` - 图标
- ✅ `README.md` - 使用说明

## 🔗 路径引用说明

### 静态资源路径

所有文件中的静态资源路径保持不变，使用绝对路径：

- **图标**: `/static/imageclassify.png`
- **JS文件**: `/static/app.js`（仅admin使用）
- **数据文件**: `/static/imagenet_classes.json`（仅admin使用）

这些路径需要通过Web服务器配置来映射到实际文件位置。

### 访问路径

**管理后台**：
- 主页面: `/static/admin/index.html` 或 `/admin/`
- 登录页: `/static/admin/login.html` 或 `/admin/login.html`

**微信公众号**：
- 会员页: `/wechat/member.html`
- 购买额度: `/wechat/credits.html`
- 额度信息: `/wechat/credits_info.html`

## ⚙️ 服务器配置更新

### Nginx配置

如果使用Nginx服务静态文件，需要更新配置：

```nginx
# 管理后台
location /static/admin/ {
    alias /opt/ImageClassifierBackend/admin/;
}

# 微信公众号
location /wechat/ {
    alias /opt/ImageClassifierBackend/wechat/;
}

# 或者统一映射（分别映射）
location /static/admin/ {
    alias /opt/ImageClassifierBackend/admin/;
}
location /wechat/ {
    alias /opt/ImageClassifierBackend/wechat/;
}
```

### FastAPI配置

如果通过FastAPI服务静态文件，需要在 `app/main.py` 中添加：

```python
# 管理后台静态文件
admin_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin")
if os.path.exists(admin_path):
    app.mount("/static/admin", StaticFiles(directory=admin_path), name="admin")

# 微信公众号静态文件
wechat_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wechat")
if os.path.exists(wechat_path):
    app.mount("/wechat", StaticFiles(directory=wechat_path), name="wechat")
```

## 📝 文档更新

已创建以下文档：

1. **`admin/README.md`** - 管理后台使用说明
2. **`wechat/README.md`** - 微信公众号页面说明

## ⚠️ 注意事项

1. **路径引用**: 所有文件中的路径引用保持不变，使用 `/static/` 绝对路径
2. **Web服务器配置**: 需要更新Web服务器配置以支持新的目录结构（从 `web/admin` 改为 `admin`，从 `web/wechat` 改为 `wechat`）
3. **图标文件**: `imageclassify.png` 已复制到两个目录，确保各自独立
4. **目录位置**: `admin` 和 `wechat` 目录现在位于项目根目录，与 `app`、`docs`、`tools` 等目录平级

## 🔄 后续工作

- [ ] 更新服务器上的Web服务器配置（Nginx/Lighttpd）
- [ ] 测试管理后台页面访问
- [ ] 测试微信公众号页面访问
- [ ] 验证所有静态资源加载正常

---

**拆分完成时间**: 2025-11-18  
**维护者**: ImageClassifier Team

