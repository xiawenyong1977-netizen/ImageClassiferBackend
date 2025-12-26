#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将image_edit_cache表的数据迁移到llm_inference_cache_v2表
"""

import sys
import os
import hashlib
import json
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
from dotenv import load_dotenv


def calculate_prompt_hash(edit_type: str, prompt: str) -> str:
    """
    计算编辑服务的prompt哈希
    格式: edit_type:prompt
    """
    prompt_str = f"{edit_type}:{prompt}"
    return hashlib.sha256(prompt_str.encode('utf-8')).hexdigest()


def get_v1_data_count(cursor):
    """获取image_edit_cache表的数据总数"""
    cursor.execute("SELECT COUNT(*) as count FROM image_edit_cache")
    result = cursor.fetchone()
    return result['count'] if result else 0


def migrate_data(conn, cursor, batch_size: int = 1000):
    """迁移数据从image_edit_cache到llm_inference_cache_v2"""
    
    # 获取v1数据总数
    total_count = get_v1_data_count(cursor)
    print(f"📊 image_edit_cache表数据总数: {total_count}")
    
    if total_count == 0:
        print("⚠️  image_edit_cache表没有数据，无需迁移")
        return
    
    # 分批迁移
    offset = 0
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    while offset < total_count:
        # 获取一批v1数据
        cursor.execute("""
            SELECT 
                image_hash,
                edit_type,
                prompt,
                result_url,
                hit_count,
                created_at,
                last_hit_at
            FROM image_edit_cache
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (batch_size, offset))
        
        v1_records = cursor.fetchall()
        
        if not v1_records:
            break
        
        # 处理每一条记录
        for v1_record in v1_records:
            try:
                image_hash = v1_record['image_hash']
                edit_type = v1_record['edit_type']
                prompt = v1_record['prompt']
                
                # 计算prompt_hash（格式: edit_type:prompt）
                prompt_hash = calculate_prompt_hash(edit_type, prompt)
                
                # 检查是否已存在（使用组合键查询）
                cursor.execute(
                    "SELECT id FROM llm_inference_cache_v2 WHERE prompt_hash = %s AND image_hash = %s",
                    (prompt_hash, image_hash)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # 已存在，更新hit_count和last_hit_at
                    last_hit = v1_record['last_hit_at'] if v1_record['last_hit_at'] else v1_record['created_at']
                    cursor.execute("""
                        UPDATE llm_inference_cache_v2
                        SET 
                            hit_count = GREATEST(hit_count, %s),
                            last_hit_at = GREATEST(last_hit_at, %s),
                            updated_at = NOW()
                        WHERE prompt_hash = %s AND image_hash = %s
                    """, (
                        v1_record['hit_count'],
                        last_hit,
                        prompt_hash,
                        image_hash
                    ))
                    skipped_count += 1
                else:
                    # 构建模型key（编辑服务使用 qwen-image-edit）
                    model_key = "aliyun:qwen-image-edit"
                    
                    # 构建result对象（编辑服务的结果是URL字符串）
                    result_url = v1_record['result_url']
                    
                    # 处理时间格式
                    created_at = v1_record['created_at']
                    if isinstance(created_at, datetime):
                        created_at_str = created_at.isoformat()
                    else:
                        created_at_str = str(created_at)
                    
                    # 构建model_results JSON
                    model_result = {
                        "result": result_url,  # 编辑服务的结果是URL字符串
                        "service_type": "image_edit",
                        "edit_type": edit_type,
                        "created_at": created_at_str,
                        "status": "success",
                        "hit_count": v1_record['hit_count']
                    }
                    
                    model_results = {model_key: model_result}
                    
                    last_hit = v1_record['last_hit_at'] if v1_record['last_hit_at'] else v1_record['created_at']
                    
                    # 插入v2表
                    cursor.execute("""
                        INSERT INTO llm_inference_cache_v2 (
                            prompt_hash,
                            image_hash,
                            model_results,
                            total_models,
                            hit_count,
                            created_at,
                            last_hit_at
                        ) VALUES (%s, %s, %s, 1, %s, %s, %s)
                    """, (
                        prompt_hash,
                        image_hash,
                        json.dumps(model_results, ensure_ascii=False),
                        v1_record['hit_count'],
                        v1_record['created_at'],
                        last_hit
                    ))
                    migrated_count += 1
            
            except Exception as e:
                error_count += 1
                image_hash_preview = v1_record.get('image_hash', 'unknown')[:16] if v1_record.get('image_hash') else 'unknown'
                print(f"❌ 迁移失败: image_hash={image_hash_preview}..., edit_type={v1_record.get('edit_type')}, 错误: {e}")
        
        conn.commit()
        offset += len(v1_records)
        
        # 显示进度
        progress = min(offset, total_count)
        percent = (progress * 100 // total_count) if total_count > 0 else 0
        print(f"📈 迁移进度: {progress}/{total_count} ({percent}%) - 已迁移: {migrated_count}, 已跳过: {skipped_count}, 错误: {error_count}")
    
    print(f"\n✅ 迁移完成:")
    print(f"   - 已迁移: {migrated_count} 条")
    print(f"   - 已跳过（已存在）: {skipped_count} 条")
    print(f"   - 错误: {error_count} 条")
    print(f"   - 总计: {migrated_count + skipped_count + error_count} 条")


def verify_migration(cursor):
    """验证迁移结果"""
    # 获取v1和v2的数据量
    cursor.execute("SELECT COUNT(*) as count FROM image_edit_cache")
    v1_count = cursor.fetchone()['count']
    
    # 统计v2表中编辑服务的数据量（通过service_type判断）
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM llm_inference_cache_v2
        WHERE JSON_EXTRACT(model_results, '$."aliyun:qwen-image-edit".service_type') = 'image_edit'
    """)
    v2_edit_count = cursor.fetchone()['count']
    
    # 获取命中次数统计
    cursor.execute("SELECT SUM(hit_count) as total FROM image_edit_cache")
    v1_hits_result = cursor.fetchone()
    v1_hits = v1_hits_result['total'] if v1_hits_result['total'] else 0
    
    cursor.execute("""
        SELECT SUM(CAST(JSON_EXTRACT(model_results, '$."aliyun:qwen-image-edit".hit_count') AS UNSIGNED)) as total
        FROM llm_inference_cache_v2
        WHERE JSON_EXTRACT(model_results, '$."aliyun:qwen-image-edit".service_type') = 'image_edit'
    """)
    v2_hits_result = cursor.fetchone()
    v2_hits = v2_hits_result['total'] if v2_hits_result['total'] else 0
    
    print(f"\n📊 迁移验证:")
    print(f"   image_edit_cache表数据量: {v1_count}")
    print(f"   v2表中编辑服务数据量: {v2_edit_count}")
    print(f"   image_edit_cache表命中次数: {v1_hits}")
    print(f"   v2表中编辑服务命中次数: {v2_hits}")
    
    if v1_count == v2_edit_count:
        print("   ✅ 数据量一致，迁移成功")
    else:
        print(f"   ⚠️  数据量不一致，差值: {abs(v1_count - v2_edit_count)}")
    
    if v1_hits == v2_hits:
        print("   ✅ 命中次数一致，迁移成功")
    else:
        print(f"   ⚠️  命中次数不一致，差值: {abs(v1_hits - v2_hits)}")


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    # 数据库连接配置
    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'image_classifier'),
        'charset': 'utf8mb4'
    }
    
    try:
        print("=" * 60)
        print("开始迁移image_edit_cache数据到v2")
        print("=" * 60)
        
        # 连接数据库
        print("连接数据库...")
        conn = pymysql.connect(**db_config, cursorclass=DictCursor)
        cursor = conn.cursor()
        print("✅ 数据库连接成功")
        
        # 检查v1表是否存在
        cursor.execute("SHOW TABLES LIKE 'image_edit_cache'")
        if not cursor.fetchone():
            print("❌ 错误: image_edit_cache 表不存在")
            return
        
        # 检查v2表是否存在
        cursor.execute("SHOW TABLES LIKE 'llm_inference_cache_v2'")
        if not cursor.fetchone():
            print("❌ 错误: llm_inference_cache_v2 表不存在，请先执行 create_llm_inference_cache_v2.sql")
            return
        
        # 迁移数据
        migrate_data(conn, cursor, batch_size=1000)
        
        # 验证迁移结果
        verify_migration(cursor)
        
        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)
        
        # 关闭连接
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

