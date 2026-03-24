import cv2
import numpy as np
import torch
import os
from PIL import Image
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
import argparse

def filter_top_k_masks(raw_masks, top_k=4, min_area=2000, min_new_area_ratio=0.6):
    """
    使用贪心算法和面积排序过滤 SAM 生成的冗余掩码
    """
    # 1. 基础过滤：移除面积太小的噪点
    candidates = [m for m in raw_masks if m['area'] > min_area]
    
    if not candidates:
        return []

    # 2. 按置信度排序：优先处理 SAM 认为最准确的预测
    candidates.sort(key=lambda x: x['predicted_iou'], reverse=True)

    # 3. 贪心去重：确保每个 mask 都贡献了足够多的“新”区域，避免嵌套
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
            # 更新全局占用矩阵
            occupancy_mask = np.logical_or(occupancy_mask, current_seg)

    # 4. 按面积大小排序，并截取最大的前 K 个
    unique_masks.sort(key=lambda x: x['area'], reverse=True)
    return unique_masks[:top_k]


def extract_and_save_masks(image_path, output_dir, top_k=4, model_type="vit_h", checkpoint_path="sam_vit_h_4b8939.pth"):
    os.makedirs(output_dir, exist_ok=True)

    print("正在加载 SAM 模型...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    sam = sam_model_registry[model_type](checkpoint=checkpoint_path)
    sam.to(device=device)

    # 初始化生成器：适当降低采样点，结合后处理能达到最好效果
    mask_generator = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=16,
        pred_iou_thresh=0.90,
        min_mask_region_area=2000
    )

    print(f"正在处理图片: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法加载图片: {image_path}")
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    print("正在生成初始掩码...")
    raw_masks = mask_generator.generate(image_rgb)
    print(f"SAM 初始生成了 {len(raw_masks)} 个 masks。")

    # ================= 核心：应用过滤算法 =================
    print(f"正在应用智能过滤，提取最大的 {top_k} 个主体...")
    filtered_masks = filter_top_k_masks(raw_masks, top_k=top_k)
    print(f"过滤完成，最终保留了 {len(filtered_masks)} 个 masks。")
    # ======================================================

    all_mask_arrays = []

    for i, mask_data in enumerate(filtered_masks):
        mask_bool = mask_data["segmentation"]
        all_mask_arrays.append(mask_bool)
        
        # 提取原图对应区域，保存为带透明通道 (RGBA) 的抠图 PNG
        h, w = mask_bool.shape
        rgba_image = np.zeros((h, w, 4), dtype=np.uint8)
        rgba_image[mask_bool, :3] = image_rgb[mask_bool] # 填入原图颜色
        rgba_image[mask_bool, 3] = 255                   # 设置不透明度(Alpha)为255
        
        pil_image = Image.fromarray(rgba_image, 'RGBA')
        png_filename = os.path.join(output_dir, f"object_top_{i+1}.png")
        pil_image.save(png_filename)
        print(f"已保存抠图: {png_filename}")

    # 保存 .npy 文件
    if all_mask_arrays:
        stacked_masks = np.stack(all_mask_arrays, axis=0)
        npy_filename = os.path.join(output_dir, "top_objects_masks.npy")
        
        # 将布尔值转换为 0/255 的 uint8 格式保存
        np.save(npy_filename, (stacked_masks.astype(np.uint8)) * 255)
        print(f"\n全部处理完成！.npy 文件已保存，形状为: {stacked_masks.shape} (N, H, W)")

if __name__ == "__main__":
    # 使用 argparse 接收从 main.py 传过来的动态参数
    parser = argparse.ArgumentParser(description="SAM 图像分割 Worker")
    parser.add_argument("--image", required=True, help="输入原图的绝对路径")
    parser.add_argument("--output", required=True, help="输出 masks 的绝对路径")
    parser.add_argument("--top_k", type=int, default=15, help="保留的最大 mask 数量")
    parser.add_argument("--checkpoint", required=True, help="SAM 权重文件的绝对路径")
    args = parser.parse_args()

    # 执行核心逻辑
    extract_and_save_masks(
        image_path=args.image, 
        output_dir=args.output, 
        top_k=args.top_k,
        model_type="vit_h", 
        checkpoint_path=args.checkpoint
    )
