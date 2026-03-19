import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))  # 自动添加项目根目录到Python路径

from mcp.server.fastmcp import FastMCP
import subprocess
import os
import json

from config import Config
"""
blender_mcp_server
工具列表:


"""


#环境配置
mcp = FastMCP("Builder_MCP_Server")

#脚本路径
server_dir = os.path.dirname(os.path.abspath(__file__)) #当前mcp服务器文件夹位置
root_dir = os.path.dirname(server_dir)  #项目根目录位置
blender_scripts_dir = os.path.join(root_dir,"blender_scripts")
blender_path = Config.blender_path

#工具定义
@mcp.tool()
def initialize_blender_scene() -> str:
    """
    工具名：场景初始化
    描述：能够初始化一个干净的Blender场景，在执行其他3D操作前，必须先调用此工具，除非出现不得不重置场景的情况，否则不要轻易调用此工具
    参数：无
    """
    script_path = os.path.join(blender_scripts_dir,"init_scene.py")
    print(f"[MCP Server]:接收到指令，准备执行 {script_path}")

    try:
        # 使用subprocess来执行blender脚本
        result = subprocess.run(
            [blender_path,"-b","-P",script_path],
            capture_output = True,
            text  =True,
            check=True
        )
        return "[MCP Server]: 场景成功初始化"
    except subprocess.CalledProcessError as e:
        return f"[Error]: Blender 脚本执行失败,{e.stderr}"
    except Exception as e:
        return f"[Error]: 系统调用异常，检查环境变量,{str(e)}"

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
    # ... 原有的路径拼接逻辑保持不变 ...
    # 我们需要写一个新的 blender_script 叫做 import_asset.py，并把 asset_name 传给它
    script_path = os.path.join(blender_scripts_dir, "create_object.py") # 咱们可以直接升级原有的脚本
    scene_path = os.path.join(root_dir, "assets", "scenes", "output.blend")
    
    # 构造命令行参数
    blender_args = [blender_path, 
    "-b", scene_path, 
    "-P", script_path, 
    "--", obj_type, name, 
    str(location[0]), 
    str(location[1]), 
    str(location[2])
    ]
    
    # 【核心修改】：如果是资产类型，把 asset_name 塞进去
    if obj_type == "ASSET":
        if not asset_name: return "[Error]: 创建ASSET类型必须提供 asset_name 参数"
        # 资产的绝对路径是固定的：root_dir/assets/models/asset_name
        asset_full_path = os.path.join(root_dir, "assets", "models", asset_name)
        if not os.path.exists(asset_full_path): return f"[Error]: 找不到资产文件: {asset_full_path}"
        blender_args.append(asset_full_path) # 把这个路径传给脚本的 argv[6]

    # ... 原有的 subprocess.run 逻辑保持不变 ...
    try:
        # 2. 核心！构建 subprocess 命令。
        # 逻辑是：启动 Blender -> 在后台 (-b) 打开现有工程文件 -> 执行脚本 (-P) -> 传入自定义参数 (--)
        result = subprocess.run(
            blender_args,
            capture_output=True,
            text=True,
            check=True
        )
        return f"[MCP Server]: 成功创建物体 {name}，已保存至场景。"
        
    except subprocess.CalledProcessError as e:
        # 如果你写的 create_object.py 里面触发了 sys.exit(1)，就会被这里捕获
        return f"[Error]: 创建物体执行失败。\n错误信息: {e.stderr}"
    except Exception as e:
        return f"[Error]: 系统调用异常: {str(e)}"

@mcp.tool()
def move_object(name: str, location: list[float]) -> str:
    """
    工具名：移动物体
    描述：将场景中指定名字的物体移动到新的给定的绝对坐标位置。
    参数：
    - name: 待移动的物体名称
    - location: 目标绝对坐标 [X, Y, Z] 
    """
    script_path = os.path.join(blender_scripts_dir, "transform_object.py")
    scene_path = os.path.join(root_dir, "assets", "scenes", "output.blend")
    
    print(f"[MCP Server]: 准备将物体 {name} 移动至 {location}")
    
    try:
        result = subprocess.run(
            [
                blender_path,
                "-b", scene_path,
                "-P", script_path,
                "--",
                "MOVE",  # 对应 option_type
                name,
                str(location[0]),
                str(location[1]),
                str(location[2])
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return f"[MCP Server]: 成功移动 {name} 到 {location}。\nBlender输出: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        # 同时捕获 stdout 和 stderr，防止有漏掉的错误信息
        return f"[Error]: 移动失败。\n报错信息: {e.stderr}\n标准输出: {e.stdout}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"

@mcp.tool()
def rotate_object(name: str, rotation: list[float]) -> str:
    """
    工具名：旋转物体
    描述：调整场景中指定名字物体的旋转角度（欧拉角）。如果大模型计算出的是角度(Degrees)，请直接传入，底层脚本会处理。
    参数：
    - name: 待旋转的物体名称
    - rotation: 目标旋转角度 [rX, rY, rZ]
    """
    script_path = os.path.join(blender_scripts_dir, "transform_object.py")
    scene_path = os.path.join(root_dir, "assets", "scenes", "output.blend")
    
    print(f"[MCP Server]: 准备将物体 {name} 旋转至 {rotation}")
    
    try:
        result = subprocess.run(
            [
                blender_path,
                "-b", scene_path,
                "-P", script_path,
                "--",
                "ROTATION",  # 对应 option_type
                name,
                str(rotation[0]),
                str(rotation[1]),
                str(rotation[2])
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return f"[MCP Server]: 成功旋转 {name} 至 {rotation}。\nBlender输出: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        # 同时捕获 stdout 和 stderr，防止有漏掉的错误信息
        return f"[Error]: 旋转失败。\n报错信息: {e.stderr}\n标准输出: {e.stdout}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"

@mcp.tool()
def scale_object(name: str, scale: list[float]) -> str:
    """
    工具名：缩放物体
    描述：调整场景中指定名字物体的三维缩放比例。(1.0为原始大小)
    参数：
    - name: 待缩放的物体名称
    - scale: 目标尺寸缩放比例 [sX, sY, sZ]
    """
    script_path = os.path.join(blender_scripts_dir, "transform_object.py")
    scene_path = os.path.join(root_dir, "assets", "scenes", "output.blend")
    
    print(f"[MCP Server]: 准备将物体 {name} 缩放至 {scale}")
    
    try:
        result = subprocess.run(
            [
                blender_path,
                "-b", scene_path,
                "-P", script_path,
                "--",
                "SCALE",  # 对应 option_type
                name,
                str(scale[0]),
                str(scale[1]),
                str(scale[2])
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return f"[MCP Server]: 成功缩放 {name} 至 {scale}。\nBlender输出: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        # 同时捕获 stdout 和 stderr，防止有漏掉的错误信息
        return f"[Error]: 缩放失败。\n报错信息: {e.stderr}\n标准输出: {e.stdout}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"


if __name__ == "__main__":
    mcp.run()