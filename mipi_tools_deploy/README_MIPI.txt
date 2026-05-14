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

BPU 目标检测 + 可选网页（:8000，与 mipi_preview 互斥）
----------------------------------------------------
  依赖：apt 安装 tros-humble-dnn-node-example、hobot-models-basic 等，详见仓库 RDK_X5_MIPI相机部署与使用说明.md。
  /root/mipi_tools/mipi_detect_preview.sh
  默认：YOLO26 nano（config/yolo26workconfig.json）、640×640、15fps、**不**开 MJPEG/WebSocket（省 CPU）。
  开浏览器预览：ENABLE_PREVIEW=true 且必须 WEBSOCKET_OUTPUT_FPS>0，例如：
    ENABLE_PREVIEW=true WEBSOCKET_OUTPUT_FPS=10 /root/mipi_tools/mipi_detect_preview.sh
  可选环境变量：DNN_DETECT_CONFIG、DNN_IMAGE_WIDTH/HEIGHT、MIPI_FRAMERATE、IMAGE_THROTTLE_HZ（默认 15，设 0 关闭 topic_tools 限帧）、IMAGE_THROTTLE_OUT_TOPIC、CODEC_JPG_QUALITY
  部署时请同步 `mipi_tools/config/yolo26workconfig.json`（见仓库 mipi_tools_deploy/config/）。
  systemd：mipi-detect-preview.service（默认未 enable；unit 内已设 ENABLE_PREVIEW=true 与 WEBSOCKET_OUTPUT_FPS=15，保持「检测 + :8000」）

排查：/image_raw 约 60Hz 但 launch 里 mipi 已设 15fps
------------------------------------------
  板端实测 `ros2 topic hz /image_raw` 常为 ~60，而 `perc_node` 里 `Sub img fps` 同步约 60，说明当前 **mipi_cam 的 framerate 参数未必限制 ROS 图像发布频率**（与 TROS 版本/传感器模式有关）。
  本仓库 `mipi_detect_websocket.launch.py` 已默认在 **同一 component 容器** 内加载 **`topic_tools::ThrottleNode`**（`image_throttle_hz` 默认 **15.0**），将 **dnn** 订阅改为 **`/image_raw_to_dnn`**（可改 `image_throttle_out_topic`），从而在 `/image_raw` 仍为高帧时把 **推理输入** 压到设定 Hz。依赖：`sudo apt install ros-humble-topic-tools`（并保证 `source` 后能找到该包）。
  关闭限帧（恢复 dnn 直接订 `/image_raw`）：`image_throttle_hz:=0`。
  本 launch 已默认：`mipi_gdc_enable:=false`、`mipi_sub_stream_enable:=false`，且 `sub_image_*` 与主路同分辨率。
  若需几何校正再开：`ros2 launch ... mipi_gdc_enable:=true mipi_gdc_bin_file:=<板端 sc132gs gdc bin 路径>`。

手势识别 + 网页（与上互斥，勿并行开多路 mipi）
----------------------------------------------
  export CAM_TYPE=mipi
  /root/mipi_tools/mipi_gesture_preview.sh
  （使用 launch/mipi_gesture_sc132gs.launch.py，避免从家目录启动时 config/*.hbm 找不到）

官方文档：https://developer.d-robotics.cc/rdk_doc/RDK
