#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 city_name_mapping 中 name_zh 含「市」的记录：
1. 去掉「市」后检查是否存在对应无「市」记录
2. 可选：显示拼音（需安装 pypinyin: pip install pypinyin）
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

# 拼音支持（可选）
try:
    from pypinyin import lazy_pinyin
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False


def _name_without_shi(name_zh: str) -> str:
    """去掉末尾的「市」"""
    if not name_zh or not name_zh.strip().endswith("市"):
        return ""
    return name_zh.strip()[:-1]


def _to_pinyin(name_zh: str) -> str:
    """中文转拼音（首字母大写，如 Shenzhen）。需安装 pypinyin"""
    if not HAS_PYPINYIN or not name_zh:
        return ""
    parts = lazy_pinyin(name_zh)
    return "".join(p.capitalize() for p in parts)


async def check_city_name_shi(show_pinyin: bool = True):
    """检查含「市」记录，并对比无「市」记录是否存在"""
    try:
        await db.connect()

        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT id, name_zh, name_en, country_code
                FROM city_name_mapping
                ORDER BY name_zh
            """)
            rows = await cursor.fetchall()

        # 所有 name_zh 的集合，用于快速查找
        all_name_zh = {r.get("name_zh") or "" for r in rows}

        # 筛选 name_zh 含「市」的记录
        with_shi = [r for r in rows if (r.get("name_zh") or "").strip().endswith("市")]

        if not with_shi:
            print("✅ 未发现 name_zh 含「市」的记录")
            await db.disconnect()
            return

        print(f"发现 {len(with_shi)} 条 name_zh 以「市」结尾的记录\n")
        print("说明：检查去掉「市」后，映射表中是否已有对应记录")
        if show_pinyin and HAS_PYPINYIN:
            print("（拼音由 pypinyin 生成，可作为 name_en 参考）")
        elif show_pinyin and not HAS_PYPINYIN:
            print("（安装 pypinyin 可显示拼音: pip install pypinyin）")
        print()
        print(f"{'id':<8} {'name_zh':<24} {'去掉市':<16} {'无市记录':<10} {'当前name_en':<20} {'拼音':<16}")
        print("-" * 110)

        has_dup = 0
        no_dup = 0
        for r in with_shi:
            rid = r["id"]
            name_zh = (r.get("name_zh") or "").strip()
            name_without = _name_without_shi(name_zh)
            exists = name_without in all_name_zh if name_without else False
            name_en = (r.get("name_en") or "")[:18]
            pinyin = _to_pinyin(name_without or name_zh) if show_pinyin else ""

            if exists:
                has_dup += 1
                status = "✓ 已有"
            else:
                no_dup += 1
                status = "— 无"

            print(f"{rid:<8} {name_zh:<24} {name_without:<16} {status:<10} {name_en:<20} {pinyin:<16}")

        print("-" * 110)
        print(f"\n统计：去掉「市」后已有记录 {has_dup} 条，无记录 {no_dup} 条")
        print("\n拼音说明：多数中国城市英文名为拼音形式（如 Shenzhen、Beijing），")
        print("可用 pinyin 列作为 name_en 的参考，但需人工核对（多音字、惯用名等）")

        await db.disconnect()

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    show_pinyin = "--no-pinyin" not in sys.argv
    asyncio.run(check_city_name_shi(show_pinyin=show_pinyin))
