#!/usr/bin/env python3
"""
测试微信公众号菜单创建接口
"""

import requests
import json
import sys

# 服务器地址配置
SERVER_URL = "http://admin.xintuxiangce.top:8000"  # 生产服务器
# SERVER_URL = "http://127.0.0.1:8000"  # 本地测试

# 菜单接口
MENU_ENDPOINT = f"{SERVER_URL}/api/v1/auth/wechat/create-menu"
GET_MENU_ENDPOINT = f"{SERVER_URL}/api/v1/auth/wechat/get-menu"


def get_current_menu():
    """查询当前菜单"""
    print("=" * 60)
    print("查询当前微信公众号菜单")
    print("=" * 60)
    print(f"接口地址: {GET_MENU_ENDPOINT}")
    print()
    
    try:
        response = requests.get(GET_MENU_ENDPOINT, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print("✅ 查询成功！")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result
        else:
            print(f"❌ 查询失败: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ 查询异常: {str(e)}")
        return None


def test_create_menu():
    """测试创建微信公众号菜单"""
    print("=" * 60)
    print("测试微信公众号菜单创建接口")
    print("=" * 60)
    print(f"服务器地址: {SERVER_URL}")
    print(f"接口地址: {MENU_ENDPOINT}")
    print()
    
    try:
        print("正在调用菜单创建接口...")
        response = requests.post(
            MENU_ENDPOINT,
            timeout=30
        )
        
        print(f"HTTP状态码: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 接口调用成功！")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("success"):
                print()
                print("=" * 60)
                print("✅ 菜单创建成功！")
                print("=" * 60)
                print()
                print("请按以下步骤验证：")
                print("1. 打开微信客户端")
                print("2. 进入'芯图相册'公众号")
                print("3. 查看底部菜单栏，应该看到：")
                print("   - 左侧：'芯图相册'（点击跳转到主页）")
                print("   - 右侧：'会员服务'（点击展开子菜单）")
                print("      ├─ 开通会员")
                print("      ├─ 购买额度")
                print("      └─ 额度查询")
            else:
                print()
                print("❌ 菜单创建失败，请查看错误信息")
        else:
            print("❌ 接口调用失败")
            print(f"错误信息: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请检查服务器是否正常运行")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务器: {SERVER_URL}")
        print("请检查：")
        print("1. 服务器是否正在运行")
        print("2. 服务器地址是否正确")
        print("3. 网络连接是否正常")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    # 如果提供了命令行参数，使用该参数作为服务器地址
    if len(sys.argv) > 1:
        SERVER_URL = sys.argv[1]
        MENU_ENDPOINT = f"{SERVER_URL}/api/v1/auth/wechat/create-menu"
        GET_MENU_ENDPOINT = f"{SERVER_URL}/api/v1/auth/wechat/get-menu"
    
    print("\n")
    
    # 先查询当前菜单
    print("步骤1: 查询当前菜单...")
    current_menu = get_current_menu()
    print("\n")
    
    # 创建新菜单
    print("步骤2: 创建新菜单...")
    success = test_create_menu()
    print("\n")
    
    # 再次查询菜单确认
    if success:
        print("步骤3: 验证菜单是否创建成功...")
        import time
        time.sleep(2)  # 等待2秒
        new_menu = get_current_menu()
    
    sys.exit(0 if success else 1)

