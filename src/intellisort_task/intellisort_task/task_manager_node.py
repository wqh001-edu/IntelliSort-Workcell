"""IntelliSort task manager: pick-and-place behavior orchestration.

Implements a lightweight behavior-tree style loop:
  Perceive -> SelectTarget -> BuildScene -> PlanPick -> ExecutePick
  -> ConfirmGrasp -> PlanPlace -> ExecutePlace -> ConfirmPlace
with Recovery on failure (retry / replan / skip).
"""
from __future__ import annotations

import time
import traceback

from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.action import ExecuteTask, PickPlace
from intellisort_interfaces.msg import (
    ExceptionEvent,
    GraspCandidateArray,
    TargetPose,
    TargetPoseArray,
    TaskStatus,
)
from intellisort_interfaces.srv import GripperCommand

from intellisort_task.moveit_client import MoveItClient


# Class -> place slot mapping (multiclass sorting)
CLASS_SLOT = {
    'red': 'slot_a',
    'green': 'slot_b',
    'blue': 'slot_c',
    'yellow': 'slot_a',
}

SLOT_POSE = {
    'slot_a': (0.35, 0.28, 0.77),
    'slot_b': (0.48, 0.12, 0.77),
    'slot_c': (0.48, -0.12, 0.77),
}

APPROACH_HEIGHT = 0.12
GRASP_OFFSET = 0.02
PLACE_HEIGHT = 0.12


class TaskManagerNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('task_manager')
        self.declare_parameter('auto_run_demo', True)
        self.declare_parameter('max_targets', 6)
        self.declare_parameter('max_retries', 2)
        self.declare_parameter('enable_recovery', True)
        self.declare_parameter('cycle_timeout_sec', 60.0)

        self._cb_group = ReentrantCallbackGroup()
        self._targets: TargetPoseArray = TargetPoseArray()
        self._grasps: GraspCandidateArray = GraspCandidateArray()
        self._moveit: MoveItClient | None = None
        self._status_pub = None
        self._exception_pub = None
        self._gripper_cli = None
        self._pick_place_server = None
        self._execute_server = None
        self._demo_timer = None
        self._running = False

        # metrics
        self._completed = 0
        self._failed = 0
        self._plan_ok = 0
        self._plan_total = 0
        self._grasp_ok = 0
        self._grasp_total = 0

    # -------------------- lifecycle --------------------
    def on_configure(self, state) -> TransitionCallbackReturn:
        self._status_pub = self.create_lifecycle_publisher(
            TaskStatus, '/task_status', 10)
        self._exception_pub = self.create_lifecycle_publisher(
            ExceptionEvent, '/exception_events', 10)
        self.create_subscription(
            TargetPoseArray, '/target_poses', self._on_targets, 10)
        self.create_subscription(
            GraspCandidateArray, '/grasp_candidates', self._on_grasps, 10)

        self._gripper_cli = self.create_client(
            GripperCommand, '/gripper_command')
        self._moveit = MoveItClient(self)

        self._pick_place_server = ActionServer(
            self, PickPlace, '/pick_place',
            execute_callback=self._exec_pick_place,
            callback_group=self._cb_group)
        self._execute_server = ActionServer(
            self, ExecuteTask, '/execute_task',
            execute_callback=self._exec_task,
            callback_group=self._cb_group)

        self.get_logger().info('Task manager configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state) -> TransitionCallbackReturn:
        if self._status_pub:
            self._status_pub.on_activate(state)
        if self._exception_pub:
            self._exception_pub.on_activate(state)
        if self._moveit:
            self._moveit.wait_for_servers(timeout_sec=15.0)
        if bool(self.get_parameter('auto_run_demo').value) and self._demo_timer is None:
            self._demo_timer = self.create_timer(3.0, self._maybe_auto_demo)
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        if self._demo_timer:
            self._demo_timer.cancel()
        if self._status_pub:
            self._status_pub.on_deactivate(state)
        if self._exception_pub:
            self._exception_pub.on_deactivate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    # -------------------- subscriptions --------------------
    def _on_targets(self, msg: TargetPoseArray) -> None:
        self._targets = msg

    def _on_grasps(self, msg: GraspCandidateArray) -> None:
        self._grasps = msg

    # -------------------- feedback helpers --------------------
    def _publish_status(self, task_id: str, phase: str, state: str,
                        progress: float, message: str = '') -> None:
        if not self._status_pub:
            return
        msg = TaskStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.task_id = task_id
        msg.phase = phase
        msg.state = state
        msg.progress = float(progress)
        msg.message = message
        self._status_pub.publish(msg)

    def _publish_exception(self, code: str, severity: str,
                           description: str, recovery: str = '') -> None:
        if not self._exception_pub:
            return
        msg = ExceptionEvent()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.error_code = code
        msg.severity = severity
        msg.description = description
        msg.recovery_action = recovery
        self._exception_pub.publish(msg)
        self.get_logger().warn(f'[{code}] {description} -> {recovery}')

    # -------------------- gripper --------------------
    def _gripper_move(self, position: float, timeout_sec: float = 3.0) -> bool:
        if self._gripper_cli is None:
            return False
        if not self._gripper_cli.wait_for_service(timeout_sec=timeout_sec):
            self.get_logger().warn('gripper service unavailable')
            return False
        req = GripperCommand.Request()
        req.position = float(position)
        req.max_effort = 20.0
        future = self._gripper_cli.call_async(req)
        import rclpy
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if not future.done() or future.result() is None:
            return False
        return bool(future.result().success)

    # -------------------- core skill --------------------
    def _pick_and_place_one(
        self,
        target: TargetPose,
        place_slot: str,
        task_id: str,
        feedback_cb=None,
    ) -> tuple[bool, str]:
        assert self._moveit is not None
        cls = target.object_class
        self._publish_status(task_id, 'PICK', 'RUNNING', 0.15,
                             f'picking {target.object_id}')

        # 1. Find best grasp for this object
        grasp_pose = None
        for g in self._grasps.candidates:
            if g.object_id == target.object_id:
                grasp_pose = g.grasp_pose
                break
        if grasp_pose is None:
            # fallback top-down from target pose
            grasp_pose = PoseStamped()
            grasp_pose.header = target.pose.header
            grasp_pose.header.frame_id = 'base_link'
            grasp_pose.pose = target.pose.pose
            grasp_pose.pose.position.z += GRASP_OFFSET

        # 2. Pre-grasp (approach)
        pre = PoseStamped()
        pre.header = grasp_pose.header
        pre.pose = grasp_pose.pose
        pre.pose.position.z += APPROACH_HEIGHT

        self._publish_status(task_id, 'PICK', 'RUNNING', 0.25, 'approach')
        self._plan_total += 1
        ok, msg = self._moveit.plan_and_move_pose(pre, tip_link='tcp_link')
        if not ok:
            self._publish_exception('PLAN_FAIL', 'RECOVERABLE', msg, 'retry')
            self._plan_total += 1
            ok, msg = self._moveit.plan_and_move_pose(pre, tip_link='tcp_link')
        if ok:
            self._plan_ok += 1
        else:
            return False, f'approach failed: {msg}'

        # 3. Open gripper
        self._gripper_move(0.035)

        # 4. Grasp descent
        self._publish_status(task_id, 'PICK', 'RUNNING', 0.4, 'descend')
        self._plan_total += 1
        ok, msg = self._moveit.plan_and_move_pose(grasp_pose, tip_link='tcp_link')
        if ok:
            self._plan_ok += 1
        else:
            self._publish_exception('PLAN_FAIL', 'RECOVERABLE', msg, 'skip_object')
            return False, f'descend failed: {msg}'

        # 5. Close gripper (simulate grasp)
        self._grasp_total += 1
        closed = self._gripper_move(0.0)
        if closed:
            self._grasp_ok += 1
        else:
            self._publish_exception('GRASP_FAIL', 'RECOVERABLE',
                                    'gripper close failed', 'retry')
            self._gripper_move(0.0)

        # 6. Lift
        self._publish_status(task_id, 'PICK', 'RUNNING', 0.55, 'lift')
        lift = PoseStamped()
        lift.header = grasp_pose.header
        lift.pose = grasp_pose.pose
        lift.pose.position.z += APPROACH_HEIGHT
        ok, msg = self._moveit.plan_and_move_pose(lift, tip_link='tcp_link')
        if not ok:
            self._gripper_move(0.035)
            return False, f'lift failed: {msg}'

        # 7. Place
        slot_xyz = SLOT_POSE.get(place_slot, SLOT_POSE['slot_a'])
        place_pre = PoseStamped()
        place_pre.header.frame_id = 'base_link'
        place_pre.pose.position.x = slot_xyz[0]
        place_pre.pose.position.y = slot_xyz[1]
        place_pre.pose.position.z = slot_xyz[2] + PLACE_HEIGHT
        place_pre.pose.orientation.x = 1.0
        place_pre.pose.orientation.w = 0.0

        place = PoseStamped()
        place.header.frame_id = 'base_link'
        place.pose.position.x = slot_xyz[0]
        place.pose.position.y = slot_xyz[1]
        place.pose.position.z = slot_xyz[2] + 0.03
        place.pose.orientation.x = 1.0
        place.pose.orientation.w = 0.0

        self._publish_status(task_id, 'PLACE', 'RUNNING', 0.75,
                             f'transport to {place_slot} ({cls})')
        ok, msg = self._moveit.plan_and_move_pose(place_pre, tip_link='tcp_link')
        if not ok:
            self._publish_exception('PLAN_FAIL', 'RECOVERABLE', msg, 'retry_place')
            ok, msg = self._moveit.plan_and_move_pose(place_pre, tip_link='tcp_link')
        if not ok:
            self._gripper_move(0.035)
            return False, f'place approach failed: {msg}'

        ok, msg = self._moveit.plan_and_move_pose(place, tip_link='tcp_link')
        if not ok:
            self._gripper_move(0.035)
            return False, f'place descend failed: {msg}'

        self._gripper_move(0.035)

        # 8. Retreat to ready
        self._publish_status(task_id, 'PLACE', 'RUNNING', 0.9, 'retreat')
        self._moveit.move_named('ready')
        return True, 'ok'

    # -------------------- action servers --------------------
    def _exec_pick_place(self, goal_handle):
        goal = goal_handle.request
        task_id = goal.object_id or 'pick_place'
        feedback = PickPlace.Feedback()
        result = PickPlace.Result()
        t0 = time.time()

        target = None
        for tp in self._targets.poses:
            if tp.object_id == goal.object_id or (
                not goal.object_id and tp.object_class == goal.object_class):
                target = tp
                break
        if target is None and self._targets.poses:
            target = self._targets.poses[0]
        if target is None:
            result.success = False
            result.error_code = 'DETECT_FAIL'
            result.message = 'no target'
            goal_handle.abort()
            return result

        slot = goal.place_slot or CLASS_SLOT.get(target.object_class, 'slot_a')
        ok, msg = self._pick_and_place_one(target, slot, task_id)
        result.success = ok
        result.error_code = 'OK' if ok else 'PICK_PLACE_FAIL'
        result.message = msg
        result.duration_sec = float(time.time() - t0)
        if ok:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        return result

    def _exec_task(self, goal_handle):
        goal = goal_handle.request
        task_id = goal.task_id or 'demo_task'
        result = ExecuteTask.Result()
        feedback = ExecuteTask.Feedback()
        t0 = time.time()
        self._running = True

        max_targets = int(goal.max_targets) or int(self.get_parameter('max_targets').value)
        enable_recovery = bool(goal.enable_recovery)
        completed = 0
        failed = 0

        # Wait briefly for perception to fill targets
        time.sleep(1.5)

        candidates = list(self._targets.poses)
        if not goal.object_classes:
            allowed = None
        else:
            allowed = set(goal.object_classes)

        done_ids = set()
        attempts = 0
        while self._running and (completed + failed) < max_targets and attempts < max_targets * 2:
            attempts += 1
            target = None
            for tp in candidates:
                if tp.object_id in done_ids:
                    continue
                if allowed and tp.object_class not in allowed:
                    continue
                target = tp
                break
            if target is None:
                break

            slot = CLASS_SLOT.get(target.object_class, 'slot_a')
            if goal.place_slots:
                # rotate through provided slots
                slot = goal.place_slots[completed % len(goal.place_slots)]

            self._publish_status(
                task_id, 'CYCLE', 'RUNNING',
                (completed + failed) / float(max_targets),
                f'process {target.object_id}')
            feedback.phase = 'CYCLE'
            feedback.progress = (completed + failed) / float(max_targets)
            feedback.completed = completed
            feedback.failed = failed
            feedback.message = target.object_id
            goal_handle.publish_feedback(feedback)

            ok, msg = self._pick_and_place_one(target, slot, task_id)
            if ok:
                completed += 1
                done_ids.add(target.object_id)
            else:
                failed += 1
                done_ids.add(target.object_id)
                self._publish_exception('TASK_FAIL', 'RECOVERABLE', msg, 'skip')
                if not enable_recovery:
                    break

        result.completed = completed
        result.failed = failed
        result.duration_sec = float(time.time() - t0)
        result.success = completed > 0 and failed <= completed
        result.message = f'completed={completed} failed={failed}'
        self._publish_status(task_id, 'DONE',
                             'SUCCESS' if result.success else 'FAILED',
                             1.0, result.message)
        if result.success:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        return result

    # -------------------- auto demo --------------------
    def _maybe_auto_demo(self) -> None:
        if self._running:
            return
        if not self._targets.poses and not self._grasps.candidates:
            return
        self._running = True

        def _run():
            try:
                self.get_logger().info('Auto demo starting')
                time.sleep(0.5)
                max_t = int(self.get_parameter('max_targets').value)
                completed = failed = 0
                seen = set()
                for tp in list(self._targets.poses)[:max_t]:
                    if self._running is False:
                        break
                    slot = CLASS_SLOT.get(tp.object_class, 'slot_a')
                    ok, msg = self._pick_and_place_one(tp, slot, 'auto_demo')
                    if ok:
                        completed += 1
                    else:
                        failed += 1
                    seen.add(tp.object_id)
                self._publish_status(
                    'auto_demo', 'DONE',
                    'SUCCESS' if completed else 'FAILED',
                    1.0, f'auto demo finished completed={completed} failed={failed}')
                self.get_logger().info(
                    f'Auto demo done completed={completed} failed={failed}')
            except Exception:  # noqa: BLE001
                self.get_logger().error(traceback.format_exc())
            finally:
                self._running = False

        import threading
        threading.Thread(target=_run, daemon=True).start()


def main(args=None) -> None:
    import rclpy
    rclpy.init(args=args)
    node = TaskManagerNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        node.trigger_configure()
        node.trigger_activate()
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
