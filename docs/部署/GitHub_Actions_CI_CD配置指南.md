# GitHub Actions CI/CD 配置指南

## 📋 概述

本项目已配置完整的 CI/CD 流水线，实现：
- ✅ **自动测试**: 每次代码推送和 PR 时自动运行测试
- ✅ **自动部署**: main/master 分支推送时自动部署到服务器
- ✅ **版本化部署**: 每次部署到新目录，支持一键回退
- ✅ **健康检查**: 部署后自动检查服务状态

## 🚀 快速开始

### 1. 配置 GitHub Secrets

在 GitHub 仓库中配置以下 Secrets：

**路径**: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

#### 必需配置

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `SSH_PRIVATE_KEY` | 服务器 SSH 私钥（完整内容，包括 `-----BEGIN` 和 `-----END`） | 见下方说明 |
| `SSH_HOST` | 服务器 IP 或域名 | `192.168.1.100` 或 `app.example.com` |
| `SSH_USER` | SSH 登录用户名 | `root` 或 `deploy` |

#### 可选配置

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `DEPLOY_DIR` | 部署目录路径（默认: `/opt/ImageClassifierBackend`） | `/opt/ImageClassifierBackend` |
| `HEALTH_CHECK_URL` | 健康检查 URL | `https://api.example.com/api/v1/health` |

### 2. 生成 SSH 密钥对

如果还没有 SSH 密钥，在本地生成：

```bash
# 生成密钥对
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/github_deploy.pub user@server

# 或者手动添加
cat ~/.ssh/github_deploy.pub | ssh user@server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 3. 配置 GitHub Secret

复制私钥内容到 GitHub Secret：

```bash
# 查看私钥内容
cat ~/.ssh/github_deploy

# 复制完整内容（包括 -----BEGIN 和 -----END 行）
# 粘贴到 GitHub Secret: SSH_PRIVATE_KEY
```

### 4. 服务器准备

#### 创建部署目录

```bash
# SSH 登录服务器
ssh user@server

# 创建部署目录
sudo mkdir -p /opt/ImageClassifierBackend/versions
sudo chown -R $USER:$USER /opt/ImageClassifierBackend
```

#### 配置 systemd 服务（如果还没有）

创建服务文件 `/etc/systemd/system/image-classifier.service`:

```ini
[Unit]
Description=Image Classifier Backend Service
After=network.target mysql.service

[Service]
Type=notify
User=root
WorkingDirectory=/opt/ImageClassifierBackend/current
Environment="PATH=/opt/ImageClassifierBackend/current/venv/bin"
ExecStart=/opt/ImageClassifierBackend/current/venv/bin/gunicorn -c gunicorn_config.py app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable image-classifier
```

#### 配置环境变量

```bash
# 在部署目录创建 .env 文件
cd /opt/ImageClassifierBackend
cp env.example .env
nano .env  # 编辑配置
```

### 5. 测试部署

推送代码到 main/master 分支，GitHub Actions 会自动：

1. 运行测试
2. 如果测试通过，自动部署到服务器
3. 执行健康检查

查看部署状态：

- GitHub: `Actions` 标签页
- 服务器: `ls -la /opt/ImageClassifierBackend/versions/`

## 📁 部署目录结构

```
/opt/ImageClassifierBackend/
├── current -> versions/20250120-143022-abc12345/  # 符号链接
└── versions/
    ├── 20250120-143022-abc12345/  # 版本目录
    │   ├── app/                   # 应用代码
    │   ├── venv/                  # Python 虚拟环境
    │   ├── requirements.txt
    │   ├── gunicorn_config.py
    │   └── env.example
    ├── 20250120-120000-def67890/  # 旧版本（保留最近5个）
    └── ...
```

## 🔄 版本回退

### 方法 1: 使用回退脚本

```bash
# SSH 登录服务器
ssh user@server

# 查看所有版本
ls -la /opt/ImageClassifierBackend/versions/

# 回退到指定版本
/opt/ImageClassifierBackend/scripts/rollback.sh 20250120-120000-def67890
```

### 方法 2: 手动回退

```bash
# 切换到旧版本
cd /opt/ImageClassifierBackend
ln -sfn versions/20250120-120000-def67890 current

# 重启服务
sudo systemctl restart image-classifier
```

## 🛠️ 手动部署

如果需要手动部署（不使用 GitHub Actions）：

```bash
# 1. 克隆或更新代码
cd /opt/ImageClassifierBackend
git pull origin main

# 2. 运行部署脚本
chmod +x scripts/deploy-versioned.sh
./scripts/deploy-versioned.sh
```

## 📊 监控和日志

### 查看服务状态

```bash
# 服务状态
sudo systemctl status image-classifier

# 实时日志
sudo journalctl -u image-classifier -f

# 最近 100 行日志
sudo journalctl -u image-classifier -n 100
```

### 查看当前版本

```bash
# 查看当前版本
ls -la /opt/ImageClassifierBackend/current

# 查看所有版本
ls -lt /opt/ImageClassifierBackend/versions/
```

## 🔍 故障排查

### 部署失败

1. **检查 SSH 连接**
   ```bash
   ssh -i ~/.ssh/github_deploy user@server
   ```

2. **检查 GitHub Actions 日志**
   - 在 GitHub 仓库的 `Actions` 标签页查看详细错误信息

3. **检查服务器权限**
   ```bash
   ls -la /opt/ImageClassifierBackend
   ```

### 服务启动失败

1. **查看服务状态**
   ```bash
   sudo systemctl status image-classifier
   ```

2. **查看错误日志**
   ```bash
   sudo journalctl -u image-classifier -n 50 --no-pager
   ```

3. **检查环境变量**
   ```bash
   cat /opt/ImageClassifierBackend/current/.env
   ```

4. **手动测试启动**
   ```bash
   cd /opt/ImageClassifierBackend/current
   source venv/bin/activate
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### 健康检查失败

如果配置了 `HEALTH_CHECK_URL` 但检查失败：

1. 检查服务是否正常运行
2. 检查防火墙和端口配置
3. 检查 URL 是否正确
4. 可以暂时移除 `HEALTH_CHECK_URL` Secret，跳过健康检查

## 📝 工作流说明

### 测试阶段

- **触发**: 所有 Push 和 Pull Request
- **运行**: Ubuntu Latest + Python 3.8
- **步骤**:
  1. 代码检出
  2. Python 环境设置
  3. 依赖安装
  4. 代码检查（可选）
  5. 运行测试
  6. 生成覆盖率报告

### 部署阶段

- **触发**: 仅 main/master 分支的 Push
- **前提**: 测试必须通过
- **步骤**:
  1. 生成版本号（时间戳 + Git SHA）
  2. 设置 SSH
  3. 创建部署包
  4. 上传到服务器
  5. 执行部署脚本
  6. 健康检查
  7. 清理临时文件

## ⚙️ 自定义配置

### 修改保留版本数量

编辑 `.github/workflows/ci-cd.yml`，找到：

```yaml
# 清理旧版本（保留最近5个版本）
```

修改脚本中的 `KEEP_VERSIONS` 变量。

### 修改部署目录

1. 在 GitHub Secret 中设置 `DEPLOY_DIR`
2. 或修改工作流文件中的默认值

### 添加部署前/后钩子

在部署脚本中添加自定义命令：

```bash
# 部署前
echo "执行部署前操作..."

# 部署后
echo "执行部署后操作..."
```

## 🔐 安全建议

1. **SSH 密钥**: 使用专用密钥，不要使用个人密钥
2. **权限**: 使用最小权限原则，创建专用部署用户
3. **密钥轮换**: 定期轮换 SSH 密钥
4. **日志**: 定期清理和归档日志
5. **备份**: 重要数据定期备份

## 📚 相关文档

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [部署脚本说明](../scripts/deploy-versioned.sh)
- [回退脚本说明](../scripts/rollback.sh)
- [测试配置说明](../../pytest.ini)

## ❓ 常见问题

### Q: 如何跳过自动部署？

A: 在提交信息中添加 `[skip ci]` 或 `[skip deploy]`

### Q: 如何只运行测试不部署？

A: 推送到非 main/master 分支，或创建 Pull Request

### Q: 部署失败后如何重试？

A: 在 GitHub Actions 页面点击 "Re-run jobs"

### Q: 如何查看部署历史？

A: 在服务器上查看 `/opt/ImageClassifierBackend/versions/` 目录

### Q: 可以部署到多个服务器吗？

A: 可以，需要为每个服务器配置不同的 Secrets，并修改工作流文件

---

**配置完成后，每次推送到 main/master 分支都会自动测试和部署！** 🎉

