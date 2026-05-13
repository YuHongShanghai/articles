# Reactor 模式与事件驱动网络框架

## 前言

如果你跟着前两篇文章走到了这里，应该已经能用 `epoll` 写出一个能处理多个客户端连接的服务器了。但你大概也感受到了一个问题——代码很快就变成了一锅粥。

accept 逻辑、read/write 逻辑、业务处理逻辑全部塞在一个大循环里，fd 和回调之间没有清晰的映射关系，想加个定时器或者改个协议解析，就得在 `while(1)` 里到处插代码。这种写法在连接数增长、业务变复杂后，维护成本会急剧上升。

业界早就给出了解决方案——**Reactor 模式**。几乎所有主流的流媒体服务器（SRS、live555、Janus、ZLMediaKit）和高性能网络库（muduo、libevent、Netty）都构建在这个模式之上。理解 Reactor，是读懂这些开源项目源码的第一把钥匙。

本文的目标很明确：先搞懂 Reactor 模式的设计哲学，然后用 C++ 从零实现一个轻量级的事件驱动框架，最后横向对比主流网络库，帮你在实际项目中做出合理选型。

---

## 1. Reactor 模式的核心思想

Reactor 模式的本质可以用一句话概括：**等待事件发生，然后分发给对应的处理函数**。

这和你在 GUI 编程中见到的消息循环是同一个思路——程序不主动轮询，而是被动地等待操作系统通知"某个 fd 上有事件了"，然后调用预先注册好的回调函数来处理。

Reactor 模式包含三个核心角色：

| 角色 | 职责 | 对应实现 |
|------|------|----------|
| **Demultiplexer**（事件分离器） | 等待并收集就绪事件 | `epoll_wait`、`select`、`poll` |
| **Dispatcher**（事件分发器） | 根据 fd 查找对应的 Handler 并调用 | EventLoop 中的分发逻辑 |
| **Handler**（事件处理器） | 处理具体的 I/O 和业务逻辑 | 用户注册的回调函数 |

整个工作流程如下：

1. 用户将 fd 和对应的事件回调注册到 Reactor
2. Reactor 调用 Demultiplexer 阻塞等待事件
3. 有事件就绪时，Dispatcher 根据 fd 找到对应的 Handler
4. 调用 Handler 的回调函数处理事件
5. 回到步骤 2，继续等待

![Reactor模式架构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/reactor_pattern.png)

这种设计带来的好处是**关注点分离**：事件的等待、分发、处理各自独立，新增业务只需注册新的 Handler，不用修改框架核心逻辑。

---

## 2. 单 Reactor 单线程模型

最简单的 Reactor 实现是单线程模型：一个线程既负责 `accept` 新连接，也负责所有已建立连接的 I/O 读写和业务处理。

![单Reactor单线程](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/single_reactor.png)

工作流程很直观：

1. 主循环中 `epoll_wait` 等待事件
2. 如果是 listen fd 上的可读事件，执行 `accept` 接入新连接
3. 如果是已连接 fd 上的可读事件，读取数据并处理业务
4. 如果是已连接 fd 上的可写事件，发送响应数据

**适用场景**：连接数较少（几十到几百）、业务处理耗时短（微秒级）的场景。Redis 6.0 之前就是典型的单 Reactor 单线程模型——它的瓶颈在内存和网络带宽，而不是 CPU。

**局限性**也很明显：如果某个连接的业务处理耗时较长（比如编解码、磁盘 I/O），就会阻塞整个事件循环，导致其他所有连接的延迟飙升。对于流媒体服务器来说，这是不可接受的——一个客户端的卡顿不应该影响其他客户端的播放体验。

---

## 3. 主从 Reactor 多线程模型

为了解决单线程模型的阻塞问题，业界演化出了**主从 Reactor 多线程模型**（也叫 Multi-Reactor 或 One Loop Per Thread）。

![主从Reactor多线程](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/multi_reactor.png)

核心架构分为三层：

**Main Reactor（主 Reactor）**：运行在主线程中，只负责一件事——监听 listen fd，`accept` 新连接。接入新连接后，按照某种策略（通常是 round-robin）将连接分配给某个 Sub Reactor。

**Sub Reactor（从 Reactor）**：每个 Sub Reactor 运行在独立线程中，拥有自己的 `epoll` 实例。它只负责已分配给自己的连接的 I/O 读写。每个 Sub Reactor 管理一批连接，互不干扰。

**Worker 线程池**（可选）：如果业务处理比较耗时（比如视频转码、数据库查询），可以将业务逻辑丢给线程池异步执行，避免阻塞 Sub Reactor 的事件循环。

这个模型的优势在于：

- **accept 不会被业务阻塞**：Main Reactor 专注于接入连接，响应极快
- **连接之间互不影响**：不同 Sub Reactor 在不同线程中运行
- **充分利用多核 CPU**：线程数通常设为 CPU 核心数

Nginx 的 master-worker 架构、Netty 的 Boss-Worker EventLoopGroup、muduo 的 one loop per thread，本质上都是这个模型的变体。在流媒体服务器中，SRS 也采用了类似的设计——Main Reactor 接入 RTMP/WebRTC 连接，Sub Reactor 处理各个连接上的音视频数据收发。

---

## 4. C++ 实战：实现一个轻量级 EventLoop

理论说够了，下面我们用 C++ 从零实现一个简化版的 Reactor 框架。目标是实现一个能跑起来的 echo server，让你对 Reactor 的骨架有直观感受。

我们需要三个核心类：

- **Channel**：封装 fd 和它的事件回调
- **EventLoop**：封装 epoll 事件循环和事件分发
- **TcpServer**：整合 accept 逻辑和连接管理

### 4.1 Channel：fd 与回调的绑定

Channel 是 fd 的代理对象，每个 fd 对应一个 Channel，Channel 持有该 fd 上各种事件的回调函数。

```cpp
// channel.h
#pragma once
#include <functional>
#include <sys/epoll.h>

class EventLoop;

class Channel {
public:
    using EventCallback = std::function<void()>;

    Channel(EventLoop* loop, int fd) : loop_(loop), fd_(fd) {}
    ~Channel() = default;

    int fd() const { return fd_; }
    uint32_t events() const { return events_; }
    void setRevents(uint32_t revents) { revents_ = revents; }

    void setReadCallback(EventCallback cb) { readCb_ = std::move(cb); }
    void setWriteCallback(EventCallback cb) { writeCb_ = std::move(cb); }
    void setErrorCallback(EventCallback cb) { errorCb_ = std::move(cb); }
    void setCloseCallback(EventCallback cb) { closeCb_ = std::move(cb); }

    void enableReading() { events_ |= EPOLLIN; update(); }
    void enableWriting() { events_ |= EPOLLOUT; update(); }
    void disableWriting() { events_ &= ~EPOLLOUT; update(); }
    void disableAll() { events_ = 0; update(); }

    void handleEvent() {
        if (revents_ & (EPOLLERR)) {
            if (errorCb_) errorCb_();
        }
        if (revents_ & (EPOLLHUP | EPOLLRDHUP)) {
            if (closeCb_) closeCb_();
        }
        if (revents_ & (EPOLLIN | EPOLLPRI)) {
            if (readCb_) readCb_();
        }
        if (revents_ & EPOLLOUT) {
            if (writeCb_) writeCb_();
        }
    }

private:
    void update();

    EventLoop* loop_;
    int fd_;
    uint32_t events_ = 0;
    uint32_t revents_ = 0;
    EventCallback readCb_, writeCb_, errorCb_, closeCb_;
};
```

设计要点：`events_` 记录该 Channel 关注哪些事件，`revents_` 记录实际发生了哪些事件。每次修改关注事件后调用 `update()` 通知 EventLoop 更新 epoll 注册。

### 4.2 EventLoop：事件循环的心脏

EventLoop 封装了 `epoll` 的创建、事件的注册/修改/删除，以及核心的事件循环。

```cpp
// eventloop.h
#pragma once
#include "channel.h"
#include <unordered_map>
#include <vector>
#include <sys/epoll.h>
#include <unistd.h>
#include <cstring>
#include <stdexcept>

class EventLoop {
public:
    EventLoop() {
        epollFd_ = epoll_create1(EPOLL_CLOEXEC);
        if (epollFd_ < 0) {
            throw std::runtime_error("epoll_create1 failed");
        }
        events_.resize(1024);
    }

    ~EventLoop() {
        ::close(epollFd_);
    }

    void loop() {
        running_ = true;
        while (running_) {
            int numEvents = epoll_wait(epollFd_, events_.data(),
                                       static_cast<int>(events_.size()), -1);
            if (numEvents < 0) {
                if (errno == EINTR) continue;
                break;
            }
            for (int i = 0; i < numEvents; ++i) {
                auto* channel = static_cast<Channel*>(events_[i].data.ptr);
                channel->setRevents(events_[i].events);
                channel->handleEvent();
            }
        }
    }

    void quit() { running_ = false; }

    void updateChannel(Channel* channel) {
        int fd = channel->fd();
        struct epoll_event ev;
        std::memset(&ev, 0, sizeof(ev));
        ev.events = channel->events();
        ev.data.ptr = channel;

        if (channels_.find(fd) == channels_.end()) {
            channels_[fd] = channel;
            epoll_ctl(epollFd_, EPOLL_CTL_ADD, fd, &ev);
        } else {
            epoll_ctl(epollFd_, EPOLL_CTL_MOD, fd, &ev);
        }
    }

    void removeChannel(Channel* channel) {
        int fd = channel->fd();
        channels_.erase(fd);
        epoll_ctl(epollFd_, EPOLL_CTL_DEL, fd, nullptr);
    }

private:
    int epollFd_ = -1;
    bool running_ = false;
    std::vector<struct epoll_event> events_;
    std::unordered_map<int, Channel*> channels_;
};

inline void Channel::update() {
    loop_->updateChannel(this);
}
```

注意 `epoll_event.data.ptr` 直接存储 Channel 指针，这样在事件就绪时可以 O(1) 找到对应的 Channel，不需要额外的查找表。

### 4.3 TcpServer：一个完整的 Echo Server

有了 Channel 和 EventLoop，我们可以组装一个完整的 TCP 服务器。

```cpp
// echo_server.cpp
#include "eventloop.h"
#include <iostream>
#include <memory>
#include <unordered_map>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <csignal>

void setNonBlocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

class TcpServer {
public:
    TcpServer(EventLoop* loop, uint16_t port) : loop_(loop) {
        listenFd_ = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);

        int opt = 1;
        setsockopt(listenFd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        struct sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(port);
        bind(listenFd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
        listen(listenFd_, SOMAXCONN);

        listenChannel_ = std::make_unique<Channel>(loop_, listenFd_);
        listenChannel_->setReadCallback([this]() { handleAccept(); });
        listenChannel_->enableReading();

        std::cout << "Server listening on port " << port << std::endl;
    }

    ~TcpServer() {
        ::close(listenFd_);
    }

private:
    void handleAccept() {
        struct sockaddr_in peerAddr{};
        socklen_t addrLen = sizeof(peerAddr);
        int connFd = accept4(listenFd_, reinterpret_cast<sockaddr*>(&peerAddr),
                             &addrLen, SOCK_NONBLOCK);
        if (connFd < 0) return;

        std::cout << "New connection from "
                  << inet_ntoa(peerAddr.sin_addr) << ":"
                  << ntohs(peerAddr.sin_port) << std::endl;

        auto channel = std::make_shared<Channel>(loop_, connFd);

        channel->setReadCallback([this, connFd, channel]() {
            char buf[4096];
            ssize_t n = read(connFd, buf, sizeof(buf));
            if (n > 0) {
                write(connFd, buf, n);
            } else {
                handleClose(connFd);
            }
        });

        channel->setCloseCallback([this, connFd]() {
            handleClose(connFd);
        });

        channel->enableReading();
        connections_[connFd] = channel;
    }

    void handleClose(int fd) {
        std::cout << "Connection closed: fd=" << fd << std::endl;
        auto it = connections_.find(fd);
        if (it != connections_.end()) {
            it->second->disableAll();
            loop_->removeChannel(it->second.get());
            connections_.erase(it);
        }
        ::close(fd);
    }

    EventLoop* loop_;
    int listenFd_;
    std::unique_ptr<Channel> listenChannel_;
    std::unordered_map<int, std::shared_ptr<Channel>> connections_;
};

int main() {
    std::signal(SIGPIPE, SIG_IGN);

    EventLoop loop;
    TcpServer server(&loop, 9527);
    loop.loop();

    return 0;
}
```

编译并测试：

```bash
g++ -std=c++14 -o echo_server echo_server.cpp -lpthread
./echo_server

# 另一个终端
echo "hello reactor" | nc localhost 9527
```

收到 "hello reactor" 的回显，说明我们的 Reactor 框架已经跑通了。

回头看这段代码，和文章开头提到的 epoll 裸写相比：

- **fd 和回调绑定在 Channel 中**，不再需要在循环里用 if-else 判断 fd 类型
- **EventLoop 屏蔽了 epoll 的细节**，上层只需要关注业务回调
- **新增连接类型只需创建新的 Channel**，框架核心不用改动

这就是 Reactor 模式带来的代码结构改善。当然，这是一个教学版本，生产级的实现还需要处理缓冲区管理、优雅关闭、定时器、跨线程唤醒等问题。

---

## 5. 成熟网络库对比

自己造轮子适合学习，但在生产环境中，通常会选择成熟的网络库。以下是流媒体开发中常见的几个选择：

| 网络库 | 语言 | 模式 | 跨平台 | 特点 | 典型应用 |
|--------|------|------|--------|------|----------|
| **libevent** | C | Reactor | 是 | 轻量、稳定，API 是 C 风格回调 | memcached、NTP |
| **libuv** | C | Proactor 风格 | 是 | 事件循环 + 线程池，抽象层较厚 | Node.js、luvit |
| **Boost.Asio** | C++ | Proactor | 是 | 模板重度使用，灵活但学习曲线陡峭 | 各类 C++ 服务端 |
| **muduo** | C++ | Reactor | Linux | One Loop Per Thread，代码清晰，教科书实现 | 适合学习和中小项目 |
| **libevent + FFmpeg** | C | Reactor | 是 | 流媒体领域常见组合 | 自研流媒体服务器 |

**选型建议**：

- 如果目标是**学习 Reactor 模式**，首推陈硕的 muduo，代码质量高，配套书籍《Linux 多线程服务端编程》讲解透彻
- 如果需要**跨平台**且项目是 C++，Boost.Asio 是工业级选择，C++20 协程加持后使用体验大幅改善
- 如果是**嵌入式或资源受限**环境，libevent 的轻量级和 C 接口更合适
- 如果团队已经在用 **Node.js 技术栈**，libuv 的事件模型与之无缝衔接

muduo 的代码结构和我们第 4 节实现的框架非常相似——Channel、EventLoop、TcpServer 这些概念是一一对应的。实际上，muduo 正是这套设计范式的标杆实现。

---

## 6. Proactor 模式简介

说完 Reactor，有必要提一下它的"对手"——**Proactor 模式**。

两者的核心区别在于**谁来执行实际的 I/O 操作**：

| | Reactor | Proactor |
|--|---------|----------|
| **I/O 操作** | 应用程序自己执行（read/write） | 操作系统/框架代为执行 |
| **通知时机** | 通知"fd 就绪，你可以读了" | 通知"数据已经读好了，给你" |
| **编程模型** | 同步非阻塞 I/O | 异步 I/O |
| **典型实现** | Linux epoll、BSD kqueue | Windows IOCP |

用一个生活类比：Reactor 像是餐厅告诉你"你的菜好了，自己来端"；Proactor 像是服务员直接把菜端到你桌上。

Windows 的 IOCP（I/O Completion Port）是最经典的 Proactor 实现。Boost.Asio 在 Windows 上使用 IOCP，在 Linux 上用 epoll 模拟 Proactor 行为，实现了跨平台的统一 API。

Linux 近年来引入的 `io_uring` 终于为 Linux 带来了真正的内核级异步 I/O 支持，是 Linux 世界的 Proactor。不过目前 `io_uring` 在流媒体服务器中的应用还不多，主流项目（SRS、ZLMediaKit、Janus）仍然是 epoll + Reactor 的组合。

**为什么流媒体开发中 Reactor 更常见？**

1. Linux 是流媒体服务器的主要部署平台，epoll 是最成熟的 I/O 多路复用机制
2. 流媒体的 I/O 模式相对固定（接收音视频包、转发音视频包），Reactor 的同步读写模型足够高效
3. 大量开源项目和参考实现都基于 Reactor，生态成熟

---

## 总结

回顾一下本文的核心内容：

- **Reactor 模式**将事件的等待、分发、处理三个关注点分离，是构建高性能网络服务器的基础架构模式
- **单 Reactor 单线程**模型简单但存在阻塞风险，**主从 Reactor 多线程**模型通过分工协作解决了这个问题
- 我们用 C++ 实现了 Channel、EventLoop、TcpServer 三个核心组件，搭建了一个最小可运行的 Reactor 框架
- 生产环境中应根据平台、语言、性能需求选择合适的成熟网络库
- Reactor 和 Proactor 各有适用场景，流媒体开发中 Reactor 目前仍是主流

理解了 Reactor 模式，你再去看 SRS 的 `SrsServer`、live555 的 `TaskScheduler`、Janus 的事件循环，就会发现它们的骨架都是我们今天实现的这套东西——Channel 负责封装 fd，EventLoop 负责事件驱动，上层业务只需注册回调。

下一篇我们将进入**网络性能优化**的话题，探讨 TCP 调优、零拷贝、用户态协议栈等在流媒体场景中的实战技巧。掌握了 Reactor 框架之后，这些优化手段才能真正落地。
