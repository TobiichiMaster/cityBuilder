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
                    "5. 搭建完毕后，向 Observer 汇报你的操作进度。\n"
                    "【⚠️ 极其重要的空间坐标法则 ⚠️】\n"
                    "1. 资产原点：你所使用的所有 3D 模型资产，其坐标原点 (Location) 都位于该物体的【绝对几何中心】，而不是底部！\n"
                    "2. 贴地公式：如果你想让一个物体平稳地放置在地面 (Z=0) 上，你绝对不能把它的 location.z 设为 0（这会导致它一半陷入地下）。\n"
                    "3. 正确做法：你必须先获取该物体的 dimensions（尺寸），然后将其 Z 坐标严格设置为 `dimensions.z / 2`。\n"
                    "4. 举例：如果一栋楼的 dimensions.z 是 10 米，想让它站在地面上，它的 location.z 必须是 5。\n"
                    "5. 坐标继承原则：当 Observer 让你修复 Z 轴穿模问题时，你【绝对不能】将 X 和 Y 坐标归零！你必须查阅之前的记录，保留该物体原本在平面的 X 和 Y 位置，仅仅修改 Z 的值！\n"
                )
            }]
            
            observer_messages = [{
                "role": "system", 
                "content": (
                    "你是极其严苛的多模态 3D 场景穿模审查员 (Observer Brain)。\n"
                    "你的工作流：\n"
                    "1. 必须调用 render_camera_view 拍摄现场照片。要检查穿模，你【必须】使用 view_type='LEVEL' 或 'UNDER'！\n"
                    "2. 在 LEVEL（纯水平）视角下，地面是一条绝对的水平线。如果任何建筑或物体的底部超出了这条线（向下延伸），说明发生了严重的穿模 (Clipping)！\n"
                    "3. 如果发生穿模，交叉比对 get_scene_status 获取的 JSON 数据。记住物理法则：物体的绝对底部 Z 坐标 = location.z - (dimensions.z / 2)。\n"
                    "4. 如果计算出底部 Z 坐标 < 0，必须明确告诉 Builder：'大楼陷入了地下！请调用 move_object 将其 location.z 设置为 [正确的数值]'。\n"
                    "5. 如果一切完美，没有任何像素低于地平线，回复最后单列一行：[VERDICT: PASS]。如果有穿模，回复：[VERDICT: FAIL]。"
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