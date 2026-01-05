-- 清理中国境内但数据来源是 local 的数据
-- 这些数据主要是英文名，对中国境内坐标不准确
-- 删除后，系统会重新调用高德 API 获取准确的中文名数据

-- ===== 第一步：查看要删除的数据统计 =====
-- 执行前先运行这个查询，确认要删除的数据量

-- 1. 统计要删除的数据量（按省份/城市分组）
SELECT 
    province,
    city,
    COUNT(*) as count,
    MIN(latitude) as min_lat,
    MAX(latitude) as max_lat,
    MIN(longitude) as min_lon,
    MAX(longitude) as max_lon
FROM global_cities_v2
WHERE country_code = 'CN'
  AND data_source = 'local'
GROUP BY province, city
ORDER BY count DESC
LIMIT 50;

-- 2. 统计总数
SELECT 
    COUNT(*) as total_to_delete,
    COUNT(DISTINCT CONCAT(latitude, ',', longitude)) as unique_locations
FROM global_cities_v2
WHERE country_code = 'CN'
  AND data_source = 'local';

-- 3. 查看特定坐标附近的数据（用于确认）
SELECT 
    id,
    name_en,
    latitude,
    longitude,
    data_source,
    api_adcode,
    ST_Distance_Sphere(
        POINT(longitude, latitude),
        POINT(113.799919, 22.643883)
    ) / 1000 AS distance_km
FROM global_cities_v2
WHERE ST_Distance_Sphere(
    POINT(longitude, latitude),
    POINT(113.799919, 22.643883)
) / 1000 <= 5
ORDER BY distance_km;

-- ===== 第二步：执行删除（谨慎操作！） =====
-- 确认数据量后，取消下面的注释执行删除

-- 方案1：删除所有中国境内但数据来源是 local 的数据（推荐）
-- 这样可以确保所有中国境内的坐标都使用高德 API 获取准确的中文名
-- DELETE FROM global_cities_v2
-- WHERE country_code = 'CN'
--   AND data_source = 'local';

-- 方案2：只删除特定坐标附近的数据（更安全，适合测试）
-- 例如：删除坐标 22.643883, 113.799919 附近 3km 内的 local 数据
-- DELETE FROM global_cities_v2
-- WHERE country_code = 'CN'
--   AND data_source = 'local'
--   AND ST_Distance_Sphere(
--       POINT(longitude, latitude),
--       POINT(113.799919, 22.643883)
--   ) / 1000 <= 3;

-- 方案3：保留有中文名映射的数据，只删除没有中文名映射的数据
-- DELETE gc FROM global_cities_v2 gc
-- WHERE country_code = 'CN'
--   AND data_source = 'local'
--   AND NOT EXISTS (
--       SELECT 1 FROM city_name_mapping cnm 
--       WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
--   );

-- ===== 第三步：验证删除结果 =====
-- 删除后，运行以下查询验证

-- 1. 查看剩余的中国境内 local 数据数量
SELECT COUNT(*) as remaining_local_cn_data
FROM global_cities_v2
WHERE country_code = 'CN'
  AND data_source = 'local';

-- 2. 查看高德 API 来源的数据数量（应该保持不变）
SELECT COUNT(*) as gaode_cn_data
FROM global_cities_v2
WHERE country_code = 'CN'
  AND data_source = 'gaode';

-- ===== 注意事项 =====
-- 1. 执行删除前请先备份数据库！
-- 2. 建议先在测试环境验证
-- 3. 删除后，下次查询这些坐标时会重新调用高德 API，可能需要一些时间
-- 4. 高德 API 有频率限制（30/s），大量坐标可能需要分批处理


