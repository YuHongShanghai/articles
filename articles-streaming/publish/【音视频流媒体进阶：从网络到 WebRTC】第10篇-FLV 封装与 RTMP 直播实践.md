# FLV 封装与 RTMP 直播实践

## 前言

如果说 RTMP 是直播数据的"高速公路"，那 FLV 就是公路上行驶的"标准集装箱"。这两个技术从 Adobe Flash 时代就绑定在一起——RTMP 负责在网络上传输音视频数据，而 FLV 定义了这些数据的封装格式。你在 RTMP 连接上收到的每一帧视频、每一段音频，拆开来看都是一个 FLV Tag。

Flash 已死，但这对搭档依然活跃。HTTP-FLV 方案将 FLV 数据流嫁接到 HTTP 协议上，绕开了 RTMP 对 Flash Player 的依赖，同时保留了低延迟的优势。如今国内的大部分直播平台——从斗鱼、B 站到各种电商直播——底层仍在大量使用 RTMP 推流 + HTTP-FLV 拉流的组合。

本文的目标是：彻底理解 FLV 的二进制封装格式，搞清楚 RTMP 与 FLV 之间的映射关系，并通过实战走完一条完整的 RTMP 直播链路——从推流到拉流，从服务端到浏览器。

---

## 1. FLV 文件格式详解

FLV（Flash Video）是一种非常紧凑的容器格式，结构简单到可以用"线性"来形容：一个固定的文件头，后面跟着一连串的 Tag，每两个 Tag 之间有一个 4 字节的 Previous Tag Size 字段。这种扁平结构使得 FLV 天然适合流式传输——不需要像 MP4 那样先读取 moov box 才能开始解码。

### FLV Header

FLV 文件的前 9 个字节是文件头：

| 字段 | 大小 | 说明 |
|------|------|------|
| Signature | 3 字节 | 固定为 `FLV`（0x46 0x4C 0x56） |
| Version | 1 字节 | 版本号，通常为 `0x01` |
| Flags | 1 字节 | bit0 = 有视频，bit2 = 有音频 |
| DataOffset | 4 字节 | Header 长度，大端序，通常为 `9` |

Flags 字段的低 5 位中，bit0 表示是否包含视频流，bit2 表示是否包含音频流。一个同时包含音视频的 FLV 文件，Flags 值为 `0x05`（二进制 00000101）。

### FLV Body

Header 之后紧跟 FLV Body，其结构是严格的交替排列：

```
[PreviousTagSize0] [Tag1] [PreviousTagSize1] [Tag2] [PreviousTagSize2] ...
```

第一个 PreviousTagSize0 总是 `0x00000000`（因为前面没有 Tag）。之后每个 PreviousTagSize 记录的是前一个 Tag 的完整长度（Tag Header + Tag Data）。这个冗余信息的作用是支持**反向 seek**——从文件末尾往前跳转时，可以快速定位到前一个 Tag 的起始位置。

### FLV Tag

每个 FLV Tag 由 11 字节的 Tag Header 和变长的 Tag Data 组成：

| 字段 | 大小 | 说明 |
|------|------|------|
| TagType | 1 字节 | `8` = Audio, `9` = Video, `18` = Script |
| DataSize | 3 字节 | Tag Data 的长度（不含 Header） |
| Timestamp | 3 字节 | 时间戳低 24 位，单位毫秒 |
| TimestampExtended | 1 字节 | 时间戳高 8 位，与前 3 字节组成 32 位时间戳 |
| StreamID | 3 字节 | 固定为 `0`（FLV 只支持单流） |
| Data | DataSize 字节 | 音频/视频/脚本数据 |

注意时间戳的存储方式比较别扭：低 24 位在前，高 8 位在后。组合方式是 `(TimestampExtended << 24) | Timestamp`。这是 FLV 格式的历史遗留设计。

![FLV文件结构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/flv_structure.png)

---

## 2. FLV 音视频 Tag 详解

FLV Tag 的 Header 结构是统一的，但 Tag Data 内部的格式因类型而异。这一节深入每种 Tag 的数据结构。

### Video Tag Data

Video Tag Data 的第一个字节编码了帧类型和编码器 ID：

| 位域 | 说明 |
|------|------|
| 高 4 位（FrameType） | `1` = 关键帧, `2` = 非关键帧, `5` = video info/command frame |
| 低 4 位（CodecID） | `7` = AVC (H.264), `12` = HEVC (H.265, Enhanced RTMP) |

当 CodecID 为 7（AVC/H.264）时，后续数据遵循 **AVCVIDEOPACKET** 格式：

| 字段 | 大小 | 说明 |
|------|------|------|
| AVCPacketType | 1 字节 | `0` = AVC Sequence Header, `1` = AVC NALU, `2` = AVC End of Sequence |
| CompositionTime | 3 字节 | CTS 偏移（有符号），DTS + CTS = PTS |

**AVC Sequence Header** 是视频流的"配置帧"，包含 AVCDecoderConfigurationRecord，其中封装了 SPS 和 PPS 两个关键的 NAL 单元。解码器必须先收到这个配置帧才能正确解码后续的视频帧。它只在流的开头发送一次（或在参数变更时重发）。

**AVC NALU** 则是实际的视频帧数据。注意 FLV 中的 NALU 使用 **AVCC 格式**（长度前缀），而不是 Annex B 格式（0x00000001 起始码）。每个 NALU 前有 4 字节的长度字段，一个 Tag Data 中可以包含多个 NALU。

### Audio Tag Data

Audio Tag Data 的第一个字节编码了音频参数：

| 位域 | 说明 |
|------|------|
| 高 4 位（SoundFormat） | `10` = AAC, `2` = MP3, `11` = Speex |
| bit 3-2（SoundRate） | `0`=5.5kHz, `1`=11kHz, `2`=22kHz, `3`=44kHz |
| bit 1（SoundSize） | `0` = 8-bit, `1` = 16-bit |
| bit 0（SoundType） | `0` = Mono, `1` = Stereo |

当 SoundFormat 为 10（AAC）时，后续第一个字节是 AACPacketType：

- `0` = **AAC Sequence Header**：包含 AudioSpecificConfig（2 字节），描述了 AAC 的 Profile、采样率索引、声道配置等关键参数。和视频的 Sequence Header 一样，这是解码器的"说明书"。
- `1` = **AAC Raw**：原始的 AAC 帧数据（去掉了 ADTS 头），解码器直接消费。

### Script Tag（onMetaData）

Script Tag 的 TagType 为 18，Data 部分使用 AMF（Action Message Format）编码。最常见的 Script Tag 是 `onMetaData`，包含视频的全局元信息：

```
duration:       120.5      // 时长（秒）
width:          1920       // 视频宽度
height:         1080       // 视频高度
videodatarate:  2500       // 视频码率（kbps）
audiodatarate:  128        // 音频码率（kbps）
framerate:      30         // 帧率
videocodecid:   7          // 视频编码（7 = AVC）
audiocodecid:   10         // 音频编码（10 = AAC）
audiosamplerate: 44100     // 音频采样率
```

对于直播流，onMetaData 中的 `duration` 通常为 0 或不存在。播放器通过这些元信息来初始化解码器和渲染参数。

---

## 3. RTMP 与 FLV 的关系

上一篇文章详细拆解了 RTMP 的握手、Chunk 分块和 Message 结构。现在回头来看，你会发现 **RTMP Message 的 payload 几乎就是 FLV Tag Data 的原样搬运**。

### 消息类型的对应关系

| RTMP Message Type | FLV Tag Type | 内容 |
|-------------------|--------------|------|
| 8 (Audio) | 8 (Audio Tag) | 音频数据，格式完全一致 |
| 9 (Video) | 9 (Video Tag) | 视频数据，格式完全一致 |
| 18 (Data AMF0) | 18 (Script Tag) | Metadata，AMF0 编码 |

RTMP 的 Message Header 中有 Timestamp 和 Message Length 字段，对应 FLV Tag Header 中的 Timestamp 和 DataSize。也就是说，将 RTMP Message 转换为 FLV Tag，只需要：

1. 根据 Message Type ID 填写 Tag Header 的 TagType
2. 用 Message 的 Timestamp 填写 Tag Header 的时间戳字段
3. 用 Message 的 payload 长度填写 DataSize
4. 将 Message payload 直接作为 Tag Data

反过来也一样——读取一个 FLV 文件，逐个 Tag 地通过 RTMP 发出去，就完成了推流。这种一一对应的关系让 FLV 和 RTMP 之间的互转几乎零成本。

### RTMP 首帧三件套

RTMP 推流建立连接后，发送端首先要发出三个关键消息：

1. **onMetaData**（Script Message）：视频的元信息
2. **Video Sequence Header**（Video Message, AVCPacketType=0）：SPS/PPS 配置
3. **Audio Sequence Header**（Audio Message, AACPacketType=0）：AudioSpecificConfig

这三个消息合称"首帧三件套"。它们的作用各不相同，但都是正确播放的前提：

- **Video Sequence Header（SPS/PPS）**：H.264 解码器必须先解析 SPS/PPS 才能知道分辨率、Profile、参考帧数量等参数。没有它，解码器根本无法初始化——不是花屏，而是完全黑屏
- **Audio Sequence Header（AudioSpecificConfig）**：同理，AAC 解码器需要据此了解采样率、声道数等配置
- **onMetaData**：播放器据此获取码率、帧率、分辨率等信息，用于 UI 展示和缓冲策略调整

在直播场景中，当新观众接入时，服务器需要按以下顺序推送数据：

```
新观众接入
    │
    ▼
① 推送缓存的首帧三件套    ← 解码器初始化（SPS/PPS + AudioSpecificConfig）
    │
    ▼
② 推送最新 GOP 的关键帧   ← 解码器获得参考基准（IDR 帧）
    │
    ▼
③ 推送后续的 P/B 帧       ← 基于关键帧解码差分数据，正常画面出现
```

如果跳过步骤 ①，解码器无法初始化，完全黑屏。如果跳过步骤 ②，直接从当前实时流的某个 P 帧开始发送，解码器虽然初始化了但缺少关键帧作为参考——P 帧是基于关键帧的差分编码，没有参考基准同样无法正确解码，只能黑屏等到下一个 IDR 帧自然到来（可能要等 1~2 秒的 GOP 间隔）。

### 为什么理解 FLV 是理解 RTMP 的关键

很多开发者在学习 RTMP 时，把大量时间花在握手和 Chunk 分块上，却忽略了 Message payload 的结构。但实际开发中，调试最多的恰恰是 payload 层面的问题——SPS/PPS 解析错误导致花屏、CTS 计算错误导致音画不同步、Sequence Header 缺失导致黑屏。理解 FLV 的 Tag Data 格式，就等于理解了 RTMP 数据层的全部细节。

---

## 4. HTTP-FLV 直播方案

### 原理

HTTP-FLV 的思路异常简洁：在 HTTP 响应中直接输出 FLV 字节流。

1. 客户端发起一个普通的 HTTP GET 请求：`GET /live/stream.flv`
2. 服务端返回响应，Content-Type 设为 `video/x-flv`，Transfer-Encoding 设为 `chunked`
3. 服务端先写入 FLV Header（9 字节）+ 第一个 PreviousTagSize（4 字节）
4. 之后源源不断地将 FLV Tag 写入 HTTP 响应体——每来一帧就写一个 Tag + PreviousTagSize
5. 连接不关闭，数据持续流动，直到客户端断开或直播结束

这本质上是一个 HTTP 长连接（Long Connection）上的流式传输。整个响应就是一个完整的 FLV 文件，只不过这个"文件"永远写不完。

![HTTP-FLV架构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/http_flv_arch.png)

### HTTP-FLV vs RTMP 拉流

| 维度 | RTMP 拉流 | HTTP-FLV |
|------|-----------|----------|
| 传输层 | TCP，私有协议 | TCP，标准 HTTP |
| 端口 | 1935（常被防火墙拦截） | 80/443（畅通无阻） |
| CDN 支持 | 需要专用 RTMP CDN 节点 | 复用 HTTP CDN，成本低 |
| 浏览器支持 | 依赖 Flash（已淘汰） | flv.js + MSE，原生支持 |
| HTTPS | 不原生支持 | 天然支持（HTTPS-FLV） |
| 延迟 | 1-3 秒 | 1-3 秒（基本一致） |

HTTP-FLV 几乎在所有维度上都优于 RTMP 拉流，唯一的"代价"是需要播放端支持 FLV 解封装。在浏览器中，B 站开源的 [flv.js](https://github.com/bilibili/flv.js) 通过 MSE（Media Source Extensions）API 完美解决了这个问题。

### 延迟分析

HTTP-FLV 的端到端延迟由以下环节组成：

- **编码延迟**：编码器缓冲 1-2 帧，约 30-60ms
- **推流传输延迟**：RTMP 推流到服务器，取决于网络 RTT，通常 10-50ms
- **服务器转发延迟**：几乎为零（直接转写 FLV Tag）
- **拉流传输延迟**：HTTP 传输，10-50ms
- **播放器缓冲**：通常缓冲 0.5-1 秒以应对抖动

总延迟通常在 **1-3 秒**范围内，满足大部分直播场景的需求。如果追求更低延迟，可以将播放器缓冲压缩到 200-500ms，但需要接受弱网下的卡顿风险。

---

## 5. 实战：完整的 RTMP 直播链路

理论讲完，我们来走通一条完整的 RTMP 直播链路：推流 → 服务器 → 拉流/播放。

### 搭建流媒体服务器

推荐使用 [SRS](https://github.com/ossrs/srs)（Simple Realtime Server），它是国内最流行的开源流媒体服务器，部署简单，功能全面。

使用 Docker 一键启动：

```bash
docker run -d --name srs \
  -p 1935:1935 \
  -p 8080:8080 \
  ossrs/srs:5
```

启动后：
- `1935` 端口用于 RTMP 推流和拉流
- `8080` 端口提供 HTTP-FLV 拉流和管理控制台

访问 `http://localhost:8080` 可以查看 SRS 管理后台。

### 使用 FFmpeg 推流

准备一个测试视频文件（如 `test.mp4`），使用 FFmpeg 推送 RTMP 流：

```bash
ffmpeg -re -i test.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -c:a aac -ar 44100 -ac 2 \
  -f flv rtmp://localhost:1935/live/stream
```

参数解释：
- `-re`：按原始帧率读取输入，模拟实时推流（不加则全速推送）
- `-c:v libx264`：视频编码为 H.264
- `-preset veryfast -tune zerolatency`：低延迟编码配置
- `-c:a aac`：音频编码为 AAC
- `-f flv`：输出格式为 FLV（RTMP 要求 FLV 封装）

如果要推送摄像头和麦克风的实时画面：

```bash
ffmpeg -f v4l2 -i /dev/video0 \
  -f alsa -i default \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -c:a aac -ar 44100 \
  -f flv rtmp://localhost:1935/live/camera
```

### 拉流播放

**FFmpeg/ffplay 拉流：**

```bash
ffplay rtmp://localhost:1935/live/stream
```

**VLC 播放：** 打开 VLC → 媒体 → 打开网络串流 → 输入 `rtmp://localhost:1935/live/stream`

**HTTP-FLV 拉流：**

```bash
ffplay http://localhost:8080/live/stream.flv
```

### 浏览器播放 HTTP-FLV

在浏览器中使用 flv.js 播放 HTTP-FLV 流，只需要一个简单的 HTML 页面：

```html
<!DOCTYPE html>
<html>
<head>
    <title>HTTP-FLV Player</title>
    <script src="https://cdn.jsdelivr.net/npm/flv.js@latest/dist/flv.min.js"></script>
</head>
<body>
    <video id="player" controls autoplay muted
           style="width:800px; height:450px;"></video>
    <script>
        if (flvjs.isSupported()) {
            const player = flvjs.createPlayer({
                type: 'flv',
                url: 'http://localhost:8080/live/stream.flv',
                isLive: true
            });
            player.attachMediaElement(document.getElementById('player'));
            player.load();
            player.play();
        }
    </script>
</body>
</html>
```

flv.js 的工作原理是：通过 `fetch` 或 `XMLHttpRequest` 拉取 HTTP-FLV 流，在 JavaScript 中解析 FLV Tag，提取出 H.264 和 AAC 裸流，再通过 MSE API 喂给浏览器内置的解码器。整个过程不需要 Flash，不需要插件。

### C++ 实战：FLV 文件解析器

最后，我们用 C++ 写一个 FLV 文件解析器，读取 FLV 文件并打印每个 Tag 的详细信息。这个练习能加深你对 FLV 二进制格式的理解。

```cpp
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

struct FlvHeader {
    char     signature[3];
    uint8_t  version;
    uint8_t  flags;
    uint32_t data_offset;
};

struct FlvTagHeader {
    uint8_t  tag_type;
    uint32_t data_size;
    uint32_t timestamp;
    uint32_t stream_id;
};

static uint32_t ReadBE24(FILE* fp) {
    uint8_t buf[3];
    fread(buf, 1, 3, fp);
    return (buf[0] << 16) | (buf[1] << 8) | buf[2];
}

static uint32_t ReadBE32(FILE* fp) {
    uint8_t buf[4];
    fread(buf, 1, 4, fp);
    return (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
}

static std::string TagTypeName(uint8_t type) {
    switch (type) {
        case 8:  return "Audio";
        case 9:  return "Video";
        case 18: return "Script";
        default: return "Unknown(" + std::to_string(type) + ")";
    }
}

static std::string VideoFrameType(uint8_t byte) {
    switch ((byte >> 4) & 0x0F) {
        case 1: return "Keyframe";
        case 2: return "Inter";
        case 3: return "Disposable Inter";
        case 5: return "Video Info";
        default: return "Other";
    }
}

static std::string VideoCodec(uint8_t byte) {
    switch (byte & 0x0F) {
        case 2:  return "Sorenson H.263";
        case 7:  return "AVC (H.264)";
        case 12: return "HEVC (H.265)";
        case 13: return "AV1";
        default: return "Codec(" + std::to_string(byte & 0x0F) + ")";
    }
}

static std::string AudioFormat(uint8_t byte) {
    switch ((byte >> 4) & 0x0F) {
        case 2:  return "MP3";
        case 10: return "AAC";
        case 11: return "Speex";
        default: return "Format(" + std::to_string((byte >> 4) & 0x0F) + ")";
    }
}

bool ParseFlvHeader(FILE* fp, FlvHeader& header) {
    fread(header.signature, 1, 3, fp);
    if (memcmp(header.signature, "FLV", 3) != 0) {
        fprintf(stderr, "Not a valid FLV file\n");
        return false;
    }
    fread(&header.version, 1, 1, fp);
    fread(&header.flags, 1, 1, fp);
    header.data_offset = ReadBE32(fp);

    printf("=== FLV Header ===\n");
    printf("Version     : %d\n", header.version);
    printf("Has Audio   : %s\n", (header.flags & 0x04) ? "Yes" : "No");
    printf("Has Video   : %s\n", (header.flags & 0x01) ? "Yes" : "No");
    printf("Header Size : %u\n\n", header.data_offset);
    return true;
}

bool ParseFlvTag(FILE* fp, int index) {
    uint32_t prev_tag_size = ReadBE32(fp);

    uint8_t tag_type;
    if (fread(&tag_type, 1, 1, fp) != 1) return false;

    FlvTagHeader tag;
    tag.tag_type = tag_type;
    tag.data_size = ReadBE24(fp);

    uint32_t ts_low = ReadBE24(fp);
    uint8_t ts_ext;
    fread(&ts_ext, 1, 1, fp);
    tag.timestamp = (ts_ext << 24) | ts_low;

    tag.stream_id = ReadBE24(fp);

    printf("Tag #%-4d | %-6s | Size: %-7u | TS: %-10u ms",
           index, TagTypeName(tag.tag_type).c_str(),
           tag.data_size, tag.timestamp);

    if (tag.data_size > 0) {
        uint8_t first_byte;
        fread(&first_byte, 1, 1, fp);

        if (tag.tag_type == 9) {
            printf(" | %s, %s", VideoFrameType(first_byte).c_str(),
                   VideoCodec(first_byte).c_str());
            if ((first_byte & 0x0F) == 7 && tag.data_size > 1) {
                uint8_t pkt_type;
                fread(&pkt_type, 1, 1, fp);
                printf(", %s", pkt_type == 0 ? "SeqHeader" :
                               pkt_type == 1 ? "NALU" : "EndOfSeq");
                fseek(fp, tag.data_size - 2, SEEK_CUR);
            } else {
                fseek(fp, tag.data_size - 1, SEEK_CUR);
            }
        } else if (tag.tag_type == 8) {
            printf(" | %s", AudioFormat(first_byte).c_str());
            if (((first_byte >> 4) & 0x0F) == 10 && tag.data_size > 1) {
                uint8_t pkt_type;
                fread(&pkt_type, 1, 1, fp);
                printf(", %s", pkt_type == 0 ? "SeqHeader" : "Raw");
                fseek(fp, tag.data_size - 2, SEEK_CUR);
            } else {
                fseek(fp, tag.data_size - 1, SEEK_CUR);
            }
        } else {
            fseek(fp, tag.data_size - 1, SEEK_CUR);
        }
    }

    printf("\n");
    return true;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <file.flv>\n", argv[0]);
        return 1;
    }

    FILE* fp = fopen(argv[1], "rb");
    if (!fp) {
        perror("fopen");
        return 1;
    }

    FlvHeader header;
    if (!ParseFlvHeader(fp, header)) {
        fclose(fp);
        return 1;
    }

    fseek(fp, header.data_offset, SEEK_SET);

    int tag_index = 0;
    while (!feof(fp)) {
        if (!ParseFlvTag(fp, tag_index++)) break;
    }

    printf("\nTotal tags: %d\n", tag_index);
    fclose(fp);
    return 0;
}
```

编译并运行：

```bash
g++ -o flv_parser flv_parser.cpp -std=c++17
./flv_parser test.flv
```

输出示例：

```
=== FLV Header ===
Version     : 1
Has Audio   : Yes
Has Video   : Yes
Header Size : 9

Tag #0    | Script | Size: 283     | TS: 0          ms
Tag #1    | Video  | Size: 46      | TS: 0          ms | Keyframe, AVC (H.264), SeqHeader
Tag #2    | Audio  | Size: 4       | TS: 0          ms | AAC, SeqHeader
Tag #3    | Video  | Size: 28844   | TS: 0          ms | Keyframe, AVC (H.264), NALU
Tag #4    | Audio  | Size: 371     | TS: 0          ms | AAC, Raw
Tag #5    | Video  | Size: 5765    | TS: 40         ms | Inter, AVC (H.264), NALU
Tag #6    | Audio  | Size: 370     | TS: 23         ms | AAC, Raw
...
```

可以清楚地看到：前三个 Tag 就是"首帧三件套"（Script → Video SeqHeader → Audio SeqHeader），之后才是实际的音视频帧数据。把这个工具跑一遍你手头的 FLV 文件，FLV 格式就彻底印在脑子里了。

---

## 6. Enhanced RTMP 与未来

### Enhanced RTMP

传统 RTMP 最大的硬伤是编码格式支持有限——Video Tag 的 CodecID 只有 4 个 bit，Adobe 只定义了 H.263、VP6、AVC 等少数几种。随着 H.265（HEVC）、AV1、VP9 等现代编码的普及，传统 RTMP 已经无法承载这些新格式。

2023 年，Veritone 联合 YouTube、OBS 等社区推出了 **Enhanced RTMP** 规范，主要扩展包括：

- **支持 HEVC/AV1/VP9 等现代视频编码**：通过扩展 Video Tag 的 FourCC 机制，不再受限于 4-bit CodecID
- **支持多轨道音频**（如杜比全景声）
- **支持 HDR 元数据**传递

SRS 5.0、OBS 29.1+、FFmpeg 6.1+ 等主流工具已经支持 Enhanced RTMP。如果你的直播系统需要支持 H.265 推流，Enhanced RTMP 是当前最现实的方案。

### RTMP 的替代方案与未来趋势

尽管 RTMP 仍是国内直播推流的主力，但行业正在向多元化方向演进：

**推流侧：**
- **SRT**（Secure Reliable Transport）：基于 UDP，抗丢包能力强，适合远距离和弱网推流，正在成为广电和跨国推流的首选
- **WHIP**（WebRTC-HTTP Ingestion Protocol）：基于 WebRTC，延迟可以压到亚秒级，但生态还在建设中

**拉流侧：**
- **LL-HLS**（Low-Latency HLS）：苹果推出的低延迟 HLS 方案，延迟可压到 2-3 秒，兼容性好
- **WHEP**（WebRTC-HTTP Egress Protocol）：基于 WebRTC 的拉流标准，延迟低于 1 秒
- **LL-DASH**：DASH 的低延迟版本，配合 CMAF 使用

总的趋势是：**推流协议从 TCP 向 UDP 迁移（追求弱网表现），拉流协议从私有协议向 HTTP 标准化迁移（追求兼容性和 CDN 友好）**。但在可预见的未来，RTMP + HTTP-FLV 的组合仍然是成本最低、部署最简单的直播方案。

---

## 总结

本文从 FLV 的二进制格式出发，逐层拆解了 Header、Tag、Audio/Video Tag Data 的结构，然后揭示了 RTMP 与 FLV 之间近乎一一对应的关系。核心要点回顾：

- **FLV 格式**简单而紧凑，线性的 Tag 链结构天然适合流式传输
- **RTMP Message 的 payload 就是 FLV Tag Data**，两者互转几乎零成本
- **首帧三件套**（Metadata + Video SeqHeader + Audio SeqHeader）是正确播放的前提
- **HTTP-FLV** 将 FLV 流嫁接到 HTTP 上，是当前最实用的低延迟直播拉流方案
- **Enhanced RTMP** 正在解决传统 RTMP 的编码格式限制，支持 HEVC/AV1 等新编码

至此，经典流媒体协议篇落幕。我们从 RTSP/RTP 的信令+媒体分离架构，到 RTMP 的私有协议深度剖析，再到 FLV 封装与直播实践，覆盖了监控、直播两大传统场景的核心协议栈。

下一篇，我们将进入**现代流媒体协议**的世界，从 HLS 开始——看看 Apple 如何用 HTTP + 切片的思路，打造出覆盖数十亿设备的流媒体分发方案。
