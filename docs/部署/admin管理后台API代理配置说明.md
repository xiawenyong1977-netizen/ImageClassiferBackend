# Admin管理后台API代理配置说明

## 📋 配置概述

**配置时间**: 2025-11-18  
**问题**: HTTP页面（admin.xintuxiangce.top）访问HTTPS API（api.aifuture.net.cn）存在混合内容问题  
**解决方案**: 通过lighttpd反向代理，API请求使用同源访问

## 🔧 配置方案

### 方案说明

由于 `admin.xintuxiangce.top` 使用HTTP协议，而 `api.aifuture.net.cn` 使用HTTPS协议，浏览器会阻止这种混合内容请求。

**解决方案**: 通过lighttpd反向代理，将 `/api/` 路径的请求代理到app服务器的8000端口，这样API调用就是同源的（HTTP -> HTTP）。

### 配置内容

#### 1. Lighttpd虚拟主机配置

在 `/etc/lighttpd/conf.d/admin-vhost.conf` 中添加API反向代理：

```lighttpd
$SERVER["socket"] == ":80" {
    $HTTP["host"] =~ "^(www\.)?admin\.xintuxiangce\.top$" {
        server.document-root = "/var/www/xintuxiangce/admin"
        index-file.names = ("index.html")
        server.follow-symlink = "enable"
        
        # API请求反向代理到app服务器8000端口
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

#### 2. Admin页面API地址配置

**修改前**:
```javascript
apiUrl: 'https://api.aifuture.net.cn'
```

**修改后**:
```javascript
apiUrl: window.location.origin  // 使用同源，通过lighttpd反向代理
```

这样API调用路径为：
- `http://admin.xintuxiangce.top/api/v1/health`
- `http://admin.xintuxiangce.top/api/v1/stats/today`
- 等等...

## 🔄 请求流程

```
浏览器
  ↓ HTTP请求
http://admin.xintuxiangce.top/api/v1/health
  ↓
Lighttpd (web服务器)
  ↓ 反向代理
http://47.98.167.63:8000/api/v1/health
  ↓
FastAPI (app服务器)
  ↓ 响应
JSON数据
  ↓ 通过lighttpd返回
浏览器
```

## ✅ 配置验证

### 1. 检查lighttpd配置

```bash
lighttpd -t -f /etc/lighttpd/lighttpd.conf
```

应该输出：`Syntax OK`

### 2. 检查服务状态

```bash
systemctl status lighttpd
```

应该显示：`Active: active (running)`

### 3. 测试API代理

```bash
# 测试health接口
curl -H "Host: admin.xintuxiangce.top" http://localhost/api/v1/health

# 应该返回JSON:
# {"status":"healthy","timestamp":"...","database":"connected","model_api":"available"}
```

### 4. 浏览器测试

在浏览器中访问 `http://admin.xintuxiangce.top/`，打开开发者工具：

1. **Network标签**: 查看API请求是否成功（状态码200）
2. **Console标签**: 检查是否有CORS或混合内容错误
3. **健康状态**: 页面上的健康状态应该正常显示，不再一直转圈

## 📝 已更新的文件

### 服务器端

- ✅ `/etc/lighttpd/conf.d/admin-vhost.conf` - 添加了API反向代理配置

### 客户端（admin页面）

- ✅ `/var/www/xintuxiangce/admin/app.js` - API地址改为 `window.location.origin`
- ✅ `/var/www/xintuxiangce/admin/login.html` - API地址改为 `window.location.origin`
- ✅ `/var/www/xintuxiangce/admin/index.html` - placeholder更新

## ⚠️ 注意事项

1. **API路径**: 所有API请求必须以 `/api/` 开头，才会被代理
2. **同源策略**: 使用同源访问避免了CORS和混合内容问题
3. **性能**: 通过lighttpd代理，性能影响很小
4. **安全性**: 代理在服务器内部进行，不暴露8000端口到外网

## 🔍 故障排查

### 问题1: API请求返回404

**检查**:
```bash
# 检查代理配置是否正确
grep -A 3 'proxy.server' /etc/lighttpd/conf.d/admin-vhost.conf

# 检查app服务器是否可访问
curl http://47.98.167.63:8000/api/v1/health
```

### 问题2: API请求超时

**检查**:
```bash
# 检查app服务器8000端口是否监听
ssh root@app "netstat -tlnp | grep ':8000'"

# 检查防火墙
ssh root@web "telnet 47.98.167.63 8000"
```

### 问题3: 返回HTML而不是JSON

**原因**: 代理规则可能被其他配置覆盖

**解决**: 检查配置优先级，确保admin-vhost配置在最后加载

## 🎯 优势

1. ✅ **无混合内容问题**: HTTP页面访问HTTP API
2. ✅ **无CORS问题**: 同源访问
3. ✅ **安全性**: 不暴露8000端口到外网
4. ✅ **灵活性**: 可以随时切换API地址
5. ✅ **性能**: lighttpd代理性能优秀

---

**配置完成时间**: 2025-11-18  
**维护者**: ImageClassifier Team

