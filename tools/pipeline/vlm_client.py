import base64
import os
import re
import time
import sys
from openai import OpenAI

# 📍 动态定位项目根目录，确保能正确导入 config
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(PIPELINE_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config

def encode_image_to_base64(image_path):
    """将本地图片文件转换为 Base64 编码字符串"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ask_vlm_for_label(mask_png_path, original_image_path=None, max_retries=3):
    """
    调用 VLM 来识别抠出来的带有透明通道的 mask 图片。
    [重构升级]: 自动读取全局 config，无需再手动传入 api_key 和 base_url
    """
    # 直接从全局配置读取 Processer 视觉大模型的参数
    client = OpenAI(
        api_key=Config.processer_api_key, 
        base_url=Config.processer_base_url
    )
    model_id = Config.processer_model_id

    print(f"  🔍 正在请求 VLM ({model_id}) 识别图片...")
    mask_base64 = encode_image_to_base64(mask_png_path)
    
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
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{mask_base64}"}}
    ]

    if original_image_path and os.path.exists(original_image_path):
        ori_base64 = encode_image_to_base64(original_image_path)
        content_list.append({"type": "text", "text": "Here is the original full image for context:"})
        content_list.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ori_base64}"}})

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": content_list}],
                max_tokens=10,
                temperature=0.0
            )
            
            raw_label = None
            if hasattr(response, 'choices') and response.choices:
                msg = response.choices[0].message
                raw_label = msg.get('content') if isinstance(msg, dict) else msg.content
            
            if not raw_label:
                raise ValueError("API 返回了空数据")

            raw_label = raw_label.strip().lower()
            clean_label = re.sub(r'[^\w\s]', '', raw_label)
            clean_label = re.sub(r'\s+', '_', clean_label).strip('_')
            
            # 规则兜底
            if "background" in clean_label: return "background"
            if "ground" in clean_label or "floor" in clean_label: return "ground"
            if "animal" in clean_label or "person" in clean_label or "human" in clean_label: return "animal"
            if not clean_label: return "other"
                
            return clean_label
            
        except Exception as e:
            print(f"  ⚠️ 第 {attempt + 1} 次请求异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return "other"