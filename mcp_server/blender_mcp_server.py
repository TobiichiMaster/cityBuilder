import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))  # 自动添加项目根目录到Python路径

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
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
load_dotenv()

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
def create_blender_object():
    """
    在Blender内创建一个新物体

    """
    pass

if __name__ == "__main__":
    mcp.run()

