-- ============================================================
-- V3 位置缓存表：坐标 -> 三级行政区（中英文完整存储）
-- 用于 LLM 逆地址编码结果缓存，单表设计，无 mapping 依赖
-- ============================================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS location_cache_v3 (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    
    -- 坐标（精确到小数点后6位，约0.1米）
    latitude DECIMAL(10, 6) NOT NULL COMMENT '纬度',
    longitude DECIMAL(10, 6) NOT NULL COMMENT '经度',
    
    -- 国家
    country_code CHAR(2) NOT NULL COMMENT '国家代码 ISO 3166-1',
    country_zh VARCHAR(100) NOT NULL DEFAULT '' COMMENT '国家中文名',
    country_en VARCHAR(100) NOT NULL DEFAULT '' COMMENT '国家英文名',
    
    -- 一级行政区（省/州）
    province_zh VARCHAR(100) DEFAULT NULL COMMENT '省/州中文名',
    province_en VARCHAR(100) DEFAULT NULL COMMENT '省/州英文名',
    
    -- 二级行政区（市/县）
    city_zh VARCHAR(100) DEFAULT NULL COMMENT '市/县中文名',
    city_en VARCHAR(100) DEFAULT NULL COMMENT '市/县英文名',
    
    -- 三级行政区（区/县）
    district_zh VARCHAR(100) DEFAULT NULL COMMENT '区/县中文名',
    district_en VARCHAR(100) DEFAULT NULL COMMENT '区/县英文名',
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    KEY idx_coords (longitude, latitude),
    KEY idx_country (country_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='V3位置缓存：坐标对应三级行政区中英文';

-- 名称规范化说明（与客户端 LocationStorageService 一致）：
-- 1. trim 空格
-- 2. 去掉末尾：特别行政区、自治区、直辖市、地区、市、省、县、区、州、盟
-- 3. 英文去掉：Province、City、District、County 等
