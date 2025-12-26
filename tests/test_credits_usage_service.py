"""
额度消耗记录服务测试
"""

import pytest
from app.services.credits_usage_service import credits_usage_service
from app.database import db


class TestCreditsUsageService:
    """额度消耗记录服务测试类"""
    
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
                await cursor.execute("DELETE FROM credits_usage WHERE openid LIKE 'test_%' OR task_id LIKE 'test_%'")
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_log_usage_success(self, cleanup):
        """测试记录额度消耗成功"""
        result = await credits_usage_service.log_usage(
            openid="test_openid_1",
            task_id="test_task_1",
            task_type="image_edit",
            credits_used=5,
            request_image_count=10,
            success_image_count=8
        )
        assert result is True
        
        # 验证记录已插入
        async with db.get_cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM credits_usage WHERE task_id = %s",
                ("test_task_1",)
            )
            record = await cursor.fetchone()
            assert record is not None
            assert record['openid'] == "test_openid_1"
            assert record['task_id'] == "test_task_1"
            assert record['task_type'] == "image_edit"
            assert record['credits_used'] == 5
            assert record['request_image_count'] == 10
            assert record['success_image_count'] == 8
    
    @pytest.mark.asyncio
    async def test_log_usage_empty_openid(self, cleanup):
        """测试记录额度消耗时 openid 为空"""
        result = await credits_usage_service.log_usage(
            openid="",
            task_id="test_task_2",
            task_type="image_edit",
            credits_used=1,
            request_image_count=1,
            success_image_count=1
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_log_usage_empty_task_id(self, cleanup):
        """测试记录额度消耗时 task_id 为空"""
        result = await credits_usage_service.log_usage(
            openid="test_openid_2",
            task_id="",
            task_type="image_edit",
            credits_used=1,
            request_image_count=1,
            success_image_count=1
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_usage_by_openid_success(self, cleanup):
        """测试根据 openid 查询额度消耗记录成功"""
        import asyncio
        # 先插入测试数据
        await credits_usage_service.log_usage(
            openid="test_openid_3",
            task_id="test_task_3",
            task_type="image_edit",
            credits_used=3,
            request_image_count=5,
            success_image_count=4
        )
        # 添加小延迟，确保时间戳不同
        await asyncio.sleep(0.1)
        await credits_usage_service.log_usage(
            openid="test_openid_3",
            task_id="test_task_4",
            task_type="batch_classify",
            credits_used=2,
            request_image_count=3,
            success_image_count=3
        )
        
        # 查询记录
        records = await credits_usage_service.get_usage_by_openid(
            openid="test_openid_3",
            limit=10
        )
        
        assert len(records) == 2
        assert records[0]['task_id'] == "test_task_4"  # 按时间倒序，后插入的在前面
        assert records[1]['task_id'] == "test_task_3"
        assert records[0]['task_type'] == "batch_classify"
        assert records[1]['task_type'] == "image_edit"
    
    @pytest.mark.asyncio
    async def test_get_usage_by_openid_with_limit(self, cleanup):
        """测试根据 openid 查询额度消耗记录（带 limit）"""
        # 先插入多条测试数据
        for i in range(5):
            await credits_usage_service.log_usage(
                openid="test_openid_4",
                task_id=f"test_task_{i}",
                task_type="image_edit",
                credits_used=1,
                request_image_count=1,
                success_image_count=1
            )
        
        # 查询记录（限制3条）
        records = await credits_usage_service.get_usage_by_openid(
            openid="test_openid_4",
            limit=3
        )
        
        assert len(records) == 3
    
    @pytest.mark.asyncio
    async def test_get_usage_by_openid_with_offset(self, cleanup):
        """测试根据 openid 查询额度消耗记录（带 offset）"""
        # 先插入多条测试数据
        for i in range(5):
            await credits_usage_service.log_usage(
                openid="test_openid_5",
                task_id=f"test_task_offset_{i}",
                task_type="image_edit",
                credits_used=1,
                request_image_count=1,
                success_image_count=1
            )
        
        # 查询记录（offset=2, limit=2）
        records = await credits_usage_service.get_usage_by_openid(
            openid="test_openid_5",
            limit=2,
            offset=2
        )
        
        assert len(records) == 2
    
    @pytest.mark.asyncio
    async def test_get_usage_by_openid_empty(self, cleanup):
        """测试根据 openid 查询额度消耗记录（无记录）"""
        records = await credits_usage_service.get_usage_by_openid(
            openid="test_openid_nonexist",
            limit=10
        )
        assert records == []
    
    @pytest.mark.asyncio
    async def test_get_usage_by_openid_empty_openid(self, cleanup):
        """测试根据 openid 查询额度消耗记录（openid 为空）"""
        records = await credits_usage_service.get_usage_by_openid(
            openid="",
            limit=10
        )
        assert records == []
    
    @pytest.mark.asyncio
    async def test_get_usage_by_task_id_success(self, cleanup):
        """测试根据 task_id 查询额度消耗记录成功"""
        # 先插入测试数据
        await credits_usage_service.log_usage(
            openid="test_openid_6",
            task_id="test_task_6",
            task_type="image_edit",
            credits_used=5,
            request_image_count=10,
            success_image_count=8
        )
        
        # 查询记录
        record = await credits_usage_service.get_usage_by_task_id("test_task_6")
        
        assert record is not None
        assert record['openid'] == "test_openid_6"
        assert record['task_id'] == "test_task_6"
        assert record['task_type'] == "image_edit"
        assert record['credits_used'] == 5
        assert record['request_image_count'] == 10
        assert record['success_image_count'] == 8
    
    @pytest.mark.asyncio
    async def test_get_usage_by_task_id_not_found(self, cleanup):
        """测试根据 task_id 查询额度消耗记录（未找到）"""
        record = await credits_usage_service.get_usage_by_task_id("test_task_nonexist")
        assert record is None
    
    @pytest.mark.asyncio
    async def test_get_usage_by_task_id_empty(self, cleanup):
        """测试根据 task_id 查询额度消耗记录（task_id 为空）"""
        record = await credits_usage_service.get_usage_by_task_id("")
        assert record is None
    
    @pytest.mark.asyncio
    async def test_get_total_credits_used_success(self, cleanup):
        """测试查询用户累计消耗的额度总数成功"""
        # 先插入多条测试数据
        await credits_usage_service.log_usage(
            openid="test_openid_7",
            task_id="test_task_7_1",
            task_type="image_edit",
            credits_used=3,
            request_image_count=5,
            success_image_count=4
        )
        await credits_usage_service.log_usage(
            openid="test_openid_7",
            task_id="test_task_7_2",
            task_type="image_edit",
            credits_used=5,
            request_image_count=8,
            success_image_count=7
        )
        await credits_usage_service.log_usage(
            openid="test_openid_7",
            task_id="test_task_7_3",
            task_type="batch_classify",
            credits_used=2,
            request_image_count=3,
            success_image_count=3
        )
        
        # 查询累计额度
        total = await credits_usage_service.get_total_credits_used("test_openid_7")
        assert total == 10  # 3 + 5 + 2
    
    @pytest.mark.asyncio
    async def test_get_total_credits_used_empty(self, cleanup):
        """测试查询用户累计消耗的额度总数（无记录）"""
        total = await credits_usage_service.get_total_credits_used("test_openid_nonexist")
        assert total == 0
    
    @pytest.mark.asyncio
    async def test_get_total_credits_used_empty_openid(self, cleanup):
        """测试查询用户累计消耗的额度总数（openid 为空）"""
        total = await credits_usage_service.get_total_credits_used("")
        assert total == 0

