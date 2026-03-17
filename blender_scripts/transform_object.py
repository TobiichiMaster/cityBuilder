import bpy
import sys

# 解析 MCP Server 传递过来的命令行参数
argv = sys.argv
if "--" not in argv:
    print("Error: 未找到脚本参数分隔符'--'")
    sys.exit(1)

# 获取 '--' 之后的参数
args = argv[argv.index('--') + 1:]

if len(args) < 5:
    print("Error: 参数不足。需要：行动类型，name，x，y，z")
    sys.exit(1)

option_type = args[0].upper()
obj_name = args[1]

# 确保在正确的上下文对象中操作
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# 获取物体
obj = bpy.data.objects.get(obj_name)
if not obj: 
    print(f"Error: 在场景中找不到名为 '{obj_name}' 的物体，请检查名字是否正确。")
    sys.exit(1)     

# 执行形变操作
if option_type == "MOVE":
    loc_x, loc_y, loc_z = float(args[2]), float(args[3]), float(args[4])
    obj.location = (loc_x, loc_y, loc_z)
    
elif option_type == "ROTATION":
    # 注意：Agent 传来的可能是角度（比如 90 度），如果发现旋转异常，
    # 后期需要导入 math 模块，用 math.radians() 把角度转成弧度
    rot_x, rot_y, rot_z = float(args[2]), float(args[3]), float(args[4])
    obj.rotation_euler = (rot_x, rot_y, rot_z)
    
elif option_type == "SCALE":
    # 既然架子搭好了，顺手把 SCALE 也加上吧！
    scale_x, scale_y, scale_z = float(args[2]), float(args[3]), float(args[4])
    obj.scale = (scale_x, scale_y, scale_z)
    
else:
    print(f"Error: 不存在的操作类型: {option_type}")
    sys.exit(1)

# 保存工程
bpy.ops.wm.save_mainfile()
print(f"Success: 成功对 {obj_name} 执行了 {option_type} 操作，场景已保存。")