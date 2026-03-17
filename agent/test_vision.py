import asyncio
import os
import sys
import base64
from pathlib import Path
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# 导入配置
sys.path.append(str(Path(__file__).parent.parent))
from config import Config

# 初始化视觉大模型客户端 (请确保你的 .env 里换成了视觉模型，比如 qwen-vl-max)
llm_client = AsyncOpenAI(
    api_key=Config.llm_api_key,
    base_url=Config.llm_base_url
)
MODEL_ID = Config.vllm_model_id

def encode_image_to_base64(image_path):
    """将本地图片文件转换为 Base64 字符串"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def test_camera_and_vision():
    print(f"👁️ 正在通电... 启动视觉中枢测试 (当前模型: {MODEL_ID})...")
    
    server_script = os.path.join(Path(__file__).parent.parent, "mcp_server", "blender_mcp_server.py")
    server_params = StdioServerParameters(command=Config.server_command, args=[server_script])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ MCP 神经连接握手成功！")

            # ==========================================
            # 第一步：强制调用拍照工具
            # ==========================================
            print("\n📸 正在命令 Blender 拍下场景的全景照片...")
            try:
                # 传入一个方向向量 [1, 1, 1] 代表从右上方俯视
                mcp_result = await session.call_tool("render_camera_view", arguments={"view_direction": [1.0, 1.0, 1.0]})
                result_text = mcp_result.content[0].text
                print(result_text)
            except Exception as e:
                print(f"❌ 拍照失败: {e}")
                return

            # 解析出图片保存的路径
            # 我们在 mcp server 里写死了路径在 assets/renders/current_view.png
            image_path = os.path.join(Path(__file__).parent.parent, "assets", "renders", "current_view.png")
            
            if not os.path.exists(image_path):
                print(f"❌ 找不到渲染的图片文件: {image_path}")
                return

            # ==========================================
            # 第二步：将图片转为 Base64 并构建多模态消息
            # ==========================================
            print("\n🧬 正在将图片转换为神经电信号 (Base64)...")
            base64_image = encode_image_to_base64(image_path)
            
            # 【核心知识点】：OpenAI 格式的多模态请求体构造
            # 注意看 content 变成了一个列表，里面可以混排 text 和 image_url 字典
            vision_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "你是一个 3D 场景审查员。这是我刚才用 Blender 渲染的场景照片。请仔细观察并告诉我：你看到了哪些物体？它们的位置关系大概是怎样的？有没有穿模或者悬空的情况？"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                # 这里的格式是固定的：data:image/图片格式;base64,真实的base64字符串
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]

            # ==========================================
            # 第三步：发给大模型进行视觉推理
            # ==========================================
            print("🧠 正在请求大模型进行视觉推理，请稍候...")
            try:
                response = await llm_client.chat.completions.create(
                    model=MODEL_ID,
                    messages=vision_messages,
                )
                print("\n🧐 [视觉大模型分析报告]:")
                print(response.choices[0].message.content)
            except Exception as e:
                print(f"\n❌ API 请求失败，请检查模型名称和密钥是否支持视觉输入: {e}")

if __name__ == "__main__":
    asyncio.run(test_camera_and_vision())