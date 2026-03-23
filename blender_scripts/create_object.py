import bpy
import sys
import os
import json

argv = sys.argv
if "--" not in argv: sys.exit(1)
args = argv[argv.index("--") + 1:]
if len(args) < 5: sys.exit(1)

obj_type = args[0].upper()
obj_name = args[1]
loc_x, loc_y, loc_z = float(args[2]), float(args[3]), float(args[4])

if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# 导入前先取消选中所有物体，防止抓取错 Active Object
bpy.ops.object.select_all(action='DESELECT')
active_obj = None

if obj_type in ["CUBE", "SPHERE"]:
    if obj_type == "CUBE":
        bpy.ops.mesh.primitive_cube_add(location=(loc_x, loc_y, loc_z))
    elif obj_type == "SPHERE":
        bpy.ops.mesh.primitive_uv_sphere_add(location=(loc_x, loc_y, loc_z))
    active_obj = bpy.context.active_object

elif obj_type == "ASSET":
    if len(args) < 6:
        print("Error: 资产类型未提供文件路径")
        sys.exit(1)
    
    asset_path = args[5]
    print(f"正在尝试导入资产: {asset_path}")
    
    # 导入 GLB
    bpy.ops.import_scene.gltf(filepath=asset_path)
    
    # 获取刚导入的物体（确保拿到的不是默认的 Ground_Plane）
    imported_objs = bpy.context.selected_objects
    if not imported_objs:
        print("Error: 导入失败，未在场景中找到新物体")
        sys.exit(1)
    
    active_obj = imported_objs[0]
    
    # 🧠 核心：智能坐标还原，读取 SAM3D 计算出的 json 元数据
    json_path = asset_path.replace(".glb", "_info.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
        
        # 1. 恢复真实缩放
        scale = info.get("scale", [1.0, 1.0, 1.0])
        active_obj.scale = (scale[0], scale[1], scale[2])
        
        # 2. 恢复真实平移
        translation = info.get("translation", [loc_x, loc_y, loc_z])
        active_obj.location = (translation[0], translation[1], translation[2])
        
        # 3. 恢复旋转：SAM3D 输出的是四元数，我们直接交给 Blender 原生处理
        rotation = info.get("rotation", [1.0, 0.0, 0.0, 0.0])
        active_obj.rotation_mode = 'QUATERNION'
        active_obj.rotation_quaternion = (rotation[0], rotation[1], rotation[2], rotation[3])
        
        print("✅ 成功应用 SAM3D 的 T/R/S 空间矩阵与四元数！")
    else:
        # 兜底：如果没有 json，退回默认创建坐标
        active_obj.location = (loc_x, loc_y, loc_z)

else:
    print(f"Error: 不支持的物体类型 {obj_type}")
    sys.exit(1)

# 重命名物体，方便 Observer 识别与 Builder 后续抓取
active_obj.name = obj_name

bpy.ops.wm.save_mainfile()
print(f"Success: 成功创建/导入了 {obj_name}")