"""Exception supervisor: monitors status/events and provides recovery guidance."""
from __future__ import annotations

import rclpy
from rclpy.action import ActionServer
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.action import Recovery
from intellisort_interfaces.msg import ExceptionEvent, TaskStatus


RECOVERY_POLICY = {
    'DETECT_FAIL': ('re-perceive', 'skip'),
    'POSE_LOW': ('re-perceive', 'skip'),
    'PLAN_FAIL': ('replan', 'retry'),
    'GRASP_FAIL': ('re-grasp', 'retry'),
    'COLLISION': ('clear-scene-replan', 'retry'),
    'TIMEOUT': ('abort-cycle', 'error'),
    'COMM': ('reconnect', 'error'),
    'TASK_FAIL': ('skip-target', 'skip'),
}


class SupervisorNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('supervisor')
        self.declare_parameter('max_auto_recoveries', 3)
        self._recoveries = 0
        self._sub_ev = None
        self._sub_st = None
        self._action = None

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._sub_ev = self.create_subscription(
            ExceptionEvent, '/exception_events', self._on_exception, 10)
        self._sub_st = self.create_subscription(
            TaskStatus, '/task_status', self._on_status, 10)
        self._action = ActionServer(
            self, Recovery, '/recovery', execute_callback=self._exec_recovery)
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_exception(self, msg: ExceptionEvent) -> None:
        policy = RECOVERY_POLICY.get(msg.error_code, ('retry', 'skip'))
        self.get_logger().warn(
            f'exception {msg.error_code}: {msg.description} policy={policy}')

    def _on_status(self, msg: TaskStatus) -> None:
        if msg.state in ('FAILED', 'ERROR'):
            self.get_logger().error(f'task {msg.task_id} state={msg.state} {msg.message}')

    def _exec_recovery(self, goal_handle):
        result = Recovery.Result()
        code = goal_handle.request.error_code
        action, severity = RECOVERY_POLICY.get(code, ('retry', 'skip'))
        if self._recoveries >= int(self.get_parameter('max_auto_recoveries').value):
            result.success = False
            result.recovery_action = 'error'
            result.message = 'max auto recoveries exceeded'
            goal_handle.abort()
            return result
        self._recoveries += 1
        result.success = True
        result.recovery_action = action
        result.message = f'applied {action} for {code}'
        goal_handle.succeed()
        return result


def main(args=None) -> None:
    import rclpy
    from rclpy.action import ActionServer  # noqa: F401
    # bind ActionServer onto module used above
    rclpy.init(args=args)
    # local patch: Supervisor uses rclpy.action.ActionServer
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
