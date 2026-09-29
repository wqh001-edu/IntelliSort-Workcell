# 03 · 机械臂模型

## 选型结论

| 角色 | 型号 |
|------|------|
| 仿真 | 自包含 6-DOF `isc_arm`（xArm6 尺度，无外部依赖） |
| 实物首选 | UFACTORY **xArm6**（`xarm_ros2`，与上层接口兼容） |
| 备选 | UR5e（预算充足） |

## 模型文件

- `intellisort_description/urdf/isc_arm.urdf.xacro` — 臂+夹爪+相机
- `intellisort_description/urdf/isc_arm.gazebo.xacro` — Gazebo 插件与相机
- `intellisort_description/urdf/workstation.urdf.xacro` — 工作台/料位/障碍
- `intellisort_description/urdf/isc_workcell.urdf.xacro` — 总装

## 关节

| 关节 | 类型 | 范围 |
|------|------|------|
| joint1 | revolute Z | ±180° |
| joint2 | revolute Y | ±100° |
| joint3 | revolute Y | ±120° |
| joint4 | revolute Z | ±180° |
| joint5 | revolute Y | ±120° |
| joint6 | revolute Z | ±360° |
| gripper_left/right | prismatic | 0–0.04 m |

## 坐标系

- `tool0`：法兰  
- `tcp_link`：夹爪 TCP  
- `camera_color_optical_frame`：相机光学系  

## 验证

```bash
ros2 launch intellisort_description display.launch.py
```
