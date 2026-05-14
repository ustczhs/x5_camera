#!/bin/bash
# 停止与 TogetheROS MIPI 预览/检测争用 VIN/ISP 的官方常驻服务及残留节点。
# 典型冲突：x5-tros-30fps.service（官方 30fps 预览，占 MIPI 与 :8000）、sunrise-camera.service。
# 由 mipi_preview.sh / mipi_detect_preview.sh / mipi_highperf.sh / mipi_snap.sh 等在启动前调用。
# 注意：本文件可能被 source，勿使用 set -e，以免中断调用方脚本。
# 「独占停 cam-service」仅放在 mipi_highperf.sh 内，避免环境变量 MIPI_CAM_EXCLUSIVE 误伤其它脚本。

echo "[mipi_tools] 停止与 MIPI 争用的服务/残留节点（x5-tros-30fps、sunrise-camera 等）…" >&2

stop_svc() {
  local u="$1"
  if systemctl is-active --quiet "$u" 2>/dev/null; then
    systemctl stop "$u" || true
  fi
}

stop_svc x5-tros-30fps.service
stop_svc sunrise-camera.service
stop_svc x5-sunrise-camera.service 2>/dev/null || true
stop_svc mipi-preview.service 2>/dev/null || true
stop_svc mipi-detect-preview.service 2>/dev/null || true

# 与官方 x5-tros ExecStopPost 一致，清理残留进程名
pkill -x mipi_cam 2>/dev/null || true
pkill -x hobot_codec 2>/dev/null || true
pkill -x hobot_codec_republish 2>/dev/null || true
pkill -x websocket 2>/dev/null || true

# 与官方 x5-tros-30fps 的 ExecStartPre 类似：重启 cam 服务有助于释放 ISP/VIN，避免紧接着出现 creat_isp_node ret -10。
# mipi_highperf.sh 会设 MIPI_SKIP_CAM_SERVICE_RESTART=1：避免「刚 restart 占住 ISP → 再 stop」导致 creat_isp_node ret -10。
if [ "${MIPI_SKIP_CAM_SERVICE_RESTART:-0}" != "1" ]; then
  systemctl restart S90cam-service.service 2>/dev/null || true
  sleep 4
else
  echo "[mipi_tools] 跳过 S90cam-service restart（MIPI_SKIP_CAM_SERVICE_RESTART=1）…" >&2
  sleep 2
fi
