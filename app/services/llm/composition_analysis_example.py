"""
构图分析功能使用示例
"""

import asyncio
import json
from app.services.llm import llm_service


async def example_composition_analysis():
    """构图分析示例"""
    # 读取测试图片
    with open("tests/test.jpg", "rb") as f:
        image_bytes = f.read()
    
    # 调用构图分析
    print("开始进行构图分析...")
    result = await llm_service.analyze_composition(
        image_bytes=image_bytes,
        use_cache=False  # 测试时建议关闭缓存，确保每次都调用API
    )
    
    if result["success"]:
        print("\n✅ 构图分析成功！")
        print(f"是否来自缓存: {result.get('from_cache', False)}")
        print("\n构图分析结果:")
        print("=" * 60)
        
        # 解析JSON结果
        composition_data = json.loads(result["content"])
        
        print(f"构图类型: {composition_data.get('composition_type')}")
        print(f"置信度: {composition_data.get('confidence')}")
        print(f"\n主体位置: {composition_data.get('subject_position')}")
        print(f"视觉平衡: {composition_data.get('visual_balance')}")
        print(f"\n空间布局: {composition_data.get('spatial_layout')}")
        print(f"线条与形状: {composition_data.get('lines_and_shapes')}")
        
        print(f"\n优点:")
        for i, strength in enumerate(composition_data.get('strengths', []), 1):
            print(f"  {i}. {strength}")
        
        suggestions = composition_data.get('suggestions', [])
        if suggestions and any(s.strip() for s in suggestions):
            print(f"\n改进建议:")
            for i, suggestion in enumerate(suggestions, 1):
                if suggestion.strip():
                    print(f"  {i}. {suggestion}")
        
        print(f"\n构图评分: {composition_data.get('score')}/10")
        print(f"\n详细分析:\n{composition_data.get('detailed_analysis')}")
        print("=" * 60)
    else:
        print("\n❌ 构图分析失败！")
        print(f"错误信息: {result['error']}")


async def example_with_custom_prompt():
    """使用自定义提示词的示例"""
    with open("tests/test.jpg", "rb") as f:
        image_bytes = f.read()
    
    # 自定义提示词（简化版）
    custom_prompt = """请识别这张照片的构图方式。

构图方式必须从以下选择：
1. rule_of_thirds - 三分法构图
2. center_composition - 中心构图
3. symmetry - 对称构图
4. other - 其他

请以JSON格式返回：
{
    "composition_type": "构图类型key",
    "confidence": 0.9,
    "subject_position": "主体位置描述",
    "score": 8.0
}

只返回JSON，不要有其他文字。"""
    
    result = await llm_service.analyze_composition(
        image_bytes=image_bytes,
        prompt=custom_prompt,
        use_cache=False
    )
    
    if result["success"]:
        composition_data = json.loads(result["content"])
        print(f"构图类型: {composition_data.get('composition_type')}")
        print(f"评分: {composition_data.get('score')}")


if __name__ == "__main__":
    print("构图分析功能测试")
    print("=" * 60)
    
    # 运行示例
    asyncio.run(example_composition_analysis())
    
    # 如果需要测试自定义提示词，取消下面的注释
    # print("\n\n使用自定义提示词:")
    # asyncio.run(example_with_custom_prompt())


