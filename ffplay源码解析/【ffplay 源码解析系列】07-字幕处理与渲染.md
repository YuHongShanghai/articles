# ffplay 源码解析系列（七）：字幕处理与渲染

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 字幕是多媒体播放中不可或缺的一环。本篇深入分析 ffplay 对字幕的完整处理链路：从解码、入队、渲染叠加到过期清理。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 字幕类型简介

在多媒体领域，字幕大致分为两大类：

### 1.1 Bitmap 字幕（图形字幕）

Bitmap 字幕以图像形式存储，每条字幕实际上是一张带透明通道的小图片。常见格式包括：

- **DVD 字幕（VobSub）**：MPEG-2 PS 中的 DVD 字幕流，像素格式为 PAL8（调色板索引）
- **Blu-ray PGS 字幕**：HDMV Presentation Graphic Stream，常见于蓝光碟
- **DVB 字幕**：数字电视广播中的图形字幕

这类字幕的特点是：解码后直接得到像素数据（`AVSubtitleRect`），渲染时只需做像素格式转换再叠加到视频帧上。

### 1.2 Text 字幕（文本字幕）

Text 字幕以文本形式存储，需要经过文字排版和渲染才能变成可显示的图像：

- **SRT**：最常见的纯文本字幕，支持简单的 HTML 标签
- **ASS/SSA**：支持丰富的样式、定位、特效
- **WebVTT**：Web 环境下的字幕格式

### 1.3 ffplay 的选择

ffplay 内置只支持 bitmap 字幕的直接渲染。在 `subtitle_thread()` 中有一个关键判断：

```c
if (got_subtitle && sp->sub.format == 0) {
    // format==0 表示 bitmap 字幕，入队渲染
    // ...
    frame_queue_push(&is->subpq);
} else if (got_subtitle) {
    // format!=0（text 字幕），直接释放，不渲染
    avsubtitle_free(&sp->sub);
}
```

这里 `format == 0` 对应 `SUBTITLE_BITMAP`，`format == 1` 对应 `SUBTITLE_TEXT/ASS`。

对于 text 字幕，ffplay 需要借助 libavfilter 中的 subtitles 滤镜进行处理，通过命令行参数 `-vf subtitles=xxx.srt` 使用，后文会详细说明。

![字幕处理完整数据流](https://gitee.com/yuhong1234/ffplay/raw/master/07-subtitle-data-flow.png)

## 2. subtitle_thread：字幕解码线程

字幕解码线程在 `stream_component_open()` 中被创建，与音频、视频解码线程并行工作。其完整实现如下（ffplay.c 行 2263-2295）：

```c
static int subtitle_thread(void *arg)
{
    VideoState *is = arg;
    Frame *sp;
    int got_subtitle;
    double pts;

    for (;;) {
        // 从 subpq 获取一个可写帧槽位（可能阻塞等待空位）
        if (!(sp = frame_queue_peek_writable(&is->subpq)))
            return 0;  // 队列已关闭，退出线程

        // 解码一帧字幕（内部调用 avcodec_decode_subtitle2）
        if ((got_subtitle = decoder_decode_frame(&is->subdec, NULL, &sp->sub)) < 0)
            break;

        pts = 0;

        // 🔑 format==0 表示 bitmap 字幕，才入队
        if (got_subtitle && sp->sub.format == 0) {
            if (sp->sub.pts != AV_NOPTS_VALUE)
                pts = sp->sub.pts / (double)AV_TIME_BASE;  // 时间戳转秒
            sp->pts = pts;
            sp->serial = is->subdec.pkt_serial;  // 继承 serial（用于 seek 判断）
            sp->width = is->subdec.avctx->width;
            sp->height = is->subdec.avctx->height;
            sp->uploaded = 0;  // 标记未上传到纹理

            /* 入队，通知渲染端 */
            frame_queue_push(&is->subpq);
        } else if (got_subtitle) {
            // text 字幕（format!=0），无法直接渲染，释放资源
            avsubtitle_free(&sp->sub);
        }
    }
    return 0;
}
```

### 2.1 解码 API：avcodec_decode_subtitle2

值得注意的是，字幕解码使用的是旧式 API `avcodec_decode_subtitle2()`，而不是音视频使用的 `avcodec_send_packet()` / `avcodec_receive_frame()` 新 API。这是因为 FFmpeg 至今未将字幕解码迁移到新的编解码 API，字幕仍然使用同步的一进一出解码模式。

在 `decoder_decode_frame()` 内部的字幕解码路径如下（ffplay.c 行 645-656）：

```c
if (d->avctx->codec_type == AVMEDIA_TYPE_SUBTITLE) {
    int got_frame = 0;
    // 旧式同步解码 API：输入一个 packet，同步输出一个 subtitle
    ret = avcodec_decode_subtitle2(d->avctx, sub, &got_frame, d->pkt);
    if (ret < 0) {
        ret = AVERROR(EAGAIN);
    } else {
        if (got_frame && !d->pkt->data) {
            d->packet_pending = 1;  // 空包触发了输出，标记为 pending
        }
        ret = got_frame ? 0 : (d->pkt->data ? AVERROR(EAGAIN) : AVERROR_EOF);
    }
    av_packet_unref(d->pkt);
}
```

### 2.2 AVSubtitle 结构体

解码后的字幕存储在 `AVSubtitle` 结构体中：

```c
typedef struct AVSubtitle {
    uint16_t format;             // 0=bitmap, 1=text
    uint32_t start_display_time; // 相对于 pts 的开始显示偏移（毫秒）
    uint32_t end_display_time;   // 相对于 pts 的结束显示偏移（毫秒）
    unsigned num_rects;          // 字幕矩形区域数量
    AVSubtitleRect **rects;      // 字幕矩形数组
    int64_t pts;                 // 显示时间戳（AV_TIME_BASE 单位）
} AVSubtitle;
```

每个 `AVSubtitleRect` 包含一个字幕矩形区域的位置和像素数据：

```c
typedef struct AVSubtitleRect {
    int x, y;                 // 矩形左上角坐标
    int w, h;                 // 矩形宽高
    int nb_colors;            // 调色板颜色数（PAL8 时有效）
    uint8_t *data[4];         // 像素数据（PAL8：data[0]=索引，data[1]=调色板）
    int linesize[4];          // 行字节数
    enum AVSubtitleType type; // SUBTITLE_BITMAP / SUBTITLE_TEXT / SUBTITLE_ASS
    char *text;               // 纯文本（SUBTITLE_TEXT 时有效）
    char *ass;                // ASS 标记文本（SUBTITLE_ASS 时有效）
} AVSubtitleRect;
```

### 2.3 subpq 队列

字幕帧队列 `subpq` 的大小为 `SUBPICTURE_QUEUE_SIZE = 16`，远大于视频帧队列（3）。这是因为字幕的显示时间较长（通常几秒），需要更多的缓冲来实现平滑的字幕切换。

`Frame` 结构体中与字幕相关的字段：

```c
typedef struct Frame {
    AVFrame *frame;
    AVSubtitle sub;    // 字幕数据
    int serial;        // 用于 seek 时判断字幕是否过期
    double pts;        // 字幕 PTS（秒）
    int width;         // 字幕区域宽度
    int height;        // 字幕区域高度
    int uploaded;      // 是否已上传到 SDL 纹理
    // ...
} Frame;
```

## 3. video_image_display：字幕叠加渲染

字幕的渲染发生在 `video_image_display()` 函数中（ffplay.c 行 963-1050），它在每次绘制视频帧时被调用。

### 3.1 整体流程

渲染字幕的步骤为：

1. 检查当前是否有字幕流
2. 从 `subpq` 取出队首字幕帧
3. 判断当前视频帧的 PTS 是否已到达字幕显示时间
4. 将 bitmap 字幕从 PAL8 转换为 BGRA 像素格式
5. 写入 SDL sub_texture
6. 叠加渲染到视频帧上方

### 3.2 时间判断与纹理上传

```c
static void video_image_display(VideoState *is)
{
    Frame *vp;
    Frame *sp = NULL;
    SDL_Rect rect;

    vp = frame_queue_peek_last(&is->pictq);  // 取当前视频帧

    // === 字幕处理 ===
    if (is->subtitle_st) {
        if (frame_queue_nb_remaining(&is->subpq) > 0) {
            sp = frame_queue_peek(&is->subpq);  // 取队首字幕帧

            // 🔑 时间判断：视频帧 PTS >= 字幕 PTS + start_display_time
            if (vp->pts >= sp->pts + ((float) sp->sub.start_display_time / 1000)) {
                if (!sp->uploaded) {
                    // 首次显示，需要上传纹理
                    uint8_t* pixels[4];
                    int pitch[4];

                    if (!sp->width || !sp->height) {
                        sp->width = vp->width;   // 没有字幕尺寸时用视频尺寸
                        sp->height = vp->height;
                    }

                    // 分配/复用 ARGB8888 纹理
                    if (realloc_texture(&is->sub_texture,
                            SDL_PIXELFORMAT_ARGB8888,
                            sp->width, sp->height,
                            SDL_BLENDMODE_BLEND, 1) < 0)
                        return;
```

时间判断公式 `vp->pts >= sp->pts + start_display_time/1000` 非常关键：它确保字幕只在正确的时间点开始显示。`start_display_time` 是相对于 `pts` 的偏移量，单位为毫秒，因此需要除以 1000 转为秒。

### 3.3 PAL8 到 BGRA 的像素格式转换

Bitmap 字幕解码后的像素格式为 PAL8（8 位调色板索引），而 SDL 纹理需要 ARGB8888/BGRA 格式。ffplay 使用 swscale 进行转换：

```c
                    for (i = 0; i < sp->sub.num_rects; i++) {
                        AVSubtitleRect *sub_rect = sp->sub.rects[i];

                        // 裁剪坐标，防止越界
                        sub_rect->x = av_clip(sub_rect->x, 0, sp->width );
                        sub_rect->y = av_clip(sub_rect->y, 0, sp->height);
                        sub_rect->w = av_clip(sub_rect->w, 0, sp->width  - sub_rect->x);
                        sub_rect->h = av_clip(sub_rect->h, 0, sp->height - sub_rect->y);

                        // 🔑 创建/复用 swscale 上下文：PAL8 → BGRA
                        is->sub_convert_ctx = sws_getCachedContext(
                            is->sub_convert_ctx,
                            sub_rect->w, sub_rect->h, AV_PIX_FMT_PAL8,   // 源格式
                            sub_rect->w, sub_rect->h, AV_PIX_FMT_BGRA,   // 目标格式
                            0, NULL, NULL, NULL);

                        // 锁定纹理对应区域，获取像素写入地址
                        if (!SDL_LockTexture(is->sub_texture,
                                (SDL_Rect *)sub_rect, (void **)pixels, pitch)) {
                            // 🔑 执行像素格式转换，直接写入纹理内存
                            sws_scale(is->sub_convert_ctx,
                                      (const uint8_t * const *)sub_rect->data,
                                      sub_rect->linesize,
                                      0, sub_rect->h,
                                      pixels, pitch);
                            SDL_UnlockTexture(is->sub_texture);
                        }
                    }
                    // 标记已上传，避免重复转换
                    sp->uploaded = 1;
                }
            } else
                sp = NULL;  // 字幕还没到显示时间
        }
    }
```

注意这里使用 `sws_getCachedContext` 而非 `sws_getContext`，可以在参数不变时复用已有的 swscale 上下文，避免频繁创建和销毁。

`uploaded` 标记是一个重要的优化：字幕通常会持续显示数秒，每次调用 `video_image_display()` 时无需重新转换和上传像素数据。

### 3.4 SDL_RenderCopy 叠加渲染

纹理上传完成后，渲染阶段将字幕叠加到视频帧上方：

```c
    // 先渲染视频帧
    SDL_RenderCopyEx(renderer, is->vid_texture, NULL, &rect,
                     0, NULL, vp->flip_v ? SDL_FLIP_VERTICAL : 0);

    // 再叠加字幕
    if (sp) {
#if USE_ONEPASS_SUBTITLE_RENDER
        // 一次性渲染：将整个字幕纹理叠加到视频区域
        SDL_RenderCopy(renderer, is->sub_texture, NULL, &rect);
#else
        // 逐矩形渲染：按比例缩放每个字幕矩形
        int i;
        double xratio = (double)rect.w / (double)sp->width;
        double yratio = (double)rect.h / (double)sp->height;
        for (i = 0; i < sp->sub.num_rects; i++) {
            SDL_Rect *sub_rect = (SDL_Rect*)sp->sub.rects[i];
            SDL_Rect target = {
                .x = rect.x + sub_rect->x * xratio,
                .y = rect.y + sub_rect->y * yratio,
                .w = sub_rect->w * xratio,
                .h = sub_rect->h * yratio
            };
            SDL_RenderCopy(renderer, is->sub_texture, sub_rect, &target);
        }
#endif
    }
```

### 3.5 USE_ONEPASS_SUBTITLE_RENDER 宏

ffplay 在源码开头定义了：

```c
#define USE_ONEPASS_SUBTITLE_RENDER 1
```

默认值为 1，表示使用一次性渲染模式。两种模式的区别：

| 模式 | 特点 |
|------|------|
| 一次性渲染（默认） | 将整个 sub_texture 缩放叠加到视频区域，简单高效 |
| 逐矩形渲染 | 逐个处理每个字幕矩形，对每个矩形单独计算缩放比例 |

一次性渲染的前提是 sub_texture 的尺寸与字幕参考分辨率一致，SDL 在 RenderCopy 时会自动完成缩放适配。

## 4. video_refresh 中的字幕过期清理

字幕有明确的显示时长（`start_display_time` 到 `end_display_time`），过期后需要清理。这个逻辑在 `video_refresh()` 中（ffplay.c 行 1657-1689）：

```c
if (is->subtitle_st) {
    while (frame_queue_nb_remaining(&is->subpq) > 0) {
        sp = frame_queue_peek(&is->subpq);

        if (frame_queue_nb_remaining(&is->subpq) > 1)
            sp2 = frame_queue_peek_next(&is->subpq);  // 窥探下一帧
        else
            sp2 = NULL;

        // 🔑 三个出队条件（满足任一即可）：
        // 1. serial 不匹配（seek 后字幕已过期）
        // 2. 当前视频时间超过字幕的 end_display_time
        // 3. 下一条字幕的 start_display_time 已到达
        if (sp->serial != is->subtitleq.serial
                || (is->vidclk.pts > (sp->pts + ((float) sp->sub.end_display_time / 1000)))
                || (sp2 && is->vidclk.pts > (sp2->pts + ((float) sp2->sub.start_display_time / 1000))))
        {
            // 如果字幕已上传到纹理，需要清除对应区域
            if (sp->uploaded) {
                int i;
                for (i = 0; i < sp->sub.num_rects; i++) {
                    AVSubtitleRect *sub_rect = sp->sub.rects[i];
                    uint8_t *pixels;
                    int pitch, j;

                    if (!SDL_LockTexture(is->sub_texture,
                            (SDL_Rect *)sub_rect, (void **)&pixels, &pitch)) {
                        // 🔑 将字幕区域像素清零（透明）
                        for (j = 0; j < sub_rect->h; j++, pixels += pitch)
                            memset(pixels, 0, sub_rect->w << 2);  // <<2 即 *4（ARGB=4字节/像素）
                        SDL_UnlockTexture(is->sub_texture);
                    }
                }
            }
            // 出队，释放字幕帧
            frame_queue_next(&is->subpq);
        } else {
            break;  // 当前字幕仍在有效期内，停止检查
        }
    }
}
```

### 4.1 三个出队条件详解

**条件一：serial 不匹配**

```c
sp->serial != is->subtitleq.serial
```

当用户执行 seek 操作时，PacketQueue 的 serial 会递增。如果字幕帧的 serial 与当前队列的 serial 不同，说明这是 seek 之前的旧字幕，必须丢弃。

**条件二：显示时间已过**

```c
is->vidclk.pts > (sp->pts + ((float) sp->sub.end_display_time / 1000))
```

当前视频时钟超过了字幕的结束显示时间，字幕自然过期。

**条件三：下一条字幕已到达**

```c
sp2 && is->vidclk.pts > (sp2->pts + ((float) sp2->sub.start_display_time / 1000))
```

即使当前字幕还没"自然结束"，如果下一条字幕已经到了开始显示的时间，也要将当前字幕出队，为新字幕让路。

### 4.2 纹理清除

清除操作使用 `memset(pixels, 0, sub_rect->w << 2)` 将对应区域的像素全部置零。`<< 2` 相当于乘以 4，因为 ARGB8888 每个像素占 4 字节。全零意味着 RGBA 各通道均为 0，即完全透明，不会影响后续的视频帧渲染。

## 5. 字幕时间轴模型

理解 ffplay 的字幕时间计算，需要搞清楚 `pts`、`start_display_time` 和 `end_display_time` 三者的关系。

![字幕时间轴与显示窗口](https://gitee.com/yuhong1234/ffplay/raw/master/07-subtitle-timeline.png)

### 5.1 时间参数关系

```
绝对显示开始时间 = pts + start_display_time / 1000
绝对显示结束时间 = pts + end_display_time / 1000
显示持续时长    = (end_display_time - start_display_time) / 1000
```

- `pts`：字幕的基准时间戳，单位为秒（由 `AVSubtitle.pts / AV_TIME_BASE` 转换得到）
- `start_display_time`：相对于 `pts` 的开始显示偏移，单位为毫秒。通常为 0
- `end_display_time`：相对于 `pts` 的结束显示偏移，单位为毫秒

### 5.2 典型示例

一条 SRT 字幕：

```
1
00:01:30,000 --> 00:01:35,000
Hello, World!
```

对应的 `AVSubtitle` 字段值大约为：

| 字段 | 值 | 说明 |
|------|-----|------|
| pts | 90,000,000 | 90秒 x AV_TIME_BASE |
| start_display_time | 0 ms | 从 pts 时刻开始显示 |
| end_display_time | 5000 ms | 从 pts 起 5 秒后停止显示 |

因此：
- 开始显示时间 = 90.0 + 0/1000 = 90.0 秒
- 结束显示时间 = 90.0 + 5000/1000 = 95.0 秒

### 5.3 在代码中的使用

渲染时（`video_image_display`）：

```c
// 判断是否开始显示
vp->pts >= sp->pts + ((float) sp->sub.start_display_time / 1000)
```

清理时（`video_refresh`）：

```c
// 判断是否已过期
is->vidclk.pts > (sp->pts + ((float) sp->sub.end_display_time / 1000))
```

## 6. 局限性与扩展

### 6.1 ffplay 内置字幕渲染的局限

ffplay 内置的字幕渲染仅支持 bitmap 字幕：

- **不支持 SRT/ASS 等文本字幕**的直接渲染（`format != 0` 时直接丢弃）
- **不支持字幕样式**（如 ASS 的颜色、字体、定位特效等）
- **不支持多行文本排版**

这些局限源于 ffplay 定位为一个简单的参考播放器，而非功能完整的播放器。

### 6.2 使用 subtitles 滤镜处理文本字幕

对于 SRT、ASS 等文本字幕，ffplay 可通过 libavfilter 中的 subtitles 滤镜来处理：

```bash
# 加载外部 SRT 字幕
ffplay video.mp4 -vf subtitles=subtitle.srt

# 加载外部 ASS 字幕
ffplay video.mp4 -vf subtitles=subtitle.ass

# 加载内嵌字幕（指定流索引）
ffplay video.mkv -vf subtitles=video.mkv:si=0

# 设置字幕样式（对 SRT 生效）
ffplay video.mp4 -vf "subtitles=subtitle.srt:force_style='FontSize=24,PrimaryColour=&H00FFFFFF'"
```

subtitles 滤镜的工作原理：

1. 在视频滤镜图中插入 subtitles 滤镜
2. 滤镜内部使用 libass 库进行文本渲染
3. 将渲染后的文字图像叠加到视频帧上
4. 输出的视频帧已经包含字幕，不需要 ffplay 的字幕渲染流程

### 6.3 ass 滤镜

除了 subtitles 滤镜，FFmpeg 还提供 ass 滤镜，专门处理 ASS 格式字幕：

```bash
# 使用 ass 滤镜
ffplay video.mp4 -vf ass=subtitle.ass
```

两者区别：

| 特性 | subtitles 滤镜 | ass 滤镜 |
|------|---------------|---------|
| 支持格式 | SRT、ASS、SSA 等多种格式 | 仅 ASS/SSA |
| 内嵌字幕 | 支持（通过 si= 指定流） | 不支持 |
| 底层实现 | libass | libass |
| 适用场景 | 通用 | ASS 专用场景 |

## 7. 小结

本篇详细分析了 ffplay 的字幕处理全链路：

- **解码阶段**：`subtitle_thread` 通过旧式 `avcodec_decode_subtitle2` API 解码字幕，只有 bitmap 字幕（`format==0`）才会入队 `subpq`
- **渲染阶段**：`video_image_display` 在每帧绘制时检查字幕时间，将 PAL8 像素通过 swscale 转换为 BGRA，上传到 `sub_texture` 并叠加渲染
- **清理阶段**：`video_refresh` 检查 serial 和时间戳，将过期字幕从队列移除，并清零纹理区域
- **时间模型**：字幕的显示窗口由 `pts + start_display_time` 到 `pts + end_display_time` 确定
- **扩展方式**：文本字幕通过 `-vf subtitles` 或 `-vf ass` 滤镜处理

ffplay 的字幕处理虽然功能有限，但其代码清晰地展示了字幕渲染的核心流程：解码、时间同步、像素转换、纹理叠加和过期清理。这对于理解专业播放器的字幕系统有很好的参考价值。
