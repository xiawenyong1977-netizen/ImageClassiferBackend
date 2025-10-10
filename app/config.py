"""
配置管理模块
使用pydantic-settings进行环境变量管理
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    
    # ===== MySQL配置 =====
    MYSQL_HOST: str = Field(default="localhost", description="MySQL主机")
    MYSQL_PORT: int = Field(default=3306, description="MySQL端口")
    MYSQL_USER: str = Field(default="root", description="MySQL用户名")
    MYSQL_PASSWORD: str = Field(default="", description="MySQL密码")
    MYSQL_DATABASE: str = Field(default="image_classifier", description="数据库名")
    MYSQL_POOL_SIZE: int = Field(default=10, description="连接池大小")
    MYSQL_MAX_OVERFLOW: int = Field(default=5, description="最大溢出连接数")
    
    # ===== 大模型配置 =====
    LLM_PROVIDER: str = Field(default="openai", description="大模型提供商")
    LLM_API_KEY: str = Field(default="", description="大模型API密钥")
    LLM_MODEL: str = Field(default="gpt-4-vision-preview", description="模型名称")
    LLM_MAX_TOKENS: int = Field(default=500, description="最大token数")
    LLM_TIMEOUT: int = Field(default=30, description="请求超时(秒)")
    
    # ===== 应用配置 =====
    APP_HOST: str = Field(default="0.0.0.0", description="应用主机")
    APP_PORT: int = Field(default=8000, description="应用端口")
    APP_DEBUG: bool = Field(default=False, description="调试模式")
    APP_ENV: str = Field(default="production", description="环境")
    
    # ===== 图片配置 =====
    MAX_IMAGE_SIZE_MB: int = Field(default=10, description="最大图片大小(MB)")
    ALLOWED_IMAGE_FORMATS: str = Field(
        default="jpg,jpeg,png,webp,gif",
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
        "other"               # 其它
    ]
    
    # ===== 提示词配置 =====
    CLASSIFICATION_PROMPT: str = Field(
        default="""请对这张图片进行分类。你必须从以下8个类别中选择一个：

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

只返回JSON，不要有其他文字。""",
        description="图片分类提示词"
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()

