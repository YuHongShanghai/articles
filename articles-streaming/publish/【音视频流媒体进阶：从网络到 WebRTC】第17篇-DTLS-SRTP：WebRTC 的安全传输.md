# DTLS-SRTP：WebRTC 的安全传输

## 前言

上一篇文章中，我们通过 ICE/STUN/TURN 解决了 NAT 穿越问题——两个藏在 NAT 后面的端点终于能"看到"彼此了。但"能通信"不等于"安全通信"。此刻，双方之间传输的 RTP 包就像明信片一样在公网上裸奔，任何中间路由器都可以窃听音视频内容，甚至篡改数据。

WebRTC 的安全模型非常坚决：**所有媒体传输必须加密，没有例外**。这不是一个可选功能，而是写在规范（RFC 8827）里的硬性要求。实现这一目标的核心机制就是 **DTLS-SRTP**——用 DTLS 握手协商出密钥，然后用 SRTP 加密每一个音视频包。

本文将完整剖析这套安全机制：DTLS 握手的每一步细节、SRTP 的加密结构、密钥如何从 DTLS 导出并分配给收发双方，以及如何在 Wireshark 中观察和验证整个过程。

---

## 1. 为什么需要 DTLS-SRTP

### WebRTC 的安全模型

传统的 RTP 传输本身没有任何加密机制——这在内网环境或受信任的运营商网络中或许可以接受，但在公共互联网上完全不行。WebRTC 从设计之初就确立了端到端加密的原则：每一路音频、每一帧视频，从离开发送方的那一刻起就必须是加密的，直到到达接收方才被解密。

这个安全模型带来一个直接的工程问题：**加密需要密钥，密钥需要协商，协商需要安全通道**。

### 为什么不直接用 TLS

TLS 是互联网上最成熟的安全协议，HTTPS 背后就是它。但 TLS 有一个根本限制——它基于 TCP。TLS 记录层假设底层传输是可靠、有序的字节流，握手消息的分片和重组完全依赖 TCP 的保证。

而 WebRTC 的媒体传输走的是 UDP。原因我们在前面的文章中分析过：TCP 的队头阻塞和重传机制会给实时音视频带来不可接受的延迟。你不能为了加密而放弃 UDP 的实时性优势。

### DTLS：TLS over Datagram

**DTLS**（Datagram Transport Layer Security，RFC 6347）就是为了解决这个矛盾而生的。它在 TLS 的基础上做了适配，让安全握手和加密传输能够在不可靠的数据报协议（如 UDP）上工作。DTLS 1.2 对应 TLS 1.2，核心密码学算法完全相同，区别仅在于传输层的适配。

### SRTP：安全的 RTP

有了 DTLS 建立的安全通道，下一步是加密实际的媒体数据。**SRTP**（Secure Real-time Transport Protocol，RFC 3711）定义了 RTP 的加密版本——保留 RTP 头部（路由需要用到），对 payload 加密，并在末尾附加认证标签防篡改。

DTLS-SRTP 的分工非常清晰：

- **DTLS**：负责握手和密钥协商，建立双方的信任关系
- **SRTP**：使用 DTLS 协商出的密钥，对每一个 RTP/RTCP 包进行加密和完整性保护

这种分离设计的好处是：DTLS 握手只在连接建立时发生一次（几个来回），之后的媒体加密由 SRTP 高效完成，每包只增加很小的开销。

---

## 2. DTLS 握手流程

### DTLS 与 TLS 1.2 的异同

DTLS 1.2 的握手流程在逻辑上与 TLS 1.2 几乎一致——双方交换随机数、协商加密套件、验证证书、生成主密钥。但底层传输从可靠的 TCP 换成了不可靠的 UDP，这带来了三个核心问题：

1. **消息可能丢失**：UDP 不保证送达，握手消息可能丢包
2. **消息可能乱序**：UDP 不保证顺序，握手消息可能不按序到达
3. **消息可能超大**：证书链可能超过 UDP 的 MTU 限制

DTLS 针对这三个问题分别设计了对应的机制。

### DTLS 的三大适配机制

**重传定时器**

DTLS 为每一轮握手消息设置了重传定时器。如果在超时时间内没有收到对端的响应，就重发当前这一轮的所有消息。初始超时通常为 1 秒，采用指数退避策略（1s → 2s → 4s → ...），最大退避到 60 秒。这在本质上是在应用层实现了 TCP 的超时重传逻辑。

**消息序列号与分片**

每条 DTLS 握手消息都携带两个关键字段：

- `message_seq`：握手消息的序列号，接收方用它来检测丢失和重排序
- `fragment_offset` + `fragment_length`：当握手消息（尤其是证书）超过 PMTU 时，DTLS 在握手层面进行分片，而不是依赖 IP 层分片

这比 IP 分片安全得多——IP 分片中丢失一个分片就会导致整个数据报被丢弃，而 DTLS 可以单独重传丢失的分片。

**Cookie 验证（防 DoS）**

TLS 握手中，服务端收到 ClientHello 后会立即分配资源（生成密钥、加载证书等）。攻击者可以用伪造源地址的 UDP 包发送大量 ClientHello 来耗尽服务端资源。DTLS 引入了 `HelloVerifyRequest` 机制来对抗这种攻击。

### 完整握手流程

下面是 DTLS 1.2 的完整握手过程：

```
Client                                          Server
------                                          ------
ClientHello           -------->
                                                （不分配资源）
                      <--------    HelloVerifyRequest
                                                + cookie

ClientHello           -------->
+ cookie                                        （验证 cookie）

                      <--------    ServerHello
                      <--------    Certificate
                      <--------    ServerKeyExchange
                      <--------    CertificateRequest*
                      <--------    ServerHelloDone

Certificate*          -------->
ClientKeyExchange     -------->
CertificateVerify*    -------->
[ChangeCipherSpec]    -------->
Finished              -------->

                      <--------    [ChangeCipherSpec]
                      <--------    Finished
```

逐步解读：

**第一轮：Cookie 交换**

客户端发送初始 ClientHello（不含 cookie）。服务端不分配任何状态，仅返回一个 `HelloVerifyRequest`，其中包含一个基于客户端地址计算的 cookie。客户端必须用同一个源地址带上这个 cookie 重新发送 ClientHello，服务端验证 cookie 通过后才开始正式握手。这确保了客户端确实在那个 IP 地址上，而不是伪造的。

**第二轮：参数协商**

服务端回复 ServerHello（选定加密套件和随机数）、Certificate（自签名证书）、ServerKeyExchange（ECDHE 公钥参数）和 ServerHelloDone。

**第三轮：密钥交换完成**

客户端发送自己的 ClientKeyExchange（ECDHE 公钥），双方各自用对方的公钥和自己的私钥计算出相同的 Pre-Master Secret，再通过 PRF（Pseudo-Random Function）推导出 Master Secret 和各种会话密钥。最后双方交换 ChangeCipherSpec 和 Finished 消息，Finished 消息本身已经是加密的，用于验证握手过程没有被篡改。

![DTLS握手流程](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/dtls_handshake.png)

### SDP 中的 a=fingerprint：证书验证

WebRTC 使用自签名证书，没有 CA 体系做信任背书。那如何防止中间人攻击？答案是通过 SDP 中的 `a=fingerprint` 属性。

在 Offer/Answer 交换时，双方在 SDP 中携带自己证书的指纹（hash 值）：

```
a=fingerprint:sha-256 AB:CD:EF:12:34:56:78:9A:BC:DE:F0:...
```

这个指纹通过信令通道（通常是 HTTPS/WSS，本身有 TLS 保护）传递给对方。DTLS 握手时，接收方会验证对端出示的证书指纹与 SDP 中声明的是否一致。如果不匹配，说明存在中间人攻击，连接会被立即拒绝。

这构成了一条信任链：**信令通道的 TLS 保护 SDP → SDP 中的 fingerprint 绑定证书 → 证书绑定 DTLS 会话 → DTLS 导出 SRTP 密钥**。环环相扣，任何一环被破坏都会导致连接失败。

---

## 3. SRTP 加密机制

### SRTP 报文结构

SRTP 包的结构是在 RTP 的基础上扩展的。RTP 头部保持不变（中间网络设备和 SFU 需要读取头部做路由和转发），payload 被加密，末尾追加一个 Authentication Tag：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|V=2|P|X|  CC   |M|     PT      |       Sequence Number         |  ← 明文
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Timestamp                           |  ← 明文
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Synchronization Source (SSRC)                        |  ← 明文
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                    Encrypted Payload                           |  ← 密文
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Authentication Tag                          |  ← 完整性校验
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

与普通 RTP 相比，SRTP 的变化是：

- **Payload 被加密**：窃听者能看到 RTP 头部（知道这是一个 RTP 包、时间戳、序列号等元信息），但无法解密实际的音视频数据
- **末尾增加 Authentication Tag**：覆盖 RTP 头部 + 加密后的 payload，保证整个包没有被篡改

![SRTP加密结构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/srtp_structure.png)

### 加密算法：AES-128-CM

SRTP 默认使用 **AES-128-CM**（AES 128-bit Counter Mode）进行 payload 加密。Counter Mode 是一种流密码模式，它将 AES 变成了一个密钥流生成器：

1. 构造一个计数器（counter），由 SSRC、包序列号和块索引组成
2. 用 AES 加密这个计数器，生成一个密钥流块
3. 将密钥流与明文 payload 进行异或，得到密文

Counter Mode 的优势在于：

- **无需填充**：密钥流可以按需截断到任意长度，不像 CBC 模式需要对齐到块大小
- **支持随机访问**：每个包的加密独立于其他包，丢包不影响后续包的解密
- **可并行化**：不同块的加密可以并行执行

这些特性非常契合 RTP 的场景——包可能丢失、乱序，每个包必须独立可解密。

### 完整性保护：HMAC-SHA1

SRTP 使用 **HMAC-SHA1** 计算 Authentication Tag，输入覆盖 RTP 头部和加密后的 payload。默认的 tag 长度是 80 bit（10 字节），对应加密 profile `SRTP_AES128_CM_HMAC_SHA1_80`。

认证的意义在于：攻击者即使无法解密内容，也可能通过翻转密文中的特定比特来破坏解码——比如修改视频帧的 slice header，导致解码器崩溃。有了 HMAC 校验，任何篡改都会被接收方检测出来并丢弃该包。

验证流程是"先验证、后解密"（authenticate-then-decrypt）。接收方收到 SRTP 包后：

1. 先用认证密钥计算 HMAC，与包末尾的 Authentication Tag 比对
2. 验证通过后，再用加密密钥解密 payload
3. 如果 HMAC 校验失败，直接丢弃，不尝试解密

这种顺序可以避免对篡改过的密文进行解密操作，减少了 padding oracle 等侧信道攻击的风险。

### 密钥导出

DTLS 握手完成后，双方共享了一个 Master Secret。但 SRTP 不直接使用 Master Secret，而是通过 DTLS-SRTP 扩展（RFC 5764）导出专用的密钥材料。这个过程使用 TLS 的 `ExportKeyingMaterial` 接口（RFC 5705）：

```
SRTP_keys = ExportKeyingMaterial(
    label   = "EXTRACTOR-dtls_srtp",
    context = "",           // 无上下文（use_context = false）
    length  = 2 * (master_key_len + master_salt_len))
```

导出的密钥材料按固定顺序排列：

```
client_write_SRTP_master_key   (16 bytes)
server_write_SRTP_master_key   (16 bytes)
client_write_SRTP_master_salt  (14 bytes)
server_write_SRTP_master_salt  (14 bytes)
```

这些是 SRTP 的"主密钥"和"主盐值"。每个 RTP 包的实际加密使用的 IV（初始向量）由 SSRC 和包索引（packet index）构成，因此每个包的密钥流都不同。此外，如果配置了非零的 `key_derivation_rate`（默认为 0，即仅初始化时推导一次），SRTP 还会通过内部的 Key Derivation Function（KDF）周期性地从主密钥重新推导会话密钥，进一步增强安全性。

### SRTCP：RTCP 也要加密

RTCP 包（Sender Report、Receiver Report、NACK、PLI 等）同样包含敏感信息——比如发送速率、丢包率、网络质量指标。攻击者可以利用这些信息推断通话状态，甚至伪造 RTCP 包来干扰拥塞控制。

因此 SRTP 规范同样定义了 **SRTCP**，对 RTCP 包施加相同级别的加密和完整性保护。SRTCP 的密钥与 SRTP 共享同一组主密钥材料，但通过 KDF 推导出独立的加密密钥和认证密钥。

SRTCP 还有一个特殊之处：它在 Authentication Tag 前面插入了一个 4 字节的 **SRTCP Index** 字段，其中最高位是加密标志（E flag），指示该 RTCP 包是否被加密。这是因为某些 RTCP 包类型（如某些信令消息）可能不需要加密但仍需要完整性保护。

---

## 4. 密钥协商机制

### DTLS-SRTP 扩展（use_srtp）

DTLS 本身只负责建立安全通道，并不知道上层要用 SRTP。**DTLS-SRTP 扩展**（RFC 5764）通过在 DTLS 握手中添加 `use_srtp` TLS 扩展来桥接两者。

客户端在 ClientHello 中携带 `use_srtp` 扩展，列出自己支持的 SRTP 加密 Profile：

```
Extension: use_srtp
  Protection Profiles:
    SRTP_AES128_CM_HMAC_SHA1_80  (0x0001)
    SRTP_AES128_CM_HMAC_SHA1_32  (0x0002)
    SRTP_AEAD_AES_128_GCM        (0x0007)
    SRTP_AEAD_AES_256_GCM        (0x0008)
```

服务端在 ServerHello 中回复选定的 Profile：

```
Extension: use_srtp
  Protection Profile:
    SRTP_AES128_CM_HMAC_SHA1_80  (0x0001)
```

### 加密 Profile 详解

常见的 SRTP 加密 Profile 有以下几种：

| Profile | 加密算法 | 认证算法 | Auth Tag 长度 | 说明 |
|---------|----------|----------|---------------|------|
| `SRTP_AES128_CM_HMAC_SHA1_80` | AES-128-CM | HMAC-SHA1 | 80 bit | 最经典，兼容性最好 |
| `SRTP_AES128_CM_HMAC_SHA1_32` | AES-128-CM | HMAC-SHA1 | 32 bit | 缩短认证标签以节省带宽 |
| `SRTP_AEAD_AES_128_GCM` | AES-128-GCM | 内含 | 128 bit | AEAD 模式，更现代 |
| `SRTP_AEAD_AES_256_GCM` | AES-256-GCM | 内含 | 128 bit | 更高安全强度 |

`SRTP_AES128_CM_HMAC_SHA1_80` 是目前 WebRTC 实现中使用最广泛的 Profile。GCM 模式（AEAD）在安全性和性能上都更优，但需要双方都支持。Chrome 和 Firefox 的较新版本已支持 GCM Profile。

`SRTP_AES128_CM_HMAC_SHA1_32` 将认证标签从 10 字节缩短到 4 字节，节省带宽但降低了完整性保护强度，通常只在极度带宽受限的场景下使用。

### 密钥材料的分配

上一节我们看到 DTLS 导出的密钥材料包含四部分。分配规则如下：

- **DTLS client 发送媒体时**：使用 `client_write_SRTP_master_key` + `client_write_SRTP_master_salt`
- **DTLS server 发送媒体时**：使用 `server_write_SRTP_master_key` + `server_write_SRTP_master_salt`

这意味着两个方向的加密使用**不同的密钥**。即使攻击者破解了一个方向的密钥，也无法解密另一个方向的数据。

需要注意的是，DTLS 的 client/server 角色与 SDP 的 Offerer/Answerer 角色不一定一致。SDP 中通过 `a=setup` 属性来协商谁是 DTLS client、谁是 DTLS server：

```
a=setup:actpass   // Offerer：我都行，你来决定
a=setup:active    // Answerer：我来当 client（主动发起 DTLS 握手）
```

通常 Offerer 声明 `actpass`，Answerer 选择 `active`（作为 DTLS client）。这样 Answerer 主动发起 ClientHello，Offerer 作为 DTLS server 响应。

---

## 5. 抓包分析实战

### Wireshark 捕获 DTLS 握手

要抓取 WebRTC 通话中的 DTLS 握手，可以在 Wireshark 中对 WebRTC 端点的网络接口进行捕获。过滤条件可以使用：

```
dtls || stun || rtp || rtcp
```

或者直接按端口过滤，WebRTC 通常使用动态分配的 UDP 高端口（如 10000-65535）。

### DTLS 包的识别

DTLS 记录的第一个字节是 ContentType，常见值如下：

| ContentType | 值 | 说明 |
|-------------|-----|------|
| ChangeCipherSpec | 20 (0x14) | 通知对端切换到加密模式 |
| Alert | 21 (0x15) | 错误或警告 |
| Handshake | 22 (0x16) | 握手消息 |
| ApplicationData | 23 (0x17) | 加密的应用数据 |

在 Wireshark 中，DTLS 握手包会被解析显示为 `DTLSv1.2` 协议，可以展开看到完整的握手消息类型（ClientHello、ServerHello、Certificate 等）。

### 端口复用：DTLS、STUN、RTP 如何共存

WebRTC 默认使用 **RTP/RTCP 多路复用**（RFC 5761）和 **DTLS-SRTP 与 ICE 共享端口**（RFC 7983）。也就是说，DTLS 握手包、STUN Binding 请求、SRTP 媒体包和 SRTCP 控制包，全部走**同一个 UDP 端口**。

接收方如何区分？通过检查 UDP 载荷的**第一个字节**：

| 第一字节范围 | 协议 | 说明 |
|-------------|------|------|
| 0-3 | STUN | STUN 消息以 0x00 或 0x01 开头 |
| 20-63 | DTLS | ContentType 值 20-63 |
| 128-191 | RTP/RTCP | RTP 版本号 V=2，对应首字节 bit 6-7 = 10 |

这个分流逻辑定义在 RFC 7983 中，实现上就是一个简单的字节范围判断：

```cpp
void demux_udp_packet(const uint8_t* data, size_t len) {
    if (len == 0) return;

    uint8_t first_byte = data[0];

    if (first_byte <= 3) {
        handle_stun(data, len);
    } else if (first_byte >= 20 && first_byte <= 63) {
        handle_dtls(data, len);
    } else if (first_byte >= 128 && first_byte <= 191) {
        handle_srtp_srtcp(data, len);
    }
}
```

![抓包分析](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/dtls_wireshark.png)

### 在 Wireshark 中解密 SRTP

正常情况下 Wireshark 无法解密 SRTP 包，看到的 payload 都是密文。但在调试场景下，可以导出 SRTP master key 来解密。

**方法一：通过浏览器导出**

Chrome 支持通过 `chrome://webrtc-internals` 页面查看 WebRTC 内部状态。在较新版本中，可以通过设置环境变量 `OSSL_KEYLOG_FILE` 或使用特定的调试构建来导出密钥。

**方法二：通过 libwebrtc 日志导出**

如果你在服务端使用 libwebrtc 或其他 SRTP 库，可以在代码中打印导出的密钥材料：

```cpp
// 伪代码：从 DTLS 会话导出 SRTP 密钥
uint8_t keying_material[SRTP_MASTER_KEY_LEN * 2 + SRTP_MASTER_SALT_LEN * 2];
SSL_export_keying_material(ssl,
                           keying_material, sizeof(keying_material),
                           "EXTRACTOR-dtls_srtp",
                           strlen("EXTRACTOR-dtls_srtp"),
                           nullptr, 0, 0);
```

**方法三：在 Wireshark 中配置解密**

获取到密钥后，在 Wireshark 中通过 `Edit → Preferences → Protocols → SRTP` 配置密钥，即可看到解密后的 RTP payload。结合 RTP payload 类型，还可以进一步解码出原始的 Opus 音频帧或 H.264 NAL 单元。

这在排查"音视频不出声/不出画面"的问题时非常有用——你可以确认问题是出在加密层（密钥不匹配）还是编解码层。

---

## 6. 安全注意事项

### 自签名证书 vs CA 签名证书

WebRTC 使用**自签名证书**进行 DTLS 握手。这和传统 HTTPS 使用 CA 签发的证书不同。原因在于：

- WebRTC 的端点通常是浏览器或客户端 App，不具备域名，无法申请传统的 CA 证书
- 每次会话可以生成全新的临时证书，用完即弃
- 证书的信任不依赖 CA 体系，而是通过 SDP fingerprint 在信令层建立

每个 PeerConnection 在创建时会生成一对 ECDSA（或 RSA）密钥和对应的自签名证书。证书的指纹通过 SDP 告知对方，DTLS 握手时验证指纹匹配即可。

### 中间人攻击的防护

DTLS-SRTP 的安全性最终取决于**信令通道的安全**。攻击链条是这样的：

1. 如果信令通道未加密（用 HTTP 而非 HTTPS），攻击者可以篡改 SDP 中的 `a=fingerprint`
2. 攻击者替换为自己的证书指纹
3. 分别与通话双方建立 DTLS 连接
4. 作为中间人转发（并窃听）所有媒体数据

防护措施：

- **信令通道必须使用 TLS 加密**（WSS、HTTPS），这是最基本的要求
- **SDP fingerprint 验证必须严格执行**，任何不匹配都应中断连接
- 对于高安全需求场景，可以考虑额外的身份验证机制（如 WebRTC Identity Provider，参见 RFC 8827）

### 密钥轮换

SRTP 的密钥推导中包含了 packet index，这意味着随着包的发送，加密密钥会隐式变化。但 SRTP Master Key 在整个 DTLS 会话期间保持不变。

对于长时间运行的会话（如数小时的视频会议），可以通过 **DTLS 重协商**（renegotiation）来刷新主密钥。不过在实践中，WebRTC 会话通常不会持续太长时间，密钥轮换的需求并不强烈。

如果确实需要更强的前向安全性，可以关注 DTLS 1.3 的进展——它基于 TLS 1.3，原生支持更频繁的密钥更新。

### DTLS 1.3 的未来

DTLS 1.3（RFC 9147）已经发布，它与 TLS 1.3 对齐，带来了重要的改进：

- **更短的握手**：1-RTT 握手（TLS 1.3 移除了 ChangeCipherSpec，减少了一个来回）
- **更强的加密**：移除了所有非 AEAD 加密套件，只保留 AES-GCM 和 ChaCha20-Poly1305
- **0-RTT 恢复**：支持会话恢复时的 0-RTT 数据发送（有重放风险，需谨慎使用）
- **改进的重传**：引入 ACK 机制替代隐式重传

WebRTC 规范正在逐步引入 DTLS 1.3 支持，Chrome 和 Firefox 已在实验性阶段。对于新项目，建议关注并尽早适配。

---

## 总结

本文从 WebRTC 的安全需求出发，完整剖析了 DTLS-SRTP 的工作机制。核心要点回顾：

- **WebRTC 强制加密所有媒体传输**，DTLS-SRTP 是实现这一安全模型的基石
- **DTLS 是 TLS 在 UDP 上的适配**，通过重传定时器、消息分片和 Cookie 验证解决了不可靠传输带来的问题
- **DTLS 握手流程**与 TLS 1.2 逻辑一致，通过 `a=fingerprint` 和信令通道的 TLS 保护构建信任链
- **SRTP 保留 RTP 头部明文，加密 payload，并附加认证标签**，使用 AES-128-CM 加密和 HMAC-SHA1 完整性保护
- **密钥从 DTLS 会话导出**，收发两个方向使用独立密钥，通过 `use_srtp` 扩展协商加密 Profile
- **DTLS、STUN、RTP 共享同一 UDP 端口**，通过首字节范围进行分流
- **安全的信令通道是整个安全模型的根基**——没有安全的信令，fingerprint 验证就是空谈

DTLS-SRTP 保证了 WebRTC 媒体数据的机密性和完整性。但安全只是通话质量的一个维度——在复杂多变的互联网上，丢包、延迟、带宽波动同样是实时通信的大敌。下一篇文章我们将进入 **WebRTC 拥塞控制**的领域，深入分析 **GCC（Google Congestion Control）** 和 **BBR** 算法如何在保证通话质量的同时公平地使用网络带宽。
