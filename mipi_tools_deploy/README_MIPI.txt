RDK X5 MIPI 相机（当前识别为 SC132GS-1280p）使用说明
================================================

硬件与驱动
----------
- 板卡已带 tros-humble-mipi-cam；相机不走 /dev/video*，由 Hobot/VIN 栈采集。
- 环境脚本 /root/mipi_tools/env.sh 会先 source /etc/profile.d/environment.sh（含 /usr/hobot/lib 等库路径），再加载 TogetheROS；systemd/脚本与 SSH 登录行为一致。
- 若开机启用了官方 x5-tros-30fps.service（占 MIPI 与 :8000），直接跑 mipi_preview 会 creat_isp_node -10；请先 source mipi_stop_conflicts.sh（已并入 mipi_preview.sh 等）或手动 systemctl stop x5-tros-30fps.service。

标定与分辨率
------------
- 建议使用标定文件：/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml
- 默认预览分辨率 960x544@30（官方 mipi_cam_websocket.launch.py）。

实时预览（浏览器 MJPEG）
-------------------------
  /root/mipi_tools/mipi_preview.sh
  浏览器访问：http://<板子IP>:8000

  systemd（默认未启用开机自启）：
    systemctl start mipi-preview.service
    systemctl enable mipi-preview.service   # 可选

单帧抓图（JPG，BGR8 ROS 模式）
------------------------------
  /root/mipi_tools/mipi_snap.sh [输出路径.jpg]
  可选：WIDTH=1280 HEIGHT=720 /root/mipi_tools/mipi_snap.sh /tmp/hd.jpg

零拷贝高性能话题（算法对接）
----------------------------
  /root/mipi_tools/mipi_highperf.sh
  话题：/hbmem_img（NV12，hbmem）

注意：BGR8 抓图与 NV12 网页预览切换
------------------------------------
若先运行 mipi_snap（BGR8 /image_raw）再立即启动网页预览，可能出现 hobot_codec 的 infmt 报错。
请先结束相关节点并稍等数秒，或 reboot 后再启动预览。

其它系统服务
------------
板端可能还有 S90cam-service、sunrise-camera 等；若与 mipi 争用，请按需 systemctl stop 对应服务。

BPU 目标检测 + 网页（:8000，与 mipi_preview 互斥）
-------------------------------------------------
  依赖：apt 安装 tros-humble-dnn-node-example、hobot-models-basic 等，详见仓库 RDK_X5_MIPI相机部署与使用说明.md。
  /root/mipi_tools/mipi_detect_preview.sh
  systemd：mipi-detect-preview.service（默认未 enable）

手势识别 + 网页（与上互斥，勿并行开多路 mipi）
----------------------------------------------
  export CAM_TYPE=mipi
  /root/mipi_tools/mipi_gesture_preview.sh
  （使用 launch/mipi_gesture_sc132gs.launch.py，避免从家目录启动时 config/*.hbm 找不到）

官方文档：https://developer.d-robotics.cc/rdk_doc/RDK
