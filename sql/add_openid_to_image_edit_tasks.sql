-- ====================================
-- 给 image_edit_tasks 表添加 openid 字段
-- 用于额度管理和用户关联
-- ====================================

USE image_classifier;

-- 添加 openid 字段
ALTER TABLE `image_edit_tasks` 
ADD COLUMN `openid` VARCHAR(64) DEFAULT NULL COMMENT '微信openid（用于额度管理）' AFTER `user_id`;

-- 添加索引
ALTER TABLE `image_edit_tasks` 
ADD KEY `idx_openid` (`openid`);

SELECT 'openid字段已添加到image_edit_tasks表' AS 'Status';

