import subprocess
import os

class Sam3DClient:
    def __init__(self, config_path, python_exe):
        self.config_path = config_path
        self.sam3d_python_exe = python_exe
        
        # 自动定位项目根目录，并指向我们即将新建的 worker 脚本
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.worker_script = os.path.join(project_root, "utils", "sam3d_worker.py")

    def generate_3d_asset(self, original_image_path, mask_npy_path, output_glb_path):
        print(f"  [Sam3D Client] 正在跨环境呼叫 SAM3D 生成: {os.path.basename(output_glb_path)}...")
        
        # 构建跨进程调用的命令清单
        cmd = [
            self.sam3d_python_exe, 
            self.worker_script,
            "--config", self.config_path,
            "--image", original_image_path,
            "--mask", mask_npy_path,
            "--output", output_glb_path
        ]
        
        try:
            # 唤醒另一个虚拟环境干活，并等待它完成
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"  ✅ SAM3D 渲染成功: {os.path.basename(output_glb_path)}")
        except subprocess.CalledProcessError as e:
            print(f"❌ SAM3D 生成失败！\n--- 底层报错信息 ---\n{e.stderr}")