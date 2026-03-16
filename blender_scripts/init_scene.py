import bpy
import os

# 1. 鲁棒的路径推导：基于当前脚本所在位置计算绝对路径
# 当前脚本在 blender_agent_project/blender_scripts/init_scene.py
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir) # 回退一级，拿到项目根目录

# 2. 构建目标路径 (注意文件夹名称和标准后缀)
scenes_dir = os.path.join(root_dir, "assets", "scenes")
save_path = os.path.join(scenes_dir, "output.blend")

print(f"项目根目录: {root_dir}")
print(f"目标保存路径: {save_path}")

# 3. 准备文件夹 (修复了 makedirs 和 True 的拼写)
os.makedirs(scenes_dir, exist_ok=True)

# 4. 清空默认场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 5. 保存干净的场景 (传入具体的文件路径 save_path)
bpy.ops.wm.save_as_mainfile(filepath=save_path)
print(f"SUCCESS: 初始空白场景已保存至 {save_path}")