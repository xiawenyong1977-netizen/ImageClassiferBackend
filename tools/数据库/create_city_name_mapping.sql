-- ====================================
-- 创建城市名称中英文映射表
-- 用于v2版本地理位置查询
-- ====================================

USE image_classifier;

-- 创建映射表
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 
COMMENT='全球城市名称中英文映射表';

-- 显示创建结果
SELECT '城市名称映射表创建完成！' AS 'Status';
SELECT COUNT(*) AS '当前记录数' FROM city_name_mapping;

