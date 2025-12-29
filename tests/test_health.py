"""
健康检查测试
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """测试健康检查接口"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_app_startup():
    """测试应用是否可以正常启动"""
    # 如果应用可以导入并创建客户端，说明启动成功
    assert app is not None
    assert client is not None

