"""
大模型提供商适配层
实现不同提供商的API调用逻辑
"""

import base64
import asyncio
from typing import Dict, Any, Optional
from abc import abstractmethod
from loguru import logger
from app.services.llm.base_service import BaseLLMService, LLMError, LLMErrorType
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
            status_code = getattr(response, 'status_code', None)
            if status_code == 200:
                if hasattr(response, 'output') and hasattr(response.output, 'choices'):
                    content = response.output.choices[0].message.content[0]['text']
                    return {
                        "success": True,
                        "content": content,
                        "raw_response": response
                    }
                else:
                    raise LLMError(
                        message="响应格式错误: 缺少 output 或 choices",
                        error_type=LLMErrorType.FORMAT_ERROR,
                        status_code=status_code
                    )
            else:
                error_msg = f"API返回状态码: {status_code or 'unknown'}"
                error_code = None
                if hasattr(response, 'message'):
                    error_msg += f", 消息: {response.message}"
                if hasattr(response, 'code'):
                    error_code = response.code
                
                # 根据状态码判断错误类型
                if status_code == 400:
                    error_type = LLMErrorType.INPUT_ERROR
                elif status_code in [401, 403]:
                    error_type = LLMErrorType.AUTH_ERROR
                elif status_code == 429:
                    error_type = LLMErrorType.RATE_LIMIT_ERROR
                elif status_code and status_code >= 500:
                    error_type = LLMErrorType.SERVER_ERROR
                else:
                    error_type = LLMErrorType.BUSINESS_ERROR
                
                raise LLMError(
                    message=error_msg,
                    error_type=error_type,
                    status_code=status_code,
                    error_code=error_code
                )
                
        except ImportError:
            raise LLMError(
                message="dashscope SDK未安装，请运行: pip install dashscope",
                error_type=LLMErrorType.BUSINESS_ERROR
            )
        except LLMError:
            raise  # 重新抛出LLMError
        except Exception as e:
            logger.error(f"阿里云分类API调用失败: {e}")
            # 转换为LLMError
            raise LLMError(
                message=str(e),
                error_type=LLMErrorType.NETWORK_ERROR
            ) from e
    
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
                        raise LLMError(
                            message=f"API返回格式错误: {result}",
                            error_type=LLMErrorType.FORMAT_ERROR,
                            status_code=200
                        )
                else:
                    error_info = response.json() if response.text else {"message": "未知错误"}
                    error_code = error_info.get('code') if isinstance(error_info, dict) else None
                    error_message = error_info.get('message', str(error_info)) if isinstance(error_info, dict) else str(error_info)
                    
                    # 根据状态码判断错误类型
                    if response.status_code == 400:
                        error_type = LLMErrorType.INPUT_ERROR
                    elif response.status_code in [401, 403]:
                        error_type = LLMErrorType.AUTH_ERROR
                    elif response.status_code == 429:
                        error_type = LLMErrorType.RATE_LIMIT_ERROR
                    elif response.status_code >= 500:
                        error_type = LLMErrorType.SERVER_ERROR
                    else:
                        error_type = LLMErrorType.BUSINESS_ERROR
                    
                    raise LLMError(
                        message=f"API调用失败: {error_message}",
                        error_type=error_type,
                        status_code=response.status_code,
                        error_code=error_code
                    )
                    
        except LLMError:
            raise  # 重新抛出LLMError
        except Exception as e:
            logger.error(f"阿里云图像编辑API调用失败: {e}")
            # 转换为LLMError
            raise LLMError(
                message=str(e),
                error_type=LLMErrorType.NETWORK_ERROR
            ) from e


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
            
        except ImportError:
            raise LLMError(
                message="openai SDK未安装，请运行: pip install openai",
                error_type=LLMErrorType.BUSINESS_ERROR
            )
        except LLMError:
            raise  # 重新抛出LLMError
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            # OpenAI SDK 会抛出特定异常，需要解析
            error_str = str(e).lower()
            status_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
            
            # 判断错误类型
            if status_code == 400 or 'invalid' in error_str or 'bad request' in error_str:
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code in [401, 403] or 'authentication' in error_str or 'unauthorized' in error_str:
                error_type = LLMErrorType.AUTH_ERROR
            elif status_code == 429 or 'rate limit' in error_str:
                error_type = LLMErrorType.RATE_LIMIT_ERROR
            elif status_code and status_code >= 500 or 'server' in error_str:
                error_type = LLMErrorType.SERVER_ERROR
            elif 'timeout' in error_str or 'connection' in error_str:
                error_type = LLMErrorType.NETWORK_ERROR
            else:
                error_type = LLMErrorType.NETWORK_ERROR
            
            raise LLMError(
                message=str(e),
                error_type=error_type,
                status_code=status_code
            ) from e
    
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
            
        except ImportError:
            raise LLMError(
                message="anthropic SDK未安装，请运行: pip install anthropic",
                error_type=LLMErrorType.BUSINESS_ERROR
            )
        except LLMError:
            raise  # 重新抛出LLMError
        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            # Claude SDK 会抛出特定异常，需要解析
            error_str = str(e).lower()
            status_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
            
            # 判断错误类型
            if status_code == 400 or 'invalid' in error_str or 'bad request' in error_str:
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code in [401, 403] or 'authentication' in error_str or 'unauthorized' in error_str:
                error_type = LLMErrorType.AUTH_ERROR
            elif status_code == 429 or 'rate limit' in error_str:
                error_type = LLMErrorType.RATE_LIMIT_ERROR
            elif status_code and status_code >= 500 or 'server' in error_str:
                error_type = LLMErrorType.SERVER_ERROR
            elif 'timeout' in error_str or 'connection' in error_str:
                error_type = LLMErrorType.NETWORK_ERROR
            else:
                error_type = LLMErrorType.NETWORK_ERROR
            
            raise LLMError(
                message=str(e),
                error_type=error_type,
                status_code=status_code
            ) from e
    
    async def _call_image_edit(
        self,
        image_bytes: bytes,
        prompt: str,
        edit_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Claude暂不支持图像编辑"""
        raise NotImplementedError("Claude暂不支持图像编辑功能")

