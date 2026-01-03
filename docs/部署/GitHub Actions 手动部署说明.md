# GitHub Actions 手动部署说明

## 概述

GitHub Actions 工作流支持手动触发部署，方便在需要时重新部署服务器，而无需创建新的 commit。

## 手动触发部署

### 方法一：通过 GitHub Web 界面（推荐）

1. **打开 GitHub 仓库页面**
   - 访问你的 GitHub 仓库：`https://github.com/你的用户名/ImageClassifierBackend`

2. **进入 Actions 页面**
   - 点击仓库顶部的 **"Actions"** 标签

3. **选择工作流**
   - 在左侧边栏选择 **"CI/CD Pipeline"** 工作流

4. **手动触发**
   - 点击右侧的 **"Run workflow"** 按钮
   - 选择要部署的分支（通常是 `main` 或 `master`）
   - **可选**：勾选 **"跳过测试直接部署"**（仅当代码已测试通过时使用）
   - 点击 **"Run workflow"** 按钮

5. **查看部署进度**
   - 工作流开始运行后，点击最新的运行记录查看进度
   - 等待部署完成

### 方法二：通过 GitHub CLI

```bash
# 安装 GitHub CLI（如果还没有）
# macOS: brew install gh
# Linux: 参考 https://cli.github.com/manual/installation

# 登录 GitHub
gh auth login

# 手动触发工作流（运行测试+部署）
gh workflow run "CI/CD Pipeline.yml" --ref main

# 手动触发工作流（跳过测试，直接部署）
gh workflow run "CI/CD Pipeline.yml" --ref main -f skip_tests=true
```

### 方法三：通过 API

```bash
# 设置 GitHub Token（需要 workflow 权限）
export GITHUB_TOKEN=your_github_token

# 手动触发工作流（运行测试+部署）
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/你的用户名/ImageClassifierBackend/actions/workflows/ci-cd.yml/dispatches \
  -d '{"ref":"main"}'

# 手动触发工作流（跳过测试，直接部署）
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/你的用户名/ImageClassifierBackend/actions/workflows/ci-cd.yml/dispatches \
  -d '{"ref":"main","inputs":{"skip_tests":"true"}}'
```

## 重新运行失败的部署

如果部署失败，可以重新运行：

1. **打开 Actions 页面**
   - 进入 GitHub 仓库的 **"Actions"** 标签

2. **找到失败的运行**
   - 点击失败的 workflow 运行记录

3. **重新运行**
   - 点击右上角的 **"Re-run all jobs"** 或 **"Re-run failed jobs"**

## 部署选项说明

### 跳过测试直接部署

- **何时使用**：当代码已经通过测试，只需要重新部署到服务器时
- **注意事项**：
  - 仅在确认代码已测试通过时使用
  - 跳过测试会直接执行部署步骤
  - 建议在紧急修复或配置更新时使用

### 运行测试+部署（默认）

- **何时使用**：正常部署流程，确保代码质量
- **流程**：
  1. 运行所有测试
  2. 测试通过后自动部署
  3. 测试失败则不会部署

## 部署流程

手动触发部署时，工作流会执行以下步骤：

1. **代码检出**
   - 从 GitHub 仓库检出最新代码

2. **生成部署版本**
   - 格式：`YYYYMMDD-HHMMSS-<commit_sha前8位>`
   - 例如：`20260103-221500-a1b2c3d4`

3. **创建部署包**
   - 复制 `app/`、`requirements.txt`、`gunicorn_config.py` 等必要文件
   - 创建部署脚本和回退脚本

4. **上传到服务器**
   - 通过 SSH 上传部署包到服务器临时目录

5. **执行部署**
   - 创建新版本目录
   - 安装/更新依赖（如果需要）
   - 切换 `current` 符号链接到新版本
   - 重启 systemd 服务
   - 健康检查

6. **清理**
   - 删除临时文件
   - 清理旧版本（保留最近 5 个版本）

## 查看部署状态

### 在 GitHub Actions 中查看

1. 进入 **Actions** 页面
2. 点击对应的 workflow 运行记录
3. 查看各个步骤的执行状态和日志

### 在服务器上查看

```bash
# SSH 连接到服务器
ssh user@your-server

# 查看服务状态
systemctl status image-classifier

# 查看服务日志
journalctl -u image-classifier -f

# 查看部署版本
ls -la /opt/ICBackend/versions/

# 查看当前版本
readlink -f /opt/ICBackend/current
```

## 回退到旧版本

如果新版本有问题，可以回退到之前的版本：

```bash
# SSH 连接到服务器
ssh user@your-server

# 查看可用版本
ls -la /opt/ICBackend/versions/

# 回退到指定版本（使用部署包中的回退脚本）
cd /tmp/deploy-<version>
./rollback.sh /opt/ICBackend <version_name>

# 或者手动回退
cd /opt/ICBackend
ln -sfn versions/<old_version> current
systemctl restart image-classifier
```

## 常见问题

### Q: 手动触发后，测试任务被跳过了，但部署任务还在等待？

A: 这是正常的。如果选择跳过测试，部署任务会立即开始，不等待测试任务完成。

### Q: 可以只运行测试，不部署吗？

A: 可以。只需要 push 代码到非 main/master 分支，或者创建 PR，这样只会运行测试，不会触发部署。

### Q: 部署失败后如何查看错误？

A: 
1. 在 GitHub Actions 中查看部署步骤的日志
2. SSH 到服务器查看服务日志：`journalctl -u image-classifier -n 100`
3. 检查部署目录：`ls -la /opt/ICBackend/versions/`

### Q: 如何查看部署历史？

A: 
1. GitHub Actions 页面会显示所有 workflow 运行历史
2. 服务器上：`ls -la /opt/ICBackend/versions/` 查看所有版本目录

## 参考

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [工作流语法](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [手动触发工作流](https://docs.github.com/en/actions/using-workflows/manually-running-a-workflow)

