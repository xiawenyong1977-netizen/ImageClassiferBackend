"""
pytest配置和测试工具
"""
import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth import create_access_token
from app.config import settings
from app.database import db


# 加载测试环境变量（如果存在）
test_env_file = Path(__file__).parent / ".env.test"
if test_env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(test_env_file, override=True)




@pytest.fixture(scope="session")
async def setup_test_db():
    """
    测试数据库初始化fixture（session级别）
    只在需要真实数据库的测试中使用
    """
    # 检查是否配置了测试数据库
    test_db = os.getenv("MYSQL_DATABASE", "image_classifier_test")
    
    # 如果使用测试数据库，尝试连接
    if test_db.endswith("_test"):
        try:
            # 初始化数据库连接池（session级别，所有测试共享）
            if not db.pool:
                await db.connect()
            
            # 执行数据库初始化脚本
            sql_file = Path(__file__).parent / "setup_test_db.sql"
            if sql_file.exists():
                try:
                    # 读取SQL文件（移除BOM字符）
                    sql_content = sql_file.read_text(encoding='utf-8-sig')  # utf-8-sig会自动移除BOM
                    
                    # 移除注释和空行，按分号分割SQL语句
                    statements = []
                    current_statement = []
                    for line in sql_content.split('\n'):
                        # 移除行注释
                        line = line.split('--')[0].strip()
                        if not line or line.startswith('--'):
                            continue
                        current_statement.append(line)
                        # 如果行以分号结尾，说明语句结束
                        if line.rstrip().endswith(';'):
                            statement = ' '.join(current_statement).strip()
                            if statement:
                                statements.append(statement)
                            current_statement = []
                    
                    # 执行所有SQL语句
                    async with db.get_connection() as conn:
                        async with conn.cursor() as cursor:
                            for statement in statements:
                                if statement:
                                    # 跳过CREATE DATABASE语句（连接已指定数据库）
                                    if statement.strip().upper().startswith('CREATE DATABASE'):
                                        continue
                                    # 跳过USE语句（连接已指定数据库）
                                    if statement.strip().upper().startswith('USE '):
                                        continue
                                    # 跳过SELECT语句（只是显示状态）
                                    if statement.strip().upper().startswith('SELECT ') and 'AS \'Status\'' in statement:
                                        continue
                                    try:
                                        await cursor.execute(statement)
                                    except Exception as e:
                                        # 忽略表已存在的错误和重复键错误
                                        error_str = str(e).lower()
                                        if any(keyword in error_str for keyword in ["already exists", "duplicate", "table"]):
                                            # 表已存在或重复键，这是正常的，忽略
                                            pass
                                        else:
                                            # 对于其他错误，记录警告但不中断测试
                                            import warnings
                                            warnings.warn(f"执行SQL语句时出现警告: {e}\n语句: {statement[:100]}")
                            await conn.commit()
                except Exception as e:
                    # 如果初始化脚本执行失败，记录警告但不中断测试
                    import warnings
                    warnings.warn(f"数据库初始化脚本执行失败（可能表已存在）: {e}")
        except Exception as e:
            pytest.skip(f"测试数据库不可用: {e}")
    
    yield
    
    # 测试session结束后，关闭数据库连接池
    if db.pool:
        try:
            import asyncio
            # 检查事件循环是否还在运行
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    # 事件循环已关闭，直接设置pool为None
                    db.pool = None
                else:
                    # 事件循环还在运行，正常关闭连接池
                    await db.disconnect()
            except RuntimeError:
                # 没有运行中的事件循环，直接设置pool为None
                db.pool = None
        except Exception:
            # 忽略清理时的错误，确保pool被设置为None
            db.pool = None


@pytest.fixture
def client():
    """测试客户端fixture（同步）"""
    return TestClient(app)


@pytest.fixture
async def async_client(setup_test_db):
    """
    异步测试客户端fixture（推荐用于需要数据库的测试）
    
    注意：ASGITransport 会创建新的事件循环，导致数据库连接池的事件循环不匹配
    解决方法：让每个请求在FastAPI的lifespan中重新初始化连接池，或使用lifespan参数
    """
    # 使用 ASGITransport，它会自动调用 FastAPI 的 lifespan（如果使用 root_path 参数）
    # 但我们不在这里管理连接池，让 lifespan 管理它
    # 如果连接池已在不同的循环中创建，get_connection 会自动检测并重新创建
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_connection():
    """
    数据库连接fixture（用于需要真实数据库的测试）
    注意：大部分测试使用mock，不需要此fixture
    """
    try:
        await db.connect()
        yield db
    finally:
        await db.disconnect()


@pytest.fixture
def auth_headers():
    """生成认证头部的fixture"""
    # 使用默认管理员用户名创建token
    token = create_access_token(data={"sub": settings.ADMIN_USERNAME})
    return {"Authorization": f"Bearer {token}"}


def get_test_token(username: str = None) -> str:
    """
    获取测试用的JWT token
    
    Args:
        username: 用户名，默认使用管理员用户名
        
    Returns:
        JWT token字符串
    """
    if username is None:
        username = settings.ADMIN_USERNAME
    return create_access_token(data={"sub": username})

