"""
哈希计算工具
使用SHA-256算法
"""

import hashlib


class HashUtils:
    """哈希工具类"""
    
    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """
        计算数据的SHA-256哈希值
        
        Args:
            data: 二进制数据
            
        Returns:
            64字符的十六进制哈希字符串
        """
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        计算文件的SHA-256哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            64字符的十六进制哈希字符串
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # 分块读取，避免大文件内存溢出
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


# 全局函数别名，方便导入使用
def calculate_hash(data: bytes) -> str:
    """
    计算数据的SHA-256哈希值（全局函数）
    
    Args:
        data: 二进制数据
        
    Returns:
        64字符的十六进制哈希字符串
    """
    return HashUtils.calculate_sha256(data)

