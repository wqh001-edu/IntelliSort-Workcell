"""
IntelliSort Workcell — full system bringup (sim).

Launches:
  Gazebo workcell + robot + controllers
  MoveIt2 move_group (+ optional RViz)
  Perception (detector / pose / workspace)
  Grasp planner
  Scene builder
  Task manager + gripper + supervisor + metrics
  Hardware mode manager

Usage:
  ros2 launch intellisort_bringup demo.launch.py
  ros2 launch intellisort_bringup demo.launch.py use_rviz:=true
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')
    auto_run = LaunchConfiguration('auto_run_demo')

    pkg_gazebo = get_package_share_directory('intellisort_gazebo')
    pkg_moveit = get_package_share_directory('intellisort_moveit_config')
    pkg_perception = get_package_share_directory('intellisort_perception')
    pkg_bringup = get_package_share_directory('intellisort_bringup')

    perception_yaml = os.path.join(pkg_perception, 'config', 'perception.yaml')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo, 'launch', 'gazebo_workcell.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    # Give Gazebo + controllers a moment before MoveIt / task stack
    moveit = TimerAction(
        period=4.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_moveit, 'launch', 'move_group.launch.py')),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'use_rviz': use_rviz,
                }.items(),
            )
        ],
    )

    stack = TimerAction(
        period=7.0,
        actions=[
            Node(
                package='intellisort_perception',
                executable='detector_node',
                name='object_detection',
                output='screen',
                parameters=[perception_yaml, {'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_perception',
                executable='pose_estimator_node',
                name='pose_estimator',
                output='screen',
                parameters=[perception_yaml, {'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_perception',
                executable='workspace_state_node',
                name='workspace_state',
                output='screen',
                parameters=[perception_yaml, {'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_grasp',
                executable='grasp_planner_node',
                name='grasp_planner',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_scene',
                executable='scene_builder_node',
                name='scene_builder',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_task',
                executable='gripper_server_node',
                name='gripper_server',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_task',
                executable='supervisor_node',
                name='supervisor',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_task',
                executable='metric_publisher_node',
                name='metric_publisher',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
            ),
            Node(
                package='intellisort_hw_abstraction',
                executable='mode_manager',
                name='mode_manager',
                output='screen',
                parameters=[os.path.join(pkg_bringup, 'config', 'system.yaml')],
            ),
            Node(
                package='intellisort_task',
                executable='task_manager_node',
                name='task_manager',
                output='screen',
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'auto_run_demo': auto_run,
                    'max_targets': 4,
                    'enable_recovery': True,
                }],
            ),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('auto_run_demo', default_value='false'),
        gazebo,
        moveit,
        stack,
    ])
