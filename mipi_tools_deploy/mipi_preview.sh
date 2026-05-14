#!/bin/bash
# 浏览器实时预览：MIPI → /image_raw(NV12) → JPEG → WebSocket，nginx 端口 8000
set -eo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$DIR/env.sh"
# shellcheck source=/dev/null
source "$DIR/mipi_stop_conflicts.sh"
CAL="${MIPI_CALIB:-/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml}"
exec ros2 launch mipi_cam mipi_cam_websocket.launch.py \
  mipi_camera_calibration_file_path:="${CAL}" \
  "$@"
