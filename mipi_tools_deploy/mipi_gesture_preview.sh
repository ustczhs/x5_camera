#!/bin/bash
# 手势识别链路（mono2d 人体 + 手部关键点 + 手势 BPU），含网页 MJPEG :8000。
# 与 mipi_detect_preview.sh 互斥：同一 MIPI 勿并行；启动前请停 mipi-preview / mipi_detect 等。
set -eo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$DIR/env.sh"
# shellcheck source=/dev/null
source "$DIR/mipi_stop_conflicts.sh"
export CAM_TYPE="${CAM_TYPE:-mipi}"
exec ros2 launch "$DIR/launch/mipi_gesture_sc132gs.launch.py" "$@"
