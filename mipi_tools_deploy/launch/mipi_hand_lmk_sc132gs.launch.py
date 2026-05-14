# hand_lmk_detection 链路的 SC132GS/X5 适配：绝对路径 .hbm + mipi device=default。
# 替代官方 hand_lmk_detection.launch.py 中被 Include 的同名片段逻辑。

import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    mono2d_prefix = get_package_prefix("mono2d_body_detection")
    hand_lmk_prefix = get_package_prefix("hand_lmk_detection")
    kps_default = os.path.join(
        mono2d_prefix,
        "lib/mono2d_body_detection/config/multitask_body_head_face_hand_kps_960x544.hbm",
    )
    hand_default = os.path.join(
        hand_lmk_prefix,
        "lib/hand_lmk_detection/config/handLMKs.hbm",
    )

    web_smart_topic_arg = DeclareLaunchArgument(
        "smart_topic",
        default_value="/hobot_hand_lmk_detection",
        description="websocket smart topic",
    )
    kps_model_arg = DeclareLaunchArgument(
        "kps_model_file_name",
        default_value=TextSubstitution(text=kps_default),
        description="absolute path to mono2d multitask .hbm",
    )
    device_arg = DeclareLaunchArgument(
        "device",
        default_value="default",
        description="mipi_cam video_device (default for SC132GS)",
    )

    mono2d_body_det_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("mono2d_body_detection"),
                "launch/mono2d_body_detection.launch.py",
            )
        ),
        launch_arguments={
            "smart_topic": LaunchConfiguration("smart_topic"),
            "mono2d_body_pub_topic": "/hobot_mono2d_body_detection",
            "kps_model_file_name": LaunchConfiguration("kps_model_file_name"),
            "device": LaunchConfiguration("device"),
        }.items(),
    )

    hand_lmk_pub_topic_arg = DeclareLaunchArgument(
        "hand_lmk_pub_topic",
        default_value="/hobot_hand_lmk_detection",
        description="hand landmark ai message publish topic",
    )

    hand_lmk_det_node = Node(
        package="hand_lmk_detection",
        executable="hand_lmk_detection",
        output="screen",
        parameters=[
            {"ai_msg_pub_topic_name": LaunchConfiguration("hand_lmk_pub_topic")},
            {"ai_msg_sub_topic_name": "/hobot_mono2d_body_detection"},
            {"model_file_name": hand_default},
        ],
        arguments=["--ros-args", "--log-level", "warn"],
    )

    return LaunchDescription(
        [
            web_smart_topic_arg,
            kps_model_arg,
            device_arg,
            mono2d_body_det_node,
            hand_lmk_pub_topic_arg,
            hand_lmk_det_node,
        ]
    )
