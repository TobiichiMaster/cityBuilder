import os
import sys
import json
import numpy as np
import torch

# 往上跳 3 层回到根目录
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.append(os.path.join(BASE_DIR, "utils", "sam3d", "notebook"))
sys.path.append(os.path.join(BASE_DIR, "utils", "sam3d"))

from inference import Inference, load_image

def tensor_to_list(obj):
    """辅助函数：安全地将 Tensor 或 Ndarray 转为 List (借鉴自你的优秀代码)"""
    if isinstance(obj, torch.Tensor):
        return obj.detach().cpu().numpy().tolist()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

class Sam3DClient:
    def __init__(self, config_path):
        """
        初始化 SAM3D 客户端。确保流水线中模型只加载一次。
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"找不到 SAM3D 配置文件: {config_path}")
            
        print("🤖 正在加载 SAM3D 模型进入显存...")
        self.inference = Inference(config_path, compile=False)
        print("✅ SAM3D 模型加载完毕！")

    def generate_3d_asset(self, original_image_path, mask_npy_path, output_glb_path):
        """
        调用 SAM3D 生成 3D 模型。
        直接导出原始网格，并将 T/R/S 坐标信息保存为 JSON 供 Blender 使用。
        """
        print(f"  🧱 正在为 {os.path.basename(mask_npy_path)} 重建 3D 资产...")
        
        # 加载图像和 Mask
        image = load_image(original_image_path)
        mask = np.load(mask_npy_path)
        mask = mask > 0  # 确保类型安全
        
        # 运行推理
        output = self.inference(image, mask, seed=42)

        if "glb" in output and output["glb"] is not None:
            # 1. 直接导出原始网格 (绕过所有复杂的 PyTorch3D 顶点变换)
            os.makedirs(os.path.dirname(output_glb_path), exist_ok=True)
            output["glb"].export(output_glb_path)

            # 2. 提取原始缩放、平移和旋转四元数，保存为 JSON
            metadata = {
                "source_mask": os.path.basename(mask_npy_path),
                "glb_file": os.path.basename(output_glb_path),
                "translation": tensor_to_list(output.get("translation", [0, 0, 0])),
                "rotation": tensor_to_list(output.get("rotation", [1, 0, 0, 0])),
                "scale": tensor_to_list(output.get("scale", [1, 1, 1]))
            }
            
            json_output_path = output_glb_path.replace(".glb", "_info.json")
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)
                
            print(f"  ✅ 成功导出 3D 模型: {os.path.basename(output_glb_path)}")
            print(f"  ✅ 成功导出坐标元数据: {os.path.basename(json_output_path)}")
            
            # 清理显存缓存
            del output
            import gc; gc.collect()
            torch.cuda.empty_cache()
            
            return output_glb_path, json_output_path
        else:
            raise ValueError("SAM3D 未能生成 GLB 数据")