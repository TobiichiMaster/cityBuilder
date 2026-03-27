from typing import Optional
from dotenv import load_dotenv
import os
from pathlib import Path

# 获取 config.py 所在的目录（即项目根目录）
BASE_DIR = Path(__file__).resolve().parent #cityBuilder
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
    # Processer大模型配置
    processer_api_key: Optional[str] = os.getenv("PROCESSER_API_KEY","")
    processer_base_url: Optional[str] = os.getenv("PROCESSER_BASE_URL","")
    processer_model_id: Optional[str] = os.getenv("PROCESSER_MODEL_ID","")
    # Blender配置
    blender_path: str = os.getenv("BLENDER_PATH")
    # 地址配置
    assets_path: str = os.getenv("ASSETS_PATH","")
    # MCP配置
    server_command: str = "python"
    server_args: list = None

    # ====== 新增：隔离运行环境 ======
    sam_python_exe: str = os.getenv("SAM_PYTHON_EXE", "")
    sam3d_python_exe: str = os.getenv("SAM3D_PYTHON_EXE", "")
    
    # ====== 新增：模型权重与配置 ======
    # 如果 .env 里写的是相对路径，这里自动转为绝对路径
    sam_checkpoint_path: str = os.getenv("SAM_CHECKPOINT_PATH", "")
    sam3d_config_path: str = os.getenv("SAM3D_CONFIG_PATH", "")
    
    # 如果使用的是相对路径，自动拼接 BASE_DIR
    if sam_checkpoint_path and not os.path.isabs(sam_checkpoint_path):
        sam_checkpoint_path = os.path.join(BASE_DIR, sam_checkpoint_path)
    if sam3d_config_path and not os.path.isabs(sam3d_config_path):
        sam3d_config_path = os.path.join(BASE_DIR, sam3d_config_path)

    # ====== 新增：默认测试图 ======
    default_source_image: str = os.getenv("DEFAULT_SOURCE_IMAGE", "assets/source/default.png")
    if not os.path.isabs(default_source_image):
        default_source_image = os.path.join(BASE_DIR, default_source_image)

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
        if not cls.processer_api_key:
            raise ValueError("环境变量中未配置PROCESSER_API_KEY，请检查.env文件")
        if not cls.processer_base_url:
            raise ValueError("环境变量中未配置PROCESSER_BASE_URL，请检查.env文件")
        if not cls.processer_model_id:
            raise ValueError("环境变量中未配置PROCESSER_MODEL_ID，请检查.env文件")
        if not cls.assets_path:
            raise ValueError("环境变量中未配置ASSETS_PATH，请检查.env文件")
        if not cls.blender_path:
            raise ValueError("环境变量中未配置BLENDER_PATH，请检查.env文件")
        if not cls.sam_python_exe or not os.path.exists(cls.sam_python_exe):
            raise ValueError(f"无效的 SAM_PYTHON_EXE，请检查 .env 文件: {cls.sam_python_exe}")
        if not cls.sam3d_python_exe or not os.path.exists(cls.sam3d_python_exe):
            raise ValueError(f"无效的 SAM3D_PYTHON_EXE，请检查 .env 文件: {cls.sam3d_python_exe}")
        if not cls.sam_checkpoint_path or not os.path.exists(cls.sam_checkpoint_path):
            raise ValueError(f"找不到 SAM 权重文件，请检查 .env: {cls.sam_checkpoint_path}")
        if not cls.sam3d_config_path or not os.path.exists(cls.sam3d_config_path):
            raise ValueError(f"找不到 SAM3D 配置文件，请检查 .env: {cls.sam3d_config_path}")

Config.validate()