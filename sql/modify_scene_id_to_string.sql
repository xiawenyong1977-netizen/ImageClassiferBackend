-- 修改scene_id字段类型为VARCHAR，支持字符串类型
ALTER TABLE `wechat_qrcode_bindings` 
MODIFY COLUMN `scene_id` VARCHAR(128) NOT NULL COMMENT '二维码场景值（字符串格式）';
