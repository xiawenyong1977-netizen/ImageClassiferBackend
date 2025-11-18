-- 支付相关表设计

-- 1. 订单表
CREATE TABLE IF NOT EXISTS `payment_orders` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_no` VARCHAR(64) NOT NULL COMMENT '订单号',
  `openid` VARCHAR(64) NOT NULL COMMENT '用户openid',
  `order_type` ENUM('member', 'credits') NOT NULL COMMENT '订单类型：member-会员开通，credits-额度购买',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '订单金额（元）',
  `credits_amount` INT DEFAULT NULL COMMENT '额度数量（仅type=credits时有效）',
  `status` ENUM('pending', 'paid', 'refunded', 'failed') DEFAULT 'pending' COMMENT '订单状态',
  `wx_payment_no` VARCHAR(64) DEFAULT NULL COMMENT '微信支付订单号',
  `wx_transaction_id` VARCHAR(64) DEFAULT NULL COMMENT '微信支付交易号',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `paid_at` TIMESTAMP NULL DEFAULT NULL COMMENT '支付时间',
  `expire_at` TIMESTAMP NULL DEFAULT NULL COMMENT '过期时间（未支付订单过期）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_openid` (`openid`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付订单表';

-- 2. 会员表（扩展wechat_users表）
ALTER TABLE `wechat_users` 
  ADD COLUMN `is_member` TINYINT(1) DEFAULT 0 COMMENT '是否会员' AFTER `unionid`,
  ADD COLUMN `member_expire_at` TIMESTAMP NULL DEFAULT NULL COMMENT '会员过期时间' AFTER `is_member`,
  ADD COLUMN `total_paid_amount` DECIMAL(10,2) DEFAULT 0 COMMENT '累计支付金额' AFTER `member_expire_at`;

-- 3. 支付记录表（用于对账）
CREATE TABLE IF NOT EXISTS `payment_records` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_no` VARCHAR(64) NOT NULL COMMENT '订单号',
  `openid` VARCHAR(64) NOT NULL COMMENT '用户openid',
  `transaction_id` VARCHAR(64) NOT NULL COMMENT '微信交易号',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '支付金额',
  `payment_method` VARCHAR(32) DEFAULT 'wechat_pay' COMMENT '支付方式',
  `payment_time` TIMESTAMP NOT NULL COMMENT '支付时间',
  `notify_data` TEXT COMMENT '微信回调原始数据',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_transaction_id` (`transaction_id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_openid` (`openid`),
  KEY `idx_payment_time` (`payment_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付记录表';

