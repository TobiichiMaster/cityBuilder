import os
import cv2
import sys
from pathlib import Path

# 引入项目根目录的配置
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import Config,BASE_DIR

# 引入我们写好的底层工具
from tools.file_manager import load_stacked_mask_pairs, rename_and_move_asset
from tools.mask_operations import merge_npy_masks, save_merged_asset
from tools.vlm_client import ask_vlm_for_label

# 地址配置
assets_path = Config.assets_path
masks_path = os.path.join(assets_path,"masks")

class VisionProcesserAgent:
    def __init__(self, input_dir="assets/masks", output_dir="assets/processed_assets", original_image_path=None):
        self.input_dir = os.path.join(BASE_DIR, input_dir)
        self.output_dir = os.path.join(BASE_DIR, output_dir)
        if original_image_path:
            self.original_image_path = os.path.join(BASE_DIR, original_image_path)
        else:
            self.original_image_path = None

        # 挂载配置中的 Observer 大模型参数 (专门用于视觉识别)
        self.vlm_api_key = Config.processer_api_key
        self.vlm_base_url = Config.processer_base_url
        self.vlm_model = Config.processer_model_id

    def run_pipeline(self):
        print("🚀 启动 Vision Processer 资产处理工作流...")
        
        # 定义输入文件路径
        npy_path = os.path.join(self.input_dir, "top_objects_masks.npy")
        if not os.path.exists(npy_path):
            print(f"❌ 错误: 找不到输入矩阵文件 {npy_path}")
            return

        # 1. 加载切片数据 (NPY 与对应的 PNG 配对)
        mask_pairs = load_stacked_mask_pairs(npy_path, png_dir=self.input_dir)
        
        # 用于对具有相同语义的资产进行分组
        semantic_groups = {}

        # 2. 调用 VLM 思考与判断
        print("\n🧠 正在将图层发送至 Observer 大模型进行语义识别...")
        for pair in mask_pairs:
            png_path = pair['png_path']
            npy_data = pair['npy_data']
            
            # 请求大模型
            label = ask_vlm_for_label(
                mask_png_path=png_path,
                original_image_path=self.original_image_path,
                model=self.vlm_model,
                api_key=self.vlm_api_key,
                base_url=self.vlm_base_url
            )
            print(f"  👉 资产 {pair['id']} 被打上标签: [{label}]")
            
            # 严格丢弃背景
            if label == "background":
                print(f"  🗑️ 已丢弃无用背景图层。")
                continue
            
            # 存入分组字典，准备后续合并
            if label not in semantic_groups:
                semantic_groups[label] = []
                
            semantic_groups[label].append({
                "old_png_path": png_path,
                "npy_data": npy_data
            })

        # 3. 按字典顺序排序并执行合并/落地
        print("\n📦 正在合并同类项并生成最终 3D 注入资产...")
        
        # 加载原图 RGB 信息 (用于在合并矩阵后，重新扣出带有色彩和透明通道的合并图像)
        original_image_rgb = None
        if self.original_image_path and os.path.exists(self.original_image_path):
            img_bgr = cv2.imread(self.original_image_path)
            if img_bgr is not None:
                original_image_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        else:
            print("  ⚠️ 警告: 未提供原图路径，合并后的资产将无法生成带颜色的 PNG 图片。")

        # 提取字典的所有 key 并按字母表顺序排序 (例如 animal, ground, house, tree...)
        sorted_labels = sorted(semantic_groups.keys())
        
        for label in sorted_labels:
            # 严格丢弃背景 (虽然在上方的 VLM 请求阶段已经过滤过一次，这里作为兜底防御)
            if label == "background":
                continue

            items = semantic_groups[label]
            
            # 逻辑分支 A: 只有标签是 ground 且数量大于 1 时，才进行合并
            if label == "ground" and len(items) > 1:
                print(f"  🔄 发现 {len(items)} 个 '{label}'，正在进行地面矩阵物理合并...")
                npy_data_list = [item["npy_data"] for item in items]
                
                # 合并底层的 numpy 数组
                merged_npy = merge_npy_masks(npy_data_list)
                
                if original_image_rgb is not None:
                    # 根据合并后的数组和原图，重新切出一张全景的大图
                    png_path, npy_path = save_merged_asset(
                        merged_npy_data=merged_npy,
                        original_image_rgb=original_image_rgb,
                        semantic_label=label,
                        output_dir=self.output_dir
                    )
                    print(f"  ✅ 聚合地面资产已导出: {os.path.basename(npy_path)}")
                    
            # 逻辑分支 B: 对于单个 ground，以及所有的 house、tree、animal 等其他资产
            # 无论数量多少，都不合并，而是依次赋予独立编号并导出
            else:
                for idx, item in enumerate(items):
                    new_png, new_npy = rename_and_move_asset(
                        old_png_path=item["old_png_path"],
                        npy_data=item["npy_data"],
                        semantic_label=label,
                        index=idx + 1,  # 确保编号依次递增，例如 house_001, house_002
                        output_dir=self.output_dir
                    )
                    print(f"  ✅ 单体资产已导出: {os.path.basename(new_npy)}")

        print("\n🎉 Vision Processer 处理完毕，所有清洗后的 NPY/PNG 资产已放入输出目录！")


# ================== 测试入口 ==================
if __name__ == "__main__":
    # 填入原始大图的路径，用于做上下文推理和最终裁图
    ORI_IMAGE = "assets/source/9.png" 
    
    agent = VisionProcesserAgent(
        input_dir=masks_path,
        output_dir="assets/processed_assets",
        original_image_path=ORI_IMAGE
    )
    
    agent.run_pipeline()