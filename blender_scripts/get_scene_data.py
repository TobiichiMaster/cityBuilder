import bpy
import json
import sys

# 确认当前处于对象模式
if bpy.context.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")

scene_data = {
    "objects":[] #键值对
}

#遍历场景中的物体
for obj in bpy.data.objects:
    #只关注场景中的网格模型，忽略摄像机、灯光等元素
    if obj.type == "MESH":
        # dimensions 是物体的绝对长宽高 (X, Y, Z)
        size_x, size_y, size_z = obj.dimensions
        loc_x, loc_y, loc_z = obj.location
        rot_x, rot_y, rot_z = obj.rotation_euler

        obj_info = {
            "name":obj.name,
            "location":[round(loc_x,3),round(loc_y,3),round(loc_z,3)],
            "rotation":[round(rot_x,3),round(rot_y,3),round(rot_z,3)],
            "scale":[round(obj.scale[0],3),round(obj.scale[1],3),round(obj.scale[2],3)],
            "dimensions":[round(size_x,3),round(size_y,3),round(size_z,3)]
        }
        scene_data["objects"].append(obj_info)

# 将scene_data字典转为 JSON 字符串，并通过 print 输出给 MCP 的 capture_output 捕获
# 加上特定的前缀，方便我们在 MCP 端剥离掉 Blender 启动时自带的乱七八糟的系统输出
print("===SCENE_DATA_START===")
print(json.dumps(scene_data, ensure_ascii=False, indent=2))
print("===SCENE_DATA_END===")