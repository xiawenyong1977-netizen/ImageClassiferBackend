-- 检查位置数据质量
-- 用于分析 global_cities_v2 表中的数据来源和中文名覆盖情况

-- 1. 统计各数据来源的数量
SELECT 
    data_source,
    COUNT(*) as total_count,
    COUNT(CASE WHEN name_en IS NOT NULL AND name_en != '' THEN 1 END) as has_name_en,
    COUNT(CASE WHEN EXISTS (
        SELECT 1 FROM city_name_mapping cnm 
        WHERE cnm.name_en = global_cities_v2.name_en COLLATE utf8mb4_unicode_ci
    ) THEN 1 END) as has_name_zh_mapping
FROM global_cities_v2
GROUP BY data_source
ORDER BY total_count DESC;

-- 2. 查找中国境内（CN）但没有中文名映射的数据
SELECT 
    id,
    name_en,
    latitude,
    longitude,
    country_code,
    data_source,
    api_adcode,
    api_city_id,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM city_name_mapping cnm 
            WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
        ) THEN '有映射'
        ELSE '无映射'
    END as has_chinese_mapping
FROM global_cities_v2 gc
WHERE country_code = 'CN'
  AND NOT EXISTS (
      SELECT 1 FROM city_name_mapping cnm 
      WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
  )
ORDER BY latitude, longitude
LIMIT 100;

-- 3. 统计中国境内数据的数据来源分布
SELECT 
    data_source,
    COUNT(*) as total,
    COUNT(CASE WHEN EXISTS (
        SELECT 1 FROM city_name_mapping cnm 
        WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
    ) THEN 1 END) as with_chinese,
    COUNT(CASE WHEN NOT EXISTS (
        SELECT 1 FROM city_name_mapping cnm 
        WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
    ) THEN 1 END) as without_chinese
FROM global_cities_v2 gc
WHERE country_code = 'CN'
GROUP BY data_source
ORDER BY total DESC;

-- 4. 查找特定坐标附近的数据（用于调试）
-- 坐标：22.643883, 113.799919（深圳下沙）
SELECT 
    id,
    name_en,
    latitude,
    longitude,
    country_code,
    data_source,
    api_adcode,
    api_city_id,
    ST_Distance_Sphere(
        POINT(longitude, latitude),
        POINT(113.799919, 22.643883)
    ) / 1000 AS distance_km,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM city_name_mapping cnm 
            WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
        ) THEN '有映射'
        ELSE '无映射'
    END as has_chinese_mapping
FROM global_cities_v2 gc
WHERE ST_Distance_Sphere(
    POINT(longitude, latitude),
    POINT(113.799919, 22.643883)
) / 1000 <= 5  -- 5km范围内
ORDER BY distance_km
LIMIT 10;


