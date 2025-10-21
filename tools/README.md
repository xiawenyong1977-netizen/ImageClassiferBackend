# 工具脚本目录

本目录包含项目开发和运维过程中使用的各种工具脚本。

## 📋 工具列表

### 🔍 数据查询工具
- **`check_user_data.py`** - 检查用户数据，验证 request_log 和 image_classification_cache 中的数据
- **`check_user_ids.py`** - 查询所有用户ID，支持模糊匹配搜索

### 🗑️ 缓存管理工具
- **`delete_user_cache.py`** - 删除指定用户的所有缓存数据
- **`delete_cache_by_hash.py`** - 根据图片哈希删除特定缓存记录

### 🔐 认证工具
- **`generate_password_hash.py`** - 生成管理员密码哈希值

### 🌍 地理位置数据工具
- **`import_chinese_names.py`** - 导入中文地名数据
- **`supplement_chinese_names.py`** - 补充中文地名数据
- **`auto_search_chinese_names.py`** - 自动搜索中文地名
- **`cities_chinese_supplement.csv`** - 中文地名补充数据
- **`cities_no_chinese.tsv`** - 缺少中文名的城市数据

### 🧪 测试工具
- **`test_local_inference.py`** - 本地模型推理测试

## 🚀 使用方法

### 缓存管理
```bash
# 删除用户缓存
python tools/delete_user_cache.py <user_id> [--confirm]

# 根据哈希删除缓存
python tools/delete_cache_by_hash.py <image_hash> [--confirm]
```

### 数据查询
```bash
# 检查用户数据
python tools/check_user_data.py <user_id>

# 查询用户ID
python tools/check_user_ids.py [partial_user_id]
```

### 认证管理
```bash
# 生成密码哈希
python tools/generate_password_hash.py
```

### 地理位置数据
```bash
# 导入中文地名
python tools/import_chinese_names.py

# 补充中文地名
python tools/supplement_chinese_names.py
```

### 本地模型测试
```bash
# 测试本地推理
python tools/test_local_inference.py
```

## 📝 注意事项

1. **权限要求**：某些工具需要数据库访问权限
2. **环境配置**：确保已正确配置环境变量（参考 `env.example`）
3. **备份数据**：删除操作前建议先备份重要数据
4. **测试环境**：建议先在测试环境中验证工具功能

## 🔧 依赖要求

所有工具脚本都依赖于项目的主要依赖包，请确保已安装：
```bash
pip install -r requirements.txt
```

---

**提示**：使用工具前请仔细阅读相关文档，确保理解其功能和影响。
