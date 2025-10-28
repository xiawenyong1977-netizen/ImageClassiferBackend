-- 微信二维码绑定表
CREATE TABLE IF NOT EXISTS `wechat_qrcode_bindings` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `client_id` VARCHAR(128) NOT NULL COMMENT '客户端ID',
  `scene_id` INT NOT NULL COMMENT '二维码场景值',
  `openid` VARCHAR(64) DEFAULT NULL COMMENT '用户openid（扫码关注后填入）',
  `status` ENUM('pending', 'completed', 'expired') DEFAULT 'pending' COMMENT '状态：pending-等待扫码，completed-已完成，expired-已过期',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `completed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_client_id` (`client_id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_openid` (`openid`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信二维码绑定表';
