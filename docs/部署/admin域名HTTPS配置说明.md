# admin.xintuxiangce.top HTTPS配置说明

## 问题描述

当访问 `https://admin.xintuxiangce.top` 时：
- 会自动跳转到 `https://www.xintuxiangce.top`
- 浏览器显示"不安全"警告

**原因**：
- Lighttpd的443端口只配置了 `www.xintuxiangce.top` 的SSL证书
- 访问 `admin.xintuxiangce.top` 时使用了错误的证书，导致证书不匹配

## 解决方案

为 `admin.xintuxiangce.top` 配置独立的HTTPS虚拟主机。

## 配置步骤

### 方法1：使用自动化脚本（推荐）

```bash
# 1. 上传脚本到服务器
scp tools/部署/setup-admin-https.sh root@web:/tmp/

# 2. 执行脚本
ssh root@web "bash /tmp/setup-admin-https.sh"
```

脚本会自动：
1. 检查并安装certbot（如需要）
2. 获取SSL证书
3. 更新Lighttpd配置
4. 测试并重启服务
5. 验证HTTPS访问

### 方法2：手动配置

#### 步骤1：获取SSL证书

```bash
ssh root@web

# 获取证书
certbot certonly \
    --webroot \
    -w /var/www/xintuxiangce/admin \
    -d admin.xintuxiangce.top \
    --email xiawenyong@xintuxiangce.top \
    --agree-tos \
    --non-interactive
```

#### 步骤2：更新Lighttpd配置

更新 `/etc/lighttpd/conf.d/admin-vhost.conf`：

```lighttpd
# HTTP 80 端口配置 - 重定向到HTTPS
$SERVER["socket"] == ":80" {
    $HTTP["host"] =~ "^(www\.)?admin\.xintuxiangce\.top$" {
        # 重定向HTTP到HTTPS
        url.redirect = ("^/(.*)" => "https://admin.xintuxiangce.top/$1")
        
        # 日志配置
        accesslog.filename = "/var/log/lighttpd/admin-access.log"
        server.errorlog = "/var/log/lighttpd/admin-error.log"
    }
}

# HTTPS 443 端口配置
$SERVER["socket"] == ":443" {
    $HTTP["host"] =~ "^(www\.)?admin\.xintuxiangce\.top$" {
        ssl.engine = "enable"
        ssl.pemfile = "/etc/letsencrypt/live/admin.xintuxiangce.top/fullchain.pem"
        ssl.privkey = "/etc/letsencrypt/live/admin.xintuxiangce.top/privkey.pem"
        ssl.cipher-list = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384"
        ssl.honor-cipher-order = "enable"
        ssl.use-sslv2 = "disable"
        ssl.use-sslv3 = "disable"
        
        server.document-root = "/var/www/xintuxiangce/admin"
        index-file.names = ("index.html")
        server.follow-symlink = "enable"
        
        # API请求反向代理到app服务器8000端口（通过HTTP内网访问）
        $HTTP["url"] =~ "^/api/" {
            proxy.server = ( "" => (
                ( "host" => "47.98.167.63", "port" => 8000 )
            ))
        }
        
        # 日志配置
        accesslog.filename = "/var/log/lighttpd/admin-access.log"
        server.errorlog = "/var/log/lighttpd/admin-error.log"
        
        # 允许访问的文件类型
        static-file.exclude-extensions = ( ".php", ".pl", ".fcgi", ".scgi" )
    }
}
```

#### 步骤3：测试并重启

```bash
# 测试配置
lighttpd -t -f /etc/lighttpd/lighttpd.conf

# 重启服务
systemctl restart lighttpd

# 验证HTTPS
curl -I https://admin.xintuxiangce.top
```

## 配置后的效果

### HTTP访问
- `http://admin.xintuxiangce.top` → 自动重定向到 `https://admin.xintuxiangce.top`

### HTTPS访问
- `https://admin.xintuxiangce.top` → 正常访问，显示安全锁
- API调用：前端通过HTTPS，API通过HTTPS（`https://api.aifuture.net.cn`）

## 证书自动续期

Let's Encrypt证书有效期为90天，需要定期续期：

```bash
# 测试续期
certbot renew --dry-run

# 手动续期
certbot renew

# 设置自动续期（通常已自动配置）
# 检查cron任务
crontab -l | grep certbot
```

## 注意事项

1. **DNS解析**：确保 `admin.xintuxiangce.top` 的DNS已正确解析到服务器IP
2. **防火墙**：确保80和443端口已开放
3. **Webroot目录**：确保 `/var/www/xintuxiangce/admin` 目录存在且可访问
4. **证书路径**：证书文件位于 `/etc/letsencrypt/live/admin.xintuxiangce.top/`

## 故障排查

### 问题1：证书获取失败

**可能原因**：
- DNS未解析
- 防火墙阻止80端口
- Webroot目录不可访问

**解决方法**：
```bash
# 检查DNS
nslookup admin.xintuxiangce.top

# 检查防火墙
iptables -L -n | grep 80
iptables -L -n | grep 443

# 检查目录权限
ls -la /var/www/xintuxiangce/admin
```

### 问题2：HTTPS访问仍显示不安全

**可能原因**：
- 证书未正确配置
- Lighttpd配置错误
- 证书文件权限问题

**解决方法**：
```bash
# 检查证书文件
ls -la /etc/letsencrypt/live/admin.xintuxiangce.top/

# 检查Lighttpd配置
lighttpd -t -f /etc/lighttpd/lighttpd.conf

# 检查Lighttpd日志
tail -f /var/log/lighttpd/admin-error.log
```

### 问题3：HTTP未重定向到HTTPS

**可能原因**：
- 重定向规则未生效
- 配置顺序问题

**解决方法**：
- 确保HTTP配置在HTTPS配置之前
- 检查重定向规则语法

## 相关文件

- 配置文件：`/etc/lighttpd/conf.d/admin-vhost.conf`
- 证书目录：`/etc/letsencrypt/live/admin.xintuxiangce.top/`
- 自动化脚本：`tools/部署/setup-admin-https.sh`

