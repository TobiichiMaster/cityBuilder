import os
import numpy as np
import shutil

"""
load_stacked_mask_pairs() 读取单个mask和在整体npy文件中对于的npy数组，然后组合成一个pair
rename_and_move_asset() 会根据vlm返回的语义标签来修改mask的文件名，然后再把对于的npy文件单独保存下来
"""


def load_stacked_mask_pairs(npy_path: str, png_dir: str = None) -> list:
    """
    读取形状为 (N, H, W) 的合并 npy 文件，并与目录下的 object_top_X.png 匹配。
    """
    if not os.path.exists(npy_path):
        raise FileNotFoundError(f"找不到 NPY 文件: {npy_path}")
        
    if png_dir is None:
        png_dir = os.path.dirname(npy_path)

    print(f"📦 正在加载合并矩阵: {npy_path}")
    stacked_masks = np.load(npy_path)
    
    # 防止读取非三维矩阵崩溃
    if len(stacked_masks.shape) != 3:
        raise ValueError(f"输入的 NPY 矩阵不是三维 (N, H, W) 格式，当前形状: {stacked_masks.shape}")

    num_masks = stacked_masks.shape[0]
    pairs = [] 
    
    for i in range(num_masks):
        mask_2d = stacked_masks[i]
        base_name = f"object_top_{i+1}"
        png_path = os.path.join(png_dir, f"{base_name}.png")
        
        if os.path.exists(png_path):
            pairs.append({
                "id": base_name,
                "png_path": png_path,
                "npy_data": mask_2d 
            })
        else:
            print(f"⚠️ 警告: 找不到对应的图片文件 {png_path}")

    print(f"✅ 成功提取了 {len(pairs)} 个 Mask 对。")
    return pairs

def rename_and_move_asset(old_png_path: str, npy_data: np.ndarray, semantic_label: str, index: int, output_dir: str):
    """
    给资产赋予语义，保存新的 PNG 和独立的 NPY 到输出目录。
    """
    os.makedirs(output_dir, exist_ok=True)
    
    new_base_name = f"{semantic_label}_{index:03d}"
    new_png_path = os.path.join(output_dir, f"{new_base_name}.png")
    new_npy_path = os.path.join(output_dir, f"{new_base_name}.npy")
    
    # 复制图片并保存二维矩阵
    shutil.copy2(old_png_path, new_png_path)
    np.save(new_npy_path, npy_data)
    
    return new_png_path, new_npy_path