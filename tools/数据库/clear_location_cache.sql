-- ============================================================
-- 清空服务器端位置缓存
-- 执行后：客户端需卸载重装以清空 IndexedDB/SQLite 缓存
-- ============================================================
-- 执行前请备份数据库！V3 需先执行 create_location_cache_v3.sql
-- mysql -u root -p image_classifier < clear_location_cache.sql
-- ============================================================

USE image_classifier;

-- V3 位置缓存（单表，三级行政区中英文）
TRUNCATE TABLE location_cache_v3;
SELECT 'location_cache_v3 已清空' AS status;

-- 旧表（v2 使用，可选）
-- TRUNCATE TABLE global_cities_v2;
