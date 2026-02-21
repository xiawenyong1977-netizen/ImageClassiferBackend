-- 修改 global_cities_v2 表的 data_source 字段，添加 'llm' 选项
USE image_classifier;

ALTER TABLE global_cities_v2 
MODIFY COLUMN data_source ENUM('local', 'gaode', 'nominatim', 'llm') DEFAULT 'local' COMMENT '数据来源';

SELECT 'data_source 字段已更新，现在支持: local, gaode, nominatim, llm' AS 'Status';
