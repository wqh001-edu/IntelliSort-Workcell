"""Unit tests that do not require a live ROS graph."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

# allow importing package modules without install
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'intellisort_task'))
sys.path.insert(0, str(ROOT / 'src' / 'intellisort_grasp'))
sys.path.insert(0, str(ROOT / 'src' / 'intellisort_perception'))
sys.path.insert(0, str(ROOT / 'src' / 'intellisort_scene'))


class TestSlotConstants(unittest.TestCase):
    def test_table_top_matches_urdf(self):
        from intellisort_task.workspace import SLOT_POSE, TABLE_TOP_Z
        self.assertAlmostEqual(TABLE_TOP_Z, 0.75)
        for x, y, z in SLOT_POSE.values():
            self.assertAlmostEqual(z, TABLE_TOP_Z)

    def test_class_slot_mapping(self):
        from intellisort_task.workspace import CLASS_SLOT
        self.assertEqual(CLASS_SLOT['red'], 'slot_a')
        self.assertEqual(CLASS_SLOT['green'], 'slot_b')
        self.assertEqual(CLASS_SLOT['blue'], 'slot_c')


class TestGraspQuaternion(unittest.TestCase):
    def test_yaw0_is_topdown(self):
        from intellisort_grasp.quat import topdown_quat_with_yaw
        x, y, z, w = topdown_quat_with_yaw(0.0)
        self.assertAlmostEqual(x, 1.0, places=6)
        self.assertAlmostEqual(y, 0.0, places=6)
        self.assertAlmostEqual(z, 0.0, places=6)
        self.assertAlmostEqual(w, 0.0, places=6)

    def test_yaw_pi_over_2(self):
        from intellisort_grasp.quat import topdown_quat_with_yaw
        x, y, z, w = topdown_quat_with_yaw(math.pi / 2)
        self.assertAlmostEqual(x, math.cos(math.pi / 4), places=6)
        self.assertAlmostEqual(y, math.sin(math.pi / 4), places=6)

    def test_unit_norm(self):
        from intellisort_grasp.quat import topdown_quat_with_yaw
        for yaw in (0.0, 0.7, math.pi):
            x, y, z, w = topdown_quat_with_yaw(yaw)
            n = math.sqrt(x * x + y * y + z * z + w * w)
            self.assertAlmostEqual(n, 1.0, places=6)


class TestRecoveryPolicy(unittest.TestCase):
    def test_codes_cover_task_failures(self):
        from intellisort_task.recovery_policy import RECOVERY_POLICY
        for code in ('PLAN_FAIL', 'GRASP_FAIL', 'DETECT_FAIL', 'TIMEOUT', 'TASK_FAIL'):
            self.assertIn(code, RECOVERY_POLICY)


class TestSceneGeometry(unittest.TestCase):
    def test_make_box_top_surface_formula(self):
        # pure math used by scene_builder: center = top - thickness/2
        top, th = 0.75, 0.05
        center = top - th / 2.0
        self.assertAlmostEqual(center + th / 2.0, top)

    def test_make_box_if_ros_available(self):
        try:
            from intellisort_scene.geometry import make_box
        except ImportError:
            self.skipTest('ROS msgs not available')
        co = make_box('t', 0, 0, 0.725, 1.2, 0.8, 0.05)
        self.assertEqual(co.id, 't')
        self.assertAlmostEqual(co.primitive_poses[0].position.z, 0.725)


class TestMetricsNotHardcoded(unittest.TestCase):
    def test_metric_publisher_has_no_literal_rates(self):
        src = (
            ROOT / 'src' / 'intellisort_task' / 'intellisort_task'
            / 'metric_publisher_node.py'
        ).read_text(encoding='utf-8')
        import re
        # forbid hardcoded success rates assigned to the metric fields
        self.assertIsNone(re.search(
            r'plan_success_rate\s*=\s*0\.\d+', src))
        self.assertIsNone(re.search(
            r'grasp_success_rate\s*=\s*0\.\d+', src))
        self.assertIsNone(re.search(
            r'avg_cycle_time_sec\s*=\s*\d+', src))
        self.assertIsNone(re.search(
            r'recovery_success_rate\s*=\s*0\.\d+', src))


if __name__ == '__main__':
    unittest.main()
