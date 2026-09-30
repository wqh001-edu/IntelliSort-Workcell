"""Workspace constants shared by task_manager and tests (no ROS deps)."""

TABLE_TOP_Z = 0.75

SLOT_POSE = {
    'slot_a': (0.35, 0.28, TABLE_TOP_Z),
    'slot_b': (0.48, 0.12, TABLE_TOP_Z),
    'slot_c': (0.48, -0.12, TABLE_TOP_Z),
}

CLASS_SLOT = {
    'red': 'slot_a',
    'green': 'slot_b',
    'blue': 'slot_c',
    'yellow': 'slot_a',
}

APPROACH_HEIGHT = 0.12
GRASP_OFFSET = 0.015
PLACE_CLEARANCE = 0.04
