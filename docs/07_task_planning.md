# 07 · 任务规划

## 编排模型（与代码一致）

运行时是 **Python 行为树风格状态机**（Sequence / Fallback 语义）：  
`bt/*.xml` 是**设计规范文档**，供讲解与后续 py_trees 迁移，**当前不解析执行**。

```text
Main (Sequence)
  select → pre-grasp → open → descend → close(confirm) → lift
  → place approach → place → open → retreat → ready
Recovery (on fail)
  call /recovery → replan | re-grasp | skip-target | abort-cycle
```

规范 XML：`intellisort_task/bt/main_tree.xml`

## 类别到料位（单一来源：`workspace.py`）

| 类别 | 料位 | 桌面坐标 (x,y,z) |
|------|------|------------------|
| red / yellow | slot_a | (0.35, 0.28, 0.75) |
| green | slot_b | (0.48, 0.12, 0.75) |
| blue | slot_c | (0.48, -0.12, 0.75) |

## Action

- `/pick_place`：消费 `object_id` / `object_class` / `target_pose` / `timeout_sec` / `place_slot`
- `/execute_task`：多目标队列，支持 cancel

## 真实行为（不要夸大）

- **确认抓取**：比较夹爪到位与宽度，失败则 `GRASP_FAIL`，**禁止空爪搬运**
- **取消**：`goal_handle.is_cancel_requested` → 松爪回 ready → CANCELLED
- **超时**：`cycle_timeout_sec` 参数生效
- **暂停/继续**：**未实现**（可取消；暂停列为后续升级）

## 运行

```bash
ros2 run intellisort_demo run_pick_demo
# 失败时进程退出码 ≠ 0
```

## 验收

- 连续任务 `failed==0` 或失败率 ≤20% 记成功
- `/task_status`、`/system_metrics` 为真实计数
