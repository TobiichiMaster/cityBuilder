import asyncio
import os
import sys
import json
import base64
from pathlib import Path
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# 🌟 修改点 1：包名从 agent 变成了 agents
from agents.memoryManager import MemoryManager 

# 自动将项目根目录加入环境变量
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import Config

# ==========================================
# 🧠 1. 异构大模型客户端初始化
# ==========================================
# Builder 大脑 (干活的苦力)
builder_client = AsyncOpenAI(
    api_key=Config.builder_api_key,
    base_url=Config.builder_base_url
)
BUILDER_MODEL_ID = Config.builder_model_id

# Observer 大脑 (冷酷的监工)
observer_client = AsyncOpenAI(
    api_key=Config.observer_api_key, 
    base_url=Config.observer_base_url
)
OBSERVER_MODEL_ID = Config.observer_model_id

# ==========================================
# 🔧 2. 工具与编码辅助函数
# ==========================================
def format_mcp_tools_for_llm(mcp_tools, allowed_tool_names=None):
    """将 MCP 工具转为大模型识别的 OpenAI 格式，并支持白名单过滤"""
    formatted_tools = []
    for tool in mcp_tools:
        if allowed_tool_names is not None and tool.name not in allowed_tool_names:
            continue
        formatted_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema 
            }
        })
    return formatted_tools

def encode_image_to_base64(image_path):
    """将本地图片转换为 Base64 编码"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# ==========================================
# 🚀 3. 双核驱动主循环
# ==========================================
async def run_heterogeneous_agents(image_path: str):
    print("🔋 正在启动异构多模态双脑架构...")
    
    # 🌟 修改点 2：更新 MCP Server 的路径定位，指向新的 tools/mcp_servers 目录
    mcp_dir = os.path.join(Path(__file__).resolve().parent.parent, "tools", "mcp_servers")
    
    b_params = StdioServerParameters(command=Config.server_command, args=[os.path.join(mcp_dir, "builder_mcp_server.py")])
    o_params = StdioServerParameters(command=Config.server_command, args=[os.path.join(mcp_dir, "observer_mcp_server.py")])

    print("🔗 正在建立双 MCP 物理隔离通道...")
    async with stdio_client(b_params) as (b_read, b_write), stdio_client(o_params) as (o_read, o_write):
        async with ClientSession(b_read, b_write) as b_session, ClientSession(o_read, o_write) as o_session:
            
            await b_session.initialize()
            await o_session.initialize()
            print("✅ 双路 MCP 握手成功！\n")

            # 拆分并获取各自的工具
            b_tools_raw = (await b_session.list_tools()).tools
            o_tools_raw = (await o_session.list_tools()).tools
            
            # 严格控制白名单
            builder_tools = format_mcp_tools_for_llm(b_tools_raw, ["initialize_blender_scene", "create_blender_object", "move_object", "rotate_object", "scale_object","get_available_assets"])
            observer_tools = format_mcp_tools_for_llm(o_tools_raw, ["get_scene_status", "render_camera_view"])

            # 初始化灵魂记忆
            builder_messages = [{
                "role": "system", 
                "content": (
                    "你是首席 3D 场景建造专家 (Builder Brain)，具备视觉能力。\n"
                    "你的工作流：\n"
                    "1. 必须先调用 initialize_blender_scene 初始化场景。\n"
                    "2. 必须调用 get_available_assets 获取当前所有由 SAM3D 生成的 3D 资产及其绝对坐标。\n"
                    "3. 遍历这些资产，调用 create_blender_object (obj_type设为'ASSET') 将它们一一导入。导入时无需传入 location 参数，底层会自动根据 JSON 坐标对齐！\n"
                    "4. 观察我发给你的【原始参考图】，对比你导入后的 3D 空间关系。如果发现有穿模、悬空或位置不对，通过 move_object 等工具进行微调。\n"
                    "5. 搭建完毕后，向 Observer 汇报你的操作进度。"
                )
            }]
            
            observer_messages = [{
                "role": "system", 
                "content": (
                    "你是极其严苛的多模态 3D 场景审查员(Observer Brain)。"
                    "你的工作流："
                    "1. 必须同时调用 get_scene_status (获取雷达数据) 和 render_camera_view (拍照)。"
                    "2. 拿到照片和 JSON 数据后，进行图文交叉验证！照片看整体关系和穿模，JSON 算绝对坐标。"
                    "3. 指出错误，并用公式算出正确的 location 坐标给 Builder。"
                    "4. 【极其重要】：如果有错误，回复最后单列一行：[VERDICT: FAIL] 。如果一切完美没有穿模，回复最后单列一行：[VERDICT: PASS] 。"
                )
            }]

            print("\n🧬 正在将原始图像编码为视觉神经信号，注入 Builder 大脑...")
            base64_image = encode_image_to_base64(image_path)

            user_task = [
                {
                    "type": "text", 
                    "text": "这是一张我们需要重建的原始参考图。我已经使用前置流水线提取了图片中的物体，并为你生成了 3D 资产（存放在本地）。请你结合这张图片，开始执行你的场景重组任务！"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
            
            MemoryManager.append_and_prune(builder_messages, {"role": "user", "content": user_task})
            max_turns = 10
            
            for turn in range(max_turns):
                print(f"\n==================== 🔄 [第 {turn + 1} 轮迭代] ====================")
                
                # ================================================
                # 👷 阶段 1：Builder 闭眼摸黑干活
                # ================================================
                print(f"👷 [Builder Brain ({BUILDER_MODEL_ID})] 正在满头大汗地施工...")
                while True: 
                    await asyncio.sleep(2) 
                    try:
                        response = await builder_client.chat.completions.create(
                            model=BUILDER_MODEL_ID, messages=builder_messages, tools=builder_tools, tool_choice="auto"
                        )
                    except Exception as e:
                        print(f"❌ Builder API 请求失败: {e}"); break
                        
                    if not getattr(response, 'choices', None): break
                    msg = response.choices[0].message
                    
                    safe_msg = {"role": "assistant", "content": msg.content or ""}
                    if msg.tool_calls:
                        safe_msg["tool_calls"] = [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in msg.tool_calls]
                    MemoryManager.append_and_prune(builder_messages, safe_msg)
                    
                    if not msg.tool_calls:
                        print(f"👷 [Builder 汇报]:\n{msg.content}")
                        break
                        
                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        func_args = json.loads(tool_call.function.arguments)
                        print(f"  ⚡ Builder 挥舞铲子 -> {func_name} {func_args}")
                        try:
                            mcp_res = await b_session.call_tool(func_name, arguments=func_args)
                            res_text = mcp_res.content[0].text
                        except Exception as e:
                            res_text = f"失败: {str(e)}"
                        MemoryManager.append_and_prune(builder_messages, {"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": res_text})

                # ================================================
                # 🧐 阶段 2：Observer 睁眼多模态视察
                # ================================================
                print(f"\n🧐 [Observer Brain ({OBSERVER_MODEL_ID})] 提着单反和卷尺进入了现场...")
                MemoryManager.append_and_prune(observer_messages, {"role": "user", "content": "Builder 刚刚完成了一轮施工。请你立刻调用雷达和摄像机进行双重检查。"})
                
                feedback = ""
                
                while True: 
                    await asyncio.sleep(2) 
                    try:
                        response = await observer_client.chat.completions.create(
                            model=OBSERVER_MODEL_ID, messages=observer_messages, tools=observer_tools, tool_choice="auto"
                        )
                    except Exception as e:
                        print(f"❌ Observer API 请求失败: {e}"); break
                        
                    if not getattr(response, 'choices', None): break
                    msg = response.choices[0].message
                    
                    safe_msg = {"role": "assistant", "content": msg.content or ""}
                    if msg.tool_calls:
                        safe_msg["tool_calls"] = [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in msg.tool_calls]
                    MemoryManager.append_and_prune(observer_messages, safe_msg)
                    
                    if not msg.tool_calls:
                        feedback = msg.content
                        print(f"🧐 [Observer 判定报告]:\n{feedback}")
                        break
                        
                    has_new_photo = False
                    
                    # 执行 Observer 的检查工具
                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        print(f"  📡 Observer 启动设备 -> {func_name}...")
                        try:
                            func_args = json.loads(tool_call.function.arguments)
                            mcp_res = await o_session.call_tool(func_name, arguments=func_args)
                            res_text = mcp_res.content[0].text
                        except Exception as e:
                            res_text = f"扫描失败: {str(e)}"
                            
                        MemoryManager.append_and_prune(observer_messages, {"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": res_text})
                        
                        # 📸 视觉劫持逻辑
                        if func_name == "render_camera_view" and "SUCCESS" in res_text:
                            has_new_photo = True

                    # 补充照片给大模型
                    if has_new_photo:
                        photo_path = os.path.join(Path(__file__).resolve().parent.parent, "assets", "renders", "current_view.png")
                        if os.path.exists(photo_path):
                            print("  🧬 正在将照片编码为视觉神经信号输入大模型...")
                            base64_image = encode_image_to_base64(photo_path)
                            MemoryManager.append_and_prune(observer_messages, {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "📸 这是刚刚拍下的现场照片！请结合前面的 JSON 数据，告诉我你看到了什么？有没有穿模？"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                                ]
                            })

                # ================================================
                # ⚖️ 阶段 3：命运的裁决
                # ================================================
                if "[VERDICT: PASS]" in feedback:
                    print("\n🎉🎉🎉 奇迹诞生！Observer 验收通过！完美的 3D 场景搭建完毕！")
                    break
                else:
                    print("\n💥 验收不合格！Observer 发现严重缺陷，已将整改意见和严厉警告发回给 Builder！")
                    MemoryManager.append_and_prune(builder_messages, {
                        "role": "user", 
                        "content": f"【最高级别警告】你的搭建被带有视觉能力的 Observer 打回！请务必根据它的现场图文质检报告，严格计算坐标并调用工具修改：\n{feedback}"
                    })

if __name__ == "__main__":
    # 🌟 修改点 3：直接使用我们之前在 .env 配置的全局默认测试图
    test_image = Config.default_source_image
    asyncio.run(run_heterogeneous_agents(test_image))