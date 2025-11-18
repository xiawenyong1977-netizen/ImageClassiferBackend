-- 将scene_id字段类型改回INT，支持整数类型
ALTER TABLE `wechat_qrcode_bindings` 
MODIFY COLUMN `scene_id` INT NOT NULL COMMENT '二维码场景值（整数格式）';
