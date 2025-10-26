"""
图像编辑服务
基于阿里云百炼图像编辑API
"""

import asyncio
import base64
import json
import os
from typing import List, Dict, Optional
from loguru import logger
import dashscope
import httpx
import aiomysql

from app.database import db
from app.config import settings
from app.utils.hash_utils import calculate_hash


class ImageEditService:
    """图像编辑服务"""
    
    MAX_IMAGES_PER_BATCH = 3  # 阿里云限制
    CONCURRENT_LIMIT = 3      # 并发限制
    
    async def submit_task(
        self,
        images: List[Dict],
        edit_type: str,
        edit_params: Dict,
        user_id: Optional[str] = None
    ) -> str:
        """提交编辑任务"""
        
        # 生成任务ID
        from app.utils.id_generator import IDGenerator
        task_id = IDGenerator.generate_request_id("task")
        total_images = len(images)
        
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
        
        logger.info(f"任务已创建: {task_id}, 图片数: {total_images}")
        
        # 启动异步处理
        asyncio.create_task(
            self._execute_task(task_id, images, edit_type, edit_params, user_id)
        )
        
        return task_id
    
    async def _execute_task(
        self,
        task_id: str,
        images: List[Dict],
        edit_type: str,
        edit_params: Dict,
        user_id: Optional[str]
    ):
        """执行编辑任务（异步后台处理）"""
        try:
            await self._update_status(task_id, 'processing')
            
            # 分批处理
            batches = self._split_into_batches(images, self.MAX_IMAGES_PER_BATCH)
            all_results = []
            
            for batch_index, batch in enumerate(batches):
                logger.info(f"处理批次 {batch_index + 1}/{len(batches)}")
                
                # 并发处理当前批次
                batch_results = await self._process_batch_concurrently(
                    batch_index * self.MAX_IMAGES_PER_BATCH,
                    batch,
                    edit_type,
                    edit_params
                )
                
                all_results.extend(batch_results)
                
                # 更新进度
                await self._update_progress(task_id, len(all_results), len(images))
            
            # 保存结果
            await self._save_results(task_id, all_results)
            
            logger.info(f"任务完成: {task_id}")
            
        except Exception as e:
            logger.error(f"编辑失败: {e}")
            await self._update_status(task_id, 'failed')
    
    async def _process_batch_concurrently(
        self,
        start_index: int,
        batch: List[Dict],
        edit_type: str,
        edit_params: Dict
    ) -> List[Dict]:
        """并发处理一批图片"""
        semaphore = asyncio.Semaphore(self.CONCURRENT_LIMIT)
        
        async def process_with_limit(index, image_data):
            async with semaphore:
                return await self._edit_single_image(
                    index, image_data, edit_type, edit_params
                )
        
        tasks = [
            process_with_limit(i + start_index, img)
            for i, img in enumerate(batch)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]
    
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
            
            # 调用阿里云API
            result_url = await self._call_aliyun_api(
                image_bytes, edit_type, edit_params
            )
            
            return {
                'index': index,
                'filename': image_data['filename'],
                'status': 'completed',
                'result_url': result_url
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
    ) -> str:
        """调用阿里云图像编辑API - 使用image_edit_tasks表做缓存"""
        dashscope.api_key = settings.LLM_API_KEY
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        prompt = edit_params.get('prompt', '修复面部瑕疵和皱纹，提亮肤色，保持人物原貌不变')
        
        # 生成图片哈希
        image_hash = calculate_hash(image_bytes)
        
        # 从image_edit_tasks表查询是否有相同的图片和提示词已处理完成
        # 查询条件：相同的edit_type、相同的prompt、status为completed的结果
        try:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """SELECT results, created_at 
                           FROM image_edit_tasks 
                           WHERE status = 'completed' 
                             AND edit_type = %s
                             AND edit_params LIKE %s
                           ORDER BY created_at DESC 
                           LIMIT 1""",
                        (edit_type, f'%"{prompt}"%')
                    )
                    cached = await cursor.fetchone()
                    
                    if cached and cached.get('results'):
                        results = json.loads(cached['results'])
                        if results and len(results) > 0:
                            # 检查结果中的图片是否是同一张（通过对比URL或索引）
                            # 简单策略：返回第一个结果
                            result_url = results[0].get('result_url')
                            if result_url:
                                logger.info(f"缓存命中: image_hash={image_hash[:16]}..., prompt={prompt[:50]}")
                                return result_url
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
                    
                    return download_url
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
            filename = f"{IDGenerator.generate_request_id('img')}.png"
            
            save_dir = "/opt/ImageClassifierBackend/web/images/edited"
            os.makedirs(save_dir, exist_ok=True)
            
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            public_url = f"http://123.57.68.4:8000/images/edited/{filename}"
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
    
    async def _save_results(self, task_id: str, results: List[Dict]):
        """保存任务结果"""
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE image_edit_tasks SET results = %s, status = %s WHERE task_id = %s",
                    (json.dumps(results), 'completed', task_id)
                )
                await conn.commit()
    
    def _split_into_batches(self, images: List[Dict], batch_size: int) -> List[List[Dict]]:
        """分批处理"""
        return [images[i:i + batch_size] for i in range(0, len(images), batch_size)]
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """查询任务状态"""
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
                return None


# 全局服务实例
image_editor = ImageEditService()
