# 12 · 排障指南

## 编译失败

- 确认 `source /opt/ros/humble/setup.bash`  
- 缺消息包：`sudo apt install ros-humble-<pkg>`  
- 清理重建：`rm -rf build install log && colcon build`

## Gazebo 起不来

- 无显示：`export LIBGL_ALWAYS_SOFTWARE=1`（虚拟机）  
- 插件找不到：确认 `gazebo_ros2_control` 已安装  
- 世界空：检查 `world` 路径

## 控制器未加载

```bash
ros2 control list_controllers
ros2 control load_controller --set-state active arm_controller
```

## move_group 规划失败

- 先 `synthetic_targets` 保证有目标  
- 降低速度缩放  
- 检查 SRDF 禁用碰撞对  
- 增加 `allowed_planning_time`

## 无 `/target_poses`

```bash
ros2 topic hz /camera/color/image_raw
ros2 topic echo /detections --once
```

可先用 `synthetic_targets` 绕过相机链路。

## 任务卡住

```bash
ros2 topic echo /task_status
ros2 topic echo /exception_events
```

## 常用

```bash
ros2 node list
ros2 topic list
ros2 action list
tf2_tools view_frames
```
