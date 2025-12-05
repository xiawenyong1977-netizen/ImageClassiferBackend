-- ====================================
-- 检查迁移结果：验证 ip_address 字段是否已添加
-- 执行方式：mysql -u root -p image_classifier < check_migration_result.sql
-- ====================================

USE image_classifier;

-- 1. 检查字段是否存在
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ ip_address 字段已存在'
        ELSE '❌ ip_address 字段不存在'
    END AS '字段检查',
    CASE 
        WHEN COUNT(*) > 0 THEN CONCAT('类型: ', COLUMN_TYPE, ', 允许NULL: ', IS_NULLABLE, ', 注释: ', COLUMN_COMMENT)
        ELSE '请执行迁移脚本'
    END AS '详细信息'
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'image_classifier'
  AND TABLE_NAME = 'image_edit_tasks'
  AND COLUMN_NAME = 'ip_address';

-- 2. 检查索引是否存在
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ idx_ip_address 索引已存在'
        ELSE '❌ idx_ip_address 索引不存在'
    END AS '索引检查',
    CASE 
        WHEN COUNT(*) > 0 THEN CONCAT('列名: ', COLUMN_NAME, ', 非唯一: ', NON_UNIQUE)
        ELSE '请执行迁移脚本'
    END AS '详细信息'
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'image_classifier'
  AND TABLE_NAME = 'image_edit_tasks'
  AND INDEX_NAME = 'idx_ip_address';

-- 3. 显示相关字段列表
SELECT 
    '📋 相关字段列表' AS '信息',
    COLUMN_NAME AS '字段名',
    COLUMN_TYPE AS '类型',
    CASE 
        WHEN COLUMN_KEY = 'PRI' THEN '主键'
        WHEN COLUMN_KEY = 'MUL' THEN '索引'
        WHEN COLUMN_KEY = 'UNI' THEN '唯一索引'
        ELSE ''
    END AS '键类型',
    IS_NULLABLE AS '允许NULL',
    COLUMN_DEFAULT AS '默认值'
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'image_classifier'
  AND TABLE_NAME = 'image_edit_tasks'
  AND COLUMN_NAME IN ('id', 'task_id', 'user_id', 'ip_address', 'openid', 'edit_type')
ORDER BY ORDINAL_POSITION;

-- 4. 显示表结构（DESC）
SELECT '📋 完整表结构（DESC image_edit_tasks）' AS '信息';
DESC image_edit_tasks;

