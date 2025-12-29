-- ====================================
-- 创建地理位置查询外部API调用统计表（v2版本）
-- 只记录外部API调用次数，不记录详细查询日志
-- ====================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS location_api_call_stats (
    -- 主键
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    
    -- 统计维度
    stat_date DATE NOT NULL COMMENT '统计日期',
    api_provider ENUM('gaode', 'nominatim') NOT NULL COMMENT 'API提供商（高德/Nominatim）',
    
    -- 调用统计
    total_calls INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '总调用次数',
    success_calls INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '成功调用次数',
    failed_calls INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '失败调用次数',
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (id),
    
    -- 唯一索引：确保每天每个API只有一条记录
    UNIQUE KEY uk_date_provider (stat_date, api_provider) COMMENT '日期+提供商唯一索引',
    
    -- 查询索引
    KEY idx_stat_date (stat_date) COMMENT '日期索引（用于按日期查询）',
    KEY idx_api_provider (api_provider) COMMENT 'API提供商索引',
    KEY idx_date_provider (stat_date, api_provider) COMMENT '日期+提供商复合索引'
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='地理位置查询外部API调用统计表（v2版本）';

-- 显示创建结果
SELECT 'location_api_call_stats 表创建完成！' AS 'Status';
SELECT COUNT(*) AS '当前记录数' FROM location_api_call_stats;

