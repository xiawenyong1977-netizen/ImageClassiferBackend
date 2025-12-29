-- ====================================
-- 创建用户照片关系表（v2版本）
-- 用于记录用户分类的照片，支持客户端通过image_uri查询
-- ====================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS `user_photos` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 用户标识
  `user_id` VARCHAR(64) NOT NULL COMMENT '用户ID/设备ID',
  `openid` VARCHAR(64) DEFAULT NULL COMMENT '微信openid（可选）',
  
  -- 图片标识
  `image_hash` VARCHAR(64) NOT NULL COMMENT '图片SHA-256哈希（后端主要使用）',
  `image_uri` VARCHAR(512) DEFAULT NULL COMMENT '图片URI（客户端传入，用于客户端查询和对账）',
  
  -- 统计信息
  `classify_count` INT UNSIGNED DEFAULT 1 COMMENT '该用户分类这张照片的次数',
  
  -- 时间戳
  `first_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次分类时间',
  `last_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后分类时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_image` (`user_id`, `image_hash`) COMMENT '用户和图片的唯一组合',
  KEY `idx_user_id` (`user_id`) COMMENT '用户ID索引',
  KEY `idx_openid` (`openid`) COMMENT '微信openid索引',
  KEY `idx_image_hash` (`image_hash`) COMMENT '图片哈希索引',
  KEY `idx_image_uri` (`image_uri`) COMMENT '图片URI索引（用于客户端查询）',
  KEY `idx_last_seen_at` (`last_seen_at`) COMMENT '最后分类时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='用户照片关系表（v2版本，记录用户分类的照片，支持通过image_uri查询）';

-- 显示创建结果
SELECT 'user_photos 表创建完成！' AS 'Status';

