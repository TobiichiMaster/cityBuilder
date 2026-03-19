import bpy
import sys
import os
# === 1. 解析外部传入的参数 ===
argv = sys.argv
if "--" not in argv:
    sys.exit(1)



args = argv[argv.index("--") + 1:]


if len(args) < 5:
    sys.exit(1)

obj_type = args[0].upper()
obj_name = args[1]
loc_x, loc_y, loc_z = float(args[2]), float(args[3]), float(args[4])

# === 2. 准备 Blender 环境 ===
# 确保我们在物体模式 (Object Mode) 下才能新建物体
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')



active_obj = None
# === 3. 核心工具：调用 bpy API 创建物体 ===
if obj_type == "CUBE":
    bpy.ops.mesh.primitive_cube_add(location=(loc_x, loc_y, loc_z))
    active_obj = bpy.context.active_object
    print(f"准备在 ({loc_x}, {loc_y}, {loc_z}) 创建 {obj_type}，命名为 {obj_name}...")
elif obj_type == "SPHERE":
    bpy.ops.mesh.primitive_uv_sphere_add(location=(loc_x, loc_y, loc_z))
    active_obj = bpy.context.active_object
    print(f"准备在 ({loc_x}, {loc_y}, {loc_z}) 创建 {obj_type}，命名为 {obj_name}...")
elif obj_type == "ASSET":
    # === 核心逻辑：导入外部 GLB ===
    if len(args) < 6:
        print("Error: 资产类型未提供文件路径")
        sys.exit(1)
    
    asset_path = args[5] # 拿到从 mcp server 传过来的绝对路径
    print(f"正在尝试导入资产: {asset_path}")
    
    # 导入 GLTF/GLB (这是 Blender 的内置算子)
    bpy.ops.import_scene.gltf(filepath=asset_path)
    
    # 导入后，自动把刚导入的物体设为激活，并改名
    # 因为 GLB 导入可能会包含多个物体（比如包含一个 Armature），
    # 更好的做法通常是导入到一个新的 Collection，然后我们取里面的物体
    # 为了简单起见，我们假设导入的是单一物体
    active_obj = bpy.context.active_object
    
    # 3D 资产归一化的坑：强制把刚导入的模型缩放到 1x1x1m 的包围盒里，
    # 否则 SAM3D 生成的物体可能会像个星球那么大
    max_dim = max(active_obj.dimensions)
    if max_dim > 0:
        scale_factor = 1.0 / max_dim
        active_obj.scale = (active_obj.scale[0] * scale_factor, active_obj.scale[1] * scale_factor, active_obj.scale[2] * scale_factor)
    
    # 移动到指定位置
    active_obj.location = (loc_x, loc_y, loc_z)

else:
    print(f"Error: 不支持的物体类型 {obj_type}")
    sys.exit(1)

# 改名
active_obj.name = obj_name
# 收尾
bpy.ops.wm.save_mainfile()
print(f"Success: 成功创建/导入了 {obj_name}")