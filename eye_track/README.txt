eye_track — MIPI 检测 + 眼随人动（一键 launch）
==============================================

本包 `launch/eye_track.launch.py` 会：
  1) `chdir` 到 `mipi_tools_dir`（默认 `/root/mipi_tools`），再 Include
     `launch/mipi_detect_websocket.launch.py`（与 `mipi_detect_preview.sh` 同源：MIPI + BPU 检测；**浏览器 MJPEG 默认关闭**）
  2) 启动 `eye_track_node`，订阅 `/hobot_dnn_detection`，向 `127.0.0.1:8765` 发 TCP `look px py`

默认（省资源）
--------------
  - 检测配置：`config/yolo26workconfig.json`（YOLO26 **nano**，板载模型路径见该 json）
  - 图像：`640×640`，MIPI 参数 `mipi_image_framerate:=15.0`（**部分固件上 `/image_raw` 仍可能约 60Hz**，见 `mipi_tools/README_MIPI.txt` 排查节）
  - `image_throttle_hz` 默认 **15.0**：同容器内 **`topic_tools::ThrottleNode`**，dnn 订阅 **`/image_raw_to_dnn`**（需 `sudo apt install ros-humble-topic-tools`）；设为 **0** 则 dnn 直接订 `/image_raw`
  - `mipi_gdc_enable:=false`、`mipi_sub_stream_enable:=false`（省 GDC/子流；要校正再 `mipi_gdc_enable:=true`）
  - `mipi_frame_ts_type` 默认 `realtime`（与官方 dnn+mipi component 一致）
  - `enable_preview:=false`：不启动 JPEG 编码与 WebSocket
  - 若 `enable_preview:=true`，**必须**同时设置 `websocket_output_fps:=` 大于 0（例如 `10`），否则 launch 会报错退出

板端前置
--------
  - `/root/mipi_tools/` 已部署（含 `launch/mipi_detect_websocket.launch.py`、`env.sh`，以及建议同步的 `config/yolo26workconfig.json`）
  - `x5_roboeyes` 已开 TCP（如 `--tcp 8765`）
  - 已安装 `tros-humble-dnn-node-example`；**`sudo apt install ros-humble-topic-tools`**（launch 默认用 Throttle 限 dnn 输入帧率）
  - YOLO26 需 `dnn_Parser` 支持 `ultralytics_yolo`（与当前 TROS 版本一致）

编译（已在板 `/root/ros2_ws` 示范）
----------------------------------
  source /opt/tros/humble/setup.bash
  cd /root/ros2_ws
  colcon build --packages-select eye_track --symlink-install
  source install/setup.bash

systemd（手动启停，默认不开机自启）
----------------------------------
  安装单元（以下为板端默认路径；若 ROS2_WS 不同请改 unit 内路径或 `systemctl edit`）：
    sudo cp /root/ros2_ws/install/eye_track/share/eye_track/scripts/eye-track.service /etc/systemd/system/
    sudo systemctl daemon-reload
  启动 / 停止 / 状态：
    sudo systemctl start eye-track.service
    sudo systemctl stop eye-track.service
    sudo systemctl status eye-track.service
  日志：
    journalctl -u eye-track.service -f
  **不要**执行 `sudo systemctl enable eye-track.service`，则**不会**开机自启；需要开机自启时再 enable。
  改 MIPI/工作区路径或追加 launch 参数：`sudo systemctl edit eye-track.service`（override）。
  若曾报 `Failed to get logging directory` / `rcutils_expand_user failed`：单元内已设 `HOME=/root`；请重新 `cp` 安装后的 `eye-track.service` 到 `/etc/systemd/system/` 并 `daemon-reload`。

推荐启动（launch 内已自动执行 mipi_stop_conflicts，勿与下面「手动 source」重复）
--------------------------------------------------------------------------------
  bash /root/ros2_ws/install/eye_track/share/eye_track/scripts/launch_eye_track_board.sh

或手动：
  source /root/mipi_tools/env.sh
  source /root/ros2_ws/install/setup.bash
  ros2 launch eye_track eye_track.launch.py

带浏览器预览（示例）：
  ros2 launch eye_track eye_track.launch.py enable_preview:=true websocket_output_fps:=10

若仍手动 source mipi_stop_conflicts.sh 后再 launch，会多执行一次停冲突/重启 cam，一般仍可工作，但异常时更易出现 MIPI gpio 问题，建议只保留上面一种方式。

异常退出（Ctrl+Z、kill -9）后若再次启动报 mipi host/gpio failure：先
  pkill -x mipi_cam; pkill -x websocket; pkill -x hobot_codec; pkill -x component_container_isolated
  再 launch；无效则 reboot。

结束请用 Ctrl+C，勿用 Ctrl+Z 挂起（易残留占 MIPI 的进程）。

可选 launch 参数（节选）：
  image_throttle_hz:=15.0          # 0=关闭 topic_tools 限帧
  image_throttle_out_topic:=/image_raw_to_dnn
  mipi_tools_dir:=/root/mipi_tools
  mipi_camera_calibration_file_path:=/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml
  dnn_example_config_file:=config/yolo26workconfig.json
  dnn_example_image_width:=640 dnn_example_image_height:=640
  mipi_image_framerate:=15.0
  enable_preview:=false
  websocket_output_fps:=0

浏览器预览检测画面（仅 enable_preview=true 且 fps>0）：http://<板IP>:8000

眼控参数在 `launch/eye_track.launch.py` 的 `eye_node` 里修改（如 `flip_horizontal`、`gaze_gain` 注视幅度，默认 3.0，再大会更快顶满 ±1）。
