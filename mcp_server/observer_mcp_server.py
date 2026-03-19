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
mcp = FastMCP("Observer_MCP_Server")

#脚本路径
server_dir = os.path.dirname(os.path.abspath(__file__)) #当前mcp服务器文件夹位置
root_dir = os.path.dirname(server_dir)  #项目根目录位置
blender_scripts_dir = os.path.join(root_dir,"blender_scripts")
blender_path = Config.blender_path

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

