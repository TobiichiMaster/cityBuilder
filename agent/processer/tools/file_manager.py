import os
import numpy as np
import shutil

def load_stacked_mask_pairs(npy_path, png_dir=None):
    """
    读取形状为 (N, H, W) 的合并 npy 文件，并与目录下的 object_top_X.png 匹配。
    """
    if not os.path.exists(npy_path):
        raise FileNotFoundError(f"找不到 NPY 文件: {npy_path}")
        
    if png_dir is None:
        png_dir = os.path.dirname(npy_path)

    print(f"📦 正在加载合并矩阵: {npy_path}")
    # 1. 读取三维矩阵
    stacked_masks = np.load(npy_path)
    num_masks = stacked_masks.shape[0]
    
    pairs = [] #制作png文件和矩阵的pair
    
    # 2. 开始切片并组装数据
    for i in range(num_masks):
        mask_2d = stacked_masks[i]
        
        # 直接利用规律：第 0 个矩阵对应 object_top_1.png
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

def rename_and_move_asset(old_png_path, npy_data, semantic_label, index, output_dir):
    """
    给资产赋予语义，保存新的 PNG 和独立的 NPY 到输出目录。
    注意：这里我们直接传入 npy_data (二维矩阵) 并保存为新文件，而不是复制旧的合并版 NPY。
    """
    os.makedirs(output_dir, exist_ok=True)
    
    new_base_name = f"{semantic_label}_{index:03d}"
    new_png_path = os.path.join(output_dir, f"{new_base_name}.png")
    new_npy_path = os.path.join(output_dir, f"{new_base_name}.npy")
    
    # 复制图片
    shutil.copy2(old_png_path, new_png_path)
    
    # 将切片出来的二维矩阵保存为独立的 NPY 文件，方便后续单独调用
    np.save(new_npy_path, npy_data)
    
    return new_png_path, new_npy_path