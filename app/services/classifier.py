"""
分类服务
整合缓存查询、大模型调用、本地推理和日志记录
支持：优先本地推理、大模型失败时降级到本地推理
"""

import time
import io
from typing import Optional, Tuple, List
from app.utils.hash_utils import HashUtils
from app.utils.id_generator import IDGenerator
from app.services.cache_service import cache_service
from app.services.model_client import model_client
from app.services.stats_service import stats_service
from app.config import settings
from loguru import logger

# 二维码检测相关导入
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    from PIL import Image
    QRCODE_DETECTION_AVAILABLE = True
except ImportError:
    QRCODE_DETECTION_AVAILABLE = False
    logger.warning("pyzbar 或 PIL 未安装，二维码检测功能不可用")

# 延迟导入本地推理服务（避免循环依赖）
_local_inference = None

def get_local_inference():
    """获取本地推理服务实例"""
    global _local_inference
    if _local_inference is None:
        from app.services.local_model_inference import local_model_inference
        _local_inference = local_model_inference
    return _local_inference


class ClassifierService:
    """分类服务类"""
    
    def _is_valid_classification(self, result: dict) -> bool:
        """
        判断分类结果是否有效（用于决定是否缓存）
        
        Args:
            result: 分类结果
            
        Returns:
            是否为有效的分类结果
        """
        # 检查description中是否包含"失败"字样
        description = result.get('description', '')
        if description and '失败' in description:
            return False
        
        # 检查是否是默认错误值（category=other, confidence=0.5）
        if result.get('category') == 'other' and result.get('confidence') == 0.5:
            return False
        
        # 检查置信度是否过低（小于0.3认为不可靠）
        if result.get('confidence', 0) < 0.3:
            return False
        
        return True
    
    def _detect_qrcode(self, image_bytes: bytes) -> bool:
        """
        检测图片是否包含二维码（快速检测，失败则交给大模型）
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            是否包含二维码
        """
        if not QRCODE_DETECTION_AVAILABLE:
            return False
            
        try:
            # 使用PIL加载图片
            img = Image.open(io.BytesIO(image_bytes))
            
            # 转换为RGB模式（pyzbar需要）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 直接检测
            decoded_objects = pyzbar_decode(img)
            if len(decoded_objects) > 0:
                logger.info(f"✅ 检测到二维码: {len(decoded_objects)} 个")
                return True
            
            # 检测失败，返回False（交给大模型处理）
            return False
            
        except Exception as e:
            # 检测异常，返回False（不阻塞流程，交给大模型处理）
            logger.debug(f"二维码检测异常: {e}")
            return False
    
    async def classify_by_hash(
        self,
        image_hash: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[dict], bool, str]:
        """
        根据哈希查询分类（仅查询缓存）
        
        Args:
            image_hash: 图片哈希
            user_id: 用户ID
            ip_address: IP地址
            
        Returns:
            (分类结果, 是否来自缓存, 请求ID)
        """
        request_id = IDGenerator.generate_request_id()
        start_time = time.time()
        
        # 查询缓存
        cached_result = await cache_service.get_cached_result(image_hash)
        
        if cached_result:
            # 缓存命中
            await cache_service.increment_hit_count(image_hash)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # 记录日志
            await stats_service.log_request(
                request_id=request_id,
                user_id=user_id,
                ip_address=ip_address,
                image_hash=image_hash,
                image_size=0,  # 只查哈希，不知道图片大小
                category=cached_result['category'],
                confidence=float(cached_result['confidence']),
                from_cache=True,
                processing_time_ms=processing_time,
                inference_method="cache"
            )
            
            result = {
                "category": cached_result['category'],
                "confidence": float(cached_result['confidence']),
                "description": cached_result.get('description'),
                "background_color": cached_result.get('background_color')
            }
            
            return result, True, request_id
        
        # 缓存未命中
        return None, False, request_id
    
    async def batch_check_cache(
        self,
        image_hashes: List[str],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[List[dict], str]:
        """
        批量查询缓存
        
        Args:
            image_hashes: 图片哈希列表
            user_id: 用户ID
            ip_address: IP地址
            
        Returns:
            (缓存项列表, 请求ID)
        """
        request_id = IDGenerator.generate_request_id()
        results = []
        
        # 并发查询所有哈希的缓存
        for i, image_hash in enumerate(image_hashes):
            # 正常的缓存查询逻辑
            cached_result = await cache_service.get_cached_result(image_hash)
            
            if cached_result:
                # 缓存命中
                await cache_service.increment_hit_count(image_hash)
                
                results.append({
                    "image_hash": image_hash,
                    "cached": True,
                    "data": {
                        "category": cached_result['category'],
                        "confidence": float(cached_result['confidence']),
                        "description": cached_result.get('description'),
                        "background_color": cached_result.get('background_color'),
                        "local_inference_result": cached_result.get('local_inference_result')
                    }
                })
            else:
                # 缓存未命中
                results.append({
                    "image_hash": image_hash,
                    "cached": False,
                    "data": None
                })
        
        return results, request_id
    
    async def classify_image(
        self,
        image_bytes: bytes,
        image_hash: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[dict, bool, str, int, str]:
        """
        完整的图片分类流程
        
        Args:
            image_bytes: 图片二进制数据
            image_hash: 可选的预计算哈希
            user_id: 用户ID
            ip_address: IP地址
            
        Returns:
            (分类结果, 是否来自缓存, 请求ID, 处理耗时, 推理方式)
        """
        request_id = IDGenerator.generate_request_id()
        start_time = time.time()
        
        # 计算哈希（如果未提供）
        if not image_hash:
            image_hash = HashUtils.calculate_sha256(image_bytes)
            logger.debug(f"计算图片哈希: {image_hash[:16]}...")
        
        image_size = len(image_bytes)
        
        # 查询缓存
        cached_result = await cache_service.get_cached_result(image_hash)
        
        if cached_result:
            # 缓存命中
            await cache_service.increment_hit_count(image_hash)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # 记录日志
            await stats_service.log_request(
                request_id=request_id,
                user_id=user_id,
                ip_address=ip_address,
                image_hash=image_hash,
                image_size=image_size,
                category=cached_result['category'],
                confidence=float(cached_result['confidence']),
                from_cache=True,
                processing_time_ms=processing_time,
                inference_method="cache"
            )
            
            result = {
                "category": cached_result['category'],
                "confidence": float(cached_result['confidence']),
                "description": cached_result.get('description'),
                "background_color": cached_result.get('background_color')
            }
            
            logger.info(f"缓存命中 [{request_id}]: {result['category']} ({processing_time}ms)")
            return result, True, request_id, processing_time, "cache"
        
        # 🆕 缓存未命中，先检测二维码
        logger.info(f"🔍 开始二维码检测 [{request_id}], 图片大小: {image_size} 字节, QRCODE_DETECTION_AVAILABLE={QRCODE_DETECTION_AVAILABLE}")
        has_qrcode = self._detect_qrcode(image_bytes)
        logger.info(f"🔍 二维码检测结果 [{request_id}]: {has_qrcode}")
        if has_qrcode:
            logger.info(f"检测到二维码 [{request_id}]，跳过推理，直接返回qrcode分类")
            
            # 构造二维码分类结果（和本地推理不同，二维码可以直接返回category）
            qrcode_result = {
                "category": "qrcode",
                "confidence": 1.0,
                "description": "检测到二维码",
                "background_color": None
            }
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # 记录日志（inference_method 使用 qrcode_detection，统计时算作 local_count）
            await stats_service.log_request(
                request_id=request_id,
                user_id=user_id,
                ip_address=ip_address,
                image_hash=image_hash,
                image_size=image_size,
                category=qrcode_result['category'],
                confidence=qrcode_result['confidence'],
                from_cache=False,
                processing_time_ms=processing_time,
                inference_method="qrcode_detection"
            )
            
            logger.info(f"二维码检测完成 [{request_id}]: qrcode ({processing_time}ms)")
            # 🆕 注意：不缓存，和本地推理保持一致
            return qrcode_result, False, request_id, processing_time, "qrcode_detection"
        
        # 缓存未命中且未检测到二维码，根据配置选择推理方式
        model_result = None
        inference_method = "unknown"
        
        # 策略1：如果开启本地推理开关，直接使用本地推理
        if settings.USE_LOCAL_INFERENCE:
            logger.info(f"缓存未命中，使用本地推理 [{request_id}]（配置开关已开启）")
            try:
                local_inference = get_local_inference()
                if not local_inference.is_initialized:
                    await local_inference.initialize()
                
                local_result = await local_inference.classify_image(image_bytes)
                if local_result['success']:
                    # 本地推理需要客户端做分类映射，category留空作为标识
                    model_result = {
                        "category": "",  # 留空，客户端根据此判断需要使用本地映射
                        "confidence": 0.8,
                        "description": "本地推理完成（需客户端映射分类）",
                        "local_inference_result": local_result  # 附带原始检测结果
                    }
                    inference_method = "local"
                    logger.info(f"本地推理成功 [{request_id}]")
                else:
                    raise Exception("本地推理失败")
            except Exception as e:
                logger.error(f"本地推理失败: {e}")
                # 本地推理失败时，直接抛出异常，不降级到大模型
                # 避免循环降级：本地推理失败 -> 大模型 -> 大模型失败 -> 本地推理 -> 循环
                raise Exception(f"本地推理失败: {str(e)}")
        
        # 策略2：优先大模型，失败时降级到本地推理
        else:
            logger.info(f"缓存未命中，调用大模型 [{request_id}]")
            try:
                model_result = await model_client.classify_image(image_bytes)
                inference_method = "llm"
            except Exception as e:
                logger.error(f"大模型调用失败: {e}")
                
                # 如果开启降级策略，使用本地推理
                if settings.LOCAL_INFERENCE_FALLBACK:
                    logger.warning(f"大模型失败，降级到本地推理 [{request_id}]")
                    try:
                        local_inference = get_local_inference()
                        if not local_inference.is_initialized:
                            await local_inference.initialize()
                        
                        local_result = await local_inference.classify_image(image_bytes)
                        if local_result['success']:
                            model_result = {
                                "category": "",  # 留空，客户端根据此判断需要使用本地映射
                                "confidence": 0.8,
                                "description": "本地推理完成（大模型失败降级）",
                                "local_inference_result": local_result
                            }
                            inference_method = "local_fallback"
                            logger.info(f"本地推理降级成功 [{request_id}]")
                        else:
                            raise Exception("本地推理也失败")
                    except Exception as local_error:
                        logger.error(f"本地推理降级也失败: {local_error}")
                        raise Exception(f"大模型和本地推理都失败: LLM={str(e)}, Local={str(local_error)}")
                else:
                    raise
        
        # 判断是否成功分类（只有成功的结果才缓存）
        is_success = self._is_valid_classification(model_result)
        
        # 注意：本地推理结果不缓存（因为需要客户端映射）
        if is_success and inference_method in ["llm", "llm_fallback"]:
            # 保存到缓存（仅大模型成功的分类结果）
            await cache_service.save_result(
                image_hash=image_hash,
                category=model_result['category'],
                confidence=model_result['confidence'],
                description=model_result.get('description'),
                background_color=model_result.get('background_color'),
                model_used=f"{model_client.model}_{inference_method}"
            )
            logger.info(f"分类结果已缓存: {model_result['category']}")
        elif inference_method in ["local", "local_fallback", "qrcode_detection"]:
            logger.info(f"本地推理/二维码检测结果不缓存")
        else:
            logger.warning(f"分类失败，不缓存此结果: {model_result.get('description')}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # 记录日志（category为空时用特殊标记）
        await stats_service.log_request(
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            image_hash=image_hash,
            image_size=image_size,
            category=model_result['category'] or "local_pending",  # category为空时用特殊标记
            confidence=model_result['confidence'],
            from_cache=False,
            processing_time_ms=processing_time,
            inference_method=inference_method
        )
        
        logger.info(f"分类完成 [{request_id}]: {model_result['category']} ({processing_time}ms) [方式: {inference_method}]")
        return model_result, False, request_id, processing_time, inference_method


# 全局分类服务实例
classifier = ClassifierService()

