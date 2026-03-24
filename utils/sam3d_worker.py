import sys
import os
import argparse

# 1. 自动定位项目根目录和 SAM3D 的根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAM3D_ROOT = os.path.join(PROJECT_ROOT, "utils", "sam3d")

# 2. 【核心修复】：强行把 SAM3D 的目录塞进环境变量
sys.path.append(PROJECT_ROOT)                         
sys.path.append(SAM3D_ROOT)                           # <--- 加上这一行，Python 就能找到 sam3d_objects 这个本地文件夹了！
sys.path.append(os.path.join(SAM3D_ROOT, "notebook")) 

# 3. 现在再导入，绝对不会报错了
from inference import Inference

def main():
    # 接收从 Agent 发送过来的参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--mask", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # 初始化大模型并开始推理
    try:
        inference_model = Inference(args.config)
        inference_model.run(args.image, args.mask, args.output)
    except Exception as e:
        print(f"底层推理发生异常: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()