-- 清理位置数据质量问题的SQL脚本
-- 注意：执行前请先备份数据库！

-- ===== 方案1：删除中国境内但数据来源不是高德的数据 =====
-- 这些数据可能是从 Nominatim 或 fallback 查询得到的，对于中国境内坐标不准确
-- 删除后，系统会重新调用高德 API 获取准确的中文名数据

-- 先查看要删除的数据数量（执行前先运行这个查询确认）
SELECT 
    data_source,
    COUNT(*) as count_to_delete
FROM global_cities_v2
WHERE country_code = 'CN'
  AND data_source != 'gaode'
GROUP BY data_source;

-- 确认后，执行删除（谨慎操作！）
-- DELETE FROM global_cities_v2
-- WHERE country_code = 'CN'
--   AND data_source != 'gaode';

-- ===== 方案2：删除中国境内但没有中文名映射的数据 =====
-- 这些数据可能是高德 API 返回的，但保存时没有正确保存中文名
-- 删除后，系统会重新调用高德 API 获取完整数据

-- 先查看要删除的数据数量
SELECT 
    data_source,
    COUNT(*) as count_to_delete
FROM global_cities_v2 gc
WHERE country_code = 'CN'
  AND NOT EXISTS (
      SELECT 1 FROM city_name_mapping cnm 
      WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
  )
GROUP BY data_source;

-- 确认后，执行删除（谨慎操作！）
-- DELETE gc FROM global_cities_v2 gc
-- WHERE country_code = 'CN'
--   AND NOT EXISTS (
--       SELECT 1 FROM city_name_mapping cnm 
--       WHERE cnm.name_en = gc.name_en COLLATE utf8mb4_unicode_ci
--   );

-- ===== 方案3：只删除特定坐标附近的数据（最安全） =====
-- 删除特定坐标附近的数据，让系统重新查询

-- 例如：删除坐标 22.643883, 113.799919 附近 3km 内的数据
-- 先查看要删除的数据
SELECT 
    id,
    name_en,
    latitude,
    longitude,
    data_source,
    ST_Distance_Sphere(
        POINT(longitude, latitude),
        POINT(113.799919, 22.643883)
    ) / 1000 AS distance_km
FROM global_cities_v2
WHERE ST_Distance_Sphere(
    POINT(longitude, latitude),
    POINT(113.799919, 22.643883)
) / 1000 <= 3;

-- 确认后，执行删除
-- DELETE FROM global_cities_v2
-- WHERE ST_Distance_Sphere(
--     POINT(longitude, latitude),
--     POINT(113.799919, 22.643883)
-- ) / 1000 <= 3;

-- ===== 推荐方案：组合方案 =====
-- 1. 先删除中国境内但数据来源不是高德的数据（这些数据不准确）
-- 2. 对于高德来源但没有中文名映射的数据，可以考虑保留（因为可能是高德 API 返回的问题）
--    或者也删除，让系统重新调用高德 API

-- 执行前请先运行检查脚本确认数据情况！


