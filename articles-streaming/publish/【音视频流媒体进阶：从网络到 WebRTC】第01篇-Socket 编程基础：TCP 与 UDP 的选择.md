# Socket 编程基础：TCP 与 UDP 的选择

## 前言

想象一个直播场景：主播的摄像头每秒采集 30 帧画面，麦克风不断产出音频采样，这些数据经过编码压缩后，需要在毫秒级的时间窗口内穿越网络，到达成千上万个观众的播放器。或者一个视频通话场景：两端的音视频数据必须双向实时流动，任何超过 200ms 的延迟都会让对话变得别扭。

在这些场景背后，无论你用 FFmpeg 推流、用 WebRTC 建立 P2P 连接，还是用 RTMP 向 CDN 分发内容，最终都绕不开一个基础设施——**Socket**。它是应用程序与网络协议栈之间的接口，是所有网络通信的起点。

本文将从 Socket 编程模型出发，分别深入 TCP 和 UDP 的编程实践，并结合流媒体的实际需求，帮助你理解在不同场景下如何做出正确的协议选择。

---

## 1. Socket 编程模型概述

### BSD Socket API

Socket 最早由 BSD Unix 在 1983 年引入，至今仍是几乎所有操作系统网络编程的标准接口。它的核心思想是将网络通信抽象为类似文件 I/O 的操作——创建一个"端点"（socket），然后通过这个端点读写数据。

一个 Socket 由五元组唯一标识：**协议、本地地址、本地端口、远端地址、远端端口**。

### 两种编程模型

根据传输层协议的不同，Socket 编程分为两种基本模型：

**面向连接（TCP）**：通信前需要建立连接，数据按序到达，丢包自动重传。编程流程较长，涉及 `listen`、`accept`、`connect` 等步骤。

**无连接（UDP）**：不需要建立连接，直接发送数据报。每个数据报独立路由，可能乱序、丢失。编程流程简洁，核心就是 `sendto` 和 `recvfrom`。

![Socket编程模型](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/socket_model.png)

两种模型没有绝对的优劣，选择取决于应用场景——这正是流媒体开发中需要反复权衡的问题。

---

## 2. TCP Socket 编程详解

### 三次握手与四次挥手

TCP 在传输数据前必须建立连接，这个过程称为三次握手：

1. **SYN**：客户端发送 SYN 报文，携带初始序列号 `seq=x`
2. **SYN+ACK**：服务端回复 SYN+ACK，携带自己的序列号 `seq=y` 和确认号 `ack=x+1`
3. **ACK**：客户端发送 ACK，确认号 `ack=y+1`，连接建立

断开连接则需要四次挥手，因为 TCP 是全双工的，每个方向的关闭需要独立确认。

![TCP三次握手](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/tcp_handshake.png)

### 核心 API 流程

TCP 服务端的典型调用顺序：

```
socket() → bind() → listen() → accept() → recv()/send() → close()
```

TCP 客户端的典型调用顺序：

```
socket() → connect() → send()/recv() → close()
```

### 实战代码：TcpServer 类

下面封装一个支持多客户端连接的 TCP 服务端，使用 `std::thread` 处理并发：

```cpp
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
#include <atomic>

class TcpServer {
public:
    using ClientHandler = std::function<void(int client_fd, const std::string& client_addr)>;

    explicit TcpServer(uint16_t port, ClientHandler handler)
        : port_(port), handler_(std::move(handler)) {}

    ~TcpServer() { Stop(); }

    bool Start() {
        listen_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (listen_fd_ < 0) {
            perror("socket");
            return false;
        }

        int opt = 1;
        setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(port_);

        if (bind(listen_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
            perror("bind");
            return false;
        }

        if (listen(listen_fd_, 128) < 0) {
            perror("listen");
            return false;
        }

        running_ = true;
        accept_thread_ = std::thread(&TcpServer::AcceptLoop, this);
        std::cout << "TcpServer listening on port " << port_ << std::endl;
        return true;
    }

    void Stop() {
        running_ = false;
        if (listen_fd_ >= 0) {
            shutdown(listen_fd_, SHUT_RDWR);
            close(listen_fd_);
            listen_fd_ = -1;
        }
        if (accept_thread_.joinable()) accept_thread_.join();
        for (auto& t : client_threads_) {
            if (t.joinable()) t.join();
        }
    }

private:
    void AcceptLoop() {
        while (running_) {
            sockaddr_in client_addr{};
            socklen_t addr_len = sizeof(client_addr);
            int client_fd = accept(listen_fd_,
                                   reinterpret_cast<sockaddr*>(&client_addr), &addr_len);
            if (client_fd < 0) {
                if (running_) perror("accept");
                break;
            }

            std::string addr_str = std::string(inet_ntoa(client_addr.sin_addr))
                                   + ":" + std::to_string(ntohs(client_addr.sin_port));
            std::cout << "New connection from " << addr_str << std::endl;

            client_threads_.emplace_back([this, client_fd, addr_str]() {
                handler_(client_fd, addr_str);
                close(client_fd);
            });
        }
    }

    uint16_t port_;
    ClientHandler handler_;
    int listen_fd_ = -1;
    std::atomic<bool> running_{false};
    std::thread accept_thread_;
    std::vector<std::thread> client_threads_;
};
```

使用方式非常直观：

```cpp
int main() {
    TcpServer server(8080, [](int fd, const std::string& addr) {
        char buf[4096];
        while (true) {
            ssize_t n = recv(fd, buf, sizeof(buf), 0);
            if (n <= 0) break;
            // 回显收到的数据
            send(fd, buf, n, 0);
        }
        std::cout << "Client " << addr << " disconnected" << std::endl;
    });

    server.Start();

    std::cout << "Press Enter to stop..." << std::endl;
    std::cin.get();
    server.Stop();
    return 0;
}
```

### TCP 在流媒体场景中的表现

TCP 提供了有序、可靠的字节流传输，这对流媒体意味着：

**优势**：数据完整无丢失，天然适合需要完整性保障的协议（如 RTMP、HLS/HTTP）。

**劣势**：当网络出现丢包时，TCP 的重传机制会导致**队头阻塞**（Head-of-Line Blocking）——后续数据必须等待丢失的包重传完成才能交付给应用层。对于实时音视频来说，一个已经过时的帧被重传回来，不如直接丢弃。此外，TCP 的拥塞控制算法在检测到丢包时会主动降速，这可能导致直播画面突然模糊（编码器被迫降低码率）。

---

## 3. UDP Socket 编程详解

### 无连接特性

UDP 是一种"发后即忘"的协议。它不维护连接状态，不保证送达，不保证顺序，也不做拥塞控制。每个 UDP 数据报都是独立的，头部开销只有 8 字节（TCP 是 20 字节起）。

这些"缺点"在流媒体场景中反而是优点——应用层可以根据自己的需求定制可靠性策略，而不被传输层的固有机制所束缚。

### 核心 API 流程

UDP 的编程模型要简单得多：

```
socket() → bind() → recvfrom()/sendto() → close()
```

注意 UDP 没有 `listen`、`accept`、`connect`（虽然 UDP 也可以调用 `connect`，但语义不同，只是绑定默认目标地址）。

### 实战代码：UdpSocket 类

```cpp
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

#include <cstring>
#include <iostream>
#include <string>

class UdpSocket {
public:
    UdpSocket() = default;
    ~UdpSocket() { Close(); }

    UdpSocket(const UdpSocket&) = delete;
    UdpSocket& operator=(const UdpSocket&) = delete;

    bool Bind(uint16_t port) {
        fd_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (fd_ < 0) {
            perror("socket");
            return false;
        }

        int opt = 1;
        setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(port);

        if (bind(fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
            perror("bind");
            return false;
        }
        return true;
    }

    ssize_t SendTo(const void* data, size_t len,
                   const std::string& ip, uint16_t port) {
        sockaddr_in dest{};
        dest.sin_family = AF_INET;
        dest.sin_port = htons(port);
        inet_pton(AF_INET, ip.c_str(), &dest.sin_addr);
        return sendto(fd_, data, len, 0,
                      reinterpret_cast<sockaddr*>(&dest), sizeof(dest));
    }

    ssize_t RecvFrom(void* buf, size_t len,
                     std::string& src_ip, uint16_t& src_port) {
        sockaddr_in src{};
        socklen_t addr_len = sizeof(src);
        ssize_t n = recvfrom(fd_, buf, len, 0,
                             reinterpret_cast<sockaddr*>(&src), &addr_len);
        if (n > 0) {
            char ip_buf[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &src.sin_addr, ip_buf, sizeof(ip_buf));
            src_ip = ip_buf;
            src_port = ntohs(src.sin_port);
        }
        return n;
    }

    void Close() {
        if (fd_ >= 0) {
            close(fd_);
            fd_ = -1;
        }
    }

    int fd() const { return fd_; }

private:
    int fd_ = -1;
};
```

一个简单的 UDP 回显服务端：

```cpp
int main() {
    UdpSocket sock;
    if (!sock.Bind(9000)) return 1;

    std::cout << "UDP server listening on port 9000" << std::endl;

    char buf[65536];
    std::string src_ip;
    uint16_t src_port;

    while (true) {
        ssize_t n = sock.RecvFrom(buf, sizeof(buf), src_ip, src_port);
        if (n <= 0) break;

        std::cout << "Received " << n << " bytes from "
                  << src_ip << ":" << src_port << std::endl;

        sock.SendTo(buf, n, src_ip, src_port);
    }
    return 0;
}
```

### UDP 在流媒体场景中的表现

**优势**：没有队头阻塞，丢包不会拖累后续数据的交付。延迟可控，适合实时通信场景。应用层可以自己决定哪些包值得重传（如关键帧），哪些直接丢弃（如过期的 P 帧）。

**劣势**：所有的可靠性保障都需要应用层自己实现——序列号、乱序重组、丢包检测、重传策略、拥塞控制，一个都不能少。此外，UDP 包大小受 MTU 限制（通常 1500 字节），大帧需要应用层分片和重组。

---

## 4. 流媒体场景下 TCP vs UDP 的选择

### 多维度对比

| 维度 | TCP | UDP |
|------|-----|-----|
| **延迟** | 握手增加 1-RTT 开销；队头阻塞可能导致突发延迟 | 无握手开销；无队头阻塞 |
| **可靠性** | 协议栈保证有序可靠 | 应用层自行保障 |
| **拥塞控制** | 内置（慢启动、AIMD），不可控 | 无内置机制，灵活但需自行实现 |
| **NAT 穿越** | 困难（需要中继服务器） | 相对容易（STUN/TURN/ICE） |
| **头部开销** | 20+ 字节 | 8 字节 |
| **适用场景** | 点播、文件传输、信令 | 实时通话、低延迟直播 |

### 实际协议的选择

流媒体领域中，各协议的传输层选择都有其工程考量：

**RTMP（TCP）**：Adobe 设计的直播推流协议。选择 TCP 是因为推流端到 CDN 之间的链路通常较好，可靠传输比低延迟更重要。代价是在弱网下延迟会累积。

**RTP/RTCP（UDP）**：IETF 为实时媒体设计的传输协议。RTP 承载媒体数据，RTCP 负责质量反馈。选择 UDP 是为了获得最低延迟，丢包由应用层处理（NACK 重传或 FEC 前向纠错）。

**WebRTC（UDP + DTLS + SRTP）**：Google 主导的实时通信框架。底层走 UDP，用 DTLS 做密钥协商，用 SRTP 加密媒体数据。通过 ICE 框架实现 NAT 穿越，是目前端到端实时通信的主流方案。

**SRT（UDP）**：Haivision 开源的安全可靠传输协议。在 UDP 之上实现 ARQ 重传和自适应拥塞控制，专为不稳定网络上的低延迟直播设计。

**QUIC/HTTP3（UDP）**：新一代传输协议，在 UDP 之上实现了多路复用和独立流控制，解决了 TCP 的队头阻塞问题。LL-HLS 等低延迟协议正在向 HTTP/3 迁移。

![TCP vs UDP对比](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/tcp_vs_udp.png)

### 决策参考表

| 场景 | 推荐协议 | 传输层 | 理由 |
|------|----------|--------|------|
| CDN 推流 | RTMP / SRT | TCP / UDP | 链路可控，RTMP 生态成熟；弱网场景优先 SRT |
| CDN 拉流（点播） | HLS / DASH | TCP (HTTP) | 兼容性好，CDN 友好 |
| 低延迟直播 | WebRTC / SRT | UDP | 延迟敏感，允许少量丢包 |
| 视频通话 | WebRTC | UDP | 双向实时，P2P 优先 |
| 信令传输 | WebSocket / HTTP | TCP | 可靠性优先，数据量小 |
| 监控/安防 | RTSP + RTP | UDP (媒体) + TCP (信令) | 经典方案，设备兼容性好 |

---

## 5. 踩坑与调优

### 常见 Socket 编程陷阱

**SIGPIPE 信号**

向一个已关闭的 TCP 连接写数据，内核会发送 SIGPIPE 信号，默认行为是终止进程。流媒体服务端一个客户端断开就导致整个进程崩溃，这是经典的线上事故。

解决方案：

```cpp
// 方案一：全局忽略 SIGPIPE
signal(SIGPIPE, SIG_IGN);

// 方案二：send 时指定 MSG_NOSIGNAL 标志（Linux）
send(fd, buf, len, MSG_NOSIGNAL);

// 方案三：使用 SO_NOSIGPIPE 选项（macOS）
int opt = 1;
setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &opt, sizeof(opt));
```

**TIME_WAIT 状态**

TCP 主动关闭方会进入 TIME_WAIT 状态，默认持续 2MSL（通常 60 秒）。如果流媒体服务端频繁重启，会发现端口被占用无法绑定。

```cpp
int opt = 1;
setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
```

`SO_REUSEADDR` 允许绑定处于 TIME_WAIT 状态的地址，是服务端 Socket 的标准配置。

**send/recv 的短读短写**

TCP 是字节流协议，一次 `send(1000)` 可能只发出 500 字节，一次 `recv` 可能收到半个消息或者一个半消息。必须在应用层处理消息边界：

```cpp
bool SendAll(int fd, const void* data, size_t len) {
    const char* p = static_cast<const char*>(data);
    size_t remaining = len;
    while (remaining > 0) {
        ssize_t n = send(fd, p, remaining, MSG_NOSIGNAL);
        if (n <= 0) return false;
        p += n;
        remaining -= n;
    }
    return true;
}
```

**UDP 数据报截断**

UDP 的 `recvfrom` 如果提供的缓冲区小于实际数据报大小，多余的部分会被静默丢弃。接收缓冲区大小要根据实际最大报文大小来设置，RTP 场景下通常 2048 字节足够（MTU 限制下单个 RTP 包一般不超过 1400 字节）。

### 流媒体场景的特殊注意事项

**Socket 缓冲区大小调优**

流媒体的数据量远大于普通 Web 应用。系统默认的 Socket 收发缓冲区（通常 128KB ~ 256KB）在高码率场景下可能成为瓶颈：

```cpp
int buf_size = 2 * 1024 * 1024; // 2MB
setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &buf_size, sizeof(buf_size));
setsockopt(fd, SOL_SOCKET, SO_SNDBUF, &buf_size, sizeof(buf_size));
```

注意 Linux 内核会将设置值翻倍（内核需要额外空间存储元数据），可以通过 `getsockopt` 验证实际值。如果需要设置超过系统上限的缓冲区大小，需要调整 `/proc/sys/net/core/rmem_max` 和 `/proc/sys/net/core/wmem_max`。

**TCP_NODELAY**

TCP 默认启用 Nagle 算法，会将小包聚合后再发送，这会给流媒体信令带来额外延迟。对于交互性要求高的连接，应当禁用：

```cpp
#include <netinet/tcp.h>
int opt = 1;
setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &opt, sizeof(opt));
```

**非阻塞模式**

生产环境的流媒体服务不会使用阻塞 Socket，因为一个卡住的客户端会拖累整个服务。通常会将 Socket 设置为非阻塞模式，配合 I/O 多路复用（epoll/kqueue）使用：

```cpp
#include <fcntl.h>

int flags = fcntl(fd, F_GETFL, 0);
fcntl(fd, F_SETFL, flags | O_NONBLOCK);
```

非阻塞模式下 `send`/`recv` 在无法立即完成时会返回 -1 并设置 `errno = EAGAIN`，这不是错误，而是需要等待 I/O 就绪后重试。这部分内容将在下一篇文章中展开。

---

## 总结

本文从 Socket 编程模型出发，分别介绍了 TCP 和 UDP 两种传输协议的编程实践。核心要点回顾：

- **Socket** 是网络编程的基础抽象，理解它的 API 和行为是构建流媒体系统的前提
- **TCP** 提供有序可靠的字节流，适合对完整性要求高、对延迟容忍度较大的场景（点播、推流、信令）
- **UDP** 提供轻量的数据报服务，适合对延迟敏感、允许应用层自定义可靠性的场景（实时通话、低延迟直播）
- 流媒体协议的传输层选择是**工程权衡**的结果，没有银弹
- Socket 编程中的细节（SIGPIPE、短读短写、缓冲区调优、Nagle 算法）往往是线上问题的根源

掌握了 Socket 基础之后，你会发现单线程逐个处理连接的方式无法应对高并发的流媒体服务。下一篇文章我们将进入 **I/O 多路复用**的世界，探讨 `select`、`poll`、`epoll` 的原理与实践，看看如何用一个线程高效管理成千上万个连接。
