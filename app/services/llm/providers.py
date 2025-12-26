"""
大模型提供商适配层
实现不同提供商的API调用逻辑
"""

import base64
import asyncio
from typing import Dict, Any, Optional
from abc import abstractmethod
from loguru import logger
from app.services.llm.base_service import BaseLLMService
from app.config import settings


class LLMProvider(BaseLLMService):
    """LLM提供商基类"""
    
    async def _call_api(
        self,
        task_type: str,
        image_bytes: bytes,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        根据任务类型分发到具体的实现方法
        """
        if task_type == "classification":
            return await self._call_classification(image_bytes, prompt)
        elif task_type == "image_edit":
            return await self._call_image_edit(image_bytes, prompt, **kwargs)
        else:
            raise ValueError(f"不支持的任务类型: {task_type}")
    
    @abstractmethod
    async def _call_classification(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """分类任务实现"""
        pass
    
    @abstractmethod
    async def _call_image_edit(
        self,
        image_bytes: bytes,
        prompt: str,
        edit_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """图像编辑任务实现"""
        pass


class AliyunProvider(LLMProvider):
    """阿里云通义千问提供商适配器"""
    
    async def _call_classification(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """使用阿里云通义千问VL进行分类"""
        try:
            import dashscope
            from dashscope import MultiModalConversation
            
            dashscope.api_key = self.api_key
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
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
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: MultiModalConversation.call(
                    model=self.model,
                    messages=messages
                )
            )
            
            # 解析响应
            if hasattr(response, 'status_code') and response.status_code == 200:
                if hasattr(response, 'output') and hasattr(response.output, 'choices'):
                    content = response.output.choices[0].message.content[0]['text']
                    return {
                        "success": True,
                        "content": content,
                        "raw_response": response
                    }
                else:
                    raise Exception("响应格式错误: 缺少 output 或 choices")
            else:
                error_msg = f"API返回状态码: {getattr(response, 'status_code', 'unknown')}"
                if hasattr(response, 'message'):
                    error_msg += f", 消息: {response.message}"
                raise Exception(error_msg)
                
        except ImportError:
            raise Exception("dashscope SDK未安装，请运行: pip install dashscope")
        except Exception as e:
            logger.error(f"阿里云分类API调用失败: {e}")
            raise
    
    async def _call_image_edit(
        self,
        image_bytes: bytes,
        prompt: str,
        edit_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """使用阿里云图像编辑API"""
        try:
            import httpx
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 构建请求payload
            payload = {
                "model": self.model if self.model else "qwen-image-edit",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": f"data:image/jpeg;base64,{image_base64}"},
                                {"text": prompt}
                            ]
                        }
                    ]
                },
                "parameters": {
                    "negative_prompt": kwargs.get("negative_prompt", ""),
                    "watermark": kwargs.get("watermark", False)
                }
            }
            
            # 调用HTTP API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'output' in result and 'choices' in result['output']:
                        result_url = result['output']['choices'][0]['message']['content'][0]['image']
                        return {
                            "success": True,
                            "result_url": result_url,
                            "raw_response": result
                        }
                    else:
                        raise Exception(f"API返回格式错误: {result}")
                else:
                    error_info = response.json() if response.text else "未知错误"
                    raise Exception(f"API调用失败: {error_info}")
                    
        except Exception as e:
            logger.error(f"阿里云图像编辑API调用失败: {e}")
            raise


class OpenAIProvider(LLMProvider):
    """OpenAI提供商适配器"""
    
    async def _call_classification(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """使用OpenAI Vision API进行分类"""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
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
                timeout=self.timeout
            )
            
            content = response.choices[0].message.content
            return {
                "success": True,
                "content": content,
                "raw_response": response
            }
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise
    
    async def _call_image_edit(
        self,
        image_bytes: bytes,
        prompt: str,
        edit_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """OpenAI暂不支持图像编辑"""
        raise NotImplementedError("OpenAI暂不支持图像编辑功能")


class ClaudeProvider(LLMProvider):
    """Claude提供商适配器"""
    
    async def _call_classification(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """使用Claude Vision API进行分类"""
        try:
            from anthropic import AsyncAnthropic
            
            client = AsyncAnthropic(api_key=self.api_key)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
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
                timeout=self.timeout
            )
            
            content = message.content[0].text
            return {
                "success": True,
                "content": content,
                "raw_response": message
            }
            
        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            raise
    
    async def _call_image_edit(
        self,
        image_bytes: bytes,
        prompt: str,
        edit_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Claude暂不支持图像编辑"""
        raise NotImplementedError("Claude暂不支持图像编辑功能")

