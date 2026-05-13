# RTMP 协议深度剖析

## 前言

如果你做过直播推流，那你一定对 `rtmp://` 开头的推流地址不陌生。打开 OBS，输入一个 RTMP 地址，点击"开始推流"——背后就是 RTMP 协议在工作。尽管 Adobe 早在 2020 年就终止了 Flash Player 的支持，但 RTMP 作为直播推流协议的地位并没有被撼动。几乎所有主流直播平台的推流端仍然使用 RTMP：Twitch、YouTube Live、B 站直播、抖音直播，无一例外。

这种"Flash 已死，RTMP 犹存"的局面有其合理性。RTMP 协议本身与 Flash 播放器是解耦的——它是一个基于 TCP 的通用传输协议，任何能建立 TCP 连接的程序都可以实现。SRS、Nginx-RTMP、MediaMTX 等流媒体服务器以 RTMP 为核心协议接收推流，然后转封装为 HLS、HTTP-FLV 或 DASH 分发给观众。RTMP 在整个直播链路中扮演的是"推流入口"的角色。

你可能会问：RTSP 和 WebRTC 的传输延迟不是更低吗？为什么不用它们来推流？事实上，RTSP（通过 ANNOUNCE/RECORD）和 WebRTC 在技术上都可以实现推流，FFmpeg 也支持 RTSP over TCP 推流。但 RTMP 能成为推流事实标准，靠的不是延迟优势，而是一个常被忽视的关键事实：**RTMP 的媒体封装格式与 FLV 完全一致**。

RTMP 和 FLV 同为 Adobe 体系下的产物，它们的 Audio Message / Video Message 的 payload 结构和 FLV 文件中 Audio Tag / Video Tag 的 payload 结构完全相同——同样的编码信息头、同样的 AVC/HEVC 封装方式、同样的 AAC 封装方式。这意味着 RTMP 天然站在了 HTTP 分发链路的起点：

```
RTMP 推流数据（= FLV Tag payload）
         │
         ├──► HTTP-FLV：加 FLV 文件头 + Tag Header，几乎零成本转换
         ├──► HLS：remux 到 TS/fMP4 切片
         └──► DASH：remux 到 fMP4 切片
```

如果换成 RTSP/RTP 作为推流入口，服务端需要先将 RTP 载荷中的 NAL 分片（FU-A）重组为完整的 NAL 单元，再封装为 FLV/TS/fMP4 才能分发——多了一层解封装和重封装的开销与复杂度。RTMP 在这里省掉的不只是一点代码量，而是整条链路上的一层抽象。

RTMP 本身是全双工协议，既能推流（publish）也能拉流（play）。但在拉流/分发侧，RTMP 逐渐被 HTTP 系协议取代：RTMP 拉流需要维护持久 TCP 长连接和会话状态，无法利用 HTTP CDN 的缓存能力，端口 1935 也容易被防火墙封锁。而 HTTP-FLV 本质上就是 RTMP 拉流的 HTTP 化替代品——数据格式完全一样，只是传输从 RTMP 长连接换成了 HTTP 流式响应，延迟几乎相同但对 CDN 友好得多。于是现代直播的架构自然演变为：

```
推流端 ── RTMP ──► 流媒体服务器 ──┬── HTTP-FLV ──► 低延迟观众（1~3s）
                                  ├── HLS ────────► 大众观众（5~10s）
                                  └── WebRTC ─────► 超低延迟场景（<1s）
```

RTMP 的主战场收缩到了推流侧，而这个位置恰恰是它最不可替代的地方——OBS、硬件编码器、手机推流 SDK、CDN 推流接口全部围绕 RTMP 构建，整个推流端生态高度成熟。

不过趋势正在变化。WHIP（WebRTC HTTP Ingest Protocol）正在成为新一代推流标准——它保留了 WebRTC 的低延迟传输，但将建连简化为一个 HTTP POST 交换 SDP，OBS 29+ 已经支持。SRT 也在专业广电领域逐步替代 RTMP。但要撼动 RTMP 的推流入口地位，仍需要整个生态的迁移。

上一篇文章我们深入学习了 RTSP 协议——一个基于文本的信令协议，数据通过 RTP 传输。RTMP 则完全不同：它是一个**二进制协议**，信令和数据都在同一个 TCP 连接上传输，通过分块（Chunk）机制实现多路复用。理解 RTMP 需要掌握三个核心机制：**握手**、**分块**和**消息**。

本文将从协议规范出发，逐层拆解 RTMP 的工作原理，最后用 librtmp 完成一个完整的推流实战。

---

## 1. RTMP 协议概述

### RTMP 的历史与现状

RTMP（Real-Time Messaging Protocol）由 Macromedia 公司开发，2005 年 Adobe 收购 Macromedia 后接管了该协议。2012 年 Adobe 公开了 RTMP 规范（但并非完全开放，某些扩展如 RTMPE 仍为私有）。

RTMP 的设计初衷是为 Flash Player 提供低延迟的音视频传输能力，后来逐渐演变为直播推流的事实标准。时至今日，RTMP 推流 + HTTP-FLV/HLS 拉流仍然是国内直播行业最主流的技术方案。

### 基于 TCP 的全双工协议

RTMP 运行在 TCP 之上，默认端口 1935。一个 RTMP 连接从头到尾只使用一条 TCP 连接，所有的控制命令和音视频数据都在这条连接上双向传输。这种设计的好处是简化了 NAT 穿透和防火墙配置（只需开放一个端口），代价是 TCP 的队头阻塞可能影响实时性。

### RTMP 变种

| 变种 | 全称 | 传输方式 | 说明 |
|------|------|----------|------|
| RTMP | Real-Time Messaging Protocol | TCP:1935 | 标准协议 |
| RTMPS | RTMP over TLS/SSL | TCP:443 | TLS 加密，解决安全性和防火墙问题 |
| RTMPT | RTMP over HTTP | TCP:80 | HTTP 隧道封装，穿越严格防火墙 |
| RTMPE | Encrypted RTMP | TCP:1935 | Adobe 私有加密方案（已不推荐） |
| RTMFP | RT Media Flow Protocol | UDP | 基于 UDP 的 P2P 变种（已废弃） |

实际生产环境中，标准 RTMP 和 RTMPS 是最常用的。RTMPT 因为 HTTP 封装带来的额外延迟，仅在不得已时使用。

![RTMP协议栈](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/rtmp_stack.png)

---

## 2. RTMP 握手流程

RTMP 连接建立的第一步是握手。握手的目的是**确认协议版本**和**交换随机数据**，为后续通信建立基础。

### 三阶段握手

RTMP 握手由三对报文组成，客户端发送 C0、C1、C2，服务端发送 S0、S1、S2。整体流程如下：

1. **C0 + C1**：客户端发送版本号（C0）和 1536 字节的随机数据（C1）
2. **S0 + S1 + S2**：服务端回复版本号（S0）、自己的随机数据（S1）、以及对 C1 的回显（S2）
3. **C2**：客户端发送对 S1 的回显（C2），握手完成

实际实现中，C0+C1 通常合并在一个 TCP 包中发送，S0+S1+S2 也合并发送，以减少 RTT。

### 报文结构

**C0 / S0（1 字节）：**

```
+--------+
| version|
+--------+
  1 byte
```

`version` 固定为 3，表示使用 RTMP 协议。如果服务端收到不认识的版本号，应返回 S0 并终止连接。

**C1 / S1（1536 字节）：**

```
+--------+--------+--------+--------+
|           time (4 bytes)           |
+--------+--------+--------+--------+
|           zero (4 bytes)           |
+--------+--------+--------+--------+
|        random data (1528 bytes)    |
+--------+--------+--------+--------+
```

- `time`：发送方的时间戳（单位毫秒），用于后续计算网络延迟
- `zero`：在 Simple Handshake 中填 0；在 Complex Handshake 中用于版本协商
- `random data`：1528 字节的随机数据，对端会在 C2/S2 中原样回显

**C2 / S2（1536 字节）：**

```
+--------+--------+--------+--------+
|           time (4 bytes)           |
+--------+--------+--------+--------+
|          time2 (4 bytes)           |
+--------+--------+--------+--------+
|        random echo (1528 bytes)    |
+--------+--------+--------+--------+
```

- `time`：对端 C1/S1 中的 time 值原样回显
- `time2`：收到对端 C1/S1 时的本地时间戳
- `random echo`：对端 C1/S1 中 random data 的原样回显

### Simple Handshake vs Complex Handshake

Adobe 规范定义的是 Simple Handshake，随机数据不做任何校验。但实际上 Adobe 的 Flash Player 和 FMS 使用的是 **Complex Handshake**（也叫 RTMP Handshake with Digest），在 C1/S1 中嵌入 HMAC-SHA256 摘要来做身份校验，防止非 Adobe 客户端接入。

开源实现（如 SRS、librtmp）通常同时支持两种握手模式：先尝试 Complex Handshake，如果对端不支持则回退到 Simple Handshake。对于自己搭建的流媒体服务器，使用 Simple Handshake 就足够了。

![RTMP握手流程](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/rtmp_handshake.png)

---

## 3. RTMP Chunk 分块机制

握手完成后，RTMP 的所有数据都以 **Chunk**（块）为单位传输。分块机制是 RTMP 协议设计中最精妙、也最容易让人困惑的部分。

### Message 与 Chunk 的关系

理解分块机制之前，先要分清两个概念：

- **Message（消息）**：逻辑语义单位——一帧视频、一帧音频、一条 connect 命令，各自是一个完整的 Message
- **Chunk（块）**：网络传输单位——Message 不直接发送，而是先按固定大小切分为 Chunk，再通过 TCP 传输

一个 Message 被切分为一个或多个 Chunk，接收端把属于同一个 Message 的所有 Chunk 按序拼接，还原出完整的 Message 后交给上层处理：

```
            一个 Video Message（50KB 关键帧）
┌──────────────────────────────────────────────────┐
│                 完整的视频帧数据                     │
└──────────────────────────────────────────────────┘
                        │
                        │ 按 Chunk Size（假设 4096B）切分
                        ▼
┌──────────┐ ┌──────────┐ ┌──────────┐     ┌──────────┐
│ Chunk 1  │ │ Chunk 2  │ │ Chunk 3  │ ... │ Chunk 13 │
│ fmt=0    │ │ fmt=3    │ │ fmt=3    │     │ fmt=3    │
│ 完整头部  │ │ 无头部    │ │ 无头部    │     │ 无头部    │
│ 4096B    │ │ 4096B    │ │ 4096B    │     │ 剩余字节  │
└──────────┘ └──────────┘ └──────────┘     └──────────┘
```

第一个 Chunk 使用 fmt=0 携带完整的 Message 元数据（时间戳、消息长度、消息类型、stream id），后续 Chunk 使用 fmt=3（0 字节头部），因为它们属于同一个 Message，元数据完全相同无需重复。接收端根据 Chunk 头中的 **cs id**（chunk stream id）和第一个 Chunk 中声明的消息总长度，识别并重组出完整的 Message。

### 为什么需要分块

分块的核心价值在于**多路复用**。不同 Message 的 Chunk 可以在 TCP 连接上交错发送：

```
TCP 连接上的实际字节流：

[Video Chunk 1][Audio Chunk 1][Video Chunk 2][Audio Chunk 2][Video Chunk 3]...
   cs_id=6        cs_id=4        cs_id=6        cs_id=4        cs_id=6
```

考虑这样一个场景：主播正在推流，一个视频关键帧大小为 100KB，同时还有一个 200 字节的音频帧要发送。如果不分块，音频帧必须等 100KB 的视频帧全部发完才能发送，延迟会非常大。有了分块，视频每发一个 Chunk（如 4096 字节）就可以插入一个音频 Chunk，音频延迟从"等 100KB 发完"缩短到"最多等一个 Chunk 的时间"。

总结分块解决的三个问题：

- **大消息切分**：将大的音视频帧切分为固定大小的块，避免单个大消息长时间占用连接
- **多路复用**：不同类型的消息（音频、视频、控制命令）的 Chunk 可以交错发送
- **缓解队头阻塞**：视频关键帧的传输不会长时间阻塞音频帧和控制消息

### Chunk 的整体结构

每个 Chunk 由四部分组成：

```
+--------------+----------------+--------------------+------------+
| Basic Header | Message Header | Extended Timestamp | Chunk Data |
+--------------+----------------+--------------------+------------+
   1~3 bytes      0/3/7/11 bytes     0 or 4 bytes      variable
```

![RTMP Chunk结构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/rtmp_chunk.png)

### Basic Header

Basic Header 包含两个字段：**chunk type**（fmt，2 bit）和 **chunk stream ID**（cs id）。根据 cs id 的范围，Basic Header 有三种长度：

**1 字节格式（cs id: 2~63）：**

```
 0 1 2 3 4 5 6 7
+-+-+-+-+-+-+-+-+
|fmt|   cs id   |
+-+-+-+-+-+-+-+-+
```

**2 字节格式（cs id: 64~319）：**

```
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|fmt|     0     |   cs id - 64  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

当第一个字节的低 6 位为 0 时，表示使用 2 字节格式，实际 cs id = 第二个字节 + 64。

**3 字节格式（cs id: 64~65599）：**

```
 0 1 2 3 4 5 6 7 8 9 ... 2 3
+-+-+-+-+-+-+-+-+-+-+...+-+-+
|fmt|     1     |  cs id - 64  |
+-+-+-+-+-+-+-+-+-+-+...+-+-+
```

当第一个字节的低 6 位为 1 时，使用 3 字节格式，后两个字节以小端序存储 cs id - 64。

cs id 0 和 1 被保留用于标识 2 字节和 3 字节格式，cs id 2 保留给协议控制消息。实践中，RTMP 通常只用到几个固定的 cs id：2（协议控制）、3（命令消息）、4（音频）、6（视频）等。

### Message Header（四种类型）

`fmt` 字段决定了 Message Header 的格式，这是 RTMP 压缩头部开销的核心设计：

**Type 0（fmt=0，11 字节）—— 完整头部：**

```
+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
|              timestamp             | message length  |type id |          message stream id        |
+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
              3 bytes                    3 bytes         1 byte            4 bytes (little-endian)
```

包含完整的消息元数据。每个 Chunk Stream 的第一个消息，或者当时间戳发生不连续跳变时，必须使用 Type 0。

**Type 1（fmt=1，7 字节）—— 省略 stream id：**

```
+--------+--------+--------+--------+--------+--------+--------+
|         timestamp delta            | message length  |type id |
+--------+--------+--------+--------+--------+--------+--------+
              3 bytes                    3 bytes         1 byte
```

省略了 message stream id（与前一个 Chunk 相同）。timestamp 变为增量（delta）。适用于同一个流上消息大小或类型变化的情况。

**Type 2（fmt=2，3 字节）—— 仅时间戳增量：**

```
+--------+--------+--------+
|      timestamp delta      |
+--------+--------+--------+
           3 bytes
```

消息长度和类型都与前一个 Chunk 相同，只有时间戳在递增。适用于固定码率的音频流——每个音频帧大小一致，只有时间戳在变。

**Type 3（fmt=3，0 字节）：**

没有 Message Header。所有字段都与前一个 Chunk 完全一致。用于同一个消息被切分为多个 Chunk 时，后续的 Chunk 使用 Type 3（因为它们属于同一个消息，元数据完全相同）。

这种逐级压缩的设计非常高效。一个 AAC 音频流，第一帧用 Type 0（12 字节头），后续帧如果大小一致就用 Type 2（4 字节头），如果连时间戳增量都一样就用 Type 3（1 字节头）。对于持续推流的场景，绝大多数 Chunk 只需 1 字节的头部开销。

### Chunk Size 的协商与调整

默认的 Chunk Size 是 128 字节。这个值对于现代直播场景来说太小了——一个 100KB 的视频关键帧会被切成近 800 个 Chunk，每个 Chunk 都要带上至少 1 字节的 Basic Header，额外开销显著。

双方可以通过 **Set Chunk Size** 控制消息动态调整 Chunk Size。常见的设置是 4096 或 65536 字节。OBS 默认使用 4096，SRS 默认使用 60000。

---

## 4. RTMP Message 类型

RTMP 的消息通过 Message Type ID 区分，主要分为以下几类。

### 协议控制消息（Message Type ID: 1~6）

这些消息使用 cs id=2、message stream id=0 传输，用于控制协议行为：

| Type ID | 名称 | 说明 |
|---------|------|------|
| 1 | Set Chunk Size | 设置后续 Chunk 的最大大小（默认 128） |
| 2 | Abort Message | 通知对端丢弃指定 Chunk Stream 上未完成的消息 |
| 3 | Acknowledgement | 确认已接收的字节数 |
| 5 | Window Acknowledgement Size | 设置 ACK 窗口大小 |
| 6 | Set Peer Bandwidth | 设置对端的输出带宽限制 |

**Set Chunk Size** 是最常用的协议控制消息。推流开始前，客户端通常会先发一个 Set Chunk Size 将块大小调大：

```cpp
// Set Chunk Size 消息结构（4 字节 payload）
// 最高位必须为 0，有效范围 1~16777215
uint32_t chunk_size = htonl(4096);
```

**Acknowledgement** 和 **Window Acknowledgement Size** 实现了一个简单的流控机制。发送方设置一个窗口大小（比如 2500000 字节），接收方每收到窗口大小的数据就回复一个 Acknowledgement 消息，告知发送方"我已经处理了这么多数据"。如果发送方在窗口耗尽后没有收到 ACK，应停止发送，防止接收方被淹没。

### 用户控制消息（Message Type ID: 4）

用户控制消息用于传递流级别的事件，payload 的前 2 字节是事件类型：

| 事件类型 | 名称 | 说明 |
|----------|------|------|
| 0 | Stream Begin | 流可用，通知客户端可以开始播放 |
| 1 | Stream EOF | 流结束 |
| 3 | SetBufferLength | 客户端通知服务端自己的缓冲区大小 |
| 6 | Ping Request | 服务端发起 ping |
| 7 | Ping Response | 客户端回复 pong |

### 音视频消息

| Type ID | 说明 |
|---------|------|
| 8 | Audio Message，承载音频数据 |
| 9 | Video Message，承载视频数据 |

音视频消息的 payload 第一个字节包含编码信息。以视频消息为例：

```
+--------+--------+
|FTCC CCCC|  AVC   |  ...video data...
+--------+--------+
```

- 高 4 位（F+T）：帧类型（1=关键帧，2=非关键帧）
- 低 4 位（C）：编码 ID（7=AVC/H.264，12=HEVC/H.265）

对于 AVC（H.264），紧随其后是 AVC Packet Type（0=AVC Sequence Header，即 SPS/PPS；1=AVC NALU，即实际视频帧数据）。音频消息的结构类似，第一个字节包含音频编码类型（10=AAC）、采样率、位深和声道信息。

### 命令消息（Message Type ID: 20/17）

命令消息使用 AMF（Action Message Format）编码，Type 20 是 AMF0 编码，Type 17 是 AMF3 编码。RTMP 推流/拉流的核心交互就是通过命令消息完成的。

一个完整的 RTMP 推流交互流程：

```
Client                                 Server
  |                                      |
  |------- connect("live") ------------->|
  |<------ Window Ack Size --------------|
  |<------ Set Peer Bandwidth -----------|
  |<------ Set Chunk Size ---------------|
  |<------ _result (connect OK) ---------|
  |                                      |
  |------- releaseStream("stream") ----->|
  |------- FCPublish("stream") --------->|
  |------- createStream() ------------->|
  |<------ _result (stream id=1) --------|
  |                                      |
  |------- publish("stream","live") ---->|
  |<------ Stream Begin -----------------|
  |<------ onStatus("Publishing") -------|
  |                                      |
  |------- Set Chunk Size(4096) -------->|
  |------- Audio/Video Data ------------>|
  |------- Audio/Video Data ------------>|
  |           ...                        |
```

**connect**：建立网络连接后的第一个命令，参数包含 app 名称（如 "live"）、tcUrl、flashVer 等。服务端回复 `_result` 表示连接成功。

**createStream**：请求服务端创建一个逻辑流，服务端返回一个 stream id（通常为 1）。后续的音视频数据都关联到这个 stream id。

**publish**：开始推流，参数包含流名称和推流类型（"live" 表示直播）。服务端回复 `onStatus` 事件确认推流开始。

**play**：拉流时使用，请求服务端开始发送指定流的音视频数据。

---

## 5. AMF 编码格式

RTMP 的命令消息使用 AMF（Action Message Format）进行序列化。AMF 是一种紧凑的二进制格式，有 AMF0 和 AMF3 两个版本。RTMP 主要使用 AMF0。

### AMF0 基本数据类型

AMF0 采用 TLV（Type-Length-Value）风格的编码，每个值以 1 字节的类型标记开头：

| 类型标记 | 数据类型 | 编码方式 |
|----------|----------|----------|
| 0x00 | Number | 8 字节 IEEE 754 双精度浮点（大端序） |
| 0x01 | Boolean | 1 字节（0x00=false, 0x01=true） |
| 0x02 | String | 2 字节长度 + UTF-8 字符串数据 |
| 0x03 | Object | 键值对序列，以 0x000009 结束 |
| 0x05 | Null | 无附加数据 |
| 0x08 | ECMA Array | 4 字节元素个数 + 键值对序列 |

### 编码/解码示例

以 RTMP connect 命令为例，它的 AMF0 编码如下：

```
02 0007 "connect"    -- String: 命令名称
00 3FF0000000000000  -- Number: 事务 ID = 1.0
03                   -- Object 开始
  02 0003 "app"      -- 键: "app"
  02 0004 "live"     -- 值: "live"
  02 0005 "tcUrl"    -- 键: "tcUrl"
  02 001C "rtmp://192.168.1.100/live"  -- 值
  000009             -- Object 结束
```

用 C++ 实现一个简单的 AMF0 编码器：

```cpp
#include <cstring>
#include <string>
#include <vector>

class Amf0Writer {
public:
    void WriteNumber(double value) {
        buf_.push_back(0x00);
        uint64_t n;
        std::memcpy(&n, &value, 8);
        for (int i = 7; i >= 0; --i)
            buf_.push_back(static_cast<uint8_t>(n >> (i * 8)));
    }

    void WriteString(const std::string& s) {
        buf_.push_back(0x02);
        WriteUint16(static_cast<uint16_t>(s.size()));
        buf_.insert(buf_.end(), s.begin(), s.end());
    }

    void WriteBoolean(bool value) {
        buf_.push_back(0x01);
        buf_.push_back(value ? 0x01 : 0x00);
    }

    void WriteNull() {
        buf_.push_back(0x05);
    }

    void WriteObjectStart() {
        buf_.push_back(0x03);
    }

    void WriteObjectKey(const std::string& key) {
        WriteUint16(static_cast<uint16_t>(key.size()));
        buf_.insert(buf_.end(), key.begin(), key.end());
    }

    void WriteObjectEnd() {
        buf_.push_back(0x00);
        buf_.push_back(0x00);
        buf_.push_back(0x09);
    }

    const uint8_t* Data() const { return buf_.data(); }
    size_t Size() const { return buf_.size(); }

private:
    void WriteUint16(uint16_t val) {
        buf_.push_back(static_cast<uint8_t>(val >> 8));
        buf_.push_back(static_cast<uint8_t>(val));
    }

    std::vector<uint8_t> buf_;
};
```

构造一个 connect 命令：

```cpp
Amf0Writer writer;
writer.WriteString("connect");
writer.WriteNumber(1.0);  // transaction ID
writer.WriteObjectStart();
writer.WriteObjectKey("app");
writer.WriteString("live");
writer.WriteObjectKey("tcUrl");
writer.WriteString("rtmp://192.168.1.100/live");
writer.WriteObjectKey("type");
writer.WriteString("nonprivate");
writer.WriteObjectEnd();
```

---

## 6. C++ 实战：使用 librtmp 推流

### librtmp 简介与安装

librtmp 是 RTMPDump 项目的核心库，提供了 RTMP 协议的完整客户端实现，包括握手、连接、推拉流等全部功能。

```bash
# Ubuntu 安装
sudo apt-get install librtmp-dev

# 或从源码编译
git clone https://git.ffmpeg.org/rtmpdump.git
cd rtmpdump
make SYS=posix
sudo make install
```

### 推送 H.264 + AAC 到 RTMP 服务器

下面是一个使用 librtmp 推流的完整示例。核心流程是：读取 FLV 文件 → 解析 Tag → 通过 RTMP 发送。选择 FLV 作为输入是因为 RTMP 的音视频封装格式与 FLV 完全一致。

```cpp
#include <librtmp/rtmp.h>
#include <librtmp/log.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <chrono>
#include <thread>

struct FlvTagHeader {
    uint8_t  tag_type;
    uint32_t data_size;
    uint32_t timestamp;
};

bool ReadFlvTagHeader(FILE* fp, FlvTagHeader& tag) {
    uint8_t buf[11];
    if (fread(buf, 1, 11, fp) != 11) return false;

    tag.tag_type = buf[0];
    tag.data_size = (buf[1] << 16) | (buf[2] << 8) | buf[3];
    tag.timestamp = (buf[7] << 24) | (buf[4] << 16) | (buf[5] << 8) | buf[6];
    return true;
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::fprintf(stderr, "Usage: %s <input.flv> <rtmp://url>\n", argv[0]);
        return 1;
    }

    const char* flv_path = argv[1];
    const char* rtmp_url = argv[2];

    FILE* fp = std::fopen(flv_path, "rb");
    if (!fp) {
        std::perror("fopen");
        return 1;
    }

    // 跳过 FLV 文件头（9 字节）和第一个 PreviousTagSize（4 字节）
    std::fseek(fp, 9 + 4, SEEK_SET);

    RTMP* rtmp = RTMP_Alloc();
    RTMP_Init(rtmp);

    RTMP_SetupURL(rtmp, const_cast<char*>(rtmp_url));
    RTMP_EnableWrite(rtmp);

    if (!RTMP_Connect(rtmp, nullptr)) {
        std::fprintf(stderr, "RTMP_Connect failed\n");
        RTMP_Free(rtmp);
        std::fclose(fp);
        return 1;
    }

    if (!RTMP_ConnectStream(rtmp, 0)) {
        std::fprintf(stderr, "RTMP_ConnectStream failed\n");
        RTMP_Close(rtmp);
        RTMP_Free(rtmp);
        std::fclose(fp);
        return 1;
    }

    std::printf("Connected to %s\n", rtmp_url);

    uint32_t start_time = 0;
    bool first_tag = true;
    auto base_clock = std::chrono::steady_clock::now();

    FlvTagHeader tag;
    while (ReadFlvTagHeader(fp, tag)) {
        std::vector<uint8_t> tag_data(11 + tag.data_size + 4);

        // 回退 11 字节重新读取完整 Tag（包括 header + data + PreviousTagSize）
        std::fseek(fp, -11, SEEK_CUR);
        if (fread(tag_data.data(), 1, tag_data.size(), fp) != tag_data.size())
            break;

        if (first_tag) {
            start_time = tag.timestamp;
            first_tag = false;
        }

        // 按时间戳控制发送节奏，模拟实时推流
        uint32_t elapsed = tag.timestamp - start_time;
        auto target = base_clock + std::chrono::milliseconds(elapsed);
        std::this_thread::sleep_until(target);

        // 发送 Tag Data（不含 11 字节 header 和 4 字节 PreviousTagSize）
        RTMPPacket packet;
        std::memset(&packet, 0, sizeof(packet));
        packet.m_nChannel    = tag.tag_type == 0x09 ? 0x06 : 0x04;
        packet.m_headerType  = RTMP_PACKET_SIZE_LARGE;
        packet.m_packetType  = tag.tag_type;
        packet.m_nTimeStamp  = tag.timestamp;
        packet.m_nInfoField2 = rtmp->m_stream_id;
        packet.m_nBodySize   = tag.data_size;
        packet.m_body        = reinterpret_cast<char*>(tag_data.data() + 11);

        if (!RTMP_SendPacket(rtmp, &packet, 0)) {
            std::fprintf(stderr, "RTMP_SendPacket failed\n");
            break;
        }
    }

    std::printf("Push finished\n");
    RTMP_Close(rtmp);
    RTMP_Free(rtmp);
    std::fclose(fp);
    return 0;
}
```

### 编译与测试

```bash
g++ -o rtmp_push rtmp_push.cpp -lrtmp -lz -lssl -lcrypto
```

搭配 SRS 进行测试：

```bash
# 启动 SRS（Docker 方式）
docker run -d -p 1935:1935 -p 8080:8080 ossrs/srs:5

# 推流
./rtmp_push test.flv rtmp://127.0.0.1/live/stream

# 另一个终端用 FFplay 拉流验证
ffplay rtmp://127.0.0.1/live/stream

# 或通过 HTTP-FLV 拉流
ffplay http://127.0.0.1:8080/live/stream.flv
```

如果使用 Nginx-RTMP：

```bash
# 安装 Nginx-RTMP
sudo apt-get install libnginx-mod-rtmp

# 在 nginx.conf 中添加 RTMP 配置
# rtmp {
#     server {
#         listen 1935;
#         application live {
#             live on;
#         }
#     }
# }
```

---

## 踩坑与调优

### Chunk Size 对性能的影响

默认的 128 字节 Chunk Size 在现代直播场景下性能很差。一个 4Mbps 码率的视频流，每个关键帧约 50KB，按 128 字节分块会产生约 400 个 Chunk，每个 Chunk 都有 Basic Header 开销。将 Chunk Size 调大到 4096 或更高，可以显著减少头部开销和系统调用次数。

但 Chunk Size 也不是越大越好。过大的 Chunk Size 会降低多路复用的粒度——如果一个视频 Chunk 占满了整个发送窗口，音频数据的延迟会增加。一般推荐 4096~60000 字节。

### 时间戳单调递增的重要性

RTMP 的时间戳必须保持单调递增。如果时间戳出现回退或跳变，服务端可能会：

- 丢弃该帧数据
- 重置播放缓冲区，导致观众端出现卡顿
- 直接断开连接

常见的时间戳问题源于推流端重连后没有重新计算时间戳基准，导致新连接的时间戳从 0 开始而非接续上次的值。正确的做法是在重连时记录上次的时间戳偏移，新连接的时间戳 = 实际时间戳 + 偏移量。

### 推流断开重连策略

直播推流中断对用户体验的影响是致命的。一个健壮的推流客户端应该实现自动重连：

```cpp
void PushWithReconnect(const char* url, int max_retries) {
    int retry_count = 0;
    int backoff_ms = 1000;

    while (retry_count < max_retries) {
        if (DoPush(url)) {
            retry_count = 0;
            backoff_ms = 1000;
        }
        retry_count++;
        std::fprintf(stderr, "Reconnecting in %dms (attempt %d/%d)\n",
                     backoff_ms, retry_count, max_retries);
        std::this_thread::sleep_for(std::chrono::milliseconds(backoff_ms));
        backoff_ms = std::min(backoff_ms * 2, 30000);  // 指数退避，上限 30 秒
    }
}
```

关键点：

- **指数退避**：避免频繁重连加重服务器负担
- **重连上限**：防止无限重试（网络彻底不可用时应通知上层）
- **重发关键帧**：重连成功后必须先发送 SPS/PPS（AVC Sequence Header）和 AAC Sequence Header，否则播放端无法解码

---

## 总结

本文从协议规范出发，系统剖析了 RTMP 协议的核心机制：

- **RTMP 基于 TCP** 的单连接全双工设计，让它天然具备 NAT 穿透友好、部署简单的优势，同时也继承了 TCP 队头阻塞的缺点
- **三阶段握手**（C0C1C2 / S0S1S2）建立连接，Simple Handshake 用于开源生态，Complex Handshake 用于 Adobe 私有校验
- **Chunk 分块机制**是 RTMP 的精髓——通过 4 种 Message Header 类型实现头部压缩，通过可调节的 Chunk Size 平衡传输效率和多路复用粒度
- **AMF0 编码**为 RTMP 的命令消息提供了紧凑的序列化格式
- **connect → createStream → publish** 是推流的标准命令序列
- 实际开发中需要关注 **Chunk Size 调优**、**时间戳单调性**和**断线重连**等工程细节

RTMP 虽然不再是"现代"协议，但它的设计思想——分块复用、头部压缩、流控机制——在后续的协议（如 HTTP/2 的帧机制）中都能看到影子。深入理解 RTMP，不仅是直播开发的实际需要，也是理解流媒体协议演进的重要一环。

下一篇我们将进入 **FLV 封装与 RTMP 直播实践**，探讨 FLV 容器格式的细节、HTTP-FLV 直播方案的原理，以及如何基于 Nginx-RTMP 搭建一套完整的直播分发系统。
