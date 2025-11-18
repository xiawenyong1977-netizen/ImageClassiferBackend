# Lighttpd Admin域名配置说明

## 📋 配置概述

**配置时间**: 2025-11-18  
**域名**: `admin.xintuxiangce.top`  
**部署目录**: `/var/www/xintuxiangce/admin/`  
**协议**: HTTP (80端口，不使用HTTPS)

## ✅ 配置完成状态

- ✅ 虚拟主机配置文件已创建：`/etc/lighttpd/conf.d/admin-vhost.conf`
- ✅ 主配置文件已包含：`include "conf.d/admin-vhost.conf"`
- ✅ Lighttpd服务已启动并运行
- ✅ 80端口已监听
- ✅ 域名配置已生效

## 📁 配置文件位置

### 虚拟主机配置
- **文件**: `/etc/lighttpd/conf.d/admin-vhost.conf`
- **本地文件**: `tools/部署/lighttpd-admin-vhost.conf`

### 主配置文件
- **文件**: `/etc/lighttpd/lighttpd.conf`
- **包含语句**: `include "conf.d/admin-vhost.conf"`

## 🔧 配置内容

### HTTP 80端口配置

```lighttpd
$SERVER["socket"] == ":80" {
    $HTTP["host"] =~ "^(www\.)?admin\.xintuxiangce\.top$" {
        server.document-root = "/var/www/xintuxiangce/admin"
        index-file.names = ("index.html")
        server.follow-symlink = "enable"
        
        # 日志配置
        accesslog.filename = "/var/log/lighttpd/admin-access.log"
        server.errorlog = "/var/log/lighttpd/admin-error.log"
        
        # 允许访问的文件类型
        static-file.exclude-extensions = ( ".php", ".pl", ".fcgi", ".scgi" )
    }
}
```

### HTTPS配置（已禁用）

由于admin域名不使用SSL证书，HTTPS 443端口配置已被注释掉。如果需要启用HTTPS，需要：

1. 获取SSL证书：
   ```bash
   certbot certonly --webroot -w /var/www/xintuxiangce/admin -d admin.xintuxiangce.top
   ```

2. 取消注释HTTPS配置部分

## 🌐 访问方式

### 通过域名访问

- **主页面**: `http://admin.xintuxiangce.top/` 或 `http://admin.xintuxiangce.top/index.html`
- **登录页面**: `http://admin.xintuxiangce.top/login.html`

### 本地测试

```bash
# 使用curl测试
curl -H "Host: admin.xintuxiangce.top" http://localhost/

# 或直接访问
curl http://admin.xintuxiangce.top/
```

## 📝 配置步骤总结

1. **创建虚拟主机配置文件**
   ```bash
   scp tools/部署/lighttpd-admin-vhost.conf root@web:/etc/lighttpd/conf.d/admin-vhost.conf
   ```

2. **在主配置文件中添加include**
   ```bash
   echo 'include "conf.d/admin-vhost.conf"' >> /etc/lighttpd/lighttpd.conf
   ```

3. **测试配置**
   ```bash
   lighttpd -t -f /etc/lighttpd/lighttpd.conf
   ```

4. **启动/重启服务**
   ```bash
   systemctl restart lighttpd
   ```

## ✅ 验证方法

### 1. 检查配置语法
```bash
lighttpd -t -f /etc/lighttpd/lighttpd.conf
```
应该输出：`Syntax OK`

### 2. 检查服务状态
```bash
systemctl status lighttpd
```
应该显示：`Active: active (running)`

### 3. 检查端口监听
```bash
ss -tlnp | grep ':80 '
```
应该显示80端口正在监听

### 4. 测试域名访问
```bash
curl -H "Host: admin.xintuxiangce.top" http://localhost/
```
应该返回HTML内容

## 📊 日志文件

- **访问日志**: `/var/log/lighttpd/admin-access.log`
- **错误日志**: `/var/log/lighttpd/admin-error.log`

## ⚠️ 注意事项

1. **DNS配置**: 确保 `admin.xintuxiangce.top` 的A记录指向web服务器IP
2. **防火墙**: 确保80端口已开放
3. **文件权限**: admin目录文件所有者应为 `lighttpd:lighttpd`，权限为 `755`
4. **SSL证书**: 当前配置不使用HTTPS，如需HTTPS需要先获取证书

## 🔄 后续操作

如果需要启用HTTPS：

1. 获取SSL证书
2. 取消注释HTTPS配置部分
3. 更新证书路径
4. 重启lighttpd服务

---

**配置完成时间**: 2025-11-18  
**维护者**: ImageClassifier Team

