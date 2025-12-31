"""
七牛云存储服务
用于上传图片到七牛云CDN
"""

import httpx
from typing import Optional
from loguru import logger
from qiniu import Auth, put_data, BucketManager
from app.config import settings


class QiniuService:
    """七牛云存储服务"""
    
    def __init__(self):
        """初始化七牛云服务"""
        self.access_key = getattr(settings, 'QINIU_ACCESS_KEY', '')
        self.secret_key = getattr(settings, 'QINIU_SECRET_KEY', '')
        self.bucket_name = getattr(settings, 'QINIU_BUCKET_NAME', '')
        self.domain = getattr(settings, 'QINIU_DOMAIN', '')
        
        if not all([self.access_key, self.secret_key, self.bucket_name, self.domain]):
            logger.warning("⚠️ 七牛云配置不完整，图片上传功能将不可用")
            self.enabled = False
        else:
            self.enabled = True
            self.auth = Auth(self.access_key, self.secret_key)
            logger.info("✅ 七牛云服务初始化成功")
    
    async def upload_image_from_url(
        self,
        image_url: str,
        key_prefix: str = "image-edit",
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        从URL下载图片并上传到七牛云
        
        Args:
            image_url: 图片URL
            key_prefix: 存储路径前缀（默认：image-edit）
            filename: 文件名（可选，如果不提供则自动生成）
            
        Returns:
            上传成功返回CDN URL，失败返回None
        """
        if not self.enabled:
            logger.warning("⚠️ 七牛云服务未启用，跳过上传")
            return None
        
        try:
            # 1. 下载图片
            logger.info(f"📥 开始下载图片: {image_url[:50]}...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            
            logger.info(f"✅ 图片下载成功，大小: {len(image_data)} bytes")
            
            # 2. 生成存储key
            if filename:
                key = f"{key_prefix}/{filename}"
            else:
                from app.utils.id_generator import IDGenerator
                import time
                timestamp = int(time.time() * 1000)
                key = f"{key_prefix}/{IDGenerator.generate_request_id('img')}_{timestamp}.png"
            
            # 3. 上传到七牛云
            logger.info(f"📤 开始上传到七牛云: bucket={self.bucket_name}, key={key}")
            token = self.auth.upload_token(self.bucket_name, key, 3600)
            
            # 使用同步方式上传（qiniu SDK不支持异步）
            ret, info = put_data(token, key, image_data)
            
            if ret is None:
                logger.error(f"❌ 七牛云上传失败: {info}")
                return None
            
            # 4. 生成CDN URL
            cdn_url = f"{self.domain}/{key}"
            logger.info(f"✅ 图片上传成功: {cdn_url}")
            
            return cdn_url
            
        except httpx.TimeoutException:
            logger.error(f"❌ 下载图片超时: {image_url[:50]}...")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ 下载图片失败: HTTP {e.response.status_code}, URL: {image_url[:50]}...")
            return None
        except Exception as e:
            logger.error(f"❌ 上传图片到七牛云失败: {e}", exc_info=True)
            return None
    
    async def upload_image_from_bytes(
        self,
        image_bytes: bytes,
        key_prefix: str = "image-edit",
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        直接上传图片字节数据到七牛云
        
        Args:
            image_bytes: 图片二进制数据
            key_prefix: 存储路径前缀（默认：image-edit）
            filename: 文件名（可选，如果不提供则自动生成）
            
        Returns:
            上传成功返回CDN URL，失败返回None
        """
        if not self.enabled:
            logger.warning("⚠️ 七牛云服务未启用，跳过上传")
            return None
        
        try:
            # 1. 生成存储key
            if filename:
                key = f"{key_prefix}/{filename}"
            else:
                from app.utils.id_generator import IDGenerator
                import time
                timestamp = int(time.time() * 1000)
                key = f"{key_prefix}/{IDGenerator.generate_request_id('img')}_{timestamp}.png"
            
            # 2. 上传到七牛云
            logger.info(f"📤 开始上传到七牛云: bucket={self.bucket_name}, key={key}, size={len(image_bytes)} bytes")
            token = self.auth.upload_token(self.bucket_name, key, 3600)
            
            # 使用同步方式上传（qiniu SDK不支持异步）
            ret, info = put_data(token, key, image_bytes)
            
            if ret is None:
                logger.error(f"❌ 七牛云上传失败: {info}")
                return None
            
            # 3. 生成CDN URL
            cdn_url = f"{self.domain}/{key}"
            logger.info(f"✅ 图片上传成功: {cdn_url}")
            
            return cdn_url
            
        except Exception as e:
            logger.error(f"❌ 上传图片到七牛云失败: {e}", exc_info=True)
            return None


# 全局服务实例
qiniu_service = QiniuService()

