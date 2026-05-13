# ffplay 源码解析系列（十一）：事件处理与用户交互（收官篇）

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 本篇是系列收官篇。一个播放器不仅要能播，还要能"用"——暂停、快进、调音量、切流、全屏，这些交互能力赋予播放器灵魂。本篇将完整剖析 ffplay 的事件处理机制：从事件主循环到每一个按键响应，从 seek 请求到资源清理的全流程。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. event_loop：事件主循环

在第一篇中我们分析过 `main()` 函数的最后一行：

```c
event_loop(is);

/* never returns */
```

`main()` 在完成所有初始化（SDL、窗口、渲染器创建）和调用 `stream_open()` 启动播放后，将**主线程的控制权永久移交**给 `event_loop()`。这是一个典型的**事件驱动主循环**，永不返回。

### 1.1 主循环结构

`event_loop()` 的整体结构非常清晰（ffplay.c 行 3352-3548）：

```c
static void event_loop(VideoState *cur_stream)
{
    SDL_Event event;
    double incr, pos, frac;

    for (;;) {  // 无限循环，永不退出
        double x;
        // 🔑 等待事件（同时驱动视频渲染）
        refresh_loop_wait_event(cur_stream, &event);

        // 根据事件类型分发处理
        switch (event.type) {
        case SDL_KEYDOWN:       // 键盘按下
            // ...
            break;
        case SDL_MOUSEBUTTONDOWN: // 鼠标按下
            // ...
        case SDL_MOUSEMOTION:   // 鼠标移动（注意：故意没有 break，fall-through）
            // ...
            break;
        case SDL_WINDOWEVENT:   // 窗口事件（大小变化、曝光）
            // ...
            break;
        case SDL_QUIT:          // 窗口关闭按钮
        case FF_QUIT_EVENT:     // 自定义退出事件
            do_exit(cur_stream);
            break;
        default:
            break;
        }
    }
}
```

这里有一个关键设计：**主线程既是事件处理者，也是视频渲染的驱动者**。在没有用户事件的时候，`refresh_loop_wait_event()` 会利用等待间隙驱动 `video_refresh()` 进行视频帧的显示。

![event_loop 与 video_refresh 协作关系](https://gitee.com/yuhong1234/ffplay/raw/master/11-event-loop.png)

## 2. refresh_loop_wait_event：刷新等待机制

这是 ffplay 中最精巧的设计之一——在等待用户事件的同时，以稳定的频率驱动视频渲染（ffplay.c 行 3308-3323）：

```c
static void refresh_loop_wait_event(VideoState *is, SDL_Event *event) {
    double remaining_time = 0.0;
    SDL_PumpEvents();  // 将系统事件泵入 SDL 事件队列
    // 循环：直到取到一个事件为止
    while (!SDL_PeepEvents(event, 1, SDL_GETEVENT, SDL_FIRSTEVENT, SDL_LASTEVENT)) {
        // 自动隐藏鼠标光标（1 秒无操作后隐藏）
        if (!cursor_hidden && av_gettime_relative() - cursor_last_shown > CURSOR_HIDE_DELAY) {
            SDL_ShowCursor(0);
            cursor_hidden = 1;
        }
        // 精确睡眠：不超过 remaining_time
        if (remaining_time > 0.0)
            av_usleep((int64_t)(remaining_time * 1000000.0));
        // 重置为最大刷新间隔 10ms
        remaining_time = REFRESH_RATE;  // REFRESH_RATE = 0.01 (10ms)
        // 🔑 驱动视频渲染（video_refresh 可能会缩短 remaining_time）
        if (is->show_mode != SHOW_MODE_NONE && (!is->paused || is->force_refresh))
            video_refresh(is, &remaining_time);
        SDL_PumpEvents();  // 再次泵入事件
    }
}
```

### 2.1 工作流程详解

这段代码的核心思想是 **"用等待事件的空闲时间来驱动视频渲染"**：

1. **`SDL_PumpEvents()`**：将操作系统的原始事件（键盘、鼠标、窗口消息）收集到 SDL 内部队列
2. **`SDL_PeepEvents()`**：从 SDL 队列中非阻塞地取一个事件。取到返回 1，否则返回 0
3. **取不到事件时**：执行循环体——先睡眠 `remaining_time`，再调用 `video_refresh()` 渲染一帧
4. **`video_refresh()`** 在内部会根据下一帧的目标显示时间，将 `remaining_time` 修改为更精确的等待时间
5. **取到事件后**：跳出循环，返回给 `event_loop()` 分发处理

### 2.2 为什么不用 SDL_WaitEvent？

SDL 提供了阻塞式的 `SDL_WaitEvent()`，但 ffplay 不能用它——因为阻塞等待期间无法刷新视频画面。使用 `PumpEvents + PeepEvents` 的组合，可以在**非阻塞轮询事件**的间隙，以约 10ms 的周期驱动视频输出。

### 2.3 鼠标光标自动隐藏

```c
#define CURSOR_HIDE_DELAY 1000000  // 1秒 = 1000000微秒
```

在每次循环中检查：如果距离上次鼠标活动已超过 1 秒，就调用 `SDL_ShowCursor(0)` 隐藏光标。当鼠标再次移动时（`SDL_MOUSEMOTION` 事件），会恢复显示并重置计时：

```c
case SDL_MOUSEMOTION:
    if (cursor_hidden) {
        SDL_ShowCursor(1);
        cursor_hidden = 0;
    }
    cursor_last_shown = av_gettime_relative();
```

## 3. 键盘事件处理

键盘事件是 ffplay 交互功能的核心。`SDL_KEYDOWN` 事件到来后，通过嵌套的 `switch` 语句分发到各个处理函数。

### 3.1 完整键盘映射表

| 按键 | 功能 | 处理函数/操作 |
|------|------|-------------|
| ESC / Q | 退出播放器 | `do_exit()` |
| F | 全屏切换 | `toggle_full_screen()` |
| P / Space | 暂停/恢复 | `toggle_pause()` |
| M | 静音切换 | `toggle_mute()` |
| 0 / * (小键盘) | 增大音量 | `update_volume(+1, 0.75dB)` |
| 9 / / (小键盘) | 减小音量 | `update_volume(-1, 0.75dB)` |
| S | 单帧步进 | `step_to_next_frame()` |
| A | 切换音频流 | `stream_cycle_channel(AUDIO)` |
| V | 切换视频流 | `stream_cycle_channel(VIDEO)` |
| T | 切换字幕流 | `stream_cycle_channel(SUBTITLE)` |
| C | 循环切换所有流 | 依次切换视频、音频、字幕 |
| W | 切换滤镜/显示模式 | 滤镜切换或 `toggle_audio_display()` |
| Left | 快退 10s（或自定义） | `stream_seek()` |
| Right | 快进 10s（或自定义） | `stream_seek()` |
| Up | 快进 60s | `stream_seek()` |
| Down | 快退 60s | `stream_seek()` |
| PageUp | 下一章节 / 快进 600s | `seek_chapter()` 或 `stream_seek()` |
| PageDown | 上一章节 / 快退 600s | `seek_chapter()` 或 `stream_seek()` |

### 3.2 退出处理

```c
case SDL_KEYDOWN:
    if (exit_on_keydown || event.key.keysym.sym == SDLK_ESCAPE
                        || event.key.keysym.sym == SDLK_q) {
        do_exit(cur_stream);
        break;
    }
    // 窗口尚未创建时忽略其他按键
    if (!cur_stream->width)
        continue;
```

注意 `exit_on_keydown` 选项——如果启用，**任意按键**都会退出。`!cur_stream->width` 判断是一个保护：在 `read_thread` 还在初始化、尚未创建窗口时，跳过除退出外的所有键盘处理。

### 3.3 暂停与恢复：toggle_pause / stream_toggle_pause

按下 P 或 Space 触发暂停：

```c
static void toggle_pause(VideoState *is)
{
    stream_toggle_pause(is);
    is->step = 0;  // 清除单帧步进标志
}
```

核心在 `stream_toggle_pause()`（ffplay.c 行 1497-1508）：

```c
static void stream_toggle_pause(VideoState *is)
{
    if (is->paused) {
        // 从暂停恢复：补偿 frame_timer
        // 暂停期间时间流逝了，但视频帧没有推进，所以要把 frame_timer 往前推
        is->frame_timer += av_gettime_relative() / 1000000.0 - is->vidclk.last_updated;
        if (is->read_pause_return != AVERROR(ENOSYS)) {
            is->vidclk.paused = 0;
        }
        // 重新设置视频时钟（让时钟"追上"当前时间）
        set_clock(&is->vidclk, get_clock(&is->vidclk), is->vidclk.serial);
    }
    // 设置外部时钟
    set_clock(&is->extclk, get_clock(&is->extclk), is->extclk.serial);
    // 🔑 三个时钟同步切换暂停状态
    is->paused = is->audclk.paused = is->vidclk.paused = is->extclk.paused = !is->paused;
}
```

这里 `frame_timer` 补偿是关键：暂停期间墙上时钟在走但视频没推进，恢复后需要把 `frame_timer` 加上这段暂停时间，否则 `video_refresh` 会认为大量帧超时需要丢弃。

### 3.4 静音切换

```c
static void toggle_mute(VideoState *is)
{
    is->muted = !is->muted;
}
```

简单地翻转 `muted` 标志。在音频回调 `sdl_audio_callback()` 中会检查此标志，静音时输出全零数据。

### 3.5 音量调节：update_volume

```c
#define SDL_VOLUME_STEP (0.75)  // 每步 0.75 dB

static void update_volume(VideoState *is, int sign, double step)
{
    // 将当前线性音量转换为 dB 值
    double volume_level = is->audio_volume
        ? (20 * log(is->audio_volume / (double)SDL_MIX_MAXVOLUME) / log(10))
        : -1000.0;
    // 在 dB 域加减 step，再转回线性值
    int new_volume = lrint(SDL_MIX_MAXVOLUME * pow(10.0, (volume_level + sign * step) / 20.0));
    // 防止音量不变时的死循环，并 clamp 到 [0, SDL_MIX_MAXVOLUME]
    is->audio_volume = av_clip(
        is->audio_volume == new_volume ? (is->audio_volume + sign) : new_volume,
        0, SDL_MIX_MAXVOLUME);
}
```

为什么用 **dB 对数映射**而不是直接加减？因为人耳对音量的感知是对数的。线性增加 1 在小音量时变化巨大，在大音量时几乎无感。dB 域的等步长增减能提供**感知上均匀**的音量变化体验。

核心公式：
- 线性转 dB：`dB = 20 * log10(volume / max_volume)`
- dB 转线性：`volume = max_volume * 10^(dB / 20)`

### 3.6 单帧步进：step_to_next_frame

```c
static void step_to_next_frame(VideoState *is)
{
    // 如果当前是暂停状态，先恢复播放
    if (is->paused)
        stream_toggle_pause(is);
    is->step = 1;  // 设置单帧步进标志
}
```

设置 `step = 1` 后，`video_refresh()` 在显示完一帧后会检测到此标志，重新调用 `stream_toggle_pause()` 暂停。这样就实现了"播放一帧后立即暂停"的逐帧效果。

### 3.7 W 键：滤镜切换与显示模式

```c
case SDLK_w:
    if (cur_stream->show_mode == SHOW_MODE_VIDEO && cur_stream->vfilter_idx < nb_vfilters - 1) {
        // 在视频模式下，如果有多个滤镜，切换到下一个滤镜
        if (++cur_stream->vfilter_idx >= nb_vfilters)
            cur_stream->vfilter_idx = 0;
    } else {
        // 否则，切换显示模式（视频 -> 波形 -> 频谱 -> 视频）
        cur_stream->vfilter_idx = 0;
        toggle_audio_display(cur_stream);
    }
    break;
```

`toggle_audio_display()` 在 `SHOW_MODE_VIDEO`、`SHOW_MODE_WAVES`、`SHOW_MODE_RDFT` 之间循环切换：

```c
static void toggle_audio_display(VideoState *is)
{
    int next = is->show_mode;
    do {
        next = (next + 1) % SHOW_MODE_NB;
    } while (next != is->show_mode &&
            (next == SHOW_MODE_VIDEO && !is->video_st ||
             next != SHOW_MODE_VIDEO && !is->audio_st));
    if (is->show_mode != next) {
        is->force_refresh = 1;
        is->show_mode = next;
    }
}
```

循环跳过不可用的模式（无视频流时跳过视频模式，无音频流时跳过波形/频谱模式）。

### 3.8 方向键 Seek

Left/Right/Up/Down 四个方向键通过 `goto do_seek` 跳转到统一的 seek 处理逻辑：

```c
case SDLK_LEFT:
    incr = seek_interval ? -seek_interval : -10.0;
    goto do_seek;
case SDLK_RIGHT:
    incr = seek_interval ? seek_interval : 10.0;
    goto do_seek;
case SDLK_UP:
    incr = 60.0;
    goto do_seek;
case SDLK_DOWN:
    incr = -60.0;
do_seek:
    if (seek_by_bytes) {
        // 按字节 seek：将秒数转为字节偏移量
        pos = -1;
        if (pos < 0 && cur_stream->video_stream >= 0)
            pos = frame_queue_last_pos(&cur_stream->pictq);
        if (pos < 0 && cur_stream->audio_stream >= 0)
            pos = frame_queue_last_pos(&cur_stream->sampq);
        if (pos < 0)
            pos = avio_tell(cur_stream->ic->pb);
        if (cur_stream->ic->bit_rate)
            incr *= cur_stream->ic->bit_rate / 8.0;
        else
            incr *= 180000.0;
        pos += incr;
        stream_seek(cur_stream, pos, incr, 1);
    } else {
        // 按时间 seek（默认模式）
        pos = get_master_clock(cur_stream);
        if (isnan(pos))
            pos = (double)cur_stream->seek_pos / AV_TIME_BASE;
        pos += incr;
        // 防止 seek 到 start_time 之前
        if (cur_stream->ic->start_time != AV_NOPTS_VALUE
            && pos < cur_stream->ic->start_time / (double)AV_TIME_BASE)
            pos = cur_stream->ic->start_time / (double)AV_TIME_BASE;
        stream_seek(cur_stream, (int64_t)(pos * AV_TIME_BASE),
                    (int64_t)(incr * AV_TIME_BASE), 0);
    }
    break;
```

Left/Right 的 seek 间隔可通过 `-seek_interval` 命令行参数自定义（默认 10 秒）。

## 4. 鼠标事件处理

### 4.1 左键双击：全屏切换

```c
case SDL_MOUSEBUTTONDOWN:
    if (exit_on_mousedown) {
        do_exit(cur_stream);
        break;
    }
    if (event.button.button == SDL_BUTTON_LEFT) {
        static int64_t last_mouse_left_click = 0;
        // 500ms 内两次点击视为双击
        if (av_gettime_relative() - last_mouse_left_click <= 500000) {
            toggle_full_screen(cur_stream);
            cur_stream->force_refresh = 1;
            last_mouse_left_click = 0;
        } else {
            last_mouse_left_click = av_gettime_relative();
        }
    }
```

`toggle_full_screen()` 非常简洁：

```c
static void toggle_full_screen(VideoState *is)
{
    is_full_screen = !is_full_screen;
    SDL_SetWindowFullscreen(window, is_full_screen ? SDL_WINDOW_FULLSCREEN_DESKTOP : 0);
}
```

### 4.2 右键拖拽/点击：按比例 Seek

注意 `SDL_MOUSEBUTTONDOWN` 和 `SDL_MOUSEMOTION` 之间**故意没有 `break`**，使用 C 语言的 fall-through 特性：

```c
case SDL_MOUSEBUTTONDOWN:
    // ... 左键双击处理 ...
case SDL_MOUSEMOTION:   // fall-through from MOUSEBUTTONDOWN
    if (cursor_hidden) {
        SDL_ShowCursor(1);
        cursor_hidden = 0;
    }
    cursor_last_shown = av_gettime_relative();
    if (event.type == SDL_MOUSEBUTTONDOWN) {
        if (event.button.button != SDL_BUTTON_RIGHT)
            break;          // 非右键的按下事件到此结束
        x = event.button.x;
    } else {
        if (!(event.motion.state & SDL_BUTTON_RMASK))
            break;          // 非右键拖拽的移动事件到此结束
        x = event.motion.x;
    }
    // 计算 seek 目标位置
    if (seek_by_bytes || cur_stream->ic->duration <= 0) {
        uint64_t size = avio_size(cur_stream->ic->pb);
        stream_seek(cur_stream, size * x / cur_stream->width, 0, 1);
    } else {
        int64_t ts;
        int ns, hh, mm, ss;
        int tns, thh, tmm, tss;
        tns  = cur_stream->ic->duration / 1000000LL;
        thh  = tns / 3600;
        tmm  = (tns % 3600) / 60;
        tss  = (tns % 60);
        frac = x / cur_stream->width;  // 鼠标 x 坐标占窗口宽度的比例
        ns   = frac * tns;
        hh   = ns / 3600;
        mm   = (ns % 3600) / 60;
        ss   = (ns % 60);
        av_log(NULL, AV_LOG_INFO,
               "Seek to %2.0f%% (%2d:%02d:%02d) of total duration (%2d:%02d:%02d)\n",
               frac * 100, hh, mm, ss, thh, tmm, tss);
        ts = frac * cur_stream->ic->duration;
        if (cur_stream->ic->start_time != AV_NOPTS_VALUE)
            ts += cur_stream->ic->start_time;
        stream_seek(cur_stream, ts, 0, 0);
    }
    break;
```

核心逻辑：**鼠标 x 坐标 / 窗口宽度 = 目标位置占总时长的比例**。这是一种非常直观的 seek 方式——在窗口中点击越靠右，seek 的位置越靠后。

## 5. stream_seek：Seek 请求函数

所有 seek 操作最终都汇聚到 `stream_seek()`（ffplay.c 行 1482-1494）：

```c
static void stream_seek(VideoState *is, int64_t pos, int64_t rel, int by_bytes)
{
    if (!is->seek_req) {          // 只有没有待处理的 seek 请求时才接受新请求
        is->seek_pos = pos;       // 目标位置（AV_TIME_BASE 单位或字节）
        is->seek_rel = rel;       // 相对偏移量（用于计算 seek 范围）
        is->seek_flags &= ~AVSEEK_FLAG_BYTE;
        if (by_bytes)
            is->seek_flags |= AVSEEK_FLAG_BYTE;  // 按字节 seek
        is->seek_req = 1;         // 🔑 设置 seek 请求标志
        SDL_CondSignal(is->continue_read_thread);  // 唤醒 read_thread
    }
}
```

这个函数只是**提交 seek 请求**，不执行实际的 seek。实际的 seek 由 `read_thread` 在下一轮循环中处理。

### 5.1 read_thread 中的 Seek 处理

`read_thread` 在其主循环中检测 `seek_req` 标志（ffplay.c 行 3029-3058）：

```c
if (is->seek_req) {
    int64_t seek_target = is->seek_pos;
    int64_t seek_min    = is->seek_rel > 0 ? seek_target - is->seek_rel + 2 : INT64_MIN;
    int64_t seek_max    = is->seek_rel < 0 ? seek_target - is->seek_rel - 2 : INT64_MAX;

    // 调用 FFmpeg 的 seek API
    ret = avformat_seek_file(is->ic, -1, seek_min, seek_target, seek_max, is->seek_flags);
    if (ret < 0) {
        av_log(NULL, AV_LOG_ERROR, "%s: error while seeking\n", is->ic->url);
    } else {
        // 🔑 清空所有队列中的旧数据
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
    is->seek_req = 0;               // 清除 seek 请求标志
    is->queue_attachments_req = 1;   // 重新附加封面图
    is->eof = 0;                     // 清除 EOF 标志
    if (is->paused)
        step_to_next_frame(is);      // 暂停状态下 seek 后显示一帧
}
```

**Seek 操作的完整链路**：

1. 用户按键 / 鼠标操作
2. `event_loop()` 捕获事件
3. `stream_seek()` 设置请求参数并唤醒 `read_thread`
4. `read_thread` 调用 `avformat_seek_file()` 执行实际 seek
5. `packet_queue_flush()` 清空各队列的旧数据（同时推入 flush_pkt 递增 serial）
6. 解码器检测到 serial 变化，丢弃旧帧
7. 新位置的数据被读取、解码、渲染

![Seek 操作完整链路](https://gitee.com/yuhong1234/ffplay/raw/master/11-seek-flow.png)

## 6. stream_cycle_channel：流切换

按 A/V/T 键可以在同类型的多条流之间切换（ffplay.c 行 3211-3287）：

```c
static void stream_cycle_channel(VideoState *is, int codec_type)
{
    AVFormatContext *ic = is->ic;
    int start_index, stream_index;
    int old_index;
    AVStream *st;
    AVProgram *p = NULL;
    int nb_streams = is->ic->nb_streams;

    // 确定当前流索引和起始搜索位置
    if (codec_type == AVMEDIA_TYPE_VIDEO) {
        start_index = is->last_video_stream;
        old_index = is->video_stream;
    } else if (codec_type == AVMEDIA_TYPE_AUDIO) {
        start_index = is->last_audio_stream;
        old_index = is->audio_stream;
    } else {
        start_index = is->last_subtitle_stream;
        old_index = is->subtitle_stream;
    }
    stream_index = start_index;

    // 🔑 限制在同一 program 内搜索
    if (codec_type != AVMEDIA_TYPE_VIDEO && is->video_stream != -1) {
        p = av_find_program_from_stream(ic, NULL, is->video_stream);
        if (p) {
            nb_streams = p->nb_stream_indexes;
            for (start_index = 0; start_index < nb_streams; start_index++)
                if (p->stream_index[start_index] == stream_index)
                    break;
            if (start_index == nb_streams)
                start_index = -1;
            stream_index = start_index;
        }
    }

    // 循环查找下一个可用的同类型流
    for (;;) {
        if (++stream_index >= nb_streams) {
            if (codec_type == AVMEDIA_TYPE_SUBTITLE) {
                stream_index = -1;            // 字幕允许关闭（-1 表示无字幕）
                is->last_subtitle_stream = -1;
                goto the_end;
            }
            if (start_index == -1)
                return;
            stream_index = 0;   // 回绕到开头继续找
        }
        if (stream_index == start_index)
            return;             // 绕了一圈没找到，放弃
        st = is->ic->streams[p ? p->stream_index[stream_index] : stream_index];
        if (st->codecpar->codec_type == codec_type) {
            switch (codec_type) {
            case AVMEDIA_TYPE_AUDIO:
                if (st->codecpar->sample_rate != 0 &&
                    st->codecpar->ch_layout.nb_channels != 0)
                    goto the_end;   // 音频流需要有效的采样率和声道数
                break;
            case AVMEDIA_TYPE_VIDEO:
            case AVMEDIA_TYPE_SUBTITLE:
                goto the_end;
            default:
                break;
            }
        }
    }
 the_end:
    if (p && stream_index != -1)
        stream_index = p->stream_index[stream_index];
    av_log(NULL, AV_LOG_INFO, "Switch %s stream from #%d to #%d\n",
           av_get_media_type_string(codec_type), old_index, stream_index);

    // 🔑 先关闭旧流，再打开新流
    stream_component_close(is, old_index);
    stream_component_open(is, stream_index);
}
```

几个设计要点：

- **Program 约束**：在 MPEG-TS 等容器中，一个 program 包含一组相关的音视频流。切换音频/字幕时会限制在当前 program 内，避免切到无关流
- **字幕特殊性**：字幕流允许 `stream_index = -1`，即"关闭字幕"。音视频不允许关闭
- **关闭再打开**：通过 `stream_component_close()` 关闭旧流（停止解码线程、清空队列），再通过 `stream_component_open()` 打开新流（创建新的解码器和解码线程）

## 7. seek_chapter：章节跳转

PageUp/PageDown 在有章节信息的媒体中可以跳转到上一个/下一个章节（ffplay.c 行 3325-3350）：

```c
static void seek_chapter(VideoState *is, int incr)
{
    int64_t pos = get_master_clock(is) * AV_TIME_BASE;
    int i;

    if (!is->ic->nb_chapters)
        return;  // 无章节信息，直接返回

    // 找到当前所在的章节
    for (i = 0; i < is->ic->nb_chapters; i++) {
        AVChapter *ch = is->ic->chapters[i];
        if (av_compare_ts(pos, AV_TIME_BASE_Q, ch->start, ch->time_base) < 0) {
            i--;
            break;
        }
    }

    i += incr;                     // 向前或向后跳一个章节
    i = FFMAX(i, 0);              // 不小于 0
    if (i >= is->ic->nb_chapters)
        return;                    // 不超过最后一个章节

    av_log(NULL, AV_LOG_VERBOSE, "Seeking to chapter %d.\n", i);
    stream_seek(is,
        av_rescale_q(is->ic->chapters[i]->start, is->ic->chapters[i]->time_base,
                     AV_TIME_BASE_Q),
        0, 0);
}
```

如果没有章节信息（`nb_chapters == 0`），PageUp/PageDown 退化为 600 秒的大步长 seek：

```c
case SDLK_PAGEUP:
    if (cur_stream->ic->nb_chapters <= 1) {
        incr = 600.0;
        goto do_seek;
    }
    seek_chapter(cur_stream, 1);
    break;
```

## 8. stream_close：资源清理全流程

当用户按 ESC/Q 退出时，调用链为 `do_exit()` -> `stream_close()`。`stream_close()` 负责销毁 `VideoState` 及其所有子资源（ffplay.c 行 1267-1301）：

```c
static void stream_close(VideoState *is)
{
    // 1. 通知所有线程退出
    is->abort_request = 1;

    // 2. 等待 read_thread 退出（read_thread 会在检测到 abort_request 后退出循环）
    SDL_WaitThread(is->read_tid, NULL);

    // 3. 关闭各流的解码组件（包括等待解码线程退出）
    if (is->audio_stream >= 0)
        stream_component_close(is, is->audio_stream);
    if (is->video_stream >= 0)
        stream_component_close(is, is->video_stream);
    if (is->subtitle_stream >= 0)
        stream_component_close(is, is->subtitle_stream);

    // 4. 关闭解复用器
    avformat_close_input(&is->ic);

    // 5. 销毁 PacketQueue
    packet_queue_destroy(&is->videoq);
    packet_queue_destroy(&is->audioq);
    packet_queue_destroy(&is->subtitleq);

    // 6. 销毁 FrameQueue
    frame_queue_destroy(&is->pictq);
    frame_queue_destroy(&is->sampq);
    frame_queue_destroy(&is->subpq);

    // 7. 销毁同步原语和辅助资源
    SDL_DestroyCond(is->continue_read_thread);
    sws_freeContext(is->sub_convert_ctx);
    av_free(is->filename);

    // 8. 销毁 SDL 纹理
    if (is->vis_texture)
        SDL_DestroyTexture(is->vis_texture);
    if (is->vid_texture)
        SDL_DestroyTexture(is->vid_texture);
    if (is->sub_texture)
        SDL_DestroyTexture(is->sub_texture);

    // 9. 释放 VideoState 自身
    av_free(is);
}
```

`do_exit()` 在 `stream_close()` 之后继续清理全局资源（ffplay.c 行 1303-1328）：

```c
static void do_exit(VideoState *is)
{
    if (is) {
        stream_close(is);
    }
    if (renderer)
        SDL_DestroyRenderer(renderer);
    if (vk_renderer)
        vk_renderer_destroy(vk_renderer);
    if (window)
        SDL_DestroyWindow(window);
    uninit_opts();
    // 释放滤镜列表和编解码器名称
    for (int i = 0; i < nb_vfilters; i++)
        av_freep(&vfilters_list[i]);
    av_freep(&vfilters_list);
    av_freep(&video_codec_name);
    av_freep(&audio_codec_name);
    av_freep(&subtitle_codec_name);
    av_freep(&input_filename);
    avformat_network_deinit();
    if (show_status)
        printf("\n");
    SDL_Quit();
    av_log(NULL, AV_LOG_QUIET, "%s", "");
    exit(0);  // 直接退出进程
}
```

清理顺序遵循**创建的逆序**原则：先停线程、再关流、再销毁队列、最后释放内存。

## 9. 命令行选项系统

ffplay 使用 FFmpeg 通用的 `OptionDef` 系统来定义命令行选项（ffplay.c 行 3659-3711）。以下是部分常用选项：

```c
static const OptionDef options[] = {
    CMDUTILS_COMMON_OPTIONS                          // FFmpeg 通用选项（-h, -v, -loglevel 等）
    { "x",              OPT_TYPE_FUNC, ..., "force displayed width", "width" },
    { "y",              OPT_TYPE_FUNC, ..., "force displayed height", "height" },
    { "fs",             OPT_TYPE_BOOL, ..., "force full screen" },
    { "an",             OPT_TYPE_BOOL, ..., "disable audio" },
    { "vn",             OPT_TYPE_BOOL, ..., "disable video" },
    { "sn",             OPT_TYPE_BOOL, ..., "disable subtitling" },
    { "ss",             OPT_TYPE_TIME, ..., "seek to a given position in seconds", "pos" },
    { "t",              OPT_TYPE_TIME, ..., "play \"duration\" seconds", "duration" },
    { "bytes",          OPT_TYPE_INT,  ..., "seek by bytes 0=off 1=on -1=auto" },
    { "seek_interval",  OPT_TYPE_FLOAT,..., "set seek interval for left/right keys" },
    { "volume",         OPT_TYPE_INT,  ..., "set startup volume 0=min 100=max" },
    { "sync",           OPT_TYPE_FUNC, ..., "set audio-video sync type (audio/video/ext)" },
    { "vf",             OPT_TYPE_FUNC, ..., "set video filters", "filter_graph" },
    { "af",             OPT_TYPE_STRING,.., "set audio filters", "filter_graph" },
    { "loop",           OPT_TYPE_INT,  ..., "set number of times playback shall be looped" },
    { "framedrop",      OPT_TYPE_BOOL, ..., "drop frames when cpu is too slow" },
    { "autoexit",       OPT_TYPE_BOOL, ..., "exit at the end" },
    { "hwaccel",        OPT_TYPE_STRING,.., "use HW accelerated decoding" },
    { "enable_vulkan",  OPT_TYPE_BOOL, ..., "enable vulkan renderer" },
    { NULL, },  // 以 NULL 终止
};
```

`OptionDef` 的每个条目包含：选项名、类型（BOOL/INT/FLOAT/STRING/FUNC/TIME）、标志位、存储地址或处理函数、帮助文本和参数名。

在 `main()` 中通过 `parse_options()` 解析命令行参数：

```c
ret = parse_options(NULL, argc, argv, options, opt_input_file);
```

不匹配任何选项的参数会作为输入文件名传给 `opt_input_file()` 回调。

常用使用示例：

```bash
# 基本播放
ffplay video.mp4

# 从 30 秒开始播放，指定窗口大小
ffplay -ss 30 -x 1280 -y 720 video.mp4

# 以音频为主时钟，启用丢帧
ffplay -sync audio -framedrop video.mp4

# 应用视频滤镜和音频滤镜
ffplay -vf "hflip,drawtext=text='Hello'" -af "volume=0.5" video.mp4

# 硬件加速 + Vulkan 渲染
ffplay -hwaccel cuda -enable_vulkan video.mp4
```

## 10. 窗口事件处理

除了键盘和鼠标，ffplay 还处理窗口相关事件：

```c
case SDL_WINDOWEVENT:
    switch (event.window.event) {
        case SDL_WINDOWEVENT_SIZE_CHANGED:
            // 窗口大小变化：更新尺寸并销毁旧的可视化纹理
            screen_width  = cur_stream->width  = event.window.data1;
            screen_height = cur_stream->height = event.window.data2;
            if (cur_stream->vis_texture) {
                SDL_DestroyTexture(cur_stream->vis_texture);
                cur_stream->vis_texture = NULL;
            }
            if (vk_renderer)
                vk_renderer_resize(vk_renderer, screen_width, screen_height);
        case SDL_WINDOWEVENT_EXPOSED:
            // 窗口曝光（被遮挡后重新显示）：强制重绘一帧
            cur_stream->force_refresh = 1;
    }
    break;
```

注意这里 `SIZE_CHANGED` 和 `EXPOSED` 之间也是 fall-through：窗口大小变化后也需要强制刷新。

## 11. 系列总结

至此，ffplay 源码解析系列全部完成。让我们回顾整个系列的内容脉络：

| 篇目 | 主题 | 核心内容 |
|------|------|---------|
| 第一篇 | 整体架构与启动流程 | 多线程架构、main() 初始化、stream_open() |
| 第二篇 | 核心数据结构 | VideoState、PacketQueue、FrameQueue、Clock |
| 第三篇 | 解复用线程 | read_thread、av_read_frame、数据包分发 |
| 第四篇 | 解码核心机制 | 三个解码线程、avcodec 新旧 API |
| 第五篇 | 音频输出与处理 | SDL 回调、audio_decode_frame、重采样 |
| 第六篇 | 视频渲染与显示 | video_refresh、帧调度、SDL 纹理渲染 |
| 第七篇 | 字幕处理与渲染 | 字幕解码、bitmap 叠加、过期清理 |
| 第八篇 | 音频可视化 | 波形显示、RDFT 频谱分析 |
| 第九篇 | 音视频同步 | 三种同步模式、compute_target_delay |
| 第十篇 | AVFilter 滤镜系统 | 滤镜图构建、configure_filtergraph |
| 第十一篇 | 事件处理与用户交互 | event_loop、键盘/鼠标处理、seek、资源清理 |

**ffplay 的设计哲学**可以归纳为以下几点：

1. **简约而不简单**：3900 行代码实现一个功能完整的播放器，没有一行多余的代码
2. **线程分治**：read_thread 负责 IO、三个 decode_thread 负责解码、主线程负责渲染和交互，职责清晰
3. **事件驱动**：主线程在等待用户输入的间隙驱动视频渲染，一个线程两个职责，高效复用
4. **队列解耦**：PacketQueue 和 FrameQueue 是线程间通信的核心，通过 serial 机制优雅地处理 seek
5. **时钟同步**：三种同步模式的统一抽象，drift 补偿和 PTS 预测的精妙配合

ffplay 虽然体量不大，但涵盖了一个播放器需要面对的几乎所有核心问题。深入理解它的源码，对于音视频开发者来说是一笔宝贵的财富。
