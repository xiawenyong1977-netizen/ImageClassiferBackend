# 配置阿里云通义千问API密钥

## 🔑 获取API密钥步骤

### 步骤1：开通阿里云灵积DashScope服务

1. 访问：https://dashscope.console.aliyun.com/
2. 使用您的阿里云账号登录
3. 点击"开通服务"（免费开通）

### 步骤2：创建API Key

1. 进入API Key管理：https://dashscope.console.aliyun.com/apiKey
2. 点击"创建API Key"
3. **复制并保存生成的API Key**（格式：sk-xxxxxx）
4. ⚠️ **重要**：密钥只显示一次，请妥善保存

### 步骤3：配置到服务器

**SSH连接到服务器：**
```bash
ssh root@123.57.68.4
```

**编辑配置文件：**
```bash
cd /opt/ImageClassifierBackend
vi .env
```

**找到并修改这一行：**
```ini
LLM_API_KEY=sk-你刚才复制的阿里云API密钥
```

**保存并退出**：
- 按 `i` 进入编辑模式
- 粘贴API密钥
- 按 `ESC` 退出编辑
- 输入 `:wq` 回车保存

**重启服务：**
```bash
systemctl restart image-classifier
```

**验证配置：**
```bash
# 查看日志
journalctl -u image-classifier -f

# 应该看到：
# "大模型提供商: aliyun"
# "数据库连接成功"
```

---

## ✅ 配置完成后

### 测试分类功能

1. **访问Web界面**：http://123.57.68.4:8000/
2. **切换到"分类测试"标签**
3. **上传一张图片**
4. **点击"开始分类"**
5. **查看分类结果**

应该能看到：
- ✅ 分类类别（中文）
- ✅ 置信度
- ✅ 图片描述
- ✅ 处理时间

---

## 📋 当前配置

| 配置项 | 值 |
|--------|------|
| 大模型提供商 | 阿里云 (aliyun) |
| 模型名称 | qwen-vl-plus |
| 模型版本 | 通义千问3-VL-Plus-2025-09-23 |
| API文档 | https://help.aliyun.com/zh/dashscope/ |

---

## 💰 费用说明

**通义千问VL-Plus定价**：
- 约 ¥0.008-0.01/次调用
- 每张图片分类成本：约 ¥0.01元

**示例计算**：
- 每天1000次请求
- 缓存命中率30%
- 实际调用：700次
- 每日成本：约 ¥7元
- 每月成本：约 ¥210元

**通过缓存节省**：
- 无缓存：¥10元/天 = ¥300元/月
- 有缓存：¥7元/天 = ¥210元/月
- **月节省：¥90元**

---

## 🔍 验证API密钥

配置后验证是否正确：

```bash
# SSH到服务器
ssh root@123.57.68.4

# 查看配置
cd /opt/ImageClassifierBackend
cat .env | grep LLM

# 应该显示：
# LLM_PROVIDER=aliyun
# LLM_API_KEY=sk-你的密钥
# LLM_MODEL=qwen-vl-plus
```

---

## 🎯 快速配置命令

**如果您的API密钥是：sk-abc123xyz**

```bash
ssh root@123.57.68.4 "cd /opt/ImageClassifierBackend && sed -i 's/LLM_API_KEY=.*/LLM_API_KEY=sk-abc123xyz/' .env && systemctl restart image-classifier && echo '✓ 配置完成并重启服务'"
```

（记得替换 `sk-abc123xyz` 为您的真实密钥）

---

## 📞 需要帮助？

**遇到问题时：**

1. **查看服务日志**：
   ```bash
   journalctl -u image-classifier -f
   ```

2. **测试健康检查**：
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. **测试图片分类**：
   在Web界面上传图片测试

---

**配置完成后立即可以使用！** 🚀

