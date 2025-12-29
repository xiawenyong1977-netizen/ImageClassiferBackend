-- ====================================
-- 从 global_cities 迁移数据到 global_cities_v2
-- ====================================

USE image_classifier;

-- 开始迁移
SELECT '开始迁移数据...' AS 'Status';

-- 迁移数据（从v1表到v2表）
INSERT INTO global_cities_v2 (
    name_en,
    name_zh,
    latitude,
    longitude,
    country_code,
    admin1_code,
    admin2_code,
    geoname_id,
    feature_code,
    population,
    data_source,
    created_at,
    updated_at
)
SELECT 
    COALESCE(ascii_name, name) AS name_en,  -- 优先使用ascii_name，如果没有则使用name
    name_zh,
    latitude,
    longitude,
    country_code,
    admin1_code,
    admin2_code,
    geoname_id,
    feature_code,
    population,
    'local' AS data_source,  -- 标记为本地数据
    created_at,
    updated_at
FROM global_cities
WHERE geoname_id IS NOT NULL  -- 只迁移有geoname_id的记录（确保唯一性）
ON DUPLICATE KEY UPDATE
    name_en = VALUES(name_en),
    name_zh = VALUES(name_zh),
    latitude = VALUES(latitude),
    longitude = VALUES(longitude),
    country_code = VALUES(country_code),
    admin1_code = VALUES(admin1_code),
    admin2_code = VALUES(admin2_code),
    feature_code = VALUES(feature_code),
    population = VALUES(population),
    updated_at = CURRENT_TIMESTAMP;

-- 显示迁移结果
SELECT 
    (SELECT COUNT(*) FROM global_cities) AS 'v1表记录数',
    (SELECT COUNT(*) FROM global_cities_v2) AS 'v2表记录数',
    (SELECT COUNT(*) FROM global_cities_v2 WHERE data_source = 'local') AS '本地数据记录数';

-- 检查数据完整性
SELECT 
    '数据完整性检查' AS 'Check',
    COUNT(*) AS '总记录数',
    COUNT(DISTINCT geoname_id) AS '唯一geoname_id数',
    COUNT(DISTINCT name_en) AS '唯一英文名数',
    SUM(CASE WHEN name_zh IS NOT NULL THEN 1 ELSE 0 END) AS '有中文名记录数',
    SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) AS '有坐标记录数'
FROM global_cities_v2;

SELECT '数据迁移完成！' AS 'Status';

