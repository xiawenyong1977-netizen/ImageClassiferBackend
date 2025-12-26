"""
统一大模型推理缓存服务（v2版本）测试
"""

import pytest
import hashlib
from app.services.unified_llm_cache import unified_llm_cache
from app.config import settings


class TestUnifiedLLMCacheService:
    """统一缓存服务测试类"""
    
    @pytest.fixture(autouse=True)
    async def setup(self, setup_test_db):
        """每个测试前确保数据库已初始化"""
        # setup_test_db fixture 会自动初始化数据库
        # 如果数据库不可用，setup_test_db会抛出skip异常
        pass
    
    def test_generate_prompt_hash(self):
        """测试提示词哈希生成"""
        prompt = "test prompt"
        hash1 = unified_llm_cache._generate_prompt_hash(prompt)
        hash2 = unified_llm_cache._generate_prompt_hash(prompt)
        
        # 相同prompt应该生成相同hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 哈希是64字符
        
        # 不同prompt应该生成不同hash
        hash3 = unified_llm_cache._generate_prompt_hash("different prompt")
        assert hash1 != hash3
    
    def test_generate_model_key(self):
        """测试模型key生成"""
        # 不带版本
        key1 = unified_llm_cache._generate_model_key("aliyun", "qwen-vl-plus")
        assert key1 == "aliyun:qwen-vl-plus"
        
        # 带版本
        key2 = unified_llm_cache._generate_model_key("aliyun", "qwen-vl-plus", "v2.0")
        assert key2 == "aliyun:qwen-vl-plus:v2.0"
    
    @pytest.mark.asyncio
    async def test_save_and_get_classification_result(self):
        """测试保存和查询分类服务结果"""
        # 使用分类服务的prompt
        prompt = settings.CLASSIFICATION_PROMPT
        image_hash = hashlib.sha256(b"test_image_data").hexdigest()
        
        # 准备分类结果
        classification_result = {
            "category": "social_activities",
            "confidence": 0.95,
            "description": "多人聚会场景",
            "background_color": "蓝色"
        }
        
        # 保存结果
        success = await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result=classification_result,
            service_type="classification",
            cost=0.01,
            processing_time_ms=1200
        )
        assert success is True
        
        # 查询结果（不指定模型）
        cached = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash
        )
        assert cached is not None
        assert "aliyun:qwen-vl-plus" in cached
        
        model_result = cached["aliyun:qwen-vl-plus"]
        assert model_result["result"] == classification_result
        assert model_result["service_type"] == "classification"
        assert model_result["status"] == "success"
        assert model_result["cost"] == 0.01
        assert model_result["processing_time_ms"] == 1200
        
        # 查询结果（指定模型）
        cached_specific = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash,
            model_key="aliyun:qwen-vl-plus"
        )
        assert cached_specific is not None
        assert cached_specific["result"] == classification_result
    
    @pytest.mark.asyncio
    async def test_save_and_get_image_edit_result(self):
        """测试保存和查询编辑服务结果"""
        # 编辑服务的prompt格式：edit_type:user_prompt
        edit_type = "remove"
        user_prompt = "移除背景中的物体"
        prompt = f"{edit_type}:{user_prompt}"
        image_hash = hashlib.sha256(b"test_edit_image_data").hexdigest()
        
        # 编辑服务的结果是URL字符串
        result_url = "https://example.com/images/edited/xxx.png"
        
        # 保存结果
        success = await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-image-edit",
            result=result_url,
            service_type="image_edit",
            edit_type=edit_type,
            cost=0.01,
            processing_time_ms=2000
        )
        assert success is True
        
        # 查询结果
        cached = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash,
            model_key="aliyun:qwen-image-edit"
        )
        assert cached is not None
        assert cached["result"] == result_url
        assert cached["service_type"] == "image_edit"
        assert cached["edit_type"] == edit_type
        assert cached["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_multiple_models_same_prompt_image(self):
        """测试同一prompt+image可以存储多个模型的结果"""
        prompt = settings.CLASSIFICATION_PROMPT
        image_hash = hashlib.sha256(b"test_multi_model_image").hexdigest()
        
        # 保存第一个模型的结果
        result1 = {
            "category": "pets",
            "confidence": 0.92,
            "description": "可爱的小猫",
            "background_color": "白色"
        }
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result=result1,
            service_type="classification"
        )
        
        # 保存第二个模型的结果（不同模型）
        result2 = {
            "category": "pets",
            "confidence": 0.88,
            "description": "小猫照片",
            "background_color": "白色"
        }
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="openai",
            model_id="gpt-4-vision",
            result=result2,
            service_type="classification"
        )
        
        # 查询所有模型结果
        all_results = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash
        )
        assert all_results is not None
        assert "aliyun:qwen-vl-plus" in all_results
        assert "openai:gpt-4-vision" in all_results
        assert all_results["aliyun:qwen-vl-plus"]["result"] == result1
        assert all_results["openai:gpt-4-vision"]["result"] == result2
        
        # 查询特定模型结果
        model1_result = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash,
            model_key="aliyun:qwen-vl-plus"
        )
        assert model1_result["result"] == result1
        
        model2_result = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash,
            model_key="openai:gpt-4-vision"
        )
        assert model2_result["result"] == result2
    
    @pytest.mark.asyncio
    async def test_batch_get_cached_results(self):
        """测试批量查询缓存"""
        prompt = settings.CLASSIFICATION_PROMPT
        
        # 准备多个图像哈希
        image_hash1 = hashlib.sha256(b"batch_image_1").hexdigest()
        image_hash2 = hashlib.sha256(b"batch_image_2").hexdigest()
        image_hash3 = hashlib.sha256(b"batch_image_3").hexdigest()  # 不保存，用于测试未命中
        
        # 保存前两个的结果
        result1 = {
            "category": "foods",
            "confidence": 0.90,
            "description": "美食照片",
            "background_color": "橙色"
        }
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash1,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result=result1,
            service_type="classification"
        )
        
        result2 = {
            "category": "travel_scenery",
            "confidence": 0.93,
            "description": "旅行风景",
            "background_color": "蓝色"
        }
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash2,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result=result2,
            service_type="classification"
        )
        
        # 批量查询
        image_hashes = [image_hash1, image_hash2, image_hash3]
        batch_results = await unified_llm_cache.batch_get_cached_results(
            prompt=prompt,
            image_hashes=image_hashes,
            model_key="aliyun:qwen-vl-plus"
        )
        
        # 应该只返回有缓存的两个
        assert len(batch_results) == 2
        assert image_hash1 in batch_results
        assert image_hash2 in batch_results
        assert image_hash3 not in batch_results
        
        assert batch_results[image_hash1]["result"] == result1
        assert batch_results[image_hash2]["result"] == result2
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_cache(self):
        """测试查询不存在的缓存"""
        prompt = settings.CLASSIFICATION_PROMPT
        image_hash = hashlib.sha256(b"nonexistent_image").hexdigest()
        
        # 查询不存在的缓存
        result = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash
        )
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_available_models(self):
        """测试获取已缓存的模型列表"""
        prompt = settings.CLASSIFICATION_PROMPT
        image_hash = hashlib.sha256(b"test_models_list").hexdigest()
        
        # 保存多个模型的结果
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result={"category": "other", "confidence": 0.5},
            service_type="classification"
        )
        
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="openai",
            model_id="gpt-4-vision",
            result={"category": "other", "confidence": 0.5},
            service_type="classification"
        )
        
        # 获取模型列表
        models = await unified_llm_cache.get_available_models(
            prompt=prompt,
            image_hash=image_hash
        )
        
        assert len(models) == 2
        assert "aliyun:qwen-vl-plus" in models
        assert "openai:gpt-4-vision" in models
    
    @pytest.mark.asyncio
    async def test_hit_count_increment(self):
        """测试命中次数增加"""
        prompt = settings.CLASSIFICATION_PROMPT
        image_hash = hashlib.sha256(b"test_hit_count").hexdigest()
        
        # 保存结果
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result={"category": "other", "confidence": 0.5},
            service_type="classification"
        )
        
        # 第一次查询（保存时已经计数1次）
        result1 = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash
        )
        assert result1 is not None
        
        # 再次查询（应该增加命中次数）
        result2 = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash
        )
        assert result2 is not None
        
        # 命中次数应该增加（通过数据库查询验证）
        from app.database import db
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT hit_count
                FROM llm_inference_cache_v2
                WHERE prompt_hash = %s AND image_hash = %s
            """, (unified_llm_cache._generate_prompt_hash(prompt), image_hash))
            row = await cursor.fetchone()
            # 保存时1次，查询2次，至少应该是3次
            assert row['hit_count'] >= 3
    
    @pytest.mark.asyncio
    async def test_different_prompts_same_image(self):
        """测试相同图像不同prompt应该有不同的缓存"""
        image_hash = hashlib.sha256(b"same_image_different_prompt").hexdigest()
        
        # 分类服务的prompt
        classification_prompt = settings.CLASSIFICATION_PROMPT
        classification_result = {
            "category": "pets",
            "confidence": 0.9,
            "description": "宠物照片",
            "background_color": "白色"
        }
        await unified_llm_cache.save_result(
            prompt=classification_prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result=classification_result,
            service_type="classification"
        )
        
        # 编辑服务的prompt（不同prompt）
        edit_prompt = "remove:移除背景"
        edit_result = "https://example.com/edited.png"
        await unified_llm_cache.save_result(
            prompt=edit_prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-image-edit",
            result=edit_result,
            service_type="image_edit",
            edit_type="remove"
        )
        
        # 查询分类结果
        classification_cached = await unified_llm_cache.get_cached_result(
            prompt=classification_prompt,
            image_hash=image_hash,
            model_key="aliyun:qwen-vl-plus"
        )
        assert classification_cached is not None
        assert classification_cached["result"] == classification_result
        
        # 查询编辑结果
        edit_cached = await unified_llm_cache.get_cached_result(
            prompt=edit_prompt,
            image_hash=image_hash,
            model_key="aliyun:qwen-image-edit"
        )
        assert edit_cached is not None
        assert edit_cached["result"] == edit_result
    
    @pytest.mark.asyncio
    async def test_empty_batch_query(self):
        """测试空列表批量查询"""
        prompt = settings.CLASSIFICATION_PROMPT
        results = await unified_llm_cache.batch_get_cached_results(
            prompt=prompt,
            image_hashes=[]
        )
        assert results == {}
    
    @pytest.mark.asyncio
    async def test_extra_fields(self):
        """测试扩展字段"""
        prompt = settings.CLASSIFICATION_PROMPT
        image_hash = hashlib.sha256(b"test_extra_fields").hexdigest()
        
        # 保存带扩展字段的结果
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result={"category": "other", "confidence": 0.5},
            service_type="classification",
            cost=0.01,
            processing_time_ms=1200,
            raw_response="原始响应文本",
            custom_field="自定义字段值"
        )
        
        # 查询结果
        cached = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash,
            model_key="aliyun:qwen-vl-plus"
        )
        
        assert cached is not None
        assert cached["cost"] == 0.01
        assert cached["processing_time_ms"] == 1200
        assert cached["raw_response"] == "原始响应文本"
        assert cached["custom_field"] == "自定义字段值"

