-- ====================================
-- 图片分类系统数据库初始化脚本
-- 版本: 1.0
-- 日期: 2025-10-10
-- ====================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS image_classifier 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

USE image_classifier;

-- ====================================
-- 表1: 图片分类缓存表
-- 用途：存储图片分类结果，实现全局去重缓存
-- ====================================
CREATE TABLE IF NOT EXISTS `image_classification_cache` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 图片标识
  `image_hash` VARCHAR(64) NOT NULL COMMENT 'SHA-256哈希值',
  
  -- 分类结果（8个固定类别）
  `category` VARCHAR(50) NOT NULL COMMENT '分类Key（8个预定义类别之一）',
  `confidence` DECIMAL(5,4) NOT NULL COMMENT '置信度(0-1)',
  `description` TEXT DEFAULT NULL COMMENT '图片描述',
  
  -- 模型信息
  `model_used` VARCHAR(50) NOT NULL COMMENT '使用的模型',
  `model_response` JSON DEFAULT NULL COMMENT '完整模型响应',
  
  -- 统计信息
  `hit_count` INT UNSIGNED DEFAULT 1 COMMENT '缓存命中次数',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
  `last_hit_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_image_hash` (`image_hash`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`),
  KEY `idx_hit_count` (`hit_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='图片分类全局缓存表';

-- category 字段可能的值（8个固定类别）：
-- 'social_activities' - 社交活动
-- 'pets' - 宠物萌照  
-- 'single_person' - 单人照片
-- 'foods' - 美食记录
-- 'travel_scenery' - 旅行风景
-- 'screenshot' - 手机截图
-- 'idcard' - 证件照
-- 'other' - 其它

-- ====================================
-- 表2: 请求日志表
-- 用途：记录每次分类请求，用于统计分析
-- ====================================
CREATE TABLE IF NOT EXISTS `request_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 请求标识
  `request_id` VARCHAR(64) NOT NULL COMMENT '请求唯一ID',
  
  -- 用户信息（可选）
  `user_id` VARCHAR(64) DEFAULT NULL COMMENT '用户ID/设备ID',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址',
  
  -- 图片信息
  `image_hash` VARCHAR(64) NOT NULL COMMENT 'SHA-256哈希',
  `image_size` INT UNSIGNED DEFAULT NULL COMMENT '图片大小(字节)',
  
  -- 分类结果（冗余存储）
  `category` VARCHAR(50) NOT NULL COMMENT '分类Key（8个类别之一）',
  `confidence` DECIMAL(5,4) NOT NULL COMMENT '置信度',
  
  -- 统计字段
  `from_cache` TINYINT(1) DEFAULT 0 COMMENT '是否来自缓存(0-否 1-是)',
  `processing_time_ms` INT UNSIGNED DEFAULT NULL COMMENT '处理耗时(毫秒)',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` DATE GENERATED ALWAYS AS (DATE(`created_at`)) STORED COMMENT '日期',
  
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_from_cache` (`from_cache`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='请求日志表-用于统计分析';

-- ====================================
-- 初始化完成
-- ====================================
SELECT '========================================' AS '';
SELECT '数据库初始化完成！' AS 'Status';
SELECT '共创建 2 张表：' AS 'Info';
SELECT '  1. image_classification_cache (缓存表)' AS '';
SELECT '  2. request_log (请求日志表)' AS '';
SELECT '========================================' AS '';

