"""
请求ID生成器
生成格式：req_{timestamp}_{random_string}
"""

import uuid
import time
from typing import Optional


class IDGenerator:
    """请求ID生成器"""
    
    @staticmethod
    def generate_request_id(prefix: str = "req") -> str:
        """
        生成请求ID
        
        Args:
            prefix: ID前缀，默认为"req"
            
        Returns:
            格式化的请求ID，如：req_1696934400_a3f5d8c2b1e9
        """
        timestamp = int(time.time())
        random_part = uuid.uuid4().hex[:12]
        return f"{prefix}_{timestamp}_{random_part}"
    
    @staticmethod
    def parse_request_id(request_id: str) -> Optional[dict]:
        """
        解析请求ID，提取时间戳
        
        Args:
            request_id: 请求ID
            
        Returns:
            包含前缀、时间戳、随机字符串的字典，解析失败返回None
        """
        try:
            parts = request_id.split('_')
            if len(parts) >= 3:
                return {
                    'prefix': parts[0],
                    'timestamp': int(parts[1]),
                    'random': parts[2]
                }
        except Exception:
            pass
        return None

