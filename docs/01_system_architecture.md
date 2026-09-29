# 01 · 系统架构

## 分层

```text
L5 展示与学习   HTML 门户 / RViz / Gazebo
L4 任务决策     task_manager · supervisor · metrics
L3 感知抓取     detector · pose_estimator · grasp_planner
L2 运动规划     scene_builder · MoveIt2
L1 控制执行     ros2_control · arm/gripper controllers
L0 硬件抽象     mode_manager · sim/real drivers
```

## 数据流

1. 相机图像 → `object_detection` → `/detections`
2. 深度 + 检测 → `pose_estimator` → `/target_poses`
3. 位姿 → `grasp_planner` → `/grasp_candidates`
4. 位姿/障碍 → `scene_builder` → `/planning_scene`
5. 任务层选择目标 → MoveIt2 规划执行 → 夹爪 → 放置确认

## sim/real 解耦

**不变**：任务树、检测/位姿/抓取接口、MoveIt 请求类型、Topic/Action 名称。  
**可换**：hardware interface、controller 参数、相机/机械臂驱动、标定、限位。

配置见 `intellisort_hw_abstraction/config/hw_mode.yaml`。
