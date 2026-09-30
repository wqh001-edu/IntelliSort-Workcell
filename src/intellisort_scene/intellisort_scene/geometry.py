"""Pure geometry helpers for PlanningScene (no ROS node deps in factory)."""
from __future__ import annotations

from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive


def make_box(name, x, y, z, sx, sy, sz, frame_id='base_link') -> CollisionObject:
    co = CollisionObject()
    co.id = name
    co.header.frame_id = frame_id
    box = SolidPrimitive()
    box.type = SolidPrimitive.BOX
    box.dimensions = [float(sx), float(sy), float(sz)]
    pose = Pose()
    pose.position.x = float(x)
    pose.position.y = float(y)
    pose.position.z = float(z)
    pose.orientation.w = 1.0
    co.primitives.append(box)
    co.primitive_poses.append(pose)
    co.operation = CollisionObject.ADD
    return co
