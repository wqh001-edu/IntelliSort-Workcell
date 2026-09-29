"""Build and update MoveIt PlanningScene from static workstation + detections."""
from __future__ import annotations

from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, PlanningScene
from shape_msgs.msg import SolidPrimitive

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.msg import TargetPoseArray


class SceneBuilderNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('scene_builder')
        self.declare_parameter('poses_topic', '/target_poses')
        self.declare_parameter('planning_scene_topic', '/planning_scene')
        self.declare_parameter('publish_rate_hz', 2.0)
        self.declare_parameter('add_static_environment', True)

        self._pub = None
        self._sub = None
        self._timer = None
        self._targets = TargetPoseArray()
        self._static_ready = False

    def on_configure(self, state) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(
            PlanningScene, self.get_parameter('planning_scene_topic').value, 10)
        self._sub = self.create_subscription(
            TargetPoseArray,
            self.get_parameter('poses_topic').value,
            self._on_poses, 10)
        rate = float(self.get_parameter('publish_rate_hz').value)
        self._timer = self.create_timer(1.0 / max(rate, 0.1), self._publish_scene)
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
        if self._sub:
            self.destroy_subscription(self._sub)
        if self._pub:
            self.destroy_publisher(self._pub)
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _on_poses(self, msg: TargetPoseArray) -> None:
        self._targets = msg

    def _make_box(self, name, x, y, z, sx, sy, sz) -> CollisionObject:
        co = CollisionObject()
        co.id = name
        co.header.frame_id = 'base_link'
        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [sx, sy, sz]
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        pose.orientation.w = 1.0
        co.primitives.append(box)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD
        return co

    def _make_cylinder(self, name, x, y, z, radius, height) -> CollisionObject:
        co = CollisionObject()
        co.id = name
        co.header.frame_id = 'base_link'
        cyl = SolidPrimitive()
        cyl.type = SolidPrimitive.CYLINDER
        cyl.dimensions = [height, radius]  # [height, radius]
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        pose.orientation.w = 1.0
        co.primitives.append(cyl)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD
        return co

    def _publish_scene(self) -> None:
        if self._pub is None:
            return
        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects.clear()

        if bool(self.get_parameter('add_static_environment').value) and not self._static_ready:
            # table top surface collision
            scene.world.collision_objects.append(
                self._make_box('table', 0.15, 0.0, 0.75, 1.2, 0.8, 0.05))
            scene.world.collision_objects.append(
                self._make_box('obstacle_block', 0.18, 0.22, 0.81, 0.10, 0.10, 0.12))
            self._static_ready = True

        # dynamic targets as small collision boxes
        for tp in self._targets.poses:
            sx, sy, sz = 0.03, 0.03, 0.03
            if len(tp.size) >= 3:
                sx, sy, sz = tp.size[0], tp.size[1], tp.size[2]
            self.world_add(scene, tp.object_id, tp.pose.pose.position.x,
                           tp.pose.pose.position.y, tp.pose.pose.position.z, sx, sy, sz)

        self._pub.publish(scene)

    @staticmethod
    def world_add(scene, name, x, y, z, sx, sy, sz) -> None:
        co = CollisionObject()
        co.id = name
        co.header.frame_id = 'base_link'
        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [sx, sy, sz]
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        pose.orientation.w = 1.0
        co.primitives.append(box)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD
        scene.world.collision_objects.append(co)


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
