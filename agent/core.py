import asyncio
import os
import sys
import json
from pathlib import Path
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# 自动添加项目根目录到Python路径，导入配置
sys.path.append(str(Path(__file__).parent.parent))
from config import Config

# 初始化 Qwen 大模型客户端
llm_client = AsyncOpenAI(
    api_key=Config.llm_api_key,
    base_url=Config.llm_base_url
)
MODEL_ID = Config.llm_model_id

# 辅助函数：将 MCP 工具转换为 OpenAI 格式
def format_mcp_tools_for_llm(mcp_tools):
    formatted_tools = []
    for tool in mcp_tools:
        formatted_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema 
            }
        })
    return formatted_tools

async def run_builder_agent():
    print("🧠 正在通电... 唤醒 Builder 大脑...")
    
    # 定位 Server 脚本
    server_script = os.path.join(Path(__file__).parent.parent, "mcp_server", "blender_mcp_server.py")
    server_params = StdioServerParameters(command=Config.server_command, args=[server_script])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ 与 Blender 的 MCP 神经连接已打通！")

            # 获取并转换工具
            mcp_tools = (await session.list_tools()).tools
            llm_tools = format_mcp_tools_for_llm(mcp_tools)
            print(f"🛠️ 大脑已加载 {len(mcp_tools)} 个可用工具: {[t.name for t in mcp_tools]}\n")

            # ========================================================
            # 注入灵魂：System Prompt 与用户需求
            # ========================================================
            messages = [
                {
                    "role": "system", 
                    "content": (
                        "你是出色的 3D 场景搭建师。你拥有控制 Blender 的能力。"
                        "规则："
                        "1. 在开始任何搭建前，必须先调用 initialize_blender_scene 清理场景。"
                        "2. 你的单位是米(m)。"
                        "3. 遇到复杂物体，你需要思考它的结构。例如桌子由1个桌面和4条腿组成，你需要多次调用创建和形变工具。"
                        "4. 一旦你认为场景搭建完成，请向用户汇报你搭建的思路。"
                    )
                }
            ]
            
            # 咱们给 Agent 出的考卷
            user_task = "请你帮我用基础图像搭建一个长城，长城不需要特别长"
            print(f"👤 用户需求: {user_task}\n")
            messages.append({"role": "user", "content": user_task})

            # ========================================================
            # Agent 主循环 (ReAct 模式: 思考 -> 调用工具 -> 获取反馈 -> 继续思考)
            # ========================================================
            max_turns = 30 # 设定最多允许它思考和动作 10 个回合
            
            for turn in range(max_turns):
                print(f"🔄 [第 {turn + 1} 回合] Builder 正在思考...")
                
                # 发请求给大模型
                response = await llm_client.chat.completions.create(
                    model=MODEL_ID,
                    messages=messages,
                    tools=llm_tools,
                    tool_choice="auto"
                )
                
                assistant_msg = response.choices[0].message
                messages.append(assistant_msg) # 把模型的回复记入记忆
                
                # 情况 A：模型决定调用工具
                if assistant_msg.tool_calls:
                    for tool_call in assistant_msg.tool_calls:
                        func_name = tool_call.function.name
                        # 解析大模型生成的参数
                        func_args = json.loads(tool_call.function.arguments)
                        
                        print(f"⚡ [Builder 执行]: 调用 {func_name}")
                        print(f"   [参数]: {func_args}")
                        
                        # 真实调用 MCP Server
                        try:
                            mcp_result = await session.call_tool(func_name, arguments=func_args)
                            result_text = mcp_result.content[0].text
                        except Exception as e:
                            result_text = f"工具执行异常: {str(e)}"
                            
                        print(f"🖥️ [Blender 反馈]: {result_text}\n")
                        
                        # 把工具执行的结果“喂”回给大模型，让它知道刚刚那一铲子下去挖出了啥
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": result_text
                        })
                        
                # 情况 B：模型没有调用工具，而是直接说话（通常意味着任务完成了，或者它卡住了）
                else:
                    print(f"🎉 [Builder 汇报]: {assistant_msg.content}\n")
                    print("✅ 任务执行完毕，退出循环。")
                    break
            else:
                print("⚠️ 达到了最大执行回合数，被强制叫停。")

if __name__ == "__main__":
    asyncio.run(run_builder_agent())