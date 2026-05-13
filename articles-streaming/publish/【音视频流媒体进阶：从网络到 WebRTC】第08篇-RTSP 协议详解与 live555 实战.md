# RTSP 协议详解与 live555 实战

## 前言

如果你接触过 IP 摄像头、安防监控或者视频点播系统，那你几乎一定见过 `rtsp://` 开头的 URL。RTSP（Real Time Streaming Protocol）是这些场景中最常见的流媒体协议，至今仍然是安防领域的事实标准。

理解 RTSP 有一个关键的类比：**RTSP 是网络上的遥控器**。你用遥控器控制电视播放、暂停、停止，但视频信号并不是通过遥控器传输的。同理，RTSP 只负责控制媒体的播放状态——告诉服务器"开始播"、"暂停"、"停止"——而真正的音视频数据通过 RTP 协议传输。RTSP 管信令，RTP 管数据，两者各司其职。

本文目标：掌握 RTSP 协议的完整交互流程，理解每个方法的报文格式和语义，然后用 live555 这个经典的 C++ 开源库搭建一个实际可用的 RTSP 点播服务器。

## 1. RTSP 协议概述

### RTSP 的定位

RTSP 定义在 RFC 2326（1998 年发布，后由 RFC 7826 更新为 RTSP 2.0），它是一个**应用层信令控制协议**，运行在 TCP 之上（默认端口 554）。RTSP 的职责是建立和控制媒体会话，而不是传输媒体数据本身。

在整个协议栈中，RTSP 的位置如下：

- **RTSP**：信令控制（DESCRIBE、SETUP、PLAY、TEARDOWN 等）
- **SDP**：媒体描述（编码格式、采样率、RTP payload type 等）
- **RTP**：媒体数据传输（音频帧、视频帧）
- **RTCP**：传输质量反馈（丢包率、抖动、SR/RR 报告）

![RTSP协议栈](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/rtsp_stack.png)

### RTSP 与 HTTP 的异同

RTSP 在设计上大量借鉴了 HTTP，两者有很多相似之处，也有关键差异：

| 特性 | HTTP | RTSP |
|------|------|------|
| 文本协议 | 是 | 是 |
| 请求/响应模型 | 是 | 是 |
| 状态 | 无状态 | **有状态**（Session） |
| 方向 | 客户端 → 服务器 | 双向（服务器可发请求） |
| 默认端口 | 80/443 | 554 |
| 数据传输 | 自身承载 | 通常由 RTP 承载 |
| 连接复用 | HTTP/1.1 Keep-Alive | 天然持久连接 |

最本质的差异在于**有状态**。HTTP 的每个请求都是独立的，服务器不需要记住之前发生了什么。而 RTSP 维护一个会话（Session），从 SETUP 建立到 TEARDOWN 销毁，整个生命周期内服务器持续跟踪会话状态——当前是播放中还是暂停，客户端的传输参数是什么，RTP 端口是哪个。这个有状态的特性也是 RTSP 实现复杂度高于 HTTP 的根本原因。

### RTSP URL 格式

RTSP URL 遵循标准的 URI 格式：

```
rtsp://host[:port]/path[?query]
```

几个典型的例子：

```
rtsp://192.168.1.100/live/camera1          # IP 摄像头实时流
rtsp://192.168.1.100:8554/vod/movie.264    # 点播服务（自定义端口）
rtsp://admin:pass@10.0.0.1/stream1         # 带认证信息
```

端口号默认是 554，如果省略则使用默认值。路径部分由服务器自行定义，没有统一的标准——不同厂商的 IP 摄像头路径格式千差万别，这也是安防集成中经常遇到的麻烦。

## 2. RTSP 核心方法详解

RTSP 定义了一组方法（Method），覆盖了从查询能力到控制播放的完整流程。一个典型的 RTSP 会话从 OPTIONS 开始，经过 DESCRIBE → SETUP → PLAY，最终以 TEARDOWN 结束。

![RTSP交互时序](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/rtsp_sequence.png)

### OPTIONS

OPTIONS 用于查询服务器支持哪些方法。这通常是客户端发出的第一个请求，同时也常被用作心跳保活。

**请求：**

```
OPTIONS rtsp://192.168.1.100:8554/stream RTSP/1.0
CSeq: 1
User-Agent: VLC/3.0.18
```

**响应：**

```
RTSP/1.0 200 OK
CSeq: 1
Public: OPTIONS, DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE
```

`CSeq` 是序列号，每个请求递增，响应中回显相同的值，用于匹配请求和响应。`Public` 头列出服务器支持的所有方法。

### DESCRIBE

DESCRIBE 请求服务器返回媒体资源的描述信息。服务器通常以 SDP（Session Description Protocol）格式响应，其中包含了音视频的编码参数、RTP 封装格式等关键信息。

**请求：**

```
DESCRIBE rtsp://192.168.1.100:8554/stream RTSP/1.0
CSeq: 2
Accept: application/sdp
```

**响应：**

```
RTSP/1.0 200 OK
CSeq: 2
Content-Type: application/sdp
Content-Length: 362

v=0
o=- 1234567890 1 IN IP4 192.168.1.100
s=H.264 Video Stream
t=0 0
a=tool:live555
a=type:broadcast
a=control:*
m=video 0 RTP/AVP 96
c=IN IP4 0.0.0.0
a=rtpmap:96 H264/90000
a=fmtp:96 packetization-mode=1;profile-level-id=640028;sprop-parameter-sets=Z2QAKKzZQLQ9+X5CAAADAAIAAAMAPCAs,aOvjyyLA
a=control:track1
m=audio 0 RTP/AVP 97
c=IN IP4 0.0.0.0
a=rtpmap:97 MPEG4-GENERIC/44100/2
a=fmtp:97 streamtype=5;profile-level-id=1;mode=AAC-hbr;sizelength=13;indexlength=3;indexdeltalength=3;config=1210
a=control:track2
```

SDP 中的关键信息：`m=video` 行描述视频流，payload type 96 对应 H.264；`m=audio` 行描述音频流，payload type 97 对应 AAC。`a=control` 指定了每个轨道的控制路径，后续 SETUP 会用到。如果你对 SDP 格式还不熟悉，可以回顾前面关于 SDP 与媒体协商的文章。

### SETUP

SETUP 为指定的媒体轨道建立传输通道。客户端在 `Transport` 头中告诉服务器自己期望的传输方式（UDP 还是 TCP interleaved）和端口，服务器确认并返回实际使用的参数和会话 ID。

**请求（UDP 方式）：**

```
SETUP rtsp://192.168.1.100:8554/stream/track1 RTSP/1.0
CSeq: 3
Transport: RTP/AVP;unicast;client_port=50000-50001
```

Transport 头的格式是 `transport/profile/lower-transport`。这里 `RTP/AVP` 实际上是 `RTP/AVP/UDP` 的简写——RFC 2326 规定当底层传输协议省略时默认为 UDP。如果要使用 TCP，则必须显式写成 `RTP/AVP/TCP`（详见后文"RTSP 传输方式"一节）。

**响应：**

```
RTSP/1.0 200 OK
CSeq: 3
Session: 12345678;timeout=60
Transport: RTP/AVP;unicast;client_port=50000-50001;server_port=6970-6971;ssrc=1A2B3C4D
```

Transport 响应中各参数的含义：

- `client_port=50000-50001`：回显客户端请求的端口——50000 接收 RTP 数据，50001 收发 RTCP
- `server_port=6970-6971`：服务器侧的端口——6970 是 RTP 数据的发送源端口，6971 是 RTCP 的收发端口。客户端可以据此校验收到的 UDP 包来源是否合法，也需要向 6971 端口发送 RTCP RR（接收报告）
- `ssrc=1A2B3C4D`：服务器为该 RTP 流分配的同步源标识符

整个 UDP 传输的端口映射关系：

```
客户端                          服务器
50000 (RTP 接收)  ◄──────────  6970 (RTP 发送)
50001 (RTCP 收发) ◄──────────► 6971 (RTCP 收发)
```

`Session` 头是服务器分配的会话标识，后续所有请求都必须携带它。`timeout=60` 表示 60 秒没有活动则会话超时。

每个媒体轨道需要单独 SETUP。对于同时包含音视频的流，需要发两次 SETUP——一次为视频轨道，一次为音频轨道。

### PLAY

PLAY 通知服务器开始发送 RTP 数据。可以通过 `Range` 头指定播放起始位置（点播场景）。

**请求：**

```
PLAY rtsp://192.168.1.100:8554/stream RTSP/1.0
CSeq: 5
Session: 12345678
Range: npt=0.000-
```

**响应：**

```
RTSP/1.0 200 OK
CSeq: 5
Session: 12345678
Range: npt=0.000-
RTP-Info: url=track1;seq=12345;rtptime=0,url=track2;seq=54321;rtptime=0
```

`Range: npt=0.000-` 表示从起始位置播放到结束。`RTP-Info` 头告诉客户端每个轨道的初始序列号和 RTP 时间戳，客户端据此进行同步。

收到 200 OK 后，服务器开始通过 RTP 发送音视频数据。

### PAUSE

PAUSE 暂停媒体发送，但不释放会话和传输资源。客户端后续可以发 PLAY 继续播放。

**请求：**

```
PAUSE rtsp://192.168.1.100:8554/stream RTSP/1.0
CSeq: 6
Session: 12345678
```

**响应：**

```
RTSP/1.0 200 OK
CSeq: 6
Session: 12345678
```

### TEARDOWN

TEARDOWN 终止会话，服务器释放所有相关资源（RTP/RTCP 端口、编码器上下文等）。

**请求：**

```
TEARDOWN rtsp://192.168.1.100:8554/stream RTSP/1.0
CSeq: 7
Session: 12345678
```

**响应：**

```
RTSP/1.0 200 OK
CSeq: 7
```

会话结束后，如果客户端想重新观看，需要从 DESCRIBE 或 SETUP 重新开始。

## 3. RTSP 传输方式

RTSP 本身不传输媒体数据，但它负责协商数据的传输方式。两种主流方式各有优劣。

### RTP over UDP

这是最常见也是默认的传输方式。RTP 数据通过独立的 UDP 端口传输，RTCP 使用相邻端口进行质量反馈。

**优势：**
- 延迟最低，UDP 没有重传和拥塞控制的开销
- 服务器和客户端的实现最简单

**劣势：**
- NAT/防火墙穿透困难——客户端在 NAT 后面时，服务器的 UDP 包可能到达不了（下文详述原因）
- 丢包需要应用层自行处理

SETUP 中的 Transport 头格式：

```
Transport: RTP/AVP;unicast;client_port=50000-50001
```

`RTP/AVP` 表示 RTP over UDP（AVP 是 Audio Video Profile 的缩写），`unicast` 表示单播，`client_port` 指定 RTP 和 RTCP 的接收端口。

### RTP over TCP（Interleaved）

当 UDP 不可用时（NAT 穿透失败、防火墙封锁 UDP），可以退回到 TCP interleaved 模式。此模式下 RTP/RTCP 数据直接复用 RTSP 的 TCP 连接传输，不需要额外打开端口。

SETUP 请求：

```
Transport: RTP/AVP/TCP;unicast;interleaved=0-1
```

`interleaved=0-1` 表示 RTP 数据使用 channel 0，RTCP 使用 channel 1。如果有音频轨道，通常是 `interleaved=2-3`。

TCP interleaved 模式下，RTP 数据被封装在一个特殊的帧头中，通过 RTSP TCP 连接发送：

```
+----+--------+--------+--------+--------+...+--------+
| $  | channel| length (2 bytes) |  RTP data payload   |
+----+--------+--------+--------+--------+...+--------+
```

- `$`（0x24）：魔术字节，标识这是一个 interleaved 数据帧而非 RTSP 文本消息
- `channel`：1 字节，标识数据属于哪个通道（对应 SETUP 中 interleaved 的值）
- `length`：2 字节（网络字节序），后续 RTP 数据的长度
- 其后紧跟完整的 RTP 包

这个设计使得 RTSP 文本消息和 RTP 二进制数据可以在同一个 TCP 连接上交错传输，接收端通过第一个字节是 `$` 还是 `R`（RTSP 响应以 `RTSP/1.0` 开头）来区分。

### 为什么 UDP 过不了 NAT 而 TCP interleaved 可以

这是一个值得展开说明的问题。RTSP 信令本身走 TCP，客户端主动连接服务器，NAT 网关会为这条出站连接创建映射记录，后续的双向数据都能正常通过。但 SETUP 之后，RTP 数据要走**独立的 UDP 端口**，问题就出现了：

```
客户端（NAT 内网）                     NAT 网关                 服务器（公网）

[TCP] ──── RTSP SETUP ─────────────────────────────► [TCP:554]   ✓ 主动出站，NAT 放行
      client_port=50000-50001

[UDP:50000] ◄── RTP 数据 ──────── ✗ NAT 丢弃 ─────── [UDP:6970]  ✗ 外部主动入站，无映射记录
```

服务器往客户端的 UDP 50000 端口发 RTP 包时，NAT 网关发现这是一个从外部发起的 UDP 包，而客户端从未通过 50000 端口向服务器发过任何数据，NAT 上没有这条映射记录，直接丢弃。

TCP interleaved 模式则完全绕开了这个问题——RTP 数据直接复用已经建好的 RTSP TCP 连接：

```
客户端（NAT 内网）                     NAT 网关                 服务器（公网）

[TCP] ──── RTSP 信令 ──────────────────────────────► [TCP:554]   ✓ 客户端主动建立
[TCP] ◄─── RTP 数据（$ 帧头）──────────────────────── [TCP:554]   ✓ 同一条连接，NAT 已放行
```

这条 TCP 连接是客户端主动建立的，NAT 早已创建了映射。后续所有数据——RTSP 文本消息和 `$` 开头的 RTP 二进制帧——都在这条连接上双向流动，不需要打开任何新端口或新连接，NAT 自然不会拦截。严格来说，TCP interleaved 不是"穿透"了 NAT，而是**根本不需要穿透**。

### 两种方式对比

| 特性 | RTP over UDP | RTP over TCP (interleaved) |
|------|-------------|---------------------------|
| 延迟 | 低 | 较高（TCP 重传开销） |
| 可靠性 | 可能丢包 | 可靠传输 |
| NAT 穿透 | 困难 | 无问题（复用 TCP 连接） |
| 端口占用 | 每路流需要额外 UDP 端口对 | 不需要额外端口 |
| 服务端压力 | 较低 | 较高（TCP 状态维护） |
| 适用场景 | 局域网、低延迟要求 | 公网、防火墙严格环境 |

实践中，很多 RTSP 客户端的策略是：先尝试 UDP，如果一段时间收不到 RTP 数据，自动切换为 TCP interleaved。VLC 和 FFmpeg 都支持这种回退机制。

## 4. live555 源码架构分析

live555 是一个用 C++ 编写的开源流媒体库，自 1996 年至今持续维护，几乎是 RTSP 领域最经典的实现。很多商业产品和开源项目（如早期的 VLC、FFmpeg 的 RTSP 模块）都参考或直接使用了 live555。

### 模块组成

live555 的源码分为四个核心模块：

![live555架构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/live555_arch.png)

**UsageEnvironment**：抽象环境层，定义了任务调度器（TaskScheduler）和错误报告的接口。这是一个纯抽象层，不依赖任何具体的操作系统 API。

**BasicUsageEnvironment**：UsageEnvironment 的默认实现，基于 `select()` 系统调用实现事件循环。适用于 POSIX 和 Windows 平台。如果你需要将 live555 集成到已有的事件框架（如 libevent、libuv）中，需要自己实现 UsageEnvironment 接口。

**groupsock**：封装了网络 Socket 操作，支持 UDP 单播/组播、TCP 连接管理。名字中的 "group" 来源于组播（multicast group）的概念。

**liveMedia**：核心模块，包含了 RTSP 服务器/客户端、RTP 发送/接收、媒体格式解析（H.264、H.265、AAC、MP3 等）以及各种 Source/Sink/Filter 组件。

### 核心类

**RTSPServer**：RTSP 服务器的入口类，负责监听 TCP 端口、接受客户端连接、解析 RTSP 请求并派发处理。每个客户端连接对应一个 `RTSPClientConnection` 对象，每个活跃会话对应一个 `RTSPClientSession` 对象。

**ServerMediaSession**：代表一个媒体会话（对应一个 RTSP URL 路径）。一个 ServerMediaSession 可以包含多个 `ServerMediaSubsession`——典型情况是一个视频子会话和一个音频子会话。

**FramedSource**：所有媒体数据源的基类。它定义了一个异步的数据获取接口：调用 `getNextFrame()` 发起读取请求，数据就绪后通过回调函数通知。live555 提供了多种具体实现，如 `ByteStreamFileSource`（从文件读取）、`H264VideoStreamFramer`（H.264 帧解析和封装）。

**RTPSink**：负责将 FramedSource 产生的数据封装成 RTP 包并发送。不同编码格式有不同的 RTPSink 实现（`H264VideoRTPSink`、`MPEG4GenericRTPSink` 等），它们处理各自特有的 RTP 封装逻辑。

### 事件驱动模型

live555 采用**单线程事件驱动**架构，与我们之前学习的 Reactor 模式一脉相承。核心是 `TaskScheduler`，它维护一个事件循环：

1. 通过 `select()`（或平台特定的 I/O 多路复用机制）监控所有 Socket 的可读/可写事件
2. 维护一个延迟任务队列（delayed task），用于定时触发数据发送
3. 维护一个触发事件队列（triggered event），用于跨组件通知

事件循环的伪代码：

```cpp
while (true) {
    // 1. 检查并执行到期的延迟任务
    processDelayedTasks();
    // 2. 处理已触发的事件
    processTriggeredEvents();
    // 3. select() 等待 I/O 事件
    selectAndProcessIO();
}
```

RTP 数据发送的流程是：`RTPSink` 注册一个延迟任务，时间间隔基于目标帧率计算。任务触发时，`RTPSink` 调用 `FramedSource::getNextFrame()` 获取下一帧数据，封装成 RTP 包发送出去，然后再注册下一个延迟任务。这种基于定时器的发送机制保证了 RTP 包按照媒体时间戳均匀发送，而不是一股脑全部灌出去。

## 5. 实战：基于 live555 搭建 RTSP 服务器

### 编译安装 live555

在 Ubuntu 上编译 live555 非常简单：

```bash
# 下载源码
wget http://www.live555.com/liveMedia/public/live555-latest.tar.gz
tar xzf live555-latest.tar.gz
cd live

# 生成 Makefile（Linux 平台）
./genMakefiles linux-64bit

# 编译
make -j$(nproc)

# 安装头文件和库到系统目录（可选）
sudo make install
```

编译完成后，在各个子目录下会生成对应的静态库（`.a` 文件），以及 `mediaServer/` 下的示例 RTSP 服务器程序 `live555MediaServer`。

### 代码实战：H.264 文件 RTSP 点播服务

下面是一个完整的 RTSP 点播服务器，它将本地的 H.264 文件通过 RTSP 提供给客户端播放：

```cpp
#include "liveMedia.hh"
#include "BasicUsageEnvironment.hh"

static void announceStream(RTSPServer* rtspServer,
                           ServerMediaSession* sms,
                           const char* streamName);

int main(int argc, char* argv[]) {
    const char* inputFileName = "test.264";
    if (argc > 1) {
        inputFileName = argv[1];
    }

    TaskScheduler* scheduler = BasicTaskScheduler::createNew();
    UsageEnvironment* env = BasicUsageEnvironment::createNew(*scheduler);

    UserAuthenticationDatabase* authDB = nullptr;
    // 如果需要认证，取消下面的注释：
    // authDB = new UserAuthenticationDatabase;
    // authDB->addUserRecord("admin", "123456");

    RTSPServer* rtspServer = RTSPServer::createNew(*env, 8554, authDB);
    if (rtspServer == nullptr) {
        *env << "Failed to create RTSP server: "
             << env->getResultMsg() << "\n";
        return 1;
    }

    const char* streamName = "live";
    const char* descriptionString = "H.264 Video On Demand";

    ServerMediaSession* sms =
        ServerMediaSession::createNew(*env, streamName,
                                      streamName, descriptionString);

    sms->addSubsession(
        H264VideoFileServerMediaSubsession::createNew(*env,
                                                       inputFileName,
                                                       False /* reuseFirstSource */));

    rtspServer->addServerMediaSession(sms);
    announceStream(rtspServer, sms, streamName);

    // 进入事件循环，永不返回
    env->taskScheduler().doEventLoop();

    return 0;
}

static void announceStream(RTSPServer* rtspServer,
                           ServerMediaSession* sms,
                           const char* streamName) {
    UsageEnvironment& env = rtspServer->envir();
    char* url = rtspServer->rtspURL(sms);
    env << "Stream \"" << streamName << "\" is available at " << url << "\n";
    delete[] url;
}
```

**关键代码解读：**

1. **环境初始化**：`BasicTaskScheduler` 和 `BasicUsageEnvironment` 创建了事件循环的基础设施。所有的 I/O 事件和定时任务都在这个调度器中管理。

2. **创建 RTSP 服务器**：`RTSPServer::createNew()` 在指定端口上监听。第三个参数是可选的认证数据库，传 `nullptr` 表示不需要认证。

3. **配置媒体会话**：`ServerMediaSession` 对应一个 RTSP URL 路径（这里是 `/live`）。`H264VideoFileServerMediaSubsession` 是 live555 内置的 H.264 文件点播子会话，它内部封装了文件读取、H.264 NAL Unit 解析、RTP 封装等全部逻辑。

4. **`reuseFirstSource` 参数**：设为 `False` 表示每个客户端独立读取文件，互不影响。设为 `True` 则所有客户端共享同一个数据源——适用于直播场景（模拟直播）。

5. **事件循环**：`doEventLoop()` 进入无限循环，处理所有的 RTSP 请求和 RTP 发送。这是 live555 的单线程模型——所有逻辑都在这个循环里跑。

### 编译

创建一个 `CMakeLists.txt`：

```cmake
cmake_minimum_required(VERSION 3.10)
project(rtsp_server)

set(CMAKE_CXX_STANDARD 14)

# live555 头文件路径（根据实际安装位置调整）
include_directories(
    /usr/local/include/liveMedia
    /usr/local/include/groupsock
    /usr/local/include/BasicUsageEnvironment
    /usr/local/include/UsageEnvironment
)

add_executable(rtsp_server main.cpp)

target_link_libraries(rtsp_server
    liveMedia
    groupsock
    BasicUsageEnvironment
    UsageEnvironment
)
```

```bash
mkdir build && cd build
cmake ..
make
```

### 拉流测试

启动服务器后，可以用 VLC 或 FFmpeg 进行拉流验证：

```bash
# 启动服务器
./rtsp_server test.264

# VLC 拉流（另一个终端）
vlc rtsp://127.0.0.1:8554/live

# FFmpeg 拉流并保存为 MP4
ffmpeg -rtsp_transport tcp -i rtsp://127.0.0.1:8554/live -c copy output.mp4

# FFplay 播放
ffplay -rtsp_transport udp rtsp://127.0.0.1:8554/live
```

`-rtsp_transport tcp` 参数让 FFmpeg 使用 TCP interleaved 模式拉流，在网络环境不稳定时推荐使用。

如果需要同时提供视频和音频，只需在 `ServerMediaSession` 中添加音频子会话：

```cpp
sms->addSubsession(
    H264VideoFileServerMediaSubsession::createNew(*env, "test.264", False));
sms->addSubsession(
    ADTSAudioFileServerMediaSubsession::createNew(*env, "test.aac", False));
```

### 用 Wireshark 抓包验证

用 Wireshark 抓取 RTSP 交互是验证协议理解最直接的方式：

```bash
# 抓取 RTSP 信令和 RTP 数据
tcpdump -i lo port 8554 or udp portrange 6970-6999 -w rtsp_capture.pcap
```

在 Wireshark 中打开抓包文件，用 `rtsp` 过滤器可以清楚看到完整的 OPTIONS → DESCRIBE → SETUP → PLAY → TEARDOWN 交互过程，以及 DESCRIBE 响应中的 SDP 内容、SETUP 中协商的传输参数。切到 `rtp` 过滤器可以看到 PLAY 之后服务器开始发送的 RTP 数据包。

## 6. 踩坑与调优

在生产环境中使用 live555，有几个常见的坑需要注意。

### 单线程模型的限制

live555 的单线程模型意味着：所有 RTSP 请求处理、RTP 数据发送、文件 I/O 都在同一个线程中进行。一旦某个操作阻塞（比如磁盘 I/O 慢），整个服务器都会卡住，影响所有客户端。

应对策略：

- **小规模场景**（几十路以下）：live555 单线程完全够用，不需要特殊处理
- **中等规模**：启动多个 live555 实例，通过不同端口或反向代理分担负载
- **大规模场景**：考虑基于 live555 进行二次开发——将文件 I/O 放到独立线程池，或者直接换用支持多线程的 RTSP 实现（如 GStreamer RTSP Server）

如果要在 live555 中引入多线程，需要特别小心：live555 的内部数据结构没有加锁，直接从其他线程调用 live555 的 API 会导致竞态条件。正确的做法是通过 `EventTriggerId` 机制向事件循环投递任务：

```cpp
// 在事件循环线程中注册一个触发事件
EventTriggerId triggerId =
    env->taskScheduler().createEventTrigger(handleExternalEvent);

// 在其他线程中安全地触发该事件
env->taskScheduler().triggerEvent(triggerId, clientData);
```

`triggerEvent()` 是 live555 中唯一可以跨线程调用的方法。

### 长连接超时处理

RTSP 会话有一个服务端指定的超时时间（SETUP 响应的 `timeout` 参数）。如果客户端在超时时间内没有发送任何 RTSP 请求，服务器会主动释放会话。

但实际场景中，客户端可能正常播放视频却不发送任何 RTSP 请求——因为数据都走 RTP 了。这种情况下需要客户端定时发送保活请求：

- **推荐方式**：定时发送 OPTIONS 或 GET_PARAMETER 请求作为心跳
- **保活间隔**：通常设为 timeout 值的一半到三分之二

live555 的 RTSPServer 默认的会话超时是 65 秒。可以在创建时调整：

```cpp
// 设置会话回收策略
// reclamationSeconds = 0 表示不主动回收
RTSPServer* rtspServer =
    RTSPServer::createNew(*env, 8554, authDB,
                          65 /* reclamationSeconds */);
```

### 大并发场景下的性能瓶颈

live555 使用 `select()` 做 I/O 多路复用，而 `select()` 有文件描述符上限（通常 1024）。当并发连接超过几百路时，性能会急剧下降。

优化方向：

- 修改 live555 的 `BasicTaskScheduler` 实现，将 `select()` 替换为 `epoll`
- 或者自行实现 `TaskScheduler` 接口，集成到已有的高性能事件框架中
- 社区有一些 epoll 补丁，但需要注意与 live555 版本的兼容性

### TCP interleaved 模式的缓冲区问题

TCP interleaved 模式下，RTP 数据和 RTSP 信令共享一个 TCP 连接。如果客户端处理 RTP 数据的速度跟不上发送速度（比如解码器卡顿），TCP 发送缓冲区会被填满。此时 `send()` 会阻塞（或返回 `EAGAIN`），进而阻塞整个事件循环。

live555 的处理方式是：当 TCP 写入返回 `EAGAIN` 时，暂停当前 RTPSink 的发送，注册一个 Socket 可写事件的回调。当 TCP 缓冲区有空间时，事件循环通知 RTPSink 继续发送。这个机制在大多数情况下工作正常，但如果客户端持续跟不上，积压的数据可能导致服务端内存不断增长。

建议在应用层增加积压检测逻辑：如果某个客户端的发送积压超过阈值（如 5 秒的数据量），主动断开该客户端连接，避免影响其他客户端。

## 总结

本文从协议理论到代码实战，系统梳理了 RTSP 协议的核心知识：

- **RTSP 是信令协议**，负责控制媒体会话的建立和播放状态，实际数据通过 RTP 传输
- **六个核心方法**（OPTIONS、DESCRIBE、SETUP、PLAY、PAUSE、TEARDOWN）构成了完整的会话生命周期
- **两种传输方式**——RTP over UDP 适合局域网低延迟场景，RTP over TCP interleaved 解决 NAT 穿透问题
- **live555** 是 RTSP 领域最经典的 C++ 开源实现，单线程事件驱动架构简洁高效，但在大并发场景下有局限性
- **实际部署**时需要关注会话超时、并发上限、缓冲区管理等生产级问题

RTSP 虽然诞生于 1998 年，在 Web 直播场景中已被 HLS/DASH/RTMP 取代，但在安防监控和专业音视频领域依然不可替代。理解 RTSP 的工作原理，对于掌握整个流媒体协议体系至关重要。

下一篇我们将进入另一个经典协议——**RTMP 协议深度剖析**，深入解析 RTMP 的握手、Chunk 分块、AMF 编码等核心机制，并用 librtmp 进行推流实战。
