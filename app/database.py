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
        # 如果连接池已存在，直接返回（避免重复创建）
        if self.pool is not None:
            try:
                # 检查连接池是否仍然有效
                async with self.pool.acquire() as conn:
                    await conn.ping()
                logger.debug("数据库连接池已存在且有效，跳过创建")
                return
            except Exception:
                # 如果连接池无效，关闭它并重新创建
                logger.debug("检测到无效的连接池，将重新创建")
                try:
                    self.pool.close()
                    await self.pool.wait_closed()
                except Exception:
                    pass
                self.pool = None
        
        try:
            # 如果配置了 unix_socket，优先使用 socket 连接
            if settings.MYSQL_UNIX_SOCKET:
                self.pool = await aiomysql.create_pool(
                    unix_socket=settings.MYSQL_UNIX_SOCKET,
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
                logger.info(f"数据库连接池已创建（使用socket）: {settings.MYSQL_UNIX_SOCKET}/{settings.MYSQL_DATABASE}")
            else:
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
        if not self.pool:
            return
        
        pool = self.pool
        self.pool = None  # 先设置为None，避免并发问题
        
        try:
            # 先关闭连接池，这会关闭所有连接
            pool.close()
            # 等待连接池关闭完成
            await pool.wait_closed()
            logger.info("数据库连接池已关闭")
        except RuntimeError as e:
            # 如果事件循环已关闭，无法等待关闭完成
            error_msg = str(e).lower()
            if "event loop is closed" in error_msg:
                logger.warning("数据库连接池已关闭（事件循环已关闭，无法等待关闭完成）")
            else:
                # 其他RuntimeError，可能是事件循环问题，记录警告
                logger.warning(f"数据库连接池关闭时出现RuntimeError（已忽略）: {e}")
        except Exception as e:
            # 其他错误也记录警告，但不抛出异常
            # 特别注意：在测试环境中，连接对象可能在事件循环关闭后才被垃圾回收，
            # 这会导致 aiomysql 的 Connection.__del__ 方法抛出 RuntimeError，
            # 这是正常的，不影响测试结果
            error_msg = str(e).lower()
            if "event loop is closed" in error_msg:
                logger.debug("数据库连接池关闭时事件循环已关闭（测试环境正常现象）")
            else:
                logger.warning(f"数据库连接池关闭时出现错误（已忽略）: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        logger.info(f"[database] get_connection开始: pool存在={self.pool is not None}")
        # 如果连接池不存在或绑定到了不同的事件循环，重新创建
        import asyncio
        current_loop = asyncio.get_running_loop()
        
        if not self.pool:
            logger.info(f"[database] 连接池不存在，准备创建...")
            await self.connect()
        else:
            # 检查连接池是否绑定到当前事件循环
            # 如果pool是在不同的事件循环中创建的，需要重新创建
            # 注意：在 Gunicorn 多 worker 模式下，每个 worker 都有自己的事件循环
            # 这是正常现象，连接池会在每个 worker 中重新创建
            try:
                # 尝试检查pool的内部状态（aiomysql的pool._loop）
                pool_loop = getattr(self.pool, '_loop', None)
                if pool_loop is not None and pool_loop != current_loop:
                    # 只在 DEBUG 模式下记录详细信息，避免过多警告日志
                    logger.debug(f"检测到数据库连接池绑定到不同的事件循环（pool_loop: {pool_loop}, current_loop: {current_loop}），重新创建连接池")
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
            logger.info(f"[database] 准备从连接池获取连接...")
            async with self.pool.acquire() as conn:
                logger.info(f"[database] 已从连接池获取连接，准备ping...")
                try:
                    # 确保连接可用并设置会话级隔离级别与autocommit
                    await conn.ping()
                    logger.info(f"[database] ping成功，准备设置会话参数...")
                    async with conn.cursor() as cursor:
                        await cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                        await cursor.execute("SET autocommit=1")
                    logger.info(f"[database] 会话参数设置完成")
                except Exception as e:
                    logger.warning(f"数据库连接会话初始化失败: {e}")
                logger.info(f"[database] 准备yield连接...")
                yield conn
                logger.info(f"[database] 连接已返回给调用者")
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
                try:
                    await self.connect()
                except Exception as connect_err:
                    logger.error(f"重新创建数据库连接池失败: {connect_err}")
                    raise RuntimeError(f"无法重新创建数据库连接池: {connect_err}") from e
                
                # 重试获取连接
                try:
                    async with self.pool.acquire() as conn:
                        try:
                            await conn.ping()
                            async with conn.cursor() as cursor:
                                await cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                                await cursor.execute("SET autocommit=1")
                        except Exception as e2:
                            logger.warning(f"数据库连接会话初始化失败: {e2}")
                        yield conn
                except Exception as acquire_err:
                    logger.error(f"重试获取数据库连接失败: {acquire_err}")
                    raise RuntimeError(f"重试获取数据库连接失败: {acquire_err}") from e
            elif "event loop is closed" in error_msg:
                logger.error("数据库操作失败：事件循环已关闭（可能是测试环境问题）")
                raise RuntimeError("数据库操作失败：事件循环已关闭。请确保在异步上下文中使用数据库操作。")
            else:
                raise
    
    @asynccontextmanager
    async def get_cursor(self):
        """获取游标（上下文管理器）"""
        logger.info(f"[database] get_cursor开始...")
        async with self.get_connection() as conn:
            logger.info(f"[database] get_cursor已获取连接，准备创建游标...")
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield cursor
                await conn.commit()


# 全局数据库实例
db = Database()

