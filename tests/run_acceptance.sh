#!/usr/bin/env bash
# Run one pick-and-place demo (requires demo.launch.py + synthetic_targets)
set -e
source /opt/ros/humble/setup.bash
# workspace overlay if present
if [ -f install/setup.bash ]; then
  # shellcheck disable=SC1091
  source install/setup.bash
fi
ros2 run intellisort_demo run_pick_demo
