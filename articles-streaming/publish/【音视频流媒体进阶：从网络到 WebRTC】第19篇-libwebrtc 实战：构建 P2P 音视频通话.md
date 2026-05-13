# libwebrtc 实战：构建 P2P 音视频通话

## 前言

前面四篇文章，我们从 WebRTC 的整体架构和信令设计出发，逐步深入了 ICE/STUN/TURN 的 NAT 穿越机制、DTLS-SRTP 的安全传输体系、以及 GCC/BBR 拥塞控制算法。到这里，WebRTC 的理论知识已经完备。但理论和实践之间，始终隔着一层"编译通过并跑起来"的距离。

本篇进入实战。

**libwebrtc** 是 Google 官方的 WebRTC C++ 实现，也是 Chromium 浏览器底层使用的媒体引擎。当我们在 Chrome 中调用 `RTCPeerConnection` 时，JavaScript API 背后驱动一切的就是这套 C++ 代码。它包含了完整的音视频采集、编解码、网络传输、拥塞控制、回声消除等能力，是目前功能最全、最经得起生产环境考验的 WebRTC 实现。

本文的目标很明确：**从源码编译 libwebrtc，使用其 Native C++ API 构建一个 1v1 音视频通话 Demo**。信令服务器复用第 15 篇中实现的 WebSocket 信令服务。完成本文后，你将拥有一个可以实际运行的端到端 WebRTC 通话程序，而不仅仅停留在浏览器 JavaScript Demo 的层面。

---

## 1. libwebrtc 编译指南

libwebrtc 的编译是整个实战的第一道门槛，也是劝退率最高的环节。它使用了 Chromium 的构建体系（depot_tools + GN + Ninja），与常规的 CMake 项目截然不同。

### 环境准备

推荐使用 **Ubuntu 22.04 LTS**，这是 Google 官方测试最充分的平台。确保至少 30GB 磁盘空间（源码 + 编译产物）和 8GB 以上内存。

安装基础依赖：

```bash
sudo apt update
sudo apt install -y git python3 python3-pip lsb-release sudo wget curl
```

### 安装 depot_tools

depot_tools 是 Chromium 系项目的工具集，包含 `gclient`、`gn`、`ninja` 等构建工具：

```bash
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH=$PWD/depot_tools:$PATH
# 建议写入 ~/.bashrc 或 ~/.zshrc 持久化
echo 'export PATH=$HOME/depot_tools:$PATH' >> ~/.bashrc
```

### 获取 WebRTC 源码

```bash
mkdir webrtc-checkout && cd webrtc-checkout
fetch --nohooks webrtc
gclient sync
```

`fetch webrtc` 会拉取 WebRTC 源码及其所有第三方依赖，整个过程可能需要 30 分钟到数小时（取决于网络状况）。国内网络环境下建议配置代理。

拉取完成后，源码位于 `src/` 目录，其目录结构大致如下：

```
src/
├── api/            # 对外暴露的公共 API（重点关注）
├── audio/          # 音频引擎
├── video/          # 视频引擎
├── media/          # 媒体抽象层
├── modules/        # 功能模块（编解码、RTP、拥塞控制等）
├── pc/             # PeerConnection 实现
├── call/           # 通话会话管理
├── rtc_base/       # 基础库（线程、网络、时间等）
├── p2p/            # ICE/STUN/TURN 实现
└── third_party/    # 第三方依赖
```

### 安装系统依赖

WebRTC 提供了一键安装脚本：

```bash
cd src
./build/install-build-deps.sh
```

### 编译选项配置（GN）

GN 是 Chromium 的元构建系统，用于生成 Ninja 构建文件。通过 `gn gen` 命令配置编译选项：

```bash
cd src

# Debug 构建（包含调试符号，编译产物较大）
gn gen out/Debug --args='
  is_debug=true
  is_component_build=false
  rtc_include_tests=false
  rtc_use_h264=true
  use_rtti=true
  treat_warnings_as_errors=false
'

# Release 构建（优化后的发布版本）
gn gen out/Release --args='
  is_debug=false
  is_component_build=false
  rtc_include_tests=false
  rtc_use_h264=true
  use_rtti=true
  treat_warnings_as_errors=false
  symbol_level=0
'
```

几个关键参数说明：

| 参数 | 说明 |
|------|------|
| `is_component_build=false` | 编译为静态库（推荐），避免运行时依赖大量 .so 文件 |
| `rtc_include_tests=false` | 不编译测试代码，显著减少编译时间 |
| `rtc_use_h264=true` | 包含 H.264 编解码支持（通过 OpenH264） |
| `use_rtti=true` | 启用 C++ RTTI，某些场景下需要 |

你可以用 `gn args out/Debug --list` 查看所有可用的编译选项。

### 编译

```bash
# 使用 Ninja 编译（-j 指定并行任务数）
ninja -C out/Debug
# 或编译 Release 版本
ninja -C out/Release
```

首次编译可能需要 30 分钟到 1 小时以上，取决于机器性能。后续增量编译会快很多。

### 编译产物

编译完成后，核心产物包括：

- `out/Debug/obj/libwebrtc.a` — 静态库，包含 WebRTC 的全部功能
- `src/api/` 目录下的头文件 — Native API 的公共接口

在你的项目中，需要链接 `libwebrtc.a` 并引用 `src/` 及 `src/third_party/abseil-cpp/` 下的头文件。

### 常见编译问题

**Python 版本冲突**：depot_tools 依赖特定版本的 Python，如果系统中有多个 Python 版本可能冲突。使用 depot_tools 自带的 `vpython3` 可以避免这类问题。

**磁盘空间不足**：Debug 编译产物可能超过 20GB，确保磁盘充足。

**网络问题**：`gclient sync` 需要下载大量依赖，失败后重新执行即可（支持断点续传）。

---

## 2. libwebrtc Native API 概览

编译通过只是第一步。要用 libwebrtc 写业务代码，需要理解它对外暴露的核心接口。所有公共 API 定义在 `src/api/` 目录下，这也是 Google 承诺保持相对稳定的接口层。

### 核心接口

![libwebrtc API层次](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/libwebrtc_api.png)

**PeerConnectionFactoryInterface**

这是整个 API 的入口点，相当于一个"工厂"。通过它创建 PeerConnection、AudioSource、VideoSource 等对象。一个进程通常只需要一个 Factory 实例。

```cpp
// api/peer_connection_interface.h
class PeerConnectionFactoryInterface {
public:
    virtual rtc::scoped_refptr<PeerConnectionInterface> CreatePeerConnectionOrError(
        const PeerConnectionInterface::RTCConfiguration& config,
        PeerConnectionDependencies dependencies) = 0;

    virtual rtc::scoped_refptr<AudioSourceInterface> CreateAudioSource(
        const cricket::AudioOptions& options) = 0;

    virtual rtc::scoped_refptr<VideoTrackInterface> CreateVideoTrack(
        rtc::scoped_refptr<VideoTrackSourceInterface> source,
        absl::string_view id) = 0;
    // ...
};
```

**PeerConnectionInterface**

WebRTC 的核心对象，对应 JavaScript 中的 `RTCPeerConnection`。它管理着 ICE 连接、DTLS 握手、SDP 协商、媒体收发的全部生命周期。

```cpp
class PeerConnectionInterface {
public:
    virtual RTCErrorOr<rtc::scoped_refptr<RtpSenderInterface>>
        AddTrack(rtc::scoped_refptr<MediaStreamTrackInterface> track,
                 const std::vector<std::string>& stream_ids) = 0;

    virtual void CreateOffer(
        CreateSessionDescriptionObserver* observer,
        const RTCOfferAnswerOptions& options) = 0;

    virtual void CreateAnswer(
        CreateSessionDescriptionObserver* observer,
        const RTCOfferAnswerOptions& options) = 0;

    virtual void SetLocalDescription(
        SetSessionDescriptionObserver* observer,
        SessionDescriptionInterface* desc) = 0;

    virtual void SetRemoteDescription(
        SetSessionDescriptionObserver* observer,
        SessionDescriptionInterface* desc) = 0;

    virtual bool AddIceCandidate(const IceCandidateInterface* candidate) = 0;

    virtual void Close() = 0;
    // ...
};
```

**Observer 接口**

libwebrtc 大量使用观察者模式。异步操作通过 Observer 回调通知结果：

- `PeerConnectionObserver` — 监听 ICE 状态变化、远端 Track 到达、DataChannel 创建等事件
- `CreateSessionDescriptionObserver` — CreateOffer/CreateAnswer 的异步回调
- `SetSessionDescriptionObserver` — SetLocalDescription/SetRemoteDescription 的回调

**MediaStreamTrack 体系**

音视频数据通过 Track 抽象传输：

- `AudioSourceInterface` → `AudioTrackInterface` — 音频采集源和音频轨
- `VideoTrackSourceInterface` → `VideoTrackInterface` — 视频采集源和视频轨
- `MediaStreamInterface` — 将多个 Track 组合成一路媒体流

### 线程模型

libwebrtc 内部维护三个核心线程，理解它们是避免死锁和崩溃的关键：

| 线程 | 职责 | 典型操作 |
|------|------|----------|
| **Signaling Thread** | API 调用和信令处理 | CreateOffer、SetRemoteDescription、AddTrack |
| **Worker Thread** | 媒体数据处理 | 编解码、音频处理、RTP 收发 |
| **Network Thread** | 网络 I/O | ICE 连通性检查、DTLS 握手、数据包收发 |

大多数 API 方法必须在 Signaling Thread 上调用。如果你在错误的线程上调用 API，Debug 模式下会触发断言失败。通过 `rtc::Thread::Current()` 可以检查当前线程，`thread->PostTask()` 可以将任务投递到指定线程执行。

```cpp
signaling_thread->PostTask([pc = peer_connection_]() {
    pc->CreateOffer(observer, options);
});
```

---

## 3. C++ 实战：构建 1v1 通话 Demo

### 系统架构

整个 Demo 由三个部分组成：

1. **信令服务器**：复用第 15 篇实现的 WebSocket 信令服务，负责转发 SDP Offer/Answer 和 ICE Candidate
2. **Peer A**（Offerer）：采集本地音视频，发起通话
3. **Peer B**（Answerer）：接收来自 Peer A 的通话请求，回复 Answer

两个 Peer 运行相同的 C++ 程序，通过命令行参数区分角色。信令通信使用 JSON 格式，消息类型与第 15 篇保持一致：`join`、`offer`、`answer`、`candidate`。

### 创建 PeerConnectionFactory

Factory 是所有操作的起点。创建时需要指定线程模型和媒体引擎的编解码器工厂：

```cpp
#include "api/create_peerconnection_factory.h"
#include "api/audio_codecs/builtin_audio_decoder_factory.h"
#include "api/audio_codecs/builtin_audio_encoder_factory.h"
#include "api/video_codecs/builtin_video_decoder_factory.h"
#include "api/video_codecs/builtin_video_encoder_factory.h"
#include "api/task_queue/default_task_queue_factory.h"

class WebRTCClient {
public:
    bool Initialize() {
        signaling_thread_ = rtc::Thread::Create();
        signaling_thread_->SetName("signaling", nullptr);
        signaling_thread_->Start();

        worker_thread_ = rtc::Thread::Create();
        worker_thread_->SetName("worker", nullptr);
        worker_thread_->Start();

        network_thread_ = rtc::Thread::CreateWithSocketServer();
        network_thread_->SetName("network", nullptr);
        network_thread_->Start();

        factory_ = webrtc::CreatePeerConnectionFactory(
            network_thread_.get(),
            worker_thread_.get(),
            signaling_thread_.get(),
            nullptr,  // ADM，传 nullptr 使用默认音频设备
            webrtc::CreateBuiltinAudioEncoderFactory(),
            webrtc::CreateBuiltinAudioDecoderFactory(),
            webrtc::CreateBuiltinVideoEncoderFactory(),
            webrtc::CreateBuiltinVideoDecoderFactory(),
            nullptr,  // audio_mixer
            nullptr   // audio_processing
        );

        return factory_ != nullptr;
    }

private:
    std::unique_ptr<rtc::Thread> signaling_thread_;
    std::unique_ptr<rtc::Thread> worker_thread_;
    std::unique_ptr<rtc::Thread> network_thread_;
    rtc::scoped_refptr<webrtc::PeerConnectionFactoryInterface> factory_;
};
```

`CreatePeerConnectionFactory` 的参数依次指定了网络线程、工作线程、信令线程、音频设备模块（ADM）、音视频编解码器工厂。传 `nullptr` 作为 ADM 时，libwebrtc 会自动创建默认的音频采集模块。

### 创建 PeerConnection

有了 Factory，就可以创建 PeerConnection 并配置 ICE 服务器：

```cpp
class PeerConnectionCallback : public webrtc::PeerConnectionObserver {
public:
    // ICE 候选就绪，需要通过信令发送给对端
    void OnIceCandidate(const webrtc::IceCandidateInterface* candidate) override {
        std::string sdp;
        candidate->ToString(&sdp);

        json msg;
        msg["type"] = "candidate";
        msg["candidate"] = sdp;
        msg["sdpMid"] = candidate->sdp_mid();
        msg["sdpMLineIndex"] = candidate->sdp_mline_index();
        // 通过信令通道发送给对端
        signaling_->Send(msg.dump());
    }

    // ICE 连接状态变化
    void OnIceConnectionChange(
        webrtc::PeerConnectionInterface::IceConnectionState state) override {
        std::cout << "ICE connection state: " << static_cast<int>(state) << std::endl;
    }

    // 远端添加了 Track
    void OnAddTrack(
        rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver,
        const std::vector<rtc::scoped_refptr<webrtc::MediaStreamInterface>>& streams) override {
        auto track = receiver->track();
        if (track->kind() == webrtc::MediaStreamTrackInterface::kVideoKind) {
            auto* video_track = static_cast<webrtc::VideoTrackInterface*>(track.get());
            video_track->AddOrUpdateSink(video_renderer_, rtc::VideoSinkWants());
        }
    }

    void OnSignalingChange(
        webrtc::PeerConnectionInterface::SignalingState state) override {}
    void OnDataChannel(
        rtc::scoped_refptr<webrtc::DataChannelInterface> channel) override {}
    void OnRenegotiationNeeded() override {}
    void OnIceGatheringChange(
        webrtc::PeerConnectionInterface::IceGatheringState state) override {}

    SignalingChannel* signaling_ = nullptr;
    VideoRenderer* video_renderer_ = nullptr;
};
```

```cpp
bool WebRTCClient::CreatePeerConnection() {
    webrtc::PeerConnectionInterface::RTCConfiguration config;

    webrtc::PeerConnectionInterface::IceServer stun_server;
    stun_server.uri = "stun:stun.l.google.com:19302";
    config.servers.push_back(stun_server);

    // 如果需要 TURN 中继（对称 NAT 环境）
    webrtc::PeerConnectionInterface::IceServer turn_server;
    turn_server.uri = "turn:your-turn-server.com:3478";
    turn_server.username = "user";
    turn_server.password = "pass";
    config.servers.push_back(turn_server);

    config.sdp_semantics = webrtc::SdpSemantics::kUnifiedPlan;

    observer_ = std::make_unique<PeerConnectionCallback>();
    observer_->signaling_ = signaling_.get();

    webrtc::PeerConnectionDependencies deps(observer_.get());
    auto result = factory_->CreatePeerConnectionOrError(config, std::move(deps));
    if (!result.ok()) {
        std::cerr << "Failed to create PeerConnection: "
                  << result.error().message() << std::endl;
        return false;
    }
    peer_connection_ = result.MoveValue();
    return true;
}
```

注意 `sdp_semantics` 设置为 `kUnifiedPlan`，这是 WebRTC 1.0 标准要求的语义模型（已取代旧的 Plan B）。

### 添加本地音视频 Track

```cpp
void WebRTCClient::AddLocalTracks() {
    // 添加音频 Track
    cricket::AudioOptions audio_options;
    auto audio_source = factory_->CreateAudioSource(audio_options);
    auto audio_track = factory_->CreateAudioTrack("audio0", audio_source.get());
    auto audio_result = peer_connection_->AddTrack(audio_track, {"stream0"});
    if (!audio_result.ok()) {
        std::cerr << "Failed to add audio track" << std::endl;
    }

    // 添加视频 Track（使用摄像头采集，详见第 4 节）
    auto video_source = CreateCameraSource();
    auto video_track = factory_->CreateVideoTrack(video_source, "video0");
    auto video_result = peer_connection_->AddTrack(video_track, {"stream0"});
    if (!video_result.ok()) {
        std::cerr << "Failed to add video track" << std::endl;
    }
}
```

### 创建 Offer / 处理 Answer

SDP 的创建和设置是异步操作，通过 Observer 回调获取结果：

```cpp
class CreateSDPCallback : public webrtc::CreateSessionDescriptionObserver {
public:
    using Callback = std::function<void(webrtc::SessionDescriptionInterface*)>;
    explicit CreateSDPCallback(Callback cb) : callback_(std::move(cb)) {}

    void OnSuccess(webrtc::SessionDescriptionInterface* desc) override {
        callback_(desc);
    }
    void OnFailure(webrtc::RTCError error) override {
        std::cerr << "SDP creation failed: " << error.message() << std::endl;
    }

private:
    Callback callback_;
};

class SetSDPCallback : public webrtc::SetSessionDescriptionObserver {
public:
    void OnSuccess() override {}
    void OnFailure(webrtc::RTCError error) override {
        std::cerr << "SetDescription failed: " << error.message() << std::endl;
    }
};

// Offerer：创建并发送 Offer
void WebRTCClient::CreateAndSendOffer() {
    webrtc::PeerConnectionInterface::RTCOfferAnswerOptions options;
    options.offer_to_receive_audio = 1;
    options.offer_to_receive_video = 1;

    auto callback = rtc::make_ref_counted<CreateSDPCallback>(
        [this](webrtc::SessionDescriptionInterface* desc) {
            std::string sdp_str;
            desc->ToString(&sdp_str);

            auto set_sdp_observer = rtc::make_ref_counted<SetSDPCallback>();
            peer_connection_->SetLocalDescription(set_sdp_observer.get(), desc);

            json msg;
            msg["type"] = "offer";
            msg["sdp"] = sdp_str;
            signaling_->Send(msg.dump());
        });

    peer_connection_->CreateOffer(callback.get(), options);
}

// Answerer：收到 Offer 后创建 Answer
void WebRTCClient::OnOfferReceived(const std::string& sdp) {
    auto offer = webrtc::CreateSessionDescription(
        webrtc::SdpType::kOffer, sdp);

    peer_connection_->SetRemoteDescription(
        rtc::make_ref_counted<SetSDPCallback>().get(), offer.release());

    auto callback = rtc::make_ref_counted<CreateSDPCallback>(
        [this](webrtc::SessionDescriptionInterface* desc) {
            std::string sdp_str;
            desc->ToString(&sdp_str);

            auto set_sdp_observer = rtc::make_ref_counted<SetSDPCallback>();
            peer_connection_->SetLocalDescription(set_sdp_observer.get(), desc);

            json msg;
            msg["type"] = "answer";
            msg["sdp"] = sdp_str;
            signaling_->Send(msg.dump());
        });

    peer_connection_->CreateAnswer(callback.get(), {});
}

// Offerer：收到 Answer 后设置
void WebRTCClient::OnAnswerReceived(const std::string& sdp) {
    auto answer = webrtc::CreateSessionDescription(
        webrtc::SdpType::kAnswer, sdp);
    peer_connection_->SetRemoteDescription(
        rtc::make_ref_counted<SetSDPCallback>().get(), answer.release());
}
```

### ICE 候选交换

ICE Candidate 通过 `PeerConnectionObserver::OnIceCandidate` 回调产生（前面已实现），收到对端的 Candidate 后添加：

```cpp
void WebRTCClient::OnRemoteCandidateReceived(const json& msg) {
    std::string sdp = msg["candidate"];
    std::string sdp_mid = msg["sdpMid"];
    int sdp_mline_index = msg["sdpMLineIndex"];

    webrtc::SdpParseError error;
    auto candidate = webrtc::CreateIceCandidate(
        sdp_mid, sdp_mline_index, sdp, &error);
    if (!candidate) {
        std::cerr << "Failed to parse ICE candidate: "
                  << error.description << std::endl;
        return;
    }

    if (!peer_connection_->AddIceCandidate(candidate.get())) {
        std::cerr << "Failed to add ICE candidate" << std::endl;
    }
}
```

### 远端媒体渲染

远端视频到达时，通过 `OnAddTrack` 回调获取 VideoTrack，注册一个 VideoSink 来接收解码后的视频帧：

```cpp
class SimpleVideoRenderer : public rtc::VideoSinkInterface<webrtc::VideoFrame> {
public:
    void OnFrame(const webrtc::VideoFrame& frame) override {
        // frame.video_frame_buffer() 可以获取 I420 格式的像素数据
        // 渲染到窗口或写入文件取决于你的需求
        auto buffer = frame.video_frame_buffer()->ToI420();
        int width = buffer->width();
        int height = buffer->height();

        // 实际项目中这里对接 SDL、OpenGL 或其他渲染引擎
        std::cout << "Received video frame: "
                  << width << "x" << height << std::endl;
    }
};
```

### CMake 构建配置

将 libwebrtc 集成到你的 CMake 项目中，关键是正确设置头文件路径和链接静态库：

```cmake
cmake_minimum_required(VERSION 3.20)
project(webrtc_p2p_demo)

set(CMAKE_CXX_STANDARD 17)

# libwebrtc 源码和编译产物路径
set(WEBRTC_SRC_DIR "/path/to/webrtc-checkout/src")
set(WEBRTC_BUILD_DIR "${WEBRTC_SRC_DIR}/out/Release")

add_executable(p2p_demo
    main.cpp
    webrtc_client.cpp
    signaling_channel.cpp
    video_renderer.cpp
)

target_include_directories(p2p_demo PRIVATE
    ${WEBRTC_SRC_DIR}
    ${WEBRTC_SRC_DIR}/third_party/abseil-cpp
    ${WEBRTC_SRC_DIR}/third_party/libyuv/include
)

target_compile_definitions(p2p_demo PRIVATE
    WEBRTC_POSIX
    WEBRTC_LINUX
)

target_link_libraries(p2p_demo PRIVATE
    ${WEBRTC_BUILD_DIR}/obj/libwebrtc.a
    pthread
    dl
    X11
    Xext
)

# Boost.Beast 用于 WebSocket 信令通道
find_package(Boost REQUIRED COMPONENTS system)
find_package(nlohmann_json REQUIRED)

target_link_libraries(p2p_demo PRIVATE
    Boost::system
    nlohmann_json::nlohmann_json
)
```

需要特别注意的是 `WEBRTC_POSIX` 和 `WEBRTC_LINUX` 这两个宏定义，缺少它们会导致大量条件编译错误。

---

## 4. 音频与视频采集

### 音频采集：AudioDeviceModule

libwebrtc 内置了完整的音频采集模块（AudioDeviceModule，简称 ADM），在创建 PeerConnectionFactory 时传入 `nullptr` 就会使用默认实现。默认 ADM 在 Linux 上通过 PulseAudio 或 ALSA 采集麦克风音频，自动处理采样率转换、通道映射等细节。

如果需要指定音频设备或自定义参数：

```cpp
#include "modules/audio_device/include/audio_device.h"

auto adm = webrtc::AudioDeviceModule::Create(
    webrtc::AudioDeviceModule::kPlatformDefaultAudio,
    task_queue_factory.get());

// 枚举录音设备
int16_t num_devices = adm->RecordingDevices();
for (int16_t i = 0; i < num_devices; ++i) {
    char name[webrtc::kAdmMaxDeviceNameSize];
    char guid[webrtc::kAdmMaxGuidSize];
    adm->RecordingDeviceName(i, name, guid);
    std::cout << "Recording device " << i << ": " << name << std::endl;
}

// 选择指定设备
adm->SetRecordingDevice(0);
```

音频引擎还内置了强大的 3A 处理能力：

- **AEC（Acoustic Echo Cancellation）**：回声消除，避免扬声器输出的声音被麦克风再次采集
- **NS（Noise Suppression）**：噪声抑制
- **AGC（Automatic Gain Control）**：自动增益控制

这些处理默认启用，可以通过 `AudioProcessing` 接口进行精细配置。

### 视频采集：VideoCaptureModule

视频采集的方式比音频灵活得多。libwebrtc 提供了 `VideoCaptureModule` 用于摄像头采集，同时也支持自定义视频源。

**使用摄像头采集：**

```cpp
#include "modules/video_capture/video_capture_factory.h"

rtc::scoped_refptr<webrtc::VideoTrackSourceInterface> CreateCameraSource() {
    std::unique_ptr<webrtc::VideoCaptureModule::DeviceInfo> info(
        webrtc::VideoCaptureFactory::CreateDeviceInfo());

    int num_devices = info->NumberOfDevices();
    if (num_devices == 0) {
        std::cerr << "No camera found" << std::endl;
        return nullptr;
    }

    // 获取第一个摄像头的设备 ID
    char device_name[256];
    char device_id[256];
    info->GetDeviceName(0, device_name, sizeof(device_name),
                        device_id, sizeof(device_id));
    std::cout << "Using camera: " << device_name << std::endl;

    // 查询支持的采集能力
    webrtc::VideoCaptureCapability capability;
    info->GetCapability(device_id, 0, capability);

    auto capturer = webrtc::VideoCaptureFactory::Create(device_id);
    capturer->StartCapture(capability);

    // 将 capturer 包装为 VideoTrackSource
    // 实际实现需要一个适配器类，将 capturer 帧回调桥接到 VideoTrackSource
    return CreateVideoTrackSourceFromCapturer(std::move(capturer));
}
```

**自定义视频源：**

从文件、屏幕截图或自定义渲染管线输入视频帧时，需要实现 `VideoTrackSourceInterface`：

```cpp
#include "api/video/video_frame.h"
#include "api/video/i420_buffer.h"
#include "media/base/adapted_video_track_source.h"

class CustomVideoSource : public rtc::AdaptedVideoTrackSource {
public:
    // 外部调用此方法推送视频帧
    void PushFrame(const uint8_t* rgba_data, int width, int height) {
        auto i420_buffer = webrtc::I420Buffer::Create(width, height);

        // RGBA 内存布局 -> I420（libyuv 使用寄存器序命名，ABGR 即内存中的 RGBA）
        libyuv::ABGRToI420(
            rgba_data, width * 4,
            i420_buffer->MutableDataY(), i420_buffer->StrideY(),
            i420_buffer->MutableDataU(), i420_buffer->StrideU(),
            i420_buffer->MutableDataV(), i420_buffer->StrideV(),
            width, height);

        auto frame = webrtc::VideoFrame::Builder()
            .set_video_frame_buffer(i420_buffer)
            .set_timestamp_us(rtc::TimeMicros())
            .build();

        OnFrame(frame);
    }

    webrtc::MediaSourceInterface::SourceState state() const override {
        return kLive;
    }
    bool remote() const override { return false; }
    bool is_screencast() const override { return false; }
    absl::optional<bool> needs_denoising() const override {
        return absl::nullopt;
    }
};
```

这个自定义视频源在很多实际场景中非常有用——比如从视频文件读取帧进行测试、从 GPU 渲染管线获取画面（云游戏）、或者从屏幕采集实现远程桌面。

---

## 5. 常见问题排查与调优

### 编译相关

**符号未定义（链接顺序问题）**

这是最常见的编译问题。libwebrtc.a 是一个超大的静态库，但它依赖的某些系统库需要显式链接。典型报错和解决方案：

```
undefined reference to `dlopen` → 添加 -ldl
undefined reference to `pthread_create` → 添加 -lpthread
undefined reference to `XOpenDisplay` → 添加 -lX11
```

在 CMake 中，链接顺序也很重要——`libwebrtc.a` 应放在你自己的源文件之后、系统库之前。

**头文件找不到**

libwebrtc 的头文件 `#include` 路径都是相对于源码根目录的，例如 `#include "api/peer_connection_interface.h"`。确保源码根目录 `src/` 在 include path 中。同时，Abseil 的头文件路径需要单独添加 `src/third_party/abseil-cpp/`。

### 运行时

**ICE 连接失败**

ICE 失败是最常见的运行时问题，表现为 `IceConnectionState` 停留在 `checking` 或转为 `failed`。排查思路：

1. **STUN 服务器是否可达**：用 `stunclient` 工具测试，确认能获取到 server reflexive 地址
2. **防火墙规则**：确保 UDP 端口未被屏蔽，WebRTC 默认使用的端口范围较宽
3. **对称 NAT 环境**：两端都在对称 NAT 后面时，STUN 无法穿越，必须配置 TURN 服务器
4. **TURN 服务器配置**：检查用户名密码是否正确，是否支持 UDP 和 TCP relay

**没有音视频**

连接建立成功但看不到画面、听不到声音：

1. **编解码不匹配**：检查双方 SDP 是否协商出了共同支持的 codec。如果一端只支持 VP8 而另一端只支持 H.264，就无法通信
2. **Track 未添加**：确保在 CreateOffer 之前就调用了 `AddTrack`
3. **远端 Track 未渲染**：确认实现了 `OnAddTrack` 回调并注册了 VideoSink

**单向通话（只有一端有画面）**

通常是 SDP 方向属性配置不正确。检查 SDP 中 `a=sendrecv`、`a=sendonly`、`a=recvonly` 属性。确保双方都设置了 `offer_to_receive_audio` 和 `offer_to_receive_video`。

### 调优

**配置编码器**

使用内置编码器工厂时，可以通过 `RtpSender` 的 `RtpParameters` 控制编码参数：

```cpp
auto sender = peer_connection_->GetSenders()[0];
auto params = sender->GetParameters();

if (!params.encodings.empty()) {
    params.encodings[0].max_bitrate_bps = 2000000;   // 最大码率 2Mbps
    params.encodings[0].max_framerate = 30;           // 最大帧率 30fps
    params.encodings[0].scale_resolution_down_by = 1; // 不缩放
}

sender->SetParameters(params);
```

**设置视频分辨率**

视频分辨率由采集源决定。通过 `VideoTrackSourceInterface` 的 `AdaptedVideoTrackSource` 可以在采集阶段控制分辨率和帧率，也可以在编码阶段通过 `RtpParameters` 动态调整。

**启用 Simulcast**

Simulcast 让发送端同时编码多个分辨率层（如 720p + 360p + 180p），接收端根据网络状况选择合适的层。在 SFU 架构中尤其有用：

```cpp
webrtc::RtpTransceiverInit init;
init.direction = webrtc::RtpTransceiverDirection::kSendRecv;

// 配置三层 Simulcast
webrtc::RtpEncodingParameters high, mid, low;
high.rid = "h";
high.max_bitrate_bps = 2000000;
mid.rid = "m";
mid.max_bitrate_bps = 500000;
mid.scale_resolution_down_by = 2;
low.rid = "l";
low.max_bitrate_bps = 150000;
low.scale_resolution_down_by = 4;

init.send_encodings = {high, mid, low};

peer_connection_->AddTransceiver(
    video_track, init);
```

---

## 6. 替代方案

libwebrtc 功能完整但体量庞大、编译复杂。根据项目需求，你可能会考虑更轻量的替代方案。

### Pion WebRTC

[Pion](https://github.com/pion/webrtc) 是用 Go 语言实现的 WebRTC 库，是 Go 生态中最流行的 WebRTC 方案。

**优势**：纯 Go 实现，`go get` 即可引入，无需处理 C++ 编译问题。代码质量高，文档和示例丰富。非常适合用 Go 开发 SFU 服务器或后端媒体处理服务。

**局限**：音视频编解码、回声消除等能力需要外部库配合。不适合做端侧客户端（Go 不适合移动端开发）。

### libdatachannel

[libdatachannel](https://github.com/paullouisageneau/libdatachannel) 是一个轻量级的 C/C++ WebRTC 实现，专注于 DataChannel，同时也支持媒体传输。

**优势**：代码量小（相比 libwebrtc 小两个数量级），编译简单（标准 CMake），依赖少。如果你只需要 DataChannel 或者简单的媒体转发，它是理想选择。

**局限**：不包含音视频采集、编解码、回声消除等端侧能力。更适合服务端或者对 WebRTC 功能需求不完整的场景。

### GStreamer WebRTC 插件

GStreamer 的 `webrtcbin` 插件在 GStreamer 的管线（pipeline）框架内集成了 WebRTC 能力。

**优势**：可以利用 GStreamer 丰富的编解码和媒体处理插件，构建灵活的媒体管线。适合需要复杂媒体处理（转码、混流、滤镜）的场景。

**局限**：学习曲线陡峭，WebRTC 的某些高级特性（如 Simulcast）支持程度不如 libwebrtc。

### 选型建议

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 客户端应用（桌面/移动端） | libwebrtc | 功能完整，音视频全栈能力 |
| Go 语言后端 / SFU 服务器 | Pion | 生态成熟，开发效率高 |
| 只需 DataChannel / 轻量服务端 | libdatachannel | 编译简单，依赖少 |
| 复杂媒体处理管线 | GStreamer webrtcbin | 管线灵活，插件丰富 |
| 快速原型验证 | Pion 或 libdatachannel | 上手快，调试方便 |

实际项目中，混合使用也很常见——例如用 libwebrtc 做客户端，用 Pion 做 SFU 服务器，两者通过标准 WebRTC 协议互通，这是很多视频会议产品的典型架构。

---

## 总结

本文从 libwebrtc 的编译开始，逐步介绍了 Native API 的核心接口、线程模型，并通过完整的代码示例演示了如何构建一个 1v1 音视频通话程序。到此为止，WebRTC 系列的五篇文章已经覆盖了从理论到实践的完整链路：

- **第 15 篇**：WebRTC 协议栈全景、信令设计与 WebSocket 信令服务器实现
- **第 16 篇**：ICE/STUN/TURN 的 NAT 穿越原理与 coturn 部署
- **第 17 篇**：DTLS-SRTP 的安全传输机制与密钥协商流程
- **第 18 篇**：GCC 和 BBR 拥塞控制算法在 WebRTC 中的应用
- **第 19 篇（本文）**：libwebrtc 编译、Native API 使用与 P2P 通话实战

需要强调的是，本文给出的是核心流程和关键代码片段。一个生产级的 WebRTC 客户端还需要处理很多细节：错误恢复、ICE 重启、动态码率适应、多设备管理、渲染优化等。但有了本文的基础框架，你可以在此之上逐步完善。

libwebrtc 的源码本身就是最好的学习材料。当你遇到 API 行为不符合预期时，直接阅读 `src/pc/` 下的 PeerConnection 实现代码，往往比查文档更高效。

下一篇，我们将离开 WebRTC 的微观世界，进入综合实战环节——**构建一套完整的直播系统**。我们会将前面学到的 RTMP 推流、HLS 分发、SRS 媒体服务器等知识整合到一个端到端的直播方案中。
