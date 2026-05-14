# MIPI + dnn_node_example（BPU 检测）+ JPEG + WebSocket。
# 基于官方 dnn_node_example_mipi_component.launch.py，增加 SC132GS 等标定与编码参数可配置项。
# Copyright (c) 2024 D-Robotics (derived); Apache-2.0

import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    dnn_node_example_path = os.path.join(
        get_package_prefix("dnn_node_example"), "lib/dnn_node_example"
    )
    os.system("cp -r " + dnn_node_example_path + "/config .")

    config_file_launch_arg = DeclareLaunchArgument(
        "dnn_example_config_file",
        default_value=TextSubstitution(text="config/yolov5workconfig.json"),
    )
    dump_render_launch_arg = DeclareLaunchArgument(
        "dnn_example_dump_render_img", default_value=TextSubstitution(text="0")
    )
    image_width_launch_arg = DeclareLaunchArgument(
        "dnn_example_image_width", default_value=TextSubstitution(text="960")
    )
    image_height_launch_arg = DeclareLaunchArgument(
        "dnn_example_image_height", default_value=TextSubstitution(text="544")
    )
    msg_pub_topic_name_launch_arg = DeclareLaunchArgument(
        "dnn_example_msg_pub_topic_name",
        default_value=TextSubstitution(text="hobot_dnn_detection"),
    )
    declare_container_name_cmd = DeclareLaunchArgument(
        "container_name",
        default_value="tros_container",
        description="component container name",
    )
    declare_log_level_cmd = DeclareLaunchArgument(
        "log_level", default_value="warn", description="log level"
    )
    mipi_cam_device_arg = DeclareLaunchArgument(
        "device",
        default_value="default",
        description="mipi camera device (default for auto / SC132GS 等)",
    )
    mipi_calib_arg = DeclareLaunchArgument(
        "mipi_camera_calibration_file_path",
        default_value="/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml",
        description="camera calibration yaml",
    )
    mipi_frame_ts_arg = DeclareLaunchArgument(
        "mipi_frame_ts_type",
        default_value="sensor",
        description="sensor or realtime",
    )
    mipi_framerate_arg = DeclareLaunchArgument(
        "mipi_image_framerate",
        default_value="30.0",
        description="camera framerate (double)",
    )
    codec_jpg_quality_arg = DeclareLaunchArgument(
        "codec_jpg_quality",
        default_value="80.0",
        description="MJPEG JPEG quality 0-100",
    )
    websocket_output_fps_arg = DeclareLaunchArgument(
        "websocket_output_fps",
        default_value="15",
        description="0=unlimited; lower reduces WS buffer warnings",
    )

    mipi_params = [
        {"out_format": "nv12"},
        {"image_width": LaunchConfiguration("dnn_example_image_width")},
        {"image_height": LaunchConfiguration("dnn_example_image_height")},
        {"io_method": "ros"},
        {"video_device": LaunchConfiguration("device")},
        {"frame_ts_type": LaunchConfiguration("mipi_frame_ts_type")},
        {"framerate": LaunchConfiguration("mipi_image_framerate")},
        {
            "camera_calibration_file_path": LaunchConfiguration(
                "mipi_camera_calibration_file_path"
            )
        },
    ]

    load_composable_nodes = LoadComposableNodes(
        target_container=LaunchConfiguration("container_name"),
        composable_node_descriptions=[
            ComposableNode(
                package="mipi_cam",
                plugin="mipi_cam::MipiCamNode",
                name="mipi_cam_node",
                parameters=mipi_params,
                extra_arguments=[{"use_intra_process_comms": True}],
            ),
            ComposableNode(
                package="dnn_node_example",
                plugin="DnnExampleNode",
                name="perc_node",
                parameters=[
                    {"feed_type": 1},
                    {"config_file": LaunchConfiguration("dnn_example_config_file")},
                    {"ros_img_topic_name": "/image_raw"},
                    {
                        "msg_pub_topic_name": LaunchConfiguration(
                            "dnn_example_msg_pub_topic_name"
                        )
                    },
                    {"dump_render_img": LaunchConfiguration("dnn_example_dump_render_img")},
                ],
                extra_arguments=[{"use_intra_process_comms": True}],
            ),
            ComposableNode(
                package="hobot_codec",
                plugin="HobotCodecNode",
                name="image_jpeg_encoder_node",
                parameters=[
                    {"sub_topic": "/image_raw"},
                    {"in_format": "nv12"},
                    {"in_mode": "ros"},
                    {"out_mode": "ros"},
                    {"pub_topic": "/image_jpeg"},
                    {"out_format": "jpeg"},
                    {"jpg_quality": LaunchConfiguration("codec_jpg_quality")},
                ],
                extra_arguments=[{"use_intra_process_comms": True}],
            ),
        ],
    )

    web_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("websocket"),
                "launch/websocket.launch.py",
            )
        ),
        launch_arguments={
            "websocket_image_topic": "/image_jpeg",
            "websocket_image_type": "mjpeg",
            "websocket_smart_topic": LaunchConfiguration("dnn_example_msg_pub_topic_name"),
            "websocket_output_fps": LaunchConfiguration("websocket_output_fps"),
        }.items(),
    )

    bringup_cmd_group = GroupAction(
        [
            Node(
                name="tros_container",
                package="rclcpp_components",
                executable="component_container_isolated",
                exec_name="tros_container",
                parameters=[{"autostart": "True"}],
                arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
                output="screen",
            )
        ]
    )

    return LaunchDescription(
        [
            mipi_cam_device_arg,
            mipi_calib_arg,
            mipi_frame_ts_arg,
            mipi_framerate_arg,
            codec_jpg_quality_arg,
            websocket_output_fps_arg,
            config_file_launch_arg,
            dump_render_launch_arg,
            image_width_launch_arg,
            image_height_launch_arg,
            msg_pub_topic_name_launch_arg,
            declare_container_name_cmd,
            declare_log_level_cmd,
            bringup_cmd_group,
            load_composable_nodes,
            web_node,
        ]
    )
