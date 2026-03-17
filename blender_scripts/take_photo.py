import bpy
import sys
import math
import mathutils

# 解析参数
argv = sys.argv
if "--" not in argv:
    sys.exit(1)

args = argv[argv.index("--") + 1:]
if len(args) < 4:
    print("Error: 参数不足。需要 dir_x, dir_y, dir_z, save_path")
    sys.exit(1)

# 我们不再接收绝对坐标，而是接收一个“观察方向向量”
dir_x, dir_y, dir_z = float(args[0]), float(args[1]), float(args[2])
save_path = args[3]

if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# ==========================================
# 🧠 核心算法：自动计算场景包围盒与中心点
# ==========================================
min_coords = [float('inf'), float('inf'), float('inf')]
max_coords = [float('-inf'), float('-inf'), float('-inf')]
has_mesh = False

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        has_mesh = True
        # 获取物体所有顶点的全局坐标
        bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        for corner in bbox_corners:
            for i in range(3):
                min_coords[i] = min(min_coords[i], corner[i])
                max_coords[i] = max(max_coords[i], corner[i])

if not has_mesh:
    # 如果场景是空的，给个默认值
    min_coords, max_coords = [-1, -1, -1], [1, 1, 1]

# 计算场景的绝对几何中心
center = mathutils.Vector((
    (min_coords[0] + max_coords[0]) / 2,
    (min_coords[1] + max_coords[1]) / 2,
    (min_coords[2] + max_coords[2]) / 2
))

# 计算场景的包围球半径（中心到最远角落的距离）
radius = max([
    (mathutils.Vector((max_coords[0], max_coords[1], max_coords[2])) - center).length,
    (mathutils.Vector((min_coords[0], min_coords[1], min_coords[2])) - center).length
])

# 如果只有一个很小的物体，给一个最小的距离保障
radius = max(radius, 1.0)

# ==========================================
# 📷 摄像机自动安置逻辑
# ==========================================
cam_obj = bpy.data.objects.get("AgentCamera")
if not cam_obj:
    cam_data = bpy.data.cameras.new(name="AgentCamera")
    cam_obj = bpy.data.objects.new("AgentCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)

bpy.context.scene.camera = cam_obj

# 获取摄像机的水平视场角 (Field of View)，通常是基于传感器尺寸和焦距计算的
cam_data = cam_obj.data
fov = cam_data.angle

# 利用三角函数计算“要装下这个半径的球体，摄像机需要离多远”
# 加上 1.2 的系数作为留白安全边距（Padding），防止边缘贴得太紧
optimal_distance = (radius / math.sin(fov / 2.0)) * 1.2

# 计算摄像机坐标：中心点 + (归一化方向向量 * 最佳距离)
direction = mathutils.Vector((dir_x, dir_y, dir_z))
if direction.length == 0:
    direction = mathutils.Vector((1, 1, 1)) # 默认使用等轴测视角
direction.normalize()

cam_obj.location = center + (direction * optimal_distance)

# 强制让摄像机死盯着场景中心
target_name = "CameraTarget_Temp"
target = bpy.data.objects.get(target_name)
if not target:
    target = bpy.data.objects.new(target_name, None)
    bpy.context.collection.objects.link(target)
target.location = center

cam_obj.constraints.clear()
constraint = cam_obj.constraints.new(type='TRACK_TO')
constraint.target = target
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

# ==========================================
# 💡 上帝说要有光：添加自动照明
# ==========================================
light_name = "Agent_SunLight"
sun_obj = bpy.data.objects.get(light_name)

# 如果场景里没有咱们的专属太阳，就建一个
if not sun_obj:
    # 创建太阳光数据
    sun_data = bpy.data.lights.new(name=light_name, type='SUN')
    sun_data.energy = 3.0  # 调整光照强度 (Cycles下3.0是一个比较明亮的晴天)
    
    # 将光数据绑定到物体上并放入场景
    sun_obj = bpy.data.objects.new(name=light_name, object_data=sun_data)
    bpy.context.collection.objects.link(sun_obj)

# 太阳光的位置不重要，但【旋转角度】决定了光的方向
# 让光从斜上方 45 度角打下来，这样能产生好看的阴影，方便大模型识别立体感
sun_obj.rotation_euler = (math.radians(45), math.radians(0), math.radians(45))

# 为了防止阴影死黑，我们顺手把世界环境光（World Ambient）提亮一点
if bpy.data.worlds:
    world = bpy.data.worlds[0]
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.1, 0.1, 0.1, 1.0) # 给一点淡淡的灰色环境光

# ==========================================
# 🖼️ 渲染保存
# ==========================================
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.cycles.samples = 128
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 600
bpy.context.scene.render.filepath = save_path

# 更新场景以应用约束
bpy.context.view_layer.update()
bpy.ops.render.render(write_still=True)

bpy.data.objects.remove(target)
bpy.ops.wm.save_mainfile()
print(f"SUCCESS: 拍照完成！场景半径 {radius:.2f}m, 摄像机距离 {optimal_distance:.2f}m")