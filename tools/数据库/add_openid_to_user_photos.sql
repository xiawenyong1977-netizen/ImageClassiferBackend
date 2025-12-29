-- ====================================
-- 为user_photos表添加openid字段
-- 用于v2版本分类接口
-- ====================================

USE image_classifier;

-- 添加openid字段
ALTER TABLE `user_photos` 
ADD COLUMN `openid` VARCHAR(64) DEFAULT NULL COMMENT '微信openid（可选）' AFTER `user_id`;

-- 添加openid索引
ALTER TABLE `user_photos` 
ADD KEY `idx_openid` (`openid`) COMMENT '微信openid索引';

-- 显示更新结果
SELECT 'user_photos 表已添加 openid 字段！' AS 'Status';

