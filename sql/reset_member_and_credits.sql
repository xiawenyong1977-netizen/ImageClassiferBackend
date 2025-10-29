-- 重置会员状态和额度
-- 将所有用户的会员状态设为非会员，并将额度重置为初始值

UPDATE `wechat_users` 
SET 
    `is_member` = 0,
    `member_expire_at` = NULL,
    `total_credits` = 100,
    `used_credits` = 0,
    `remaining_credits` = 100,
    `updated_at` = NOW()
WHERE `openid` = 'okbfi1wlkjqhkaHYIYKUxwJe66P8';

SELECT '会员状态和额度已重置' AS 'Status';

