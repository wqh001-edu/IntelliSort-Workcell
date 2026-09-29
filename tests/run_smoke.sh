#!/usr/bin/env bash
# Smoke tests after bringup (run in a terminal with workspace sourced)
set -e
echo "[1] node list"
ros2 node list || true
echo "[2] detections"
timeout 5 ros2 topic echo /detections --once || echo "no detections yet"
echo "[3] target_poses"
timeout 5 ros2 topic echo /target_poses --once || echo "no poses yet (start synthetic_targets)"
echo "[4] task_status"
timeout 3 ros2 topic echo /task_status --once || true
echo "Smoke done. For full demo see docs/11_demo.md"
