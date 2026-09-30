"""Pure grasp orientation math (no ROS deps)."""
from __future__ import annotations

import math


def topdown_quat_with_yaw(yaw: float) -> tuple[float, float, float, float]:
    """Quaternion for tool-Z-down + yaw about world Z.

    q = qz(yaw) ⊗ (1,0,0,0)  →  (cos(yaw/2), sin(yaw/2), 0, 0)
    """
    half = yaw * 0.5
    return math.cos(half), math.sin(half), 0.0, 0.0
