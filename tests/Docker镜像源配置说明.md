# Docker镜像源配置说明

当无法从Docker Hub拉取镜像时（如出现 `EOF`、`timeout` 等错误），需要配置Docker镜像源（镜像加速器）。

## Windows Docker Desktop配置方法

### 方法1：通过Docker Desktop GUI配置（推荐）

1. 打开 **Docker Desktop**
2. 点击右上角 **设置图标**（齿轮⚙️）
3. 选择 **Docker Engine**
4. 在JSON配置中添加以下内容：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.nju.edu.cn"
  ]
}
```

5. 点击 **Apply & Restart** 应用并重启Docker

### 方法2：直接编辑配置文件

配置文件位置：`%USERPROFILE%\.docker\daemon.json`

1. 创建或编辑该文件
2. 添加以下内容：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.nju.edu.cn"
  ]
}
```

3. 重启Docker Desktop

## 常用的国内Docker镜像源

| 镜像源 | 地址 | 说明 |
|--------|------|------|
| **DaoCloud** | `https://docker.m.daocloud.io` | 稳定快速，推荐 |
| **Docker Proxy** | `https://dockerproxy.com` | 新镜像源，速度快 |
| **上海交大** | `https://docker.mirrors.sjtug.sjtu.edu.cn` | 教育网用户推荐 |
| **南京大学** | `https://docker.nju.edu.cn` | 稳定可靠 |
| **阿里云** | `https://<你的ID>.mirror.aliyuncs.com` | 需要注册阿里云账号 |
| **腾讯云** | `https://mirror.ccs.tencentyun.com` | 需要腾讯云账号 |

## 验证配置

配置完成后，运行以下命令验证：

```powershell
docker info | Select-String -Pattern "Registry Mirrors"
```

应该能看到配置的镜像源地址。

## 使用镜像源拉取镜像

配置镜像源后，直接使用原命令即可：

```powershell
docker pull mysql:8.0
```

Docker会自动通过配置的镜像源拉取镜像。

## 临时使用镜像源（无需配置）

如果不想修改配置，也可以直接在拉取时指定镜像源：

```powershell
# 使用DaoCloud镜像源
docker pull docker.m.daocloud.io/library/mysql:8.0

# 拉取后重新打标签
docker tag docker.m.daocloud.io/library/mysql:8.0 mysql:8.0
```

## 故障排查

如果配置后仍然无法拉取：

1. **检查配置格式**：确保JSON格式正确，没有语法错误
2. **重启Docker**：配置后必须重启Docker Desktop
3. **检查网络**：确保可以访问镜像源地址
4. **尝试其他镜像源**：如果某个镜像源不稳定，尝试其他的
5. **查看日志**：在Docker Desktop中查看日志获取详细错误信息

## 推荐配置（中国大陆用户）

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com"
  ]
}
```

