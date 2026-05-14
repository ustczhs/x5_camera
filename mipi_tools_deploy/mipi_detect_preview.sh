#!/bin/bash
# BPU 目标检测 + 可选浏览器 MJPEG（nginx :8000）。依赖 tros-humble-dnn-node-example、ros-humble-topic-tools（限帧）。
# 默认：YOLO26 nano、640×640、15fps、关闭预览；开预览须 ENABLE_PREVIEW=true 且 WEBSOCKET_OUTPUT_FPS>0。
set -eo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$DIR/env.sh"
# shellcheck source=/dev/null
source "$DIR/mipi_stop_conflicts.sh"
CAL="${MIPI_CALIB:-/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml}"
CFG="${DNN_DETECT_CONFIG:-config/yolo26workconfig.json}"
QUAL="${CODEC_JPG_QUALITY:-80.0}"
W="${DNN_IMAGE_WIDTH:-640}"
H="${DNN_IMAGE_HEIGHT:-640}"
FPS="${MIPI_FRAMERATE:-15.0}"
THROTTLE_HZ="${IMAGE_THROTTLE_HZ:-15.0}"
THROTTLE_OUT="${IMAGE_THROTTLE_OUT_TOPIC:-/image_raw_to_dnn}"
ENABLE_PREVIEW_RAW="${ENABLE_PREVIEW:-false}"
WSFPS="${WEBSOCKET_OUTPUT_FPS:-0}"

_preview_on() {
  case "${ENABLE_PREVIEW_RAW,,}" in
    true|1|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

if _preview_on; then
  if ! awk -v x="${WSFPS}" 'BEGIN{ exit !(x > 0) }' 2>/dev/null; then
    echo "ENABLE_PREVIEW 为真时须设置 WEBSOCKET_OUTPUT_FPS 为大于 0 的数（例如 WEBSOCKET_OUTPUT_FPS=10）" >&2
    exit 1
  fi
  ENABLE_PREVIEW_ARG="true"
else
  ENABLE_PREVIEW_ARG="false"
fi

exec ros2 launch "$DIR/launch/mipi_detect_websocket.launch.py" \
  mipi_camera_calibration_file_path:="${CAL}" \
  dnn_example_config_file:="${CFG}" \
  dnn_example_image_width:="${W}" \
  dnn_example_image_height:="${H}" \
  mipi_image_framerate:="${FPS}" \
  enable_preview:="${ENABLE_PREVIEW_ARG}" \
  codec_jpg_quality:="${QUAL}" \
  websocket_output_fps:="${WSFPS}" \
  image_throttle_hz:="${THROTTLE_HZ}" \
  image_throttle_out_topic:="${THROTTLE_OUT}" \
  "$@"
