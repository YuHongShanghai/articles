# RTP/RTCP 协议深度解析

## 前言

在上一篇的网络优化中，我们提到过 `writev` 聚集写入 RTP 头和载荷的例子，也在抓包分析中用 Wireshark 观察过 RTP 流的统计信息。从本篇开始，我们正式进入流媒体传输的核心领域。

RTP（Real-time Transport Protocol）和 RTCP（RTP Control Protocol）是整个实时流媒体传输的基石协议。无论是 WebRTC 的音视频通话、RTSP 的摄像头监控、还是视频会议系统，底层传输都依赖 RTP 来承载媒体数据、依赖 RTCP 来反馈传输质量。可以说，理解 RTP/RTCP 是深入学习任何实时流媒体协议的前提。

本文的目标很明确：**深入理解 RTP/RTCP 的每一个字段含义，掌握 H.264、H.265、AAC 等主流编码在 RTP 中的载荷打包格式，并能用 C++ 从零解析和构造 RTP 包**。读完本文，你应该能用 Wireshark 抓一个 RTP 包，逐比特地说出每个字段的含义，知道载荷里的 FU-A 分片是怎么回事，并且能写出一个可以接收和解析 RTP 流的 C++ 程序。

## 1. RTP 协议概述

### 协议栈定位

RTP 定义在 RFC 3550 中，从协议分层的角度看，它是一个**应用层协议**，通常运行在 UDP 之上。之所以选择 UDP 而非 TCP，核心原因是实时性——TCP 的重传机制会引入不可控的延迟，对于实时音视频来说，一帧迟到的数据不如一帧丢掉的数据。

典型的协议栈是这样的：

```
┌─────────────────────────┐
│   应用层（编解码器）       │
├─────────────────────────┤
│   RTP / RTCP            │
├─────────────────────────┤
│   UDP                   │
├─────────────────────────┤
│   IP                    │
├─────────────────────────┤
│   链路层                 │
└─────────────────────────┘
```

一个常见的约定是：RTP 使用偶数端口，RTCP 使用紧邻的奇数端口。比如 RTP 端口是 5004，那么 RTCP 端口就是 5005。这个约定来自早期的 RFC 规范，虽然现代协议（如 WebRTC）已经支持 RTP/RTCP 复用同一端口（RTCP-mux），但在 RTSP 等经典场景中仍然广泛使用。

### RTP 不做什么

理解 RTP 的边界和理解它能做什么同样重要。RTP **不保证**以下任何一项：

- **可靠传输**：包丢了就丢了，RTP 本身不会重传
- **有序到达**：UDP 不保证顺序，RTP 只是提供序列号让接收端自己排序
- **拥塞控制**：RTP 没有内置的拥塞控制机制，这部分职责由 RTCP 反馈和应用层共同承担

RTP 真正提供的是：**时间戳**（用于播放同步）、**序列号**（用于检测丢包和排序）、**载荷类型标识**（用于识别编码格式）以及**源标识**（用于区分不同的媒体源）。它是一个轻量的封装协议，把"媒体数据如何在网络上打包传输"这件事做好，其余交给上层处理。

## 2. RTP 报文结构详解

### 固定头部（12 字节）

RTP 报文的固定头部占 12 字节（96 比特），结构紧凑、设计精炼。每一个比特都有明确的用途：

![RTP报文结构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/rtp_header.png)

下面逐字段分析：

**V（Version，2 bit）**：RTP 版本号，当前版本固定为 2。如果收到 V 不等于 2 的包，直接丢弃。

**P（Padding，1 bit）**：填充标志。当 P=1 时，报文末尾包含若干填充字节，载荷的最后一个字节指示填充字节的总数。填充通常用于加密场景——某些加密算法要求数据长度对齐到固定块大小。

**X（Extension，1 bit）**：扩展头标志。当 X=1 时，固定头部之后紧跟一个扩展头。WebRTC 大量使用 RTP 扩展头来传递额外信息（如绝对发送时间、视频旋转角度等）。

**CC（CSRC Count，4 bit）**：CSRC 列表中的项数，范围 0~15。表示固定头部后面跟了多少个 CSRC 标识符。在混音等场景中使用，后面会详细说明。

**M（Marker，1 bit）**：标记位，含义取决于载荷类型。对于视频来说，M=1 通常表示当前包是一帧的最后一个包（一帧可能被拆成多个 RTP 包）；对于音频来说，M=1 表示一段静音后的第一个有声包。这个标记位非常重要——接收端可以据此判断一帧视频数据是否接收完整。

**PT（Payload Type，7 bit）**：载荷类型，范围 0~127。它标识了 RTP 包中承载的媒体数据的编码格式。常见的静态分配值有：

| PT 值 | 编码格式 | 类型 | 时钟频率 |
|--------|---------|------|---------|
| 0 | PCMU (G.711 μ-law) | 音频 | 8000 Hz |
| 8 | PCMA (G.711 A-law) | 音频 | 8000 Hz |
| 96-127 | 动态分配 | - | 由 SDP 协商 |

现代流媒体中最常用的编码格式（H.264、H.265、VP8、VP9、Opus、AAC）都使用动态 PT（96~127），具体值在 SDP 协商阶段确定。所以当你看到 PT=96 时，不能直接知道它是什么编码格式，必须参考对应的 SDP。

**Sequence Number（16 bit）**：序列号，每发送一个 RTP 包递增 1，初始值随机。它有两个关键作用：一是让接收端检测丢包（序列号不连续说明有包丢失），二是让接收端按序重组（UDP 不保证有序到达）。16 位意味着最大值 65535，之后会回绕到 0，接收端必须正确处理这种回绕。

**Timestamp（32 bit）**：时间戳，反映 RTP 包中第一个采样数据的采样时刻。注意，**时间戳不是墙上时钟时间**，而是基于媒体时钟频率递增的计数器。不同媒体类型的时钟频率不同——视频通常是 90000 Hz，音频根据采样率而定（如 48000 Hz、8000 Hz）。同一帧的多个 RTP 包拥有相同的时间戳。

**SSRC（Synchronization Source，32 bit）**：同步源标识符，随机生成，用于唯一标识一个 RTP 流。同一个会话中，每个媒体源（比如一个摄像头、一个麦克风）都有自己独立的 SSRC。如果两个参与者碰巧生成了相同的 SSRC，需要通过冲突解决机制来处理。

### CSRC 列表（可选）

在 SSRC 之后，如果 CC > 0，则紧跟 CC 个 CSRC（Contributing Source）标识符，每个 32 位。CSRC 的典型场景是**混音服务器（Mixer）**：当多个音频源混合成一路音频后发出时，RTP 包的 SSRC 是混音服务器的标识，而 CSRC 列表记录了所有被混合的原始音频源标识。接收端可以据此知道"这个混音包里包含了哪些人的声音"。

### 扩展头（可选）

当 X=1 时，在 CSRC 列表（或固定头部，如果 CC=0）之后紧跟一个扩展头。扩展头的结构如下：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      defined by profile       |           length              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        header extension                       |
|                             ....                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

前 16 位是 profile 自定义的标识（WebRTC 中使用 0xBEDE 表示 one-byte header extension），后 16 位的 length 表示扩展数据的长度（以 32 位字为单位，不包括这 4 字节头部本身）。WebRTC 中常见的扩展头包括 `abs-send-time`（绝对发送时间）、`transport-cc`（传输层拥塞控制序列号）等。

### 完整报文布局

把上面的内容串起来，一个完整的 RTP 报文结构如下：

```
+--------------------+
| 固定头部 (12 bytes) |
+--------------------+
| CSRC 列表 (可选)    |  CC × 4 bytes
+--------------------+
| 扩展头 (可选)       |  X=1 时存在
+--------------------+
| 载荷 (Payload)     |  实际的媒体数据
+--------------------+
| 填充 (可选)        |  P=1 时存在
+--------------------+
```

## 3. RTP 时间戳与音视频同步

### 时间戳的时钟频率

RTP 时间戳的增长速度取决于**媒体时钟频率**，不同的编码格式使用不同的时钟频率：

- **视频**：几乎所有视频编码（H.264、H.265、VP8、VP9、AV1）都使用 **90000 Hz**。这意味着每秒时间戳增加 90000。对于 30fps 的视频，每帧的时间戳增量是 90000 / 30 = 3000。
- **音频（Opus/高采样率）**：Opus 编码固定使用 **48000 Hz**。如果每帧 20ms，时间戳增量为 48000 × 0.02 = 960。
- **音频（G.711 等窄带）**：采样率 **8000 Hz**，每帧 20ms 的时间戳增量为 160。

这个设计背后有实际的考量：视频选择 90000 Hz 是因为它能被常见帧率（24、25、30、60）整除，保证时间戳增量总是整数，避免浮点精度问题。

### 音视频同步的挑战

在一个视频通话场景中，音频和视频是两路独立的 RTP 流，各自有独立的 SSRC 和独立的时间戳序列。问题来了：音频时间戳的单位是 1/48000 秒，视频时间戳的单位是 1/90000 秒，它们的初始值又是随机的，**怎么知道哪个音频帧和哪个视频帧应该同时播放**？

仅靠 RTP 时间戳无法解决这个问题——两路时间戳没有共同的参考基准。这就是 RTCP Sender Report 登场的地方。

### RTCP SR 实现唇音同步

RTCP Sender Report（SR）中携带了两个关键的时间信息：

1. **NTP 时间戳（64 bit）**：发送这个 SR 时的墙上时钟时间（NTP 格式，高 32 位是秒，低 32 位是秒的小数部分）
2. **RTP 时间戳（32 bit）**：与这个 NTP 时间戳对应的 RTP 时间戳值

音频流和视频流各自发送 SR，每个 SR 都建立了一个"NTP 时间 ↔ RTP 时间"的映射关系。接收端收到两路流的 SR 后，就可以通过 NTP 时间这个**共同基准**把两路 RTP 时间戳对齐：

![音视频同步](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/av_sync.png)

具体计算过程如下：

1. 从音频 SR 中得到映射关系：`NTP_a = f(RTP_a)`
2. 从视频 SR 中得到映射关系：`NTP_v = f(RTP_v)`
3. 对于任意一个音频帧 `rtp_a` 和视频帧 `rtp_v`，分别计算出它们对应的 NTP 时间
4. NTP 时间差即为播放时间差，如果差值超过阈值（通常 ±80ms 以上人就能感知到音画不同步），需要调整播放节奏

在实现中，接收端通常维护一个同步模块，持续根据最新的 SR 更新映射关系，并以音频播放时间线为基准（人耳对音频延迟更敏感），调整视频渲染的节奏。

## 4. RTP 载荷格式：H.264、H.265 与 AAC

### 从 RTP 头到编码数据

前面我们掌握了 RTP 头部的每一个字段，知道 Payload Type 标识了编码格式，Marker 位标识帧边界。但有一个关键问题悬而未决：**RTP 载荷（Payload）里面的数据到底长什么样？**

RTP 头部之后就是载荷区域，而载荷的内部格式完全取决于所承载的编码类型。每种主流编解码器都有对应的 RFC 定义其 RTP 打包规则——H.264 对应 RFC 6184，H.265 对应 RFC 7798，AAC 对应 RFC 3640。理解这些打包格式，是实现 RTP 收发、解封装和喂入解码器的必修课。

### H.264 RTP 打包（RFC 6184）

H.264 的编码数据由一系列 **NAL（Network Abstraction Layer）单元**组成。每个 NAL 单元有一个 1 字节的头部：

```
+---------------+
|0|1|2|3|4|5|6|7|
+-+-+-+-+-+-+-+-+
|F|NRI|  Type   |
+---------------+
```

- **F（1 bit）**：forbidden_zero_bit，正常情况下必须为 0
- **NRI（2 bit）**：nal_ref_idc，表示该 NAL 的重要性。3 表示最重要（如 SPS/PPS/IDR），0 表示可丢弃（如非参考帧的数据）
- **Type（5 bit）**：NAL 单元类型

常见的 NAL 类型：

| Type | 含义 | 说明 |
|------|------|------|
| 1 | 非 IDR 图像片段 | P 帧/B 帧的编码数据 |
| 5 | IDR 图像片段 | 关键帧，解码器刷新点 |
| 6 | SEI | 补充增强信息 |
| 7 | SPS | 序列参数集，包含分辨率/Profile 等全局信息 |
| 8 | PPS | 图像参数集，包含熵编码模式等帧级信息 |
| 24 | STAP-A | 单时间聚合包（RTP 打包专用类型） |
| 28 | FU-A | 分片单元（RTP 打包专用类型） |

Type 1-23 是 H.264 标准定义的原始 NAL 类型，Type 24-31 是 RFC 6184 为 RTP 打包扩展定义的类型。在 RTP 载荷中，**第一个字节的 Type 字段决定了这个 RTP 包的打包模式**。

#### 三种打包模式

**模式一：Single NAL Unit（单 NAL 单元包）**

最简单的模式——当一个 NAL 单元的大小不超过 MTU 限制时，直接将整个 NAL 单元（含 NAL 头）作为 RTP 载荷：

```
 RTP Header (12 bytes)
+---------------------+
| V=2|P|X|CC|M|PT|Seq |
| Timestamp           |
| SSRC                |
+---------------------+
| NAL Header (1 byte) |  ← Type = 1~23（原始 NAL 类型）
+---------------------+
| NAL 编码数据         |
| ...                 |
+---------------------+
```

对于 SPS、PPS 这类很小的参数集 NAL（通常只有几十字节），Single NAL Unit 模式非常合适。

**模式二：STAP-A（Single-Time Aggregation Packet，Type=24）**

当多个 NAL 单元属于同一时间戳（比如 SPS + PPS + SEI 通常在关键帧前一起发出），可以将它们聚合到一个 RTP 包中，减少包数量和头部开销：

```
+---------------------+
| RTP Header          |
+---------------------+
| STAP-A NAL Hdr(1B)  |  ← Type = 24
+---------------------+
| NAL 1 Size (16 bit) |
+---------------------+
| NAL 1 Data          |
+---------------------+
| NAL 2 Size (16 bit) |
+---------------------+
| NAL 2 Data          |
+---------------------+
| ...                 |
+---------------------+
```

每个被聚合的 NAL 前面有一个 2 字节的长度字段（网络字节序），指示该 NAL 的完整长度（含 NAL 头）。接收端解包时按长度逐个提取即可。

STAP-A 的典型应用场景是打包 SPS+PPS：在 RTSP 中，SDP 通常通过 `sprop-parameter-sets` 携带 Base64 编码的 SPS/PPS；而在实际 RTP 流中，编码器也会在每个 IDR 帧前通过 STAP-A 发送一次 SPS+PPS，确保解码器能随时初始化。

**模式三：FU-A（Fragmentation Unit，Type=28）**

这是实际应用中最常见的模式。当一个 NAL 单元超过网络路径 MTU 限制（通常 1500 字节减去 IP/UDP/RTP 头后约 1400 字节可用）时，必须将其拆分为多个 RTP 包发送。FU-A 就是为此设计的分片机制：

```
+---------------------+
| RTP Header          |
+---------------------+
| FU Indicator (1B)   |  ← Type = 28，F 和 NRI 来自原始 NAL
+---------------------+
| FU Header (1B)      |
+---------------------+
| FU Payload          |  ← 原始 NAL 数据的一个分片（不含 NAL 头）
| ...                 |
+---------------------+
```

**FU Indicator** 的格式与 NAL Header 完全相同，但 Type 字段固定为 28，F 和 NRI 则从原始 NAL 头复制过来。

**FU Header** 的格式：

```
+---------------+
|0|1|2|3|4|5|6|7|
+-+-+-+-+-+-+-+-+
|S|E|R|  Type   |
+---------------+
```

- **S（Start）**：为 1 表示这是第一个分片
- **E（End）**：为 1 表示这是最后一个分片
- **R（Reserved）**：保留位，必须为 0
- **Type（5 bit）**：原始 NAL 单元的类型（如 5 = IDR，1 = 非 IDR）

一个 IDR 帧的完整 FU-A 分片序列示例：

```
包 1: S=1, E=0, Type=5 (IDR)  seq=1000  ts=90000  Marker=0
包 2: S=0, E=0, Type=5 (IDR)  seq=1001  ts=90000  Marker=0
包 3: S=0, E=0, Type=5 (IDR)  seq=1002  ts=90000  Marker=0
包 4: S=0, E=1, Type=5 (IDR)  seq=1003  ts=90000  Marker=1  ← 最后一个分片
```

几个关键细节：

- 同一个 NAL 的所有分片共享**相同的 RTP 时间戳**（属于同一帧）
- 序列号**连续递增**，中间不能插入其他 NAL 的包
- 只有最后一个分片的 **RTP Marker 位置 1**，标志这一帧传输完成
- 接收端重组时，将所有分片的 FU Payload 按序拼接，再在最前面补上重构的 NAL Header（由 FU Indicator 的 F+NRI 和 FU Header 的 Type 组合而成），即可还原完整的 NAL 单元

#### C++ 解析示例

```cpp
enum class H264PacketType : uint8_t {
    kSingleNalu = 0, // Type 1-23
    kStapA      = 24,
    kFuA        = 28,
};

struct FuHeader {
    bool start;
    bool end;
    uint8_t nal_type;
};

FuHeader parse_fu_header(uint8_t byte) {
    return {
        .start    = (byte & 0x80) != 0,
        .end      = (byte & 0x40) != 0,
        .nal_type = static_cast<uint8_t>(byte & 0x1F),
    };
}

// 处理单个 RTP 包的 H.264 载荷
// nal_buffer: 跨包重组缓冲区（调用者维护，用于 FU-A 重组）
// 返回 true 表示一个完整的 NAL 单元已就绪
bool process_h264_rtp_payload(const uint8_t* payload, size_t len,
                               std::vector<uint8_t>& nal_buffer) {
    if (len < 1) return false;

    uint8_t nal_header = payload[0];
    uint8_t nal_type = nal_header & 0x1F;

    if (nal_type >= 1 && nal_type <= 23) {
        // Single NAL Unit — 整个载荷就是一个完整的 NAL
        nal_buffer.assign(payload, payload + len);
        return true;
    }

    if (nal_type == 24) {
        // STAP-A — 按长度前缀逐个提取（简化处理：只取第一个）
        size_t offset = 1;
        while (offset + 2 <= len) {
            uint16_t size = (payload[offset] << 8) | payload[offset + 1];
            offset += 2;
            if (offset + size > len) return false;
            // 每个 NAL 单元: payload[offset .. offset + size)
            // 实际应用中应逐个送入解码器或回调
            offset += size;
        }
        return true;
    }

    if (nal_type == 28) {
        // FU-A — 跨包重组
        if (len < 2) return false;
        auto fu = parse_fu_header(payload[1]);

        if (fu.start) {
            nal_buffer.clear();
            // 重构 NAL 头: F+NRI 来自 FU Indicator，Type 来自 FU Header
            uint8_t reconstructed = (nal_header & 0xE0) | fu.nal_type;
            nal_buffer.push_back(reconstructed);
        }

        // 追加分片数据（跳过 2 字节的 FU Indicator + FU Header）
        nal_buffer.insert(nal_buffer.end(), payload + 2, payload + len);

        if (fu.end) {
            return true; // 重组完成，nal_buffer 中是完整的 NAL
        }
        return false; // 等待后续分片
    }

    return false;
}
```

### H.265/HEVC RTP 打包（RFC 7798）

H.265 的 RTP 打包思路与 H.264 相似，但 NAL 单元头部从 1 字节扩展到了 **2 字节**：

```
 0                   1
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|F|    Type(6)  | LayerID | TID |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **F（1 bit）**：forbidden_zero_bit
- **Type（6 bit）**：NAL 单元类型（范围 0~63，比 H.264 的 5 位更宽）
- **LayerID（6 bit）**：层 ID，用于可伸缩视频编码（SVC/MV-HEVC），单层编码时固定为 0
- **TID（3 bit）**：时域层 ID，最小值为 1

H.265 常见 NAL 类型：

| Type | 含义 | 说明 |
|------|------|------|
| 0-9 | TRAIL 帧 | 非 IDR/CRA 的普通编码帧 |
| 19 | IDR_W_RADL | IDR 帧（可带 RADL 图像） |
| 20 | IDR_N_LP | IDR 帧（无前导图像） |
| 21 | CRA | 随机访问清除帧 |
| 32 | VPS | 视频参数集（H.265 新增） |
| 33 | SPS | 序列参数集 |
| 34 | PPS | 图像参数集 |
| 48 | AP | 聚合包（对应 H.264 的 STAP-A） |
| 49 | FU | 分片单元（对应 H.264 的 FU-A） |

#### 与 H.264 打包的关键差异

| 特性 | H.264（RFC 6184） | H.265（RFC 7798） |
|------|-------------------|-------------------|
| NAL 头大小 | 1 字节 | 2 字节 |
| 聚合包 | STAP-A（Type=24） | AP（Type=48） |
| 分片包 | FU-A（Type=28，2B 头） | FU（Type=49，3B 头） |
| 参数集 | SPS + PPS | VPS + SPS + PPS |
| 类型字段宽度 | 5 bit | 6 bit |

#### FU 分片包结构

```
+---------------------+
| RTP Header          |
+---------------------+
| PayloadHdr (2B)     |  ← Type=49，LayerID/TID 保留原始值
+---------------------+
| FU Header (1B)      |
+---------------------+
| FU Payload          |  ← 原始 NAL 数据（不含 2 字节 NAL 头）
| ...                 |
+---------------------+
```

FU Header 只有 1 字节，比 H.264 的 FU 头更紧凑：

```
+---------------+
|0|1|2|3|4|5|6|7|
+-+-+-+-+-+-+-+-+
|S|E|  FuType   |
+---------------+
```

- **S（Start）**：首个分片标志
- **E（End）**：末尾分片标志
- **FuType（6 bit）**：原始 NAL 单元类型

重组时，需要用 PayloadHdr 中的 F/LayerID/TID 与 FU Header 中的 FuType 组合，重构出原始的 2 字节 NAL 头。

#### C++ 解析示例

```cpp
struct H265NalHeader {
    uint8_t forbidden;
    uint8_t nal_type;
    uint8_t layer_id;
    uint8_t tid;
};

H265NalHeader parse_h265_nal_header(const uint8_t* data) {
    uint16_t val = (data[0] << 8) | data[1];
    return {
        .forbidden = static_cast<uint8_t>((val >> 15) & 0x01),
        .nal_type  = static_cast<uint8_t>((val >> 9) & 0x3F),
        .layer_id  = static_cast<uint8_t>((val >> 3) & 0x3F),
        .tid       = static_cast<uint8_t>(val & 0x07),
    };
}

bool process_h265_rtp_payload(const uint8_t* payload, size_t len,
                               std::vector<uint8_t>& nal_buffer) {
    if (len < 2) return false;

    auto hdr = parse_h265_nal_header(payload);

    if (hdr.nal_type <= 47) {
        // Single NAL Unit — 整个载荷就是一个完整的 NAL
        nal_buffer.assign(payload, payload + len);
        return true;
    }

    if (hdr.nal_type == 48) {
        // AP (Aggregation Packet) — 与 STAP-A 类似
        size_t offset = 2; // 跳过 2 字节 PayloadHdr
        while (offset + 2 <= len) {
            uint16_t nal_size = (payload[offset] << 8) | payload[offset + 1];
            offset += 2;
            if (offset + nal_size > len) return false;
            // 每个 NAL: payload[offset .. offset + nal_size)
            offset += nal_size;
        }
        return true;
    }

    if (hdr.nal_type == 49) {
        // FU (Fragmentation Unit)
        if (len < 3) return false;

        uint8_t fu_hdr = payload[2];
        bool start   = (fu_hdr & 0x80) != 0;
        bool end     = (fu_hdr & 0x40) != 0;
        uint8_t fu_type = fu_hdr & 0x3F;

        if (start) {
            nal_buffer.clear();
            // 重构 2 字节 NAL 头：替换 Type 字段为 fu_type
            uint8_t byte0 = (payload[0] & 0x81) | (fu_type << 1);
            nal_buffer.push_back(byte0);
            nal_buffer.push_back(payload[1]);
        }

        // 追加分片数据（跳过 3 字节的 PayloadHdr + FU Header）
        nal_buffer.insert(nal_buffer.end(), payload + 3, payload + len);

        return end; // end=true 时重组完成
    }

    return false;
}
```

### AAC RTP 打包（RFC 3640）

AAC 音频通过 **MPEG-4 Generic** RTP 载荷格式传输，SDP 中的编码名称通常标记为 `mpeg4-generic`。与视频编码的分片重组相比，AAC 的 RTP 打包要简单得多——音频帧通常很小（一帧 AAC 约几百字节），一般不需要分片。

#### 载荷结构

RFC 3640 定义的 RTP 载荷由两部分组成：**AU Header Section**（描述信息）和 **AU Data Section**（编码数据）：

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| AU-headers-length (16 bit)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| AU-header 1   | AU-header 2   | ... | pad  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| AU 1 数据      | AU 2 数据      | ...        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **AU-headers-length（16 bit）**：所有 AU Header 的总长度，单位是**比特**（不是字节）
- **AU Header**：每个 Access Unit（即一帧 AAC 编码数据）的描述
- **AU Data**：按 AU Header 描述的顺序排列的实际编码数据

#### AAC-hbr 模式

实际应用中，AAC 最常用的 RTP 打包模式是 **AAC-hbr（High Bit-Rate）**，对应 SDP 中的参数 `mode=AAC-hbr`。在这种模式下，每个 AU Header 固定为 2 字节（16 bit）：

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       AU-size (13 bit)        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  AU-Index / Delta (3 bit)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **AU-size（13 bit）**：该 Access Unit 的字节数
- **AU-Index（3 bit）**：第一个 AU 的序号（通常为 0），后续 AU 使用 AU-Index-delta 表示相对偏移

最常见的场景是**每个 RTP 包只携带一帧 AAC**，此时载荷结构非常简洁：

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| AU-headers-length = 0x0010    |  ← 16 bits（1 个 AU Header × 16 bit）
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| AU-size (13b) | AU-Index (3b) |  ← 一个 AU Header
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                               |
|         AAC 帧数据             |
|                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

#### SDP 中的 AAC 配置

AAC 的 RTP 参数通过 SDP 的 `fmtp` 行传递，理解这些参数对正确解析载荷至关重要：

```
a=rtpmap:97 mpeg4-generic/44100/2
a=fmtp:97 profile-level-id=1;mode=AAC-hbr;sizelength=13;
          indexlength=3;indexdeltalength=3;config=1210
```

关键参数含义：

| 参数 | 值 | 含义 |
|------|-----|------|
| `mode` | AAC-hbr | 高码率模式，AU Header 为 16 bit |
| `sizelength` | 13 | AU-size 字段占 13 位 |
| `indexlength` | 3 | AU-Index 字段占 3 位 |
| `config` | 1210 | AudioSpecificConfig 的十六进制编码 |

`config=1210` 解析为二进制 `0001 0010 0001 0000`：前 5 位 `00010` 表示 AAC-LC Profile，接下来 4 位 `0100` 对应采样率索引 4（即 44100 Hz），再 4 位 `0010` 表示声道数 2（立体声）。解码器（如 FFmpeg 中的 `libfdk_aac`）需要先解析这个配置值才能正确初始化。

#### C++ 解析示例

```cpp
struct AacFrame {
    const uint8_t* data;
    size_t size;
};

// 解析 AAC-hbr 模式的 RTP 载荷，提取所有 AAC 帧
std::vector<AacFrame> parse_aac_rtp_payload(const uint8_t* payload, size_t len) {
    std::vector<AacFrame> frames;
    if (len < 4) return frames; // 至少 2B AU-headers-length + 2B AU-header

    // AU-headers-length: 所有 AU header 的总位数
    uint16_t au_headers_length_bits = (payload[0] << 8) | payload[1];
    uint16_t au_headers_length_bytes = (au_headers_length_bits + 7) / 8;

    // AAC-hbr: 每个 AU header 2 字节（13-bit size + 3-bit index）
    size_t num_au = au_headers_length_bytes / 2;
    size_t header_offset = 2;  // 跳过 AU-headers-length
    size_t data_offset = 2 + au_headers_length_bytes;

    for (size_t i = 0; i < num_au && header_offset + 2 <= len; ++i) {
        uint16_t au_header = (payload[header_offset] << 8) | payload[header_offset + 1];
        uint16_t au_size = au_header >> 3;  // 高 13 位
        header_offset += 2;

        if (data_offset + au_size > len) break;

        frames.push_back({payload + data_offset, au_size});
        data_offset += au_size;
    }

    return frames;
}
```

### 载荷格式小结

三种编码的 RTP 打包格式虽然细节不同，但设计思路一致：

| 问题 | H.264 解法 | H.265 解法 | AAC 解法 |
|------|-----------|-----------|---------|
| NAL/帧太大，超过 MTU | FU-A 分片 | FU 分片 | 通常不需要（帧很小） |
| 多个小 NAL/帧合并传输 | STAP-A 聚合 | AP 聚合 | 多 AU 打包 |
| 参数集传递 | SPS/PPS via STAP-A 或 SDP | VPS/SPS/PPS via AP 或 SDP | config via SDP |
| 帧边界标识 | RTP Marker bit | RTP Marker bit | 每包即一帧 |

在实际开发中，接收端解析 RTP 载荷的核心流程是：**先看第一个字节（或两个字节）判断打包类型，再按对应格式提取或重组原始编码数据，最后送入解码器**。

## 5. RTCP 协议详解

### RTCP 的角色

如果说 RTP 负责"运货"，那么 RTCP 就负责"报路况"。RTCP 是 RTP 的伴侣协议，提供以下核心功能：

- **传输质量反馈**：丢包率、抖动、往返时延（RTT）
- **音视频同步**：通过 SR 中的 NTP/RTP 时间戳映射
- **成员管理**：参与者加入、离开的通知
- **源描述**：参与者的 CNAME 等标识信息

### 带宽限制

RTCP 有一个重要的设计约束：**RTCP 流量不应超过会话总带宽的 5%**。这是为了防止控制消息抢占数据传输的带宽。在一个 2 Mbps 的视频会话中，RTCP 最多只能使用 100 Kbps。

RTCP 包的发送间隔也是动态计算的：参与者越多，每个参与者发送 RTCP 的间隔就越长，以保持总 RTCP 带宽不超标。对于典型的两方通话，RTCP 发送间隔通常在 1~5 秒之间。

### 五种基本报文类型

![RTCP报文类型](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/rtcp_packets.png)

RTCP 定义了五种基本报文类型，每种都有特定的 Payload Type 编号：

#### SR（Sender Report，PT=200）

发送端定期发送 SR，包含以下关键信息：

- **NTP 时间戳（64 bit）**：发送 SR 时的墙上时钟
- **RTP 时间戳（32 bit）**：与 NTP 时间戳对应的 RTP 时间
- **发送统计**：已发送的 RTP 包数量、已发送的字节数

SR 的两大用途：一是为音视频同步提供时间基准（上文已详述），二是让接收端了解发送端的发送速率，用于带宽估计。

#### RR（Receiver Report，PT=201）

接收端定期发送 RR，报告每个接收到的 RTP 流的质量统计：

- **丢包分数（8 bit）**：上一个 RR 间隔内的丢包率，255 表示 100%
- **累计丢包数（24 bit）**：自会话开始以来的总丢包数
- **最高序列号（32 bit）**：收到的最大扩展序列号
- **抖动（32 bit）**：包间到达时间的统计方差
- **LSR（32 bit）**：最后一次收到的 SR 的 NTP 时间戳中间 32 位
- **DLSR（32 bit）**：从收到上一次 SR 到发送本次 RR 的延迟

RR 中的信息对发送端至关重要。发送端可以据此判断网络状况：丢包率升高说明需要降低码率或开启 FEC，抖动增大说明需要建议接收端增大 Jitter Buffer。此外，发送端可以通过 LSR 和 DLSR 计算出往返时延 RTT：

```
RTT = 当前时间 - LSR - DLSR
```

#### SDES（Source Description，PT=202）

SDES 携带源的描述信息，最重要的是 **CNAME（Canonical Name）**。CNAME 在整个会话中保持不变，即使 SSRC 因冲突而改变，接收端仍然可以通过 CNAME 识别出同一个参与者。音视频同步也依赖 CNAME——来自同一参与者的音频和视频流拥有相同的 CNAME，接收端据此知道这两路流需要同步播放。

#### BYE（PT=203）

参与者离开会话时发送 BYE 包。收到 BYE 后，其他参与者可以清理与该 SSRC 关联的资源。BYE 包可以携带一个可选的原因字符串（如 "user left"）。

#### APP（Application Defined，PT=204）

应用自定义包，允许应用在 RTCP 通道上传递私有数据。包含一个 4 字节的名字标识和任意长度的应用数据。在 WebRTC 中使用较少，但某些私有系统会用它来传递自定义的控制信息。

### RTCP 复合包

一个重要的细节：RTCP 通常以**复合包（Compound Packet）**的形式发送，即多个 RTCP 包拼接在一个 UDP 数据报中。RFC 规定复合包的第一个包必须是 SR 或 RR，第二个包必须是 SDES（至少包含 CNAME）。这样即使只收到一个 UDP 包，接收端也能获得完整的质量反馈和源标识信息。

## 6. C++ 实战：RTP 包解析器

理论讲了很多，现在用 C++ 来实现一个完整的 RTP 包解析器。这个程序可以通过 UDP Socket 接收 RTP 流，解析头部字段并打印关键信息。

### RTP 头部结构定义

首先定义 RTP 头部的结构体。这里需要特别注意**字节序问题**——RTP 使用网络字节序（大端），而大多数 x86 机器是小端的。

```cpp
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <stdexcept>
#include <arpa/inet.h>

struct RtpHeader {
    uint8_t cc : 4;
    uint8_t extension : 1;
    uint8_t padding : 1;
    uint8_t version : 2;

    uint8_t payload_type : 7;
    uint8_t marker : 1;

    uint16_t sequence_number;
    uint32_t timestamp;
    uint32_t ssrc;
};

static_assert(sizeof(RtpHeader) == 12, "RtpHeader must be 12 bytes");
```

这里的位域布局和结构体成员顺序适用于小端机器（x86/x64）。在小端系统上，编译器按从 LSB 到 MSB 的顺序排列位域——第一个字节的低 4 位是 CC，然后依次是 X、P、V。这恰好对应 RTP 头第一个字节在网络字节序下的布局经过小端翻转后的结果。

### 完整的 RTP 包解析器

```cpp
#include <iostream>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <array>
#include <stdexcept>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

struct RtpHeader {
    uint8_t cc : 4;
    uint8_t extension : 1;
    uint8_t padding : 1;
    uint8_t version : 2;

    uint8_t payload_type : 7;
    uint8_t marker : 1;

    uint16_t sequence_number;
    uint32_t timestamp;
    uint32_t ssrc;
};

static_assert(sizeof(RtpHeader) == 12, "RtpHeader must be 12 bytes");

struct RtpPacket {
    uint8_t version;
    bool padding;
    bool extension;
    uint8_t cc;
    bool marker;
    uint8_t payload_type;
    uint16_t seq_number;
    uint32_t timestamp;
    uint32_t ssrc;
    std::vector<uint32_t> csrc_list;

    uint16_t ext_profile;
    std::vector<uint8_t> ext_data;

    const uint8_t* payload;
    size_t payload_size;
};

class RtpParser {
public:
    static bool parse(const uint8_t* data, size_t len, RtpPacket& pkt) {
        if (len < sizeof(RtpHeader)) {
            return false;
        }

        const auto* hdr = reinterpret_cast<const RtpHeader*>(data);

        if (hdr->version != 2) {
            return false;
        }

        pkt.version = hdr->version;
        pkt.padding = hdr->padding;
        pkt.extension = hdr->extension;
        pkt.cc = hdr->cc;
        pkt.marker = hdr->marker;
        pkt.payload_type = hdr->payload_type;
        pkt.seq_number = ntohs(hdr->sequence_number);
        pkt.timestamp = ntohl(hdr->timestamp);
        pkt.ssrc = ntohl(hdr->ssrc);

        size_t offset = sizeof(RtpHeader);

        // CSRC 列表
        if (pkt.cc > 0) {
            size_t csrc_bytes = pkt.cc * 4;
            if (offset + csrc_bytes > len) return false;

            pkt.csrc_list.resize(pkt.cc);
            for (int i = 0; i < pkt.cc; ++i) {
                uint32_t csrc;
                std::memcpy(&csrc, data + offset + i * 4, 4);
                pkt.csrc_list[i] = ntohl(csrc);
            }
            offset += csrc_bytes;
        }

        // 扩展头
        if (pkt.extension) {
            if (offset + 4 > len) return false;

            uint16_t ext_profile, ext_length;
            std::memcpy(&ext_profile, data + offset, 2);
            std::memcpy(&ext_length, data + offset + 2, 2);
            pkt.ext_profile = ntohs(ext_profile);
            ext_length = ntohs(ext_length);

            offset += 4;
            size_t ext_bytes = ext_length * 4;
            if (offset + ext_bytes > len) return false;

            pkt.ext_data.assign(data + offset, data + offset + ext_bytes);
            offset += ext_bytes;
        }

        // 处理填充
        size_t padding_bytes = 0;
        if (pkt.padding) {
            if (len == offset) return false;
            padding_bytes = data[len - 1];
            if (padding_bytes == 0 || offset + padding_bytes > len) return false;
        }

        pkt.payload = data + offset;
        pkt.payload_size = len - offset - padding_bytes;
        return true;
    }
};

class RtpReceiver {
public:
    explicit RtpReceiver(uint16_t port) : port_(port), sockfd_(-1) {}

    ~RtpReceiver() {
        if (sockfd_ >= 0) close(sockfd_);
    }

    void start() {
        sockfd_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (sockfd_ < 0) {
            throw std::runtime_error("socket creation failed");
        }

        int reuse = 1;
        setsockopt(sockfd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_ANY);
        addr.sin_port = htons(port_);

        if (bind(sockfd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
            throw std::runtime_error("bind failed on port " + std::to_string(port_));
        }

        std::cout << "Listening for RTP packets on port " << port_ << "...\n\n";
        receive_loop();
    }

private:
    void receive_loop() {
        std::array<uint8_t, 65536> buffer{};
        uint32_t packet_count = 0;

        while (true) {
            sockaddr_in sender_addr{};
            socklen_t addr_len = sizeof(sender_addr);

            ssize_t n = recvfrom(sockfd_, buffer.data(), buffer.size(), 0,
                                 reinterpret_cast<sockaddr*>(&sender_addr),
                                 &addr_len);
            if (n <= 0) continue;

            RtpPacket pkt{};
            if (!RtpParser::parse(buffer.data(), static_cast<size_t>(n), pkt)) {
                std::cerr << "Failed to parse RTP packet (size=" << n << ")\n";
                continue;
            }

            ++packet_count;
            print_packet(pkt, packet_count, static_cast<size_t>(n));
        }
    }

    static void print_packet(const RtpPacket& pkt, uint32_t count, size_t raw_size) {
        std::cout << "[#" << count << "] "
                  << "seq=" << pkt.seq_number
                  << " ts=" << pkt.timestamp
                  << " pt=" << static_cast<int>(pkt.payload_type)
                  << " ssrc=0x" << std::hex << pkt.ssrc << std::dec
                  << " marker=" << pkt.marker
                  << " payload=" << pkt.payload_size << "B"
                  << " total=" << raw_size << "B";
        if (pkt.extension) {
            std::cout << " ext_profile=0x" << std::hex << pkt.ext_profile
                      << std::dec << " ext_size=" << pkt.ext_data.size() << "B";
        }
        std::cout << "\n";
    }

    uint16_t port_;
    int sockfd_;
};

int main(int argc, char* argv[]) {
    uint16_t port = 5004;
    if (argc > 1) {
        port = static_cast<uint16_t>(std::stoi(argv[1]));
    }

    try {
        RtpReceiver receiver(port);
        receiver.start();
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
```

### 编译与测试

编译这个程序不需要任何外部依赖：

```bash
g++ -std=c++17 -O2 -Wall -o rtp_receiver rtp_receiver.cpp
```

启动接收端后，可以用 FFmpeg 向它推送 RTP 流来测试：

```bash
# 终端 1：启动 RTP 接收器
./rtp_receiver 5004

# 终端 2：用 FFmpeg 推送 RTP 流
ffmpeg -re -f lavfi -i testsrc=size=640x480:rate=30 \
       -c:v libx264 -profile:v baseline -tune zerolatency \
       -f rtp rtp://127.0.0.1:5004
```

FFmpeg 启动后会输出 SDP 信息，接收端则会持续打印解析出的 RTP 包信息：

```
Listening for RTP packets on port 5004...

[#1] seq=12345 ts=0 pt=96 ssrc=0xa1b2c3d4 marker=1 payload=1200B total=1212B
[#2] seq=12346 ts=3000 pt=96 ssrc=0xa1b2c3d4 marker=0 payload=1400B total=1412B
[#3] seq=12347 ts=3000 pt=96 ssrc=0xa1b2c3d4 marker=1 payload=800B total=812B
...
```

从输出中可以看到：相同时间戳的包属于同一帧，marker=1 的包是该帧的最后一个分片，时间戳增量 3000 对应 30fps（90000 / 30 = 3000）。

### RTP 包构造

除了解析，有时也需要构造 RTP 包（比如自己实现推流端）。下面是一个 RTP 包构造器：

```cpp
class RtpBuilder {
public:
    RtpBuilder(uint8_t payload_type, uint32_t ssrc)
        : pt_(payload_type), ssrc_(ssrc),
          seq_(static_cast<uint16_t>(rand())),
          timestamp_(static_cast<uint32_t>(rand())) {}

    std::vector<uint8_t> build(const uint8_t* payload, size_t payload_len,
                                uint32_t ts_increment, bool marker) {
        std::vector<uint8_t> packet(sizeof(RtpHeader) + payload_len);

        auto* hdr = reinterpret_cast<RtpHeader*>(packet.data());
        hdr->version = 2;
        hdr->padding = 0;
        hdr->extension = 0;
        hdr->cc = 0;
        hdr->marker = marker ? 1 : 0;
        hdr->payload_type = pt_;
        hdr->sequence_number = htons(seq_++);

        timestamp_ += ts_increment;
        hdr->timestamp = htonl(timestamp_);
        hdr->ssrc = htonl(ssrc_);

        std::memcpy(packet.data() + sizeof(RtpHeader), payload, payload_len);
        return packet;
    }

private:
    uint8_t pt_;
    uint32_t ssrc_;
    uint16_t seq_;
    uint32_t timestamp_;
};
```

## 7. 踩坑与调优

### 序列号回绕处理

RTP 序列号是 16 位的，最大值 65535，之后回绕到 0。在计算两个序列号的差值或判断先后顺序时，不能简单做减法，需要处理回绕：

```cpp
int16_t seq_diff(uint16_t a, uint16_t b) {
    return static_cast<int16_t>(a - b);
}

bool seq_newer_than(uint16_t a, uint16_t b) {
    return seq_diff(a, b) > 0;
}
```

这个技巧利用了无符号整数溢出的定义行为和有符号强制转换：当 `a=0, b=65535` 时，`a - b` 的无符号结果是 1（回绕），转成 `int16_t` 后值为 1，正确表示 a 比 b 更新。相反，当 `a=65535, b=0` 时，结果是 -1，表示 a 比 b 更旧。这个方法在序列号差值不超过 32767 时都能正确工作，对于正常的 RTP 流绰绰有余。

### SSRC 冲突检测

虽然 SSRC 是 32 位随机值，冲突概率很低，但在大规模会议场景下仍然可能发生。RFC 3550 定义了冲突检测和解决机制：

1. 收到一个 RTP 包，其 SSRC 与已知源相同但来源 IP/端口不同
2. 这可能是冲突，也可能是路由变化，需要等待后续包确认
3. 如果确认是冲突，本地源需要生成新的 SSRC 并发送 BYE 通知旧 SSRC

在实现中，维护一个 SSRC → (IP, Port) 的映射表即可做基本的冲突检测：

```cpp
#include <unordered_map>
#include <cstdint>

struct SourceInfo {
    uint32_t ip;
    uint16_t port;
    uint32_t packet_count;
};

class SsrcTracker {
public:
    enum class Result { kOk, kNew, kConflict };

    Result on_packet(uint32_t ssrc, uint32_t ip, uint16_t port) {
        auto it = sources_.find(ssrc);
        if (it == sources_.end()) {
            sources_[ssrc] = {ip, port, 1};
            return Result::kNew;
        }

        auto& info = it->second;
        if (info.ip != ip || info.port != port) {
            return Result::kConflict;
        }

        info.packet_count++;
        return Result::kOk;
    }

private:
    std::unordered_map<uint32_t, SourceInfo> sources_;
};
```

### 大端/小端字节序

RTP 中所有多字节字段（Sequence Number、Timestamp、SSRC）都使用**网络字节序（大端）**。在解析时必须用 `ntohs()` / `ntohl()` 转换，构造时用 `htons()` / `htonl()` 转换。这是前面代码中你看到大量 `ntohl` 调用的原因。

一个容易踩坑的地方是位域的字节序。C/C++ 标准明确指出，位域在存储单元内的分配方向（从高位到低位，还是从低位到高位）是 **implementation-defined** 的。实践中，编译器的选择与平台字节序挂钩：小端平台从 LSB 开始分配，大端平台从 MSB 开始分配。

以前面 `RtpHeader` 的第一个字节为例，RTP 头在网线上的比特布局是：

```
  bit7  bit6  bit5  bit4  bit3  bit2  bit1  bit0
  [ Version ][ P  ][ X  ][        CC          ]
```

在小端平台（x86/x64）上，位域从 LSB 开始分配，第一个声明的 `cc:4` 占 bit[3:0]，最后声明的 `version:2` 占 bit[7:6]——恰好与网线布局一致，解析正确。

但在大端平台（PowerPC、SPARC 等）上，位域从 MSB 开始分配，第一个声明的 `cc:4` 会占据 bit[7:4]，`version:2` 则落到 bit[1:0]——整个字节的字段映射完全反转，version 读到的实际上是 cc 的值：

```
小端平台: [ver(2) | pad(1) | ext(1) | cc(4) ]  ✓ 匹配网线布局
大端平台: [cc(4)  | ext(1) | pad(1) | ver(2)]  ✗ 完全反转
```

这就是为什么前面 `RtpHeader` 结构体的位域布局仅适用于小端平台。如果需要同时支持大端平台，可以像 Linux 内核中 IP 头的做法一样，用 `#if __BYTE_ORDER == __LITTLE_ENDIAN` 条件编译来反转位域声明顺序。但更稳健的方式是彻底不用位域，而是手动通过位运算提取各字段：

```cpp
struct RtpFields {
    uint8_t version;
    bool padding;
    bool extension;
    uint8_t cc;
    bool marker;
    uint8_t payload_type;
    uint16_t seq_number;
    uint32_t timestamp;
    uint32_t ssrc;
};

bool parse_rtp_portable(const uint8_t* data, size_t len, RtpFields& f) {
    if (len < 12) return false;

    f.version    = (data[0] >> 6) & 0x03;
    f.padding    = (data[0] >> 5) & 0x01;
    f.extension  = (data[0] >> 4) & 0x01;
    f.cc         = data[0] & 0x0F;
    f.marker     = (data[1] >> 7) & 0x01;
    f.payload_type = data[1] & 0x7F;

    uint16_t seq;
    uint32_t ts, ssrc;
    std::memcpy(&seq, data + 2, 2);
    std::memcpy(&ts, data + 4, 4);
    std::memcpy(&ssrc, data + 8, 4);

    f.seq_number = ntohs(seq);
    f.timestamp  = ntohl(ts);
    f.ssrc       = ntohl(ssrc);
    return f.version == 2;
}
```

这种方式完全不依赖位域分配方向，在任何平台上都能正确工作。核心原因是：所有操作都在单字节（`uint8_t`）的**值域**上进行——`data[0] >> 6` 在任何平台上都是取该字节值的最高 2 位，不涉及"位域在内存中如何排列"的问题。而多字节字段（`seq`、`ts`、`ssrc`）则通过 `ntohs()`/`ntohl()` 显式处理字节序。在需要考虑可移植性的项目中，推荐使用这种方法。

### RTP 扩展头的处理

在 WebRTC 场景中，RTP 扩展头承载了很多重要信息。最常见的是 one-byte header 格式（profile=0xBEDE），每个扩展元素的结构是：

```
 0                   
 0 1 2 3 4 5 6 7 
+-+-+-+-+-+-+-+-+
|  ID   |  len  |
+-+-+-+-+-+-+-+-+
```

ID（4 bit）标识扩展的类型，len（4 bit）表示数据长度减 1（即 len=0 表示 1 字节数据）。ID=0 表示填充，ID=15 表示结束。

解析 one-byte header extension 的代码：

```cpp
struct RtpExtElement {
    uint8_t id;
    std::vector<uint8_t> data;
};

std::vector<RtpExtElement> parse_one_byte_extensions(const uint8_t* data, size_t len) {
    std::vector<RtpExtElement> elements;
    size_t pos = 0;

    while (pos < len) {
        uint8_t byte = data[pos];
        if (byte == 0) { // 填充
            pos++;
            continue;
        }

        uint8_t id = (byte >> 4) & 0x0F;
        if (id == 15) break; // 终止标记

        uint8_t data_len = (byte & 0x0F) + 1;
        pos++;

        if (pos + data_len > len) break;

        RtpExtElement elem;
        elem.id = id;
        elem.data.assign(data + pos, data + pos + data_len);
        elements.push_back(std::move(elem));
        pos += data_len;
    }

    return elements;
}
```

## 总结

本文从协议设计到 C++ 实现，系统地剖析了 RTP/RTCP 协议：

- **RTP 报文结构**：12 字节固定头部中的每一个比特都有明确用途，V/P/X/CC/M/PT 控制报文格式，序列号检测丢包和排序，时间戳驱动播放同步，SSRC 标识媒体源
- **时间戳与同步**：不同媒体类型使用不同的时钟频率（视频 90000Hz，音频按采样率），音视频同步依赖 RTCP SR 中的 NTP 时间戳建立共同基准
- **RTP 载荷格式**：H.264 通过 FU-A 分片和 STAP-A 聚合解决 NAL 打包问题，H.265 扩展为 2 字节 NAL 头并使用 FU/AP 机制，AAC 在 AAC-hbr 模式下通过 AU Header 描述每帧大小
- **RTCP 反馈机制**：SR 提供发送端统计和同步信息，RR 提供接收端质量反馈（丢包率、抖动、RTT），SDES 绑定 CNAME 与 SSRC 的关系
- **实战要点**：字节序转换是必修课，序列号回绕处理用 int16_t 差值法，跨平台场景避免使用位域

RTP/RTCP 是后续所有流媒体协议学习的基础。在 RTSP 中，RTP 承载媒体数据，RTCP 提供同步和反馈；在 WebRTC 中，RTP/RTCP 的扩展机制（如 transport-cc、REMB、NACK）构成了拥塞控制和丢包恢复的核心。

下一篇我们将进入 **SDP 与媒体协商机制**——当你已经知道 RTP 包里的 PT=96 时，你需要靠 SDP 来知道它到底是 H.264 还是 VP8，以及使用什么采样率、什么 profile。SDP 正是连接"协商"与"传输"之间的桥梁。
