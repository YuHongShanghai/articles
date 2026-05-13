# HLS 协议原理与实践

## 前言

在前面几篇文章中，我们深入剖析了 RTSP、RTMP 和 FLV 这些经典流媒体协议。它们各有所长，但也各有痛点——RTSP 部署复杂、RTMP 依赖 Flash 生态日渐式微、HTTP-FLV 在移动端浏览器中的兼容性参差不齐。有没有一种协议，既能利用成熟的 HTTP 基础设施，又能在几乎所有终端设备上原生播放？

答案是 **HLS（HTTP Live Streaming）**。

HLS 是苹果在 2009 年推出的自适应流媒体协议。它的核心思想非常朴素：把媒体流切成一个个小文件，用一个播放列表来索引这些文件，客户端通过标准的 HTTP 请求逐个下载播放。这个设计让 HLS 天然兼容所有 CDN 和 HTTP 缓存基础设施，iOS/Android/主流浏览器均原生支持，使其成为当今点播和直播分发的绝对主力。

当然，HLS 的代价也很明显——传统 HLS 的端到端延迟通常在 10-30 秒，远不及 RTMP 或 WebRTC。不过苹果后来推出的 LL-HLS（Low-Latency HLS）已将延迟压缩到 2-3 秒，大幅缩小了差距。

本文将深入 HLS 的协议架构，逐一拆解 M3U8 格式、多码率自适应、TS 容器以及 LL-HLS 的低延迟机制，最后用 C++ 实现一个简易的 HLS 切片器。

---

## 1. HLS 协议概述

### 基本架构

HLS 的整体架构非常清晰，由三个角色组成：

- **Server（服务端）**：编码器将音视频编码后，按固定时长切分为 TS 媒体切片，同时生成/更新 M3U8 播放列表文件
- **CDN（分发网络）**：标准的 HTTP CDN，负责缓存和分发 M3U8 文件与 TS 切片
- **Client（播放器）**：定时拉取 M3U8 文件获取切片列表，按顺序下载 TS 切片并解码播放

![HLS架构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/hls_architecture.png)

### 核心组件

HLS 只依赖两种文件：

**M3U8 Playlist**：一个 UTF-8 编码的文本文件，本质上是一个 `.m3u8` 扩展名的播放列表。它包含一系列标签和 URI，告诉播放器有哪些切片可以播放、每个切片的时长是多少、当前播放的起始序列号等元信息。

**TS 媒体切片**：MPEG-2 Transport Stream 格式的媒体文件，通常时长为 2-10 秒。每个 TS 文件都可以独立解码（以关键帧开头），这使得播放器可以从任意切片开始播放。

### 工作流程

一次完整的 HLS 播放流程如下：

1. 播放器请求 M3U8 URL，获取播放列表
2. 如果是 Master Playlist，播放器根据带宽选择合适的码率流，再请求对应的 Media Playlist
3. 播放器解析 Media Playlist，获取 TS 切片 URL 列表
4. 按顺序下载 TS 切片，送入解码器播放
5. 直播场景下，播放器每隔一个切片时长重新请求 M3U8，获取新的切片信息

这个设计的精妙之处在于：整个过程只用到 HTTP GET 请求，没有任何专有协议。防火墙友好、CDN 友好、代理友好——这正是 HLS 能大规模普及的根本原因。

---

## 2. M3U8 Playlist 格式详解

M3U8 是 HLS 的"大脑"，播放器的所有行为都由它驱动。下面逐一讲解核心标签。

### 核心标签

**`#EXTM3U`**：文件头标识，必须出现在第一行，表明这是一个扩展 M3U 文件。

**`#EXT-X-VERSION:<n>`**：协议版本号。不同版本支持的特性不同，例如 version 3 支持浮点 EXTINF 时长，version 7 支持 MAP 标签。常用版本为 3 或 7。

**`#EXT-X-TARGETDURATION:<s>`**：所有切片的最大时长（秒，整数）。播放器用这个值来决定 Playlist 的刷新间隔。例如设为 6，则播放器大约每 6 秒请求一次新的 M3U8。

**`#EXTINF:<duration>,[<title>]`**：紧随其后的 URI 对应切片的时长。这是每个切片的"身份证"。duration 在 version 3 及以上支持浮点数（如 5.005），title 通常留空。

**`#EXT-X-MEDIA-SEQUENCE:<number>`**：Playlist 中第一个切片的序列号。直播场景中，服务端会不断追加新切片、移除旧切片，播放器通过序列号判断哪些切片是新增的、哪些已经过期。

**`#EXT-X-ENDLIST`**：表示 Playlist 不会再更新。出现这个标签意味着这是一个点播（VOD）流，播放器无需再刷新。

### 直播 vs 点播

**直播 Playlist（Live/Event）**：

- 没有 `#EXT-X-ENDLIST` 标签
- 服务端持续追加新切片，同时移除旧切片（滑动窗口）
- 播放器定时轮询更新
- 通常只保留最近 3-5 个切片

**点播 Playlist（VOD）**：

- 包含 `#EXT-X-ENDLIST` 标签
- 列出所有切片，不会再变化
- 播放器可以随意拖动进度条（Seek）

### 完整示例

一个典型的直播 M3U8 文件：

```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:2680

#EXTINF:5.005,
segment2680.ts
#EXTINF:5.005,
segment2681.ts
#EXTINF:4.838,
segment2682.ts
```

这个 Playlist 告诉播放器：当前最早可用的切片序列号是 2680，有三个切片可供下载，每个约 5 秒。播放器应该在约 5 秒后重新请求 M3U8，获取更新后的列表。

一个点播 M3U8 文件：

```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-PLAYLIST-TYPE:VOD

#EXTINF:5.005,
segment0.ts
#EXTINF:5.005,
segment1.ts
#EXTINF:5.005,
segment2.ts
#EXTINF:3.338,
segment3.ts
#EXT-X-ENDLIST
```

`#EXT-X-ENDLIST` 的存在表明这是完整的点播内容，共 4 个切片，总时长约 18.35 秒。

---

## 3. Master Playlist 与多码率自适应

### Master Playlist 结构

真实的 HLS 部署中，服务端通常会提供多种码率的流，让播放器根据网络状况动态切换。这通过 **Master Playlist** 实现——它不直接包含媒体切片，而是索引多个不同码率的 Media Playlist。

关键标签是 `#EXT-X-STREAM-INF`，它描述了一个变体流的属性：

```
#EXTM3U

#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,CODECS="avc1.4d401e,mp4a.40.2"
360p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
720p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"
1080p/playlist.m3u8
```

各属性说明：
- **BANDWIDTH**：该流的峰值码率（bps），播放器据此判断当前带宽是否能支撑该流
- **RESOLUTION**：视频分辨率
- **CODECS**：编解码器标识，遵循 RFC 6381 格式

### 自适应码率切换

播放器拿到 Master Playlist 后，会估算当前可用带宽，选择一个 BANDWIDTH 不超过可用带宽的最高码率流。切换逻辑通常是：

1. 播放器持续测量每个 TS 切片的下载速度
2. 如果连续几个切片的下载速度远高于当前码率，升级到更高码率
3. 如果某个切片下载超时或速度骤降，立即降级到更低码率
4. 切换时在下一个切片边界生效，做到无缝过渡（因为每个 TS 切片都以关键帧开头）

![HLS多码率](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/hls_abr.png)

这种 **ABR（Adaptive Bitrate）** 机制是 HLS 在不稳定网络环境下保证流畅播放的关键。用户可能感知到画质的波动，但不会遭遇卡顿——这在用户体验上是更优的权衡。

---

## 4. TS 容器格式简介

### MPEG-TS 基本结构

HLS 的媒体切片采用 MPEG-2 Transport Stream（TS）格式。TS 最早为数字电视广播设计，其核心特点是 **188 字节的固定长度包**。

每个 TS 包结构如下：

- **同步字节**（1 byte）：固定为 `0x47`
- **头部标志**（3 bytes）：包含传输错误标志、负载起始标志、PID（Packet ID）等
- **自适应域**（可选）：携带 PCR 时钟、填充等信息
- **负载**（最多 184 bytes）：实际的音视频数据

### PES 包与 TS 包的关系

编码器输出的一帧音频或视频数据，首先封装为 **PES（Packetized Elementary Stream）** 包。PES 包没有固定长度限制，一帧视频数据（尤其是关键帧）可能有几十 KB。因此一个 PES 包需要拆分到多个 188 字节的 TS 包中传输。接收端收到 TS 包后，根据 PID 和起始标志将它们重新组装为完整的 PES 包，再从中提取出 ES（Elementary Stream）数据送入解码器。

### PAT 和 PMT

TS 流中有两张关键的"导航表"：

**PAT（Program Association Table）**：PID 固定为 0x0000。它列出了所有节目及其对应的 PMT PID。HLS 中通常只有一个节目。

**PMT（Program Map Table）**：描述一个节目包含哪些流（视频流、音频流），以及每个流的 PID 和编解码类型。播放器通过 PAT 找到 PMT，再通过 PMT 知道应该从哪些 PID 提取音视频数据。

### 为什么 HLS 选择 TS

HLS 选择 TS 而非 MP4 作为切片格式，关键原因是 **随机访问能力**。TS 的每个包都携带 PID 和时间戳信息，解复用器可以从流中的任意位置开始解析——即使前面的数据丢失或不可用。而 MP4 的 `moov` 原子包含了全局索引信息，必须先读取它才能定位媒体数据，不适合流式切片场景。

不过值得一提的是，苹果从 HLS version 7 开始也支持了 **fMP4（Fragmented MP4）** 格式作为切片容器，这使得 HLS 和 DASH 可以共享相同的媒体文件（即 CMAF 方案），降低了编码和存储成本。

---

## 5. Low-Latency HLS（LL-HLS）

### 传统 HLS 延迟分析

传统 HLS 的端到端延迟很高，原因是多重缓冲的叠加：

- **编码延迟**：编码器凑够一个 GOP 才输出（~2s）
- **切片延迟**：必须等一整个切片生产完毕才能发布（~6s）
- **分发延迟**：CDN 缓存刷新（~1-2s）
- **播放器缓冲**：播放器通常缓冲 2-3 个切片才开始播放（~12-18s）

叠加起来，总延迟可达 **15-30 秒**。对于体育赛事直播、互动直播等场景来说，这个延迟完全不可接受。

### LL-HLS 的核心改进

苹果在 2019 年的 WWDC 上发布了 LL-HLS（Low-Latency HLS），通过三项关键技术大幅降低延迟：

**Partial Segments（部分切片）**

传统 HLS 必须等一个完整切片（比如 6 秒）生产完毕才能发布。LL-HLS 引入了 `#EXT-X-PART` 标签，允许将一个切片拆分为多个 **Part**（通常 200ms-500ms），每个 Part 生产完毕就可以立即发布。播放器收到 Part 就可以立即解码播放，不用等完整切片。

**Preload Hints（预加载提示）**

`#EXT-X-PRELOAD-HINT` 标签告诉播放器下一个 Part 的 URI，播放器可以提前建立 HTTP 连接，在 Part 生产完毕的瞬间就开始下载，减少请求延迟。

**Blocking Playlist Reload（阻塞式更新）**

传统 HLS 播放器通过定时轮询获取新 M3U8，存在"轮询周期"的延迟浪费。LL-HLS 中播放器可以在请求 M3U8 时附带 `_HLS_msn`（Media Sequence Number）和 `_HLS_part` 参数，服务端在对应切片就绪前会 **hold 住这个请求不返回**（类似 HTTP Long Polling）。一旦新内容就绪，立即响应。这彻底消除了轮询间隔造成的延迟。

![LL-HLS vs 传统HLS](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/ll_hls.png)

### 延迟效果

通过以上改进，LL-HLS 能将端到端延迟降至 **2-3 秒**，接近 RTMP 的水平，同时保留了 HLS 的 CDN 友好性和设备兼容性。代价是服务端需要处理更多的 HTTP 请求（每个 Part 一个请求），对 CDN 和源站的请求量有较高要求。

---

## 6. C++ 实战：简易 HLS 切片器

下面我们用 C++ 和 FFmpeg 的 libavformat API 实现一个简易的 HLS 切片器：读取输入文件或流，按固定时长切分为 TS 文件，同时生成 M3U8 播放列表。

### 完整实现

```cpp
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <iomanip>

extern "C" {
#include <libavformat/avformat.h>
#include <libavutil/timestamp.h>
}

struct SegmentInfo {
    std::string filename;
    double duration;
};

class HlsSegmenter {
public:
    HlsSegmenter(const std::string& input_url,
                  const std::string& output_dir,
                  double segment_duration)
        : input_url_(input_url),
          output_dir_(output_dir),
          segment_duration_(segment_duration) {}

    ~HlsSegmenter() { Cleanup(); }

    int Run() {
        if (OpenInput() < 0) return -1;
        if (ProcessSegments() < 0) return -1;
        WritePlaylist();
        std::cout << "HLS segmentation completed. Generated "
                  << segments_.size() << " segments." << std::endl;
        return 0;
    }

private:
    int OpenInput() {
        int ret = avformat_open_input(&ifmt_ctx_, input_url_.c_str(),
                                      nullptr, nullptr);
        if (ret < 0) {
            std::cerr << "Failed to open input: " << input_url_ << std::endl;
            return ret;
        }

        ret = avformat_find_stream_info(ifmt_ctx_, nullptr);
        if (ret < 0) {
            std::cerr << "Failed to find stream info" << std::endl;
            return ret;
        }

        av_dump_format(ifmt_ctx_, 0, input_url_.c_str(), 0);
        return 0;
    }

    int OpenOutputSegment(int segment_index) {
        CloseOutputSegment();

        std::ostringstream oss;
        oss << output_dir_ << "/segment" << segment_index << ".ts";
        current_segment_name_ = oss.str();

        int ret = avformat_alloc_output_context2(&ofmt_ctx_, nullptr,
                                                  "mpegts", current_segment_name_.c_str());
        if (ret < 0) {
            std::cerr << "Failed to create output context" << std::endl;
            return ret;
        }

        for (unsigned i = 0; i < ifmt_ctx_->nb_streams; i++) {
            AVStream* out_stream = avformat_new_stream(ofmt_ctx_, nullptr);
            if (!out_stream) return AVERROR(ENOMEM);

            ret = avcodec_parameters_copy(out_stream->codecpar,
                                          ifmt_ctx_->streams[i]->codecpar);
            if (ret < 0) return ret;
            out_stream->codecpar->codec_tag = 0;
        }

        if (!(ofmt_ctx_->oformat->flags & AVFMT_NOFILE)) {
            ret = avio_open(&ofmt_ctx_->pb, current_segment_name_.c_str(),
                            AVIO_FLAG_WRITE);
            if (ret < 0) {
                std::cerr << "Failed to open output file: "
                          << current_segment_name_ << std::endl;
                return ret;
            }
        }

        ret = avformat_write_header(ofmt_ctx_, nullptr);
        if (ret < 0) {
            std::cerr << "Failed to write header" << std::endl;
            return ret;
        }

        return 0;
    }

    void CloseOutputSegment() {
        if (!ofmt_ctx_) return;

        av_write_trailer(ofmt_ctx_);

        if (!(ofmt_ctx_->oformat->flags & AVFMT_NOFILE))
            avio_closep(&ofmt_ctx_->pb);

        avformat_free_context(ofmt_ctx_);
        ofmt_ctx_ = nullptr;
    }

    int ProcessSegments() {
        AVPacket pkt;
        int segment_index = 0;
        double segment_start_time = 0.0;
        bool need_new_segment = true;

        while (av_read_frame(ifmt_ctx_, &pkt) >= 0) {
            AVStream* in_stream = ifmt_ctx_->streams[pkt.stream_index];
            double pkt_time = pkt.pts * av_q2d(in_stream->time_base);

            bool is_video = (in_stream->codecpar->codec_type == AVMEDIA_TYPE_VIDEO);
            bool is_keyframe = (pkt.flags & AV_PKT_FLAG_KEY);

            if (need_new_segment ||
                (is_video && is_keyframe &&
                 (pkt_time - segment_start_time) >= segment_duration_)) {

                if (ofmt_ctx_) {
                    double seg_duration = pkt_time - segment_start_time;
                    std::ostringstream fname;
                    fname << "segment" << segment_index << ".ts";
                    segments_.push_back({fname.str(), seg_duration});
                    segment_index++;
                }

                if (OpenOutputSegment(segment_index) < 0) {
                    av_packet_unref(&pkt);
                    return -1;
                }
                segment_start_time = pkt_time;
                need_new_segment = false;
            }

            AVStream* out_stream = ofmt_ctx_->streams[pkt.stream_index];
            pkt.pts = av_rescale_q(pkt.pts, in_stream->time_base,
                                   out_stream->time_base);
            pkt.dts = av_rescale_q(pkt.dts, in_stream->time_base,
                                   out_stream->time_base);
            pkt.duration = av_rescale_q(pkt.duration, in_stream->time_base,
                                        out_stream->time_base);
            pkt.pos = -1;

            int ret = av_interleaved_write_frame(ofmt_ctx_, &pkt);
            if (ret < 0) {
                std::cerr << "Error writing frame" << std::endl;
                av_packet_unref(&pkt);
                return ret;
            }

            av_packet_unref(&pkt);
        }

        if (ofmt_ctx_) {
            std::ostringstream fname;
            fname << "segment" << segment_index << ".ts";

            double total_duration = 0;
            if (ifmt_ctx_->duration != AV_NOPTS_VALUE)
                total_duration = ifmt_ctx_->duration / (double)AV_TIME_BASE;
            double last_seg_duration = total_duration - segment_start_time;
            if (last_seg_duration <= 0) last_seg_duration = segment_duration_;

            segments_.push_back({fname.str(), last_seg_duration});
            CloseOutputSegment();
        }

        return 0;
    }

    void WritePlaylist() {
        std::string playlist_path = output_dir_ + "/playlist.m3u8";
        std::ofstream ofs(playlist_path);

        double max_duration = 0;
        for (const auto& seg : segments_) {
            if (seg.duration > max_duration) max_duration = seg.duration;
        }

        ofs << "#EXTM3U\n";
        ofs << "#EXT-X-VERSION:3\n";
        ofs << "#EXT-X-TARGETDURATION:" << static_cast<int>(max_duration + 1) << "\n";
        ofs << "#EXT-X-MEDIA-SEQUENCE:0\n";
        ofs << "#EXT-X-PLAYLIST-TYPE:VOD\n";
        ofs << "\n";

        for (const auto& seg : segments_) {
            ofs << std::fixed << std::setprecision(3);
            ofs << "#EXTINF:" << seg.duration << ",\n";
            ofs << seg.filename << "\n";
        }

        ofs << "#EXT-X-ENDLIST\n";
        ofs.close();

        std::cout << "Playlist written to " << playlist_path << std::endl;
    }

    void Cleanup() {
        CloseOutputSegment();
        if (ifmt_ctx_) {
            avformat_close_input(&ifmt_ctx_);
            ifmt_ctx_ = nullptr;
        }
    }

    std::string input_url_;
    std::string output_dir_;
    double segment_duration_;
    std::string current_segment_name_;

    AVFormatContext* ifmt_ctx_ = nullptr;
    AVFormatContext* ofmt_ctx_ = nullptr;
    std::vector<SegmentInfo> segments_;
};

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0]
                  << " <input> <output_dir> [segment_duration]\n"
                  << "Example: " << argv[0]
                  << " input.mp4 ./hls_output 6" << std::endl;
        return 1;
    }

    std::string input = argv[1];
    std::string output_dir = argv[2];
    double segment_duration = (argc > 3) ? std::stod(argv[3]) : 6.0;

    HlsSegmenter segmenter(input, output_dir, segment_duration);
    return segmenter.Run();
}
```

### 关键实现要点

上面的代码有几个值得注意的设计：

**在关键帧处切片**：不能在任意位置切割视频，必须在关键帧（IDR 帧）处开始新切片。否则播放器拿到切片后无法独立解码。代码中通过 `is_keyframe` 判断当前包是否为关键帧，只在关键帧且超过目标时长时才切换到新切片。

**时间基转换**：输入流和输出流的时间基（time_base）可能不同，必须用 `av_rescale_q` 进行转换，否则音视频时间戳会错乱。

**先关再开**：写完一个切片（`av_write_trailer`）后再打开下一个（`avformat_write_header`），确保每个 TS 文件都有完整的头尾结构。

### CMake 构建配置

```cmake
cmake_minimum_required(VERSION 3.16)
project(hls_segmenter)

set(CMAKE_CXX_STANDARD 17)

find_package(PkgConfig REQUIRED)
pkg_check_modules(FFMPEG REQUIRED
    libavformat
    libavcodec
    libavutil
)

add_executable(hls_segmenter main.cpp)
target_include_directories(hls_segmenter PRIVATE ${FFMPEG_INCLUDE_DIRS})
target_link_libraries(hls_segmenter ${FFMPEG_LIBRARIES})
```

构建并运行：

```bash
mkdir build && cd build
cmake ..
make

mkdir -p ../hls_output
./hls_segmenter ../input.mp4 ../hls_output 6
```

运行后 `hls_output/` 目录下会生成 `playlist.m3u8` 和一系列 `segment0.ts`、`segment1.ts` 等文件。用任意支持 HLS 的播放器（如 VLC、Safari、hls.js）打开 `playlist.m3u8` 即可播放。

---

## 总结

本文从协议架构到实战实现，全面梳理了 HLS 的核心知识：

- **架构层面**：HLS 基于 HTTP 协议，通过 M3U8 + TS 的组合实现流媒体分发，天然兼容 CDN 基础设施
- **M3U8 格式**：掌握 TARGETDURATION、EXTINF、MEDIA-SEQUENCE、ENDLIST 等核心标签，理解直播与点播 Playlist 的区别
- **多码率自适应**：Master Playlist 通过 STREAM-INF 索引多路不同码率的流，播放器根据带宽动态切换，保证流畅体验
- **TS 容器**：188 字节固定包长，PAT/PMT 导航表，天然支持随机访问；fMP4 作为新选项正在被广泛采纳
- **LL-HLS**：通过 Partial Segments、Preload Hints 和 Blocking Playlist Reload 三项改进将延迟从 15-30 秒压缩到 2-3 秒
- **实战切片器**：基于 FFmpeg libavformat API，在关键帧处切片、正确转换时间基是两个核心要点

HLS 作为当今覆盖面最广的流媒体协议，理解它的原理和实现是音视频开发者的必修课。但 HLS 并非唯一选择——下一篇文章我们将探讨 **DASH（Dynamic Adaptive Streaming over HTTP）** 协议，看看 MPEG 阵营的开放标准如何与 HLS 竞争，以及 CMAF 如何让两者走向融合。
