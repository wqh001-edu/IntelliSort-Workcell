"""Send ExecuteTask action to run the sorting demo once."""
from __future__ import annotations

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from intellisort_interfaces.action import ExecuteTask


class RunPickDemo(Node):
    def __init__(self) -> None:
        super().__init__('run_pick_demo')
        self.declare_parameter('task_id', 'demo_sorting')
        self.declare_parameter('max_targets', 3)
        self.declare_parameter('object_classes', ['red', 'green', 'blue'])
        self._client = ActionClient(self, ExecuteTask, '/execute_task')

    def send(self) -> None:
        if not self._client.wait_for_server(timeout_sec=15.0):
            self.get_logger().error('/execute_task not available')
            return
        goal = ExecuteTask.Goal()
        goal.task_id = self.get_parameter('task_id').value
        goal.object_classes = list(self.get_parameter('object_classes').value)
        goal.place_slots = []
        goal.max_targets = int(self.get_parameter('max_targets').value)
        goal.enable_recovery = True

        self.get_logger().info('Sending ExecuteTask...')
        send_future = self._client.send_goal_async(
            goal, feedback_callback=self._feedback)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error('goal rejected')
            return
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result
        self.get_logger().info(
            f'Demo finished success={result.success} '
            f'completed={result.completed} failed={result.failed} '
            f'msg={result.message}')

    def _feedback(self, msg) -> None:
        fb = msg.feedback
        self.get_logger().info(
            f'feedback phase={fb.phase} progress={fb.progress:.2f} '
            f'completed={fb.completed} failed={fb.failed} {fb.message}')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RunPickDemo()
    try:
        node.send()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
