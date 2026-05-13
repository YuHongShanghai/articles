# ffplay 源码解析系列（一）：开篇 - ffplay 整体架构与启动流程

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
> 
> 本系列文章将由浅入深，全方位剖析 ffplay 源码，帮助读者深入理解一个完整播放器的实现原理。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. ffplay 是什么？

ffplay 是 FFmpeg 项目自带的一个**轻量级媒体播放器**，整个实现仅一个 C 源文件 `ffplay.c`（约 3900 行），却涵盖了一个播放器所需的全部核心功能：

- **解封装**（Demuxing）：从媒体文件或网络流中读取压缩数据包
- **解码**（Decoding）：将压缩的音视频数据解码为原始帧
- **音视频同步**（A/V Sync）：确保音频和视频按正确的时间关系播放
- **渲染输出**（Rendering）：将视频帧渲染到屏幕、将音频帧输出到扬声器
- **用户交互**（Interaction）：支持暂停、seek、音量调节、全屏切换等操作
- **滤镜处理**（Filtering）：支持通过 AVFilter 对音视频进行实时处理

虽然代码量不大，但 ffplay 的设计非常精妙，是学习**多线程播放器架构**和**音视频同步算法**的绝佳素材。

## 2. 依赖的库

ffplay 的实现依赖两大类库：**FFmpeg 自身的库**和**外部的 SDL2 库**。

从源码头文件引用可以清晰看到这些依赖：

```c
// FFmpeg 核心库
#include "libavutil/avstring.h"        // 通用工具库（字符串、数学、内存等）
#include "libavutil/channel_layout.h"
#include "libavutil/mathematics.h"
#include "libavutil/mem.h"
#include "libavutil/pixdesc.h"
#include "libavutil/dict.h"
#include "libavutil/fifo.h"
#include "libavutil/samplefmt.h"
#include "libavutil/time.h"
#include "libavformat/avformat.h"      // 封装/解封装库
#include "libavdevice/avdevice.h"      // 设备输入输出库
#include "libswscale/swscale.h"        // 视频缩放与像素格式转换库
#include "libswresample/swresample.h"  // 音频重采样库

// 滤镜库
#include "libavfilter/avfilter.h"      // 滤镜框架
#include "libavfilter/buffersink.h"    // 滤镜输出端
#include "libavfilter/buffersrc.h"     // 滤镜输入端

// 外部库：SDL2（Simple DirectMedia Layer）
#include <SDL.h>                       // 窗口管理、渲染、事件处理
#include <SDL_thread.h>                // 线程、互斥锁、条件变量
```

各库的职责如下表：

| 库 | 职责 |
|---|------|
| **libavformat** | 媒体容器的封装与解封装（如 MP4、MKV、FLV），网络协议支持（RTSP、HTTP） |
| **libavcodec** | 音视频编解码器（H.264、H.265、AAC、MP3 等） |
| **libavutil** | 通用工具函数（内存管理、数学运算、时间处理、数据结构等） |
| **libswscale** | 视频像素格式转换（如 YUV420P → RGB）和缩放 |
| **libswresample** | 音频采样格式、采样率、声道布局转换 |
| **libavfilter** | 音视频滤镜框架（如旋转、裁剪、变速等） |
| **libavdevice** | 采集设备支持（摄像头、麦克风等） |
| **SDL2** | 跨平台多媒体库，提供窗口创建、2D渲染、音频输出、键盘鼠标事件处理 |

![ffplay 依赖的 FFmpeg 库与 SDL2](https://gitee.com/yuhong1234/ffplay/raw/master/01-ffmpeg-libs.png)

## 3. 多线程架构总览

ffplay 采用**多线程架构**，主要由以下线程协同工作：

| 线程 | 函数 | 职责 |
|------|------|------|
| **主线程** | `main()` → `event_loop()` | SDL 事件处理、视频渲染刷新 |
| **读取线程** | `read_thread()` | 解复用（Demux），从文件/网络读取数据包并分发到各队列 |
| **视频解码线程** | `video_thread()` | 视频包解码 + 滤镜处理 → 解码帧入队 |
| **音频解码线程** | `audio_thread()` | 音频包解码 + 滤镜处理 → 解码帧入队 |
| **字幕解码线程** | `subtitle_thread()` | 字幕包解码 → 解码帧入队 |
| **SDL 音频回调** | `sdl_audio_callback()` | 在 SDL 音频线程中被调用，从音频帧队列取数据填充播放缓冲区 |

线程之间通过**两级队列**进行数据传递：

1. **PacketQueue**（包队列）：read_thread → 各解码线程，传递未解码的压缩数据包
2. **FrameQueue**（帧队列）：各解码线程 → 主线程/音频回调，传递解码后的原始帧

![ffplay 多线程架构与数据流](https://gitee.com/yuhong1234/ffplay/raw/master/01-ffplay-architecture.png)

从架构图中可以看出，ffplay 的设计遵循经典的**生产者-消费者模型**：

- `read_thread` 是 PacketQueue 的**生产者**
- 各解码线程是 PacketQueue 的**消费者**，同时是 FrameQueue 的**生产者**
- 主线程的 `video_refresh()` 和 SDL 的 `sdl_audio_callback()` 是 FrameQueue 的**消费者**

## 4. main() 函数分析

`main()` 函数是 ffplay 的入口点，负责完成初始化并启动播放。下面逐步分析其核心流程：

### 4.1 初始化阶段

```c
int main(int argc, char **argv)
{
    int flags, ret;
    VideoState *is;

    init_dynload();                          // 动态库加载初始化

    av_log_set_flags(AV_LOG_SKIP_REPEATED);  // 跳过重复日志
    parse_loglevel(argc, argv, options);     // 解析日志级别

    /* 注册所有编解码器、解复用器和协议 */
#if CONFIG_AVDEVICE
    avdevice_register_all();                 // 注册设备（摄像头等）
#endif
    avformat_network_init();                 // 初始化网络（用于 RTSP/HTTP 等）

    signal(SIGINT , sigterm_handler);        // 注册信号处理
    signal(SIGTERM, sigterm_handler);

    show_banner(argc, argv, options);        // 显示 FFmpeg 版本信息

    // 解析命令行参数（如 -i input.mp4 -vf "scale=1280:720"）
    ret = parse_options(NULL, argc, argv, options, opt_input_file);
    if (ret < 0)
        exit(ret == AVERROR_EXIT ? 0 : 1);

    if (!input_filename) {
        show_usage();
        av_log(NULL, AV_LOG_FATAL, "An input file must be specified\n");
        exit(1);
    }
    // ...
```

### 4.2 SDL 初始化与窗口创建

```c
    // 根据配置确定需要初始化的 SDL 子系统
    flags = SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_TIMER;
    if (audio_disable)
        flags &= ~SDL_INIT_AUDIO;
    if (display_disable)
        flags &= ~SDL_INIT_VIDEO;
    if (SDL_Init(flags)) {
        av_log(NULL, AV_LOG_FATAL, "Could not initialize SDL - %s\n", SDL_GetError());
        exit(1);
    }

    // 创建 SDL 窗口
    if (!display_disable) {
        int flags = SDL_WINDOW_HIDDEN;
        if (alwaysontop)
            flags |= SDL_WINDOW_ALWAYS_ON_TOP;
        if (borderless)
            flags |= SDL_WINDOW_BORDERLESS;
        else
            flags |= SDL_WINDOW_RESIZABLE;

        // 支持 Vulkan 渲染器（用于硬件加速解码的渲染）
        if (enable_vulkan) {
            vk_renderer = vk_get_renderer();
            if (vk_renderer)
                flags |= SDL_WINDOW_VULKAN;
        }

        // 创建窗口，初始大小 640x480（隐藏状态，后续由 video_open 显示）
        window = SDL_CreateWindow(program_name, SDL_WINDOWPOS_UNDEFINED,
                                  SDL_WINDOWPOS_UNDEFINED,
                                  default_width, default_height, flags);

        // 创建渲染器（优先使用硬件加速）
        if (!vk_renderer) {
            renderer = SDL_CreateRenderer(window, -1,
                                          SDL_RENDERER_ACCELERATED |
                                          SDL_RENDERER_PRESENTVSYNC);
            if (!renderer)
                renderer = SDL_CreateRenderer(window, -1, 0); // 回退到软件渲染
        }
    }
```

这里有两个值得注意的设计：

1. **窗口以隐藏状态创建**（`SDL_WINDOW_HIDDEN`），等到第一帧视频解码后才通过 `video_open()` 设置正确的窗口尺寸并显示
2. **渲染器支持降级策略**：优先尝试硬件加速渲染器，失败时回退到软件渲染

### 4.3 打开媒体流与进入事件循环

```c
    // 打开媒体流：这是播放的核心入口
    // 内部会创建 read_thread，启动整个播放管线
    is = stream_open(input_filename, file_iformat);
    if (!is) {
        av_log(NULL, AV_LOG_FATAL, "Failed to initialize VideoState!\n");
        do_exit(NULL);
    }

    // 进入事件主循环（永不返回，由 do_exit 调用 exit() 退出）
    event_loop(is);

    return 0;
}
```

短短几行代码，背后却启动了一套完整的播放管线。`stream_open()` 是整个播放流程的起点，而 `event_loop()` 是主线程的归宿。

![main() 启动流程](https://gitee.com/yuhong1234/ffplay/raw/master/01-main-flow.png)

## 5. stream_open()：播放管线的启动

`stream_open()` 是 ffplay 中最重要的初始化函数之一，它创建并初始化了 `VideoState` 结构体——这是贯穿整个播放器的**核心上下文**。

```c
static VideoState *stream_open(const char *filename,
                               const AVInputFormat *iformat)
{
    VideoState *is;

    // 分配并零初始化 VideoState
    is = av_mallocz(sizeof(VideoState));
    if (!is)
        return NULL;

    // 初始化流索引为"未选择"状态
    is->last_video_stream = is->video_stream = -1;
    is->last_audio_stream = is->audio_stream = -1;
    is->last_subtitle_stream = is->subtitle_stream = -1;
    is->filename = av_strdup(filename);
    is->iformat = iformat;
    is->ytop    = 0;
    is->xleft   = 0;

    /* 初始化帧队列（FrameQueue） - 解码后的帧缓冲区 */
    // 视频帧队列：容量 3，保留上一帧（keep_last=1，用于渲染时参考）
    if (frame_queue_init(&is->pictq, &is->videoq, VIDEO_PICTURE_QUEUE_SIZE, 1) < 0)
        goto fail;
    // 字幕帧队列：容量 16，不保留上一帧
    if (frame_queue_init(&is->subpq, &is->subtitleq, SUBPICTURE_QUEUE_SIZE, 0) < 0)
        goto fail;
    // 音频帧队列：容量 9，保留上一帧
    if (frame_queue_init(&is->sampq, &is->audioq, SAMPLE_QUEUE_SIZE, 1) < 0)
        goto fail;

    /* 初始化包队列（PacketQueue） - 未解码的压缩数据缓冲区 */
    if (packet_queue_init(&is->videoq) < 0 ||
        packet_queue_init(&is->audioq) < 0 ||
        packet_queue_init(&is->subtitleq) < 0)
        goto fail;

    // 创建条件变量，用于 read_thread 的等待唤醒
    if (!(is->continue_read_thread = SDL_CreateCond()))
        goto fail;

    /* 初始化三个时钟（音频时钟、视频时钟、外部时钟） */
    init_clock(&is->vidclk, &is->videoq.serial);   // 视频时钟
    init_clock(&is->audclk, &is->audioq.serial);   // 音频时钟
    init_clock(&is->extclk, &is->extclk.serial);   // 外部时钟

    // 音量初始化
    is->audio_clock_serial = -1;
    startup_volume = av_clip(startup_volume, 0, 100);
    startup_volume = av_clip(SDL_MIX_MAXVOLUME * startup_volume / 100, 0, SDL_MIX_MAXVOLUME);
    is->audio_volume = startup_volume;
    is->muted = 0;
    is->av_sync_type = av_sync_type;  // 默认为 AV_SYNC_AUDIO_MASTER

    // 🔑 关键：创建 read_thread，正式启动播放管线！
    is->read_tid = SDL_CreateThread(read_thread, "read_thread", is);
    if (!is->read_tid) {
        av_log(NULL, AV_LOG_FATAL, "SDL_CreateThread(): %s\n", SDL_GetError());
        goto fail;
    }
    return is;

fail:
    stream_close(is);
    return NULL;
}
```

`stream_open()` 完成了以下关键初始化：

1. **分配 VideoState**：这个结构体包含了播放器的全部状态，后续文章会详细剖析
2. **初始化两级队列**：3 个 PacketQueue + 3 个 FrameQueue
3. **初始化 3 个时钟**：用于音视频同步（audclk、vidclk、extclk）
4. **创建 read_thread**：这是播放管线的真正起点，后续所有解码线程都由它内部创建

## 6. event_loop()：主线程的事件循环

`stream_open()` 返回后，主线程进入 `event_loop()`，这是一个**永不返回**的循环：

```c
static void event_loop(VideoState *cur_stream)
{
    SDL_Event event;
    double incr, pos, frac;

    for (;;) {
        double x;
        // 在等待事件的间隙，执行视频刷新
        refresh_loop_wait_event(cur_stream, &event);

        // 处理各类 SDL 事件
        switch (event.type) {
        case SDL_KEYDOWN:
            // 键盘事件处理（暂停、seek、音量、全屏等）
            // ...
            break;
        case SDL_MOUSEBUTTONDOWN:
            // 鼠标事件处理（双击全屏、右键 seek 等）
            // ...
            break;
        case SDL_WINDOWEVENT:
            // 窗口事件处理（窗口大小变化、窗口重绘等）
            // ...
            break;
        case SDL_QUIT:
        case FF_QUIT_EVENT:
            do_exit(cur_stream);
            break;
        }
    }
}
```

这里最关键的是 `refresh_loop_wait_event()` 函数——它不仅仅是"等待事件"这么简单：

```c
static void refresh_loop_wait_event(VideoState *is, SDL_Event *event) {
    double remaining_time = 0.0;
    SDL_PumpEvents();
    // 当没有待处理的事件时，利用"空闲时间"执行视频刷新
    while (!SDL_PeepEvents(event, 1, SDL_GETEVENT, SDL_FIRSTEVENT, SDL_LASTEVENT)) {
        if (!cursor_hidden && av_gettime_relative() - cursor_last_shown > CURSOR_HIDE_DELAY) {
            SDL_ShowCursor(0);      // 自动隐藏鼠标光标
            cursor_hidden = 1;
        }
        if (remaining_time > 0.0)
            av_usleep((int64_t)(remaining_time * 1000000.0)); // 精确休眠
        remaining_time = REFRESH_RATE;  // 默认刷新间隔 10ms
        // 🔑 核心：执行视频刷新逻辑（音视频同步的关键入口）
        if (is->show_mode != SHOW_MODE_NONE && (!is->paused || is->force_refresh))
            video_refresh(is, &remaining_time);
        SDL_PumpEvents();
    }
}
```

这个设计非常巧妙：

- **主线程不会空转**：当没有 SDL 事件时，主线程利用空闲时间执行 `video_refresh()` 进行视频渲染
- **精确的刷新控制**：`video_refresh()` 会根据音视频同步状态计算出下一次需要刷新的时间，通过 `remaining_time` 控制休眠时长，避免 CPU 空耗
- **事件优先**：一旦有 SDL 事件到来（键盘、鼠标等），立即跳出内层循环去处理

## 7. 全局变量与宏定义

ffplay 使用了大量全局变量来存储命令行选项和运行时状态。这些定义位于文件开头，理解它们有助于后续阅读：

### 7.1 关键宏定义

```c
#define MAX_QUEUE_SIZE (15 * 1024 * 1024)   // PacketQueue 最大缓冲 15MB
#define MIN_FRAMES 25                        // 队列中最少保持 25 个包

/* 音视频同步阈值 */
#define AV_SYNC_THRESHOLD_MIN 0.04          // 最小同步阈值 40ms
#define AV_SYNC_THRESHOLD_MAX 0.1           // 最大同步阈值 100ms
#define AV_SYNC_FRAMEDUP_THRESHOLD 0.1      // 帧复制阈值
#define AV_NOSYNC_THRESHOLD 10.0            // 超过 10s 不做同步

#define SAMPLE_CORRECTION_PERCENT_MAX 10    // 音频同步最大补偿 10%
#define REFRESH_RATE 0.01                   // 视频刷新轮询间隔 10ms

#define VIDEO_PICTURE_QUEUE_SIZE 3          // 视频帧队列容量
#define SUBPICTURE_QUEUE_SIZE 16            // 字幕帧队列容量
#define SAMPLE_QUEUE_SIZE 9                 // 音频帧队列容量
```

### 7.2 同步模式

ffplay 支持三种音视频同步模式：

```c
enum {
    AV_SYNC_AUDIO_MASTER,     // 以音频为主时钟（默认）
    AV_SYNC_VIDEO_MASTER,     // 以视频为主时钟
    AV_SYNC_EXTERNAL_CLOCK,   // 以外部时钟为主时钟
};
```

默认使用 `AV_SYNC_AUDIO_MASTER`——这是业界最常用的同步策略。因为人耳对音频的不连续性（如卡顿、杂音）比眼睛对视频的不连续性（如丢帧、重复帧）更敏感，所以播放器通常以音频为基准，让视频去追赶或等待音频。

## 8. 资源清理

当用户按下 ESC/Q 或关闭窗口时，`do_exit()` 被调用执行清理：

```c
static void do_exit(VideoState *is)
{
    if (is) {
        stream_close(is);       // 关闭所有流、销毁所有队列和线程
    }
    if (renderer)
        SDL_DestroyRenderer(renderer);
    if (vk_renderer)
        vk_renderer_destroy(vk_renderer);
    if (window)
        SDL_DestroyWindow(window);
    uninit_opts();              // 释放命令行选项
    avformat_network_deinit();  // 清理网络
    SDL_Quit();                 // 清理 SDL
    exit(0);                    // 直接退出进程
}
```

`stream_close()` 内部会依次：
1. 设置 `abort_request = 1`，通知 read_thread 退出
2. 等待 read_thread 结束
3. 关闭各个流（音频/视频/字幕），销毁对应的解码器和线程
4. 销毁所有 PacketQueue 和 FrameQueue
5. 释放所有纹理和内存

## 9. 小结

本篇作为系列开篇，我们从宏观层面了解了 ffplay 的整体设计：

- **单文件实现**：约 3900 行 C 代码，实现了一个功能完整的媒体播放器
- **多线程架构**：读取线程 + 解码线程 + 主线程（事件循环/渲染），通过两级队列通信
- **主函数流程**：初始化 → SDL 创建窗口 → `stream_open()` 启动播放管线 → `event_loop()` 处理事件与渲染
- **核心入口**：`stream_open()` 创建 `VideoState` 并启动 `read_thread`；`event_loop()` 中的 `video_refresh()` 驱动视频渲染与同步

在下一篇文章中，我们将深入剖析 ffplay 的**核心数据结构**——`VideoState`、`PacketQueue`、`FrameQueue`、`Clock`、`Decoder` 等，理解这些结构体是读懂后续所有代码的基础。
