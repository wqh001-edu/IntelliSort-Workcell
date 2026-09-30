"""Exception supervisor: recovery policy + real /recovery action execution.

task_manager calls /recovery; this node decides the recovery action and
keeps honest statistics for recovery_success_rate.
"""
from __future__ import annotations

import time

import rclpy
from rclpy.action import ActionServer
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.action import Recovery
from intellisort_interfaces.msg import ExceptionEvent, TaskStatus
from intellisort_task.recovery_policy import RECOVERY_POLICY


class SupervisorNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('supervisor')
        self.declare_parameter('max_auto_recoveries', 5)
        self.declare_parameter('recovery_window_sec', 120.0)
        self._recoveries = 0
        self._window_start = time.time()
        self._ok = 0
        self._total = 0
        self._sub_ev = None
        self._sub_st = None
        self._action = None
        self._event_pub = None

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._sub_ev = self.create_subscription(
            ExceptionEvent, '/exception_events', self._on_exception, 10)
        self._sub_st = self.create_subscription(
            TaskStatus, '/task_status', self._on_status, 10)
        self._event_pub = self.create_lifecycle_publisher(
            ExceptionEvent, '/recovery_events', 10)
        self._action = ActionServer(
            self, Recovery, '/recovery', execute_callback=self._exec_recovery)
        self.get_logger().info('Supervisor ready (/recovery)')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state) -> TransitionCallbackReturn:
        if self._event_pub:
            self._event_pub.on_activate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        if self._event_pub:
            self._event_pub.on_deactivate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _reset_window_if_needed(self) -> None:
        window = float(self.get_parameter('recovery_window_sec').value)
        if time.time() - self._window_start > window:
            self._recoveries = 0
            self._window_start = time.time()

    def _on_exception(self, msg: ExceptionEvent) -> None:
        policy = RECOVERY_POLICY.get(msg.error_code, ('retry', 'RECOVERABLE'))
        self.get_logger().warn(
            f'exception {msg.error_code}: {msg.description} policy={policy[0]}')

    def _on_status(self, msg: TaskStatus) -> None:
        if msg.state in ('FAILED', 'ERROR'):
            self.get_logger().error(
                f'task {msg.task_id} state={msg.state} {msg.message}')

    def _exec_recovery(self, goal_handle):
        self._reset_window_if_needed()
        result = Recovery.Result()
        code = goal_handle.request.error_code
        description = goal_handle.request.description
        self._total += 1

        action, severity = RECOVERY_POLICY.get(code, ('retry', 'RECOVERABLE'))
        max_r = int(self.get_parameter('max_auto_recoveries').value)

        if severity == 'FATAL' or self._recoveries >= max_r:
            result.success = False
            result.recovery_action = 'error' if severity == 'FATAL' else 'error'
            result.message = (
                f'no auto-recovery for {code} '
                f'(count={self._recoveries}/{max_r})')
            self._emit(code, 'FATAL', description, result.recovery_action)
            goal_handle.abort()
            return result

        self._recoveries += 1
        result.success = True
        result.recovery_action = action
        result.message = f'applied {action} for {code} (#{self._recoveries})'
        self._ok += 1
        self._emit(code, 'RECOVERABLE', description, action)
        self.get_logger().info(result.message)
        goal_handle.succeed()
        return result

    def _emit(self, code, severity, description, recovery) -> None:
        if not self._event_pub:
            return
        msg = ExceptionEvent()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.error_code = code
        msg.severity = severity
        msg.description = description
        msg.recovery_action = recovery
        self._event_pub.publish(msg)

    # stats helper (optional topic later)
    @property
    def recovery_success_rate(self) -> float:
        return (self._ok / self._total) if self._total else 0.0


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SupervisorNode()
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
