# ffplay 源码解析系列（二）：核心数据结构详解

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 数据结构是程序的骨架。理解 ffplay 的数据结构，就掌握了阅读整个源码的钥匙。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 数据结构全景

ffplay 中定义了若干核心数据结构，它们层层嵌套、相互关联，共同构成了播放器的运行框架。下面先从全局视角看它们之间的关系：

![核心数据结构关系图](https://gitee.com/yuhong1234/ffplay/raw/master/02-data-structures-overview.png)

各结构体的职责概览：

| 结构体 | 职责 |
|--------|------|
| **VideoState** | 播放器的"上帝结构体"，包含了播放器的全部状态 |
| **PacketQueue** | 压缩数据包（AVPacket）的线程安全 FIFO 队列 |
| **FrameQueue** | 解码后帧（AVFrame）的线程安全环形缓冲区 |
| **Frame** | 解码后帧的封装，附带 pts、duration、serial 等播放信息 |
| **Decoder** | 解码器的封装，关联 AVCodecContext、PacketQueue 和解码线程 |
| **Clock** | 播放时钟，用于音视频同步 |
| **AudioParams** | 音频参数描述（采样率、声道布局、采样格式等） |

## 2. PacketQueue —— 压缩数据包队列

`PacketQueue` 是 ffplay 实现的**线程安全 FIFO 队列**，用于在 read_thread（生产者）和各解码线程（消费者）之间传递未解码的压缩数据包。

### 2.1 结构体定义

```c
typedef struct MyAVPacketList {
    AVPacket *pkt;    // 指向实际的 AVPacket
    int serial;       // 序列号，用于标记队列的"代"（seek 时递增）
} MyAVPacketList;

typedef struct PacketQueue {
    AVFifo *pkt_list;     // 底层 FIFO 存储（FFmpeg 7.x 使用 AVFifo 替代链表）
    int nb_packets;       // 队列中的包数量
    int size;             // 队列占用的总字节数（包数据 + 结构体开销）
    int64_t duration;     // 队列中所有包的总时长
    int abort_request;    // 中止标志（1 = 退出）
    int serial;           // 当前序列号（每次 seek 或 flush 时递增）
    SDL_mutex *mutex;     // 互斥锁（线程安全）
    SDL_cond *cond;       // 条件变量（用于阻塞等待）
} PacketQueue;
```

**关键设计点**：

- **AVFifo 替代链表**：FFmpeg 7.x 版本中，PacketQueue 的底层存储从链表改为 `AVFifo`（自动增长的 FIFO 缓冲区），减少了频繁的内存分配
- **serial 机制**：这是 ffplay 中一个精妙的设计。每次 seek 操作或队列 flush 时，`serial` 会递增。解码器通过比较 packet 的 serial 与队列的 serial，判断该 packet 是否属于当前播放序列——如果不属于，则直接丢弃。这避免了 seek 后播放旧数据的问题

### 2.2 核心操作

#### 初始化

```c
static int packet_queue_init(PacketQueue *q)
{
    memset(q, 0, sizeof(PacketQueue));
    // 创建 AVFifo，初始容量为 1 个元素，支持自动增长
    q->pkt_list = av_fifo_alloc2(1, sizeof(MyAVPacketList), AV_FIFO_FLAG_AUTO_GROW);
    if (!q->pkt_list)
        return AVERROR(ENOMEM);
    q->mutex = SDL_CreateMutex();       // 创建互斥锁
    q->cond = SDL_CreateCond();         // 创建条件变量
    q->abort_request = 1;              // 初始状态为"中止"，需调用 start 启用
    return 0;
}
```

#### 入队（生产者调用）

```c
static int packet_queue_put(PacketQueue *q, AVPacket *pkt)
{
    AVPacket *pkt1;
    int ret;

    pkt1 = av_packet_alloc();          // 分配新的 AVPacket
    if (!pkt1) {
        av_packet_unref(pkt);
        return -1;
    }
    av_packet_move_ref(pkt1, pkt);     // 移动引用（零拷贝）

    SDL_LockMutex(q->mutex);
    ret = packet_queue_put_private(q, pkt1);  // 在锁内执行实际入队
    SDL_UnlockMutex(q->mutex);

    if (ret < 0)
        av_packet_free(&pkt1);
    return ret;
}

// 实际入队操作（必须在持锁状态下调用）
static int packet_queue_put_private(PacketQueue *q, AVPacket *pkt)
{
    MyAVPacketList pkt1;
    int ret;

    if (q->abort_request)              // 如果队列已中止，拒绝入队
       return -1;

    pkt1.pkt = pkt;
    pkt1.serial = q->serial;           // 打上当前序列号标记

    ret = av_fifo_write(q->pkt_list, &pkt1, 1);  // 写入 FIFO
    if (ret < 0)
        return ret;

    q->nb_packets++;
    q->size += pkt1.pkt->size + sizeof(pkt1);     // 累加字节数
    q->duration += pkt1.pkt->duration;             // 累加时长
    SDL_CondSignal(q->cond);           // 唤醒等待的消费者
    return 0;
}
```

#### 出队（消费者调用）

```c
static int packet_queue_get(PacketQueue *q, AVPacket *pkt, int block, int *serial)
{
    MyAVPacketList pkt1;
    int ret;

    SDL_LockMutex(q->mutex);

    for (;;) {
        if (q->abort_request) {        // 收到退出信号
            ret = -1;
            break;
        }

        if (av_fifo_read(q->pkt_list, &pkt1, 1) >= 0) {  // 有数据可读
            q->nb_packets--;
            q->size -= pkt1.pkt->size + sizeof(pkt1);
            q->duration -= pkt1.pkt->duration;
            av_packet_move_ref(pkt, pkt1.pkt);   // 移动数据到输出 pkt
            if (serial)
                *serial = pkt1.serial;            // 返回该 packet 的 serial
            av_packet_free(&pkt1.pkt);
            ret = 1;
            break;
        } else if (!block) {           // 非阻塞模式，队列为空直接返回 0
            ret = 0;
            break;
        } else {                       // 阻塞模式，等待生产者放入新数据
            SDL_CondWait(q->cond, q->mutex);
        }
    }
    SDL_UnlockMutex(q->mutex);
    return ret;
}
```

#### Flush（seek 时清空队列）

```c
static void packet_queue_flush(PacketQueue *q)
{
    MyAVPacketList pkt1;

    SDL_LockMutex(q->mutex);
    while (av_fifo_read(q->pkt_list, &pkt1, 1) >= 0)
        av_packet_free(&pkt1.pkt);     // 释放所有 packet
    q->nb_packets = 0;
    q->size = 0;
    q->duration = 0;
    q->serial++;                       // 🔑 递增序列号！
    SDL_UnlockMutex(q->mutex);
}
```

`serial++` 是 flush 的关键：序列号递增后，解码器中残留的旧 serial 的 packet 都会被识别为"过期数据"而被丢弃。

![PacketQueue 结构与操作](https://gitee.com/yuhong1234/ffplay/raw/master/02-packet-queue.png)

### 2.3 特殊的 Null Packet

ffplay 使用空包（null packet）作为 **EOF 信号**传递给解码器：

```c
static int packet_queue_put_nullpacket(PacketQueue *q, AVPacket *pkt, int stream_index)
{
    pkt->stream_index = stream_index;
    return packet_queue_put(q, pkt);   // pkt->data == NULL, pkt->size == 0
}
```

当 `av_read_frame()` 返回 EOF 时，read_thread 会向各队列发送 null packet，通知解码器"没有更多数据了，请输出缓冲区中剩余的帧"。

## 3. FrameQueue —— 解码帧环形缓冲区

`FrameQueue` 是一个**固定大小的环形缓冲区**，用于在解码线程（生产者）和渲染/音频输出（消费者）之间传递解码后的帧。

### 3.1 Frame 结构体

每个队列元素是一个 `Frame` 结构体，封装了解码后的帧数据及其播放元信息：

```c
typedef struct Frame {
    AVFrame *frame;       // 解码后的帧数据（视频：像素数据；音频：采样数据）
    AVSubtitle sub;       // 字幕数据（仅字幕帧使用）
    int serial;           // 序列号（与 PacketQueue 的 serial 配合）
    double pts;           // 显示时间戳（秒）
    double duration;      // 帧时长（秒）
    int64_t pos;          // 该帧在输入文件中的字节位置
    int width;            // 视频帧宽度
    int height;           // 视频帧高度
    int format;           // 像素/采样格式
    AVRational sar;       // 像素宽高比（Sample Aspect Ratio）
    int uploaded;         // 是否已上传到 SDL 纹理（避免重复上传）
    int flip_v;           // 是否需要垂直翻转
} Frame;
```

### 3.2 FrameQueue 结构体

```c
typedef struct FrameQueue {
    Frame queue[FRAME_QUEUE_SIZE];  // 固定大小的数组（环形缓冲区）
    int rindex;          // 读索引（消费者位置）
    int windex;          // 写索引（生产者位置）
    int size;            // 当前队列中的元素数量
    int max_size;        // 队列最大容量
    int keep_last;       // 是否保留最近一次显示的帧（用于视频渲染参考）
    int rindex_shown;    // 标记当前读位置的帧是否已显示（配合 keep_last 使用）
    SDL_mutex *mutex;    // 互斥锁
    SDL_cond *cond;      // 条件变量
    PacketQueue *pktq;   // 关联的 PacketQueue（用于获取 abort_request 状态）
} FrameQueue;
```

**关键设计点**：

- **FRAME_QUEUE_SIZE**：取 `VIDEO_PICTURE_QUEUE_SIZE(3)`、`SUBPICTURE_QUEUE_SIZE(16)`、`SAMPLE_QUEUE_SIZE(9)` 的最大值 = 16。所有 FrameQueue 共享同一个数组大小，通过 `max_size` 控制实际容量
- **keep_last 机制**：视频帧和音频帧设置 `keep_last=1`，表示消费完一帧后不立即释放，而是保留为"上一帧"。这样在计算帧间时长（`vp_duration`）时可以参考上一帧的 pts
- **rindex_shown**：配合 `keep_last` 使用。当 `rindex_shown=1` 时，表示 `rindex` 位置的帧已经显示过了，真正的"当前帧"应该是 `rindex+1` 的位置

### 3.3 核心操作

#### 初始化

```c
static int frame_queue_init(FrameQueue *f, PacketQueue *pktq, int max_size, int keep_last)
{
    memset(f, 0, sizeof(FrameQueue));
    f->mutex = SDL_CreateMutex();
    f->cond = SDL_CreateCond();
    f->pktq = pktq;
    f->max_size = FFMIN(max_size, FRAME_QUEUE_SIZE);
    f->keep_last = !!keep_last;
    // 预分配所有 AVFrame 对象（避免运行时频繁分配）
    for (int i = 0; i < f->max_size; i++)
        if (!(f->queue[i].frame = av_frame_alloc()))
            return AVERROR(ENOMEM);
    return 0;
}
```

预分配策略是一个性能优化：队列中的 `AVFrame` 在初始化时一次性分配，运行时只需 `av_frame_move_ref` 移动数据，避免了反复 alloc/free 的开销。

#### 获取可写帧（生产者调用）

```c
static Frame *frame_queue_peek_writable(FrameQueue *f)
{
    SDL_LockMutex(f->mutex);
    // 等待队列有空位
    while (f->size >= f->max_size && !f->pktq->abort_request) {
        SDL_CondWait(f->cond, f->mutex);
    }
    SDL_UnlockMutex(f->mutex);

    if (f->pktq->abort_request)
        return NULL;

    return &f->queue[f->windex];  // 返回写位置的 Frame 指针
}
```

#### 写入完成，推入队列

```c
static void frame_queue_push(FrameQueue *f)
{
    if (++f->windex == f->max_size)
        f->windex = 0;            // 环形回绕
    SDL_LockMutex(f->mutex);
    f->size++;
    SDL_CondSignal(f->cond);      // 唤醒消费者
    SDL_UnlockMutex(f->mutex);
}
```

#### Peek 操作族（消费者使用）

FrameQueue 提供了三种 peek 操作，用于查看不同位置的帧：

```c
// 获取当前帧（即将显示的帧）
static Frame *frame_queue_peek(FrameQueue *f)
{
    return &f->queue[(f->rindex + f->rindex_shown) % f->max_size];
}

// 获取下一帧（当前帧的后一帧）
static Frame *frame_queue_peek_next(FrameQueue *f)
{
    return &f->queue[(f->rindex + f->rindex_shown + 1) % f->max_size];
}

// 获取上一帧（最后显示的帧，仅 keep_last=1 时有意义）
static Frame *frame_queue_peek_last(FrameQueue *f)
{
    return &f->queue[f->rindex];
}
```

这三个函数在 `video_refresh()` 中被频繁使用：
- `peek_last()` 获取上一帧（lastvp），用于计算帧间时长
- `peek()` 获取当前帧（vp），用于判断是否该显示
- `peek_next()` 获取下一帧（nextvp），用于判断是否需要丢帧

#### 消费完成，移动读指针

```c
static void frame_queue_next(FrameQueue *f)
{
    if (f->keep_last && !f->rindex_shown) {
        f->rindex_shown = 1;      // 第一次调用：标记为"已显示"，不移动 rindex
        return;
    }
    frame_queue_unref_item(&f->queue[f->rindex]);  // 释放旧帧数据
    if (++f->rindex == f->max_size)
        f->rindex = 0;            // 环形回绕
    SDL_LockMutex(f->mutex);
    f->size--;
    SDL_CondSignal(f->cond);      // 唤醒生产者（有空位了）
    SDL_UnlockMutex(f->mutex);
}
```

`keep_last` 机制体现在：第一次调用 `frame_queue_next()` 时只设置 `rindex_shown = 1`，不移动 `rindex`。这样 `rindex` 位置的帧被保留为"上一帧"，供 `peek_last()` 访问。

![FrameQueue 环形缓冲区](https://gitee.com/yuhong1234/ffplay/raw/master/02-frame-queue.png)

## 4. Clock —— 播放时钟

`Clock` 是 ffplay 音视频同步的核心基础设施。ffplay 维护三个时钟实例：`audclk`（音频时钟）、`vidclk`（视频时钟）、`extclk`（外部时钟）。

### 4.1 结构体定义

```c
typedef struct Clock {
    double pts;           // 当前时钟的 PTS 值（秒）
    double pts_drift;     // pts 与系统时间的差值（pts - last_updated）
    double last_updated;  // 上次更新时钟的系统时间
    double speed;         // 播放速度（1.0 = 正常速度）
    int serial;           // 时钟所基于的 packet 的序列号
    int paused;           // 是否暂停
    int *queue_serial;    // 指向关联 PacketQueue 的 serial（用于过期检测）
} Clock;
```

### 4.2 时钟的核心思想

时钟不是简单地存储一个时间值，而是通过 `pts_drift`（PTS 漂移量）来实现**实时推算**。核心公式：

```
当前时间 = pts_drift + 当前系统时间
         = (pts - last_updated) + 当前系统时间
```

这样，在任意时刻调用 `get_clock()` 都能获取到精确的播放时间，而不需要每帧都更新时钟。

### 4.3 核心操作

```c
// 设置时钟：记录 pts 和当前系统时间
static void set_clock_at(Clock *c, double pts, int serial, double time)
{
    c->pts = pts;
    c->last_updated = time;
    c->pts_drift = c->pts - time;   // 计算漂移量
    c->serial = serial;
}

static void set_clock(Clock *c, double pts, int serial)
{
    double time = av_gettime_relative() / 1000000.0;  // 获取当前系统时间（秒）
    set_clock_at(c, pts, serial, time);
}

// 获取时钟：利用漂移量实时推算当前播放时间
static double get_clock(Clock *c)
{
    // 如果时钟的 serial 与队列的 serial 不一致，说明时钟已过期
    if (*c->queue_serial != c->serial)
        return NAN;
    if (c->paused) {
        return c->pts;     // 暂停时返回固定值
    } else {
        double time = av_gettime_relative() / 1000000.0;
        // 核心公式：利用 pts_drift 推算，并考虑播放速度
        return c->pts_drift + time - (time - c->last_updated) * (1.0 - c->speed);
    }
}

// 初始化时钟
static void init_clock(Clock *c, int *queue_serial)
{
    c->speed = 1.0;
    c->paused = 0;
    c->queue_serial = queue_serial;
    set_clock(c, NAN, -1);  // 初始为无效值
}
```

### 4.4 主时钟选择

ffplay 支持三种同步模式，通过 `get_master_sync_type()` 决定谁是主时钟：

```c
static int get_master_sync_type(VideoState *is) {
    if (is->av_sync_type == AV_SYNC_VIDEO_MASTER) {
        if (is->video_st)
            return AV_SYNC_VIDEO_MASTER;
        else
            return AV_SYNC_AUDIO_MASTER;   // 无视频时回退到音频主时钟
    } else if (is->av_sync_type == AV_SYNC_AUDIO_MASTER) {
        if (is->audio_st)
            return AV_SYNC_AUDIO_MASTER;
        else
            return AV_SYNC_EXTERNAL_CLOCK; // 无音频时回退到外部时钟
    } else {
        return AV_SYNC_EXTERNAL_CLOCK;
    }
}

// 获取主时钟的当前时间
static double get_master_clock(VideoState *is)
{
    switch (get_master_sync_type(is)) {
        case AV_SYNC_VIDEO_MASTER:
            return get_clock(&is->vidclk);
        case AV_SYNC_AUDIO_MASTER:
            return get_clock(&is->audclk);
        default:
            return get_clock(&is->extclk);
    }
}
```

注意**降级策略**：当选择的主时钟对应的流不存在时，会自动降级到其他时钟。

![Clock 时钟工作原理](https://gitee.com/yuhong1234/ffplay/raw/master/02-clock.png)

## 5. Decoder —— 解码器封装

`Decoder` 封装了解码器的状态，将 `AVCodecContext`、`PacketQueue` 和解码线程关联在一起。

### 5.1 结构体定义

```c
typedef struct Decoder {
    AVPacket *pkt;              // 当前正在处理的 packet
    PacketQueue *queue;         // 关联的输入 PacketQueue
    AVCodecContext *avctx;      // FFmpeg 解码器上下文
    int pkt_serial;             // 当前 packet 的序列号
    int finished;               // 解码完成标志（值 = 完成时的 serial）
    int packet_pending;         // 是否有待处理的 packet（send 失败时置 1）
    SDL_cond *empty_queue_cond; // 当队列为空时用于唤醒 read_thread
    int64_t start_pts;          // 起始 PTS（用于无时间戳格式的 PTS 推算）
    AVRational start_pts_tb;    // 起始 PTS 的时间基
    int64_t next_pts;           // 下一帧预期的 PTS（用于音频 PTS 推算）
    AVRational next_pts_tb;     // 下一帧 PTS 的时间基
    SDL_Thread *decoder_tid;    // 解码线程句柄
} Decoder;
```

### 5.2 初始化与启动

```c
// 初始化解码器
static int decoder_init(Decoder *d, AVCodecContext *avctx,
                        PacketQueue *queue, SDL_cond *empty_queue_cond)
{
    memset(d, 0, sizeof(Decoder));
    d->pkt = av_packet_alloc();
    d->avctx = avctx;
    d->queue = queue;
    d->empty_queue_cond = empty_queue_cond;
    d->start_pts = AV_NOPTS_VALUE;
    d->pkt_serial = -1;
    return 0;
}

// 启动解码线程
static int decoder_start(Decoder *d, int (*fn)(void *),
                         const char *thread_name, void *arg)
{
    packet_queue_start(d->queue);      // 启用 PacketQueue（清除 abort_request）
    d->decoder_tid = SDL_CreateThread(fn, thread_name, arg);  // 创建解码线程
    return 0;
}
```

### 5.3 终止与销毁

```c
// 中止解码器：发送中止信号并等待线程退出
static void decoder_abort(Decoder *d, FrameQueue *fq)
{
    packet_queue_abort(d->queue);    // 设置 PacketQueue 的 abort_request
    frame_queue_signal(fq);          // 唤醒可能阻塞在 FrameQueue 上的线程
    SDL_WaitThread(d->decoder_tid, NULL);  // 等待解码线程退出
    d->decoder_tid = NULL;
    packet_queue_flush(d->queue);    // 清空残留的 packet
}

// 销毁解码器
static void decoder_destroy(Decoder *d) {
    av_packet_free(&d->pkt);
    avcodec_free_context(&d->avctx);
}
```

## 6. AudioParams —— 音频参数

`AudioParams` 描述了音频流的格式参数，在音频重采样和格式协商中被广泛使用：

```c
typedef struct AudioParams {
    int freq;                    // 采样率（如 44100、48000）
    AVChannelLayout ch_layout;   // 声道布局（如立体声、5.1声道）
    enum AVSampleFormat fmt;     // 采样格式（如 AV_SAMPLE_FMT_S16）
    int frame_size;              // 一个采样帧的字节数（声道数 × 每采样字节数）
    int bytes_per_sec;           // 每秒字节数（采样率 × 帧大小）
} AudioParams;
```

在 VideoState 中有三个 AudioParams 实例：

```c
struct AudioParams audio_src;        // 解码器输出的音频格式（源格式）
struct AudioParams audio_filter_src; // 滤镜源格式
struct AudioParams audio_tgt;       // SDL 音频设备的目标格式
```

当 `audio_src` 和 `audio_tgt` 不一致时，就需要通过 `SwrContext` 进行重采样转换。

## 7. VideoState —— 上帝结构体

`VideoState` 是 ffplay 中最大、最重要的结构体，包含了播放器的**全部运行状态**。理解了它的成员分布，就理解了 ffplay 的全貌。

```c
typedef struct VideoState {
    // ========== 线程与控制 ==========
    SDL_Thread *read_tid;           // 读取线程句柄
    const AVInputFormat *iformat;   // 输入格式
    int abort_request;              // 全局退出标志
    int force_refresh;              // 强制刷新标志
    int paused;                     // 暂停状态
    int last_paused;                // 上次暂停状态（用于检测暂停状态变化）
    int queue_attachments_req;      // 请求发送 attached_pic（封面图）
    int seek_req;                   // Seek 请求标志
    int seek_flags;                 // Seek 标志
    int64_t seek_pos;               // Seek 目标位置
    int64_t seek_rel;               // Seek 相对偏移量
    int read_pause_return;          // RTSP 暂停返回值
    AVFormatContext *ic;            // 解复用上下文
    int realtime;                   // 是否为实时流

    // ========== 时钟系统 ==========
    Clock audclk;                   // 音频时钟
    Clock vidclk;                   // 视频时钟
    Clock extclk;                   // 外部时钟

    // ========== 帧队列（解码后） ==========
    FrameQueue pictq;               // 视频帧队列
    FrameQueue subpq;               // 字幕帧队列
    FrameQueue sampq;               // 音频帧队列

    // ========== 解码器 ==========
    Decoder auddec;                 // 音频解码器
    Decoder viddec;                 // 视频解码器
    Decoder subdec;                 // 字幕解码器

    // ========== 音频相关 ==========
    int audio_stream;               // 音频流索引
    int av_sync_type;               // 同步类型
    double audio_clock;             // 当前音频播放时间
    int audio_clock_serial;         // 音频时钟序列号
    double audio_diff_cum;          // 音频差异累积值（用于均值计算）
    double audio_diff_avg_coef;     // 差异均值系数
    double audio_diff_threshold;    // 同步纠正阈值
    int audio_diff_avg_count;       // 差异采样计数
    AVStream *audio_st;             // 音频流
    PacketQueue audioq;             // 音频包队列
    int audio_hw_buf_size;          // 硬件音频缓冲区大小
    uint8_t *audio_buf;             // 当前音频缓冲区指针
    uint8_t *audio_buf1;            // 重采样后的音频缓冲区
    unsigned int audio_buf_size;    // 音频缓冲区大小
    unsigned int audio_buf1_size;   // 重采样缓冲区大小
    int audio_buf_index;            // 当前读取位置
    int audio_write_buf_size;       // 未播放的数据大小
    int audio_volume;               // 音量 (0-128)
    int muted;                      // 是否静音
    struct AudioParams audio_src;   // 音频源参数
    struct AudioParams audio_filter_src;  // 滤镜源参数
    struct AudioParams audio_tgt;   // 音频目标参数
    struct SwrContext *swr_ctx;     // 重采样上下文
    int frame_drops_early;          // 早期丢帧计数（解码阶段）
    int frame_drops_late;           // 晚期丢帧计数（渲染阶段）

    // ========== 音频可视化 ==========
    enum ShowMode {
        SHOW_MODE_NONE = -1,
        SHOW_MODE_VIDEO = 0,
        SHOW_MODE_WAVES,            // 波形显示
        SHOW_MODE_RDFT,             // 频谱显示
        SHOW_MODE_NB
    } show_mode;
    int16_t sample_array[SAMPLE_ARRAY_SIZE]; // 音频采样缓冲
    int sample_array_index;
    int last_i_start;
    AVTXContext *rdft;              // RDFT 变换上下文
    av_tx_fn rdft_fn;
    int rdft_bits;
    float *real_data;
    AVComplexFloat *rdft_data;
    int xpos;
    double last_vis_time;
    SDL_Texture *vis_texture;       // 可视化纹理
    SDL_Texture *sub_texture;       // 字幕纹理
    SDL_Texture *vid_texture;       // 视频纹理

    // ========== 字幕相关 ==========
    int subtitle_stream;
    AVStream *subtitle_st;
    PacketQueue subtitleq;

    // ========== 视频相关 ==========
    double frame_timer;             // 视频帧定时器
    double frame_last_returned_time;
    double frame_last_filter_delay;
    int video_stream;
    AVStream *video_st;
    PacketQueue videoq;
    double max_frame_duration;      // 最大帧时长（超过则认为时间戳不连续）
    struct SwsContext *sub_convert_ctx; // 字幕像素格式转换
    int eof;                        // 文件结束标志

    char *filename;                 // 输入文件名
    int width, height, xleft, ytop; // 窗口尺寸和位置
    int step;                       // 单帧步进标志

    // ========== 滤镜系统 ==========
    int vfilter_idx;                // 当前视频滤镜索引
    AVFilterContext *in_video_filter;   // 视频滤镜链入口
    AVFilterContext *out_video_filter;  // 视频滤镜链出口
    AVFilterContext *in_audio_filter;   // 音频滤镜链入口
    AVFilterContext *out_audio_filter;  // 音频滤镜链出口
    AVFilterGraph *agraph;             // 音频滤镜图

    // ========== 流切换 ==========
    int last_video_stream, last_audio_stream, last_subtitle_stream;

    SDL_cond *continue_read_thread;    // read_thread 条件变量
} VideoState;
```

### 7.1 成员分组理解

VideoState 的 100+ 个成员可以分为 **8 大类**：

| 分组 | 核心成员 | 用途 |
|------|---------|------|
| 线程与控制 | `read_tid`, `abort_request`, `paused`, `seek_req` | 线程管理、播放控制 |
| 时钟系统 | `audclk`, `vidclk`, `extclk` | 音视频同步的时间基准 |
| 帧队列 | `pictq`, `subpq`, `sampq` | 解码后的数据缓冲 |
| 解码器 | `auddec`, `viddec`, `subdec` | 三路解码器 |
| 包队列 | `audioq`, `videoq`, `subtitleq` | 未解码的压缩数据缓冲 |
| 音频处理 | `audio_buf`, `swr_ctx`, `audio_tgt` | 音频重采样与输出 |
| 视频渲染 | `vid_texture`, `frame_timer`, `sub_convert_ctx` | 视频帧渲染与字幕叠加 |
| 滤镜系统 | `agraph`, `in_video_filter`, `out_audio_filter` | 音视频滤镜处理 |

![VideoState 成员分组](https://gitee.com/yuhong1234/ffplay/raw/master/02-videostate.png)

## 8. Serial 机制详解

serial 机制贯穿 PacketQueue、FrameQueue、Clock 和 Decoder，是 ffplay 处理 **seek 操作**的关键设计。

### 8.1 工作原理

1. **正常播放时**：所有 packet 打上相同的 serial（如 serial=1），解码器正常处理
2. **用户触发 seek 时**：
   - `packet_queue_flush()` 清空队列并执行 `serial++`（变为 serial=2）
   - 新读取的 packet 打上新的 serial=2
3. **解码器处理时**：
   - 从队列取出 packet，发现其 serial 与之前的不同
   - 调用 `avcodec_flush_buffers()` 清空解码器内部缓冲
   - 丢弃所有 serial 不匹配的旧数据
4. **时钟检查**：
   - `get_clock()` 会检查 `*c->queue_serial != c->serial`
   - 如果不一致，返回 `NAN`，表示时钟已失效

### 8.2 为什么需要 serial？

如果没有 serial 机制，seek 后可能出现以下问题：

- 解码器内部可能还缓存着 seek 前的帧，会被错误显示
- PacketQueue 中可能残留旧数据
- 时钟可能还维持着 seek 前的时间，导致同步错乱

serial 机制用一个简单的整数就优雅地解决了所有这些问题。

![Serial 机制工作原理](https://gitee.com/yuhong1234/ffplay/raw/master/02-serial.png)

## 9. FrameData —— 辅助数据传递

```c
typedef struct FrameData {
    int64_t pkt_pos;   // 对应 packet 在文件中的字节偏移
} FrameData;
```

`FrameData` 通过 `AVPacket->opaque_ref` / `AVFrame->opaque_ref` 在解码管线中传递附加信息。解码器的 `copy_opaque` 特性确保这些数据能从 packet 传递到解码出的 frame，这样在渲染阶段也能访问到原始 packet 的文件位置信息（用于 seek-by-bytes 模式）。

## 10. 小结

本篇深入分析了 ffplay 的六大核心数据结构：

- **PacketQueue**：基于 AVFifo 的线程安全 FIFO，连接读取线程与解码线程
- **FrameQueue**：固定大小的环形缓冲区，连接解码线程与渲染/输出
- **Clock**：通过 pts_drift 机制实现高精度实时时钟推算
- **Decoder**：将 AVCodecContext、PacketQueue 和解码线程打包在一起
- **VideoState**：包含 100+ 成员的"上帝结构体"，存储播放器全部状态
- **Serial 机制**：贯穿全局的序列号设计，优雅解决 seek 时的数据一致性问题

这些数据结构之间的关系可以用一句话概括：

> **read_thread 读取 packet → PacketQueue → Decoder 解码 → FrameQueue → 主线程渲染/音频回调输出，全程由 Clock 和 Serial 保驾护航。**

在下一篇文章中，我们将跟随数据流的方向，深入分析 `read_thread` ——解复用线程的工作机制。
