"""IntelliSort task manager: pick-and-place orchestration (BT-style).

Behavior-tree *style* runtime (Sequence / Fallback semantics) implemented as a
Python state machine. Canonical XML lives in bt/ for design docs & future
py_trees migration — it is not parsed at runtime.

PICK sequence:
  select -> pre-grasp -> open -> descend -> close (confirm) -> lift
PLACE:
  transport -> descend -> open -> retreat -> ready
"""
from __future__ import annotations

import threading
import time
import traceback

from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn

from intellisort_interfaces.action import ExecuteTask, PickPlace, Recovery
from intellisort_interfaces.msg import (
    ExceptionEvent,
    GraspCandidateArray,
    SystemMetrics,
    TargetPose,
    TargetPoseArray,
    TaskStatus,
)
from intellisort_interfaces.srv import GripperCommand

from intellisort_task.moveit_client import ARM_JOINTS, MoveItClient
from intellisort_task.workspace import (
    APPROACH_HEIGHT,
    CLASS_SLOT,
    GRASP_OFFSET,
    PLACE_CLEARANCE,
    SLOT_POSE,
    TABLE_TOP_Z,
)


class TaskManagerNode(LifecycleNode):
    def __init__(self) -> None:
        super().__init__('task_manager')
        self.declare_parameter('auto_run_demo', False)
        self.declare_parameter('max_targets', 6)
        self.declare_parameter('max_retries', 2)
        self.declare_parameter('enable_recovery', True)
        self.declare_parameter('cycle_timeout_sec', 60.0)
        self.declare_parameter('tip_link', 'tcp_link')
        self.declare_parameter('metrics_topic', '/task_metrics')

        self._cb_group = ReentrantCallbackGroup()
        self._targets: TargetPoseArray = TargetPoseArray()
        self._grasps: GraspCandidateArray = GraspCandidateArray()
        self._moveit: MoveItClient | None = None
        self._status_pub = None
        self._exception_pub = None
        self._metrics_pub = None
        self._gripper_cli = None
        self._recovery_cli = None
        self._demo_timer = None
        self._running = False
        self._run_lock = threading.Lock()
        self._metrics_timer = None

        # real metrics
        self._plan_ok = 0
        self._plan_total = 0
        self._grasp_ok = 0
        self._grasp_total = 0
        self._recover_ok = 0
        self._recover_total = 0
        self._completed = 0
        self._failed = 0
        self._cycle_times: list[float] = []

    # -------------------- lifecycle --------------------
    def on_configure(self, state) -> TransitionCallbackReturn:
        self._status_pub = self.create_lifecycle_publisher(TaskStatus, '/task_status', 10)
        self._exception_pub = self.create_lifecycle_publisher(
            ExceptionEvent, '/exception_events', 10)
        self._metrics_pub = self.create_lifecycle_publisher(
            SystemMetrics, '/system_metrics', 10)
        self.create_subscription(
            TargetPoseArray, '/target_poses', self._on_targets, 10)
        self.create_subscription(
            GraspCandidateArray, '/grasp_candidates', self._on_grasps, 10)
        self._gripper_cli = self.create_client(
            GripperCommand, '/gripper_command', callback_group=self._cb_group)
        self._recovery_cli = ActionClient(
            self, Recovery, '/recovery', callback_group=self._cb_group)
        self._moveit = MoveItClient(self)

        self._pick_place_server = ActionServer(
            self, PickPlace, '/pick_place',
            execute_callback=self._exec_pick_place,
            goal_callback=self._goal_cb,
            cancel_callback=self._cancel_cb,
            callback_group=self._cb_group)
        self._execute_server = ActionServer(
            self, ExecuteTask, '/execute_task',
            execute_callback=self._exec_task,
            goal_callback=self._goal_cb,
            cancel_callback=self._cancel_cb,
            callback_group=self._cb_group)

        self._metrics_timer = self.create_timer(2.0, self._publish_metrics)
        self.get_logger().info('Task manager configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state) -> TransitionCallbackReturn:
        for pub in (self._status_pub, self._exception_pub, self._metrics_pub):
            if pub:
                pub.on_activate(state)
        if self._moveit:
            self._moveit.wait_for_servers(timeout_sec=15.0)
        if bool(self.get_parameter('auto_run_demo').value) and self._demo_timer is None:
            self._demo_timer = self.create_timer(5.0, self._maybe_auto_demo)
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state) -> TransitionCallbackReturn:
        if self._demo_timer:
            self._demo_timer.cancel()
        for pub in (self._status_pub, self._exception_pub, self._metrics_pub):
            if pub:
                pub.on_deactivate(state)
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state) -> TransitionCallbackReturn:
        if self._metrics_timer:
            self._metrics_timer.cancel()
            self._metrics_timer = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS

    def _goal_cb(self, goal_request):
        return GoalResponse.ACCEPT

    def _cancel_cb(self, goal_handle):
        return CancelResponse.ACCEPT

    # -------------------- io --------------------
    def _on_targets(self, msg: TargetPoseArray) -> None:
        self._targets = msg

    def _on_grasps(self, msg: GraspCandidateArray) -> None:
        self._grasps = msg

    def _publish_status(self, task_id, phase, state, progress, message='') -> None:
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

    def _publish_exception(self, code, severity, description, recovery='') -> None:
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

    def _publish_metrics(self) -> None:
        if not self._metrics_pub:
            return
        m = SystemMetrics()
        m.header.stamp = self.get_clock().now().to_msg()
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
        self._metrics_pub.publish(m)

    # -------------------- recovery --------------------
    def _call_recovery(self, error_code: str, description: str) -> str:
        """Ask supervisor for a recovery action; returns action name."""
        self._publish_exception(error_code, 'RECOVERABLE', description, 'ask-supervisor')
        self._recover_total += 1
        if not self._recovery_cli.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn('recovery server unavailable — fallback retry')
            return 'retry'
        goal = Recovery.Goal()
        goal.error_code = error_code
        goal.description = description
        send_fut = self._recovery_cli.send_goal_async(goal)
        if not self._wait_future(send_fut, 3.0):
            return 'retry'
        handle = send_fut.result()
        if handle is None or not handle.accepted:
            return 'retry'
        res_fut = handle.get_result_async()
        if not self._wait_future(res_fut, 5.0):
            return 'retry'
        wrapped = res_fut.result()
        action = (wrapped.result.recovery_action if wrapped else 'retry') or 'retry'
        if wrapped and wrapped.result.success:
            self._recover_ok += 1
        return action

    def _wait_future(self, future, timeout_sec: float) -> bool:
        """Wait without nested spin (node is already on MultiThreadedExecutor)."""
        deadline = time.time() + timeout_sec
        while not future.done() and time.time() < deadline:
            time.sleep(0.02)
        return future.done()

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
        if not self._wait_future(future, timeout_sec):
            return False
        result = future.result()
        return bool(result and result.success)

    def _confirm_grasp(self, closed_position: float = 0.01) -> bool:
        """Grasp confirm: closed fingers should sit near the object width.

        gripper_server reports measured position; if it is still near the
        fully-open value the fingers never closed (missed / stalled).
        """
        if self._gripper_cli is None or not self._gripper_cli.wait_for_service(timeout_sec=1.0):
            return False
        req = GripperCommand.Request()
        req.position = closed_position
        req.max_effort = 20.0
        future = self._gripper_cli.call_async(req)
        if not self._wait_future(future, 3.0):
            return False
        result = future.result()
        if not result or not result.success:
            return False
        # fingers should not be fully open after a real grasp
        return result.reached_goal and result.position < 0.030

    # -------------------- core skill --------------------
    def _pick_and_place_one(
        self,
        target: TargetPose,
        place_slot: str,
        task_id: str,
        timeout_sec: float = 60.0,
    ) -> tuple[bool, str]:
        assert self._moveit is not None
        tip = str(self.get_parameter('tip_link').value)
        t0 = time.time()
        oid = target.object_id
        cls = target.object_class

        def timed_out() -> bool:
            return (time.time() - t0) > timeout_sec

        self._publish_status(task_id, 'PICK', 'RUNNING', 0.1, f'picking {oid}')

        # 1. grasp pose
        grasp_pose = None
        for g in self._grasps.candidates:
            if g.object_id == oid:
                grasp_pose = g.grasp_pose
                break
        if grasp_pose is None:
            grasp_pose = PoseStamped()
            grasp_pose.header = target.pose.header
            grasp_pose.header.frame_id = 'base_link'
            grasp_pose.pose = target.pose.pose
            grasp_pose.pose.position.z += GRASP_OFFSET

        pre = PoseStamped()
        pre.header = grasp_pose.header
        pre.header.frame_id = pre.header.frame_id or 'base_link'
        pre.pose = grasp_pose.pose
        pre.pose.position.z += APPROACH_HEIGHT

        # 2. approach
        self._publish_status(task_id, 'PICK', 'RUNNING', 0.2, f'approach {oid}')
        self._plan_total += 1
        ok, msg = self._moveit.plan_and_move_pose(pre, tip_link=tip)
        if not ok:
            action = self._call_recovery('PLAN_FAIL', f'approach: {msg}')
            if action in ('retry', 'replan'):
                self._plan_total += 1
                ok, msg = self._moveit.plan_and_move_pose(pre, tip_link=tip)
            elif action in ('skip', 'skip-target'):
                return False, f'skip after approach fail: {msg}'
            else:
                return False, f'approach failed: {msg}'
        if ok:
            self._plan_ok += 1
        else:
            return False, f'approach failed after retry: {msg}'

        if timed_out():
            return False, 'TIMEOUT after approach'

        # 3. open + descend
        self._gripper_move(0.035)
        self._publish_status(task_id, 'PICK', 'RUNNING', 0.35, f'descend {oid}')
        self._plan_total += 1
        ok, msg = self._moveit.plan_and_move_pose(grasp_pose, tip_link=tip)
        if ok:
            self._plan_ok += 1
        else:
            action = self._call_recovery('PLAN_FAIL', f'descend: {msg}')
            if action in ('retry', 'replan', 'clear-scene-replan'):
                self._plan_total += 1
                ok, msg = self._moveit.plan_and_move_pose(grasp_pose, tip_link=tip)
                if ok:
                    self._plan_ok += 1
            if not ok:
                self._gripper_move(0.035)
                return False, f'descend failed: {msg}'

        # 4. close + confirm (do NOT continue with empty gripper)
        self._publish_status(task_id, 'GRASP', 'RUNNING', 0.45, f'grasp {oid}')
        self._grasp_total += 1
        if not self._gripper_move(0.005):
            action = self._call_recovery('GRASP_FAIL', 'gripper close cmd failed')
            if not self._gripper_move(0.005):
                self._gripper_move(0.035)
                return False, 'gripper close failed'
        if not self._confirm_grasp(0.005):
            self._gripper_move(0.035)
            action = self._call_recovery('GRASP_FAIL', 'grasp confirm failed')
            if action in ('retry', 're-grasp'):
                self._gripper_move(0.035)
                self._plan_total += 1
                ok2, msg2 = self._moveit.plan_and_move_pose(grasp_pose, tip_link=tip)
                if ok2:
                    self._plan_ok += 1
                    self._gripper_move(0.005)
                    if self._confirm_grasp(0.005):
                        self._grasp_ok += 1
                    else:
                        return False, 'grasp confirm failed after retry'
                else:
                    return False, f'regrasp approach failed: {msg2}'
            else:
                return False, 'grasp confirm failed'
        else:
            self._grasp_ok += 1

        # 5. lift
        self._publish_status(task_id, 'PICK', 'RUNNING', 0.55, f'lift {oid}')
        lift = PoseStamped()
        lift.header = grasp_pose.header
        lift.pose = grasp_pose.pose
        lift.pose.position.z += APPROACH_HEIGHT
        ok, msg = self._moveit.plan_and_move_pose(lift, tip_link=tip)
        if not ok:
            self._gripper_move(0.035)
            return False, f'lift failed: {msg}'

        if timed_out():
            self._gripper_move(0.035)
            return False, 'TIMEOUT before place'

        # 6. place
        slot_xyz = SLOT_POSE.get(place_slot, SLOT_POSE['slot_a'])
        place_pre = PoseStamped()
        place_pre.header.frame_id = 'base_link'
        place_pre.pose.position.x = slot_xyz[0]
        place_pre.pose.position.y = slot_xyz[1]
        place_pre.pose.position.z = slot_xyz[2] + APPROACH_HEIGHT
        place_pre.pose.orientation.x = 1.0
        place_pre.pose.orientation.w = 0.0

        place = PoseStamped()
        place.header.frame_id = 'base_link'
        place.pose.position.x = slot_xyz[0]
        place.pose.position.y = slot_xyz[1]
        place.pose.position.z = slot_xyz[2] + PLACE_CLEARANCE
        place.pose.orientation.x = 1.0
        place.pose.orientation.w = 0.0

        self._publish_status(
            task_id, 'PLACE', 'RUNNING', 0.75,
            f'transport {oid} to {place_slot} ({cls})')
        self._plan_total += 1
        ok, msg = self._moveit.plan_and_move_pose(place_pre, tip_link=tip)
        if not ok:
            action = self._call_recovery('PLAN_FAIL', f'place approach: {msg}')
            if action in ('retry', 'replan'):
                self._plan_total += 1
                ok, msg = self._moveit.plan_and_move_pose(place_pre, tip_link=tip)
            if not ok:
                self._gripper_move(0.035)
                return False, f'place approach failed: {msg}'
        else:
            self._plan_ok += 1

        ok, msg = self._moveit.plan_and_move_pose(place, tip_link=tip)
        if not ok:
            self._gripper_move(0.035)
            return False, f'place descend failed: {msg}'

        self._gripper_move(0.035)

        self._publish_status(task_id, 'PLACE', 'RUNNING', 0.9, f'retreat after {oid}')
        self._moveit.move_named('ready')
        return True, 'ok'

    # -------------------- actions --------------------
    def _exec_pick_place(self, goal_handle):
        goal = goal_handle.request
        task_id = goal.object_id or 'pick_place'
        result = PickPlace.Result()
        t0 = time.time()

        target = None
        if goal.object_id:
            for tp in self._targets.poses:
                if tp.object_id == goal.object_id:
                    target = tp
                    break
            if target is None:
                # do NOT silently pick another object
                result.success = False
                result.error_code = 'DETECT_FAIL'
                result.message = f'object_id {goal.object_id} not found'
                goal_handle.abort()
                return result
        elif goal.object_class:
            for tp in self._targets.poses:
                if tp.object_class == goal.object_class:
                    target = tp
                    break
        if target is None:
            result.success = False
            result.error_code = 'DETECT_FAIL'
            result.message = 'no matching target'
            goal_handle.abort()
            return result

        if goal.target_pose.header.frame_id:
            # honor explicit pose if provided
            target = TargetPose()
            target.object_id = goal.object_id or 'explicit'
            target.object_class = goal.object_class or 'unknown'
            target.pose = goal.target_pose
            target.confidence = 1.0
            target.size = [0.03, 0.03, 0.03]

        slot = goal.place_slot or CLASS_SLOT.get(target.object_class, 'slot_a')
        timeout = float(goal.timeout_sec) if goal.timeout_sec > 0 else float(
            self.get_parameter('cycle_timeout_sec').value)

        ok, msg = self._pick_and_place_one(target, slot, task_id, timeout_sec=timeout)
        result.success = ok
        result.error_code = 'OK' if ok else 'PICK_PLACE_FAIL'
        result.message = msg
        result.duration_sec = float(time.time() - t0)
        if ok:
            self._completed += 1
            self._cycle_times.append(result.duration_sec)
            self._publish_status(task_id, 'DONE', 'SUCCESS', 1.0, msg)
            goal_handle.succeed()
        else:
            self._failed += 1
            self._publish_status(task_id, 'DONE', 'FAILED', 1.0, msg)
            goal_handle.abort()
        return result

    def _exec_task(self, goal_handle):
        goal = goal_handle.request
        task_id = goal.task_id or 'demo_task'
        result = ExecuteTask.Result()
        t0 = time.time()

        with self._run_lock:
            self._running = True

        max_targets = int(goal.max_targets) or int(self.get_parameter('max_targets').value)
        enable_recovery = bool(goal.enable_recovery)
        completed = 0
        failed = 0
        done_ids: set[str] = set()

        try:
            # wait briefly for perception / synthetic targets
            time.sleep(1.0)

            allowed = set(goal.object_classes) if goal.object_classes else None
            attempts = 0
            while (completed + failed) < max_targets and attempts < max_targets * 2:
                if goal_handle.is_cancel_requested:
                    self._moveit.move_named('ready')
                    self._gripper_move(0.035)
                    self._publish_status(task_id, 'DONE', 'CANCELLED', 1.0, 'cancelled')
                    result.completed = completed
                    result.failed = failed
                    result.duration_sec = float(time.time() - t0)
                    result.success = False
                    result.message = 'cancelled'
                    goal_handle.canceled()
                    return result

                attempts += 1
                target = None
                for tp in self._targets.poses:
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
                    slot = goal.place_slots[(completed + failed) % len(goal.place_slots)]

                self._publish_status(
                    task_id, 'CYCLE', 'RUNNING',
                    (completed + failed) / float(max_targets),
                    f'process {target.object_id}')
                fb = ExecuteTask.Feedback()
                fb.phase = 'CYCLE'
                fb.progress = (completed + failed) / float(max_targets)
                fb.completed = completed
                fb.failed = failed
                fb.message = target.object_id
                goal_handle.publish_feedback(fb)

                timeout = float(self.get_parameter('cycle_timeout_sec').value)
                ok, msg = self._pick_and_place_one(
                    target, slot, task_id, timeout_sec=timeout)
                done_ids.add(target.object_id)
                if ok:
                    completed += 1
                else:
                    failed += 1
                    if not enable_recovery:
                        break

            # success criterion: all attempted succeeded, or at least one done
            # and no more than max(1, 20%) failures — strict for acceptance
            total = completed + failed
            result.completed = completed
            result.failed = failed
            result.duration_sec = float(time.time() - t0)
            if total == 0:
                result.success = False
                result.message = 'no targets processed'
            else:
                result.success = (failed == 0) or (
                    completed > 0 and failed <= max(1, total // 5))
                result.message = f'completed={completed} failed={failed}'

            self._completed += completed
            self._failed += failed
            if result.success:
                self._cycle_times.append(result.duration_sec)
                self._publish_status(task_id, 'DONE', 'SUCCESS', 1.0, result.message)
                goal_handle.succeed()
            else:
                self._publish_status(task_id, 'DONE', 'FAILED', 1.0, result.message)
                goal_handle.abort()
            return result
        finally:
            with self._run_lock:
                self._running = False

    # -------------------- auto demo --------------------
    def _maybe_auto_demo(self) -> None:
        with self._run_lock:
            if self._running:
                return
            if not self._targets.poses:
                return
            self._running = True

        def _run():
            try:
                self.get_logger().info('Auto demo starting')
                time.sleep(0.5)
                max_t = int(self.get_parameter('max_targets').value)
                completed = failed = 0
                done_ids: set[str] = set()
                for tp in list(self._targets.poses)[:max_t]:
                    if tp.object_id in done_ids:
                        continue
                    slot = CLASS_SLOT.get(tp.object_class, 'slot_a')
                    ok, msg = self._pick_and_place_one(
                        tp, slot, 'auto_demo',
                        timeout_sec=float(self.get_parameter('cycle_timeout_sec').value))
                    done_ids.add(tp.object_id)
                    if ok:
                        completed += 1
                    else:
                        failed += 1
                self._completed += completed
                self._failed += failed
                state = 'SUCCESS' if completed and not failed else (
                    'SUCCESS' if completed else 'FAILED')
                self._publish_status(
                    'auto_demo', 'DONE', state, 1.0,
                    f'auto demo completed={completed} failed={failed}')
                self.get_logger().info(
                    f'Auto demo done completed={completed} failed={failed}')
            except Exception:  # noqa: BLE001
                self.get_logger().error(traceback.format_exc())
            finally:
                with self._run_lock:
                    self._running = False

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
