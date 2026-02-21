-- ====================================
-- 修改 global_cities_v2 表的 data_source 字段
-- 添加 'llm' 选项（V3接口使用大模型查询）
-- ====================================

USE image_classifier;

-- 修改 data_source 字段，添加 'llm' 选项
ALTER TABLE global_cities_v2 
MODIFY COLUMN data_source ENUM('local', 'gaode', 'nominatim', 'llm') DEFAULT 'local' COMMENT '数据来源';

-- 验证修改结果
SELECT 'data_source 字段已更新，现在支持: local, gaode, nominatim, llm' AS 'Status';

-- 查看表结构确认
DESCRIBE global_cities_v2;
