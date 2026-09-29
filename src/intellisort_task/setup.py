from setuptools import setup

package_name = 'intellisort_task'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/bt', ['bt/main_tree.xml', 'bt/recovery_subtree.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='IntelliSort',
    maintainer_email='wqh001-edu@users.noreply.github.com',
    description='Task orchestration, behavior tree and exception recovery',
    license='MIT',
    entry_points={
        'console_scripts': [
            'task_manager_node = intellisort_task.task_manager_node:main',
            'supervisor_node = intellisort_task.supervisor_node:main',
            'metric_publisher_node = intellisort_task.metric_publisher_node:main',
            'gripper_server_node = intellisort_task.gripper_server_node:main',
        ],
    },
)
