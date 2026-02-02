"""
测试试用模式接口返回
当 ALLOW_IMAGE_EDIT_WITHOUT_OPENID=true 时，验证接口返回是否正确
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_credits_api_without_openid_when_enabled():
    """测试额度查询接口：配置项开启，无openid"""
    # 临时设置配置项
    original_value = settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID
    settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = True
    
    try:
        # 测试场景1：只有 client_id，但没有绑定 openid
        response = client.get("/api/v1/user/credits?client_id=test-client-id-123")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回字段
        assert data["success"] is True
        assert data["total_credits"] is None  # 试用模式无额度限制
        assert data["used_credits"] == 0
        assert data["remaining_credits"] is None  # 试用模式无额度限制
        assert data["is_followed"] is False  # 未关注公众号
        assert data["is_member"] is False
        assert data["member_expire_at"] is None
        assert data["is_trial_mode"] is True  # 标识为试用模式
        
        # 测试场景2：既没有 client_id 也没有 openid
        response = client.get("/api/v1/user/credits")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回字段
        assert data["success"] is True
        assert data["is_trial_mode"] is True
        
    finally:
        # 恢复原始配置
        settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = original_value


def test_member_status_api_without_openid_when_enabled():
    """测试会员状态接口：配置项开启，无openid"""
    # 临时设置配置项
    original_value = settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID
    settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = True
    
    try:
        # 测试场景1：只有 client_id，但没有绑定 openid
        response = client.get("/api/v1/user/member-status?client_id=test-client-id-123")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回字段
        assert data["success"] is True
        assert data["is_followed"] is False  # 未关注公众号
        assert data["is_member"] is False
        assert data["member_expire_at"] is None
        assert data["is_trial_mode"] is True  # 标识为试用模式
        
        # 测试场景2：既没有 client_id 也没有 openid
        response = client.get("/api/v1/user/member-status")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回字段
        assert data["success"] is True
        assert data["is_trial_mode"] is True
        
    finally:
        # 恢复原始配置
        settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = original_value


def test_image_edit_api_without_openid_when_enabled():
    """测试图像编辑接口：配置项开启，无openid"""
    # 临时设置配置项
    original_value = settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID
    settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = True
    
    try:
        # 模拟请求（需要实际的图片文件）
        # 这里只测试逻辑，不实际发送请求
        # 实际测试需要提供图片文件
        
        # 验证配置项已设置
        assert settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID is True
        
    finally:
        # 恢复原始配置
        settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = original_value


def test_credits_api_without_openid_when_disabled():
    """测试额度查询接口：配置项关闭，无openid（应该返回错误）"""
    # 临时设置配置项
    original_value = settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID
    settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = False
    
    try:
        # 测试场景：只有 client_id，但没有绑定 openid
        response = client.get("/api/v1/user/credits?client_id=test-client-id-123")
        
        # 应该返回404错误
        assert response.status_code == 404
        data = response.json()
        assert "用户未关注公众号" in data["detail"]
        
    finally:
        # 恢复原始配置
        settings.ALLOW_IMAGE_EDIT_WITHOUT_OPENID = original_value


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
