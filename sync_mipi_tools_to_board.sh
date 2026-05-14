#!/usr/bin/env bash
# 将本仓库 mipi_tools_deploy/ 同步到开发板 /root/mipi_tools/（与 RDK_X5_MIPI相机部署与使用说明.md 一致）。
# 依赖：本机已安装 rsync、ssh；板端目标目录可写（一般为 root）。
#
# 用法：
#   ./sync_mipi_tools_to_board.sh
#   ./sync_mipi_tools_to_board.sh root@192.168.1.50
#   MIPI_SYNC_TARGET=sunrise@x5 ./sync_mipi_tools_to_board.sh   # 若目录在 sunrise 家目录请改 REMOTE_ROOT
#   ./sync_mipi_tools_to_board.sh --dry-run root@x5
#
# 环境变量：
#   MIPI_SYNC_TARGET   默认 root@x5（与 ssh config 里 Host x5 对应）
#   MIPI_REMOTE_DIR    默认 /root/mipi_tools
#   MIPI_SKIP_DAEMON_RELOAD  设为 1 则不同步后执行 systemctl daemon-reload

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${SCRIPT_DIR}/mipi_tools_deploy"
REMOTE_ROOT="${MIPI_REMOTE_DIR:-/root/mipi_tools}"

DRY_RUN=()
POS_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n | --dry-run)
      DRY_RUN=(--dry-run)
      shift
      ;;
    -h | --help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
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

if [[ ! -d "$SRC" ]]; then
  echo "错误: 找不到部署目录: $SRC" >&2
  exit 1
fi

echo "[sync] 源: $SRC"
echo "[sync] 目标: ${REMOTE}:${REMOTE_ROOT}/"

if [[ ${#DRY_RUN[@]} -eq 0 ]]; then
  ssh "$REMOTE" "mkdir -p \"${REMOTE_ROOT}\""
fi

rsync -avz "${DRY_RUN[@]}" -e ssh \
  "$SRC/" "${REMOTE}:${REMOTE_ROOT}/"

if [[ ${#DRY_RUN[@]} -gt 0 ]]; then
  echo "[sync] dry-run 结束，未写远端。"
  exit 0
fi

if [[ "${MIPI_SKIP_DAEMON_RELOAD:-0}" != "1" ]]; then
  echo "[sync] 远端: systemctl daemon-reload（更新 *.service 单元后需要）"
  ssh "$REMOTE" "systemctl daemon-reload"
fi

echo "[sync] 完成。若首次部署 systemd 单元，可在板上执行:"
echo "       sudo cp ${REMOTE_ROOT}/mipi-preview.service ${REMOTE_ROOT}/mipi-detect-preview.service /etc/systemd/system/"
echo "       sudo systemctl daemon-reload"
