-- ====================================
-- 测试数据库初始化脚本
-- 用于本地测试时创建测试数据库和表
-- ====================================

-- 创建测试数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS image_classifier_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE image_classifier_test;

-- 注意：这里只创建v2版本需要的表
-- 如果需要测试v1版本，需要导入完整的数据库结构

-- 创建城市名称映射表
CREATE TABLE IF NOT EXISTS city_name_mapping (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name_zh VARCHAR(255) NOT NULL COMMENT '中文名称',
    name_en VARCHAR(255) NOT NULL COMMENT '英文名称',
    country_code CHAR(2) COMMENT '国家代码',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_name_zh (name_zh),
    KEY idx_name_en (name_en),
    KEY idx_country_code (country_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='全球城市名称中英文映射表';

-- 创建v2版本城市表
CREATE TABLE IF NOT EXISTS global_cities_v2 (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    name_en VARCHAR(255) NOT NULL COMMENT '英文名称（用于关联city_name_mapping表获取中文名）',
    latitude DECIMAL(10, 7) NOT NULL COMMENT '纬度',
    longitude DECIMAL(10, 7) NOT NULL COMMENT '经度',
    country_code CHAR(2) NOT NULL COMMENT '国家代码（ISO 3166-1 alpha-2）',
    admin1_code VARCHAR(20) DEFAULT NULL COMMENT '一级行政区代码（省/州）',
    admin2_code VARCHAR(80) DEFAULT NULL COMMENT '二级行政区代码（市/县）',
    province VARCHAR(100) DEFAULT NULL COMMENT '省份/州名称',
    city VARCHAR(100) DEFAULT NULL COMMENT '城市名称',
    district VARCHAR(100) DEFAULT NULL COMMENT '区县名称',
    data_source ENUM('local', 'gaode', 'nominatim') DEFAULT 'local' COMMENT '数据来源',
    api_city_id VARCHAR(255) DEFAULT NULL COMMENT '外部API返回的城市ID（高德的adcode或Nominatim的place_id）',
    api_city_code VARCHAR(50) DEFAULT NULL COMMENT '外部API的城市代码（高德的citycode）',
    api_adcode VARCHAR(20) DEFAULT NULL COMMENT '高德地图的行政区划代码',
    geoname_id INT DEFAULT NULL COMMENT 'GeoNames ID（如果来自GeoNames）',
    feature_code VARCHAR(10) DEFAULT NULL COMMENT 'GeoNames feature_code（PPLC, PPLA等）',
    population INT DEFAULT NULL COMMENT '人口数',
    elevation INT DEFAULT NULL COMMENT '海拔高度（米）',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_geoname_id (geoname_id) COMMENT 'GeoNames ID唯一索引',
    UNIQUE KEY uk_gaode_adcode (api_adcode) COMMENT '高德adcode唯一索引（如果来自高德）',
    KEY idx_name_en (name_en) COMMENT '英文名称索引（用于关联city_name_mapping表）',
    KEY idx_country_code (country_code) COMMENT '国家代码索引',
    KEY idx_data_source (data_source) COMMENT '数据来源索引',
    KEY idx_location (longitude, latitude) COMMENT '地理位置索引',
    KEY idx_country_location (country_code, latitude, longitude) COMMENT '国家+坐标复合索引',
    KEY idx_source_api_id (data_source, api_city_id) COMMENT '数据来源+API ID索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='全球城市地理信息表（v2版本）';

-- 创建API调用统计表
CREATE TABLE IF NOT EXISTS location_api_call_stats (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    stat_date DATE NOT NULL COMMENT '统计日期',
    api_provider ENUM('gaode', 'nominatim') NOT NULL COMMENT 'API提供商（高德/Nominatim）',
    total_calls INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '总调用次数',
    success_calls INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '成功调用次数',
    failed_calls INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '失败调用次数',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_date_provider (stat_date, api_provider) COMMENT '日期+提供商唯一索引',
    KEY idx_stat_date (stat_date) COMMENT '日期索引（用于按日期查询）',
    KEY idx_api_provider (api_provider) COMMENT 'API提供商索引',
    KEY idx_date_provider (stat_date, api_provider) COMMENT '日期+提供商复合索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='地理位置查询外部API调用统计表（v2版本）';

-- 插入一些测试数据（可选）
-- 插入测试城市
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

SELECT '测试数据库初始化完成！' AS 'Status';

