#!/usr/bin/env bash
# Acceptance: requires demo stack already running OR starts synthetic + pick.
# Exit non-zero if pick demo fails.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

source /opt/ros/humble/setup.bash
if [ -f install/setup.bash ]; then
  # shellcheck disable=SC1091
  source install/setup.bash
fi

echo "=== Acceptance: run_pick_demo ==="
set +e
ros2 run intellisort_demo run_pick_demo
CODE=$?
set -e

if [ "$CODE" -ne 0 ]; then
  echo "ACCEPTANCE FAILED: run_pick_demo exit=$CODE" >&2
  exit "$CODE"
fi

echo "ACCEPTANCE PASSED"
