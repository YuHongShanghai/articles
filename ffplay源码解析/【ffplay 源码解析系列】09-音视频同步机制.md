# ffplay 源码解析系列（九）：音视频同步机制（核心篇）

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 这是本系列中最核心、最复杂的一篇。音视频同步是播放器的灵魂——没有它，视频和音频各跑各的，声画就会完全错乱。本篇将深入拆解 ffplay 的三时钟体系、视频刷新同步算法、音频补偿策略以及帧丢弃机制。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 为什么需要音视频同步？

在一个完整的播放器中，音频和视频是两条独立的处理流水线：

- **音频**：解码线程解码 → 音频回调函数从 FrameQueue 取帧 → SDL 音频设备播放
- **视频**：解码线程解码 → 主线程从 FrameQueue 取帧 → SDL 渲染到窗口

它们各自以不同的节奏运行：音频由声卡硬件驱动，按固定采样率消耗数据；视频由主线程定时刷新驱动，帧率可能不固定。如果不加任何同步控制，经过一段时间运行后，两者的累积误差会越来越大，最终导致：

- **口型对不上**：嘴巴动了但声音还没出来，或声音先到画面后到
- **动作与音效不同步**：爆炸的画面和爆炸的声音对不上
- **字幕时间错乱**：字幕提前或延迟显示

因此，播放器必须有一个**同步机制**——选定一个"基准时钟"，让另一方不断向它对齐。ffplay 的同步机制精巧而高效，是理解播放器架构的关键。

![三时钟同步模型](https://gitee.com/yuhong1234/ffplay/raw/master/09-sync-model.png)

## 2. Clock 时钟体系

ffplay 设计了一套优雅的时钟抽象。每个时钟实例记录了一个时间基准点，并能在任意时刻推算出当前时间。

### 2.1 Clock 结构体

```c
typedef struct Clock {
    double pts;           /* clock base - 时钟基准PTS */
    double pts_drift;     /* clock base minus time at which we updated the clock */
                          /* pts_drift = pts - last_updated，用于推算当前时钟值 */
    double last_updated;  /* 上次更新时钟的系统时间 */
    double speed;         /* 播放速度，1.0为正常速度 */
    int serial;           /* 时钟所基于的数据包的serial号 */
    int paused;           /* 是否暂停 */
    int *queue_serial;    /* 指向对应PacketQueue的serial */
} Clock;
```

ffplay 为 `VideoState` 维护了三个时钟实例：

| 时钟 | 字段 | 用途 |
|------|------|------|
| **音频时钟** | `is->audclk` | 跟踪音频播放进度 |
| **视频时钟** | `is->vidclk` | 跟踪视频显示进度 |
| **外部时钟** | `is->extclk` | 独立于音视频的参考时钟 |

### 2.2 时钟初始化：init_clock()

```c
static void init_clock(Clock *c, int *queue_serial)
{
    c->speed = 1.0;          // 默认正常速度
    c->paused = 0;           // 默认非暂停
    c->queue_serial = queue_serial;  // 关联到对应PacketQueue的serial
    set_clock(c, NAN, -1);   // 初始值设为NAN，serial设为-1（无效）
}
```

三个时钟分别关联到对应的 PacketQueue：

```c
init_clock(&is->vidclk, &is->videoq.serial);   // 视频时钟 → 视频队列serial
init_clock(&is->audclk, &is->audioq.serial);   // 音频时钟 → 音频队列serial
init_clock(&is->extclk, &is->extclk.serial);   // 外部时钟 → 自身serial
```

### 2.3 设置时钟：set_clock_at() / set_clock()

每次有新的 PTS 到来时，调用 `set_clock()` 更新时钟：

```c
static void set_clock_at(Clock *c, double pts, int serial, double time)
{
    c->pts = pts;                // 记录PTS值
    c->last_updated = time;      // 记录系统时间
    c->pts_drift = c->pts - time; // 关键：保存 pts 与系统时间的差值
    c->serial = serial;          // 记录serial号
}

static void set_clock(Clock *c, double pts, int serial)
{
    double time = av_gettime_relative() / 1000000.0;  // 获取当前系统时间（秒）
    set_clock_at(c, pts, serial, time);
}
```

`pts_drift` 是理解时钟推算的关键。它记录了"PTS 值与系统时间的差值"，后续 `get_clock()` 就靠这个差值来推算当前时刻的时钟值。

### 2.4 获取时钟：get_clock()

这是最精妙的部分——不需要每帧都更新时钟，通过 `pts_drift` 就能在任意时刻推算出当前时钟值：

```c
static double get_clock(Clock *c)
{
    // serial不匹配，说明数据已经过期，返回NAN
    if (*c->queue_serial != c->serial)
        return NAN;

    if (c->paused) {
        return c->pts;  // 暂停时，时钟冻结在最后的pts
    } else {
        double time = av_gettime_relative() / 1000000.0;
        // 核心推算公式：
        // clock = pts_drift + time - (time - last_updated) * (1.0 - speed)
        // 当 speed = 1.0 时简化为：clock = pts_drift + time = pts + (time - last_updated)
        return c->pts_drift + time - (time - c->last_updated) * (1.0 - c->speed);
    }
}
```

**推算原理**：

当 `speed = 1.0`（正常速度）时：

```
get_clock() = pts_drift + time
            = (pts - last_updated) + time
            = pts + (time - last_updated)
```

也就是说，当前时钟值 = 上次设置的 PTS + 从那以后经过的系统时间。这样就实现了时钟的"自由运行"——设置一次后，时钟会随系统时间自动前进。

当 `speed != 1.0` 时，公式会按播放速度缩放时间增量，支持变速播放。

### 2.5 主时钟选择

ffplay 支持三种同步模式，由 `-sync` 命令行参数控制：

```c
enum {
    AV_SYNC_AUDIO_MASTER,    /* 默认：以音频为主时钟 */
    AV_SYNC_VIDEO_MASTER,    /* 以视频为主时钟 */
    AV_SYNC_EXTERNAL_CLOCK,  /* 以外部时钟为主时钟 */
};
```

`get_master_sync_type()` 根据实际可用的流进行降级处理：

```c
static int get_master_sync_type(VideoState *is) {
    if (is->av_sync_type == AV_SYNC_VIDEO_MASTER) {
        if (is->video_st)
            return AV_SYNC_VIDEO_MASTER;   // 有视频流，使用视频主时钟
        else
            return AV_SYNC_AUDIO_MASTER;   // 无视频流，降级为音频主时钟
    } else if (is->av_sync_type == AV_SYNC_AUDIO_MASTER) {
        if (is->audio_st)
            return AV_SYNC_AUDIO_MASTER;   // 有音频流，使用音频主时钟
        else
            return AV_SYNC_EXTERNAL_CLOCK; // 无音频流，降级为外部时钟
    } else {
        return AV_SYNC_EXTERNAL_CLOCK;     // 外部时钟
    }
}
```

`get_master_clock()` 获取当前主时钟的值：

```c
static double get_master_clock(VideoState *is)
{
    double val;
    switch (get_master_sync_type(is)) {
        case AV_SYNC_VIDEO_MASTER:
            val = get_clock(&is->vidclk);
            break;
        case AV_SYNC_AUDIO_MASTER:
            val = get_clock(&is->audclk);
            break;
        default:
            val = get_clock(&is->extclk);
            break;
    }
    return val;
}
```

**为什么默认以音频为主时钟？** 因为人耳对声音不连续极其敏感（卡顿、断裂、杂音会非常明显），而人眼对视频帧的微小延迟感知较弱。所以让音频稳定输出，视频去追音频，是最佳策略。

## 3. video_refresh()：核心同步逻辑

`video_refresh()` 是整个同步机制的核心调度函数。它在主线程的事件循环中被周期性调用（每次最多等待 `REFRESH_RATE = 0.01` 秒），负责决定：**当前这一帧该不该显示？是等一等还是跳过？**

![video_refresh 核心决策流程](https://gitee.com/yuhong1234/ffplay/raw/master/09-video-refresh-flow.png)

### 3.1 完整源码与逐段分析

```c
/* called to display each frame */
static void video_refresh(void *opaque, double *remaining_time)
{
    VideoState *is = opaque;
    double time;
    Frame *sp, *sp2;

    // [1] 外部时钟速度调节（实时流场景）
    if (!is->paused && get_master_sync_type(is) == AV_SYNC_EXTERNAL_CLOCK && is->realtime)
        check_external_clock_speed(is);

    // [2] 音频可视化模式的刷新（非视频显示模式）
    if (!display_disable && is->show_mode != SHOW_MODE_VIDEO && is->audio_st) {
        time = av_gettime_relative() / 1000000.0;
        if (is->force_refresh || is->last_vis_time + rdftspeed < time) {
            video_display(is);
            is->last_vis_time = time;
        }
        *remaining_time = FFMIN(*remaining_time, is->last_vis_time + rdftspeed - time);
    }
```

前面这段处理两个特殊场景：外部时钟模式下的速度调节和音频可视化模式的刷新。核心逻辑从下面开始。

#### 步骤 1-2：获取帧并检查 serial

```c
    if (is->video_st) {
retry:
        if (frame_queue_nb_remaining(&is->pictq) == 0) {
            // 队列为空，没有可显示的帧，直接跳过
        } else {
            double last_duration, duration, delay;
            Frame *vp, *lastvp;

            /* dequeue the picture */
            lastvp = frame_queue_peek_last(&is->pictq);  // 上一帧（正在显示的帧）
            vp = frame_queue_peek(&is->pictq);            // 下一帧（待显示的帧）

            // serial检查：如果待显示帧的serial与队列当前serial不同，
            // 说明发生了seek等操作，这帧已过期，跳过它
            if (vp->serial != is->videoq.serial) {
                frame_queue_next(&is->pictq);
                goto retry;  // 继续检查下一帧
            }
```

这里的 `lastvp` 和 `vp` 分别代表"正在显示的帧"和"下一帧待显示的帧"。`frame_queue_peek_last()` 返回读指针前一个位置的帧（即上次 `frame_queue_next()` 之后保留的帧），`frame_queue_peek()` 返回读指针当前位置的帧。

#### 步骤 3-4：serial 变化处理与暂停检查

```c
            // serial变化时重置frame_timer
            // 这意味着发生了不连续（如seek），需要重新建立时间基准
            if (lastvp->serial != vp->serial)
                is->frame_timer = av_gettime_relative() / 1000000.0;

            // 暂停状态下直接跳到显示，不做同步计算
            if (is->paused)
                goto display;
```

`frame_timer` 记录了上一帧应该被显示的时间点。当 serial 发生变化（跨越了 seek 边界），旧的 `frame_timer` 已经没有意义，需要重置为当前时间。

#### 步骤 5-6：计算帧时长与目标延迟

```c
            /* compute nominal last_duration */
            last_duration = vp_duration(is, lastvp, vp);   // 上一帧的持续时长
            delay = compute_target_delay(last_duration, is); // 经过同步校正后的延迟
```

`vp_duration()` 计算两帧之间的时间差：

```c
static double vp_duration(VideoState *is, Frame *vp, Frame *nextvp) {
    if (vp->serial == nextvp->serial) {
        double duration = nextvp->pts - vp->pts;
        // 异常处理：NaN、负数、超过max_frame_duration都用编码器标称时长
        if (isnan(duration) || duration <= 0 || duration > is->max_frame_duration)
            return vp->duration;
        else
            return duration;
    } else {
        return 0.0;  // 跨serial的帧间距为0（立即切换）
    }
}
```

`compute_target_delay()` 是同步算法的核心，详见第 4 节。

#### 步骤 7：时间判断——是否该显示

```c
            time = av_gettime_relative() / 1000000.0;
            // 如果当前时间还没到 frame_timer + delay，说明还不该切换到下一帧
            if (time < is->frame_timer + delay) {
                // 设置remaining_time，告诉事件循环还需要等多久再来
                *remaining_time = FFMIN(is->frame_timer + delay - time, *remaining_time);
                goto display;  // 继续显示当前帧
            }
```

这是核心的时间判断：`frame_timer + delay` 是下一帧应该显示的时间点。如果当前时间还没到，就继续显示当前帧（lastvp），并设置 `remaining_time` 让主循环适时唤醒。

#### 步骤 8-9：更新 frame_timer 和视频时钟

```c
            // 更新frame_timer：累加delay
            is->frame_timer += delay;
            // 如果frame_timer严重落后（超过AV_SYNC_THRESHOLD_MAX），直接重置
            if (delay > 0 && time - is->frame_timer > AV_SYNC_THRESHOLD_MAX)
                is->frame_timer = time;

            // 更新视频时钟
            SDL_LockMutex(is->pictq.mutex);
            if (!isnan(vp->pts))
                update_video_pts(is, vp->pts, vp->serial);
            SDL_UnlockMutex(is->pictq.mutex);
```

`update_video_pts()` 不仅设置视频时钟，还会同步外部时钟：

```c
static void update_video_pts(VideoState *is, double pts, int serial)
{
    set_clock(&is->vidclk, pts, serial);
    sync_clock_to_slave(&is->extclk, &is->vidclk);  // 外部时钟跟随视频时钟
}
```

#### 步骤 10：Late frame drop（迟到帧丢弃）

```c
            // 如果队列中还有下一帧，检查当前帧是否已经来不及显示
            if (frame_queue_nb_remaining(&is->pictq) > 1) {
                Frame *nextvp = frame_queue_peek_next(&is->pictq);
                duration = vp_duration(is, vp, nextvp);
                // 条件：非单步模式 && 开启丢帧 && 当前时间已经超过了下一帧的显示时间
                if (!is->step
                    && (framedrop > 0 || (framedrop && get_master_sync_type(is) != AV_SYNC_VIDEO_MASTER))
                    && time > is->frame_timer + duration) {
                    is->frame_drops_late++;       // 统计迟到丢帧数
                    frame_queue_next(&is->pictq); // 跳过当前帧
                    goto retry;                   // 继续检查下一帧
                }
            }
```

这是**后期丢帧（Late Drop）**策略：如果一帧取出来发现已经过期了（连下一帧的显示时间都过了），就跳过它。这个循环可能连续丢弃多帧，直到找到一帧还来得及显示。

#### 步骤 11：字幕过期清理

```c
            // 清理过期字幕
            if (is->subtitle_st) {
                while (frame_queue_nb_remaining(&is->subpq) > 0) {
                    sp = frame_queue_peek(&is->subpq);

                    if (frame_queue_nb_remaining(&is->subpq) > 1)
                        sp2 = frame_queue_peek_next(&is->subpq);
                    else
                        sp2 = NULL;

                    // 三种清理条件：serial过期、显示时间结束、下一条字幕即将开始
                    if (sp->serial != is->subtitleq.serial
                            || (is->vidclk.pts > (sp->pts + ((float) sp->sub.end_display_time / 1000)))
                            || (sp2 && is->vidclk.pts > (sp2->pts + ((float) sp2->sub.start_display_time / 1000))))
                    {
                        if (sp->uploaded) {
                            // 清除已上传到纹理的字幕像素
                            int i;
                            for (i = 0; i < sp->sub.num_rects; i++) {
                                AVSubtitleRect *sub_rect = sp->sub.rects[i];
                                uint8_t *pixels;
                                int pitch, j;
                                if (!SDL_LockTexture(is->sub_texture, (SDL_Rect *)sub_rect,
                                                     (void **)&pixels, &pitch)) {
                                    for (j = 0; j < sub_rect->h; j++, pixels += pitch)
                                        memset(pixels, 0, sub_rect->w << 2);
                                    SDL_UnlockTexture(is->sub_texture);
                                }
                            }
                        }
                        frame_queue_next(&is->subpq);
                    } else {
                        break;
                    }
                }
            }
```

#### 步骤 12：最终显示

```c
            frame_queue_next(&is->pictq);   // 移动读指针，vp变为"当前显示帧"
            is->force_refresh = 1;          // 标记需要刷新

            // 单步模式下显示一帧后自动暂停
            if (is->step && !is->paused)
                stream_toggle_pause(is);
        }
display:
        /* display picture */
        if (!display_disable && is->force_refresh
            && is->show_mode == SHOW_MODE_VIDEO && is->pictq.rindex_shown)
            video_display(is);  // 真正执行渲染
    }
    is->force_refresh = 0;
```

### 3.2 关键时间变量关系

理解 `video_refresh()` 的关键在于把握几个时间变量的关系：

| 变量 | 含义 |
|------|------|
| `frame_timer` | 上一帧应该被显示的时间点 |
| `delay` | 经过同步校正后，上一帧到当前帧的延迟 |
| `frame_timer + delay` | 当前帧应该被显示的时间点 |
| `time` | 当前系统时间 |
| `remaining_time` | 主循环需要等待的时间 |

**判断逻辑**：

- `time < frame_timer + delay` → 还没到时间，继续等
- `time >= frame_timer + delay` → 该显示了，推进到下一帧
- `time > frame_timer + delay + next_duration` → 下一帧都过期了，丢帧

## 4. compute_target_delay()：延迟计算详解

这个函数是同步算法的精华，它根据视频时钟与主时钟的偏差，动态调整帧显示延迟：

```c
static double compute_target_delay(double delay, VideoState *is)
{
    double sync_threshold, diff = 0;

    /* update delay to follow master synchronisation source */
    if (get_master_sync_type(is) != AV_SYNC_VIDEO_MASTER) {
        /* if video is slave, we try to correct big delays by
           duplicating or deleting a frame */

        // 计算视频时钟与主时钟的偏差
        diff = get_clock(&is->vidclk) - get_master_clock(is);

        /* skip or repeat frame. We take into account the
           delay to compute the threshold. I still don't know
           if it is the best guess */

        // 动态同步阈值：在 [MIN, MAX] 范围内，取 delay 的值
        sync_threshold = FFMAX(AV_SYNC_THRESHOLD_MIN,
                               FFMIN(AV_SYNC_THRESHOLD_MAX, delay));

        if (!isnan(diff) && fabs(diff) < is->max_frame_duration) {
            if (diff <= -sync_threshold)
                // 情况1：视频落后（diff < 0），减小delay以加速追赶
                delay = FFMAX(0, delay + diff);
            else if (diff >= sync_threshold && delay > AV_SYNC_FRAMEDUP_THRESHOLD)
                // 情况2a：视频超前且delay较长，加上diff减速
                delay = delay + diff;
            else if (diff >= sync_threshold)
                // 情况2b：视频超前且delay较短，直接翻倍（复制帧）
                delay = 2 * delay;
            // 情况3：|diff| < sync_threshold，偏差在阈值内，不调整
        }
    }

    av_log(NULL, AV_LOG_TRACE, "video: delay=%0.3f A-V=%f\n",
            delay, -diff);

    return delay;
}
```

### 4.1 同步偏差 diff

```
diff = get_clock(&is->vidclk) - get_master_clock(is)
```

- `diff < 0`：视频时钟落后于主时钟 → 视频慢了，需要加速
- `diff > 0`：视频时钟超前于主时钟 → 视频快了，需要减速
- `diff ≈ 0`：基本同步，无需调整

### 4.2 动态同步阈值 sync_threshold

```c
sync_threshold = FFMAX(AV_SYNC_THRESHOLD_MIN, FFMIN(AV_SYNC_THRESHOLD_MAX, delay));
```

阈值范围被限制在 `[0.04, 0.1]` 秒之间，且与帧间隔 `delay` 相关。这样做的好处是：

- 对于高帧率视频（如 60fps，delay ≈ 0.017s），阈值取 0.04s，允许约 2 帧的偏差
- 对于低帧率视频（如 10fps，delay ≈ 0.1s），阈值取 0.1s，允许约 1 帧的偏差

偏差在阈值范围内就不做调整，避免频繁的微调导致画面抖动。

### 4.3 三种同步校正策略

**情况 1：视频落后（diff <= -sync_threshold）**

```c
delay = FFMAX(0, delay + diff);
```

`diff` 为负值，`delay + diff` 会减小甚至变为 0。效果是缩短等待时间，让视频帧更快地切换，追赶音频。极端情况下 delay 可以降到 0（立刻切换到下一帧）。

**情况 2a：视频超前 + 长帧间隔（diff >= sync_threshold && delay > AV_SYNC_FRAMEDUP_THRESHOLD）**

```c
delay = delay + diff;
```

`diff` 为正值，delay 增大。用于帧间隔较长的视频（比如 PPT 录屏、低帧率内容），精确地加上偏差值来减速。

**情况 2b：视频超前 + 短帧间隔（diff >= sync_threshold）**

```c
delay = 2 * delay;
```

直接将延迟翻倍，相当于"复制帧"——多显示一帧时间，让主时钟赶上来。这比精确计算更简单粗暴，但对于正常帧率的视频来说已经够用。

**情况 3：在阈值内（|diff| < sync_threshold）**

不调整 delay，保持原始帧间隔。这是大部分时间的正常状态。

### 4.4 关键常量

```c
#define AV_SYNC_THRESHOLD_MIN 0.04      // 最小同步阈值（40ms）
#define AV_SYNC_THRESHOLD_MAX 0.1       // 最大同步阈值（100ms）
#define AV_SYNC_FRAMEDUP_THRESHOLD 0.1  // 帧复制阈值（100ms）
#define AV_NOSYNC_THRESHOLD 10.0        // 超过10秒差距不做同步校正
```

- 同步阈值定义了"可容忍的偏差范围"
- 帧复制阈值决定了超前时是翻倍 delay 还是精确加 diff
- `max_frame_duration`（TS 流为 10 秒，其他为 3600 秒）防止异常时间戳导致错误校正

## 5. synchronize_audio()：音频同步补偿

当音频不是主时钟时（即 `AV_SYNC_VIDEO_MASTER` 或 `AV_SYNC_EXTERNAL_CLOCK` 模式），音频也需要向主时钟对齐。与视频通过调整显示时机不同，音频通过**调整采样数**来实现同步——增减每次输出的采样点数量，从而微调音频播放速度。

```c
/* return the wanted number of samples to get better sync if sync_type is video
 * or external master clock */
static int synchronize_audio(VideoState *is, int nb_samples)
{
    int wanted_nb_samples = nb_samples;

    /* if not master, then we try to remove or add samples to correct the clock */
    if (get_master_sync_type(is) != AV_SYNC_AUDIO_MASTER) {
        double diff, avg_diff;
        int min_nb_samples, max_nb_samples;

        // 计算音频时钟与主时钟的偏差
        diff = get_clock(&is->audclk) - get_master_clock(is);

        if (!isnan(diff) && fabs(diff) < AV_NOSYNC_THRESHOLD) {
            // 加权移动平均：用指数衰减累积偏差值
            // audio_diff_cum = diff + coef * audio_diff_cum
            // 新的diff权重最大，历史diff逐渐衰减
            is->audio_diff_cum = diff + is->audio_diff_avg_coef * is->audio_diff_cum;

            if (is->audio_diff_avg_count < AUDIO_DIFF_AVG_NB) {
                /* not enough measures to have a correct estimate */
                is->audio_diff_avg_count++;  // 积累不够，暂不校正
            } else {
                /* estimate the A-V difference */
                // 计算加权平均偏差
                avg_diff = is->audio_diff_cum * (1.0 - is->audio_diff_avg_coef);

                if (fabs(avg_diff) >= is->audio_diff_threshold) {
                    // 偏差超过阈值，调整采样数
                    wanted_nb_samples = nb_samples + (int)(diff * is->audio_src.freq);
                    // 限制调整幅度在 +/- SAMPLE_CORRECTION_PERCENT_MAX (10%) 范围内
                    min_nb_samples = ((nb_samples * (100 - SAMPLE_CORRECTION_PERCENT_MAX) / 100));
                    max_nb_samples = ((nb_samples * (100 + SAMPLE_CORRECTION_PERCENT_MAX) / 100));
                    wanted_nb_samples = av_clip(wanted_nb_samples, min_nb_samples, max_nb_samples);
                }
                av_log(NULL, AV_LOG_TRACE, "diff=%f adiff=%f sample_diff=%d apts=%0.3f %f\n",
                        diff, avg_diff, wanted_nb_samples - nb_samples,
                        is->audio_clock, is->audio_diff_threshold);
            }
        } else {
            /* too big difference : may be initial PTS errors, so
               reset A-V filter */
            is->audio_diff_avg_count = 0;  // 偏差太大，重置滤波器
            is->audio_diff_cum       = 0;
        }
    }

    return wanted_nb_samples;
}
```

### 5.1 加权移动平均原理

音频同步不是看到一次偏差就立即校正，而是通过**指数加权移动平均**（EWMA）来平滑偏差值，避免因为瞬时抖动导致频繁调整：

```
audio_diff_cum = diff + coef * audio_diff_cum
avg_diff = audio_diff_cum * (1.0 - coef)
```

其中 `coef = exp(log(0.01) / AUDIO_DIFF_AVG_NB)` 约等于 0.794，`AUDIO_DIFF_AVG_NB = 20`。也就是说，大约需要 20 次采样才能使滤波器的估计达到稳定。在此之前（`audio_diff_avg_count < 20`），不做校正。

### 5.2 采样数调整

```c
wanted_nb_samples = nb_samples + (int)(diff * is->audio_src.freq);
```

例如：采样率 48000Hz，偏差 diff = -0.01 秒（音频落后 10ms），则：

```
wanted_nb_samples = 1024 + (-0.01 * 48000) = 1024 - 480 = 544
```

输出更少的采样点，等效于音频加速播放，追赶主时钟。但调整幅度被限制在 +/- 10%（`SAMPLE_CORRECTION_PERCENT_MAX`），避免音质明显变化。

## 6. 帧丢弃策略

ffplay 实现了两级帧丢弃机制——**Early Drop**（早期丢弃）和 **Late Drop**（后期丢弃），构成了一道双保险。

![帧丢弃策略](https://gitee.com/yuhong1234/ffplay/raw/master/09-frame-drop.png)

### 6.1 Early Drop：解码后立即丢弃

在 `get_video_frame()` 中，帧刚解码完成就检查是否已经过期：

```c
static int get_video_frame(VideoState *is, AVFrame *frame)
{
    int got_picture;

    if ((got_picture = decoder_decode_frame(&is->viddec, frame, NULL)) < 0)
        return -1;

    if (got_picture) {
        double dpts = NAN;

        if (frame->pts != AV_NOPTS_VALUE)
            dpts = av_q2d(is->video_st->time_base) * frame->pts;

        frame->sample_aspect_ratio = av_guess_sample_aspect_ratio(is->ic, is->video_st, frame);

        // 丢帧判断
        if (framedrop > 0 || (framedrop && get_master_sync_type(is) != AV_SYNC_VIDEO_MASTER)) {
            if (frame->pts != AV_NOPTS_VALUE) {
                double diff = dpts - get_master_clock(is);
                if (!isnan(diff)                                // diff有效
                    && fabs(diff) < AV_NOSYNC_THRESHOLD         // 偏差在合理范围内
                    && diff - is->frame_last_filter_delay < 0   // 考虑滤镜延迟后仍然过期
                    && is->viddec.pkt_serial == is->vidclk.serial  // serial匹配
                    && is->videoq.nb_packets) {                 // 队列中还有数据
                    is->frame_drops_early++;   // 统计
                    av_frame_unref(frame);     // 释放帧
                    got_picture = 0;           // 标记为未获取到帧
                }
            }
        }
    }
    return got_picture;
}
```

**Early Drop 的优势**：帧还没有进入 FrameQueue，不会占用队列槽位。这对于解码速度远低于播放速度的场景尤其有用——尽早丢弃过期帧，让解码器把时间花在还来得及显示的帧上。

**五个判断条件**：

1. `diff` 有效（不是 NaN）
2. 偏差在 `AV_NOSYNC_THRESHOLD`（10 秒）范围内
3. 考虑滤镜延迟后，帧的 PTS 仍然早于主时钟（`diff - filter_delay < 0`）
4. serial 匹配（不是 seek 后的过期帧）
5. 队列中还有数据（确保不会丢光）

### 6.2 Late Drop：显示时刻丢弃

在 `video_refresh()` 中，帧已经从 FrameQueue 取出，但发现来不及显示：

```c
if (frame_queue_nb_remaining(&is->pictq) > 1) {
    Frame *nextvp = frame_queue_peek_next(&is->pictq);
    duration = vp_duration(is, vp, nextvp);
    if (!is->step
        && (framedrop > 0 || (framedrop && get_master_sync_type(is) != AV_SYNC_VIDEO_MASTER))
        && time > is->frame_timer + duration) {
        is->frame_drops_late++;
        frame_queue_next(&is->pictq);
        goto retry;
    }
}
```

**Late Drop 的特点**：帧已经在 FrameQueue 中了，此时丢弃虽然不如 Early Drop 高效，但能应对解码和显示之间的延迟波动。

### 6.3 两级丢帧的协作

| 属性 | Early Drop | Late Drop |
|------|------------|-----------|
| **发生位置** | `get_video_frame()`（解码线程） | `video_refresh()`（主线程） |
| **判断时机** | 解码完成后、入队前 | 从队列取出后、显示前 |
| **参考时钟** | 与主时钟比较 PTS | 与 frame_timer 比较系统时间 |
| **统计变量** | `frame_drops_early` | `frame_drops_late` |
| **优势** | 节省队列空间和后续处理开销 | 应对队列中的延迟波动 |

两者的统计值会在状态栏的 `fd=` 字段中求和显示。

## 7. 外部时钟同步

外部时钟模式（`AV_SYNC_EXTERNAL_CLOCK`）用于需要外部控制播放节奏的场景。它的核心机制是根据缓冲区充盈度动态调节播放速度。

### 7.1 check_external_clock_speed()

```c
static void check_external_clock_speed(VideoState *is) {
   // 情况1：缓冲区数据不足，降速以减少消耗
   if (is->video_stream >= 0 && is->videoq.nb_packets <= EXTERNAL_CLOCK_MIN_FRAMES ||
       is->audio_stream >= 0 && is->audioq.nb_packets <= EXTERNAL_CLOCK_MIN_FRAMES) {
       set_clock_speed(&is->extclk,
           FFMAX(EXTERNAL_CLOCK_SPEED_MIN, is->extclk.speed - EXTERNAL_CLOCK_SPEED_STEP));
   }
   // 情况2：缓冲区数据充足，加速以加快消耗
   else if ((is->video_stream < 0 || is->videoq.nb_packets > EXTERNAL_CLOCK_MAX_FRAMES) &&
            (is->audio_stream < 0 || is->audioq.nb_packets > EXTERNAL_CLOCK_MAX_FRAMES)) {
       set_clock_speed(&is->extclk,
           FFMIN(EXTERNAL_CLOCK_SPEED_MAX, is->extclk.speed + EXTERNAL_CLOCK_SPEED_STEP));
   }
   // 情况3：缓冲区适中，速度向1.0回归
   else {
       double speed = is->extclk.speed;
       if (speed != 1.0)
           set_clock_speed(&is->extclk,
               speed + EXTERNAL_CLOCK_SPEED_STEP * (1.0 - speed) / fabs(1.0 - speed));
   }
}
```

### 7.2 相关常量

```c
#define EXTERNAL_CLOCK_MIN_FRAMES 2      // 缓冲区下限
#define EXTERNAL_CLOCK_MAX_FRAMES 10     // 缓冲区上限
#define EXTERNAL_CLOCK_SPEED_MIN  0.900  // 最慢 0.9 倍速
#define EXTERNAL_CLOCK_SPEED_MAX  1.010  // 最快 1.01 倍速
#define EXTERNAL_CLOCK_SPEED_STEP 0.001  // 每次调整步长
```

速度调节范围 [0.9, 1.01] 的不对称设计是有意为之：降速空间（10%）大于加速空间（1%），这是因为实时流场景下更容易出现缓冲不足，需要更大的降速能力来适应网络波动。

### 7.3 sync_clock_to_slave()

```c
static void sync_clock_to_slave(Clock *c, Clock *slave)
{
    double clock = get_clock(c);
    double slave_clock = get_clock(slave);
    // 如果从时钟有效，且主时钟无效或偏差过大，则将主时钟同步到从时钟
    if (!isnan(slave_clock) && (isnan(clock) || fabs(clock - slave_clock) > AV_NOSYNC_THRESHOLD))
        set_clock(c, slave_clock, slave->serial);
}
```

这个函数用于让外部时钟跟随音频/视频时钟。它在 `update_video_pts()` 和音频输出回调中被调用，确保外部时钟不会偏离实际播放进度太远。

## 8. 暂停对同步的影响

暂停和恢复看似简单，但对同步机制的影响需要仔细处理。

### 8.1 stream_toggle_pause()

```c
static void stream_toggle_pause(VideoState *is)
{
    if (is->paused) {
        // 从暂停恢复播放时，需要补偿暂停期间的时间流逝
        // frame_timer 累加暂停持续时间，避免恢复后认为帧已过期
        is->frame_timer += av_gettime_relative() / 1000000.0 - is->vidclk.last_updated;

        // 如果是网络暂停（RTSP PAUSE），恢复视频时钟的运行状态
        if (is->read_pause_return != AVERROR(ENOSYS)) {
            is->vidclk.paused = 0;
        }

        // 重新设置视频时钟（刷新 pts_drift）
        set_clock(&is->vidclk, get_clock(&is->vidclk), is->vidclk.serial);
    }

    // 同步更新外部时钟
    set_clock(&is->extclk, get_clock(&is->extclk), is->extclk.serial);

    // 翻转所有暂停标志
    is->paused = is->audclk.paused = is->vidclk.paused = is->extclk.paused = !is->paused;
}
```

**关键补偿逻辑**：恢复播放时，`frame_timer` 需要加上暂停持续的时间（`当前时间 - vidclk.last_updated`）。否则，暂停 5 秒后恢复，`video_refresh()` 会认为 `frame_timer` 落后了 5 秒，导致疯狂丢帧。

暂停时，`get_clock()` 检测到 `paused` 标志后直接返回 `pts`，时钟冻结。恢复时通过 `set_clock()` 重新计算 `pts_drift`，使时钟从暂停点继续运行。

### 8.2 暂停时 video_refresh() 的处理

```c
if (is->paused)
    goto display;
```

在 `video_refresh()` 中，暂停状态直接跳到 `display` 标签。此时显示的是 `lastvp`（当前帧），画面静止不动。由于不执行 `frame_queue_next()`，帧队列的读指针也不会移动。

## 9. 同步机制的全景视图

让我们把所有同步相关的组件串联起来，看看它们如何协同工作：

### 9.1 默认模式（音频主时钟）下的同步流程

1. **音频回调**（`sdl_audio_callback`）持续消耗音频数据，每次输出音频帧后更新 `audclk`
2. **视频主循环**（`video_refresh`）周期性检查：
   - 从 `pictq` 取出待显示帧
   - 计算视频时钟与音频时钟的偏差
   - 通过 `compute_target_delay()` 调整帧显示延迟
   - 太快就多等（增大 delay），太慢就加速（减小 delay 甚至丢帧）
3. **帧丢弃**作为兜底：
   - Early Drop 在解码阶段剔除过期帧
   - Late Drop 在显示阶段丢弃迟到帧

### 9.2 关键设计原则

1. **时钟解耦**：三个时钟独立维护，通过 `get_master_clock()` 统一对外提供参考
2. **渐进校正**：同步校正是渐进式的（每帧微调 delay），不是突变式的，保证视觉流畅
3. **双阈值保护**：只在偏差超过 `sync_threshold` 时才校正，避免过度调整；偏差超过 `AV_NOSYNC_THRESHOLD` 则放弃校正
4. **优雅降级**：当请求的同步源不可用时，自动降级到次优选择
5. **暂停补偿**：暂停/恢复时正确补偿时间差，避免状态突变

## 10. 总结

音视频同步是 ffplay 最精妙的部分。它用不到 200 行核心代码（`compute_target_delay` + `video_refresh` 的同步部分 + `synchronize_audio`），实现了一个鲁棒、高效的同步引擎。核心思想可以归纳为：

- **选定基准**：默认以音频为主时钟（人耳敏感）
- **持续追踪**：通过 `pts_drift` 机制让时钟自由运行，只在关键节点更新
- **动态调整**：根据偏差大小，在"正常/加速/减速/丢帧"之间平滑切换
- **双重保险**：Early Drop + Late Drop 确保视频不会严重落后

理解了这套机制，你就掌握了播放器最核心的技术。后续的滤镜系统、快进快退等功能都建立在这套同步体系之上。
