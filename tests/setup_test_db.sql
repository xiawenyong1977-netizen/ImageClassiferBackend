-- ====================================
-- 测试数据库初始化脚本
-- 从生产环境导出，自动生成
-- 生成时间: 2025-12-26 09:05:50
-- ====================================
-- 创建测试数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS image_classifier_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE image_classifier_test;

CREATE TABLE IF NOT EXISTS `batch_cache_stats` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `request_id` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '请求ID',
  `user_id` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户ID',
  `ip_address` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'IP地址',
  `total_count` int NOT NULL COMMENT '查询总数',
  `cached_count` int NOT NULL COMMENT '缓存命中数',
  `miss_count` int NOT NULL COMMENT '缓存未命中数',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` date GENERATED ALWAYS AS (cast(`created_at` as date)) STORED COMMENT '创建日期',
  PRIMARY KEY (`id`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_request_id` (`request_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='批量缓存查询统计';

CREATE TABLE IF NOT EXISTS `batch_classify_stats` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `request_id` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '请求ID',
  `user_id` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户ID',
  `ip_address` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'IP地址',
  `total_count` int NOT NULL COMMENT '图片总数',
  `success_count` int NOT NULL COMMENT '成功数',
  `fail_count` int NOT NULL COMMENT '失败数',
  `total_processing_time_ms` int NOT NULL COMMENT '总处理耗时(毫秒)',
  `avg_processing_time_ms` decimal(10,2) GENERATED ALWAYS AS ((`total_processing_time_ms` / `total_count`)) STORED COMMENT '平均处理耗时',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` date GENERATED ALWAYS AS (cast(`created_at` as date)) STORED COMMENT '创建日期',
  PRIMARY KEY (`id`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_request_id` (`request_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='批量分类统计';

CREATE TABLE IF NOT EXISTS `city_name_mapping` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name_zh` varchar(255) NOT NULL COMMENT '中文名称',
  `name_en` varchar(255) NOT NULL COMMENT '英文名称',
  `country_code` char(2) DEFAULT NULL COMMENT '国家代码',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name_zh` (`name_zh`),
  KEY `idx_name_en` (`name_en`),
  KEY `idx_country_code` (`country_code`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='全球城市名称中英文映射表';

CREATE TABLE IF NOT EXISTS `credits_usage` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户openid',
  `task_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务ID',
  `task_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务类型（image_edit等）',
  `credits_used` int unsigned DEFAULT '1' COMMENT '消耗的额度',
  `request_image_count` int unsigned DEFAULT '1' COMMENT '请求的图片张数',
  `success_image_count` int unsigned DEFAULT '1' COMMENT '成功处理的图片张数',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_openid` (`openid`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='额度消耗记录表';

CREATE TABLE IF NOT EXISTS `download_stats` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '下载类型：android、windows',
  `download_count` bigint unsigned DEFAULT '0' COMMENT '下载量',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_type` (`type`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='下载量统计表（按类型）';

CREATE TABLE IF NOT EXISTS `global_cities` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `geoname_id` int NOT NULL,
  `name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name_zh` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '中文名称',
  `ascii_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `latitude` decimal(10,7) NOT NULL,
  `longitude` decimal(10,7) NOT NULL,
  `country_code` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `admin1_code` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `admin2_code` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `population` int DEFAULT '0',
  `feature_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `geoname_id` (`geoname_id`),
  KEY `idx_coords` (`latitude`,`longitude`),
  KEY `idx_country` (`country_code`),
  KEY `idx_population` (`population`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='全球城市经纬度数据库';

CREATE TABLE IF NOT EXISTS `global_cities_v2` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name_en` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '英文名称（用于关联city_name_mapping表获取中文名）',
  `latitude` decimal(10,7) NOT NULL COMMENT '纬度',
  `longitude` decimal(10,7) NOT NULL COMMENT '经度',
  `country_code` char(2) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '国家代码（ISO 3166-1 alpha-2）',
  `admin1_code` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '一级行政区代码（省/州）',
  `admin2_code` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '二级行政区代码（市/县）',
  `province` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '省份/州名称',
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '城市名称',
  `district` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '区县名称',
  `data_source` enum('local','gaode','nominatim') COLLATE utf8mb4_unicode_ci DEFAULT 'local' COMMENT '数据来源',
  `api_city_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部API返回的城市ID（高德的adcode或Nominatim的place_id）',
  `api_city_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部API的城市代码（高德的citycode）',
  `api_adcode` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '高德地图的行政区划代码',
  `geoname_id` int DEFAULT NULL COMMENT 'GeoNames ID（如果来自GeoNames）',
  `feature_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'GeoNames feature_code（PPLC, PPLA等）',
  `population` int DEFAULT NULL COMMENT '人口数',
  `elevation` int DEFAULT NULL COMMENT '海拔高度（米）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_geoname_id` (`geoname_id`) COMMENT 'GeoNames ID唯一索引',
  UNIQUE KEY `uk_gaode_adcode` (`api_adcode`) COMMENT '高德adcode唯一索引（如果来自高德）',
  KEY `idx_name_en` (`name_en`) COMMENT '英文名称索引（用于关联city_name_mapping表）',
  KEY `idx_country_code` (`country_code`) COMMENT '国家代码索引',
  KEY `idx_data_source` (`data_source`) COMMENT '数据来源索引',
  KEY `idx_location` (`longitude`,`latitude`) COMMENT '地理位置索引（用于距离查询）',
  KEY `idx_country_location` (`country_code`,`latitude`,`longitude`) COMMENT '国家+坐标复合索引',
  KEY `idx_source_api_id` (`data_source`,`api_city_id`) COMMENT '数据来源+API ID索引'
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='全球城市地理信息表（v2版本）';

CREATE TABLE IF NOT EXISTS `image_classification_cache` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `image_hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'SHA-256哈希值',
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分类Key（8个预定义类别之一）',
  `confidence` decimal(5,4) NOT NULL COMMENT '置信度(0-1)',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '图片描述',
  `background_color` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '背景颜色（橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色）',
  `model_used` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '使用的模型',
  `model_response` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin COMMENT '完整模型响应',
  `hit_count` int unsigned DEFAULT '1' COMMENT '缓存命中次数',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
  `last_hit_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_image_hash` (`image_hash`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`),
  KEY `idx_hit_count` (`hit_count`),
  CONSTRAINT `image_classification_cache_chk_1` CHECK (json_valid(`model_response`))
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图片分类全局缓存表';

CREATE TABLE IF NOT EXISTS `image_edit_cache` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `image_hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '图片SHA-256哈希值',
  `edit_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '编辑类型（如：enhance等）',
  `prompt` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '提示词（用于区分不同的编辑效果）',
  `result_url` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '处理结果的URL',
  `result_hash` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '结果图片的哈希值（可选）',
  `hit_count` int unsigned DEFAULT '1' COMMENT '命中次数',
  `last_hit_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cache_key` (`image_hash`,`edit_type`,`prompt`),
  KEY `idx_image_hash` (`image_hash`),
  KEY `idx_edit_type` (`edit_type`),
  KEY `idx_hit_count` (`hit_count`),
  KEY `idx_last_hit` (`last_hit_at`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图像编辑结果缓存表';

CREATE TABLE IF NOT EXISTS `image_edit_tasks` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `task_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务唯一ID',
  `user_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户ID',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '客户端IP地址',
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信openid（用于额度管理）',
  `image_hash` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '图片SHA-256哈希值（用于缓存）',
  `edit_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '编辑类型（如：remove, expand等）',
  `edit_params` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin COMMENT '编辑参数（JSON格式）',
  `total_images` int unsigned DEFAULT '1' COMMENT '总图片数',
  `completed_images` int unsigned DEFAULT '0' COMMENT '已完成数',
  `progress` decimal(5,2) DEFAULT '0.00' COMMENT '进度（0-100）',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'pending' COMMENT '状态（pending/processing/completed/failed）',
  `results` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin COMMENT '编辑结果（JSON格式，包含每张图片的URL）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_image_hash` (`image_hash`),
  KEY `idx_cache_query` (`image_hash`,`status`,`edit_type`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_openid` (`openid`),
  KEY `idx_ip_address` (`ip_address`),
  CONSTRAINT `image_edit_tasks_chk_1` CHECK (json_valid(`edit_params`)),
  CONSTRAINT `image_edit_tasks_chk_2` CHECK (json_valid(`results`))
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图像编辑任务表';

CREATE TABLE IF NOT EXISTS `location_api_call_stats` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `api_provider` enum('gaode','nominatim') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'API提供商（高德/Nominatim）',
  `total_calls` int unsigned NOT NULL DEFAULT '0' COMMENT '总调用次数',
  `success_calls` int unsigned NOT NULL DEFAULT '0' COMMENT '成功调用次数',
  `failed_calls` int unsigned NOT NULL DEFAULT '0' COMMENT '失败调用次数',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_date_provider` (`stat_date`,`api_provider`) COMMENT '日期+提供商唯一索引',
  KEY `idx_stat_date` (`stat_date`) COMMENT '日期索引（用于按日期查询）',
  KEY `idx_api_provider` (`api_provider`) COMMENT 'API提供商索引',
  KEY `idx_date_provider` (`stat_date`,`api_provider`) COMMENT '日期+提供商复合索引'
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='地理位置查询外部API调用统计表（v2版本）';

CREATE TABLE IF NOT EXISTS `location_query_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `query_type` enum('nearest','nearby') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '查询类型',
  `latitude` decimal(10,7) NOT NULL COMMENT '查询纬度',
  `longitude` decimal(10,7) NOT NULL COMMENT '查询经度',
  `result_city_id` bigint DEFAULT NULL COMMENT '返回的城市ID',
  `result_city_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '返回的城市名称',
  `result_city_name_zh` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '返回的城市中文名',
  `result_count` int DEFAULT '1' COMMENT '返回结果数量',
  `distance_km` decimal(10,2) DEFAULT NULL COMMENT '距离(公里)',
  `user_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户ID（可选）',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'IP地址',
  `processing_time_ms` int unsigned DEFAULT NULL COMMENT '处理时间(毫秒)',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '查询时间',
  `created_date` date GENERATED ALWAYS AS (cast(`created_at` as date)) STORED COMMENT '查询日期',
  PRIMARY KEY (`id`),
  KEY `idx_query_type` (`query_type`),
  KEY `idx_coords` (`latitude`,`longitude`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_ip` (`ip_address`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='位置查询日志';

CREATE TABLE IF NOT EXISTS `payment_orders` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `order_no` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '订单号',
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户openid',
  `order_type` enum('member','credits') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '订单类型：member-会员开通，credits-额度购买',
  `amount` decimal(10,2) NOT NULL COMMENT '订单金额（元）',
  `credits_amount` int DEFAULT NULL COMMENT '额度数量（仅type=credits时有效）',
  `status` enum('pending','paid','refunded','failed') COLLATE utf8mb4_unicode_ci DEFAULT 'pending' COMMENT '订单状态',
  `wx_payment_no` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信支付订单号',
  `wx_transaction_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信支付交易号',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `paid_at` timestamp NULL DEFAULT NULL COMMENT '支付时间',
  `expire_at` timestamp NULL DEFAULT NULL COMMENT '过期时间（未支付订单过期）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_openid` (`openid`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付订单表';

CREATE TABLE IF NOT EXISTS `payment_records` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `order_no` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '订单号',
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户openid',
  `transaction_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '微信交易号',
  `amount` decimal(10,2) NOT NULL COMMENT '支付金额',
  `payment_method` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'wechat_pay' COMMENT '支付方式',
  `payment_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '支付时间',
  `notify_data` text COLLATE utf8mb4_unicode_ci COMMENT '微信回调原始数据',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_transaction_id` (`transaction_id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_openid` (`openid`),
  KEY `idx_payment_time` (`payment_time`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付记录表';

CREATE TABLE IF NOT EXISTS `request_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `request_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '请求唯一ID',
  `user_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户ID/设备ID',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '客户端IP地址',
  `image_hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'SHA-256哈希',
  `image_size` int unsigned DEFAULT NULL COMMENT '图片大小(字节)',
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分类Key（8个类别之一）',
  `confidence` decimal(5,4) NOT NULL COMMENT '置信度',
  `from_cache` tinyint(1) DEFAULT '0' COMMENT '是否来自缓存(0-否 1-是)',
  `processing_time_ms` int unsigned DEFAULT NULL COMMENT '处理耗时(毫秒)',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` date GENERATED ALWAYS AS (cast(`created_at` as date)) STORED COMMENT '日期',
  `inference_method` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'llm' COMMENT '推理方式: llm/local/llm_fallback/local_fallback',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_from_cache` (`from_cache`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`),
  KEY `idx_inference_method` (`inference_method`),
  KEY `idx_created_date_method` (`created_date`,`inference_method`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='请求日志表-用于统计分析';

CREATE TABLE IF NOT EXISTS `test_replication` (
  `id` int NOT NULL,
  `name` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `unified_request_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `request_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '请求唯一ID',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '客户端IP地址',
  `client_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '客户端ID（user_id）',
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信openid',
  `request_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '请求类型: single_classify/batch_classify/batch_cache/image_edit',
  `total_images` int unsigned DEFAULT '0' COMMENT '照片总数',
  `cached_count` int unsigned DEFAULT '0' COMMENT '缓存命中数',
  `llm_count` int unsigned DEFAULT '0' COMMENT '大模型处理数',
  `local_count` int unsigned DEFAULT '0' COMMENT '本地处理数',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` date GENERATED ALWAYS AS (cast(`created_at` as date)) STORED COMMENT '日期',
  PRIMARY KEY (`id`),
  KEY `idx_request_type` (`request_type`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_openid` (`openid`),
  KEY `idx_client_id` (`client_id`),
  KEY `idx_request_id` (`request_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一请求日志表-用于简化统计';

CREATE TABLE IF NOT EXISTS `wechat_qrcode_bindings` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `client_id` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户端ID',
  `scene_id` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '二维码场景值（字符串格式）',
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户openid（扫码关注后填入）',
  `status` enum('pending','completed','expired') COLLATE utf8mb4_unicode_ci DEFAULT 'pending' COMMENT '状态：pending-等待扫码，completed-已完成，expired-已过期',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `completed_at` timestamp NULL DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_client_id` (`client_id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_openid` (`openid`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信二维码绑定表';

CREATE TABLE IF NOT EXISTS `wechat_users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `openid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '微信openid',
  `unionid` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信unionid（可选）',
  `is_member` tinyint(1) DEFAULT '0' COMMENT '是否会员',
  `member_expire_at` timestamp NULL DEFAULT NULL COMMENT '会员过期时间',
  `total_paid_amount` decimal(10,2) DEFAULT '0.00' COMMENT '累计支付金额',
  `nickname` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信昵称',
  `avatar_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信头像',
  `total_credits` int unsigned DEFAULT '100' COMMENT '总额度（张）',
  `used_credits` int unsigned DEFAULT '0' COMMENT '已使用额度（张）',
  `remaining_credits` int unsigned DEFAULT '100' COMMENT '剩余额度（张）',
  `subscribe_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '关注时间',
  `last_active_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活跃时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_openid` (`openid`),
  KEY `idx_last_active` (`last_active_time`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信用户表';
-- ====================================
-- 插入测试数据
-- ====================================
-- 插入测试城市数据（v2）
INSERT INTO global_cities_v2 (name_en, latitude, longitude, country_code, data_source) VALUES
('Beijing', 39.9042, 116.4074, 'CN', 'local'),
('Shanghai', 31.2304, 121.4737, 'CN', 'local'),
('New York', 40.7128, -74.0060, 'US', 'local')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;
-- 插入测试映射数据
INSERT INTO city_name_mapping (name_zh, name_en, country_code) VALUES
('北京', 'Beijing', 'CN'),
('上海', 'Shanghai', 'CN'),
('纽约', 'New York', 'US')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;
-- ====================================
-- v2版本统一缓存表
-- ====================================

CREATE TABLE IF NOT EXISTS `llm_inference_cache_v2` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `prompt_hash` VARCHAR(64) NOT NULL COMMENT '提示词SHA-256哈希（分类服务：纯prompt；编辑服务：edit_type:prompt）',
  `image_hash` VARCHAR(64) NOT NULL COMMENT '图像SHA-256哈希',
  `model_results` JSON NOT NULL COMMENT '多模型推理结果集合',
  `total_models` INT UNSIGNED DEFAULT 1 COMMENT '已缓存的模型数量',
  `hit_count` INT UNSIGNED DEFAULT 1 COMMENT '缓存命中次数',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `last_hit_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prompt_image` (`prompt_hash`, `image_hash`) COMMENT '组合唯一索引（prompt_hash + image_hash）',
  KEY `idx_prompt_hash` (`prompt_hash`) COMMENT '提示词哈希索引',
  KEY `idx_image_hash` (`image_hash`) COMMENT '图像哈希索引',
  KEY `idx_hit_count` (`hit_count`) COMMENT '命中次数索引',
  KEY `idx_last_hit` (`last_hit_at`) COMMENT '最后命中时间索引',
  KEY `idx_created_at` (`created_at`) COMMENT '创建时间索引'
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='统一大模型推理缓存表（v2版本，支持分类和编辑服务，多模型结果集合）';

-- ====================================
-- v2版本用户照片关系表
-- ====================================

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

SELECT '测试数据库初始化完成！' AS 'Status';