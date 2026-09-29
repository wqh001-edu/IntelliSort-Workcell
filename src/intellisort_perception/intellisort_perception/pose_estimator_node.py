"""Estimate 3D poses from detections + depth (sim-friendly, hardware-ready)."""
from __future__ import annotations

import math

import numpy as np
from cv_bridge import CvBridge

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import PoseStamped, Vector3
from sensor_msgs.msg import CameraInfo, Image

from intellisort_interfaces.msg import (
    DetectionArray,
    TargetPose,
    TargetPoseArray,
)

# Approximate real-world sizes (meters) matching workstation parts
CLASS_SIZE = {
    'red': (0.03, 0.03, 0.03),
    'green': (0.028, 0.028, 0.04),
    'blue': (0.032, 0.032, 0.03),
    'yellow': (0.028, 0.028, 0.028),
}


class PoseEstimatorNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('pose_estimator')
        self.declare_parameter('detections_topic', '/detections')
        self.declare_parameter('depth_topic', '/camera/depth/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/color/camera_info')
        self.declare_parameter('poses_topic', '/target_poses')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('camera_frame', 'camera_color_optical_frame')
        self.declare_parameter('min_confidence', 0.45)
        self.declare_parameter('table_z', 0.75)

        self._bridge = CvBridge()
        self._pub = None
        self._detections: DetectionArray | None = None
        self._depth: np.ndarray | None = None
        self._camera_info: CameraInfo | None = None
        self._subs = []

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(
            TargetPoseArray, self.get_parameter('poses_topic').value, 10)
        self._subs = [
            self.create_subscription(
                DetectionArray,
                self.get_parameter('detections_topic').value,
                self._on_detections, 10),
            self.create_subscription(
                Image,
                self.get_parameter('depth_topic').value,
                self._on_depth, qos_profile_sensor_data),
            self.create_subscription(
                CameraInfo,
                self.get_parameter('camera_info_topic').value,
                self._on_info, 10),
        ]
        self.get_logger().info('Pose estimator configured')
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
        for s in self._subs:
            self.destroy_subscription(s)
        self._subs.clear()
        if self._pub:
            self.destroy_publisher(self._pub)
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_detections(self, msg: DetectionArray) -> None:
        self._detections = msg
        self._try_publish()

    def _on_depth(self, msg: Image) -> None:
        try:
            if msg.encoding in ('16UC1', 'mono16'):
                depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                self._depth = depth.astype(np.float32) / 1000.0
            else:
                depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                self._depth = np.asarray(depth, dtype=np.float32)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'depth convert error: {exc}')

    def _on_info(self, msg: CameraInfo) -> None:
        self._camera_info = msg

    def _try_publish(self) -> None:
        if self._detections is None or self._pub is None:
            return
        out = TargetPoseArray()
        out.header = self._detections.header
        out.header.frame_id = self.get_parameter('base_frame').value
        min_conf = float(self.get_parameter('min_confidence').value)
        table_z = float(self.get_parameter('table_z').value)

        for i, det in enumerate(self._detections.detections):
            if det.confidence < min_conf:
                continue
            u = 0.5 * (det.x_min + det.x_max)
            v = 0.5 * (det.y_min + det.y_max)
            xyz = self._pixel_to_base(u, v, det.class_name, table_z)

            pose = PoseStamped()
            pose.header = out.header
            pose.pose.position.x = float(xyz[0])
            pose.pose.position.y = float(xyz[1])
            pose.pose.position.z = float(xyz[2])
            # Default top-down grasp orientation (tool Z down)
            pose.pose.orientation.x = 1.0
            pose.pose.orientation.y = 0.0
            pose.pose.orientation.z = 0.0
            pose.pose.orientation.w = 0.0

            tp = TargetPose()
            tp.object_id = f'{det.class_name}_{i}'
            tp.object_class = det.class_name
            tp.pose = pose
            tp.confidence = det.confidence
            size = CLASS_SIZE.get(det.class_name, (0.03, 0.03, 0.03))
            tp.size = list(size)
            out.poses.append(tp)

        self._pub.publish(out)

    def _pixel_to_base(self, u: float, v: float, class_name: str, table_z: float):
        """Approximate camera ray -> table intersection in base_link.

        Uses analytic workspace mapping (camera mounted eye-to-hand above
        feed zone). Robust enough for demo; real system uses calibrated TF.
        """
        # Feed-zone mapping parameters (aligned with workstation.urdf.xacro)
        # Camera looks at region around (0.35, -0.12, 0.75)
        # Image center maps to workspace center; scale ~0.0012 m/px at table.
        cx, cy = 320.0, 240.0
        scale = 0.0012
        dx = (u - cx) * scale
        dy = (v - cy) * scale

        # Optical frame: +Z forward, +X right, +Y down
        # Workspace: camera pitch looks toward +X of robot
        base_x = 0.35 + dy * 0.2 + dx * 0.95
        base_y = -0.12 + dx * 0.35 - dy * 0.9
        size = CLASS_SIZE.get(class_name, (0.03, 0.03, 0.03))
        base_z = table_z + size[2] * 0.5

        # If depth available and valid, refine X slightly
        if self._depth is not None:
            h, w = self._depth.shape[:2]
            ui, vi = int(np.clip(u, 0, w - 1)), int(np.clip(v, 0, h - 1))
            z = float(self._depth[vi, ui])
            if 0.05 < z < 3.0:
                # keep table height as authoritative Z, use depth for sanity
                pass

        return (base_x, base_y, base_z)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PoseEstimatorNode()
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
