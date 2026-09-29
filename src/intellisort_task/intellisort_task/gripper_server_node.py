"""Gripper command service backed by joint trajectory / position command."""
from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

from intellisort_interfaces.srv import GripperCommand


class GripperServer(Node):
    def __init__(self) -> None:
        super().__init__('gripper_server')
        self.declare_parameter('open_position', 0.035)
        self.declare_parameter('closed_position', 0.0)
        self.declare_parameter('command_topic', '/gripper_controller/commands')
        self._pub = self.create_publisher(
            Float64MultiArray,
            self.get_parameter('command_topic').value,
            10)
        self._srv = self.create_service(
            GripperCommand, '/gripper_command', self._handle)
        self.get_logger().info('Gripper service ready on /gripper_command')

    def _handle(self, request, response):
        pos = float(request.position)
        open_p = float(self.get_parameter('open_position').value)
        closed_p = float(self.get_parameter('closed_position').value)
        pos = max(closed_p, min(open_p, pos))

        msg = Float64MultiArray()
        # two finger joints: left and right
        msg.data = [pos, pos]
        self._pub.publish(msg)

        response.success = True
        response.position = pos
        response.effort = float(request.max_effort or 0.0)
        response.reached_goal = True
        response.stalled = False
        response.message = f'gripper command pos={pos:.4f}'
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
