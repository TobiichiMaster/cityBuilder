from typing import Optional
from dotenv import load_dotenv
import os
from pathlib import Path

# 获取 config.py 所在的目录（即项目根目录）
BASE_DIR = Path(__file__).resolve().parent
# 显式指定 .env 文件的绝对路径
env_path = BASE_DIR / ".env"

# 加载配置
load_dotenv(dotenv_path=env_path)
# 创建配置类
class Config:
    # Builder大模型配置
    builder_api_key: str = os.getenv("BUILDER_API_KEY", "local")
    builder_base_url: Optional[str] = os.getenv("BUILDER_BASE_URL", "")
    builder_model_id: Optional[str] = os.getenv("BUILDER_MODEL_ID", "")
    # Observer大模型配置
    observer_api_key: Optional[str] = os.getenv("OBSERVER_API_KEY","")
    observer_base_url: Optional[str] = os.getenv("OBSERVER_BASE_URL","")
    observer_model_id: Optional[str] = os.getenv("OBSERVER_MODEL_ID","")
    # Blender配置
    blender_path: str = os.getenv("BLENDER_PATH")
    
    # MCP配置
    server_command: str = "python"
    server_args: list = None

    # 🔥 这里必须缩进！我帮你修好了
    @classmethod
    def validate(cls):
        if not cls.builder_api_key:
            raise ValueError("环境变量中未配置BUILDER_API_KEY，请检查.env文件")
        if not cls.builder_base_url:
            raise ValueError("环境变量中未配置BUILDER_BASE_URL，请检查.env文件")
        if not cls.builder_model_id:
            raise ValueError("环境变量中未配置BUILDER_MODEL_ID，请检查.env文件")
        if not cls.observer_api_key:
            raise ValueError("环境变量中未配置OBSERVER_API_KEY，请检查.env文件")
        if not cls.observer_base_url:
            raise ValueError("环境变量中未配置OBSERVER_BASE_URL，请检查.env文件")
        if not cls.observer_model_id:
            raise ValueError("环境变量中未配置OBSERVER_MODEL_ID，请检查.env文件")
        if not cls.blender_path:
            raise ValueError("环境变量中未配置BLENDER_PATH，请检查.env文件")

Config.validate()