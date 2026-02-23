#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量补齐 global_cities_v2 中 name_en 为中文的记录
使用 city_name_mapping 映射表将中文名替换为正确的英文名
"""
import sys
from pathlib import Path

# 添加项目根目录到路径（向上查找包含 app 目录的父级）
_project_dir = Path(__file__).resolve().parent
_project_root = _project_dir
while _project_root != _project_root.parent:
    if (_project_root / "app").is_dir():
        break
    _project_root = _project_root.parent
sys.path.insert(0, str(_project_root))

from app.database import db
from app.config import settings
import asyncio


def _contains_chinese(text: str) -> bool:
    """检测字符串是否包含中文字符"""
    if not text or not isinstance(text, str):
        return False
    return any('\u4e00' <= c <= '\u9fff' for c in text)


def _normalize_name_zh(name: str) -> str:
    """规范化中文地名：去掉末尾的「市」"""
    if not name or not isinstance(name, str):
        return ""
    s = name.strip()
    if s.endswith("市"):
        return s[:-1]
    return s


async def supplement_name_en_batch(dry_run: bool = True):
    """
    批量补齐 global_cities_v2 中 name_en 为中文的记录
    
    Args:
        dry_run: 若为 True 仅统计和打印，不执行更新；为 False 时执行实际更新
    """
    try:
        await db.connect()
        
        async with db.get_cursor() as cursor:
            # 1. 查出所有 name_en 含中文的记录
            await cursor.execute("""
                SELECT id, name_en, city, province, country_code
                FROM global_cities_v2
                WHERE name_en IS NOT NULL AND name_en != ''
            """)
            rows = await cursor.fetchall()
            
            to_fix = []
            for row in rows:
                name_en = row.get("name_en") or ""
                if _contains_chinese(name_en):
                    to_fix.append(row)
            
            if not to_fix:
                print("✅ 未发现 name_en 含中文的记录，无需处理")
                await db.disconnect()
                return
            
            print(f"发现 {len(to_fix)} 条 name_en 含中文的记录")
            
            # 2. 对每条记录查 city_name_mapping 获取正确英文名
            updated = 0
            not_found = []
            
            for row in to_fix:
                rid = row["id"]
                lookup_zh = (row.get("name_en") or "").strip()
                if not lookup_zh:
                    continue
                # 规范化：去掉末尾「市」后查询
                lookup_normalized = _normalize_name_zh(lookup_zh)
                lookup_key = lookup_normalized if lookup_normalized else lookup_zh

                # 用规范化后的名字查询映射表
                await cursor.execute(
                    "SELECT name_en FROM city_name_mapping WHERE name_zh = %s LIMIT 1",
                    (lookup_key,)
                )
                mapping = await cursor.fetchone()
                # 若规范化后未找到，再尝试原始名字（如映射表存的是「深圳市」）
                if not mapping and lookup_key != lookup_zh:
                    await cursor.execute(
                        "SELECT name_en FROM city_name_mapping WHERE name_zh = %s LIMIT 1",
                        (lookup_zh,)
                    )
                    mapping = await cursor.fetchone()
                
                if mapping and mapping.get("name_en"):
                    new_name_en = mapping["name_en"].strip()
                    # 若映射表的 name_en 仍含中文，视为无效映射，不更新
                    if _contains_chinese(new_name_en):
                        not_found.append((rid, lookup_zh))
                        print(f"  [{rid}] {lookup_zh} -> (映射表 name_en 为中文，跳过)")
                    else:
                        if not dry_run:
                            await cursor.execute(
                                "UPDATE global_cities_v2 SET name_en = %s WHERE id = %s",
                                (new_name_en, rid)
                            )
                        updated += 1
                        print(f"  [{rid}] {lookup_zh} -> {new_name_en}")
                else:
                    not_found.append((rid, lookup_zh))
            
            if not_found:
                print(f"\n⚠️ 以下 {len(not_found)} 条在 city_name_mapping 中未找到映射:")
                for rid, zh in not_found[:20]:
                    print(f"  id={rid}, name_en(中文)={zh}")
                if len(not_found) > 20:
                    print(f"  ... 还有 {len(not_found) - 20} 条")
            
            if dry_run:
                print(f"\n[DRY RUN] 将更新 {updated} 条记录。若要实际执行，请使用: python supplement_name_en_batch.py --execute")
            else:
                print(f"\n✅ 已更新 {updated} 条记录")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    asyncio.run(supplement_name_en_batch(dry_run=dry_run))
