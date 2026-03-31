import sys
import os
import subprocess
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ==========================================
# 📍 1. 动态定位项目根目录
# ==========================================
# 当前在 tools/mcp_servers/ 目录下，往上两级是根目录
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SERVER_DIR))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import Config

# ==========================================
# ⚙️ 2. 环境与路径配置
# ==========================================
mcp = FastMCP("Builder_MCP_Server")

blender_scripts_dir = os.path.join(ROOT_DIR, "blender_scripts")
blender_path = Config.blender_path

# 兼容 Config 中的资产路径
assets_dir = Config.assets_path if getattr(Config, 'assets_path', None) else "assets"
if not os.path.isabs(assets_dir):
    assets_dir = os.path.join(ROOT_DIR, assets_dir)

models_path = os.path.join(assets_dir, "models")
scene_path = os.path.join(assets_dir, "scenes", "output.blend")

# ==========================================
# 🛠️ 3. 工具定义
# ==========================================
@mcp.tool()
def initialize_blender_scene() -> str:
    """
    工具名：场景初始化
    描述：能够初始化一个干净的Blender场景，在执行其他3D操作前，必须先调用此工具，除非出现不得不重置场景的情况，否则不要轻易调用此工具
    """
    script_path = os.path.join(blender_scripts_dir, "init_scene.py")
    print(f"[MCP Server]: 接收到指令，准备执行 {script_path}")

    try:
        result = subprocess.run(
            [blender_path, "-b", "-P", script_path],
            capture_output=True,
            text=True,
            check=True
        )
        return "[MCP Server]: 场景成功初始化"
    except subprocess.CalledProcessError as e:
        return f"[Error]: Blender 脚本执行失败, {e.stderr}"
    except Exception as e:
        return f"[Error]: 系统调用异常，检查环境变量, {str(e)}"

@mcp.tool()
def create_blender_object(obj_type: str, name: str, location: list[float] = [0.0, 0.0, 0.0], asset_name: str = "") -> str:
    """
    工具名：创建 3D 物体
    描述：在场景中创建一个基础几何体，或者从 assets/models/ 目录中导入一个 GLB 资产。
    参数：
    - obj_type: 物体类型。可选: "CUBE", "SPHERE", "MONKEY" (几何体) 或 "ASSET" (导入外部GLB)
    - name: 物体的唯一命名
    - location: 坐标 [X, Y, Z]
    - asset_name: 当 obj_type 为 "ASSET" 时，必须提供资产文件名 (例如 "apple.glb")，不带路径。
    """
    script_path = os.path.join(blender_scripts_dir, "create_object.py")
    
    blender_args = [
        blender_path, "-b", scene_path, "-P", script_path, "--", 
        obj_type, name, str(location[0]), str(location[1]), str(location[2])
    ]
    
    if obj_type == "ASSET":
        if not asset_name: 
            return "[Error]: 创建ASSET类型必须提供 asset_name 参数"
        asset_full_path = os.path.join(models_path, asset_name)
        if not os.path.exists(asset_full_path): 
            return f"[Error]: 找不到资产文件: {asset_full_path}"
        blender_args.append(asset_full_path)

    try:
        result = subprocess.run(blender_args, capture_output=True, text=True, check=True)
        return f"[MCP Server]: 成功创建物体 {name}，已保存至场景。\n--- Blender 底层日志 ---\n{result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"[Error]: 创建物体执行失败。\n错误信息: {e.stderr}"
    except Exception as e:
        return f"[Error]: 系统调用异常: {str(e)}"

@mcp.tool()
def move_object(name: str, x: float = None, y: float = None, z: float = None) -> str:
    """
    工具名：移动物体
    描述：将场景中指定名字的物体移动到新的位置。
    【重要用法】：支持增量/局部更新！如果你只想修复高度穿模，只传入 z 即可，【千万不要】传入 x 和 y，系统会自动保留其原有的平面坐标！
    """
    script_path = os.path.join(blender_scripts_dir, "transform_object.py")
    
    # 将 None 转换为字符串 "None"，方便通过命令行传给 Blender
    str_x = str(x) if x is not None else "None"
    str_y = str(y) if y is not None else "None"
    str_z = str(z) if z is not None else "None"
    
    print(f"[MCP Server]: 准备更新物体 {name} 的坐标 -> X:{str_x}, Y:{str_y}, Z:{str_z}")
    
    try:
        result = subprocess.run(
            [
                blender_path, "-b", scene_path, "-P", script_path, 
                "--", "MOVE", name, str_x, str_y, str_z
            ],
            capture_output=True, text=True, check=True
        )
        return f"[MCP Server]: 成功更新 {name} 坐标 (X:{str_x}, Y:{str_y}, Z:{str_z})。\nBlender输出: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"[Error]: 移动失败。\n报错信息: {e.stderr}\n标准输出: {e.stdout}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"
        
@mcp.tool()
def rotate_object(name: str, rotation: list[float]) -> str:
    """
    工具名：旋转物体
    描述：调整场景中指定名字物体的旋转角度（欧拉角）。
    """
    script_path = os.path.join(blender_scripts_dir, "transform_object.py")
    try:
        result = subprocess.run(
            [blender_path, "-b", scene_path, "-P", script_path, "--", "ROTATION", name, str(rotation[0]), str(rotation[1]), str(rotation[2])],
            capture_output=True, text=True, check=True
        )
        return f"[MCP Server]: 成功旋转 {name} 至 {rotation}。\nBlender输出: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"[Error]: 旋转失败。\n报错信息: {e.stderr}\n标准输出: {e.stdout}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"

@mcp.tool()
def scale_object(name: str, scale: list[float]) -> str:
    """
    工具名：缩放物体
    描述：调整场景中指定名字物体的三维缩放比例。(1.0为原始大小)
    """
    script_path = os.path.join(blender_scripts_dir, "transform_object.py")
    try:
        result = subprocess.run(
            [blender_path, "-b", scene_path, "-P", script_path, "--", "SCALE", name, str(scale[0]), str(scale[1]), str(scale[2])],
            capture_output=True, text=True, check=True
        )
        return f"[MCP Server]: 成功缩放 {name} 至 {scale}。\nBlender输出: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"[Error]: 缩放失败。\n报错信息: {e.stderr}\n标准输出: {e.stdout}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"

@mcp.tool()
def get_available_assets() -> str:
    """
    工具名：获取可用的3D模型资产列表
    描述：返回目录下由视觉大模型清洗、SAM3D生成的3D模型资产文件（.glb）以及对应的空间坐标（JSON）
    """
    assets_list = []
    if os.path.exists(models_path):
        for f in os.listdir(models_path):
            if f.endswith("_info.json"):
                json_path = os.path.join(models_path, f)
                with open(json_path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                    assets_list.append(data)
    
    return json.dumps(assets_list, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run()