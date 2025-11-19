-- 下载量统计表（按类型统计：android、windows）
CREATE TABLE IF NOT EXISTS `download_stats` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `type` VARCHAR(32) NOT NULL COMMENT '下载类型：android、windows',
  `download_count` BIGINT UNSIGNED DEFAULT 0 COMMENT '下载量',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_type` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='下载量统计表（按类型）';

-- 初始化两条记录（如果不存在）
INSERT IGNORE INTO `download_stats` (`type`, `download_count`) VALUES ('android', 0);
INSERT IGNORE INTO `download_stats` (`type`, `download_count`) VALUES ('windows', 0);
