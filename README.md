# 智拣柔性工作站（IntelliSort Workcell）

面向多品种零件的视觉引导柔性分拣与上下料系统  
Vision-Guided Flexible Part Sorting & Machine Tending System

**项目代号**：`ISC-1`  
**技术栈**：Ubuntu 22.04 · ROS2 Humble · MoveIt2 · Gazebo Classic · ros2_control  
**仓库**：https://github.com/wqh001-edu/IntelliSort-Workcell

---

## 1. 项目是什么

一台视觉引导的六轴机械臂工作站，完成：

> 多品种零件识别 → 位姿估计 → 抓取规划 → MoveIt2 避障运动 → 按类分拣/上下料 → 结果确认 → 异常自动恢复

深度来自完整的机器人系统工程（感知 + 决策 + 规划 + 控制 + 仿真 + 硬件迁移 + 异常处理），而不是单点算法堆砌。

---

## 2. 快速开始（Ubuntu 22.04 + ROS2 Humble 虚拟机）

### 2.1 依赖

```bash
sudo apt update
sudo apt install -y \
  ros-humble-desktop \
  ros-humble-moveit \
  ros-humble-moveit-resources \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control \
  ros-humble-xacro \
  ros-humble-cv-bridge \
  ros-humble-vision-msgs \
  python3-opencv python3-numpy
```

### 2.2 获取代码并编译

```bash
mkdir -p ~/intellisort_ws/src
cd ~/intellisort_ws/src
git clone https://github.com/wqh001-edu/IntelliSort-Workcell.git
# 若仓库根目录就是 src 内容，可直接把包放进 src/

cd ~/intellisort_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src -y --ignore-src || true
colcon build --symlink-install
source install/setup.bash
```

> 如果你把整个仓库 clone 到 `~/IntelliSort-Workcell`，仓库内已有 `src/`，也可以：
>
> ```bash
> cd ~/IntelliSort-Workcell
> source /opt/ros/humble/setup.bash
> colcon build --symlink-install
> source install/setup.bash
> ```

### 2.3 一键启动仿真系统

```bash
source install/setup.bash
ros2 launch intellisort_bringup demo.launch.py use_rviz:=true
```

### 2.4 合成目标（保证 Demo 可跑通）

另开终端：

```bash
source install/setup.bash
ros2 run intellisort_demo synthetic_targets
```

### 2.5 执行分拣任务

```bash
source install/setup.bash
ros2 run intellisort_demo run_pick_demo
# 或手动发 action
ros2 action send_goal /execute_task intellisort_interfaces/action/ExecuteTask \
  "{task_id: demo1, object_classes: [red, green, blue], max_targets: 3, enable_recovery: true}"
```

### 2.6 仅查看模型

```bash
ros2 launch intellisort_description display.launch.py
```

---

## 3. 系统架构（简图）

```text
┌─────────────────────────────────────────────────────────┐
│  展示层：HTML 门户 / RViz2 / Gazebo                       │
├─────────────────────────────────────────────────────────┤
│  任务层：task_manager（行为树） + supervisor（异常恢复）   │
├─────────────────────────────────────────────────────────┤
│  感知抓取：detector → pose_estimator → grasp_planner      │
├─────────────────────────────────────────────────────────┤
│  运动规划：scene_builder → MoveIt2 move_group             │
├─────────────────────────────────────────────────────────┤
│  控制执行：ros2_control → arm/gripper controllers         │
├─────────────────────────────────────────────────────────┤
│  硬件抽象：mode_manager（sim | xarm | real）               │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Workspace 包一览

| Package | 职责 |
|---------|------|
| `intellisort_interfaces` | 自定义 msg/srv/action |
| `intellisort_description` | URDF/Xacro 机器人+工作站+相机 |
| `intellisort_control` | ros2_control 控制器配置 |
| `intellisort_gazebo` | Gazebo 世界与零件模型 |
| `intellisort_moveit_config` | SRDF / OMPL / kinematics / controllers |
| `intellisort_perception` | 检测、位姿、工作区状态 |
| `intellisort_grasp` | 抓取候选生成 |
| `intellisort_scene` | PlanningScene 同步 |
| `intellisort_task` | 任务编排、夹爪服务、异常、指标 |
| `intellisort_hw_abstraction` | sim/real 模式管理 |
| `intellisort_bringup` | 一键启动 |
| `intellisort_demo` | 合成目标与演示脚本 |

---

## 5. 常用命令

```bash
# 节点图
ros2 node list

# 目标位姿
ros2 topic echo /target_poses

# 任务状态
ros2 topic echo /task_status

# 异常事件
ros2 topic echo /exception_events

# 切换模式（仿真/实物）
ros2 service call /set_mode intellisort_interfaces/srv/SetMode "{mode: sim, enable_task: true}"
```

---

## 6. 文档

| 文档 | 内容 |
|------|------|
| [`docs/00_project_overview.md`](docs/00_project_overview.md) | 项目总览 |
| [`docs/01_system_architecture.md`](docs/01_system_architecture.md) | 系统架构 |
| [`docs/02_ros2_architecture.md`](docs/02_ros2_architecture.md) | ROS2 节点与接口 |
| [`docs/03_robot_arm.md`](docs/03_robot_arm.md) | 机械臂与模型 |
| [`docs/04_perception.md`](docs/04_perception.md) | 感知 |
| [`docs/05_motion_planning.md`](docs/05_motion_planning.md) | 运动规划 |
| [`docs/06_grasping.md`](docs/06_grasping.md) | 抓取 |
| [`docs/07_task_planning.md`](docs/07_task_planning.md) | 任务与行为树 |
| [`docs/08_simulation.md`](docs/08_simulation.md) | 仿真工作站 |
| [`docs/09_hardware.md`](docs/09_hardware.md) | 硬件迁移 |
| [`docs/10_testing.md`](docs/10_testing.md) | 测试与验收 |
| [`docs/11_demo.md`](docs/11_demo.md) | 最终 Demo |
| [`docs/12_troubleshooting.md`](docs/12_troubleshooting.md) | 排障 |
| [`docs/13_html_demo_system.md`](docs/13_html_demo_system.md) | HTML 演示系统 |

打开根目录 [`index.html`](index.html) 可浏览交互式项目门户（架构、学习卡片、阶段验收）。

---

## 7. 硬件迁移原则

上层**尽量不改**：任务逻辑、感知接口、MoveIt 规划、行为树、Topic/Action 名称。  
只替换：`hardware interface`、controller 参数、相机/机械臂驱动、标定与限位。

推荐实物：**UFACTORY xArm6** + 电动夹爪 + RealSense D435（与仿真同构）。

---

## 8. 开发原则

1. 不为了高级而复杂  
2. 仿真和硬件兼容  
3. 模块化  
4. 可调试 / 可测试 / 可演示 / 可解释  

---

## 9. License

MIT
