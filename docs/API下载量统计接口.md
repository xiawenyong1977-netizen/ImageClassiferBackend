# 下载量统计API接口文档

> **重要提示**：官网用户下载时，请使用**公开接口**（无需认证），接口路径为：`/api/v1/stats/download-count/increment/public`



## 1. 增加下载量接口（公开接口，推荐官网使用）⭐

### 接口信息
- **URL**: `/api/v1/stats/download-count/increment/public`
- **方法**: `POST`
- **认证**: **无需认证**（公开接口，供官网用户下载时调用）

### 请求参数

#### Query参数（必填）
```
download_type: string (必填)
```
- **说明**: 下载类型
- **可选值**: 
  - `android` - Android平台
  - `windows` - Windows平台
- **示例**: `?download_type=android`

### 响应格式

#### 成功响应 (200 OK)
```json
{
  "success": true
}
```
**说明**：接口只返回成功状态，不返回统计数据。

#### 错误响应

**400 Bad Request** - 参数错误
```json
{
  "detail": "download_type必须是android或windows"
}
```

**500 Internal Server Error** - 服务器错误
```json
{
  "detail": "增加下载量失败"
}
```

### 调用示例

#### JavaScript示例（官网推荐使用）

**方式一：使用相对路径（推荐，通过当前域名 www.xintuxiangce.top 访问）**

如果 Lighttpd 已配置 API 转发，可以使用相对路径：
```javascript
// 增加Android下载量（无需认证）
async function incrementAndroidDownload() {
  try {
    const response = await fetch(
      '/api/v1/stats/download-count/increment/public?download_type=android',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (data.success) {
      console.log('下载量统计成功');
    }
    return data;
  } catch (error) {
    console.error('增加下载量失败:', error);
    // 失败不影响下载流程，静默处理
  }
}

// 增加Windows下载量（无需认证）
async function incrementWindowsDownload() {
  try {
    const response = await fetch(
      '/api/v1/stats/download-count/increment/public?download_type=windows',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (data.success) {
      console.log('下载量统计成功');
    }
    return data;
  } catch (error) {
    console.error('增加下载量失败:', error);
    // 失败不影响下载流程，静默处理
  }
}

// 在下载按钮点击时调用
document.getElementById('download-android-btn').addEventListener('click', async () => {
  // 先调用统计接口（异步，不阻塞下载）
  incrementAndroidDownload().catch(() => {}); // 静默失败，不影响下载
  
  // 执行实际的下载逻辑
  window.location.href = '/downloads/app-android.apk';
});

document.getElementById('download-windows-btn').addEventListener('click', async () => {
  // 先调用统计接口（异步，不阻塞下载）
  incrementWindowsDownload().catch(() => {}); // 静默失败，不影响下载
  
  // 执行实际的下载逻辑
  window.location.href = '/downloads/app-windows.exe';
});
```

**方式二：使用绝对路径（直接访问 API 服务器）**

如果 Lighttpd 未配置 API 转发，可以使用绝对路径（需要 CORS 支持）：
```javascript
// 增加Android下载量（无需认证）
async function incrementAndroidDownload() {
  try {
    const response = await fetch(
      'https://api.aifuture.net.cn/api/v1/stats/download-count/increment/public?download_type=android',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (data.success) {
      console.log('下载量统计成功');
    }
    return data;
  } catch (error) {
    console.error('增加下载量失败:', error);
    // 失败不影响下载流程，静默处理
  }
}

// 增加Windows下载量（无需认证）
async function incrementWindowsDownload() {
  try {
    const response = await fetch(
      'https://api.aifuture.net.cn/api/v1/stats/download-count/increment/public?download_type=windows',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (data.success) {
      console.log('下载量统计成功');
    }
    return data;
  } catch (error) {
    console.error('增加下载量失败:', error);
    // 失败不影响下载流程，静默处理
  }
}

// 在下载按钮点击时调用
document.getElementById('download-android-btn').addEventListener('click', async () => {
  // 先调用统计接口（异步，不阻塞下载）
  incrementAndroidDownload().catch(() => {}); // 静默失败，不影响下载
  
  // 执行实际的下载逻辑
  window.location.href = '/downloads/app-android.apk';
});

document.getElementById('download-windows-btn').addEventListener('click', async () => {
  // 先调用统计接口（异步，不阻塞下载）
  incrementWindowsDownload().catch(() => {}); // 静默失败，不影响下载
  
  // 执行实际的下载逻辑
  window.location.href = '/downloads/app-windows.exe';
});
```

#### cURL示例

**使用相对路径（如果 Lighttpd 已配置 API 转发）：**
```bash
# 在 www.xintuxiangce.top 域名下
curl -X POST "https://www.xintuxiangce.top/api/v1/stats/download-count/increment/public?download_type=android"
curl -X POST "https://www.xintuxiangce.top/api/v1/stats/download-count/increment/public?download_type=windows"
```

**使用绝对路径（直接访问 API 服务器）：**
```bash
# Android下载量+1（无需认证）
curl -X POST "https://api.aifuture.net.cn/api/v1/stats/download-count/increment/public?download_type=android"

# Windows下载量+1（无需认证）
curl -X POST "https://api.aifuture.net.cn/api/v1/stats/download-count/increment/public?download_type=windows"
```

#### Python示例
```python
import requests

def increment_download(download_type: str):
    """
    增加下载量（公开接口，无需认证）
    
    Args:
        download_type: 'android' 或 'windows'
    """
    url = "https://api.aifuture.net.cn/api/v1/stats/download-count/increment/public"
    params = {"download_type": download_type}
    
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"增加下载量失败: {e}")
        return None

# 使用示例
result = increment_download("android")
if result and result.get("success"):
    print("下载量统计成功")
```

---

## 2. 增加下载量接口（需要认证，仅管理后台使用）

### 接口信息
- **URL**: `/api/v1/stats/download-count/increment`
- **方法**: `POST`
- **认证**: 需要Bearer Token认证（仅管理后台使用）
- **Content-Type**: `application/x-www-form-urlencoded` 或 `application/json`

### 请求参数

#### Query参数（推荐）
```
download_type: string (必填)
```
- **说明**: 下载类型
- **可选值**: 
  - `android` - Android平台
  - `windows` - Windows平台
- **示例**: `?download_type=android`

#### 请求头
```
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded
```

### 响应格式

#### 成功响应 (200 OK)
```json
{
  "success": true
}
```
**说明**：接口只返回成功状态，不返回统计数据。

#### 错误响应

**400 Bad Request** - 参数错误
```json
{
  "detail": "download_type必须是android或windows"
}
```

**401 Unauthorized** - 认证失败
```json
{
  "detail": "未授权：无效的认证凭证"
}
```

**500 Internal Server Error** - 服务器错误
```json
{
  "detail": "增加下载量失败"
}
```

### 调用示例

#### cURL示例
```bash
# 1. 先登录获取Token（替换username和password）
TOKEN=$(curl -X POST "https://api.aifuture.net.cn/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

# 2. 使用Token调用接口
# Android下载量+1
curl -X POST "https://api.aifuture.net.cn/api/v1/stats/download-count/increment?download_type=android" \
  -H "Authorization: Bearer $TOKEN"

# Windows下载量+1
curl -X POST "https://api.aifuture.net.cn/api/v1/stats/download-count/increment?download_type=windows" \
  -H "Authorization: Bearer $TOKEN"
```

#### JavaScript示例
```javascript
// 1. 先登录获取Token
async function getToken(username, password) {
  const response = await fetch('https://api.aifuture.net.cn/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });
  const data = await response.json();
  return data.access_token;
}

// 2. 增加Android下载量
async function incrementAndroidDownload(token) {
  const response = await fetch(
    'https://api.aifuture.net.cn/api/v1/stats/download-count/increment?download_type=android',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  const data = await response.json();
  console.log('下载量统计:', data);
  return data;
}

// 3. 增加Windows下载量
async function incrementWindowsDownload(token) {
  const response = await fetch(
    'https://api.aifuture.net.cn/api/v1/stats/download-count/increment?download_type=windows',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  const data = await response.json();
  console.log('下载量统计:', data);
  return data;
}

// 使用示例
(async () => {
  // 获取Token
  const token = await getToken('admin', 'your_password');
  
  // 调用接口
  await incrementAndroidDownload(token);
  await incrementWindowsDownload(token);
})();
```

#### Python示例
```python
import requests

def login(username: str, password: str) -> str:
    """登录获取Token"""
    url = "https://api.aifuture.net.cn/api/v1/auth/login"
    payload = {"username": username, "password": password}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def increment_download(download_type: str, token: str):
    """
    增加下载量
    
    Args:
        download_type: 'android' 或 'windows'
        token: Bearer Token
    """
    url = "https://api.aifuture.net.cn/api/v1/stats/download-count/increment"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"download_type": download_type}
    
    response = requests.post(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# 使用示例
# 1. 登录获取Token
token = login("admin", "your_password")

# 2. 调用接口
result = increment_download("android", token)
print(result)
```

---

## 3. 查询下载量接口

### 接口信息
- **URL**: `/api/v1/stats/download-count`
- **方法**: `GET`
- **认证**: 需要Bearer Token认证（管理后台使用）

### 请求参数

#### Query参数（可选）
```
download_type: string (可选)
```
- **说明**: 下载类型，如果为空则返回所有类型的统计
- **可选值**: 
  - `android` - 仅查询Android平台
  - `windows` - 仅查询Windows平台
  - 不传 - 返回所有类型的统计

### 响应格式

#### 查询所有类型 (不传download_type)
```json
{
  "success": true,
  "data": {
    "android": 100,
    "windows": 50,
    "total": 150
  }
}
```

#### 查询指定类型 (download_type=android)
```json
{
  "success": true,
  "data": {
    "android": 100
  }
}
```

### 调用示例

```bash
# 查询所有类型
curl "https://api.aifuture.net.cn/api/v1/stats/download-count" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查询Android
curl "https://api.aifuture.net.cn/api/v1/stats/download-count?download_type=android" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

---

## 注意事项

1. **接口选择**:
   - **官网用户下载**: 使用 `/api/v1/stats/download-count/increment/public`（无需认证，推荐）⭐
   - **管理后台**: 使用 `/api/v1/stats/download-count/increment`（需要认证）

2. **域名和路径**:
   - **推荐方式**：如果 Lighttpd 已配置 API 转发，使用相对路径 `/api/...`（通过当前域名访问）
   - **备选方式**：如果 Lighttpd 未配置 API 转发，使用绝对路径 `https://api.aifuture.net.cn/api/...`（直接访问 API 服务器，需要 CORS 支持）
   - FastAPI 已配置 CORS（`allow_origins=["*"]`），支持跨域访问

3. **错误处理**: 
   - 统计接口失败不应影响用户的下载流程
   - 建议使用异步调用，失败时静默处理，不向用户显示错误

4. **调用时机**: 
   - 建议在实际下载开始或下载完成时调用
   - 可以使用异步调用，不阻塞下载流程

5. **频率限制**: 
   - 公开接口目前没有频率限制
   - 如果担心恶意刷量，可以在前端添加简单的防重复点击机制

