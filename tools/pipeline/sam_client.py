import subprocess
import os
import sys
import cv2

# 📍 动态定位项目根目录
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(PIPELINE_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config

# 导入我们写好的 Pipeline 工具
from tools.pipeline.file_manager import load_stacked_mask_pairs, rename_and_move_asset
from tools.pipeline.mask_operations import merge_npy_masks, save_merged_asset
from tools.pipeline.vlm_client import ask_vlm_for_label

class SamClient:
    def __init__(self):
        # 自动读取底层执行环境与权重
        self.sam_python_exe = Config.sam_python_exe
        self.sam_checkpoint = Config.sam_checkpoint_path
        self.worker_script = os.path.join(PROJECT_ROOT, "tools", "workers", "get_mask_worker.py")

    def generate_masks(self, source_image: str, output_dir: str, top_k: int = 15):
        """阶段 1：调用底层 SAM 环境执行抠图"""
        print(f"  [Sam Client] 正在跨环境呼叫 SAM 进行图像分割...")
        cmd = [
            self.sam_python_exe,
            self.worker_script,
            "--image", source_image,
            "--output", output_dir,
            "--top_k", str(top_k),
            "--checkpoint", self.sam_checkpoint
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"  ✅ SAM 图像分割成功，Masks 已存入: {output_dir}")
        except subprocess.CalledProcessError:
            raise RuntimeError("SAM 图像分割底层执行失败，请检查上方 worker 输出的错误信息。")

    def process_masks(self, input_dir: str, output_dir: str, original_image_path: str = None):
        """阶段 2：调用视觉大模型进行语义分类，并对碎片进行同类项合并"""
        print(f"  [Sam Client] 启动视觉清洗与合并工作流...")
        
        npy_path = os.path.join(input_dir, "top_objects_masks.npy")
        if not os.path.exists(npy_path):
            raise FileNotFoundError(f"找不到输入矩阵文件 {npy_path}")

        mask_pairs = load_stacked_mask_pairs(npy_path, png_dir=input_dir)
        semantic_groups = {}

        print("  🧠 正在向 VLM 发送图层进行语义识别...")
        for pair in mask_pairs:
            label = ask_vlm_for_label(
                mask_png_path=pair['png_path'],
                original_image_path=original_image_path
            )
            print(f"    👉 资产 {pair['id']} 被打上标签: [{label}]")
            
            if label == "background":
                continue
            
            if label not in semantic_groups:
                semantic_groups[label] = []
            semantic_groups[label].append({
                "old_png_path": pair['png_path'],
                "npy_data": pair['npy_data']
            })

        print("  📦 正在合并同类项并导出最终 2D 资产...")
        original_image_rgb = None
        if original_image_path and os.path.exists(original_image_path):
            img_bgr = cv2.imread(original_image_path)
            if img_bgr is not None:
                original_image_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        sorted_labels = sorted(semantic_groups.keys())
        for label in sorted_labels:
            if label == "background":
                continue

            items = semantic_groups[label]
            if label == "ground" and len(items) > 1:
                npy_data_list = [item["npy_data"] for item in items]
                merged_npy = merge_npy_masks(npy_data_list)
                
                if original_image_rgb is not None:
                    png_path, final_npy_path = save_merged_asset(
                        merged_npy_data=merged_npy,
                        original_image_rgb=original_image_rgb,
                        semantic_label=label,
                        output_dir=output_dir
                    )
                    if final_npy_path:
                        print(f"    ✅ 聚合资产导出: {os.path.basename(final_npy_path)}")
            else:
                for idx, item in enumerate(items):
                    new_png, new_npy = rename_and_move_asset(
                        old_png_path=item["old_png_path"],
                        npy_data=item["npy_data"],
                        semantic_label=label,
                        index=idx + 1,  
                        output_dir=output_dir
                    )
                    print(f"    ✅ 单体资产导出: {os.path.basename(new_npy)}")
        
        print("  🎉 Sam Client 2D 资产清洗完毕！")