# 09 · 硬件设计与迁移

## 现状（与代码一致）

`mode_manager` 提供 `/set_mode` **模式标记服务**（sim/real 参数记录）。  
**驱动切换需要改 launch / 参数**，不是一键热切换。完整 adapter 层是后续升级。

## 三档方案

| 档位 | 预算 | 配置 |
|------|------|------|
| 入门 | ¥0.6–1.2万 | 仿真优先 |
| **推荐** | ¥6–12万 | xArm6 + 电动夹爪 + D435 + 工控机 |
| 高配 | ¥18–35万 | xArm7/UR5e + 力控预留 |

## 迁移清单（接口已预留）

1. `use_sim_time:=false`  
2. 安装并启用 `xarm_ros2`，替换 hardware plugin  
3. 相机换成 `realsense2_camera`  
4. 手眼标定 → 更新 `pose_estimator` 的 `camera_pos/look_at`  
5. 速度缩放 0.2–0.3  
6. 急停与软限位  
7. 先空跑再抓取  

## 上层尽量不改

任务逻辑、`/target_poses`、`/gripper_command`、MoveIt 规划请求、Task/Action 名称。
