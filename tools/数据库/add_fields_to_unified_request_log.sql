-- ====================================
-- 为统一请求日志表添加批量分类统计所需字段
-- 用于替代 batch_classify_stats 表
-- ====================================

USE image_classifier;

-- 添加 success_count 字段（成功数）
ALTER TABLE `unified_request_log` 
ADD COLUMN `success_count` INT UNSIGNED DEFAULT 0 COMMENT '成功数（用于批量分类）' AFTER `local_count`;

-- 添加 fail_count 字段（失败数）
ALTER TABLE `unified_request_log` 
ADD COLUMN `fail_count` INT UNSIGNED DEFAULT 0 COMMENT '失败数（用于批量分类）' AFTER `success_count`;

-- 添加 total_processing_time_ms 字段（总处理耗时）
ALTER TABLE `unified_request_log` 
ADD COLUMN `total_processing_time_ms` INT UNSIGNED DEFAULT 0 COMMENT '总处理耗时(毫秒)' AFTER `fail_count`;

SELECT '统一请求日志表字段已添加' AS 'Status';

