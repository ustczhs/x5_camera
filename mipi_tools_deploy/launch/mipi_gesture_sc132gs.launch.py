# 手势识别：CAM_TYPE=mipi + SC132GS 适配（与官方 hand_gesture_detection.launch.py 等价，
# 但 hand_lmk 子链路改用 mipi_hand_lmk_sc132gs.launch.py，解决 config/*.hbm 相对路径与 F37 默认值问题。

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    here = os.path.dirname(os.path.abspath(__file__))

    web_smart_topic_arg = DeclareLaunchArgument(
        "smart_topic",
        default_value="/hobot_hand_gesture_detection",
        description="websocket smart topic",
    )
    is_dynamic_gesture_arg = DeclareLaunchArgument(
        "is_dynamic_gesture",
        default_value="false",
        description="true is dynamic gesture, false is static gesture",
    )
    log_level_arg = DeclareLaunchArgument(
        "log_level",
        default_value="warn",
        description="log level",
    )
    time_interval_sec_arg = DeclareLaunchArgument(
        "time_interval_sec",
        default_value="0.25",
        description="time interval for hand gesture voting",
    )

    hand_lmk_det_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(here, "mipi_hand_lmk_sc132gs.launch.py")
        ),
        launch_arguments={
            "smart_topic": "/hobot_hand_gesture_detection",
            "hand_lmk_pub_topic": "/hobot_hand_lmk_detection",
        }.items(),
    )

    hand_gesture_det_node = Node(
        package="hand_gesture_detection",
        executable="hand_gesture_detection",
        output="screen",
        parameters=[
            {"ai_msg_pub_topic_name": "/hobot_hand_gesture_detection"},
            {"ai_msg_sub_topic_name": "/hobot_hand_lmk_detection"},
            {"is_dynamic_gesture": LaunchConfiguration("is_dynamic_gesture")},
            {"time_interval_sec": LaunchConfiguration("time_interval_sec")},
        ],
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
    )

    return LaunchDescription(
        [
            web_smart_topic_arg,
            is_dynamic_gesture_arg,
            log_level_arg,
            time_interval_sec_arg,
            hand_lmk_det_node,
            hand_gesture_det_node,
        ]
    )
