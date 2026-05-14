# MIPI + dnn_node_example（BPU 检测）+ 可选 JPEG + WebSocket。
# 默认：YOLO26 nano、640×640、15fps、关闭 MJPEG/WebSocket；开启预览须显式设置 websocket_output_fps>0。
# 默认插入 topic_tools Throttle（与 mipi 同容器），将 dnn 实际订阅帧率限制为 image_throttle_hz（需 apt 安装 ros-humble-topic-tools）。
# Copyright (c) 2024 D-Robotics (derived); Apache-2.0

import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch.utilities import perform_substitutions
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode


def _validate_preview_fps(context):
    """enable_preview 为 true/1 时，要求 websocket_output_fps 为大于 0 的数值（与 IfCondition 一致，勿用 yes/on）。"""
    preview_raw = perform_substitutions(context, [LaunchConfiguration("enable_preview")]).strip().lower()
    preview_on = preview_raw in ("true", "1")
    fps_raw = perform_substitutions(context, [LaunchConfiguration("websocket_output_fps")]).strip()
    if preview_on:
        try:
            fps = float(fps_raw)
        except ValueError as e:
            raise RuntimeError(
                "enable_preview 为 true 或 1 时必须设置有效 websocket_output_fps（例如 websocket_output_fps:=10）"
            ) from e
        if fps <= 0.0:
            raise RuntimeError(
                f"开启 MJPEG/WebSocket 时 websocket_output_fps 必须大于 0（当前为 {fps_raw!r}）"
            )
    return []


def generate_launch_description():
    dnn_node_example_path = os.path.join(
        get_package_prefix("dnn_node_example"), "lib/dnn_node_example"
    )
    os.system("cp -r " + dnn_node_example_path + "/config .")

    validate_preview = OpaqueFunction(function=_validate_preview_fps)

    config_file_launch_arg = DeclareLaunchArgument(
        "dnn_example_config_file",
        default_value=TextSubstitution(text="config/yolo26workconfig.json"),
        description="dnn_node 工作目录下相对 config 路径；默认 YOLO26 nano",
    )
    dump_render_launch_arg = DeclareLaunchArgument(
        "dnn_example_dump_render_img", default_value=TextSubstitution(text="0")
    )
    image_width_launch_arg = DeclareLaunchArgument(
        "dnn_example_image_width",
        default_value=TextSubstitution(text="640"),
        description="MIPI 输出宽，需与 eye_track 等下游一致",
    )
    image_height_launch_arg = DeclareLaunchArgument(
        "dnn_example_image_height",
        default_value=TextSubstitution(text="640"),
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
        default_value="realtime",
        description="与官方 dnn_node_example_mipi_component 一致：realtime；亦可 sensor",
    )
    mipi_framerate_arg = DeclareLaunchArgument(
        "mipi_image_framerate",
        default_value="15.0",
        description="传给 mipi_cam 的 framerate（部分机型上 /image_raw 仍可能满帧）",
    )
    mipi_device_mode_arg = DeclareLaunchArgument(
        "mipi_device_mode",
        default_value="single",
        description="mipi device_mode：single / dual",
    )
    mipi_dual_combine_arg = DeclareLaunchArgument(
        "mipi_dual_combine",
        default_value="0",
        description="dual 模式下输出通道；single 时保持 0",
    )
    mipi_gdc_enable_arg = DeclareLaunchArgument(
        "mipi_gdc_enable",
        default_value="false",
        description="GDC 几何校正；false 可明显降 CPU（画面几何略差时可开 true）",
    )
    mipi_gdc_bin_arg = DeclareLaunchArgument(
        "mipi_gdc_bin_file",
        default_value="",
        description="GDC bin 路径；gdc 关闭时通常可留空",
    )
    mipi_sub_stream_enable_arg = DeclareLaunchArgument(
        "mipi_sub_stream_enable",
        default_value="false",
        description="是否启用子流；false 避免 960x540 等子路处理",
    )
    mipi_stream_mode_arg = DeclareLaunchArgument(
        "mipi_stream_mode",
        default_value="0",
        description="与官方 dual launch 一致：stream_mode",
    )
    image_throttle_hz_arg = DeclareLaunchArgument(
        "image_throttle_hz",
        default_value=TextSubstitution(text="15.0"),
        description=">0：同容器内加载 topic_tools::ThrottleNode，限定 dnn 输入帧率；0：dnn 直接订阅 /image_raw（需 apt 安装 ros-humble-topic-tools）",
    )
    image_throttle_out_topic_arg = DeclareLaunchArgument(
        "image_throttle_out_topic",
        default_value=TextSubstitution(text="/image_raw_to_dnn"),
        description="限帧输出话题（image_throttle_hz>0 时 dnn 订阅此话题）",
    )
    codec_jpg_quality_arg = DeclareLaunchArgument(
        "codec_jpg_quality",
        default_value="80.0",
        description="MJPEG JPEG quality 0-100（仅 enable_preview=true 时生效）",
    )
    websocket_output_fps_arg = DeclareLaunchArgument(
        "websocket_output_fps",
        default_value="0",
        description="Web 输出帧率；enable_preview=true 时必须 >0。未开预览时忽略",
    )
    enable_preview_arg = DeclareLaunchArgument(
        "enable_preview",
        default_value="false",
        description="是否启动 JPEG 编码 + WebSocket（:8000）；true 时必须设置 websocket_output_fps>0",
    )

    mipi_params = [
        {"out_format": "nv12"},
        {"image_width": LaunchConfiguration("dnn_example_image_width")},
        {"image_height": LaunchConfiguration("dnn_example_image_height")},
        {"sub_image_width": LaunchConfiguration("dnn_example_image_width")},
        {"sub_image_height": LaunchConfiguration("dnn_example_image_height")},
        {"io_method": "ros"},
        {"video_device": LaunchConfiguration("device")},
        {"device_mode": LaunchConfiguration("mipi_device_mode")},
        {"dual_combine": LaunchConfiguration("mipi_dual_combine")},
        {"frame_ts_type": LaunchConfiguration("mipi_frame_ts_type")},
        {"framerate": LaunchConfiguration("mipi_image_framerate")},
        {"gdc_enable": LaunchConfiguration("mipi_gdc_enable")},
        {"gdc_bin_file": LaunchConfiguration("mipi_gdc_bin_file")},
        {"sub_stream_enable": LaunchConfiguration("mipi_sub_stream_enable")},
        {"stream_mode": LaunchConfiguration("mipi_stream_mode")},
        {
            "camera_calibration_file_path": LaunchConfiguration(
                "mipi_camera_calibration_file_path"
            )
        },
    ]

    def _load_mipi_throttle_dnn(context):
        hz_raw = perform_substitutions(context, [LaunchConfiguration("image_throttle_hz")]).strip()
        try:
            hz = float(hz_raw)
        except ValueError:
            hz = 0.0
        use_throttle = hz > 0.0
        out_topic = perform_substitutions(
            context, [LaunchConfiguration("image_throttle_out_topic")]
        ).strip()
        if not out_topic.startswith("/"):
            out_topic = "/" + out_topic
        dnn_img_topic = out_topic if use_throttle else "/image_raw"

        descs = [
            ComposableNode(
                package="mipi_cam",
                plugin="mipi_cam::MipiCamNode",
                name="mipi_cam_node",
                parameters=mipi_params,
                extra_arguments=[{"use_intra_process_comms": True}],
            )
        ]
        if use_throttle:
            descs.append(
                ComposableNode(
                    package="topic_tools",
                    plugin="topic_tools::ThrottleNode",
                    name="image_raw_throttle",
                    parameters=[
                        {"input_topic": "/image_raw"},
                        {"output_topic": out_topic},
                        {"throttle_type": "messages"},
                        {"msgs_per_sec": hz},
                        {"lazy": False},
                    ],
                    extra_arguments=[{"use_intra_process_comms": True}],
                )
            )
        descs.append(
            ComposableNode(
                package="dnn_node_example",
                plugin="DnnExampleNode",
                name="perc_node",
                parameters=[
                    {"feed_type": 1},
                    {"config_file": LaunchConfiguration("dnn_example_config_file")},
                    {"ros_img_topic_name": dnn_img_topic},
                    {
                        "msg_pub_topic_name": LaunchConfiguration(
                            "dnn_example_msg_pub_topic_name"
                        )
                    },
                    {"dump_render_img": LaunchConfiguration("dnn_example_dump_render_img")},
                ],
                extra_arguments=[{"use_intra_process_comms": True}],
            )
        )
        return [
            LoadComposableNodes(
                target_container=LaunchConfiguration("container_name"),
                composable_node_descriptions=descs,
            )
        ]

    load_cam_dnn = OpaqueFunction(function=_load_mipi_throttle_dnn)

    load_jpeg_encoder = LoadComposableNodes(
        target_container=LaunchConfiguration("container_name"),
        condition=IfCondition(LaunchConfiguration("enable_preview")),
        composable_node_descriptions=[
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
        condition=IfCondition(LaunchConfiguration("enable_preview")),
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
            validate_preview,
            mipi_cam_device_arg,
            mipi_calib_arg,
            mipi_frame_ts_arg,
            mipi_framerate_arg,
            mipi_device_mode_arg,
            mipi_dual_combine_arg,
            mipi_gdc_enable_arg,
            mipi_gdc_bin_arg,
            mipi_sub_stream_enable_arg,
            mipi_stream_mode_arg,
            image_throttle_hz_arg,
            image_throttle_out_topic_arg,
            codec_jpg_quality_arg,
            websocket_output_fps_arg,
            enable_preview_arg,
            config_file_launch_arg,
            dump_render_launch_arg,
            image_width_launch_arg,
            image_height_launch_arg,
            msg_pub_topic_name_launch_arg,
            declare_container_name_cmd,
            declare_log_level_cmd,
            bringup_cmd_group,
            load_cam_dnn,
            load_jpeg_encoder,
            web_node,
        ]
    )
