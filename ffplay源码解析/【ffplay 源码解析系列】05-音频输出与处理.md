# ffplay 源码解析系列（五）：音频输出与处理

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 音频输出是播放器最基础的能力。本篇将深入分析 ffplay 如何打开 SDL 音频设备、如何通过回调机制驱动音频数据流、以及重采样和音量控制的实现细节。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 概述

在前几篇中，我们已经了解了 ffplay 的解复用（read_thread）和解码（audio_thread）流程。解码后的音频帧被放入 `sampq`（FrameQueue），但这只是完成了数据准备。真正让声音从扬声器播出，还需要经历以下环节：

1. **打开音频设备**：`audio_open()` 配置 SDL 音频参数并注册回调
2. **SDL 音频回调**：`sdl_audio_callback()` 被 SDL 音频线程周期性调用
3. **获取解码帧并重采样**：`audio_decode_frame()` 从 sampq 取帧，必要时进行格式转换
4. **音量控制**：`update_volume()` 基于 dB 对数映射调节音量
5. **音频时钟更新**：为音视频同步提供时间基准

音频输出的完整数据流如下图所示：

![音频输出完整数据流](https://gitee.com/yuhong1234/ffplay/raw/master/05-audio-data-flow.png)

## 2. audio_open()：SDL 音频设备配置与参数协商

`audio_open()` 在 `stream_component_open()` 中被调用，负责打开 SDL 音频设备。它的核心任务是：将解码器输出的音频参数（采样率、声道数）传递给 SDL，协商出硬件实际支持的参数。

### 2.1 函数签名与调用时机

```c
// 在 stream_component_open() 中调用
// ch_layout 和 sample_rate 来自音频滤镜链的输出端
if ((ret = audio_open(is, &ch_layout, sample_rate, &is->audio_tgt)) < 0)
    goto fail;
is->audio_hw_buf_size = ret;   // 返回值是硬件缓冲区大小
is->audio_src = is->audio_tgt; // 初始化源格式 = 目标格式（后续可能变化）
```

### 2.2 SDL_AudioSpec 参数设置

```c
static int audio_open(void *opaque, AVChannelLayout *wanted_channel_layout,
                      int wanted_sample_rate, struct AudioParams *audio_hw_params)
{
    SDL_AudioSpec wanted_spec, spec;
    const char *env;
    // 声道降级表：当某个声道数打开失败时，尝试降级到的声道数
    static const int next_nb_channels[] = {0, 0, 1, 6, 2, 6, 4, 6};
    // 采样率降级表：当所有声道数都失败时，尝试降级采样率
    static const int next_sample_rates[] = {0, 44100, 48000, 96000, 192000};
    int next_sample_rate_idx = FF_ARRAY_ELEMS(next_sample_rates) - 1;
    int wanted_nb_channels = wanted_channel_layout->nb_channels;

    // 环境变量覆盖声道数
    env = SDL_getenv("SDL_AUDIO_CHANNELS");
    if (env) {
        wanted_nb_channels = atoi(env);
        av_channel_layout_uninit(wanted_channel_layout);
        av_channel_layout_default(wanted_channel_layout, wanted_nb_channels);
    }
    // 非原生声道布局时，回退到默认布局
    if (wanted_channel_layout->order != AV_CHANNEL_ORDER_NATIVE) {
        av_channel_layout_uninit(wanted_channel_layout);
        av_channel_layout_default(wanted_channel_layout, wanted_nb_channels);
    }

    wanted_nb_channels = wanted_channel_layout->nb_channels;
    wanted_spec.channels = wanted_nb_channels;
    wanted_spec.freq = wanted_sample_rate;
    if (wanted_spec.freq <= 0 || wanted_spec.channels <= 0) {
        av_log(NULL, AV_LOG_ERROR, "Invalid sample rate or channel count!\n");
        return -1;
    }

    // 定位当前采样率在降级表中的位置
    while (next_sample_rate_idx && next_sample_rates[next_sample_rate_idx] >= wanted_spec.freq)
        next_sample_rate_idx--;

    // 固定使用 S16SYS（16位有符号整数，系统字节序）
    wanted_spec.format = AUDIO_S16SYS;
    wanted_spec.silence = 0;
    // 计算缓冲区大小：保证回调频率不超过 30 次/秒，且不小于 512 样本
    wanted_spec.samples = FFMAX(SDL_AUDIO_MIN_BUFFER_SIZE,
                                2 << av_log2(wanted_spec.freq / SDL_AUDIO_MAX_CALLBACKS_PER_SEC));
    // 🔑 注册音频回调函数
    wanted_spec.callback = sdl_audio_callback;
    wanted_spec.userdata = opaque;
    // ...
```

几个关键设计点：

- **固定 AUDIO_S16SYS 格式**：ffplay 强制使用 16 位有符号整数格式，简化了后续处理逻辑
- **缓冲区大小计算**：`2 << av_log2(freq / 30)` 确保缓冲区是 2 的幂，且回调频率约 30Hz（每秒约 30 次回调）
- **回调函数注册**：`sdl_audio_callback` 将在 SDL 的音频线程中被调用

### 2.3 声道数/采样率的降级策略

当 `SDL_OpenAudioDevice()` 失败时，ffplay 并不直接报错退出，而是按照预设的降级策略逐步尝试：

```c
    // 循环尝试打开音频设备
    while (!(audio_dev = SDL_OpenAudioDevice(NULL, 0, &wanted_spec, &spec,
                SDL_AUDIO_ALLOW_FREQUENCY_CHANGE | SDL_AUDIO_ALLOW_CHANNELS_CHANGE))) {
        av_log(NULL, AV_LOG_WARNING, "SDL_OpenAudio (%d channels, %d Hz): %s\n",
               wanted_spec.channels, wanted_spec.freq, SDL_GetError());
        // 第一步：降级声道数（按 next_nb_channels 表）
        wanted_spec.channels = next_nb_channels[FFMIN(7, wanted_spec.channels)];
        if (!wanted_spec.channels) {
            // 第二步：声道数用尽，降级采样率，重置声道数
            wanted_spec.freq = next_sample_rates[next_sample_rate_idx--];
            wanted_spec.channels = wanted_nb_channels;
            if (!wanted_spec.freq) {
                av_log(NULL, AV_LOG_ERROR,
                       "No more combinations to try, audio open failed\n");
                return -1;
            }
        }
        av_channel_layout_default(wanted_channel_layout, wanted_spec.channels);
    }
```

降级策略的核心思路：

| 原始声道数 | 降级到 | 说明 |
|-----------|--------|------|
| 7 | 6 | 7.0 降到 5.1 |
| 6 | 4 | 5.1 降到 4.0 |
| 5 | 6 | 尝试 5.1（某些硬件更友好） |
| 4 | 2 | 4.0 降到立体声 |
| 3 | 6 | 尝试 5.1 |
| 2 | 1 | 立体声降到单声道 |
| 1 | 0 | 单声道失败，触发采样率降级 |

当声道数降到 0 时，说明当前采样率下所有声道数都无法打开。此时切换到下一个较低的采样率（192000 -> 96000 -> 48000 -> 44100），并重置声道数重新尝试。

### 2.4 记录硬件参数

```c
    // 验证 SDL 实际返回的格式
    if (spec.format != AUDIO_S16SYS) {
        av_log(NULL, AV_LOG_ERROR,
               "SDL advised audio format %d is not supported!\n", spec.format);
        return -1;
    }
    // 如果 SDL 实际返回的声道数与请求不同，更新声道布局
    if (spec.channels != wanted_spec.channels) {
        av_channel_layout_uninit(wanted_channel_layout);
        av_channel_layout_default(wanted_channel_layout, spec.channels);
        if (wanted_channel_layout->order != AV_CHANNEL_ORDER_NATIVE) {
            av_log(NULL, AV_LOG_ERROR,
                   "SDL advised channel count %d is not supported!\n", spec.channels);
            return -1;
        }
    }

    // 🔑 记录硬件实际参数到 audio_hw_params（即 is->audio_tgt）
    audio_hw_params->fmt = AV_SAMPLE_FMT_S16;
    audio_hw_params->freq = spec.freq;
    av_channel_layout_copy(&audio_hw_params->ch_layout, wanted_channel_layout);
    // 计算每帧大小和每秒字节数（用于后续音频时钟计算）
    audio_hw_params->frame_size = av_samples_get_buffer_size(NULL,
        audio_hw_params->ch_layout.nb_channels, 1, audio_hw_params->fmt, 1);
    audio_hw_params->bytes_per_sec = av_samples_get_buffer_size(NULL,
        audio_hw_params->ch_layout.nb_channels, audio_hw_params->freq,
        audio_hw_params->fmt, 1);

    return spec.size; // 返回硬件缓冲区大小（字节）
}
```

`audio_open()` 的返回值 `spec.size` 被存入 `is->audio_hw_buf_size`，这个值在后续音频时钟计算中至关重要——它表示硬件缓冲区中已有但尚未播放的数据量。

## 3. sdl_audio_callback()：SDL 音频回调机制

`sdl_audio_callback()` 是整个音频输出管线的核心驱动函数。它**不是**由 ffplay 主动调用的，而是由 SDL 的音频线程周期性调用。每次调用时，SDL 要求回调函数填充指定长度的音频数据。

### 3.1 回调函数总体结构

```c
static void sdl_audio_callback(void *opaque, Uint8 *stream, int len)
{
    VideoState *is = opaque;
    int audio_size, len1;

    // 记录回调时间（用于音频时钟校正）
    audio_callback_time = av_gettime_relative();

    while (len > 0) {
        // 当前缓冲区已耗尽，需要获取新的解码数据
        if (is->audio_buf_index >= is->audio_buf_size) {
           audio_size = audio_decode_frame(is);
           if (audio_size < 0) {
                // 获取失败，输出静音
               is->audio_buf = NULL;
               is->audio_buf_size = SDL_AUDIO_MIN_BUFFER_SIZE /
                   is->audio_tgt.frame_size * is->audio_tgt.frame_size;
           } else {
               // 非视频模式下更新波形显示数据
               if (is->show_mode != SHOW_MODE_VIDEO)
                   update_sample_display(is, (int16_t *)is->audio_buf, audio_size);
               is->audio_buf_size = audio_size;
           }
           is->audio_buf_index = 0;
        }

        // 计算本次可拷贝的数据量
        len1 = is->audio_buf_size - is->audio_buf_index;
        if (len1 > len)
            len1 = len;

        // 🔑 音量控制与数据输出
        if (!is->muted && is->audio_buf && is->audio_volume == SDL_MIX_MAXVOLUME)
            // 最大音量：直接拷贝（零开销）
            memcpy(stream, (uint8_t *)is->audio_buf + is->audio_buf_index, len1);
        else {
            // 非最大音量或静音：先清零，再混音
            memset(stream, 0, len1);
            if (!is->muted && is->audio_buf)
                SDL_MixAudioFormat(stream,
                    (uint8_t *)is->audio_buf + is->audio_buf_index,
                    AUDIO_S16SYS, len1, is->audio_volume);
        }

        len -= len1;
        stream += len1;
        is->audio_buf_index += len1;
    }

    // 记录未播放的数据量（用于音频时钟校正）
    is->audio_write_buf_size = is->audio_buf_size - is->audio_buf_index;

    // 🔑 更新音频时钟
    if (!isnan(is->audio_clock)) {
        set_clock_at(&is->audclk,
            is->audio_clock - (double)(2 * is->audio_hw_buf_size + is->audio_write_buf_size)
                / is->audio_tgt.bytes_per_sec,
            is->audio_clock_serial,
            audio_callback_time / 1000000.0);
        sync_clock_to_slave(&is->extclk, &is->audclk);
    }
}
```

![sdl_audio_callback 工作流程](https://gitee.com/yuhong1234/ffplay/raw/master/05-sdl-audio-callback.png)

### 3.2 数据填充逻辑

回调的核心是一个 `while (len > 0)` 循环，它的工作模式类似"消费者"：

1. **检查缓冲区**：如果 `audio_buf_index >= audio_buf_size`，说明上一帧数据已耗尽
2. **获取新帧**：调用 `audio_decode_frame()` 获取一帧解码（并可能重采样）后的数据
3. **拷贝数据**：将数据从 `audio_buf` 拷贝到 SDL 提供的 `stream` 缓冲区
4. **重复**：直到填满 SDL 要求的 `len` 字节

这种设计意味着一次回调可能跨越多个解码帧。当一帧数据不足以填满 SDL 缓冲区时，会继续获取下一帧。

### 3.3 音量控制（SDL_MixAudioFormat）

音量控制有三条路径：

| 条件 | 处理方式 | 说明 |
|------|---------|------|
| 静音 或 audio_buf 为空 | `memset(stream, 0, len1)` | 输出纯静音 |
| 非静音 且 最大音量 | `memcpy(stream, ...)` | 直接拷贝，零开销 |
| 非静音 且 非最大音量 | `memset` + `SDL_MixAudioFormat` | 先清零，再按音量比例混合 |

最大音量时走 `memcpy` 是一个性能优化：避免了不必要的乘法运算。

### 3.4 音频时钟更新

回调结束时更新音频时钟，这个时钟是音视频同步的核心参考：

```c
set_clock_at(&is->audclk,
    is->audio_clock - (double)(2 * is->audio_hw_buf_size + is->audio_write_buf_size)
        / is->audio_tgt.bytes_per_sec,
    is->audio_clock_serial,
    audio_callback_time / 1000000.0);
```

这里有一个精妙的校正：`is->audio_clock` 是最后一帧解码数据的 PTS（播放结束时间），但实际播放位置要减去**尚未播放的数据量**：

- `2 * is->audio_hw_buf_size`：假设 SDL 使用双缓冲，两个硬件缓冲区中的数据
- `is->audio_write_buf_size`：当前软件缓冲区中剩余未拷贝的数据

这个校正确保了音频时钟尽可能准确地反映当前正在"听到"的音频位置。

## 4. audio_decode_frame()：音频帧获取与重采样

`audio_decode_frame()` 是回调链中最复杂的函数，承担了从 FrameQueue 获取帧、格式转换、重采样等多重职责。

### 4.1 从 FrameQueue 获取帧

```c
static int audio_decode_frame(VideoState *is)
{
    int data_size, resampled_data_size;
    int wanted_nb_samples;
    Frame *af;

    // 暂停状态直接返回，输出静音
    if (is->paused)
        return -1;

    do {
        // 从 sampq 获取一帧（阻塞等待）
        if (!(af = frame_queue_peek_readable(&is->sampq)))
            return -1;
        frame_queue_next(&is->sampq);
    } while (af->serial != is->audioq.serial);
    // 🔑 serial 检查：跳过 Seek 前的旧帧
    // 如果帧的 serial 与当前队列 serial 不匹配，说明是 Seek 前的残留数据，丢弃
```

`do...while` 循环配合 `serial` 检查是 ffplay Seek 机制的重要环节。当用户 Seek 时，PacketQueue 的 serial 会递增，但 FrameQueue 中可能还残留着旧 serial 的帧。通过这个循环，回调函数会跳过所有旧帧，直到找到与当前 serial 匹配的帧。

### 4.2 音频同步补偿

```c
    // 计算原始数据大小
    data_size = av_samples_get_buffer_size(NULL, af->frame->ch_layout.nb_channels,
                                           af->frame->nb_samples,
                                           af->frame->format, 1);

    // 获取同步补偿后的样本数
    wanted_nb_samples = synchronize_audio(is, af->frame->nb_samples);
```

`synchronize_audio()` 是音频同步的核心函数。当音频不是主时钟时（如以视频为主时钟），它会计算音频时钟与主时钟的差值，并调整样本数来"追赶"或"等待"：

```c
static int synchronize_audio(VideoState *is, int nb_samples)
{
    int wanted_nb_samples = nb_samples;

    // 仅当音频不是主时钟时才做补偿
    if (get_master_sync_type(is) != AV_SYNC_AUDIO_MASTER) {
        double diff, avg_diff;
        int min_nb_samples, max_nb_samples;

        // 计算音频时钟与主时钟的差值
        diff = get_clock(&is->audclk) - get_master_clock(is);

        if (!isnan(diff) && fabs(diff) < AV_NOSYNC_THRESHOLD) {
            // 使用加权移动平均平滑差值
            is->audio_diff_cum = diff + is->audio_diff_avg_coef * is->audio_diff_cum;
            if (is->audio_diff_avg_count < AUDIO_DIFF_AVG_NB) {
                is->audio_diff_avg_count++;  // 积累足够样本
            } else {
                avg_diff = is->audio_diff_cum * (1.0 - is->audio_diff_avg_coef);
                if (fabs(avg_diff) >= is->audio_diff_threshold) {
                    // 调整样本数：加速（减少样本）或减速（增加样本）
                    wanted_nb_samples = nb_samples + (int)(diff * is->audio_src.freq);
                    // 限制调整幅度不超过 +-10%
                    min_nb_samples = nb_samples * (100 - SAMPLE_CORRECTION_PERCENT_MAX) / 100;
                    max_nb_samples = nb_samples * (100 + SAMPLE_CORRECTION_PERCENT_MAX) / 100;
                    wanted_nb_samples = av_clip(wanted_nb_samples, min_nb_samples, max_nb_samples);
                }
            }
        } else {
            // 差值过大，重置滤波器
            is->audio_diff_avg_count = 0;
            is->audio_diff_cum = 0;
        }
    }

    return wanted_nb_samples;
}
```

补偿的关键设计：

- **加权移动平均**：避免因瞬时波动而频繁调整，`audio_diff_avg_coef = exp(log(0.01) / 20) ≈ 0.794`
- **阈值控制**：只有平均差值超过阈值（硬件缓冲区时长）才做调整
- **幅度限制**：调整不超过 +-10%，避免用户感知到明显的音调变化
- **超阈值重置**：差值超过 `AV_NOSYNC_THRESHOLD`（10秒）时放弃同步，重新积累

### 4.3 SwrContext 重采样

当解码帧的格式与 SDL 硬件期望的格式不一致时，需要通过 SwrContext 进行重采样：

```c
    // 检查是否需要重采样
    if (af->frame->format        != is->audio_src.fmt            ||
        av_channel_layout_compare(&af->frame->ch_layout, &is->audio_src.ch_layout) ||
        af->frame->sample_rate   != is->audio_src.freq           ||
        (wanted_nb_samples       != af->frame->nb_samples && !is->swr_ctx)) {
        // 格式/声道/采样率变化 或 需要补偿但还没有 swr_ctx → 重新创建
        swr_free(&is->swr_ctx);
        ret = swr_alloc_set_opts2(&is->swr_ctx,
                    &is->audio_tgt.ch_layout, is->audio_tgt.fmt, is->audio_tgt.freq,   // 目标：SDL 硬件格式
                    &af->frame->ch_layout, af->frame->format, af->frame->sample_rate,  // 源：解码帧格式
                    0, NULL);
        if (ret < 0 || swr_init(is->swr_ctx) < 0) {
            av_log(NULL, AV_LOG_ERROR,
                   "Cannot create sample rate converter for conversion of %d Hz %s %d channels "
                   "to %d Hz %s %d channels!\n",
                    af->frame->sample_rate, av_get_sample_fmt_name(af->frame->format),
                    af->frame->ch_layout.nb_channels,
                    is->audio_tgt.freq, av_get_sample_fmt_name(is->audio_tgt.fmt),
                    is->audio_tgt.ch_layout.nb_channels);
            swr_free(&is->swr_ctx);
            return -1;
        }
        // 更新源格式记录
        av_channel_layout_copy(&is->audio_src.ch_layout, &af->frame->ch_layout);
        is->audio_src.freq = af->frame->sample_rate;
        is->audio_src.fmt = af->frame->format;
    }
```

`audio_src` 记录了上一次的源格式。只有当格式发生变化时才重新创建 SwrContext，避免了每帧都重新初始化的开销。

### 4.4 执行重采样与补偿

```c
    if (is->swr_ctx) {
        const uint8_t **in = (const uint8_t **)af->frame->extended_data;
        uint8_t **out = &is->audio_buf1;
        int out_count = (int64_t)wanted_nb_samples * is->audio_tgt.freq /
                        af->frame->sample_rate + 256;
        int out_size = av_samples_get_buffer_size(NULL,
            is->audio_tgt.ch_layout.nb_channels, out_count, is->audio_tgt.fmt, 0);

        // 如果需要补偿（wanted_nb_samples != 原始样本数）
        if (wanted_nb_samples != af->frame->nb_samples) {
            // 设置补偿参数：让 swr_convert 通过插值/丢弃来调整样本数
            swr_set_compensation(is->swr_ctx,
                (wanted_nb_samples - af->frame->nb_samples)
                    * is->audio_tgt.freq / af->frame->sample_rate,
                wanted_nb_samples * is->audio_tgt.freq / af->frame->sample_rate);
        }

        // 分配输出缓冲区
        av_fast_malloc(&is->audio_buf1, &is->audio_buf1_size, out_size);

        // 🔑 执行重采样
        len2 = swr_convert(is->swr_ctx, out, out_count, in, af->frame->nb_samples);

        if (len2 == out_count) {
            av_log(NULL, AV_LOG_WARNING, "audio buffer is probably too small\n");
            if (swr_init(is->swr_ctx) < 0)
                swr_free(&is->swr_ctx);
        }
        is->audio_buf = is->audio_buf1;
        resampled_data_size = len2 * is->audio_tgt.ch_layout.nb_channels
                            * av_get_bytes_per_sample(is->audio_tgt.fmt);
    } else {
        // 无需重采样：直接使用解码帧数据
        is->audio_buf = af->frame->data[0];
        resampled_data_size = data_size;
    }
```

`swr_set_compensation()` 的补偿机制是音频同步的硬件层实现：

- `compensation_distance`：补偿量（正值表示增加样本/减速，负值表示减少样本/加速）
- `sample_delta`：在多少样本内完成补偿

这种方式比简单丢弃/重复样本更平滑，因为 `swr_convert` 会通过插值算法来实现样本数的调整。

### 4.5 更新音频时钟

```c
    // 更新音频时钟 PTS
    if (!isnan(af->pts))
        is->audio_clock = af->pts + (double)af->frame->nb_samples / af->frame->sample_rate;
    else
        is->audio_clock = NAN;
    is->audio_clock_serial = af->serial;

    return resampled_data_size;
}
```

`audio_clock` 被设为当前帧的 PTS 加上帧时长，即这帧**播放完成后**的时间点。这个值会在 `sdl_audio_callback()` 中被校正（减去未播放的缓冲区时长），得到当前实际播放位置。

## 5. update_volume()：音量控制

ffplay 的音量控制使用了 dB（分贝）对数映射，这符合人耳对响度的感知特性：

```c
static void update_volume(VideoState *is, int sign, double step)
{
    // 1. 将当前线性音量转换为 dB 值
    //    公式：dB = 20 * log10(volume / max_volume)
    double volume_level = is->audio_volume ?
        (20 * log(is->audio_volume / (double)SDL_MIX_MAXVOLUME) / log(10)) : -1000.0;

    // 2. 在 dB 域上加减步长
    // 3. 转回线性值
    //    公式：volume = max_volume * 10^(dB / 20)
    int new_volume = lrint(SDL_MIX_MAXVOLUME * pow(10.0, (volume_level + sign * step) / 20.0));

    // 4. 限幅并处理边界
    is->audio_volume = av_clip(
        is->audio_volume == new_volume ? (is->audio_volume + sign) : new_volume,
        0, SDL_MIX_MAXVOLUME);
}
```

dB 映射的优点：

- **符合人耳感知**：人耳对响度的感知是对数关系，线性调节会导致低音量区变化不敏感、高音量区变化过剧烈
- **步长均匀**：在 dB 域上等步长调节，每次调节带来的主观响度变化一致
- **边界处理**：当计算结果没有变化时（精度限制），强制加减 1，避免"卡住"

用户通过键盘 `0`/`9` 键触发 `update_volume()`，默认步长为 `SDL_VOLUME_STEP`（0.75 dB）。

## 6. 音频输出数据流总结

从解码到最终输出，音频数据经历以下完整路径：

```
PacketQueue (audioq)
    |
    v
audio_thread:  decoder_decode_frame() → 解码得到 AVFrame
    |
    v
audio_thread:  音频滤镜链处理（如有）
    |
    v
FrameQueue (sampq)
    |
    v
sdl_audio_callback:  audio_decode_frame() 从 sampq 取帧
    |
    v
audio_decode_frame:  synchronize_audio() 计算补偿样本数
    |
    v
audio_decode_frame:  swr_convert() 重采样（格式/采样率/声道转换）
    |
    v
sdl_audio_callback:  音量控制（memcpy 或 SDL_MixAudioFormat）
    |
    v
SDL 音频设备 → 扬声器
```

各环节中涉及的关键缓冲区和状态变量：

| 变量 | 含义 |
|------|------|
| `is->audio_buf` | 当前可用的 PCM 数据指针 |
| `is->audio_buf_size` | 当前缓冲区总大小（字节） |
| `is->audio_buf_index` | 当前已消费的偏移量 |
| `is->audio_buf1` | 重采样输出缓冲区（av_fast_malloc 管理） |
| `is->audio_hw_buf_size` | SDL 硬件缓冲区大小 |
| `is->audio_write_buf_size` | 软件缓冲区中剩余未拷贝的数据量 |
| `is->audio_src` | 上一次源格式（用于检测格式变化） |
| `is->audio_tgt` | SDL 硬件目标格式 |
| `is->audio_clock` | 音频时钟 PTS |
| `is->audio_volume` | 当前音量（0 到 SDL_MIX_MAXVOLUME） |

## 7. 小结

本篇详细分析了 ffplay 的音频输出与处理管线，核心要点：

- **audio_open()**：配置 SDL 音频设备，采用声道数优先、采样率其次的降级策略，确保在各种硬件环境下都能正常打开音频设备
- **sdl_audio_callback()**：由 SDL 音频线程驱动，是"拉"模型的核心——SDL 需要数据时才会调用，而非 ffplay 主动推送
- **audio_decode_frame()**：承担帧获取、serial 过滤、音频同步补偿、格式转换（SwrContext 重采样）等多重职责
- **音频时钟更新**：考虑了硬件双缓冲和软件缓冲的延迟，精确校正播放位置
- **update_volume()**：基于 dB 对数映射实现符合人耳感知的音量调节

音频输出采用的是**"拉"模型**：SDL 音频线程按固定节奏回调 → 回调从 FrameQueue 取帧 → 必要时重采样 → 填充到 SDL 缓冲区。这种模型的优点是天然地控制了数据消费速度，音频播放速度由硬件采样率决定，这也是为什么音频时钟通常是最稳定的同步源。
