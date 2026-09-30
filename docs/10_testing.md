# 10 · 实验与测试

## 指标（真实统计，非写死）

由 `task_manager` 在 `/system_metrics` 发布：

| 指标 | 来源 | 说明 |
|------|------|------|
| plan_success_rate | `_plan_ok/_plan_total` | 无样本时为 0 |
| grasp_success_rate | `_grasp_ok/_grasp_total` | 含 confirm |
| recovery_success_rate | supervisor `/recovery` 计数 | 无恢复则为 0 |
| avg_cycle_time_sec | ExecuteTask duration 滑动 | — |
| completed/failed_tasks | 任务结果 | — |

**目标值**（实现稳定后验收用，不是已达成声明）：  
规划 ≥95% · 抓取 ≥85% · 任务 ≥85% · 恢复 ≥70% · 节拍 12–25s

## 测试脚本

| 脚本 | 作用 |
|------|------|
| `tests/run_smoke.sh` | 节点与话题断言，**失败 exit 1** |
| `tests/run_acceptance.sh` | 跑 pick demo，按退出码判定 |
| `tests/inject_faults.sh` | 故障注入：移目标/加障碍/夹爪/超时 |
| `tests/test_unit_constants.py` | 纯函数单测（可 `python -m unittest`） |

```bash
python -m unittest tests.test_unit_constants -v
bash tests/run_smoke.sh
bash tests/run_acceptance.sh
```

## 异常注入

```bash
bash tests/inject_faults.sh remove_target
bash tests/inject_faults.sh add_obstacle
# 观察 /exception_events 与 /recovery_events
```
