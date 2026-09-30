# 04 · 感知系统

## 流水线

相机 → **目标检测** → **位姿估计** → `/target_poses`

## 目标检测（`detector_node`）— 已实现

- HSV 颜色分割（红/绿/蓝/黄）+ 形态学
- 输出 `/detections`（框、类别、置信度）
- `track_id` 字段目前 **未使用**（预留）

## 位姿估计（`pose_estimator_node`）— 射线-桌面求交

- **相机模型**：CameraInfo 的 K（无则用 640×480 默认内参）
- **外参**：`camera_pos` + `camera_look_at`（默认对齐 URDF 安装位）
- **算法**：像素→光线→与桌面平面 `z=table_z` 求交点（base_link）
- **失败**：求交失败 → 发 `POSE_LOW` 并降低 confidence
- 手眼标定后只需改参数，无需改算法

```yaml
camera_pos: [0.55, 0.35, 0.95]
camera_look_at: [0.35, -0.12, 0.75]
table_z: 0.75
```

## 合成目标（演示/验收）

```bash
ros2 run intellisort_demo synthetic_targets
# 默认 disable_grasp_pub:=true，不与 grasp_planner 抢 /grasp_candidates
# publish_once:=true 可避免已抓走目标被反复重发
```

## 代码

- `intellisort_perception/detector_node.py`
- `intellisort_perception/pose_estimator_node.py`
- `intellisort_demo/synthetic_targets.py`
