#!/usr/bin/env bash
# Full demo launch helper
set -e
source /opt/ros/humble/setup.bash
cd "$(dirname "$0")/.."
if [ -f install/setup.bash ]; then
  # shellcheck disable=SC1091
  source install/setup.bash
fi
exec ros2 launch intellisort_bringup demo.launch.py use_rviz:=true
