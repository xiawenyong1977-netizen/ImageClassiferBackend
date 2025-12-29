"""
直接运行新添加的测试用例
"""
import sys
import asyncio
import pytest

def main():
    """运行新添加的测试用例"""
    print("=" * 60)
    print("开始运行新添加的测试用例")
    print("=" * 60)
    
    # 运行所有新功能的测试
    test_patterns = [
        "test_classify_color",
        "test_analyze_composition", 
        "test_predict_face_fortune"
    ]
    
    exit_code = 0
    for pattern in test_patterns:
        print(f"\n运行 {pattern} 相关测试...")
        result = pytest.main([
            "tests/test_llm_service.py",
            "-k", pattern,
            "-v",
            "--tb=short"
        ])
        if result != 0:
            exit_code = result
            print(f"❌ {pattern} 测试失败")
        else:
            print(f"✅ {pattern} 测试通过")
    
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ 所有新功能的测试用例运行完成！")
    else:
        print("❌ 部分测试用例失败，请检查输出")
    print("=" * 60)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())

