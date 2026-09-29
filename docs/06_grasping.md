# 06 · 抓取系统

## 流程

目标位姿 → 抓取候选（顶抓 + yaw 样本）→ 评分 → 与规划联调 → 夹爪执行 → 确认

## 抓取策略（首版）

- 顶抓（tool Z 朝下）  
- 2 个 yaw 样本  
- 接近高度 12 cm，抓取深度 1.5 cm  
- 夹爪开 3.5 cm / 闭 0  

## 代码

`intellisort_grasp/intellisort_grasp/grasp_planner_node.py`  
任务层在 `task_manager_node._pick_and_place_one` 中执行接近-下降-闭合-抬起。

## 为何不用深度学习抓取

受控离散摆放下，简单顶抓稳定可复现、可调试、可迁移。深度学习抓取作后续升级。

## 验收

离散抓取成功率 ≥ 85%（20 次量级）；失败回安全位。
