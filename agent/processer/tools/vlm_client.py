import base64
import os
import re
import time
from openai import OpenAI

def encode_image_to_base64(image_path):
    """将本地图片文件转换为 Base64 编码字符串"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ask_vlm_for_label(mask_png_path, original_image_path=None, model="gpt-4o", api_key=None, base_url=None, max_retries=3):
    """
    调用 VLM (如 GPT-4o) 来识别抠出来的带有透明通道的 mask 图片。
    包含自动重试、安全解析，并支持开放式物体分类。
    """
    client = OpenAI(api_key=api_key, base_url=base_url)

    print(f"  🔍 正在请求 VLM 识别图片...")
    mask_base64 = encode_image_to_base64(mask_png_path)
    
    # 1. 组装 System Prompt 与核心任务 (修复了换行符，并保留了你优秀的 Prompt 结构)
    prompt_text = (
        "Role: CV Segmentation Expert.\n"
        "Task: Identify the semantic label of the masked region.\n"
        "Rules:\n"
        "1. If the object is the ground, floor, road, or terrain, output strictly 'ground'.\n"
        "2. If the object is the background, sky, or irrelevant context, output strictly 'background'.\n"
        "3. If the object is a human, person, or ANY type of animal, output strictly 'animal'.\n"
        "4. For all other objects, output a concise 1-2 word noun describing it (e.g., 'tree', 'house', 'car').\n\n"
        "Use only lowercase letters. Do not provide any explanations or punctuation. ONLY output the noun.\n"
        "Examples:\n"
        "● Input: Mask on a cloudy sky. Output: background\n"
        "● Input: Mask on a person. Output: animal\n"
        "Output: Return ONLY the single label string."
    )

    content_list = [
        {
            "type": "text",
            "text": prompt_text
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{mask_base64}"
            }
        }
    ]

    # 2. 如果提供了原图，将其作为上下文补充进去
    if original_image_path and os.path.exists(original_image_path):
        ori_base64 = encode_image_to_base64(original_image_path)
        content_list.append({
            "type": "text",
            "text": "Here is the original full image for context, so you can see where this object is located:"
        })
        content_list.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{ori_base64}"
            }
        })

    # 3. 发送请求 (加入重试循环)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": content_list
                    }
                ],
                max_tokens=10,    # 限制输出长度
                temperature=0.0   # 必须设为 0，确保分类的确定性和稳定性
            )
            
            # 4. 安全提取：防止 NoneType 报错
            raw_label = None
            if hasattr(response, 'choices') and response.choices:
                msg = response.choices[0].message
                # 兼容某些非标准模型返回字典的情况
                raw_label = msg.get('content') if isinstance(msg, dict) else msg.content
            elif isinstance(response, dict) and 'choices' in response and response['choices']:
                raw_label = response['choices'][0]['message'].get('content')
            
            if not raw_label:
                raise ValueError("API 返回了空数据")

            raw_label = raw_label.strip().lower()
            
            # 5. 动态正则清洗：支持 tree, car 等任意标签，自动替换空格为下划线
            clean_label = re.sub(r'[^\w\s]', '', raw_label)
            clean_label = re.sub(r'\s+', '_', clean_label).strip('_')
            
            # 6. 最终的规则兜底
            if "background" in clean_label: 
                return "background"
            if "ground" in clean_label or "floor" in clean_label: 
                return "ground"
            if "animal" in clean_label or "person" in clean_label or "human" in clean_label: 
                return "animal"
                
            if not clean_label:
                return "other"
                
            return clean_label
            
        except Exception as e:
            print(f"  ⚠️ 第 {attempt + 1} 次请求异常: {e}")
            if attempt < max_retries - 1:
                print("  ⏳ 等待 2 秒后自动重试...")
                time.sleep(2)
            else:
                print("  ❌ 多次重试均失败，触发兜底策略，标记为 'other'")
                return "other"