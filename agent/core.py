import asyncio
import os
import sys
import json
from pathlib import Path
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from memoryManager import MemoryManager
sys.path.append(str(Path(__file__).parent.parent))
from config import Config

# ==========================================
# 🧠 1. 异构大模型客户端初始化
# ==========================================
# Builder 大脑：可以配置为本地 vLLM (例如 Qwen-VL 部署在本地的 8000 端口)
builder_client = AsyncOpenAI(
    api_key=os.getenv("BUILDER_API_KEY", "EMPTY"), # vLLM 通常不需要复杂的 key
    base_url=os.getenv("BUILDER_BASE_URL", "http://localhost:8000/v1")
)
BUILDER_MODEL_ID = os.getenv("BUILDER_MODEL_ID", "qwen-vl-chat")

# Observer 大脑：可以配置为云端最强多模态模型 (例如 ModelScope 的 qwen-vl-max)
observer_client = AsyncOpenAI(
    api_key=Config.llm_api_key, 
    base_url=Config.llm_base_url
)
OBSERVER_MODEL_ID = Config.llm_model_id





# ==========================================
# 🚀 3. 双核驱动主循环
# ==========================================
async def run_heterogeneous_agents():
    print("🔋 正在启动异构双脑架构...")
    
    # 定义两个独立的 MCP Server 路径
    mcp_dir = os.path.join(Path(__file__).parent.parent, "mcp_server")
    builder_server_script = os.path.join(mcp_dir, "builder_mcp_server.py")
    observer_server_script = os.path.join(mcp_dir, "observer_mcp_server.py")

    # 配置启动参数
    builder_params = StdioServerParameters(command=Config.server_command, args=[builder_server_script])
    observer_params = StdioServerParameters(command=Config.server_command, args=[observer_server_script])

    # 🕸️ 建立双重网络连接 (使用 contextlib.AsyncExitStack 可以更优雅，这里用嵌套方便理解)
    print("🔗 正在建立双 MCP 物理隔离通道...")
    async with stdio_client(builder_params) as (b_read, b_write), \
               stdio_client(observer_params) as (o_read, o_write):
        
        async with ClientSession(b_read, b_write) as b_session, \
                   ClientSession(o_read, o_write) as o_session:
            
            await b_session.initialize()
            await o_session.initialize()
            print("✅ 双路 MCP 握手成功！")

            # 独立获取工具
            builder_tools_raw = (await b_session.list_tools()).tools
            observer_tools_raw = (await o_session.list_tools()).tools
            
            # 将工具格式化为 OpenAI 格式 (需要你自己把之前的 format_mcp_tools_for_llm 函数补进来)
            # builder_tools = format_mcp_tools_for_llm(builder_tools_raw)
            # observer_tools = format_mcp_tools_for_llm(observer_tools_raw)

            # 初始化系统提示词 (根据需要调整，加入关于处理图片的指令)
            builder_messages = [{"role": "system", "content": "你是建造者... (支持识图)"}]
            observer_messages = [{"role": "system", "content": "你是质检员... (支持识图)"}]

            # 用户的单幅图像重建需求
            # 在最终项目中，这里会附带第一张用户输入的参考图 Base64
            user_task = "请根据参考图，在 Blender 里搭建场景..."
            MemoryManager.append_and_prune(builder_messages, {"role": "user", "content": user_task})

            # ==========================================
            # 🔄 异构迭代循环
            # ==========================================
            for turn in range(5):
                print(f"\n========== 🔄 [第 {turn + 1} 轮迭代] ==========")
                
                # ------------------------------------------------
                # 👷 Builder 行动阶段 (调用 b_session)
                # ------------------------------------------------
                print(f"👷 [Builder Brain - {BUILDER_MODEL_ID}] 正在干活...")
                # ... 发起 builder_client 请求 ...
                # ... 解析并执行 b_session.call_tool ...
                # ... 使用 MemoryManager.append_and_prune 记录工具结果 ...

                # ------------------------------------------------
                # 🧐 Observer 视察阶段 (调用 o_session)
                # ------------------------------------------------
                print(f"\n🧐 [Observer Brain - {OBSERVER_MODEL_ID}] 正在拍照视察...")
                # ... Observer 发起请求 ...
                # ... 决定调用 render_camera_view 拍照 ...
                # ... 将本地生成的图片转成 Base64 ...
                # ... 使用 MemoryManager.append_and_prune 将最新的现场照片喂给 Observer ...
                
                # 命运的裁决...

if __name__ == "__main__":
    asyncio.run(run_heterogeneous_agents())