# WebRTC 整体架构与信令设计

## 前言

如果你一路跟随本系列走到这里，已经掌握了网络编程基础、RTP/RTCP 传输机制、SDP 媒体协商、RTSP/RTMP 等经典协议，以及 HLS/DASH/SRT/QUIC 等现代流媒体方案。这些知识拼在一起，恰好构成了理解 WebRTC 所需的全部前置积累。

WebRTC（Web Real-Time Communication）是 Google 在 2011 年开源的实时通信技术，并于 2021 年成为 W3C 和 IETF 的正式标准。它最初为浏览器设计——两个 Chrome 标签页之间不装任何插件就能视频通话，这在当年是革命性的。但 WebRTC 的影响力远不止于浏览器。它的 Native 实现（libwebrtc）被广泛用于移动端 App、桌面客户端、嵌入式设备，甚至服务端的 SFU/MCU 媒体服务器。

WebRTC 并不是一个单一协议，而是一整套协议栈和 API 的集合。它把我们前面学过的 RTP/RTCP、SDP、DTLS、ICE 等协议粘合在一起，形成了一个端到端的实时通信框架。本文作为 WebRTC 系列的开篇，目标是建立全局视野——理解协议栈的分层结构、通信建连的完整流程、信令服务器的设计思路，以及 PeerConnection 的生命周期。最后，我们用 C++ 实现一个完整的 WebSocket 信令服务器，为后续的实战打下基础。

---

## 1. WebRTC 协议栈全景图

WebRTC 的协议栈可以从底到顶分为四层，每一层都有明确的职责。

### 传输层：NAT 穿越

互联网上的大多数设备都藏在 NAT（Network Address Translation）后面，没有公网 IP。两个 NAT 后面的设备要直接通信，首先要解决"找到对方"的问题。WebRTC 使用 **ICE**（Interactive Connectivity Establishment）框架来完成这件事，它底层依赖两个协议：

- **STUN**（Session Traversal Utilities for NAT）：向公网上的 STUN 服务器查询自己的公网地址和端口映射，用于尝试 NAT 穿越。
- **TURN**（Traversal Using Relays around NAT）：当 NAT 穿越失败时（如对称型 NAT），通过 TURN 服务器中继媒体数据。

ICE 的工作模式是"尽力直连，直连不行就中继"，这保证了在各种网络环境下都能建立连接。

### 安全层：加密传输

WebRTC 强制要求所有媒体数据加密传输，这是其区别于传统 RTP 方案的一大特点：

- **DTLS**（Datagram Transport Layer Security）：TLS 的 UDP 版本，在 UDP 之上完成密钥协商和身份认证。
- **SRTP**（Secure Real-time Transport Protocol）：用 DTLS 协商出的密钥加密 RTP/RTCP 数据包。

这种 DTLS-SRTP 的组合实现了端到端加密——即使数据经过 TURN 服务器中继，中继服务器也无法解密媒体内容。

### 媒体层：数据传输

这一层负责实际的音视频和数据传输：

- **RTP/RTCP**：我们在前面的文章中已经详细介绍过。RTP 承载媒体数据，RTCP 提供质量反馈（丢包率、延迟、抖动等）。
- **SCTP**（Stream Control Transmission Protocol）：承载 DataChannel 的数据，运行在 DTLS 之上。它支持有序/无序、可靠/不可靠等多种传输模式。

### 应用层：引擎与 API

最上层是面向开发者的引擎和接口：

- **音频引擎**：负责音频采集、编码（Opus）、回声消除（AEC）、噪声抑制（NS）、自动增益控制（AGC）。
- **视频引擎**：负责视频采集、编码（VP8/VP9/H.264/AV1）、渲染。
- **DataChannel API**：提供类似 WebSocket 的双向数据通道，基于 SCTP over DTLS over UDP，支持可靠/不可靠、有序/无序等多种传输模式。
- **PeerConnection API**：统一管理以上所有功能的核心接口。

![WebRTC协议栈](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/webrtc_stack.png)

回顾一下前面所学的内容：RTP/RTCP 的报文格式和反馈机制、SDP 的 Offer/Answer 协商模型、DTLS 握手流程——这些知识在 WebRTC 中全部派上用场。WebRTC 并没有重新发明轮子，而是把这些成熟的协议组合成了一个完整的端到端方案。

---

## 2. WebRTC 通信流程概览

两个 WebRTC 端点从"互不相识"到"音视频畅通"，需要经过以下四个阶段。

### 阶段一：信令交换（SDP Offer/Answer）

WebRTC 复用了 SDP 的 Offer/Answer 模型来进行媒体协商。发起方（Offerer）创建一个包含自身媒体能力的 SDP Offer（支持哪些编解码器、想发送几路音视频、DTLS 指纹等），通过信令服务器发送给应答方。应答方收到后，根据自身能力生成 SDP Answer 回复。

这一步解决的核心问题是：双方就"用什么编码、多少路流、怎么加密"达成一致。

### 阶段二：ICE 候选收集与交换

在创建 SDP 的同时，双方各自启动 ICE Agent，收集自己的连接候选地址（Candidate）：

- **Host Candidate**：本机的真实 IP 和端口（可能是内网地址）。
- **Server Reflexive Candidate（srflx）**：通过 STUN 服务器发现的公网映射地址。
- **Relay Candidate**：TURN 服务器分配的中继地址。

候选地址通过信令服务器交换给对端后，ICE Agent 开始对所有候选对进行**连通性检查**（发送 STUN Binding Request），找到双方之间延迟最低、可通的路径。

### 阶段三：DTLS 握手

ICE 选出最佳传输路径后，双方在该路径上执行 DTLS 握手。这个过程与 TLS 握手类似，但运行在 UDP 之上：交换证书、验证身份、协商加密套件、导出 SRTP 密钥。

DTLS 握手完成后，双方共享了用于加密媒体数据的密钥材料。

### 阶段四：SRTP 媒体传输

一切就绪后，音视频数据以 SRTP 包的形式在 ICE 选出的路径上传输。RTCP 包也会被加密为 SRTCP。此时，实时通信正式建立。

![WebRTC通信流程](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/webrtc_flow.png)

整个流程可以浓缩为一句话：**用信令交换"怎么通信"的信息（SDP + ICE Candidate），然后在直连或中继的 UDP 通道上建立加密的媒体传输**。

---

## 3. 信令服务器的角色与设计

### WebRTC 不定义信令协议

这是 WebRTC 设计中最常让新手困惑的一点：**WebRTC 标准故意不定义信令协议**。它只规定了 SDP 的格式和 ICE 候选的结构，但"怎么把这些数据从 A 传给 B"完全由开发者自己决定。

这既是自由，也是负担。自由在于你可以用任何现有的通信机制来实现信令；负担在于你必须自己设计和实现这套系统。

### 信令的三大职责

无论使用什么传输协议，信令服务器都需要完成以下职责：

**1. 交换 SDP**

将 Offerer 生成的 SDP Offer 转发给 Answerer，将 Answerer 的 SDP Answer 转发回 Offerer。SDP 中包含了媒体协商的所有信息：支持的编解码器列表及优先级、媒体流的数量和方向（sendrecv/sendonly/recvonly）、ICE 参数（ufrag/password）、DTLS 指纹（fingerprint）等。

**2. 交换 ICE Candidate**

ICE 候选地址的收集是异步的（特别是 STUN/TURN 查询需要网络往返），候选会陆续产生。信令服务器需要实时将每个新产生的候选转发给对端。这个过程叫做 **Trickle ICE**——边收集边发送，而不是等所有候选收集完毕再一起发。

**3. 房间管理**

在实际应用中，信令服务器还需要管理"谁和谁通话"的逻辑：用户加入/离开房间的通知、房间内的成员列表、通话发起/挂断控制等。

### 常见信令方案

**WebSocket**：最常见的选择。全双工、低延迟、浏览器原生支持。信令消息通常用 JSON 编码，简单直观。绝大多数 WebRTC 应用和教程都采用这个方案。

**SIP（Session Initiation Protocol）**：电信行业的标准信令协议。如果你的 WebRTC 系统需要与传统电话网络（PSTN）互通，SIP 是必选项。但 SIP 协议本身比较复杂，对于纯互联网应用来说是"杀鸡用牛刀"。

**HTTP 轮询/SSE**：技术上可行，但体验较差。HTTP 轮询延迟高且浪费带宽；SSE（Server-Sent Events）是单向的，仍需配合 HTTP POST 发送消息，不如 WebSocket 优雅。

### 为什么 WebSocket 是最佳选择

对于大多数 WebRTC 应用来说，WebSocket 是信令传输的首选方案，原因很直接：

- **全双工**：服务端可以主动推送消息（新的 ICE Candidate、对端的 SDP Answer），无需客户端轮询。
- **低延迟**：建连后消息在已有的 TCP 连接上传输，没有 HTTP 请求/响应的额外开销。
- **生态完善**：浏览器端有原生 WebSocket API，C++ 端有 websocketpp、Boost.Beast、libwebsockets 等成熟库。
- **简单可靠**：JSON over WebSocket 的方案人人能读懂，调试方便。

---

## 4. PeerConnection 生命周期

`RTCPeerConnection` 是 WebRTC 的核心 API，它封装了 ICE、DTLS、RTP/RTCP、SCTP 等所有子系统。理解它的状态机和关键事件，是正确使用 WebRTC 的基础。

### 状态机

PeerConnection 维护着多个相互关联的状态：

**Signaling State**（信令状态）：跟踪 SDP Offer/Answer 的交换进度。

```
发起方：stable → have-local-offer  → stable
应答方：stable → have-remote-offer → stable
```

- `stable`：没有正在进行的 SDP 交换，初始状态和每次协商完成后的状态。
- `have-local-offer`：本端已调用 `setLocalDescription(offer)`，等待对端的 Answer。收到 Answer 并调用 `setRemoteDescription(answer)` 后回到 `stable`。
- `have-remote-offer`：收到了对端的 Offer（调用 `setRemoteDescription(offer)`），等待本端生成 Answer。调用 `setLocalDescription(answer)` 后回到 `stable`。

**ICE Connection State**（ICE 连接状态）：反映 ICE 连通性检查的进展。

```
new → checking → connected → completed
                     ↓
                disconnected → failed
```

- `checking`：ICE Agent 正在进行连通性检查。
- `connected`：至少找到一对可用的候选对。
- `completed`：所有候选对检查完毕，选出了最佳路径。
- `disconnected`/`failed`：连接中断或所有候选对都失败。

**Connection State**（整体连接状态）：综合 ICE 和 DTLS 的状态，给出一个简化的整体视图。

```
new → connecting → connected → disconnected → failed → closed
```

### 关键回调事件

**`onicecandidate`**

每当 ICE Agent 收集到一个新的候选地址时触发。开发者需要在这个回调中将候选通过信令服务器发送给对端。当候选收集完毕时，事件的 `candidate` 字段为 `null`。

```cpp
peer_connection->onLocalCandidate([&](rtc::Candidate candidate) {
    json msg;
    msg["type"] = "candidate";
    msg["candidate"] = candidate.candidate();
    msg["sdpMid"] = candidate.mid();
    signaling->send(msg.dump());
});
```

**`ontrack`**

收到对端的媒体轨道时触发。这是获取远端音视频数据的入口：

```cpp
peer_connection->onTrack([](std::shared_ptr<rtc::Track> track) {
    track->onMessage([](rtc::message_variant data) {
        // 处理接收到的 RTP 包
    });
});
```

**`oniceconnectionstatechange`**

ICE 连接状态变化时触发。开发者通常在这里处理连接成功的 UI 更新和断线重连逻辑。

**`onnegotiationneeded`**

当 PeerConnection 的媒体配置发生变化（如添加/移除 Track）时触发，提示开发者需要重新进行一次 SDP 协商。

### Perfect Negotiation 模式

在实际应用中，双方可能同时发起协商（例如双方同时添加了新的媒体轨道），这会导致 SDP Offer 冲突——被称为"glare"问题。

**Perfect Negotiation** 是 WebRTC 推荐的协商模式，核心思想是为两端分配不对称的角色：

- **Polite peer**（礼貌方）：当收到对端 Offer 时，如果自己也有一个未完成的 Offer，主动回滚自己的 Offer，优先处理对方的。
- **Impolite peer**（强硬方）：忽略冲突，坚持自己的 Offer。

这套规则确保在任何情况下都能收敛到稳定状态，避免死锁。伪代码如下：

```cpp
void OnRemoteOffer(const std::string& sdp) {
    bool collision = (signaling_state != "stable") || is_making_offer_;

    if (collision && is_impolite_) {
        return;  // 强硬方：忽略对方的 Offer
    }

    if (collision) {
        // 礼貌方：回滚自己的 Offer
        peer_connection->setLocalDescription(rollback);
    }

    peer_connection->setRemoteDescription(sdp);
    auto answer = peer_connection->createAnswer();
    peer_connection->setLocalDescription(answer);
    signaling->send(answer);
}
```

---

## 5. C++ 实战：搭建 WebSocket 信令服务器

理论讲完了，接下来用 C++ 实现一个完整的 WebSocket 信令服务器。我们使用 **Boost.Beast** 库——它是 Boost 生态的一部分，基于 Boost.Asio 构建，API 设计优雅，适合生产环境使用。

### 信令消息设计

信令消息采用 JSON 格式，定义以下几种类型：

```json
// 加入房间
{"type": "join", "roomId": "room-001", "peerId": "peer-abc"}

// 离开房间
{"type": "leave", "roomId": "room-001", "peerId": "peer-abc"}

// SDP Offer
{"type": "offer", "roomId": "room-001", "from": "peer-abc", "to": "peer-xyz", "sdp": "v=0\r\n..."}

// SDP Answer
{"type": "answer", "roomId": "room-001", "from": "peer-xyz", "to": "peer-abc", "sdp": "v=0\r\n..."}

// ICE Candidate
{"type": "candidate", "roomId": "room-001", "from": "peer-abc", "to": "peer-xyz",
 "candidate": "candidate:...", "sdpMid": "0"}
```

设计要点：每条消息都携带 `roomId` 和 `from`/`to` 字段，信令服务器根据这些字段做消息路由，不需要解析 SDP 内容本身。

### 完整实现

以下代码依赖 Boost 1.70+ 和 nlohmann/json，使用 CMake 构建：

```cpp
#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/strand.hpp>
#include <nlohmann/json.hpp>

#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace beast = boost::beast;
namespace websocket = beast::websocket;
namespace net = boost::asio;
using tcp = net::ip::tcp;
using json = nlohmann::json;

class Session;
using SessionPtr = std::shared_ptr<Session>;

// ---- 房间管理 ----

class RoomManager {
public:
    void Join(const std::string& room_id, const std::string& peer_id,
              SessionPtr session) {
        std::lock_guard<std::mutex> lock(mutex_);
        rooms_[room_id][peer_id] = session;
    }

    void Leave(const std::string& room_id, const std::string& peer_id) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto room_it = rooms_.find(room_id);
        if (room_it == rooms_.end()) return;
        room_it->second.erase(peer_id);
        if (room_it->second.empty()) {
            rooms_.erase(room_it);
        }
    }

    SessionPtr FindPeer(const std::string& room_id,
                        const std::string& peer_id) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto room_it = rooms_.find(room_id);
        if (room_it == rooms_.end()) return nullptr;
        auto peer_it = room_it->second.find(peer_id);
        if (peer_it == room_it->second.end()) return nullptr;
        return peer_it->second;
    }

    std::vector<std::string> GetPeers(const std::string& room_id,
                                      const std::string& exclude) {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<std::string> peers;
        auto room_it = rooms_.find(room_id);
        if (room_it == rooms_.end()) return peers;
        for (auto& [id, _] : room_it->second) {
            if (id != exclude) peers.push_back(id);
        }
        return peers;
    }

private:
    std::mutex mutex_;
    std::unordered_map<std::string,
        std::unordered_map<std::string, SessionPtr>> rooms_;
};

static RoomManager g_room_manager;

// ---- WebSocket 会话 ----

class Session : public std::enable_shared_from_this<Session> {
public:
    explicit Session(tcp::socket&& socket)
        : ws_(std::move(socket)) {}

    void Run() {
        ws_.async_accept(
            beast::bind_front_handler(&Session::OnAccept, shared_from_this()));
    }

    void Send(const std::string& msg) {
        net::post(ws_.get_executor(),
            beast::bind_front_handler(&Session::DoSend, shared_from_this(), msg));
    }

private:
    void OnAccept(beast::error_code ec) {
        if (ec) return;
        DoRead();
    }

    void DoRead() {
        ws_.async_read(buffer_,
            beast::bind_front_handler(&Session::OnRead, shared_from_this()));
    }

    void OnRead(beast::error_code ec, std::size_t bytes_transferred) {
        if (ec) {
            if (!peer_id_.empty() && !room_id_.empty()) {
                g_room_manager.Leave(room_id_, peer_id_);
                BroadcastLeave();
            }
            return;
        }

        std::string text = beast::buffers_to_string(buffer_.data());
        buffer_.consume(buffer_.size());

        HandleMessage(text);
        DoRead();
    }

    void HandleMessage(const std::string& text) {
        json msg;
        try { msg = json::parse(text); }
        catch (...) { return; }

        std::string type = msg.value("type", "");

        if (type == "join") {
            room_id_ = msg.value("roomId", "");
            peer_id_ = msg.value("peerId", "");
            if (room_id_.empty() || peer_id_.empty()) return;

            auto existing_peers = g_room_manager.GetPeers(room_id_, peer_id_);
            g_room_manager.Join(room_id_, peer_id_, shared_from_this());

            json peers_msg;
            peers_msg["type"] = "peers";
            peers_msg["peers"] = existing_peers;
            Send(peers_msg.dump());

            json join_msg;
            join_msg["type"] = "peer-joined";
            join_msg["peerId"] = peer_id_;
            for (auto& pid : existing_peers) {
                auto s = g_room_manager.FindPeer(room_id_, pid);
                if (s) s->Send(join_msg.dump());
            }

            std::cout << "[" << room_id_ << "] " << peer_id_
                      << " joined" << std::endl;

        } else if (type == "offer" || type == "answer" || type == "candidate") {
            std::string to = msg.value("to", "");
            if (to.empty()) return;
            msg["from"] = peer_id_;
            auto target = g_room_manager.FindPeer(room_id_, to);
            if (target) target->Send(msg.dump());

        } else if (type == "leave") {
            if (!peer_id_.empty() && !room_id_.empty()) {
                g_room_manager.Leave(room_id_, peer_id_);
                BroadcastLeave();
            }
        }
    }

    void BroadcastLeave() {
        json leave_msg;
        leave_msg["type"] = "peer-left";
        leave_msg["peerId"] = peer_id_;
        auto peers = g_room_manager.GetPeers(room_id_, peer_id_);
        for (auto& pid : peers) {
            auto s = g_room_manager.FindPeer(room_id_, pid);
            if (s) s->Send(leave_msg.dump());
        }
        std::cout << "[" << room_id_ << "] " << peer_id_
                  << " left" << std::endl;
    }

    void DoSend(const std::string& msg) {
        send_queue_.push_back(msg);
        if (send_queue_.size() > 1) return;
        DoWrite();
    }

    void DoWrite() {
        ws_.async_write(
            net::buffer(send_queue_.front()),
            beast::bind_front_handler(&Session::OnWrite, shared_from_this()));
    }

    void OnWrite(beast::error_code ec, std::size_t) {
        if (ec) return;
        send_queue_.erase(send_queue_.begin());
        if (!send_queue_.empty()) DoWrite();
    }

    websocket::stream<beast::tcp_stream> ws_;
    beast::flat_buffer buffer_;
    std::vector<std::string> send_queue_;
    std::string room_id_;
    std::string peer_id_;
};

// ---- 监听器 ----

class Listener : public std::enable_shared_from_this<Listener> {
public:
    Listener(net::io_context& ioc, tcp::endpoint endpoint)
        : ioc_(ioc), acceptor_(net::make_strand(ioc)) {
        acceptor_.open(endpoint.protocol());
        acceptor_.set_option(net::socket_base::reuse_address(true));
        acceptor_.bind(endpoint);
        acceptor_.listen(net::socket_base::max_listen_connections);
    }

    void Run() { DoAccept(); }

private:
    void DoAccept() {
        acceptor_.async_accept(
            net::make_strand(ioc_),
            beast::bind_front_handler(&Listener::OnAccept, shared_from_this()));
    }

    void OnAccept(beast::error_code ec, tcp::socket socket) {
        if (!ec) {
            std::make_shared<Session>(std::move(socket))->Run();
        }
        DoAccept();
    }

    net::io_context& ioc_;
    tcp::acceptor acceptor_;
};

// ---- 主函数 ----

int main(int argc, char* argv[]) {
    uint16_t port = 8080;
    if (argc > 1) port = static_cast<uint16_t>(std::atoi(argv[1]));

    net::io_context ioc{1};

    std::make_shared<Listener>(
        ioc, tcp::endpoint{tcp::v4(), port})->Run();

    std::cout << "Signaling server listening on ws://0.0.0.0:"
              << port << std::endl;

    ioc.run();
    return 0;
}
```

CMakeLists.txt 参考配置：

```cmake
cmake_minimum_required(VERSION 3.16)
project(webrtc_signaling)

set(CMAKE_CXX_STANDARD 17)

find_package(Boost REQUIRED COMPONENTS system)
find_package(nlohmann_json REQUIRED)

add_executable(signaling_server signaling_server.cpp)
target_link_libraries(signaling_server
    Boost::system
    nlohmann_json::nlohmann_json
    pthread
)
```

### 测试页面

搭配一个简单的 HTML 页面来验证信令服务器的消息收发：

```html
<!DOCTYPE html>
<html>
<head><title>WebRTC Signaling Test</title></head>
<body>
<h2>信令服务器测试</h2>
<div>
    <input id="room" placeholder="房间号" value="test-room">
    <input id="peer" placeholder="Peer ID" value="">
    <button onclick="connect()">加入房间</button>
    <button onclick="leave()">离开</button>
</div>
<pre id="log" style="background:#1e1e1e;color:#d4d4d4;padding:16px;
     margin-top:12px;height:400px;overflow-y:auto;border-radius:6px;"></pre>

<script>
let ws = null;

function log(msg) {
    const el = document.getElementById('log');
    el.textContent += new Date().toLocaleTimeString() + ' ' + msg + '\n';
    el.scrollTop = el.scrollHeight;
}

function connect() {
    const room = document.getElementById('room').value;
    const peer = document.getElementById('peer').value ||
                 'peer-' + Math.random().toString(36).substr(2, 6);
    document.getElementById('peer').value = peer;

    ws = new WebSocket('ws://localhost:8080');
    ws.onopen = () => {
        log('>>> Connected');
        ws.send(JSON.stringify({type: 'join', roomId: room, peerId: peer}));
    };
    ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        log('<<< ' + JSON.stringify(msg, null, 2));

        if (msg.type === 'peer-joined') {
            log('--- New peer: ' + msg.peerId + ', should create offer');
        }
    };
    ws.onclose = () => log('>>> Disconnected');
}

function leave() {
    if (ws) { ws.close(); ws = null; }
}
</script>
</body>
</html>
```

在两个浏览器标签页中分别打开这个页面，输入相同的房间号、不同的 Peer ID，加入房间后即可看到 `peer-joined` 消息互相通知。这就是信令服务器最基本的工作方式——后续只需在 `onmessage` 回调中处理 `offer`、`answer`、`candidate` 消息并转交给 `RTCPeerConnection`，就能建立完整的 WebRTC 通话。

---

## 6. WebRTC 的应用场景

WebRTC 的低延迟和端到端能力使其远远超出了"浏览器视频通话"的范畴，以下是几个典型的应用领域。

### 1 对 1 视频通话

这是 WebRTC 最经典的应用场景。两个端点通过信令服务器交换 SDP 和 ICE Candidate，然后建立 P2P 连接直接传输音视频。延迟通常在 100-300ms 之间，体验接近面对面交谈。典型代表：Google Meet 的 1v1 模式、微信/FaceTime 的视频通话。

### 多人视频会议（SFU/MCU）

当参与者超过 2 人时，全网状 P2P 模式的带宽消耗会二次方增长（连接数为 N×(N-1)/2，每个参与者需要向其他所有人发送音视频）。工程上通常引入媒体服务器：

- **SFU（Selective Forwarding Unit）**：接收每个参与者的一路上行流，选择性地转发给其他人。不做编解码，延迟低，是当前主流方案。代表开源项目：Janus、mediasoup、Pion。
- **MCU（Multipoint Control Unit）**：将所有参与者的音视频混合成一路流再分发。服务器计算开销大，但客户端只需接收一路流，带宽要求低。

### 直播连麦

主播与观众或嘉宾实时互动。主播端和连麦嘉宾之间用 WebRTC 实现低延迟通信，SFU 将各路流转发给一个混流服务（Compositor），混流后推送给 CDN，普通观众通过 HLS/FLV 观看。这种 WebRTC + CDN 的混合架构兼顾了实时性和大规模分发。

### 低延迟直播（WHIP/WHEP）

**WHIP**（WebRTC-HTTP Ingestion Protocol）和 **WHEP**（WebRTC-HTTP Egress Protocol）是 IETF 定义的标准化协议，将 WebRTC 的信令过程简化为一次 HTTP POST 请求。WHIP 用于推流（Ingest），WHEP 用于拉流（Egress），实现了亚秒级端到端延迟的直播体验。这种方案正在成为低延迟直播的新标准，SRS、OBS 等项目已经支持。

### 云游戏与远程桌面

云游戏服务器在云端运行游戏，将画面编码后通过 WebRTC 实时传输给玩家的设备，同时通过 DataChannel 接收玩家的操作输入。WebRTC 的低延迟特性（目标 < 50ms 端到端）对这类场景至关重要。Google Stadia（已停止服务）和 NVIDIA GeForce NOW 都使用了 WebRTC 或类似的技术栈。远程桌面软件（如 Chrome Remote Desktop）同样基于 WebRTC 构建。

### 物联网实时监控

安防摄像头、无人机、工业传感器等 IoT 设备可以通过 WebRTC 将实时画面推送到浏览器或控制中心。相比传统的 RTSP 方案，WebRTC 的优势在于：原生支持 NAT 穿越（设备通常在内网）、浏览器无需插件直接播放、端到端加密保障安全。

---

## 总结

本文作为 WebRTC 系列的开篇，从全局视角勾勒了 WebRTC 的技术全貌。回顾关键知识点：

- **协议栈分层**：ICE/STUN/TURN（穿越）→ DTLS/SRTP（加密）→ RTP/RTCP/SCTP（传输）→ 音视频引擎 + DataChannel（应用），每一层各司其职。
- **通信流程**：信令交换 SDP → ICE 候选收集与连通性检查 → DTLS 握手 → SRTP 加密传输，四个阶段环环相扣。
- **信令设计**：WebRTC 不定义信令协议，WebSocket + JSON 是最实用的方案。信令负责交换 SDP、ICE Candidate 和房间管理。
- **PeerConnection**：WebRTC 的核心 API，管理着信令状态、ICE 状态和整体连接状态三个状态机。Perfect Negotiation 解决了并发协商的冲突问题。
- **应用场景**：从 P2P 通话到大规模直播，从云游戏到物联网，WebRTC 的低延迟和穿越能力使其成为实时通信的基础设施。

有了这张全景图，后续的文章将逐一深入各个子系统。下一篇《**ICE/STUN/TURN：NAT 穿越全攻略**》，我们将详细剖析 NAT 的四种类型、ICE 候选的收集和配对算法、STUN 协议的报文格式，并用 coturn 搭建一套完整的 TURN 服务器。
