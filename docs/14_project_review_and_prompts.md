# 14 · 项目深度体检报告 & 修复提示词

> **修复状态（本轮）**  
> - [x] A 场景碰撞：抓取前 REMOVE 目标盒、失败恢复、桌面顶面 z=0.75 与 URDF 对齐  
> - [x] B 指标去假：`/system_metrics` 来自真实 `_plan/_grasp/_recover/_cycle` 计数  
> - [x] C task bug：`_running` finally 复位、空爪禁止搬运、object_id 不静默替换、cancel、timeout、去死变量  
> - [x] D 恢复闭环：task_manager 调用 `/recovery`，supervisor 策略表 + 窗口限次 + `/recovery_events`  
> - [x] E 夹爪反馈：joint_states 到位判定；MoveIt 只管 arm，夹爪走 `/gripper_command`  
> - [x] F 位姿：K + 相机外参 + 桌面射线求交（参数可标定）；grasp yaw 轴修正  
> - [x] G 硬件抽象：文档降级为「模式标记 + 迁移清单」，与代码一致  
> - [x] H 测试：run_pick_demo 退出码、smoke 断言、inject_faults、unittest、CI 跑测试  
> - [x] I 文档/门户：行为树表述、DoD 状态标记、指标口径  
> - [x] J 接口：workspace 单源常量、synthetic 可停发/可关 grasp、tip_link 参数化  
>  
> 仍为后续项：暂停/继续、驱动热切换、真机闭环、launch_testing 全链路。

> 审查范围：`src/` 12 个 ROS2 包、`tests/`、`tools/`、CI、`docs/`、HTML 门户  
> 审查方式：逐文件阅读 + 交叉核对「文档声称 vs 代码实现」  
> 结论日期：基于当前工作区状态

---

## 0. 一句话结论

**骨架完整、文档精美、主链路能看懂，但离「完善」还差一截：多处关键能力是假实现/空壳/未接线，且有 2 个几何问题会直接让抓取规划失败。**  
按毕业设计/作品集演示：**目前约 65–70 分**（架构完整、可讲解）；按工程验收标准：**约 40–50 分**（指标造假、恢复空转、测试不可失败）。

---

## 1. 总体评分卡

| 维度 | 得分 | 说明 |
|------|------|------|
| 系统架构 | 8/10 | 分层清晰，12 包职责合理，接口命名自洽 |
| 机器人模型 / URDF | 7/10 | 六轴+夹爪+相机完整，但全是几何基元，meshes/ 空 |
| 感知 | 5/10 | HSV 检测是真的；位姿是拍脑袋仿射映射，深度/CameraInfo 未用 |
| 抓取 | 6/10 | 候选生成闭环，但 yaw 轴写错、评分极简 |
| 运动规划 / MoveIt | 7/10 | 配置基本自洽；夹爪控制器类型错配；tip_link 不一致 |
| 场景管理 | 4/10 | **目标碰撞盒不移除/不放行，桌面高 2.5cm**，会阻塞抓取 |
| 任务编排 | 6/10 | 抓放序列完整；确认/超时/取消/指标未闭合；有真 bug |
| 异常恢复 | 2/10 | supervisor 空壳，`/recovery` 无人调用 |
| 硬件抽象 | 2/10 | mode_manager 只改自己参数，无任何驱动 adapter |
| 指标与测试 | 2/10 | **核心指标硬编码造假**；测试恒绿、0 断言 |
| 文档 | 7/10 | 结构好，但多处夸大（行为树/暂停/恢复率/硬件抽象） |
| HTML 门户 | 7/10 | 26 页可跑，但阶段验收未做、学习卡片占位 |

---

## 2. 做得好的地方（值得保留）

1. **包划分专业**：interfaces / description / control / gazebo / moveit_config / perception / grasp / scene / task / hw_abstraction / bringup / demo，职责边界清楚。
2. **接口层完整**：9 msg + 3 srv + 3 action，CMakeLists 生成规则正确，核心 topic 链路自洽。
3. **`_pick_and_place_one` 是真业务**：接近→开爪→下降→闭爪→抬起→放置→回 ready，是仓库里最完整的函数。
4. **synthetic_targets 与 Gazebo world 坐标对齐**：demo 不依赖相机也能跑通任务层。
5. **LifecycleNode 使用规范**（perception/grasp/scene），资源释放意识好。
6. **HTML 门户无空链接**，26 路由齐全，架构图/知识下钻做得认真。
7. **CMake 包安装规则正确**，entry_points 与 launch/文档命令一致。

---

## 3. 关键问题清单（按优先级）

### P0 · 会直接让 Demo 失败或产出假数据

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **被抓目标被加为碰撞盒且从不移除/放行** | `scene_builder_node.py:114-119` | 抓取下探必碰撞，规划大概率失败 |
| 2 | **桌面碰撞盒比真实桌面高 2.5cm** | `scene_builder_node.py:107-108`（z 顶面 0.775 vs URDF 0.75） | 手指落在桌子碰撞体内部 |
| 3 | **规划/抓取/恢复成功率、节拍硬编码** | `metric_publisher_node.py:55-58` 写死 0.95/0.9/0.75/18.0 | 对外指标全是假的 |
| 4 | **`_running` 在 `/execute_task` 结束后永不复位** | `task_manager_node.py:344` vs 402-414 | 跑过一次 action 后 auto demo 永久失效 |
| 5 | **Gazebo 控制器加载竞态** | `gazebo_workcell.launch.py:52-74` 与 Gazebo 并行、无重试 | 一键 bringup 高概率缺控制器 |
| 6 | **`run_pick_demo` 失败时 exit code 仍为 0** | `run_pick_demo.py:53-67` | 验收脚本永远绿 |

### P1 · 能力名不副实 / 半成品

| # | 问题 | 位置 |
|---|------|------|
| 7 | supervisor 只打日志+返回策略字符串，恢复动作零实现；`/recovery` 全库无客户端 | `supervisor_node.py:54-78` |
| 8 | gripper_server 恒 `success=True/reached_goal=True`，ConfirmGrasp 无意义 | `gripper_server_node.py:36-40` |
| 9 | 位姿估计是固定仿射映射，深度读了只 `pass`，CameraInfo 不用 | `pose_estimator_node.py:147-177` |
| 10 | 行为树 XML 从未被加载/解析，实为手写循环 | `bt/*.xml` vs `task_manager_node.py` |
| 11 | mode_manager 只改自身参数，无驱动切换；`hw_mode.yaml` 不安装也不读 | `mode_manager.py` + `setup.py` |
| 12 | grasp "yaw 样本"实际绕 X 滚转，轴写错 | `grasp_planner_node.py:94-105` |
| 13 | 抓取失败仍继续搬运（无 return False） | `task_manager_node.py:243-250` |
| 14 | MoveIt 夹爪控制器声明 `GripperCommand`，ros2_control 实际是 `JointGroupPositionController` | `moveit_controllers.yaml` vs `isc_controllers.yaml` |
| 15 | tip_link 不一致：SRDF=`tool0`，task 传 `tcp_link` | `moveit_client.py:64` vs `task_manager_node.py` |
| 16 | `PickPlace.action` 的 `target_pose`/`timeout_sec` 字段被完全忽略 | `task_manager_node.py:305-336` |
| 17 | 槽位坐标双份且冲突：task z=0.77 vs workspace z=0.75 | `task_manager_node.py:41-43` vs `workspace_state_node.py` |
| 18 | docs/07「可暂停/继续」无任何实现 | 全库无 cancel/pause |
| 19 | `intellisort_task/package.xml` 声明不存在的 `rclpy_action` | `package.xml:11` |
| 20 | 并发隐患：对已在 MultiThreadedExecutor 的节点再 `spin_until_future_complete` | `task_manager_node.py:177-179`、`moveit_client.py:54-58` |

### P2 · 完善度 / 一致性 / 测试

| # | 问题 |
|---|------|
| 21 | 测试只有 2 个恒绿 shell 脚本，0 单元测试、0 断言、CI 不跑 test |
| 22 | `tests/run_smoke.sh` 全部 `\|\| true` 吞错 |
| 23 | 文档夸大：行为树、异常恢复率、硬件抽象、成功率阈值 |
| 24 | HTML 门户：阶段验收/进度页未做（CSS 残留）；学习卡片占位文案；DoD 打钩与实现不符 |
| 25 | `/get_workspace_state`、`/recovery`、`/set_mode` 无客户端；`Detection.track_id` 恒 -1 |
| 26 | `system.yaml` 的 `task_manager` 段从未加载；`cycle_timeout_sec`/`max_retries` 声明未用 |
| 27 | synthetic_targets 1Hz 永久重发已抓走的零件；`seen` 死变量 |
| 28 | meshes/、gazebo/models/、assets/ 为空目录 |
| 29 | `data.js` meta 块死数据；GitHub 链接不可点 |
| 30 | 自动恢复计数 `_recoveries` 永不重置 |

---

## 4. 「文档声称 vs 真实实现」对照

| 声称 | 出处 | 真相 |
|------|------|------|
| 规划≥95%/抓取≥85%/恢复≥70%/节拍12-25s 且可统计 | docs/10、DoD | 指标写死 0.95/0.9/0.75/18.0 |
| 异常恢复 / ≥6 类策略落地 | README、DoD | supervisor 空壳，实际只 retry/skip |
| 行为树任务编排 | README、docs/07 | XML 不加载，手写 while |
| 可暂停/继续 | docs/07 | 未实现 |
| 硬件抽象 sim/xarm/real | README、docs/09 | 只改自身参数 |
| 位姿=检测+深度+CameraInfo | docs/04 | 仿射映射，深度 `pass` |
| 一键启动最终 Demo | README、docs/11 | 需 3 终端 + 控制器竞态 |
| 阶段验收/进度（HTML） | README、docs/13 | 页面不存在 |
| 每页学习卡片 | docs/13 | 仅 5 页有，且 html 页是模板句 |

---

## 5. 修复提示词（可直接复制给 AI / 开发用）

> 用法：按优先级逐条执行；每条提示词可单独开一轮会话。  
> 前置约定：Ubuntu 22.04 + ROS2 Humble；仓库根为 `~/intellisort_ws`（或按你的布局）；改完必须 `colcon build` 并跑通对应验证命令。

### 提示词 A · 【P0】修复场景碰撞，打通抓取规划

```text
你在 ROS2 Humble 机械臂项目 IntelliSort Workcell 工作。请修复 PlanningScene 几何问题，否则 MoveIt 抓取规划会失败。

【必改 1】src/intellisort_scene/intellisort_scene/scene_builder_node.py
问题：目标物被加为碰撞盒（约 L114-119），但抓取时 tcp/手指要伸进目标内部；目标从不 REMOVE/放行。
要求：
1. 抓取执行前，把当前目标的碰撞盒从 PlanningScene REMOVE，或对 gripper 相关 link 与该目标 ID 设置 AllowedCollisionMatrix 放行。
2. 目标被抓走后（task_manager 成功放置），同步 REMOVE 该目标碰撞盒，避免场景残留。
3. 建议接口：scene_builder 增加服务或订阅 task_manager 的阶段事件（如 /task_status phase=PICK/PLACE）来触发放行/移除；或由 task_manager 通过 /planning_scene 直接发 diff。
4. 保持 is_diff=True 的增量更新语义。

【必改 2】桌面碰撞盒高度
问题：L107-108 桌盒 z 中心 0.75、高 0.05 → 顶面 0.775；URDF workstation.urdf.xacro 桌面顶面在 z=0.75。
要求：调整 scene 中 table 碰撞盒，使顶面 = 0.75（与 URDF 一致），并避免与 URDF 中 table_link 重复建模（二选一：只信 URDF，或 scene 只补 URDF 没有的障碍）。

【必改 3】清理死代码：_make_cylinder 未调用、world_add 与 _make_box 重复，合并为一个工厂函数。

【验证】
- ros2 launch intellisort_bringup demo.launch.py
- 跑 run_pick_demo，确认 PlanPick/Descend 不再因「与目标物碰撞」失败
- ros2 service call 或 echo /planning_scene 确认目标盒在抓取时被放行/移除
```

### 提示词 B · 【P0】指标去假，接真实计数

```text
项目 IntelliSort Workcell。metric_publisher_node.py:55-58 把规划/抓取/恢复成功率和节拍写死为 0.95/0.9/0.75/18.0，这是假数据，必须改成真实统计。

要求：
1. task_manager_node.py 已有 _plan_ok/_plan_total/_grasp_ok/_grasp_total，但只累加不外发。把这些计数随 /task_status 或新增轻量 msg（如 IntellisortMetricsSample）周期发布；或 metric_publisher 通过 topic/service 拉取。
2. metric_publisher_node.py 删除硬编码：
   - plan_success_rate = _plan_ok/_plan_total（分母 0 时给 NaN 或 1.0 并标注）
   - grasp_success_rate 同理
   - recovery_success_rate：由 supervisor 真实统计（见提示词 D），若暂无恢复实现则发布 0.0 并在 message 标注 "not_implemented"
   - avg_cycle_time_sec：用每次 ExecuteTask 的 duration_sec 做滑动平均
3. 保存 timer 句柄，on_cleanup 时 cancel。
4. 同步修正 HTML 门户 DoD：js/app.js 中「指标可统计」若尚未真统计，不要打 ✓；或在指标卡标注「实测」vs「目标」。

【验证】
- ros2 topic echo /system_metrics，改代码让成功率随真实成败变化
- 故意让一次规划失败，确认 plan_success_rate 下降
```

### 提示词 C · 【P0】task_manager 真 bug + 抓取确认闭环

```text
项目 IntelliSort Workcell，修 src/intellisort_task/intellisort_task/task_manager_node.py：

1. 【bug】_exec_task 结束后 self._running 永不复位（L344 置 True，函数尾 L402-414 无 False）。后果：跑过一次 /execute_task 后 auto demo 永久不触发。在 try/finally 中复位，与 _maybe_auto_demo 一致。
2. 【bug】闭爪失败（L243-250）只 retry 一次就继续搬运。必须：失败则 return False（或按 enable_recovery 走完整恢复），禁止空爪搬运。
3. ConfirmGrasp 要有真实判据：调用 gripper 后对比 joint_states 或 gripper 反馈（见提示词 E）；连续 N 次夹爪宽度不收敛视为 GRASP_FAIL。
4. /pick_place 找不到 goal.object_id 时不要静默换 poses[0]（L317-318），应 abort 并报 DETECT_FAIL。
5. result.success 判据（L405）改为：失败数==0 或 按 goal 约定的允许失败数；不要 completed>0 and failed<=completed 这种放水条件。
6. 处理 action 取消：循环内检查 goal_handle.is_cancel_requested，取消时松爪并回 ready，状态发 CANCELLED。
7. 实现 cycle_timeout_sec 参数：单次 pick-place 超时则中断并报 TIMEOUT。
8. 删除死变量 seen、未用参数 feedback_cb；PickPlace feedback 要 publish_feedback。
9. SLOT_POSE/CLASS_SLOT/高度常量改为 ROS 参数或与 workspace_state 同源（消除 0.77 vs 0.12/0.015 不一致）。

【验证】
- ros2 action send_goal /execute_task ... 跑两次，第二次 auto demo 仍能触发（若 auto_run_demo:=true）
- 故意闭爪失败路径（可 mock gripper 返回 false），确认任务失败而非继续放置
```

### 提示词 D · 【P1】异常恢复从空壳变真

```text
项目 IntelliSort Workcell，把异常恢复做实。现状：supervisor_node.py 只 log + 返回策略字符串，/recovery 无任何客户端，恢复动作零实现。

要求：
1. task_manager 失败时改为：publish ExceptionEvent → 调用 /recovery action → 按 result.recovery_action 执行：
   - replan / retry：重新规划同一目标
   - re-perceive：触发感知刷新（或短等待新 /target_poses）
   - clear-scene-replan：通知 scene_builder 清理/放行后重规划
   - skip / skip-target：放弃当前目标继续下一个
   - abort-cycle / error：结束任务并 FAILED
2. supervisor 执行 /recovery 时不能只返回字符串：更新内部状态、发布恢复结果事件；max_auto_recoveries 计数按 task_id 或定时窗口重置，不要永不复位。
3. 补齐错误码闭环：要么实现并发布 POSE_LOW / COLLISION / TIMEOUT / COMM，要么从 RECOVERY_POLICY 删除死键；task_manager 发出的每个码都必须在策略表中。
4. docs/10「异常恢复率」改为可统计：metric_publisher 的 recovery_success_rate 来自 supervisor 真实计数。
5. 提供 tests/inject_faults.sh：支持「移走目标 / 加障碍 / 夹爪失败 / 超时」四种注入，输出恢复是否成功。

【验证】
- 注入规划失败 → 日志显示 recovery action 被调用 → 重试后成功
- ros2 topic echo /exception_events 与 /recovery feedback 有真实内容
- recovery_success_rate 随实验变化
```

### 提示词 E · 【P1】夹爪真反馈 + 控制器配置对齐

```text
项目 IntelliSort Workcell：

1. gripper_server_node.py 目前恒返回 success=True/reached_goal=True（L36-40）。改为：
   - 订阅 joint_states（或 gripper_controller 状态）
   - 下发位置后等待到位（带超时），未到位则 success=False/stalled 可置位
   - effort 字段填实测或 0，不要回显请求值
   - 增加「夹持检测」：闭合后目标宽度 vs 实际关节位置，判断是否夹到物体
2. 对齐 MoveIt 与 ros2_control 夹爪控制器：
   - moveit_controllers.yaml 声明 gripper_controller type= GripperCommand, action_ns= gripper_cmd
   - isc_controllers.yaml 实际是 position_controllers/JointGroupPositionController（只有 topic）
   二选一统一：要么 ros2_control 用 GripperActionController 并提供 gripper_cmd action，要么 MoveIt 侧删掉夹爪控制器（任务层已直调 /gripper_command）。
3. 修 package.xml：intellisort_task 删除不存在的 <depend>rclpy_action</depend>（action API 在 rclpy 内）。
4. 修并发：task_manager._gripper_move 与 moveit_client._spin_until 不要在已被 MultiThreadedExecutor spin 的节点上调用 rclpy.spin_until_future_complete；改为 future + 事件等待，或统一用 callback_group + 多线程 executor。

【验证】
- 断开 gripper_controller 时，/gripper_command 返回 success=False
- 正常夹取时 reached_goal 与 joint_states 一致
- colcon build 无 rosdep 报 rclpy_action 错误
```

### 提示词 F · 【P1】感知位姿用真相机模型

```text
项目 IntelliSort Workcell，重写 pose_estimator_node.py 的 _pixel_to_base：

现状：固定 cx=320,cy=240,scale=0.0012 仿射映射；深度读了只 pass；CameraInfo 收了不用。

要求：
1. 用 CameraInfo 的 K/P 矩阵做像素→射线；用 depth 图（或已知 table_z 平面）求射线与桌面交点，得到 base_link 下 XYZ。
2. 用 tf2（camera_color_optical_frame → base_link）做坐标变换，去掉手写仿射系数。
3. 深度无效时 fallback 到 table_z 平面交点，并下调 confidence / 发 POSE_LOW。
4. 尺寸不要只写死 CLASS_SIZE：优先用检测框 + 深度估计实际尺寸，写死表仅作 fallback。
5. 同步修 docs/04：「2D+深度+CameraInfo」在实现后才成立；检测 track_id 若无跟踪实现，删掉该字段或明确标注 unused。
6. grasp_planner_node.py：修 yaw 四元数轴（L94-105 现在绕 X 滚转，应为绕 Z 的 yaw 叠加顶抓姿态）；num_yaw_samples>2 时均匀采样；approach_height 不要取而不用。

【验证】
- 在 Gazebo 中移动零件，/target_poses 的 x/y 随动且与 world 真值误差 < 2cm（可用 synthetic 对比）
- ros2 run intellisort_demo synthetic_targets 与感知结果同 topic 时坐标接近
```

### 提示词 G · 【P1】硬件抽象做实或降级宣传

```text
项目 IntelliSort Workcell。hw_abstraction 目前是空壳，但 README/docs 宣传 sim|xarm|real。

方案 A（做实，工作量大）：
1. mode_manager 按 mode 真正切换：sim 启 gazebo_ros2_control；real 启 xarm_ros2 + realsense2_camera 驱动（可用 launch 前缀/事件句柄）。
2. 统一 hardware interface 接口层，上层不感知驱动差异。
3. 补 xarm/RealSense 的 launch 片段与参数文件（可先 fake 模式用 joint_state_publisher 顶替）。
4. setup.py 安装 config/hw_mode.yaml，并让 mode_manager 启动时加载它（目前 docs/01 指向该文件但无人读取）。

方案 B（降级宣传，工作量小）：
1. README/docs/门户 删除或改写「硬件抽象/只换驱动」为「迁移清单与接口预留」。
2. mode_manager 仅保留 SetMode 服务用于模式标记，文档明确「驱动切换需手工改 launch」。

任选其一，但文档与代码必须一致。

【验证】
- 方案 A：/set_mode real 后节点图出现对应驱动；方案 B：文档无夸大表述
- hw_mode.yaml 被安装到 share 且被读取（若选 A）
```

### 提示词 H · 【P0】测试与 CI 从「恒绿」变「可失败」

```text
项目 IntelliSort Workcell。tests/ 两个脚本退出码恒 0，CI 只 build 不测。

要求：
1. run_pick_demo.py：根据 ExecuteTask result.success 设置 sys.exit(0/1)。
2. tests/run_smoke.sh：加断言——
   - ros2 node list 必须包含 task_manager、object_detection、pose_estimator、gripper_server 等关键节点
   - /target_poses、/task_status 在超时内至少收到 1 条，否则 exit 1
   - 不要 || true 吞掉关键检查
3. tests/run_acceptance.sh：启动 demo + synthetic_targets（或调用 tools/run_demo.sh），跑 pick demo，按退出码判定；统计 completed/failed 并与 docs/10 阈值对比，低于阈值 exit 1。
4. 新增单元测试（pytest / ament_cmake_pytest）：
   - CLASS_SLOT 映射、grasp 生成四元数、pixel_to_base/射线交点、mode_manager 参数切换、SLOT 坐标一致性
5. 新增 launch_testing 或 headless 冒烟：Gazebo + synthetic + ExecuteTask，断言 completed>0。
6. .github/workflows/ci.yml 增加：rosdep install、colcon test、ament_flake8/pep257、失败上传日志。

【验证】
- 故意破坏一个断言，CI/脚本必须红
- colcon test 全绿后方可合入
```

### 提示词 I · 【P2】文档与 HTML 门户对齐真实状态

```text
项目 IntelliSort Workcell，做一次「文档去水分」：

1. 对照 docs/14 列表，修改 README/docs 中的夸大表述：
   - 「行为树」→「行为树风格编排（XML 为规范文档，运行时为 Python 状态机）」或真正接入 py_trees（二选一）
   - 「异常恢复率≥70%」→ 等真实现后再写目标值
   - 「可暂停/继续」→ 实现后保留，否则删除
   - 「硬件抽象」按提示词 G 的选择改写
   - 「指标可统计」等 metric 去假后再勾选
2. HTML 门户：
   - 补「阶段验收/进度」页，或删除 README/docs 的「阶段验收」承诺与 styles.css 死样式（.phase/.timeline）
   - 把 app.js 占位学习卡片换成真实内容，或只保留已有实质内容的 4 个知识页并改 docs/13「每页」表述
   - DoD 打钩与实现状态一致（指标/恢复/暂停等未完成项不要 ✓）
   - data.js meta 块投入使用或删除；GitHub 文本改可点链接；统一夹爪行程口径（35mm vs 40mm）
   - ros2 页补 workspace_state 节点与 /recovery、/get_workspace_state、/system_metrics
3. assets/、site/：填充演示资源（录屏 GIF）或在 README 说明用途；空目录建议加 .gitkeep 说明。

【验证】
- 全文搜索「≥95%」「行为树」「暂停」「硬件抽象」等关键词，与代码实现一一对应
- 门户 DoD 与 tests 实际结果一致
```

### 提示词 J · 【P2】接口清理与一致性

```text
项目 IntelliSort Workcell，清理未接线/冲突接口：

1. PickPlace.action：实现 target_pose/timeout_sec 的消费，或从 action 定义删除这些字段。
2. GetWorkspaceState.srv：让 task_manager 放置前查询占用槽位（替代硬编码 SLOT_POSE），或删除该服务。
3. SetMode.srv：找到真实客户端（bringup/演示 UI），或文档标明仅供手动调试。
4. Detection.track_id：实现简易跟踪，或删除字段/注释改为 unused。
5. system.yaml 的 task_manager 段真正加载到 task_manager 节点（参数文件路径传入 launch）。
6. 统一槽位与抓深常量来源（消除 0.77/0.75、0.02/0.015 冲突）。
7. synthetic_targets：支持「只发布一次」或按 scene/感知确认后停发，避免已抓走目标被反复重发；删掉 seen 死变量。
8. tip_link 统一为 SRDF 的 tool0，或把 SRDF tip 改为 tcp_link 并同步 kinematics。
9. grasp 与 synthetic 不要同时无协调地发 /grasp_candidates（同 topic 混流）；给 synthetic 加开关参数 disable_grasp_pub。

【验证】
- 每个 msg/srv/action 字段要么被消费，要么从定义中移除
- colcon build + 冒烟测试通过
```

---

## 6. 建议实施顺序（1–2 周节奏）

| 天 | 提示词 | 目标 |
|----|--------|------|
| 1 | A + H(1-3) | 抓取能规划成功，验收脚本可红 |
| 2 | B + C | 指标真实，task 真 bug 修掉 |
| 3 | E | 夹爪真反馈，配置对齐 |
| 4 | D | 异常恢复闭环 + 故障注入 |
| 5 | F | 感知位姿专业化 |
| 6 | H(4-6) + G | 单测/CI + 硬件抽象定调 |
| 7 | I + J | 文档/门户去水分，接口清理 |

---

## 7. 验收红线（做完再叫「完善」）

- [ ] `run_pick_demo` 失败时进程退出码 ≠ 0
- [ ] `/system_metrics` 四项核心指标随真实成败变化（禁止常量）
- [ ] 抓取下探不再与目标碰撞盒冲突；目标抓走后场景更新
- [ ] `/recovery` 被 task_manager 真实调用，且能重试/跳过
- [ ] 夹爪未到位时 success=False
- [ ] `colcon test` 有断言且 CI 会跑
- [ ] 文档/门户无「行为树/暂停/硬件抽象/恢复率」等未实现承诺

---

*本文件由项目深度体检生成，修复时请同步更新对应条目的状态。*
