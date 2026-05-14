# RDK X5 相机与媒体 — 待办与路线（上下文整理）

> **新建工程承接**：本仓库 `x5_camera2` 已在板端 `/root/mipi_tools/` 落地脚本与说明。主文档 [RDK_X5_MIPI相机部署与使用说明.md](RDK_X5_MIPI相机部署与使用说明.md)；部署包目录 [mipi_tools_deploy/](mipi_tools_deploy/)（`env.sh`、`mipi_stop_conflicts.sh`、`mipi_preview.sh`、`mipi_detect_preview.sh`、`mipi_gesture_preview.sh`、`mipi_highperf.sh`、`mipi_snap.sh`、`launch/*.launch.py`、systemd 单元）。新工程可 **git submodule / 复制 mipi_tools_deploy + 文档** 或 **ansible 同步板端** 继续迭代。

> 背景：地瓜 RDK X5 + MIPI（**SC132GS-1280p**），TogetheROS Humble；MIPI 预览 **:8000**；与官方 **`x5-tros-30fps.service`** 争用 VIN 时需先停冲突（脚本已内置）。

---

## 〇、本阶段已完成（便于新工程跳过重复劳动）

- [x] **MIPI 预览 / 抓图 / hbmem**：`mipi_preview.sh`、`mipi_snap.sh`、`mipi_highperf.sh`。
- [x] **BPU 目标检测 + 网页**：`mipi_detect_preview.sh` + `launch/mipi_detect_websocket.launch.py`（Composable：`mipi_cam` + `dnn_node_example` + JPEG + websocket）；依赖 `tros-humble-dnn-node-example`、`hobot-models-basic`。
- [x] **手势识别 + 网页**：`mipi_gesture_preview.sh` + `launch/mipi_gesture_sc132gs.launch.py` / `launch/mipi_hand_lmk_sc132gs.launch.py`（解决相对路径 `config/*.hbm` 与 `device:=F37` 问题；依赖 `hand_gesture_detection` 等包）。
- [x] **与官方 30fps / sunrise 冲突**：`mipi_stop_conflicts.sh`（停 `x5-tros-30fps`、`sunrise-camera`，`pkill` 残留，`restart S90cam-service`，`sleep`）；各 `mipi_*.sh` 已 `source`。
- [x] **systemd**：`mipi-detect-preview.service`、`mipi-preview.service`（仓库内模板）；说明文档含 **scp 同步**、**`creat_isp_node -10` / reboot**、**勿与 x5-tros 并行** 等排障。
- [ ] **单画面 OD + 手势合并**：未实现（文档已注明）；新工程若做需自研编排或厂商方案。

---

## 一、低功耗下的图像 / 视频获取

### 目标

在 **CPU 占用尽量低、内存与带宽可控** 的前提下，稳定获取静态图或连续视频流（机内或局域网）。

### 待办

- [ ] **默认走零拷贝链路**：业务采集优先使用 `shared_mem` + `/hbmem_img`（`mipi_highperf.sh`），避免常驻 **JPEG + WebSocket** 全链路。
- [ ] **按需降规格**：为 **检测 / 手势 / 预览** 各 launch **透传** `mipi_image_framerate`（如 15）、`codec_jpg_quality`、`websocket_output_fps`，在画质可接受范围内降 CPU（手势链当前多为官方默认 30fps）。
- [ ] **抓图与预览分离策略**：BGR8（`mipi_snap`）与 NV12 网页预览勿无间隔切换；文档已有「先停再起 / 重启」；新工程可加 **自检脚本**（`ros2 topic` / 进程探测）。
- [ ] **评估非 ROS 采集路径**（可选、中长期）：Hobot 非 rclcpp MIPI Sample/SDK，量化相对 `mipi_cam` 的 CPU 与开发成本。

---

## 二、WebRTC 视频通话

### 目标

在局域网或穿透场景下，实现 **浏览器 / 移动端 ↔ 板端** 的实时视频（及可选音频），与现有 MJPEG over WebSocket 区分。

### 待办

- [ ] **明确需求**：单向 vs 双向、分辨率/帧率上限、TURN、目标浏览器。
- [ ] **技术选型**：GStreamer webrtcbin、Pion/livekit、或厂商 WebRTC；输入从 **NV12 硬件编码** 或 **hbmem** 衔接。
- [ ] **与现有 ROS 的关系**：独立进程 vs ROS2 桥接，**避免重复开相机**。
- [ ] **原型验证**：640×480@15fps 延迟与 CPU，与 MJPEG `:8000` 对比。
- [ ] **安全与运维**：HTTPS/WSS、鉴权、防火墙、开机自启。

---

## 三、`cam-service` / 官方相机栈 与资源优化

### 已知现象

运行 **`mipi_detect_preview`** 或 **`mipi_gesture_preview`** 时，`top` 中 **`cam-service` 仍占约 15%～35% CPU**（与 TogetheROS 并行、非推理本体）；手势链另有多进程 + 三路 BPU 模型，总负载高于检测 Composable 单进程。

### 待办

- [ ] **梳理依赖**：镜像中 `S90cam-service.service` / `cam-service` 被哪些功能依赖。
- [ ] **对比实验**：停 `cam-service` 前后，对 **检测 / 手势 / mipi_highperf** 测 CPU、帧率、VIN 是否报错；记录 **回滚** `systemctl start`。
- [ ] **与 `sunrise-camera` / `x5-tros-30fps` 协同**：业务只用 `mipi_tools` 时是否 **disable** 官方 30fps 自启（需评估是否还要官方演示）。
- [ ] **决策与文档**：生产环境「保留 / 禁用」systemd 列表写入说明文档「运维」小节。
- [ ] **可选 systemd**：`Conflicts=` 防止 cam-service 与自研 MIPI 同时占设备（需厂商确认）。

---

## 四、横切项（文档与工程化）

- [x] 与 `RDK_X5_MIPI相机部署与使用说明.md` 交叉引用（BPU 检测、手势、冲突停止、scp、排障「二、6–9」等）。
- [x] 板端 `/root/mipi_tools/` 与仓库同步策略（说明文档「二、8」scp 示例）。
- [ ] **新工程建议**：独立 git 仓库时，将 **`mipi_tools_deploy/` + `RDK_X5_MIPI相机部署与使用说明.md`** 作为唯一板端交付物版本化；板子 IP/账号不进库。

---

## 五、建议优先级（简表，供新工程排序）

| 优先级 | 项 |
|--------|-----|
| P0 | **停 `cam-service` 对比压测** + 文档化生产推荐服务列表 |
| P1 | **手势/检测 launch 透传**：`mipi_image_framerate`、`websocket_output_fps`、`codec_jpg_quality` 降 CPU |
| P2 | WebRTC 需求澄清 + GStreamer/厂商 demo 验证 |
| P3 | 非 ROS 采集路径调研；单画面 **OD+手势** 合并（若产品需要） |

---

*执行板级 `systemctl disable`、内核模块类操作前请备份并做好回滚。*
