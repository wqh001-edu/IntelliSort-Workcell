"""MoveIt2 action helpers used by the task manager."""
from __future__ import annotations

from typing import Optional

from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    OrientationConstraint,
    PositionConstraint,
)
from shape_msgs.msg import SolidPrimitive
from trajectory_msgs.msg import JointTrajectoryPoint

import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node


ARM_JOINTS = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']

PRESETS = {
    'home': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    'ready': [0.0, -0.6, 1.1, 0.0, 0.8, 0.0],
}


class MoveItClient:
    """Thin wrapper around MoveGroup + arm FollowJointTrajectory."""

    def __init__(self, node: Node) -> None:
        self._node = node
        self._move_group = ActionClient(node, MoveGroup, 'move_action')
        self._arm_traj = ActionClient(
            node, FollowJointTrajectory, '/arm_controller/follow_joint_trajectory')
        self._log = node.get_logger()

    def wait_for_servers(self, timeout_sec: float = 20.0) -> bool:
        ok = True
        for client, name in (
            (self._move_group, 'move_action'),
            (self._arm_traj, 'arm_controller'),
        ):
            if not client.wait_for_server(timeout_sec=timeout_sec):
                self._log.error(f'Action server not available: {name}')
                ok = False
        return ok

    def _spin_until(self, future, timeout_sec: float) -> bool:
        from rclpy.executor import FutureReturnCode
        rc = rclpy.spin_until_future_complete(
            self._node, future, timeout_sec=timeout_sec)
        return rc == FutureReturnCode.SUCCESS and future.done()

    def plan_and_move_pose(
        self,
        pose: PoseStamped,
        group: str = 'arm',
        tip_link: str = 'tool0',
        timeout_sec: float = 10.0,
        velocity_scale: float = 0.4,
    ) -> tuple[bool, str]:
        goal = MoveGroup.Goal()
        req = MotionPlanRequest()
        req.group_name = group
        req.num_planning_attempts = 5
        req.allowed_planning_time = min(timeout_sec, 5.0)
        req.max_velocity_scaling_factor = velocity_scale
        req.max_acceleration_scaling_factor = velocity_scale
        req.pipeline_id = 'ompl'
        req.planner_id = 'RRTConnect'

        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [0.025]

        pc = PositionConstraint()
        pc.header = pose.header
        pc.link_name = tip_link
        pc.constraint_region.primitives.append(sphere)
        pc.constraint_region.primitive_poses.append(pose.pose)
        pc.weight = 1.0

        oc = OrientationConstraint()
        oc.header = pose.header
        oc.link_name = tip_link
        oc.orientation = pose.pose.orientation
        oc.absolute_x_axis_tolerance = 0.35
        oc.absolute_y_axis_tolerance = 0.35
        oc.absolute_z_axis_tolerance = 0.5
        oc.weight = 1.0

        constraints = Constraints()
        constraints.position_constraints.append(pc)
        constraints.orientation_constraints.append(oc)
        req.goal_constraints.append(constraints)

        goal.request = req
        goal.planning_options.plan_only = False
        return self._send_move_group(goal, timeout_sec)

    def plan_and_move_joints(
        self,
        joints: list[str],
        positions: list[float],
        group: str = 'arm',
        timeout_sec: float = 10.0,
    ) -> tuple[bool, str]:
        goal = MoveGroup.Goal()
        req = MotionPlanRequest()
        req.group_name = group
        req.num_planning_attempts = 5
        req.allowed_planning_time = min(timeout_sec, 5.0)
        req.max_velocity_scaling_factor = 0.5
        req.max_acceleration_scaling_factor = 0.5
        req.pipeline_id = 'ompl'
        req.planner_id = 'RRTConnect'

        constraints = Constraints()
        for name, val in zip(joints, positions):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = float(val)
            jc.tolerance_above = 0.03
            jc.tolerance_below = 0.03
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
        req.goal_constraints.append(constraints)
        goal.request = req
        goal.planning_options.plan_only = False
        return self._send_move_group(goal, timeout_sec)

    def move_named(self, name: str, group: str = 'arm') -> tuple[bool, str]:
        if name not in PRESETS:
            return False, f'unknown named target {name}'
        return self.plan_and_move_joints(ARM_JOINTS, PRESETS[name], group=group)

    def _send_move_group(self, goal: MoveGroup.Goal, timeout_sec: float) -> tuple[bool, str]:
        if not self._move_group.wait_for_server(timeout_sec=3.0):
            return False, 'move_action server unavailable'
        send_future = self._move_group.send_goal_async(goal)
        if not self._spin_until(send_future, timeout_sec):
            return False, 'move_group goal send timeout'
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return False, 'goal rejected'
        result_future = goal_handle.get_result_async()
        if not self._spin_until(result_future, timeout_sec + 6.0):
            goal_handle.cancel_goal_async()
            return False, 'planning/execution timeout'
        wrapped = result_future.result()
        if wrapped is None:
            return False, 'no result'
        code = getattr(wrapped.result, 'error_code', None)
        val = getattr(code, 'val', -1) if code is not None else -1
        if val == 1:
            return True, 'ok'
        return False, f'MoveGroup error_code={val}'

    def execute_joint_trajectory(
        self,
        points: list[list[float]],
        times_from_start: list[float],
        joints: Optional[list[str]] = None,
        timeout_sec: float = 12.0,
    ) -> tuple[bool, str]:
        joints = joints or ARM_JOINTS
        if not self._arm_traj.wait_for_server(timeout_sec=2.0):
            return False, 'arm_controller unavailable'

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(joints)
        for pt, t in zip(points, times_from_start):
            p = JointTrajectoryPoint()
            p.positions = [float(v) for v in pt]
            sec = int(t)
            nanosec = int((float(t) - sec) * 1e9)
            p.time_from_start = Duration(seconds=sec, nanoseconds=nanosec).to_msg()
            goal.trajectory.points.append(p)

        send_future = self._arm_traj.send_goal_async(goal)
        if not self._spin_until(send_future, timeout_sec):
            return False, 'trajectory send timeout'
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return False, 'trajectory rejected'
        result_future = goal_handle.get_result_async()
        if not self._spin_until(result_future, timeout_sec):
            goal_handle.cancel_goal_async()
            return False, 'trajectory timeout'
        wrapped = result_future.result()
        return True, 'ok' if wrapped is not None else 'no result'
