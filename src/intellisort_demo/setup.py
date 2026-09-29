from setuptools import setup

package_name = 'intellisort_demo'

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
    description='Demo scripts, synthetic targets and acceptance runners',
    license='MIT',
    entry_points={
        'console_scripts': [
            'synthetic_targets = intellisort_demo.synthetic_targets:main',
            'run_pick_demo = intellisort_demo.run_pick_demo:main',
        ],
    },
)
