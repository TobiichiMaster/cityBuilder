import numpy as np
import os
from PIL import Image

def merge_npy_masks(npy_data_list: list) -> np.ndarray:
    """
    接收一个包含多个 numpy 数组的列表，将它们在物理空间上合并。
    """
    if not npy_data_list:
        return None
        
    # 以第一个矩阵为底板
    merged_mask = npy_data_list[0].astype(bool)
    
    # 依次与后续的矩阵进行逻辑或 (OR) 运算
    for mask in npy_data_list[1:]:
        merged_mask = np.logical_or(merged_mask, mask.astype(bool))
        
    # 返回合并后的矩阵 (转回 0/255 的 uint8 格式，方便后续保存)
    return (merged_mask.astype(np.uint8)) * 255

def save_merged_asset(merged_npy_data: np.ndarray, original_image_rgb: np.ndarray, semantic_label: str, output_dir: str):
    """
    将合并后的 Numpy 矩阵保存为新的 .npy 文件，
    并根据原图裁剪出新的带透明通道的 RGBA .png 图片。
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = f"{semantic_label}_merged"
    
    # 1. 保存新的 NPY
    npy_output_path = os.path.join(output_dir, f"{base_name}.npy")
    np.save(npy_output_path, merged_npy_data)
    
    # 2. 生成新的透明 PNG 图片
    h, w = merged_npy_data.shape
    merged_bool = merged_npy_data > 0 # 转为 boolean 掩码
    
    # 创建 4 通道空画布 (RGBA)
    rgba_image = np.zeros((h, w, 4), dtype=np.uint8)
    
    # 将属于合并区域的原图颜色填入，并将透明度(Alpha)设为完全不透明(255)
    # 加入边界检查防止原图和 mask 尺寸不匹配
    try:
        rgba_image[merged_bool, :3] = original_image_rgb[merged_bool]
        rgba_image[merged_bool, 3] = 255
    except IndexError as e:
        print(f"❌ 矩阵尺寸与原图不匹配，无法合并颜色: {e}")
        return None, npy_output_path
    
    png_output_path = os.path.join(output_dir, f"{base_name}.png")
    Image.fromarray(rgba_image, 'RGBA').save(png_output_path)
    
    return png_output_path, npy_output_path