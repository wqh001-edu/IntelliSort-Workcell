"""Generate top-down and side grasp candidates from target poses."""
from __future__ import annotations

import math

from geometry_msgs.msg import PoseStamped, Vector3

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.msg import (
    GraspCandidate,
    GraspCandidateArray,
    TargetPose,
    TargetPoseArray,
)


class GraspPlannerNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('grasp_planner')
        self.declare_parameter('poses_topic', '/target_poses')
        self.declare_parameter('grasp_topic', '/grasp_candidates')
        self.declare_parameter('approach_height', 0.12)
        self.declare_parameter('grasp_depth', 0.015)
        self.declare_parameter('num_yaw_samples', 2)
        self.declare_parameter('default_width', 0.05)

        self._pub = None
        self._sub = None

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(
            GraspCandidateArray, self.get_parameter('grasp_topic').value, 10)
        self._sub = self.create_subscription(
            TargetPoseArray,
            self.get_parameter('poses_topic').value,
            self._on_poses, 10)
        self.get_logger().info('Grasp planner configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state) -> TransitionCallbackReturn:
        if self._pub:
            self._pub.on_activate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        if self._pub:
            self._pub.on_deactivate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        if self._sub:
            self.destroy_subscription(self._sub)
        if self._pub:
            self.destroy_publisher(self._pub)
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_poses(self, msg: TargetPoseArray) -> None:
        if self._pub is None:
            return
        out = GraspCandidateArray()
        out.header = msg.header
        for tp in msg.poses:
            out.candidates.extend(self.generate(tp))
        # sort by score desc
        out.candidates.sort(key=lambda c: c.score, reverse=True)
        self._pub.publish(out)

    def generate(self, tp: TargetPose) -> list[GraspCandidate]:
        candidates: list[GraspCandidate] = []
        approach_h = float(self.get_parameter('approach_height').value)
        depth = float(self.get_parameter('grasp_depth').value)
        n_yaw = int(self.get_parameter('num_yaw_samples').value)
        width = float(self.get_parameter('default_width').value)

        base = tp.pose
        x = base.pose.position.x
        y = base.pose.position.y
        z = base.pose.position.z

        yaws = [0.0] if n_yaw <= 1 else [0.0, math.pi / 2.0]
        for yaw in yaws:
            grasp = PoseStamped()
            grasp.header = base.header
            grasp.header.frame_id = base.header.frame_id or 'base_link'
            grasp.pose.position.x = x
            grasp.pose.position.y = y
            grasp.pose.position.z = z + depth
            # tool Z pointing down; yaw around Z
            half = yaw * 0.5
            grasp.pose.orientation.x = math.sin(half)
            grasp.pose.orientation.y = 0.0
            grasp.pose.orientation.z = 0.0
            grasp.pose.orientation.w = math.cos(half)
            # For top-down: use (x=1,w=0) then adjust — keep explicit quaternion
            # Top-down default (matches pose_estimator):
            if abs(yaw) < 1e-6:
                grasp.pose.orientation.x = 1.0
                grasp.pose.orientation.y = 0.0
                grasp.pose.orientation.z = 0.0
                grasp.pose.orientation.w = 0.0

            approach = Vector3()
            approach.x = 0.0
            approach.y = 0.0
            approach.z = -1.0

            gc = GraspCandidate()
            gc.object_id = tp.object_id
            gc.object_class = tp.object_class
            gc.grasp_pose = grasp
            gc.approach_dir = approach
            gc.width = width
            # Prefer higher confidence and centered yaw sample
            score = tp.confidence * (1.0 if abs(yaw) < 1e-6 else 0.85)
            gc.score = float(score)
            candidates.append(gc)

        # Pre-approach pose is produced later in task layer (z + approach_h)
        _ = approach_h
        return candidates


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GraspPlannerNode()
    try:
        node.trigger_configure()
        node.trigger_activate()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
