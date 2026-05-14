#!/bin/bash
# 抓取一帧为 JPG（ROS 模式，默认 640x480；可用环境变量 WIDTH/HEIGHT 调整）
set -eo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$DIR/env.sh"
# shellcheck source=/dev/null
source "$DIR/mipi_stop_conflicts.sh"
WIDTH="${WIDTH:-640}"
HEIGHT="${HEIGHT:-480}"
CAL="${MIPI_CALIB:-/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml}"
OUT="${1:-/root/mipi_captures/$(date +%Y%m%d_%H%M%S).jpg}"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d)"
cleanup() {
  kill "${MIPID:-}" 2>/dev/null || true
  rm -rf "${TMP}"
}
trap cleanup EXIT
cd "${TMP}"
ros2 launch mipi_cam mipi_cam.launch.py \
  mipi_io_method:=ros mipi_out_format:=bgr8 \
  "mipi_image_width:=${WIDTH}" "mipi_image_height:=${HEIGHT}" \
  "mipi_camera_calibration_file_path:=${CAL}" \
  log_level:=error >/tmp/mipi_snap_mipi.log 2>&1 &
MIPID=$!
sleep 5
timeout 5 ros2 run image_view image_saver --ros-args -r image:=/image_raw >/tmp/mipi_snap_saver.log 2>&1 || true
kill "${MIPID}" 2>/dev/null || true
wait "${MIPID}" 2>/dev/null || true
latest="$(ls -t "${TMP}"/*.jpg 2>/dev/null | head -1 || true)"
if [ -z "${latest}" ]; then
  echo "错误: 未生成图像。请查看 /tmp/mipi_snap_mipi.log /tmp/mipi_snap_saver.log" >&2
  exit 1
fi
cp -f "${latest}" "${OUT}"
echo "已保存: ${OUT}"
