from setuptools import setup

package_name = 'intellisort_scene'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='IntelliSort',
    maintainer_email='wqh001-edu@users.noreply.github.com',
    description='MoveIt PlanningScene synchronization for IntelliSort Workcell',
    license='MIT',
    entry_points={
        'console_scripts': [
            'scene_builder_node = intellisort_scene.scene_builder_node:main',
        ],
    },
)
