-- ============================================
-- MySQL主从复制手工配置SQL语句
-- ============================================
-- 主库IP: 172.16.208.27
-- 从库IP: 172.16.46.125
-- 主库日志文件: binlog.000052
-- 主库日志位置: 1042
-- ============================================

-- ============================================
-- 步骤1：在主库（App服务器）创建复制用户
-- ============================================
-- 在App服务器上执行（使用classifier用户或root用户）：

-- 方式1：使用classifier用户（如果已有CREATE USER权限）
-- mysql -u classifier -p'Classifier@2024'

-- 方式2：使用root用户（推荐）
-- mysql -u root

-- 执行以下SQL：

-- 1. 删除已存在的复制用户（如果存在）
DROP USER IF EXISTS 'repl_user'@'%';

-- 2. 创建复制用户（使用脚本生成的密码）
CREATE USER 'repl_user'@'%' IDENTIFIED BY 'bG0OE6DR0IcMxDVb6rJDox5km';

-- 3. 授予复制权限
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';

-- 4. 刷新权限
FLUSH PRIVILEGES;

-- 5. 查看主库状态（确认日志文件和位置）
SHOW MASTER STATUS;
-- 应该显示：
-- File: binlog.000052
-- Position: 1042


-- ============================================
-- 步骤2：在从库（Web服务器）配置主从复制
-- ============================================
-- 在Web服务器上执行（使用classifier用户或root用户）：

-- 方式1：使用classifier用户
-- mysql -u classifier -p'Classifier@2024'

-- 方式2：使用root用户（推荐）
-- mysql -u root

-- 执行以下SQL：

-- 1. 停止从库（如果已经在运行）
STOP SLAVE;

-- 2. 配置主库信息
-- 注意：MASTER_PASSWORD请使用步骤1中设置的密码
CHANGE MASTER TO
    MASTER_HOST='172.16.208.27',
    MASTER_USER='repl_user',
    MASTER_PASSWORD='bG0OE6DR0IcMxDVb6rJDox5km',
    MASTER_LOG_FILE='binlog.000052',
    MASTER_LOG_POS=1042;

-- 3. 启动从库
START SLAVE;

-- 4. 查看从库状态
SHOW SLAVE STATUS\G;

-- 检查关键字段：
-- Slave_IO_Running: 应该是 Yes
-- Slave_SQL_Running: 应该是 Yes
-- Seconds_Behind_Master: 延迟秒数（应该接近0）
-- Last_Error: 应该是空的（如果有错误会显示在这里）


-- ============================================
-- 如果遇到错误，可以重置从库
-- ============================================
-- 在从库上执行：
-- STOP SLAVE;
-- RESET SLAVE;
-- 然后重新执行步骤2的CHANGE MASTER和START SLAVE

