# 基于官方 mipi_cam_websocket.launch.py：
# SC132GS 等在 mipi_io_method:=ros 时 /image_raw 实际为 bgr8，hobot_codec 默认 nv12 会报错，
# 此处显式指定 mipi_out_format 与 codec_in_format 为 bgr8。
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python import get_package_share_directory


def generate_launch_description():
    print("camera_type is ", os.getenv("CAM_TYPE"))

    mipi_camera_calibration_file_path_arg = DeclareLaunchArgument(
        "mipi_camera_calibration_file_path",
        default_value="default",
        description="mipi camera calibration file path",
    )
    mipi_camera_gdc_file_path_arg = DeclareLaunchArgument(
        "mipi_gdc_bin_file",
        default_value="default",
        description="mipi camera gdc file path",
    )
    mipi_rotation_arg = DeclareLaunchArgument(
        "mipi_rotation",
        default_value="0.0",
        description="mipi camera out image rotation",
    )
    mipi_cal_rotation_arg = DeclareLaunchArgument(
        "mipi_cal_rotation",
        default_value="0.0",
        description="mipi camera calibration rotation",
    )
    mipi_image_width_arg = DeclareLaunchArgument(
        "mipi_image_width",
        default_value="960",
        description="mipi camera out image width",
    )
    mipi_image_height_arg = DeclareLaunchArgument(
        "mipi_image_height",
        default_value="544",
        description="mipi camera out image height",
    )
    mipi_channel_arg = DeclareLaunchArgument(
        "mipi_channel",
        default_value="0",
        description="mipi camera host channel",
    )
    mipi_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("mipi_cam"),
                "launch/mipi_cam.launch.py",
            )
        ),
        launch_arguments={
            "mipi_image_width": LaunchConfiguration("mipi_image_width"),
            "mipi_image_height": LaunchConfiguration("mipi_image_height"),
            "mipi_io_method": "ros",
            "mipi_channel": LaunchConfiguration("mipi_channel"),
            "mipi_camera_calibration_file_path": LaunchConfiguration(
                "mipi_camera_calibration_file_path"
            ),
            "mipi_gdc_bin_file": LaunchConfiguration("mipi_gdc_bin_file"),
            "mipi_rotation": LaunchConfiguration("mipi_rotation"),
            "mipi_cal_rotation": LaunchConfiguration("mipi_cal_rotation"),
            "mipi_frame_ts_type": "sensor",
        }.items(),
    )

    jpeg_codec_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("hobot_codec"),
                "launch/hobot_codec_encode.launch.py",
            )
        ),
        launch_arguments={
            "codec_in_mode": "ros",
            "codec_in_format": "bgr8",
            "codec_out_mode": "ros",
            "codec_jpg_quality": "85.0",
            "codec_sub_topic": "/image_raw",
            "codec_pub_topic": "/image_jpeg",
        }.items(),
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
            "websocket_only_show_image": "True",
        }.items(),
    )
    shared_mem_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("hobot_shm"),
                "launch/hobot_shm.launch.py",
            )
        )
    )

    return LaunchDescription(
        [
            mipi_camera_calibration_file_path_arg,
            mipi_camera_gdc_file_path_arg,
            mipi_image_width_arg,
            mipi_image_height_arg,
            mipi_rotation_arg,
            mipi_cal_rotation_arg,
            mipi_channel_arg,
            shared_mem_node,
            mipi_node,
            jpeg_codec_node,
            web_node,
        ]
    )
