#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库中使用的模型名称"""

import sys
import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'image_classifier'),
        'charset': 'utf8mb4'
    }
    
    conn = pymysql.connect(**db_config, cursorclass=DictCursor)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("检查分类服务使用的模型")
    print("=" * 60)
    cursor.execute("SELECT DISTINCT model_used FROM image_classification_cache LIMIT 10")
    models = cursor.fetchall()
    for m in models:
        print(f"  - {m['model_used']}")
    
    print("\n" + "=" * 60)
    print("检查编辑服务使用的编辑类型")
    print("=" * 60)
    cursor.execute("SELECT DISTINCT edit_type FROM image_edit_cache LIMIT 10")
    edit_types = cursor.fetchall()
    for e in edit_types:
        print(f"  - {e['edit_type']}")
    
    print("\n" + "=" * 60)
    print("检查v2表中已迁移的模型")
    print("=" * 60)
    cursor.execute("""
        SELECT 
            JSON_KEYS(model_results) as model_keys,
            COUNT(*) as count
        FROM llm_inference_cache_v2
        GROUP BY JSON_KEYS(model_results)
        LIMIT 10
    """)
    v2_models = cursor.fetchall()
    for m in v2_models:
        print(f"  - {m['model_keys']}: {m['count']} 条")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

