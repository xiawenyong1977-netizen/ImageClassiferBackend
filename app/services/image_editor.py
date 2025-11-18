"""
图像编辑服务
基于阿里云百炼图像编辑API
"""

import asyncio
import base64
import json
import os
from typing import List, Dict, Optional, Tuple
from loguru import logger
import dashscope
import httpx
import aiomysql

from app.database import db
from app.config import settings
from app.utils.hash_utils import calculate_hash
from app.services.credit_service import credit_service


class ImageEditService:
    """图像编辑服务"""
    
    MAX_IMAGES_PER_BATCH = 9  # 最大图片数（虽然不会有批处理，但保留字段）
    CONCURRENT_LIMIT = 1      # 串行处理，避免触发阿里云频率限制
    
    async def submit_task(
        self,
        images: List[Dict],
        edit_type: str,
        edit_params: Dict,
        user_id: Optional[str] = None,
        openid: Optional[str] = None
    ) -> str:
        """提交编辑任务（同步处理，确保数据已写入数据库）"""
        
        # 参数校验：必须提供edit_type和prompt，避免降级处理隐藏问题
        if not edit_type:
            raise ValueError("edit_type参数缺失")
        if not edit_params or 'prompt' not in edit_params:
            raise ValueError("edit_params中必须包含prompt参数")
        
        # 生成任务ID
        from app.utils.id_generator import IDGenerator
        task_id = IDGenerator.generate_request_id("task")
        total_images = len(images)
        
        # 检查用户额度（如果传入了openid）
        if openid:
            # 使用 credit_service 检查额度（会员和非会员都检查，会员有无限额度）
            has_credit, error_msg = await credit_service.check_and_deduct_credit(openid, deduct_on_success=False)
            if not has_credit:
                raise ValueError(error_msg)
        
        # 保存任务到数据库
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO image_edit_tasks 
                       (task_id, user_id, edit_type, edit_params, total_images, status) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (task_id, user_id, edit_type, 
                     json.dumps(edit_params), total_images, 'pending')
                )
                await conn.commit()
        
        logger.info(f"任务已创建并提交到数据库: {task_id}, 图片数: {total_images}")
        
        # 同步处理任务（不启动后台任务）
        try:
            await self._update_status(task_id, 'processing')
            
            # 串行处理每张图片
            all_results = []
            
            for index, image_data in enumerate(images):
                logger.info(f"处理第 {index + 1}/{len(images)} 张图片")
                
                # 处理单张图片
                result = await self._edit_single_image(
                    index, image_data, edit_type, edit_params
                )
                
                all_results.append(result)
                
                # 更新进度
                await self._update_progress(task_id, len(all_results), len(images))
            
            # 保存结果
            await self._save_results(task_id, all_results, openid)
            
            logger.info(f"任务同步处理完成: {task_id}")
            
        except Exception as e:
            logger.error(f"编辑失败: {e}")
            await self._update_status(task_id, 'failed')
        
        return task_id
    

    async def _edit_single_image(
        self,
        index: int,
        image_data: Dict,
        edit_type: str,
        edit_params: Dict
    ) -> Dict:
        """编辑单张图片"""
        try:
            # 直接使用内存中的原图数据
            image_bytes = image_data['bytes']
            
            # 调用阿里云API，返回 (result_url, from_cache)
            result_url, from_cache = await self._call_aliyun_api(
                image_bytes, edit_type, edit_params
            )
            
            return {
                'index': index,
                'filename': image_data['filename'],
                'status': 'completed',
                'result_url': result_url,
                'enhanced_uri': result_url,
                'from_cache': from_cache
            }
        except Exception as e:
            logger.error(f"图片 {index} 处理失败: {e}")
            return {
                'index': index,
                'filename': image_data.get('filename', ''),
                'status': 'failed',
                'error': str(e)
            }
    
    async def _call_aliyun_api(
        self,
        image_bytes: bytes,
        edit_type: str,
        edit_params: Dict
    ) -> Tuple[str, bool]:
        """调用阿里云图像编辑API - 使用image_edit_cache表做缓存
        
        Returns:
            tuple: (result_url, from_cache) - 结果URL和是否来自缓存
        """
        dashscope.api_key = settings.LLM_API_KEY
        
        # 先保留原始字节用于计算缓存哈希（避免压缩影响缓存命中）
        original_bytes = image_bytes
        
        # 确保单条 data-uri 大小不超过 10,485,760 字节（base64 膨胀约 4/3）
        try:
            from app.utils.image_utils import ImageUtils
            MAX_DATA_URI_BYTES = 10_485_760
            # 估算 base64 长度：约为原始字节 * 4 / 3
            def will_exceed(b: bytes) -> bool:
                approx_b64_len = int(len(b) * 4 / 3) + 64  # 预留前缀/行开销
                return approx_b64_len > MAX_DATA_URI_BYTES
            if will_exceed(image_bytes):
                # 以 7MB 为目标反复压缩一次（ImageUtils 内部会等比缩放+JPEG压缩）
                image_bytes = ImageUtils.compress_image(image_bytes, max_size_kb=7000)
                # 仍超出则再压至 5MB
                if will_exceed(image_bytes):
                    image_bytes = ImageUtils.compress_image(image_bytes, max_size_kb=5000)
        except Exception:
            # 压缩失败则按原图继续，后续由 API 报错
            pass

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        prompt = edit_params['prompt']  # 已经在submit_task中校验过，这里直接取
        logger.info(f"使用编辑提示词: '{prompt}'")
        
        # 生成图片哈希
        image_hash = calculate_hash(original_bytes)
        
        # 从image_edit_cache表查询缓存
        try:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """SELECT id, result_url 
                           FROM image_edit_cache 
                           WHERE image_hash = %s
                             AND edit_type = %s
                             AND prompt = %s
                           LIMIT 1""",
                        (image_hash, edit_type, prompt)
                    )
                    cached = await cursor.fetchone()
                    
                    if cached:
                        # 更新命中次数
                        await cursor.execute(
                            """UPDATE image_edit_cache 
                               SET hit_count = hit_count + 1,
                                   last_hit_at = NOW()
                               WHERE id = %s""",
                            (cached['id'],)
                        )
                        await conn.commit()
                        logger.info(f"缓存命中: image_hash={image_hash[:16]}..., prompt={prompt[:50]}")
                        return (cached['result_url'], True)  # 返回缓存结果
        except Exception as e:
            logger.warning(f"缓存查询失败，将继续调用API: {e}")
        
        # 缓存未命中，调用API
        payload = {
            "model": "qwen-image-edit",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": f"data:image/jpeg;base64,{image_base64}"},
                            {"text": prompt}
                        ]
                    }
                ]
            },
            "parameters": {
                "negative_prompt": "",
                "watermark": False
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.LLM_API_KEY}"
                },
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'choices' in result['output']:
                    result_url = result['output']['choices'][0]['message']['content'][0]['image']
                    logger.info(f"图片编辑成功，结果URL: {result_url}")
                    
                    # 下载并保存图片
                    download_url = await self._download_and_save_image(result_url)
                    
                    # 将结果写入缓存表
                    try:
                        async with db.get_connection() as conn:
                            async with conn.cursor() as cursor:
                                await cursor.execute(
                                    """INSERT INTO image_edit_cache 
                                       (image_hash, edit_type, prompt, result_url) 
                                       VALUES (%s, %s, %s, %s)
                                       ON DUPLICATE KEY UPDATE 
                                         result_url = VALUES(result_url),
                                         hit_count = hit_count,
                                         updated_at = NOW()""",
                                    (image_hash, edit_type, prompt, download_url)
                                )
                                await conn.commit()
                                logger.info(f"缓存已写入: image_hash={image_hash[:16]}...")
                    except Exception as e:
                        logger.warning(f"缓存写入失败: {e}")
                    
                    return (download_url, False)  # 返回API调用结果
                else:
                    raise Exception(f"API返回格式错误: {result}")
            else:
                error_info = response.json() if response.text else "未知错误"
                raise Exception(f"API调用失败: {error_info}")
    
    async def _download_and_save_image(self, url: str) -> str:
        """下载图片并保存到服务器"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                image_data = response.content
            
            from app.utils.id_generator import IDGenerator
            import os as os_module
            filename = f"{IDGenerator.generate_request_id('img')}.png"
            
            # 保存到app/images/edited目录（相对于app目录）
            app_dir = os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__)))
            save_dir = os_module.path.join(app_dir, "images", "edited")
            os_module.makedirs(save_dir, exist_ok=True)
            
            filepath = os_module.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # 使用配置的基础URL（新服务器域名）
            public_url = f"{settings.IMAGE_EDIT_BASE_URL}/images/edited/{filename}"
            logger.info(f"图片已保存: {filepath}, 公共URL: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return url
    
    async def _update_status(self, task_id: str, status: str):
        """更新任务状态"""
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE image_edit_tasks SET status = %s WHERE task_id = %s",
                    (status, task_id)
                )
                await conn.commit()
    
    async def _update_progress(self, task_id: str, completed: int, total: int):
        """更新任务进度"""
        progress = (completed / total) * 100 if total > 0 else 0
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE image_edit_tasks SET completed_images = %s, progress = %s WHERE task_id = %s",
                    (completed, progress, task_id)
                )
                await conn.commit()
    
    async def _update_results_incremental(self, task_id: str, results: List[Dict]):
        """增量更新任务结果（实时保存已完成的图片）"""
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE image_edit_tasks SET results = %s WHERE task_id = %s",
                    (json.dumps(results), task_id)
                )
                await conn.commit()
    
    async def _save_results(self, task_id: str, results: List[Dict], openid: Optional[str] = None):
        """保存任务结果并扣除用户额度
        注意：completed_images 表示已处理数量（成功或失败都计入），progress 同理。
        额度扣减仅按成功数量统计。
        """
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 保存任务结果，并确保完成数与进度准确（成功或失败都计为已处理）
                total_images = len(results)
                processed_count = len([r for r in results if r and r.get('status') in ('completed', 'failed')])
                success_count = len([r for r in results if r and r.get('status') == 'completed'])
                progress = (processed_count / total_images) * 100 if total_images > 0 else 0
                await cursor.execute(
                    "UPDATE image_edit_tasks SET results = %s, status = %s, completed_images = %s, progress = %s WHERE task_id = %s",
                    (json.dumps(results), 'completed', processed_count, progress, task_id)
                )
                
                # 如果传入了openid，扣除用户额度
                if openid:
                    # 统计请求与成功数量
                    total_images = len(results)
                    success_count = len([r for r in results if r and r.get('status') == 'completed'])
                    
                    # 统计缓存命中的数量（用于日志和扣减）
                    cache_count = len([r for r in results if r and r.get('status') == 'completed' and r.get('from_cache', False)])
                    api_count = success_count - cache_count
                    
                    # 只对API调用的成功数量进行扣减，缓存命中的不扣减
                    if api_count > 0:
                        # 使用 credit_service 扣减额度（会员和非会员都扣减）
                        for _ in range(api_count):
                            success, msg = await credit_service.check_and_deduct_credit(openid, deduct_on_success=True)
                            if not success:
                                logger.warning(f"扣减额度失败: {msg}")
                        
                        # 记录额度消耗（包含详细信息）
                        await cursor.execute(
                            """INSERT INTO credits_usage 
                               (openid, task_id, task_type, credits_used, request_image_count, success_image_count)
                               VALUES (%s, %s, 'image_edit', %s, %s, %s)""",
                            (openid, task_id, api_count, total_images, success_count)
                        )
                        
                        logger.info(f"已扣除额度: openid={openid[:16]}..., 扣除={api_count}张(总请求={total_images}张, 成功={success_count}, 缓存={cache_count}, API={api_count})")
                    elif cache_count > 0:
                        logger.info(f"缓存命中，不扣减额度: openid={openid[:16]}..., 成功={success_count}张全部来自缓存")
                
                await conn.commit()
    

    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """查询任务状态"""
        try:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT task_id, user_id, edit_type, edit_params, total_images, "
                        "completed_images, progress, status, results, created_at, updated_at "
                        "FROM image_edit_tasks WHERE task_id = %s",
                        (task_id,)
                    )
                    result = await cursor.fetchone()
                    if result:
                        if result.get('edit_params'):
                            result['edit_params'] = json.loads(result['edit_params'])
                        if result.get('results'):
                            result['results'] = json.loads(result['results'])
                        return result
                    logger.warning(f"任务不存在: {task_id}")
                    return None
        except Exception as e:
            logger.error(f"查询任务状态失败: {task_id}, 错误: {e}")
            return None
    
    async def submit_task_async(
        self,
        images: List[Dict],
        edit_type: str,
        edit_params: Dict,
        user_id: Optional[str] = None,
        openid: Optional[str] = None
    ) -> str:
        """提交编辑任务（异步处理，立即返回task_id）"""
        
        # 参数校验：必须提供edit_type和prompt，避免降级处理隐藏问题
        if not edit_type:
            raise ValueError("edit_type参数缺失")
        if not edit_params or 'prompt' not in edit_params:
            raise ValueError("edit_params中必须包含prompt参数")
        
        # 生成任务ID
        from app.utils.id_generator import IDGenerator
        task_id = IDGenerator.generate_request_id("task")
        total_images = len(images)
        
        # 保存任务到数据库（兼容未添加openid列的表结构）
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO image_edit_tasks 
                       (task_id, user_id, edit_type, edit_params, total_images, status) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (task_id, user_id, edit_type, 
                     json.dumps(edit_params), total_images, 'pending')
                )
                await conn.commit()
        
        logger.info(f"任务已创建: {task_id}, 图片数: {total_images}")
        
        # 异步处理任务（不阻塞）
        asyncio.create_task(self._process_task_async(task_id, images, edit_type, edit_params, openid))
        
        return task_id
    
    async def _process_task_async(
        self,
        task_id: str,
        images: List[Dict],
        edit_type: str,
        edit_params: Dict,
        openid: Optional[str] = None
    ):
        """异步处理任务（优化版：先批量检查缓存，缓存命中立即返回）"""
        try:
            await self._update_status(task_id, 'processing')
            
            # 1. 先批量检查所有图片的缓存
            logger.info(f"批量检查 {len(images)} 张图片的缓存...")
            cache_results = await self._batch_check_cache(images, edit_type, edit_params)
            
            # 2. 初始化结果数组（按原始顺序）
            all_results = [None] * len(images)
            cache_hit_count = 0
            
            for index, cache_result in enumerate(cache_results):
                if cache_result:
                    # 缓存命中，立即填充结果
                    all_results[index] = cache_result
                    cache_hit_count += 1
                    logger.info(f"图片 {index + 1}/{len(images)} 缓存命中")
            
            # 3. 如果有缓存命中的，立即更新结果（让客户端快速看到）
            if cache_hit_count > 0:
                # 填充缓存未命中的位置为pending状态
                for i in range(len(images)):
                    if all_results[i] is None:
                        all_results[i] = {
                            'index': i,
                            'filename': images[i].get('filename', ''),
                            'status': 'processing',
                            'result_url': None,
                            'enhanced_uri': None
                        }
                await self._update_results_incremental(task_id, all_results)
                logger.info(f"缓存命中 {cache_hit_count}/{len(images)} 张，已实时更新结果")
                # 即时更新进度，反映缓存命中的已完成数量
                await self._update_progress(task_id, cache_hit_count, len(images))
            
            # 4. 处理缓存未命中的图片（串行调用API）
            api_count = 0
            for index, image_data in enumerate(images):
                if all_results[index] and all_results[index].get('status') == 'completed':
                    # 已缓存命中，跳过
                    continue
                
                logger.info(f"处理第 {index + 1}/{len(images)} 张图片（API调用）")
                api_count += 1
                
                # 调用API处理
                result = await self._edit_single_image_api_call(
                    index, image_data, edit_type, edit_params
                )
                
                all_results[index] = result
                
                # 实时保存已完成的图片结果
                await self._update_results_incremental(task_id, all_results)
                
                # 更新进度：已处理数量（成功或失败都计入）
                processed = sum(1 for r in all_results if r and r.get('status') in ('completed', 'failed'))
                await self._update_progress(task_id, processed, len(images))
            
            logger.info(f"处理完成: 缓存命中={cache_hit_count}张, API调用={api_count}张")
            
            # 5. 最终保存结果并扣除额度
            await self._save_results(task_id, all_results, openid)
            
            logger.info(f"任务处理完成: {task_id}")
            
        except Exception as e:
            logger.error(f"任务处理失败: {task_id}, 错误: {e}")
            await self._update_status(task_id, 'failed')
    
    async def _batch_check_cache(self, images: List[Dict], edit_type: str, edit_params: Dict) -> List[Optional[Dict]]:
        """批量检查所有图片的缓存（一次性查询所有哈希）"""
        # 计算所有图片的哈希
        image_hashes = []
        image_filenames = {}
        for index, image_data in enumerate(images):
            image_bytes = image_data['bytes']
            image_hash = calculate_hash(image_bytes)
            image_hashes.append((image_hash, index))
            image_filenames[index] = image_data.get('filename', '')
        
        # 提取prompt参数用于缓存查询（已经在submit_task中校验过，这里直接取）
        prompt = edit_params['prompt']
        
        # 批量查询缓存
        cache_map = {}  # {image_hash: result_url}
        if image_hashes:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 构建IN查询（如果图片数量多，可以分批查询）
                    placeholders = ','.join(['%s'] * len(image_hashes))
                    hash_list = [h[0] for h in image_hashes]
                    
                    await cursor.execute(
                        f"""SELECT image_hash, result_url FROM image_edit_cache 
                           WHERE image_hash IN ({placeholders}) AND edit_type = %s AND prompt = %s""",
                        hash_list + [edit_type, prompt]
                    )
                    
                    for row in await cursor.fetchall():
                        cache_map[row['image_hash']] = row['result_url']
        
        # 构建结果列表（按原始顺序）
        cache_results = [None] * len(images)
        for image_hash, index in image_hashes:
            if image_hash in cache_map:
                cache_results[index] = {
                    'index': index,
                    'filename': image_filenames[index],
                    'status': 'completed',
                    'result_url': cache_map[image_hash],
                    'enhanced_uri': cache_map[image_hash],
                    'from_cache': True
                }
        
        return cache_results
    
    async def _edit_single_image_api_call(
        self,
        index: int,
        image_data: Dict,
        edit_type: str,
        edit_params: Dict
    ) -> Dict:
        """只调用API处理单张图片（不检查缓存，因为已经批量检查过了）"""
        try:
            image_bytes = image_data['bytes']
            
            # 直接调用API
            result_url, from_cache = await self._call_aliyun_api(
                image_bytes, edit_type, edit_params
            )
            
            return {
                'index': index,
                'filename': image_data.get('filename', ''),
                'status': 'completed',
                'result_url': result_url,
                'enhanced_uri': result_url,
                'from_cache': from_cache
            }
        except Exception as e:
            logger.error(f"图片 {index} 处理失败: {e}")
            return {
                'index': index,
                'filename': image_data.get('filename', ''),
                'status': 'failed',
                'error': str(e)
            }
    
    async def _edit_single_image_with_cache(
        self,
        index: int,
        image_data: Dict,
        edit_type: str,
        edit_params: Dict
    ) -> Dict:
        """编辑单张图片（带缓存检查）"""
        try:
            image_bytes = image_data['bytes']
            image_hash = calculate_hash(image_bytes)
            
            # 先查询缓存
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """SELECT result_url FROM image_edit_cache 
                           WHERE image_hash = %s AND edit_type = %s""",
                        (image_hash, edit_type)
                    )
                    cache = await cursor.fetchone()
                    
                    if cache:
                        logger.info(f"缓存命中: image_hash={image_hash[:16]}...")
                        return {
                            'index': index,
                            'filename': image_data['filename'],
                            'status': 'completed',
                            'result_url': cache['result_url'],
                            'from_cache': True
                        }
            
            # 缓存未命中，调用API
            result_url, from_cache = await self._call_aliyun_api(
                image_bytes, edit_type, edit_params
            )
            
            return {
                'index': index,
                'filename': image_data['filename'],
                'status': 'completed',
                'result_url': result_url,
                'from_cache': from_cache
            }
        except Exception as e:
            logger.error(f"图片 {index} 处理失败: {e}")
            return {
                'index': index,
                'filename': image_data.get('filename', ''),
                'status': 'failed',
                'error': str(e)
            }


# 全局服务实例
image_editor = ImageEditService()
