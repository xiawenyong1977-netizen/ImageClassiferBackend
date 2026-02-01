-- 根据 client_id 查询 openid 并取消会员状态
-- 使用方法：替换下面的 client_id 值后执行

SET @client_id = 'd2dca4de-8de1-496f-84c7-1710a0e7263a';

-- 1. 查询该 client_id 对应的 openid 和当前会员状态
SELECT 
    b.client_id,
    b.openid,
    b.status,
    b.completed_at,
    u.is_member,
    u.member_expire_at,
    u.total_credits,
    u.remaining_credits,
    u.nickname
FROM wechat_qrcode_bindings b
LEFT JOIN wechat_users u ON b.openid = u.openid
WHERE b.client_id = @client_id 
  AND b.openid IS NOT NULL
ORDER BY b.completed_at DESC, b.id DESC
LIMIT 1;

-- 2. 取消会员状态（使用 JOIN 方式更新，更可靠）
UPDATE wechat_users u
INNER JOIN (
    SELECT openid 
    FROM wechat_qrcode_bindings 
    WHERE client_id = @client_id 
      AND openid IS NOT NULL 
    ORDER BY completed_at DESC, id DESC 
    LIMIT 1
) b ON u.openid = b.openid
SET 
    u.is_member = 0,
    u.member_expire_at = NULL,
    u.updated_at = NOW();

-- 3. 验证更新结果
SELECT 
    u.openid,
    u.is_member,
    u.member_expire_at,
    u.total_credits,
    u.remaining_credits,
    u.updated_at,
    u.nickname
FROM wechat_users u
INNER JOIN (
    SELECT openid 
    FROM wechat_qrcode_bindings 
    WHERE client_id = @client_id 
      AND openid IS NOT NULL 
    ORDER BY completed_at DESC, id DESC 
    LIMIT 1
) b ON u.openid = b.openid;

SELECT CONCAT('会员状态已取消，openid: ', (
    SELECT openid 
    FROM wechat_qrcode_bindings 
    WHERE client_id = @client_id 
      AND openid IS NOT NULL 
    ORDER BY completed_at DESC, id DESC 
    LIMIT 1
)) AS 'Status';
