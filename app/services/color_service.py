"""
本地主色识别服务
使用 PIL + HSV 分析图片主色，映射到 10 种预定义颜色
与 model_client.BACKGROUND_COLORS 保持一致
"""

import io
from typing import Optional

from PIL import Image
from loguru import logger

# 与 model_client.BACKGROUND_COLORS 一致
BACKGROUND_COLORS = [
    "橙色", "蓝色", "红色", "绿色", "紫色",
    "粉色", "黄色", "灰色", "黑色", "白色"
]

# HSV 色相区间映射到颜色（H: 0-360, S: 0-1, V: 0-1）
# 色相环：红0, 橙30, 黄60, 绿120, 青180, 蓝240, 紫270, 品红300
HUE_TO_COLOR = [
    (0, 15, "红色"),
    (15, 45, "橙色"),
    (45, 70, "黄色"),
    (70, 160, "绿色"),
    (160, 200, "蓝色"),
    (200, 260, "紫色"),
    (260, 320, "粉色"),
    (320, 360, "红色"),
]


def get_dominant_color(image_bytes: bytes) -> Optional[str]:
    """
    分析图片主色，返回 10 种预定义颜色之一
    
    Args:
        image_bytes: 图片二进制数据
        
    Returns:
        颜色名称（橙色/蓝色/红色/绿色/紫色/粉色/黄色/灰色/黑色/白色之一），失败返回 None
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        
        # 缩小以提升性能
        max_size = 256
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        pixels = list(img.getdata())
        if not pixels:
            return None
        
        # 统计非边缘像素（排除四周 10% 以更好反映背景）
        w, h = img.size
        margin_w = max(1, w // 10)
        margin_h = max(1, h // 10)
        
        center_pixels = []
        for y in range(margin_h, h - margin_h):
            for x in range(margin_w, w - margin_w):
                idx = y * w + x
                if idx < len(pixels):
                    center_pixels.append(pixels[idx])
        
        if not center_pixels:
            center_pixels = pixels
        
        # 灰度/黑白检测
        gray_count = 0
        black_count = 0
        white_count = 0
        total = len(center_pixels)
        
        hue_sum = 0.0
        sat_sum = 0.0
        val_sum = 0.0
        colored_count = 0
        
        for r, g, b in center_pixels:
            # RGB 转 HSV（简化）
            rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
            cmax = max(rn, gn, bn)
            cmin = min(rn, gn, bn)
            delta = cmax - cmin
            
            v = cmax
            s = delta / cmax if cmax > 0 else 0
            
            if delta == 0:
                h = 0
            elif cmax == rn:
                h = 60 * (((gn - bn) / delta) % 6)
            elif cmax == gn:
                h = 60 * ((bn - rn) / delta + 2)
            else:
                h = 60 * ((rn - gn) / delta + 4)
            if h < 0:
                h += 360
            
            # 灰度判断：饱和度低
            if s < 0.15:
                gray_count += 1
                if v < 0.2:
                    black_count += 1
                elif v > 0.9:
                    white_count += 1
            else:
                hue_sum += h
                sat_sum += s
                val_sum += v
                colored_count += 1
        
        # 优先返回灰/黑/白
        if total > 0:
            white_ratio = white_count / total
            black_ratio = black_count / total
            gray_ratio = gray_count / total
            
            if white_ratio > 0.5:
                return "白色"
            if black_ratio > 0.5:
                return "黑色"
            if gray_ratio > 0.6:
                return "灰色"
        
        # 有色彩：按色相统计
        if colored_count == 0:
            return "灰色"
        
        avg_hue = hue_sum / colored_count
        avg_sat = sat_sum / colored_count
        avg_val = val_sum / colored_count
        
        # 低饱和度偏灰
        if avg_sat < 0.2:
            return "灰色"
        if avg_val < 0.15:
            return "黑色"
        if avg_val > 0.95:
            return "白色"
        
        # 按色相映射
        for low, high, color in HUE_TO_COLOR:
            if low <= avg_hue < high:
                return color
        
        return "红色"  # 360 附近
        
    except Exception as e:
        logger.debug(f"主色识别异常: {e}")
        return None
