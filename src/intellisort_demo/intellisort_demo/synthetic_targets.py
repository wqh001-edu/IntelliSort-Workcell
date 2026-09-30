"""Publish synthetic ground-truth targets matching the Gazebo world.

Options:
- publish_once: stop after first publish (avoids resurrecting grasped parts)
- disable_grasp_pub: do not publish /grasp_candidates (let grasp_planner own it)
"""
from __future__ import annotations

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from intellisort_interfaces.msg import (
    GraspCandidate,
    GraspCandidateArray,
    TargetPose,
    TargetPoseArray,
)


SYNTHETIC = [
    ('red_0', 'red', 0.38, -0.18, 0.765),
    ('green_0', 'green', 0.30, -0.12, 0.77),
    ('blue_0', 'blue', 0.42, -0.08, 0.765),
    ('yellow_0', 'yellow', 0.32, -0.20, 0.764),
]


class SyntheticTargets(Node):
    def __init__(self) -> None:
        super().__init__('synthetic_targets')
        self.declare_parameter('rate_hz', 1.0)
        self.declare_parameter('frame_id', 'base_link')
        self.declare_parameter('publish_once', False)
        self.declare_parameter('disable_grasp_pub', True)
        self._poses_pub = self.create_publisher(TargetPoseArray, '/target_poses', 10)
        self._grasp_pub = self.create_publisher(GraspCandidateArray, '/grasp_candidates', 10)
        self._sent = False
        self._timer = self.create_timer(
            1.0 / float(self.get_parameter('rate_hz').value), self._tick)

    def _tick(self) -> None:
        if self._sent and bool(self.get_parameter('publish_once').value):
            return
        frame = self.get_parameter('frame_id').value
        poses = TargetPoseArray()
        poses.header.frame_id = frame
        poses.header.stamp = self.get_clock().now().to_msg()

        grasps = GraspCandidateArray()
        grasps.header = poses.header

        for oid, cls, x, y, z in SYNTHETIC:
            ps = PoseStamped()
            ps.header = poses.header
            ps.pose.position.x = x
            ps.pose.position.y = y
            ps.pose.position.z = z
            ps.pose.orientation.x = 1.0
            ps.pose.orientation.w = 0.0

            tp = TargetPose()
            tp.object_id = oid
            tp.object_class = cls
            tp.pose = ps
            tp.confidence = 0.92
            tp.size = [0.03, 0.03, 0.03]
            poses.poses.append(tp)

            if not bool(self.get_parameter('disable_grasp_pub').value):
                gc = GraspCandidate()
                gc.object_id = oid
                gc.object_class = cls
                gpose = PoseStamped()
                gpose.header = poses.header
                gpose.pose.position.x = x
                gpose.pose.position.y = y
                gpose.pose.position.z = z + 0.015
                gpose.pose.orientation.x = 1.0
                gpose.pose.orientation.w = 0.0
                gc.grasp_pose = gpose
                gc.approach_dir.z = -1.0
                gc.width = 0.05
                gc.score = 0.9
                grasps.candidates.append(gc)

        self._poses_pub.publish(poses)
        if not bool(self.get_parameter('disable_grasp_pub').value):
            self._grasp_pub.publish(grasps)
        self._sent = True


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SyntheticTargets()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
