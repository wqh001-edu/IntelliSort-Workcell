from setuptools import setup

package_name = 'intellisort_perception'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/perception.launch.py']),
        ('share/' + package_name + '/config', ['config/perception.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='IntelliSort',
    maintainer_email='wqh001-edu@users.noreply.github.com',
    description='Object detection and pose estimation for IntelliSort Workcell',
    license='MIT',
    entry_points={
        'console_scripts': [
            'detector_node = intellisort_perception.detector_node:main',
            'pose_estimator_node = intellisort_perception.pose_estimator_node:main',
            'workspace_state_node = intellisort_perception.workspace_state_node:main',
        ],
    },
)
