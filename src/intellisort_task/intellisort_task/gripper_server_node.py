"""Gripper command service with joint_state feedback.

Returns success only when the fingers actually reach the commanded width
(within tolerance). Used by task_manager ConfirmGrasp.
"""
from __future__ import annotations

import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from intellisort_interfaces.srv import GripperCommand


class GripperServer(Node):
    def __init__(self) -> None:
        super().__init__('gripper_server')
        self.declare_parameter('open_position', 0.035)
        self.declare_parameter('closed_position', 0.0)
        self.declare_parameter('command_topic', '/gripper_controller/commands')
        self.declare_parameter('joint_states_topic', '/joint_states')
        self.declare_parameter('left_joint', 'gripper_left_joint')
        self.declare_parameter('right_joint', 'gripper_right_joint')
        self.declare_parameter('position_tolerance', 0.006)
        self.declare_parameter('settle_timeout_sec', 2.0)

        self._positions: dict[str, float] = {}
        self._cmd_pub = self.create_publisher(
            Float64MultiArray,
            self.get_parameter('command_topic').value, 10)
        self._js_sub = self.create_subscription(
            JointState,
            self.get_parameter('joint_states_topic').value,
            self._on_js, 10)
        self._srv = self.create_service(GripperCommand, '/gripper_command', self._handle)
        self.get_logger().info('Gripper service ready (feedback-enabled)')

    def _on_js(self, msg: JointState) -> None:
        for name, pos in zip(msg.name, msg.position):
            self._positions[name] = float(pos)

    def _finger_width(self) -> float | None:
        left = self._positions.get(str(self.get_parameter('left_joint').value))
        right = self._positions.get(str(self.get_parameter('right_joint').value))
        if left is None and right is None:
            return None
        if left is None:
            return float(right) * 2.0
        if right is None:
            return float(left) * 2.0
        return float(left) + float(right)

    def _handle(self, request, response):
        pos = float(request.position)
        open_p = float(self.get_parameter('open_position').value)
        closed_p = float(self.get_parameter('closed_position').value)
        pos = max(closed_p, min(open_p, pos))

        msg = Float64MultiArray()
        msg.data = [pos, pos]
        self._cmd_pub.publish(msg)

        tol = float(self.get_parameter('position_tolerance').value)
        timeout = float(self.get_parameter('settle_timeout_sec').value)
        deadline = time.time() + timeout
        reached = False
        measured = None
        while time.time() < deadline:
            measured = self._finger_width()
            if measured is not None and abs(measured - 2.0 * pos) <= tol * 2.0:
                reached = True
                break
            time.sleep(0.05)

        response.position = float(measured if measured is not None else pos)
        response.effort = 0.0  # not measured in this interface
        response.reached_goal = reached
        response.stalled = (not reached) and (measured is not None)
        if reached:
            response.success = True
            response.message = f'reached width={response.position:.4f} cmd={pos:.4f}'
        else:
            # no joint feedback yet (controller not loaded) — treat as failure
            response.success = False
            response.message = (
                f'timeout waiting for width cmd={pos:.4f} '
                f'measured={measured} (is gripper_controller up?)')
            self.get_logger().warn(response.message)
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GripperServer()
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
