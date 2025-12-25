#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从GeoNames数据文件提取城市名称中英文映射关系
支持从cities15000.txt和CN.txt提取
"""
import re
import sys
from collections import defaultdict

def is_chinese(text):
    """
    判断是否主要是中文字符（排除日文假名）
    
    规则：
    1. 必须包含中文字符（\u4e00-\u9fff）
    2. 不能包含日文平假名（\u3040-\u309f）
    3. 不能包含日文片假名（\u30a0-\u30ff）
    4. 中文字符占比应该超过50%
    """
    if not text:
        return False
    
    # 检查是否包含日文假名
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return False
    
    # 检查是否包含中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    if not chinese_chars:
        return False
    
    # 计算中文字符占比
    total_chars = len([c for c in text if c.isprintable()])
    chinese_count = len(chinese_chars)
    
    # 如果中文字符占比超过50%，认为是中文
    if total_chars > 0 and chinese_count * 100 / total_chars >= 50:
        return True
    
    return False

def normalize_city_name(name):
    """
    规范化城市名称，去除常见后缀
    
    去除的后缀：市、区、县、州、省、自治区、特别行政区、地区、盟、旗、自治县、自治州、镇等
    
    规则：
    - 如果原始名称长度 > 2，则去除后缀进行规范化（如"三明市" -> "三明"）
    - 如果原始名称长度 <= 2，则不规范化，保留原样（如"万市"保留为"万市"，避免出现"万"这样的单字）
    """
    if not name:
        return name
    
    # 如果原始名称长度 <= 2，不进行规范化
    if len(name) <= 2:
        return name.strip()
    
    # 行政级别后缀列表（按长度从长到短排序，避免部分匹配）
    # 注意：不包含"镇"、"乡"、"村"，因为这些可能是地名的一部分（如"景德镇"）
    suffixes = [
        '特别行政区', '自治区', '自治县', '自治州',
        '市', '区', '县', '州', '省', '地区', '盟', '旗',
        '街道', '办事处'
    ]
    
    normalized = name
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
            break  # 只去除一个后缀
    
    return normalized.strip()

def extract_mapping_from_file(file_path):
    """
    从GeoNames文件提取映射关系
    
    过滤规则：
    - 只保留 PPLA2 及以上级别（PPLC、PPLG、PPLA、PPLA2）
    - 排除 PPLA3、PPLA4、PPLX 等细粒度地点
    - 不考虑人口数量
    
    Args:
        file_path: GeoNames文件路径
    
    Returns:
        dict: {
            'name_zh': {
                'name_en': 'Beijing',
                'country_code': 'CN'
            }
        }
    """
    mapping = {}
    
    # 城市级别的feature_code（PPLA2及以上）
    # 注意：GeoNames中的feature_code格式是"PPLC"而不是"P.PPLC"（没有点）
    # PPLC: 国家首都
    # PPLG: 州/省首府
    # PPLA: 一级行政中心（通常是城市）
    # PPLA2: 二级行政中心（可能是区县，也保留）
    valid_feature_codes = {'PPLC', 'PPLG', 'PPLA', 'PPLA2'}
    
    # 排除的feature_code（太细的行政级别，如街道、小区等）
    # PPLA3: 三级行政中心（街道级别）
    # PPLA4: 四级行政中心（社区级别）
    # PPLX: 废弃的定居点
    excluded_feature_codes = {'PPLA3', 'PPLA4', 'PPLX'}
    
    print(f"正在处理文件: {file_path}")
    print(f"过滤条件: feature_code in {valid_feature_codes}（PPLA2及以上）")
    print(f"排除: {excluded_feature_codes}（街道、小区等细粒度地点）")
    print(f"不考虑人口数量")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line_count = 0
            filtered_count = 0
            for line in f:
                line_count += 1
                if line_count % 10000 == 0:
                    print(f"  已处理 {line_count} 行，通过过滤 {filtered_count} 条...")
                
                fields = line.strip().split('\t')
                if len(fields) < 9:
                    continue
                
                # 只处理人口聚集地（feature_class = 'P'）
                if fields[6] != 'P':
                    continue
                
                feature_code = fields[7] if len(fields) > 7 else ''
                country_code = fields[8] if len(fields) > 8 else ''
                
                # 排除太细的行政级别
                if feature_code in excluded_feature_codes:
                    continue
                
                # 只保留 PPLA2 及以上级别，不考虑人口数量
                if feature_code not in valid_feature_codes:
                    continue
                
                filtered_count += 1
                
                english_name = fields[1]  # 英文名
                country_code = fields[8]
                alternatenames = fields[3] if len(fields) > 3 else ''
                
                # 提取所有中文名（包括别名）
                chinese_names = []
                if alternatenames:
                    for alt_name in alternatenames.split(','):
                        alt_name = alt_name.strip()
                        if alt_name and is_chinese(alt_name) and len(alt_name) >= 2:
                            chinese_names.append(alt_name)
                
                # 如果没有中文名称，不填充（留空），避免混淆
                # 只处理有中文名称的城市
                if not chinese_names:
                    continue
                
                if chinese_names:
                    # 策略：先规范化所有名称，然后按规范化后的名称去重
                    # 如果规范化后的名称相同（如"三明"和"三明市"都规范化为"三明"），只保留一个
                    normalized_groups = {}
                    
                    for chinese_name in chinese_names:
                        # 先规范化名称（去除"市"、"县"、"镇"等后缀）
                        # 规则：原始名称长度 > 2 才规范化，<= 2 保留原样
                        normalized_name = normalize_city_name(chinese_name)
                        
                        # 使用规范化后的名称作为key进行分组
                        if normalized_name not in normalized_groups:
                            normalized_groups[normalized_name] = []
                        normalized_groups[normalized_name].append(chinese_name)
                    
                    # 为每个规范化后的名称组选择最佳的中文名称并去重
                    # 优先级：原始名称就是规范化名称的 > 带后缀的，短的 > 长的
                    for normalized_key, variants in normalized_groups.items():
                        # 优先选择原始名称就是规范化名称的（不带后缀）
                        # 如果都有后缀，选择最短的
                        best_name = min(variants, key=lambda x: (
                            x != normalized_key,  # 不带后缀的优先（x == normalized_key）
                            len(x)               # 短的优先
                        ))
                        
                        # 只存储最佳名称，不存储其他变体
                        # 这样"三明"和"三明市"都规范化为"三明"，只存储"三明"
                        if best_name not in mapping:
                            mapping[best_name] = {
                                'name_en': english_name,
                                'country_code': country_code
                            }
                        
                        # 如果最佳名称与规范化名称不同，也存储规范化名称
                        # 这样如果只有"三明市"（没有"三明"），会存储"三明市"和"三明"
                        # 但如果同时有"三明"和"三明市"，只存储"三明"（最佳名称）
                        if normalized_key != best_name and normalized_key not in mapping:
                            # 只有当规范化名称不在variants中时，才存储规范化名称
                            # 这样可以避免重复存储
                            mapping[normalized_key] = {
                                'name_en': english_name,
                                'country_code': country_code
                            }
        
        print(f"处理完成，共 {line_count} 行，通过过滤 {filtered_count} 条，提取到 {len(mapping)} 个映射关系")
        
    except FileNotFoundError:
        print(f"错误: 文件不存在: {file_path}")
        return {}
    except Exception as e:
        print(f"错误: 处理文件时出错: {e}")
        return {}
    
    return mapping

def merge_mappings(*mappings):
    """
    合并多个映射字典，并进行全局去重
    
    优先级：后面的映射会覆盖前面的（如果中文名相同）
    去重：如果规范化后的名称相同，只保留一个（优先保留不带后缀的）
    """
    # 先合并所有映射
    merged = {}
    for mapping in mappings:
        for name_zh, data in mapping.items():
            # 如果还没有该中文名的映射，或者当前记录更详细，则更新
            if name_zh not in merged:
                merged[name_zh] = {
                    'name_en': data['name_en'],
                    'country_code': data['country_code']
                }
    
    # 全局去重：按（英文名+国家代码）分组，同一城市的多个中文名都保留
    # 但规范化后相同的名称（如"三明"和"三明市"）只保留一个
    by_city = {}
    for name_zh, data in merged.items():
        city_key = (data['name_en'], data['country_code'])
        if city_key not in by_city:
            by_city[city_key] = []
        by_city[city_key].append(name_zh)
    
    # 对每个城市的多个中文名进行规范化去重
    result = {}
    for (name_en, country_code), name_zh_list in by_city.items():
        # 按规范化后的名称分组
        normalized_groups = {}
        for name_zh in name_zh_list:
            normalized_name = normalize_city_name(name_zh)
            if normalized_name not in normalized_groups:
                normalized_groups[normalized_name] = []
            normalized_groups[normalized_name].append(name_zh)
        
        # 为每个规范化组选择最佳名称
        for normalized_key, variants in normalized_groups.items():
            # 优先选择不带后缀的（原始名称就是规范化名称的）
            # 如果都有后缀，选择最短的
            best_name = min(variants, key=lambda x: (
                x != normalized_key,  # 不带后缀的优先
                len(x)               # 短的优先
            ))
            
            # 存储最佳名称
            result[best_name] = {
                'name_en': name_en,
                'country_code': country_code
            }
            
            # 如果最佳名称与规范化名称不同，且规范化名称不在variants中，也存储规范化名称
            if normalized_key != best_name and normalized_key not in variants:
                result[normalized_key] = {
                    'name_en': name_en,
                    'country_code': country_code
                }
    
    return result

def save_to_csv(mapping, output_file):
    """
    保存映射关系到CSV文件
    """
    print(f"正在保存到: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('name_zh,name_en,country_code\n')
        
        for name_zh in sorted(mapping.keys()):
            data = mapping[name_zh]
            f.write(f'{name_zh},{data["name_en"]},{data["country_code"]}\n')
    
    print(f"保存完成，共 {len(mapping)} 条记录")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python extract_city_mapping.py <输入文件1> [输入文件2] ... [输出文件]")
        print("")
        print("示例:")
        print("  python extract_city_mapping.py cities15000.txt CN.txt city_mapping.csv")
        print("  python extract_city_mapping.py CN.txt city_mapping_china.csv")
        sys.exit(1)
    
    input_files = sys.argv[1:-1] if len(sys.argv) > 2 else [sys.argv[1]]
    output_file = sys.argv[-1] if len(sys.argv) > 2 else 'city_mapping.csv'
    
    print("=" * 50)
    print("城市名称中英文映射提取工具")
    print("=" * 50)
    print()
    
    # 提取所有文件的映射
    # 只保留 PPLA2 及以上级别，不考虑人口数量
    all_mappings = []
    for input_file in input_files:
        mapping = extract_mapping_from_file(input_file)
        if mapping:
            all_mappings.append(mapping)
            print(f"从 {input_file} 提取到 {len(mapping)} 个映射关系")
        print()
    
    if not all_mappings:
        print("错误: 没有提取到任何映射关系")
        sys.exit(1)
    
    # 合并映射
    print("正在合并映射关系...")
    final_mapping = merge_mappings(*all_mappings)
    print(f"合并后共 {len(final_mapping)} 个映射关系")
    print()
    
    # 统计信息
    china_count = sum(1 for data in final_mapping.values() if data['country_code'] == 'CN')
    print(f"统计信息:")
    print(f"  总映射数: {len(final_mapping)}")
    print(f"  中国城市: {china_count}")
    print(f"  其他国家: {len(final_mapping) - china_count}")
    print()
    
    # 保存到CSV
    save_to_csv(final_mapping, output_file)
    
    print()
    print("=" * 50)
    print("提取完成！")
    print("=" * 50)

if __name__ == '__main__':
    main()

