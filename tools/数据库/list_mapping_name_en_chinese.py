#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列举 city_name_mapping 表中 name_en 为中文的异常记录
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
_project_dir = Path(__file__).resolve().parent
_project_root = _project_dir
while _project_root != _project_root.parent:
    if (_project_root / "app").is_dir():
        break
    _project_root = _project_root.parent
sys.path.insert(0, str(_project_root))

from app.database import db
import asyncio


def _contains_chinese(text: str) -> bool:
    """检测字符串是否包含中文字符"""
    if not text or not isinstance(text, str):
        return False
    return any('\u4e00' <= c <= '\u9fff' for c in text)


async def list_name_en_chinese():
    """列举 city_name_mapping 中 name_en 含中文的记录"""
    try:
        await db.connect()

        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT id, name_zh, name_en, country_code
                FROM city_name_mapping
                ORDER BY id
            """)
            rows = await cursor.fetchall()

        bad = [r for r in rows if _contains_chinese(r.get("name_en") or "")]

        if not bad:
            print("✅ 未发现 name_en 含中文的记录")
            await db.disconnect()
            return

        print(f"发现 {len(bad)} 条 name_en 含中文的异常记录：\n")
        print(f"{'id':<8} {'name_zh':<30} {'name_en':<30} country_code")
        print("-" * 80)
        for r in bad:
            print(f"{r['id']:<8} {(r.get('name_zh') or ''):<30} {(r.get('name_en') or ''):<30} {r.get('country_code') or ''}")

        print(f"\n共 {len(bad)} 条，需修复 mapping 表或补充正确英文名")

        await db.disconnect()

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(list_name_en_chinese())
