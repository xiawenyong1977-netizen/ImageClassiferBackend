# 阿里云通义千问配置指南

## 📋 概述

使用阿里云通义千问（Qwen-VL）作为图片分类的大模型，优势：
- ✅ 国内访问速度快
- ✅ 稳定性高
- ✅ 支持中文更好
- ✅ 价格相对便宜

---

## 🔑 获取API密钥

### 步骤1：开通服务

1. 登录阿里云控制台：https://www.aliyun.com/
2. 搜索"灵积DashScope"或直接访问：https://dashscope.console.aliyun.com/
3. 点击"开通服务"（免费开通）

### 步骤2：创建API密钥

1. 进入控制台：https://dashscope.console.aliyun.com/apiKey
2. 点击"创建API密钥"
3. 复制生成的API Key（格式：sk-xxxxxx）
4. **妥善保存**（只显示一次）

### 步骤3：选择模型

阿里云提供多个视觉模型：

| 模型名称 | 模型ID | 能力 | 价格 |
|---------|--------|------|------|
| 通义千问VL Plus | `qwen-vl-plus` | 标准视觉理解 | 较低 |
| 通义千问VL Max | `qwen-vl-max` | 高级视觉理解 | 较高 |
| 通义千问VL | `qwen-vl-v1` | 基础版本 | 最低 |

**推荐**：`qwen-vl-max`（效果最好）

---

## ⚙️ 配置到服务器

### 方式1：SSH修改（推荐）

```bash
# 连接到服务器
ssh root@123.57.68.4

# 编辑配置文件
cd /opt/ImageClassifierBackend
vi .env

# 修改以下配置：
# LLM_PROVIDER=aliyun
# LLM_API_KEY=sk-你的阿里云API密钥
# LLM_MODEL=qwen-vl-max

# 保存退出（ESC -> :wq -> 回车）

# 重启服务
systemctl restart image-classifier

# 查看日志确认
journalctl -u image-classifier -f
```

### 方式2：本地修改后上传

在本地编辑 `.env` 文件：

```ini
# ===== 大模型API配置 =====
LLM_PROVIDER=aliyun
LLM_API_KEY=sk-你的阿里云密钥
LLM_MODEL=qwen-vl-max
LLM_MAX_TOKENS=500
LLM_TIMEOUT=30
```

上传到服务器：
```bash
scp .env root@123.57.68.4:/opt/ImageClassifierBackend/
ssh root@123.57.68.4 "systemctl restart image-classifier"
```

---

## 🧪 测试配置

### 方法1：使用Web界面测试

1. 访问：http://123.57.68.4:8000/
2. 切换到"分类测试"标签
3. 上传一张图片
4. 点击"开始分类"
5. 查看结果

### 方法2：使用curl测试

```bash
# 准备一张测试图片
curl -X POST "http://123.57.68.4:8000/api/v1/classify" \
  -F "image=@test.jpg"
```

---

## 💰 定价说明

### 阿里云通义千问定价（参考）

- **qwen-vl-plus**：约 ¥0.008/千tokens
- **qwen-vl-max**：约 ¥0.02/千tokens

**一般一张图片分类**：
- 输入：图片 + prompt ≈ 1000 tokens
- 输出：分类结果 ≈ 100 tokens
- 总计：≈ 1100 tokens
- 成本：约 ¥0.01-0.02/次

**与OpenAI对比**：
- OpenAI GPT-4V：约 ¥0.05/次
- 阿里云Qwen-VL：约 ¥0.01/次
- **节省**：约60%

---

## 📚 参考文档

- 阿里云灵积DashScope：https://dashscope.console.aliyun.com/
- API文档：https://help.aliyun.com/zh/dashscope/
- 通义千问VL文档：https://help.aliyun.com/zh/dashscope/developer-reference/qwen-vl-api

---

## 🔍 常见问题

### Q1: 如何获取免费额度？

新用户开通DashScope服务后，会获得一定的免费额度。具体额度请查看控制台。

### Q2: API调用限制是多少？

- 普通账户：约 60次/分钟
- 企业账户：可申请更高限额

### Q3: 支持哪些图片格式？

- JPG/JPEG
- PNG
- WebP
- GIF

### Q4: 图片大小限制？

- 建议：小于5MB
- 最大：10MB
- **建议客户端压缩到1MB以内**

---

## ✅ 配置检查清单

完成配置后请检查：

- [ ] 阿里云DashScope服务已开通
- [ ] API密钥已创建并保存
- [ ] 服务器.env文件已更新
- [ ] LLM_PROVIDER=aliyun
- [ ] LLM_API_KEY已填写
- [ ] LLM_MODEL=qwen-vl-max（或其他模型）
- [ ] 服务已重启
- [ ] Web界面能正常访问
- [ ] 上传图片测试分类成功

---

## 🎯 快速配置命令

```bash
# 一键配置（替换下面的API密钥）
ssh root@123.57.68.4 "
cd /opt/ImageClassifierBackend
sed -i 's/LLM_PROVIDER=.*/LLM_PROVIDER=aliyun/' .env
sed -i 's/LLM_API_KEY=.*/LLM_API_KEY=sk-你的阿里云密钥/' .env
sed -i 's/LLM_MODEL=.*/LLM_MODEL=qwen-vl-max/' .env
systemctl restart image-classifier
echo '✓ 配置完成'
"
```

---

**配置完成后，立即就能在Web界面测试图片分类了！** 🚀

