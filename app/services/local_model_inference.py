"""
本地神经网络模型推理服务
使用Ultralytics库简化YOLO预处理和后处理
使用torchvision.transforms简化MobileNetV3预处理
"""

import os
import numpy as np
from PIL import Image
import io
from typing import Dict, List, Tuple, Optional
from loguru import logger

# 导入必需的库（服务器环境已确保安装）
from ultralytics import YOLO
import torchvision.transforms as transforms

import onnxruntime as ort


class LocalModelInference:
    """本地模型推理服务类（只做模型推理，不做分类映射）"""
    
    def __init__(self):
        """初始化模型推理服务"""
        self.models = {}
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        
        # 模型路径
        self.model_paths = {
            "idCard": os.path.join(self.model_dir, "id_card_detection.onnx"),
            "yolo8s": os.path.join(self.model_dir, "yolov8s.onnx"),
            "mobilenetv3": os.path.join(self.model_dir, "mobilenetv3_rw_Opset17.onnx")
        }
        
        # MobileNetV3标准预处理（使用torchvision）
        self.mobilenet_transform = transforms.Compose([
            transforms.Resize(256),                      # 缩放到256
            transforms.CenterCrop(224),                  # 中心裁剪到224
            transforms.ToTensor(),                       # 转换为Tensor并归一化到[0,1]
            # 注意：MobileNetV3通常不需要ImageNet标准化，已经在[0,1]范围
        ])
        
        self.is_initialized = False
    
    async def initialize(self):
        """
        初始化模型（严格模式）
        
        如果模型文件不存在或加载失败，将抛出异常
        确保服务器环境的模型完整性
        """
        if self.is_initialized:
            return
        
        logger.info("🚀 开始初始化本地ONNX模型（严格模式）...")
        
        # 加载YOLO模型（严格模式：必须成功）
        for model_name in ["idCard", "yolo8s"]:
            model_path = self.model_paths[model_name]
            
            # 检查文件存在性
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"模型文件不存在: {model_path}")
            
            # 加载模型（失败将抛异常）
            self.models[model_name] = YOLO(model_path, task='detect')
            logger.info(f"✅ {model_name}模型加载成功")
        
        # 加载MobileNetV3（严格模式：必须成功）
        model_path = self.model_paths["mobilenetv3"]
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] \
            if 'CUDAExecutionProvider' in ort.get_available_providers() \
            else ['CPUExecutionProvider']
        
        self.models["mobilenetv3"] = ort.InferenceSession(
            model_path,
            sess_options=session_options,
            providers=providers
        )
        logger.info(f"✅ MobileNetV3模型加载成功")
        
        self.is_initialized = True
        logger.info(f"✅ 本地模型初始化完成，共加载 {len(self.models)} 个模型")
    
    def detect_with_yolo(self, image_bytes: bytes, model_name: str, conf_threshold: float = 0.25) -> List[Dict]:
        """
        使用Ultralytics YOLO进行检测（自动预处理和后处理）
        
        Args:
            image_bytes: 图片二进制数据
            model_name: 模型名称 ('idCard' 或 'yolo8s')
            conf_threshold: 置信度阈值
            
        Returns:
            检测结果列表
        """
        try:
            # 加载图片
            image = Image.open(io.BytesIO(image_bytes))
            
            # 使用Ultralytics进行推理（自动预处理和后处理）
            results = self.models[model_name](
                image,
                conf=conf_threshold,
                verbose=False  # 不打印详细信息
            )
            
            # 转换结果格式
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    # 获取边界框（xyxy格式转xywh）
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = xyxy
                    x = (x1 + x2) / 2
                    y = (y1 + y2) / 2
                    w = x2 - x1
                    h = y2 - y1
                    
                    # 获取类别名称
                    class_name = result.names[class_id] if hasattr(result, 'names') else f'class_{class_id}'
                    
                    detections.append({
                        'classId': class_id,
                        'className': class_name,
                        'confidence': confidence,
                        'bbox': [float(x), float(y), float(w), float(h)]
                    })
            
            logger.debug(f"{model_name}检测到{len(detections)}个物体")
            return detections
            
        except Exception as e:
            logger.error(f"{model_name}推理失败: {e}")
            return []
    
    def classify_mobilenet(self, image_bytes: bytes, conf_threshold: float = 0.3) -> Dict:
        """MobileNetV3分类"""
        try:
            # 预处理（使用torchvision）
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            tensor = self.mobilenet_transform(image)
            input_tensor = tensor.unsqueeze(0).numpy()  # (1, C, H, W)
            
            # 推理
            outputs = self.models["mobilenetv3"].run(['496'], {'x': input_tensor})
            output = outputs[0][0]
            
            # Softmax
            exp_output = np.exp(output - np.max(output))
            probabilities = exp_output / np.sum(exp_output)
            
            # Top-5
            top_indices = np.argsort(probabilities)[-5:][::-1]
            
            predictions = []
            valid_predictions = []
            
            for idx in top_indices:
                prob = float(probabilities[idx])
                prediction = {
                    'index': int(idx),
                    'probability': prob,
                    'class': f'imagenet_class_{idx}'
                }
                predictions.append(prediction)
                
                if prob >= conf_threshold:
                    valid_predictions.append(prediction)
            
            return {
                'predictions': predictions,
                'validPredictions': valid_predictions,
                'topPrediction': predictions[0] if predictions else None,
                'confidence': predictions[0]['probability'] if predictions else 0
            }
            
        except Exception as e:
            logger.error(f"MobileNetV3推理失败: {e}")
            return {}
    
    # 注意：
    # 1. 手机截图识别应该在客户端完成（上传前），因为服务器收到的图片已经过缩放处理
    # 2. 分类映射（categoryId）也应该在客户端完成，因为：
    #    - 客户端有完整的 MapObjectes2Category 实现
    #    - 客户端有 configService 配置驱动的映射规则
    #    - 客户端有主角识别（identifyMainRole）面积占比计算
    #    - 客户端可以灵活调整分类策略
    # 
    # 服务器端只负责返回原始检测结果，客户端负责业务逻辑映射
    
    async def classify_image(self, image_bytes: bytes) -> Dict:
        """
        执行模型推理，返回原始检测结果（不做分类映射）
        
        服务器端只负责模型推理，返回原始检测结果
        客户端负责使用这些结果进行分类映射（MapObjectes2Category）
        
        Returns:
            原始检测结果
        """
        try:
            # 确保模型已初始化
            if not self.is_initialized:
                await self.initialize()
            
            # 执行所有模型推理（严格模式：初始化成功保证模型已加载）
            logger.info("🔍 执行所有模型推理...")
            
            # ID卡检测（使用Ultralytics）
            id_card_detections = self.detect_with_yolo(image_bytes, 'idCard', conf_threshold=0.7)
            
            # YOLO8s通用检测（使用Ultralytics）
            general_detections = self.detect_with_yolo(image_bytes, 'yolo8s', conf_threshold=0.25)
            
            # MobileNetV3分类
            mobilenet_result = self.classify_mobilenet(image_bytes, conf_threshold=0.3)
            
            # 返回原始检测结果（不包含 categoryId 和 imageDimensions，由客户端提供）
            return {
                'success': True,
                'message': '模型推理完成',
                'idCardDetections': id_card_detections,
                'generalDetections': general_detections,
                'mobileNetV3Detections': mobilenet_result
            }
            
        except Exception as e:
            logger.error(f"❌ 模型推理失败: {e}")
            return {
                'success': False,
                'message': f'推理失败: {str(e)}',
                'idCardDetections': [],
                'generalDetections': [],
                'mobileNetV3Detections': {}
            }


# 全局实例
local_model_inference = LocalModelInference()

