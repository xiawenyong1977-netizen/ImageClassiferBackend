"""
分类服务
整合缓存查询、大模型调用和日志记录
"""

import time
from typing import Optional, Tuple
from app.utils.hash_utils import HashUtils
from app.utils.id_generator import IDGenerator
from app.services.cache_service import cache_service
from app.services.model_client import model_client
from app.services.stats_service import stats_service
from app.config import settings
from loguru import logger


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
                processing_time_ms=processing_time
            )
            
            result = {
                "category": cached_result['category'],
                "confidence": float(cached_result['confidence']),
                "description": cached_result.get('description')
            }
            
            return result, True, request_id
        
        # 缓存未命中
        return None, False, request_id
    
    async def classify_image(
        self,
        image_bytes: bytes,
        image_hash: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[dict, bool, str, int]:
        """
        完整的图片分类流程
        
        Args:
            image_bytes: 图片二进制数据
            image_hash: 可选的预计算哈希
            user_id: 用户ID
            ip_address: IP地址
            
        Returns:
            (分类结果, 是否来自缓存, 请求ID, 处理耗时)
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
                processing_time_ms=processing_time
            )
            
            result = {
                "category": cached_result['category'],
                "confidence": float(cached_result['confidence']),
                "description": cached_result.get('description')
            }
            
            logger.info(f"缓存命中 [{request_id}]: {result['category']} ({processing_time}ms)")
            return result, True, request_id, processing_time
        
        # 缓存未命中，调用大模型
        logger.info(f"缓存未命中，调用大模型 [{request_id}]")
        model_result = await model_client.classify_image(image_bytes)
        
        # 判断是否成功分类（只有成功的结果才缓存）
        is_success = self._is_valid_classification(model_result)
        
        if is_success:
            # 保存到缓存（仅成功的分类结果）
            await cache_service.save_result(
                image_hash=image_hash,
                category=model_result['category'],
                confidence=model_result['confidence'],
                description=model_result.get('description'),
                model_used=settings.LLM_MODEL
            )
            logger.info(f"分类结果已缓存: {model_result['category']}")
        else:
            logger.warning(f"分类失败，不缓存此结果: {model_result.get('description')}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # 记录日志
        await stats_service.log_request(
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            image_hash=image_hash,
            image_size=image_size,
            category=model_result['category'],
            confidence=model_result['confidence'],
            from_cache=False,
            processing_time_ms=processing_time
        )
        
        logger.info(f"分类完成 [{request_id}]: {model_result['category']} ({processing_time}ms)")
        return model_result, False, request_id, processing_time


# 全局分类服务实例
classifier = ClassifierService()

