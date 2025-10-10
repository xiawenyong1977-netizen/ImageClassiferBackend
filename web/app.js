// 配置
const CONFIG_KEY = 'image_classifier_config';

// 默认提示词
const DEFAULT_PROMPT = `请对这张图片进行分类。你必须从以下8个类别中选择一个：

1. social_activities - 社交活动（聚会、合影、多人互动场景）
2. pets - 宠物萌照（猫、狗等宠物照片）
3. single_person - 单人照片（个人照、自拍、肖像）
4. foods - 美食记录（食物、餐饮、烹饪相关）
5. travel_scenery - 旅行风景（旅游景点、自然风光、城市风景）
6. screenshot - 手机截图（手机屏幕截图、应用界面）
7. idcard - 证件照（身份证、护照、驾照等证件）
8. other - 其它（无法归类到上述类别）

请以JSON格式返回结果：
{
    "category": "类别key（必须是上述8个之一）",
    "confidence": 0.95,
    "description": "简短描述图片内容（可选，中文，30字以内）"
}

只返回JSON，不要有其他文字。`;

let currentConfig = {
    apiUrl: 'http://123.57.68.4:8000',
    llmProvider: 'aliyun',
    llmApiKey: '',
    llmModel: 'qwen-vl-plus',  // 固定使用通义千问VL-Plus
    prompt: DEFAULT_PROMPT
};

// 分类名称映射
const categoryNameMap = {
    "social_activities": {
        "chinese": "社交活动",
        "english": "Social Activities"
    },
    "pets": {
        "chinese": "宠物萌照",
        "english": "Pet Photos"
    },
    "single_person": {
        "chinese": "单人照片",
        "english": "Single Person Photos"
    },
    "foods": {
        "chinese": "美食记录",
        "english": "Food Records"
    },
    "travel_scenery": {
        "chinese": "旅行风景",
        "english": "Travel Scenery"
    },
    "screenshot": {
        "chinese": "手机截图",
        "english": "Mobile Screenshots"
    },
    "idcard": {
        "chinese": "证件照",
        "english": "ID Card"
    },
    "other": {
        "chinese": "其它",
        "english": "Other Images"
    }
};

// 页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    checkSystemStatus();
    loadTodayStats();
    loadCacheStats();
    loadCategoryDistribution();
    
    // 自动刷新统计（每30秒）
    setInterval(() => {
        if (document.getElementById('stats-tab').classList.contains('active')) {
            loadTodayStats();
            loadCacheStats();
            loadCategoryDistribution();
        }
    }, 30000);
    
    // 文件上传处理
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', handleFileSelect);
    
    // 拖拽上传
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });
});

// 标签页切换
function showTab(tabName) {
    // 隐藏所有标签页
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 移除所有按钮的active状态
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 显示选中的标签页
    document.getElementById(tabName + '-tab').classList.add('active');
    event.target.classList.add('active');
    
    // 如果切换到统计页，刷新数据
    if (tabName === 'stats') {
        loadTodayStats();
        loadCacheStats();
        loadCategoryDistribution();
    }
}

// 检查系统状态
async function checkSystemStatus() {
    try {
        const response = await fetch(`${currentConfig.apiUrl}/api/v1/health`);
        const data = await response.json();
        
        const statusHtml = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>服务状态</h3>
                    <div class="value">
                        <span class="status-dot ${data.status === 'healthy' ? 'green' : 'red'}"></span>
                        ${data.status === 'healthy' ? '正常' : '异常'}
                    </div>
                </div>
                <div class="stat-card">
                    <h3>数据库</h3>
                    <div class="value">
                        <span class="status-dot ${data.database === 'connected' ? 'green' : 'red'}"></span>
                        ${data.database === 'connected' ? '已连接' : '未连接'}
                    </div>
                </div>
                <div class="stat-card">
                    <h3>大模型API</h3>
                    <div class="value">
                        <span class="status-dot ${data.model_api === 'available' ? 'green' : 'red'}"></span>
                        ${data.model_api === 'available' ? '可用' : '未配置'}
                    </div>
                </div>
                <div class="stat-card">
                    <h3>最后更新</h3>
                    <div class="value" style="font-size: 1.2rem;">
                        ${new Date(data.timestamp).toLocaleTimeString('zh-CN')}
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('system-status').innerHTML = statusHtml;
    } catch (error) {
        document.getElementById('system-status').innerHTML = `
            <div class="alert alert-error">
                ❌ 无法连接到服务器: ${error.message}
            </div>
        `;
    }
}

// 加载今日统计
async function loadTodayStats() {
    try {
        const response = await fetch(`${currentConfig.apiUrl}/api/v1/stats/today`);
        const result = await response.json();
        const data = result.data;
        
        const statsHtml = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>总请求数</h3>
                    <div class="value">${data.total_requests || 0}</div>
                    <div class="sub">今日累计</div>
                </div>
                <div class="stat-card">
                    <h3>缓存命中</h3>
                    <div class="value">${data.cache_hits || 0}</div>
                    <div class="sub">命中率: ${data.cache_hit_rate || 0}%</div>
                </div>
                <div class="stat-card">
                    <h3>独立用户</h3>
                    <div class="value">${data.unique_users || 0}</div>
                    <div class="sub">独立IP: ${data.unique_ips || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>平均耗时</h3>
                    <div class="value">${data.avg_processing_time || 0}</div>
                    <div class="sub">毫秒</div>
                </div>
                <div class="stat-card">
                    <h3>预估成本</h3>
                    <div class="value">¥${parseFloat(data.estimated_cost || 0).toFixed(2)}</div>
                    <div class="sub">API调用成本</div>
                </div>
                <div class="stat-card">
                    <h3>节省成本</h3>
                    <div class="value">¥${parseFloat(data.cost_saved || 0).toFixed(2)}</div>
                    <div class="sub">缓存节省</div>
                </div>
            </div>
        `;
        
        document.getElementById('today-stats').innerHTML = statsHtml;
    } catch (error) {
        document.getElementById('today-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 加载缓存统计
async function loadCacheStats() {
    try {
        const response = await fetch(`${currentConfig.apiUrl}/api/v1/stats/cache-efficiency`);
        const result = await response.json();
        const data = result.data;
        
        const statsHtml = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>缓存图片数</h3>
                    <div class="value">${data.total_cached_images || 0}</div>
                    <div class="sub">总缓存</div>
                </div>
                <div class="stat-card">
                    <h3>总命中次数</h3>
                    <div class="value">${data.total_hits || 0}</div>
                    <div class="sub">累计命中</div>
                </div>
                <div class="stat-card">
                    <h3>节省调用</h3>
                    <div class="value">${data.times_saved || 0}</div>
                    <div class="sub">次数</div>
                </div>
                <div class="stat-card">
                    <h3>平均命中</h3>
                    <div class="value">${parseFloat(data.avg_hit_per_image || 0).toFixed(2)}</div>
                    <div class="sub">次/图片</div>
                </div>
                <div class="stat-card">
                    <h3>最高命中</h3>
                    <div class="value">${data.max_hits || 0}</div>
                    <div class="sub">单图片最高</div>
                </div>
                <div class="stat-card">
                    <h3>累计节省</h3>
                    <div class="value">¥${parseFloat(data.cost_saved || 0).toFixed(2)}</div>
                    <div class="sub">总成本节省</div>
                </div>
            </div>
        `;
        
        document.getElementById('cache-stats').innerHTML = statsHtml;
    } catch (error) {
        document.getElementById('cache-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 加载分类分布
async function loadCategoryDistribution() {
    try {
        const response = await fetch(`${currentConfig.apiUrl}/api/v1/stats/category-distribution`);
        const result = await response.json();
        const data = result.data;
        
        if (!data || data.length === 0) {
            document.getElementById('category-distribution').innerHTML = `
                <div class="alert alert-info">暂无数据</div>
            `;
            return;
        }
        
        const gridHtml = data.map(item => {
            const categoryInfo = categoryNameMap[item.category] || { chinese: item.category, english: '' };
            return `
                <div class="category-item">
                    <div class="name">${categoryInfo.chinese}</div>
                    <div class="count">${item.count}</div>
                    <div class="sub">${item.percentage || 0}% | 置信度: ${item.avg_confidence || 0}</div>
                </div>
            `;
        }).join('');
        
        document.getElementById('category-distribution').innerHTML = `
            <div class="category-grid">${gridHtml}</div>
        `;
    } catch (error) {
        document.getElementById('category-distribution').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 文件选择处理
function handleFileSelect() {
    const file = document.getElementById('file-input').files[0];
    if (!file) return;
    
    // 验证文件大小
    if (file.size > 10 * 1024 * 1024) {
        showAlert('test-alert', '文件过大，最大支持10MB', 'error');
        return;
    }
    
    // 显示预览
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('preview-image').src = e.target.result;
        document.getElementById('upload-area').classList.add('hidden');
        document.getElementById('preview-area').classList.remove('hidden');
        document.getElementById('result-area').classList.add('hidden');
    };
    reader.readAsDataURL(file);
}

// 重置上传
function resetUpload() {
    document.getElementById('file-input').value = '';
    document.getElementById('upload-area').classList.remove('hidden');
    document.getElementById('preview-area').classList.add('hidden');
    document.getElementById('result-area').classList.add('hidden');
    document.getElementById('test-alert').innerHTML = '';
}

// 图片分类
async function classifyImage() {
    const file = document.getElementById('file-input').files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('image', file);
    
    // 显示加载状态
    const resultArea = document.getElementById('result-area');
    resultArea.classList.remove('hidden');
    document.getElementById('classification-result').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>正在分类中，请稍候...</p>
        </div>
    `;
    
    try {
        const startTime = Date.now();
        const response = await fetch(`${currentConfig.apiUrl}/api/v1/classify`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        const endTime = Date.now();
        const actualTime = endTime - startTime;
        
        if (result.success) {
            displayClassificationResult(result, actualTime);
            showAlert('test-alert', '✅ 分类成功！', 'success');
        } else {
            throw new Error(result.error || '分类失败');
        }
        
    } catch (error) {
        document.getElementById('classification-result').innerHTML = `
            <div class="alert alert-error">❌ 分类失败: ${error.message}</div>
        `;
        showAlert('test-alert', `分类失败: ${error.message}`, 'error');
    }
}

// 显示分类结果
function displayClassificationResult(result, actualTime) {
    const data = result.data;
    const categoryInfo = categoryNameMap[data.category] || { chinese: data.category, english: '' };
    
    const resultHtml = `
        <div class="result-item">
            <span class="result-label">分类类别</span>
            <span class="result-value">
                <span class="category-badge">${categoryInfo.chinese}</span>
            </span>
        </div>
        <div class="result-item">
            <span class="result-label">类别Key</span>
            <span class="result-value"><code>${data.category}</code></span>
        </div>
        <div class="result-item">
            <span class="result-label">置信度</span>
            <span class="result-value">${(data.confidence * 100).toFixed(2)}%</span>
        </div>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${data.confidence * 100}%">
                ${(data.confidence * 100).toFixed(1)}%
            </div>
        </div>
        ${data.description ? `
        <div class="result-item" style="margin-top: 15px;">
            <span class="result-label">图片描述</span>
            <span class="result-value">${data.description}</span>
        </div>
        ` : ''}
        <div class="result-item">
            <span class="result-label">数据来源</span>
            <span class="result-value">${result.from_cache ? '✅ 缓存命中' : '🆕 大模型调用'}</span>
        </div>
        <div class="result-item">
            <span class="result-label">处理耗时</span>
            <span class="result-value">${result.processing_time_ms}ms (实际: ${actualTime}ms)</span>
        </div>
        <div class="result-item">
            <span class="result-label">请求ID</span>
            <span class="result-value"><code>${result.request_id}</code></span>
        </div>
    `;
    
    document.getElementById('classification-result').innerHTML = resultHtml;
}

// 显示提示信息
function showAlert(elementId, message, type) {
    const alertClass = type === 'error' ? 'alert-error' : type === 'success' ? 'alert-success' : 'alert-info';
    document.getElementById(elementId).innerHTML = `
        <div class="alert ${alertClass}">${message}</div>
    `;
    
    // 3秒后自动消失
    setTimeout(() => {
        document.getElementById(elementId).innerHTML = '';
    }, 3000);
}

// 保存配置
function saveConfig() {
    currentConfig = {
        apiUrl: document.getElementById('api-url').value,
        llmProvider: document.getElementById('llm-provider').value,
        llmApiKey: document.getElementById('llm-api-key').value,
        llmModel: document.getElementById('llm-model').value,
        prompt: document.getElementById('prompt-config').value
    };
    
    localStorage.setItem(CONFIG_KEY, JSON.stringify(currentConfig));
    showAlert('config-alert', '✅ 配置已保存到浏览器本地存储（提示词需要在服务器.env中配置才能生效）', 'success');
    
    // 刷新系统状态
    checkSystemStatus();
}

// 加载配置
function loadConfig() {
    const saved = localStorage.getItem(CONFIG_KEY);
    if (saved) {
        currentConfig = JSON.parse(saved);
    }
    
    // 确保有默认提示词
    if (!currentConfig.prompt) {
        currentConfig.prompt = DEFAULT_PROMPT;
    }
    
    document.getElementById('api-url').value = currentConfig.apiUrl;
    document.getElementById('llm-provider').value = currentConfig.llmProvider;
    document.getElementById('llm-api-key').value = currentConfig.llmApiKey;
    document.getElementById('llm-model').value = currentConfig.llmModel;
    document.getElementById('prompt-config').value = currentConfig.prompt;
}

// 重置提示词为默认值
function resetPrompt() {
    document.getElementById('prompt-config').value = DEFAULT_PROMPT;
    showAlert('config-alert', '✅ 提示词已恢复为默认值', 'info');
}

// 格式化数字
function formatNumber(num) {
    return num ? num.toLocaleString('zh-CN') : 0;
}

// 格式化百分比
function formatPercent(num) {
    return num ? num.toFixed(2) + '%' : '0%';
}

