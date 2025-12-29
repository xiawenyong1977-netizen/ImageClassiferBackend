"""
文本生成功能使用示例
"""

import asyncio
from app.services.llm import LLMService


async def main():
    """示例：使用文本生成功能"""
    
    # 方式1：直接使用Deepseek（推荐）
    service = LLMService(
        provider="deepseek",
        api_key="sk-b55b7e703b0e45c1b326cb0a5e04fb2a",
        model="deepseek-chat"
    )
    
    # 简单文本生成
    result = await service.generate_text(
        prompt="请用一句话介绍Python编程语言"
    )
    
    if result["success"]:
        print(f"生成结果: {result['content']}")
    else:
        print(f"生成失败: {result['error']}")
    
    # 带系统提示词的文本生成
    result = await service.generate_text(
        prompt="写一首关于春天的诗",
        system_prompt="你是一位专业的诗人，擅长写优美的诗歌。",
        max_tokens=500,
        temperature=0.8
    )
    
    if result["success"]:
        print(f"\n诗歌生成结果:\n{result['content']}")
    else:
        print(f"生成失败: {result['error']}")
    
    # 方式2：使用其他provider，但文本生成会自动使用Deepseek
    service2 = LLMService(
        provider="aliyun",
        api_key="test_key",
        model="qwen-vl-plus"
    )
    
    # 即使provider是aliyun，文本生成也会使用Deepseek
    result = await service2.generate_text(
        prompt="解释什么是人工智能"
    )
    
    if result["success"]:
        print(f"\nAI解释: {result['content']}")
    else:
        print(f"生成失败: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())

