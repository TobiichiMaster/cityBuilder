from typing import Optional
from dotenv import load_dotenv
import os

# 加载配置
load_dotenv()

# 创建配置类
class Config:
    # 大模型配置
    llm_api_key: str = os.getenv("LLM_API_KEY", "local")
    llm_base_url: Optional[str] = os.getenv("LLM_BASE_URL", "")
    llm_model_id: Optional[str] = os.getenv("LLM_MODEL_ID", "")
    
    # Blender配置
    blender_path: str = os.getenv("BLENDER_PATH")
    
    # MCP配置
    server_command: str = "python"
    server_args: list = None

    # 🔥 这里必须缩进！我帮你修好了
    @classmethod
    def validate(cls):
        if not cls.llm_api_key:
            raise ValueError("环境变量中未配置API_KEY，请检查.env文件")
        if not cls.llm_base_url:
            raise ValueError("环境变量中未配置BASE_URL，请检查.env文件")
        if not cls.llm_model_id:
            raise ValueError("环境变量中未配置MODEL_ID，请检查.env文件")
        if not cls.blender_path:
            raise ValueError("环境变量中未配置BLENDER_PATH，请检查.env文件")

Config.validate()