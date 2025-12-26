"""
大模型提供商适配层
实现不同提供商的API调用逻辑

错误处理说明：
- 每个provider都有自己的错误码定义和错误消息格式
- 阿里云(Aliyun): 使用DashScope API，有详细的错误码（400, 401, 402, 403, 404, 409, 422, 429, 500, 503等）
- OpenAI: 使用OpenAI SDK，错误通过异常对象传递，主要基于HTTP状态码
- Claude: 使用Anthropic SDK，错误处理与OpenAI类似
- Deepseek: 兼容OpenAI API格式，错误处理与OpenAI类似

所有provider的错误最终都会转换为统一的LLMError类型，详见ERROR_CODES.md文档
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
    """
    阿里云提供商适配器
    
    错误处理：
    - 使用DashScope API，有详细的错误码定义
    - 支持400, 401, 402, 403, 404, 409, 422, 429, 500, 503等状态码
    - 400错误包含大量子类型（InvalidParameter, url error, InvalidFile.*等）
    - 详见ERROR_CODES.md文档
    """
    
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
                        "content": content
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
                
                # 根据状态码判断错误类型（根据阿里云DashScope API文档）
                # 400 - InvalidParameter：所有400错误都是参数/输入错误，不应重试
                if status_code == 400:
                    error_type = LLMErrorType.INPUT_ERROR
                elif status_code == 401:
                    # 401 - 认证失败：API key 错误
                    error_type = LLMErrorType.AUTH_ERROR
                elif status_code == 402:
                    # 402 - 余额不足：账号余额不足（Arrearage）
                    error_type = LLMErrorType.BUSINESS_ERROR
                elif status_code == 403:
                    # 403 - 访问被拒绝：无权限访问资源
                    error_type = LLMErrorType.AUTH_ERROR
                elif status_code == 404:
                    # 404 - 资源不存在：模型不存在、工作空间不存在等
                    error_type = LLMErrorType.BUSINESS_ERROR
                elif status_code == 409:
                    # 409 - 冲突：资源已存在等
                    error_type = LLMErrorType.BUSINESS_ERROR
                elif status_code == 422:
                    # 422 - 参数错误
                    error_type = LLMErrorType.INPUT_ERROR
                elif status_code == 429:
                    # 429 - 请求速率达到上限：TPM 或 RPM 达到上限
                    error_type = LLMErrorType.RATE_LIMIT_ERROR
                elif status_code == 500:
                    # 500 - 服务器内部错误
                    error_type = LLMErrorType.SERVER_ERROR
                elif status_code == 503:
                    # 503 - 服务不可用：服务器繁忙、模型不可用等
                    error_type = LLMErrorType.SERVER_ERROR
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
                            "result_url": result_url
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
                    
                    # 根据状态码判断错误类型（根据阿里云DashScope API文档）
                    # 400 - InvalidParameter：所有400错误都是参数/输入错误，不应重试
                    if response.status_code == 400:
                        error_type = LLMErrorType.INPUT_ERROR
                    elif response.status_code == 401:
                        # 401 - 认证失败：API key 错误
                        error_type = LLMErrorType.AUTH_ERROR
                    elif response.status_code == 402:
                        # 402 - 余额不足：账号余额不足（Arrearage）
                        error_type = LLMErrorType.BUSINESS_ERROR
                    elif response.status_code == 403:
                        # 403 - 访问被拒绝：无权限访问资源
                        error_type = LLMErrorType.AUTH_ERROR
                    elif response.status_code == 404:
                        # 404 - 资源不存在：模型不存在、工作空间不存在等
                        error_type = LLMErrorType.BUSINESS_ERROR
                    elif response.status_code == 409:
                        # 409 - 冲突：资源已存在等
                        error_type = LLMErrorType.BUSINESS_ERROR
                    elif response.status_code == 422:
                        # 422 - 参数错误
                        error_type = LLMErrorType.INPUT_ERROR
                    elif response.status_code == 429:
                        # 429 - 请求速率达到上限：TPM 或 RPM 达到上限
                        error_type = LLMErrorType.RATE_LIMIT_ERROR
                    elif response.status_code == 500:
                        # 500 - 服务器内部错误
                        error_type = LLMErrorType.SERVER_ERROR
                    elif response.status_code == 503:
                        # 503 - 服务不可用：服务器繁忙、模型不可用等
                        error_type = LLMErrorType.SERVER_ERROR
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
    """
    OpenAI提供商适配器
    
    错误处理：
    - 使用OpenAI SDK，错误通过异常对象传递
    - 主要基于HTTP状态码（400, 401, 402, 422, 429, 500, 503）
    - 通过错误消息关键词识别错误类型
    - 详见ERROR_CODES.md文档
    """
    
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
                "content": content
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
            
            # 判断错误类型（根据OpenAI API错误码规范，Deepseek兼容OpenAI格式）
            if status_code == 400 or 'invalid' in error_str or 'bad request' in error_str:
                # 400 - 格式错误：请求体格式错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code in [401, 403] or 'authentication' in error_str or 'unauthorized' in error_str:
                # 401 - 认证失败：API key 错误
                error_type = LLMErrorType.AUTH_ERROR
            elif status_code == 402 or 'insufficient' in error_str or 'balance' in error_str:
                # 402 - 余额不足：账号余额不足
                error_type = LLMErrorType.BUSINESS_ERROR
            elif status_code == 422 or 'unprocessable' in error_str:
                # 422 - 参数错误：请求体参数错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code == 429 or 'rate limit' in error_str:
                # 429 - 请求速率达到上限：TPM 或 RPM 达到上限
                error_type = LLMErrorType.RATE_LIMIT_ERROR
            elif status_code == 503 or 'service unavailable' in error_str or 'busy' in error_str:
                # 503 - 服务器繁忙：服务器负载过高
                error_type = LLMErrorType.SERVER_ERROR
            elif status_code and status_code >= 500 or 'server' in error_str:
                # 500 - 服务器故障：服务器内部故障
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
    """
    Claude提供商适配器
    
    错误处理：
    - 使用Anthropic SDK，错误通过异常对象传递
    - 错误处理逻辑与OpenAI类似
    - 主要基于HTTP状态码和错误消息关键词
    - 详见ERROR_CODES.md文档
    """
    
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
                "content": content
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
            
            # 判断错误类型（根据OpenAI API错误码规范，Deepseek兼容OpenAI格式）
            if status_code == 400 or 'invalid' in error_str or 'bad request' in error_str:
                # 400 - 格式错误：请求体格式错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code in [401, 403] or 'authentication' in error_str or 'unauthorized' in error_str:
                # 401 - 认证失败：API key 错误
                error_type = LLMErrorType.AUTH_ERROR
            elif status_code == 402 or 'insufficient' in error_str or 'balance' in error_str:
                # 402 - 余额不足：账号余额不足
                error_type = LLMErrorType.BUSINESS_ERROR
            elif status_code == 422 or 'unprocessable' in error_str:
                # 422 - 参数错误：请求体参数错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code == 429 or 'rate limit' in error_str:
                # 429 - 请求速率达到上限：TPM 或 RPM 达到上限
                error_type = LLMErrorType.RATE_LIMIT_ERROR
            elif status_code == 503 or 'service unavailable' in error_str or 'busy' in error_str:
                # 503 - 服务器繁忙：服务器负载过高
                error_type = LLMErrorType.SERVER_ERROR
            elif status_code and status_code >= 500 or 'server' in error_str:
                # 500 - 服务器故障：服务器内部故障
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


class DeepseekProvider(LLMProvider):
    """
    Deepseek提供商适配器（兼容OpenAI API格式）
    
    错误处理：
    - 使用OpenAI兼容的API格式，API基础URL: https://api.deepseek.com
    - 错误处理逻辑与OpenAI类似
    - 支持400, 401, 402, 422, 429, 500, 503等状态码
    - 详见ERROR_CODES.md文档
    """
    
    async def _call_classification(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """使用Deepseek Vision API进行分类"""
        try:
            from openai import AsyncOpenAI
            
            # Deepseek使用OpenAI兼容的API格式
            # API基础URL为 https://api.deepseek.com
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
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
                "content": content
            }
            
        except ImportError:
            raise LLMError(
                message="openai SDK未安装，请运行: pip install openai",
                error_type=LLMErrorType.BUSINESS_ERROR
            )
        except LLMError:
            raise  # 重新抛出LLMError
        except Exception as e:
            logger.error(f"Deepseek API调用失败: {e}")
            # OpenAI SDK 会抛出特定异常，需要解析
            error_str = str(e).lower()
            status_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
            
            # 判断错误类型（根据OpenAI API错误码规范，Deepseek兼容OpenAI格式）
            if status_code == 400 or 'invalid' in error_str or 'bad request' in error_str:
                # 400 - 格式错误：请求体格式错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code in [401, 403] or 'authentication' in error_str or 'unauthorized' in error_str:
                # 401 - 认证失败：API key 错误
                error_type = LLMErrorType.AUTH_ERROR
            elif status_code == 402 or 'insufficient' in error_str or 'balance' in error_str:
                # 402 - 余额不足：账号余额不足
                error_type = LLMErrorType.BUSINESS_ERROR
            elif status_code == 422 or 'unprocessable' in error_str:
                # 422 - 参数错误：请求体参数错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code == 429 or 'rate limit' in error_str:
                # 429 - 请求速率达到上限：TPM 或 RPM 达到上限
                error_type = LLMErrorType.RATE_LIMIT_ERROR
            elif status_code == 503 or 'service unavailable' in error_str or 'busy' in error_str:
                # 503 - 服务器繁忙：服务器负载过高
                error_type = LLMErrorType.SERVER_ERROR
            elif status_code and status_code >= 500 or 'server' in error_str:
                # 500 - 服务器故障：服务器内部故障
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
        """Deepseek暂不支持图像编辑"""
        raise NotImplementedError("Deepseek暂不支持图像编辑功能")
    
    async def _call_text_generation(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """使用Deepseek API进行文本生成"""
        try:
            from openai import AsyncOpenAI
            
            # Deepseek使用OpenAI兼容的API格式
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            
            # 支持自定义参数
            max_tokens = kwargs.get('max_tokens', settings.LLM_MAX_TOKENS)
            temperature = kwargs.get('temperature', 0.7)
            system_prompt = kwargs.get('system_prompt', None)
            
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout
            )
            
            content = response.choices[0].message.content
            return {
                "success": True,
                "content": content
            }
            
        except ImportError:
            raise LLMError(
                message="openai SDK未安装，请运行: pip install openai",
                error_type=LLMErrorType.BUSINESS_ERROR
            )
        except LLMError:
            raise  # 重新抛出LLMError
        except Exception as e:
            logger.error(f"Deepseek文本生成API调用失败: {e}")
            # OpenAI SDK 会抛出特定异常，需要解析
            error_str = str(e).lower()
            status_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
            
            # 判断错误类型（根据OpenAI API错误码规范，Deepseek兼容OpenAI格式）
            if status_code == 400 or 'invalid' in error_str or 'bad request' in error_str:
                # 400 - 格式错误：请求体格式错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code in [401, 403] or 'authentication' in error_str or 'unauthorized' in error_str:
                # 401 - 认证失败：API key 错误
                error_type = LLMErrorType.AUTH_ERROR
            elif status_code == 402 or 'insufficient' in error_str or 'balance' in error_str:
                # 402 - 余额不足：账号余额不足
                error_type = LLMErrorType.BUSINESS_ERROR
            elif status_code == 422 or 'unprocessable' in error_str:
                # 422 - 参数错误：请求体参数错误
                error_type = LLMErrorType.INPUT_ERROR
            elif status_code == 429 or 'rate limit' in error_str:
                # 429 - 请求速率达到上限：TPM 或 RPM 达到上限
                error_type = LLMErrorType.RATE_LIMIT_ERROR
            elif status_code == 503 or 'service unavailable' in error_str or 'busy' in error_str:
                # 503 - 服务器繁忙：服务器负载过高
                error_type = LLMErrorType.SERVER_ERROR
            elif status_code and status_code >= 500 or 'server' in error_str:
                # 500 - 服务器故障：服务器内部故障
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
