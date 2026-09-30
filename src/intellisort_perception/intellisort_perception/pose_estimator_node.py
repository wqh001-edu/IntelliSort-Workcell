"""3D pose from detections via ray–table intersection.

Camera model: pinhole (CameraInfo K). Extrinsics: camera pose in base_link
(parameters, defaults match URDF mount). Target Z is on the table plane.

This is honest engineering: no magic affine scale. Hand-eye calibration
only updates the camera_x/y/z/rpy parameters.
"""
from __future__ import annotations

import math

import numpy as np
from cv_bridge import CvBridge

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import CameraInfo, Image

from intellisort_interfaces.msg import (
    DetectionArray,
    ExceptionEvent,
    TargetPose,
    TargetPoseArray,
)


CLASS_SIZE = {
    'red': (0.03, 0.03, 0.03),
    'green': (0.028, 0.028, 0.04),
    'blue': (0.032, 0.032, 0.03),
    'yellow': (0.028, 0.028, 0.028),
}

# Default camera pose in base_link (aligned with isc_arm.urdf.xacro mount)
DEFAULT_CAM_POS = (0.55, 0.35, 0.95)
# Look-at feed zone (0.35, -0.12, 0.75) from camera position
DEFAULT_LOOK_AT = (0.35, -0.12, 0.75)


def rpy_to_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
    return rz @ ry @ rx


def look_at_rotation(cam_pos, target) -> np.ndarray:
    """Rotation of camera optical frame (Z forward, Y down) looking at target."""
    pos = np.array(cam_pos, dtype=float)
    tgt = np.array(target, dtype=float)
    z = tgt - pos
    z = z / (np.linalg.norm(z) + 1e-9)
    # world up
    up = np.array([0.0, 0.0, 1.0])
    x = np.cross(up, z)
    n = np.linalg.norm(x)
    if n < 1e-6:
        x = np.array([1.0, 0.0, 0.0])
    else:
        x = x / n
    y = np.cross(z, x)
    # columns are camera axes in base: X_right, Y_down, Z_forward
    return np.column_stack([x, y, z])


class PoseEstimatorNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('pose_estimator')
        self.declare_parameter('detections_topic', '/detections')
        self.declare_parameter('depth_topic', '/camera/depth/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/color/camera_info')
        self.declare_parameter('poses_topic', '/target_poses')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('min_confidence', 0.45)
        self.declare_parameter('table_z', 0.75)
        self.declare_parameter('object_z_offset', 0.015)
        self.declare_parameter('camera_pos', list(DEFAULT_CAM_POS))
        self.declare_parameter('camera_look_at', list(DEFAULT_LOOK_AT))
        self.declare_parameter('use_look_at', True)
        self.declare_parameter('camera_rpy', [0.0, 0.0, 0.0])

        self._bridge = CvBridge()
        self._pub = None
        self._exc_pub = None
        self._detections: DetectionArray | None = None
        self._depth: np.ndarray | None = None
        self._camera_info: CameraInfo | None = None
        self._subs = []
        self._R: np.ndarray | None = None
        self._cam_pos: np.ndarray | None = None

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(
            TargetPoseArray, self.get_parameter('poses_topic').value, 10)
        self._exc_pub = self.create_lifecycle_publisher(
            ExceptionEvent, '/exception_events', 10)
        self._subs = [
            self.create_subscription(
                DetectionArray, self.get_parameter('detections_topic').value,
                self._on_detections, 10),
            self.create_subscription(
                Image, self.get_parameter('depth_topic').value,
                self._on_depth, qos_profile_sensor_data),
            self.create_subscription(
                CameraInfo, self.get_parameter('camera_info_topic').value,
                self._on_info, 10),
        ]
        self._update_extrinsics()
        self.get_logger().info(
            f'Pose estimator ready cam_pos={self._cam_pos.tolist()}')
        return TransitionCallbackReturn.SUCCESS

    def _update_extrinsics(self) -> None:
        pos = self.get_parameter('camera_pos').value
        self._cam_pos = np.array([float(v) for v in pos], dtype=float)
        if bool(self.get_parameter('use_look_at').value):
            look = self.get_parameter('camera_look_at').value
            self._R = look_at_rotation(self._cam_pos, [float(v) for v in look])
        else:
            rpy = self.get_parameter('camera_rpy').value
            self._R = rpy_to_matrix(float(rpy[0]), float(rpy[1]), float(rpy[2]))

    def on_activate(self, state) -> TransitionCallbackReturn:
        if self._pub:
            self._pub.on_activate(state)
        if self._exc_pub:
            self._exc_pub.on_activate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        if self._pub:
            self._pub.on_deactivate(state)
        if self._exc_pub:
            self._exc_pub.on_deactivate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        for s in self._subs:
            self.destroy_subscription(s)
        self._subs.clear()
        if self._pub:
            self.destroy_publisher(self._pub)
        if self._exc_pub:
            self.destroy_publisher(self._exc_pub)
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_detections(self, msg: DetectionArray) -> None:
        self._detections = msg
        self._try_publish()

    def _on_depth(self, msg: Image) -> None:
        try:
            depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            arr = np.asarray(depth, dtype=np.float32)
            if arr.size and float(np.nanmax(arr)) > 10.0:
                arr = arr / 1000.0
            self._depth = arr
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'depth convert error: {exc}')

    def _on_info(self, msg: CameraInfo) -> None:
        self._camera_info = msg

    def _intrinsics(self):
        if self._camera_info is not None and len(self._camera_info.k) >= 6:
            k = self._camera_info.k
            fx, fy, cx, cy = k[0], k[4], k[2], k[5]
            if fx > 1.0 and fy > 1.0:
                return float(fx), float(fy), float(cx), float(cy)
        # Gazebo default for 640x480 60deg HFOV
        return 554.256, 554.256, 320.0, 240.0

    def _try_publish(self) -> None:
        if self._detections is None or self._pub is None:
            return
        fx, fy, cx, cy = self._intrinsics()
        table_z = float(self.get_parameter('table_z').value)
        z_off = float(self.get_parameter('object_z_offset').value)
        min_conf = float(self.get_parameter('min_confidence').value)

        out = TargetPoseArray()
        out.header = self._detections.header
        out.header.frame_id = self.get_parameter('base_frame').value

        for i, det in enumerate(self._detections.detections):
            if det.confidence < min_conf:
                continue
            u = 0.5 * (det.x_min + det.x_max)
            v = 0.5 * (det.y_min + det.y_max)
            xyz, ok = self._intersect_table(u, v, fx, fy, cx, cy, table_z + z_off)
            conf = det.confidence
            if not ok:
                conf = min(conf, 0.5)
                self._emit_pose_low(det.class_name)

            pose = PoseStamped()
            pose.header = out.header
            pose.pose.position.x = float(xyz[0])
            pose.pose.position.y = float(xyz[1])
            pose.pose.position.z = float(xyz[2])
            pose.pose.orientation.x = 1.0
            pose.pose.orientation.w = 0.0

            tp = TargetPose()
            tp.object_id = f'{det.class_name}_{i}'
            tp.object_class = det.class_name
            tp.pose = pose
            tp.confidence = float(conf)
            tp.size = list(CLASS_SIZE.get(det.class_name, (0.03, 0.03, 0.03)))
            out.poses.append(tp)

        self._pub.publish(out)

    def _intersect_table(self, u, v, fx, fy, cx, cy, z_plane):
        """Ray from camera through pixel, intersect plane z=z_plane in base."""
        if self._R is None or self._cam_pos is None:
            self._update_extrinsics()
        x_n = (u - cx) / fx
        y_n = (v - cy) / fy
        ray_cam = np.array([x_n, y_n, 1.0], dtype=float)
        ray_cam /= np.linalg.norm(ray_cam)
        ray_base = self._R @ ray_cam
        origin = self._cam_pos
        if abs(ray_base[2]) < 1e-6:
            return (float(origin[0]), float(origin[1]), z_plane), False
        t = (z_plane - origin[2]) / ray_base[2]
        if t <= 0.0:
            return (float(origin[0]), float(origin[1]), z_plane), False
        p = origin + t * ray_base
        return (float(p[0]), float(p[1]), float(z_plane)), True

    def _emit_pose_low(self, class_name: str) -> None:
        if not self._exc_pub:
            return
        msg = ExceptionEvent()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.error_code = 'POSE_LOW'
        msg.severity = 'RECOVERABLE'
        msg.description = f'ray-table intersection failed for {class_name}'
        msg.recovery_action = 're-perceive'
        self._exc_pub.publish(msg)


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
