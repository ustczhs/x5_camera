#!/usr/bin/env bash
# 将本仓库部署到开发板：
#   1) mipi_tools_deploy/  -> 远端 MIPI_REMOTE_DIR（默认 /root/mipi_tools/）
#   2) 可选：eye_track/    -> 远端 ROS2 工作区 src/eye_track（见 MIPI_SYNC_ROS_WS）
#
# 依赖：本机 rsync、ssh；远端目录可写。
#
# 用法：
#   ./sync_mipi_tools_to_board.sh
#   ./sync_mipi_tools_to_board.sh root@172.16.40.159
#   MIPI_SYNC_TARGET=sunrise@x5 MIPI_REMOTE_DIR=/home/sunrise/mipi_tools ./sync_mipi_tools_to_board.sh
#   MIPI_SYNC_ROS_WS=/root/ros2_ws ./sync_mipi_tools_to_board.sh root@172.16.40.159   # 同时同步 eye_track 包
#   ./sync_mipi_tools_to_board.sh --dry-run root@x5
#
# 环境变量：
#   MIPI_SYNC_TARGET         默认 root@x5（可与 ssh config Host 对应）
#   MIPI_REMOTE_DIR          默认 /root/mipi_tools
#   MIPI_SYNC_ROS_WS         若设置（如 /root/ros2_ws），则额外 rsync eye_track/ 到 $MIPI_SYNC_ROS_WS/src/eye_track/
#   MIPI_EYE_TRACK_SRC       默认本仓库 ./eye_track
#   MIPI_SKIP_DAEMON_RELOAD  设为 1 则不同步后执行 systemctl daemon-reload
#   MIPI_RSYNC_DELETE        设为 1 时 eye_track 同步加 --delete（会删远端多余文件，慎用）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${SCRIPT_DIR}/mipi_tools_deploy"
EYE_TRACK_SRC="${MIPI_EYE_TRACK_SRC:-${SCRIPT_DIR}/eye_track}"
REMOTE_ROOT="${MIPI_REMOTE_DIR:-/root/mipi_tools}"

DRY_RUN=()
RSYNC_EXCLUDES=(
  --exclude='__pycache__/'
  --exclude='*.pyc'
  --exclude='.DS_Store'
  --exclude='*.swp'
)

POS_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n | --dry-run)
      DRY_RUN=(--dry-run)
      shift
      ;;
    -h | --help)
      awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
      exit 0
      ;;
    -*)
      echo "未知选项: $1" >&2
      exit 1
      ;;
    *)
      POS_ARGS+=("$1")
      shift
      ;;
  esac
done

REMOTE="${POS_ARGS[0]:-${MIPI_SYNC_TARGET:-root@x5}}"
ROS_WS="${MIPI_SYNC_ROS_WS:-}"
EYE_DELETE=()
if [[ "${MIPI_RSYNC_DELETE:-0}" == "1" ]]; then
  EYE_DELETE=(--delete)
fi

if [[ ! -d "$SRC" ]]; then
  echo "错误: 找不到部署目录: $SRC" >&2
  exit 1
fi

echo "[sync] 源(mipi_tools): $SRC"
echo "[sync] 目标: ${REMOTE}:${REMOTE_ROOT}/"

if [[ ${#DRY_RUN[@]} -eq 0 ]]; then
  ssh "$REMOTE" "mkdir -p \"${REMOTE_ROOT}\""
fi

rsync -avz "${DRY_RUN[@]}" -e ssh "${RSYNC_EXCLUDES[@]}" \
  "$SRC/" "${REMOTE}:${REMOTE_ROOT}/"

if [[ -n "$ROS_WS" ]]; then
  if [[ ! -d "$EYE_TRACK_SRC" ]]; then
    echo "错误: MIPI_SYNC_ROS_WS 已设置但找不到 eye_track 目录: $EYE_TRACK_SRC" >&2
    exit 1
  fi
  EYE_DEST="${ROS_WS}/src/eye_track"
  echo "[sync] 源(eye_track):  $EYE_TRACK_SRC/"
  echo "[sync] 目标:         ${REMOTE}:${EYE_DEST}/"
  if [[ ${#DRY_RUN[@]} -eq 0 ]]; then
    ssh "$REMOTE" "mkdir -p \"${EYE_DEST}\""
  fi
  rsync -avz "${DRY_RUN[@]}" -e ssh "${RSYNC_EXCLUDES[@]}" "${EYE_DELETE[@]}" \
    "$EYE_TRACK_SRC/" "${REMOTE}:${EYE_DEST}/"
fi

if [[ ${#DRY_RUN[@]} -gt 0 ]]; then
  echo "[sync] dry-run 结束，未写远端。"
  exit 0
fi

if [[ "${MIPI_SKIP_DAEMON_RELOAD:-0}" != "1" ]]; then
  echo "[sync] 远端: systemctl daemon-reload（更新 *.service 单元后需要）"
  ssh "$REMOTE" "systemctl daemon-reload"
fi

echo "[sync] mipi_tools 已同步到 ${REMOTE}:${REMOTE_ROOT}/"
if [[ -n "$ROS_WS" ]]; then
  echo "[sync] eye_track 已同步到 ${REMOTE}:${ROS_WS}/src/eye_track/"
  echo "[sync] 板上请编译 eye_track（示例）："
  echo "       ssh $REMOTE 'source /opt/tros/humble/setup.bash && cd ${ROS_WS} && colcon build --packages-select eye_track --symlink-install'"
  echo "[sync] systemd 单元在安装后路径：${ROS_WS}/install/eye_track/share/eye_track/scripts/eye-track.service（见 eye_track/README.txt）"
fi
echo "[sync] 若首次部署 systemd 单元，可在板上执行:"
echo "       sudo cp ${REMOTE_ROOT}/mipi-preview.service ${REMOTE_ROOT}/mipi-detect-preview.service /etc/systemd/system/"
echo "       sudo systemctl daemon-reload"
