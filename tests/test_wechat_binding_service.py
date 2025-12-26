"""
微信二维码绑定服务测试
"""

import pytest
from app.services.wechat_binding_service import wechat_binding_service
from app.database import db


class TestWeChatBindingService:
    """微信二维码绑定服务测试类"""
    
    @pytest.fixture(autouse=True)
    async def setup(self, setup_test_db):
        """每个测试前确保数据库已初始化"""
        pass
    
    @pytest.fixture
    async def cleanup(self):
        """测试后清理数据"""
        yield
        # 清理测试数据
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("DELETE FROM wechat_qrcode_bindings WHERE client_id LIKE 'test_%'")
        except Exception:
            pass
    
    @pytest.fixture
    async def setup_binding_data(self, cleanup):
        """设置测试用的绑定数据"""
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 先清理可能存在的测试数据
                await cursor.execute("DELETE FROM wechat_qrcode_bindings WHERE client_id LIKE 'test_client_%'")
                await conn.commit()
                
                # 插入测试绑定数据（使用 ON DUPLICATE KEY UPDATE 避免重复键错误）
                # 注意：由于 client_id 有唯一约束，同一个 client_id 只能有一条记录
                # 所以 test_client_1 的测试改为：先插入旧记录，然后更新为新记录
                await cursor.execute("""
                    INSERT INTO wechat_qrcode_bindings 
                    (client_id, scene_id, openid, status, completed_at)
                    VALUES 
                    ('test_client_1', 'test_scene_1', 'test_openid_1', 'completed', DATE_SUB(NOW(), INTERVAL 1 SECOND)),
                    ('test_client_2', 'test_scene_2', 'test_openid_2', 'completed', NOW()),
                    ('test_client_3', 'test_scene_3', NULL, 'pending', NULL)
                    AS new_values
                    ON DUPLICATE KEY UPDATE 
                        openid = new_values.openid,
                        status = new_values.status,
                        completed_at = new_values.completed_at
                """)
                # 更新 test_client_1 为新记录（用于测试返回最新的 openid）
                await cursor.execute("""
                    UPDATE wechat_qrcode_bindings 
                    SET openid = 'test_openid_1_new', 
                        completed_at = NOW()
                    WHERE client_id = 'test_client_1'
                """)
                await conn.commit()
        yield
        # cleanup fixture 会清理数据
    
    @pytest.mark.asyncio
    async def test_get_openid_by_client_id_success(self, setup_binding_data):
        """测试根据 client_id 查询 openid 成功"""
        openid = await wechat_binding_service.get_openid_by_client_id("test_client_1")
        # 应该返回最新的 openid（按 completed_at DESC 排序）
        assert openid == "test_openid_1_new"
    
    @pytest.mark.asyncio
    async def test_get_openid_by_client_id_single(self, setup_binding_data):
        """测试根据 client_id 查询 openid（只有一条记录）"""
        openid = await wechat_binding_service.get_openid_by_client_id("test_client_2")
        assert openid == "test_openid_2"
    
    @pytest.mark.asyncio
    async def test_get_openid_by_client_id_no_openid(self, setup_binding_data):
        """测试根据 client_id 查询 openid（openid 为 NULL）"""
        openid = await wechat_binding_service.get_openid_by_client_id("test_client_3")
        assert openid is None
    
    @pytest.mark.asyncio
    async def test_get_openid_by_client_id_not_found(self, cleanup):
        """测试根据 client_id 查询 openid（未找到）"""
        openid = await wechat_binding_service.get_openid_by_client_id("test_client_nonexist")
        assert openid is None
    
    @pytest.mark.asyncio
    async def test_get_openid_by_client_id_empty(self, cleanup):
        """测试根据 client_id 查询 openid（client_id 为空）"""
        openid = await wechat_binding_service.get_openid_by_client_id("")
        assert openid is None
    
    @pytest.mark.asyncio
    async def test_resolve_openid_with_openid(self, cleanup):
        """测试 resolve_openid（直接提供 openid）"""
        openid = await wechat_binding_service.resolve_openid(
            openid="test_openid_direct",
            client_id="test_client_any"
        )
        assert openid == "test_openid_direct"
    
    @pytest.mark.asyncio
    async def test_resolve_openid_with_client_id(self, setup_binding_data):
        """测试 resolve_openid（通过 client_id 查询）"""
        openid = await wechat_binding_service.resolve_openid(
            openid=None,
            client_id="test_client_2"
        )
        assert openid == "test_openid_2"
    
    @pytest.mark.asyncio
    async def test_resolve_openid_both_none(self, cleanup):
        """测试 resolve_openid（openid 和 client_id 都为 None）"""
        openid = await wechat_binding_service.resolve_openid(
            openid=None,
            client_id=None
        )
        assert openid is None
    
    @pytest.mark.asyncio
    async def test_resolve_openid_openid_priority(self, setup_binding_data):
        """测试 resolve_openid（openid 优先于 client_id）"""
        # 即使 client_id 存在，也应该返回直接提供的 openid
        openid = await wechat_binding_service.resolve_openid(
            openid="test_openid_priority",
            client_id="test_client_1"
        )
        assert openid == "test_openid_priority"
    
    @pytest.mark.asyncio
    async def test_resolve_openid_client_id_not_found(self, cleanup):
        """测试 resolve_openid（client_id 未找到）"""
        openid = await wechat_binding_service.resolve_openid(
            openid=None,
            client_id="test_client_nonexist"
        )
        assert openid is None

