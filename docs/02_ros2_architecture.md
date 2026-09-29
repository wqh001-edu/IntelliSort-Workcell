# 02 · ROS2 架构

## 主要节点

| 节点 | Package | 说明 |
|------|---------|------|
| `robot_state_publisher` | description | TF / URDF |
| `controller_manager` | control | ros2_control |
| `move_group` | moveit_config | 规划执行 |
| `object_detection` | perception | 颜色检测 |
| `pose_estimator` | perception | 目标位姿 |
| `workspace_state` | perception | 料位占用 |
| `grasp_planner` | grasp | 抓取候选 |
| `scene_builder` | scene | PlanningScene |
| `task_manager` | task | 任务编排 |
| `gripper_server` | task | `/gripper_command` |
| `supervisor` | task | 异常恢复 |
| `metric_publisher` | task | 指标 |
| `mode_manager` | hw_abstraction | sim/real |
| `synthetic_targets` | demo | 合成目标 |

## Topic

| Topic | 类型 |
|-------|------|
| `/camera/color/image_raw` | `sensor_msgs/Image` |
| `/detections` | `intellisort_interfaces/DetectionArray` |
| `/target_poses` | `intellisort_interfaces/TargetPoseArray` |
| `/grasp_candidates` | `intellisort_interfaces/GraspCandidateArray` |
| `/task_status` | `intellisort_interfaces/TaskStatus` |
| `/exception_events` | `intellisort_interfaces/ExceptionEvent` |
| `/system_metrics` | `intellisort_interfaces/SystemMetrics` |

## Service / Action

| 接口 | 类型 |
|------|------|
| `/gripper_command` | `GripperCommand.srv` |
| `/set_mode` | `SetMode.srv` |
| `/get_workspace_state` | `GetWorkspaceState.srv` |
| `/pick_place` | `PickPlace.action` |
| `/execute_task` | `ExecuteTask.action` |
| `/recovery` | `Recovery.action` |

## TF

```text
world → base_link → link1..link6 → tool0 → gripper_link → tcp_link
world → camera_stand_link → camera_link → camera_color_optical_frame
world → table_link → table_top
```
