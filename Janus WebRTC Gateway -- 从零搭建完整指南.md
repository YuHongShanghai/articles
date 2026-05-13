# Janus WebRTC Gateway -- 从零搭建完整指南

本文档面向新手，手把手指导你在 **Ubuntu 22.04** 上从源码编译、配置并运行 Janus WebRTC 服务器。  
所有编译产物安装在项目目录下的 `local/`，不污染系统目录，无需 root 权限即可运行。

---

## 目录

1. [什么是 Janus](#1-什么是-janus)
2. [整体架构](#2-整体架构)
3. [环境准备](#3-环境准备)
4. [编译安装](#4-编译安装)
5. [项目结构](#5-项目结构)
6. [启动与停止](#6-启动与停止)
7. [验证服务](#7-验证服务)
8. [配置详解](#8-配置详解)
9. [插件介绍](#9-插件介绍)
10. [Janus API 入门](#10-janus-api-入门)
11. [常见问题排查](#11-常见问题排查)
12. [进阶：生产环境部署](#12-进阶生产环境部署)
13. [参考资料](#13-参考资料)

---

## 1. 什么是 Janus

[Janus](https://janus.conf.meetecho.com/) 是由 Meetecho 开发的开源 **WebRTC 服务器（Gateway）**。它本身不提供具体的音视频业务逻辑，而是充当一个通用的 WebRTC 信令和媒体中转框架，通过**插件**机制实现各种场景：

- 多人视频会议（VideoRoom，SFU 模式）
- 一对一视频通话（VideoCall）
- 流媒体分发（Streaming）
- 音频混音会议（AudioBridge，MCU 模式）
- SIP 网关（对接传统电话网络）
- 录制与回放（RecordPlay）

**为什么选择 Janus：**
- C 语言编写，性能优秀，资源占用低
- 插件架构灵活，可只加载需要的功能
- 同时支持 HTTP REST 和 WebSocket 两种信令通道
- 社区活跃，文档完善

## 2. 整体架构

```
浏览器 / App
    │
    │  WebSocket (ws://localhost:8188)
    │  或 HTTP REST (http://localhost:8088/janus)
    │
    ▼
┌─────────────────────────────────────────┐
│            Janus Gateway                │
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │ Transport │  │ Transport │  信令层    │
│  │  HTTP     │  │ WebSocket│            │
│  └────┬─────┘  └────┬─────┘            │
│       └──────┬───────┘                  │
│              ▼                          │
│  ┌─────────────────────────────┐        │
│  │       Janus Core            │  核心   │
│  │  (ICE / DTLS / SRTP / SDP) │        │
│  └──────┬──────────────────────┘        │
│         ▼                               │
│  ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │VideoRoom │ │EchoTest  │ │Streaming│  │  插件层
│  │(SFU 会议)│ │(回显测试)│ │(流转发) │  │
│  └──────────┘ └──────────┘ └────────┘  │
└─────────────────────────────────────────┘
    │
    │  RTP / RTCP (UDP)
    │
    ▼
  WebRTC 媒体流
```

**关键概念：**

| 概念 | 说明 |
|------|------|
| **Session** | 浏览器与 Janus 之间的一个会话，通过 session_id 标识 |
| **Handle (Plugin Handle)** | 在 session 内 attach 到某个插件后得到的句柄，通过 handle_id 标识 |
| **Transport** | 信令传输方式（HTTP / WebSocket / Unix Socket 等） |
| **Plugin** | 实际业务逻辑模块（VideoRoom / EchoTest 等） |
| **ICE** | WebRTC 连接建立协议，负责 NAT 穿透 |
| **DTLS-SRTP** | WebRTC 媒体加密机制 |

## 3. 环境准备

### 3.1 系统要求

- Ubuntu 22.04 LTS（其他 Debian 系发行版类似）
- GCC / G++ 编译器
- 至少 2GB 可用磁盘空间
- 网络通畅（需要从 GitHub / GitLab 下载源码）

### 3.2 安装系统依赖

以下包是编译 Janus 及其依赖所必须的，**只需运行一次**：

```bash
# 方式一：使用项目提供的脚本（推荐）
./install_deps.sh

# 方式二：手动安装
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake pkg-config gengetopt libtool automake autoconf git \
  meson ninja-build gtk-doc-tools wget ca-certificates \
  libglib2.0-dev libjansson-dev libconfig-dev libssl-dev \
  libcurl4-openssl-dev libopus-dev libogg-dev \
  libavutil-dev libavcodec-dev libavformat-dev \
  libsofia-sip-ua-dev libmicrohttpd-dev \
  libgnutls28-dev zlib1g-dev \
  lua5.3 liblua5.3-dev
```

**各依赖包的作用：**

| 包名 | 用途 |
|------|------|
| `build-essential` | GCC 编译器、make 等基础编译工具 |
| `cmake` / `meson` / `ninja-build` | 构建系统（不同依赖库使用不同构建系统） |
| `libglib2.0-dev` | GLib 基础库，Janus 核心依赖 |
| `libjansson-dev` | JSON 解析库 |
| `libconfig-dev` | 配置文件解析库 |
| `libssl-dev` | OpenSSL，DTLS/SRTP 加密 |
| `libopus-dev` | Opus 音频编解码器 |
| `libsofia-sip-ua-dev` | SIP 协议栈（SIP 插件需要） |
| `libmicrohttpd-dev` | 轻量 HTTP 服务器（HTTP transport 需要） |
| `gengetopt` | 命令行参数解析代码生成器 |

## 4. 编译安装

Janus 依赖 3 个需要从源码编译的库（Ubuntu 仓库版本太旧）：

| 组件 | 版本 | 为什么需要源码编译 |
|------|------|------|
| **libnice** | 0.1.22 | ICE 协议库，Ubuntu 22.04 自带版本不满足 Janus 要求 |
| **libsrtp** | 2.6.0 | SRTP 加密库，需要 2.x 版本 |
| **libwebsockets** | 4.3.3 | WebSocket 支持，系统版本不兼容 |
| **Janus Gateway** | 1.2.4 | 最新稳定版 |

### 4.1 一键编译（推荐）

```bash
# 编译所有依赖 + Janus，约 2-5 分钟（取决于 CPU 核数）
bash build_janus.sh
```

脚本会自动下载源码、编译并安装到 `./local/` 目录下。

### 4.2 手动分步编译

如果你想了解每一步在做什么，可以按以下顺序手动执行。

#### 第 1 步：设置环境变量

```bash
export PREFIX="$(pwd)/local"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib/x86_64-linux-gnu/pkgconfig"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib/x86_64-linux-gnu"
export CFLAGS="-I$PREFIX/include"
export LDFLAGS="-L$PREFIX/lib -L$PREFIX/lib/x86_64-linux-gnu"
```

#### 第 2 步：编译 libnice

```bash
wget https://gitlab.freedesktop.org/libnice/libnice/-/archive/0.1.22/libnice-0.1.22.tar.gz
tar xf libnice-0.1.22.tar.gz && cd libnice-0.1.22
meson setup builddir --prefix="$PREFIX" -Dexamples=disabled -Dtests=disabled -Dgstreamer=disabled
ninja -C builddir -j$(nproc) && ninja -C builddir install
```

#### 第 3 步：编译 libsrtp

```bash
wget https://github.com/cisco/libsrtp/archive/refs/tags/v2.6.0.tar.gz -O libsrtp-2.6.0.tar.gz
tar xf libsrtp-2.6.0.tar.gz && cd libsrtp-2.6.0
./configure --prefix="$PREFIX" --enable-openssl
make -j$(nproc) && make install
```

#### 第 4 步：编译 libwebsockets

```bash
wget https://github.com/warmcat/libwebsockets/archive/refs/tags/v4.3.3.tar.gz -O lws-4.3.3.tar.gz
tar xf lws-4.3.3.tar.gz && cd libwebsockets-4.3.3 && mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_C_FLAGS="-fpic" \
      -DLWS_MAX_SMP=1 -DLWS_WITHOUT_EXTENSIONS=0 \
      -DLWS_WITHOUT_TESTAPPS=ON -DLWS_WITH_STATIC=OFF ..
make -j$(nproc) && make install
```

#### 第 5 步：编译 Janus

```bash
wget https://github.com/meetecho/janus-gateway/archive/refs/tags/v1.2.4.tar.gz -O janus-1.2.4.tar.gz
tar xf janus-1.2.4.tar.gz && cd janus-gateway-1.2.4
sh autogen.sh
./configure --prefix="$PREFIX/janus" \
    --enable-websockets --enable-rest \
    --enable-plugin-echotest --enable-plugin-videoroom \
    --enable-plugin-streaming --enable-plugin-videocall \
    --enable-plugin-audiobridge --enable-plugin-sip \
    --enable-plugin-textroom --enable-plugin-recordplay
make -j$(nproc) && make install && make configs
```

## 5. 项目结构

```
LibjanusLearn/
├── install_deps.sh             # [第一步] 安装系统依赖（需 sudo，仅运行一次）
├── build_janus.sh              # [第二步] 一键编译 Janus 及依赖
├── start_janus.sh              # 启动 Janus
├── stop_janus.sh               # 停止 Janus
├── html/
│   └── echotest.html           # Echo Test 前端测试页面
├── local/                      # 编译产物（自动生成）
│   ├── lib/                    #   libnice / libsrtp / libwebsockets 动态库
│   ├── include/                #   头文件
│   └── janus/                  #   Janus Gateway
│       ├── bin/janus           #     可执行文件
│       ├── etc/janus/          #     配置文件
│       ├── lib/janus/
│       │   ├── plugins/        #     插件 (.so)
│       │   └── transports/     #     Transport (.so)
│       └── share/janus/
│           └── html/           #     Janus 自带 Demo 页面
└── README.md                   # 本文档
```

## 6. 启动与停止

### 启动

```bash
./start_janus.sh
```

启动后终端会输出 Janus 日志，你会看到类似以下关键行：

```
Websockets server started (port 8188)...
HTTP webserver started (port 8088, /janus path listener)...
```

这表明两个 transport 都已就绪。

### 停止

新开一个终端：

```bash
./stop_janus.sh
```

或者直接在运行 Janus 的终端按 `Ctrl+C`。

### 后台运行

```bash
nohup ./start_janus.sh > janus.log 2>&1 &
echo $!    # 记录 PID
```

## 7. 验证服务

### 7.1 API 验证

```bash
# 查看服务器信息
curl -s http://localhost:8088/janus/info | python3 -m json.tool
```

正常返回中会包含：

```json
{
    "janus": "server_info",
    "version_string": "1.2.4",
    "plugins": {
        "janus.plugin.echotest": { ... },
        "janus.plugin.videoroom": { ... },
        ...
    }
}
```

### 7.2 Echo Test 页面测试

Echo Test 是最简单的 WebRTC 功能验证——你发出去的音视频会被服务器原样回传给你。

```bash
# 在 html 目录启动一个静态文件服务器
cd html && python3 -m http.server 8080
```

浏览器打开 `http://localhost:8080/echotest.html`。

**页面支持三种模式：**

| 模式 | 说明 | 适用场景 |
|------|------|------|
| 摄像头 | 使用真实摄像头和麦克风 | 有物理摄像头的本地机器 |
| 模拟视频 | Canvas 生成动态画面 | 无摄像头 / 远程服务器 / 摄像头被占用 |
| 纯音频 | 只使用麦克风 | 无摄像头但有麦克风 |

**如果摄像头被占用**，页面会自动检测并在 3 秒后切换到模拟视频模式。

### 7.3 测试流程

1. 选择一种模式，点击「开始测试」
2. 等待状态变为 **"WebRTC 连接已建立 - Echo 测试运行中"**
3. 左侧显示你的本地画面，右侧显示服务器回传的画面
4. 如果两边都有画面/声音，恭喜，Janus 工作正常！

## 8. 配置详解

配置文件位于 `local/janus/etc/janus/`，采用 JCFG 格式（类似 JSON 的 libconfig 语法）。

### 8.1 核心配置 `janus.jcfg`

```
general: {
    debug_level = 4          # 日志级别 0(关闭) ~ 7(最详细)
    admin_secret = "janusoverlord"  # Admin API 密钥
    server_name = "MyJanusInstance"
}

nat: {
    stun_server = "stun.l.google.com"   # STUN 服务器
    stun_port = 19302
    nice_debug = false
    ice_lite = false         # true=Lite模式(服务端不主动探测)
    full_trickle = true      # true=完整trickle ICE
    # nat_1_1_mapping = "公网IP"   # 云服务器必须设置
}

media: {
    max_nack_queue = 500     # NACK 队列长度(ms)
    no_media_timer = 1       # 无媒体超时(s)
}
```

### 8.2 HTTP Transport `janus.transport.http.jcfg`

```
general: {
    base_path = "/janus"     # API 路径前缀
    http = true              # 启用 HTTP
    port = 8088              # HTTP 端口
}

admin: {
    admin_base_path = "/admin"
    admin_http = true
    admin_port = 7088
}
```

### 8.3 WebSocket Transport `janus.transport.websockets.jcfg`

```
general: {
    ws = true                # 启用 WebSocket
    ws_port = 8188           # WebSocket 端口
    # wss = true             # 启用 WSS (加密 WebSocket)
    # wss_port = 8989
}
```

### 8.4 VideoRoom 插件 `janus.plugin.videoroom.jcfg`

```
general: {
    admin_key = "supersecret"
}

# 预配置房间
room-1234: {
    description = "Demo Room"
    publishers = 6           # 最大同时发布者
    bitrate = 512000         # 最大比特率 (bps)
    audiocodec = "opus"
    videocodec = "vp8,h264"
    record = false
}
```

## 9. 插件介绍

| 插件 | 文件名 | 说明 | 典型场景 |
|------|--------|------|----------|
| **EchoTest** | `libjanus_echotest.so` | 回显音视频，用于调试 | 验证 WebRTC 链路是否正常 |
| **VideoRoom** | `libjanus_videoroom.so` | SFU 多人视频会议 | 视频会议、在线课堂 |
| **VideoCall** | `libjanus_videocall.so` | 一对一视频/音频通话 | 点对点通信 |
| **AudioBridge** | `libjanus_audiobridge.so` | MCU 音频混音会议 | 语音会议、播客 |
| **Streaming** | `libjanus_streaming.so` | 将 RTP 流转为 WebRTC | 监控、直播、IPTV |
| **SIP** | `libjanus_sip.so` | SIP 协议网关 | 对接 IP 电话/PSTN |
| **RecordPlay** | `libjanus_recordplay.so` | 录制 WebRTC 并回放 | 课程录制、取证 |

## 10. Janus API 入门

Janus 的 API 基于 JSON 消息，无论 HTTP 还是 WebSocket 格式相同。完整交互流程如下：

### 10.1 创建 Session

```bash
curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"abc123"}' | python3 -m json.tool
```

返回：

```json
{
    "janus": "success",
    "data": { "id": 1234567890 }    // 这就是 session_id
}
```

### 10.2 Attach 到插件

```bash
curl -s -X POST http://localhost:8088/janus/1234567890 \
  -H "Content-Type: application/json" \
  -d '{"janus":"attach","plugin":"janus.plugin.echotest","transaction":"def456"}'
```

返回 `handle_id`。

### 10.3 发送消息 + SDP Offer

```bash
curl -s -X POST http://localhost:8088/janus/1234567890/9876543210 \
  -H "Content-Type: application/json" \
  -d '{
    "janus": "message",
    "transaction": "ghi789",
    "body": {"audio": true, "video": true},
    "jsep": {"type": "offer", "sdp": "v=0\r\n..."}
  }'
```

### 10.4 Long Poll 获取事件

```bash
curl -s http://localhost:8088/janus/1234567890?maxev=5
```

> **提示：** 生产环境推荐使用 WebSocket，可以实时收到事件推送，不需要 long poll。

### 10.5 WebSocket 交互示例

```javascript
const ws = new WebSocket('ws://localhost:8188', 'janus-protocol');

// 创建 session
ws.send(JSON.stringify({
    janus: 'create',
    transaction: 'txn_001'
}));

// 收到回复后 attach 插件
ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    console.log(msg);
};
```

## 11. 常见问题排查

### Q: 启动报 "error while loading shared libraries"

**原因：** 找不到编译的动态库。  
**解决：** 使用 `./start_janus.sh` 启动（脚本自动设置 `LD_LIBRARY_PATH`），不要直接调用 janus 二进制。

### Q: 浏览器提示 "Could not start video source"

**可能原因：**
- 摄像头被其他程序占用（微信/Zoom/OBS 等）→ 关闭占用程序，或使用「模拟视频」模式
- 通过 HTTP 远程访问 → 浏览器要求 HTTPS 才能调用 `getUserMedia`
- 没有物理摄像头 → 选择「模拟视频」模式

```bash
# 查看谁在占用摄像头
lsof /dev/video0
fuser /dev/video0
```

### Q: 页面提示 "WebSocket 连接失败" 或 "连接已关闭"

**原因：** Janus 没有运行，或端口被防火墙拦截。

```bash
# 检查 Janus 是否运行
pgrep -a janus

# 检查端口是否监听
ss -tlnp | grep -E '8088|8188'

# 测试 API
curl http://localhost:8088/janus/info
```

### Q: ICE 连接失败（WebRTC 建立不了）

**原因：** NAT 穿透失败。

- 本机测试：通常不会遇到此问题
- 云服务器：必须在 `janus.jcfg` 中设置 `nat_1_1_mapping` 为公网 IP
- 复杂网络：需要配置 TURN 服务器

### Q: 如何查看详细日志？

```bash
# 启动时设置更高日志级别
./start_janus.sh --debug-level=7
```

## 12. 进阶：生产环境部署

### 12.1 启用 HTTPS / WSS

WebRTC 在生产环境必须使用加密连接。使用 Let's Encrypt 获取免费证书后：

编辑 `janus.transport.http.jcfg`：
```
general: {
    https = true
    secure_port = 8089
}
certificates: {
    cert_pem = "/etc/letsencrypt/live/your-domain/fullchain.pem"
    cert_key = "/etc/letsencrypt/live/your-domain/privkey.pem"
}
```

编辑 `janus.transport.websockets.jcfg`：
```
general: {
    wss = true
    wss_port = 8989
}
certificates: {
    cert_pem = "/etc/letsencrypt/live/your-domain/fullchain.pem"
    cert_key = "/etc/letsencrypt/live/your-domain/privkey.pem"
}
```

### 12.2 配置 TURN 服务器

推荐使用 [coturn](https://github.com/coturn/coturn)：

```bash
sudo apt-get install coturn
```

在 `janus.jcfg` 中配置：
```
nat: {
    stun_server = "your-server.com"
    stun_port = 3478
    turn_server = "your-server.com"
    turn_port = 3478
    turn_type = "udp"
    turn_user = "janususer"
    turn_pwd = "januspassword"
    nat_1_1_mapping = "公网IP"
}
```

### 12.3 Nginx 反向代理

```nginx
upstream janus_http {
    server 127.0.0.1:8088;
}
upstream janus_ws {
    server 127.0.0.1:8188;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain/privkey.pem;

    location /janus {
        proxy_pass http://janus_http;
    }

    location /janus-ws {
        proxy_pass http://janus_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### 12.4 性能调优

```
# janus.jcfg
general: {
    debug_level = 1          # 生产环境降低日志级别
    session_timeout = 60
    no_media_timer = 1
}

media: {
    max_nack_queue = 1000    # 增大 NACK 队列应对丢包
    slowlink_threshold = 4
}
```

操作系统层面：
```bash
# 增大文件描述符限制
ulimit -n 65536

# 增大 UDP 缓冲区
sudo sysctl -w net.core.rmem_max=26214400
sudo sysctl -w net.core.rmem_default=26214400
```

## 13. 参考资料

- [Janus 官方文档](https://janus.conf.meetecho.com/docs/) - 最权威的参考
- [Janus GitHub](https://github.com/meetecho/janus-gateway) - 源码和 Issue
- [Janus REST API 文档](https://janus.conf.meetecho.com/docs/rest.html) - 完整 API 说明
- [Janus Plugin API 文档](https://janus.conf.meetecho.com/docs/pluginapi.html) - 插件开发指南
- [WebRTC 标准](https://webrtc.org/) - WebRTC 技术背景
- [ICE / STUN / TURN 协议](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols) - NAT 穿透原理
