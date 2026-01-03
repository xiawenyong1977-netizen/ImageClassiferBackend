"""
大模型客户端
支持阿里云通义千问、OpenAI和Claude的Vision API
"""

import base64
import json
from typing import Dict
from app.config import settings
from loguru import logger
import httpx


class ModelClient:
    """大模型客户端类"""
    
    # 预定义的分类类别
    CATEGORIES = [
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
    
    # 预定义的背景颜色
    BACKGROUND_COLORS = [
        "橙色", "蓝色", "红色", "绿色", "紫色",
        "粉色", "黄色", "灰色", "黑色", "白色"
    ]
    
    def __init__(self):
        from app.services.llm.model_config import TaskType, get_default_model
        
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        # 🔥 使用分类任务的默认模型（向后兼容）
        # 优先级：1. LLM_MODEL_CLASSIFICATION配置 2. 提供商默认模型
        if settings.LLM_MODEL_CLASSIFICATION:
            self.model = settings.LLM_MODEL_CLASSIFICATION
        else:
            # 使用提供商默认的分类模型
            default_model = get_default_model(self.provider, TaskType.CLASSIFICATION)
            if not default_model:
                raise ValueError(f"提供商 {self.provider} 不支持图像分类任务")
            self.model = default_model
    
    async def classify_image(self, image_bytes: bytes) -> Dict:
        """
        调用大模型进行图片分类
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            分类结果字典
            {
                "category": str,
                "confidence": float,
                "description": str,
                "background_color": str
            }
        """
        try:
            if self.provider == "aliyun" or self.provider == "qwen":
                return await self._classify_with_aliyun(image_bytes)
            elif self.provider == "openai":
                return await self._classify_with_openai(image_bytes)
            elif self.provider == "claude":
                return await self._classify_with_claude(image_bytes)
            else:
                raise ValueError(f"不支持的大模型提供商: {self.provider}")
                
        except Exception as e:
            logger.error(f"大模型调用失败: {e}")
            raise
    
    async def _classify_with_aliyun(self, image_bytes: bytes) -> Dict:
        """使用阿里云通义千问VL进行分类（官方SDK）"""
        # 🔍 代码版本检查标记：v2.0-20241207-修复body-KeyError
        logger.debug("✅ model_client.py 已更新到 v2.0-20241207 (修复body-KeyError版本)")
        try:
            import dashscope
            from dashscope import MultiModalConversation
            
            # 设置API密钥
            dashscope.api_key = self.api_key
            
            # Base64编码图片
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 构建prompt
            prompt = self._build_prompt()
            
            # 调用通义千问VL API
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": f"data:image/jpeg;base64,{image_base64}"},
                        {"text": prompt}
                    ]
                }
            ]
            
            # 同步调用（dashscope SDK暂不支持异步）
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: MultiModalConversation.call(
                    model=self.model,
                    messages=messages
                )
            )
            
            # 解析响应（完全避免直接访问可能不存在的属性）
            # 使用 try-except 包裹所有属性访问，防止 KeyError
            # 🔍 代码版本检查：如果看到这个日志，说明新代码已生效
            logger.debug("✅ 使用新版本响应解析逻辑 (v2.0-20241207)")
            status_code = None
            try:
                # 尝试安全获取 status_code
                if hasattr(response, 'status_code'):
                    try:
                        status_code = response.status_code
                    except (KeyError, AttributeError, TypeError):
                        pass
            except Exception:
                pass
            
            # 检查是否是成功响应
            if status_code == 200:
                # 成功响应 - 安全访问 output
                try:
                    if hasattr(response, 'output'):
                        try:
                            output = response.output
                            if hasattr(output, 'choices') and output.choices:
                                try:
                                    content = output.choices[0].message.content[0]['text']
                                    result = self._parse_response(content)
                                    logger.info(f"阿里云通义千问分类完成: {result['category']}")
                                    return result
                                except (KeyError, AttributeError, IndexError, TypeError) as e:
                                    logger.error(f"解析响应内容失败: {e}")
                                    raise Exception(f"响应格式错误: 无法解析内容 - {str(e)}")
                        except (KeyError, AttributeError, TypeError) as e:
                            logger.error(f"访问 choices 失败: {e}")
                            raise Exception(f"响应格式错误: 缺少 choices - {str(e)}")
                    else:
                        logger.error(f"响应格式错误: 缺少 output 属性")
                        raise Exception(f"响应格式错误: 缺少 output")
                except Exception as e:
                    # 如果已经是我们抛出的异常，直接抛出
                    if "响应格式错误" in str(e):
                        raise
                    # 其他异常也抛出
                    logger.error(f"处理响应时发生错误: {e}")
                    raise Exception(f"响应处理失败: {str(e)}")
            else:
                # API调用失败 - 构建错误信息
                error_msg = f"API调用失败"
                if status_code:
                    error_msg = f"API返回HTTP状态码: {status_code}"
                
                # 尝试获取错误消息（完全安全的方式）
                try:
                    if hasattr(response, 'message'):
                        try:
                            msg = response.message
                            if msg:
                                error_msg += f", 消息: {msg}"
                        except (KeyError, AttributeError, TypeError):
                            pass
                except Exception:
                    pass
                
                logger.error(error_msg)
                raise Exception(error_msg)
            
        except ImportError:
            logger.error("dashscope SDK未安装，请运行: pip install dashscope")
            return {
                "category": "other",
                "confidence": 0.5,
                "description": "dashscope SDK未安装",
                "background_color": None
            }
        except Exception as e:
            logger.error(f"阿里云API调用失败: {e}")
            raise
    
    async def _classify_with_openai(self, image_bytes: bytes) -> Dict:
        """使用OpenAI Vision API进行分类"""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            # Base64编码图片
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 构建prompt
            prompt = self._build_prompt()
            
            # 调用API
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=settings.LLM_MAX_TOKENS_CLASSIFICATION or 500,
                timeout=settings.LLM_TIMEOUT_CLASSIFICATION or 30
            )
            
            # 解析响应
            content = response.choices[0].message.content
            result = self._parse_response(content)
            
            logger.info(f"OpenAI分类完成: {result['category']}")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            # 返回默认结果
            return {
                "category": "other",
                "confidence": 0.5,
                "description": "分类失败，使用默认类别",
                "background_color": None
            }
    
    async def _classify_with_claude(self, image_bytes: bytes) -> Dict:
        """使用Claude Vision API进行分类"""
        try:
            from anthropic import AsyncAnthropic
            
            client = AsyncAnthropic(api_key=self.api_key)
            
            # Base64编码图片
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 构建prompt
            prompt = self._build_prompt()
            
            # 调用API
            message = await client.messages.create(
                model=self.model,
                max_tokens=settings.LLM_MAX_TOKENS_CLASSIFICATION or 500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
                timeout=settings.LLM_TIMEOUT_CLASSIFICATION or 30
            )
            
            # 解析响应
            content = message.content[0].text
            result = self._parse_response(content)
            
            logger.info(f"Claude分类完成: {result['category']}")
            return result
            
        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            # 返回默认结果
            return {
                "category": "other",
                "confidence": 0.5,
                "description": "分类失败，使用默认类别",
                "background_color": None
            }
    
    def _build_prompt(self) -> str:
        """构建分类提示词（从配置读取）"""
        return settings.CLASSIFICATION_PROMPT
    
    def _parse_response(self, content: str) -> Dict:
        """
        解析大模型响应
        
        Args:
            content: 响应内容
            
        Returns:
            解析后的结果字典
        """
        import json
        import re
        
        try:
            # 尝试直接解析JSON
            result = json.loads(content)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # 正则提取的JSON也无法解析，返回默认值
                    logger.warning(f"无法解析响应（正则提取后仍失败）: {content}")
                    return {
                        "category": "other",
                        "confidence": 0.5,
                        "description": "无法解析分类结果",
                        "background_color": None
                    }
            else:
                # 解析失败，返回默认值
                logger.warning(f"无法解析响应: {content}")
                return {
                    "category": "other",
                    "confidence": 0.5,
                    "description": "无法解析分类结果",
                    "background_color": None
                }
        
        # 验证category是否在预定义列表中
        category = result.get("category", "other")
        if category not in self.CATEGORIES:
            logger.warning(f"无效的类别: {category}，使用默认类别")
            category = "other"
        
        # 验证background_color是否在预定义列表中
        background_color = result.get("background_color")
        if background_color and background_color not in self.BACKGROUND_COLORS:
            logger.warning(f"无效的背景颜色: {background_color}，设为None")
            background_color = None
        
        return {
            "category": category,
            "confidence": float(result.get("confidence", 0.5)),
            "description": result.get("description", ""),
            "background_color": background_color
        }


# 全局模型客户端实例
model_client = ModelClient()

