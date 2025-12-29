#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将v1版本的缓存数据迁移到v2版本
从 image_classification_cache 迁移到 llm_inference_cache_v2
"""

import sys
import os
import hashlib
import json
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv


def calculate_prompt_hash(prompt: str) -> str:
    """计算提示词的SHA-256哈希"""
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()


def get_classification_prompt():
    """获取分类服务的prompt（从配置中获取）"""
    try:
        # 尝试从app.config导入（需要项目路径）
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
        from app.config import settings
        return settings.CLASSIFICATION_PROMPT
    except Exception:
        # 如果导入失败，尝试从环境变量获取
        prompt = os.getenv('CLASSIFICATION_PROMPT')
        if prompt:
            return prompt
        
        # 使用默认prompt（与app/config.py中的一致）
        return """请对这张图片进行分类。你必须从以下9个类别中选择一个：

1. social_activities - 社交活动（聚会、合影、多人互动场景）
2. pets - 宠物萌照（猫、狗等宠物照片）
3. single_person - 单人照片（个人照、自拍、肖像）
4. foods - 美食记录（食物、餐饮、烹饪相关）
5. travel_scenery - 旅行风景（旅游景点、自然风光、城市风景）
6. screenshot - 手机截图（手机屏幕截图、应用界面）
7. idcard - 证件照（身份证、护照、驾照等证件）
8. qrcode - 二维码（只要照片中含有二维码，无论是否还有其他内容，都必须分类为qrcode）
9. other - 其它（无法归类到上述类别）

重要：如果图片中包含二维码（QR码），无论图片中是否还有其他内容，都必须分类为 qrcode。

同时，请识别照片背景的主要颜色。背景颜色必须从以下10种颜色中选择一个：
橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色

请以JSON格式返回结果：
{
    "category": "类别key（必须是上述9个之一）",
    "confidence": 0.95,
    "description": "简短描述图片内容（可选，中文，30字以内）",
    "background_color": "背景颜色（必须是：橙色、蓝色、红色、绿色、紫色、粉色、黄色、灰色、黑色、白色之一）"
}

只返回JSON，不要有其他文字。"""


def get_v1_data_count(cursor):
    """获取v1表的数据总数"""
    cursor.execute("SELECT COUNT(*) as count FROM image_classification_cache")
    result = cursor.fetchone()
    return result['count'] if result else 0


def migrate_data(conn, cursor, prompt_hash: str, batch_size: int = 1000):
    """迁移数据从v1到v2"""
    
    # 获取v1数据总数
    total_count = get_v1_data_count(cursor)
    print(f"📊 v1表数据总数: {total_count}")
    
    if total_count == 0:
        print("⚠️  v1表没有数据，无需迁移")
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
                category,
                confidence,
                description,
                background_color,
                model_used,
                hit_count,
                created_at,
                last_hit_at
            FROM image_classification_cache
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
                    # 构建模型key（处理model_used格式）
                    model_used = v1_record['model_used']
                    if ':' not in model_used:
                        model_key = f"aliyun:{model_used}"
                    else:
                        model_key = model_used
                    
                    # 构建result对象
                    result_obj = {
                        "category": v1_record['category'],
                        "confidence": float(v1_record['confidence']),
                        "description": v1_record['description'] or "",
                        "background_color": v1_record['background_color']
                    }
                    
                    # 处理时间格式
                    created_at = v1_record['created_at']
                    if isinstance(created_at, datetime):
                        created_at_str = created_at.isoformat()
                    else:
                        created_at_str = str(created_at)
                    
                    # 构建model_results JSON
                    model_result = {
                        "result": result_obj,
                        "service_type": "classification",
                        "created_at": created_at_str,
                        "status": "success",
                        "model_used": model_used,
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
                print(f"❌ 迁移失败: image_hash={image_hash_preview}..., 错误: {e}")
        
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
    cursor.execute("SELECT COUNT(*) as count FROM image_classification_cache")
    v1_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM llm_inference_cache_v2")
    v2_count = cursor.fetchone()['count']
    
    # 获取命中次数统计
    cursor.execute("SELECT SUM(hit_count) as total FROM image_classification_cache")
    v1_hits_result = cursor.fetchone()
    v1_hits = v1_hits_result['total'] if v1_hits_result['total'] else 0
    
    cursor.execute("SELECT SUM(hit_count) as total FROM llm_inference_cache_v2")
    v2_hits_result = cursor.fetchone()
    v2_hits = v2_hits_result['total'] if v2_hits_result['total'] else 0
    
    print(f"\n📊 迁移验证:")
    print(f"   v1表数据量: {v1_count}")
    print(f"   v2表数据量: {v2_count}")
    print(f"   v1表命中次数: {v1_hits}")
    print(f"   v2表命中次数: {v2_hits}")
    
    if v1_count == v2_count:
        print("   ✅ 数据量一致，迁移成功")
    else:
        print(f"   ⚠️  数据量不一致，差值: {abs(v1_count - v2_count)}")
    
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
        print("开始迁移v1缓存数据到v2")
        print("=" * 60)
        
        # 连接数据库
        print("连接数据库...")
        conn = pymysql.connect(**db_config, cursorclass=DictCursor)
        cursor = conn.cursor()
        print("✅ 数据库连接成功")
        
        # 检查v1表是否存在
        cursor.execute("SHOW TABLES LIKE 'image_classification_cache'")
        if not cursor.fetchone():
            print("❌ 错误: image_classification_cache 表不存在")
            return
        
        # 检查v2表是否存在
        cursor.execute("SHOW TABLES LIKE 'llm_inference_cache_v2'")
        if not cursor.fetchone():
            print("❌ 错误: llm_inference_cache_v2 表不存在，请先执行 create_llm_inference_cache_v2.sql")
            return
        
        # 获取分类服务的prompt
        prompt = get_classification_prompt()
        print(f"📝 使用分类提示词（长度: {len(prompt)} 字符）")
        
        # 计算prompt_hash
        prompt_hash = calculate_prompt_hash(prompt)
        print(f"🔑 prompt_hash: {prompt_hash}")
        
        # 迁移数据
        migrate_data(conn, cursor, prompt_hash, batch_size=1000)
        
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

