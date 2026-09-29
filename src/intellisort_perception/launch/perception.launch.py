from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg = get_package_share_directory('intellisort_perception')
    default_yaml = os.path.join(pkg, 'config', 'perception.yaml')
    params = LaunchConfiguration('params_file')

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_yaml),
        Node(
            package='intellisort_perception',
            executable='detector_node',
            name='object_detection',
            output='screen',
            parameters=[params],
        ),
        Node(
            package='intellisort_perception',
            executable='pose_estimator_node',
            name='pose_estimator',
            output='screen',
            parameters=[params],
        ),
        Node(
            package='intellisort_perception',
            executable='workspace_state_node',
            name='workspace_state',
            output='screen',
            parameters=[params],
        ),
    ])
