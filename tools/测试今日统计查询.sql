-- 测试今日统计查询
-- 用于验证 unified_request_log 表的查询是否正确

USE image_classifier;

-- 1. 检查今日是否有数据
SELECT 
    COUNT(*) as total_records,
    MIN(created_at) as first_record,
    MAX(created_at) as last_record
FROM unified_request_log
WHERE created_date = CURDATE();

-- 2. 检查 created_date 字段是否正确生成
SELECT 
    created_at,
    created_date,
    DATE(created_at) as manual_date
FROM unified_request_log
ORDER BY created_at DESC
LIMIT 5;

-- 3. 执行完整的统计查询（与代码中的查询一致）
SELECT 
    -- 独立IP个数
    COUNT(DISTINCT ip_address) as unique_ips,
    
    -- 用户数（client_id 或 openid）
    COUNT(DISTINCT CASE 
        WHEN openid IS NOT NULL THEN openid 
        WHEN client_id IS NOT NULL THEN client_id 
        ELSE NULL 
    END) as unique_users,
    
    -- 图片分类统计（包括单个分类、批量分类、单个缓存查询、批量缓存查询）
    SUM(CASE WHEN request_type IN ('single_classify', 'batch_classify', 'single_cache', 'batch_cache') THEN total_images ELSE 0 END) as classify_total,
    SUM(CASE WHEN request_type IN ('single_classify', 'batch_classify', 'single_cache', 'batch_cache') THEN cached_count ELSE 0 END) as classify_cached,
    SUM(CASE WHEN request_type IN ('single_classify', 'batch_classify') THEN llm_count ELSE 0 END) as classify_llm,
    SUM(CASE WHEN request_type IN ('single_classify', 'batch_classify') THEN local_count ELSE 0 END) as classify_local,
    
    -- 图像编辑统计
    SUM(CASE WHEN request_type = 'image_edit' THEN total_images ELSE 0 END) as edit_total,
    SUM(CASE WHEN request_type = 'image_edit' THEN cached_count ELSE 0 END) as edit_cached,
    SUM(CASE WHEN request_type = 'image_edit' THEN llm_count ELSE 0 END) as edit_llm
FROM unified_request_log
WHERE created_date = CURDATE();

-- 4. 按请求类型分组查看
SELECT 
    request_type,
    COUNT(*) as request_count,
    SUM(total_images) as total_images,
    SUM(cached_count) as cached_count,
    SUM(llm_count) as llm_count,
    SUM(local_count) as local_count
FROM unified_request_log
WHERE created_date = CURDATE()
GROUP BY request_type
ORDER BY request_type;

-- 5. 查看最近几条记录
SELECT 
    request_id,
    request_type,
    ip_address,
    client_id,
    openid,
    total_images,
    cached_count,
    llm_count,
    local_count,
    created_at,
    created_date
FROM unified_request_log
ORDER BY created_at DESC
LIMIT 10;

