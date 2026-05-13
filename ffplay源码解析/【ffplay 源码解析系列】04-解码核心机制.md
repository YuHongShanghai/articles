# ffplay 源码解析系列（四）：解码核心机制——音视频字幕解码线程

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 上一篇我们分析了 read_thread 如何将 AVPacket 分发到各个 PacketQueue。本篇将深入解码器内部，看看 packet 是如何被解码为可播放的帧的。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 概述

ffplay 的解码管线由三个独立的解码线程构成：

- **video_thread**：从 `videoq` 取出视频 packet，解码为 `AVFrame`，经过滤镜处理后放入 `pictq`
- **audio_thread**：从 `audioq` 取出音频 packet，解码为 `AVFrame`，经过滤镜处理后放入 `sampq`
- **subtitle_thread**：从 `subtitleq` 取出字幕 packet，解码为 `AVSubtitle`，放入 `subpq`

三个线程共享同一个底层解码函数 `decoder_decode_frame()`，这是整个解码管线最核心的函数。

![三个解码线程与队列关系](https://gitee.com/yuhong1234/ffplay/raw/master/04-three-decode-threads.png)

## 2. decoder_decode_frame()——解码核心状态机

`decoder_decode_frame()` 是 ffplay 中最重要的函数之一。它封装了 FFmpeg 新的解码 API（send_packet / receive_frame 模式），并以一个**无限循环状态机**的形式运行，处理了 serial 同步、flush、EAGAIN 重试、字幕特殊路径等各种复杂情况。

![decoder_decode_frame 状态机流程](https://gitee.com/yuhong1234/ffplay/raw/master/04-decoder-decode-frame.png)

### 2.1 函数签名与初始化

```c
static int decoder_decode_frame(Decoder *d, AVFrame *frame, AVSubtitle *sub) {
    int ret = AVERROR(EAGAIN);

    for (;;) {
```

函数接收三个参数：
- `d`：Decoder 结构体，包含解码器上下文、PacketQueue 引用、serial 等状态
- `frame`：输出的音/视频帧（音视频解码时使用）
- `sub`：输出的字幕（字幕解码时使用）

返回值约定：
- `< 0`：出错或退出
- `0`：解码到 EOF
- `1`：成功解码一帧

`ret` 初始化为 `AVERROR(EAGAIN)`，这个值会驱动状态机在首次进入时跳过 receive_frame 阶段，直接进入取包阶段。

### 2.2 阶段一：尝试接收解码帧（receive_frame）

进入循环后，首先检查当前 packet 的 serial 是否与队列的 serial 一致。只有 serial 匹配时，才会尝试从解码器接收帧：

```c
        if (d->queue->serial == d->pkt_serial) {
            do {
                if (d->queue->abort_request)
                    return -1;

                switch (d->avctx->codec_type) {
                    case AVMEDIA_TYPE_VIDEO:
                        // 🔑 从解码器取出一帧视频
                        ret = avcodec_receive_frame(d->avctx, frame);
                        if (ret >= 0) {
                            // PTS 策略：优先使用 best_effort_timestamp
                            if (decoder_reorder_pts == -1) {
                                frame->pts = frame->best_effort_timestamp;
                            } else if (!decoder_reorder_pts) {
                                frame->pts = frame->pkt_dts;
                            }
                        }
                        break;
                    case AVMEDIA_TYPE_AUDIO:
                        // 🔑 从解码器取出一帧音频
                        ret = avcodec_receive_frame(d->avctx, frame);
                        if (ret >= 0) {
                            // 将 PTS 转换为以采样率为时基的值
                            AVRational tb = (AVRational){1, frame->sample_rate};
                            if (frame->pts != AV_NOPTS_VALUE)
                                frame->pts = av_rescale_q(frame->pts, d->avctx->pkt_timebase, tb);
                            else if (d->next_pts != AV_NOPTS_VALUE)
                                // 如果没有 PTS，使用上一帧推算
                                frame->pts = av_rescale_q(d->next_pts, d->next_pts_tb, tb);
                            if (frame->pts != AV_NOPTS_VALUE) {
                                // 记录下一帧的预期 PTS = 当前 PTS + 样本数
                                d->next_pts = frame->pts + frame->nb_samples;
                                d->next_pts_tb = tb;
                            }
                        }
                        break;
                }
```

**关键设计要点**：

1. **视频 PTS 策略**：`decoder_reorder_pts` 为 -1（默认值）时使用 `best_effort_timestamp`，这是 FFmpeg 基于 DTS/PTS 推算出的最佳时间戳，对 B 帧重排序场景尤为重要。
2. **音频时基转换**：音频的 PTS 被转换为 `{1, sample_rate}` 时基，即以采样点为单位。这样 `next_pts` 的推算就是简单的加法：`当前PTS + nb_samples`。
3. **音频 PTS 推算**：当某一帧没有 PTS 时（如某些容器格式），使用 `next_pts` 进行线性推算，保证音频时间线的连续性。

### 2.3 EOF 与成功返回

```c
                if (ret == AVERROR_EOF) {
                    d->finished = d->pkt_serial;
                    avcodec_flush_buffers(d->avctx);
                    return 0;
                }
                if (ret >= 0)
                    return 1;
            } while (ret != AVERROR(EAGAIN));
        }
```

- **AVERROR_EOF**：解码器已排空所有缓冲帧。将 `finished` 设为当前 serial（标记此 serial 下解码完成），然后 flush 解码器以便后续 seek 时复用。
- **ret >= 0**：成功解码一帧，返回 1。
- **AVERROR(EAGAIN)**：解码器需要更多 packet 才能输出帧，退出内层 do-while 循环，进入下面的取包阶段。

> 注意内层是 `do { ... } while (ret != AVERROR(EAGAIN))` 循环——这意味着一次 `send_packet` 之后可能连续取出多帧（如 B 帧场景），直到返回 EAGAIN。

### 2.4 阶段二：从 PacketQueue 取包

当解码器需要更多数据时，进入取包逻辑：

```c
        do {
            if (d->queue->nb_packets == 0)
                SDL_CondSignal(d->empty_queue_cond);
            if (d->packet_pending) {
                // 🔑 上次 send_packet 返回 EAGAIN，复用之前的 packet
                d->packet_pending = 0;
            } else {
                int old_serial = d->pkt_serial;
                // 🔑 从队列取出一个 packet（阻塞等待）
                if (packet_queue_get(d->queue, d->pkt, 1, &d->pkt_serial) < 0)
                    return -1;
                // 🔑 serial 变化说明发生了 seek，需要 flush 解码器
                if (old_serial != d->pkt_serial) {
                    avcodec_flush_buffers(d->avctx);
                    d->finished = 0;
                    d->next_pts = d->start_pts;
                    d->next_pts_tb = d->start_pts_tb;
                }
            }
            if (d->queue->serial == d->pkt_serial)
                break;
            av_packet_unref(d->pkt);
        } while (1);
```

**逐行解析**：

1. **空队列信号**：当队列为空时，发送 `empty_queue_cond` 信号，唤醒 read_thread 让它继续读取数据（背压反馈机制）。

2. **packet_pending 机制**：如果上一次 `avcodec_send_packet()` 返回了 EAGAIN（解码器内部缓冲已满），说明 packet 还没被消费，此时不从队列取新包，而是重新使用之前的 packet。

3. **packet_queue_get()**：以阻塞模式（第三个参数 `block=1`）从队列中取一个 packet，同时获取这个 packet 的 serial。

4. **serial 变化处理**：如果取到的 packet 的 serial 与之前不同，说明发生了 seek。此时需要：
   - `avcodec_flush_buffers()`：清空解码器内部缓冲
   - `d->finished = 0`：重置完成标志
   - 恢复 `next_pts` 到 `start_pts`：重新开始 PTS 推算

5. **丢弃旧 serial 的 packet**：在外层 do-while 中，如果取到的 packet serial 与队列当前 serial 不匹配（说明是 seek 之前的残留），直接丢弃，继续取下一个。

### 2.5 阶段三：发送 packet 到解码器

根据媒体类型，走不同的发送路径：

#### 字幕的特殊处理（旧 API）

```c
        if (d->avctx->codec_type == AVMEDIA_TYPE_SUBTITLE) {
            int got_frame = 0;
            // 🔑 字幕使用旧的同步解码 API
            ret = avcodec_decode_subtitle2(d->avctx, sub, &got_frame, d->pkt);
            if (ret < 0) {
                ret = AVERROR(EAGAIN);
            } else {
                if (got_frame && !d->pkt->data) {
                    d->packet_pending = 1;
                }
                ret = got_frame ? 0 : (d->pkt->data ? AVERROR(EAGAIN) : AVERROR_EOF);
            }
            av_packet_unref(d->pkt);
```

字幕解码使用的是 FFmpeg 的旧 API `avcodec_decode_subtitle2()`，而不是新的 send/receive 模式。原因是字幕的 `AVSubtitle` 结构与 `AVFrame` 不同，FFmpeg 并未为字幕实现新 API。

返回值逻辑：
- 解码出错：返回 EAGAIN（跳过这个包，继续尝试下一个）
- 解码成功且 `got_frame=1`：返回 0（表示拿到一帧字幕）
- 解码成功但 `got_frame=0` 且还有数据：返回 EAGAIN（继续送下一个包）
- 解码成功但 `got_frame=0` 且无数据（null packet）：返回 EOF

#### 音视频发送（新 API）

```c
        } else {
            // 🔑 通过 opaque_ref 传递 FrameData（携带 pkt_pos）
            if (d->pkt->buf && !d->pkt->opaque_ref) {
                FrameData *fd;

                d->pkt->opaque_ref = av_buffer_allocz(sizeof(*fd));
                if (!d->pkt->opaque_ref)
                    return AVERROR(ENOMEM);
                fd = (FrameData*)d->pkt->opaque_ref->data;
                fd->pkt_pos = d->pkt->pos;
            }

            // 🔑 将 packet 送入解码器
            if (avcodec_send_packet(d->avctx, d->pkt) == AVERROR(EAGAIN)) {
                av_log(d->avctx, AV_LOG_ERROR,
                       "Receive_frame and send_packet both returned EAGAIN, "
                       "which is an API violation.\n");
                d->packet_pending = 1;
            } else {
                av_packet_unref(d->pkt);
            }
        }
    }
}
```

**FrameData / opaque_ref 数据传递机制**：

这是一个精巧的设计。FFmpeg 的新 API 中，`avcodec_send_packet()` 和 `avcodec_receive_frame()` 是异步的——送入 packet 时不一定立刻就能取出 frame（特别是有 B 帧时）。那么如何将 packet 携带的元数据（如文件位置 `pkt_pos`）传递到最终输出的 frame 呢？

答案就是 `opaque_ref`：
1. 在 `send_packet` 之前，将 `FrameData`（包含 `pkt_pos`）封装到 `pkt->opaque_ref` 中
2. FFmpeg 解码器内部会将 `pkt->opaque_ref` 自动透传到对应的 `frame->opaque_ref`
3. 在 `video_thread` / `audio_thread` 中通过 `frame->opaque_ref` 取回 `FrameData`

```c
typedef struct FrameData {
    int64_t pkt_pos;    // packet 在文件中的字节偏移
} FrameData;
```

**packet_pending 机制**：

当 `avcodec_send_packet()` 返回 EAGAIN 时（解码器缓冲满了），说明解码器当前无法接受更多 packet，需要先通过 `receive_frame` 取走一些帧。这种情况下：
- 设置 `packet_pending = 1`，表示这个 packet 还没被消费
- 不调用 `av_packet_unref()`，保留 packet 数据
- 下次循环时跳过 `packet_queue_get()`，直接复用此 packet

### 2.6 状态机完整流程总结

整个 `decoder_decode_frame()` 可以概括为一个三阶段循环：

```
┌─────────────────────────────────────────────────────────────┐
│                      for (;;) 主循环                         │
│                                                             │
│  阶段1: receive_frame                                       │
│    ├─ serial 匹配？否 → 跳过，直接进入阶段2                    │
│    ├─ avcodec_receive_frame()                               │
│    ├─ 成功(ret>=0) → return 1                               │
│    ├─ EOF → flush 并 return 0                               │
│    └─ EAGAIN → 进入阶段2                                    │
│                                                             │
│  阶段2: 从 PacketQueue 取包                                  │
│    ├─ packet_pending？是 → 复用之前的 packet                  │
│    ├─ packet_queue_get() 阻塞取包                            │
│    ├─ serial 变化 → flush 解码器                             │
│    └─ 丢弃不匹配 serial 的旧包                                │
│                                                             │
│  阶段3: send_packet                                         │
│    ├─ 字幕 → avcodec_decode_subtitle2()（旧 API）            │
│    ├─ 音视频 → 填充 opaque_ref + avcodec_send_packet()       │
│    ├─ EAGAIN → 设置 packet_pending                          │
│    └─ 成功 → av_packet_unref(), 回到阶段1                    │
└─────────────────────────────────────────────────────────────┘
```

## 3. video_thread()——视频解码线程

`video_thread()` 是视频解码的主线程函数。它在 `stream_component_open()` 中通过 `decoder_start()` 创建：

```c
static int decoder_start(Decoder *d, int (*fn)(void *), const char *thread_name, void* arg)
{
    packet_queue_start(d->queue);
    d->decoder_tid = SDL_CreateThread(fn, thread_name, arg);
    if (!d->decoder_tid) {
        av_log(NULL, AV_LOG_ERROR, "SDL_CreateThread(): %s\n", SDL_GetError());
        return AVERROR(ENOMEM);
    }
    return 0;
}
```

### 3.1 get_video_frame()——获取并判断丢帧

在分析 `video_thread` 之前，先看它依赖的 `get_video_frame()`：

```c
static int get_video_frame(VideoState *is, AVFrame *frame)
{
    int got_picture;

    // 调用底层解码函数
    if ((got_picture = decoder_decode_frame(&is->viddec, frame, NULL)) < 0)
        return -1;

    if (got_picture) {
        double dpts = NAN;

        if (frame->pts != AV_NOPTS_VALUE)
            dpts = av_q2d(is->video_st->time_base) * frame->pts;

        frame->sample_aspect_ratio = av_guess_sample_aspect_ratio(is->ic, is->video_st, frame);

        // 🔑 丢帧策略：当视频落后于主时钟时，直接丢弃该帧
        if (framedrop>0 || (framedrop && get_master_sync_type(is) != AV_SYNC_VIDEO_MASTER)) {
            if (frame->pts != AV_NOPTS_VALUE) {
                double diff = dpts - get_master_clock(is);
                if (!isnan(diff) && fabs(diff) < AV_NOSYNC_THRESHOLD &&
                    diff - is->frame_last_filter_delay < 0 &&
                    is->viddec.pkt_serial == is->vidclk.serial &&
                    is->videoq.nb_packets) {
                    is->frame_drops_early++;
                    av_frame_unref(frame);
                    got_picture = 0;
                }
            }
        }
    }

    return got_picture;
}
```

**丢帧条件**（全部满足时才丢帧）：

| 条件 | 含义 |
|------|------|
| `framedrop > 0` 或非视频主时钟模式 | 允许丢帧 |
| `diff < 0`（减去滤镜延迟后） | 视频帧已落后于主时钟 |
| `fabs(diff) < AV_NOSYNC_THRESHOLD` | 差值不超过 10 秒（否则可能是 seek，不应丢帧） |
| `pkt_serial == vidclk.serial` | serial 一致（不在 seek 过程中） |
| `videoq.nb_packets > 0` | 队列中还有包（确保不是最后一帧） |

这是一种**早期丢帧（Early Drop）** 策略——在解码完成后、送入滤镜和 FrameQueue 之前就判断是否过期。相比渲染阶段的 Late Drop，它更高效，因为避免了不必要的滤镜处理和队列占用。

### 3.2 video_thread 主循环

```c
static int video_thread(void *arg)
{
    VideoState *is = arg;
    AVFrame *frame = av_frame_alloc();
    double pts;
    double duration;
    int ret;
    AVRational tb = is->video_st->time_base;
    AVRational frame_rate = av_guess_frame_rate(is->ic, is->video_st, NULL);

    // 滤镜相关变量
    AVFilterGraph *graph = NULL;
    AVFilterContext *filt_out = NULL, *filt_in = NULL;
    int last_w = 0;
    int last_h = 0;
    enum AVPixelFormat last_format = -2;
    int last_serial = -1;
    int last_vfilter_idx = 0;

    if (!frame)
        return AVERROR(ENOMEM);

    for (;;) {
        // 🔑 步骤1：获取一帧解码后的视频（含丢帧判断）
        ret = get_video_frame(is, frame);
        if (ret < 0)
            goto the_end;
        if (!ret)
            continue;   // 被丢帧或 EOF，继续下一帧
```

`last_w`、`last_h`、`last_format`、`last_serial`、`last_vfilter_idx` 用于检测视频参数是否变化。当分辨率、像素格式、serial 或滤镜索引变化时，需要重新配置滤镜图。

### 3.3 视频滤镜配置与处理

```c
        // 🔑 步骤2：检测视频参数变化，重新配置滤镜
        if (   last_w != frame->width
            || last_h != frame->height
            || last_format != frame->format
            || last_serial != is->viddec.pkt_serial
            || last_vfilter_idx != is->vfilter_idx) {
            av_log(NULL, AV_LOG_DEBUG,
                   "Video frame changed from size:%dx%d format:%s serial:%d "
                   "to size:%dx%d format:%s serial:%d\n",
                   last_w, last_h,
                   (const char *)av_x_if_null(av_get_pix_fmt_name(last_format), "none"),
                   last_serial,
                   frame->width, frame->height,
                   (const char *)av_x_if_null(av_get_pix_fmt_name(frame->format), "none"),
                   is->viddec.pkt_serial);
            // 释放旧的滤镜图，创建新的
            avfilter_graph_free(&graph);
            graph = avfilter_graph_alloc();
            if (!graph) {
                ret = AVERROR(ENOMEM);
                goto the_end;
            }
            graph->nb_threads = filter_nbthreads;
            if ((ret = configure_video_filters(graph, is,
                    vfilters_list ? vfilters_list[is->vfilter_idx] : NULL, frame)) < 0) {
                SDL_Event event;
                event.type = FF_QUIT_EVENT;
                event.user.data1 = is;
                SDL_PushEvent(&event);
                goto the_end;
            }
            filt_in  = is->in_video_filter;
            filt_out = is->out_video_filter;
            last_w = frame->width;
            last_h = frame->height;
            last_format = frame->format;
            last_serial = is->viddec.pkt_serial;
            last_vfilter_idx = is->vfilter_idx;
            frame_rate = av_buffersink_get_frame_rate(filt_out);
        }
```

视频滤镜图的结构为：`buffer (源) → [用户指定滤镜] → buffersink (汇)`。关于滤镜的详细配置将在第 10 篇中深入分析，这里只需理解它是一个"输入帧 → 处理 → 输出帧"的管道。

### 3.4 滤镜输出与入队

```c
        // 🔑 步骤3：将解码帧送入滤镜
        ret = av_buffersrc_add_frame(filt_in, frame);
        if (ret < 0)
            goto the_end;

        // 🔑 步骤4：从滤镜取出处理后的帧，放入 pictq
        while (ret >= 0) {
            FrameData *fd;

            is->frame_last_returned_time = av_gettime_relative() / 1000000.0;

            ret = av_buffersink_get_frame_flags(filt_out, frame, 0);
            if (ret < 0) {
                if (ret == AVERROR_EOF)
                    is->viddec.finished = is->viddec.pkt_serial;
                ret = 0;
                break;
            }

            // 🔑 通过 opaque_ref 取回 FrameData（在 decoder_decode_frame 中设置）
            fd = frame->opaque_ref ? (FrameData*)frame->opaque_ref->data : NULL;

            is->frame_last_filter_delay = av_gettime_relative() / 1000000.0
                                        - is->frame_last_returned_time;
            if (fabs(is->frame_last_filter_delay) > AV_NOSYNC_THRESHOLD / 10.0)
                is->frame_last_filter_delay = 0;
            tb = av_buffersink_get_time_base(filt_out);
            // 计算帧时长
            duration = (frame_rate.num && frame_rate.den
                        ? av_q2d((AVRational){frame_rate.den, frame_rate.num}) : 0);
            // 计算 PTS（秒）
            pts = (frame->pts == AV_NOPTS_VALUE) ? NAN : frame->pts * av_q2d(tb);
            // 🔑 将帧放入 FrameQueue
            ret = queue_picture(is, frame, pts, duration,
                                fd ? fd->pkt_pos : -1, is->viddec.pkt_serial);
            av_frame_unref(frame);
            // serial 变化时提前退出
            if (is->videoq.serial != is->viddec.pkt_serial)
                break;
        }

        if (ret < 0)
            goto the_end;
    }
 the_end:
    avfilter_graph_free(&graph);
    av_frame_free(&frame);
    return 0;
}
```

**`frame_last_filter_delay`** 记录了滤镜处理的耗时，用于 `get_video_frame()` 中更精确地判断丢帧（减去滤镜延迟后再与主时钟比较）。

### 3.5 queue_picture()——视频帧入队

```c
static int queue_picture(VideoState *is, AVFrame *src_frame, double pts,
                         double duration, int64_t pos, int serial)
{
    Frame *vp;

    // 获取 FrameQueue 中可写位置（可能阻塞等待空间）
    if (!(vp = frame_queue_peek_writable(&is->pictq)))
        return -1;

    vp->sar = src_frame->sample_aspect_ratio;
    vp->uploaded = 0;      // 标记为未上传（需要重新上传到 GPU 纹理）

    vp->width = src_frame->width;
    vp->height = src_frame->height;
    vp->format = src_frame->format;

    vp->pts = pts;         // 显示时间戳（秒）
    vp->duration = duration; // 帧持续时间（秒）
    vp->pos = pos;         // 在文件中的字节位置
    vp->serial = serial;   // 所属的播放序列号

    set_default_window_size(vp->width, vp->height, vp->sar);

    // 🔑 将帧数据 move 到 FrameQueue 的槽位中（零拷贝）
    av_frame_move_ref(vp->frame, src_frame);
    // 推进写指针，通知消费者
    frame_queue_push(&is->pictq);
    return 0;
}
```

注意 `av_frame_move_ref()` 是**移动语义**而非拷贝——它将 `src_frame` 的数据所有权转移到 `vp->frame`，避免了像素数据的深拷贝。

## 4. audio_thread()——音频解码线程

音频解码线程的结构与视频类似，但有一些音频特有的逻辑：

```c
static int audio_thread(void *arg)
{
    VideoState *is = arg;
    AVFrame *frame = av_frame_alloc();
    Frame *af;
    int last_serial = -1;
    int reconfigure;
    int got_frame = 0;
    AVRational tb;
    int ret = 0;

    if (!frame)
        return AVERROR(ENOMEM);

    do {
        // 🔑 步骤1：解码一帧音频
        if ((got_frame = decoder_decode_frame(&is->auddec, frame, NULL)) < 0)
            goto the_end;

        if (got_frame) {
                tb = (AVRational){1, frame->sample_rate};
```

### 4.1 音频格式变化检测

```c
                // 🔑 检测音频格式是否发生变化
                reconfigure =
                    cmp_audio_fmts(is->audio_filter_src.fmt,
                                   is->audio_filter_src.ch_layout.nb_channels,
                                   frame->format, frame->ch_layout.nb_channels) ||
                    av_channel_layout_compare(&is->audio_filter_src.ch_layout,
                                             &frame->ch_layout) ||
                    is->audio_filter_src.freq != frame->sample_rate ||
                    is->auddec.pkt_serial     != last_serial;
```

音频格式变化的检测比视频更复杂，需要比较四个维度：

| 检测项 | 说明 |
|--------|------|
| 采样格式（fmt） | 如 S16 → FLOAT |
| 声道布局（ch_layout） | 如 stereo → 5.1 |
| 采样率（freq） | 如 44100 → 48000 |
| serial | seek 导致的 serial 变化 |

### 4.2 滤镜重配置

```c
                if (reconfigure) {
                    char buf1[1024], buf2[1024];
                    av_channel_layout_describe(&is->audio_filter_src.ch_layout, buf1, sizeof(buf1));
                    av_channel_layout_describe(&frame->ch_layout, buf2, sizeof(buf2));
                    av_log(NULL, AV_LOG_DEBUG,
                           "Audio frame changed from rate:%d ch:%d fmt:%s layout:%s serial:%d "
                           "to rate:%d ch:%d fmt:%s layout:%s serial:%d\n",
                           is->audio_filter_src.freq,
                           is->audio_filter_src.ch_layout.nb_channels,
                           av_get_sample_fmt_name(is->audio_filter_src.fmt), buf1, last_serial,
                           frame->sample_rate, frame->ch_layout.nb_channels,
                           av_get_sample_fmt_name(frame->format), buf2, is->auddec.pkt_serial);

                    // 更新源格式记录
                    is->audio_filter_src.fmt            = frame->format;
                    ret = av_channel_layout_copy(&is->audio_filter_src.ch_layout,
                                                &frame->ch_layout);
                    if (ret < 0)
                        goto the_end;
                    is->audio_filter_src.freq           = frame->sample_rate;
                    last_serial                         = is->auddec.pkt_serial;

                    // 🔑 重新配置音频滤镜图
                    if ((ret = configure_audio_filters(is, afilters, 1)) < 0)
                        goto the_end;
                }
```

`configure_audio_filters()` 会创建 `abuffer → [用户滤镜] → abuffersink` 的音频滤镜链。参数 `force_output_format=1` 表示强制输出格式为 SDL 音频设备需要的格式（采样率、声道数、采样格式）。

### 4.3 滤镜处理与入队

```c
            // 🔑 步骤3：将解码帧送入音频滤镜
            if ((ret = av_buffersrc_add_frame(is->in_audio_filter, frame)) < 0)
                goto the_end;

            // 🔑 步骤4：从滤镜取出处理后的帧，放入 sampq
            while ((ret = av_buffersink_get_frame_flags(is->out_audio_filter, frame, 0)) >= 0) {
                FrameData *fd = frame->opaque_ref ? (FrameData*)frame->opaque_ref->data : NULL;
                tb = av_buffersink_get_time_base(is->out_audio_filter);
                if (!(af = frame_queue_peek_writable(&is->sampq)))
                    goto the_end;

                af->pts = (frame->pts == AV_NOPTS_VALUE) ? NAN : frame->pts * av_q2d(tb);
                af->pos = fd ? fd->pkt_pos : -1;
                af->serial = is->auddec.pkt_serial;
                af->duration = av_q2d((AVRational){frame->nb_samples, frame->sample_rate});

                av_frame_move_ref(af->frame, frame);
                frame_queue_push(&is->sampq);

                // serial 变化时提前退出滤镜循环
                if (is->audioq.serial != is->auddec.pkt_serial)
                    break;
            }
            if (ret == AVERROR_EOF)
                is->auddec.finished = is->auddec.pkt_serial;
        }
    } while (ret >= 0 || ret == AVERROR(EAGAIN) || ret == AVERROR_EOF);
 the_end:
    avfilter_graph_free(&is->agraph);
    av_frame_free(&frame);
    return ret;
}
```

**与视频线程的差异**：

1. **循环结构不同**：音频使用 `do { ... } while(...)` 而视频使用 `for (;;)`。音频的外层循环会在 `ret >= 0 || EAGAIN || EOF` 时继续，这意味着 EOF 不会立刻退出线程，而是在下一次 `decoder_decode_frame` 中处理。
2. **没有丢帧**：音频不做 early drop，因为音频是连续的流，丢帧会导致听觉上的卡顿（"咔嗒"声）。音频同步是通过调整采样数来实现的（详见第 5 篇）。
3. **duration 计算**：`nb_samples / sample_rate` 得到的是精确的帧持续时间（秒）。

## 5. subtitle_thread()——字幕解码线程

字幕解码线程是三个解码线程中最简单的：

```c
static int subtitle_thread(void *arg)
{
    VideoState *is = arg;
    Frame *sp;
    int got_subtitle;
    double pts;

    for (;;) {
        // 🔑 获取 FrameQueue 可写位置（提前获取，因为 sub 直接解码到 sp->sub）
        if (!(sp = frame_queue_peek_writable(&is->subpq)))
            return 0;

        // 🔑 解码字幕（注意传入的是 &sp->sub 而非 AVFrame）
        if ((got_subtitle = decoder_decode_frame(&is->subdec, NULL, &sp->sub)) < 0)
            break;

        pts = 0;

        // 🔑 只处理 bitmap 格式的字幕（format == 0）
        if (got_subtitle && sp->sub.format == 0) {
            if (sp->sub.pts != AV_NOPTS_VALUE)
                pts = sp->sub.pts / (double)AV_TIME_BASE;
            sp->pts = pts;
            sp->serial = is->subdec.pkt_serial;
            sp->width = is->subdec.avctx->width;
            sp->height = is->subdec.avctx->height;
            sp->uploaded = 0;

            /* now we can update the picture count */
            frame_queue_push(&is->subpq);
        } else if (got_subtitle) {
            // 非 bitmap 格式（如 ASS/SRT 文本字幕），释放
            avsubtitle_free(&sp->sub);
        }
    }
    return 0;
}
```

**关键设计要点**：

1. **先获取可写位置再解码**：与视频/音频不同，字幕先调用 `frame_queue_peek_writable()` 获取目标 `Frame`，然后将 `&sp->sub` 传给 `decoder_decode_frame()`，这样字幕数据直接解码到 FrameQueue 的槽位中，避免多余的拷贝。

2. **只处理 bitmap 字幕**：`sp->sub.format == 0` 表示 bitmap 字幕（如 DVD/Blu-ray 的图形字幕）。ffplay 只渲染这种格式的字幕，文本字幕（ASS、SRT 等 `format != 0`）会被直接释放丢弃。

3. **不经过滤镜**：字幕没有滤镜处理阶段，直接从解码器到 FrameQueue。

4. **PTS 处理**：字幕的 PTS 以 `AV_TIME_BASE`（微秒）为时基，转换为秒需要除以 `AV_TIME_BASE`。

## 6. 三个解码线程对比总结

| 特性 | video_thread | audio_thread | subtitle_thread |
|------|:------------|:------------|:---------------|
| **输入队列** | videoq (PacketQueue) | audioq (PacketQueue) | subtitleq (PacketQueue) |
| **输出队列** | pictq (FrameQueue) | sampq (FrameQueue) | subpq (FrameQueue) |
| **解码 API** | send/receive (新 API) | send/receive (新 API) | avcodec_decode_subtitle2 (旧 API) |
| **输出类型** | AVFrame | AVFrame | AVSubtitle |
| **滤镜处理** | buffersrc/buffersink (视频滤镜) | abuffer/abuffersink (音频滤镜) | 无 |
| **丢帧策略** | get_video_frame 中 early drop | 无（通过采样数调整同步） | 无 |
| **格式变化检测** | 分辨率、像素格式、serial | 采样格式、声道、采样率、serial | 无 |
| **循环结构** | `for (;;)` | `do { } while(...)` | `for (;;)` |
| **PTS 处理** | best_effort_timestamp | 转换为采样率时基 + 线性推算 | AV_TIME_BASE 转秒 |
| **FrameData 传递** | 通过 opaque_ref | 通过 opaque_ref | 不使用 |

## 7. 小结

本篇深入分析了 ffplay 的解码核心机制，核心内容可以总结为：

- **decoder_decode_frame()** 是三个解码线程共享的底层引擎，以无限循环状态机的形式工作，包含三个阶段：receive_frame → 取包 → send_packet
- **serial 机制** 贯穿整个解码过程，确保 seek 后旧数据被正确丢弃、解码器被正确 flush
- **packet_pending** 是处理 send/receive 异步模型中 EAGAIN 情况的巧妙设计
- **opaque_ref / FrameData** 解决了异步解码中元数据透传的问题
- **视频线程** 在解码后还有丢帧判断和滤镜处理两个重要环节
- **音频线程** 需要检测格式变化并动态重配置滤镜链
- **字幕线程** 使用旧 API，且只处理 bitmap 格式

数据流在解码阶段的完整路径：`PacketQueue → decoder_decode_frame() → 滤镜(可选) → FrameQueue`。下一篇我们将继续跟随数据流，分析音频帧是如何从 FrameQueue 被送到 SDL 音频设备进行播放的。
