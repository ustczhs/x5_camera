#!/bin/bash
# 高性能零拷贝：发布 /hbmem_img（NV12），适合自研节点或算法流水线对接
set -eo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 与 mipi_preview / mipi_detect 共用 mipi_stop_conflicts（含 restart S90cam-service）。
# 板端实测：先 skip restart 再 stop cam-service 后起 shared_mem，易出现 creat_isp_node ret -10；
# 保持 cam-service 与 mipi_cam 并行（默认）时 shared_mem 可正常 Enabling zero-copy。
# shellcheck source=/dev/null
source "$DIR/env.sh"
# shellcheck source=/dev/null
source "$DIR/mipi_stop_conflicts.sh"

# 仅当显式 MIPI_CAM_EXCLUSIVE=1：停官方相机栈（部分场景需独占；在 X5 上可能再次 ret -10，需自测）。
_SETTLE="${MIPI_ISP_SETTLE_SEC:-8}"
if [ "${MIPI_CAM_EXCLUSIVE:-0}" = "1" ]; then
  for u in S90cam-service.service cam-service.service; do
    systemctl stop "$u" 2>/dev/null || true
  done
  sleep 2
  pkill -x cam-service 2>/dev/null || true
  if [ "${MIPI_STOP_ROBOEYES:-1}" = "1" ]; then
    pkill -x x5_roboeyes_gpu 2>/dev/null || true
  fi
  sleep "${_SETTLE}"
fi

CAL="${MIPI_CALIB:-/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml}"
# 对比排障： MIPI_HIGHPERF_IO_METHOD=ros（走 /image_raw，非 hbmem）
IO="${MIPI_HIGHPERF_IO_METHOD:-shared_mem}"
exec ros2 launch mipi_cam mipi_cam.launch.py \
  mipi_io_method:="${IO}" \
  mipi_out_format:=nv12 \
  mipi_image_width:=960 mipi_image_height:=544 \
  "mipi_camera_calibration_file_path:=${CAL}" \
  "$@"
