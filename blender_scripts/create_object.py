import bpy
import sys
import os
import mathutils  # 务必导入 mathutils 用于计算世界矩阵

# === 1. 解析外部传入的参数 ===
argv = sys.argv
if "--" not in argv:
    sys.exit(1)

args = argv[argv.index("--") + 1:]
if len(args) < 5:
    print("Error: 参数不足。至少需要: obj_type, name, loc_x, loc_y, loc_z")
    sys.exit(1)

obj_type = args[0].upper()
obj_name = args[1]
loc_x, loc_y, loc_z = float(args[2]), float(args[3]), float(args[4])

if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

active_obj = None

if obj_type == "CUBE":
    bpy.ops.mesh.primitive_cube_add(location=(loc_x, loc_y, loc_z))
    active_obj = bpy.context.active_object
elif obj_type == "SPHERE":
    bpy.ops.mesh.primitive_uv_sphere_add(location=(loc_x, loc_y, loc_z))
    active_obj = bpy.context.active_object
elif obj_type == "ASSET":
    if len(args) < 6:
        print("Error: 资产类型未提供文件路径")
        sys.exit(1)
    
    asset_path = args[5]
    print(f"正在尝试导入资产: {asset_path}")
    
    # === 核心修复 1：利用差集精确捕获新导入的资产 ===
    objs_before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=asset_path)
    objs_after = set(bpy.data.objects)
    
    new_objs = list(objs_after - objs_before)
    if not new_objs:
        print(f"Error: 从 {asset_path} 中没有导入任何物体")
        sys.exit(1)
        
    # === 核心修复 2：创建一个 Empty 控制柄统一管理 ===
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    asset_root = bpy.context.active_object
    asset_root.name = obj_name # 将大模型指定的名字赋给控制柄
    
    # 梳理层级：将所有游离的新顶级物体塞进控制柄
    for obj in new_objs:
        if obj.parent is None and obj != asset_root:
            obj.parent = asset_root
            
    # === 核心修复 3：批量重命名网格，让 Observer 雷达能扫到 ===
    meshes = [o for o in new_objs if o.type == 'MESH']
    for i, m in enumerate(meshes):
        m.name = f"{obj_name}_mesh_{i}"

    # === 核心修复 4：穿透 Empty 层级，计算真实的全局包围盒 ===
    bpy.context.view_layer.update() # 强制更新矩阵，防止坐标计算错误
    if meshes:
        min_coords = [float('inf')] * 3
        max_coords = [float('-inf')] * 3
        for m in meshes:
            # bbox 必须乘以 matrix_world 才能得到真实的绝对长宽高
            bbox = [m.matrix_world @ mathutils.Vector(corner) for corner in m.bound_box]
            for corner in bbox:
                for i in range(3):
                    min_coords[i] = min(min_coords[i], corner[i])
                    max_coords[i] = max(max_coords[i], corner[i])
                    
        # 提取真实尺寸并进行 1m 安全归一化
        max_dim = max([max_coords[i] - min_coords[i] for i in range(3)])
        if max_dim > 0:
            scale_factor = 1.0 / max_dim
            asset_root.scale = (scale_factor, scale_factor, scale_factor)
            
    # 将控制柄移动到目标位置
    asset_root.location = (loc_x, loc_y, loc_z)
    active_obj = asset_root

else:
    print(f"Error: 不支持的物体类型 {obj_type}")
    sys.exit(1)

# 为基础几何体改名（ASSET在上面已经改过了）
if obj_type != "ASSET":
    active_obj.name = obj_name

bpy.ops.wm.save_mainfile()
print(f"Success: 成功创建/导入了 {obj_name}")