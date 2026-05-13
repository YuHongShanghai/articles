# DASH 协议与自适应码率

## 前言

上一篇文章中我们深入学习了 HLS——Apple 生态中最主流的 HTTP 自适应流媒体协议。HLS 凭借 Apple 设备的原生支持和 CDN 的天然兼容性，在点播和直播领域占据了重要地位。但它终究是 Apple 主导的私有协议，在编解码格式支持、DRM 加密方案、容器格式选择等方面存在一定局限。

**DASH（Dynamic Adaptive Streaming over HTTP）** 是 MPEG 组织制定的国际标准（ISO/IEC 23009-1），它的目标是成为一个真正开放、灵活、厂商中立的 HTTP 自适应流媒体方案。YouTube、Netflix、Disney+ 等全球头部视频平台都将 DASH 作为主力分发协议。

DASH 和 HLS 在架构上有很多相似之处——都是基于 HTTP 的分片传输，都支持自适应码率切换。但 DASH 在媒体描述的表达能力、编解码格式的开放性、DRM 加密的统一性上更胜一筹。

本文将从 DASH 的协议架构出发，深入剖析 MPD 文件结构和 Segment 组织方式，对比 DASH 与 HLS 的异同，然后重点展开 ABR（Adaptive Bitrate）自适应码率算法的原理与实现，最后介绍 CMAF 这一统一 HLS 和 DASH 的媒体格式标准。

---

## 1. DASH 协议概述

### 基本架构

DASH 的核心思想与 HLS 一致：将媒体内容切分为一系列短小的片段（Segment），通过标准的 HTTP 协议分发，客户端根据网络状况动态选择合适码率的片段进行播放。

一个完整的 DASH 流媒体系统包含三个核心环节：

1. **内容准备**：将源媒体编码为多个码率版本，切分为 Segment 文件，并生成 MPD 描述文件
2. **内容分发**：将 MPD 和 Segment 文件部署到标准的 HTTP 服务器或 CDN 上
3. **客户端播放**：DASH 客户端下载 MPD，解析可用的码率和片段信息，通过 ABR 算法选择合适码率的 Segment 逐个下载、解码、渲染

![DASH架构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/dash_architecture.png)

与 HLS 不同的是，DASH 标准只定义了服务端的媒体格式和 MPD 描述规范，**并不规定客户端的播放行为**。ABR 算法、缓冲策略、错误恢复等实现细节完全由客户端决定。这意味着不同的播放器（如 dash.js、ExoPlayer、Shaka Player）可以采用截然不同的码率选择策略。

### 核心组件

DASH 协议的核心就是两个东西：

- **MPD（Media Presentation Description）**：一个 XML 格式的描述文件，类似于 HLS 中的 M3U8 播放列表，但表达能力更强。它描述了媒体内容的完整结构——有哪些码率、分辨率、编解码器可选，每个片段的 URL 是什么，时间范围如何组织。
- **Segment**：实际的媒体数据片段。通常采用 fMP4（Fragmented MP4）或 WebM 格式封装，每个 Segment 包含若干秒的音频或视频数据。

这个模型可以类比为"菜单 + 菜品"：MPD 是菜单，告诉客户端有什么可选；Segment 是实际的菜品，客户端根据自己的"胃口"（带宽）从菜单上点菜。

---

## 2. MPD 文件结构详解

### 层次结构

MPD 采用 XML 格式，拥有一套严谨的层次结构。理解这个层次结构是掌握 DASH 的关键：

![MPD层次结构](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/mpd_hierarchy.png)

**MPD（根节点）** → **Period** → **AdaptationSet** → **Representation** → **Segment**

从外到内依次展开：

- **MPD**：根元素，描述整个媒体呈现。包含全局属性如类型（静态/动态）、时长、最小缓冲时间等。
- **Period**：时间段，将媒体内容按时间切分。点播场景通常只有一个 Period；直播场景或包含广告插入的内容可能有多个 Period。每个 Period 有独立的时间偏移和持续时长。
- **AdaptationSet**：自适应集合，将同一类型的媒体轨道分组。例如一个视频 AdaptationSet 包含不同码率的视频轨，一个音频 AdaptationSet 包含不同语言的音频轨。同一个 AdaptationSet 内的 Representation 可以无缝切换。
- **Representation**：具体的一路编码版本，对应一个特定的码率、分辨率、编解码器组合。客户端的 ABR 算法本质上就是在同一个 AdaptationSet 的多个 Representation 之间做选择。
- **Segment**：最小的可请求单元，每个 Representation 的内容被切分为时间上连续的 Segment 序列。

### 完整 MPD 示例

下面是一个典型的点播 MPD 文件，包含视频和音频两个 AdaptationSet，视频有三个码率档位：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"
     type="static"
     mediaPresentationDuration="PT10M30S"
     minBufferTime="PT2S"
     profiles="urn:mpeg:dash:profile:isoff-on-demand:2011">

  <!-- 单个 Period，覆盖整个视频时长 -->
  <Period id="1" duration="PT10M30S">

    <!-- 视频自适应集合：三个码率档位，可自由切换 -->
    <AdaptationSet mimeType="video/mp4" codecs="avc1.4D401F"
                   segmentAlignment="true" startWithSAP="1">

      <!-- 低码率：480p, 800kbps -->
      <Representation id="video-low" bandwidth="800000"
                      width="854" height="480" frameRate="30">
        <SegmentTemplate media="video/low/seg-$Number$.m4s"
                         initialization="video/low/init.mp4"
                         startNumber="1" duration="4000"
                         timescale="1000"/>
      </Representation>

      <!-- 中码率：720p, 2.5Mbps -->
      <Representation id="video-mid" bandwidth="2500000"
                      width="1280" height="720" frameRate="30">
        <SegmentTemplate media="video/mid/seg-$Number$.m4s"
                         initialization="video/mid/init.mp4"
                         startNumber="1" duration="4000"
                         timescale="1000"/>
      </Representation>

      <!-- 高码率：1080p, 5Mbps -->
      <Representation id="video-high" bandwidth="5000000"
                      width="1920" height="1080" frameRate="30">
        <SegmentTemplate media="video/high/seg-$Number$.m4s"
                         initialization="video/high/init.mp4"
                         startNumber="1" duration="4000"
                         timescale="1000"/>
      </Representation>
    </AdaptationSet>

    <!-- 音频自适应集合 -->
    <AdaptationSet mimeType="audio/mp4" codecs="mp4a.40.2"
                   lang="zh" segmentAlignment="true">
      <Representation id="audio" bandwidth="128000"
                      audioSamplingRate="44100">
        <SegmentTemplate media="audio/seg-$Number$.m4s"
                         initialization="audio/init.mp4"
                         startNumber="1" duration="4000"
                         timescale="1000"/>
      </Representation>
    </AdaptationSet>

  </Period>
</MPD>
```

逐一解析几个关键属性：

- `type="static"`：静态类型，表示点播内容。直播场景用 `type="dynamic"`，并附带 `availabilityStartTime` 和 `publishTime` 等时间锚点。
- `mediaPresentationDuration="PT10M30S"`：总时长 10 分 30 秒，采用 ISO 8601 时间格式。
- `minBufferTime="PT2S"`：客户端在开始播放前至少需要缓冲 2 秒的数据。
- `segmentAlignment="true"`：同一 AdaptationSet 中各 Representation 的 Segment 在时间上对齐，这是码率切换的前提条件。
- `startWithSAP="1"`：每个 Segment 以 SAP Type 1 开头（即 IDR 帧），保证可以独立解码。
- `bandwidth`：该 Representation 的峰值码率（bps），ABR 算法用这个值来判断当前带宽能否承载。
- `SegmentTemplate` 中的 `$Number$`：一个模板变量，客户端按序列号替换生成实际的 Segment URL。`duration="4000"` 配合 `timescale="1000"` 表示每个 Segment 时长 4 秒。

### 动态 MPD（直播场景）

直播场景下，MPD 的 `type` 为 `dynamic`，客户端需要定期重新拉取 MPD 来获知新生成的 Segment：

```xml
<MPD type="dynamic"
     availabilityStartTime="2026-03-17T10:00:00Z"
     publishTime="2026-03-17T10:30:00Z"
     minimumUpdatePeriod="PT4S"
     timeShiftBufferDepth="PT1H"
     minBufferTime="PT2S">
  ...
</MPD>
```

- `availabilityStartTime`：直播开始的绝对时间，客户端据此计算当前应该请求哪个 Segment。
- `minimumUpdatePeriod="PT4S"`：客户端至少每 4 秒刷新一次 MPD。
- `timeShiftBufferDepth="PT1H"`：时移缓冲深度 1 小时，允许用户回看最近 1 小时的内容。

---

## 3. Segment 格式

### 两种索引方式

MPD 中描述 Segment 的方式有两种，适用于不同场景：

**SegmentTemplate**：通过 URL 模板 + 规则生成 Segment 地址，MPD 体积小、扩展性好，是最常用的方式。支持两种变量：

- `$Number$`：基于序号，客户端递增序号构造 URL（如 `seg-1.m4s`、`seg-2.m4s`）
- `$Time$`：基于时间戳，配合 `<SegmentTimeline>` 精确控制每个 Segment 的时间范围，适合 Segment 时长不均匀的场景

```xml
<!-- 基于 SegmentTimeline 的模板 -->
<SegmentTemplate media="seg-$Time$.m4s" initialization="init.mp4"
                 timescale="1000">
  <SegmentTimeline>
    <S t="0" d="4000" r="9"/>    <!-- 10个4秒的Segment -->
    <S d="2500"/>                 <!-- 最后一个2.5秒的Segment -->
  </SegmentTimeline>
</SegmentTemplate>
```

**SegmentList**：显式列出每个 Segment 的 URL，简单直观但 MPD 体积会随 Segment 数量线性增长，通常只在 Segment 数量较少时使用。

```xml
<SegmentList duration="4000" timescale="1000">
  <Initialization sourceURL="init.mp4"/>
  <SegmentURL media="seg-1.m4s"/>
  <SegmentURL media="seg-2.m4s"/>
  <SegmentURL media="seg-3.m4s"/>
</SegmentList>
```

### Init Segment 与 Media Segment

每个 Representation 的 Segment 序列由两部分组成：

- **Init Segment（初始化片段）**：包含媒体的元信息——编解码器配置、轨道参数、采样率等。它对应 fMP4 中的 `ftyp` + `moov` Box。客户端在开始播放某个 Representation 前必须先下载其 Init Segment。
- **Media Segment（媒体片段）**：包含实际的音视频数据。它对应 fMP4 中的 `moof` + `mdat` Box。每个 Media Segment 都是可独立请求、独立解码的单元。

码率切换时，客户端需要先下载新 Representation 的 Init Segment，然后从下一个时间点开始请求新码率的 Media Segment。由于 `segmentAlignment` 的保证，不同码率的 Segment 在时间上是对齐的，切换是无缝的。

### fMP4（Fragmented MP4）格式

DASH 默认使用 fMP4 作为媒体容器。与传统 MP4 不同，fMP4 不需要完整的 `moov` Box 来索引整个文件——每个 Fragment 都自带时间戳和偏移信息，天然适合流式传输。

传统 MP4 的结构：

```
[ftyp] [moov (整个文件的索引)] [mdat (所有媒体数据)]
```

fMP4 的结构：

```
[ftyp] [moov (基础信息)]
[moof (Fragment 1 索引)] [mdat (Fragment 1 数据)]
[moof (Fragment 2 索引)] [mdat (Fragment 2 数据)]
...
```

使用 FFmpeg 生成 DASH 所需的 fMP4 片段非常简单：

```bash
ffmpeg -i input.mp4 \
  -map 0:v -b:v 2500k -s 1280x720 \
  -map 0:a -b:a 128k \
  -f dash -seg_duration 4 \
  -init_seg_name 'init-$RepresentationID$.mp4' \
  -media_seg_name 'seg-$RepresentationID$-$Number$.m4s' \
  output.mpd
```

### Segment 时长与延迟

Segment 时长是影响播放延迟的关键参数：

- **时长越长**：编码效率越高（更多帧用于预测），CDN 缓存友好，但播放延迟越大，码率切换的粒度越粗。典型值为 4~6 秒。
- **时长越短**：延迟越低，码率切换响应更快，但会增加 HTTP 请求数和 MPD 复杂度。低延迟场景可缩短至 1~2 秒。

理论最低延迟 ≈ Segment 时长 × 3（编码 1 个 + 传输 1 个 + 缓冲 1 个）。这也是 CMAF 引入 Chunk 传输的动机——在 Segment 内部进一步细分，实现亚秒级延迟。

---

## 4. DASH vs HLS 对比

学过 HLS 之后再看 DASH，会发现它们在思路上高度相似，但在技术细节上有不少差异。下面从多个维度做一个系统对比：

| 维度 | DASH | HLS |
|------|------|-----|
| **标准归属** | MPEG 国际标准（ISO/IEC 23009） | Apple 私有协议（RFC 8216 为信息性 RFC） |
| **媒体描述** | MPD（XML 格式） | M3U8（扩展的 M3U 播放列表） |
| **容器格式** | fMP4、WebM | TS（传统）、fMP4（HLS v7+） |
| **视频编码** | H.264, H.265, VP9, AV1 等均支持 | H.264, H.265（Apple 设备限制较多） |
| **音频编码** | AAC, Opus, AC-3, Vorbis 等 | AAC, AC-3（Opus 支持较晚） |
| **DRM 加密** | CENC 统一加密，支持 Widevine/PlayReady/FairPlay | FairPlay 为主，其他需要额外适配 |
| **多音轨/字幕** | 原生支持，AdaptationSet 灵活组织 | 支持，但描述能力相对有限 |
| **低延迟方案** | Low-Latency DASH（CMAF Chunk） | LL-HLS（Partial Segment） |
| **浏览器支持** | 需要 MSE（Media Source Extensions）| iOS Safari 原生支持，其他浏览器需 MSE |
| **移动端支持** | Android ExoPlayer 原生支持 | iOS 原生支持，Android 需第三方库 |
| **CDN 兼容性** | 标准 HTTP，完全兼容 | 标准 HTTP，完全兼容 |
| **典型平台** | YouTube, Netflix, Disney+ | Apple TV+, Twitch, 国内主流平台 |

几个值得展开的差异点：

**DRM 是 DASH 的重要优势**。DASH 定义了 CENC（Common Encryption Scheme）标准，允许一份加密内容同时兼容多种 DRM 系统（Widevine、PlayReady、FairPlay）。内容只需加密一次，每个 DRM 系统提供自己的 License Server 即可。HLS 则传统上与 FairPlay 绑定，跨平台 DRM 需要做更多适配工作。

**编解码灵活性**。DASH 在标准设计上对编解码器保持中立，天然支持 VP9、AV1 等开放编码格式，也支持 WebM 容器。这让 YouTube 可以大规模使用 VP9/AV1 来节省带宽。HLS 的生态则更偏向 H.264/H.265，对新编码格式的支持节奏取决于 Apple。

**浏览器端的现状**。DASH 在浏览器中需要通过 MSE（Media Source Extensions）API 来实现，dash.js 和 Shaka Player 是最成熟的开源方案。HLS 在 Safari 中有原生支持，但在 Chrome/Firefox 中同样需要 hls.js 这样的 MSE 库。目前主流浏览器对 MSE 的支持已经非常成熟，两者在浏览器端的可用性差距已大幅缩小。

---

## 5. ABR 自适应码率算法

ABR 是 DASH（以及 HLS）客户端最核心的决策逻辑。它需要回答一个看似简单但实际非常困难的问题：**下一个 Segment 应该请求哪个码率？**

选高了，带宽不够，会导致缓冲区耗尽、播放卡顿（rebuffering）；选低了，浪费了可用带宽，用户看到不必要的低画质。好的 ABR 算法需要在**最大化画质**和**最小化卡顿**之间找到平衡，同时还要考虑码率切换频率（频繁跳变会影响观看体验）。

![ABR算法对比](https://gitee.com/yuhong1234/streaming-tutorial-images/raw/master/diagrams/output/abr_algorithms.png)

### BBA（Buffer-Based Approach）

BBA 是最直观的 ABR 策略：**根据当前播放缓冲区的水位来决定码率**。

核心思路：

- 缓冲区水位低 → 网络可能不好或消耗过快 → 降低码率
- 缓冲区水位高 → 网络充裕或消耗慢 → 提升码率
- 设定两个阈值 `r_low` 和 `r_high`，缓冲区在两者之间时线性映射码率

BBA 的优势在于不需要预测带宽——带宽估计本身就是一个噪声很大的信号，尤其在移动网络场景下。缓冲区水位是一个更稳定、更直接反映实际情况的指标。

```cpp
struct Representation {
    std::string id;
    int bandwidth;  // bps
};

class BBASelector {
public:
    BBASelector(std::vector<Representation> reps,
                double buf_low_sec, double buf_high_sec)
        : reps_(std::move(reps)), buf_low_(buf_low_sec), buf_high_(buf_high_sec)
    {
        std::sort(reps_.begin(), reps_.end(),
                  [](auto& a, auto& b) { return a.bandwidth < b.bandwidth; });
    }

    int SelectRepIndex(double buffer_level_sec) const {
        if (buffer_level_sec <= buf_low_) {
            return 0;  // 水位过低，选最低码率
        }
        if (buffer_level_sec >= buf_high_) {
            return static_cast<int>(reps_.size()) - 1;  // 水位充足，选最高码率
        }

        // 线性映射：缓冲区水位 → 码率档位
        double ratio = (buffer_level_sec - buf_low_) / (buf_high_ - buf_low_);
        int index = static_cast<int>(ratio * (reps_.size() - 1));
        return std::clamp(index, 0, static_cast<int>(reps_.size()) - 1);
    }

private:
    std::vector<Representation> reps_;
    double buf_low_;   // 低水位阈值（秒）
    double buf_high_;  // 高水位阈值（秒）
};
```

### MPC（Model Predictive Control）

MPC 基于带宽预测来做决策。它的核心思想是：**根据最近若干个 Segment 的下载速度预估未来带宽，然后在未来 N 个决策步上优化一个综合指标。**

预测模型通常使用滑动窗口的调和平均值来估计带宽（调和平均对低值更敏感，更保守）：

```cpp
class BandwidthEstimator {
public:
    void AddSample(double throughput_bps) {
        samples_.push_back(throughput_bps);
        if (samples_.size() > window_size_) {
            samples_.erase(samples_.begin());
        }
    }

    double HarmonicMean() const {
        if (samples_.empty()) return 0.0;
        double sum_reciprocal = 0.0;
        for (double s : samples_) {
            if (s > 0) sum_reciprocal += 1.0 / s;
        }
        return samples_.size() / sum_reciprocal;
    }

private:
    std::vector<double> samples_;
    size_t window_size_ = 5;
};
```

MPC 的优化目标通常定义为：

```
maximize: Σ Q(Ri)                    -- 画质尽可能高
minimize: Σ |Q(Ri) - Q(Ri-1)|       -- 码率切换尽可能少
minimize: Σ max(0, rebuffer_time_i)  -- 卡顿尽可能少
```

将这三项加权组合为一个标量目标函数，然后在有限的码率档位空间中搜索最优解。由于预测窗口通常只有 3~5 步，搜索空间不大，可以直接暴力枚举。

```cpp
struct ABRDecision {
    int rep_index;
    double score;
};

ABRDecision MPCSelect(
    const std::vector<Representation>& reps,
    double current_buffer_sec,
    double segment_duration_sec,
    double estimated_bandwidth_bps,
    int current_rep_index,
    int lookahead = 3)
{
    int best_index = 0;
    double best_score = -1e18;

    double w_quality = 1.0;
    double w_switch = 0.8;
    double w_rebuffer = 5.0;  // 卡顿惩罚权重最高

    for (int i = 0; i < static_cast<int>(reps.size()); ++i) {
        double bitrate = reps[i].bandwidth;
        double download_time = (bitrate * segment_duration_sec) / estimated_bandwidth_bps;
        double rebuffer = std::max(0.0, download_time - current_buffer_sec);
        double new_buffer = std::max(0.0, current_buffer_sec - download_time)
                            + segment_duration_sec;

        double quality = std::log(static_cast<double>(bitrate));
        double switch_cost = std::abs(quality - std::log(
            static_cast<double>(reps[current_rep_index].bandwidth)));
        double score = w_quality * quality
                     - w_switch * switch_cost
                     - w_rebuffer * rebuffer;

        if (score > best_score) {
            best_score = score;
            best_index = i;
        }
    }

    return {best_index, best_score};
}
```

### Pensieve：基于深度强化学习的 ABR

MIT 在 2017 年提出的 Pensieve 开创了用深度强化学习（DRL）解决 ABR 问题的方向。

传统 ABR 算法需要人工设计规则和调参（BBA 的阈值、MPC 的权重），而 Pensieve 让神经网络直接从经验中学习最优策略：

- **状态空间**：过去 k 个 Segment 的下载吞吐量、下载时间、缓冲区水位、上一个选择的码率、下一个 Segment 各码率档位的大小
- **动作空间**：选择下一个 Segment 的码率档位
- **奖励函数**：综合画质、卡顿时长、码率切换幅度的加权组合
- **网络结构**：A3C（Asynchronous Advantage Actor-Critic）框架，Actor 网络输出码率选择的概率分布，Critic 网络估计状态价值

Pensieve 在大规模 trace 驱动的模拟实验中表现优于 BBA 和 MPC，尤其在网络状况复杂多变的场景下。但它也有局限性：

- 训练需要大量真实网络 trace 数据
- 模型的泛化能力取决于训练数据的多样性
- 在线推理的计算开销（虽然单次推理很快，但部署和维护深度学习模型增加了系统复杂度）
- 可解释性差，出了问题不容易排查

### 实际工程中的选择

在生产环境中，ABR 算法的选择通常是这样的：

- **dash.js** 默认使用 BOLA（Buffer Occupancy based Lyapunov Algorithm），一种经过理论证明的 Buffer-Based 算法
- **Shaka Player** 默认使用带宽估计 + 缓冲区水位的混合策略
- **Netflix** 采用自研的复杂 ABR 系统，结合带宽预测、缓冲区管理和 A/B 测试持续优化
- **YouTube** 使用基于 MPC 改进的自研算法，并在部分场景实验了强化学习方案

工程实践中，一个简单而稳健的混合策略往往比复杂的理论最优算法更可靠：

```cpp
class HybridABR {
public:
    int SelectRepIndex(double buffer_sec, double estimated_bw_bps,
                       double segment_duration_sec,
                       const std::vector<Representation>& reps,
                       int current_index) {
        // 安全阈值：缓冲区过低时无条件降到最低码率
        if (buffer_sec < panic_threshold_sec_) {
            return 0;
        }

        // 带宽约束：排除超出预估带宽的档位
        int max_feasible = 0;
        for (int i = 0; i < static_cast<int>(reps.size()); ++i) {
            if (reps[i].bandwidth <= estimated_bw_bps * safety_factor_) {
                max_feasible = i;
            }
        }

        // 缓冲区引导：在可行范围内根据缓冲水位调整
        int target = max_feasible;
        if (buffer_sec < low_threshold_sec_) {
            target = std::min(target, current_index);  // 不上升
        } else if (buffer_sec > high_threshold_sec_) {
            target = max_feasible;  // 允许上升
        } else {
            target = std::min(target, current_index + 1);  // 最多上升一档
        }

        return std::clamp(target, 0, static_cast<int>(reps.size()) - 1);
    }

private:
    double panic_threshold_sec_ = 2.0;
    double low_threshold_sec_ = 6.0;
    double high_threshold_sec_ = 15.0;
    double safety_factor_ = 0.8;  // 带宽留 20% 余量
};
```

这个混合策略结合了 BBA 和 MPC 的优点：用带宽估计确定可行的码率上界，用缓冲区水位做最终决策，同时加入了紧急降码率的保护机制。`safety_factor_` 留出 20% 的带宽余量，是工程中常见的保守策略——宁可画质低一点，也不要卡顿。

---

## 6. CMAF（Common Media Application Format）

### 碎片化的困境

长期以来，HLS 使用 MPEG-TS 容器，DASH 使用 fMP4 容器。这意味着内容提供商如果要同时支持两个协议，需要将同一份源文件编码切片两次，存储两套文件，CDN 缓存也需要双倍空间。这显然是一种浪费。

### CMAF 的解法

CMAF（Common Media Application Format，ISO/IEC 23000-19）由 Apple 和 Microsoft 联合提出，目标很明确：**让 HLS 和 DASH 共享同一套媒体文件。**

CMAF 选择 **fMP4** 作为统一的容器格式。事实上，HLS 从 v7 版本（2017 年）开始就支持了 fMP4 容器，而 DASH 原本就以 fMP4 为主。这意味着：

- 一份源文件编码一次，切片一次
- 生成的 fMP4 Segment 文件 HLS 和 DASH 共享
- 只需要分别生成 M3U8 和 MPD 两个清单文件
- CDN 上的媒体文件只存一份

```
源文件 → 编码 → fMP4 Segment 文件（共享）
                    ├── 生成 M3U8 播放列表 → HLS 客户端
                    └── 生成 MPD 描述文件  → DASH 客户端
```

### CMAF 低延迟 Chunk 传输

CMAF 除了统一容器格式，还引入了 **CMAF Chunk** 的概念来实现低延迟传输。

传统模式下，一个 Segment（比如 4 秒）必须完整生成后才能被客户端请求。CMAF 将一个 Segment 内部进一步切分为多个 Chunk（比如每个 200ms），服务端可以在 Chunk 生成后立即通过 HTTP Chunked Transfer Encoding 推送给客户端。

```
传统 Segment 传输：
|---- 4s Segment ----|
                      ^ 客户端在 Segment 完整生成后才能请求

CMAF Chunk 传输：
|Chunk|Chunk|Chunk|Chunk|...|
 200ms 200ms 200ms 200ms
 ^ 每个 Chunk 生成后立即可用
```

这将理论延迟从 Segment 级别（数秒）降低到了 Chunk 级别（亚秒）。配合 HTTP/1.1 的 Chunked Transfer Encoding 或 HTTP/2 的 Server Push，CMAF 可以实现与 WebRTC 接近的端到端延迟（1~3 秒），同时保持 HTTP 协议栈和 CDN 的兼容性。

LL-HLS（Low-Latency HLS）的 Partial Segment 和 CMAF Chunk 在思路上是一致的，实际上 Apple 也建议 LL-HLS 使用 CMAF 兼容的 fMP4 格式。这进一步推动了 HLS 和 DASH 在技术栈上的融合。

---

## 总结

本文系统介绍了 DASH 协议的核心知识体系，回顾关键要点：

- **DASH 是 MPEG 国际标准**，相比 HLS 更加开放和灵活，在编解码支持、DRM 加密、多轨道管理上有明显优势
- **MPD 文件**采用 XML 格式描述媒体内容的完整结构，层次为 Period → AdaptationSet → Representation → Segment，表达能力强大
- **Segment 格式**以 fMP4 为主，通过 Init Segment + Media Segment 的组织方式支持高效的流式传输和码率切换
- **ABR 算法**是 DASH 客户端的核心智能，经典方案包括基于缓冲区的 BBA、基于带宽预测的 MPC、以及基于强化学习的 Pensieve，工程实践中通常采用混合策略
- **CMAF** 通过统一 fMP4 容器格式，解决了 HLS 和 DASH 的碎片化问题，其 Chunk 传输机制更是低延迟流媒体的关键技术

DASH 和 HLS 的融合趋势已经非常明显——fMP4 成为公共容器，CMAF 成为公共格式标准，两者的差异正在逐渐缩小为"清单文件的格式不同"。对于流媒体开发者来说，理解两个协议的共同基础（HTTP 分片传输、自适应码率、fMP4 封装）比纠结于选择哪一个更重要。

下一篇文章，我们将进入 **SRT 协议与低延迟传输**，看看在 HTTP 之外，如何基于 UDP 构建一个专为不稳定网络设计的安全可靠传输协议。
