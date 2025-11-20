"""
图片处理工具
使用Pillow进行图片验证和处理
"""

from PIL import Image
import io
from typing import Tuple, Optional
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
            
            # MPO格式特殊处理：允许MPO格式，但需要转换为JPEG
            if format_lower == "mpo":
                return True, ""
            
            if format_lower not in settings.allowed_formats_list:
                allowed = ", ".join(settings.allowed_formats_list)
                return False, f"不支持的图片格式：{img.format}，支持的格式：{allowed}"
            
            return True, ""
            
        except Exception as e:
            return False, f"无效的图片文件：{str(e)}"
    
    @staticmethod
    def convert_mpo_to_jpeg(image_bytes: bytes) -> Optional[bytes]:
        """
        将MPO格式图片转换为JPEG格式
        MPO（Multi Picture Object）通常包含两张图片，提取第一张并转换为JPEG
        
        Args:
            image_bytes: MPO格式的图片二进制数据
            
        Returns:
            转换后的JPEG格式图片数据，如果转换失败返回None
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            format_lower = img.format.lower() if img.format else ""
            
            # 如果不是MPO格式，直接返回原数据
            if format_lower != "mpo":
                return image_bytes
            
            # MPO格式通常包含多张图片，提取第一张
            # 确保图片是RGB模式
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 转换为JPEG
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            from loguru import logger
            logger.error(f"MPO格式转换失败: {e}")
            return None
    
    @staticmethod
    def normalize_image_format(image_bytes: bytes) -> bytes:
        """
        标准化图片格式，将特殊格式（如MPO）转换为标准格式（JPEG）
        
        Args:
            image_bytes: 原始图片二进制数据
            
        Returns:
            标准化后的图片数据
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            format_lower = img.format.lower() if img.format else ""
            
            # 如果是MPO格式，转换为JPEG
            if format_lower == "mpo":
                converted = ImageUtils.convert_mpo_to_jpeg(image_bytes)
                if converted:
                    return converted
                # 如果转换失败，返回原数据
                return image_bytes
            
            # 其他格式直接返回
            return image_bytes
            
        except Exception:
            # 如果无法识别格式，返回原数据
            return image_bytes
    
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

