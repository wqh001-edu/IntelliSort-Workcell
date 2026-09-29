"""Track free slots / occupied slots for task assignment."""
from __future__ import annotations

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.msg import TargetPoseArray
from intellisort_interfaces.srv import GetWorkspaceState


class WorkspaceStateNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('workspace_state')
        self.declare_parameter('poses_topic', '/target_poses')
        self.declare_parameter('slots', ['slot_a', 'slot_b', 'slot_c'])
        self.declare_parameter('slot_positions', [
            0.35, 0.28, 0.75,
            0.48, 0.12, 0.75,
            0.48, -0.12, 0.75,
        ])
        self.declare_parameter('occupancy_radius', 0.06)

        self._targets = TargetPoseArray()
        self._sub = None
        self._srv = None

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._sub = self.create_subscription(
            TargetPoseArray,
            self.get_parameter('poses_topic').value,
            self._on_poses, 10)
        self._srv = self.create_service(
            GetWorkspaceState, '/get_workspace_state', self._on_get_state)
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        if self._sub:
            self.destroy_subscription(self._sub)
        if self._srv:
            self.destroy_service(self._srv)
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_poses(self, msg: TargetPoseArray) -> None:
        self._targets = msg

    def _on_get_state(self, request, response):
        slots = list(self.get_parameter('slots').value)
        flat = list(self.get_parameter('slot_positions').value)
        radius = float(self.get_parameter('occupancy_radius').value)
        occupied, free = [], []
        for i, slot in enumerate(slots):
            x, y, z = flat[3 * i:3 * i + 3]
            occ = False
            for tp in self._targets.poses:
                dx = tp.pose.pose.position.x - x
                dy = tp.pose.pose.position.y - y
                if (dx * dx + dy * dy) ** 0.5 < radius:
                    occ = True
                    break
            (occupied if occ else free).append(slot)

        response.success = True
        response.targets = self._targets
        response.occupied_slots = occupied
        response.free_slots = free
        response.message = f'occupied={occupied} free={free}'
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WorkspaceStateNode()
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
