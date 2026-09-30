"""Aggregate system metrics from live topics (no hardcoded rates).

Primary metrics are published by task_manager on /system_metrics.
This node can be used standalone: it counts /task_status transitions and
publishes honest rates (0 when no data yet).
"""
from __future__ import annotations

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.msg import SystemMetrics, TaskStatus


class MetricPublisherNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('metric_publisher')
        self.declare_parameter('publish_period_sec', 2.0)
        self._pub = None
        self._sub = None
        self._timer = None
        self._completed = 0
        self._failed = 0
        self._cycle_times: list[float] = []
        self._plan_ok = self._plan_total = 0
        self._grasp_ok = self._grasp_total = 0
        self._recover_ok = self._recover_total = 0

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(SystemMetrics, '/system_metrics_agg', 10)
        self._sub = self.create_subscription(TaskStatus, '/task_status', self._on_status, 10)
        period = float(self.get_parameter('publish_period_sec').value)
        self._timer = self.create_timer(max(period, 0.5), self._publish)
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
        if self._timer:
            self._timer.cancel()
            self._timer = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_status(self, msg: TaskStatus) -> None:
        if msg.state == 'SUCCESS':
            self._completed += 1
        elif msg.state in ('FAILED', 'ERROR'):
            self._failed += 1

    def _publish(self) -> None:
        if not self._pub:
            return
        m = SystemMetrics()
        m.header.stamp = self.get_clock().now().to_msg()
        # Honest: without plan/grasp samples these stay 0 (not fake 0.95)
        m.plan_success_rate = (
            self._plan_ok / self._plan_total) if self._plan_total else 0.0
        m.grasp_success_rate = (
            self._grasp_ok / self._grasp_total) if self._grasp_total else 0.0
        m.recovery_success_rate = (
            self._recover_ok / self._recover_total) if self._recover_total else 0.0
        m.avg_cycle_time_sec = (
            sum(self._cycle_times) / len(self._cycle_times)) if self._cycle_times else 0.0
        m.completed_tasks = self._completed
        m.failed_tasks = self._failed
        self._pub.publish(m)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MetricPublisherNode()
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
