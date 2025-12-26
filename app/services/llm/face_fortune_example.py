"""
面相预测功能使用示例
"""

import asyncio
import json
from datetime import datetime
from app.services.llm import llm_service


async def example_face_fortune():
    """面相预测示例"""
    # 读取测试图片（需要包含清晰的人脸）
    with open("tests/test.jpg", "rb") as f:
        image_bytes = f.read()
    
    # 用户描述的事件
    event = "我要去参加一个重要的面试"
    
    # 当前时间（可选，不提供则自动生成）
    time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    # 调用面相预测
    print("开始进行面相预测...")
    print(f"事件: {event}")
    print(f"时间: {time}")
    print("-" * 60)
    
    result = await llm_service.predict_face_fortune(
        image_bytes=image_bytes,
        event=event,
        time=time,
        use_cache=False  # 测试时建议关闭缓存，确保每次都调用API
    )
    
    if result["success"]:
        print("\n✅ 面相预测成功！")
        print(f"是否来自缓存: {result.get('from_cache', False)}")
        print("\n面相预测结果:")
        print("=" * 60)
        
        # 解析JSON结果
        fortune_data = json.loads(result["content"])
        
        # 内容合规检查
        print(f"内容合规: {fortune_data.get('isCompliant')}")
        print(f"合规说明: {fortune_data.get('complianceReason')}")
        
        # 面相分析
        print("\n【面相分析】")
        face_analysis = fortune_data.get('faceAnalysis', {})
        print(f"额头: {face_analysis.get('forehead')}")
        print(f"眼睛: {face_analysis.get('eyes')}")
        print(f"鼻子: {face_analysis.get('nose')}")
        print(f"嘴巴: {face_analysis.get('mouth')}")
        print(f"整体: {face_analysis.get('overall')}")
        
        # 事件分析
        print("\n【事件预测】")
        event_analysis = fortune_data.get('eventAnalysis', {})
        print(f"预测状态: {event_analysis.get('status')}")
        print(f"评分: {event_analysis.get('score')}/100")
        print(f"总结: {event_analysis.get('summary')}")
        
        advice = event_analysis.get('advice', [])
        if advice:
            print(f"\n建议:")
            for i, item in enumerate(advice, 1):
                if item.strip():
                    print(f"  {i}. {item}")
        
        remedy = event_analysis.get('remedy', '')
        if remedy and remedy.strip():
            print(f"\n化解方法: {remedy}")
        
        # 时间反思
        print(f"\n【时间反思】")
        print(f"{fortune_data.get('timeReflection')}")
        
        print("=" * 60)
    else:
        print("\n❌ 面相预测失败！")
        print(f"错误信息: {result['error']}")


async def example_multiple_events():
    """测试多个不同的事件"""
    with open("tests/test.jpg", "rb") as f:
        image_bytes = f.read()
    
    events = [
        "我要去参加一个重要的面试",
        "我准备投资一个新的项目",
        "我要去旅行",
        "我要参加考试"
    ]
    
    time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    for event in events:
        print(f"\n{'='*60}")
        print(f"预测事件: {event}")
        print('='*60)
        
        result = await llm_service.predict_face_fortune(
            image_bytes=image_bytes,
            event=event,
            time=time,
            use_cache=False
        )
        
        if result["success"]:
            fortune_data = json.loads(result["content"])
            event_analysis = fortune_data.get('eventAnalysis', {})
            print(f"预测状态: {event_analysis.get('status')}")
            print(f"评分: {event_analysis.get('score')}/100")
            print(f"总结: {event_analysis.get('summary')}")
        else:
            print(f"预测失败: {result['error']}")


async def example_with_custom_time():
    """使用自定义时间的示例"""
    with open("tests/test.jpg", "rb") as f:
        image_bytes = f.read()
    
    event = "我要去参加一个重要的面试"
    custom_time = "2024年12月25日 10:30"  # 自定义时间
    
    result = await llm_service.predict_face_fortune(
        image_bytes=image_bytes,
        event=event,
        time=custom_time,
        use_cache=False
    )
    
    if result["success"]:
        fortune_data = json.loads(result["content"])
        print(f"时间反思: {fortune_data.get('timeReflection')}")


if __name__ == "__main__":
    print("面相预测功能测试")
    print("=" * 60)
    
    # 运行基础示例
    asyncio.run(example_face_fortune())
    
    # 如果需要测试多个事件，取消下面的注释
    # print("\n\n测试多个事件:")
    # asyncio.run(example_multiple_events())
    
    # 如果需要测试自定义时间，取消下面的注释
    # print("\n\n使用自定义时间:")
    # asyncio.run(example_with_custom_time())

