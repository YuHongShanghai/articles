# ICE/STUN/TURN：NAT 穿越全攻略

## 前言

在上一篇文章中，我们了解了 WebRTC 的整体架构和信令设计。你已经知道两个浏览器之间的音视频通话需要经过 Offer/Answer 交换 SDP、建立 PeerConnection 等步骤。但有一个关键问题被我们暂时搁置了——**这两个浏览器怎么找到彼此？**

现实世界中，绝大多数终端设备都藏在 NAT（Network Address Translation）后面。你的电脑可能拿到的是 `192.168.1.100` 这样的私网地址，而对端看到的可能是运营商分配的某个公网 IP 加上一个映射端口。两台都在 NAT 后面的设备想直接通信，就像两个人分别住在两栋没有门牌号的大楼里，彼此不知道对方的房间号。

NAT 是互联网的"铁幕"。它解决了 IPv4 地址枯竭的问题，但也给 P2P 通信设置了天然障碍。WebRTC 要实现端到端的实时音视频传输，就必须穿越这道铁幕。

为此，IETF 设计了一整套 NAT 穿越方案：**STUN** 帮你发现自己的公网地址，**TURN** 在直连失败时提供中继转发，而 **ICE** 框架则将它们整合在一起，系统化地完成候选地址的收集、优先级排序和连通性检查。

本文的目标是让你彻底理解 NAT 穿越的原理，并能在生产环境中部署和配置自己的 TURN 服务器。

---

## 1. NAT 类型分类

在深入穿越方案之前，先简单回顾 NAT 的基本工作原理。当内网设备向外部发送数据包时，NAT 网关会将数据包的源 IP（私网地址）替换为自己的公网 IP，同时分配一个映射端口，并在映射表中记录这条映射关系。外部的响应数据包到达时，NAT 根据映射表将目标地址替换回内部设备的私网地址，转发给它。这个过程对通信双方是透明的。

问题在于，不同的 NAT 实现对"谁可以通过映射端口向内部设备发送数据"有不同的策略。RFC 3489 将 NAT 分为四种类型，它们的"开放程度"从宽松到严格依次递减。

### 完全锥形 NAT（Full Cone）

内部主机 `192.168.1.100:5000` 向外发送数据后，NAT 建立映射 `203.0.113.1:8000`。此后，**任何外部主机**都可以通过 `203.0.113.1:8000` 向该内部主机发送数据，无论之前是否有过通信。

这是最宽松的 NAT 类型，P2P 穿越最容易。

### 地址限制锥形 NAT（Address Restricted Cone）

映射规则与完全锥形相同，但多了一条限制：只有**内部主机曾经发送过数据的目标 IP**，才能通过映射端口回传数据。

也就是说，如果内部主机只给 `1.2.3.4` 发过包，那么 `5.6.7.8` 试图通过映射端口发数据进来，会被 NAT 丢弃。

### 端口限制锥形 NAT（Port Restricted Cone）

在地址限制的基础上，进一步限制端口：只有**内部主机曾经发送过数据的目标 IP + 端口**组合，才能回传数据。

这意味着即使你给 `1.2.3.4:3000` 发过包，`1.2.3.4:4000` 试图回传也会被拒绝。大部分家用路由器属于这种类型。

### 对称型 NAT（Symmetric）

对称型 NAT 是最严格的类型。它为**每一个不同的目标地址 + 端口**组合分配不同的映射端口。内部主机给 `1.2.3.4:3000` 发数据时映射为 `203.0.113.1:8000`，给 `5.6.7.8:4000` 发数据时映射为 `203.0.113.1:8001`——端口号不再固定。

这对 STUN 来说是致命的：通过 STUN 服务器发现的公网地址 `203.0.113.1:8000`，只对 STUN 服务器有效。当你把这个地址告诉对端，对端发数据过来时 NAT 会拒绝，因为映射关系不匹配。

![NAT类型分类](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/nat_types.png)

### 各类型对 P2P 的影响

四种 NAT 类型的核心区别在于映射规则和过滤规则：

| NAT 类型 | 映射规则 | 过滤规则 | P2P 难度 |
|----------|----------|----------|----------|
| 完全锥形 | 固定映射 | 无限制 | 容易 |
| 地址限制锥形 | 固定映射 | 限制源 IP | 中等 |
| 端口限制锥形 | 固定映射 | 限制源 IP + 端口 | 较难 |
| 对称型 | 每目标不同映射 | 限制源 IP + 端口 | 极难 |

对称型 NAT 是 P2P 穿越的最大敌人。当通信双方都是对称型 NAT 时，STUN 完全无能为力，只能依赖 TURN 中继。幸运的是，对称型 NAT 在家庭网络中相对少见，主要出现在企业级防火墙和运营商级 NAT（CGNAT）中。

---

## 2. STUN 协议工作原理

STUN（Session Traversal Utilities for NAT，RFC 8489，废弃了旧版 RFC 5389）是 NAT 穿越的基础工具。它的核心职责非常简单：**让 NAT 后面的客户端发现自己的公网 IP 和端口**。

### 基本思路

客户端向公网上的 STUN 服务器发送一个请求，STUN 服务器看到这个请求的源 IP 和源端口（经过 NAT 映射后的公网地址），然后把这个地址告诉客户端。客户端由此得知自己在公网上的"门牌号"。

这个过程类似于你打电话问朋友："你看到的我的来电号码是什么？"

### STUN 报文结构

STUN 消息采用 TLV（Type-Length-Value）格式，所有消息共享一个 20 字节的头部：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|0 0|     STUN Message Type     |         Message Length        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Magic Cookie                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                     Transaction ID (96 bits)                  |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

几个关键字段：

- **Message Type**（14 位）：最高 2 位固定为 `00`（区分 STUN 和其他复用同一端口的协议），剩余位编码方法和类别（Request/Response/Indication/Error）
- **Magic Cookie**：固定值 `0x2112A442`，用于识别 STUN 协议版本
- **Transaction ID**：96 位随机数，用于匹配请求和响应

头部之后是零到多个属性（Attribute），每个属性也是 TLV 格式。最重要的属性是 `XOR-MAPPED-ADDRESS`，它包含了客户端的公网 IP 和端口（经过 XOR 混淆，防止某些 NAT 设备篡改负载中的 IP 地址）。之所以用 XOR 而不是直接放明文地址，是因为有些"聪明"的 NAT 设备会检查 UDP 负载中的 IP 地址并尝试改写，XOR 混淆可以绕过这种行为。

其他常见属性包括 `USERNAME`（用于认证）、`MESSAGE-INTEGRITY`（HMAC-SHA1 消息完整性校验）和 `FINGERPRINT`（CRC32 指纹，用于多协议复用同一端口时的协议识别）。

### Binding Request / Response 交互

STUN 最核心的交互是 Binding 事务：

1. 客户端构造一个 **Binding Request**，通过 UDP 发送到 STUN 服务器
2. STUN 服务器收到请求后，提取数据包的源 IP 和源端口（即 NAT 映射后的公网地址）
3. 服务器将这个地址放入 `XOR-MAPPED-ADDRESS` 属性，构造 **Binding Response** 返回给客户端
4. 客户端解析响应，得知自己的公网地址

![STUN工作原理](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/stun_protocol.png)

如果客户端发现自己的本地地址与 STUN 返回的地址相同，说明它没有在 NAT 后面（或 NAT 是一对一映射的），可以直接通信。如果不同，客户端就拿到了一个"服务器反射候选地址"（Server Reflexive Candidate），可以提供给对端尝试连接。

由于 STUN 使用 UDP 传输，请求可能丢失。RFC 8489 定义了重传机制：初始超时为 500ms（可配置的 RTO 值），之后每次重传将超时翻倍，直到达到 Rm×RTO 的上限（默认 16×500ms=8s）后不再增长，最多重传 7 次。整个 Binding 事务的超时上限约为 39.5 秒。在实际 WebRTC 实现中，ICE Agent 通常配置更短的超时（如 5 秒），以避免因 STUN 服务器不可达而长时间阻塞候选收集。

### 公共 STUN 服务器

STUN 服务器的负载极低——它只需要收一个请求、回一个响应，不需要中继任何媒体数据。因此互联网上有大量免费的公共 STUN 服务器可供使用：

| 服务器地址 | 提供方 |
|-----------|--------|
| `stun:stun.l.google.com:19302` | Google |
| `stun:stun1.l.google.com:19302` | Google |
| `stun:stun.cloudflare.com:3478` | Cloudflare |
| `stun:stun.stunprotocol.org:3478` | 开源社区 |

在 WebRTC 的 `RTCPeerConnection` 配置中使用：

```javascript
const pc = new RTCPeerConnection({
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' }
  ]
});
```

### STUN 的局限

STUN 只能解决**非对称型 NAT** 的穿越问题。对于对称型 NAT，STUN 发现的地址对其他目标无效。此外，当两端的 NAT 都比较严格时，即使知道了彼此的公网地址，双方的 NAT 也可能因为没有"先发包"的记录而互相拒绝对方的数据。

这就需要 TURN 出场了。

---

## 3. TURN 中继方案

TURN（Traversal Using Relays around NAT，RFC 8656，废弃了旧版 RFC 5766）是 NAT 穿越的"最后防线"。当 STUN 无法帮助双方建立直连时，TURN 服务器作为中继节点，转发双方的所有媒体数据。

### 工作原理

TURN 的核心思路是：客户端在 TURN 服务器上"申请"一个公网地址，然后把这个地址告诉对端。对端发给这个地址的数据，TURN 服务器负责转发给客户端。可以把 TURN 服务器理解为一个"邮件转发站"——你告诉朋友你的转发站地址，朋友把信寄到转发站，转发站再送到你手里。

值得注意的是，TURN 协议是 STUN 的扩展。TURN 消息使用与 STUN 相同的报文格式和头部结构，只是定义了额外的方法（Allocate、Refresh、CreatePermission、ChannelBind 等）和属性。TURN 服务器同时也是 STUN 服务器，能够处理 STUN Binding 请求。

### 完整交互流程

TURN 的交互比 STUN 复杂得多，涉及多个步骤：

**1. Allocate（分配）**

客户端向 TURN 服务器发送 Allocate Request，服务器验证身份后，在服务器端分配一个中继地址（Relayed Transport Address），如 `203.0.113.50:49152`。这个地址就是客户端在公网上的"代理门牌号"。

**2. CreatePermission（创建权限）**

为了防止滥用，TURN 服务器默认不会转发任何数据。客户端需要发送 CreatePermission 请求，明确告诉服务器允许哪些 IP 地址向自己的中继地址发送数据。

**3. ChannelBind（通道绑定）**

每个 TURN 数据包都有 36 字节的 TURN 头部开销。为了减少开销，客户端可以通过 ChannelBind 将特定的对端地址绑定到一个 2 字节的通道号（0x4000-0x7FFE）。绑定后，数据转发只需要 4 字节的通道头部。

**4. Data Relay（数据中继）**

一切就绪后，客户端通过 Send Indication 或 ChannelData 将数据发给 TURN 服务器，服务器转发给对端；对端的数据也经由 TURN 服务器中转回来。

**5. Refresh（刷新）**

TURN 的 Allocation 不是永久的，默认有效期为 10 分钟。客户端需要在到期前定期发送 Refresh 请求来续期。如果客户端崩溃或网络断开导致未能续期，服务器会自动回收 Allocation，释放资源。这个机制确保了 TURN 服务器不会因为"僵尸连接"而耗尽资源。

![TURN中继原理](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/turn_relay.png)

### 延迟与带宽成本

TURN 中继意味着所有媒体数据都要经过中间节点，这带来两个直接影响：

**延迟增加**：P2P 直连时数据走最短路径，而 TURN 中继需要客户端 → TURN 服务器 → 对端，多了一跳。在地理距离较远时，额外延迟可能达到 50-100ms。

**带宽成本**：TURN 服务器需要承载所有中继流量。一路 720p 视频通话的码率约 1.5 Mbps，双向就是 3 Mbps。如果有 1000 路并发通话走 TURN，服务器需要 3 Gbps 的带宽——这是非常可观的成本。

正因如此，TURN 是最后手段。ICE 框架的设计原则是**尽一切可能建立 P2P 直连，只在直连确实不可行时才回退到 TURN**。

### 何时会回退到 TURN

以下场景通常需要 TURN 介入：

- 双方都在对称型 NAT 后面
- 企业防火墙严格限制了 UDP 出站流量
- 运营商级 NAT（CGNAT）导致端口映射不可预测
- 网络中间设备（如某些酒店/机场 Wi-Fi）阻断 UDP

在生产环境中，大约 10-20% 的 WebRTC 连接需要 TURN 中继。这个比例虽然不高，但对于用户体验至关重要——没有 TURN，这部分用户将完全无法通话。

---

## 4. ICE 框架详解

ICE（Interactive Connectivity Establishment，RFC 8445）不是一个独立协议，而是一个**框架**。它整合了 STUN 和 TURN，定义了一套系统化的流程来完成 NAT 穿越：收集所有可能的候选地址、与对端交换、逐一测试连通性、选出最优路径。

为什么需要一个框架？因为在现实网络中，一台设备可能同时有多个网络接口（有线、Wi-Fi、VPN），每个接口在 NAT 映射后可能产生不同的公网地址，加上 TURN 分配的中继地址，候选地址的组合空间非常大。手动管理这些地址并逐一测试连通性是不现实的，ICE 将这个过程自动化了。

ICE 中有两个角色：**Controlling Agent**（控制方）和 **Controlled Agent**（被控制方）。在 WebRTC 中，创建 Offer 的一方默认是 Controlling，创建 Answer 的一方是 Controlled。Controlling Agent 负责最终决定使用哪个候选对。

### ICE 候选类型

ICE 定义了四种候选地址类型，按优先级从高到低排列：

**host candidate（主机候选）**

本机网卡上的实际地址，如 `192.168.1.100:5000`。如果双方在同一局域网内，host 候选可以直接通信，延迟最低。

**srflx candidate（服务器反射候选）**

通过 STUN 服务器发现的公网映射地址，如 `203.0.113.1:8000`。这是跨 NAT 通信的首选地址。srflx 是 "Server Reflexive" 的缩写。

**prflx candidate（对端反射候选）**

在 ICE 连通性检查过程中动态发现的地址。当 A 向 B 的某个候选地址发送 STUN Binding Request 时，B 可以从这个请求中看到 A 经过 NAT 映射后的实际地址。这个地址可能与 A 通过 STUN 服务器获得的 srflx 地址不同（特别是在对称型 NAT 的情况下），但有时候恰好能用于直连。

**relay candidate（中继候选）**

通过 TURN 服务器分配的中继地址，如 `203.0.113.50:49152`。优先级最低，但可靠性最高——只要 TURN 服务器可达，就一定能通信。

### 候选收集过程

当 `RTCPeerConnection` 创建 Offer 或 Answer 时，ICE Agent 开始收集候选地址：

1. **枚举本地网卡**：获取所有 host 候选（可能有多个网卡、多个 IP）
2. **STUN 查询**：向配置的 STUN 服务器发送 Binding Request，获取 srflx 候选
3. **TURN 分配**：向配置的 TURN 服务器发送 Allocate Request，获取 relay 候选

每个候选地址收集完成后，通过信令通道发送给对端。在 SDP 中，候选地址以 `a=candidate:` 行的形式出现：

```
a=candidate:1 1 UDP 2130706431 192.168.1.100 5000 typ host
a=candidate:2 1 UDP 1694498815 203.0.113.1 8000 typ srflx raddr 192.168.1.100 rport 5000
a=candidate:3 1 UDP 16777215 203.0.113.50 49152 typ relay raddr 203.0.113.1 rport 8000
```

每一行包含候选的基础信息：foundation（用于冻结优化）、组件 ID（1 表示 RTP，2 表示 RTCP）、传输协议、优先级、地址、端口、类型，以及相关地址（raddr/rport，用于调试）。

### 候选对与优先级

当双方的候选地址收集完毕并交换后，ICE 将它们组合成**候选对（Candidate Pair）**。如果 A 有 3 个候选，B 有 4 个候选，就会产生 3×4=12 个候选对。

每个候选对被赋予一个优先级，计算规则大致为：

```
pair_priority = 2^32 * MIN(G, D) + 2 * MAX(G, D) + (G > D ? 1 : 0)
```

其中 G 和 D 分别是控制方（Controlling）和被控制方（Controlled）的候选优先级。host-host 对的优先级最高，relay-relay 对最低。

### 连通性检查

ICE 按照候选对的优先级顺序，逐一进行连通性检查。每次检查本质上就是向对端的候选地址发送一个 **STUN Binding Request**，观察是否能收到响应。

检查过程遵循以下规则：

- 双方同时发起检查（ICE 是双向的），使用 STUN 短期凭证（由 SDP 中的 `ice-ufrag` 和 `ice-pwd` 组成）进行身份验证
- 收到对端的 Binding Request 后，如果是来自一个未知地址，会创建 prflx 候选并生成新的候选对——这个机制让对称型 NAT 也有概率被"意外"穿透
- 当一个候选对双向检查都成功时，该对被标记为"成功"（succeeded）
- 检查完成后，ICE Agent 从所有成功的候选对中选择优先级最高的作为**提名对（nominated pair）**，用于后续的媒体传输

这个过程涉及一个有限状态机。每个候选对从 Frozen 状态开始，进入 Waiting 状态表示等待检查，In-Progress 表示检查正在进行，最终进入 Succeeded 或 Failed。ICE Agent 通过维护一个检查列表（Check List）来管理所有候选对的状态转换。

在实际场景中，为了加速连通性检查，ICE 引入了**冻结（Freezing）**机制：具有相同 foundation 的候选对会被分组，同一组中只有优先级最高的那个会先被检查。当这个检查成功后，同组的其他候选对会被"解冻"加入检查队列。这避免了对大量候选对进行毫无必要的并行检查，节省了网络带宽。

![ICE候选收集与检查](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/ice_process.png)

### Trickle ICE

早期的 ICE 实现需要等所有候选收集完毕后才能开始发送 Offer/Answer，这会引入显著的建连延迟（TURN 分配可能需要数百毫秒）。

**Trickle ICE**（RFC 8838）改进了这一点：**候选地址一旦收集到，立即通过信令发送给对端**，不必等待全部完成。这样双方可以在候选收集的同时就开始连通性检查，显著缩短了建连时间。

在 WebRTC API 中，Trickle ICE 体现为 `onicecandidate` 事件的逐个触发：

```javascript
pc.onicecandidate = (event) => {
  if (event.candidate) {
    // 立即通过信令发送给对端
    signalingChannel.send({
      type: 'candidate',
      candidate: event.candidate
    });
  }
};
```

### ICE Restart

当网络环境发生变化（如从 Wi-Fi 切换到 4G，或 IP 地址变更）时，当前的 ICE 连接可能失效。ICE Restart 允许在不改变媒体配置（编解码器、流方向等）的前提下，通过一次新的 SDP Offer/Answer 交换来重新收集候选地址并进行连通性检查。

```javascript
// 触发 ICE Restart
const offer = await pc.createOffer({ iceRestart: true });
await pc.setLocalDescription(offer);
// 通过信令发送新的 Offer 给对端
```

ICE Restart 会生成新的 ICE 用户名片段（ufrag）和密码（pwd），但保留已有的媒体会话，实现无缝的网络切换。移动端场景下 ICE Restart 尤其重要——用户从 Wi-Fi 走到户外切换到蜂窝网络时，如果没有 ICE Restart，通话就会中断。良好的 WebRTC 应用应该监听 `oniceconnectionstatechange` 事件，在检测到 `disconnected` 或 `failed` 状态时自动触发 ICE Restart。

---

## 5. 实战：部署 coturn 服务器

coturn 是目前最成熟的开源 TURN/STUN 服务器实现，支持 TURN（RFC 5766）、STUN（RFC 5389）、TURNS（TURN over TLS/DTLS）等标准，被 Jitsi、Nextcloud Talk、BigBlueButton 等众多开源项目采用。它使用 C 语言编写，性能出色，单台服务器可以承载数千路并发中继。本节将从安装到生产级配置完整走一遍。

### 安装

**Ubuntu/Debian 直接安装：**

```bash
sudo apt update
sudo apt install coturn
```

**从源码编译（获取最新版本）：**

```bash
git clone https://github.com/coturn/coturn.git
cd coturn
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
```

安装完成后，主要涉及以下文件：

- 配置文件：`/etc/turnserver.conf`
- 可执行文件：`/usr/bin/turnserver`
- systemd 服务：`/lib/systemd/system/coturn.service`

### 配置文件详解

coturn 的配置项非常多，下面列出生产环境的关键参数：

```ini
# === 监听配置 ===
listening-port=3478
tls-listening-port=5349
listening-ip=0.0.0.0

# 公网 IP 配置（关键！）
# 如果服务器在云平台（AWS/阿里云等），内网 IP 和公网 IP 不同
# 格式：external-ip=公网IP/内网IP
external-ip=203.0.113.50/10.0.1.100

# === 认证配置 ===
realm=turn.example.com
# 静态用户（测试用）
user=webrtc:password123
# 生产环境建议使用长期凭证机制
lt-cred-mech
# 或使用 REST API 动态生成临时凭证
use-auth-secret
static-auth-secret=your-very-long-random-secret-key

# === TLS 证书配置 ===
cert=/etc/letsencrypt/live/turn.example.com/fullchain.pem
pkey=/etc/letsencrypt/live/turn.example.com/privkey.pem

# === 安全限制 ===
# 限制中继端口范围
min-port=49152
max-port=65535
# 禁止中继到私网地址（防止 SSRF 攻击）
no-multicast-peers
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.168.0.0-192.168.255.255

# === 性能配置 ===
# 单个用户的最大带宽（bytes/s），防止滥用
max-bps=1048576
# 总带宽限制
total-quota=0
# 单用户配额（0 表示不限制）
user-quota=0

# === 日志 ===
log-file=/var/log/turnserver/turn.log
verbose
```

其中 `external-ip` 是最容易配错的参数，也是新手部署 coturn 时最常遇到的坑。在 AWS EC2、阿里云 ECS 等云平台上，服务器的网卡只绑定了内网 IP（如 `10.0.1.100`），公网 IP（如 `203.0.113.50`）是通过弹性 IP（EIP）映射的。如果不配置 `external-ip`，TURN 在 Allocate Response 中返回的中继地址会是内网 IP，客户端根本无法访问。配置格式为 `external-ip=公网IP/内网IP`，coturn 会自动将中继地址中的内网 IP 替换为公网 IP。

另一个常见问题是同时配置了 `lt-cred-mech` 和 `use-auth-secret`。这两种认证机制只能二选一：`lt-cred-mech` 使用静态的用户名密码，适合测试环境；`use-auth-secret` 配合共享密钥生成临时凭证，适合生产环境。同时启用会导致认证行为混乱。

### 启动与测试

**启用 coturn 服务：**

```bash
# 编辑 /etc/default/coturn，取消注释以下行
# TURNSERVER_ENABLED=1

sudo systemctl enable coturn
sudo systemctl start coturn
sudo systemctl status coturn
```

**防火墙放行：**

```bash
sudo ufw allow 3478/tcp
sudo ufw allow 3478/udp
sudo ufw allow 5349/tcp
sudo ufw allow 5349/udp
sudo ufw allow 49152:65535/udp
```

**命令行快速测试：**

```bash
# 测试 STUN 功能
turnutils_stunclient 203.0.113.50

# 测试 TURN 功能
turnutils_uclient -u webrtc -w password123 203.0.113.50
```

### 使用 Trickle ICE 页面验证

Google 提供了一个在线的 ICE 测试工具：[Trickle ICE](https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/)。

在页面中添加你的 TURN 服务器：

```
STUN: stun:203.0.113.50:3478
TURN: turn:203.0.113.50:3478 (username: webrtc, credential: password123)
TURNS: turns:203.0.113.50:5349 (username: webrtc, credential: password123)
```

点击 "Gather candidates" 后，你应该能看到三种类型的候选：

- `host`：本机地址
- `srflx`：STUN 发现的公网地址
- `relay`：TURN 分配的中继地址

如果只出现 host 和 srflx 而没有 relay，说明 TURN 配置有问题，通常是认证失败或端口未放行。

### 生产环境安全建议

**使用临时凭证替代静态密码**

在配置文件中启用 `use-auth-secret` 和 `static-auth-secret`，然后在你的信令服务器中动态生成临时凭证：

```python
import hashlib
import hmac
import base64
import time

def generate_turn_credentials(secret, username, ttl=86400):
    timestamp = int(time.time()) + ttl
    turn_username = f"{timestamp}:{username}"
    hmac_digest = hmac.new(
        secret.encode(),
        turn_username.encode(),
        hashlib.sha1
    ).digest()
    password = base64.b64encode(hmac_digest).decode()
    return turn_username, password
```

这样每个凭证都有过期时间，即使泄露也只在有限时间内有效。

**限速与黑名单**

```ini
# 每秒最大分配请求数
stale-nonce=600
# 黑名单特定 IP
denied-peer-ip=1.2.3.4
# 限制单用户带宽
max-bps=2097152
```

**启用 TLS**

生产环境务必配置 TLS 证书，启用 TURNS（TURN over TLS，端口 5349）。部分企业网络只放行 443 端口，可以将 `tls-listening-port` 设为 443：

```ini
tls-listening-port=443
```

**监控与日志**

coturn 支持 Prometheus 指标导出（需编译时启用 `--with-prometheus`），在运维方面建议监控：

- 活跃 Allocation 数量
- 中继带宽吞吐量
- 认证失败率
- 连接来源地域分布

---

## 6. NAT 穿越成功率分析

### NAT 类型组合矩阵

不同 NAT 类型的组合决定了穿越方式和成功率。下表展示了所有可能的组合：

| A 端 \ B 端 | 完全锥形 | 地址限制锥形 | 端口限制锥形 | 对称型 |
|-------------|----------|-------------|-------------|--------|
| **完全锥形** | STUN 直连 | STUN 直连 | STUN 直连 | STUN 直连 |
| **地址限制锥形** | STUN 直连 | STUN 直连 | STUN 直连 | STUN 直连 |
| **端口限制锥形** | STUN 直连 | STUN 直连 | STUN 直连 | **需要 TURN** |
| **对称型** | STUN 直连 | STUN 直连 | **需要 TURN** | **需要 TURN** |

规律是：

- 只要有一端是完全锥形或地址限制锥形，基本都能 STUN 直连
- 端口限制锥形 + 对称型的组合需要 TURN
- 双对称型必须 TURN

### 实际统计数据

根据多份公开的 WebRTC 部署统计报告：

| 穿越方式 | 占比 | 说明 |
|----------|------|------|
| host（局域网直连） | ~10-15% | 同一 NAT 下的设备 |
| srflx（STUN 穿越） | ~70-75% | 大部分场景 |
| relay（TURN 中继） | ~10-20% | 对称型 NAT、企业防火墙 |

也就是说，大约 **80-90% 的连接可以建立 P2P 直连**，只有 10-20% 需要 TURN 中继。但这 10-20% 的用户体验同样重要。如果你的服务没有部署 TURN 服务器，这部分用户将完全无法使用——他们通常是企业用户或处于严格网络环境中的用户，恰恰可能是高价值用户。

### 优化穿越成功率的策略

**多网卡收集**：确保 ICE 收集所有网络接口的候选，包括 VPN 接口。

**TURN over TCP/TLS**：某些网络环境会封锁 UDP 流量，配置 TURN 的 TCP 和 TLS 备选方案可以覆盖更多场景。

**多 TURN 服务器部署**：在不同地域部署 TURN 服务器，根据用户位置就近选择，降低中继延迟。

**UDP 端口多样化**：配置多个 STUN/TURN 监听端口，应对某些网络环境下特定端口被封锁的情况。

**ICE 超时调优**：适当增加 ICE 候选收集和连通性检查的超时时间，特别是在弱网环境下，给 STUN/TURN 更多时间响应。

在 WebRTC 配置中，一个完善的 iceServers 配置通常长这样：

```javascript
const pc = new RTCPeerConnection({
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    {
      urls: [
        'turn:turn.example.com:3478?transport=udp',
        'turn:turn.example.com:3478?transport=tcp',
        'turns:turn.example.com:5349?transport=tcp'
      ],
      username: temporaryUsername,
      credential: temporaryPassword
    }
  ],
  iceTransportPolicy: 'all'  // 'all' 表示优先直连，'relay' 表示强制走 TURN
});
```

---

## 总结

本文从 NAT 的分类讲起，系统地介绍了 WebRTC 中 NAT 穿越的完整方案。核心要点回顾：

- **NAT 有四种类型**，从完全锥形到对称型依次收紧。对称型 NAT 是 P2P 穿越的最大障碍
- **STUN** 是轻量级协议，帮助客户端发现公网映射地址，但对对称型 NAT 无效
- **TURN** 是最后的中继方案，能保证 100% 的连通性，但代价是额外的延迟和带宽
- **ICE 框架**整合 STUN 和 TURN，通过候选收集、优先级排序和连通性检查，系统化地找到最优传输路径
- **Trickle ICE** 通过边收集边发送候选来加速建连
- 生产环境中，**coturn** 是最主流的 TURN 服务器选择，关键配置包括 `external-ip`、认证方式和安全限制
- 实际部署中约 **80-90% 的连接可以 P2P 直连**，但 TURN 对剩余 10-20% 的场景不可或缺

NAT 穿越解决了"两端怎么找到彼此"的问题，但数据传输还面临另一个挑战——**安全**。WebRTC 的媒体数据走的是 UDP，而 UDP 本身没有任何加密机制。下一篇文章我们将进入 **DTLS-SRTP** 的世界，看看 WebRTC 如何在不可靠的 UDP 之上建立安全的加密通道，确保你的音视频数据不被窃听和篡改。
