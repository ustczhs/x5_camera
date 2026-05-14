#!/usr/bin/env python3
"""Subscribe ai_msgs/PerceptionTargets (e.g. /hobot_dnn_detection), drive x5_roboeyes TCP `look px py`."""

from __future__ import annotations

import math
import socket
import threading
import time
from typing import Optional, Tuple

import rclpy
from ai_msgs.msg import PerceptionTargets
from rclpy.node import Node


def _largest_roi(msg: PerceptionTargets, min_conf: float) -> Optional[Tuple[float, float, float, float]]:
    """Return (cx, cy, width, height) in pixels of highest-area roi, or None."""
    best_area = 0.0
    best: Optional[Tuple[float, float, float, float]] = None
    for t in msg.targets:
        for r in t.rois:
            if r.confidence < min_conf:
                continue
            rect = r.rect
            if rect.width <= 0 or rect.height <= 0:
                continue
            area = float(rect.width) * float(rect.height)
            if area > best_area:
                best_area = area
                cx = float(rect.x_offset) + float(rect.width) * 0.5
                cy = float(rect.y_offset) + float(rect.height) * 0.5
                best = (cx, cy, float(rect.width), float(rect.height))
    return best


class EyeTrackerNode(Node):
    def __init__(self) -> None:
        super().__init__("eye_track_node")

        self.declare_parameter("detection_topic", "hobot_dnn_detection")
        self.declare_parameter("image_width", 960)
        self.declare_parameter("image_height", 544)
        self.declare_parameter("tcp_host", "127.0.0.1")
        self.declare_parameter("tcp_port", 8765)
        self.declare_parameter("min_confidence", 0.35)
        self.declare_parameter("max_send_hz", 20.0)
        self.declare_parameter("smooth_alpha", 0.35)
        self.declare_parameter("dead_zone", 0.04)
        self.declare_parameter("min_move_to_send", 0.012)
        self.declare_parameter("flip_horizontal", False)
        self.declare_parameter("flip_vertical", False)
        self.declare_parameter("lost_decay_frames", 8)
        self.declare_parameter("lost_decay_factor", 0.88)
        # 注视幅度增益：>1 时同样的人体偏移会更快顶到 look 的 ±1（眼睛端会钳位）
        self.declare_parameter("gaze_gain", 3.0)

        topic = self.get_parameter("detection_topic").get_parameter_value().string_value
        self._img_w = float(self.get_parameter("image_width").value)
        self._img_h = float(self.get_parameter("image_height").value)
        self._tcp_host = self.get_parameter("tcp_host").get_parameter_value().string_value
        self._tcp_port = int(self.get_parameter("tcp_port").value)
        self._min_conf = float(self.get_parameter("min_confidence").value)
        self._max_send_hz = float(self.get_parameter("max_send_hz").value)
        self._alpha = float(self.get_parameter("smooth_alpha").value)
        self._dead = float(self.get_parameter("dead_zone").value)
        self._min_move = float(self.get_parameter("min_move_to_send").value)
        self._flip_h = bool(self.get_parameter("flip_horizontal").value)
        self._flip_v = bool(self.get_parameter("flip_vertical").value)
        self._lost_decay_n = int(self.get_parameter("lost_decay_frames").value)
        self._lost_decay_k = float(self.get_parameter("lost_decay_factor").value)
        self._gaze_gain = float(self.get_parameter("gaze_gain").value)

        self._ema_px = 0.0
        self._ema_py = 0.0
        self._last_sent_px = 0.0
        self._last_sent_py = 0.0
        self._last_send_mono = 0.0
        self._lost_streak = 0
        self._sock: Optional[socket.socket] = None
        self._sock_lock = threading.Lock()

        self.create_subscription(PerceptionTargets, topic, self._on_detection, 10)
        self.get_logger().info(
            f"eye_track: topic={topic} -> tcp://{self._tcp_host}:{self._tcp_port} "
            f"(image {int(self._img_w)}x{int(self._img_h)}, gaze_gain={self._gaze_gain})"
        )

    def destroy_node(self) -> bool:
        self._close_socket()
        return super().destroy_node()

    def _close_socket(self) -> None:
        with self._sock_lock:
            if self._sock is not None:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None

    def _ensure_socket(self) -> socket.socket:
        with self._sock_lock:
            if self._sock is not None:
                return self._sock
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(3.0)
            s.connect((self._tcp_host, self._tcp_port))
            s.settimeout(None)
            self._sock = s
            self.get_logger().info(f"TCP connected to {self._tcp_host}:{self._tcp_port}")
            return self._sock

    def _send_look(self, px: float, py: float) -> None:
        now = time.monotonic()
        min_dt = 1.0 / max(0.5, self._max_send_hz)
        if now - self._last_send_mono < min_dt:
            return
        if math.hypot(px - self._last_sent_px, py - self._last_sent_py) < self._min_move:
            return
        line = f"look {px:.4f} {py:.4f}\n".encode("ascii")
        try:
            sock = self._ensure_socket()
            sock.sendall(line)
            sock.settimeout(0.08)
            try:
                sock.recv(256)
            except socket.timeout:
                pass
            sock.settimeout(None)
        except OSError as e:
            self.get_logger().warning(f"TCP send failed: {e}")
            self._close_socket()
            return
        self._last_send_mono = now
        self._last_sent_px = px
        self._last_sent_py = py

    def _on_detection(self, msg: PerceptionTargets) -> None:
        roi = _largest_roi(msg, self._min_conf)
        if roi is None:
            self._lost_streak += 1
            if self._lost_streak >= self._lost_decay_n:
                self._ema_px *= self._lost_decay_k
                self._ema_py *= self._lost_decay_k
                if abs(self._ema_px) < 0.02 and abs(self._ema_py) < 0.02:
                    self._ema_px = 0.0
                    self._ema_py = 0.0
                self._send_look(self._ema_px, self._ema_py)
            return

        self._lost_streak = 0
        cx, cy, _w, _h = roi
        half_w = max(self._img_w * 0.5, 1.0)
        half_h = max(self._img_h * 0.5, 1.0)
        nx = (cx - half_w) / half_w
        ny = (cy - half_h) / half_h
        if self._flip_h:
            nx = -nx
        if self._flip_v:
            ny = -ny
        gain = max(0.1, min(10.0, self._gaze_gain))
        nx *= gain
        ny *= gain
        nx = max(-1.0, min(1.0, nx))
        ny = max(-1.0, min(1.0, ny))

        a = max(0.01, min(1.0, self._alpha))
        self._ema_px = a * nx + (1.0 - a) * self._ema_px
        self._ema_py = a * ny + (1.0 - a) * self._ema_py

        if abs(self._ema_px) < self._dead and abs(self._ema_py) < self._dead:
            return
        self._send_look(self._ema_px, self._ema_py)


def main() -> None:
    rclpy.init()
    node = EyeTrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
