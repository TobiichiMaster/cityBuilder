import os
import sys
import argparse
import cv2
import numpy as np
import torch
from PIL import Image

# ==========================================
# 📍 1. 动态路径注入 (防断连机制)
# ==========================================
# 当前脚本位于: cityBuilder/tools/workers/get_mask_worker.py
WORKER_DIR = os.path.dirname(os.path.abspath(__file__)) #cityBuilder/tools/workers
PROJECT_ROOT = os.path.dirname(os.path.dirname(WORKER_DIR)) #cityBuilder
SAM_SOURCE_DIR = os.path.join(PROJECT_ROOT, "utils", "segment-anything") #cityBuilder/utils/segment-anything

# 如果本地存在 segment-anything 源码包，优先加入环境变量最高优先级
if os.path.exists(SAM_SOURCE_DIR):
    sys.path.insert(0, SAM_SOURCE_DIR)

# 尝试导入核心模块，如果失败立刻报错给主进程
try:
    from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
except ImportError as e:
    print(f"❌ [Worker Error] 无法导入 segment_anything，请检查环境或 utils 目录: {e}", file=sys.stderr)
    sys.exit(1)


# ==========================================
# 🧠 2. 核心算法逻辑
# ==========================================
def filter_top_k_masks(raw_masks, top_k=4, min_area=2000, min_new_area_ratio=0.6):
    """
    使用贪心算法和面积排序过滤 SAM 生成的冗余掩码
    """
    candidates = [m for m in raw_masks if m['area'] > min_area]
    if not candidates:
        return []

    # 按置信度排序：优先处理 SAM 认为最准确的预测
    candidates.sort(key=lambda x: x['predicted_iou'], reverse=True)

    height, width = candidates[0]['segmentation'].shape
    occupancy_mask = np.zeros((height, width), dtype=bool)
    
    unique_masks = []
    for mask_data in candidates:
        current_seg = mask_data['segmentation']
        mask_area = mask_data['area']

        # 计算与已占用区域的重叠面积
        intersection = np.logical_and(current_seg, occupancy_mask)
        intersection_area = np.count_nonzero(intersection)

        # 计算这个 mask 贡献的全新面积比例
        new_area = mask_area - intersection_area
        keep_ratio = new_area / mask_area if mask_area > 0 else 0

        # 如果提供了足够多的新面积，则保留它
        if keep_ratio > min_new_area_ratio:
            unique_masks.append(mask_data)
            occupancy_mask = np.logical_or(occupancy_mask, current_seg)

    # 按面积大小排序，并截取最大的前 K 个
    unique_masks.sort(key=lambda x: x['area'], reverse=True)
    return unique_masks[:top_k]


def extract_and_save_masks(image_path, output_dir, top_k, checkpoint_path):
    """
    执行加载图片、分割、过滤并导出资产的全流程
    """
    os.makedirs(output_dir, exist_ok=True)

    print("  [SAM Worker] 正在加载 SAM (ViT-H) 大模型至显存...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        sam = sam_model_registry["vit_h"](checkpoint=checkpoint_path)
        sam.to(device=device)
    except Exception as e:
        print(f"❌ [Worker Error] 加载 SAM 权重失败，请检查权重路径: {checkpoint_path}\n报错: {str(e)}", file=sys.stderr)
        sys.exit(1)

    # 初始化生成器
    mask_generator = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=16,
        pred_iou_thresh=0.90,
        min_mask_region_area=2000
    )

    print(f"  [SAM Worker] 正在读取原图: {os.path.basename(image_path)}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ [Worker Error] 无法读取图片，文件可能不存在或损坏: {image_path}", file=sys.stderr)
        sys.exit(1)
        
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    print("  [SAM Worker] 模型正在进行全图神经推理，请稍候...")
    raw_masks = mask_generator.generate(image_rgb)
    print(f"  [SAM Worker] 推理完毕，初始生成 {len(raw_masks)} 个局部掩码。")

    print(f"  [SAM Worker] 正在应用贪心过滤算法，提取最大的 {top_k} 个主体...")
    filtered_masks = filter_top_k_masks(raw_masks, top_k=top_k)

    all_mask_arrays = []
    
    for i, mask_data in enumerate(filtered_masks):
        mask_bool = mask_data["segmentation"]
        all_mask_arrays.append(mask_bool)
        
        # 提取原图对应区域，保存为带透明通道 (RGBA) 的抠图 PNG
        h, w = mask_bool.shape
        rgba_image = np.zeros((h, w, 4), dtype=np.uint8)
        rgba_image[mask_bool, :3] = image_rgb[mask_bool] # 填入原图颜色
        rgba_image[mask_bool, 3] = 255                   # 设置不透明度(Alpha)为255
        
        png_filename = os.path.join(output_dir, f"object_top_{i+1}.png")
        Image.fromarray(rgba_image, 'RGBA').save(png_filename)

    # 聚合为一个整体的 .npy 文件供下游 Agent 使用
    if all_mask_arrays:
        stacked_masks = np.stack(all_mask_arrays, axis=0)
        npy_filename = os.path.join(output_dir, "top_objects_masks.npy")
        np.save(npy_filename, (stacked_masks.astype(np.uint8)) * 255)
        print(f"  [SAM Worker] ✅ 处理完成！共生成 {len(filtered_masks)} 个高质量资产切片。")
    else:
        print("  [SAM Worker] ⚠️ 警告：未提取到任何有效的物体掩码。")

    # 手动释放显存，防止在流水线中占用资源
    del sam
    del mask_generator
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ==========================================
# 🚀 3. CLI 入口 (由 main.py 通过 subprocess 调用)
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SAM 图像分割 Worker")
    parser.add_argument("--image", required=True, help="输入原图的绝对路径")
    parser.add_argument("--output", required=True, help="输出 masks 的绝对路径")
    parser.add_argument("--top_k", type=int, default=15, help="保留的最大 mask 数量")
    parser.add_argument("--checkpoint", required=True, help="SAM 权重文件的绝对路径")
    args = parser.parse_args()

    try:
        extract_and_save_masks(
            image_path=args.image, 
            output_dir=args.output, 
            top_k=args.top_k,
            checkpoint_path=args.checkpoint
        )
    except Exception as e:
        print(f"❌ [Worker Error] 发生了未捕获的致命异常:\n{str(e)}", file=sys.stderr)
        sys.exit(1)