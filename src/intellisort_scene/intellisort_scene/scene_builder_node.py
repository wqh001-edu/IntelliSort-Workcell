"""PlanningScene sync for IntelliSort Workcell.

Geometry rules (must match URDF / world):
- Table top surface z = 0.75
- Dynamic targets are collision boxes at their estimated pose
- Before grasp descent, the target box is REMOVED so the gripper can enter
- After a successful place, the box stays removed
- On failed pick, the box is re-ADDED
"""
from __future__ import annotations

from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, PlanningScene
from shape_msgs.msg import SolidPrimitive

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.msg import TargetPoseArray, TaskStatus
from intellisort_scene.geometry import make_box


class SceneBuilderNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('scene_builder')
        self.declare_parameter('poses_topic', '/target_poses')
        self.declare_parameter('planning_scene_topic', '/planning_scene')
        self.declare_parameter('publish_rate_hz', 2.0)
        self.declare_parameter('add_static_environment', True)
        self.declare_parameter('table_top_z', 0.75)
        self.declare_parameter('table_thickness', 0.05)
        self.declare_parameter('table_center_x', 0.15)
        self.declare_parameter('table_size_x', 1.2)
        self.declare_parameter('table_size_y', 0.8)
        self.declare_parameter('obstacle_x', 0.18)
        self.declare_parameter('obstacle_y', 0.22)
        self.declare_parameter('obstacle_height', 0.12)

        self._pub = None
        self._sub_poses = None
        self._sub_status = None
        self._timer = None
        self._targets: dict[str, tuple] = {}  # id -> (x,y,z,sx,sy,sz,class)
        self._static_ready = False
        self._held: set[str] = set()     # collision removed for grasp
        self._gone: set[str] = set()     # successfully placed / gone
        self._pending_remove: str | None = None

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(
            PlanningScene, self.get_parameter('planning_scene_topic').value, 10)
        self._sub_poses = self.create_subscription(
            TargetPoseArray,
            self.get_parameter('poses_topic').value,
            self._on_poses, 10)
        self._sub_status = self.create_subscription(
            TaskStatus, '/task_status', self._on_task_status, 10)
        rate = float(self.get_parameter('publish_rate_hz').value)
        self._timer = self.create_timer(1.0 / max(rate, 0.1), self._tick)
        self.get_logger().info(
            'Scene builder ready (table top z=%.3f)' % float(self.get_parameter('table_top_z').value))
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
        for sub in (self._sub_poses, self._sub_status):
            if sub:
                self.destroy_subscription(sub)
        if self._pub:
            self.destroy_publisher(self._pub)
            self._pub = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    # -------------------- inputs --------------------
    def _on_poses(self, msg: TargetPoseArray) -> None:
        for tp in msg.poses:
            sx, sy, sz = 0.03, 0.03, 0.03
            if len(tp.size) >= 3:
                sx, sy, sz = float(tp.size[0]), float(tp.size[1]), float(tp.size[2])
            self._targets[tp.object_id] = (
                tp.pose.pose.position.x,
                tp.pose.pose.position.y,
                tp.pose.pose.position.z,
                sx, sy, sz, tp.object_class,
            )
        # forget targets no longer reported (unless already gone)
        live = {tp.object_id for tp in msg.poses}
        self._targets = {k: v for k, v in self._targets.items() if k in live or k in self._gone}

    def _on_task_status(self, msg: TaskStatus) -> None:
        """Interpret task phase to release / drop collision boxes.

        task_manager messages:
          PICK  RUNNING 'picking <id>'
          PICK  RUNNING 'descend'  (uses _pending id from 'picking')
          PLACE RUNNING 'transport to slot'
          DONE  SUCCESS '...'
          DONE  FAILED  '...'
        """
        text = msg.message or ''
        oid = None
        if 'picking' in text:
            parts = text.split()
            if 'picking' in parts:
                idx = parts.index('picking')
                if idx + 1 < len(parts):
                    oid = parts[idx + 1]

        if oid and msg.phase in ('PICK', 'GRASP'):
            self._pending_remove = oid
            self._release_collision(oid)

        if msg.phase == 'DONE':
            if msg.state == 'SUCCESS' and self._pending_remove:
                self._gone.add(self._pending_remove)
                self._remove_collision(self._pending_remove)
                self.get_logger().info(
                    f'Target {self._pending_remove} finished — keep collision removed')
            elif msg.state in ('FAILED', 'ERROR') and self._pending_remove:
                # restore obstacle so the scene stays honest
                self._restore_collision(self._pending_remove)
            self._pending_remove = None

        if msg.phase == 'PLACE' and msg.state == 'FAILED' and self._pending_remove:
            self._restore_collision(self._pending_remove)

    # -------------------- collision ops --------------------
    def _release_collision(self, oid: str) -> None:
        if oid in self._held or oid in self._gone:
            return
        self._held.add(oid)
        self._publish_remove(oid)
        self.get_logger().info(f'Released collision for grasp target: {oid}')

    def _restore_collision(self, oid: str) -> None:
        if oid not in self._targets:
            return
        self._held.discard(oid)
        x, y, z, sx, sy, sz, _ = self._targets[oid]
        self._publish_objects([make_box(oid, x, y, z, sx, sy, sz)])
        self.get_logger().info(f'Restored collision for: {oid}')

    def _remove_collision(self, oid: str) -> None:
        self._held.add(oid)
        self._publish_remove(oid)

    def _publish_remove(self, oid: str) -> None:
        if not self._pub:
            return
        scene = PlanningScene()
        scene.is_diff = True
        co = CollisionObject()
        co.id = oid
        co.header.frame_id = 'base_link'
        co.operation = CollisionObject.REMOVE
        scene.world.collision_objects.append(co)
        self._pub.publish(scene)

    def _publish_objects(self, objects: list) -> None:
        if not self._pub:
            return
        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects.extend(objects)
        self._pub.publish(scene)

    def _tick(self) -> None:
        if not self._pub:
            return
        objects = []
        if bool(self.get_parameter('add_static_environment').value) and not self._static_ready:
            top = float(self.get_parameter('table_top_z').value)
            th = float(self.get_parameter('table_thickness').value)
            objects.append(make_box(
                'table',
                float(self.get_parameter('table_center_x').value), 0.0,
                top - th / 2.0,
                float(self.get_parameter('table_size_x').value),
                float(self.get_parameter('table_size_y').value),
                th))
            obs_h = float(self.get_parameter('obstacle_height').value)
            # obstacle sits on table
            objects.append(make_box(
                'obstacle_block',
                float(self.get_parameter('obstacle_x').value),
                float(self.get_parameter('obstacle_y').value),
                top + obs_h / 2.0,
                0.10, 0.10, obs_h))
            self._static_ready = True

        for oid, (x, y, z, sx, sy, sz, _) in self._targets.items():
            if oid in self._held or oid in self._gone:
                continue
            objects.append(make_box(oid, x, y, z, sx, sy, sz))

        if objects:
            self._publish_objects(objects)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SceneBuilderNode()
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
