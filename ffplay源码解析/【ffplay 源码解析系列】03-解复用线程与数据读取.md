# ffplay 源码解析系列（三）：解复用线程与数据读取

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> read_thread 是整个播放管线的数据源头，负责从文件或网络中读取压缩数据包并分发到各解码线程。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 概述

`read_thread` 是 ffplay 中最核心的线程之一。它在 `stream_open()` 中被创建，承担以下职责：

1. **打开媒体文件**：调用 `avformat_open_input()` 打开输入源
2. **探测流信息**：调用 `avformat_find_stream_info()` 获取流参数
3. **选择最佳流**：调用 `av_find_best_stream()` 选择音/视频/字幕流
4. **打开各流组件**：调用 `stream_component_open()` 初始化解码器并启动解码线程
5. **主读取循环**：不断调用 `av_read_frame()` 读取 packet 并分发到对应的 PacketQueue
6. **处理 Seek**：响应用户的 seek 请求
7. **处理 EOF**：文件读完后发送 null packet 通知解码器

![read_thread 主循环流程](https://gitee.com/yuhong1234/ffplay/raw/master/03-read-thread-flow.png)

## 2. 初始化阶段

### 2.1 打开输入源

```c
static int read_thread(void *arg)
{
    VideoState *is = arg;
    AVFormatContext *ic = NULL;
    int err, i, ret;
    int st_index[AVMEDIA_TYPE_NB];      // 各类型流的索引
    AVPacket *pkt = NULL;
    SDL_mutex *wait_mutex = SDL_CreateMutex();

    memset(st_index, -1, sizeof(st_index));
    is->eof = 0;

    pkt = av_packet_alloc();
    if (!pkt) {
        ret = AVERROR(ENOMEM);
        goto fail;
    }

    // 分配 AVFormatContext
    ic = avformat_alloc_context();
    // 设置中断回调（允许在阻塞的 I/O 操作中中断）
    ic->interrupt_callback.callback = decode_interrupt_cb;
    ic->interrupt_callback.opaque = is;

    // 🔑 打开输入文件/网络流
    err = avformat_open_input(&ic, is->filename, is->iformat, &format_opts);
    if (err < 0) {
        print_error(is->filename, err);
        ret = -1;
        goto fail;
    }
    is->ic = ic;
    // ...
```

**中断回调**是一个重要的设计。网络流的 I/O 操作可能会长时间阻塞（如网络超时），通过 `decode_interrupt_cb`，当用户请求退出时可以及时中断：

```c
static int decode_interrupt_cb(void *ctx)
{
    VideoState *is = ctx;
    return is->abort_request;  // 返回 1 表示中断 I/O
}
```

### 2.2 探测流信息

```c
    if (find_stream_info) {
        AVDictionary **opts;
        int orig_nb_streams = ic->nb_streams;

        err = setup_find_stream_info_opts(ic, codec_opts, &opts);

        // 读取一些帧来探测流的编码参数（如分辨率、采样率等）
        err = avformat_find_stream_info(ic, opts);

        for (i = 0; i < orig_nb_streams; i++)
            av_dict_free(&opts[i]);
        av_freep(&opts);
    }
```

`avformat_find_stream_info()` 会实际读取一些数据帧，分析编码参数。对于某些格式（如 MPEG-TS），头部信息不完整，需要通过这种方式来获取准确的流参数。

### 2.3 配置播放参数

```c
    // 判断是否为实时流
    is->realtime = is_realtime(ic);

    // 如果用户指定了开始时间，执行初始 seek
    if (start_time != AV_NOPTS_VALUE) {
        int64_t timestamp = start_time;
        if (ic->start_time != AV_NOPTS_VALUE)
            timestamp += ic->start_time;
        ret = avformat_seek_file(ic, -1, INT64_MIN, timestamp, INT64_MAX, 0);
    }

    // 设置最大帧时长（超过此值认为时间戳不连续）
    is->max_frame_duration = (ic->iformat->flags & AVFMT_TS_DISCONT) ? 10.0 : 3600.0;

    // 根据 seek_by_bytes 确定 seek 方式
    if (seek_by_bytes < 0)
        seek_by_bytes = !(ic->iformat->flags & AVFMT_NO_BYTE_SEEK) &&
                        !!(ic->iformat->flags & AVFMT_TS_DISCONT) &&
                        strcmp("ogg", ic->iformat->name);
```

`is_realtime()` 通过检查格式名或 URL 前缀来判断是否为实时流：

```c
static int is_realtime(AVFormatContext *s)
{
    if(   !strcmp(s->iformat->name, "rtp")
       || !strcmp(s->iformat->name, "rtsp")
       || !strcmp(s->iformat->name, "sdp")
    )
        return 1;
    if(s->pb && (   !strncmp(s->url, "rtp:", 4)
                 || !strncmp(s->url, "udp:", 4)
                )
    )
        return 1;
    return 0;
}
```

### 2.4 选择最佳流

```c
    // 用户可以通过 -ast/-vst/-sst 指定流
    for (i = 0; i < ic->nb_streams; i++) {
        AVStream *st = ic->streams[i];
        enum AVMediaType type = st->codecpar->codec_type;
        st->discard = AVDISCARD_ALL;
        if (type >= 0 && wanted_stream_spec[type] && st_index[type] == -1)
            if (avformat_match_stream_specifier(ic, st, wanted_stream_spec[type]) > 0)
                st_index[type] = i;
    }

    // 自动选择最佳流
    if (!video_disable)
        st_index[AVMEDIA_TYPE_VIDEO] =
            av_find_best_stream(ic, AVMEDIA_TYPE_VIDEO,
                                st_index[AVMEDIA_TYPE_VIDEO], -1, NULL, 0);
    if (!audio_disable)
        st_index[AVMEDIA_TYPE_AUDIO] =
            av_find_best_stream(ic, AVMEDIA_TYPE_AUDIO,
                                st_index[AVMEDIA_TYPE_AUDIO],
                                st_index[AVMEDIA_TYPE_VIDEO],  // 优先选同节目的音频
                                NULL, 0);
    if (!video_disable && !subtitle_disable)
        st_index[AVMEDIA_TYPE_SUBTITLE] =
            av_find_best_stream(ic, AVMEDIA_TYPE_SUBTITLE,
                                st_index[AVMEDIA_TYPE_SUBTITLE],
                                (st_index[AVMEDIA_TYPE_AUDIO] >= 0 ?
                                 st_index[AVMEDIA_TYPE_AUDIO] :
                                 st_index[AVMEDIA_TYPE_VIDEO]),
                                NULL, 0);
```

`av_find_best_stream()` 的第 4 个参数 `related_stream` 很有讲究：
- 选音频时以视频流为关联流（优先选同一个 program 中的音频）
- 选字幕时以音频流（或视频流）为关联流

### 2.5 打开各流组件

```c
    // 依次打开音频、视频、字幕流
    if (st_index[AVMEDIA_TYPE_AUDIO] >= 0)
        stream_component_open(is, st_index[AVMEDIA_TYPE_AUDIO]);

    if (st_index[AVMEDIA_TYPE_VIDEO] >= 0)
        ret = stream_component_open(is, st_index[AVMEDIA_TYPE_VIDEO]);

    // 根据视频流是否成功打开决定显示模式
    if (is->show_mode == SHOW_MODE_NONE)
        is->show_mode = ret >= 0 ? SHOW_MODE_VIDEO : SHOW_MODE_RDFT;

    if (st_index[AVMEDIA_TYPE_SUBTITLE] >= 0)
        stream_component_open(is, st_index[AVMEDIA_TYPE_SUBTITLE]);

    if (is->video_stream < 0 && is->audio_stream < 0) {
        av_log(NULL, AV_LOG_FATAL, "Failed to open file '%s'\n", is->filename);
        ret = -1;
        goto fail;
    }
```

`stream_component_open()` 是一个重要的函数，它负责：创建 AVCodecContext、查找并打开解码器、初始化 Decoder、启动解码线程。其详细逻辑将在第 4 篇中剖析。

## 3. 主读取循环

初始化完成后，read_thread 进入核心的读取-分发循环。这个循环是整个播放器的"心脏泵"。

![read_thread 数据分发流向](https://gitee.com/yuhong1234/ffplay/raw/master/03-packet-dispatch.png)

### 3.1 循环总体结构

```c
    for (;;) {
        // 1. 检查退出请求
        if (is->abort_request)
            break;

        // 2. 处理暂停状态变化
        // 3. 处理 Seek 请求
        // 4. 处理 attached_pic（封面图）
        // 5. 背压控制：队列满则等待
        // 6. 检测播放结束
        // 7. 读取 packet 并分发
    }
```

### 3.2 暂停处理

```c
        // 检测暂停状态变化
        if (is->paused != is->last_paused) {
            is->last_paused = is->paused;
            if (is->paused)
                is->read_pause_return = av_read_pause(ic);  // 通知服务端暂停（RTSP）
            else
                av_read_play(ic);                            // 通知服务端恢复
        }
```

对于本地文件，`av_read_pause/play` 是无效的。但对于 RTSP 流，这些调用会向服务端发送 PAUSE/PLAY 命令，减少不必要的网络传输。

### 3.3 Seek 处理

Seek 是播放器最复杂的操作之一。当用户按下方向键或拖动进度条时，`event_loop` 会设置 `is->seek_req = 1`，read_thread 在主循环中检测并执行：

```c
        if (is->seek_req) {
            int64_t seek_target = is->seek_pos;
            int64_t seek_min = is->seek_rel > 0 ? seek_target - is->seek_rel + 2: INT64_MIN;
            int64_t seek_max = is->seek_rel < 0 ? seek_target - is->seek_rel - 2: INT64_MAX;

            // 执行精确 seek
            ret = avformat_seek_file(is->ic, -1, seek_min, seek_target, seek_max,
                                     is->seek_flags);
            if (ret < 0) {
                av_log(NULL, AV_LOG_ERROR, "%s: error while seeking\n", is->ic->url);
            } else {
                // Seek 成功后，清空所有队列（触发 serial++）
                if (is->audio_stream >= 0)
                    packet_queue_flush(&is->audioq);
                if (is->subtitle_stream >= 0)
                    packet_queue_flush(&is->subtitleq);
                if (is->video_stream >= 0)
                    packet_queue_flush(&is->videoq);

                // 更新外部时钟
                if (is->seek_flags & AVSEEK_FLAG_BYTE) {
                    set_clock(&is->extclk, NAN, 0);
                } else {
                    set_clock(&is->extclk, seek_target / (double)AV_TIME_BASE, 0);
                }
            }

            is->seek_req = 0;
            is->queue_attachments_req = 1;
            is->eof = 0;

            // 如果暂停状态下 seek，显示 seek 后的第一帧
            if (is->paused)
                step_to_next_frame(is);
        }
```

Seek 后的关键操作是 `packet_queue_flush()`——它不仅清空队列，还会**递增 serial**。这确保了解码器能感知到 seek 事件并丢弃旧数据（参见第 2 篇 serial 机制）。

### 3.4 背压控制

当队列已满时，read_thread 会暂停读取，避免内存无限增长：

```c
        // 队列满判断条件：
        // 1. 总大小超过 15MB，或
        // 2. 所有流的队列都"足够满"
        if (infinite_buffer < 1 &&
              (is->audioq.size + is->videoq.size + is->subtitleq.size > MAX_QUEUE_SIZE
            || (stream_has_enough_packets(is->audio_st, is->audio_stream, &is->audioq) &&
                stream_has_enough_packets(is->video_st, is->video_stream, &is->videoq) &&
                stream_has_enough_packets(is->subtitle_st, is->subtitle_stream, &is->subtitleq))))
        {
            // 等待 10ms 后重试
            SDL_LockMutex(wait_mutex);
            SDL_CondWaitTimeout(is->continue_read_thread, wait_mutex, 10);
            SDL_UnlockMutex(wait_mutex);
            continue;
        }
```

`stream_has_enough_packets()` 的判断逻辑：

```c
static int stream_has_enough_packets(AVStream *st, int stream_id, PacketQueue *queue) {
    return stream_id < 0 ||                              // 流不存在
           queue->abort_request ||                       // 队列已中止
           (st->disposition & AV_DISPOSITION_ATTACHED_PIC) ||  // 是封面图
           queue->nb_packets > MIN_FRAMES &&             // 包数量 > 25
           (!queue->duration ||                          // 且总时长 > 1秒
            av_q2d(st->time_base) * queue->duration > 1.0);
}
```

这个函数体现了"**足够满**"的策略：队列中至少有 25 个包，且总时长超过 1 秒。

### 3.5 读取与分发

循环的核心部分——读取 packet 并分发到对应的队列：

```c
        // 检查播放是否结束（所有解码器都已完成且帧队列为空）
        if (!is->paused &&
            (!is->audio_st || (is->auddec.finished == is->audioq.serial &&
                               frame_queue_nb_remaining(&is->sampq) == 0)) &&
            (!is->video_st || (is->viddec.finished == is->videoq.serial &&
                               frame_queue_nb_remaining(&is->pictq) == 0)))
        {
            if (loop != 1 && (!loop || --loop)) {
                stream_seek(is, start_time != AV_NOPTS_VALUE ? start_time : 0, 0, 0);
            } else if (autoexit) {
                ret = AVERROR_EOF;
                goto fail;
            }
        }

        // 🔑 读取一个 packet
        ret = av_read_frame(ic, pkt);

        if (ret < 0) {
            // EOF 处理：向各队列发送 null packet
            if ((ret == AVERROR_EOF || avio_feof(ic->pb)) && !is->eof) {
                if (is->video_stream >= 0)
                    packet_queue_put_nullpacket(&is->videoq, pkt, is->video_stream);
                if (is->audio_stream >= 0)
                    packet_queue_put_nullpacket(&is->audioq, pkt, is->audio_stream);
                if (is->subtitle_stream >= 0)
                    packet_queue_put_nullpacket(&is->subtitleq, pkt, is->subtitle_stream);
                is->eof = 1;
            }
            if (ic->pb && ic->pb->error) {
                if (autoexit)
                    goto fail;
                else
                    break;
            }
            // 没有更多数据，等待一会儿再重试
            SDL_LockMutex(wait_mutex);
            SDL_CondWaitTimeout(is->continue_read_thread, wait_mutex, 10);
            SDL_UnlockMutex(wait_mutex);
            continue;
        } else {
            is->eof = 0;
        }

        // 检查 packet 是否在用户指定的播放范围内
        stream_start_time = ic->streams[pkt->stream_index]->start_time;
        pkt_ts = pkt->pts == AV_NOPTS_VALUE ? pkt->dts : pkt->pts;
        pkt_in_play_range = duration == AV_NOPTS_VALUE ||
                (pkt_ts - (stream_start_time != AV_NOPTS_VALUE ? stream_start_time : 0)) *
                av_q2d(ic->streams[pkt->stream_index]->time_base) -
                (double)(start_time != AV_NOPTS_VALUE ? start_time : 0) / 1000000
                <= ((double)duration / 1000000);

        // 🔑 根据 stream_index 分发到对应的 PacketQueue
        if (pkt->stream_index == is->audio_stream && pkt_in_play_range) {
            packet_queue_put(&is->audioq, pkt);
        } else if (pkt->stream_index == is->video_stream && pkt_in_play_range
                   && !(is->video_st->disposition & AV_DISPOSITION_ATTACHED_PIC)) {
            packet_queue_put(&is->videoq, pkt);
        } else if (pkt->stream_index == is->subtitle_stream && pkt_in_play_range) {
            packet_queue_put(&is->subtitleq, pkt);
        } else {
            av_packet_unref(pkt);       // 不需要的流，直接丢弃
        }
```

分发逻辑非常直观：根据 `pkt->stream_index` 判断 packet 属于哪个流，然后放入对应的 PacketQueue。不匹配任何已打开流的 packet 会被直接丢弃。

### 3.6 Attached Picture（封面图）处理

一些音频文件（如 MP3）会内嵌封面图，以 `AV_DISPOSITION_ATTACHED_PIC` 标记。这种"流"不需要反复读取，只需在启动和 seek 后发送一次：

```c
        if (is->queue_attachments_req) {
            if (is->video_st && is->video_st->disposition & AV_DISPOSITION_ATTACHED_PIC) {
                if ((ret = av_packet_ref(pkt, &is->video_st->attached_pic)) < 0)
                    goto fail;
                packet_queue_put(&is->videoq, pkt);
                packet_queue_put_nullpacket(&is->videoq, pkt, is->video_stream);
            }
            is->queue_attachments_req = 0;
        }
```

## 4. 线程退出与资源清理

```c
    ret = 0;
fail:
    if (ic && !is->ic)
        avformat_close_input(&ic);

    av_packet_free(&pkt);
    if (ret != 0) {
        // 发送退出事件通知主线程
        SDL_Event event;
        event.type = FF_QUIT_EVENT;
        event.user.data1 = is;
        SDL_PushEvent(&event);
    }
    SDL_DestroyMutex(wait_mutex);
    return 0;
}
```

当 read_thread 因错误退出时，它会通过 SDL 事件系统向主线程发送 `FF_QUIT_EVENT`，触发 `do_exit()` 进行全局清理。

## 5. stream_component_open()：打开流组件

`stream_component_open()` 是连接解复用和解码的桥梁函数，每个流（音频/视频/字幕）都会调用一次：

```c
static int stream_component_open(VideoState *is, int stream_index)
{
    AVFormatContext *ic = is->ic;
    AVCodecContext *avctx;
    const AVCodec *codec;

    // 1. 创建解码器上下文
    avctx = avcodec_alloc_context3(NULL);
    ret = avcodec_parameters_to_context(avctx, ic->streams[stream_index]->codecpar);
    avctx->pkt_timebase = ic->streams[stream_index]->time_base;

    // 2. 查找解码器
    codec = avcodec_find_decoder(avctx->codec_id);
    // 支持用户指定解码器（-acodec/-vcodec/-scodec）
    if (forced_codec_name)
        codec = avcodec_find_decoder_by_name(forced_codec_name);

    // 3. 配置解码选项
    if (fast)
        avctx->flags2 |= AV_CODEC_FLAG2_FAST;
    av_dict_set(&opts, "threads", "auto", 0);

    // 4. 视频流：创建硬件加速设备
    if (avctx->codec_type == AVMEDIA_TYPE_VIDEO) {
        ret = create_hwaccel(&avctx->hw_device_ctx);
    }

    // 5. 打开解码器
    ret = avcodec_open2(avctx, codec, &opts);

    // 6. 根据类型进行特定初始化
    switch (avctx->codec_type) {
    case AVMEDIA_TYPE_AUDIO:
        // 配置音频滤镜 → 打开 SDL 音频设备 → 初始化解码器 → 启动解码线程
        configure_audio_filters(is, afilters, 0);
        audio_open(is, &ch_layout, sample_rate, &is->audio_tgt);
        decoder_init(&is->auddec, avctx, &is->audioq, is->continue_read_thread);
        decoder_start(&is->auddec, audio_thread, "audio_decoder", is);
        SDL_PauseAudioDevice(audio_dev, 0);  // 开始播放
        break;

    case AVMEDIA_TYPE_VIDEO:
        // 初始化解码器 → 启动解码线程
        decoder_init(&is->viddec, avctx, &is->videoq, is->continue_read_thread);
        decoder_start(&is->viddec, video_thread, "video_decoder", is);
        break;

    case AVMEDIA_TYPE_SUBTITLE:
        // 初始化解码器 → 启动解码线程
        decoder_init(&is->subdec, avctx, &is->subtitleq, is->continue_read_thread);
        decoder_start(&is->subdec, subtitle_thread, "subtitle_decoder", is);
        break;
    }
    // ...
}
```

可以看到，音频流的初始化最复杂——它不仅要初始化解码器和启动解码线程，还需要配置音频滤镜链和打开 SDL 音频设备。

## 6. stream_component_close()：关闭流组件

与 open 对应，close 负责停止解码线程并释放资源：

```c
static void stream_component_close(VideoState *is, int stream_index)
{
    AVCodecParameters *codecpar = is->ic->streams[stream_index]->codecpar;

    switch (codecpar->codec_type) {
    case AVMEDIA_TYPE_AUDIO:
        decoder_abort(&is->auddec, &is->sampq);  // 中止解码器、等待线程退出
        SDL_CloseAudioDevice(audio_dev);           // 关闭音频设备
        decoder_destroy(&is->auddec);             // 释放解码器资源
        swr_free(&is->swr_ctx);                   // 释放重采样上下文
        av_freep(&is->audio_buf1);
        break;
    case AVMEDIA_TYPE_VIDEO:
        decoder_abort(&is->viddec, &is->pictq);
        decoder_destroy(&is->viddec);
        break;
    case AVMEDIA_TYPE_SUBTITLE:
        decoder_abort(&is->subdec, &is->subpq);
        decoder_destroy(&is->subdec);
        break;
    }

    // 将流标记为丢弃
    is->ic->streams[stream_index]->discard = AVDISCARD_ALL;
}
```

## 7. 小结

本篇详细分析了 ffplay 的解复用线程 `read_thread`，它是整个播放管线的数据源头：

- **初始化阶段**：打开文件 → 探测流信息 → 选择最佳流 → 打开各流组件（创建解码线程）
- **主循环**：读取 packet → 按 stream_index 分发到对应的 PacketQueue
- **背压控制**：当队列满（>15MB 或各队列充足）时暂停读取
- **Seek 处理**：执行 avformat_seek_file → flush 各队列（serial++）→ 重置 EOF 状态
- **EOF 处理**：发送 null packet 通知解码器输出剩余帧
- **stream_component_open**：创建解码器上下文 → 打开解码器 → 初始化 Decoder → 启动解码线程

数据流在 read_thread 中的走向清晰明了：`文件/网络 → av_read_frame() → 按类型分发到 audioq/videoq/subtitleq`。下一篇我们将跟随数据流，深入解码器内部，看看 packet 是如何被解码为可播放的帧的。
