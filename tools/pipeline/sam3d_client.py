import subprocess
import os
import sys

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(PIPELINE_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config

class Sam3DClient:
    def __init__(self):
        self.config_path = Config.sam3d_config_path
        self.sam3d_python_exe = Config.sam3d_python_exe
        self.worker_script = os.path.join(PROJECT_ROOT, "tools", "workers", "sam3d_worker.py")

    def generate_3d_asset(self, original_image_path, mask_npy_path, output_glb_path, gpu_id=0):
        """
        新增 gpu_id 参数，并在底层调用时强行指定 CUDA 设备
        """
        asset_name = os.path.basename(output_glb_path)
        print(f"  [Sam3D Client | 显卡 {gpu_id}] 正在生成 3D 资产: {asset_name}...")
        
        cmd = [
            self.sam3d_python_exe, 
            self.worker_script,
            "--config", self.config_path,
            "--image", original_image_path,
            "--mask", mask_npy_path,
            "--output", output_glb_path
        ]
        
        # 🌟 核心魔法：拷贝当前环境变量，并强制指定当前子进程只能看见目标 GPU
        custom_env = os.environ.copy()
        custom_env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        # 🚀 新增：把镜像源写死到环境变量，彻底断绝超时报错
        custom_env["HF_ENDPOINT"] = "https://hf-mirror.com"
        
        try:
            # 开启 capture_output=True 可以防止多张卡的进度条在终端里互相穿插打架
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=custom_env)
            print(f"  ✅ [显卡 {gpu_id}] 渲染成功: {asset_name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ [显卡 {gpu_id}] 生成失败 ({asset_name})！\n--- 底层报错信息 ---\n{e.stderr}")
            raise RuntimeError(f"GPU {gpu_id} 处理 {asset_name} 时崩溃。")