"""
pytest配置和测试工具
"""
import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
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
            # 这里可以初始化测试数据库
            # 例如：创建表、插入测试数据等
            pass
        except Exception as e:
            pytest.skip(f"测试数据库不可用: {e}")
    
    yield
    
    # 测试后的清理工作（可选）
    # 例如：清理测试数据


@pytest.fixture
def client():
    """测试客户端fixture"""
    return TestClient(app)


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

