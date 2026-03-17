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
mcp = FastMCP("Blender_tool_server")

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
def create_blender_object(obj_type: str, name: str, location: list[float] = [0.0, 0.0, 0.0]) -> str:
    """
    工具名：创建 3D 物体
    描述：在当前场景的指定位置创建一个基础 3D 物体。
    参数：
    - obj_type: 物体类型，必须是 "CUBE" (立方体), "SPHERE" (球体), 或 "MONKEY" (猴头)
    - name: 物体的唯一命名
    - location: 包含三个浮点数的列表，代表 [X, Y, Z] 坐标，默认为 [0.0, 0.0, 0.0]
    """
    # 1. 定位需要执行的脚本和场景文件
    script_path = os.path.join(blender_scripts_dir, "create_object.py")
    scene_path = os.path.join(root_dir, "assets", "scenes", "output.blend")
    
    print(f"[MCP Server]: 接收到指令，准备在 {location} 创建 {obj_type}，命名为 {name}")

    try:
        # 2. 核心！构建 subprocess 命令。
        # 逻辑是：启动 Blender -> 在后台 (-b) 打开现有工程文件 -> 执行脚本 (-P) -> 传入自定义参数 (--)
        result = subprocess.run(
            [
                blender_path, 
                "-b", scene_path,      # 极其关键：必须先打开我们 init 的场景，否则会在默认场景里乱建
                "-P", script_path,     # 挂载你的 bpy 脚本
                "--",                  # 分隔符：告诉 Blender 后面的参数是给 Python 脚本的，不是给 Blender 系统的
                obj_type,              # 对应脚本里的 args[0]
                name,                  # 对应脚本里的 args[1]
                str(location[0]),      # 对应脚本里的 args[2] (注意 subprocess 只能传字符串，所以要强转)
                str(location[1]),      # 对应脚本里的 args[3]
                str(location[2])       # 对应脚本里的 args[4]
            ],
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

@mcp.tool()
def get_scene_status()->str:
    """
    工具名：获取场景状态（雷达眼）
    描述：扫描当前3D场景，获取所有网格物体（MESH）的详细数据，其中包括物体名称、坐标（location）、旋度（rotation）、缩放（scale）以及实际长宽高尺寸（dimensions）。
    返回值：一个包含场景物体信息的JSON字符串，你可以利用 dimensions 和 location 来计算物体之间是否对齐、是否穿模或悬空。
    参数：无
    """
    script_path = os.path.join(blender_scripts_dir, "get_scene_data.py")
    scene_path = os.path.join(root_dir, "assets", "scenes", "output.blend")

    print(f"[MCP Server]: 正在扫描场景数据")
    try:
        result = subprocess.run(
            [blender_path, "-b", scene_path, "-P", script_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        # 提取被 ===SCENE_DATA_START=== 和 ===SCENE_DATA_END=== 包裹的 JSON 纯净数据
        stdout = result.stdout
        if "===SCENE_DATA_START===" in stdout and "===SCENE_DATA_END===" in stdout:
            json_str = stdout.split("===SCENE_DATA_START===")[1].split("===SCENE_DATA_END===")[0].strip()
            return json_str
        else:
            return f"[Error]: 无法解析场景数据。Blender 输出为: {stdout}"
            
    except subprocess.CalledProcessError as e:
        return f"[Error]: 扫描场景失败。\n报错信息: {e.stderr}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"

@mcp.tool()
def render_camera_view(view_direction: list[float] = [1.0, 1.0, 1.0]) -> str:
    """
    工具名：渲染场景照片 (智能光学眼)
    描述：自动计算整个 3D 场景的包围盒，将摄像机放置在完美的距离，并从你指定的方向拍摄一张全景照片。
    参数：
    - view_direction: 观察方向向量 [X, Y, Z]。例如 [1, 1, 1] 代表从右上方俯视；[0, 1, 0] 代表正上方俯视（顶视图）；[1, 0, 0] 代表正侧面视角。
    返回值：渲染生成的图片在本地的绝对路径。
    """
    script_path = os.path.join(blender_scripts_dir, "take_photo.py")
    scene_path = os.path.join(root_dir, "assets", "scenes", "output.blend")
    
    img_dir = os.path.join(root_dir, "assets", "renders")
    os.makedirs(img_dir, exist_ok=True)
    save_path = os.path.join(img_dir, "current_view.png")
    
    print(f"[MCP Server]: 正在从方向 {view_direction} 拍摄全景照片...")
    
    try:
        result = subprocess.run(
            [
                blender_path, "-b", scene_path, "-P", script_path, "--",
                str(view_direction[0]), str(view_direction[1]), str(view_direction[2]),
                save_path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        # 从 stdout 中提取有用的提示返回给 Agent
        output_lines = result.stdout.strip().split('\n')
        success_msg = next((line for line in output_lines if "SUCCESS" in line), "拍照成功")
        
        return f"[MCP Server]: {success_msg}。图片已保存至: {save_path}"
    except subprocess.CalledProcessError as e:
        return f"[Error]: 拍照失败。\n报错信息: {e.stderr}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"


if __name__ == "__main__":
    mcp.run()

