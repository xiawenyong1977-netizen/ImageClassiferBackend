-- 为 credits_usage 表添加详细统计字段
ALTER TABLE `credits_usage` 
  ADD COLUMN `request_image_count` INT UNSIGNED DEFAULT 1 COMMENT '请求的图片张数' AFTER `credits_used`,
  ADD COLUMN `success_image_count` INT UNSIGNED DEFAULT 1 COMMENT '成功处理的图片张数' AFTER `request_image_count`;

