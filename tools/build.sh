#!/usr/bin/env bash
# Build the IntelliSort workspace (run from repo root)
set -e
source /opt/ros/humble/setup.bash
cd "$(dirname "$0")/.."
rosdep install --from-paths src -y --ignore-src || true
colcon build --symlink-install
echo "Build done. source install/setup.bash"
