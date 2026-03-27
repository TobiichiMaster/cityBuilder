import os
import sys
from pathlib import Path

# 确保能导入内部模块
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import Config
from tools.pipeline.sam3d_client import Sam3DClient

def run_test():
    print("🛠️ 开始独立测试 Sam3DClient...")
    
    # 1. 初始化客户端 (它会自动去读 Config 里的环境配置)
    try:
        client = Sam3DClient()
    except Exception as e:
        print(f"❌ 客户端初始化失败，请检查 .env 配置: {e}")
        return

    # 2. 准备测试数据路径
    source_image = Config.default_source_image
    
    assets_dir = Config.assets_path if getattr(Config, 'assets_path', None) else "assets"
    if not os.path.isabs(assets_dir):
        assets_dir = os.path.join(BASE_DIR, assets_dir)
        
    models_dir = os.path.join(assets_dir, "models")
    
    # ⚠️ 寻找一个用来测试的 .npy 文件
    # 这里我们随便找 models 目录下第一个 .npy 文件来测试
    test_npy_path = None
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            if f.endswith(".npy") and "top_objects" not in f:
                test_npy_path = os.path.join(models_dir, f)
                break
                
    if not test_npy_path:
        print(f"❌ 测试中止：在 {models_dir} 下找不到任何可用的 .npy 掩码文件！")
        print("💡 建议：请先完整运行一次 `python main.py` 的前两步，或者手动放一个合法的 .npy 文件进去。")
        return
        
    # 定义输出路径
    out_glb = test_npy_path.replace(".npy", "_test_output.glb")
    
    # 3. 执行核心生成逻辑
    print(f"  👉 找到测试掩码: {os.path.basename(test_npy_path)}")
    print(f"  👉 准备输出至: {os.path.basename(out_glb)}")
    
    try:
        client.generate_3d_asset(
            original_image_path=source_image, 
            mask_npy_path=test_npy_path, 
            output_glb_path=out_glb
        )
        print(f"\n🎉 独立测试大成功！请检查生成的模型文件。")
    except Exception as e:
        print(f"\n💥 测试执行失败: {e}")

if __name__ == "__main__":
    run_test()