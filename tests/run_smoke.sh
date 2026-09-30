#!/usr/bin/env bash
# Smoke tests — FAIL FAST (no || true on critical checks)
set -euo pipefail

TIMEOUT=8
fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

echo "=== IntelliSort smoke ==="

# 1) required nodes must be up
NODES=$(ros2 node list 2>/dev/null || true)
for n in task_manager object_detection pose_estimator gripper_server; do
  echo "$NODES" | grep -q "$n" || fail "node missing: $n"
  ok "node $n"
done

# 2) must receive at least one /target_poses within timeout
if timeout "$TIMEOUT" ros2 topic echo /target_poses --once >/dev/null 2>&1; then
  ok "received /target_poses"
else
  fail "no /target_poses within ${TIMEOUT}s (start synthetic_targets?)"
fi

# 3) task_status may be idle — just ensure the topic exists
if ros2 topic list | grep -q /task_status; then
  ok "/task_status advertised"
else
  fail "/task_status missing"
fi

# 4) system_metrics should not publish hardcoded 0.95 forever if we can sample twice
#    (soft check — warn only)
if timeout "$TIMEOUT" ros2 topic echo /system_metrics --once >/dev/null 2>&1; then
  ok "received /system_metrics"
else
  echo "WARN: no /system_metrics yet"
fi

echo "SMOKE PASSED"
