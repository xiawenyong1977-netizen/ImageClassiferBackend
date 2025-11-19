// 配置
const CONFIG_KEY = 'image_classifier_config';
const TOKEN_KEY = 'admin_token';
const TOKEN_EXPIRES_KEY = 'token_expires';
const USERNAME_KEY = 'admin_username';

// ImageNet类别映射（延迟加载）
let imagenetClasses = null;

// 认证相关函数
function getAuthToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function getAuthHeaders() {
    const token = getAuthToken();
    if (token) {
        return {
            'Authorization': `Bearer ${token}`
        };
    }
    return {};
}

function checkAuth() {
    const token = getAuthToken();
    const expires = parseInt(localStorage.getItem(TOKEN_EXPIRES_KEY) || '0');
    
    if (!token || expires < Date.now()) {
        // 未登录或token已过期，跳转到登录页
        window.location.href = '/login.html';
        return false;
    }
    return true;
}

function logout() {
    if (confirm('确定要退出登录吗？')) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(TOKEN_EXPIRES_KEY);
        localStorage.removeItem(USERNAME_KEY);
        window.location.href = '/login.html';
    }
}

// 带认证的fetch请求
async function authFetch(url, options = {}) {
    const headers = {
        ...getAuthHeaders(),
        ...(options.headers || {})
    };
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        // 认证失败，跳转到登录页
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(TOKEN_EXPIRES_KEY);
        localStorage.removeItem(USERNAME_KEY);
        window.location.href = '/login.html';
        throw new Error('认证失败，请重新登录');
    }
    
    return response;
}

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
    apiUrl: '',  // 使用相对路径，通过Lighttpd转发到app服务器
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

// 页面加载完成（主初始化）
document.addEventListener('DOMContentLoaded', function() {
    // 检查认证状态
    if (!checkAuth()) {
        return;
    }
    
    // 显示用户信息
    const username = localStorage.getItem(USERNAME_KEY) || 'Admin';
    document.getElementById('user-info').textContent = `👤 ${username}`;
    
    // 检查系统状态
    checkSystemStatus();
    
    // 加载核心指标
    loadCoreStats();
    
    // 加载统计数据
    loadTodayStats();
    loadCacheStats();
    loadCategoryDistribution();
    loadInferenceMethodStats();
    loadBatchCacheStats();
    loadBatchClassifyStats();
    loadImageEditStats();
    
    // 自动刷新统计（每30秒）
    setInterval(() => {
        loadCoreStats();  // 核心指标始终刷新
        if (document.getElementById('stats-tab').classList.contains('active')) {
            loadTodayStats();
            loadCacheStats();
            loadCategoryDistribution();
            loadInferenceMethodStats();
            loadBatchCacheStats();
            loadBatchClassifyStats();
            loadImageEditStats();
        }
    }, 30000);
    
    // 文件上传处理（只设置一次）
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    if (uploadArea && fileInput) {
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
    }
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
        loadInferenceMethodStats();
        loadBatchCacheStats();
        loadBatchClassifyStats();
        loadImageEditStats();
    }
    
    // 如果切换到地理位置页，加载位置统计
    if (tabName === 'location') {
        loadLocationStats();
    }
}

// 加载核心指标
async function loadCoreStats() {
    try {
        // 并行加载3个指标
        const [downloadRes, boundUsersRes, memberRes] = await Promise.all([
            authFetch(`${currentConfig.apiUrl}/api/v1/stats/download-count`),
            authFetch(`${currentConfig.apiUrl}/api/v1/stats/bound-users-count`),
            authFetch(`${currentConfig.apiUrl}/api/v1/stats/member-count`)
        ]);
        
        // 检查响应状态
        if (!downloadRes.ok) {
            console.error('下载量统计请求失败:', downloadRes.status, downloadRes.statusText);
            const errorText = await downloadRes.text();
            console.error('错误详情:', errorText);
        }
        if (!boundUsersRes.ok) {
            console.error('已绑定用户数统计请求失败:', boundUsersRes.status, boundUsersRes.statusText);
        }
        if (!memberRes.ok) {
            console.error('会员数量统计请求失败:', memberRes.status, memberRes.statusText);
        }
        
        const downloadData = await downloadRes.json();
        const boundUsersData = await boundUsersRes.json();
        const memberData = await memberRes.json();
        
        console.log('下载量统计响应:', downloadData);
        console.log('已绑定用户数统计响应:', boundUsersData);
        console.log('会员数量统计响应:', memberData);
        
        // 下载量统计（按类型：android、windows）
        const downloadStats = downloadData.data || {};
        const androidCount = downloadStats.android || 0;
        const windowsCount = downloadStats.windows || 0;
        
        const boundUsersCount = boundUsersData.data?.bound_users_count || 0;
        const memberCount = memberData.data?.member_count || 0;
        
        // 分别显示Android和Windows下载量
        document.getElementById('download-count-android').textContent = formatNumber(androidCount);
        document.getElementById('download-count-windows').textContent = formatNumber(windowsCount);
        document.getElementById('bound-users-count').textContent = formatNumber(boundUsersCount);
        document.getElementById('member-count').textContent = formatNumber(memberCount);
        
    } catch (error) {
        console.error('加载核心指标失败:', error);
        console.error('错误堆栈:', error.stack);
        // 显示错误但不影响其他功能
        document.getElementById('download-count-android').textContent = '加载失败';
        document.getElementById('download-count-windows').textContent = '加载失败';
        document.getElementById('bound-users-count').textContent = '加载失败';
        document.getElementById('member-count').textContent = '加载失败';
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
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/stats/today`);
        const result = await response.json();
        const data = result.data || {};
        
        // 处理null值，确保显示为0而不是空
        const formatValue = (value) => {
            if (value === null || value === undefined) return 0;
            return value;
        };
        
        const formatNumber = (value) => {
            const num = formatValue(value);
            return typeof num === 'number' ? num : 0;
        };
        
        const formatPercent = (value) => {
            const num = formatNumber(value);
            return num.toFixed(2);
        };
        
        const formatCurrency = (value) => {
            const num = formatNumber(value);
            return parseFloat(num).toFixed(2);
        };
        
        const statsHtml = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>总请求数</h3>
                    <div class="value">${formatNumber(data.total_requests)}</div>
                    <div class="sub">今日累计</div>
                </div>
                <div class="stat-card">
                    <h3>缓存命中</h3>
                    <div class="value">${formatNumber(data.cache_hits)}</div>
                    <div class="sub">命中率: ${formatPercent(data.cache_hit_rate)}%</div>
                </div>
                <div class="stat-card">
                    <h3>独立用户</h3>
                    <div class="value">${formatNumber(data.unique_users)}</div>
                    <div class="sub">独立IP: ${formatNumber(data.unique_ips)}</div>
                </div>
                <div class="stat-card">
                    <h3>平均耗时</h3>
                    <div class="value">${formatNumber(data.avg_processing_time)}</div>
                    <div class="sub">毫秒</div>
                </div>
                <div class="stat-card">
                    <h3>预估成本</h3>
                    <div class="value">¥${formatCurrency(data.estimated_cost)}</div>
                    <div class="sub">API调用成本</div>
                </div>
                <div class="stat-card">
                    <h3>节省成本</h3>
                    <div class="value">¥${formatCurrency(data.cost_saved)}</div>
                    <div class="sub">缓存节省</div>
                </div>
            </div>
        `;
        
        document.getElementById('today-stats').innerHTML = statsHtml;
    } catch (error) {
        console.error('加载今日统计失败:', error);
        document.getElementById('today-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 加载缓存统计
async function loadCacheStats() {
    try {
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/stats/cache-efficiency`);
        const result = await response.json();
        const data = result.data || {};
        
        // 格式化函数（复用今日统计的逻辑）
        const formatNumber = (value) => {
            if (value === null || value === undefined) return 0;
            return typeof value === 'number' ? value : 0;
        };
        
        const formatCurrency = (value) => {
            const num = formatNumber(value);
            return parseFloat(num).toFixed(2);
        };
        
        const statsHtml = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>缓存图片数</h3>
                    <div class="value">${formatNumber(data.total_cached_images)}</div>
                    <div class="sub">总缓存</div>
                </div>
                <div class="stat-card">
                    <h3>总命中次数</h3>
                    <div class="value">${formatNumber(data.total_hits)}</div>
                    <div class="sub">累计命中</div>
                </div>
                <div class="stat-card">
                    <h3>节省调用</h3>
                    <div class="value">${formatNumber(data.times_saved)}</div>
                    <div class="sub">次数</div>
                </div>
                <div class="stat-card">
                    <h3>平均命中</h3>
                    <div class="value">${formatCurrency(data.avg_hit_per_image)}</div>
                    <div class="sub">次/图片</div>
                </div>
                <div class="stat-card">
                    <h3>最高命中</h3>
                    <div class="value">${formatNumber(data.max_hits)}</div>
                    <div class="sub">单图片最高</div>
                </div>
                <div class="stat-card">
                    <h3>累计节省</h3>
                    <div class="value">¥${formatCurrency(data.cost_saved)}</div>
                    <div class="sub">总成本节省</div>
                </div>
            </div>
        `;
        
        document.getElementById('cache-stats').innerHTML = statsHtml;
    } catch (error) {
        console.error('加载缓存统计失败:', error);
        document.getElementById('cache-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 加载分类分布
async function loadCategoryDistribution() {
    try {
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/stats/category-distribution`);
        const result = await response.json();
        const data = result.data || [];
        
        if (!data || data.length === 0) {
            document.getElementById('category-distribution').innerHTML = `
                <div class="alert alert-info">暂无数据</div>
            `;
            return;
        }
        
        const formatNumber = (value) => {
            if (value === null || value === undefined) return 0;
            return typeof value === 'number' ? value : 0;
        };
        
        const gridHtml = data.map(item => {
            const categoryInfo = categoryNameMap[item.category] || { chinese: item.category, english: '' };
            return `
                <div class="category-item">
                    <div class="name">${categoryInfo.chinese}</div>
                    <div class="count">${formatNumber(item.count)}</div>
                    <div class="sub">${formatNumber(item.percentage).toFixed(2)}% | 置信度: ${formatNumber(item.avg_confidence).toFixed(2)}</div>
                </div>
            `;
        }).join('');
        
        document.getElementById('category-distribution').innerHTML = `
            <div class="category-grid">${gridHtml}</div>
        `;
    } catch (error) {
        console.error('加载分类分布失败:', error);
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


// 格式化数字
function formatNumber(num) {
    return num ? num.toLocaleString('zh-CN') : 0;
}

// 加载推理方式统计
async function loadInferenceMethodStats() {
    try {
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/stats/inference-method`);
        const data = await response.json();
        const stats = data.data;
        
        const total = stats.total_requests || 0;
        const fromCache = stats.from_cache || 0;
        const llmSuccess = stats.llm_success || 0;
        const localDirect = stats.local_direct || 0;
        const localFallback = stats.local_fallback_success || 0;
        const localTest = stats.local_test || 0;
        const llmFail = stats.llm_fail_count || 0;
        const localTotal = stats.local_total || 0;
        
        document.getElementById('inference-method-stats').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${formatNumber(total)}</div>
                    <div class="stat-label">今日总请求</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">💾</div>
                    <div class="stat-value">${formatNumber(fromCache)}</div>
                    <div class="stat-label">缓存命中</div>
                    <div class="stat-trend" style="color: #28a745;">${total > 0 ? ((fromCache/total*100).toFixed(1)) : 0}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🌐</div>
                    <div class="stat-value">${formatNumber(llmSuccess)}</div>
                    <div class="stat-label">大模型调用成功</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🤖</div>
                    <div class="stat-value">${formatNumber(localTotal)}</div>
                    <div class="stat-label">本地推理总次数</div>
                    <div class="stat-trend" style="color: #667eea;">直接: ${localDirect} | 降级: ${localFallback} | 测试: ${localTest}</div>
                </div>
            </div>
            
            <div class="stats-grid" style="margin-top: 20px;">
                <div class="stat-card" style="border-left: 4px solid #dc3545;">
                    <div class="stat-icon">❌</div>
                    <div class="stat-value">${formatNumber(llmFail)}</div>
                    <div class="stat-label">大模型调用失败</div>
                    <div class="stat-trend" style="color: #dc3545;">已降级到本地推理</div>
                </div>
                <div class="stat-card" style="border-left: 4px solid #28a745;">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${formatNumber(localFallback)}</div>
                    <div class="stat-label">本地推理降级成功</div>
                    <div class="stat-trend" style="color: #28a745;">保障服务可用性</div>
                </div>
                <div class="stat-card" style="border-left: 4px solid #667eea;">
                    <div class="stat-icon">⚡</div>
                    <div class="stat-value">${formatNumber(localDirect)}</div>
                    <div class="stat-label">本地推理直接调用</div>
                    <div class="stat-trend" style="color: #667eea;">开关开启</div>
                </div>
                <div class="stat-card" style="border-left: 4px solid #17a2b8;">
                    <div class="stat-icon">🧪</div>
                    <div class="stat-value">${formatNumber(localTest)}</div>
                    <div class="stat-label">本地模型测试</div>
                    <div class="stat-trend" style="color: #17a2b8;">管理后台测试</div>
                </div>
            </div>
        `;
        
    } catch (error) {
        document.getElementById('inference-method-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 加载批量缓存查询统计
async function loadBatchCacheStats() {
    try {
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/stats/batch-cache?days=7`);
        const data = await response.json();
        const stats = data.data;
        
        const overall = stats.overall || {};
        const totalQueries = overall.total_queries || 0;
        const totalHashes = overall.total_hashes || 0;
        const totalCached = overall.total_cached || 0;
        const totalMiss = overall.total_miss || 0;
        const avgBatchSize = overall.avg_batch_size || 0;
        const hitRate = overall.hit_rate || 0;
        
        document.getElementById('batch-cache-stats').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📦</div>
                    <div class="stat-value">${formatNumber(totalQueries)}</div>
                    <div class="stat-label">批量查询次数</div>
                    <div class="stat-trend" style="color: #667eea;">最近7天</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🔍</div>
                    <div class="stat-value">${formatNumber(totalHashes)}</div>
                    <div class="stat-label">查询哈希总数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${formatNumber(totalCached)}</div>
                    <div class="stat-label">缓存命中</div>
                    <div class="stat-trend" style="color: #28a745;">${hitRate.toFixed(1)}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${avgBatchSize.toFixed(1)}</div>
                    <div class="stat-label">平均批次大小</div>
                    <div class="stat-trend" style="color: #17a2b8;">个/次</div>
                </div>
            </div>
            
            ${stats.daily && stats.daily.length > 0 ? `
                <div style="margin-top: 20px;">
                    <h3 style="margin-bottom: 10px;">📈 每日统计</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                                <th style="padding: 12px; text-align: left;">日期</th>
                                <th style="padding: 12px; text-align: center;">查询次数</th>
                                <th style="padding: 12px; text-align: center;">哈希数</th>
                                <th style="padding: 12px; text-align: center;">命中数</th>
                                <th style="padding: 12px; text-align: center;">命中率</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.daily.map((day, index) => `
                                <tr style="background: ${index % 2 === 0 ? '#ffffff' : '#f8f9fa'}; border-bottom: 1px solid #dee2e6;">
                                    <td style="padding: 12px;">${day.date}</td>
                                    <td style="padding: 12px; text-align: center;">${day.queries}</td>
                                    <td style="padding: 12px; text-align: center;">${day.hashes}</td>
                                    <td style="padding: 12px; text-align: center;">${day.cached}</td>
                                    <td style="padding: 12px; text-align: center;">
                                        <span style="color: ${day.hit_rate >= 50 ? '#28a745' : '#ffc107'};">
                                            ${day.hit_rate.toFixed(1)}%
                                        </span>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p style="text-align: center; color: #999; padding: 20px;">暂无数据</p>'}
        `;
        
    } catch (error) {
        document.getElementById('batch-cache-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 加载批量分类统计
async function loadBatchClassifyStats() {
    try {
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/stats/batch-classify?days=7`);
        const data = await response.json();
        const stats = data.data;
        
        const overall = stats.overall || {};
        const totalBatches = overall.total_batches || 0;
        const totalImages = overall.total_images || 0;
        const totalSuccess = overall.total_success || 0;
        const totalFail = overall.total_fail || 0;
        const avgBatchSize = overall.avg_batch_size || 0;
        const avgTimePerImage = overall.avg_time_per_image || 0;
        const successRate = overall.success_rate || 0;
        
        document.getElementById('batch-classify-stats').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📸</div>
                    <div class="stat-value">${formatNumber(totalBatches)}</div>
                    <div class="stat-label">批量分类次数</div>
                    <div class="stat-trend" style="color: #667eea;">最近7天</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🖼️</div>
                    <div class="stat-value">${formatNumber(totalImages)}</div>
                    <div class="stat-label">分类图片总数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${formatNumber(totalSuccess)}</div>
                    <div class="stat-label">成功</div>
                    <div class="stat-trend" style="color: #28a745;">${successRate.toFixed(1)}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">⏱️</div>
                    <div class="stat-value">${avgTimePerImage.toFixed(0)}</div>
                    <div class="stat-label">平均耗时</div>
                    <div class="stat-trend" style="color: #17a2b8;">ms/张</div>
                </div>
            </div>
            
            <div class="stats-grid" style="margin-top: 20px;">
                <div class="stat-card" style="border-left: 4px solid #667eea;">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${avgBatchSize.toFixed(1)}</div>
                    <div class="stat-label">平均批次大小</div>
                    <div class="stat-trend" style="color: #667eea;">张/次</div>
                </div>
                <div class="stat-card" style="border-left: 4px solid ${totalFail > 0 ? '#dc3545' : '#28a745'};">
                    <div class="stat-icon">${totalFail > 0 ? '❌' : '✨'}</div>
                    <div class="stat-value">${formatNumber(totalFail)}</div>
                    <div class="stat-label">失败数</div>
                    <div class="stat-trend" style="color: ${totalFail > 0 ? '#dc3545' : '#999'};">
                        ${totalImages > 0 ? ((totalFail/totalImages*100).toFixed(1)) : 0}%
                    </div>
                </div>
            </div>
            
            ${stats.daily && stats.daily.length > 0 ? `
                <div style="margin-top: 20px;">
                    <h3 style="margin-bottom: 10px;">📈 每日统计</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                                <th style="padding: 12px; text-align: left;">日期</th>
                                <th style="padding: 12px; text-align: center;">批次</th>
                                <th style="padding: 12px; text-align: center;">图片数</th>
                                <th style="padding: 12px; text-align: center;">成功</th>
                                <th style="padding: 12px; text-align: center;">失败</th>
                                <th style="padding: 12px; text-align: center;">成功率</th>
                                <th style="padding: 12px; text-align: center;">平均耗时</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.daily.map((day, index) => `
                                <tr style="background: ${index % 2 === 0 ? '#ffffff' : '#f8f9fa'}; border-bottom: 1px solid #dee2e6;">
                                    <td style="padding: 12px;">${day.date}</td>
                                    <td style="padding: 12px; text-align: center;">${day.batches}</td>
                                    <td style="padding: 12px; text-align: center;">${day.images}</td>
                                    <td style="padding: 12px; text-align: center;">${day.success}</td>
                                    <td style="padding: 12px; text-align: center;">${day.fail}</td>
                                    <td style="padding: 12px; text-align: center;">
                                        <span style="color: ${day.success_rate >= 90 ? '#28a745' : day.success_rate >= 70 ? '#ffc107' : '#dc3545'};">
                                            ${day.success_rate.toFixed(1)}%
                                        </span>
                                    </td>
                                    <td style="padding: 12px; text-align: center;">${day.avg_time.toFixed(0)}ms</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p style="text-align: center; color: #999; padding: 20px;">暂无数据</p>'}
        `;
        
    } catch (error) {
        document.getElementById('batch-classify-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}

// 格式化百分比
function formatPercent(num) {
    return num ? num.toFixed(2) + '%' : '0%';
}

// ==================== 地理位置功能 ====================

// 加载位置数据库统计
async function loadLocationStats() {
    try {
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/location/stats`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const stats = await response.json();
        
        document.getElementById('location-stats').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">🏙️</div>
                    <div class="stat-value">${formatNumber(stats.total_cities)}</div>
                    <div class="stat-label">总城市数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🀄</div>
                    <div class="stat-value">${formatNumber(stats.cities_with_chinese)}</div>
                    <div class="stat-label">有中文名称</div>
                    <div class="stat-trend" style="color: #28a745;">覆盖率: ${stats.chinese_coverage_percent}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">👥</div>
                    <div class="stat-value">${formatNumber(stats.cities_above_100k)}</div>
                    <div class="stat-label">人口≥10万</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${formatNumber(stats.cities_queryable)}</div>
                    <div class="stat-label">可查询城市</div>
                    <div class="stat-trend" style="color: #667eea;">人口≥10万且有中文</div>
                </div>
            </div>
            
            <h3 style="margin-top: 25px; margin-bottom: 15px; color: #333;">📊 调用统计</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📍</div>
                    <div class="stat-value">${formatNumber(stats.total_queries_today)}</div>
                    <div class="stat-label">今日查询总数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🎯</div>
                    <div class="stat-value">${formatNumber(stats.nearest_queries_today)}</div>
                    <div class="stat-label">最近城市查询</div>
                    <div class="stat-trend" style="color: #667eea;">今日</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🗺️</div>
                    <div class="stat-value">${formatNumber(stats.nearby_queries_today)}</div>
                    <div class="stat-label">附近城市查询</div>
                    <div class="stat-trend" style="color: #667eea;">今日</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📈</div>
                    <div class="stat-value">${formatNumber(stats.total_queries_all)}</div>
                    <div class="stat-label">累计查询总数</div>
                </div>
            </div>
            
            <div style="margin-top: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px; font-size: 0.9rem; color: #666;">
                <strong>说明：</strong>API接口只返回人口≥10万且有中文名称的城市，确保所有结果都有中文显示。
                当前可查询 <strong style="color: #667eea;">${formatNumber(stats.cities_queryable)}</strong> 个城市，
                覆盖率 <strong style="color: #28a745;">${stats.queryable_coverage_percent}%</strong>。
            </div>
        `;
    } catch (error) {
        document.getElementById('location-stats').innerHTML = `
            <div class="alert alert-error">❌ 加载统计信息失败: ${error.message}</div>
        `;
    }
}

// 设置坐标到输入框
function setCoordinates(lat, lng) {
    document.getElementById('nearest-latitude').value = lat;
    document.getElementById('nearest-longitude').value = lng;
    document.getElementById('nearby-latitude').value = lat;
    document.getElementById('nearby-longitude').value = lng;
}

// 查询最近的城市
async function queryNearestCity() {
    const latitude = parseFloat(document.getElementById('nearest-latitude').value);
    const longitude = parseFloat(document.getElementById('nearest-longitude').value);
    
    if (isNaN(latitude) || isNaN(longitude)) {
        document.getElementById('nearest-city-result').innerHTML = `
            <div class="alert alert-error">❌ 请输入有效的经纬度</div>
        `;
        return;
    }
    
    if (latitude < -90 || latitude > 90) {
        document.getElementById('nearest-city-result').innerHTML = `
            <div class="alert alert-error">❌ 纬度必须在 -90 到 90 之间</div>
        `;
        return;
    }
    
    if (longitude < -180 || longitude > 180) {
        document.getElementById('nearest-city-result').innerHTML = `
            <div class="alert alert-error">❌ 经度必须在 -180 到 180 之间</div>
        `;
        return;
    }
    
    document.getElementById('nearest-city-result').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>查询中...</p>
        </div>
    `;
    
    try {
        const response = await fetch(
            `${currentConfig.apiUrl}/api/v1/location/nearest-city?latitude=${latitude}&longitude=${longitude}`
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const city = await response.json();
        
        document.getElementById('nearest-city-result').innerHTML = `
            <div class="result-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <h3 style="color: white; border-bottom-color: rgba(255,255,255,0.3);">🏙️ ${city.name_zh || city.name}</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">中文名</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">${city.name_zh || city.name}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">英文名</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">${city.name}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">距离</div>
                        <div style="font-size: 1.2rem; font-weight: bold; color: #ffd700;">📏 ${city.distance_km.toFixed(2)} km</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">人口</div>
                        <div style="font-size: 1.2rem; font-weight: bold;">👥 ${formatNumber(city.population)}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">纬度</div>
                        <div style="font-size: 1.1rem;">${city.latitude.toFixed(6)}°</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">经度</div>
                        <div style="font-size: 1.1rem;">${city.longitude.toFixed(6)}°</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">国家代码</div>
                        <div style="font-size: 1.1rem;">${city.country_code}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 0.9rem; opacity: 0.8;">GeoName ID</div>
                        <div style="font-size: 1.1rem;">${city.geoname_id}</div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        document.getElementById('nearest-city-result').innerHTML = `
            <div class="alert alert-error">❌ 查询失败: ${error.message}</div>
        `;
    }
}

// 查询附近城市列表
async function queryNearbyCities() {
    const latitude = parseFloat(document.getElementById('nearby-latitude').value);
    const longitude = parseFloat(document.getElementById('nearby-longitude').value);
    const limit = parseInt(document.getElementById('nearby-limit').value) || 10;
    const maxDistance = document.getElementById('nearby-max-distance').value;
    
    if (isNaN(latitude) || isNaN(longitude)) {
        document.getElementById('nearby-cities-result').innerHTML = `
            <div class="alert alert-error">❌ 请输入有效的经纬度</div>
        `;
        return;
    }
    
    if (latitude < -90 || latitude > 90) {
        document.getElementById('nearby-cities-result').innerHTML = `
            <div class="alert alert-error">❌ 纬度必须在 -90 到 90 之间</div>
        `;
        return;
    }
    
    if (longitude < -180 || longitude > 180) {
        document.getElementById('nearby-cities-result').innerHTML = `
            <div class="alert alert-error">❌ 经度必须在 -180 到 180 之间</div>
        `;
        return;
    }
    
    document.getElementById('nearby-cities-result').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>查询中...</p>
        </div>
    `;
    
    try {
        let url = `${currentConfig.apiUrl}/api/v1/location/nearby-cities?latitude=${latitude}&longitude=${longitude}&limit=${limit}`;
        if (maxDistance && maxDistance.trim() !== '') {
            url += `&max_distance_km=${parseFloat(maxDistance)}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const cities = await response.json();
        
        if (!cities || cities.length === 0) {
            document.getElementById('nearby-cities-result').innerHTML = `
                <div class="alert alert-warning">⚠️ 未找到附近的城市</div>
            `;
            return;
        }
        
        let html = `
            <div class="result-box">
                <h3>找到 ${cities.length} 个城市</h3>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; margin-top: 15px; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                                <th style="padding: 12px; text-align: left;">#</th>
                                <th style="padding: 12px; text-align: left;">中文名称</th>
                                <th style="padding: 12px; text-align: left;">英文名称</th>
                                <th style="padding: 12px; text-align: right;">距离(km)</th>
                                <th style="padding: 12px; text-align: right;">人口</th>
                                <th style="padding: 12px; text-align: center;">坐标</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        cities.forEach((city, index) => {
            const displayName = city.name_zh || city.name;
            html += `
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 12px;">${index + 1}</td>
                    <td style="padding: 12px; font-weight: bold;">${displayName}</td>
                    <td style="padding: 12px; color: #666;">${city.name}</td>
                    <td style="padding: 12px; text-align: right; color: #667eea; font-weight: bold;">${city.distance_km.toFixed(2)}</td>
                    <td style="padding: 12px; text-align: right;">${formatNumber(city.population)}</td>
                    <td style="padding: 12px; text-align: center; font-size: 0.9rem; color: #666;">
                        ${city.latitude.toFixed(4)}°, ${city.longitude.toFixed(4)}°
                    </td>
                </tr>
            `;
        });
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        document.getElementById('nearby-cities-result').innerHTML = html;
    } catch (error) {
        document.getElementById('nearby-cities-result').innerHTML = `
            <div class="alert alert-error">❌ 查询失败: ${error.message}</div>
        `;
    }
}

// ==================== ImageNet类别映射 ====================

// 加载ImageNet类别映射
async function loadImageNetClasses() {
    if (imagenetClasses) {
        return imagenetClasses;
    }
    
    try {
        const response = await fetch('/imagenet_classes.json');
        imagenetClasses = await response.json();
        return imagenetClasses;
    } catch (error) {
        console.error('加载ImageNet类别映射失败:', error);
        return {};
    }
}

// 获取ImageNet类别名称
function getImageNetClassName(classId) {
    if (!imagenetClasses) {
        return `imagenet_class_${classId}`;
    }
    return imagenetClasses[classId.toString()] || `imagenet_class_${classId}`;
}

// ==================== 分类测试功能 ====================

// 全局变量
let selectedFile = null;

// 处理文件选择
function handleFileSelect() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    if (file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('preview-image').src = e.target.result;
            document.getElementById('upload-area').classList.add('hidden');
            document.getElementById('preview-area').classList.remove('hidden');
            document.getElementById('result-area').classList.add('hidden');
        };
        reader.readAsDataURL(file);
    }
}

// 重置上传
function resetUpload() {
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('upload-area').classList.remove('hidden');
    document.getElementById('preview-area').classList.add('hidden');
    document.getElementById('result-area').classList.add('hidden');
}

// 分类图片
async function classifyImage() {
    if (!selectedFile) {
        showAlert('test-alert', '❌ 请先选择图片', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('image', selectedFile);
    
    // 显示加载状态
    document.getElementById('classification-result').innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <div class="spinner" style="margin: 0 auto 15px;"></div>
            <p>正在分类，请稍候...</p>
        </div>
    `;
    document.getElementById('result-area').classList.remove('hidden');
    
    try {
        const startTime = Date.now();
        const response = await fetch(`${currentConfig.apiUrl}/api/v1/classify`, {
            method: 'POST',
            body: formData
        });
        const processingTime = Date.now() - startTime;
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '分类失败');
        }
        
        const result = await response.json();
        
        // 显示结果
        let html = `
            <div class="alert" style="background: #d4edda; color: #155724; border: 1px solid #c3e6cb; margin-bottom: 20px;">
                ✅ 分类成功！耗时: ${processingTime}ms
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin: 0 0 15px 0; color: #667eea;">📊 分类结果</h3>
                <p><strong>分类:</strong> <span style="color: #667eea; font-size: 1.2em;">${result.data.category}</span></p>
                <p><strong>置信度:</strong> ${(result.data.confidence * 100).toFixed(1)}%</p>
                <p><strong>描述:</strong> ${result.data.description || '无'}</p>
                <p><strong>来源:</strong> ${result.from_cache ? '💾 缓存' : '🔄 实时推理'}</p>
            </div>
        `;
        
        // 如果使用了本地推理，显示详细检测结果
        if (result.data.local_inference_result) {
            html += await displayLocalInferenceDetails(result.data.local_inference_result);
        }
        
        // 原始JSON
        html += `
            <details style="margin-top: 20px;">
                <summary style="cursor: pointer; padding: 10px; background: #f8f9fa; border-radius: 8px;">查看完整JSON</summary>
                <pre style="background: #f5f5f5; padding: 15px; border-radius: 8px; overflow-x: auto; margin-top: 10px; font-size: 0.85rem;">${JSON.stringify(result, null, 2)}</pre>
            </details>
        `;
        
        document.getElementById('classification-result').innerHTML = html;
        
    } catch (error) {
        document.getElementById('classification-result').innerHTML = `
            <div class="alert alert-error">
                ❌ 分类失败: ${error.message}
            </div>
        `;
    }
}

// 显示本地推理详细结果（当返回结果中包含local_inference_result时）
async function displayLocalInferenceDetails(localResult) {
    if (!localResult) return '';
    
    // 加载ImageNet类别映射
    await loadImageNetClasses();
    
    let html = `
        <h3 style="margin-top: 20px; color: #667eea;">🤖 本地推理详细结果</h3>
    `;
    
    // ID卡检测结果
    if (localResult.idCardDetections && localResult.idCardDetections.length > 0) {
        html += `
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <h4 style="margin: 0 0 10px 0;">🆔 ID卡检测 (${localResult.idCardDetections.length}个)</h4>
                <ul style="margin: 0; padding-left: 20px;">
        `;
        localResult.idCardDetections.forEach(det => {
            html += `
                <li>
                    <strong>${det.className}</strong> - 置信度: ${(det.confidence * 100).toFixed(1)}%
                </li>
            `;
        });
        html += `</ul></div>`;
    }
    
    // YOLO通用检测结果
    if (localResult.generalDetections && localResult.generalDetections.length > 0) {
        html += `
            <div style="background: #d1ecf1; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <h4 style="margin: 0 0 10px 0;">🔍 YOLO检测 (${localResult.generalDetections.length}个物体)</h4>
                <ul style="margin: 0; padding-left: 20px;">
        `;
        localResult.generalDetections.slice(0, 10).forEach(det => {
            html += `
                <li>
                    <strong>${det.className}</strong> - 置信度: ${(det.confidence * 100).toFixed(1)}%
                </li>
            `;
        });
        if (localResult.generalDetections.length > 10) {
            html += `<li>... 还有 ${localResult.generalDetections.length - 10} 个</li>`;
        }
        html += `</ul></div>`;
    }
    
    // MobileNetV3分类结果
    if (localResult.mobileNetV3Detections && localResult.mobileNetV3Detections.predictions) {
        html += `
            <div style="background: #e7e7ff; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <h4 style="margin: 0 0 10px 0;">🧠 MobileNetV3分类 (Top-5)</h4>
                <ul style="margin: 0; padding-left: 20px;">
        `;
        localResult.mobileNetV3Detections.predictions.forEach((pred, index) => {
            const className = getImageNetClassName(pred.index);
            html += `
                <li>
                    <strong>#${index + 1}</strong>: ${className} - 概率: ${(pred.probability * 100).toFixed(1)}%
                </li>
            `;
        });
        html += `</ul></div>`;
    }
    
    return html;
}

// 加载图片编辑统计
async function loadImageEditStats() {
    try {
        const response = await authFetch(`${currentConfig.apiUrl}/api/v1/stats/image-edit?days=7`);
        const data = await response.json();
        const stats = data.data;
        
        const overall = stats.overall || {};
        const cache = stats.cache || {};
        
        document.getElementById('image-edit-stats').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">🎨</div>
                    <div class="stat-value">${formatNumber(overall.total_tasks || 0)}</div>
                    <div class="stat-label">编辑任务总数</div>
                    <div class="stat-trend" style="color: #667eea;">最近7天</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🖼️</div>
                    <div class="stat-value">${formatNumber(overall.total_images || 0)}</div>
                    <div class="stat-label">编辑图片总数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${formatNumber(overall.completed_tasks || 0)}</div>
                    <div class="stat-label">已完成任务</div>
                    <div class="stat-trend" style="color: #28a745;">
                        ${overall.total_tasks > 0 ? ((overall.completed_tasks / overall.total_tasks * 100).toFixed(1)) : 0}%
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${(overall.avg_images_per_task || 0).toFixed(1)}</div>
                    <div class="stat-label">平均图片数</div>
                    <div class="stat-trend" style="color: #667eea;">张/任务</div>
                </div>
            </div>
            
            <div class="stats-grid" style="margin-top: 20px;">
                <div class="stat-card" style="border-left: 4px solid #28a745;">
                    <div class="stat-icon">🎯</div>
                    <div class="stat-value">${formatNumber(cache.cache_hits || 0)}</div>
                    <div class="stat-label">缓存命中</div>
                    <div class="stat-trend" style="color: #28a745;">${(cache.hit_rate || 0).toFixed(1)}%</div>
                </div>
                <div class="stat-card" style="border-left: 4px solid #ffc107;">
                    <div class="stat-icon">🔍</div>
                    <div class="stat-value">${formatNumber(cache.cache_misses || 0)}</div>
                    <div class="stat-label">缓存未命中</div>
                    <div class="stat-trend" style="color: #ffc107;">
                        ${cache.total_calls > 0 ? ((cache.cache_misses / cache.total_calls * 100).toFixed(1)) : 0}%
                    </div>
                </div>
                <div class="stat-card" style="border-left: 4px solid #17a2b8;">
                    <div class="stat-icon">📞</div>
                    <div class="stat-value">${formatNumber(cache.total_calls || 0)}</div>
                    <div class="stat-label">API调用总数</div>
                </div>
            </div>
            
            ${stats.daily && stats.daily.length > 0 ? `
                <div style="margin-top: 20px;">
                    <h3 style="margin-bottom: 10px;">📈 每日统计</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                                <th style="padding: 12px; text-align: left;">日期</th>
                                <th style="padding: 12px; text-align: center;">任务数</th>
                                <th style="padding: 12px; text-align: center;">图片数</th>
                                <th style="padding: 12px; text-align: center;">已完成</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.daily.map((day, index) => `
                                <tr style="background: ${index % 2 === 0 ? '#ffffff' : '#f8f9fa'}; border-bottom: 1px solid #dee2e6;">
                                    <td style="padding: 12px;">${day.date}</td>
                                    <td style="padding: 12px; text-align: center;">${day.tasks}</td>
                                    <td style="padding: 12px; text-align: center;">${day.images}</td>
                                    <td style="padding: 12px; text-align: center;">
                                        <span style="color: #28a745;">${day.completed}</span>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p style="text-align: center; color: #999; padding: 20px;">暂无数据</p>'}
        `;
        
    } catch (error) {
        document.getElementById('image-edit-stats').innerHTML = `
            <div class="alert alert-error">加载失败: ${error.message}</div>
        `;
    }
}


