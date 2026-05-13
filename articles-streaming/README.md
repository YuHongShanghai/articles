# 音视频流媒体技术教程：从网络编程到 WebRTC 实战

> 一套面向有音视频基础的开发者的流媒体技术进阶教程。  
> 实战代码基于 C++，配合 live555、libsrt、libwebrtc 等成熟开源库。

## 前置要求

本教程假设读者已具备以下基础知识：

- FFmpeg 命令行使用与基本 API 调用
- 音视频编解码原理（H.264/H.265、AAC/Opus 等）
- 常见媒体容器格式（MP4、FLV、TS 等）
- C++ 语言基础（C++11/14/17）
- Linux 开发环境

## 教程目录

### 第一篇：网络编程基础

流媒体的底座是网络。本篇从 Socket 编程出发，逐步构建高性能网络编程的知识体系。

| # | 文章 | 关键词 |
|---|------|--------|
| 01 | [Socket 编程基础：TCP 与 UDP 的选择](01-network-fundamentals/01-socket-basics.md) | BSD Socket, TCP/UDP, 流媒体传输选型 |
| 02 | [I/O 多路复用：从 select 到 epoll](01-network-fundamentals/02-io-multiplexing.md) | select, poll, epoll, io_uring |
| 03 | [Reactor 模式与事件驱动网络框架](01-network-fundamentals/03-reactor-pattern.md) | Reactor, EventLoop, 主从多线程 |
| 04 | [流媒体场景下的网络优化](01-network-fundamentals/04-network-optimization.md) | TCP 调优, 零拷贝, 抓包分析 |

### 第二篇：流媒体传输基础

进入流媒体领域的核心传输机制，理解音视频数据如何在网络上高效传输。

| # | 文章 | 关键词 |
|---|------|--------|
| 05 | [RTP/RTCP 协议深度解析](02-streaming-transport/05-rtp-rtcp.md) | RTP 报文, H.264/H.265/AAC 载荷格式, RTCP 反馈, 音视频同步 |
| 06 | [SDP 与媒体协商机制](02-streaming-transport/06-sdp-and-media-negotiation.md) | SDP 格式, Offer/Answer, Codec 协商 |
| 07 | [抖动缓冲与前向纠错](02-streaming-transport/07-jitter-buffer-and-fec.md) | Jitter Buffer, FEC, NACK |

### 第三篇：经典流媒体协议

深入剖析 RTSP 和 RTMP 两大经典协议，以及 FLV 直播实践。

| # | 文章 | 关键词 |
|---|------|--------|
| 08 | [RTSP 协议详解与 live555 实战](03-classic-streaming-protocols/08-rtsp-protocol.md) | RTSP 方法, live555, RTP 传输 |
| 09 | [RTMP 协议深度剖析](03-classic-streaming-protocols/09-rtmp-protocol.md) | RTMP 握手, Chunk, AMF, librtmp |
| 10 | [FLV 封装与 RTMP 直播实践](03-classic-streaming-protocols/10-flv-and-rtmp-in-practice.md) | FLV 格式, HTTP-FLV, Nginx-RTMP |

### 第四篇：现代流媒体协议

面向当下和未来的流媒体传输技术。

| # | 文章 | 关键词 |
|---|------|--------|
| 11 | [HLS 协议原理与实践](04-modern-streaming-protocols/11-hls-protocol.md) | M3U8, TS 切片, LL-HLS |
| 12 | [DASH 协议与自适应码率](04-modern-streaming-protocols/12-dash-protocol.md) | MPD, ABR 算法, CMAF |
| 13 | [SRT 协议与低延迟传输](04-modern-streaming-protocols/13-srt-protocol.md) | SRT, ARQ, libsrt |
| 14 | [QUIC/HTTP3 在流媒体中的应用](04-modern-streaming-protocols/14-quic-and-streaming.md) | QUIC, HTTP/3, MoQ |

### 第五篇：WebRTC 技术体系

WebRTC 全栈知识，从信令设计到拥塞控制。

| # | 文章 | 关键词 |
|---|------|--------|
| 15 | [WebRTC 整体架构与信令设计](05-webrtc/15-webrtc-architecture.md) | 协议栈, 信令, PeerConnection |
| 16 | [ICE/STUN/TURN：NAT 穿越全攻略](05-webrtc/16-ice-stun-turn.md) | NAT 类型, ICE, coturn |
| 17 | [DTLS-SRTP：WebRTC 的安全传输](05-webrtc/17-dtls-srtp.md) | DTLS 握手, SRTP, 密钥协商 |
| 18 | [WebRTC 拥塞控制：GCC 与 BBR](05-webrtc/18-webrtc-congestion-control.md) | GCC, BBR, Simulcast, SVC |
| 19 | [libwebrtc 实战：构建 P2P 音视频通话](05-webrtc/19-libwebrtc-practice.md) | libwebrtc, Native API, 1v1 通话 |

### 第六篇：综合实战项目

将所学知识整合到真实项目场景中。

| # | 文章 | 关键词 |
|---|------|--------|
| 20 | [实战：构建一套完整的直播系统](06-practice-projects/20-live-streaming-system.md) | SRS, RTMP 推流, HLS 分发 |
| 21 | [实战：多人视频会议系统](06-practice-projects/21-video-conferencing.md) | SFU, Janus, 弱网对抗 |
| 22 | [实战：超低延迟直播方案](06-practice-projects/22-low-latency-streaming.md) | WHIP/WHEP, SRT, 延迟优化 |

## 实战环境

- **操作系统**：Ubuntu 22.04 LTS
- **编译器**：GCC 11+ / Clang 14+
- **构建工具**：CMake 3.20+
- **核心开源库**：live555, librtmp, libsrt, libwebrtc, SRS, Janus, coturn
- **辅助工具**：FFmpeg, Wireshark, tcpdump
- **Python 3.10+**（用于绘制教程插图）

## 插图说明

本教程所有技术插图均由 Python 脚本生成，源码位于 `diagrams/` 目录。安装绘图依赖后可一键生成全部插图：

```bash
cd diagrams
pip install -r requirements.txt
python generate_all.py
```

## 许可证

本教程内容采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 许可证。  
代码示例采用 MIT 许可证。
