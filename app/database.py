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
                autocommit=True,
                pool_recycle=300,
                echo=settings.APP_DEBUG
            )
            logger.info(f"数据库连接池已创建: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    async def disconnect(self):
        """关闭数据库连接池"""
        if self.pool:
            try:
                self.pool.close()
                await self.pool.wait_closed()
                logger.info("数据库连接池已关闭")
            except (RuntimeError, Exception) as e:
                # 如果事件循环已关闭或其他错误，只关闭连接池，不等待
                error_msg = str(e).lower()
                if "event loop is closed" in error_msg or "cannot be called from a running event loop" in error_msg:
                    self.pool.close()
                    logger.warning("数据库连接池已关闭（事件循环已关闭）")
                else:
                    # 其他错误也尝试关闭连接池，但不抛出异常
                    self.pool.close()
                    logger.warning(f"数据库连接池关闭时出现错误（已忽略）: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as conn:
                try:
                    # 确保连接可用并设置会话级隔离级别与autocommit
                    await conn.ping()
                    async with conn.cursor() as cursor:
                        await cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                        await cursor.execute("SET autocommit=1")
                except Exception as e:
                    logger.warning(f"数据库连接会话初始化失败: {e}")
                yield conn
        except RuntimeError as e:
            # 如果事件循环已关闭，抛出更友好的错误
            error_msg = str(e).lower()
            if "event loop is closed" in error_msg:
                logger.error("数据库操作失败：事件循环已关闭（可能是测试环境问题）")
                raise RuntimeError("数据库操作失败：事件循环已关闭。请确保在异步上下文中使用数据库操作。")
            raise
    
    @asynccontextmanager
    async def get_cursor(self):
        """获取游标（上下文管理器）"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield cursor
                await conn.commit()


# 全局数据库实例
db = Database()

