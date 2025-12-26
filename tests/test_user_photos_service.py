"""
用户照片关系服务测试
"""

import pytest
import hashlib
from app.services.user_photos_service import user_photos_service
from app.database import db


class TestUserPhotosService:
    """用户照片关系服务测试类"""
    
    @pytest.fixture(autouse=True)
    async def setup(self, setup_test_db):
        """每个测试前确保数据库已初始化"""
        # setup_test_db fixture 会自动初始化数据库
        # 如果数据库不可用，setup_test_db会抛出skip异常
        pass
    
    @pytest.fixture
    async def cleanup(self):
        """测试后清理数据"""
        yield
        # 清理测试数据
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("DELETE FROM user_photos WHERE user_id LIKE 'test_%'")
                await cursor.execute("DELETE FROM wechat_qrcode_bindings WHERE client_id LIKE 'test_%'")
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_upsert_user_photo_insert_new(self, cleanup):
        """测试插入新用户照片记录"""
        user_id = "test_user_1"
        image_hash = hashlib.sha256(b"test_image_1").hexdigest()
        image_uri = "test://image1.jpg"
        
        # 插入新记录
        result = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            image_uri=image_uri
        )
        assert result is True
        
        # 验证记录已插入
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT user_id, image_hash, image_uri, classify_count, openid
                FROM user_photos
                WHERE user_id = %s AND image_hash = %s
            """, (user_id, image_hash))
            record = await cursor.fetchone()
            
            assert record is not None
            assert record['user_id'] == user_id
            assert record['image_hash'] == image_hash
            assert record['image_uri'] == image_uri
            assert record['classify_count'] == 1
            assert record['openid'] is None
    
    @pytest.mark.asyncio
    async def test_upsert_user_photo_update_existing(self, cleanup):
        """测试更新已存在的用户照片记录（classify_count 增加）"""
        user_id = "test_user_2"
        image_hash = hashlib.sha256(b"test_image_2").hexdigest()
        image_uri = "test://image2.jpg"
        
        # 第一次插入
        result1 = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            image_uri=image_uri
        )
        assert result1 is True
        
        # 第二次更新（应该增加 classify_count）
        result2 = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            image_uri=image_uri
        )
        assert result2 is True
        
        # 验证 classify_count 已增加
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT classify_count
                FROM user_photos
                WHERE user_id = %s AND image_hash = %s
            """, (user_id, image_hash))
            record = await cursor.fetchone()
            
            assert record is not None
            assert record['classify_count'] == 2
    
    @pytest.mark.asyncio
    async def test_upsert_user_photo_with_openid(self, cleanup):
        """测试直接提供 openid"""
        user_id = "test_user_3"
        image_hash = hashlib.sha256(b"test_image_3").hexdigest()
        openid = "test_openid_123"
        
        result = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            openid=openid
        )
        assert result is True
        
        # 验证 openid 已保存
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT openid
                FROM user_photos
                WHERE user_id = %s AND image_hash = %s
            """, (user_id, image_hash))
            record = await cursor.fetchone()
            
            assert record is not None
            assert record['openid'] == openid
    
    @pytest.mark.asyncio
    async def test_upsert_user_photo_resolve_openid_from_binding(self, cleanup):
        """测试从绑定表查询 openid"""
        user_id = "test_user_4"
        image_hash = hashlib.sha256(b"test_image_4").hexdigest()
        openid = "test_openid_456"
        
        # 先在绑定表中创建记录
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                INSERT INTO wechat_qrcode_bindings (client_id, scene_id, openid, status)
                VALUES (%s, %s, %s, 'completed')
            """, (user_id, f"scene_{user_id}", openid))
        
        # 不提供 openid，应该从绑定表查询
        result = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            openid=None
        )
        assert result is True
        
        # 验证 openid 已从绑定表查询并保存
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT openid
                FROM user_photos
                WHERE user_id = %s AND image_hash = %s
            """, (user_id, image_hash))
            record = await cursor.fetchone()
            
            assert record is not None
            assert record['openid'] == openid
    
    @pytest.mark.asyncio
    async def test_upsert_user_photo_update_image_uri(self, cleanup):
        """测试更新 image_uri"""
        user_id = "test_user_5"
        image_hash = hashlib.sha256(b"test_image_5").hexdigest()
        image_uri_old = "test://image5_old.jpg"
        image_uri_new = "test://image5_new.jpg"
        
        # 第一次插入，使用旧的 image_uri
        result1 = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            image_uri=image_uri_old
        )
        assert result1 is True
        
        # 第二次更新，使用新的 image_uri（如果提供）
        result2 = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            image_uri=image_uri_new
        )
        assert result2 is True
        
        # 验证 image_uri 已更新
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT image_uri
                FROM user_photos
                WHERE user_id = %s AND image_hash = %s
            """, (user_id, image_hash))
            record = await cursor.fetchone()
            
            assert record is not None
            assert record['image_uri'] == image_uri_new
    
    @pytest.mark.asyncio
    async def test_get_user_photos(self, cleanup):
        """测试获取用户照片列表"""
        user_id = "test_user_6"
        
        # 插入多条记录
        image_hashes = []
        for i in range(5):
            image_hash = hashlib.sha256(f"test_image_{i}".encode()).hexdigest()
            image_hashes.append(image_hash)
            await user_photos_service.upsert_user_photo(
                user_id=user_id,
                image_hash=image_hash,
                image_uri=f"test://image{i}.jpg"
            )
        
        # 获取所有照片
        photos = await user_photos_service.get_user_photos(user_id=user_id)
        assert len(photos) == 5
        
        # 验证返回的字段
        for photo in photos:
            assert 'image_hash' in photo
            assert 'image_uri' in photo
            assert 'classify_count' in photo
            assert 'first_seen_at' in photo
            assert 'last_seen_at' in photo
        
        # 验证按 last_seen_at DESC 排序（最新的在前）
        for i in range(len(photos) - 1):
            assert photos[i]['last_seen_at'] >= photos[i + 1]['last_seen_at']
    
    @pytest.mark.asyncio
    async def test_get_user_photos_with_limit(self, cleanup):
        """测试获取用户照片列表（带 limit）"""
        user_id = "test_user_7"
        
        # 插入多条记录
        for i in range(10):
            image_hash = hashlib.sha256(f"test_image_{i}".encode()).hexdigest()
            await user_photos_service.upsert_user_photo(
                user_id=user_id,
                image_hash=image_hash,
                image_uri=f"test://image{i}.jpg"
            )
        
        # 获取前3条
        photos = await user_photos_service.get_user_photos(user_id=user_id, limit=3)
        assert len(photos) == 3
    
    @pytest.mark.asyncio
    async def test_get_user_photos_with_offset(self, cleanup):
        """测试获取用户照片列表（带 offset）"""
        user_id = "test_user_8"
        
        # 插入多条记录
        for i in range(10):
            image_hash = hashlib.sha256(f"test_image_{i}".encode()).hexdigest()
            await user_photos_service.upsert_user_photo(
                user_id=user_id,
                image_hash=image_hash,
                image_uri=f"test://image{i}.jpg"
            )
        
        # 获取前5条
        photos1 = await user_photos_service.get_user_photos(user_id=user_id, limit=5, offset=0)
        assert len(photos1) == 5
        
        # 获取第6-10条
        photos2 = await user_photos_service.get_user_photos(user_id=user_id, limit=5, offset=5)
        assert len(photos2) == 5
        
        # 验证两条记录不重复
        hash_set1 = {p['image_hash'] for p in photos1}
        hash_set2 = {p['image_hash'] for p in photos2}
        assert hash_set1.isdisjoint(hash_set2)
    
    @pytest.mark.asyncio
    async def test_get_user_photos_empty(self, cleanup):
        """测试获取空用户的照片列表"""
        user_id = "test_user_nonexistent"
        
        photos = await user_photos_service.get_user_photos(user_id=user_id)
        # fetchall() 返回 tuple，需要检查长度
        assert len(photos) == 0
    
    @pytest.mark.asyncio
    async def test_get_user_photo_count(self, cleanup):
        """测试获取用户照片数量"""
        user_id = "test_user_9"
        
        # 插入多条记录
        for i in range(7):
            image_hash = hashlib.sha256(f"test_image_{i}".encode()).hexdigest()
            await user_photos_service.upsert_user_photo(
                user_id=user_id,
                image_hash=image_hash,
                image_uri=f"test://image{i}.jpg"
            )
        
        count = await user_photos_service.get_user_photo_count(user_id=user_id)
        assert count == 7
    
    @pytest.mark.asyncio
    async def test_get_user_photo_count_empty(self, cleanup):
        """测试获取空用户的照片数量"""
        user_id = "test_user_nonexistent_2"
        
        count = await user_photos_service.get_user_photo_count(user_id=user_id)
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_upsert_user_photo_openid_preserved(self, cleanup):
        """测试更新时 openid 不会被覆盖（如果已存在）"""
        user_id = "test_user_10"
        image_hash = hashlib.sha256(b"test_image_10").hexdigest()
        openid = "test_openid_789"
        
        # 第一次插入，提供 openid
        result1 = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            openid=openid
        )
        assert result1 is True
        
        # 第二次更新，不提供 openid（应该保留原有的）
        result2 = await user_photos_service.upsert_user_photo(
            user_id=user_id,
            image_hash=image_hash,
            openid=None
        )
        assert result2 is True
        
        # 验证 openid 仍然存在
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT openid
                FROM user_photos
                WHERE user_id = %s AND image_hash = %s
            """, (user_id, image_hash))
            record = await cursor.fetchone()
            
            assert record is not None
            assert record['openid'] == openid

