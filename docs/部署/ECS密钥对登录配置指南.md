# ECS密钥对登录配置指南

## 📋 概述

ECS密钥对登录是阿里云提供的一种安全的SSH登录方式，使用RSA密钥对替代密码登录，更加安全可靠。

**优势**：
- ✅ 更安全：密钥长度2048位，破解难度高
- ✅ 方便管理：可复用同一密钥对管理多台ECS
- ✅ 自动登录：配置后无需每次输入密码
- ✅ 权限可控：可在控制台统一管理

---

## 🔑 方式一：在控制台创建密钥对（推荐）

### 步骤1：创建密钥对

1. **登录阿里云控制台**
   - 访问：https://ecs.console.aliyun.com/
   - 选择您的地域（如：华北2-北京）

2. **进入密钥对管理**
   - 点击左侧菜单 **"网络与安全"** → **"密钥对"**
   - 或直接访问：https://ecs.console.aliyun.com/#/keyPair/region/cn-hangzhou

3. **创建密钥对**
   - 点击 **"创建密钥对"** 按钮
   - 输入密钥对名称（如：`my-ecs-key`）
   - 选择 **"自动新建密钥对"**
   - 点击 **"确定"**

4. **下载私钥文件**
   - ⚠️ **重要**：私钥只会显示一次，请立即下载！
   - 系统会自动下载 `my-ecs-key.pem` 文件
   - **妥善保管**：私钥文件不要丢失或泄露

### 步骤2：绑定密钥对到ECS实例

#### 方式A：创建实例时绑定（新实例）

1. 在创建ECS实例时，选择 **"密钥对"** 登录方式
2. 选择刚才创建的密钥对名称
3. 完成实例创建

#### 方式B：已有实例绑定（现有实例）

1. **停止实例**（如果正在运行）
   - 进入 **ECS实例列表**
   - 找到目标实例
   - 点击 **"停止"** 并确认

2. **绑定密钥对**
   - 选择实例，点击 **"更多"** → **"网络和安全组"** → **"替换密钥对"**
   - 或：点击实例 → **"连接信息"** → **"绑定密钥对"**
   - 选择创建的密钥对
   - 点击 **"确定"**

3. **启动实例**
   - 绑定完成后，启动实例

### 步骤3：配置本地私钥

#### Windows用户（PowerShell）

1. **创建`.ssh`目录**（如果不存在）
   ```powershell
   # 在用户主目录创建.ssh文件夹
   mkdir $env:USERPROFILE\.ssh
   ```

2. **复制私钥文件**
   ```powershell
   # 将下载的.pem文件复制到.ssh目录
   copy "C:\Users\YourName\Downloads\my-ecs-key.pem" "$env:USERPROFILE\.ssh\my-ecs-key.pem"
   ```

3. **设置私钥权限**（重要！）
   ```powershell
   # Windows PowerShell 设置文件权限
   icacls "$env:USERPROFILE\.ssh\my-ecs-key.pem" /inheritance:r
   icacls "$env:USERPROFILE\.ssh\my-ecs-key.pem" /grant:r "$env:USERNAME:(R)"
   ```

4. **测试SSH连接**
   ```powershell
   # 使用密钥登录（替换为您的ECS公网IP）
   ssh -i "$env:USERPROFILE\.ssh\my-ecs-key.pem" root@123.57.68.4
   ```

#### Linux/macOS用户

1. **复制私钥到.ssh目录**
   ```bash
   # 创建.ssh目录（如果不存在）
   mkdir -p ~/.ssh
   
   # 复制私钥文件
   cp ~/Downloads/my-ecs-key.pem ~/.ssh/my-ecs-key.pem
   ```

2. **设置正确的权限**（非常重要！）
   ```bash
   # 设置私钥文件权限为600（只有所有者可读写）
   chmod 600 ~/.ssh/my-ecs-key.pem
   
   # 设置.ssh目录权限为700
   chmod 700 ~/.ssh
   ```

3. **测试SSH连接**
   ```bash
   ssh -i ~/.ssh/my-ecs-key.pem root@123.57.68.4
   ```

### 步骤4：配置SSH配置文件（可选，推荐）

配置SSH config可以简化登录命令。

#### Windows用户（PowerShell）

创建或编辑 `$env:USERPROFILE\.ssh\config` 文件：

```powershell
# 创建配置文件
notepad $env:USERPROFILE\.ssh\config
```

**配置文件内容**：
```
Host my-ecs
    HostName 123.57.68.4
    User root
    IdentityFile C:\Users\YourName\.ssh\my-ecs-key.pem
    IdentitiesOnly yes
```

**使用方法**：
```powershell
# 直接使用别名登录
ssh my-ecs
```

#### Linux/macOS用户

编辑 `~/.ssh/config` 文件：

```bash
# 编辑配置文件
vim ~/.ssh/config
```

**配置文件内容**：
```
Host my-ecs
    HostName 123.57.68.4
    User root
    IdentityFile ~/.ssh/my-ecs-key.pem
    IdentitiesOnly yes
```

**使用方法**：
```bash
# 直接使用别名登录
ssh my-ecs
```

---

## 🔑 方式二：使用现有公钥导入

如果您已经有一个SSH密钥对，可以将公钥导入到阿里云。

### 步骤1：生成密钥对（如果还没有）

#### Windows（使用OpenSSH，Windows 10+）

```powershell
# 生成新的SSH密钥对
ssh-keygen -t rsa -b 2048 -f $env:USERPROFILE\.ssh\my-key

# 会生成两个文件：
# - my-key (私钥，保密)
# - my-key.pub (公钥，可分享)
```

#### Linux/macOS

```bash
# 生成新的SSH密钥对
ssh-keygen -t rsa -b 2048 -f ~/.ssh/my-key

# 会生成两个文件：
# - my-key (私钥，保密)
# - my-key.pub (公钥，可分享)
```

### 步骤2：查看公钥内容

#### Windows

```powershell
# 查看公钥内容
cat $env:USERPROFILE\.ssh\my-key.pub
```

#### Linux/macOS

```bash
# 查看公钥内容
cat ~/.ssh/my-key.pub
```

**公钥格式示例**：
```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... your_email@example.com
```

### 步骤3：导入公钥到阿里云

1. **进入密钥对管理**
   - 访问：https://ecs.console.aliyun.com/#/keyPair/region/cn-hangzhou
   - 点击 **"创建密钥对"**

2. **导入公钥**
   - 选择 **"导入已有密钥对"**
   - 输入密钥对名称（如：`my-imported-key`）
   - 粘贴您的公钥内容（完整的一行）
   - 点击 **"确定"**

3. **绑定到ECS实例**（参考方式一的步骤2）

---

## 🔧 常见问题排查

### 问题1：提示"Permission denied (publickey)"

**可能原因**：
- 私钥文件权限不正确
- 私钥路径错误
- 密钥对未正确绑定到ECS实例

**解决方法**：

1. **检查私钥文件权限**
   ```bash
   # Linux/macOS
   ls -l ~/.ssh/my-ecs-key.pem
   # 应该是 -rw------- (600)
   chmod 600 ~/.ssh/my-ecs-key.pem
   ```

   ```powershell
   # Windows PowerShell
   icacls "$env:USERPROFILE\.ssh\my-ecs-key.pem"
   ```

2. **使用详细模式查看错误**
   ```bash
   ssh -v -i ~/.ssh/my-ecs-key.pem root@123.57.68.4
   ```

3. **检查密钥对是否绑定**
   - 登录阿里云控制台
   - 查看ECS实例详情 → 连接信息
   - 确认已绑定密钥对

### 问题2：Windows提示"Bad permissions. Try removing permissions for group and others"

**解决方法**：
```powershell
# 移除继承权限并只授予当前用户读取权限
icacls "$env:USERPROFILE\.ssh\my-ecs-key.pem" /inheritance:r
icacls "$env:USERPROFILE\.ssh\my-ecs-key.pem" /grant:r "$env:USERNAME:(R)"
```

### 问题3：连接时仍要求输入密码

**可能原因**：
- 使用了错误的私钥文件
- SSH config配置不正确

**解决方法**：

1. **明确指定私钥文件**
   ```bash
   ssh -i ~/.ssh/my-ecs-key.pem -v root@123.57.68.4
   ```

2. **检查SSH config配置**
   ```bash
   cat ~/.ssh/config
   ```

### 问题4：首次连接提示"The authenticity of host can't be established"

**这是正常的**，输入 `yes` 确认即可。系统会将服务器指纹保存到 `~/.ssh/known_hosts` 文件中。

---

## 🔒 安全建议

### 1. 保护私钥文件

- ✅ **不要分享**：私钥文件仅限个人使用
- ✅ **妥善保管**：建议备份到安全位置（加密存储）
- ✅ **设置权限**：私钥文件权限设置为 600（仅所有者可读写）
- ✅ **定期更换**：建议定期更换密钥对

### 2. 禁用密码登录（可选，更安全）

绑定密钥对后，可以禁用密码登录：

1. **SSH到ECS实例**
   ```bash
   ssh -i ~/.ssh/my-ecs-key.pem root@123.57.68.4
   ```

2. **编辑SSH配置**
   ```bash
   sudo vim /etc/ssh/sshd_config
   ```

3. **修改配置**
   ```bash
   # 禁用密码登录
   PasswordAuthentication no
   PubkeyAuthentication yes
   ```

4. **重启SSH服务**
   ```bash
   sudo systemctl restart sshd
   ```

⚠️ **注意**：禁用密码登录前，确保密钥对登录已测试成功！

### 3. 使用多个密钥对

建议为不同用途创建不同的密钥对：
- 开发环境密钥对
- 生产环境密钥对
- 个人服务器密钥对

---

## 📝 快速命令参考

### Windows PowerShell

```powershell
# 生成新密钥对
ssh-keygen -t rsa -b 2048 -f $env:USERPROFILE\.ssh\my-key

# 查看公钥
cat $env:USERPROFILE\.ssh\my-key.pub

# 设置私钥权限
icacls "$env:USERPROFILE\.ssh\my-key" /inheritance:r
icacls "$env:USERPROFILE\.ssh\my-key" /grant:r "$env:USERNAME:(R)"

# 使用密钥登录
ssh -i "$env:USERPROFILE\.ssh\my-ecs-key.pem" root@123.57.68.4

# 配置SSH config后直接使用别名
ssh my-ecs
```

### Linux/macOS

```bash
# 生成新密钥对
ssh-keygen -t rsa -b 2048 -f ~/.ssh/my-key

# 查看公钥
cat ~/.ssh/my-key.pub

# 设置私钥权限
chmod 600 ~/.ssh/my-key
chmod 700 ~/.ssh

# 使用密钥登录
ssh -i ~/.ssh/my-ecs-key.pem root@123.57.68.4

# 配置SSH config后直接使用别名
ssh my-ecs
```

---

## ✅ 配置检查清单

完成配置后请检查：

- [ ] 在阿里云控制台创建了密钥对
- [ ] 下载并保存了私钥文件（.pem）
- [ ] 将密钥对绑定到ECS实例
- [ ] 私钥文件已复制到本地 `.ssh` 目录
- [ ] 私钥文件权限已正确设置（600）
- [ ] 测试SSH连接成功
- [ ] （可选）配置了SSH config文件简化登录

---

## 🎯 下一步

配置完成后，您可以：

1. **使用密钥对登录ECS**
   ```bash
   ssh my-ecs  # 如果配置了SSH config
   # 或
   ssh -i ~/.ssh/my-ecs-key.pem root@123.57.68.4
   ```

2. **部署应用**
   - 参考 `docs/DEPLOY.md` 进行应用部署
   - 使用 `deploy-to-server.sh` 脚本自动化部署

3. **配置自动化脚本**
   - 使用SSH密钥对进行自动化部署
   - 配置CI/CD流程

---

## 📚 相关文档

- [阿里云ECS密钥对文档](https://help.aliyun.com/document_detail/51793.html)
- [SSH密钥对最佳实践](https://help.aliyun.com/document_detail/51788.html)
- [服务器部署指南](./DEPLOY.md)

---

**祝您配置顺利！🚀**

