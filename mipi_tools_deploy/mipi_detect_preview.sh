#!/bin/bash
# BPU 目标检测 + 浏览器 MJPEG（nginx :8000）。依赖 tros-humble-dnn-node-example。
set -eo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$DIR/env.sh"
# shellcheck source=/dev/null
source "$DIR/mipi_stop_conflicts.sh"
CAL="${MIPI_CALIB:-/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml}"
CFG="${DNN_DETECT_CONFIG:-config/yolov5workconfig.json}"
QUAL="${CODEC_JPG_QUALITY:-80.0}"
WSFPS="${WEBSOCKET_OUTPUT_FPS:-15}"
exec ros2 launch "$DIR/launch/mipi_detect_websocket.launch.py" \
  mipi_camera_calibration_file_path:="${CAL}" \
  dnn_example_config_file:="${CFG}" \
  codec_jpg_quality:="${QUAL}" \
  websocket_output_fps:="${WSFPS}" \
  "$@"
