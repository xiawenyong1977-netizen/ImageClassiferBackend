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
        # 如果连接池不存在或绑定到了不同的事件循环，重新创建
        import asyncio
        current_loop = asyncio.get_running_loop()
        
        if not self.pool:
            await self.connect()
        else:
            # 检查连接池是否绑定到当前事件循环
            # 如果pool是在不同的事件循环中创建的，需要重新创建
            try:
                # 尝试检查pool的内部状态（aiomysql的pool._loop）
                pool_loop = getattr(self.pool, '_loop', None)
                if pool_loop is not None and pool_loop != current_loop:
                    logger.warning("检测到数据库连接池绑定到不同的事件循环，重新创建连接池")
                    try:
                        self.pool.close()
                        await self.pool.wait_closed()
                    except Exception:
                        pass
                    await self.connect()
            except Exception:
                # 如果检查失败，假设连接池可用，继续使用
                pass
        
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
            # 检查是否是事件循环问题
            error_msg = str(e).lower()
            if "attached to a different loop" in error_msg:
                # 如果是事件循环不匹配问题，尝试重新创建连接池
                logger.warning("检测到事件循环不匹配，重新创建连接池")
                try:
                    if self.pool:
                        try:
                            self.pool.close()
                            await self.pool.wait_closed()
                        except Exception:
                            pass
                except Exception:
                    pass
                # 重新创建连接池（会在当前事件循环中创建）
                self.pool = None
                await self.connect()
                # 重试获取连接
                async with self.pool.acquire() as conn:
                    try:
                        await conn.ping()
                        async with conn.cursor() as cursor:
                            await cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                            await cursor.execute("SET autocommit=1")
                    except Exception as e2:
                        logger.warning(f"数据库连接会话初始化失败: {e2}")
                    yield conn
            elif "event loop is closed" in error_msg:
                logger.error("数据库操作失败：事件循环已关闭（可能是测试环境问题）")
                raise RuntimeError("数据库操作失败：事件循环已关闭。请确保在异步上下文中使用数据库操作。")
            else:
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

