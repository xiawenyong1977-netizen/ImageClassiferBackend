-- ====================================
-- 图像编辑缓存表（方案1）
-- 用途：为每张图片的编辑结果提供独立缓存
-- ====================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS `image_edit_cache` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 缓存key
  `image_hash` VARCHAR(64) NOT NULL COMMENT '图片SHA-256哈希值',
  `edit_type` VARCHAR(32) NOT NULL COMMENT '编辑类型（如：enhance等）',
  `prompt` VARCHAR(512) NOT NULL COMMENT '提示词（用于区分不同的编辑效果）',
  
  -- 缓存值
  `result_url` VARCHAR(512) NOT NULL COMMENT '处理结果的URL',
  `result_hash` VARCHAR(64) DEFAULT NULL COMMENT '结果图片的哈希值（可选）',
  
  -- 统计信息
  `hit_count` INT UNSIGNED DEFAULT 1 COMMENT '命中次数',
  `last_hit_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  
  -- 时间戳
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cache_key` (`image_hash`, `edit_type`, `prompt`),
  KEY `idx_image_hash` (`image_hash`),
  KEY `idx_edit_type` (`edit_type`),
  KEY `idx_hit_count` (`hit_count`),
  KEY `idx_last_hit` (`last_hit_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='图像编辑结果缓存表';

-- ====================================
-- 初始化完成
-- ====================================
