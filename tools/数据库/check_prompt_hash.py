#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查提示词哈希"""

import sys
import os
import hashlib
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.config import settings

def main():
    # 加载环境变量
    load_dotenv()
    
    # 获取提示词
    prompt = settings.CLASSIFICATION_PROMPT
    
    # 计算哈希
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    
    print("=" * 60)
    print("提示词哈希检查")
    print("=" * 60)
    print(f"提示词长度: {len(prompt)} 字符")
    print(f"提示词哈希: {prompt_hash}")
    print(f"提示词前100字符: {prompt[:100]}...")
    print("=" * 60)

if __name__ == "__main__":
    main()

