#!/bin/bash
# 快速检查统一日志是否正常工作

echo "=========================================="
echo "检查统一日志表数据"
echo "=========================================="

# 需要手动输入MySQL密码，或者使用配置文件
echo ""
echo "1. 查看统一日志表总记录数："
echo "mysql -u root -p image_classifier -e \"SELECT COUNT(*) as total_records, MAX(created_at) as latest_record FROM unified_request_log;\""

echo ""
echo "2. 查看今日各类型请求统计："
echo "mysql -u root -p image_classifier -e \"
SELECT 
    request_type,
    COUNT(*) as requests,
    SUM(total_images) as total_images,
    SUM(cached_count) as cached,
    SUM(llm_count) as llm,
    SUM(local_count) as local
FROM unified_request_log
WHERE created_date = CURDATE()
GROUP BY request_type;
\""

echo ""
echo "3. 查看最近10条记录："
echo "mysql -u root -p image_classifier -e \"
SELECT 
    request_id,
    request_type,
    LEFT(ip_address, 15) as ip,
    total_images,
    cached_count,
    llm_count,
    local_count,
    created_at
FROM unified_request_log
ORDER BY created_at DESC
LIMIT 10;
\""

echo ""
echo "4. 查看应用日志中的统一日志记录："
echo "grep '统一请求日志' /var/log/image-classifier/app.log | tail -10"

echo ""
echo "=========================================="
echo "检查完成"
echo "=========================================="

