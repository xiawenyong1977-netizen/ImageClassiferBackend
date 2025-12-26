"""
通用异步任务服务
只负责数据库的读写操作，不包含业务逻辑
所有任务类型统一存储在一张表中
"""

from typing import Optional, List, Dict
import json
import aiomysql
from app.database import db
from app.models.schemas_v2 import TaskStatus
from loguru import logger


class AsyncTaskService:
    """通用异步任务服务（只负责数据库操作）"""
    
    def __init__(self, table_name: str = 'async_tasks'):
        """
        初始化异步任务服务
        
        Args:
            table_name: 任务表名（默认 'async_tasks'）
        """
        self.table_name = table_name
    
    async def create_task(
        self,
        task_id: str,
        task_type: str,
        total_items: int = 0,
        task_params: Optional[Dict] = None,
        user_id: Optional[str] = None,
        openid: Optional[str] = None
    ) -> None:
        """
        创建任务记录
        
        Args:
            task_id: 任务ID
            task_type: 任务类型（如 'image_edit', 'batch_classify'）
            total_items: 总项目数
            task_params: 任务参数（JSON格式）
            user_id: 用户ID（可选，用于统计）
            openid: 微信openid（可选，用于统计）
        """
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""INSERT INTO {self.table_name} 
                       (task_id, task_type, user_id, openid, total_items, task_params, status) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        task_id,
                        task_type,
                        user_id,
                        openid,
                        total_items,
                        json.dumps(task_params) if task_params else None,
                        TaskStatus.PENDING.value
                    )
                )
                await conn.commit()
    
    async def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        completed_items: Optional[int] = None,
        results: Optional[List[Dict]] = None
    ):
        """
        更新任务（统一更新接口，可同时更新多个字段）
        
        Args:
            task_id: 任务ID
            status: 任务状态（可选）
            completed_items: 已完成数量（可选）
            results: 结果列表（可选，JSON格式）
        """
        updates = []
        values = []
        
        if status is not None:
            updates.append("status = %s")
            values.append(status.value)
        
        if completed_items is not None:
            updates.append("completed_items = %s")
            values.append(completed_items)
        
        if results is not None:
            updates.append("results = %s")
            values.append(json.dumps(results))
        
        if not updates:
            return  # 没有需要更新的字段
        
        values.append(task_id)
        
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"UPDATE {self.table_name} SET {', '.join(updates)} WHERE task_id = %s",
                    values
                )
                await conn.commit()
    
    async def update_status(self, task_id: str, status: TaskStatus):
        """
        更新任务状态（便捷方法）
        
        Args:
            task_id: 任务ID
            status: 任务状态（TaskStatus枚举）
        """
        await self.update_task(task_id, status=status)
    
    async def update_progress(self, task_id: str, completed_items: int):
        """
        更新任务进度（便捷方法）
        
        Args:
            task_id: 任务ID
            completed_items: 已完成数量
        """
        await self.update_task(task_id, completed_items=completed_items)
    
    async def update_results_incremental(self, task_id: str, results: List[Dict]):
        """
        增量更新任务结果（便捷方法）
        
        Args:
            task_id: 任务ID
            results: 结果列表（JSON格式）
        """
        await self.update_task(task_id, results=results)
    
    async def save_results(
        self,
        task_id: str,
        results: List[Dict],
        completed_items: Optional[int] = None
    ):
        """
        保存任务结果（只负责数据库操作）
        
        Args:
            task_id: 任务ID
            results: 结果列表（JSON格式）
            completed_items: 已完成数量（如果不提供，自动计算）
        """
        if completed_items is None:
            completed_items = len([r for r in results if r and r.get('status') in ('completed', 'failed')])
        
        await self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            completed_items=completed_items,
            results=results
        )
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """查询任务状态"""
        try:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        f"SELECT * FROM {self.table_name} WHERE task_id = %s",
                        (task_id,)
                    )
                    result = await cursor.fetchone()
                    if result:
                        # 解析JSON字段
                        if result.get('task_params'):
                            result['task_params'] = json.loads(result['task_params'])
                        if result.get('results'):
                            result['results'] = json.loads(result['results'])
                        return result
                    logger.warning(f"任务不存在: {task_id}")
                    return None
        except Exception as e:
            logger.error(f"查询任务状态失败: {task_id}, 错误: {e}")
            return None


# 全局服务实例
async_task_service = AsyncTaskService()

