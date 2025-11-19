-- ====================================
-- 创建统一请求日志表
-- 用于统一记录所有类型的请求，简化统计逻辑
-- ====================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS `unified_request_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 请求标识
  `request_id` VARCHAR(64) NOT NULL COMMENT '请求唯一ID',
  
  -- 用户信息
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址',
  `client_id` VARCHAR(64) DEFAULT NULL COMMENT '客户端ID（user_id）',
  `openid` VARCHAR(64) DEFAULT NULL COMMENT '微信openid',
  
  -- 请求类型
  `request_type` VARCHAR(32) NOT NULL COMMENT '请求类型: single_classify/batch_classify/batch_cache/image_edit',
  
  -- 统计字段
  `total_images` INT UNSIGNED DEFAULT 0 COMMENT '照片总数',
  `cached_count` INT UNSIGNED DEFAULT 0 COMMENT '缓存命中数',
  `llm_count` INT UNSIGNED DEFAULT 0 COMMENT '大模型处理数',
  `local_count` INT UNSIGNED DEFAULT 0 COMMENT '本地处理数',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` DATE GENERATED ALWAYS AS (DATE(`created_at`)) STORED COMMENT '日期',
  
  PRIMARY KEY (`id`),
  KEY `idx_request_type` (`request_type`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_openid` (`openid`),
  KEY `idx_client_id` (`client_id`),
  KEY `idx_request_id` (`request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='统一请求日志表-用于简化统计';

SELECT '统一请求日志表已创建' AS 'Status';

