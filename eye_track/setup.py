from setuptools import setup

package_name = "eye_track"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.txt"]),
        ("share/" + package_name + "/launch", ["launch/eye_track.launch.py"]),
        ("share/" + package_name + "/scripts", ["scripts/launch_eye_track_board.sh"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="x5_camera2",
    maintainer_email="maintainer@example.com",
    description="Eye gaze from person detection via x5_roboeyes TCP look command.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "eye_track_node = eye_track.eye_tracker_node:main",
        ],
    },
)
