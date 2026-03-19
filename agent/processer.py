import numpy as np
import cv2
from PIL import Image
import os

# 假设你有一个函数可以调用 VLM (例如 GPT-4o) 
# 传入 RGBA 抠图和原图，返回 'house', 'ground', 'background' 或 'other'
def ask_vlm_for_label(rgba_image_path):
    # 这里是伪代码，实际你需要组装 prompt 并请求大模型 API
    # prompt 示例: "Look at this transparent image. Is it a 'house', 'ground', 'background', or 'other'? Reply with just one word."
    # response = client.chat.completions.create(...)
    # return response.content.strip().lower()
    pass

def process_masks_with_agent(mask_records, output_dir, original_image_rgb):
    """
    mask_records: 包含多个 mask 信息的列表，例如 [{"segmentation": np.array, "rgba_path": "..."}]
    """
    os.makedirs(output_dir, exist_ok=True)
    
    houses = []
    ground_masks = []
    
    # 获取图像尺寸，用于初始化合并地面的画布
    h, w = mask_records[0]["segmentation"].shape
    merged_ground_mask = np.zeros((h, w), dtype=bool)

    print("🤖 Agent 正在进行语义识别...")
    
    for i, record in enumerate(mask_records):
        mask_bool = record["segmentation"]
        rgba_path = record["rgba_path"]
        
        # 1. 呼叫 Agent 打标签
        label = ask_vlm_for_label(rgba_path)
        print(f"Mask {i+1} 被 Agent 识别为: {label}")
        
        # 2. 根据标签执行不同逻辑
        if label == "background":
            # 直接丢弃
            continue
            
        elif label == "ground":
            # 收集所有的 ground mask 进行合并
            ground_masks.append(mask_bool)
            merged_ground_mask = np.logical_or(merged_ground_mask, mask_bool)
            
        elif label == "house":
            # 房子作为独立资产保留
            houses.append(mask_bool)

    # 3. 输出处理后的最终资产供 SAM3D 使用
    print("\n📦 正在打包最终 3D 资产输入源...")
    
    final_assets_paths = []

    # 导出合并后的地面
    if np.any(merged_ground_mask):
        ground_rgba = np.zeros((h, w, 4), dtype=np.uint8)
        ground_rgba[merged_ground_mask, :3] = original_image_rgb[merged_ground_mask]
        ground_rgba[merged_ground_mask, 3] = 255
        
        ground_path = os.path.join(output_dir, "asset_ground_merged.png")
        Image.fromarray(ground_rgba, 'RGBA').save(ground_path)
        final_assets_paths.append(ground_path)
        print("✅ 已生成合并后的地面资产图")

    # 导出独立的房子
    for idx, house_mask in enumerate(houses):
        house_rgba = np.zeros((h, w, 4), dtype=np.uint8)
        house_rgba[house_mask, :3] = original_image_rgb[house_mask]
        house_rgba[house_mask, 3] = 255
        
        house_path = os.path.join(output_dir, f"asset_house_{idx+1:03d}.png")
        Image.fromarray(house_rgba, 'RGBA').save(house_path)
        final_assets_paths.append(house_path)
        print(f"✅ 已生成房子资产图: asset_house_{idx+1:03d}.png")

    print(f"\n🎉 预处理完成！现在可以将这 {len(final_assets_paths)} 个清洗后的图片发送给 SAM3D 了。")
    return final_assets_paths