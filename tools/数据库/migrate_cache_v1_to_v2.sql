-- ====================================
-- 将v1版本的缓存数据迁移到v2版本
-- 从 image_classification_cache 迁移到 llm_inference_cache_v2
-- ====================================

USE image_classifier;

-- 步骤1: 创建v2表（如果不存在）
CREATE TABLE IF NOT EXISTS `llm_inference_cache_v2` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `prompt_hash` VARCHAR(64) NOT NULL COMMENT '提示词SHA-256哈希（分类服务：纯prompt；编辑服务：edit_type:prompt）',
  `image_hash` VARCHAR(64) NOT NULL COMMENT '图像SHA-256哈希',
  `cache_key` VARCHAR(128) NOT NULL COMMENT '完整缓存Key（prompt_hash:image_hash）',
  `model_results` JSON NOT NULL COMMENT '多模型推理结果集合',
  `total_models` INT UNSIGNED DEFAULT 1 COMMENT '已缓存的模型数量',
  `hit_count` INT UNSIGNED DEFAULT 1 COMMENT '缓存命中次数',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `last_hit_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cache_key` (`cache_key`) COMMENT '缓存Key唯一索引',
  KEY `idx_prompt_hash` (`prompt_hash`) COMMENT '提示词哈希索引',
  KEY `idx_image_hash` (`image_hash`) COMMENT '图像哈希索引',
  KEY `idx_hit_count` (`hit_count`) COMMENT '命中次数索引',
  KEY `idx_last_hit` (`last_hit_at`) COMMENT '最后命中时间索引',
  KEY `idx_created_at` (`created_at`) COMMENT '创建时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='统一大模型推理缓存表（v2版本，支持分类和编辑服务，多模型结果集合）';

-- 步骤2: 检查v1表是否存在数据
SELECT 
    COUNT(*) as v1_total_count,
    'v1表数据总数' as info
FROM image_classification_cache;

-- 步骤3: 迁移数据
-- 注意：需要从环境变量或配置中获取 CLASSIFICATION_PROMPT 来计算 prompt_hash
-- 这里使用一个临时变量来存储prompt（实际执行时需要替换为真实的prompt）

-- 设置分类服务的prompt（需要从配置中获取，这里使用占位符）
-- 实际执行时，需要从应用配置中获取 CLASSIFICATION_PROMPT 的值
SET @classification_prompt = '请对这张图片进行分类。你必须从以下8个类别中选择一个：\n\n1. social_activities - 社交活动（聚会、合影、多人互动场景）\n2. pets - 宠物萌照（猫、狗等宠物照片）\n3. single_person - 单人照片（个人照、自拍、肖像）\n4. foods - 美食记录（食物、餐饮、烹饪相关）\n5. travel_scenery - 旅行风景（旅游景点、自然风光、城市风景）\n6. screenshot - 手机截图（手机屏幕截图、应用界面）\n7. idcard - 证件照（身份证、护照、驾照等证件）\n8. other - 其它（无法归类到上述类别）\n\n同时，请识别照片背景的主要颜色。背景颜色必须从以下10种颜色中选择一个：\n橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色\n\n请以JSON格式返回结果：\n{\n    "category": "类别key（必须是上述8个之一）",\n    "confidence": 0.95,\n    "description": "简短描述图片内容（可选，中文，30字以内）",\n    "background_color": "背景颜色（必须是：橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色之一）"\n}\n\n只返回JSON，不要有其他文字。';

-- 计算prompt_hash（使用SHA2函数）
SET @prompt_hash = UPPER(SHA2(@classification_prompt, 256));

-- 迁移数据：将v1数据转换为v2格式
INSERT INTO llm_inference_cache_v2 (
    prompt_hash,
    image_hash,
    cache_key,
    model_results,
    total_models,
    hit_count,
    created_at,
    last_hit_at
)
SELECT 
    @prompt_hash as prompt_hash,
    v1.image_hash,
    CONCAT(@prompt_hash, ':', v1.image_hash) as cache_key,
    -- 构建JSON格式的model_results
    JSON_OBJECT(
        -- 使用model_used作为模型key，如果格式不是provider:model，则使用默认格式
        CASE 
            WHEN v1.model_used LIKE '%:%' THEN v1.model_used
            ELSE CONCAT('aliyun:', v1.model_used)
        END,
        JSON_OBJECT(
            'result', JSON_OBJECT(
                'category', v1.category,
                'confidence', CAST(v1.confidence AS DECIMAL(5,4)),
                'description', COALESCE(v1.description, ''),
                'background_color', v1.background_color
            ),
            'service_type', 'classification',
            'created_at', DATE_FORMAT(v1.created_at, '%Y-%m-%dT%H:%i:%s'),
            'status', 'success',
            'model_used', v1.model_used,
            'hit_count', v1.hit_count
        )
    ) as model_results,
    1 as total_models,
    v1.hit_count,
    v1.created_at,
    COALESCE(v1.last_hit_at, v1.created_at) as last_hit_at
FROM image_classification_cache v1
WHERE NOT EXISTS (
    -- 避免重复插入（如果v2表中已存在相同的cache_key）
    SELECT 1 FROM llm_inference_cache_v2 v2 
    WHERE v2.cache_key = CONCAT(@prompt_hash, ':', v1.image_hash)
)
ON DUPLICATE KEY UPDATE
    -- 如果cache_key已存在，更新hit_count（取较大值）和last_hit_at
    hit_count = GREATEST(llm_inference_cache_v2.hit_count, VALUES(hit_count)),
    last_hit_at = GREATEST(llm_inference_cache_v2.last_hit_at, VALUES(last_hit_at)),
    updated_at = NOW();

-- 步骤4: 验证迁移结果
SELECT 
    (SELECT COUNT(*) FROM image_classification_cache) as v1_count,
    (SELECT COUNT(*) FROM llm_inference_cache_v2) as v2_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM image_classification_cache) = (SELECT COUNT(*) FROM llm_inference_cache_v2) 
        THEN '迁移成功：数据量一致'
        ELSE CONCAT('警告：数据量不一致，v1=', (SELECT COUNT(*) FROM image_classification_cache), ', v2=', (SELECT COUNT(*) FROM llm_inference_cache_v2))
    END as migration_status;

-- 步骤5: 显示迁移统计
SELECT 
    '迁移完成统计' as info,
    (SELECT COUNT(*) FROM image_classification_cache) as v1_total,
    (SELECT COUNT(*) FROM llm_inference_cache_v2) as v2_total,
    (SELECT SUM(hit_count) FROM image_classification_cache) as v1_total_hits,
    (SELECT SUM(hit_count) FROM llm_inference_cache_v2) as v2_total_hits;

