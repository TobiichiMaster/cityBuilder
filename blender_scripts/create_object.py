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
        print("Error: 缺少 asset_path")
        sys.exit(1)
        
    asset_path = args[5]
    
    # 🔥 核心修正：使用“差集法”准确捕获导入的物体
    objs_before = set(bpy.data.objects)
    
    try:
        bpy.ops.import_scene.gltf(filepath=asset_path)
    except Exception as e:
        print(f"Error: Blender GLTF 导入器崩溃 -> {e}")
        sys.exit(1)
        
    objs_after = set(bpy.data.objects)
    imported_objs = list(objs_after - objs_before)
    
    if not imported_objs:
        print(f"Error: 严重错误！{asset_path} 导入后没有产生任何 Mesh。")
        sys.exit(1)
        
    # 获取真正的根节点（剔除子网格和骨骼节点）
    root_objs = [o for o in imported_objs if o.parent is None]
    active_obj = root_objs[0] if root_objs else imported_objs[0]
    
    # 🧠 读取 SAM3D 坐标
    json_path = asset_path.replace(".glb", "_info.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
        
        scale = info.get("scale", [1.0, 1.0, 1.0])
        active_obj.scale = (scale[0], scale[1], scale[2])
        
        translation = info.get("translation", [loc_x, loc_y, loc_z])
        active_obj.location = (translation[0], translation[1], translation[2])
        
        rotation = info.get("rotation", [1.0, 0.0, 0.0, 0.0])
        active_obj.rotation_mode = 'QUATERNION'
        active_obj.rotation_quaternion = (rotation[0], rotation[1], rotation[2], rotation[3])
    else:
        print(f"Warning: 找不到 {json_path}，使用默认坐标")
        active_obj.location = (loc_x, loc_y, loc_z)

else:
    print(f"Error: 不支持的物体类型 {obj_type}")
    sys.exit(1)

# 重命名物体，方便 Observer 识别与 Builder 后续抓取
active_obj.name = obj_name

bpy.ops.wm.save_mainfile()
print(f"Success: 成功创建/导入了 {obj_name}")