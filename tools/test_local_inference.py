"""
测试本地模型推理服务
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.local_model_inference import local_model_inference
from loguru import logger


async def test_local_inference():
    """测试本地模型推理"""
    
    try:
        logger.info("=" * 80)
        logger.info("🚀 开始测试本地模型推理服务")
        logger.info("=" * 80)
        
        # 初始化模型
        logger.info("\n📦 步骤1: 初始化模型...")
        await local_model_inference.initialize()
        
        # 检查模型加载状态
        logger.info(f"\n✅ 模型初始化完成，已加载模型: {list(local_model_inference.models.keys())}")
        
        # 测试图片路径（需要准备测试图片）
        test_images = [
            # 可以添加测试图片路径
            # "test_images/person.jpg",
            # "test_images/cat.jpg",
            # "test_images/idcard.jpg",
        ]
        
        if not test_images:
            logger.warning("⚠️ 未提供测试图片，请添加测试图片路径到 test_images 列表")
            logger.info("\n💡 提示：可以创建 test_images 目录并放置测试图片")
            return
        
        # 测试每张图片
        for i, image_path in enumerate(test_images, 1):
            if not os.path.exists(image_path):
                logger.warning(f"⚠️ 图片不存在: {image_path}")
                continue
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"📸 测试图片 {i}/{len(test_images)}: {image_path}")
            logger.info(f"{'=' * 80}")
            
            # 读取图片
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # 执行推理
            logger.info("🔍 开始推理...")
            result = await local_model_inference.classify_image(image_bytes)
            
            # 显示结果
            logger.info("\n" + "=" * 80)
            logger.info("📊 推理结果:")
            logger.info("=" * 80)
            logger.info(f"✅ 成功: {result['success']}")
            logger.info(f"🏷️  分类: {result['categoryId']}")
            logger.info(f"📈 置信度: {result['confidence']}")
            logger.info(f"💬 消息: {result['message']}")
            logger.info(f"📐 图片尺寸: {result['imageDimensions']}")
            logger.info(f"\n🆔 ID卡检测: {len(result['idCardDetections'])}个")
            for det in result['idCardDetections']:
                logger.info(f"  - {det['className']}: {det['confidence']:.3f}")
            
            logger.info(f"\n🔍 通用检测: {len(result['generalDetections'])}个")
            for det in result['generalDetections'][:10]:  # 只显示前10个
                logger.info(f"  - {det['className']}: {det['confidence']:.3f}")
            
            if result['mobileNetV3Detections'] and 'predictions' in result['mobileNetV3Detections']:
                logger.info(f"\n🧠 MobileNetV3 Top-5预测:")
                for pred in result['mobileNetV3Detections']['predictions']:
                    logger.info(f"  - {pred['class']}: {pred['probability']:.3f}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ 所有测试完成！")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        raise


async def test_api_compatibility():
    """测试API兼容性 - 验证输出格式"""
    
    logger.info("\n" + "=" * 80)
    logger.info("🔧 测试API兼容性")
    logger.info("=" * 80)
    
    try:
        # 初始化模型
        await local_model_inference.initialize()
        
        # 创建一个简单的测试图片（纯色图片）
        from PIL import Image
        import io
        
        # 创建一个100x100的红色图片
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        
        # 执行推理
        result = await local_model_inference.classify_image(img_bytes)
        
        # 验证输出字段
        required_fields = [
            'success',
            'categoryId',
            'confidence',
            'message',
            'idCardDetections',
            'generalDetections',
            'mobileNetV3Detections',
            'imageDimensions',
            'allModelResults'
        ]
        
        logger.info("\n📋 验证输出字段:")
        all_fields_present = True
        for field in required_fields:
            present = field in result
            status = "✅" if present else "❌"
            logger.info(f"  {status} {field}: {present}")
            if not present:
                all_fields_present = False
        
        if all_fields_present:
            logger.info("\n✅ 所有必需字段都存在！")
            logger.info("\n📦 完整输出结构:")
            import json
            logger.info(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            logger.error("\n❌ 缺少必需字段！")
        
    except Exception as e:
        logger.error(f"❌ 兼容性测试失败: {e}", exc_info=True)
        raise


async def main():
    """主函数"""
    
    # 配置日志
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    try:
        # 测试API兼容性
        await test_api_compatibility()
        
        # 测试实际推理（如果有测试图片）
        await test_local_inference()
        
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

