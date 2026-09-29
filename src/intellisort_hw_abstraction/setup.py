from setuptools import setup

package_name = 'intellisort_hw_abstraction'

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
    description='Sim/real hardware abstraction and driver adapters',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mode_manager = intellisort_hw_abstraction.mode_manager:main',
        ],
    },
)
