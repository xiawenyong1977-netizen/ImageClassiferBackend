#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成管理员密码的bcrypt哈希值
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 生成密码哈希
password = "zywl@123"
hashed = pwd_context.hash(password)

print(f"原始密码: {password}")
print(f"密码哈希: {hashed}")
print(f"\n请将以下内容添加到服务器的 .env 文件:")
print(f"ADMIN_PASSWORD_HASH={hashed}")

# 验证
if pwd_context.verify(password, hashed):
    print("\n✓ 哈希验证成功！")
else:
    print("\n✗ 哈希验证失败！")

