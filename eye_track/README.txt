eye_track — MIPI 检测 + 眼随人动（一键 launch）
==============================================

本包 `launch/eye_track.launch.py` 会：
  1) `chdir` 到 `mipi_tools_dir`（默认 `/root/mipi_tools`），再 Include
     `launch/mipi_detect_websocket.launch.py`（与 `mipi_detect_preview.sh` 同源，MIPI + YOLO + Web :8000）
  2) 启动 `eye_track_node`，订阅 `/hobot_dnn_detection`，向 `127.0.0.1:8765` 发 TCP `look px py`

板端前置
--------
  - `/root/mipi_tools/` 已部署（含 `launch/mipi_detect_websocket.launch.py`、`env.sh`）
  - `x5_roboeyes` 已开 TCP（如 `--tcp 8765`）
  - 已安装 `tros-humble-dnn-node-example`、`hobot-models-basic` 等（与 MIPI 检测说明一致）

编译（已在板 `/root/ros2_ws` 示范）
----------------------------------
  source /opt/tros/humble/setup.bash
  cd /root/ros2_ws
  colcon build --packages-select eye_track --symlink-install
  source install/setup.bash

推荐启动（launch 内已自动执行 mipi_stop_conflicts，勿与下面「手动 source」重复）
--------------------------------------------------------------------------------
  bash /root/ros2_ws/install/eye_track/share/eye_track/scripts/launch_eye_track_board.sh

或手动：
  source /root/mipi_tools/env.sh
  source /root/ros2_ws/install/setup.bash
  ros2 launch eye_track eye_track.launch.py

若仍手动 source mipi_stop_conflicts.sh 后再 launch，会多执行一次停冲突/重启 cam，一般仍可工作，但异常时更易出现 MIPI gpio 问题，建议只保留上面一种方式。

异常退出（Ctrl+Z、kill -9）后若再次启动报 mipi host/gpio failure：先
  pkill -x mipi_cam; pkill -x websocket; pkill -x hobot_codec; pkill -x component_container_isolated
  再 launch；无效则 reboot。

结束请用 Ctrl+C，勿用 Ctrl+Z 挂起（易残留占 MIPI 的进程）。

可选 launch 参数：
  mipi_tools_dir:=/root/mipi_tools
  mipi_camera_calibration_file_path:=/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml
  dnn_example_config_file:=config/yolov5workconfig.json

浏览器预览检测画面：http://<板IP>:8000

眼控参数在 `launch/eye_track.launch.py` 的 `eye_node` 里修改（如 `flip_horizontal`、`gaze_gain` 注视幅度，默认 3.0，再大会更快顶满 ±1）。
