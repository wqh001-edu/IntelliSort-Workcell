"""MoveIt2 move_group + optional RViz."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_desc = get_package_share_directory('intellisort_description')
    pkg_moveit = get_package_share_directory('intellisort_moveit_config')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')

    xacro_file = os.path.join(pkg_desc, 'urdf', 'isc_workcell.urdf.xacro')
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' use_sim:=true']),
        value_type=str)

    srdf = os.path.join(pkg_moveit, 'srdf', 'isc_arm.srdf')
    with open(srdf, 'r', encoding='utf-8') as f:
        robot_description_semantic = f.read()

    kinematics_yaml = os.path.join(pkg_moveit, 'config', 'kinematics.yaml')
    ompl_yaml = os.path.join(pkg_moveit, 'config', 'ompl_planning.yaml')
    joint_limits_yaml = os.path.join(pkg_moveit, 'config', 'joint_limits.yaml')
    controllers_yaml = os.path.join(pkg_moveit, 'config', 'moveit_controllers.yaml')

    move_group = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            {'robot_description': robot_description,
             'robot_description_semantic': robot_description_semantic,
             'use_sim_time': use_sim_time,
             'publish_robot_description_semantic': True},
            kinematics_yaml,
            ompl_yaml,
            joint_limits_yaml,
            controllers_yaml,
            {'moveit_manage_controllers': True,
             'trajectory_execution.allowed_execution_duration_scaling': 1.2,
             'trajectory_execution.allowed_goal_duration_margin': 0.5,
             'planning_scene_monitor.publish_planning_scene': True,
             'planning_scene_monitor.publish_geometry_updates': True,
             'planning_scene_monitor.publish_state_updates': True,
             'planning_scene_monitor.publish_transforms_updates': True},
        ],
    )

    rviz_config = os.path.join(pkg_moveit, 'config', 'moveit.rviz')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{
            'robot_description': robot_description,
            'robot_description_semantic': robot_description_semantic,
            'use_sim_time': use_sim_time,
        }],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        move_group,
        rviz,
    ])
