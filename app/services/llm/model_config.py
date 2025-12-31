"""
大模型配置模块
定义支持的模型列表和任务-模型映射关系
"""

from typing import Dict, List, Optional
from enum import Enum


class TaskType(str, Enum):
    """任务类型枚举"""
    CLASSIFICATION = "classification"  # 图像分类
    IMAGE_EDIT = "image_edit"  # 图像编辑
    TEXT_GENERATION = "text_generation"  # 文本生成


class Provider(str, Enum):
    """提供商枚举"""
    ALIYUN = "aliyun"
    OPENAI = "openai"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"


# 支持的模型列表（按提供商分类）
SUPPORTED_MODELS = {
    Provider.ALIYUN: {
        TaskType.CLASSIFICATION: ["qwen-vl-plus"],
        TaskType.IMAGE_EDIT: ["qwen-image-edit"],
        TaskType.TEXT_GENERATION: ["qwen-turbo", "qwen-plus", "qwen-max"]
    },
    Provider.OPENAI: {
        TaskType.CLASSIFICATION: ["gpt-4-vision-preview", "gpt-4o"],
        TaskType.IMAGE_EDIT: [],  # OpenAI暂不支持图像编辑
        TaskType.TEXT_GENERATION: ["gpt-4", "gpt-3.5-turbo"]
    },
    Provider.CLAUDE: {
        TaskType.CLASSIFICATION: ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        TaskType.IMAGE_EDIT: [],  # Claude暂不支持图像编辑
        TaskType.TEXT_GENERATION: ["claude-3-opus", "claude-3-sonnet"]
    },
    Provider.DEEPSEEK: {
        TaskType.CLASSIFICATION: [],  # Deepseek暂不支持图像分类
        TaskType.IMAGE_EDIT: [],  # Deepseek暂不支持图像编辑
        TaskType.TEXT_GENERATION: ["deepseek-chat"]
    }
}

# 任务类型对应的默认模型（按提供商）
DEFAULT_MODELS = {
    Provider.ALIYUN: {
        TaskType.CLASSIFICATION: "qwen-vl-plus",
        TaskType.IMAGE_EDIT: "qwen-image-edit",
        TaskType.TEXT_GENERATION: "qwen-turbo"
    },
    Provider.OPENAI: {
        TaskType.CLASSIFICATION: "gpt-4-vision-preview",
        TaskType.IMAGE_EDIT: None,  # 不支持
        TaskType.TEXT_GENERATION: "gpt-4"
    },
    Provider.CLAUDE: {
        TaskType.CLASSIFICATION: "claude-3-opus",
        TaskType.IMAGE_EDIT: None,  # 不支持
        TaskType.TEXT_GENERATION: "claude-3-opus"
    },
    Provider.DEEPSEEK: {
        TaskType.CLASSIFICATION: None,  # 不支持
        TaskType.IMAGE_EDIT: None,  # 不支持
        TaskType.TEXT_GENERATION: "deepseek-chat"
    }
}


def get_supported_models(provider: str, task_type: TaskType) -> List[str]:
    """
    获取指定提供商和任务类型支持的模型列表
    
    Args:
        provider: 提供商名称
        task_type: 任务类型
        
    Returns:
        支持的模型列表
    """
    provider_enum = Provider(provider.lower())
    return SUPPORTED_MODELS.get(provider_enum, {}).get(task_type, [])


def get_default_model(provider: str, task_type: TaskType) -> Optional[str]:
    """
    获取指定提供商和任务类型的默认模型
    
    Args:
        provider: 提供商名称
        task_type: 任务类型
        
    Returns:
        默认模型名称，如果不支持则返回None
    """
    provider_enum = Provider(provider.lower())
    return DEFAULT_MODELS.get(provider_enum, {}).get(task_type)


def is_model_supported(provider: str, task_type: TaskType, model: str) -> bool:
    """
    检查指定模型是否支持指定的任务类型
    
    Args:
        provider: 提供商名称
        task_type: 任务类型
        model: 模型名称
        
    Returns:
        是否支持
    """
    supported = get_supported_models(provider, task_type)
    return model in supported


def validate_model_for_task(provider: str, task_type: TaskType, model: str) -> bool:
    """
    验证模型是否适用于指定任务
    
    Args:
        provider: 提供商名称
        task_type: 任务类型
        model: 模型名称
        
    Returns:
        是否有效
        
    Raises:
        ValueError: 如果模型不支持该任务类型
    """
    if not is_model_supported(provider, task_type, model):
        supported = get_supported_models(provider, task_type)
        raise ValueError(
            f"模型 {model} 不支持任务类型 {task_type.value}。"
            f"提供商 {provider} 支持的任务类型 {task_type.value} 的模型: {supported}"
        )
    return True


# 模型默认参数配置（按任务类型和模型）
# 格式：{provider: {task_type: {model: {max_tokens, timeout, max_retries, retry_delay}}}}
MODEL_DEFAULT_PARAMS = {
    Provider.ALIYUN: {
        TaskType.CLASSIFICATION: {
            "qwen-vl-plus": {
                "max_tokens": 500,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        },
        TaskType.IMAGE_EDIT: {
            "qwen-image-edit": {
                "max_tokens": 0,  # 图像编辑不返回文本，不需要tokens
                "timeout": 60,  # 图像编辑需要更长时间
                "max_retries": 3,
                "retry_delay": 2.0  # 图像编辑重试延迟稍长
            }
        },
        TaskType.TEXT_GENERATION: {
            "qwen-turbo": {
                "max_tokens": 2000,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "qwen-plus": {
                "max_tokens": 2000,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "qwen-max": {
                "max_tokens": 2000,
                "timeout": 60,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        }
    },
    Provider.OPENAI: {
        TaskType.CLASSIFICATION: {
            "gpt-4-vision-preview": {
                "max_tokens": 500,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "gpt-4o": {
                "max_tokens": 500,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        },
        TaskType.TEXT_GENERATION: {
            "gpt-4": {
                "max_tokens": 2000,
                "timeout": 60,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "gpt-3.5-turbo": {
                "max_tokens": 2000,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        }
    },
    Provider.CLAUDE: {
        TaskType.CLASSIFICATION: {
            "claude-3-opus": {
                "max_tokens": 500,
                "timeout": 60,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "claude-3-sonnet": {
                "max_tokens": 500,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "claude-3-haiku": {
                "max_tokens": 500,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        },
        TaskType.TEXT_GENERATION: {
            "claude-3-opus": {
                "max_tokens": 4000,
                "timeout": 60,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "claude-3-sonnet": {
                "max_tokens": 4000,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        }
    },
    Provider.DEEPSEEK: {
        TaskType.TEXT_GENERATION: {
            "deepseek-chat": {
                "max_tokens": 2000,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        }
    }
}


def get_model_default_params(provider: str, task_type: TaskType, model: str) -> Dict[str, any]:
    """
    获取指定模型的默认参数
    
    Args:
        provider: 提供商名称
        task_type: 任务类型
        model: 模型名称
        
    Returns:
        参数字典，包含 max_tokens, timeout, max_retries, retry_delay
        如果未找到，返回通用默认值
    """
    provider_enum = Provider(provider.lower())
    task_params = MODEL_DEFAULT_PARAMS.get(provider_enum, {}).get(task_type, {})
    model_params = task_params.get(model)
    
    if model_params:
        return model_params.copy()
    
    # 返回通用默认值
    return {
        "max_tokens": 500,
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1.0
    }

