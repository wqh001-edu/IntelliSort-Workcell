# 08 · 仿真环境

## 工作站构成

- 六轴臂 + 夹爪 + 相机  
- 工作台（碰撞体）  
- 来料区 4 个彩色零件（Gazebo world 自由体）  
- 分拣料位 slot_a/b/c  
- 障碍块  
- 平行光  

## 文件

- 世界：`intellisort_gazebo/worlds/intellisort_workcell.world`
- 启动：`intellisort_gazebo/launch/gazebo_workcell.launch.py`
- 模型：`intellisort_description/urdf/*`

## 启动

```bash
ros2 launch intellisort_bringup demo.launch.py
```

## 注意

- 使用 **Gazebo Classic 11**（Humble 默认）  
- `use_sim_time: true` 必须一致  
- 零件在 world 中，不在机器人 URDF 中（避免 free joint 问题）
