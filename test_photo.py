import os
import subprocess
import sys
from pathlib import Path

# 确保能导入项目的 config
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

try:
    from config import Config
    blender_exe = Config.blender_path
except ImportError:
    # 如果没法导入配置，请在这里手动填入你的 blender 路径
    blender_exe = "blender" 

def test_camera():
    print("📸 开始独立测试 Observer 多视角拍摄功能...")

    # === 路径配置 ===
    # 我们直接读取之前跑出来的最终场景
    scene_path = os.path.join(BASE_DIR, "assets", "scenes", "output.blend")
    script_path = os.path.join(BASE_DIR, "blender_scripts", "take_photo.py")
    
    # 确保输出目录存在
    render_dir = os.path.join(BASE_DIR, "assets", "renders")
    os.makedirs(render_dir, exist_ok=True)
    
    # === 【测试参数】===
    # 你可以把这里改成 "TOP", "FRONT", "SIDE", "ISO", "LEVEL", "UNDER" 来测试不同视角
    view_type = "UNDER" 
    save_path = os.path.join(render_dir, f"test_{view_type.lower()}.png")

    # 安全检查
    missing_files = []
    for f in [scene_path, script_path]:
        if not os.path.exists(f):
            missing_files.append(f)
            
    if missing_files:
        print("❌ 测试终止，缺少以下关键文件：")
        for f in missing_files:
            print(f"  - {f}")
        print("\n💡 提示：如果缺少 output.blend，说明你之前没有跑完过 Builder 流程。你可以把 scene_path 换成任意一个已有的 .blend 场景文件进行测试。")
        return

    # 构造跨进程调用命令 (后台无 UI 模式运行 Blender)
    cmd = [
        blender_exe,
        "-b", scene_path,
        "-P", script_path,
        "--",
        view_type,
        save_path
    ]

    print(f"\n🚀 即将执行的命令:\n{' '.join(cmd)}")
    print(f"\n⏳ 正在呼叫 Blender 进行 [{view_type}] 视角渲染，请稍候...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"\n🎉🎉🎉 测试成功！")
        print(f"👉 照片已保存至: {save_path}")
        
        # 提取脚本里的 print 日志（过滤掉 Blender 繁杂的启动信息）
        stdout_lines = [line for line in result.stdout.split('\n') if "SUCCESS" in line or "Error" in line]
        if stdout_lines:
            print("\n--- [Blender 脚本返回日志] ---")
            print("\n".join(stdout_lines))
            
    except subprocess.CalledProcessError as e:
        print("\n💥 测试失败！Blender 渲染抛出了异常！")
        print("--- [致命报错信息] ---")
        print(e.stderr.strip() if e.stderr else e.stdout.strip())

if __name__ == "__main__":
    test_camera()