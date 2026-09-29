"""Runtime mode manager: sim vs real driver selection.

Upper layers only talk to this service; drivers are swapped behind it.
"""
from __future__ import annotations

import rclpy
from rclpy.node import Node

from intellisort_interfaces.srv import SetMode


class ModeManager(Node):
    def __init__(self) -> None:
        super().__init__('mode_manager')
        self.declare_parameter('robot_driver', 'sim')       # sim | xarm | ur | fake
        self.declare_parameter('camera_driver', 'sim')      # sim | realsense | usb_cam
        self.declare_parameter('end_effector', 'parallel_2f')
        self.declare_parameter('use_sim_time', True)
        self._mode = 'sim'
        self._task_enabled = True
        self._srv = self.create_service(SetMode, '/set_mode', self._handle)
        self.get_logger().info('Mode manager ready')

    def _handle(self, request, response):
        mode = (request.mode or '').strip().lower()
        if mode in ('sim', 'real', 'fake'):
            self._mode = mode
            self.set_parameters([
                rclpy.parameter.Parameter(
                    'robot_driver', rclpy.Parameter.Type.STRING,
                    'sim' if mode != 'real' else 'xarm'),
                rclpy.parameter.Parameter(
                    'use_sim_time', rclpy.Parameter.Type.BOOL, mode != 'real'),
            ])
            response.success = True
            response.message = f'mode set to {self._mode}'
        else:
            response.success = False
            response.message = f'unknown mode {request.mode}'
        self._task_enabled = bool(request.enable_task)
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ModeManager()
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
