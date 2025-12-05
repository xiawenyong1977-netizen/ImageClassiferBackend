-- ====================================
-- 在主库执行：添加 ip_address 字段到 image_edit_tasks 表
-- 执行方式：mysql -u root -p image_classifier < 执行迁移_主库.sql
-- ====================================

USE image_classifier;

-- 检查字段是否已存在，如果不存在则添加
SET @column_exists = (
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = 'image_classifier' 
      AND TABLE_NAME = 'image_edit_tasks' 
      AND COLUMN_NAME = 'ip_address'
);

SET @sql = IF(@column_exists = 0,
    'ALTER TABLE `image_edit_tasks` ADD COLUMN `ip_address` VARCHAR(45) DEFAULT NULL COMMENT ''客户端IP地址'' AFTER `user_id`',
    'SELECT ''字段 ip_address 已存在，跳过添加'' AS ''Status'''
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查索引是否已存在，如果不存在则添加
SET @index_exists = (
    SELECT COUNT(*) 
    FROM information_schema.STATISTICS 
    WHERE TABLE_SCHEMA = 'image_classifier' 
      AND TABLE_NAME = 'image_edit_tasks' 
      AND INDEX_NAME = 'idx_ip_address'
);

SET @sql2 = IF(@index_exists = 0,
    'ALTER TABLE `image_edit_tasks` ADD KEY `idx_ip_address` (`ip_address`)',
    'SELECT ''索引 idx_ip_address 已存在，跳过添加'' AS ''Status'''
);

PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- 验证表结构
SELECT 'ip_address字段已添加到image_edit_tasks表' AS 'Status';
DESC image_edit_tasks;

