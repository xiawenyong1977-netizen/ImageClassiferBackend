"""
图片处理工具
使用Pillow进行图片验证和处理
"""

from PIL import Image
import io
from typing import Tuple
from app.config import settings


class ImageUtils:
    """图片工具类"""
    
    @staticmethod
    def validate_image(image_bytes: bytes) -> Tuple[bool, str]:
        """
        验证图片格式和大小
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            (是否有效, 错误信息)
        """
        # 检查大小
        if len(image_bytes) > settings.max_image_size_bytes:
            max_mb = settings.MAX_IMAGE_SIZE_MB
            actual_mb = len(image_bytes) / 1024 / 1024
            return False, f"图片过大：{actual_mb:.2f}MB，最大允许{max_mb}MB"
        
        # 检查格式
        try:
            img = Image.open(io.BytesIO(image_bytes))
            format_lower = img.format.lower() if img.format else ""
            
            if format_lower not in settings.allowed_formats_list:
                allowed = ", ".join(settings.allowed_formats_list)
                return False, f"不支持的图片格式：{img.format}，支持的格式：{allowed}"
            
            return True, ""
            
        except Exception as e:
            return False, f"无效的图片文件：{str(e)}"
    
    @staticmethod
    def get_image_info(image_bytes: bytes) -> dict:
        """
        获取图片信息
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            图片信息字典
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            return {
                "format": img.format.lower() if img.format else "unknown",
                "size": len(image_bytes),
                "width": img.width,
                "height": img.height,
                "mode": img.mode
            }
        except Exception:
            return {}
    
    @staticmethod
    def compress_image(image_bytes: bytes, max_size_kb: int = 500) -> bytes:
        """
        压缩图片（如果需要）
        
        Args:
            image_bytes: 原始图片数据
            max_size_kb: 目标大小（KB）
            
        Returns:
            压缩后的图片数据
        """
        size_kb = len(image_bytes) / 1024
        
        if size_kb <= max_size_kb:
            return image_bytes  # 已经够小，不需要压缩
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # 调整尺寸（如果需要）
            if max(img.size) > 1024:
                ratio = 1024 / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.LANCZOS)
            
            # 压缩
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception:
            # 压缩失败，返回原图
            return image_bytes

