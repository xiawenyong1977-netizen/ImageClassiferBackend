-- ====================================
-- 图像编辑任务表
-- 用途：存储图像编辑任务的状态和结果
-- ====================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS `image_edit_tasks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 任务标识
  `task_id` VARCHAR(64) NOT NULL COMMENT '任务唯一ID',
  `user_id` VARCHAR(64) DEFAULT NULL COMMENT '用户ID',
  `image_hash` VARCHAR(64) DEFAULT NULL COMMENT '图片SHA-256哈希值（用于缓存）',
  
  -- 编辑配置
  `edit_type` VARCHAR(32) NOT NULL COMMENT '编辑类型（如：remove, expand等）',
  `edit_params` JSON DEFAULT NULL COMMENT '编辑参数（JSON格式）',
  
  -- 任务进度
  `total_images` INT UNSIGNED DEFAULT 1 COMMENT '总图片数',
  `completed_images` INT UNSIGNED DEFAULT 0 COMMENT '已完成数',
  `progress` DECIMAL(5,2) DEFAULT 0.00 COMMENT '进度（0-100）',
  
  -- 任务状态
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态（pending/processing/completed/failed）',
  
  -- 结果
  `results` JSON DEFAULT NULL COMMENT '编辑结果（JSON格式，包含每张图片的URL）',
  
  -- 时间戳
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_image_hash` (`image_hash`),
  KEY `idx_cache_query` (`image_hash`, `status`, `edit_type`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='图像编辑任务表';

-- ====================================
-- 初始化完成
-- ====================================
