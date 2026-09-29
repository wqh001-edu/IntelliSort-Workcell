# 11 · 最终 Demo

## 脚本（5–8 分钟）

1. 展示工作站全景（Gazebo + RViz）  
2. `demo.launch.py` 一键启动  
3. `synthetic_targets` 或真实检测显示目标  
4. `run_pick_demo` 分拣 red/green/blue  
5. 讲解 `/task_status` 与规划轨迹  
6. 注入一次异常（移走零件）看恢复  
7. 讲解 sim→real 切换  
8. 总结架构与指标  

## 启动清单

```bash
# 终端1
ros2 launch intellisort_bringup demo.launch.py use_rviz:=true

# 终端2
ros2 run intellisort_demo synthetic_targets

# 终端3
ros2 run intellisort_demo run_pick_demo
```

## 成功标准

一键启动、闭环可看懂、含异常恢复、无长时间卡死。
