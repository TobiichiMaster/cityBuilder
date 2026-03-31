import bpy
import sys
import math
import mathutils

# === 1. 解析参数 ===
argv = sys.argv
if "--" not in argv:
    sys.exit(1)

args = argv[argv.index("--") + 1:]
# 修改为接收：view_type, save_path
if len(args) < 2:
    print("Error: 参数不足。需要 view_type (TOP/FRONT/SIDE/ISO), save_path")
    sys.exit(1)

view_type = args[0].upper()
save_path = args[1]

# 视角向量映射（你可以根据需要调整角度）
VIEW_VECTORS = {
    "TOP": (0, 0, 1),
    "FRONT": (0, -1, 0.15),  # 稍微带一点仰角，能看清地面的接触面
    "SIDE": (1, 0, 0.15),
    "ISO": (1, -1, 0.8),      # 经典的斜 45 度透视
    "LEVEL": (0, -1, 0),     # 【纯水平视角】地面将变成一条绝对的直线，低于此线的像素100%是穿模
    "UNDER": (0.7, -1, -0.3) # 【地下仰视角】从地平线下方往上看，直接看哪些物体的底座“漏”到了地下
}

# 如果传入的是 "DIR:x,y,z" 格式，则支持自定义向量
if view_type.startswith("DIR:"):
    try:
        parts = view_type.replace("DIR:", "").split(",")
        dir_vec = (float(parts[0]), float(parts[1]), float(parts[2]))
    except:
        dir_vec = VIEW_VECTORS["ISO"]
else:
    dir_vec = VIEW_VECTORS.get(view_type, VIEW_VECTORS["TOP"])

if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# === 2. 核心算法：自动计算场景包围盒与中心点 ===
min_coords = [float('inf')] * 3
max_coords = [float('-inf')] * 3
has_mesh = False

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # 【核心修复】：在计算取景范围时，忽略名字里带有 ground 或 plane 的地面物体
        obj_name = obj.name.lower()
        if "ground" in obj_name or "plane" in obj_name:
            continue
            
        has_mesh = True
        bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        for corner in bbox_corners:
            for i in range(3):
                min_coords[i] = min(min_coords[i], corner[i])
                max_coords[i] = max(max_coords[i], corner[i])

if not has_mesh:
    # 如果全被过滤掉了（比如场景里只有地面），给个默认小范围
    min_coords, max_coords = [-5, -5, -2], [5, 5, 5]

center = mathutils.Vector(((min_coords[0] + max_coords[0]) / 2, (min_coords[1] + max_coords[1]) / 2, (min_coords[2] + max_coords[2]) / 2))
# 取景半径计算
radius = max([(mathutils.Vector(max_coords) - center).length, (mathutils.Vector(min_coords) - center).length, 1.0])
# === 3. 摄影机安置逻辑 (优化针对侧视点的观察) ===
cam_obj = bpy.data.objects.get("AgentCamera")
if not cam_obj:
    cam_data = bpy.data.cameras.new(name="AgentCamera")
    cam_obj = bpy.data.objects.new("AgentCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)

bpy.context.scene.camera = cam_obj
fov = cam_obj.data.angle
# 如果是看穿模的专用视角，我们不需要那么多边缘留白，直接怼脸拍！
padding = 1.05 if view_type in ["LEVEL", "UNDER"] else 1.25
optimal_distance = (radius / math.sin(fov / 2.0)) * padding

direction = mathutils.Vector(dir_vec).normalized()
cam_obj.location = center + (direction * optimal_distance)

# 确保目标点在中心
target_name = "CameraTarget_Temp"
target = bpy.data.objects.get(target_name) or bpy.data.objects.new(target_name, None)
if target.name not in bpy.context.collection.objects:
    bpy.context.collection.objects.link(target)
target.location = center

# 重新绑定约束
cam_obj.constraints.clear()
track = cam_obj.constraints.new(type='TRACK_TO')
track.target = target
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

# === 4. 增强光照：无死角质检照明系统 ===

# 1. 天上的主光源 (照亮地上正常部分)
sun_light = bpy.data.lights.get("Agent_SunLight") or bpy.data.lights.new("Agent_SunLight", 'SUN')
sun_light.energy = 5.0
sun_obj = bpy.data.objects.get("Agent_SunLight") or bpy.data.objects.new("Agent_SunLight", sun_light)
if sun_obj.name not in bpy.context.collection.objects:
    bpy.context.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(50), 0, math.radians(45))

# 2. 地下的副光源 (常驻开启：无论什么视角，强制照亮穿模到地下的部分)
under_light = bpy.data.lights.get("Agent_UnderLight") or bpy.data.lights.new("Agent_UnderLight", 'SUN')
under_light.energy = 6.0  # 能量稍微大一点，确保地下的细节清晰锐利
under_obj = bpy.data.objects.get("Agent_UnderLight") or bpy.data.objects.new("Agent_UnderLight", under_light)
if under_obj.name not in bpy.context.collection.objects:
    bpy.context.collection.objects.link(under_obj)
# 将光线沿 X 轴旋转 180 度，让光线完全垂直向上发射！
under_obj.rotation_euler = (math.radians(180), 0, 0)

# 3. 提亮全局环境光，消灭死黑死白的对比度丢失
if bpy.data.worlds:
    bg_node = bpy.data.worlds[0].node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.5, 0.5, 0.5, 1.0)

# 渲染设置 (保持 Cycles 加速)
# === 渲染画质与分辨率升级 ===
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'

# 1. 提升采样率 (降低画面的“雪花噪点”，让边缘更锐利)
bpy.context.scene.cycles.samples = 256 

# 2. 提升物理分辨率 (推荐 1920x1080，如果需要更清晰可以改为 2560x1440)
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080

# 3. 确保渲染比例是 100%
bpy.context.scene.render.resolution_percentage = 100 

# 4. (可选) 开启 Cycles 内置的 AI 降噪，画面会瞬间变得极其干净！
bpy.context.scene.cycles.use_denoising = True 

bpy.context.scene.render.filepath = save_path
bpy.context.view_layer.update()
bpy.ops.render.render(write_still=True)

print(f"SUCCESS: {view_type} 视角拍照完成")