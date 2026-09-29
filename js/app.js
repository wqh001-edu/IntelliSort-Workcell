/* IntelliSort Workcell portal */
(function () {
  const data = window.ISC_DATA;
  const $ = (s, e = document) => e.querySelector(s);
  const $$ = (s, e = document) => Array.from(e.querySelectorAll(s));

  const pageMeta = {
    home: ["项目总览"], scenario: ["应用场景"], demo: ["最终 Demo"], quickstart: ["快速开始"],
    architecture: ["系统架构"], ros2: ["ROS2 架构"], robot: ["机械臂模型"], features: ["功能树"],
    perception: ["感知系统"], motion: ["运动规划"], grasp: ["抓取系统"], task: ["任务规划"],
    exceptions: ["异常处理"], simulation: ["仿真环境"], hardware: ["硬件设计"],
    testing: ["实验与测试"], html: ["HTML 演示系统"], repo: ["仓库结构"], dod: ["完成标准"],
    detection: ["感知系统", "目标检测"], "pose-estimation": ["感知系统", "位姿估计"],
    ompl: ["运动规划", "OMPL 规划"], bt: ["任务规划", "行为树任务"],
    "arch-perception": ["系统架构", "感知系统"], "arch-motion": ["系统架构", "运动规划"],
    "arch-control": ["系统架构", "控制系统"],
  };

  function pageHeader(kicker, title, desc) {
    return `<header class="page-header"><div class="kicker">${kicker || ""}</div>
      <h2>${title}</h2><p class="desc">${desc || ""}</p></header>`;
  }
  function section(title, body) {
    return `<section class="section"><h3 class="section-title">${title}</h3>${body}</section>`;
  }
  function learnCard(items) {
    return `<div class="learn">${items.map((it) => `
      <div class="learn-item"><h4>${it.q}</h4>
      ${it.pre ? `<pre>${it.pre}</pre>` : `<p>${it.a}</p>`}</div>`).join("")}</div>`;
  }
  function code(x) {
    return `<div class="codeblock">${x}</div>`;
  }

  const pages = {
    home() {
      return `
      <div class="hero">
        <div class="hero-kicker">● ISC-1 · IMPLEMENTED WORKCELL</div>
        <h1>智拣柔性工作站<br><span class="accent">IntelliSort Workcell</span></h1>
        <p class="lead">视觉引导六轴机械臂工作站：多品种零件识别、位姿估计、抓取、分拣与上下料，含异常恢复与仿真/实物解耦。深度来自完整机器人系统工程，而不是算法名词堆砌。</p>
        <div class="hero-meta">
          <span class="chip"><span class="dot"></span>ROS2 Humble</span>
          <span class="chip"><span class="dot"></span>MoveIt2</span>
          <span class="chip green"><span class="dot"></span>Gazebo Classic</span>
          <span class="chip amber"><span class="dot"></span>sim/real Ready</span>
        </div>
        <div class="hero-actions">
          <a class="btn primary" href="#/quickstart">快速开始</a>
          <a class="btn" href="#/architecture">系统架构</a>
          <a class="btn" href="#/demo">最终 Demo</a>
          <a class="btn ghost" href="#/repo">仓库结构</a>
        </div>
      </div>
      <div class="grid cols-4 mb-24">
        <div class="card metric"><div class="value">≥85%</div><div class="label">任务完成率目标</div></div>
        <div class="card metric"><div class="value">≥95%</div><div class="label">规划成功率目标</div></div>
        <div class="card metric"><div class="value">≥6</div><div class="label">异常类型覆盖</div></div>
        <div class="card metric"><div class="value">12</div><div class="label">ROS2 Packages</div></div>
      </div>
      ${section("项目定位", `
        <div class="grid cols-3">
          <div class="card"><div class="card-top"><div class="icon-box">技</div><span class="badge blue">系统深度</span></div>
            <h3>感知+决策+规划+控制</h3><p>完整闭环，而不是只做识别抓取 Demo。</p></div>
          <div class="card"><div class="card-top"><div class="icon-box">落</div><span class="badge green">可迁移</span></div>
            <h3>仿真与实物同架构</h3><p>上层逻辑不改，只换 hardware interface 与驱动。</p></div>
          <div class="card"><div class="card-top"><div class="icon-box">验</div><span class="badge amber">可验收</span></div>
            <h3>每模块可独立验证</h3><p>合成目标、话题、Action、指标都可脚本检查。</p></div>
        </div>`)}
      ${section("快速导航", `
        <div class="grid cols-2">
          ${[
            ["quickstart", "在虚拟机中跑起来", "依赖安装、colcon build、一键 launch"],
            ["architecture", "五层架构", "展示/任务/感知/规划/控制/硬件"],
            ["ros2", "节点与接口", "Topic / Service / Action / TF"],
            ["perception", "感知链路", "检测 → 位姿 → 抓取候选"],
            ["demo", "5–8 分钟演示脚本", "含异常恢复讲解"],
            ["dod", "完成标准", "什么程度算做完"],
          ].map(([id, t, d]) => `<a class="card" href="#/${id}" style="display:block"><h3>${t}</h3><p>${d}</p></a>`).join("")}
        </div>`)}
      <div class="callout"><strong>GitHub：</strong> <span class="mono">https://github.com/wqh001-edu/IntelliSort-Workcell</span> · 文档见 <span class="mono">docs/</span> · 源码见 <span class="mono">src/</span></div>`;
    },

    scenario() {
      return pageHeader("SCENARIO", "应用场景与问题定义", "柔性制造/实验室工位的多品种零件分拣与上下料。") +
        section("业务问题", `<p class="muted">多品种小批量、人工重复易错、专机无法适应来料变化、只有识别抓取的 Demo 不能当工位用。</p>`) +
        section("系统闭环", `<div class="callout success"><strong>来料 → 识别与位姿 → 抓取规划 → 无碰撞运动 → 分拣/上下料 → 结果确认 → 异常恢复</strong></div>
          <div class="grid cols-3">
            <div class="card"><h3>多品种识别</h3><p>≥3 类零件（红/绿/蓝/黄）。</p></div>
            <div class="card"><h3>柔性分拣</h3><p>按类放入 slot_a/b/c。</p></div>
            <div class="card"><h3>连续与恢复</h3><p>多目标循环，失败可跳过/重试。</p></div>
          </div>`) +
        section("工作台布局", `<div class="diagram"><div class="arch-flow">
          <div class="arch-row">
            <div class="arch-label">工位</div>
            <div class="arch-node hl"><strong>相机架</strong><span>Eye-to-Hand</span></div>
            <div class="arch-node"><strong>来料区</strong><span>4 彩色零件</span></div>
            <div class="arch-node"><strong>分拣区</strong><span>slot A/B/C</span></div>
          </div>
          <div class="arch-row">
            <div class="arch-label">执行</div>
            <div class="arch-node hl"><strong>ISC 6-DOF 臂</strong><span>夹爪 + TCP</span></div>
            <div class="arch-node"><strong>障碍块</strong><span>碰撞场景</span></div>
            <div class="arch-node"><strong>安全</strong><span>急停/限速（实物）</span></div>
          </div></div></div>`);
    },

    demo() {
      return pageHeader("FINAL DEMO", "最终 Demo 脚本", "5–8 分钟可复现演示。") +
        section("启动清单", code(`# 终端 1 — 全系统
ros2 launch intellisort_bringup demo.launch.py use_rviz:=true

# 终端 2 — 合成目标（保证链路可跑）
ros2 run intellisort_demo synthetic_targets

# 终端 3 — 执行分拣
ros2 run intellisort_demo run_pick_demo`)) +
        section("讲解节奏", `<div class="table-wrap"><table>
          <thead><tr><th>时间</th><th>内容</th><th>看什么</th></tr></thead>
          <tbody>
            <tr><td>0:00</td><td>工作站全景</td><td>完整工位而非单臂</td></tr>
            <tr><td>1:00</td><td>一键 bringup</td><td>节点图 / Lifecycle</td></tr>
            <tr><td>2:00</td><td>检测与位姿</td><td>/detections /target_poses</td></tr>
            <tr><td>3:00</td><td>分拣执行</td><td>MoveIt 轨迹与抓取</td></tr>
            <tr><td>5:00</td><td>异常与恢复</td><td>移走目标/跳过</td></tr>
            <tr><td>6:30</td><td>sim→real</td><td>只换驱动与参数</td></tr>
          </tbody></table></div>`);
    },

    quickstart() {
      return pageHeader("QUICKSTART", "快速开始（Ubuntu 22.04 + Humble）", "在虚拟机中编译并运行本仓库。") +
        section("1. 安装依赖", code(`sudo apt update
sudo apt install -y ros-humble-desktop ros-humble-moveit \\
  ros-humble-ros2-control ros-humble-ros2-controllers \\
  ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \\
  ros-humble-xacro ros-humble-cv-bridge python3-opencv python3-numpy`)) +
        section("2. 编译", code(`git clone https://github.com/wqh001-edu/IntelliSort-Workcell.git
cd IntelliSort-Workcell
source /opt/ros/humble/setup.bash
rosdep install --from-paths src -y --ignore-src || true
colcon build --symlink-install
source install/setup.bash`)) +
        section("3. 运行", code(`ros2 launch intellisort_bringup demo.launch.py use_rviz:=true
# 另开终端
ros2 run intellisort_demo synthetic_targets
ros2 run intellisort_demo run_pick_demo`)) +
        section("4. 仅看模型", code(`ros2 launch intellisort_description display.launch.py`)) +
        `<div class="callout warn"><strong>虚拟机提示：</strong>若 Gazebo 黑屏可执行 <code>export LIBGL_ALWAYS_SOFTWARE=1</code>。排障见 docs/12_troubleshooting.md。</div>`;
    },

    architecture() {
      return pageHeader("ARCHITECTURE", "系统架构", "六层解耦，sim/real 可切换。") +
        section("分层", `<div class="diagram"><div class="arch-flow">
          <div class="arch-row"><div class="arch-label">L5</div><div class="arch-node"><strong>展示学习</strong><span>HTML · RViz · Gazebo</span></div></div>
          <div class="arch-row"><div class="arch-label">L4</div><div class="arch-node hl"><strong>任务决策</strong><span>task_manager · supervisor</span></div></div>
          <div class="arch-row"><div class="arch-label">L3</div><div class="arch-node"><strong>感知抓取</strong><span>detector · pose · grasp</span></div></div>
          <div class="arch-row"><div class="arch-label">L2</div><div class="arch-node hl"><strong>运动规划</strong><span>scene_builder · MoveIt2</span></div></div>
          <div class="arch-row"><div class="arch-label">L1</div><div class="arch-node"><strong>控制执行</strong><span>ros2_control · controllers</span></div></div>
          <div class="arch-row"><div class="arch-label">L0</div><div class="arch-node"><strong>硬件抽象</strong><span>mode_manager · drivers</span></div></div>
        </div></div>`) +
        section("子系统下钻", `<div class="drill">
          <a href="#/arch-perception"><div><div class="t">感知系统</div><div class="d">相机 → 检测 → 位姿</div></div><div class="go">进入 →</div></a>
          <a href="#/arch-motion"><div><div class="t">运动规划</div><div class="d">MoveIt2 → OMPL → 碰撞</div></div><div class="go">进入 →</div></a>
          <a href="#/arch-control"><div><div class="t">控制系统</div><div class="d">ros2_control → 夹爪</div></div><div class="go">进入 →</div></a>
        </div>`) +
        section("sim/real", `<div class="grid cols-2">
          <div class="card"><h3>不变</h3><p>任务逻辑、感知接口、MoveIt 请求、Topic/Action 名称。</p></div>
          <div class="card"><h3>可换</h3><p>hardware interface、驱动、相机、标定与限位参数。</p></div>
        </div>`);
    },

    ros2() {
      return pageHeader("ROS2", "节点 · Topic · Action · TF", "接口在阶段早期冻结，避免后期乱改。") +
        section("主要节点", `<div class="table-wrap"><table>
          <thead><tr><th>节点</th><th>包</th><th>职责</th></tr></thead>
          <tbody>
            ${[
              ["object_detection", "perception", "颜色检测"],
              ["pose_estimator", "perception", "目标位姿"],
              ["grasp_planner", "grasp", "抓取候选"],
              ["scene_builder", "scene", "PlanningScene"],
              ["task_manager", "task", "任务编排"],
              ["gripper_server", "task", "夹爪服务"],
              ["supervisor", "task", "异常恢复"],
              ["metric_publisher", "task", "指标"],
              ["mode_manager", "hw_abstraction", "sim/real"],
              ["move_group", "moveit_config", "规划执行"],
            ].map((r) => `<tr><td class="mono">${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join("")}
          </tbody></table></div>`) +
        section("接口", code(`/detections              intellisort_interfaces/DetectionArray
/target_poses            intellisort_interfaces/TargetPoseArray
/grasp_candidates        intellisort_interfaces/GraspCandidateArray
/task_status             intellisort_interfaces/TaskStatus
/exception_events        intellisort_interfaces/ExceptionEvent
/gripper_command         intellisort_interfaces/srv/GripperCommand
/set_mode                intellisort_interfaces/srv/SetMode
/execute_task            intellisort_interfaces/action/ExecuteTask
/pick_place              intellisort_interfaces/action/PickPlace`)) +
        section("TF", code(`world → base_link → link1..6 → tool0 → gripper_link → tcp_link
world → camera_stand_link → camera_link → camera_color_optical_frame
world → table_link → table_top`));
    },

    robot() {
      return pageHeader("ROBOT", "机械臂模型", "仿真自包含 6-DOF；实物首选 xArm6。") +
        section("文件", code(`src/intellisort_description/urdf/
  isc_arm.urdf.xacro
  isc_arm.gazebo.xacro
  workstation.urdf.xacro
  isc_workcell.urdf.xacro`)) +
        section("关节", `<div class="table-wrap"><table>
          <thead><tr><th>关节</th><th>类型</th><th>范围</th></tr></thead>
          <tbody>
            <tr><td>joint1</td><td>revolute Z</td><td>±180°</td></tr>
            <tr><td>joint2</td><td>revolute Y</td><td>±100°</td></tr>
            <tr><td>joint3</td><td>revolute Y</td><td>±120°</td></tr>
            <tr><td>joint4–6</td><td>revolute</td><td>腕部</td></tr>
            <tr><td>gripper L/R</td><td>prismatic</td><td>0–40 mm</td></tr>
          </tbody></table></div>`) +
        `<div class="callout success"><strong>实物迁移：</strong>同构 xArm6 + <code>xarm_ros2</code>，上层 MoveIt 与任务接口保持不变。</div>`;
    },

    features() {
      return pageHeader("FEATURES", "功能树", "一级到三级能力域。") +
        section("树", `<div class="tree">IntelliSort Workcell
├── 1 系统管理 → 启动配置 / 标定 / sim-real
├── 2 感知系统 → 采集 / 检测 / 位姿 / 工作区
├── 3 抓取系统 → 候选 / 选择 / 夹爪
├── 4 运动规划 → 场景 / 路径 / 轨迹执行
├── 5 任务系统 → 定义 / 编排 / 监控
├── 6 异常处理 → 检测 / 恢复 / 安全
├── 7 仿真可视化 → Gazebo / RViz / HTML
└── 8 硬件抽象 → interface / 驱动 / 限位</div>`);
    },

    perception() {
      return pageHeader("PERCEPTION", "感知系统", "检测 → 位姿 → 工作区状态。") +
        section("下钻", `<div class="drill">
          <a href="#/detection"><div><div class="t">目标检测</div><div class="d">HSV 多色分割</div></div><div class="go">→</div></a>
          <a href="#/pose-estimation"><div><div class="t">位姿估计</div><div class="d">工作台映射 / 深度</div></div><div class="go">→</div></a>
        </div>`) +
        section("运行", code(`ros2 run intellisort_perception detector_node
ros2 run intellisort_perception pose_estimator_node
ros2 topic echo /target_poses`)) +
        `<div class="callout"><strong>演示备用：</strong><code>ros2 run intellisort_demo synthetic_targets</code> 发布与世界对齐的目标，隔离相机链路问题。</div>`;
    },

    motion() {
      return pageHeader("MOTION", "运动规划", "MoveIt2 + OMPL + 碰撞场景。") +
        section("配置", code(`src/intellisort_moveit_config/
  srdf/isc_arm.srdf
  config/kinematics.yaml
  config/ompl_planning.yaml
  config/joint_limits.yaml
  config/moveit_controllers.yaml`)) +
        section("下钻", `<div class="drill">
          <a href="#/ompl"><div><div class="t">OMPL 规划</div><div class="d">RRTConnect 与调参</div></div><div class="go">→</div></a>
        </div>`) +
        section("命名位姿", `<div class="grid cols-2">
          <div class="card"><h3>home</h3><p>全零位，安全收纳。</p></div>
          <div class="card"><h3>ready</h3><p>观测/准备位。</p></div>
        </div>`);
    },

    grasp() {
      return pageHeader("GRASP", "抓取系统", "顶抓候选 + 接近段 + 夹爪。") +
        section("策略", `<div class="grid cols-2">
          <div class="card"><h3>顶抓</h3><p>tool Z 朝下，简单稳定。</p></div>
          <div class="card"><h3>2 个 yaw 样本</h3><p>评分后取最优。</p></div>
          <div class="card"><h3>接近 12cm</h3><p>最后笛卡尔下降。</p></div>
          <div class="card"><h3>夹爪 0–35mm</h3><p>服务 <span class="mono">/gripper_command</span>。</p></div>
        </div>`) +
        section("代码", code(`src/intellisort_grasp/intellisort_grasp/grasp_planner_node.py
src/intellisort_task/intellisort_task/task_manager_node.py  # _pick_and_place_one`));
    },

    task() {
      return pageHeader("TASK", "任务规划", "行为树语义编排多阶段抓放。") +
        section("树", code(`Root(Fallback)
├── MainSequence
│   Perceive → Select → BuildScene → PlanPick → Pick
│   → Confirm → PlanPlace → Place → Report
└── Recovery (Diagnose → Choose → Execute → RetryOrSkip)`)) +
        section("下钻", `<div class="drill">
          <a href="#/bt"><div><div class="t">行为树任务</div><div class="d">XML 规范与实现</div></div><div class="go">→</div></a>
        </div>`) +
        section("类别映射", code(`red / yellow → slot_a
green        → slot_b
blue         → slot_c`));
    },

    exceptions() {
      return pageHeader("EXCEPTIONS", "异常处理与安全", "Retry / Replan / Skip / Error / E-Stop。") +
        section("矩阵", `<div class="table-wrap"><table>
          <thead><tr><th>异常</th><th>恢复</th></tr></thead>
          <tbody>
            <tr><td>识别失败 / 低置信度</td><td>重采 / 跳过</td></tr>
            <tr><td>规划失败</td><td>Replan / 重试</td></tr>
            <tr><td>抓取失败</td><td>重抓 / 换候选</td></tr>
            <tr><td>目标移动</td><td>重定位</td></tr>
            <tr><td>超时 / 通信</td><td>Error State</td></tr>
            <tr><td>急停</td><td>立即停止</td></tr>
          </tbody></table></div>`) +
        section("实现", code(`supervisor_node.py  · /exception_events · /recovery action
task_manager 有限重试 + skip 策略`));
    },

    simulation() {
      return pageHeader("SIMULATION", "系统级仿真工作站", "完整工位，而不是只有臂在动。") +
        section("构成", `<div class="grid cols-3">
          ${["机械臂+夹爪", "工作台碰撞体", "4 彩色零件", "料位 A/B/C", "障碍块", "RGB-D 相机", "灯光与地面", "PlanningScene 同步", "ros2_control"].map((t) => `<div class="card"><h3>${t}</h3><p>已写入 world/xacro 与配置。</p></div>`).join("")}
        </div>`) +
        section("启动", code(`ros2 launch intellisort_gazebo gazebo_workcell.launch.py
# 或全系统
ros2 launch intellisort_bringup demo.launch.py`));
    },

    hardware() {
      return pageHeader("HARDWARE", "硬件设计与采购", "从第一天考虑实物迁移。") +
        section("三档", `<div class="grid cols-3">
          <div class="card"><div class="card-top"><div class="icon-box">入</div><span class="badge">¥0.6–1.2万</span></div><h3>入门</h3><p>仿真优先，桌面展示臂/USB 相机。</p></div>
          <div class="card" style="border-color:rgba(59,130,246,.45)"><div class="card-top"><div class="icon-box">推</div><span class="badge blue">¥6–12万</span></div><h3>推荐</h3><p>xArm6 + 电动夹爪 + D435 + 工控机。</p></div>
          <div class="card"><div class="card-top"><div class="icon-box">高</div><span class="badge amber">¥18–35万</span></div><h3>高配</h3><p>xArm7/UR5e + 力控预留 + 安全围栏。</p></div>
        </div>`) +
        section("迁移步骤", code(`1. use_sim_time:=false
2. robot_driver:=xarm + 安装 xarm_ros2
3. 相机 realsense2_camera
4. 手眼标定
5. 速度缩放 0.2–0.3
6. 急停与软限位
7. 先空跑再抓取`));
    },

    testing() {
      return pageHeader("TESTING", "实验与测试", "指标、脚本、异常注入。") +
        section("指标", `<div class="table-wrap"><table>
          <thead><tr><th>指标</th><th>阈值</th></tr></thead>
          <tbody>
            <tr><td>规划成功率</td><td>≥95%</td></tr>
            <tr><td>抓取成功率</td><td>≥85%</td></tr>
            <tr><td>任务完成率</td><td>≥85%</td></tr>
            <tr><td>异常恢复率</td><td>≥70%</td></tr>
          </tbody></table></div>`) +
        section("脚本", code(`tests/run_smoke.sh
tests/run_acceptance.sh`));
    },

    html() {
      return pageHeader("HTML", "HTML 演示与学习系统", "官网 × 文档 × 答辩 × 复习站。") +
        section("结构", code(`index.html
css/styles.css
js/data.js
js/app.js`)) +
        section("学习卡片", learnCard([
          { q: "这是什么", a: "一句话定义模块。" },
          { q: "为什么需要", a: "对应场景问题。" },
          { q: "输入 / 输出", a: "消息、坐标系、失败行为。" },
          { q: "ROS2 实现", a: "节点、参数、接口。" },
          { q: "代码位置", a: "package 路径。" },
          { q: "如何运行 / 验证", a: "命令与可计数指标。" },
        ]));
    },

    repo() {
      return pageHeader("REPO", "仓库结构", "代码 / 配置 / 模型 / 文档 / 演示分离。") +
        section("布局", code(`IntelliSort-Workcell/
├── README.md
├── LICENSE
├── index.html          # 本门户
├── css/  js/
├── docs/               # 13 篇
├── src/                # 12 个 ROS2 包
├── tests/
└── .gitignore`)) +
        section("src 包", code(`intellisort_interfaces
intellisort_description
intellisort_control
intellisort_gazebo
intellisort_moveit_config
intellisort_perception
intellisort_grasp
intellisort_scene
intellisort_task
intellisort_hw_abstraction
intellisort_bringup
intellisort_demo`));
    },

    dod() {
      return pageHeader("DOD", "完成标准", "做到什么程度算完成。") +
        section("P0", `<div class="grid cols-2">
          ${[
            "一键启动完整 Gazebo 工作站",
            "≥3 类零件识别→抓取→分拣闭环",
            "多目标任务可执行",
            "规划/抓取/任务指标可统计",
            "≥6 类异常策略落地",
            "sim/real 配置开关",
            "接口与 TF 文档完整",
            "13 篇 docs + README 可跑通",
            "HTML 多级导航完整",
            "5–8 分钟可复现 Demo",
          ].map((t) => `<div class="card"><h3>✓ ${t}</h3></div>`).join("")}
        </div>`) +
        `<div class="callout success"><strong>一句话：</strong>非作者能按 README 在 1 小时内启动系统并看懂架构，即可认为工程完成。</div>`;
    },

    detection() {
      return pageHeader("LEARN", "目标检测", "颜色分割多类零件检测。") +
        section("学习卡片", learnCard([
          { q: "这是什么", a: "从 RGB 图像定位并分类零件（红/绿/蓝/黄）。" },
          { q: "为什么需要", a: "位姿、抓取、任务都依赖目标列表。" },
          { q: "在本项目中负责什么", a: "输出 /detections 供 pose_estimator 使用。" },
          { q: "输入", a: "/camera/color/image_raw" },
          { q: "输出", a: "DetectionArray（框、类别、置信度）" },
          { q: "ROS2 实现", a: "Lifecycle 节点 object_detection；cv_bridge + OpenCV。" },
          { q: "代码位置", pre: "src/intellisort_perception/intellisort_perception/detector_node.py" },
          { q: "如何运行", pre: "ros2 run intellisort_perception detector_node\nros2 topic echo /detections" },
          { q: "如何验证", a: "叠加检测框稳定；遮挡时置信度下降。" },
        ]));
    },

    "pose-estimation"() {
      return pageHeader("LEARN", "位姿估计", "检测框 → 可抓取 PoseStamped。") +
        section("学习卡片", learnCard([
          { q: "这是什么", a: "把 2D 检测变成 base_link 下 3D 位姿。" },
          { q: "为什么需要", a: "MoveIt 碰撞与抓取都需要 3D。" },
          { q: "在本项目中负责什么", a: "输出 /target_poses 与尺寸。" },
          { q: "输入", a: "/detections + depth + camera_info" },
          { q: "输出", a: "TargetPoseArray" },
          { q: "ROS2 实现", a: "pose_estimator_node；工作台平面映射，可换手眼标定。" },
          { q: "代码位置", pre: "src/intellisort_perception/intellisort_perception/pose_estimator_node.py" },
          { q: "如何运行", pre: "ros2 run intellisort_perception pose_estimator_node" },
          { q: "如何验证", a: "与 synthetic_targets 位置对比；RViz Marker 对齐。" },
        ]));
    },

    ompl() {
      return pageHeader("LEARN", "OMPL 规划", "MoveIt2 采样规划。") +
        section("学习卡片", learnCard([
          { q: "这是什么", a: "运动规划库，本项目用 RRTConnect。" },
          { q: "为什么需要", a: "高维避障路径难以手写。" },
          { q: "在本项目中负责什么", a: "到预抓取/放置点的关节轨迹。" },
          { q: "输入", a: "起始状态、目标约束、PlanningScene" },
          { q: "输出", a: "可执行轨迹或失败码" },
          { q: "ROS2 实现", a: "move_group + ompl_planning.yaml" },
          { q: "代码位置", pre: "src/intellisort_moveit_config/config/ompl_planning.yaml" },
          { q: "如何运行", pre: "ros2 launch intellisort_moveit_config move_group.launch.py" },
          { q: "如何验证", a: "RViz MotionPlanning；成功率与规划时间。" },
        ]));
    },

    bt() {
      return pageHeader("LEARN", "行为树任务", "Python 编排 + XML 规范。") +
        section("学习卡片", learnCard([
          { q: "这是什么", a: "Sequence/Fallback 结构的多阶段任务。" },
          { q: "为什么需要", a: "比巨大 if-else 可维护，失败分支清晰。" },
          { q: "在本项目中负责什么", a: "感知→抓→放→确认→恢复。" },
          { q: "输入", a: "目标列表、槽位、重试上限" },
          { q: "输出", a: "/task_status /execute_task 结果" },
          { q: "ROS2 实现", a: "task_manager_node + bt/*.xml" },
          { q: "代码位置", pre: "src/intellisort_task/intellisort_task/task_manager_node.py\nsrc/intellisort_task/bt/main_tree.xml" },
          { q: "如何运行", pre: "ros2 run intellisort_demo run_pick_demo" },
          { q: "如何验证", a: "任务完成率；异常时进入 Recovery。" },
        ]));
    },

    "arch-perception"() {
      return pageHeader("DRILL", "感知系统", "继续下钻到三级知识页。") +
        section("入口", `<div class="drill">
          <a href="#/detection"><div><div class="t">目标检测</div></div><div class="go">→</div></a>
          <a href="#/pose-estimation"><div><div class="t">位姿估计</div></div><div class="go">→</div></a>
          <a href="#/perception"><div><div class="t">感知总览</div></div><div class="go">→</div></a>
        </div>`);
    },
    "arch-motion"() {
      return pageHeader("DRILL", "运动规划", "MoveIt2 / OMPL / 碰撞。") +
        section("入口", `<div class="drill">
          <a href="#/ompl"><div><div class="t">OMPL 规划</div></div><div class="go">→</div></a>
          <a href="#/motion"><div><div class="t">规划总览</div></div><div class="go">→</div></a>
        </div>`);
    },
    "arch-control"() {
      return pageHeader("DRILL", "控制系统", "ros2_control 与夹爪。") +
        section("控制栈", code(`move_group → arm_controller (FollowJointTrajectory)
           → gripper_server (/gripper_command)
           → gazebo_ros2_control / xarm driver`)) +
        section("要点", `<div class="callout">上层只依赖标准控制接口；换臂只换 hardware plugin 与参数。</div>`);
    },
  };

  function renderNav(activeId) {
    const nav = $("#nav");
    let html = "";
    let sec = "";
    data.nav.forEach((item) => {
      if (item.section !== sec) {
        sec = item.section;
        html += `<div class="nav-section">${sec}</div>`;
      }
      html += `<a href="#/${item.id}" class="${item.id === activeId ? "active" : ""}">
        <span class="idx">${item.icon}</span><span>${item.title}</span></a>`;
    });
    nav.innerHTML = html;
  }

  function renderBreadcrumb(id) {
    const parts = pageMeta[id] || ["页面"];
    $("#breadcrumb").innerHTML =
      `<a href="#/home">首页</a>` +
      parts.map((p, i) => {
        const last = i === parts.length - 1;
        return `<span class="sep">/</span>` + (last ? `<span class="current">${p}</span>` : `<span>${p}</span>`);
      }).join("");
    document.title = `${parts[parts.length - 1]} · IntelliSort Workcell`;
  }

  function parseRoute() {
    return (location.hash || "#/home").replace(/^#\/?/, "") || "home";
  }

  function render() {
    const id = parseRoute();
    const fn = pages[id] || pages.home;
    $("#content").innerHTML = fn();
    renderNav(id);
    renderBreadcrumb(id);
    window.scrollTo(0, 0);
    closeSidebar();
  }

  function closeSidebar() {
    $("#sidebar").classList.remove("open");
    $("#overlay").classList.remove("show");
  }
  function openSidebar() {
    $("#sidebar").classList.add("open");
    $("#overlay").classList.add("show");
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("#menuBtn").addEventListener("click", openSidebar);
    $("#overlay").addEventListener("click", closeSidebar);
    window.addEventListener("hashchange", render);
    render();
  });
})();
