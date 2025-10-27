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


class ImageEditService:
    """图像编辑服务"""
    
    MAX_IMAGES_PER_BATCH = 9  # 最大图片数（虽然不会有批处理，但保留字段）
    CONCURRENT_LIMIT = 1      # 串行处理，避免触发阿里云频率限制
    
    async def submit_task(
        self,
        images: List[Dict],
        edit_type: str,
        edit_params: Dict,
        user_id: Optional[str] = None
    ) -> str:
        """提交编辑任务（同步处理，确保数据已写入数据库）"""
        
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
            await self._save_results(task_id, all_results)
            
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
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        prompt = edit_params.get('prompt', '修复面部瑕疵和皱纹，提亮肤色，保持人物原貌不变')
        
        # 生成图片哈希
        image_hash = calculate_hash(image_bytes)
        
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


# 全局服务实例
image_editor = ImageEditService()
