"""
cityBuilder 整体流程：
1、创建并清空场景 blender_script/init_scene.py
2、资产生成
3、资产第一次粗略摆放
4、Agent接手
    a、

"""
import asyncio
import os
import sys
import shutil
import subprocess
from pathlib import Path

# 确保能导入内部模块
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

from config import Config
from agent.processer.processer import VisionProcesserAgent
from agent.core import run_heterogeneous_agents

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
                print(f"无法删除 {file_path}. 原因: {e}")
    else:
        os.makedirs(dir_path, exist_ok=True)

async def main():
    print("🌟 [CityBuilder] 自动化场景重建系统启动...")
    
    # 1. 定义核心路径
    source_image = os.path.join(BASE_DIR, "assets", "source", "7.png")
    models_dir = os.path.join(BASE_DIR, "assets", "models")
    masks_dir = os.path.join(BASE_DIR, "assets", "masks")
    
    # 【新增】SAM 权重路径与隔离的 Python 路径
    sam_checkpoint = os.path.join(BASE_DIR, "utils", "segment-anything", "sam_vit_h_4b8939.pth")
    # 请确保此路径与你在 sam3d_client.py 中使用的 Python 路径一致！
    sam_python_exe = "/idas/users/lihaoze/.conda/envs/sam/bin/python"
    sam3d_python_exe = "/idas/users/lihaoze/.conda/envs/sam3d-objects/bin/python"
    get_mask_script = os.path.join(BASE_DIR, "utils", "get_mask.py")

    # 2. 清理历史残留资产
    print("\n🧹 步骤 0: 正在清理历史数据...")
    clean_directory(models_dir)
    clean_directory(masks_dir) # 必须同步清空上一次生成的旧 masks！
    print("  ✅ 历史数据已清空。")

    # 3. 图像分割阶段 (调用 SAM)
    print(f"\n🔪 步骤 1: 呼叫底层 SAM 引擎进行图像抠图...")
    sam_cmd = [
        sam_python_exe,
        get_mask_script,
        "--image", source_image,
        "--output", masks_dir,
        "--top_k", "15",
        "--checkpoint", sam_checkpoint
    ]
    try:
        subprocess.run(sam_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ SAM 图像分割失败，流程终止！")
        return
    # 4. 资产生成阶段
    print("\n🏭 步骤 2: 启动多模态视觉分类与 3D 资产生成流水线...")
    agent = VisionProcesserAgent(
        input_dir="assets/masks",
        output_dir="assets/models",
        original_image_path=source_image, 
        sam3d_python_exe=sam3d_python_exe  # <--- 在这里把总指挥部的兵权交下去！
    )
    agent.run_pipeline()
    
    # 5. Agent 智能体搭建阶段
    print("\n🤖 步骤 3: 唤醒双脑智能体系统，开始场景重建...")
    await run_heterogeneous_agents(source_image)
    
    print("\n🏁 [CityBuilder] 任务全部结束！请打开 assets/scenes/output.blend 查看最终成果。")

if __name__ == "__main__":
    asyncio.run(main())