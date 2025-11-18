-- 批量缓存查询统计表
CREATE TABLE IF NOT EXISTS batch_cache_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    request_id VARCHAR(50) NOT NULL COMMENT '请求ID',
    user_id VARCHAR(100) COMMENT '用户ID',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    total_count INT NOT NULL COMMENT '查询总数',
    cached_count INT NOT NULL COMMENT '缓存命中数',
    miss_count INT NOT NULL COMMENT '缓存未命中数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_date DATE AS (DATE(created_at)) STORED COMMENT '创建日期',
    INDEX idx_created_date (created_date),
    INDEX idx_request_id (request_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批量缓存查询统计';

