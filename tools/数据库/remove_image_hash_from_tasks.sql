-- ====================================
-- 从image_edit_tasks表删除image_hash字段
-- 原因：缓存已迁移到独立的image_edit_cache表
-- ====================================

USE image_classifier;

-- 删除image_hash字段的索引
ALTER TABLE `image_edit_tasks` DROP INDEX `idx_image_hash`;
ALTER TABLE `image_edit_tasks` DROP INDEX `idx_cache_query`;

-- 删除image_hash字段
ALTER TABLE `image_edit_tasks` DROP COLUMN `image_hash`;

-- ====================================
-- 完成
-- ====================================
