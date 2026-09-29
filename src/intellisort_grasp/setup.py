from setuptools import setup

package_name = 'intellisort_grasp'

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
    description='Grasp candidate generation for IntelliSort Workcell',
    license='MIT',
    entry_points={
        'console_scripts': [
            'grasp_planner_node = intellisort_grasp.grasp_planner_node:main',
        ],
    },
)
