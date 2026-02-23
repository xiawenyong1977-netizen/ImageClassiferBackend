"""
配置管理模块
使用pydantic-settings进行环境变量管理
支持从文件加载提示词配置
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator, model_validator
from typing import List, Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # ===== MySQL配置 =====
    MYSQL_HOST: str = Field(default="localhost", description="MySQL主机")
    MYSQL_PORT: int = Field(default=3306, description="MySQL端口")
    MYSQL_USER: str = Field(default="root", description="MySQL用户名")
    MYSQL_PASSWORD: str = Field(default="", description="MySQL密码")
    MYSQL_DATABASE: str = Field(default="image_classifier", description="数据库名")
    MYSQL_UNIX_SOCKET: Optional[str] = Field(default=None, description="MySQL Unix Socket路径（如果指定，将优先使用socket连接）")
    MYSQL_POOL_SIZE: int = Field(default=10, description="连接池大小")
    MYSQL_MAX_OVERFLOW: int = Field(default=5, description="最大溢出连接数")
    
    # ===== 大模型配置 =====
    LLM_PROVIDER: str = Field(default="aliyun", description="大模型提供商（aliyun/openai/claude/deepseek）")
    LLM_API_KEY: str = Field(default="", description="大模型API密钥")
    
    # 任务类型对应的模型配置（系统会根据任务类型自动选择对应的模型）
    # 支持的模型列表请参考 app/services/llm/model_config.py
    LLM_MODEL_CLASSIFICATION: Optional[str] = Field(
        default=None, 
        description="图像分类任务使用的模型（可选，如果不指定则使用提供商默认模型）"
    )
    LLM_MODEL_IMAGE_EDIT: Optional[str] = Field(
        default=None, 
        description="图像编辑任务使用的模型（可选，如果不指定则使用提供商默认模型，仅阿里云支持）"
    )
    
    # 任务类型对应的参数配置（如果不指定，系统会根据模型自动选择默认值）
    # 支持的参数请参考 app/services/llm/model_config.py 中的 MODEL_DEFAULT_PARAMS
    LLM_MAX_TOKENS_CLASSIFICATION: Optional[int] = Field(
        default=None, 
        description="图像分类任务的最大token数（可选，如果不指定则使用模型默认值）"
    )
    LLM_TIMEOUT_CLASSIFICATION: Optional[int] = Field(
        default=None, 
        description="图像分类任务的请求超时(秒)（可选，如果不指定则使用模型默认值）"
    )
    LLM_MAX_RETRIES_CLASSIFICATION: Optional[int] = Field(
        default=None, 
        description="图像分类任务的最大重试次数（可选，如果不指定则使用模型默认值）"
    )
    LLM_RETRY_DELAY_CLASSIFICATION: Optional[float] = Field(
        default=None, 
        description="图像分类任务的重试延迟(秒)（可选，如果不指定则使用模型默认值）"
    )
    
    LLM_MAX_TOKENS_IMAGE_EDIT: Optional[int] = Field(
        default=None, 
        description="图像编辑任务的最大token数（可选，如果不指定则使用模型默认值）"
    )
    LLM_TIMEOUT_IMAGE_EDIT: Optional[int] = Field(
        default=None, 
        description="图像编辑任务的请求超时(秒)（可选，如果不指定则使用模型默认值，图像编辑通常需要60秒）"
    )
    LLM_MAX_RETRIES_IMAGE_EDIT: Optional[int] = Field(
        default=None, 
        description="图像编辑任务的最大重试次数（可选，如果不指定则使用模型默认值）"
    )
    LLM_RETRY_DELAY_IMAGE_EDIT: Optional[float] = Field(
        default=None, 
        description="图像编辑任务的重试延迟(秒)（可选，如果不指定则使用模型默认值）"
    )
    
    @field_validator(
        'LLM_MAX_TOKENS_CLASSIFICATION', 'LLM_TIMEOUT_CLASSIFICATION', 'LLM_MAX_RETRIES_CLASSIFICATION',
        'LLM_MAX_TOKENS_IMAGE_EDIT', 'LLM_TIMEOUT_IMAGE_EDIT', 'LLM_MAX_RETRIES_IMAGE_EDIT',
        mode='before'
    )
    @classmethod
    def parse_optional_int(cls, v):
        """将空字符串转换为 None"""
        if v == '' or v is None:
            return None
        return int(v) if isinstance(v, str) else v
    
    @field_validator('LLM_RETRY_DELAY_CLASSIFICATION', 'LLM_RETRY_DELAY_IMAGE_EDIT', mode='before')
    @classmethod
    def parse_optional_float(cls, v):
        """将空字符串转换为 None"""
        if v == '' or v is None:
            return None
        return float(v) if isinstance(v, str) else v
    
    # Deepseek API密钥（用于文本生成功能，如果未配置则使用LLM_API_KEY）
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="Deepseek API密钥（可选，用于文本生成功能）")
    
    # ===== 本地推理配置 =====
    USE_LOCAL_INFERENCE: bool = Field(default=False, description="是否使用本地推理（开启后不调用大模型）")
    LOCAL_INFERENCE_FALLBACK: bool = Field(default=False, description="大模型失败时是否降级到本地推理")
    
    # ===== 应用配置 =====
    APP_HOST: str = Field(default="0.0.0.0", description="应用主机")
    APP_PORT: int = Field(default=8000, description="应用端口")
    APP_DEBUG: bool = Field(default=False, description="调试模式")
    APP_ENV: str = Field(default="production", description="环境")
    
    # ===== 图片配置 =====
    MAX_IMAGE_SIZE_MB: int = Field(default=10, description="最大图片大小(MB)")
    ALLOWED_IMAGE_FORMATS: str = Field(
        default="jpg,jpeg,png,webp,gif,mpo",
        description="允许的图片格式"
    )
    
    # ===== 日志配置 =====
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FILE: str = Field(
        default="/var/log/image-classifier/app.log",
        description="日志文件路径"
    )
    
    # ===== 统计配置 =====
    ENABLE_REQUEST_LOG: bool = Field(default=True, description="是否记录请求日志")
    LOG_RETENTION_DAYS: int = Field(default=90, description="日志保留天数")
    
    # ===== 成本配置 =====
    COST_PER_API_CALL: float = Field(default=0.01, description="每次API调用成本(元)")
    
    # ===== 预定义分类 =====
    CATEGORIES: List[str] = [
        "social_activities",  # 社交活动
        "pets",               # 宠物萌照
        "single_person",      # 单人照片
        "foods",              # 美食记录
        "travel_scenery",     # 旅行风景
        "screenshot",         # 手机截图
        "idcard",             # 证件照
        "qrcode",             # 二维码
        "other"               # 其它
    ]
    
    # ===== 提示词配置 =====
    CLASSIFICATION_PROMPT: str = Field(
        default="""请对这张图片进行分类。你必须从以下9个类别中选择一个：

1. social_activities - 社交活动（聚会、合影、多人互动场景）
2. pets - 宠物萌照（猫、狗等宠物照片）
3. single_person - 单人照片（个人照、自拍、肖像）
4. foods - 美食记录（食物、餐饮、烹饪相关）
5. travel_scenery - 旅行风景（旅游景点、自然风光、城市风景）
6. screenshot - 手机截图（手机屏幕截图、应用界面）
7. idcard - 证件照（身份证、护照、驾照等证件）
8. qrcode - 二维码（只要照片中含有二维码，无论是否还有其他内容，都必须分类为qrcode）
9. other - 其它（无法归类到上述类别）

重要：如果图片中包含二维码（QR码），无论图片中是否还有其他内容，都必须分类为 qrcode。

同时，请识别照片背景的主要颜色。背景颜色必须从以下10种颜色中选择一个：
橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色

请以JSON格式返回结果：
{
    "category": "类别key（必须是上述9个之一）",
    "confidence": 0.95,
    "description": "简短描述图片内容（可选，中文，30字以内）",
    "background_color": "背景颜色（必须是：橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色之一）"
}

只返回JSON，不要有其他文字。""",
        description="图片分类提示词"
    )
    
    CLASSIFICATION_PROMPT_CONTENT_ONLY: str = Field(
        default="""请对这张图片进行分类。你必须从以下9个类别中选择一个：

1. social_activities - 社交活动（聚会、合影、多人互动场景）
2. pets - 宠物萌照（猫、狗等宠物照片）
3. single_person - 单人照片（个人照、自拍、肖像）
4. foods - 美食记录（食物、餐饮、烹饪相关）
5. travel_scenery - 旅行风景（旅游景点、自然风光、城市风景）
6. screenshot - 手机截图（手机屏幕截图、应用界面）
7. idcard - 证件照（身份证、护照、驾照等证件）
8. qrcode - 二维码（只要照片中含有二维码，无论是否还有其他内容，都必须分类为qrcode）
9. other - 其它（无法归类到上述类别）

重要：如果图片中包含二维码（QR码），无论图片中是否还有其他内容，都必须分类为 qrcode。

请以JSON格式返回结果：
{
    "category": "类别key（必须是上述9个之一）",
    "confidence": 0.95,
    "description": "简短描述图片内容（可选，中文，30字以内）"
}

只返回JSON，不要有其他文字。""",
        description="图片分类提示词（仅内容，无背景颜色）"
    )
    
    COLOR_CLASSIFICATION_PROMPT: str = Field(
        default="""请识别这张图片背景的主要颜色。

背景颜色必须从以下10种颜色中选择一个：
橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色

请以JSON格式返回结果：
{
    "background_color": "背景颜色（必须是：橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色之一）",
    "confidence": 0.95
}

只返回JSON，不要有其他文字。""",
        description="颜色分类提示词"
    )
    
    COMPOSITION_ANALYSIS_PROMPT: str = Field(
        default="""请对这张照片的构图进行专业分析和点评。

构图方式识别（必须从以下选择）：
1. rule_of_thirds - 三分法构图（主体位于画面1/3或2/3处）
2. center_composition - 中心构图（主体位于画面中心）
3. symmetry - 对称构图（左右或上下对称）
4. leading_lines - 引导线构图（利用线条引导视线）
5. frame_within_frame - 框架构图（利用前景形成框架）
6. diagonal - 对角线构图（主体沿对角线分布）
7. golden_ratio - 黄金分割构图（符合黄金分割比例）
8. negative_space - 留白构图（大量留白突出主体）
9. other - 其他构图方式

请从以下维度进行详细分析：
- 构图方式：识别主要使用的构图技巧
- 主体位置：分析主体在画面中的位置是否合理
- 视觉平衡：评价画面的视觉平衡感
- 空间布局：分析前景、中景、背景的关系
- 线条与形状：识别画面中的线条和形状元素
- 优点：指出构图上的优点
- 改进建议：提供构图改进建议（如果有）

请以JSON格式返回结果：
{
    "composition_type": "构图类型key（必须是上述9个之一）",
    "confidence": 0.9,
    "subject_position": "主体位置详细描述（如：位于画面右侧1/3处，略微偏上）",
    "visual_balance": "视觉平衡评价（好/一般/需改进）",
    "spatial_layout": "空间布局分析（前景、中景、背景关系，50字以内）",
    "lines_and_shapes": "线条与形状分析（识别主要线条和形状元素，50字以内）",
    "strengths": ["优点1（30字以内）", "优点2（30字以内）"],
    "suggestions": ["建议1（30字以内，如无建议可为空）", "建议2（30字以内，如无建议可为空）"],
    "score": 8.5,
    "detailed_analysis": "详细构图分析（150字以内，中文）"
}

只返回JSON，不要有其他文字。""",
        description="构图分析提示词"
    )
    
    FACE_FORTUNE_PROMPT: str = Field(
        default="""你是一位精通东方面相学和周易玄学的资深命理大师。
根据用户上传的自拍照和咨询事项，进行深度分析。

【当前时间】：{time}
【求测事项】：{event}

请分析此面相在此刻对该事项的影响。

请从以下维度进行面相分析：
1. 额头（forehead）：分析额头特征，包括宽度、高度、纹路等
2. 眼睛（eyes）：分析眼睛特征，包括眼神、眼型、眼距等
3. 鼻子（nose）：分析鼻子特征，包括鼻型、鼻梁、鼻翼等
4. 嘴巴（mouth）：分析嘴巴特征，包括唇形、嘴角、唇色等
5. 整体（overall）：综合分析整体面相特征和气场

基于面相分析，预测该事项的吉凶：
- 状态（status）：大吉/吉/中平/小凶/凶
- 评分（score）：0-100分的数值评分
- 总结（summary）：对该事项的总体预测（100字以内）
- 建议（advice）：给出具体的建议（数组形式，每条30字以内）
- 化解方法（remedy）：如有不利，提供化解方法（50字以内，如无不利可为空）

时间反思（timeReflection）：结合当前时间，分析此时进行该事项的时机是否合适（100字以内）

内容合规检查：
- isCompliant：内容是否合规（true/false）
- complianceReason：合规性说明（如不合规需说明原因）

请以严格的JSON格式返回结果，不得包含Markdown标签：
{
    "isCompliant": true,
    "complianceReason": "内容合规",
    "faceAnalysis": {
        "forehead": "额头分析（50字以内）",
        "eyes": "眼睛分析（50字以内）",
        "nose": "鼻子分析（50字以内）",
        "mouth": "嘴巴分析（50字以内）",
        "overall": "整体面相分析（100字以内）"
    },
    "eventAnalysis": {
        "status": "大吉/吉/中平/小凶/凶",
        "score": 85,
        "summary": "对该事项的总体预测（100字以内）",
        "advice": ["建议1（30字以内）", "建议2（30字以内）"],
        "remedy": "化解方法（50字以内，如无不利可为空字符串）"
    },
    "timeReflection": "时间反思（100字以内）"
}

只返回JSON，不要有其他文字。""",
        description="面相预测提示词"
    )
    
    REVERSE_GEOCODING_PROMPT: str = Field(
        default="""请根据以下坐标列表，返回每个坐标的三级行政区信息（JSON数组格式）。

要求：
1. 返回中英文名称
2. 返回三级行政区：国家、一级行政区（省/州）、二级行政区（市/县）
3. 如果没有一级或二级行政区（如梵蒂冈等小国），保留为空
4. **必须返回查询坐标（query_latitude, query_longitude）和城市坐标（city_latitude, city_longitude）**
5. 返回结果必须按照输入顺序，且每个结果必须包含对应的index

坐标列表：
{coords_json}

请返回以下格式的JSON数组：
[
    {{
        "index": 0,
        "query_latitude": 39.9042,      // 查询坐标（输入的圆心坐标）
        "query_longitude": 116.4074,     // 查询坐标（输入的圆心坐标）
        "city_latitude": 39.9042,        // 城市坐标（实际城市位置）
        "city_longitude": 116.4074,      // 城市坐标（实际城市位置）
        "country_code": "CN",
        "country_name_zh": "中国",
        "country_name_en": "China",
        "admin1_name_zh": "北京市",
        "admin1_name_en": "Beijing",
        "admin2_name_zh": "东城区",
        "admin2_name_en": "Dongcheng",
        "city_name_zh": "北京市",
        "city_name_en": "Beijing"
    }}
]

重要提示：
1. query_latitude 和 query_longitude 必须与输入坐标完全一致
2. city_latitude 和 city_longitude 是实际城市的位置坐标
3. 返回结果必须包含所有输入坐标，且index必须对应
4. 只返回JSON数组，不要包含其他文字说明""",
        description="逆地址编码提示词"
    )
    
    # ===== 认证配置 =====
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production-please-use-strong-random-key",
        description="JWT密钥（请在生产环境修改为随机强密钥）"
    )
    
    # ===== 支付配置 =====
    # 测试价格配置
    MEMBER_PRICE_TEST: float = Field(default=0.10, description="会员测试价格(元)")
    CREDITS_PRICE_TEST: float = Field(default=0.01, description="额度测试价格(元)")
    CREDITS_AMOUNT_TEST: int = Field(default=1, description="测试额度数量（默认值，已废弃，使用CREDITS_AMOUNTS_TEST）")
    CREDITS_AMOUNTS_TEST: str = Field(default="1;5;10;50;100", description="测试额度套餐数量列表（用分号分隔）")
    
    # 正式价格配置（待启用）
    MEMBER_PRICE_PROD: float = Field(default=9.90, description="会员正式价格(元)")
    CREDITS_PRICE_PROD: float = Field(default=1.0, description="额度正式价格(元)")
    CREDITS_AMOUNT_PROD: int = Field(default=10, description="正式额度数量（默认值，已废弃，使用CREDITS_AMOUNTS_PROD）")
    CREDITS_AMOUNTS_PROD: str = Field(default="10;20;50;100", description="正式额度套餐数量列表（用分号分隔）")
    
    # 价格模式切换
    USE_TEST_PRICE: bool = Field(default=False, description="是否使用测试价格")
    
    # ===== 微信配置 =====
    WECHAT_APPID: str = Field(default="", description="微信AppID")
    WECHAT_SECRET: str = Field(default="", description="微信AppSecret")
    WECHAT_TOKEN: str = Field(default="", description="微信Token（用于服务器验证）")
    
    # ===== 微信支付配置 =====
    WECHAT_PAY_MCHID: str = Field(default="", description="微信支付商户号")
    WECHAT_PAY_API_KEY: str = Field(default="", description="微信支付API密钥")
    WECHAT_PAY_NOTIFY_URL: str = Field(
        default="https://your-domain.com/api/v1/payment/notify",
        description="微信支付回调URL"
    )
    
    # ===== 图像编辑结果图片URL配置 =====
    IMAGE_EDIT_BASE_URL: str = Field(
        default="https://api.aifuture.net.cn",
        description="图像编辑结果图片的基础URL（新服务器域名）"
    )
    
    # ===== 图像编辑功能配置 =====
    ALLOW_IMAGE_EDIT_WITHOUT_OPENID: bool = Field(
        default=False,
        description="是否允许未关注公众号的用户使用修图功能（开启后不检查额度，不扣减额度）"
    )
    
    # ===== 七牛云配置 =====
    QINIU_ACCESS_KEY: str = Field(default="", description="七牛云Access Key")
    QINIU_SECRET_KEY: str = Field(default="", description="七牛云Secret Key")
    QINIU_BUCKET_NAME: str = Field(default="", description="七牛云存储空间名称")
    QINIU_DOMAIN: str = Field(default="", description="七牛云CDN域名（如：https://cdn.example.com）")
    
    # ===== 地理位置API配置 =====
    GAODE_API_KEY: str = Field(default="", description="高德地图API密钥")
    GAODE_API_URL: str = Field(
        default="https://restapi.amap.com/v3/geocode/regeo",
        description="高德地图逆地理编码API地址"
    )
    NOMINATIM_API_URL: str = Field(
        default="https://nominatim.openstreetmap.org/reverse",
        description="Nominatim逆地理编码API地址"
    )
    NOMINATIM_RATE_LIMIT: float = Field(
        default=1.0,
        description="Nominatim API调用频率限制（秒/请求）"
    )
    
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT算法")
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = Field(default=1, description="Token过期天数")
    
    ADMIN_USERNAME: str = Field(default="zywl", description="管理员用户名")
    ADMIN_PASSWORD_HASH: str = Field(
        default="$2b$12$rY8vqF5xKZYP8QHXKvN8HeqN8WvXqQxVqYqzL9WQxN9wYvN8HeqN8",
        description="管理员密码哈希（bcrypt）"
    )
    
    @property
    def mysql_url(self) -> str:
        """获取MySQL连接URL"""
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    @property
    def max_image_size_bytes(self) -> int:
        """获取最大图片大小（字节）"""
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    @property
    def allowed_formats_list(self) -> List[str]:
        """获取允许的图片格式列表"""
        return [fmt.strip().lower() for fmt in self.ALLOWED_IMAGE_FORMATS.split(",")]
    
    model_config = ConfigDict(
        # 支持多个环境变量文件，按顺序加载，后面的会覆盖前面的
        # 1. 先加载 .env（非敏感配置）
        # 2. 再加载 .env.secrets（敏感配置，如果存在）
        env_file=[".env", ".env.secrets"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        # 允许从环境变量覆盖（优先级最高）
        extra="ignore"
    )
    
    @model_validator(mode='after')
    def load_prompts_from_files(self):
        """
        从 prompts/ 目录加载提示词文件（如果存在且环境变量未设置）
        
        配置优先级（从高到低）：
        1. 环境变量（.env 文件中手动设置，用于特殊覆盖）
        2. prompts/ 目录下的文件（如果存在，自动读取，用于版本控制）
        3. config.py 中的默认值（如果文件不存在，使用此默认值）
        
        注意：环境变量和 prompts/ 文件不会同时生效。
        如果环境变量已设置，则使用环境变量；否则尝试从 prompts/ 文件读取。
        """
        prompt_mappings = {
            "CLASSIFICATION_PROMPT": "classification",
            "CLASSIFICATION_PROMPT_CONTENT_ONLY": "classification_content_only",
            "COLOR_CLASSIFICATION_PROMPT": "color_classification",
            "COMPOSITION_ANALYSIS_PROMPT": "composition_analysis",
            "FACE_FORTUNE_PROMPT": "face_fortune",
            "REVERSE_GEOCODING_PROMPT": "reverse_geocoding",
        }
        
        for env_key, file_name in prompt_mappings.items():
            # 如果环境变量中没有设置，尝试从文件加载
            if env_key not in os.environ:
                current_value = getattr(self, env_key, None)
                if current_value:
                    # 获取项目根目录
                    current_dir = Path(__file__).parent.parent
                    prompt_file = current_dir / "prompts" / f"{file_name}.txt"
                    
                    if prompt_file.exists():
                        try:
                            file_content = prompt_file.read_text(encoding="utf-8").rstrip()
                            # 如果文件内容与当前值不同，使用文件内容
                            if file_content != current_value:
                                setattr(self, env_key, file_content)
                        except Exception as e:
                            # 如果读取失败，保持当前值（默认值）
                            import sys
                            from loguru import logger
                            logger.warning(f"无法读取提示词文件 {prompt_file}: {e}，使用默认值")
        
        return self


# 全局配置实例
settings = Settings()

