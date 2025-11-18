-- 添加推理方式字段到request_log表
-- 用于统计大模型失败和本地推理调用次数

-- 添加inference_method字段
ALTER TABLE request_log 
ADD COLUMN inference_method VARCHAR(20) DEFAULT 'llm' COMMENT '推理方式: llm/local/llm_fallback/local_fallback';

-- 添加索引以提高查询性能
CREATE INDEX idx_inference_method ON request_log(inference_method);
CREATE INDEX idx_created_date_method ON request_log(created_date, inference_method);

-- 查看表结构
DESC request_log;

