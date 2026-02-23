"""
测试 color_service.get_dominant_color 对 D:\\test20151014 目录下照片的主色识别
"""
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.color_service import get_dominant_color

TEST_DIR = Path(r"D:\test20151014")


def main():
    if not TEST_DIR.exists():
        print(f"目录不存在: {TEST_DIR}")
        return

    # 支持的图片扩展名
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    files = sorted(
        f for f in TEST_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in exts
    )

    if not files:
        print(f"未找到图片文件: {TEST_DIR}")
        return

    # 限制测试数量，避免输出过多
    max_test = 50
    to_test = files[:max_test]

    print(f"测试目录: {TEST_DIR}")
    print(f"共 {len(files)} 张图片，测试前 {len(to_test)} 张\n")
    print("-" * 80)

    for i, fp in enumerate(to_test, 1):
        try:
            data = fp.read_bytes()
            color = get_dominant_color(data)
            print(f"{i:3}. {fp.name[:60]:<60} -> {color or 'None'}")
        except Exception as e:
            print(f"{i:3}. {fp.name[:60]:<60} -> 错误: {e}")

    print("-" * 80)
    print("完成")


if __name__ == "__main__":
    main()
