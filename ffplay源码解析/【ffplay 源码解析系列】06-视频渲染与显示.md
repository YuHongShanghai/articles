# ffplay 源码解析系列（六）：视频渲染与显示

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 解码完成后，视频帧如何从 FrameQueue 中取出、上传为 SDL 纹理并最终渲染到屏幕上？本篇将完整拆解 ffplay 的视频渲染流水线。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 概述

视频渲染是 ffplay 播放管线中的最后一环——将解码后的 `AVFrame` 转化为屏幕上可见的画面。这个过程涉及以下关键步骤：

1. **从 FrameQueue 获取待显示帧**：`frame_queue_peek_last()` 获取当前应该显示的帧
2. **像素格式映射**：将 FFmpeg 的 `AVPixelFormat` 映射到 SDL 纹理格式
3. **纹理管理**：检测尺寸/格式变化，按需重建 SDL 纹理
4. **纹理上传**：将帧数据写入 GPU 纹理（区分 YUV 和 RGB 路径）
5. **宽高比计算**：考虑 SAR 计算正确的显示矩形
6. **最终渲染**：调用 `SDL_RenderCopyEx()` 将纹理绘制到窗口

![视频渲染流水线](https://gitee.com/yuhong1234/ffplay/raw/master/06-video-render-pipeline.png)

## 2. 渲染入口：video_display()

`video_display()` 是视频显示的顶层入口函数，由事件循环中的刷新逻辑调用。它的职责很简单——清空画布，根据当前的显示模式选择渲染路径：

```c
/* display the current picture, if any */
static void video_display(VideoState *is)
{
    // 如果窗口尚未打开，先初始化窗口
    if (!is->width)
        video_open(is);

    // 清空渲染器为黑色背景
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    SDL_RenderClear(renderer);

    // 根据 show_mode 分支
    if (is->audio_st && is->show_mode != SHOW_MODE_VIDEO)
        video_audio_display(is);   // 音频可视化模式（波形/频谱）
    else if (is->video_st)
        video_image_display(is);   // 视频画面渲染

    // 将渲染结果提交到屏幕
    SDL_RenderPresent(renderer);
}
```

这里有两条渲染路径：

| 模式 | 条件 | 处理函数 |
|------|------|----------|
| **视频模式** | `show_mode == SHOW_MODE_VIDEO` 且存在视频流 | `video_image_display()` |
| **音频可视化** | 存在音频流且 `show_mode` 不是视频模式 | `video_audio_display()` |

用户可以通过按 `w` 键在视频模式和音频可视化模式之间切换。

## 3. 窗口配置：video_open()

在首次显示前，`video_open()` 负责配置 SDL 窗口的标题、尺寸和位置：

```c
static int video_open(VideoState *is)
{
    int w, h;

    // 优先使用命令行指定的尺寸，否则使用默认值（640x480）
    w = screen_width ? screen_width : default_width;
    h = screen_height ? screen_height : default_height;

    // 设置窗口标题（默认为输入文件名）
    if (!window_title)
        window_title = input_filename;
    SDL_SetWindowTitle(window, window_title);

    // 设置窗口尺寸和位置
    SDL_SetWindowSize(window, w, h);
    SDL_SetWindowPosition(window, screen_left, screen_top);

    // 处理全屏模式
    if (is_full_screen)
        SDL_SetWindowFullscreen(window, SDL_WINDOW_FULLSCREEN_DESKTOP);
    SDL_ShowWindow(window);

    // 记录当前窗口尺寸到 VideoState
    is->width  = w;
    is->height = h;

    return 0;
}
```

注意：`window` 和 `renderer` 都是全局变量，在 `main()` 函数中通过 `SDL_CreateWindow()` 和 `SDL_CreateRenderer()` 创建。`video_open()` 只负责调整已有窗口的属性。

## 4. 视频帧渲染核心：video_image_display()

这是整个渲染流水线的核心函数，完成从 FrameQueue 取帧到最终渲染的全过程：

```c
static void video_image_display(VideoState *is)
{
    Frame *vp;
    Frame *sp = NULL;
    SDL_Rect rect;

    // 步骤1: 从 FrameQueue 获取当前应显示的帧
    vp = frame_queue_peek_last(&is->pictq);

    // 步骤2: Vulkan 渲染路径（如果启用）
    if (vk_renderer) {
        vk_renderer_display(vk_renderer, vp->frame);
        return;
    }

    // 步骤3: 字幕叠加处理（详见字幕篇）
    if (is->subtitle_st) {
        if (frame_queue_nb_remaining(&is->subpq) > 0) {
            sp = frame_queue_peek(&is->subpq);
            if (vp->pts >= sp->pts + ((float) sp->sub.start_display_time / 1000)) {
                if (!sp->uploaded) {
                    // ... 字幕纹理上传（PAL8 -> BGRA 转换）
                    sp->uploaded = 1;
                }
            } else
                sp = NULL;
        }
    }

    // 步骤4: 计算显示矩形（保持宽高比）
    calculate_display_rect(&rect, is->xleft, is->ytop, is->width, is->height,
                           vp->width, vp->height, vp->sar);

    // 步骤5: 设置 YUV 色彩空间转换模式
    set_sdl_yuv_conversion_mode(vp->frame);

    // 步骤6: 上传纹理（仅首次或帧数据变化时）
    if (!vp->uploaded) {
        if (upload_texture(&is->vid_texture, vp->frame) < 0) {
            set_sdl_yuv_conversion_mode(NULL);
            return;
        }
        vp->uploaded = 1;
        // 检测是否需要垂直翻转（负 linesize 表示图像上下颠倒）
        vp->flip_v = vp->frame->linesize[0] < 0;
    }

    // 步骤7: 最终渲染——将纹理绘制到窗口
    SDL_RenderCopyEx(renderer, is->vid_texture, NULL, &rect,
                     0, NULL, vp->flip_v ? SDL_FLIP_VERTICAL : 0);

    // 恢复默认色彩空间
    set_sdl_yuv_conversion_mode(NULL);

    // 步骤8: 叠加字幕纹理
    if (sp) {
#if USE_ONEPASS_SUBTITLE_RENDER
        SDL_RenderCopy(renderer, is->sub_texture, NULL, &rect);
#else
        // 逐个字幕矩形按比例缩放绘制
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
}
```

### 4.1 Vulkan vs SDL 渲染路径

ffplay 支持两种渲染后端：

- **Vulkan 路径**：当指定 `-vulkan` 参数时启用，通过 `vk_renderer_display()` 直接将 AVFrame 送入 Vulkan 渲染管线，跳过后续所有 SDL 纹理操作
- **SDL 路径**：默认路径，通过 SDL2 的纹理机制完成渲染，兼容性好，是我们分析的重点

### 4.2 uploaded 标志的作用

`vp->uploaded` 是一个关键的优化标志。当同一帧需要重复显示时（比如视频暂停或音视频同步导致的帧重复），纹理不需要重新上传，直接复用已有纹理即可。这避免了不必要的 CPU-GPU 数据传输。

## 5. 像素格式映射：get_sdl_pix_fmt_and_blendmode()

FFmpeg 使用 `AVPixelFormat` 枚举标识像素格式，而 SDL 使用自己的 `SDL_PIXELFORMAT_*` 常量。ffplay 通过一张静态映射表完成两者之间的转换：

```c
// FFmpeg 像素格式 -> SDL 纹理格式 映射表
static const struct TextureFormatEntry {
    enum AVPixelFormat format;
    int texture_fmt;
} sdl_texture_format_map[] = {
    { AV_PIX_FMT_RGB8,           SDL_PIXELFORMAT_RGB332 },
    { AV_PIX_FMT_RGB444,         SDL_PIXELFORMAT_RGB444 },
    { AV_PIX_FMT_RGB555,         SDL_PIXELFORMAT_RGB555 },
    { AV_PIX_FMT_BGR555,         SDL_PIXELFORMAT_BGR555 },
    { AV_PIX_FMT_RGB565,         SDL_PIXELFORMAT_RGB565 },
    { AV_PIX_FMT_BGR565,         SDL_PIXELFORMAT_BGR565 },
    { AV_PIX_FMT_RGB24,          SDL_PIXELFORMAT_RGB24 },
    { AV_PIX_FMT_BGR24,          SDL_PIXELFORMAT_BGR24 },
    { AV_PIX_FMT_0RGB32,         SDL_PIXELFORMAT_RGB888 },
    { AV_PIX_FMT_0BGR32,         SDL_PIXELFORMAT_BGR888 },
    { AV_PIX_FMT_NE(RGB0, 0BGR), SDL_PIXELFORMAT_RGBX8888 },
    { AV_PIX_FMT_NE(BGR0, 0RGB), SDL_PIXELFORMAT_BGRX8888 },
    { AV_PIX_FMT_RGB32,          SDL_PIXELFORMAT_ARGB8888 },
    { AV_PIX_FMT_RGB32_1,        SDL_PIXELFORMAT_RGBA8888 },
    { AV_PIX_FMT_BGR32,          SDL_PIXELFORMAT_ABGR8888 },
    { AV_PIX_FMT_BGR32_1,        SDL_PIXELFORMAT_BGRA8888 },
    { AV_PIX_FMT_YUV420P,        SDL_PIXELFORMAT_IYUV },     // 最常见的 YUV 格式
    { AV_PIX_FMT_YUYV422,        SDL_PIXELFORMAT_YUY2 },
    { AV_PIX_FMT_UYVY422,        SDL_PIXELFORMAT_UYVY },
    { AV_PIX_FMT_NONE,           SDL_PIXELFORMAT_UNKNOWN },   // 结束哨兵
};
```

查找函数遍历映射表，同时处理带 Alpha 通道的混合模式：

```c
static void get_sdl_pix_fmt_and_blendmode(int format, Uint32 *sdl_pix_fmt,
                                          SDL_BlendMode *sdl_blendmode)
{
    int i;
    *sdl_blendmode = SDL_BLENDMODE_NONE;
    *sdl_pix_fmt = SDL_PIXELFORMAT_UNKNOWN;

    // 含 Alpha 通道的 RGB32 格式需要启用混合模式
    if (format == AV_PIX_FMT_RGB32   ||
        format == AV_PIX_FMT_RGB32_1 ||
        format == AV_PIX_FMT_BGR32   ||
        format == AV_PIX_FMT_BGR32_1)
        *sdl_blendmode = SDL_BLENDMODE_BLEND;

    // 遍历映射表查找对应的 SDL 格式
    for (i = 0; i < FF_ARRAY_ELEMS(sdl_texture_format_map) - 1; i++) {
        if (format == sdl_texture_format_map[i].format) {
            *sdl_pix_fmt = sdl_texture_format_map[i].texture_fmt;
            return;
        }
    }
    // 未找到时 sdl_pix_fmt 保持 SDL_PIXELFORMAT_UNKNOWN
}
```

如果 FFmpeg 解码出的格式不在映射表中（比如 `AV_PIX_FMT_YUV444P`），`sdl_pix_fmt` 会保持为 `SDL_PIXELFORMAT_UNKNOWN`，后续 `upload_texture()` 会回退到 `SDL_PIXELFORMAT_ARGB8888`，此时需要通过 `sws_scale` 进行像素格式转换。

## 6. 纹理管理：realloc_texture()

SDL 纹理是 GPU 上的一块内存，创建和销毁都有开销。`realloc_texture()` 采用"按需重建"的策略——只在格式或尺寸发生变化时才重新创建纹理：

```c
static int realloc_texture(SDL_Texture **texture, Uint32 new_format,
                           int new_width, int new_height,
                           SDL_BlendMode blendmode, int init_texture)
{
    Uint32 format;
    int access, w, h;

    // 检查现有纹理是否可以复用：
    // 1. 纹理存在 2. 查询纹理参数成功 3. 尺寸和格式都匹配
    if (!*texture ||
        SDL_QueryTexture(*texture, &format, &access, &w, &h) < 0 ||
        new_width != w || new_height != h || new_format != format) {

        void *pixels;
        int pitch;

        // 销毁旧纹理
        if (*texture)
            SDL_DestroyTexture(*texture);

        // 创建新的流式纹理（SDL_TEXTUREACCESS_STREAMING 允许 CPU 写入）
        if (!(*texture = SDL_CreateTexture(renderer, new_format,
                SDL_TEXTUREACCESS_STREAMING, new_width, new_height)))
            return -1;

        // 设置混合模式
        if (SDL_SetTextureBlendMode(*texture, blendmode) < 0)
            return -1;

        // 可选：初始化纹理为全黑（用于字幕纹理等）
        if (init_texture) {
            if (SDL_LockTexture(*texture, NULL, &pixels, &pitch) < 0)
                return -1;
            memset(pixels, 0, pitch * new_height);
            SDL_UnlockTexture(*texture);
        }
        av_log(NULL, AV_LOG_VERBOSE, "Created %dx%d texture with %s.\n",
               new_width, new_height, SDL_GetPixelFormatName(new_format));
    }
    return 0;
}
```

关键设计点：

- **SDL_TEXTUREACCESS_STREAMING**：表示纹理内容会频繁从 CPU 端更新。SDL 会为此类纹理分配适合 CPU 写入的内存布局
- **init_texture 参数**：视频纹理不需要初始化（马上就会写入帧数据），但字幕纹理需要初始化为全透明黑色作为背景
- **格式变化检测**：视频分辨率或像素格式在播放过程中可能发生变化（如自适应码率流），此时必须重建纹理

## 7. 纹理上传：upload_texture()

这是将 AVFrame 像素数据从 CPU 内存传输到 GPU 纹理的核心函数。根据像素格式的不同，走不同的上传路径：

```c
static int upload_texture(SDL_Texture **tex, AVFrame *frame)
{
    int ret = 0;
    Uint32 sdl_pix_fmt;
    SDL_BlendMode sdl_blendmode;

    // 获取对应的 SDL 像素格式和混合模式
    get_sdl_pix_fmt_and_blendmode(frame->format, &sdl_pix_fmt, &sdl_blendmode);

    // 确保纹理就绪（格式/尺寸不匹配时重建）
    // 如果格式未知，回退到 ARGB8888
    if (realloc_texture(tex,
            sdl_pix_fmt == SDL_PIXELFORMAT_UNKNOWN ? SDL_PIXELFORMAT_ARGB8888 : sdl_pix_fmt,
            frame->width, frame->height, sdl_blendmode, 0) < 0)
        return -1;

    switch (sdl_pix_fmt) {
        case SDL_PIXELFORMAT_IYUV:
            // YUV420P 路径：分别上传 Y/U/V 三个平面
            if (frame->linesize[0] > 0 && frame->linesize[1] > 0 && frame->linesize[2] > 0) {
                // 正常方向
                ret = SDL_UpdateYUVTexture(*tex, NULL,
                        frame->data[0], frame->linesize[0],   // Y 平面
                        frame->data[1], frame->linesize[1],   // U 平面
                        frame->data[2], frame->linesize[2]);  // V 平面
            } else if (frame->linesize[0] < 0 && frame->linesize[1] < 0 && frame->linesize[2] < 0) {
                // 负 linesize：图像上下翻转存储
                // 从最后一行开始，使用正的步长上传
                ret = SDL_UpdateYUVTexture(*tex, NULL,
                        frame->data[0] + frame->linesize[0] * (frame->height - 1),
                        -frame->linesize[0],
                        frame->data[1] + frame->linesize[1] * (AV_CEIL_RSHIFT(frame->height, 1) - 1),
                        -frame->linesize[1],
                        frame->data[2] + frame->linesize[2] * (AV_CEIL_RSHIFT(frame->height, 1) - 1),
                        -frame->linesize[2]);
            } else {
                av_log(NULL, AV_LOG_ERROR,
                       "Mixed negative and positive linesizes are not supported.\n");
                return -1;
            }
            break;

        default:
            // RGB 等其他格式路径：单平面上传
            if (frame->linesize[0] < 0) {
                // 负 linesize 翻转处理
                ret = SDL_UpdateTexture(*tex, NULL,
                        frame->data[0] + frame->linesize[0] * (frame->height - 1),
                        -frame->linesize[0]);
            } else {
                ret = SDL_UpdateTexture(*tex, NULL,
                        frame->data[0], frame->linesize[0]);
            }
            break;
    }
    return ret;
}
```

### 7.1 YUV 路径 vs RGB 路径

| 路径 | 适用格式 | SDL API | 说明 |
|------|---------|---------|------|
| YUV | YUV420P (IYUV) | `SDL_UpdateYUVTexture()` | 分别上传 Y/U/V 三个平面，SDL 内部完成 YUV->RGB 转换 |
| RGB | 其他所有格式 | `SDL_UpdateTexture()` | 单平面上传，直接作为 RGB/RGBA 数据 |

### 7.2 负 linesize 的处理

`linesize`（行步长）表示图像每行数据之间的字节间距。正常情况下 `linesize > 0`，表示数据从上到下存储。但某些编解码器（如 BMP 解码器）会输出 `linesize < 0` 的帧，表示图像是上下颠倒存储的（即第一行数据实际对应图像底部）。

处理方式是将 data 指针移到最后一行，并使用正的步长：

```
data[0] + linesize[0] * (height - 1)  // 指向最后一行（视觉上的第一行）
-linesize[0]                           // 取正值作为步长
```

对于 YUV420P 的 U/V 平面，高度需要右移一位（除以2并向上取整），因为色度平面的分辨率是亮度的一半：

```
AV_CEIL_RSHIFT(frame->height, 1)  // 等效于 ceil(height / 2)
```

此外，`video_image_display()` 中还会检查 `linesize[0] < 0` 来设置 `flip_v` 标志，在 `SDL_RenderCopyEx()` 调用时通过 `SDL_FLIP_VERTICAL` 参数进行垂直翻转。

## 8. YUV 色彩空间：set_sdl_yuv_conversion_mode()

不同的视频内容使用不同的 YUV 色彩空间标准，这直接影响 YUV->RGB 的转换矩阵。ffplay 根据帧的元数据设置 SDL 的转换模式：

```c
// ffplay 支持的 YUV 色彩空间列表（用于 avfilter 配置）
static enum AVColorSpace sdl_supported_color_spaces[] = {
    AVCOL_SPC_BT709,
    AVCOL_SPC_BT470BG,
    AVCOL_SPC_SMPTE170M,
    AVCOL_SPC_UNSPECIFIED,
};

static void set_sdl_yuv_conversion_mode(AVFrame *frame)
{
#if SDL_VERSION_ATLEAST(2,0,8)
    SDL_YUV_CONVERSION_MODE mode = SDL_YUV_CONVERSION_AUTOMATIC;

    if (frame && (frame->format == AV_PIX_FMT_YUV420P ||
                  frame->format == AV_PIX_FMT_YUYV422 ||
                  frame->format == AV_PIX_FMT_UYVY422)) {
        if (frame->color_range == AVCOL_RANGE_JPEG)
            mode = SDL_YUV_CONVERSION_JPEG;       // JPEG 全范围 (0-255)
        else if (frame->colorspace == AVCOL_SPC_BT709)
            mode = SDL_YUV_CONVERSION_BT709;      // HD 高清标准
        else if (frame->colorspace == AVCOL_SPC_BT470BG ||
                 frame->colorspace == AVCOL_SPC_SMPTE170M)
            mode = SDL_YUV_CONVERSION_BT601;      // SD 标清标准
    }
    SDL_SetYUVConversionMode(mode);
#endif
}
```

三种色彩空间的适用场景：

| 标准 | SDL 模式 | 适用场景 |
|------|---------|---------|
| **BT.601** | `SDL_YUV_CONVERSION_BT601` | 标清视频 (SD, 720x576 及以下) |
| **BT.709** | `SDL_YUV_CONVERSION_BT709` | 高清视频 (HD, 1080p/720p) |
| **JPEG** | `SDL_YUV_CONVERSION_JPEG` | JPEG 图片及全范围 YUV，Y/Cb/Cr 使用 0-255 全范围 |

使用错误的转换矩阵会导致颜色偏移——例如，将 BT.709 的高清视频按 BT.601 转换，会出现绿色偏色等问题。

注意这个函数被**成对调用**：渲染前设置正确的转换模式，渲染后传入 `NULL` 恢复默认。这是因为 `SDL_SetYUVConversionMode()` 是全局状态，必须及时恢复以免影响其他渲染操作。

## 9. 宽高比计算：calculate_display_rect()

视频帧的分辨率通常与窗口尺寸不一致。`calculate_display_rect()` 负责在保持正确宽高比的前提下，计算帧在窗口中的最大显示区域并居中：

```c
static void calculate_display_rect(SDL_Rect *rect,
                                   int scr_xleft, int scr_ytop,
                                   int scr_width, int scr_height,
                                   int pic_width, int pic_height,
                                   AVRational pic_sar)
{
    AVRational aspect_ratio = pic_sar;
    int64_t width, height, x, y;

    // 处理无效或未指定的 SAR，默认为 1:1（方形像素）
    if (av_cmp_q(aspect_ratio, av_make_q(0, 1)) <= 0)
        aspect_ratio = av_make_q(1, 1);

    // 将 SAR 与图像宽高比相乘，得到显示宽高比 (DAR)
    // DAR = SAR * (pic_width / pic_height)
    aspect_ratio = av_mul_q(aspect_ratio, av_make_q(pic_width, pic_height));

    // 先尝试以屏幕高度为基准计算宽度
    height = scr_height;
    width = av_rescale(height, aspect_ratio.num, aspect_ratio.den) & ~1;

    // 如果宽度超出屏幕，改为以屏幕宽度为基准计算高度
    if (width > scr_width) {
        width = scr_width;
        height = av_rescale(width, aspect_ratio.den, aspect_ratio.num) & ~1;
    }

    // 居中放置
    x = (scr_width - width) / 2;
    y = (scr_height - height) / 2;
    rect->x = scr_xleft + x;
    rect->y = scr_ytop  + y;
    rect->w = FFMAX((int)width,  1);
    rect->h = FFMAX((int)height, 1);
}
```

### 9.1 SAR、DAR、PAR 概念

理解这个函数需要清楚三个关键概念：

- **SAR (Sample Aspect Ratio)**：采样宽高比，描述单个像素的形状。1:1 表示方形像素，非 1:1 表示像素是矩形的（常见于 DVD 等标清内容）
- **DAR (Display Aspect Ratio)**：显示宽高比，即最终画面应呈现的比例，如 16:9、4:3
- 三者关系：`DAR = SAR * (pic_width / pic_height)`

### 9.2 适配算法

算法采用"fit-inside"策略，确保视频完整显示在窗口内：

1. 先假设视频占满屏幕高度，按 DAR 计算所需宽度
2. 如果计算出的宽度超过屏幕宽度，则反过来占满屏幕宽度，按 DAR 计算高度
3. `& ~1` 确保宽高为偶数（视频编码通常要求偶数尺寸）
4. 将视频区域在窗口中水平和垂直居中

![宽高比适配示意](https://gitee.com/yuhong1234/ffplay/raw/master/06-display-rect.png)

## 10. 最终渲染调用

在 `video_image_display()` 中，最终的渲染通过 `SDL_RenderCopyEx()` 完成：

```c
SDL_RenderCopyEx(renderer, is->vid_texture, NULL, &rect,
                 0, NULL, vp->flip_v ? SDL_FLIP_VERTICAL : 0);
```

各参数含义：

| 参数 | 值 | 说明 |
|------|-----|------|
| renderer | 全局渲染器 | SDL 渲染上下文 |
| texture | `is->vid_texture` | 已上传帧数据的纹理 |
| srcrect | `NULL` | 源区域，NULL 表示整个纹理 |
| dstrect | `&rect` | 目标区域，`calculate_display_rect()` 计算得到 |
| angle | 0 | 旋转角度 |
| center | NULL | 旋转中心，NULL 为默认 |
| flip | `SDL_FLIP_VERTICAL` 或 0 | 根据 linesize 正负决定是否垂直翻转 |

整个渲染流程在 `video_display()` 的末尾由 `SDL_RenderPresent(renderer)` 提交，将后台缓冲区的内容显示到屏幕上。这是典型的**双缓冲**机制——先在后台缓冲区完成所有绘制操作，最后一次性提交，避免画面撕裂。

## 11. 完整渲染流程总结

将上述所有环节串联起来，一帧视频从解码完成到显示在屏幕上的完整流程如下：

```
事件循环 refresh_loop_wait_event()
    |
    v
video_refresh() 判断是否该显示新帧
    |
    v
video_display()
    |-- SDL_RenderClear()                    清空画面
    |-- video_image_display()
    |   |-- frame_queue_peek_last()          取出当前帧
    |   |-- calculate_display_rect()         计算显示区域
    |   |-- set_sdl_yuv_conversion_mode()    设置色彩空间
    |   |-- upload_texture()                 上传纹理
    |   |   |-- get_sdl_pix_fmt_and_blendmode()  格式映射
    |   |   |-- realloc_texture()                纹理管理
    |   |   |-- SDL_UpdateYUVTexture()           YUV 数据上传
    |   |   |   或 SDL_UpdateTexture()           RGB 数据上传
    |   |-- SDL_RenderCopyEx()               渲染到后台缓冲区
    |   |-- SDL_RenderCopy() (字幕)          叠加字幕
    |-- SDL_RenderPresent()                  提交到屏幕
```

## 12. 关键设计思考

### 为什么 ffplay 不使用硬件加速纹理？

ffplay 使用 `SDL_TEXTUREACCESS_STREAMING` 创建纹理，每帧都从 CPU 内存上传数据。这种方式简单直接但效率不高。现代播放器（如 mpv）会使用硬件解码（VAAPI/VDPAU/VideoToolbox）配合零拷贝路径，解码结果直接在 GPU 上，省去了 CPU->GPU 的传输开销。ffplay 作为一个参考实现和调试工具，优先选择了简洁性和可移植性。

### Vulkan 渲染器的意义

FFmpeg 7.x 版本引入了 Vulkan 渲染路径，可以通过 `-vulkan` 参数启用。Vulkan 渲染器可以直接接收 Vulkan 硬件帧（通过 `hwaccel=vulkan` 解码），实现全 GPU 流水线，大幅降低 CPU 占用。

### uploaded 标志的双重作用

`vp->uploaded` 不仅是性能优化（避免重复上传），也是正确性保证。在暂停状态下，`video_display()` 可能被多次调用（如窗口重绘），但帧数据不变，直接复用纹理是正确的行为。
