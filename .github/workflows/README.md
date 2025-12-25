# GitHub Actions CI/CD 配置说明

## 概述

本项目配置了完整的 CI/CD 流水线，包括：
- ✅ 自动测试（每次 Push 和 PR）
- ✅ 自动部署（仅 main/master 分支）
- ✅ 版本化部署（支持回退）

## 工作流文件

- `.github/workflows/ci-cd.yml` - 主要的 CI/CD 工作流

## 功能说明

### 1. 测试阶段

- **触发条件**: 所有 Push 和 Pull Request
- **运行环境**: Ubuntu Latest + Python 3.8
- **测试内容**:
  - 代码语法检查
  - 单元测试（pytest）
  - 代码覆盖率报告

### 2. 部署阶段

- **触发条件**: 仅 main/master 分支的 Push
- **部署策略**: 版本化部署
  - 每次部署到新目录：`/opt/ImageClassifierBackend/versions/YYYYMMDD-HHMMSS-COMMIT`
  - 保留最近 5 个版本
  - 通过符号链接 `current` 指向当前版本
  - 支持一键回退

## 配置 GitHub Secrets

在 GitHub 仓库设置中添加以下 Secrets：

### 必需配置

1. **SSH_PRIVATE_KEY**
   - 部署服务器的 SSH 私钥
   - 用于连接服务器

2. **SSH_HOST**
   - 服务器 IP 地址或域名
   - 例如: `192.168.1.100` 或 `app.example.com`

3. **SSH_USER**
   - SSH 登录用户名
   - 例如: `root` 或 `deploy`

### 可选配置

4. **DEPLOY_DIR** (可选)
   - 部署目录路径
   - 默认: `/opt/ImageClassifierBackend`

5. **HEALTH_CHECK_URL** (可选)
   - 健康检查 URL
   - 例如: `https://api.example.com/api/v1/health`
   - 部署后会自动检查服务是否正常

## 部署目录结构

```
/opt/ImageClassifierBackend/
├── current -> versions/20250120-143022-abc12345/  # 符号链接指向当前版本
└── versions/
    ├── 20250120-143022-abc12345/  # 版本目录
    │   ├── app/
    │   ├── venv/
    │   ├── requirements.txt
    │   └── gunicorn_config.py
    ├── 20250120-120000-def67890/
    └── ...
```

## 手动部署

如果需要在服务器上手动部署，可以使用项目中的部署脚本：

```bash
# 1. 克隆或更新代码
cd /opt/ImageClassifierBackend
git pull

# 2. 运行部署脚本
./scripts/deploy-versioned.sh

# 或者指定版本
VERSION=20250120-143022-abc12345 ./scripts/deploy-versioned.sh
```

## 版本回退

### 通过脚本回退

```bash
# 查看所有版本
ls -la /opt/ImageClassifierBackend/versions/

# 回退到指定版本
/opt/ImageClassifierBackend/scripts/rollback.sh 20250120-120000-def67890
```

### 手动回退

```bash
# 1. 切换到旧版本目录
cd /opt/ImageClassifierBackend
ln -sfn versions/20250120-120000-def67890 current

# 2. 重启服务
systemctl restart image-classifier
```

## 服务管理

部署脚本会自动管理 systemd 服务 `image-classifier`。

### 常用命令

```bash
# 查看服务状态
systemctl status image-classifier

# 查看服务日志
journalctl -u image-classifier -f

# 重启服务
systemctl restart image-classifier

# 停止服务
systemctl stop image-classifier

# 启动服务
systemctl start image-classifier
```

## 故障排查

### 部署失败

1. 检查 SSH 连接
   ```bash
   ssh -i ~/.ssh/deploy_key user@server
   ```

2. 检查服务器目录权限
   ```bash
   ls -la /opt/ImageClassifierBackend
   ```

3. 查看 GitHub Actions 日志
   - 在 GitHub 仓库的 Actions 标签页查看详细日志

### 服务启动失败

1. 检查服务状态
   ```bash
   systemctl status image-classifier
   ```

2. 查看错误日志
   ```bash
   journalctl -u image-classifier -n 50
   ```

3. 检查环境变量
   ```bash
   cat /opt/ImageClassifierBackend/current/.env
   ```

4. 手动测试
   ```bash
   cd /opt/ImageClassifierBackend/current
   source venv/bin/activate
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## 版本清理

部署脚本会自动保留最近 5 个版本，旧版本会被自动清理。

如果需要手动清理：

```bash
cd /opt/ImageClassifierBackend/versions
# 查看所有版本
ls -lt
# 删除旧版本（谨慎操作）
rm -rf 20250119-*
```

## 注意事项

1. **首次部署**: 需要手动创建部署目录和配置 systemd 服务
2. **环境变量**: 确保服务器上的 `.env` 文件已正确配置
3. **数据库**: 确保数据库连接配置正确
4. **权限**: 确保部署用户有足够的权限
5. **备份**: 重要数据请提前备份

## 相关文件

- `.github/workflows/ci-cd.yml` - CI/CD 工作流配置
- `scripts/deploy-versioned.sh` - 版本化部署脚本
- `scripts/rollback.sh` - 版本回退脚本
- `pytest.ini` - pytest 测试配置
- `tests/` - 测试文件目录

