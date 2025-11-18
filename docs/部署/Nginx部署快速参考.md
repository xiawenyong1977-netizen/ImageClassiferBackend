# Nginx部署快速参考

## 📋 当前状态

### ✅ 已完成
- ✅ Nginx 已安装并启动
- ✅ Nginx 配置文件已创建：`/etc/nginx/conf.d/api-aifuture.conf`
- ✅ 防火墙端口已开放（80, 443）
- ✅ certbot 已安装
- ✅ 证书自动续期 timer 已配置（`certbot-renew.timer`）

### ⚠️ 待完成
- ⚠️ **配置阿里云安全组开放80和443端口**（必须）
- ⚠️ 确认DNS解析：`api.aifuture.net.cn` -> `47.98.167.63`
- ⚠️ 获取Let's Encrypt证书

## 🚀 快速操作指南

### 1. 配置阿里云安全组（必须）

**步骤：**
1. 登录阿里云控制台
2. 进入 ECS 实例管理
3. 找到服务器实例（IP: 47.98.167.63）
4. 点击"安全组" → "配置规则"
5. 添加入站规则：

   **规则1：HTTP**
   - 端口范围：`80/80`
   - 协议类型：`TCP`
   - 授权对象：`0.0.0.0/0`
   - 描述：`HTTP for Let's Encrypt`

   **规则2：HTTPS**
   - 端口范围：`443/443`
   - 协议类型：`TCP`
   - 授权对象：`0.0.0.0/0`
   - 描述：`HTTPS`

### 2. 确认DNS解析

```bash
# 检查DNS解析
nslookup api.aifuture.net.cn

# 应该返回：47.98.167.63
```

### 3. 获取SSL证书

**方法1：使用脚本（推荐）**

```bash
# 在服务器上执行
/root/get-ssl-certificate.sh
```

**方法2：手动执行**

```bash
certbot --nginx -d api.aifuture.net.cn \
    --non-interactive \
    --agree-tos \
    --email admin@aifuture.net.cn \
    --redirect
```

### 4. 验证配置

```bash
# 检查证书
certbot certificates

# 测试HTTPS访问
curl -I https://api.aifuture.net.cn/

# 检查Nginx状态
systemctl status nginx
```

## 📁 文件位置

### 配置文件
- Nginx配置：`/etc/nginx/conf.d/api-aifuture.conf`
- Nginx主配置：`/etc/nginx/nginx.conf`

### 证书文件（获取成功后）
- 证书：`/etc/letsencrypt/live/api.aifuture.net.cn/fullchain.pem`
- 私钥：`/etc/letsencrypt/live/api.aifuture.net.cn/privkey.pem`
- 证书链：`/etc/letsencrypt/live/api.aifuture.net.cn/chain.pem`

### 日志文件
- Nginx访问日志：`/var/log/nginx/api-aifuture-access.log`
- Nginx错误日志：`/var/log/nginx/api-aifuture-error.log`
- Certbot日志：`/var/log/letsencrypt/letsencrypt.log`

### 脚本文件
- 证书获取脚本：`/root/get-ssl-certificate.sh`
- 本地配置文件：`tools/部署/nginx-api-aifuture.conf`
- 完整HTTPS配置：`tools/部署/nginx-api-aifuture-https.conf`

## 🔧 常用命令

### Nginx管理

```bash
# 测试配置
nginx -t

# 重载配置（不中断服务）
systemctl reload nginx

# 重启服务
systemctl restart nginx

# 查看状态
systemctl status nginx

# 查看日志
tail -f /var/log/nginx/api-aifuture-access.log
tail -f /var/log/nginx/api-aifuture-error.log
```

### 证书管理

```bash
# 查看所有证书
certbot certificates

# 手动续期
certbot renew

# 测试续期（不实际续期）
certbot renew --dry-run

# 查看证书有效期
openssl x509 -in /etc/letsencrypt/live/api.aifuture.net.cn/cert.pem -noout -dates
```

### 证书自动续期

```bash
# 检查timer状态
systemctl status certbot-renew.timer

# 启用自动续期（通常已自动启用）
systemctl enable certbot-renew.timer
systemctl start certbot-renew.timer

# 查看所有timers
systemctl list-timers
```

## 🐛 故障排查

### 问题1：证书获取失败

**错误信息：**
```
Timeout during connect (likely firewall problem)
```

**解决方案：**
1. 检查阿里云安全组是否开放80端口
2. 检查DNS解析是否正确
3. 检查防火墙规则：`firewall-cmd --list-ports`

### 问题2：Nginx配置错误

```bash
# 测试配置
nginx -t

# 查看详细错误
nginx -T 2>&1 | grep error
```

### 问题3：HTTPS无法访问

```bash
# 检查443端口是否监听
netstat -tlnp | grep 443
# 或
ss -tlnp | grep 443

# 检查证书文件是否存在
ls -la /etc/letsencrypt/live/api.aifuture.net.cn/

# 检查Nginx错误日志
tail -50 /var/log/nginx/api-aifuture-error.log
```

### 问题4：反向代理不工作

```bash
# 检查FastAPI服务是否运行
systemctl status image-classifier

# 检查8000端口
netstat -tlnp | grep 8000

# 测试本地连接
curl http://localhost:8000/docs
```

## 📊 验证清单

获取证书后，请验证以下项目：

- [ ] 证书已成功获取：`certbot certificates`
- [ ] HTTPS可以访问：`curl -I https://api.aifuture.net.cn/`
- [ ] HTTP自动重定向到HTTPS：`curl -I http://api.aifuture.net.cn/`
- [ ] API端点正常：`curl https://api.aifuture.net.cn/docs`
- [ ] 静态文件服务正常：`curl https://api.aifuture.net.cn/images/...`
- [ ] 证书自动续期已配置：`systemctl status certbot-renew.timer`
- [ ] 证书有效期检查：`openssl x509 -in /etc/letsencrypt/live/api.aifuture.net.cn/cert.pem -noout -dates`

## 🔗 相关文档

- 详细部署说明：`docs/部署/Nginx部署和证书配置说明.md`
- HTTPS配置方案：`docs/部署/FastAPI_HTTPS配置方案.md`
- Nginx vs Lighttpd对比：`docs/部署/Nginx_vs_Lighttpd对比.md`

---

**文档版本**: v1.0  
**创建日期**: 2025-01-XX  
**维护者**: ImageClassifier Team

