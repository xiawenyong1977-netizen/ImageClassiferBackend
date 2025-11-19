#!/bin/bash
# 授予classifier用户必要的权限

echo "在App服务器上授予权限..."
ssh root@app bash <<'EOF'
mysql -u root <<SQL
GRANT CREATE USER, REPLICATION SLAVE, RELOAD, PROCESS, SELECT ON *.* TO 'classifier'@'localhost';
FLUSH PRIVILEGES;
SQL
EOF

echo "在Web服务器上授予权限..."
mysql -u root <<SQL
GRANT CREATE USER, REPLICATION SLAVE, RELOAD, PROCESS, SELECT ON *.* TO 'classifier'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "权限授予完成"
