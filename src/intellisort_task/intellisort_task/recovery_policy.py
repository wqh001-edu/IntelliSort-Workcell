"""Recovery policy table (no ROS deps — unit-testable)."""

RECOVERY_POLICY = {
    'DETECT_FAIL': ('skip-target', 'RECOVERABLE'),
    'POSE_LOW': ('re-perceive', 'RECOVERABLE'),
    'PLAN_FAIL': ('replan', 'RECOVERABLE'),
    'GRASP_FAIL': ('re-grasp', 'RECOVERABLE'),
    'COLLISION': ('clear-scene-replan', 'RECOVERABLE'),
    'TIMEOUT': ('abort-cycle', 'FATAL'),
    'COMM': ('abort-cycle', 'FATAL'),
    'TASK_FAIL': ('skip-target', 'RECOVERABLE'),
    'PICK_PLACE_FAIL': ('skip-target', 'RECOVERABLE'),
}
