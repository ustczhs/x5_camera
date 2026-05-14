#!/bin/bash
# RDK X5：先加载板卡 environment（Hobot 库路径 + ROS Humble），再叠加 TogetheROS Humble
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-91}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
if [ -f /etc/profile.d/environment.sh ]; then
  # shellcheck disable=SC1091
  . /etc/profile.d/environment.sh
elif [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
fi
[ -f /opt/tros/humble/setup.bash ] && source /opt/tros/humble/setup.bash
