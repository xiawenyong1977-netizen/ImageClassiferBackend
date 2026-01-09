"""
统计服务
负责记录请求日志和查询统计数据
"""

from typing import Optional
from app.database import db
from loguru import logger
from app.config import settings


class StatsService:
    """统计服务类"""
    
    async def log_unified_request(
        self,
        request_id: str,
        request_type: str,
        ip_address: Optional[str] = None,
        client_id: Optional[str] = None,
        openid: Optional[str] = None,
        total_images: int = 0,
        cached_count: int = 0,
        llm_count: int = 0,
        local_count: int = 0
    ) -> bool:
        """
        统一的请求日志记录函数
        
        Args:
            request_id: 请求ID
            request_type: 请求类型 (single_classify/batch_classify/batch_cache/image_edit)
            ip_address: IP地址
            client_id: 客户端ID（user_id）
            openid: 微信openid
            total_images: 照片总数
            cached_count: 缓存命中数
            llm_count: 大模型处理数
            local_count: 本地处理数
            
        Returns:
            是否记录成功
        """
        if not settings.ENABLE_REQUEST_LOG:
            return True
        
        try:
            async with db.get_cursor() as cursor:
                # 如果 openid 为空但 client_id 不为空，尝试从绑定表查询 openid
                resolved_openid = openid
                if not resolved_openid and client_id:
                    try:
                        await cursor.execute("""
                            SELECT openid FROM wechat_qrcode_bindings 
                            WHERE client_id = %s AND openid IS NOT NULL 
                            LIMIT 1
                        """, (client_id,))
                        binding_result = await cursor.fetchone()
                        if binding_result:
                            resolved_openid = binding_result.get('openid')
                            logger.debug(f"通过 client_id={client_id} 查询到 openid={resolved_openid}")
                    except Exception as e:
                        logger.warning(f"查询 openid 失败 (client_id={client_id}): {e}")
                
                sql = """
                INSERT INTO unified_request_log (
                    request_id, request_type, ip_address, client_id, openid,
                    total_images, cached_count, llm_count, local_count, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                # 确保 cached_count 是整数类型
                cached_count = int(cached_count) if cached_count is not None else 0
                total_images = int(total_images) if total_images is not None else 0
                llm_count = int(llm_count) if llm_count is not None else 0
                local_count = int(local_count) if local_count is not None else 0
                
                # 不输出日志，由调用方的 log_stats 日志统一输出
                
                await cursor.execute(sql, (
                    request_id, request_type, ip_address, client_id, resolved_openid,
                    total_images, cached_count, llm_count, local_count
                ))
                logger.debug(f"统一请求日志已记录: {request_id} [{request_type}]")
                return True
                
        except Exception as e:
            logger.error(f"记录统一请求日志失败: {e}")
            return False
    
    async def log_request(
        self,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        image_hash: str,
        image_size: int,
        category: str,
        confidence: float,
        from_cache: bool,
        processing_time_ms: int,
        inference_method: str = "llm"
    ) -> bool:
        """
        记录请求日志
        
        Args:
            request_id: 请求ID
            user_id: 用户ID
            ip_address: IP地址
            image_hash: 图片哈希
            image_size: 图片大小
            category: 分类类别
            confidence: 置信度
            from_cache: 是否来自缓存
            processing_time_ms: 处理耗时
            inference_method: 推理方式(llm/local/llm_fallback/local_fallback)
            
        Returns:
            是否记录成功
        """
        if not settings.ENABLE_REQUEST_LOG:
            return True
        
        try:
            async with db.get_cursor() as cursor:
                # 显式设置 created_at 确保生成列正确计算
                # 使用 NOW() 确保日期有效，避免 '0000-00-00' 错误
                sql = """
                INSERT INTO request_log (
                    request_id, user_id, ip_address, image_hash, image_size,
                    category, confidence, from_cache, processing_time_ms, inference_method,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(NOW(), CURRENT_TIMESTAMP))
                """
                await cursor.execute(sql, (
                    request_id, user_id, ip_address, image_hash, image_size,
                    category, confidence, 1 if from_cache else 0, processing_time_ms, inference_method
                ))
                logger.debug(f"请求日志已记录: {request_id}")
                return True
                
        except Exception as e:
            # 如果是日期错误，尝试使用更明确的时间戳
            error_str = str(e)
            if "Incorrect date value" in error_str or "0000-00-00" in error_str:
                try:
                    from datetime import datetime
                    async with db.get_cursor() as cursor:
                        sql = """
                        INSERT INTO request_log (
                            request_id, user_id, ip_address, image_hash, image_size,
                            category, confidence, from_cache, processing_time_ms, inference_method,
                            created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        await cursor.execute(sql, (
                            request_id, user_id, ip_address, image_hash, image_size,
                            category, confidence, 1 if from_cache else 0, processing_time_ms, inference_method,
                            datetime.now()
                        ))
                        logger.debug(f"请求日志已记录（使用datetime）: {request_id}")
                        return True
                except Exception as retry_error:
                    logger.error(f"记录请求日志失败（重试后）: {retry_error}")
                    return False
            logger.error(f"记录请求日志失败: {e}")
            return False
    
    async def get_today_stats(self) -> dict:
        """
        获取今日统计（使用统一日志表）
        
        统计指标：
        1. 今日独立IP个数 - 从统一日志表统计
        2. 今日用户数 - 从统一日志表统计（client_id 或 openid）
        3. 今日图片分类的照片数（总数、缓存数、大模型推理数、本地推理数）
        4. 今日图像编辑的照片数（总数、缓存数、大模型处理数）
        
        Returns:
            今日统计数据
        """
        try:
            async with db.get_cursor() as cursor:
                # 使用统一日志表，一个查询搞定所有统计
                # 独立用户统计逻辑：
                # 1. 优先使用 openid（如果日志中已记录）
                # 2. 其次通过 wechat_qrcode_bindings 表将 client_id 映射到 openid
                # 3. 如果没有 openid 但有 client_id，使用 client_id
                # 4. 如果都没有，使用 ip_address 作为备选标识（匿名用户）
                await cursor.execute("""
                    SELECT 
                        -- 独立IP个数
                        COUNT(DISTINCT ip_address) as unique_ips,
                        
                        -- 用户数（优先使用 openid，其次 binding.openid，再 client_id，最后 ip_address）
                        COUNT(DISTINCT COALESCE(
                            log.openid,
                            binding.openid,
                            log.client_id,
                            log.ip_address
                        )) as unique_users,
                        
                        -- 图片分类统计（包括V1和V2版本：单个分类、批量分类、单个缓存查询、批量缓存查询）
                        SUM(CASE WHEN request_type IN ('single_classify', 'batch_classify', 'batch_classify_v2', 'single_cache', 'batch_cache', 'batch_cache_v2') THEN total_images ELSE 0 END) as classify_total,
                        -- 缓存命中数：包括分类请求中的缓存命中 + 缓存查询请求中的缓存命中
                        -- 注意：batch_cache 和 single_cache 的 cached_count 必须被统计
                        SUM(CASE 
                            WHEN request_type IN ('single_classify', 'batch_classify', 'batch_classify_v2', 'single_cache', 'batch_cache', 'batch_cache_v2') 
                            THEN COALESCE(cached_count, 0) 
                            ELSE 0 
                        END) as classify_cached,
                        SUM(CASE WHEN request_type IN ('single_classify', 'batch_classify', 'batch_classify_v2') THEN COALESCE(llm_count, 0) ELSE 0 END) as classify_llm,
                        SUM(CASE WHEN request_type IN ('single_classify', 'batch_classify', 'batch_classify_v2') THEN COALESCE(local_count, 0) ELSE 0 END) as classify_local,
                        
                        -- 图像编辑统计（包括V1和V2版本）
                        -- V1版本：只记录 image_edit（任务完成时）
                        -- V2版本：记录两次
                        --   - batch_image_edit（提交时）：记录用户提交的请求数，cached_count和llm_count为0
                        --   - image_edit（完成时）：记录实际处理的数据，包含准确的缓存和LLM数据
                        -- 统计策略：
                        --   为了避免V2版本的重复计算（同一个任务会记录batch_image_edit和image_edit），
                        --   只统计 image_edit（V1和V2版本都会在任务完成时记录，包含准确的统计信息）
                        --   这样既能覆盖所有版本，又能避免重复计算
                        SUM(CASE WHEN request_type = 'image_edit' THEN total_images ELSE 0 END) as edit_total,
                        SUM(CASE WHEN request_type = 'image_edit' THEN COALESCE(cached_count, 0) ELSE 0 END) as edit_cached,
                        SUM(CASE WHEN request_type = 'image_edit' THEN COALESCE(llm_count, 0) ELSE 0 END) as edit_llm
                    FROM unified_request_log log
                    LEFT JOIN (
                        -- 获取每个 client_id 对应的 openid（如果有）
                        -- 由于 wechat_qrcode_bindings 表有 UNIQUE KEY uk_client_id，每个 client_id 只有一条记录
                        SELECT client_id, openid
                        FROM wechat_qrcode_bindings
                        WHERE openid IS NOT NULL
                    ) binding ON log.client_id = binding.client_id
                    WHERE log.created_date = CURDATE()
                """)
                result = await cursor.fetchone()
                
                # 添加详细的调试日志
                logger.info(f"📊 主查询结果: result={result}")
                logger.info(f"📊 result 是否为 None: {result is None}")
                if result:
                    logger.info(f"📊 result 类型: {type(result)}")
                    logger.info(f"📊 result.keys(): {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                    logger.info(f"📊 unique_ips 原始值: {result.get('unique_ips')}, 类型: {type(result.get('unique_ips'))}")
                    logger.info(f"📊 classify_total 原始值: {result.get('classify_total')}, 类型: {type(result.get('classify_total'))}")
                    logger.info(f"📊 classify_cached 原始值: {result.get('classify_cached')}, 类型: {type(result.get('classify_cached'))}")
                    logger.info(f"📊 classify_llm 原始值: {result.get('classify_llm')}, 类型: {type(result.get('classify_llm'))}")
                
                # 调试：查询各类型的详细统计（包含V2类型）
                await cursor.execute("""
                    SELECT 
                        request_type,
                        COUNT(*) as request_count,
                        SUM(total_images) as total_images,
                        SUM(COALESCE(cached_count, 0)) as cached_count,
                        SUM(COALESCE(llm_count, 0)) as llm_count,
                        SUM(COALESCE(local_count, 0)) as local_count,
                        SUM(total_images) - SUM(COALESCE(cached_count, 0)) - SUM(COALESCE(llm_count, 0)) - SUM(COALESCE(local_count, 0)) as diff
                    FROM unified_request_log
                    WHERE created_date = CURDATE()
                      AND request_type IN ('single_classify', 'batch_classify', 'batch_classify_v2', 'single_cache', 'batch_cache', 'batch_cache_v2')
                    GROUP BY request_type
                """)
                detail_stats = await cursor.fetchall()
                logger.info(f"📊 今日分类统计详情（按类型）: {detail_stats}")
                
                # 调试：查询图像编辑统计详情
                await cursor.execute("""
                    SELECT 
                        request_type,
                        COUNT(*) as request_count,
                        SUM(total_images) as total_images,
                        SUM(COALESCE(cached_count, 0)) as cached_count,
                        SUM(COALESCE(llm_count, 0)) as llm_count
                    FROM unified_request_log
                    WHERE created_date = CURDATE()
                      AND request_type IN ('image_edit', 'batch_image_edit')
                    GROUP BY request_type
                """)
                edit_detail_stats = await cursor.fetchall()
                logger.info(f"📊 今日图像编辑统计详情（按类型）: {edit_detail_stats}")
                
                # 检查数据一致性
                if detail_stats:
                    for stat in detail_stats:
                        request_type = stat.get('request_type')
                        total = stat.get('total_images', 0) or 0
                        cached = stat.get('cached_count', 0) or 0
                        llm = stat.get('llm_count', 0) or 0
                        local = stat.get('local_count', 0) or 0
                        diff = stat.get('diff', 0) or 0
                        total_processed = cached + llm + local
                        
                        # 对于分类请求，total应该等于cached+llm+local
                        # 注意：差值可能是失败的请求或其他inference_method（如error等）
                        if request_type in ('single_classify', 'batch_classify', 'batch_classify_v2') and total != total_processed:
                            logger.warning(f"⚠️ {request_type} 数据不一致: total={total}, cached={cached}, llm={llm}, local={local}, 差值={diff} (差值可能是失败的请求或其他inference_method)")
                        # 对于缓存查询，total应该等于cached+miss（miss不会计入llm/local）
                        elif request_type in ('single_cache', 'batch_cache', 'batch_cache_v2') and diff != 0:
                            logger.info(f"ℹ️ {request_type} 未命中数: {diff} (这是正常的，缓存查询未命中不会触发推理)")
                
                if result:
                    # 确保所有值都转换为正确的数字类型（处理 decimal.Decimal）
                    def to_int(value):
                        """转换为整数，处理 None 和 decimal.Decimal"""
                        if value is None:
                            return 0
                        try:
                            return int(float(value))
                        except (ValueError, TypeError):
                            return 0
                    
                    stats = {
                        'unique_ips': to_int(result.get('unique_ips')),
                        'unique_users': to_int(result.get('unique_users')),
                        'classify': {
                            'total': to_int(result.get('classify_total')),
                            'cached': to_int(result.get('classify_cached')),
                            'llm_inference': to_int(result.get('classify_llm')),
                            'local_inference': to_int(result.get('classify_local'))
                        },
                        'image_edit': {
                            'total': to_int(result.get('edit_total')),
                            'cached': to_int(result.get('edit_cached')),
                            'llm_processed': to_int(result.get('edit_llm'))
                        }
                    }
                    
                    logger.info(f"📊 今日统计查询结果（转换后）: {stats}")
                    return stats
                
                # 如果没有数据，返回默认值
                return {
                    'unique_ips': 0,
                    'unique_users': 0,
                    'classify': {
                        'total': 0,
                        'cached': 0,
                        'llm_inference': 0,
                        'local_inference': 0
                    },
                    'image_edit': {
                        'total': 0,
                        'cached': 0,
                        'llm_processed': 0
                    }
                }
                
        except Exception as e:
            logger.error(f"查询今日统计失败: {e}", exc_info=True)
            return {
                'unique_ips': 0,
                'unique_users': 0,
                'classify': {
                    'total': 0,
                    'cached': 0,
                    'llm_inference': 0,
                    'local_inference': 0
                },
                'image_edit': {
                    'total': 0,
                    'cached': 0,
                    'llm_processed': 0
                }
            }
    
    async def get_cache_efficiency(self) -> dict:
        """
        获取缓存效率统计（V2版本统一缓存）
        
        使用 llm_inference_cache_v2 表统计，支持分类和编辑服务的统一缓存
        
        Returns:
            缓存效率数据
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT 
                    COUNT(*) as total_cached_images,
                    COALESCE(SUM(hit_count), 0) as total_hits,
                    COALESCE(SUM(hit_count - 1), 0) as times_saved,
                    ROUND((COALESCE(SUM(hit_count - 1), 0) * %s), 2) as cost_saved,
                    COALESCE(ROUND(AVG(hit_count), 2), 0) as avg_hit_per_image,
                    COALESCE(MAX(hit_count), 0) as max_hits
                FROM llm_inference_cache_v2
                """
                await cursor.execute(sql, (settings.COST_PER_API_CALL,))
                result = await cursor.fetchone()
                
                # 调试：记录原始查询结果
                logger.debug(f"缓存效率查询原始结果: {result}")
                
                # 确保所有值都转换为正确的数字类型（处理 decimal.Decimal）
                def to_int(value):
                    """转换为整数，处理 None 和 decimal.Decimal"""
                    if value is None:
                        return 0
                    try:
                        return int(float(value))
                    except (ValueError, TypeError):
                        return 0
                
                def to_float(value):
                    """转换为浮点数，处理 None 和 decimal.Decimal"""
                    if value is None:
                        return 0.0
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return 0.0
                
                if result:
                    stats = {
                        'total_cached_images': to_int(result.get('total_cached_images')),
                        'total_hits': to_int(result.get('total_hits')),
                        'times_saved': to_int(result.get('times_saved')),
                        'cost_saved': to_float(result.get('cost_saved')),
                        'avg_hit_per_image': to_float(result.get('avg_hit_per_image')),
                        'max_hits': to_int(result.get('max_hits'))
                    }
                    logger.debug(f"缓存效率统计结果: {stats}")
                    return stats
                return {
                    'total_cached_images': 0,
                    'total_hits': 0,
                    'times_saved': 0,
                    'cost_saved': 0.0,
                    'avg_hit_per_image': 0.0,
                    'max_hits': 0
                }
                
        except Exception as e:
            logger.error(f"查询缓存效率失败: {e}")
            return {}
    
    async def get_category_distribution(self) -> list:
        """
        获取分类分布统计（暂时返回空数据）
        
        Returns:
            分类分布列表（空列表）
        """
        # 暂时返回空数据，后续如果需要可以从 llm_inference_cache_v2 表的 model_results JSON中提取分类结果
        return []
    
    async def get_inference_method_stats(self) -> dict:
        """
        获取推理方式统计
        
        Returns:
            推理方式统计数据
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) as from_cache,
                    SUM(CASE WHEN inference_method = 'llm' THEN 1 ELSE 0 END) as llm_success,
                    SUM(CASE WHEN inference_method = 'local' THEN 1 ELSE 0 END) as local_direct,
                    SUM(CASE WHEN inference_method = 'llm_fallback' THEN 1 ELSE 0 END) as llm_fallback,
                    SUM(CASE WHEN inference_method = 'local_fallback' THEN 1 ELSE 0 END) as local_fallback_success,
                    SUM(CASE WHEN inference_method = 'local_test' THEN 1 ELSE 0 END) as local_test,
                    SUM(CASE WHEN inference_method IN ('llm_fallback', 'local_fallback') THEN 1 ELSE 0 END) as total_fallback
                FROM request_log
                WHERE created_date = CURDATE()
                """
                await cursor.execute(sql)
                result = await cursor.fetchone()
                
                if result:
                    # 计算百分比
                    total = result['total_requests'] or 0
                    return {
                        'total_requests': total,
                        'from_cache': result['from_cache'] or 0,
                        'llm_success': result['llm_success'] or 0,
                        'local_direct': result['local_direct'] or 0,
                        'llm_fallback': result['llm_fallback'] or 0,
                        'local_fallback_success': result['local_fallback_success'] or 0,
                        'local_test': result['local_test'] or 0,
                        'total_fallback': result['total_fallback'] or 0,
                        'llm_fail_count': result['local_fallback_success'] or 0,  # 大模型失败次数 = 降级到本地推理的次数
                        'local_total': (result['local_direct'] or 0) + (result['local_fallback_success'] or 0) + (result['local_test'] or 0)  # 本地推理总次数（包含测试）
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"查询推理方式统计失败: {e}")
            return {}
    async def log_batch_cache_query(
        self,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        total_count: int,
        cached_count: int,
        miss_count: int
    ) -> bool:
        """
        记录批量缓存查询统计
        
        Args:
            request_id: 请求ID
            user_id: 用户ID
            ip_address: IP地址
            total_count: 查询总数
            cached_count: 缓存命中数
            miss_count: 缓存未命中数
            
        Returns:
            是否记录成功
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO batch_cache_stats 
                    (request_id, user_id, ip_address, total_count, cached_count, miss_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (request_id, user_id, ip_address, total_count, cached_count, miss_count))
                
            return True
        except Exception as e:
            logger.error(f"记录批量缓存查询统计失败: {e}")
            return False
    
    async def get_batch_cache_stats(self, days: int = 7) -> dict:
        """
        获取批量缓存查询统计（从统一日志表统计，简化版）
        
        Args:
            days: 查询最近几天的数据
            
        Returns:
            统计数据（每日统计）
        """
        try:
            async with db.get_cursor() as cursor:
                # 类型转换函数
                def to_int(value):
                    if value is None:
                        return 0
                    try:
                        return int(float(value))
                    except (ValueError, TypeError):
                        return 0
                
                def to_float(value):
                    if value is None:
                        return 0.0
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return 0.0
                
                # 每日统计（从 unified_request_log 表，筛选 batch_cache 和 batch_cache_v2 类型）
                # 统计指标：独立用户数、独立IP数、请求总数、照片总数、缓存命中总数、命中比例
                await cursor.execute("""
                    SELECT 
                        created_date,
                        -- 请求总数（批量缓存查询请求次数，包括V1和V2版本）
                        COUNT(*) as total_requests,
                        -- 独立用户数（基于 client_id，通过绑定表映射到 openid）
                        COUNT(DISTINCT COALESCE(
                            binding.openid,
                            log.client_id
                        )) as unique_users,
                        -- 独立IP数
                        COUNT(DISTINCT ip_address) as unique_ips,
                        -- 照片总数
                        SUM(total_images) as total_images,
                        -- 缓存命中总数
                        SUM(cached_count) as total_cached,
                        -- 命中比例
                        ROUND(SUM(cached_count) * 100.0 / NULLIF(SUM(total_images), 0), 2) as hit_rate
                    FROM unified_request_log log
                    LEFT JOIN (
                        -- 获取每个 client_id 对应的 openid（如果有）
                        SELECT client_id, openid
                        FROM wechat_qrcode_bindings
                        WHERE openid IS NOT NULL
                    ) binding ON log.client_id = binding.client_id
                    WHERE log.request_type IN ('batch_cache', 'batch_cache_v2')
                      AND log.created_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    GROUP BY created_date
                    ORDER BY created_date DESC
                """, (days,))
                
                daily = await cursor.fetchall()
                
                # 转换结果
                daily_stats = []
                for row in daily:
                    daily_stats.append({
                        "date": str(row['created_date']),
                        "total_requests": to_int(row.get('total_requests')),
                        "unique_users": to_int(row.get('unique_users')),
                        "unique_ips": to_int(row.get('unique_ips')),
                        "total_images": to_int(row.get('total_images')),
                        "total_cached": to_int(row.get('total_cached')),
                        "hit_rate": to_float(row.get('hit_rate'))
                    })
                
                logger.debug(f"批量缓存查询统计结果: daily_count={len(daily_stats)}")
                
                return {
                    "daily": daily_stats
                }
        except Exception as e:
            logger.error(f"获取批量缓存统计失败: {e}", exc_info=True)
            return {
                "daily": []
            }
    
    async def log_batch_classify(
        self,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        total_count: int,
        success_count: int,
        fail_count: int,
        total_processing_time_ms: int
    ) -> bool:
        """
        记录批量分类统计
        
        Args:
            request_id: 请求ID
            user_id: 用户ID
            ip_address: IP地址
            total_count: 图片总数
            success_count: 成功数
            fail_count: 失败数
            total_processing_time_ms: 总处理耗时
            
        Returns:
            是否记录成功
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO batch_classify_stats 
                    (request_id, user_id, ip_address, total_count, success_count, fail_count, total_processing_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (request_id, user_id, ip_address, total_count, success_count, fail_count, total_processing_time_ms))
                
            return True
        except Exception as e:
            logger.error(f"记录批量分类统计失败: {e}")
            return False
    
    async def get_batch_classify_stats(self, days: int = 7) -> dict:
        """
        获取批量分类统计（从统一日志表统计，简化版）
        
        Args:
            days: 查询最近几天的数据
            
        Returns:
            统计数据（每日统计）
        """
        try:
            async with db.get_cursor() as cursor:
                # 类型转换函数
                def to_int(value):
                    if value is None:
                        return 0
                    try:
                        return int(float(value))
                    except (ValueError, TypeError):
                        return 0
                
                # 每日统计（从 unified_request_log 表，筛选 batch_classify 和 batch_classify_v2 类型）
                # 统计指标：请求总数、独立用户数、独立IP数、照片数、缓存数、大模型推理数、本地推理数
                await cursor.execute("""
                    SELECT 
                        created_date,
                        -- 请求总数（批量分类请求次数，包括V1和V2版本）
                        COUNT(*) as total_requests,
                        -- 独立用户数（基于 client_id，通过绑定表映射到 openid）
                        COUNT(DISTINCT COALESCE(
                            binding.openid,
                            log.client_id
                        )) as unique_users,
                        -- 独立IP数
                        COUNT(DISTINCT ip_address) as unique_ips,
                        -- 照片数
                        SUM(total_images) as images,
                        -- 缓存数
                        SUM(cached_count) as cached,
                        -- 大模型推理数
                        SUM(llm_count) as llm,
                        -- 本地推理数
                        SUM(local_count) as local
                    FROM unified_request_log log
                    LEFT JOIN (
                        -- 获取每个 client_id 对应的 openid（如果有）
                        SELECT client_id, openid
                        FROM wechat_qrcode_bindings
                        WHERE openid IS NOT NULL
                    ) binding ON log.client_id = binding.client_id
                    WHERE log.request_type IN ('batch_classify', 'batch_classify_v2')
                      AND log.created_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    GROUP BY created_date
                    ORDER BY created_date DESC
                """, (days,))
                
                daily = await cursor.fetchall()
                
                # 转换结果
                daily_stats = []
                for row in daily:
                    daily_stats.append({
                        "date": str(row['created_date']),
                        "total_requests": to_int(row.get('total_requests')),
                        "unique_users": to_int(row.get('unique_users')),
                        "unique_ips": to_int(row.get('unique_ips')),
                        "images": to_int(row.get('images')),
                        "cached": to_int(row.get('cached')),
                        "llm": to_int(row.get('llm')),
                        "local": to_int(row.get('local'))
                    })
                
                logger.debug(f"批量分类统计结果: daily_count={len(daily_stats)}")
                
                return {
                    "daily": daily_stats
                }
        except Exception as e:
            logger.error(f"获取批量分类统计失败: {e}", exc_info=True)
            return {
                "daily": []
            }
    
    async def get_image_edit_stats(self, days: int = 7) -> dict:
        """
        获取图片编辑统计（从统一日志表统计，简化版）
        
        Args:
            days: 查询最近几天的数据
            
        Returns:
            统计数据（每日统计）
        """
        try:
            async with db.get_cursor() as cursor:
                # 类型转换函数
                def to_int(value):
                    if value is None:
                        return 0
                    try:
                        return int(float(value))
                    except (ValueError, TypeError):
                        return 0
                
                # 每日统计（从 unified_request_log 表，筛选 image_edit 类型）
                # 统计指标：独立IP数、独立用户数、请求总数、照片总数、缓存总数、大模型处理总数
                await cursor.execute("""
                    SELECT 
                        created_date,
                        -- 请求总数（图像编辑请求次数）
                        COUNT(*) as total_requests,
                        -- 独立用户数（基于 client_id，通过绑定表映射到 openid）
                        COUNT(DISTINCT COALESCE(
                            binding.openid,
                            log.client_id
                        )) as unique_users,
                        -- 独立IP数
                        COUNT(DISTINCT ip_address) as unique_ips,
                        -- 照片总数
                        SUM(total_images) as total_images,
                        -- 缓存总数
                        SUM(cached_count) as total_cached,
                        -- 大模型处理总数
                        SUM(llm_count) as total_llm
                    FROM unified_request_log log
                    LEFT JOIN (
                        -- 获取每个 client_id 对应的 openid（如果有）
                        SELECT client_id, openid
                        FROM wechat_qrcode_bindings
                        WHERE openid IS NOT NULL
                    ) binding ON log.client_id = binding.client_id
                    WHERE log.request_type = 'image_edit'
                      AND log.created_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    GROUP BY created_date
                    ORDER BY created_date DESC
                """, (days,))
                
                daily = await cursor.fetchall()
                
                # 转换结果
                daily_stats = []
                for row in daily:
                    daily_stats.append({
                        "date": str(row['created_date']),
                        "total_requests": to_int(row.get('total_requests')),
                        "unique_users": to_int(row.get('unique_users')),
                        "unique_ips": to_int(row.get('unique_ips')),
                        "total_images": to_int(row.get('total_images')),
                        "total_cached": to_int(row.get('total_cached')),
                        "total_llm": to_int(row.get('total_llm'))
                    })
                
                logger.debug(f"图像编辑统计结果: daily_count={len(daily_stats)}")
                
                return {
                    "daily": daily_stats
                }
        except Exception as e:
            logger.error(f"获取图片编辑统计失败: {e}", exc_info=True)
            return {
                "daily": []
            }
    
    async def get_download_count(self, download_type: Optional[str] = None) -> dict:
        """
        获取下载量统计
        
        Args:
            download_type: 下载类型（android、windows），如果为None则返回所有类型的统计
        
        Returns:
            下载量统计字典，格式：{"android": 100, "windows": 50} 或 {"total": 150, "android": 100, "windows": 50}
        """
        try:
            async with db.get_cursor() as cursor:
                if download_type:
                    # 查询指定类型
                    await cursor.execute("""
                        SELECT type, download_count 
                        FROM download_stats 
                        WHERE type = %s
                    """, (download_type,))
                    result = await cursor.fetchone()
                    if result:
                        return {result['type']: result['download_count']}
                    return {download_type: 0}
                else:
                    # 查询所有类型
                    await cursor.execute("""
                        SELECT type, download_count 
                        FROM download_stats
                        ORDER BY type
                    """)
                    results = await cursor.fetchall()
                    stats = {}
                    total = 0
                    for row in results:
                        stats[row['type']] = row['download_count']
                        total += row['download_count']
                    stats['total'] = total
                    return stats
        except Exception as e:
            logger.error(f"查询下载量失败: {e}")
            return {}
    
    async def increment_download_count(self, download_type: str) -> bool:
        """
        增加下载量（+1）
        
        Args:
            download_type: 下载类型（android、windows）
        
        Returns:
            是否成功
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO download_stats (type, download_count) 
                    VALUES (%s, 1)
                    ON DUPLICATE KEY UPDATE download_count = download_count + 1
                """, (download_type,))
                return True
        except Exception as e:
            logger.error(f"增加下载量失败: {e}")
            return False
    
    async def get_bound_users_count(self) -> int:
        """
        获取已绑定用户数（按openid去重）
        
        Returns:
            已绑定用户数
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    SELECT COUNT(DISTINCT openid) as count 
                    FROM wechat_users
                """)
                result = await cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"查询已绑定用户数失败: {e}")
            return 0
    
    async def get_member_count(self) -> int:
        """
        获取会员数量（从wechat_users表中统计is_member=1的用户）
        
        Returns:
            会员数量
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    SELECT COUNT(DISTINCT openid) as count 
                    FROM wechat_users 
                    WHERE is_member = 1
                """)
                result = await cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"查询会员数量失败: {e}")
            return 0


# 全局统计服务实例
stats_service = StatsService()

