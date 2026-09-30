#!/usr/bin/env bash
# Fault injection helpers for exception/recovery testing.
# Usage: ./inject_fault.sh <remove_target|add_obstacle|gripper_fail|timeout>
set -euo pipefail

MODE="${1:-remove_target}"
source /opt/ros/humble/setup.bash
if [ -f install/setup.bash ]; then source install/setup.bash; fi

case "$MODE" in
  remove_target)
    echo "Inject: move/hide a target by republishing empty poses (sim)"
    ros2 topic pub --once /target_poses intellisort_interfaces/msg/TargetPoseArray "{header: {frame_id: base_link}, poses: []}"
    ;;
  add_obstacle)
    echo "Inject: publishing extra collision via planning_scene diff"
    ros2 topic pub --once /planning_scene moveit_msgs/msg/PlanningScene "{
      is_diff: true,
      world: {collision_objects: [{
        id: 'fault_block', header: {frame_id: base_link},
        primitives: [{type: 1, dimensions: [0.1, 0.1, 0.2]}],
        primitive_poses: [{position: {x: 0.35, y: -0.15, z: 0.85}, orientation: {w: 1.0}}],
        operation: 0
      }]}
    }"
    ;;
  gripper_fail)
    echo "Inject: stop gripper feedback path (documented manual step)"
    echo "  -> ros2 lifecycle set /gripper_server deactivate  (if lifecycle)"
    echo "  -> or kill gripper_server and observe GRASP_FAIL recovery"
    ;;
  timeout)
    echo "Inject: pause detectors to force TIMEOUT / DETECT_FAIL"
    echo "  -> kill object_detection or publish empty /detections"
    ros2 topic pub --once /detections intellisort_interfaces/msg/DetectionArray "{header: {frame_id: camera_color_optical_frame}, detections: []}"
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 2
    ;;
esac

echo "Observe: ros2 topic echo /exception_events"
echo "Observe: ros2 topic echo /recovery_events"
