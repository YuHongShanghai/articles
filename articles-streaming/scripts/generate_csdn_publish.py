#!/usr/bin/env python3
"""Generate publish/*.md for CSDN: replace diagram URLs with Gitee raw base."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "publish"

# 序号、源文件相对路径、发布文件名中的短标题（与正文首行 # 标题一致）
ARTICLES: list[tuple[int, str, str]] = [
    (1, "01-network-fundamentals/01-socket-basics.md", "Socket 编程基础：TCP 与 UDP 的选择"),
    (2, "01-network-fundamentals/02-io-multiplexing.md", "I/O 多路复用：从 select 到 epoll"),
    (3, "01-network-fundamentals/03-reactor-pattern.md", "Reactor 模式与事件驱动网络框架"),
    (4, "01-network-fundamentals/04-network-optimization.md", "流媒体场景下的网络优化"),
    (5, "02-streaming-transport/05-rtp-rtcp.md", "RTP/RTCP 协议深度解析"),
    (6, "02-streaming-transport/06-sdp-and-media-negotiation.md", "SDP 与媒体协商机制"),
    (7, "02-streaming-transport/07-jitter-buffer-and-fec.md", "抖动缓冲与前向纠错"),
    (8, "03-classic-streaming-protocols/08-rtsp-protocol.md", "RTSP 协议详解与 live555 实战"),
    (9, "03-classic-streaming-protocols/09-rtmp-protocol.md", "RTMP 协议深度剖析"),
    (10, "03-classic-streaming-protocols/10-flv-and-rtmp-in-practice.md", "FLV 封装与 RTMP 直播实践"),
    (11, "04-modern-streaming-protocols/11-hls-protocol.md", "HLS 协议原理与实践"),
    (12, "04-modern-streaming-protocols/12-dash-protocol.md", "DASH 协议与自适应码率"),
    (13, "04-modern-streaming-protocols/13-srt-protocol.md", "SRT 协议与低延迟传输"),
    (14, "04-modern-streaming-protocols/14-quic-and-streaming.md", "QUIC/HTTP3 在流媒体中的应用"),
    (15, "05-webrtc/15-webrtc-architecture.md", "WebRTC 整体架构与信令设计"),
    (16, "05-webrtc/16-ice-stun-turn.md", "ICE/STUN/TURN：NAT 穿越全攻略"),
    (17, "05-webrtc/17-dtls-srtp.md", "DTLS-SRTP：WebRTC 的安全传输"),
    (18, "05-webrtc/18-webrtc-congestion-control.md", "WebRTC 拥塞控制：GCC 与 BBR"),
    (19, "05-webrtc/19-libwebrtc-practice.md", "libwebrtc 实战：构建 P2P 音视频通话"),
    (20, "06-practice-projects/20-live-streaming-system.md", "实战：构建一套完整的直播系统"),
    (21, "06-practice-projects/21-video-conferencing.md", "实战：多人视频会议系统"),
    (22, "06-practice-projects/22-low-latency-streaming.md", "实战：超低延迟直播方案"),
]

COLUMN = os.environ.get("CSDN_COLUMN_NAME", "音视频流媒体进阶：从网络到 WebRTC")

# 可被环境变量 GITEE_RAW 覆盖（与图床仓库默认分支一致，当前为 master）
GITEE_RAW = os.environ.get(
    "GITEE_RAW", "https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master"
).rstrip("/")

IMG_PATTERN = re.compile(r"\]\(\.\./diagrams/output/")


def main() -> None:
    PUBLISH.mkdir(parents=True, exist_ok=True)
    prefix = f"【{COLUMN}】"
    for num, rel, title in ARTICLES:
        src = ROOT / rel
        text = src.read_text(encoding="utf-8")
        text = IMG_PATTERN.sub(f"]({GITEE_RAW}/diagrams/output/", text)
        safe_title = title.replace("/", "／")
        out_name = f"{prefix}第{num:02d}篇-{safe_title}.md"
        (PUBLISH / out_name).write_text(text, encoding="utf-8")
    print(f"Wrote {len(ARTICLES)} files to {PUBLISH}")
    print(f"GITEE_RAW={GITEE_RAW}")


if __name__ == "__main__":
    main()
