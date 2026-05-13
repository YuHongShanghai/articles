# SRT 协议与低延迟传输

## 前言

前两篇文章中我们学习了 HLS 和 DASH——两大基于 HTTP 的自适应流媒体协议。它们在点播和大规模直播分发场景中表现出色，但有一个无法回避的短板：**延迟**。即便引入了 LL-HLS 和 CMAF Chunk 等低延迟优化，HTTP 分片传输的架构决定了端到端延迟很难低于 2 秒，更别提在丢包率较高的不稳定网络（跨国链路、卫星链路、蜂窝网络）上表现更会大打折扣。

在广电转播、赛事直播、远程制作等场景中，延迟和可靠性同等重要。导播需要在数百毫秒内看到前方摄像机的画面，赛事制作团队需要在不稳定的公网链路上实现接近零丢包的视频回传。**SRT（Secure Reliable Transport）** 正是为这类场景而生。

SRT 由视频传输设备厂商 Haivision 于 2017 年开源，基于 UDP 构建，通过 ARQ（Automatic Repeat Request）选择性重传实现可靠传输，同时将延迟严格控制在用户指定的上限内。它不是 HLS/DASH 的替代品，而是在"第一公里"（信号采集到平台）和"长途传输"场景中，提供了一个比 RTMP 更安全、更抗丢包、更低延迟的选择。

本文将深入剖析 SRT 的核心机制——连接模型、ARQ 重传、加密认证，然后用 libsrt 实现一个完整的低延迟推拉流系统。

---

## 1. SRT 协议概述

### 设计目标

SRT 的设计围绕三个核心目标展开：

**可靠传输**：在 UDP 之上通过 ARQ 重传保证数据完整性。与 TCP 不同，SRT 的重传是有时间限制的——超过延迟窗口的丢包直接放弃，避免了 TCP 那种"不惜一切代价重传"导致的延迟累积。

**低延迟**：用户可以通过 latency 参数精确控制端到端延迟。SRT 在这个时间窗口内尽最大努力恢复丢包，但绝不超时等待。这种"有限度的可靠性"正是实时传输所需要的。

**安全性**：原生支持 AES-128/AES-192/AES-256 加密，密钥通过握手过程安全交换。在公网传输敏感的广电信号时，加密是刚需而非可选项。

### 技术演进

SRT 并非从零开始设计。它基于 **UDT（UDP-based Data Transfer Protocol）** 演进而来。UDT 最初由美国伊利诺伊大学研发，目标是在高带宽、高延迟的广域网上实现高效的大文件传输。Haivision 在 UDT 的基础上做了大量改造：

- 将 UDT 面向吞吐量优化的拥塞控制替换为面向低延迟优化的策略
- 增加了 AES 加密和密钥交换机制
- 引入了 Stream ID 支持多路复用
- 优化了 ARQ 重传策略，使其更适合实时音视频传输
- 增加了连接迁移和 Rendezvous 模式

### 核心特性总览

| 特性 | 说明 |
|------|------|
| **传输层** | UDP |
| **可靠性** | 选择性 ARQ 重传，受 latency 参数约束 |
| **加密** | AES-128 / AES-192 / AES-256，CTR 模式 |
| **延迟控制** | 用户指定 latency（通常 120ms ~ 8000ms） |
| **拥塞控制** | 基于带宽估计的自适应发送速率 |
| **连接模式** | Caller-Listener / Rendezvous |
| **多路复用** | Stream ID 标识不同流 |
| **FEC** | v1.4+ 支持前向纠错（可选） |

![SRT协议架构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/srt_architecture.png)

---

## 2. SRT 连接模式

SRT 提供了两种连接模式，适用于不同的网络拓扑和 NAT 环境。

### Caller-Listener 模式

这是最常用的连接模式，逻辑上类似 TCP 的 client-server 模型：

- **Listener**：绑定端口等待连接，类似 TCP 的 `listen` + `accept`
- **Caller**：主动发起连接，类似 TCP 的 `connect`

典型应用场景：编码器（Caller）向流媒体服务器（Listener）推流，或者播放器（Caller）从服务器（Listener）拉流。Listener 一方通常部署在有公网 IP 的服务器上。

### Rendezvous 模式

Rendezvous 模式下，双方没有主从之分，都同时主动向对方发起连接。两端在约定好的时间窗口内互相发送握手包，利用 UDP 的特性在两端的 NAT 上同时打洞。

这种模式特别适合两端都在 NAT 后面的 P2P 场景——比如两个远程制作工作站之间直接传输视频。但它需要双方事先知道对方的地址信息（通常通过一个信令服务器交换），并且对 NAT 类型有一定要求（Symmetric NAT 可能无法穿越）。

### 握手过程

SRT 的连接建立需要经过两轮握手：

**第一轮握手（Induction）**：Caller 发送带有随机 cookie 的握手请求。Listener 返回一个 SYN cookie，Caller 必须在后续握手中携带这个 cookie。这一步主要用于防止地址伪造攻击，类似 TCP 的 SYN Cookie 机制。

**第二轮握手（Conclusion）**：双方交换以下关键信息：
- SRT 版本号和能力标志位
- 延迟参数（取双方中较大的值作为最终 latency）
- 加密配置和密钥材料（如果启用了加密）
- Stream ID（如果设置了的话）
- 最大报文大小（Payload Size）

握手完成后连接建立，后续数据传输使用协商好的参数。整个握手过程只需要两个 RTT，与 TCP + TLS 1.3 持平，比 TCP + TLS 1.2（3 RTT）更少。

### Stream ID

Stream ID 是 SRT 1.3 引入的特性，允许 Caller 在连接时携带一个字符串标识。Listener 端可以在 `accept` 回调中读取这个 Stream ID，据此决定是否接受连接以及如何路由该连接。

这在多路复用场景中非常有用。例如一台 SRT 服务器同时接收多路推流，可以通过 Stream ID 区分不同的节目源：

```
srt://server:9000?streamid=#!::r=live/sports,m=publish
srt://server:9000?streamid=#!::r=live/news,m=publish
```

Stream ID 还可以编码认证信息、请求模式（推流/拉流）等元数据，是实现灵活的 SRT 网关服务的基础。

---

## 3. ARQ 重传机制

ARQ 重传是 SRT 实现"可靠但低延迟"的核心机制。理解它的工作原理，是用好 SRT 的前提。

### 选择性重传（Selective ARQ）

与 TCP 的累积确认不同，SRT 使用**选择性重传**。接收端精确告知发送端哪些包丢失了，发送端只重传丢失的包，不影响其他包的传输。

工作流程：

1. 发送端为每个数据包分配递增的序列号，发送后保留在**发送缓冲区**中
2. 接收端维护一个**接收缓冲区**，按序列号排列收到的包
3. 接收端检测到序列号不连续（即丢包）时，向发送端发送 **NAK（Negative Acknowledgment）** 报文，列出丢失的序列号
4. 发送端收到 NAK 后，从发送缓冲区中取出对应的包进行重传
5. 接收端定期发送 **ACK** 报文，通告已成功接收的最大连续序列号

![SRT ARQ机制](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/srt_arq.png)

### 发送缓冲区管理

发送端的缓冲区需要保留已发送但尚未被确认的数据包，以便在收到 NAK 时能够重传。缓冲区的大小与 latency 参数直接相关——latency 越大，缓冲区需要保留的历史数据越多。

当发送缓冲区满时（比如接收端长时间没有 ACK 回来），SRT 会开始丢弃最旧的包。这是一种有意的设计：对于实时传输来说，超过延迟窗口的数据已经没有重传价值。

### 接收端的丢失检测

接收端检测丢包的机制有两层：

**序列号间隙检测**：收到序列号 N 和 N+3 的包，中间的 N+1、N+2 就被标记为疑似丢失。但不会立即发送 NAK，因为 UDP 包可能乱序到达。

**超时触发**：如果间隙持续存在超过一定时间（通常为几十毫秒），接收端确认这些包确实丢了，发送 NAK 请求重传。

接收端还会周期性地检查所有尚未收到的数据包序列号范围，避免单个 NAK 丢失导致重传请求遗漏。

### Latency 参数的含义

SRT 的 `SRTO_LATENCY` 参数是协议的核心调节旋钮。它定义的是：**从发送端发出数据包，到接收端将数据交付给应用层的最大允许时间**。

```
发送端发出 ──→ 网络传输 ──→ 接收端收到 ──→ 等待重传/排序 ──→ 交付应用
|<─────────────────── latency ──────────────────────>|
```

在这个时间窗口内，SRT 会尽力通过 ARQ 重传恢复丢失的数据包。窗口到期后，无论是否完整，接收端都会将数据交付给应用层（丢失的包以空洞的形式存在）。

连接建立时，双方各自声明自己的 latency 值，最终使用的是两者中较大的那个。这保证了慢速一方也能在其要求的时间内完成重传恢复。

### 延迟参数选择策略

latency 值的选择需要在延迟和质量之间权衡：

| RTT | 丢包率 | 建议 latency | 适用场景 |
|-----|--------|-------------|---------|
| < 50ms | < 1% | 120 ~ 200ms | 同城/机房内传输 |
| 50~100ms | 1~3% | 200 ~ 500ms | 同国跨城传输 |
| 100~200ms | 3~5% | 500 ~ 1500ms | 跨国传输 |
| > 200ms | > 5% | 1500 ~ 8000ms | 卫星链路、极端弱网 |

经验公式：`latency ≥ RTT × 4`。这给了丢包检测（~1 RTT）+ NAK 传输（~0.5 RTT）+ 重传数据返回（~0.5 RTT）+ 安全余量（~2 RTT）足够的时间。如果丢包是突发性的（burst loss），还需要额外增加余量。

实际部署中，推荐先用较大的 latency 值（如 1000ms）确保传输稳定，再逐步降低直到出现可察觉的画面瑕疵，在这个临界点上再加 20~30% 的余量作为最终值。

---

## 4. 加密与认证

在公网上传输广电级的视频内容，加密是必不可少的。SRT 从设计之初就将安全性作为核心特性之一。

### AES 加密

SRT 使用 AES（Advanced Encryption Standard）对传输的媒体数据进行加密，支持三种密钥长度：

- **AES-128**：128 位密钥，性能开销更小，适合大多数场景
- **AES-192**：192 位密钥，安全性与性能的折中选择
- **AES-256**：256 位密钥，安全性更高，适合对安全性有极高要求的场景

加密模式采用 **CTR（Counter）** 模式，这是一种流密码模式，每个数据包使用独立的计数器值生成密钥流，然后与明文异或得到密文。CTR 模式的优势在于：各包的加解密可以并行进行，且不存在错误传播——一个包的损坏不会影响其他包的解密。

### 密钥交换机制

SRT 的加密密钥不直接在网络上传输。密钥交换过程如下：

1. 双方在连接时协商一个 **Passphrase**（密码短语），这是唯一需要预先共享的秘密
2. 发送端使用 Passphrase 通过 PBKDF2（Password-Based Key Derivation Function 2）派生出 **KEK（Key Encrypting Key）**
3. 发送端随机生成实际的 **SEK（Stream Encrypting Key）**，用于加密媒体数据
4. SEK 用 KEK 加密后，通过 **KM（Key Material）** 消息发送给接收端
5. 接收端用同样的 Passphrase 派生出 KEK，解密得到 SEK

SRT 还支持 **密钥轮换**：发送端会周期性地生成新的 SEK，在新旧密钥切换期间，数据包头中标记使用的是奇数密钥还是偶数密钥，接收端据此选择正确的密钥解密。这确保了即使一个 SEK 被破解，也只影响有限时间段的数据。

### Passphrase 认证

Passphrase 除了用于密钥派生，还起到了认证的作用——只有持有正确 Passphrase 的 Caller 才能与 Listener 建立连接。如果 Passphrase 不匹配，握手过程会失败。

这是一种简单但有效的认证方式。在实际部署中，Passphrase 通常通过带外方式（配置文件、管理界面）分发给发送端和接收端。

### 加密对性能的影响

在现代 CPU 上，AES 加密的性能影响很小。大多数 x86 CPU 都支持 AES-NI 硬件加速指令集，ARM 平台也有类似的加密扩展。在支持硬件加速的设备上：

- AES-128 加密对吞吐量的影响通常 < 2%
- AES-256 比 AES-128 的开销增加约 30~40%，但绝对值依然很小
- 加密不会增加延迟（流式加密，逐包处理）

如果你的 CPU 不支持 AES-NI（一些嵌入式设备或老旧 CPU），加密开销会显著增大，此时可能需要在安全性和性能之间做取舍。

---

## 5. libsrt API 详解

libsrt 是 SRT 协议的官方 C 语言实现库，API 设计上刻意模仿了 BSD Socket 的风格，降低了学习成本。

### 编译安装

```bash
git clone https://github.com/Haivision/srt.git
cd srt
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local -DENABLE_SHARED=ON
make -j$(nproc)
sudo make install
sudo ldconfig
```

编译依赖 OpenSSL（用于 AES 加密），确保系统已安装 `libssl-dev`（Debian/Ubuntu）或 `openssl-devel`（CentOS/Fedora）。

### 核心 API

libsrt 的 API 分为几组，整体流程与传统 Socket 编程几乎一一对应。

**初始化与清理**

```cpp
srt_startup();    // 初始化 SRT 库，程序启动时调用一次
srt_cleanup();    // 清理资源，程序退出前调用
```

**Socket 创建**

```cpp
SRTSOCKET sock = srt_create_socket();
```

返回一个 SRT socket 描述符，后续所有操作基于这个描述符。

**参数设置**

SRT 的丰富特性都通过 `srt_setsockopt` 配置：

```cpp
// 设置延迟（毫秒）
int latency_ms = 500;
srt_setsockopt(sock, 0, SRTO_LATENCY, &latency_ms, sizeof(latency_ms));

// 设置加密密钥长度（0/16/24/32，0表示不加密）
int key_len = 16;  // AES-128
srt_setsockopt(sock, 0, SRTO_PBKEYLEN, &key_len, sizeof(key_len));

// 设置密码
const char* passphrase = "my_secret_key";
srt_setsockopt(sock, 0, SRTO_PASSPHRASE, passphrase, strlen(passphrase));

// 设置最大 payload 大小（通常设为 MPEG-TS 的 7 个包 = 1316 字节）
int payload_size = 1316;
srt_setsockopt(sock, 0, SRTO_PAYLOADSIZE, &payload_size, sizeof(payload_size));

// 设置 Stream ID
const char* stream_id = "#!::r=live/sports,m=publish";
srt_setsockopt(sock, 0, SRTO_STREAMID, stream_id, strlen(stream_id));
```

**Listener 端流程**

```cpp
srt_bind(sock, addr, addrlen);       // 绑定地址和端口
srt_listen(sock, backlog);           // 开始监听
SRTSOCKET client = srt_accept(sock, addr, addrlen);  // 接受连接
```

**Caller 端流程**

```cpp
srt_connect(sock, addr, addrlen);    // 连接到 Listener
```

**数据传输**

```cpp
int sent = srt_send(sock, buf, len);      // 发送数据
int rcvd = srt_recv(sock, buf, buflen);   // 接收数据
```

`srt_send` 和 `srt_recv` 的语义与 TCP 的 `send`/`recv` 类似，但底层走的是 UDP + ARQ。SRT 保证数据按发送顺序交付（除非超过 latency 窗口的丢包被跳过）。

**关闭连接**

```cpp
srt_close(sock);
```

### 统计接口

`srt_bistats` 是监控 SRT 传输质量的利器，返回丰富的实时统计数据：

```cpp
SRT_TRACEBSTATS stats;
srt_bistats(sock, &stats, 0, 1);

// 关键指标
printf("RTT: %.1f ms\n", stats.msRTT);
printf("发送速率: %.1f Mbps\n", stats.mbpsSendRate);
printf("接收速率: %.1f Mbps\n", stats.mbpsRecvRate);
printf("发送丢包: %d\n", stats.pktSndLoss);
printf("接收丢包: %d\n", stats.pktRcvLoss);
printf("重传包数: %d\n", stats.pktRetrans);
printf("接收缓冲区时长: %d ms\n", stats.msRcvBuf);
```

这些统计数据对于调试传输问题和优化 latency 参数至关重要。

---

## 6. C++ 实战：基于 libsrt 实现低延迟推拉流

下面实现一个完整的 SRT 推拉流系统：发送端读取本地 TS 文件并通过 SRT 推流，接收端接收数据并保存为文件。

### SRT 发送端（Caller）

```cpp
#include <srt/srt.h>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
#include <chrono>

class SRTSender {
public:
    SRTSender(const std::string& host, int port, int latency_ms)
        : host_(host), port_(port), latency_ms_(latency_ms) {}

    ~SRTSender() { Close(); }

    bool Connect() {
        sock_ = srt_create_socket();
        if (sock_ == SRT_INVALID_SOCK) {
            std::cerr << "srt_create_socket failed: "
                      << srt_getlasterror_str() << std::endl;
            return false;
        }

        // 以 MPEG-TS 对齐的方式设置参数
        int payload_size = 1316;  // 7 × 188 (TS packet size)
        srt_setsockopt(sock_, 0, SRTO_PAYLOADSIZE,
                       &payload_size, sizeof(payload_size));

        srt_setsockopt(sock_, 0, SRTO_LATENCY,
                       &latency_ms_, sizeof(latency_ms_));

        int yes = 1;
        srt_setsockopt(sock_, 0, SRTO_SENDER, &yes, sizeof(yes));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port_);
        inet_pton(AF_INET, host_.c_str(), &addr.sin_addr);

        if (srt_connect(sock_, reinterpret_cast<sockaddr*>(&addr),
                        sizeof(addr)) == SRT_ERROR) {
            std::cerr << "srt_connect failed: "
                      << srt_getlasterror_str() << std::endl;
            return false;
        }

        std::cout << "Connected to srt://" << host_
                  << ":" << port_ << std::endl;
        return true;
    }

    bool SendFile(const std::string& filepath) {
        std::ifstream file(filepath, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Cannot open file: " << filepath << std::endl;
            return false;
        }

        const int kChunkSize = 1316;
        char buf[kChunkSize];
        int total_sent = 0;

        while (file.read(buf, kChunkSize) || file.gcount() > 0) {
            int to_send = static_cast<int>(file.gcount());
            int ret = srt_send(sock_, buf, to_send);
            if (ret == SRT_ERROR) {
                std::cerr << "srt_send failed: "
                          << srt_getlasterror_str() << std::endl;
                return false;
            }
            total_sent += ret;

            // 简单的发送节流，生产环境应根据实际码率计算精确间隔
            std::this_thread::sleep_for(std::chrono::microseconds(500));
        }

        std::cout << "Sent " << total_sent << " bytes" << std::endl;
        return true;
    }

    void PrintStats() {
        SRT_TRACEBSTATS stats;
        if (srt_bistats(sock_, &stats, 0, 1) == 0) {
            std::cout << "[Stats] RTT=" << stats.msRTT << "ms"
                      << " Send=" << stats.mbpsSendRate << "Mbps"
                      << " Loss=" << stats.pktSndLoss
                      << " Retrans=" << stats.pktRetrans << std::endl;
        }
    }

    void Close() {
        if (sock_ != SRT_INVALID_SOCK) {
            srt_close(sock_);
            sock_ = SRT_INVALID_SOCK;
        }
    }

private:
    std::string host_;
    int port_;
    int latency_ms_;
    SRTSOCKET sock_ = SRT_INVALID_SOCK;
};

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0]
                  << " <host> <port> <input.ts>" << std::endl;
        return 1;
    }

    srt_startup();

    SRTSender sender(argv[1], std::atoi(argv[2]), 500);
    if (sender.Connect()) {
        sender.SendFile(argv[3]);
        sender.PrintStats();
    }

    srt_cleanup();
    return 0;
}
```

### SRT 接收端（Listener）

```cpp
#include <srt/srt.h>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <atomic>
#include <csignal>

std::atomic<bool> g_running{true};

void SignalHandler(int) { g_running = false; }

class SRTReceiver {
public:
    SRTReceiver(int port, int latency_ms)
        : port_(port), latency_ms_(latency_ms) {}

    ~SRTReceiver() { Close(); }

    bool Listen() {
        listen_sock_ = srt_create_socket();
        if (listen_sock_ == SRT_INVALID_SOCK) {
            std::cerr << "srt_create_socket failed: "
                      << srt_getlasterror_str() << std::endl;
            return false;
        }

        int payload_size = 1316;
        srt_setsockopt(listen_sock_, 0, SRTO_PAYLOADSIZE,
                       &payload_size, sizeof(payload_size));

        srt_setsockopt(listen_sock_, 0, SRTO_LATENCY,
                       &latency_ms_, sizeof(latency_ms_));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(port_);

        if (srt_bind(listen_sock_, reinterpret_cast<sockaddr*>(&addr),
                     sizeof(addr)) == SRT_ERROR) {
            std::cerr << "srt_bind failed: "
                      << srt_getlasterror_str() << std::endl;
            return false;
        }

        if (srt_listen(listen_sock_, 1) == SRT_ERROR) {
            std::cerr << "srt_listen failed: "
                      << srt_getlasterror_str() << std::endl;
            return false;
        }

        std::cout << "Listening on srt://0.0.0.0:"
                  << port_ << std::endl;
        return true;
    }

    bool AcceptAndReceive(const std::string& output_path) {
        sockaddr_in client_addr{};
        int addr_len = sizeof(client_addr);

        SRTSOCKET client = srt_accept(listen_sock_,
            reinterpret_cast<sockaddr*>(&client_addr), &addr_len);
        if (client == SRT_INVALID_SOCK) {
            std::cerr << "srt_accept failed: "
                      << srt_getlasterror_str() << std::endl;
            return false;
        }

        char addr_str[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr,
                  addr_str, sizeof(addr_str));
        std::cout << "Accepted connection from " << addr_str
                  << ":" << ntohs(client_addr.sin_port) << std::endl;

        std::ofstream file(output_path, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Cannot open output file: "
                      << output_path << std::endl;
            srt_close(client);
            return false;
        }

        const int kBufSize = 1500;
        char buf[kBufSize];
        int total_received = 0;

        while (g_running) {
            int ret = srt_recv(client, buf, kBufSize);
            if (ret == SRT_ERROR) {
                int err = srt_getlasterror(nullptr);
                if (err == SRT_ECONNLOST) {
                    std::cout << "Connection closed by peer" << std::endl;
                    break;
                }
                std::cerr << "srt_recv error: "
                          << srt_getlasterror_str() << std::endl;
                break;
            }
            file.write(buf, ret);
            total_received += ret;
        }

        SRT_TRACEBSTATS stats;
        if (srt_bistats(client, &stats, 0, 1) == 0) {
            std::cout << "[Stats] RTT=" << stats.msRTT << "ms"
                      << " Recv=" << stats.mbpsRecvRate << "Mbps"
                      << " Loss=" << stats.pktRcvLoss << std::endl;
        }

        srt_close(client);
        std::cout << "Received " << total_received
                  << " bytes → " << output_path << std::endl;
        return true;
    }

    void Close() {
        if (listen_sock_ != SRT_INVALID_SOCK) {
            srt_close(listen_sock_);
            listen_sock_ = SRT_INVALID_SOCK;
        }
    }

private:
    int port_;
    int latency_ms_;
    SRTSOCKET listen_sock_ = SRT_INVALID_SOCK;
};

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0]
                  << " <port> <output.ts>" << std::endl;
        return 1;
    }

    signal(SIGINT, SignalHandler);
    srt_startup();

    SRTReceiver receiver(std::atoi(argv[1]), 500);
    if (receiver.Listen()) {
        receiver.AcceptAndReceive(argv[2]);
    }

    srt_cleanup();
    return 0;
}
```

### CMake 构建配置

```cmake
cmake_minimum_required(VERSION 3.16)
project(srt_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(SRT REQUIRED srt)

add_executable(srt_sender srt_sender.cpp)
target_include_directories(srt_sender PRIVATE ${SRT_INCLUDE_DIRS})
target_link_libraries(srt_sender ${SRT_LIBRARIES} pthread)

add_executable(srt_receiver srt_receiver.cpp)
target_include_directories(srt_receiver PRIVATE ${SRT_INCLUDE_DIRS})
target_link_libraries(srt_receiver ${SRT_LIBRARIES} pthread)
```

构建与运行：

```bash
mkdir build && cd build
cmake ..
make -j$(nproc)

# 终端 1：启动接收端
./srt_receiver 9000 output.ts

# 终端 2：启动发送端
./srt_sender 127.0.0.1 9000 input.ts
```

### 用 FFmpeg 测试互通

libsrt 实现的收发端可以直接与 FFmpeg 互通，这是验证正确性最便捷的方式：

```bash
# 用 FFmpeg 向我们的 Listener 推流
ffmpeg -re -i input.mp4 -c copy -f mpegts srt://127.0.0.1:9000

# 用 FFmpeg 从我们的 Listener 拉流（需要把 Receiver 改为转发模式，或直接用 srt-live-transmit）
srt-live-transmit srt://:9000 srt://127.0.0.1:9001

# 用 FFplay 从 SRT 源播放
ffplay srt://127.0.0.1:9000
```

`srt-live-transmit` 是 libsrt 自带的传输工具，支持 SRT 到 SRT、SRT 到 UDP 等多种转发模式，非常适合快速验证和调试。

---

## 7. SRT vs RTMP 性能对比

SRT 经常被拿来与 RTMP 对比，因为两者在"推流到平台"这个场景中存在直接竞争关系。

### 延迟对比

| 维度 | SRT | RTMP |
|------|-----|------|
| **传输层** | UDP | TCP |
| **典型端到端延迟** | 200ms ~ 1500ms | 1s ~ 3s |
| **弱网下的延迟** | 可控（受 latency 参数约束） | 不可控（TCP 重传 + 拥塞控制导致累积） |
| **延迟抖动** | 小（接收端按时间戳重新排列） | 大（TCP 队头阻塞） |

SRT 的核心优势在于**延迟可控**。TCP 在丢包时的行为是不可预测的——一次 tail drop 可能触发指数退避，延迟瞬间飙升到数秒。SRT 通过 latency 参数给延迟设置了硬上限。

### 丢包恢复能力

RTMP 基于 TCP，丢包恢复完全依赖 TCP 协议栈的重传机制。TCP 的重传是"不计代价"的：即使一个包已经过时了，TCP 仍然会重传它，并且在重传完成前阻塞后续所有数据。

SRT 的 ARQ 机制更加灵活：

- **选择性重传**：只重传丢失的包，不阻塞后续数据
- **有时限的重传**：超过 latency 窗口的包放弃重传
- **NAK 主动请求**：不依赖超时检测，丢包响应更快

在 5% 丢包率的网络上，RTMP 基本无法正常使用（TCP 重传风暴导致延迟飙升），而 SRT 在合理设置 latency 的情况下仍能保持稳定传输。

### 安全性

| 维度 | SRT | RTMP |
|------|-----|------|
| **加密** | 内置 AES-128/256 | 无内置加密 |
| **认证** | Passphrase | 无标准认证机制 |
| **安全传输** | 原生支持 | 需要外挂 RTMPS（TLS） |

RTMP 协议本身没有加密机制，敏感内容传输需要使用 RTMPS（RTMP over TLS），但 RTMPS 的兼容性和部署成本都高于 SRT 的原生加密。

### 适用场景

| 场景 | 推荐 | 理由 |
|------|------|------|
| **稳定内网推流** | RTMP | 生态成熟，工具链完善，延迟可接受 |
| **不稳定公网推流** | SRT | 抗丢包能力强，延迟可控 |
| **跨国/跨洲传输** | SRT | 高 RTT + 丢包场景下 TCP 表现极差 |
| **广电级信号回传** | SRT | 低延迟 + 加密 + 可靠性 |
| **CDN 推流入口** | 两者皆可 | 主流 CDN 已支持 SRT 收流 |
| **赛事/远程制作** | SRT | 延迟要求严格，网络环境复杂 |

总的来说，RTMP 仍然在内容分发生态中有稳固的地位（大量 CDN 和工具链的支持），但在"第一公里"传输场景中，SRT 已经成为事实上的新标准。越来越多的编码器、流媒体服务器（如 SRS、OBS、vMix）都已支持 SRT。

---

## 总结

本文从协议设计、连接模型、ARQ 重传、加密认证到实战编码，系统地探讨了 SRT 协议的核心技术。回顾关键要点：

- **SRT 基于 UDP 构建**，通过有时限的 ARQ 重传在可靠性和低延迟之间取得平衡，这是它区别于 TCP 类协议的根本设计哲学
- **两种连接模式**适配不同的网络拓扑：Caller-Listener 用于常规推拉流，Rendezvous 用于 NAT 穿越场景
- **Latency 参数**是 SRT 的核心调节旋钮，定义了从发送到交付的最大允许时间，需要根据 RTT 和丢包率合理设置
- **AES 加密和 Passphrase 认证**是原生内置的安全机制，在公网传输场景中不可或缺
- **libsrt API** 遵循 BSD Socket 风格，学习成本低，配合 `srt_bistats` 可以全面监控传输质量
- 相比 RTMP，SRT 在**抗丢包、低延迟、安全性**方面全面领先，是广电传输和远程制作的首选协议

SRT 解决了在不稳定网络上进行低延迟可靠传输的问题，但它本质上是一个点对点的传输协议，不涉及大规模分发。在实际系统中，SRT 通常负责"第一公里"的信号回传，到达平台后再通过 HLS/DASH 进行大规模 CDN 分发。

下一篇文章，我们将进入 **QUIC/HTTP3 在流媒体中的应用**，看看这个由 Google 推动的新一代传输协议如何在 UDP 之上重新定义 HTTP 传输，以及 MoQ（Media over QUIC）等新标准如何在低延迟和大规模分发之间寻找新的平衡点。
