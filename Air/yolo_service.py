"""
YOLO 车损检测服务模块
部署在无人机端，负责车辆损伤检测和数据预处理
此模块完全在无人机端运行，不依赖外部通信
"""

from ultralytics import YOLO
from PIL import Image
import io
import os

# 在函数外加载模型一次，避免每次调用时都重新加载
model = YOLO("best.pt")
print("模型加载完成")

def detect_carDamage(file, conf_thres: float = 0.25, save_result: bool = False, save_dir: str = "detection_results", output_name: str = None):
    """
    使用 YOLO 模型检测车辆损伤
    参数:
        file: 待检测的图像文件路径
        conf_thres: 置信度阈值，越高检测越精准（默认 0.25）
        save_result: 是否保存检测结果图片（默认 False）
        save_dir: 结果保存目录（默认 "detection_results"）
        output_name: 输出文件名（可选）
    返回:
        dict: 包含车损列表、图像尺寸、保存路径的字典
            - carDamage: 车损检测列表，每个元素包含 bbox、中心点、置信度
            - image_size: 图像尺寸 (宽，高)
            - save_path: 保存结果的路径（如果保存了）
    """
    img = Image.open(file)
    results = model(img, conf=conf_thres)
    carDamage = []
    print("检测已完成")
    
    save_path = None
    # 如果需要保存检测结果
    if save_result:
        os.makedirs(save_dir, exist_ok=True)
        save_path = results[0].save()
        print(f"检测结果已保存至：{save_path}")
    
    # 取出所有检测框的坐标和置信度
    for box in results[0].boxes:
        if float(box.conf[0]) >= conf_thres:  # 检测到车辆
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # 计算车损中心点并归一化
            x_center = (x1 + x2) / 2
            y_center = (y1 + y2) / 2
            img_width, img_height = img.size
            x_center_norm = x_center / img_width
            y_center_norm = y_center / img_height

            carDamage.append({
                "bbox": [x1, y1, x2, y2],  # 检测框左上角和右下角坐标
                "center": [x_center_norm, y_center_norm],  # 中心点归一化坐标（列表格式）
                "center_norm": (x_center_norm, y_center_norm),  # 中心点归一化坐标（元组格式）
                "confidence": float(box.conf[0]),  # 检测置信度
            })
            print("数据迁移已完成")
    
    return {
        "carDamage": carDamage,
        "image_size": img.size,
        "save_path": save_path
    }

def get_damage_center_for_llm(file, conf_thres: float = 0.5):
    """
    获取车损数据，用于本地决策
    参数:
        file: 待检测的图像文件路径
        conf_thres: 置信度阈值（默认 0.5）
    返回:
        dict or None: 包含最佳车损的中心点坐标、置信度和图像路径
            - center_norm: 归一化中心点坐标 (x, y)
            - confidence: 检测置信度
            - image_path: 图像路径
    """
    result = detect_carDamage(file, conf_thres)
    
    # 如果没有检测到任何车损，返回 None
    if not result['carDamage']:
        return None
    
    # 选择置信度最高的检测结果
    best_damage = max(result['carDamage'], key=lambda x: x['confidence'])
    
    return {
        'center_norm': best_damage['center_norm'],
        'confidence': best_damage['confidence'],
        'image_path': file
    }