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
        default_value="config/yolov5workconfig.json",
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
                "image_width": 960,
                "image_height": 544,
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
            OpaqueFunction(function=_preflight_mipi_tools),
            mipi_detect,
            eye_node,
        ]
    )
