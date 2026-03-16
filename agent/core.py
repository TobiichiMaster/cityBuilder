import asyncio
import os
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def run_agent_brain():
    print("🧠 正在唤醒 Agent 大脑...")
    
    # 1. 定位我们的 Server 脚本
    # 假设当前文件在 blender_agent_project/agent/core.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    server_script = os.path.join(root_dir, "mcp_server", "blender_mcp_server.py")
    
    # 2. 配置 MCP 客户端连接参数
    # 这里我们告诉 Agent，通过 Python 去执行那个 server.py 文件，并通过标准输入输出流（Stdio）和它说话
    server_params = StdioServerParameters(
        command="python",  # 如果你用了虚拟环境，这里可能需要改成绝对路径，比如 "/path/to/venv/bin/python"
        args=[server_script],
    )

    print(f"🔗 正在建立与 Blender 的 MCP 神经连接...")
    
    # 3. 建立连接并开启会话
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化 MCP 协议
            await session.initialize()
            print("✅ 神经连接握手成功！")

            # === 观察阶段 (Observation) ===
            # 大脑醒来第一件事：看看自己手里有什么牌
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            print(f"🛠️ 大脑扫描到可用工具: {tool_names}")
            
            # 看看 Server 传过来的工具说明 (这其实就是给 LLM 看的 Prompt)
            for tool in tools_response.tools:
                if tool.name == "initialize_blender_scene":
                    print(f"📖 工具说明书: {tool.description}")

            # === 决策与执行阶段 (Action) ===
            user_prompt = "请帮我初始化一个干净的 3D 场景，为接下来的 SAM3d 资产导入做准备。"
            print(f"\n👤 收到用户需求: {user_prompt}")
            print("🤔 大脑思考中... 决定调用工具 [initialize_blender_scene]")
            
            # 模拟 LLM 决定调用工具（实际项目中，这里是解析 LLM 的 JSON 输出）
            print("⚡ 正在发送执行指令到 Blender...")
            # 因为我们的工具目前不需要传参数，所以 arguments 是一个空字典
            result = await session.call_tool("initialize_blender_scene", arguments={})
            
            # === 接收反馈阶段 (Feedback) ===
            # 这部分数据后续会扔回给 LLM，让它判断是否成功，这就是 Reflection 的基础
            print(f"\n👀 收到外部世界反馈:\n{result.content[0].text}")
            print("🎉 本次 Agent 思考循环结束！")

if __name__ == "__main__":
    # 运行异步循环
    asyncio.run(run_agent_brain())