# 健康检查 URL 配置说明

## 📋 概述

`HEALTH_CHECK_URL` 用于在部署完成后验证生产服务器是否正常运行。本文档说明如何正确配置这个 URL。

## 🔍 HEALTH_CHECK_URL 的使用场景

### 执行时机

```
部署流程:
┌─────────────────────────────────────────┐
│ 1. 部署代码到服务器                       │
│    (通过 SSH 执行)                       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 2. 重启服务                              │
│    (在服务器上执行)                      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 3. 健康检查                              │
│    (在 GitHub Actions 虚拟机中执行)     │
│    curl $HEALTH_CHECK_URL                │
│    ↑                                     │
│    从 GitHub 访问生产服务器               │
└─────────────────────────────────────────┘
```

### 关键点

1. **健康检查在 GitHub Actions 虚拟机中执行**
   - 不是在测试环境中
   - 不是在服务器本地
   - 是从 GitHub 的虚拟机访问你的生产服务器

2. **需要写死生产服务器的域名**
   - 因为是从外部（GitHub）访问生产服务器
   - 必须使用可公开访问的 URL

## 🌐 URL 配置方式

### 方式 1: 使用域名（推荐）

```bash
# 在 GitHub Secrets 中配置
HEALTH_CHECK_URL=https://api.example.com/api/v1/health
```

**优点**:
- ✅ 使用域名，便于管理
- ✅ 如果服务器 IP 变化，无需修改配置
- ✅ 支持 HTTPS，更安全

**示例**:
```
https://api.xintuxiangce.top/api/v1/health
https://www.xintuxiangce.top/api/v1/health
```

### 方式 2: 使用 IP 地址

```bash
# 在 GitHub Secrets 中配置
HEALTH_CHECK_URL=http://192.168.1.100:8000/api/v1/health
```

**注意**:
- ⚠️ 如果服务器在公网，可以使用公网 IP
- ⚠️ 如果服务器在内网，GitHub Actions 无法访问
- ⚠️ 不推荐使用内网 IP

### 方式 3: 不配置（可选）

如果不配置 `HEALTH_CHECK_URL`，健康检查步骤会被跳过：

```yaml
if [ -n "$HEALTH_CHECK_URL" ]; then
  # 执行健康检查
else
  echo "跳过健康检查（未配置 HEALTH_CHECK_URL）"
fi
```

## 📝 配置步骤

### 1. 确定你的生产服务器 URL

首先确认你的生产服务器地址：

```bash
# 方式 1: 如果有域名
https://api.yourdomain.com/api/v1/health

# 方式 2: 如果有公网 IP
http://your-server-ip:8000/api/v1/health

# 方式 3: 测试健康检查接口
curl https://api.yourdomain.com/api/v1/health
```

### 2. 在 GitHub 配置 Secret

1. 进入 GitHub 仓库
2. 点击 `Settings` → `Secrets and variables` → `Actions`
3. 点击 `New repository secret`
4. 填写：
   - **Name**: `HEALTH_CHECK_URL`
   - **Value**: `https://api.yourdomain.com/api/v1/health`
5. 点击 `Add secret`

### 3. 验证配置

配置后，下次部署时会自动执行健康检查：

```
部署完成
  ↓
等待 10 秒（服务启动时间）
  ↓
执行健康检查
curl https://api.yourdomain.com/api/v1/health
  ↓
✓ 健康检查通过
```

## 🔧 健康检查接口要求

### 接口规范

你的健康检查接口应该：

1. **返回 200 状态码**（成功）
2. **响应时间合理**（< 5 秒）
3. **可公开访问**（不需要认证）

### 当前项目的健康检查接口

```python
# app/api/health.py
@router.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}
```

**访问示例**:
```bash
curl https://api.yourdomain.com/api/v1/health
# 返回: {"status":"healthy"}
```

## ⚠️ 常见问题

### Q1: 测试环境和生产环境的 URL 不同？

**A**: 这是正常的！

- **测试阶段**: 在 GitHub Actions 虚拟机中运行测试，使用测试数据库
- **部署阶段**: 部署到生产服务器，健康检查访问生产服务器 URL

```
测试阶段 (test job):
  └─ 运行在 GitHub Actions 虚拟机
  └─ 使用 MySQL 容器 (image_classifier_test)
  └─ 不涉及 HEALTH_CHECK_URL

部署阶段 (deploy job):
  └─ 部署到生产服务器
  └─ 健康检查从 GitHub 访问生产服务器
  └─ 使用 HEALTH_CHECK_URL (生产服务器地址)
```

### Q2: 服务器在内网，GitHub 无法访问？

**A**: 有几种解决方案：

#### 方案 1: 使用公网域名/IP

```bash
# 确保服务器有公网 IP 或域名
HEALTH_CHECK_URL=https://api.yourdomain.com/api/v1/health
```

#### 方案 2: 跳过健康检查

不配置 `HEALTH_CHECK_URL`，健康检查会被跳过：

```yaml
# 工作流会自动跳过
echo "跳过健康检查（未配置 HEALTH_CHECK_URL）"
```

#### 方案 3: 使用 SSH 在服务器本地检查

修改工作流，通过 SSH 在服务器本地执行健康检查：

```yaml
- name: Health check (via SSH)
  run: |
    ssh deploy-server "curl -f http://localhost:8000/api/v1/health"
```

### Q3: 健康检查失败会阻止部署吗？

**A**: 不会。当前配置中，健康检查失败只会显示警告：

```yaml
curl -f "$HEALTH_CHECK_URL" || {
  echo "警告: 健康检查失败，但部署已完成"
  exit 0  # 不会导致部署失败
}
```

如果需要健康检查失败时阻止部署，可以修改为：

```yaml
curl -f "$HEALTH_CHECK_URL" || {
  echo "错误: 健康检查失败"
  exit 1  # 会导致部署失败
}
```

### Q4: 如何测试健康检查 URL？

**A**: 在本地或服务器上测试：

```bash
# 测试健康检查接口
curl https://api.yourdomain.com/api/v1/health

# 应该返回:
# {"status":"healthy"}

# 检查状态码
curl -I https://api.yourdomain.com/api/v1/health
# 应该返回: HTTP/1.1 200 OK
```

### Q5: 可以使用相对路径吗？

**A**: 不可以。必须使用完整的 URL（包含协议和域名/IP）。

```bash
# ❌ 错误
HEALTH_CHECK_URL=/api/v1/health

# ✅ 正确
HEALTH_CHECK_URL=https://api.yourdomain.com/api/v1/health
```

## 🎯 推荐配置

### 生产环境

```bash
# GitHub Secret: HEALTH_CHECK_URL
https://api.yourdomain.com/api/v1/health
```

### 开发/测试环境（可选）

如果需要为不同环境配置不同的健康检查 URL，可以使用环境变量：

```yaml
# .github/workflows/ci-cd.yml
env:
  HEALTH_CHECK_URL: ${{ secrets.HEALTH_CHECK_URL_PRODUCTION }}
  # 或
  HEALTH_CHECK_URL: ${{ secrets.HEALTH_CHECK_URL_STAGING }}
```

## 📊 健康检查流程

### 完整流程

```
1. 部署代码到服务器 ✅
   ↓
2. 重启服务 ✅
   ↓
3. 等待 10 秒（服务启动时间）
   ↓
4. 从 GitHub Actions 执行健康检查
   curl https://api.yourdomain.com/api/v1/health
   ↓
5. 检查结果:
   ✅ 成功 (200) → 显示 "✓ 健康检查通过"
   ❌ 失败 → 显示 "警告: 健康检查失败，但部署已完成"
```

### 日志示例

**成功**:
```
执行健康检查...
✓ 健康检查通过
```

**失败**:
```
执行健康检查...
警告: 健康检查失败，但部署已完成
```

## 🔐 安全考虑

### HTTPS vs HTTP

```bash
# ✅ 推荐: 使用 HTTPS
HEALTH_CHECK_URL=https://api.yourdomain.com/api/v1/health

# ⚠️ 不推荐: 使用 HTTP（除非在内网）
HEALTH_CHECK_URL=http://api.yourdomain.com/api/v1/health
```

### 认证

如果健康检查接口需要认证，可以：

1. **使用公开的健康检查接口**（推荐）
   - 健康检查接口通常不需要认证
   - 只返回基本状态信息

2. **添加认证头**（如果需要）
   ```yaml
   curl -H "Authorization: Bearer $TOKEN" "$HEALTH_CHECK_URL"
   ```

## 📚 相关文档

- [GitHub Actions CI/CD 配置指南](./GitHub_Actions_CI_CD配置指南.md)
- [健康检查 API 文档](../../app/api/health.py)

---

**总结**: `HEALTH_CHECK_URL` 需要写死生产服务器的域名或 IP，因为健康检查是从 GitHub Actions 虚拟机访问你的生产服务器。**推荐使用 HTTPS 域名**。🌐

