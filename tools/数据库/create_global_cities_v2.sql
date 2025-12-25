-- ====================================
-- 创建全球城市地理信息表（v2版本）
-- 支持多数据源：本地GeoNames、高德地图、Nominatim
-- ====================================

USE image_classifier;

-- 创建v2版本表
CREATE TABLE IF NOT EXISTS global_cities_v2 (
    -- 基础标识
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    
    -- 名称字段（只存储英文名称，中文名称通过映射表获取）
    name_en VARCHAR(255) NOT NULL COMMENT '英文名称（用于关联city_name_mapping表获取中文名）',
    
    -- 地理坐标（核心字段，用于距离计算）
    latitude DECIMAL(10, 7) NOT NULL COMMENT '纬度',
    longitude DECIMAL(10, 7) NOT NULL COMMENT '经度',
    
    -- 行政区划信息
    country_code CHAR(2) NOT NULL COMMENT '国家代码（ISO 3166-1 alpha-2）',
    admin1_code VARCHAR(20) DEFAULT NULL COMMENT '一级行政区代码（省/州）',
    admin2_code VARCHAR(80) DEFAULT NULL COMMENT '二级行政区代码（市/县）',
    province VARCHAR(100) DEFAULT NULL COMMENT '省份/州名称',
    city VARCHAR(100) DEFAULT NULL COMMENT '城市名称',
    district VARCHAR(100) DEFAULT NULL COMMENT '区县名称',
    
    -- 外部API相关字段
    data_source ENUM('local', 'gaode', 'nominatim') DEFAULT 'local' COMMENT '数据来源',
    api_city_id VARCHAR(255) DEFAULT NULL COMMENT '外部API返回的城市ID（高德的adcode或Nominatim的place_id）',
    api_city_code VARCHAR(50) DEFAULT NULL COMMENT '外部API的城市代码（高德的citycode）',
    api_adcode VARCHAR(20) DEFAULT NULL COMMENT '高德地图的行政区划代码',
    
    -- GeoNames相关字段（保留兼容性）
    geoname_id INT DEFAULT NULL COMMENT 'GeoNames ID（如果来自GeoNames）',
    feature_code VARCHAR(10) DEFAULT NULL COMMENT 'GeoNames feature_code（PPLC, PPLA等）',
    
    -- 其他信息
    population INT DEFAULT NULL COMMENT '人口数',
    elevation INT DEFAULT NULL COMMENT '海拔高度（米）',
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (id),
    
    -- 索引设计
    UNIQUE KEY uk_geoname_id (geoname_id) COMMENT 'GeoNames ID唯一索引',
    UNIQUE KEY uk_gaode_adcode (api_adcode) COMMENT '高德adcode唯一索引（如果来自高德）',
    KEY idx_name_en (name_en) COMMENT '英文名称索引（用于关联city_name_mapping表）',
    KEY idx_country_code (country_code) COMMENT '国家代码索引',
    KEY idx_data_source (data_source) COMMENT '数据来源索引',
    
    -- 复合索引（用于常见查询和距离计算）
    KEY idx_location (longitude, latitude) COMMENT '地理位置索引（用于距离查询）',
    KEY idx_country_location (country_code, latitude, longitude) COMMENT '国家+坐标复合索引',
    KEY idx_source_api_id (data_source, api_city_id) COMMENT '数据来源+API ID索引'
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='全球城市地理信息表（v2版本）';

-- 显示创建结果
SELECT 'global_cities_v2 表创建完成！' AS 'Status';

