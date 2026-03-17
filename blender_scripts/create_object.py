import bpy
import sys

# === 1. 解析外部传入的参数 ===
argv = sys.argv
if "--" not in argv:
    print("Error: 未找到脚本参数分割符 '--'")
    sys.exit(1)

args = argv[argv.index("--") + 1:]

# 至少需要知道“建什么”和“叫什么”
if len(args) < 2:
    print("Error: 参数不足。至少需要: obj_type, name")
    sys.exit(1)

obj_type = args[0].upper()
obj_name = args[1]

# ★ 设定默认坐标为世界原点 [0, 0, 0]
loc_x, loc_y, loc_z = 0.0, 0.0, 0.0

# 如果参数够多（包含了 x, y, z），就覆盖默认值
if len(args) >= 5:
    loc_x, loc_y, loc_z = float(args[2]), float(args[3]), float(args[4])

print(f"准备在 ({loc_x}, {loc_y}, {loc_z}) 创建 {obj_type}，命名为 {obj_name}...")

# === 2. 准备 Blender 环境 ===
# 确保我们在物体模式 (Object Mode) 下才能新建物体
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# === 3. 核心工具：调用 bpy API 创建物体 ===
if obj_type == "CUBE":
    # 创建立方体
    bpy.ops.mesh.primitive_cube_add(location=(loc_x, loc_y, loc_z))
elif obj_type == "SPHERE":
    # 创建经纬球
    bpy.ops.mesh.primitive_uv_sphere_add(location=(loc_x, loc_y, loc_z))
elif obj_type == "MONKEY":
    # 创建 Blender 经典的猴头 Suzanne
    bpy.ops.mesh.primitive_monkey_add(location=(loc_x, loc_y, loc_z))
else:
    print(f"Error: 不支持的物体类型 {obj_type}")
    sys.exit(1)

# === 4. 收尾：重命名与状态保存 ===
# 新创建的物体会自动成为“当前激活物体 (Active Object)”
active_obj = bpy.context.active_object
active_obj.name = obj_name

# 将当前修改后的场景覆盖保存到我们打开的 .blend 文件中
bpy.ops.wm.save_mainfile()
print(f"Success: 成功创建了 {obj_name}")