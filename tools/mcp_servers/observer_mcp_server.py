import sys
import os
import subprocess
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ==========================================
# 📍 1. 动态定位项目根目录
# ==========================================
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SERVER_DIR))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import Config

# ==========================================
# ⚙️ 2. 环境与路径配置
# ==========================================
mcp = FastMCP("Observer_MCP_Server")

blender_scripts_dir = os.path.join(ROOT_DIR, "blender_scripts")
blender_path = Config.blender_path

# 兼容 Config 中的资产路径
assets_dir = Config.assets_path if getattr(Config, 'assets_path', None) else "assets"
if not os.path.isabs(assets_dir):
    assets_dir = os.path.join(ROOT_DIR, assets_dir)

scene_path = os.path.join(assets_dir, "scenes", "output.blend")
renders_dir = os.path.join(assets_dir, "renders")

# ==========================================
# 🛠️ 3. 工具定义
# ==========================================
@mcp.tool()
def get_scene_status() -> str:
    """
    工具名：获取场景状态（雷达眼）
    描述：扫描当前3D场景，获取所有网格物体（MESH）的详细数据，其中包括物体名称、坐标、旋度、缩放以及实际尺寸。
    """
    script_path = os.path.join(blender_scripts_dir, "get_scene_data.py")
    print(f"[MCP Server]: 正在扫描场景数据...")
    try:
        result = subprocess.run(
            [blender_path, "-b", scene_path, "-P", script_path],
            capture_output=True, text=True, check=True
        )
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
    - view_direction: 观察方向向量 [X, Y, Z]。例如 [1, 1, 1] 代表从右上方俯视。
    返回值：渲染生成的图片在本地的绝对路径。
    """
    script_path = os.path.join(blender_scripts_dir, "take_photo.py")
    os.makedirs(renders_dir, exist_ok=True)
    save_path = os.path.join(renders_dir, "current_view.png")
    
    print(f"[MCP Server]: 正在从方向 {view_direction} 拍摄全景照片...")
    try:
        result = subprocess.run(
            [
                blender_path, "-b", scene_path, "-P", script_path, "--",
                str(view_direction[0]), str(view_direction[1]), str(view_direction[2]),
                save_path
            ],
            capture_output=True, text=True, check=True
        )
        output_lines = result.stdout.strip().split('\n')
        success_msg = next((line for line in output_lines if "SUCCESS" in line), "拍照成功")
        
        return f"[MCP Server]: {success_msg}。图片已保存至: {save_path}"
    except subprocess.CalledProcessError as e:
        return f"[Error]: 拍照失败。\n报错信息: {e.stderr}"
    except Exception as e:
        return f"[Error]: 系统级异常: {str(e)}"

if __name__ == "__main__":
    mcp.run()