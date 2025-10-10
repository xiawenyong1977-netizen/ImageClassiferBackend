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
        "other"               # 其它
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
                "description": str
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
            if response.status_code == 200:
                # 成功响应
                if hasattr(response, 'output') and hasattr(response.output, 'choices'):
                    content = response.output.choices[0].message.content[0]['text']
                    result = self._parse_response(content)
                    logger.info(f"阿里云通义千问分类完成: {result['category']}")
                    return result
                else:
                    raise Exception(f"响应格式错误: {response}")
            else:
                # API调用失败
                error_msg = f"API返回错误码: {response.code}, 消息: {response.message}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
        except ImportError:
            logger.error("dashscope SDK未安装，请运行: pip install dashscope")
            return {
                "category": "other",
                "confidence": 0.5,
                "description": "dashscope SDK未安装"
            }
        except Exception as e:
            logger.error(f"阿里云API调用失败: {e}")
            # 返回默认结果
            return {
                "category": "other",
                "confidence": 0.5,
                "description": f"分类失败: {str(e)}"
            }
    
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
                "description": "分类失败，使用默认类别"
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
                "description": "分类失败，使用默认类别"
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
                result = json.loads(json_match.group())
            else:
                # 解析失败，返回默认值
                logger.warning(f"无法解析响应: {content}")
                return {
                    "category": "other",
                    "confidence": 0.5,
                    "description": "无法解析分类结果"
                }
        
        # 验证category是否在预定义列表中
        category = result.get("category", "other")
        if category not in self.CATEGORIES:
            logger.warning(f"无效的类别: {category}，使用默认类别")
            category = "other"
        
        return {
            "category": category,
            "confidence": float(result.get("confidence", 0.5)),
            "description": result.get("description", "")
        }


# 全局模型客户端实例
model_client = ModelClient()

