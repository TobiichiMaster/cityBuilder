import os
import subprocess

def test_sam3d():
    print("🧪 开始独立测试 SAM3D 3D资产生成...")

    # 1. 获取当前根目录的绝对路径
    base_dir = os.path.abspath(os.path.dirname(__file__))

    # 2. 定义执行环境与脚本路径
    # 这里使用的是你之前确定的 sam3d-objects 专属虚拟环境
    sam3d_python_exe = "/idas/users/lihaoze/.conda/envs/sam3d-objects/bin/python"
    worker_script = os.path.join(base_dir, "utils", "sam3d_worker.py")

    # 3. 定义输入与输出参数
    # 这里我们随机取上一轮日志中生成的一个现有资产作为测试用例
    config_path = os.path.join(base_dir, "utils", "sam3d", "checkpoints", "hf", "pipeline.yaml")
    test_image = os.path.join(base_dir, "assets", "source", "7.png") 
    test_mask = os.path.join(base_dir, "assets", "models", "building_001.npy") # 假设这个文件现在还在 models 目录下
    output_glb = os.path.join(base_dir, "assets", "models", "test_output_building.glb")

    # === 安全检查：确保所有前置文件都存在 ===
    missing_files = []
    for f in [sam3d_python_exe, worker_script, config_path, test_image, test_mask]:
        if not os.path.exists(f):
            missing_files.append(f)
            
    if missing_files:
        print("❌ 测试终止，缺少以下关键文件：")
        for f in missing_files:
            print(f"  - {f}")
        print("\n请检查：\n1. 你的 assets/models/ 下是否还有 building_001.npy。\n2. config 文件路径是否正确。")
        return

    # 4. 构造跨进程调用命令
    cmd = [
        sam3d_python_exe,
        worker_script,
        "--config", config_path,
        "--image", test_image,
        "--mask", test_mask,
        "--output", output_glb
    ]

    print("\n🚀 即将发送给虚拟环境的命令:")
    print(" ".join(cmd))
    print("\n⏳ 正在唤醒模型进行推理，可能需要几十秒，请耐心等待...")

    # 5. 执行命令并捕获日志
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("\n🎉🎉🎉 测试成功！3D 资产已完美生成！")
        print(f"👉 请检查输出文件: {output_glb}")
        if result.stdout.strip():
            print("\n--- [SAM3D 正常运行日志] ---")
            print(result.stdout.strip())
            
    except subprocess.CalledProcessError as e:
        print("\n💥 测试失败！底层的 sam3d_worker.py 抛出了异常！")
        print("--- [致命报错信息] ---")
        print(e.stderr.strip())

if __name__ == "__main__":
    test_sam3d()