"""
数据库连接管理
使用aiomysql进行异步MySQL操作
"""

import aiomysql
from typing import Optional
from contextlib import asynccontextmanager
from app.config import settings
from loguru import logger


class Database:
    """数据库连接池管理"""
    
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
    
    async def connect(self):
        """创建数据库连接池"""
        try:
            self.pool = await aiomysql.create_pool(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                db=settings.MYSQL_DATABASE,
                charset='utf8mb4',
                minsize=1,
                maxsize=settings.MYSQL_POOL_SIZE,
                autocommit=False,
                echo=settings.APP_DEBUG
            )
            logger.info(f"数据库连接池已创建: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    async def disconnect(self):
        """关闭数据库连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("数据库连接池已关闭")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def get_cursor(self):
        """获取游标（上下文管理器）"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield cursor
                await conn.commit()


# 全局数据库实例
db = Database()

