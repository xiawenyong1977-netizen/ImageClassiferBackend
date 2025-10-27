-- 微信用户表
CREATE TABLE IF NOT EXISTS `wechat_users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `openid` VARCHAR(64) NOT NULL COMMENT '微信openid',
  `unionid` VARCHAR(64) DEFAULT NULL COMMENT '微信unionid（可选）',
  `nickname` VARCHAR(128) DEFAULT NULL COMMENT '微信昵称',
  `avatar_url` VARCHAR(512) DEFAULT NULL COMMENT '微信头像',
  `total_credits` INT UNSIGNED DEFAULT 100 COMMENT '总额度（张）',
  `used_credits` INT UNSIGNED DEFAULT 0 COMMENT '已使用额度（张）',
  `remaining_credits` INT UNSIGNED DEFAULT 100 COMMENT '剩余额度（张）',
  `subscribe_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '关注时间',
  `last_active_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活跃时间',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_openid` (`openid`),
  KEY `idx_last_active` (`last_active_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信用户表';

-- 额度消耗记录表
CREATE TABLE IF NOT EXISTS `credits_usage` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `openid` VARCHAR(64) NOT NULL COMMENT '用户openid',
  `task_id` VARCHAR(64) NOT NULL COMMENT '任务ID',
  `task_type` VARCHAR(32) NOT NULL COMMENT '任务类型（image_edit等）',
  `credits_used` INT UNSIGNED DEFAULT 1 COMMENT '消耗的额度',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_openid` (`openid`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='额度消耗记录表';
