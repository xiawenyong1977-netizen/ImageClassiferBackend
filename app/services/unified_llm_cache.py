"""
统一大模型推理缓存服务（v2版本）
支持分类服务和编辑服务
支持多模型结果集合
"""

import hashlib
import json
from typing import Optional, List, Dict, Union, TYPE_CHECKING
from datetime import datetime
from app.database import db
from loguru import logger

if TYPE_CHECKING:
    from app.services.llm.base_service import LLMError


class UnifiedLLMCacheService:
    """统一大模型推理缓存服务（v2版本）"""
    
    def _generate_prompt_hash(self, prompt: str) -> str:
        """
        计算提示词SHA-256哈希
        
        Args:
            prompt: 提示词（分类服务：纯prompt；编辑服务：edit_type:prompt）
        
        Returns:
            提示词哈希（64字符）
        """
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    
    def _generate_model_key(
        self,
        provider: str,
        model_id: str,
        model_version: Optional[str] = None
    ) -> str:
        """
        生成模型标识Key
        
        Args:
            provider: 提供商（如 "aliyun"）
            model_id: 模型ID（如 "qwen-vl-plus"）
            model_version: 可选的模型版本
        
        Returns:
            模型key（格式: "provider:model_id" 或 "provider:model_id:version"）
        """
        if model_version:
            return f"{provider}:{model_id}:{model_version}"
        return f"{provider}:{model_id}"
    
    async def get_cached_result(
        self,
        prompt: str,
        image_hash: str,
        model_key: Optional[str] = None
    ) -> Optional[dict]:
        """
        查询单个缓存结果
        
        Args:
            prompt: 提示词（业务层传入完整prompt，服务层计算hash）
            image_hash: 图像SHA-256哈希
            model_key: 可选的模型key（如果指定，只返回该模型的结果；否则返回所有模型结果）
        
        Returns:
            如果指定model_key，返回该模型的结果dict：
            {
                "result": {...},  # 分类结果dict或编辑结果URL字符串
                "service_type": "classification" | "image_edit",
                "created_at": "...",
                "status": "success",
                ...
            }
            
            如果未指定model_key，返回所有模型的结果dict：
            {
                "aliyun:qwen-vl-plus": {...},
                "aliyun:qwen-image-edit": {...},
                ...
            }
            
            未找到返回 None
        """
        try:
            logger.info(f"[unified_llm_cache] get_cached_result方法开始: prompt长度={len(prompt)}, image_hash={image_hash[:16]}...")
            prompt_hash = self._generate_prompt_hash(prompt)
            logger.info(f"[unified_llm_cache] prompt_hash计算完成: {prompt_hash[:16]}...")
            logger.info(f"[unified_llm_cache] 开始查询缓存: prompt_hash={prompt_hash[:16]}..., image_hash={image_hash[:16]}...")
            
            logger.info(f"[unified_llm_cache] 准备获取数据库连接...")
            async with db.get_cursor() as cursor:
                logger.info(f"[unified_llm_cache] 已获取数据库连接，开始执行查询")
                sql = """
                SELECT model_results, hit_count
                FROM llm_inference_cache_v2
                WHERE prompt_hash = %s AND image_hash = %s
                """
                await cursor.execute(sql, (prompt_hash, image_hash))
                logger.info(f"[unified_llm_cache] 查询执行完成，开始获取结果")
                row = await cursor.fetchone()
                logger.info(f"[unified_llm_cache] 结果获取完成: found={row is not None}")
                
                if not row:
                    logger.debug(f"缓存未命中: prompt_hash={prompt_hash[:16]}..., image_hash={image_hash[:16]}...")
                    return None
                
                # 解析JSON
                model_results = json.loads(row['model_results'])
                
                # 更新命中次数（复用当前游标，避免嵌套连接）
                logger.info(f"[unified_llm_cache] 准备更新命中次数...")
                await self._increment_hit_count(prompt_hash, image_hash, cursor=cursor)
                logger.info(f"[unified_llm_cache] 命中次数更新完成")
                
                # 如果指定了模型Key，只返回该模型的结果
                if model_key:
                    result = model_results.get(model_key)
                    if result:
                        logger.debug(f"缓存命中: prompt_hash={prompt_hash[:16]}..., image_hash={image_hash[:16]}..., model={model_key}")
                    return result
                
                # 返回所有模型的结果
                logger.debug(f"缓存命中: prompt_hash={prompt_hash[:16]}..., image_hash={image_hash[:16]}..., models={list(model_results.keys())}")
                return model_results
                
        except Exception as e:
            logger.error(f"查询缓存失败: {e}")
            return None
    
    async def batch_get_cached_results(
        self,
        prompt: str,
        image_hashes: List[str],
        model_key: Optional[str] = None
    ) -> Dict[str, dict]:
        """
        批量查询缓存结果
        
        Args:
            prompt: 提示词
            image_hashes: 图像哈希列表
            model_key: 可选的模型key
        
        Returns:
            {image_hash: cached_result} 字典
            如果某个image_hash没有缓存，则不在字典中
        """
        if not image_hashes:
            return {}
        
        try:
            prompt_hash = self._generate_prompt_hash(prompt)
            
            # 构建IN查询
            placeholders = ','.join(['%s'] * len(image_hashes))
            
            async with db.get_cursor() as cursor:
                sql = f"""
                SELECT image_hash, model_results
                FROM llm_inference_cache_v2
                WHERE prompt_hash = %s AND image_hash IN ({placeholders})
                """
                await cursor.execute(sql, [prompt_hash] + image_hashes)
                rows = await cursor.fetchall()
                
                # 构建结果字典
                results = {}
                for row in rows:
                    image_hash = row['image_hash']
                    model_results = json.loads(row['model_results'])
                    
                    # 如果指定了模型Key，只返回该模型结果
                    if model_key:
                        if model_key in model_results:
                            results[image_hash] = model_results[model_key]
                    else:
                        # 返回所有模型结果
                        results[image_hash] = model_results
                
                # 批量更新命中次数
                if results:
                    await self._batch_increment_hit_count(prompt_hash, list(results.keys()))
                
                logger.debug(f"批量缓存查询: prompt_hash={prompt_hash[:16]}..., 查询={len(image_hashes)}, 命中={len(results)}")
                return results
                
        except Exception as e:
            logger.error(f"批量查询缓存失败: {e}")
            return {}
    
    async def save_result(
        self,
        prompt: str,
        image_hash: str,
        provider: str,
        model_id: str,
        result: Union[dict, str],
        model_version: Optional[str] = None,
        service_type: Optional[str] = None,
        edit_type: Optional[str] = None,
        is_default_prompt: Optional[bool] = None,
        **extra_fields
    ) -> bool:
        """
        保存推理结果到缓存
        
        Args:
            prompt: 提示词
            image_hash: 图像哈希
            provider: 提供商
            model_id: 模型ID
            result: 推理结果（分类服务：dict；编辑服务：URL字符串）
            model_version: 模型版本
            service_type: 业务类型（可选，用于统计）
            edit_type: 编辑类型（可选，仅编辑服务）
            is_default_prompt: 是否使用默认prompt（用于判断是否需要解析JSON）
            **extra_fields: 扩展字段
        
        Returns:
            是否保存成功
        """
        try:
            prompt_hash = self._generate_prompt_hash(prompt)
            model_key = self._generate_model_key(provider, model_id, model_version)
            
            # 构建模型结果数据
            model_result_data = {
                "result": result,
                "created_at": datetime.now().isoformat(),
                "status": "success",
                **extra_fields
            }
            
            # 可选：添加业务元数据（用于统计和查询）
            if service_type:
                model_result_data["service_type"] = service_type
            if edit_type:
                model_result_data["edit_type"] = edit_type
            if is_default_prompt is not None:
                model_result_data["is_default_prompt"] = is_default_prompt
            
            model_result_json = json.dumps(model_result_data, ensure_ascii=False)
            
            async with db.get_cursor() as cursor:
                # 先检查记录是否存在
                await cursor.execute("""
                    SELECT model_results FROM llm_inference_cache_v2
                    WHERE prompt_hash = %s AND image_hash = %s
                """, (prompt_hash, image_hash))
                existing = await cursor.fetchone()
                
                if existing:
                    # 记录已存在，更新JSON字段
                    existing_results = json.loads(existing['model_results'])
                    existing_results[model_key] = model_result_data
                    updated_results = json.dumps(existing_results, ensure_ascii=False)
                    total_models = len(existing_results)
                    
                    await cursor.execute("""
                        UPDATE llm_inference_cache_v2
                        SET 
                            model_results = %s,
                            total_models = %s,
                            updated_at = NOW()
                        WHERE prompt_hash = %s AND image_hash = %s
                    """, (updated_results, total_models, prompt_hash, image_hash))
                else:
                    # 记录不存在，插入新记录
                    initial_model_results = {model_key: model_result_data}
                    await cursor.execute("""
                        INSERT INTO llm_inference_cache_v2 
                        (prompt_hash, image_hash, model_results, total_models, hit_count)
                        VALUES (%s, %s, %s, 1, 1)
                    """, (
                        prompt_hash,
                        image_hash,
                        json.dumps(initial_model_results, ensure_ascii=False)
                    ))
                
                logger.info(f"缓存已保存: prompt_hash={prompt_hash[:16]}..., image_hash={image_hash[:16]}..., model={model_key}")
                return True
                
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
            return False
    
    async def save_error_result(
        self,
        prompt: str,
        image_hash: str,
        provider: str,
        model_id: str,
        error: "LLMError",  # 使用字符串引用避免循环导入
        model_version: Optional[str] = None,
        service_type: Optional[str] = None,
        edit_type: Optional[str] = None,
        **extra_fields
    ) -> bool:
        """
        保存错误结果到缓存（仅用于输入错误等需要缓存的错误）
        
        Args:
            prompt: 提示词
            image_hash: 图像哈希
            provider: 提供商
            model_id: 模型ID
            error: LLMError对象
            model_version: 模型版本
            service_type: 业务类型（可选，用于统计）
            edit_type: 编辑类型（可选，仅编辑服务）
            **extra_fields: 扩展字段
        
        Returns:
            是否保存成功
        """
        try:
            prompt_hash = self._generate_prompt_hash(prompt)
            model_key = self._generate_model_key(provider, model_id, model_version)
            
            # 构建错误结果数据
            model_result_data = {
                "result": None,  # 错误结果
                "error": {
                    "type": error.error_type.value,
                    "message": error.message,
                    "user_message": error.user_message,
                    "status_code": error.status_code,
                    "error_code": error.error_code
                },
                "status": "error",
                "created_at": datetime.now().isoformat(),
                **extra_fields
            }
            
            # 可选：添加业务元数据
            if service_type:
                model_result_data["service_type"] = service_type
            if edit_type:
                model_result_data["edit_type"] = edit_type
            
            model_result_json = json.dumps(model_result_data, ensure_ascii=False)
            
            async with db.get_cursor() as cursor:
                # 先检查记录是否存在
                await cursor.execute("""
                    SELECT model_results FROM llm_inference_cache_v2
                    WHERE prompt_hash = %s AND image_hash = %s
                """, (prompt_hash, image_hash))
                existing = await cursor.fetchone()
                
                if existing:
                    # 记录已存在，更新JSON字段
                    existing_results = json.loads(existing['model_results'])
                    existing_results[model_key] = model_result_data
                    updated_results = json.dumps(existing_results, ensure_ascii=False)
                    total_models = len(existing_results)
                    
                    await cursor.execute("""
                        UPDATE llm_inference_cache_v2
                        SET 
                            model_results = %s,
                            total_models = %s,
                            updated_at = NOW()
                        WHERE prompt_hash = %s AND image_hash = %s
                    """, (updated_results, total_models, prompt_hash, image_hash))
                else:
                    # 记录不存在，插入新记录
                    initial_model_results = {model_key: model_result_data}
                    await cursor.execute("""
                        INSERT INTO llm_inference_cache_v2 
                        (prompt_hash, image_hash, model_results, total_models, hit_count)
                        VALUES (%s, %s, %s, 1, 1)
                    """, (
                        prompt_hash,
                        image_hash,
                        json.dumps(initial_model_results, ensure_ascii=False)
                    ))
                
                logger.info(
                    f"错误结果已缓存: prompt_hash={prompt_hash[:16]}..., "
                    f"image_hash={image_hash[:16]}..., model={model_key}, "
                    f"error_type={error.error_type.value}"
                )
                return True
                
        except Exception as e:
            logger.error(f"保存错误缓存失败: {e}")
            return False
    
    async def get_available_models(
        self,
        prompt: str,
        image_hash: str
    ) -> List[str]:
        """
        获取已缓存的模型列表
        
        Args:
            prompt: 提示词
            image_hash: 图像哈希
        
        Returns:
            模型key列表，如 ["aliyun:qwen-vl-plus", "openai:gpt-4-vision"]
        """
        try:
            prompt_hash = self._generate_prompt_hash(prompt)
            
            async with db.get_cursor() as cursor:
                sql = """
                SELECT JSON_KEYS(model_results) as model_keys
                FROM llm_inference_cache_v2
                WHERE prompt_hash = %s AND image_hash = %s
                """
                await cursor.execute(sql, (prompt_hash, image_hash))
                row = await cursor.fetchone()
                
                if not row or not row['model_keys']:
                    return []
                
                # MySQL返回的是JSON数组字符串，需要解析
                model_keys_json = row['model_keys']
                if model_keys_json:
                    return json.loads(model_keys_json)
                return []
                
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
    
    async def _increment_hit_count(self, prompt_hash: str, image_hash: str, cursor=None) -> bool:
        """
        增加命中次数
        
        Args:
            prompt_hash: 提示词哈希
            image_hash: 图片哈希
            cursor: 可选的数据库游标（如果提供，复用已有游标；否则创建新连接）
        """
        try:
            if cursor is not None:
                # 复用已有的游标（避免嵌套连接）
                logger.info(f"[unified_llm_cache] 使用已有游标更新命中次数...")
                sql = """
                UPDATE llm_inference_cache_v2
                SET 
                    hit_count = hit_count + 1,
                    last_hit_at = NOW()
                WHERE prompt_hash = %s AND image_hash = %s
                """
                await cursor.execute(sql, (prompt_hash, image_hash))
                logger.info(f"[unified_llm_cache] 使用已有游标更新命中次数完成")
                return True
            else:
                # 创建新的连接
                logger.info(f"[unified_llm_cache] 创建新连接更新命中次数...")
                async with db.get_cursor() as new_cursor:
                    sql = """
                    UPDATE llm_inference_cache_v2
                    SET 
                        hit_count = hit_count + 1,
                        last_hit_at = NOW()
                    WHERE prompt_hash = %s AND image_hash = %s
                    """
                    await new_cursor.execute(sql, (prompt_hash, image_hash))
                    logger.info(f"[unified_llm_cache] 使用新连接更新命中次数完成")
                    return True
        except Exception as e:
            logger.error(f"更新命中次数失败: {e}")
            return False
    
    async def _batch_increment_hit_count(
        self,
        prompt_hash: str,
        image_hashes: List[str]
    ) -> bool:
        """批量增加命中次数"""
        if not image_hashes:
            return True
        
        try:
            placeholders = ','.join(['%s'] * len(image_hashes))
            
            async with db.get_cursor() as cursor:
                sql = f"""
                UPDATE llm_inference_cache_v2
                SET 
                    hit_count = hit_count + 1,
                    last_hit_at = NOW()
                WHERE prompt_hash = %s AND image_hash IN ({placeholders})
                """
                await cursor.execute(sql, [prompt_hash] + image_hashes)
                return True
        except Exception as e:
            logger.error(f"批量更新命中次数失败: {e}")
            return False


# 全局缓存服务实例
unified_llm_cache = UnifiedLLMCacheService()

