# Git 工作流指南

## 📋 规范的开发流程

本文档说明如何使用分支和 Pull Request 进行规范的代码开发和部署。

## 🔄 标准工作流程

### 完整流程图

```
┌─────────────────────────────────────────────────────────┐
│ 1. 创建功能分支                                          │
│    git checkout -b feature/new-feature                  │
│                                                          │
│ 2. 开发新特性                                            │
│    # 修改代码...                                         │
│    git add .                                            │
│    git commit -m "Add new feature"                      │
│    git push origin feature/new-feature                  │
│                                                          │
│ 3. 创建 Pull Request                                     │
│    (在 GitHub 网页上创建 PR)                            │
│    feature/new-feature → main                           │
│                                                          │
│ 4. 自动触发测试 (pull_request 事件)                    │
│    ✅ 运行测试                                           │
│    ❌ 不部署 (等待审查)                                  │
│                                                          │
│ 5. 代码审查                                              │
│    (团队成员审查代码)                                    │
│                                                          │
│ 6. 合并到主分支                                          │
│    (在 GitHub 上点击 Merge)                             │
│                                                          │
│ 7. 自动触发测试和部署 (push 事件)                       │
│    ✅ 运行测试                                           │
│    ✅ 自动部署到生产环境                                 │
└─────────────────────────────────────────────────────────┘
```

## 📝 详细步骤

### 步骤 1: 创建功能分支

```bash
# 1. 确保主分支是最新的
git checkout main
git pull origin main

# 2. 创建并切换到新分支
git checkout -b feature/your-feature-name

# 分支命名规范：
# - feature/xxx    - 新功能
# - fix/xxx        - Bug 修复
# - hotfix/xxx     - 紧急修复
# - refactor/xxx   - 重构
# - docs/xxx       - 文档更新
```

**示例**:
```bash
git checkout -b feature/add-user-authentication
git checkout -b fix/login-bug
git checkout -b hotfix/critical-security-patch
```

### 步骤 2: 开发新特性

```bash
# 在功能分支上开发
# 修改代码文件...

# 提交更改
git add .
git commit -m "Add user authentication feature"

# 可以多次提交
git add app/api/auth.py
git commit -m "Implement JWT token generation"
git add tests/test_auth.py
git commit -m "Add authentication tests"

# 推送到远程分支
git push origin feature/your-feature-name
```

### 步骤 3: 创建 Pull Request

#### 方法 1: 在 GitHub 网页上创建

1. 推送代码后，GitHub 会显示提示：
   ```
   Compare & pull request
   ```

2. 点击创建 PR，填写：
   - **标题**: 清晰描述功能
   - **描述**: 详细说明改动内容
   - **目标分支**: `main` (或 `master`)
   - **审查者**: 选择代码审查人员

3. 点击 "Create pull request"

#### 方法 2: 使用 GitHub CLI

```bash
# 安装 GitHub CLI (gh)
# 然后运行:
gh pr create --title "Add user authentication" --body "详细描述..."
```

### 步骤 4: 自动测试（GitHub Actions）

创建 PR 后，GitHub Actions 会自动：

1. **触发 `pull_request` 事件**
2. **运行测试任务**:
   - 代码检出
   - 安装依赖
   - 运行 pytest 测试
   - 生成覆盖率报告

3. **不执行部署**（等待审查通过）

**查看测试结果**:
- 在 PR 页面查看测试状态
- 点击 "Checks" 标签查看详细日志

### 步骤 5: 代码审查

团队成员审查代码：

- ✅ **审查通过**: 点击 "Approve"
- ❌ **需要修改**: 添加评论，请求更改
- 💬 **讨论**: 在代码行上添加评论

**修改代码后更新 PR**:
```bash
# 在功能分支上继续修改
git add .
git commit -m "Fix review comments"
git push origin feature/your-feature-name
# PR 会自动更新，测试会重新运行
```

### 步骤 6: 合并到主分支

审查通过后，在 GitHub 上合并 PR：

1. 点击 "Merge pull request"
2. 选择合并方式：
   - **Create a merge commit** (推荐，保留完整历史)
   - **Squash and merge** (压缩提交)
   - **Rebase and merge** (线性历史)

3. 确认合并

### 步骤 7: 自动测试和部署

合并后，GitHub Actions 会自动：

1. **触发 `push` 事件** (main 分支)
2. **运行测试任务**:
   - 再次运行所有测试
   - 确保合并后代码正常
3. **执行部署任务**:
   - 生成版本号
   - 部署到服务器
   - 执行健康检查

**查看部署状态**:
- GitHub: `Actions` 标签页
- 服务器: `ls -la /opt/ImageClassifierBackend/versions/`

## 🎯 分支命名规范

### 推荐的分支命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能 | `feature/功能描述` | `feature/user-login` |
| Bug 修复 | `fix/问题描述` | `fix/memory-leak` |
| 紧急修复 | `hotfix/问题描述` | `hotfix/security-patch` |
| 重构 | `refactor/模块名` | `refactor/auth-module` |
| 文档 | `docs/文档类型` | `docs/api-documentation` |
| 测试 | `test/测试内容` | `test/integration-tests` |

### 命名建议

- ✅ 使用小写字母和连字符
- ✅ 使用描述性的名称
- ✅ 保持简短但清晰
- ❌ 避免使用特殊字符
- ❌ 避免过长的名称

**好的示例**:
```bash
feature/add-payment-gateway
fix/login-authentication-bug
hotfix/critical-database-connection
```

**不好的示例**:
```bash
new_feature          # 不够描述性
fix-bug              # 太模糊
feature/add-new-feature-that-allows-users-to-login-and-manage-their-account  # 太长
```

## 🔍 查看和管理分支

### 查看所有分支

```bash
# 本地分支
git branch

# 远程分支
git branch -r

# 所有分支（本地+远程）
git branch -a
```

### 切换分支

```bash
# 切换到主分支
git checkout main

# 切换到功能分支
git checkout feature/your-feature-name

# 创建并切换（一步完成）
git checkout -b feature/new-feature
```

### 删除分支

```bash
# 删除本地分支（已合并后）
git branch -d feature/your-feature-name

# 强制删除本地分支
git branch -D feature/your-feature-name

# 删除远程分支
git push origin --delete feature/your-feature-name
```

## 📊 GitHub Actions 工作流说明

### 当前配置的触发条件

```yaml
on:
  push:                    # 直接推送时
    branches:
      - main
      - master
      - develop
  pull_request:           # PR 创建/更新时
    branches:
      - main
      - master
      - develop
```

### 工作流执行流程

#### PR 阶段（pull_request 事件）

```
创建/更新 PR
  ↓
触发 pull_request 事件
  ↓
运行测试任务 ✅
  ├─ 代码检查
  ├─ 安装依赖
  ├─ 运行 pytest
  └─ 生成覆盖率报告
  ↓
不执行部署 ❌ (等待审查)
```

#### 合并后阶段（push 事件）

```
合并 PR 到 main
  ↓
触发 push 事件 (main 分支)
  ↓
运行测试任务 ✅
  ├─ 再次运行测试
  └─ 确保合并后正常
  ↓
执行部署任务 ✅
  ├─ 生成版本号
  ├─ 部署到服务器
  ├─ 重启服务
  └─ 健康检查
```

## 🚨 常见问题和解决方案

### 问题 1: PR 测试失败

**原因**: 代码有错误或测试不通过

**解决**:
```bash
# 1. 查看测试日志（GitHub Actions）
# 2. 在本地运行测试
pytest tests/ -v

# 3. 修复问题后重新提交
git add .
git commit -m "Fix test failures"
git push origin feature/your-feature-name
```

### 问题 2: 合并冲突

**原因**: 主分支有新的提交，与你的分支冲突

**解决**:
```bash
# 1. 更新主分支
git checkout main
git pull origin main

# 2. 回到功能分支
git checkout feature/your-feature-name

# 3. 合并主分支的更改
git merge main
# 或使用 rebase
git rebase main

# 4. 解决冲突后
git add .
git commit -m "Resolve merge conflicts"
git push origin feature/your-feature-name
```

### 问题 3: 部署失败

**原因**: 服务器配置问题或服务启动失败

**解决**:
1. 查看 GitHub Actions 部署日志
2. 检查服务器状态: `systemctl status image-classifier`
3. 查看服务器日志: `journalctl -u image-classifier -n 50`
4. 手动回退版本（如果需要）

### 问题 4: 忘记创建分支，直接在 main 上提交

**解决**:
```bash
# 1. 创建新分支（保留当前更改）
git checkout -b feature/your-feature-name

# 2. 推送新分支
git push origin feature/your-feature-name

# 3. 重置 main 分支到远程版本
git checkout main
git reset --hard origin/main
git push origin main --force  # 谨慎使用！

# 4. 在新分支上创建 PR
```

## 💡 最佳实践

### 1. 保持分支更新

```bash
# 定期从主分支拉取最新更改
git checkout feature/your-feature-name
git fetch origin
git merge origin/main
# 或使用 rebase
git rebase origin/main
```

### 2. 小步提交

```bash
# ✅ 好的做法：多次小提交
git commit -m "Add user model"
git commit -m "Add authentication logic"
git commit -m "Add tests for authentication"

# ❌ 不好的做法：一次大提交
git commit -m "Add everything"
```

### 3. 清晰的提交信息

```bash
# ✅ 好的提交信息
git commit -m "Add user authentication with JWT tokens"
git commit -m "Fix memory leak in image processing"
git commit -m "Update API documentation"

# ❌ 不好的提交信息
git commit -m "fix"
git commit -m "update"
git commit -m "changes"
```

### 4. 及时清理分支

```bash
# 合并后删除功能分支
git checkout main
git pull origin main
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## 📚 相关文档

- [GitHub Actions CI/CD 配置指南](../部署/GitHub_Actions_CI_CD配置指南.md)
- [Git 官方文档](https://git-scm.com/doc)
- [GitHub Pull Request 文档](https://docs.github.com/en/pull-requests)

## 🎓 快速参考

### 常用命令

```bash
# 创建功能分支
git checkout -b feature/your-feature

# 提交更改
git add .
git commit -m "Your commit message"
git push origin feature/your-feature

# 更新主分支
git checkout main
git pull origin main

# 更新功能分支
git checkout feature/your-feature
git merge main  # 或 git rebase main

# 删除已合并的分支
git branch -d feature/your-feature
```

### 工作流检查清单

- [ ] 从最新的 main 分支创建功能分支
- [ ] 使用描述性的分支名称
- [ ] 小步提交，清晰的提交信息
- [ ] 创建 PR 前确保测试通过
- [ ] PR 描述清晰，包含改动说明
- [ ] 及时响应审查意见
- [ ] 合并后删除功能分支

---

**遵循这个流程，可以确保代码质量，便于团队协作，并实现自动化部署！** 🚀

