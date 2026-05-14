# RDK X5 MIPI 相机部署与使用说明

本文档说明在 **地瓜 RDK X5**（Ubuntu 22.04 / ARM64）上完成的 MIPI 相机相关工作、如何抓取图片与视频流，以及 **CPU 资源优化**方向。

---

## 一、已完成的工作概要

### 1. 环境与软件

- 板卡已预装 **TogetheROS Humble** 与 **`tros-humble-mipi-cam`**（MIPI 驱动与 ROS 2 节点）；MIPI 采集**不经过** `/dev/video*`，属正常现象。
- 额外安装 **`ros-humble-image-view`**，用于通过 `image_saver` 保存 JPG 单帧。
- 实际识别到的传感器为 **SC132GS-1280p**；标定文件建议使用包内：
  - `/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml`

### 2. 系统配置调整

- **`/etc/profile`**：将原先无条件 `source` 不存在的 `~/driver_ws`、`~/slam_ws`、`~/pp_ws` 改为「文件存在才 source」，避免每次登录报错。
- **板端脚本目录**：`/root/mipi_tools/`
  - **`env.sh`**：先 `source /etc/profile.d/environment.sh`（包含 `/usr/hobot/lib` 等 Hobot 库路径与 ROS Humble），再 `source /opt/tros/humble/setup.bash`。这样 **SSH 脚本 / systemd** 与「登录 shell」行为一致，避免 `mipi_cam` 初始化失败。
  - **`mipi_stop_conflicts.sh`**：在启动预览/检测/抓图前 **停止与 MIPI 争用的官方常驻服务**（典型为 **`x5-tros-30fps.service`**、**`sunrise-camera.service`**）并清理残留的 `mipi_cam` / `hobot_codec` / `websocket` 进程；随后 **`systemctl restart S90cam-service.service`** 并 **等待数秒**，便于 ISP/VIN 释放（与官方 `x5-tros-30fps` 的 `ExecStartPre` 思路一致）。由 `mipi_preview.sh` 等脚本自动 `source`，避免 **`creat_isp_node ... ret -10`**。
  - **`mipi_preview.sh`**：启动官方 `mipi_cam_websocket` 链路（NV12 → JPEG → WebSocket，nginx **8000** 端口）。
  - **`mipi_snap.sh`**：短时 ROS 模式 BGR8 + `image_saver` 保存 **单张 JPG**。
  - **`mipi_highperf.sh`**：默认 **shared_mem + NV12**，发布 **`/hbmem_img`**（零拷贝，适合算法对接）。
  - **`mipi_detect_preview.sh`**：**MIPI + BPU 目标检测**（`dnn_node_example`，默认 **YOLO26 nano**）+ **可选** JPEG + WebSocket；默认关闭浏览器预览以省 CPU，开启时需设置帧率（见 README_MIPI）。
  - **`mipi_gesture_preview.sh`**：**手势识别**（`mono2d_body_detection` + `hand_lmk_detection` + `hand_gesture_detection` + MIPI + 网页）。脚本使用 **`launch/mipi_gesture_sc132gs.launch.py`**（替代官方 `hand_gesture_detection.launch.py`），为 SC132GS 固定 **模型绝对路径** 与 **`device:=default`**；与检测/纯预览 **同一 MIPI 互斥**。
  - **`launch/mipi_detect_websocket.launch.py`**：上述检测链路的 launch（标定、分辨率/帧率、`enable_preview`、JPEG 质量、Web 输出帧率可参数化）。
  - **`README_MIPI.txt`**：板上的简要说明（与本文互补）。
- **systemd**：`/etc/systemd/system/mipi-preview.service`  
  - 设置了 `ROS_DOMAIN_ID=91`、`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` 等，与板端常见配置一致。  
  - **默认未 `enable`**，需时手动 `systemctl start`。
- **systemd（检测）**：`/etc/systemd/system/mipi-detect-preview.service`（由仓库 `mipi_tools_deploy/mipi-detect-preview.service` 拷贝），**默认未 enable**；unit 内通过环境变量开启 **检测 + :8000** 预览（`ENABLE_PREVIEW=true`、`WEBSOCKET_OUTPUT_FPS=15`）。

### 3. 行为与排障要点

- **官方 TROS 30fps 预览与 MIPI 互斥**：镜像若启用 **`x5-tros-30fps.service`**（`/opt/x5_tros_30fps/`，默认 **占 MIPI + 端口 8000**），再运行 `/root/mipi_tools/mipi_preview.sh` 会 **第二路抢 VIN/ISP**，表现为 **`creat_isp_node ... failed, ret -10`**、`hobot_codec` 收不到 `/image_raw`。脚本已自动 **`source mipi_stop_conflicts.sh`** 先停该服务；若你仍需官方 30fps 常驻，可在不用 `mipi_tools` 时执行 `systemctl start x5-tros-30fps.service` 恢复。
- **BGR8 抓图**（`mipi_snap`）与 **NV12 网页预览**（`mipi_cam_websocket`）切换时，若紧挨着启动，可能出现 `hobot_codec` 的 **infmt** 告警；可先结束相关节点、等待数秒，或 **重启** 后再开预览。
- 板上可能还有 **`S90cam-service`、`sunrise-camera`** 等；若与 MIPI 争用，可按需 `systemctl stop` 对应服务（`mipi_stop_conflicts.sh` 会尝试停止常见单元）。

---

## 二、如何启动：图片与视频

以下命令均在 **开发板本机**执行（或通过 SSH 登录后执行）。请先确保相机排线、供电正常。

### 1. 环境（手动跑命令时）

```bash
source /root/mipi_tools/env.sh
```

或分步等价于：`source /etc/profile.d/environment.sh` 后再 `source /opt/tros/humble/setup.bash`（与 `env.sh` 一致即可）。

### 2. 实时视频（浏览器 MJPEG）

**方式 A：脚本（推荐）**

```bash
/root/mipi_tools/mipi_preview.sh
```

**方式 B：systemd**

```bash
systemctl start mipi-preview.service
# 开机自启（可选）
# systemctl enable mipi-preview.service
```

在电脑浏览器访问：

```text
http://<开发板IP>:8000
```

默认分辨率一般为 **960×544@30fps**（由官方 `mipi_cam_websocket.launch.py` 决定，可通过 launch 参数覆盖，见下文「优化」）。

停止预览：

```bash
# 若用脚本启动：终端里 Ctrl+C
# 若用 systemd：
systemctl stop mipi-preview.service
```

### 3. 单张图片（JPG）

```bash
/root/mipi_tools/mipi_snap.sh [输出路径.jpg]
```

未指定路径时，会保存到 `/root/mipi_captures/` 下带时间戳的文件名。

指定分辨率示例（环境变量）：

```bash
WIDTH=1280 HEIGHT=720 /root/mipi_tools/mipi_snap.sh /tmp/snap.jpg
```

### 4. 高性能零拷贝图像话题（给算法用，非网页）

```bash
/root/mipi_tools/mipi_highperf.sh
```

话题 **`/hbmem_img`**（NV12，hbmem）。需自研节点或官方示例订阅，不是浏览器直接打开。

### 5. 仅用 ROS 2 命令行（对照参考）

在已 `source` 好环境的前提下，也可直接使用包内 launch，例如默认采集（零拷贝示例）：

```bash
ros2 launch mipi_cam mipi_cam.launch.py \
  mipi_camera_calibration_file_path:=/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml
```

网页预览完整链路：

```bash
ros2 launch mipi_cam mipi_cam_websocket.launch.py \
  mipi_camera_calibration_file_path:=/opt/tros/humble/lib/mipi_cam/config/sc132gs_calibration.yaml
```

更多分辨率可查看 `/opt/tros/humble/share/mipi_cam/launch/` 下其它 `mipi_cam_*.launch.py`。

### 6. BPU 目标检测 + 可选网页（YOLO 等）

**依赖（板端 apt，示例）：**

```bash
sudo apt-get update
sudo apt-get install -y tros-humble-dnn-node tros-humble-dnn-node-example hobot-models-basic ros-humble-topic-tools
```

`hobot-models-basic` 提供 `/opt/hobot/model/x5/basic/` 下与 `config/yolo26workconfig.json`、`config/yolov5workconfig.json` 等匹配的 **`.bin` 模型**；若日志报模型文件不存在，请先安装该包。仓库提供 `mipi_tools_deploy/config/yolo26workconfig.json`，请同步到板端 `/root/mipi_tools/config/`。

**启动（脚本）：**

```bash
source /root/mipi_tools/env.sh
/root/mipi_tools/mipi_detect_preview.sh
```

默认 **不** 启动 MJPEG/WebSocket（仅 MIPI + 检测）。需要浏览器 `:8000` 时：

```bash
ENABLE_PREVIEW=true WEBSOCKET_OUTPUT_FPS=10 /root/mipi_tools/mipi_detect_preview.sh
```

可选环境变量（默认值见脚本）：

- **`MIPI_CALIB`**：标定 yaml（默认 `sc132gs_calibration.yaml`）。
- **`DNN_DETECT_CONFIG`**：工作目录下相对 `config/` 的 json，默认 `config/yolo26workconfig.json`；亦可 `config/yolov5workconfig.json` 等。
- **`DNN_IMAGE_WIDTH` / `DNN_IMAGE_HEIGHT`**：MIPI 输出分辨率（默认 `640`）。
- **`MIPI_FRAMERATE`**：采集帧率（默认 `15.0`）。
- **`ENABLE_PREVIEW`**：`true`/`1`/`yes`/`on` 时启用 JPEG + WebSocket。
- **`WEBSOCKET_OUTPUT_FPS`**：在 `ENABLE_PREVIEW=true` 时**必须**大于 0；关闭预览时可省略。
- **`CODEC_JPG_QUALITY`**：MJPEG 质量（默认 `80.0`，仅开启预览时有效）。

浏览器访问 `http://<开发板IP>:8000`（仅开启预览时）。停止：终端 **Ctrl+C**，或 `systemctl stop mipi-detect-preview.service`。

**说明：** 本链路基于官方 **component 容器**（`mipi_cam` NV12 + `dnn_node_example`；可选 `hobot_codec` + `websocket`），并补全 **SC132GS 标定**、**分辨率/帧率**、**enable_preview**、**JPEG 质量**、**websocket_output_fps**。

### 7. 手势识别 + 网页（官方包）

与 **6**、**2** 共用同一 MIPI 时 **只能择一运行**。启动前请停掉其它 `mipi_cam` / `websocket` / `mipi-preview` / `mipi_detect` 相关进程。

```bash
source /root/mipi_tools/env.sh
export CAM_TYPE=mipi
/root/mipi_tools/mipi_gesture_preview.sh
```

依赖：`tros-humble-hand-gesture-detection`、`tros-humble-hand-lmk-detection`、`tros-humble-mono2d-body-detection`（一般随手势包安装）。**请勿**直接用官方 `ros2 launch hand_gesture_detection ...` 从 **`~`（家目录）** 启动：节点默认加载相对路径 **`config/*.hbm`**，工作目录不对时会报 **`Model file config/...hbm is not exist`**。本仓库使用 **`mipi_hand_lmk_sc132gs.launch.py`**，将 mono2d / hand_lmk 模型指向 **`/opt/tros/humble/lib/.../config/*.hbm`**，并将 mono2d 默认 **`device:=F37`** 改为 **`default`**（适配 SC132GS）。

可选参数（传给 `mipi_gesture_sc132gs.launch.py`）：`is_dynamic_gesture:=true` 等，参见官方手势文档。

日志中 **`Frame find ai ts ... fail`** 多为图像与 AI 结果时间戳对齐告警，有推理 fps 时通常可忽略；**`get camera calibration parameters failed`** 因官方 `mono2d_body_detection` 未传入 SC132GS 标定 yaml，一般不影响跑通（若需精确叠框可再扩展 launch）。

**单画面同时叠「目标框 + 手势」**：需自研编排或厂商后续示例，当前仓库 **未实现**（两条链路各自推理与渲染）。

### 8. 仓库与板端同步

将本仓库 [`mipi_tools_deploy/`](mipi_tools_deploy/) 中的 `env.sh`、`*.sh`、`launch/*.launch.py`、`mipi-detect-preview.service` 同步到板子 **`/root/mipi_tools/`**（及 `systemctl daemon-reload`），例如在本机执行：

```bash
scp mipi_tools_deploy/{env.sh,mipi_*.sh,mipi-detect-preview.service} root@<IP>:/root/mipi_tools/
scp mipi_tools_deploy/config/yolo26workconfig.json root@<IP>:/root/mipi_tools/config/
scp mipi_tools_deploy/launch/mipi_detect_websocket.launch.py \
  mipi_tools_deploy/launch/mipi_gesture_sc132gs.launch.py \
  mipi_tools_deploy/launch/mipi_hand_lmk_sc132gs.launch.py \
  root@<IP>:/root/mipi_tools/launch/
```

推荐一键同步（含 `config/`、全部 `launch/`、`*.service`，并远端 `daemon-reload`）：在仓库根目录执行 `./sync_mipi_tools_to_board.sh root@<IP>`；若需同时更新 `eye_track` 包，再加 `MIPI_SYNC_ROS_WS=/root/ros2_ws ./sync_mipi_tools_to_board.sh root@<IP>`，详见脚本内 `--help`。

### 9. 排障补充（BPU / MIPI）

- 若出现 **`creat_isp_node ... failed, ret -10`** 且随后进程崩溃：多为 **ISP/相机被异常占用或上次崩溃未释放**。先 `pkill` 相关 ROS 节点，无效则 **`reboot`** 后再启动脚本。
- **`parameter framerate ... integer/double`**：`mipi_cam` 的帧率参数类型为 **浮点**，launch 中请使用 **`15.0`** / **`30.0`** 等形式（本仓库 `mipi_detect_websocket.launch.py` 默认 **`15.0`**）。

---

## 三、CPU 优化改进方向

当前典型负载来自：**`mipi_cam` + BPU 检测**；若启用 **`hobot_codec`（JPEG）+ `websocket`**，CPU 会再上一档。若 **`cam-service`** 仍在运行，也会占一部分 CPU。可按优先级尝试：

### 1. 关闭不重叠的相机服务（收益通常最大）

若业务上不需要 **`cam-service`** / **`sunrise-camera`** 等官方常驻相机服务，而只用 TogetheROS MIPI 预览，可 **停止对应 systemd 单元** 后再观察 `top`。  
**注意**：停掉后，依赖这些服务的功能会不可用，需自行确认。

### 2. 降低分辨率与帧率

在启动 `mipi_cam_websocket`（或 `mipi_preview.sh` 若你改为包装自定义 launch）时减小：

- `mipi_image_width` / `mipi_image_height`
- `mipi_image_framerate`（如改为 15 或 10）

编码与传输开销大致随 **像素数 × 帧率** 下降。

### 3. 降低 JPEG 质量、限制 Web 输出帧率

- 调低 `hobot_codec_encode` 的 **`codec_jpg_quality`**（例如从 85 降到 60～70），减轻编码 CPU、减小 MJPEG 码率。  
- 若 websocket launch 支持 **`websocket_output_fps`** 等参数，可限制浏览器端显示帧率，减轻 `websocket` 与带宽。

具体参数名以你安装的 **`/opt/tros/humble/share/hobot_codec/launch/`**、**`websocket/launch/`** 中声明为准。

### 4. 不需要网页时：避免 JPEG + WebSocket 全链路

若仅需机内算法：**使用 `shared_mem` + `/hbmem_img`**（如 `mipi_highperf.sh`），不走 JPEG 与 WebSocket，CPU 通常明显更低。

若必须远程观看：可查官方文档是否提供 **RTSP / 硬件编码** 等更轻路径，替代「ROS 图像 + 软件 JPEG + WS」。

### 5. 避免重复启动与混合格式切换

- 不要同时跑多套 `mipi_cam` / 多套 websocket。  
- BGR8 抓图与 NV12 预览切换时，尽量 **先停干净再启**，或 **重启** 后再开预览，减少 `hobot_codec` 格式不匹配带来的无效计算。

---

## 四、官方文档

- [RDK 文档](https://developer.d-robotics.cc/rdk_doc/RDK)

---

*文档对应板端工具路径：`/root/mipi_tools/`。若你迁移了脚本位置，请同步修改本文中的路径。*


# 只同步 mipi_tools（含 config、launch、service）
./sync_mipi_tools_to_board.sh root@172.16.40.159

# 同时同步 eye_track 到板端工作区（改完 launch/README 时用）
MIPI_SYNC_ROS_WS=/root/ros2_ws ./sync_mipi_tools_to_board.sh root@172.16.40.159