-- 批量分类统计表
CREATE TABLE IF NOT EXISTS batch_classify_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    request_id VARCHAR(50) NOT NULL COMMENT '请求ID',
    user_id VARCHAR(100) COMMENT '用户ID',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    total_count INT NOT NULL COMMENT '图片总数',
    success_count INT NOT NULL COMMENT '成功数',
    fail_count INT NOT NULL COMMENT '失败数',
    total_processing_time_ms INT NOT NULL COMMENT '总处理耗时(毫秒)',
    avg_processing_time_ms DECIMAL(10,2) AS (total_processing_time_ms / total_count) STORED COMMENT '平均处理耗时',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_date DATE AS (DATE(created_at)) STORED COMMENT '创建日期',
    INDEX idx_created_date (created_date),
    INDEX idx_request_id (request_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批量分类统计';

