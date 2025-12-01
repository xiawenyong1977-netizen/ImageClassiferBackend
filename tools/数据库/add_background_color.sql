-- ====================================
-- 添加背景颜色字段迁移脚本
-- 版本: 1.0
-- 日期: 2025-01-XX
-- 说明: 为 image_classification_cache 表添加 background_color 字段
-- ====================================

USE image_classifier;

-- 检查字段是否已存在
SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'image_classifier'
    AND TABLE_NAME = 'image_classification_cache'
    AND COLUMN_NAME = 'background_color'
);

-- 如果字段不存在，则添加
SET @sql = IF(@column_exists = 0,
    'ALTER TABLE `image_classification_cache` ADD COLUMN `background_color` VARCHAR(20) DEFAULT NULL COMMENT ''背景颜色（橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色）'' AFTER `description`;',
    'SELECT ''字段 background_color 已存在，跳过迁移'' AS message;'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 显示迁移结果
SELECT '========================================' AS '';
SELECT '背景颜色字段迁移完成！' AS 'Status';
SELECT '字段: background_color' AS 'Info';
SELECT '类型: VARCHAR(20) DEFAULT NULL' AS 'Type';
SELECT '========================================' AS '';

