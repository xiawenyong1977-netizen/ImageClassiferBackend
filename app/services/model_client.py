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
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
    
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
            
            # 解析响应
            # 🆕 先检查响应体中的错误信息（即使HTTP状态码是200，响应体也可能包含错误）
            # 调试：打印 response 对象的所有属性
            logger.debug(f"Response对象属性: {dir(response)}")
            logger.debug(f"Response.status_code: {response.status_code}")
            
            # 检查 response.code 是否存在且表示错误（可能是字符串如 "DataInspectionFailed" 或数字如 400）
            if hasattr(response, 'code'):
                response_code = response.code
                response_message = getattr(response, 'message', '')
                logger.debug(f"检测到 response.code: {response_code} (类型: {type(response_code)}), message: {response_message}")
                
                # 如果是字符串类型的错误码（如 "DataInspectionFailed"），或者数字类型但不是200
                if (isinstance(response_code, str) and response_code != "200" and response_code.strip() != "") or \
                   (isinstance(response_code, int) and response_code != 200):
                    error_msg = f"API返回错误码: {response_code}, 消息: {response_message if response_message else '未知错误'}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                # 如果 code 是空字符串，可能是其他类型的错误
                elif isinstance(response_code, str) and response_code.strip() == "":
                    # 检查是否有其他错误信息
                    if hasattr(response, 'request_id'):
                        logger.warning(f"response.code 为空字符串，但存在 request_id: {response.request_id}")
                    # 检查响应体是否有错误信息
                    if hasattr(response, 'body') or hasattr(response, 'text'):
                        response_body = getattr(response, 'body', getattr(response, 'text', ''))
                        logger.warning(f"response.code 为空，响应体: {str(response_body)[:200]}")
            
            # 检查HTTP状态码
            if response.status_code == 200:
                # 成功响应
                if hasattr(response, 'output') and hasattr(response.output, 'choices'):
                    content = response.output.choices[0].message.content[0]['text']
                    result = self._parse_response(content)
                    logger.info(f"阿里云通义千问分类完成: {result['category']}")
                    return result
                else:
                    # 响应格式错误，记录更多信息
                    logger.error(f"响应格式错误: status_code={response.status_code}, has_output={hasattr(response, 'output')}")
                    if hasattr(response, 'output'):
                        logger.error(f"response.output 类型: {type(response.output)}, 属性: {dir(response.output)}")
                    # 尝试获取更多信息
                    response_attrs = {attr: getattr(response, attr, None) for attr in ['code', 'message', 'request_id', 'body', 'text'] if hasattr(response, attr)}
                    logger.error(f"response 其他属性: {response_attrs}")
                    raise Exception(f"响应格式错误: 缺少 output.choices")
            else:
                # API调用失败（HTTP状态码不是200）
                response_code = getattr(response, 'code', 'N/A')
                response_message = getattr(response, 'message', '未知错误')
                # 尝试获取更多错误信息
                error_details = f"HTTP状态码: {response.status_code}"
                if hasattr(response, 'text'):
                    error_details += f", 响应文本: {str(response.text)[:200]}"
                if hasattr(response, 'body'):
                    error_details += f", 响应体: {str(response.body)[:200]}"
                
                error_msg = f"API返回HTTP状态码: {response.status_code}, 错误码: {response_code}, 消息: {response_message}, 详情: {error_details}"
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
            # 🆕 抛出异常，让调用方可以触发降级逻辑（本地推理）
            raise Exception(f"分类失败: {str(e)}")
    
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
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=settings.LLM_TIMEOUT
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
                max_tokens=settings.LLM_MAX_TOKENS,
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
                timeout=settings.LLM_TIMEOUT
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

