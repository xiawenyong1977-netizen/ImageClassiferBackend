-- ====================================
-- 添加 async_tasks 表（异步任务表）
-- 创建时间: 2025-12-26
-- ====================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS `async_tasks` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `task_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE COMMENT '任务ID',
  `task_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务类型（image_edit等）',
  `user_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户ID（可选，用于统计）',
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信openid（可选，用于统计）',
  `total_items` int unsigned DEFAULT '0' COMMENT '总项目数',
  `completed_items` int unsigned DEFAULT '0' COMMENT '已完成项目数',
  `task_params` json DEFAULT NULL COMMENT '任务参数（JSON格式）',
  `results` json DEFAULT NULL COMMENT '任务结果（JSON格式）',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'pending' COMMENT '任务状态：pending|processing|completed|failed',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`),
  KEY `idx_task_type` (`task_type`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='异步任务表（统一表，用于所有类型的异步任务）';

SELECT 'async_tasks 表创建完成！' AS 'Status';

