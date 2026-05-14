# MIPI + BPU 检测（mipi_detect_websocket）+ 眼随人动（eye_track_node）一键启动。
# 依赖板端 /root/mipi_tools/launch/mipi_detect_websocket.launch.py（与 mipi_detect_preview.sh 同源）。
# dnn_node 会在当前工作目录复制 config/；OpaqueFunction 内先执行 mipi_stop_conflicts（释放 VIN/ISP），再 chdir。

import os
import shlex
import subprocess
import time

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.utilities import perform_substitutions
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _preflight_mipi_tools(context):
    """与手动 source mipi_stop_conflicts 等效（子 shell 执行 systemctl/pkill），再 chdir 供 dnn 复制 config。"""
    d = perform_substitutions(context, [LaunchConfiguration("mipi_tools_dir")])
    stop = os.path.join(d, "mipi_stop_conflicts.sh")
    if os.path.isfile(stop):
        cmd = f"source {shlex.quote(stop)}"
        r = subprocess.run(["/bin/bash", "-lc", cmd], capture_output=False, check=False)
        if r.returncode != 0:
            print(f"[eye_track.launch] mipi_stop_conflicts.sh exit {r.returncode} (continuing)")
        time.sleep(2.0)
    else:
        print(f"[eye_track.launch] missing {stop}, skip stop_conflicts")
    try:
        os.chdir(d)
    except OSError as e:
        print(f"[eye_track.launch] chdir to {d!r} failed: {e}")
    return []


def generate_launch_description():
    declare_mipi_tools = DeclareLaunchArgument(
        "mipi_tools_dir",
        default_value="/root/mipi_tools",
        description="mipi_tools 根目录（内含 launch/mipi_detect_websocket.launch.py）",
    )
    declare_calib = DeclareLaunchArgument(
        "mipi_camera_calibration_file_path",
        default_value="/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml",
    )
    declare_dnn_cfg = DeclareLaunchArgument(
        "dnn_example_config_file",
        default_value="config/yolo26workconfig.json",
        description="默认 YOLO26 nano；可改回 yolov5workconfig.json 等",
    )
    declare_img_w = DeclareLaunchArgument(
        "dnn_example_image_width",
        default_value="640",
        description="与 mipi_detect 一致，供 eye_track 归一化坐标",
    )
    declare_img_h = DeclareLaunchArgument(
        "dnn_example_image_height",
        default_value="640",
    )
    declare_fps = DeclareLaunchArgument(
        "mipi_image_framerate",
        default_value="15.0",
        description="MIPI 采集帧率",
    )
    declare_enable_preview = DeclareLaunchArgument(
        "enable_preview",
        default_value="false",
        description="true 时启用 MJPEG+WebSocket，须同时设 websocket_output_fps>0",
    )
    declare_ws_fps = DeclareLaunchArgument(
        "websocket_output_fps",
        default_value="0",
        description="仅 enable_preview=true 时生效且必须 >0",
    )
    declare_mipi_ts = DeclareLaunchArgument(
        "mipi_frame_ts_type",
        default_value="realtime",
        description="传给 mipi_detect（与官方 dnn+mipi 示例一致）",
    )
    declare_mipi_gdc = DeclareLaunchArgument(
        "mipi_gdc_enable",
        default_value="false",
        description="GDC；需几何校正时 mipi_gdc_enable:=true，并可设 mipi_gdc_bin_file",
    )
    declare_mipi_gdc_bin = DeclareLaunchArgument(
        "mipi_gdc_bin_file",
        default_value="",
    )
    declare_mipi_sub = DeclareLaunchArgument(
        "mipi_sub_stream_enable",
        default_value="false",
    )
    declare_mipi_dev_mode = DeclareLaunchArgument(
        "mipi_device_mode",
        default_value="single",
    )
    declare_mipi_dual_comb = DeclareLaunchArgument(
        "mipi_dual_combine",
        default_value="0",
    )
    declare_mipi_stream_mode = DeclareLaunchArgument(
        "mipi_stream_mode",
        default_value="0",
    )
    declare_image_throttle_hz = DeclareLaunchArgument(
        "image_throttle_hz",
        default_value="15.0",
        description="topic_tools 限 dnn 输入帧率；0 关闭（dnn 直接订 /image_raw）",
    )
    declare_image_throttle_out = DeclareLaunchArgument(
        "image_throttle_out_topic",
        default_value="/image_raw_to_dnn",
    )

    mipi_detect = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    LaunchConfiguration("mipi_tools_dir"),
                    "launch",
                    "mipi_detect_websocket.launch.py",
                ]
            )
        ),
        launch_arguments={
            "mipi_camera_calibration_file_path": LaunchConfiguration(
                "mipi_camera_calibration_file_path"
            ),
            "dnn_example_config_file": LaunchConfiguration("dnn_example_config_file"),
            "dnn_example_image_width": LaunchConfiguration("dnn_example_image_width"),
            "dnn_example_image_height": LaunchConfiguration("dnn_example_image_height"),
            "mipi_image_framerate": LaunchConfiguration("mipi_image_framerate"),
            "enable_preview": LaunchConfiguration("enable_preview"),
            "websocket_output_fps": LaunchConfiguration("websocket_output_fps"),
            "mipi_frame_ts_type": LaunchConfiguration("mipi_frame_ts_type"),
            "mipi_gdc_enable": LaunchConfiguration("mipi_gdc_enable"),
            "mipi_gdc_bin_file": LaunchConfiguration("mipi_gdc_bin_file"),
            "mipi_sub_stream_enable": LaunchConfiguration("mipi_sub_stream_enable"),
            "mipi_device_mode": LaunchConfiguration("mipi_device_mode"),
            "mipi_dual_combine": LaunchConfiguration("mipi_dual_combine"),
            "mipi_stream_mode": LaunchConfiguration("mipi_stream_mode"),
            "image_throttle_hz": LaunchConfiguration("image_throttle_hz"),
            "image_throttle_out_topic": LaunchConfiguration("image_throttle_out_topic"),
        }.items(),
    )

    eye_node = Node(
        package="eye_track",
        executable="eye_track_node",
        name="eye_track_node",
        output="screen",
        parameters=[
            {
                "detection_topic": "hobot_dnn_detection",
                "image_width": ParameterValue(
                    LaunchConfiguration("dnn_example_image_width"), value_type=int
                ),
                "image_height": ParameterValue(
                    LaunchConfiguration("dnn_example_image_height"), value_type=int
                ),
                "tcp_host": "127.0.0.1",
                "tcp_port": 8765,
                "min_confidence": 0.35,
                "max_send_hz": 20.0,
                "smooth_alpha": 0.35,
                "dead_zone": 0.04,
                "min_move_to_send": 0.012,
                "flip_horizontal": False,
                "flip_vertical": False,
                "lost_decay_frames": 8,
                "lost_decay_factor": 0.88,
                "gaze_gain": 3.0,
            }
        ],
    )

    return LaunchDescription(
        [
            declare_mipi_tools,
            declare_calib,
            declare_dnn_cfg,
            declare_img_w,
            declare_img_h,
            declare_fps,
            declare_enable_preview,
            declare_ws_fps,
            declare_mipi_ts,
            declare_mipi_gdc,
            declare_mipi_gdc_bin,
            declare_mipi_sub,
            declare_mipi_dev_mode,
            declare_mipi_dual_comb,
            declare_mipi_stream_mode,
            declare_image_throttle_hz,
            declare_image_throttle_out,
            OpaqueFunction(function=_preflight_mipi_tools),
            mipi_detect,
            eye_node,
        ]
    )
