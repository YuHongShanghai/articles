# ffplay 源码解析系列（十）：AVFilter 滤镜系统

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 滤镜（Filter）是 FFmpeg 音视频处理的核心能力之一。ffplay 利用 libavfilter 构建滤镜图（FilterGraph），实现了视频自动旋转、像素格式转换、音频重采样等功能，同时支持用户通过 `-vf` / `-af` 参数插入自定义滤镜链。本篇深入剖析 ffplay 中 AVFilter 的完整实现。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. AVFilter 框架基础概念

在分析 ffplay 源码之前，先了解 libavfilter 的核心数据结构。

### 1.1 核心数据结构

**AVFilterGraph** 是滤镜图的容器，管理所有滤镜实例及其连接关系：

```c
// 滤镜图：管理一组互相连接的滤镜
AVFilterGraph *graph = avfilter_graph_alloc();
graph->nb_threads = filter_nbthreads;  // 滤镜线程数
```

**AVFilterContext** 是滤镜的运行时实例，每个滤镜节点都是一个 AVFilterContext：

```c
AVFilterContext *filt_src = NULL;   // 输入端（buffersrc）
AVFilterContext *filt_out = NULL;   // 输出端（buffersink）
AVFilterContext *filt_ctx;          // 中间滤镜节点
```

**AVFilterInOut** 用于描述滤镜图的输入/输出端点，在解析滤镜字符串时使用：

```c
AVFilterInOut *outputs = avfilter_inout_alloc();
AVFilterInOut *inputs  = avfilter_inout_alloc();

outputs->name       = av_strdup("in");       // 输出端名称
outputs->filter_ctx = source_ctx;            // 关联到 buffersrc
outputs->pad_idx    = 0;
outputs->next       = NULL;

inputs->name        = av_strdup("out");      // 输入端名称
inputs->filter_ctx  = sink_ctx;              // 关联到 buffersink
inputs->pad_idx     = 0;
inputs->next        = NULL;
```

### 1.2 buffersrc 与 buffersink

每个滤镜图都有固定的两个端点：

- **buffersrc（buffer / abuffer）**：输入端，解码线程将 AVFrame 送入此处
- **buffersink（buffersink / abuffersink）**：输出端，处理完的 AVFrame 从此处取出

数据流方向：

```
解码器 → buffersrc → [滤镜1] → [滤镜2] → ... → buffersink → 渲染/播放
```

对应的 API 调用：

```c
// 送入帧到滤镜图输入端
av_buffersrc_add_frame(filt_in, frame);

// 从滤镜图输出端取出处理后的帧
av_buffersink_get_frame_flags(filt_out, frame, 0);
```

![AVFilter 滤镜链拓扑图](https://gitee.com/yuhong1234/ffplay/raw/master/10-filter-chain.png)

## 2. configure_filtergraph：通用配置函数

`configure_filtergraph()` 是视频和音频滤镜配置的公共底层函数，负责将 buffersrc 和 buffersink 通过滤镜串连接起来（ffplay.c 行 1817-1858）：

```c
static int configure_filtergraph(AVFilterGraph *graph, const char *filtergraph,
                                 AVFilterContext *source_ctx, AVFilterContext *sink_ctx)
{
    int ret, i;
    int nb_filters = graph->nb_filters;
    AVFilterInOut *outputs = NULL, *inputs = NULL;

    if (filtergraph) {
        // 有用户指定的滤镜字符串，解析并插入滤镜图
        outputs = avfilter_inout_alloc();
        inputs  = avfilter_inout_alloc();
        if (!outputs || !inputs) {
            ret = AVERROR(ENOMEM);
            goto fail;
        }

        // "in" 端连接 source（buffersrc）
        outputs->name       = av_strdup("in");
        outputs->filter_ctx = source_ctx;
        outputs->pad_idx    = 0;
        outputs->next       = NULL;

        // "out" 端连接 sink（buffersink）
        inputs->name        = av_strdup("out");
        inputs->filter_ctx  = sink_ctx;
        inputs->pad_idx     = 0;
        inputs->next        = NULL;

        // 解析滤镜描述字符串，如 "scale=1280:720,transpose=1"
        if ((ret = avfilter_graph_parse_ptr(graph, filtergraph,
                                            &inputs, &outputs, NULL)) < 0)
            goto fail;
    } else {
        // 没有用户滤镜，直接将 source 连接到 sink
        if ((ret = avfilter_link(source_ctx, 0, sink_ctx, 0)) < 0)
            goto fail;
    }

    /* 重排序滤镜，确保自定义滤镜的输入优先合并 */
    for (i = 0; i < graph->nb_filters - nb_filters; i++)
        FFSWAP(AVFilterContext*, graph->filters[i], graph->filters[i + nb_filters]);

    // 验证并配置整个滤镜图（协商格式、分配缓冲区等）
    ret = avfilter_graph_config(graph, NULL);
fail:
    avfilter_inout_free(&outputs);
    avfilter_inout_free(&inputs);
    return ret;
}
```

这个函数的设计非常巧妙，通过 `filtergraph` 参数是否为 NULL 来区分两种模式：

| 模式 | 条件 | 行为 |
|------|------|------|
| 用户滤镜 | `filtergraph != NULL` | 调用 `avfilter_graph_parse_ptr` 解析滤镜字符串 |
| 直连模式 | `filtergraph == NULL` | 调用 `avfilter_link` 直接连接 src 和 sink |

最后的 `avfilter_graph_config()` 是关键步骤，它会：
1. 在相邻滤镜间协商数据格式（像素格式、采样率等）
2. 自动插入必要的格式转换滤镜
3. 分配内部缓冲区

## 3. configure_video_filters：视频滤镜链构建

`configure_video_filters()` 是视频滤镜配置的核心函数，负责构建从 buffersrc 到 buffersink 的完整视频滤镜链（ffplay.c 行 1860-1993）。

### 3.1 buffersrc 参数配置

首先构建 buffersrc 的参数字符串，描述输入视频的属性：

```c
static int configure_video_filters(AVFilterGraph *graph, VideoState *is,
                                   const char *vfilters, AVFrame *frame)
{
    enum AVPixelFormat pix_fmts[FF_ARRAY_ELEMS(sdl_texture_format_map)];
    char sws_flags_str[512] = "";
    char buffersrc_args[256];
    int ret;
    AVFilterContext *filt_src = NULL, *filt_out = NULL, *last_filter = NULL;
    AVCodecParameters *codecpar = is->video_st->codecpar;
    AVRational fr = av_guess_frame_rate(is->ic, is->video_st, NULL);

    // ...

    // 构建 buffersrc 参数：描述输入帧的全部属性
    snprintf(buffersrc_args, sizeof(buffersrc_args),
             "video_size=%dx%d:pix_fmt=%d:time_base=%d/%d:pixel_aspect=%d/%d:"
             "colorspace=%d:range=%d",
             frame->width, frame->height, frame->format,
             is->video_st->time_base.num, is->video_st->time_base.den,
             codecpar->sample_aspect_ratio.num,
             FFMAX(codecpar->sample_aspect_ratio.den, 1),
             frame->colorspace, frame->color_range);
    // 如果有帧率信息，追加 frame_rate 参数
    if (fr.num && fr.den)
        av_strlcatf(buffersrc_args, sizeof(buffersrc_args),
                     ":frame_rate=%d/%d", fr.num, fr.den);

    // 创建 buffer（视频 buffersrc）滤镜
    if ((ret = avfilter_graph_create_filter(&filt_src,
                                            avfilter_get_by_name("buffer"),
                                            "ffplay_buffer", buffersrc_args, NULL,
                                            graph)) < 0)
        goto fail;
```

buffersrc 的参数汇总：

| 参数 | 含义 | 来源 |
|------|------|------|
| `video_size` | 视频分辨率 | `frame->width/height` |
| `pix_fmt` | 像素格式 | `frame->format` |
| `time_base` | 时间基 | `video_st->time_base` |
| `pixel_aspect` | 像素宽高比 | `codecpar->sample_aspect_ratio` |
| `colorspace` | 色彩空间 | `frame->colorspace` |
| `range` | 色彩范围 | `frame->color_range` |
| `frame_rate` | 帧率 | `av_guess_frame_rate()` 推测 |

### 3.2 硬件加速帧上下文

创建 buffersrc 后，如果输入帧使用了硬件加速（如 VAAPI、CUDA），需要传递硬件帧上下文：

```c
    // 硬件加速支持：传递 hw_frames_ctx
    AVBufferSrcParameters *par = av_buffersrc_parameters_alloc();
    par->hw_frames_ctx = frame->hw_frames_ctx;
    ret = av_buffersrc_parameters_set(filt_src, par);
    if (ret < 0)
        goto fail;
```

这确保了滤镜图能正确处理 GPU 上的帧数据。

### 3.3 buffersink 参数配置

buffersink 限定了输出端接受的像素格式，只允许 SDL 渲染器支持的格式：

```c
    // 创建 buffersink（输出端）
    ret = avfilter_graph_create_filter(&filt_out,
                                       avfilter_get_by_name("buffersink"),
                                       "ffplay_buffersink", NULL, NULL, graph);
    if (ret < 0)
        goto fail;

    // 限制输出像素格式为 SDL 支持的格式列表
    if ((ret = av_opt_set_int_list(filt_out, "pix_fmts", pix_fmts,
                                    AV_PIX_FMT_NONE, AV_OPT_SEARCH_CHILDREN)) < 0)
        goto fail;

    // 限制输出色彩空间（非 Vulkan 渲染器时）
    if (!vk_renderer &&
        (ret = av_opt_set_int_list(filt_out, "color_spaces",
                                    sdl_supported_color_spaces,
                                    AVCOL_SPC_UNSPECIFIED,
                                    AV_OPT_SEARCH_CHILDREN)) < 0)
        goto fail;
```

SDL 支持的像素格式通过遍历 `renderer_info.texture_formats` 与 `sdl_texture_format_map` 映射表匹配得到：

```c
    for (i = 0; i < renderer_info.num_texture_formats; i++) {
        for (j = 0; j < FF_ARRAY_ELEMS(sdl_texture_format_map) - 1; j++) {
            if (renderer_info.texture_formats[i] == sdl_texture_format_map[j].texture_fmt) {
                pix_fmts[nb_pix_fmts++] = sdl_texture_format_map[j].format;
                break;
            }
        }
    }
    pix_fmts[nb_pix_fmts] = AV_PIX_FMT_NONE;  // 哨兵值
```

### 3.4 INSERT_FILT 宏：链式插入滤镜

ffplay 定义了一个巧妙的宏，用于在 buffersink 之前依次插入滤镜：

```c
/* 注意：此宏在最后添加的滤镜之前插入新滤镜，
 * 因此滤镜的处理顺序是反向的 */
#define INSERT_FILT(name, arg) do {                                          \
    AVFilterContext *filt_ctx;                                               \
                                                                             \
    ret = avfilter_graph_create_filter(&filt_ctx,                            \
                                       avfilter_get_by_name(name),           \
                                       "ffplay_" name, arg, NULL, graph);    \
    if (ret < 0)                                                             \
        goto fail;                                                           \
                                                                             \
    ret = avfilter_link(filt_ctx, 0, last_filter, 0);                        \
    if (ret < 0)                                                             \
        goto fail;                                                           \
                                                                             \
    last_filter = filt_ctx;                                                  \
} while (0)
```

`last_filter` 初始指向 `filt_out`（buffersink），每次 `INSERT_FILT` 都在 `last_filter` 前面插入一个新滤镜，并将 `last_filter` 更新为新滤镜。因此插入顺序与实际处理顺序相反：

```
插入顺序：buffersink ← filter_A ← filter_B
处理顺序：filter_B → filter_A → buffersink
```

### 3.5 autorotate 自动旋转逻辑

手机拍摄的视频通常带有旋转元数据，ffplay 会自动检测并插入旋转滤镜：

```c
    if (autorotate) {
        double theta = 0.0;
        int32_t *displaymatrix = NULL;

        // 优先从帧 side data 获取 displaymatrix
        AVFrameSideData *sd = av_frame_get_side_data(frame,
                                  AV_FRAME_DATA_DISPLAYMATRIX);
        if (sd)
            displaymatrix = (int32_t *)sd->data;

        // 帧中没有则从流的 coded_side_data 获取
        if (!displaymatrix) {
            const AVPacketSideData *psd = av_packet_side_data_get(
                is->video_st->codecpar->coded_side_data,
                is->video_st->codecpar->nb_coded_side_data,
                AV_PKT_DATA_DISPLAYMATRIX);
            if (psd)
                displaymatrix = (int32_t *)psd->data;
        }

        // 计算旋转角度
        theta = get_rotation(displaymatrix);

        if (fabs(theta - 90) < 1.0) {
            // 90度：使用 transpose 滤镜
            INSERT_FILT("transpose",
                        displaymatrix[3] > 0 ? "cclock_flip" : "clock");
        } else if (fabs(theta - 180) < 1.0) {
            // 180度：组合使用 hflip + vflip
            if (displaymatrix[0] < 0)
                INSERT_FILT("hflip", NULL);
            if (displaymatrix[4] < 0)
                INSERT_FILT("vflip", NULL);
        } else if (fabs(theta - 270) < 1.0) {
            // 270度：使用 transpose 滤镜（反向）
            INSERT_FILT("transpose",
                        displaymatrix[3] < 0 ? "clock_flip" : "cclock");
        } else if (fabs(theta) > 1.0) {
            // 任意角度：使用 rotate 滤镜
            char rotate_buf[64];
            snprintf(rotate_buf, sizeof(rotate_buf), "%f*PI/180", theta);
            INSERT_FILT("rotate", rotate_buf);
        } else {
            // 接近 0 度但 displaymatrix 指示垂直翻转
            if (displaymatrix && displaymatrix[4] < 0)
                INSERT_FILT("vflip", NULL);
        }
    }
```

不同角度对应的滤镜策略：

| 旋转角度 | 使用的滤镜 | 说明 |
|---------|-----------|------|
| 90 度 | `transpose=clock` 或 `cclock_flip` | 根据 displaymatrix[3] 符号选择 |
| 180 度 | `hflip` + `vflip` | 分别检查矩阵对角元素符号 |
| 270 度 | `transpose=cclock` 或 `clock_flip` | 根据 displaymatrix[3] 符号选择 |
| 其他角度 | `rotate=theta*PI/180` | 任意角度旋转 |
| 约 0 度 | `vflip`（条件） | 垂直翻转修正 |

### 3.6 SWS 缩放选项传递

如果用户通过 `-sws_flags` 等参数指定了缩放选项，会传递给滤镜图：

```c
    // 收集所有 sws 选项
    while ((e = av_dict_iterate(sws_dict, e))) {
        if (!strcmp(e->key, "sws_flags")) {
            av_strlcatf(sws_flags_str, sizeof(sws_flags_str),
                        "%s=%s:", "flags", e->value);
        } else
            av_strlcatf(sws_flags_str, sizeof(sws_flags_str),
                        "%s=%s:", e->key, e->value);
    }
    if (strlen(sws_flags_str))
        sws_flags_str[strlen(sws_flags_str)-1] = '\0';

    // 设置到滤镜图的 scale_sws_opts
    graph->scale_sws_opts = av_strdup(sws_flags_str);
```

这些选项会被滤镜图中的 scale 滤镜（如果有的话）自动应用，例如 `-sws_flags bicubic` 会使用双三次插值缩放。

### 3.7 最终组装

所有滤镜插入完毕后，调用 `configure_filtergraph` 完成最终连接：

```c
    // 将 buffersrc → [autorotate 滤镜] → [用户滤镜] → buffersink 连接起来
    if ((ret = configure_filtergraph(graph, vfilters, filt_src, last_filter)) < 0)
        goto fail;

    // 记录输入/输出滤镜指针，供解码线程使用
    is->in_video_filter  = filt_src;
    is->out_video_filter = filt_out;
```

注意这里传给 `configure_filtergraph` 的 sink 端是 `last_filter`（而非 `filt_out`），因为 `last_filter` 经过 `INSERT_FILT` 宏的更新，已经是 autorotate 链的最前端。`configure_filtergraph` 内部会将 `filt_src` 与 `last_filter` 之间插入用户滤镜（如果有的话），形成完整链路：

```
filt_src(buffersrc) → [用户滤镜] → last_filter → ... → filt_out(buffersink)
```

## 4. configure_audio_filters：音频滤镜链构建

音频滤镜配置函数与视频类似，但参数和处理逻辑有所不同（ffplay.c 行 1995-2069）。

### 4.1 abuffer 参数配置

```c
static int configure_audio_filters(VideoState *is, const char *afilters,
                                   int force_output_format)
{
    static const enum AVSampleFormat sample_fmts[] = {
        AV_SAMPLE_FMT_S16, AV_SAMPLE_FMT_NONE
    };
    int sample_rates[2] = { 0, -1 };
    AVFilterContext *filt_asrc = NULL, *filt_asink = NULL;
    char aresample_swr_opts[512] = "";
    char asrc_args[256];
    int ret;

    // 每次重新创建滤镜图（音频可能动态重配置）
    avfilter_graph_free(&is->agraph);
    if (!(is->agraph = avfilter_graph_alloc()))
        return AVERROR(ENOMEM);
    is->agraph->nb_threads = filter_nbthreads;

    // ...

    // 构建 abuffer 参数
    ret = snprintf(asrc_args, sizeof(asrc_args),
                   "sample_rate=%d:sample_fmt=%s:time_base=%d/%d:channel_layout=%s",
                   is->audio_filter_src.freq,
                   av_get_sample_fmt_name(is->audio_filter_src.fmt),
                   1, is->audio_filter_src.freq,
                   bp.str);  // channel_layout 字符串

    // 创建 abuffer（音频 buffersrc）
    ret = avfilter_graph_create_filter(&filt_asrc,
                                       avfilter_get_by_name("abuffer"),
                                       "ffplay_abuffer",
                                       asrc_args, NULL, is->agraph);
```

音频 buffersrc 参数汇总：

| 参数 | 含义 | 来源 |
|------|------|------|
| `sample_rate` | 采样率 | `audio_filter_src.freq` |
| `sample_fmt` | 采样格式 | `audio_filter_src.fmt` |
| `time_base` | 时间基 | `1/sample_rate` |
| `channel_layout` | 声道布局 | `audio_filter_src.ch_layout` |

### 4.2 abuffersink 参数配置

```c
    // 创建 abuffersink（输出端）
    ret = avfilter_graph_create_filter(&filt_asink,
                                       avfilter_get_by_name("abuffersink"),
                                       "ffplay_abuffersink",
                                       NULL, NULL, is->agraph);

    // 限制输出采样格式为 S16（SDL 播放格式）
    if ((ret = av_opt_set_int_list(filt_asink, "sample_fmts", sample_fmts,
                                    AV_SAMPLE_FMT_NONE,
                                    AV_OPT_SEARCH_CHILDREN)) < 0)
        goto end;

    // 默认允许任意声道数
    if ((ret = av_opt_set_int(filt_asink, "all_channel_counts", 1,
                               AV_OPT_SEARCH_CHILDREN)) < 0)
        goto end;
```

### 4.3 force_output_format：强制输出格式

当音频格式发生变化需要重配置时，`force_output_format` 为 1，此时会严格限定输出格式与当前 SDL 音频设备匹配：

```c
    if (force_output_format) {
        // 重配置时：强制匹配 SDL 音频设备的参数
        av_bprint_clear(&bp);
        av_channel_layout_describe_bprint(&is->audio_tgt.ch_layout, &bp);
        sample_rates[0] = is->audio_tgt.freq;

        // 关闭"允许任意声道数"
        if ((ret = av_opt_set_int(filt_asink, "all_channel_counts", 0,
                                   AV_OPT_SEARCH_CHILDREN)) < 0)
            goto end;
        // 限定声道布局
        if ((ret = av_opt_set(filt_asink, "ch_layouts", bp.str,
                               AV_OPT_SEARCH_CHILDREN)) < 0)
            goto end;
        // 限定采样率
        if ((ret = av_opt_set_int_list(filt_asink, "sample_rates",
                                        sample_rates, -1,
                                        AV_OPT_SEARCH_CHILDREN)) < 0)
            goto end;
    }
```

这确保了滤镜图输出的音频格式与 SDL 音频回调期望的格式完全一致，避免额外的格式转换。

### 4.4 swr_opts 重采样选项传递

与视频的 sws_opts 类似，音频滤镜图也支持传递 SwrContext 的选项：

```c
    // 收集 swr 重采样选项
    while ((e = av_dict_iterate(swr_opts, e)))
        av_strlcatf(aresample_swr_opts, sizeof(aresample_swr_opts),
                     "%s=%s:", e->key, e->value);
    if (strlen(aresample_swr_opts))
        aresample_swr_opts[strlen(aresample_swr_opts)-1] = '\0';

    // 设置到滤镜图的 aresample_swr_opts
    av_opt_set(is->agraph, "aresample_swr_opts", aresample_swr_opts, 0);
```

例如用户可以通过命令行指定 `-swr_flags` 来控制音频重采样的算法和质量。

### 4.5 最终组装

```c
    // 连接滤镜图
    if ((ret = configure_filtergraph(is->agraph, afilters,
                                      filt_asrc, filt_asink)) < 0)
        goto end;

    is->in_audio_filter  = filt_asrc;
    is->out_audio_filter = filt_asink;
```

注意音频滤镜图没有 autorotate 这类内置滤镜，所以直接将 `filt_asrc` 和 `filt_asink` 传入 `configure_filtergraph`。

## 5. 滤镜在解码线程中的集成

滤镜图构建完成后，需要在解码线程中实际使用。ffplay 的视频和音频解码线程都采用相同的模式：解码帧 → 送入滤镜 → 取出处理后的帧 → 入队。

![滤镜在解码线程中的集成位置](https://gitee.com/yuhong1234/ffplay/raw/master/10-filter-integration.png)

### 5.1 video_thread：视频解码线程中的滤镜

视频解码线程的滤镜集成逻辑（ffplay.c 行 2160-2261）：

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

    AVFilterGraph *graph = NULL;
    AVFilterContext *filt_out = NULL, *filt_in = NULL;
    int last_w = 0;
    int last_h = 0;
    enum AVPixelFormat last_format = -2;
    int last_serial = -1;
    int last_vfilter_idx = 0;

    // ...

    for (;;) {
        ret = get_video_frame(is, frame);
        if (ret < 0)
            goto the_end;
        if (!ret)
            continue;

        // 检测变化：分辨率、格式、serial、滤镜索引
        if (   last_w != frame->width
            || last_h != frame->height
            || last_format != frame->format
            || last_serial != is->viddec.pkt_serial
            || last_vfilter_idx != is->vfilter_idx) {

            // 重新创建滤镜图
            avfilter_graph_free(&graph);
            graph = avfilter_graph_alloc();
            graph->nb_threads = filter_nbthreads;

            if ((ret = configure_video_filters(graph, is,
                    vfilters_list ? vfilters_list[is->vfilter_idx] : NULL,
                    frame)) < 0) {
                // 配置失败，发送退出事件
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

        // 将解码帧送入滤镜图输入端
        ret = av_buffersrc_add_frame(filt_in, frame);
        if (ret < 0)
            goto the_end;

        // 循环取出所有处理后的帧
        while (ret >= 0) {
            is->frame_last_returned_time = av_gettime_relative() / 1000000.0;

            ret = av_buffersink_get_frame_flags(filt_out, frame, 0);
            if (ret < 0) {
                if (ret == AVERROR_EOF)
                    is->viddec.finished = is->viddec.pkt_serial;
                ret = 0;
                break;
            }

            // 计算滤镜处理延迟
            is->frame_last_filter_delay =
                av_gettime_relative() / 1000000.0 - is->frame_last_returned_time;
            if (fabs(is->frame_last_filter_delay) > AV_NOSYNC_THRESHOLD / 10.0)
                is->frame_last_filter_delay = 0;

            // 使用 buffersink 输出的时间基重新计算时间戳
            tb = av_buffersink_get_time_base(filt_out);
            duration = (frame_rate.num && frame_rate.den ?
                        av_q2d((AVRational){frame_rate.den, frame_rate.num}) : 0);
            pts = (frame->pts == AV_NOPTS_VALUE) ? NAN : frame->pts * av_q2d(tb);

            // 入队到 pictq
            ret = queue_picture(is, frame, pts, duration,
                                fd ? fd->pkt_pos : -1,
                                is->viddec.pkt_serial);
            av_frame_unref(frame);

            if (is->videoq.serial != is->viddec.pkt_serial)
                break;
        }
    }
 the_end:
    avfilter_graph_free(&graph);
    av_frame_free(&frame);
    return 0;
}
```

关键点说明：

1. **变化检测**：检查分辨率、像素格式、serial 和滤镜索引，任何变化都触发滤镜图重建
2. **滤镜延迟追踪**：`frame_last_filter_delay` 记录滤镜处理耗时，用于音视频同步中的延迟补偿
3. **一进多出**：一帧输入可能产生多帧输出（如插帧滤镜），所以用 while 循环取出

### 5.2 audio_thread：音频解码线程中的滤镜

音频线程的滤镜集成与视频类似，但增加了动态重配置逻辑（ffplay.c 行 2071-2147）：

```c
static int audio_thread(void *arg)
{
    VideoState *is = arg;
    AVFrame *frame = av_frame_alloc();
    int last_serial = -1;
    int reconfigure;
    int got_frame = 0;
    AVRational tb;
    int ret = 0;

    do {
        if ((got_frame = decoder_decode_frame(&is->auddec, frame, NULL)) < 0)
            goto the_end;

        if (got_frame) {
            tb = (AVRational){1, frame->sample_rate};

            // 检测音频格式是否变化
            reconfigure =
                cmp_audio_fmts(is->audio_filter_src.fmt,
                               is->audio_filter_src.ch_layout.nb_channels,
                               frame->format, frame->ch_layout.nb_channels) ||
                av_channel_layout_compare(&is->audio_filter_src.ch_layout,
                                          &frame->ch_layout) ||
                is->audio_filter_src.freq != frame->sample_rate ||
                is->auddec.pkt_serial    != last_serial;

            if (reconfigure) {
                // 更新滤镜源参数
                is->audio_filter_src.fmt  = frame->format;
                ret = av_channel_layout_copy(&is->audio_filter_src.ch_layout,
                                             &frame->ch_layout);
                is->audio_filter_src.freq = frame->sample_rate;
                last_serial               = is->auddec.pkt_serial;

                // 重配置音频滤镜（force_output_format=1）
                if ((ret = configure_audio_filters(is, afilters, 1)) < 0)
                    goto the_end;
            }

            // 送入滤镜图
            if ((ret = av_buffersrc_add_frame(is->in_audio_filter, frame)) < 0)
                goto the_end;

            // 取出处理后的帧
            while ((ret = av_buffersink_get_frame_flags(
                        is->out_audio_filter, frame, 0)) >= 0) {
                tb = av_buffersink_get_time_base(is->out_audio_filter);

                if (!(af = frame_queue_peek_writable(&is->sampq)))
                    goto the_end;

                af->pts = (frame->pts == AV_NOPTS_VALUE) ?
                          NAN : frame->pts * av_q2d(tb);
                af->serial = is->auddec.pkt_serial;
                af->duration = av_q2d((AVRational){frame->nb_samples,
                                                    frame->sample_rate});
                av_frame_move_ref(af->frame, frame);
                frame_queue_push(&is->sampq);
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

音频线程与视频线程的关键区别：

| 特性 | video_thread | audio_thread |
|------|-------------|-------------|
| 格式变化检测 | 分辨率 + 像素格式 + serial + 滤镜索引 | 采样率 + 采样格式 + 声道布局 + serial |
| 重配置方式 | 销毁并重建整个 graph | 调用 `configure_audio_filters(is, afilters, 1)` |
| force_output_format | 不适用 | 重配置时为 1（强制匹配 SDL 输出） |
| 滤镜切换 | 支持运行时切换（`vfilter_idx`） | 不支持运行时切换 |

## 6. 用户自定义滤镜

### 6.1 视频滤镜 -vf

用户通过 `-vf` 参数指定视频滤镜链：

```bash
# 缩放到 1280x720 并顺时针旋转 90 度
ffplay video.mp4 -vf "scale=1280:720,transpose=1"

# 水平翻转 + 添加文字水印
ffplay video.mp4 -vf "hflip,drawtext=text='Hello':fontsize=24:x=10:y=10"

# 使用外挂字幕
ffplay video.mp4 -vf "subtitles=sub.srt"
```

`-vf` 参数通过 `opt_add_vfilter` 回调函数处理：

```c
static int opt_add_vfilter(void *optctx, const char *opt, const char *arg)
{
    int ret = GROW_ARRAY(vfilters_list, nb_vfilters);
    if (ret < 0)
        return ret;

    vfilters_list[nb_vfilters - 1] = av_strdup(arg);
    if (!vfilters_list[nb_vfilters - 1])
        return AVERROR(ENOMEM);

    return 0;
}
```

每次 `-vf` 都将滤镜字符串追加到 `vfilters_list` 数组中。多个 `-vf` 参数不是叠加关系，而是形成可切换的滤镜列表，通过按 `w` 键在它们之间循环切换。

### 6.2 音频滤镜 -af

音频滤镜通过 `-af` 参数指定，存储在全局变量 `afilters` 中：

```bash
# 音量放大 2 倍
ffplay audio.mp3 -af "volume=2.0"

# 均衡器调节
ffplay audio.mp3 -af "equalizer=f=1000:t=h:width=200:g=-10"

# 组合使用
ffplay audio.mp3 -af "volume=1.5,aecho=0.8:0.88:60:0.4"
```

与视频不同，音频滤镜只支持一个 `-af` 参数，不支持运行时切换。

### 6.3 运行时切换视频滤镜（按 w 键）

ffplay 支持在播放过程中按 `w` 键切换视频滤镜，这是通过 `vfilter_idx` 索引实现的：

```c
case SDLK_w:
    if (cur_stream->show_mode == SHOW_MODE_VIDEO &&
        cur_stream->vfilter_idx < nb_vfilters - 1) {
        // 还有下一个滤镜，递增索引
        if (++cur_stream->vfilter_idx >= nb_vfilters)
            cur_stream->vfilter_idx = 0;
    } else {
        // 没有更多滤镜或不在视频模式，重置并切换显示模式
        cur_stream->vfilter_idx = 0;
        toggle_audio_display(cur_stream);
    }
    break;
```

切换的完整流程：

1. `w` 键按下 → `vfilter_idx` 递增
2. `video_thread` 主循环检测到 `last_vfilter_idx != is->vfilter_idx`
3. 触发滤镜图重建：`configure_video_filters(graph, is, vfilters_list[is->vfilter_idx], frame)`
4. 后续帧通过新的滤镜链处理

使用示例：

```bash
# 定义多个可切换的滤镜
ffplay video.mp4 -vf "negate" -vf "hflip" -vf "edgedetect"
# 播放时按 w 键依次切换：negate → hflip → edgedetect → 回到音频显示模式
```

## 7. 小结

本篇详细分析了 ffplay 中 AVFilter 滤镜系统的完整实现：

- **框架层**：`AVFilterGraph` 管理滤镜图，`buffersrc` / `buffersink` 分别作为输入输出端点，`configure_filtergraph` 提供了统一的图构建接口
- **视频滤镜**：`configure_video_filters` 负责构建完整的视频处理链，包括 autorotate 自动旋转、像素格式协商、SWS 缩放选项等
- **音频滤镜**：`configure_audio_filters` 构建音频处理链，支持动态重配置以应对格式变化，并提供 `force_output_format` 机制确保输出匹配 SDL 设备
- **线程集成**：视频和音频解码线程都采用 `av_buffersrc_add_frame` + `av_buffersink_get_frame_flags` 模式驱动滤镜图
- **用户交互**：支持 `-vf` / `-af` 命令行参数和运行时 `w` 键滤镜切换

滤镜系统是 ffplay 中设计最优雅的模块之一。它将复杂的图像/音频处理抽象为可组合的滤镜链，通过 libavfilter 的自动格式协商机制大大简化了开发者的工作。
