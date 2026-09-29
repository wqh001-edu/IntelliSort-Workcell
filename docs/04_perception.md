# 04 · 感知系统

## 流水线

相机 → 桌面 ROI → **目标检测** → **位姿估计** → `/target_poses`

## 目标检测（`detector_node`）

- **这是什么**：从 RGB 图像定位并分类零件  
- **为什么需要**：后续位姿/抓取/任务都依赖“哪里有什么”  
- **输入**：`/camera/color/image_raw`  
- **输出**：`/detections`  
- **算法**：HSV 颜色分割 + 形态学 + 轮廓（红/绿/蓝/黄）  
- **代码**：`intellisort_perception/intellisort_perception/detector_node.py`  
- **运行**：`ros2 run intellisort_perception detector_node`  
- **验证**：RViz/图像叠加检测框，置信度阈值过滤遮挡

## 位姿估计（`pose_estimator_node`）

- **这是什么**：2D 检测 + 深度/工作区映射 → `PoseStamped`  
- **为什么需要**：抓取与碰撞检查需要 3D 位姿  
- **输入**：`/detections`、深度、CameraInfo  
- **输出**：`/target_poses`  
- **算法**：像素中心映射到工作台平面（可选手眼标定替换）  
- **代码**：`pose_estimator_node.py`  
- **验证**：与 `synthetic_targets` 对比误差

## 合成目标（演示备用）

```bash
ros2 run intellisort_demo synthetic_targets
```

与 Gazebo 世界中零件位置对齐，保证任务链路可独立验证。
