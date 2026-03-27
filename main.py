import asyncio
import os
import sys
import shutil
import concurrent.futures
from pathlib import Path

# 确保能导入内部模块
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import Config
from agents.core import run_heterogeneous_agents

# ✨ 像搭积木一样导入底层的执行客户端
from tools.pipeline.sam_client import SamClient
from tools.pipeline.sam3d_client import Sam3DClient

def clean_directory(dir_path):
    """清空目录，防止历史残留影响后续生成"""
    if os.path.exists(dir_path):
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                pass
    else:
        os.makedirs(dir_path, exist_ok=True)

async def main():
    print("🌟 [CityBuilder] 自动化场景重建系统启动...")
    
    source_image = Config.default_source_image
    
    assets_dir = Config.assets_path if getattr(Config, 'assets_path', None) else "assets"
    if not os.path.isabs(assets_dir):
        assets_dir = os.path.join(BASE_DIR, assets_dir)
        
    models_dir = os.path.join(assets_dir, "models")
    masks_dir = os.path.join(assets_dir, "masks")

    # ------------------------------------------
    # 🧹 步骤 0: 初始化与清理
    # ------------------------------------------
    print("\n🧹 步骤 0: 正在清理历史数据...")
    clean_directory(models_dir)
    clean_directory(masks_dir)

    # ------------------------------------------
    # 🔪 步骤 1: 2D 视觉处理 (SamClient)
    # ------------------------------------------
    print("\n🔪 步骤 1: 启动 2D 视觉资产处理流水线...")
    try:
        sam_client = SamClient()
        # 1.1 获取基础掩码
        sam_client.generate_masks(source_image=source_image, output_dir=masks_dir, top_k=15)
        # 1.2 清洗与合并资产
        sam_client.process_masks(input_dir=masks_dir, output_dir=models_dir, original_image_path=source_image)
    except Exception as e:
        print(f"\n❌ 视觉处理失败: {str(e)}")
        return
        
    # ------------------------------------------
    # 🏭 步骤 2: 3D 升维阶段 (多卡并发版)
    # ------------------------------------------
    print("\n🏭 步骤 2: 开始将清洗后的 2D 资产升维至 3D (启用多卡高并发)...")
    
    # 🌟 显式控制区：你要使用的 GPU 列表 (想用几张卡，就写几个 ID)
    # 例如：你有 8 张卡，现在我们只用前 2 张，就写 [0, 1]
    AVAILABLE_GPUS = [0, 1] 
    MAX_CONCURRENT = len(AVAILABLE_GPUS)
    
    try:
        sam3d_client = Sam3DClient()
        
        # 收集所有需要转换的 npy 文件
        npy_tasks = [f for f in os.listdir(models_dir) if f.endswith(".npy") and "top_objects" not in f]
        
        # 定义单体任务包装器
        def process_single_asset(task_idx, filename):
            # 轮询分配法：任务 0 给卡 0，任务 1 给卡 1，任务 2 又给卡 0...
            gpu_id = AVAILABLE_GPUS[task_idx % MAX_CONCURRENT]
            
            mask_npy = os.path.join(models_dir, filename)
            out_glb = os.path.join(models_dir, filename.replace(".npy", ".glb"))
            
            sam3d_client.generate_3d_asset(
                original_image_path=source_image, 
                mask_npy_path=mask_npy, 
                output_glb_path=out_glb,
                gpu_id=gpu_id
            )

        # 🚀 启动线程池进行派发
        print(f"  🚥 并发引擎已启动，分配了 {MAX_CONCURRENT} 张显卡，共 {len(npy_tasks)} 个资产等待生成...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
            futures = []
            for idx, filename in enumerate(npy_tasks):
                futures.append(executor.submit(process_single_asset, idx, filename))
                
            # 等待所有任务完成，并捕获子线程中可能出现的异常
            for future in concurrent.futures.as_completed(futures):
                future.result() 
                
        print("🎊 所有 3D 资产多卡并发生成完毕，模型与坐标就绪！")
    except Exception as e:
        print(f"\n❌ 3D 升维阶段出现致命错误: {str(e)}")
        return

    # ------------------------------------------
    # 🤖 步骤 3: Agent 智能体协同搭建
    # ------------------------------------------
    print("\n🤖 步骤 3: 唤醒双脑智能体系统，开始空间组装...")
    await run_heterogeneous_agents(source_image)
    
    print("\n🏁 [CityBuilder] 任务全部结束！请打开 assets/scenes/output.blend 查看最终成果。")

if __name__ == "__main__":
    asyncio.run(main())