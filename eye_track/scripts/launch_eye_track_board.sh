#!/bin/bash
# 板端一键：环境 + 停 MIPI 冲突 + 启动「检测 + 眼随人动」。
# 用法：ROS2_WS=/root/ros2_ws /path/to/launch_eye_track_board.sh
set -eo pipefail
MIPI_TOOLS="${MIPI_TOOLS:-/root/mipi_tools}"
ROS2_WS="${ROS2_WS:-/root/ros2_ws}"
if [ ! -f "${MIPI_TOOLS}/env.sh" ]; then
  echo "缺少 ${MIPI_TOOLS}/env.sh" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "${MIPI_TOOLS}/env.sh"
# mipi_stop_conflicts 已由 eye_track.launch.py 内 OpaqueFunction 执行，此处不再重复 source，避免双重重启 cam。
if [ ! -f "${ROS2_WS}/install/setup.bash" ]; then
  echo "请先 colcon build eye_track，缺少 ${ROS2_WS}/install/setup.bash" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "${ROS2_WS}/install/setup.bash"
exec ros2 launch eye_track eye_track.launch.py "$@"
