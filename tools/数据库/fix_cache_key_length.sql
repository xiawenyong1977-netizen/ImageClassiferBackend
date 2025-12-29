-- 修复 cache_key 字段长度
ALTER TABLE llm_inference_cache_v2 
MODIFY COLUMN cache_key VARCHAR(129) NOT NULL 
COMMENT '完整缓存Key（prompt_hash:image_hash，64+1+64=129字符）';

