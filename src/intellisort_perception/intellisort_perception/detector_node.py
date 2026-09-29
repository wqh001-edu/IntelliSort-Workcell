"""Classical CV multi-color object detector (sim + real, no GPU required)."""
from __future__ import annotations

import cv2
import numpy as np
from cv_bridge import CvBridge

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from std_msgs.msg import Header

from intellisort_interfaces.msg import Detection, DetectionArray


# HSV ranges: BGR-ish colors used in Gazebo parts
COLOR_PROFILES = {
    'red': {
        'ranges': [((0, 80, 80), (10, 255, 255)), ((170, 80, 80), (180, 255, 255))],
        'min_area': 80,
    },
    'green': {
        'ranges': [((40, 70, 70), (85, 255, 255))],
        'min_area': 80,
    },
    'blue': {
        'ranges': [((100, 80, 80), (135, 255, 255))],
        'min_area': 80,
    },
    'yellow': {
        'ranges': [((20, 80, 80), (35, 255, 255))],
        'min_area': 80,
    },
}


class DetectorNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('object_detection')
        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('detections_topic', '/detections')
        self.declare_parameter('publish_markers', True)
        self.declare_parameter('conf_threshold', 0.45)
        self.declare_parameter('roi_scale', 1.0)

        self._bridge = CvBridge()
        self._pub: rclpy.publisher.Publisher = None  # type: ignore
        self._sub = None
        self._active = False

    def on_configure(self, state) -> TransitionCallbackReturn:
        topic = self.get_parameter('image_topic').value
        det_topic = self.get_parameter('detections_topic').value
        self._pub = self.create_lifecycle_publisher(DetectionArray, det_topic, 10)
        self._sub = self.create_subscription(
            Image, topic, self._on_image, qos_profile_sensor_data)
        self.get_logger().info(f'Detector configured on {topic} -> {det_topic}')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state) -> TransitionCallbackReturn:
        self._active = True
        if self._pub:
            self._pub.on_activate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        self._active = False
        if self._pub:
            self._pub.on_deactivate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        self.destroy_subscription(self._sub)
        self.destroy_publisher(self._pub)
        self._pub = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_image(self, msg: Image) -> None:
        if not self._active or self._pub is None:
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'cv_bridge error: {exc}')
            return

        detections = self.detect(frame, msg.header)
        out = DetectionArray()
        out.header = msg.header if msg.header else Header()
        out.detections = detections
        self._pub.publish(out)

    def detect(self, frame: np.ndarray, header) -> list[Detection]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, w = hsv.shape[:2]
        conf_th = float(self.get_parameter('conf_threshold').value)
        results: list[Detection] = []

        for class_name, profile in COLOR_PROFILES.items():
            mask = np.zeros((h, w), dtype=np.uint8)
            for lo, hi in profile['ranges']:
                mask |= cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < profile['min_area']:
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                conf = min(0.99, 0.55 + area / float(w * h) * 8.0)
                if conf < conf_th:
                    continue
                det = Detection()
                det.class_name = class_name
                det.confidence = float(conf)
                det.x_min = float(x)
                det.y_min = float(y)
                det.x_max = float(x + bw)
                det.y_max = float(y + bh)
                det.track_id = -1
                results.append(det)

        results.sort(key=lambda d: d.confidence, reverse=True)
        return results


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DetectorNode()
    # Lifecycle nodes need to be spun and configured/activated.
    # For bringup simplicity, auto-configure + activate after startup.
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
