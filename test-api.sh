#!/bin/bash

# 图片分类API测试脚本

API_URL="http://123.57.68.4:8000"

echo "========================================"
echo "图片分类API测试"
echo "========================================"

# 测试1：健康检查
echo -e "\n[测试1] 健康检查"
curl -s "$API_URL/api/v1/health" | python3 -m json.tool

# 测试2：根路径
echo -e "\n[测试2] 根路径"
curl -s "$API_URL/" | head -5

# 测试3：今日统计
echo -e "\n[测试3] 今日统计"
curl -s "$API_URL/api/v1/stats/today" | python3 -m json.tool

# 测试4：缓存效率
echo -e "\n[测试4] 缓存效率"
curl -s "$API_URL/api/v1/stats/cache-efficiency" | python3 -m json.tool

# 测试5：分类分布
echo -e "\n[测试5] 分类分布"
curl -s "$API_URL/api/v1/stats/category-distribution" | python3 -m json.tool

echo -e "\n========================================"
echo "测试完成！"
echo "========================================"
echo "如需测试图片分类，请访问Web界面："
echo "$API_URL/"
echo "========================================"

