-- ====================================
-- 将 user_photos 表 image_uri 字段改为 TEXT 类型
-- 解决某些图片 URI 过长的问题（特别是 base64 编码的图片数据）
-- 
-- 注意：由于 image_uri 字段上有索引，需要先删除索引，修改字段类型，然后重新创建前缀索引
-- ====================================

USE image_classifier;

-- 1. 删除原有的 image_uri 索引
ALTER TABLE `user_photos` DROP INDEX `idx_image_uri`;

-- 2. 修改 image_uri 字段类型为 TEXT（可以存储更长的数据）
ALTER TABLE `user_photos` 
MODIFY COLUMN `image_uri` TEXT DEFAULT NULL COMMENT '图片URI（客户端传入，用于客户端查询和对账）';

-- 3. 重新创建前缀索引（只索引前 255 个字符，避免索引长度超过 MySQL 限制）
-- UTF8MB4 字符集下，每个字符最多 4 字节，255 * 4 = 1020 字节 < 3072 字节限制
ALTER TABLE `user_photos` 
ADD KEY `idx_image_uri` (`image_uri`(255)) COMMENT '图片URI索引（前缀索引，用于客户端查询）';

-- 显示更新结果
SELECT 'user_photos 表 image_uri 字段已改为 TEXT 类型，索引已更新为前缀索引！' AS 'Status';

