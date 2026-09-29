# 05 · 运动规划

## 链路

PlanningScene → MoveIt2 → OMPL (RRTConnect) → 碰撞检查 → 时间参数化 → 执行

## 配置位置

- SRDF：`intellisort_moveit_config/srdf/isc_arm.srdf`
- OMPL：`config/ompl_planning.yaml`
- IK：`config/kinematics.yaml`（KDL）
- 控制器：`config/moveit_controllers.yaml`
- 限位：`config/joint_limits.yaml`

## 规划组

| 组名 | 内容 |
|------|------|
| `arm` | joint1..joint6 |
| `gripper` | 两指 |
| `arm_with_gripper` | 组合 |

命名位姿：`home`、`ready`

## 调参优先级

1. 碰撞体准确性  
2. planning_time / attempts  
3. 速度缩放与平滑  

## 验收

标准场景规划成功率 ≥ 95%；抓取过程 0 碰撞。
