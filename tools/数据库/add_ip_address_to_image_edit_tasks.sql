-- ====================================
-- 给 image_edit_tasks 表添加 ip_address 字段
-- 用于统计独立IP个数
-- ====================================

USE image_classifier;

-- 添加 ip_address 字段
ALTER TABLE `image_edit_tasks` 
ADD COLUMN `ip_address` VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址' AFTER `user_id`;

-- 添加索引
ALTER TABLE `image_edit_tasks` 
ADD KEY `idx_ip_address` (`ip_address`);

SELECT 'ip_address字段已添加到image_edit_tasks表' AS 'Status';

