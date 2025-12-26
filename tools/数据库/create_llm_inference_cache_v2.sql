-- ====================================
-- 创建统一大模型推理缓存表（v2版本）
-- 支持分类服务和编辑服务
-- 支持多模型结果集合
-- ====================================

USE image_classifier;

CREATE TABLE IF NOT EXISTS `llm_inference_cache_v2` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 统一缓存Key（prompt_hash + image_hash）
  `prompt_hash` VARCHAR(64) NOT NULL COMMENT '提示词SHA-256哈希（分类服务：纯prompt；编辑服务：edit_type:prompt）',
  `image_hash` VARCHAR(64) NOT NULL COMMENT '图像SHA-256哈希',
  
  -- 多模型结果集合（JSON，灵活扩展）
  `model_results` JSON NOT NULL COMMENT '多模型推理结果集合',
  /*
  JSON结构示例：
  {
    "aliyun:qwen-vl-plus": {
      "result": {...},  // 分类结果dict或编辑结果URL字符串
      "service_type": "classification" | "image_edit",  // 业务类型（可选，用于统计）
      "edit_type": "remove" | null,  // 编辑类型（可选，仅编辑服务）
      "created_at": "2025-12-26T10:00:00",
      "cost": 0.01,
      "processing_time_ms": 1200,
      "status": "success",
      ...
    },
    "openai:gpt-4-vision": {
      "result": {...},
      "created_at": "2025-12-26T10:05:00",
      ...
    }
  }
  */
  
  -- 统计字段
  `total_models` INT UNSIGNED DEFAULT 1 COMMENT '已缓存的模型数量',
  `hit_count` INT UNSIGNED DEFAULT 1 COMMENT '缓存命中次数',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `last_hit_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prompt_image` (`prompt_hash`, `image_hash`) COMMENT '组合唯一索引（prompt_hash + image_hash）',
  KEY `idx_prompt_hash` (`prompt_hash`) COMMENT '提示词哈希索引',
  KEY `idx_image_hash` (`image_hash`) COMMENT '图像哈希索引',
  KEY `idx_hit_count` (`hit_count`) COMMENT '命中次数索引',
  KEY `idx_last_hit` (`last_hit_at`) COMMENT '最后命中时间索引',
  KEY `idx_created_at` (`created_at`) COMMENT '创建时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='统一大模型推理缓存表（v2版本，支持分类和编辑服务，多模型结果集合）';

-- 显示创建结果
SELECT 'llm_inference_cache_v2 表创建完成！' AS 'Status';

