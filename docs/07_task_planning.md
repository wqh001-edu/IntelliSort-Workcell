# 07 · 任务规划

## 编排模型

轻量行为树语义（Python 实现，XML 作为规范文档）：

```text
Root(Fallback)
├── MainSequence
│   Perceive → SelectTarget → BuildScene
│   → PlanPick → ExecutePick → ConfirmGrasp
│   → PlanPlace → ExecutePlace → ConfirmPlace
│   → ReportSuccess
└── Recovery
    Diagnose → Choose → Execute → RetryOrSkip
```

规范 XML：`intellisort_task/bt/main_tree.xml`、`recovery_subtree.xml`

## 类别到料位

| 类别 | 料位 |
|------|------|
| red / yellow | slot_a |
| green | slot_b |
| blue | slot_c |

## Action

- `/pick_place`：单次抓放  
- `/execute_task`：多目标队列  

## 运行

```bash
ros2 run intellisort_demo run_pick_demo
ros2 action send_goal /execute_task ...
```

## 验收

连续 10 个混合任务完成率 ≥ 90%；可暂停/继续；`/task_status` 可观测。
