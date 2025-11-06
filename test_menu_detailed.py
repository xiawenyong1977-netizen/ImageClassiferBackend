#!/usr/bin/env python3
"""
详细测试微信公众号菜单创建
查看实际的菜单结构和微信API响应
"""

import requests
import json

SERVER_URL = "http://admin.xintuxiangce.top:8000"
MENU_ENDPOINT = f"{SERVER_URL}/api/v1/auth/wechat/create-menu"

print("=" * 70)
print("详细测试微信公众号菜单创建")
print("=" * 70)
print()

try:
    print("正在调用菜单创建接口...")
    response = requests.post(MENU_ENDPOINT, timeout=30)
    
    print(f"HTTP状态码: {response.status_code}")
    print()
    
    if response.status_code == 200:
        result = response.json()
        print("=" * 70)
        print("接口返回结果:")
        print("=" * 70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 检查返回的菜单结构
        if 'menu_structure' in result:
            print("=" * 70)
            print("菜单结构:")
            print("=" * 70)
            menu = result['menu_structure']
            print(f"一级菜单数量: {len(menu.get('button', []))}")
            for i, btn in enumerate(menu.get('button', []), 1):
                print(f"\n一级菜单 {i}: {btn.get('name')}")
                if 'type' in btn:
                    print(f"  类型: {btn.get('type')}")
                    print(f"  URL: {btn.get('url', 'N/A')}")
                elif 'sub_button' in btn:
                    print(f"  二级菜单数量: {len(btn.get('sub_button', []))}")
                    for j, sub_btn in enumerate(btn.get('sub_button', []), 1):
                        print(f"    二级菜单 {j}: {sub_btn.get('name')}")
                        print(f"      URL: {sub_btn.get('url', 'N/A')[:80]}...")
        
        if 'wechat_response' in result:
            print()
            print("=" * 70)
            print("微信API响应:")
            print("=" * 70)
            wechat_resp = result['wechat_response']
            print(json.dumps(wechat_resp, indent=2, ensure_ascii=False))
            
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ 发生错误: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("注意事项:")
print("=" * 70)
print("1. 微信菜单更新可能需要几分钟时间才能生效")
print("2. 请完全退出公众号后重新进入查看")
print("3. 如果仍看不到变化，请检查服务器代码是否已更新")
print("4. 可以尝试在微信中长按公众号，选择'清空缓存'后重新进入")
print()

