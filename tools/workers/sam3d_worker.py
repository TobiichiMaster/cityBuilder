import sys
import os
import argparse
import json
import numpy as np
from PIL import Image

# ==========================================
# 📍 1. 动态寻址与环境注入
# ==========================================
WORKER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(WORKER_DIR))
SAM3D_ROOT = os.path.join(PROJECT_ROOT, "utils", "sam3d")

sys.path.append(PROJECT_ROOT)                         
sys.path.append(SAM3D_ROOT)                           
sys.path.append(os.path.join(SAM3D_ROOT, "notebook")) 

try:
    from inference import Inference
except ImportError as e:
    print(f"❌ [Worker Error] 无法导入 SAM3D inference: {e}", file=sys.stderr)
    sys.exit(1)


# ==========================================
# 🚀 2. 核心推理与 CLI 入口
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="SAM3D 资产生成 Worker")
    parser.add_argument("--config", required=True, help="SAM3D pipeline.yaml 的路径")
    parser.add_argument("--image", required=True, help="输入原图路径")
    parser.add_argument("--mask", required=True, help="对应的 mask (.npy) 路径")
    parser.add_argument("--output", required=True, help="输出 3D 模型 (.glb) 路径")
    args = parser.parse_args()

    try:
        # 1. 初始化模型
        inference_model = Inference(args.config, compile=False)
        
        # 2. 读取图片和掩码并处理 bug
        image_pil = Image.open(args.image).convert("RGB")
        mask = np.load(args.mask)
        if len(mask.shape) == 3:
            mask = mask[0]
            
        # 🚨 强制转换为 True/False (0/1)
        mask = mask > 0  
            
        # ✂️ [新增终极优化：按掩码边界框 (Bounding Box) 精准裁剪]
        # 找到 mask 中所有有效像素的坐标
        y_indices, x_indices = np.where(mask)
        if len(y_indices) > 0 and len(x_indices) > 0:
            # 获取边界，并预留 30 像素的 Padding 防止边缘被切坏
            pad = 30
            y_min = max(0, y_indices.min() - pad)
            y_max = min(mask.shape[0], y_indices.max() + pad)
            x_min = max(0, x_indices.min() - pad)
            x_max = min(mask.shape[1], x_indices.max() + pad)

            # 执行物理裁剪
            image_pil = image_pil.crop((x_min, y_min, x_max, y_max))
            mask = mask[y_min:y_max, x_min:x_max]
            print(f"  [Worker] ✂️ 剔除无效背景：图像已精准裁剪至 {x_max-x_min}x{y_max-y_min}", flush=True)

        # 🛡️ [显存保护装甲：裁剪后如果依然超大，则等比缩放]
        max_res = 1024  
        orig_w, orig_h = image_pil.size
        scale = 1.0
        
        # 规则1：长边不能超过 1024
        if max(orig_w, orig_h) > max_res:
            scale = max_res / float(max(orig_w, orig_h))
            
        # 规则2：防止复杂物体的有效点云过多 (把上限下调至 15000，留出足够的安全余量)
        estimated_active_pixels = np.sum(mask) * (scale ** 2)
        if estimated_active_pixels > 15000:
            safe_scale = np.sqrt(15000 / np.sum(mask))
            scale = min(scale, safe_scale)
            
        if scale < 1.0:
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            print(f"  [Worker] 🛡️ 触发降采样：面积过大，缩小至 {new_w}x{new_h}", flush=True)
            image_pil = image_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
            mask_pil = Image.fromarray((mask * 255).astype(np.uint8))
            mask_pil = mask_pil.resize((new_w, new_h), Image.Resampling.NEAREST)
            mask = np.array(mask_pil) > 127
            
        image = np.array(image_pil)
        
        # 3. 执行推理 
        output = inference_model(image, mask)
        
        # 4. 导出 3D 模型文件 (终极健壮版导出逻辑)
        exported = False
        
        # 策略 A：直接寻找字典里拥有 .export() 方法的对象 
        for k, v in output.items():
            item = v[0] if isinstance(v, list) and len(v) > 0 else v
            if hasattr(item, "export"):
                item.export(args.output)
                exported = True
                break
                
        # 策略 B：提取内部的 MeshExtractResult，手动转换为 GLB
        if not exported and "mesh" in output:
            mesh_obj = output["mesh"][0] if isinstance(output["mesh"], list) else output["mesh"]
            
            if hasattr(mesh_obj, "export"):
                mesh_obj.export(args.output)
                exported = True
            elif "gaussian" in output:
                # 🚀 核心绝杀：调用官方的 to_glb 工具，融合高斯点云和裸网格
                from sam3d_objects.model.backbone.tdfy_dit.utils import postprocessing_utils
                gs_obj = output["gaussian"][0] if isinstance(output["gaussian"], list) else output["gaussian"]
                
                print("  [Worker] 正在手动调用 to_glb 组装带纹理的标准 GLB 模型...", flush=True)
                glb_trimesh = postprocessing_utils.to_glb(gs_obj, mesh_obj)
                glb_trimesh.export(args.output)
                exported = True
            else:
                # 策略 C：退化保存为 OBJ 格式 (裸模)
                if hasattr(mesh_obj, "write_obj"):
                    args.output = args.output.replace(".glb", ".obj")
                    mesh_obj.write_obj(args.output)
                    exported = True
                elif hasattr(mesh_obj, "write_ply"):
                    args.output = args.output.replace(".glb", ".ply")
                    mesh_obj.write_ply(args.output)
                    exported = True
                    
        if not exported:
            raise RuntimeError(f"无法找到任何有效的模型导出方案！输出包含的字段有: {list(output.keys())}")
            
        # 5. 生成配套的 JSON 空间坐标信息
        json_path = args.output.replace(".glb", "_info.json")
        info = {
            "asset_name": os.path.basename(args.output),
            "location": [0.0, 0.0, 0.0]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"❌ [Worker Error] 底层推理发生异常: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    finally:
        # 🧹 [终极内存清理] 无论成功还是失败，强制清空当前 GPU 的缓存
        try:
            import torch
            import gc
            
            # 删除不再需要的大对象
            if 'output' in locals():
                del output
            if 'inference_model' in locals():
                del inference_model
                
            # 执行 Python 的垃圾回收
            gc.collect()
            
            # 强制清空 CUDA 缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            print(f"  [Worker] 🧹 显存大扫除完成。", flush=True)
        except Exception:
            pass

if __name__ == "__main__":
    main()