# ffplay 源码解析系列（八）：音频可视化——波形与频谱显示

> 基于 FFmpeg 7.1.2 版本 ffplay.c 源码分析
>
> 当没有视频流或用户按下 `w` 键时，ffplay 会以波形（Waves）或频谱（RDFT）的方式将音频数据可视化。本篇深入分析 ffplay 音频可视化的完整实现，涵盖采样缓存、波形绘制、RDFT 频谱计算与渲染。

## 👉[专栏链接](https://blog.csdn.net/qq_29681777/category_13130860.html)

## 1. 三种显示模式

ffplay 定义了一个枚举 `ShowMode`，用于控制窗口的显示内容（ffplay.c 行 257-259）：

```c
enum ShowMode {
    SHOW_MODE_NONE = -1,   // 未初始化
    SHOW_MODE_VIDEO = 0,   // 视频画面显示
    SHOW_MODE_WAVES,       // 音频波形显示（时域）
    SHOW_MODE_RDFT,        // 音频频谱显示（频域）
    SHOW_MODE_NB           // 模式总数（用于取模循环）
} show_mode;
```

三种有效模式的特点如下：

| 模式 | 含义 | 数据来源 | 显示效果 |
|------|------|---------|---------|
| `SHOW_MODE_VIDEO` | 视频画面 | 解码后的视频帧 | 正常视频播放 |
| `SHOW_MODE_WAVES` | 波形图 | sample_array 采样缓冲 | 类似示波器的波形曲线 |
| `SHOW_MODE_RDFT` | 频谱图 | sample_array 经 RDFT 变换 | 瀑布式频谱色彩图 |

![三种显示模式对比](https://gitee.com/yuhong1234/ffplay/raw/master/08-show-modes.png)

### 1.1 模式的初始选择

在 `stream_open()` 打开流时，ffplay 会根据是否存在视频流来决定初始模式（ffplay.c 行 2992-2993）：

```c
if (is->show_mode == SHOW_MODE_NONE)
    is->show_mode = ret >= 0 ? SHOW_MODE_VIDEO : SHOW_MODE_RDFT;
```

- 如果视频流打开成功（`ret >= 0`），默认为 `SHOW_MODE_VIDEO`
- 如果没有视频流（纯音频文件），默认为 `SHOW_MODE_RDFT`（频谱模式）

### 1.2 toggle_audio_display() 模式切换

用户按下 `w` 键时触发模式切换，实现在 `toggle_audio_display()` 中（ffplay.c 行 3296-3306）：

```c
static void toggle_audio_display(VideoState *is)
{
    int next = is->show_mode;
    do {
        // 循环遍历模式：VIDEO -> WAVES -> RDFT -> VIDEO ...
        next = (next + 1) % SHOW_MODE_NB;
    } while (next != is->show_mode &&
             // 跳过不可用的模式：没有视频流则跳过 VIDEO，没有音频流则跳过 WAVES/RDFT
             (next == SHOW_MODE_VIDEO && !is->video_st ||
              next != SHOW_MODE_VIDEO && !is->audio_st));
    if (is->show_mode != next) {
        is->force_refresh = 1;  // 强制刷新显示
        is->show_mode = next;
    }
}
```

关键设计点：
- **循环切换**：使用 `% SHOW_MODE_NB` 实现模式的环形切换
- **可用性检查**：如果没有视频流，跳过 `SHOW_MODE_VIDEO`；没有音频流，跳过波形和频谱模式
- **强制刷新**：切换后设置 `force_refresh = 1`，确保下一帧立即重绘

### 1.3 显示分发逻辑

在 `video_display()` 中，根据当前模式选择不同的绘制函数（ffplay.c 行 1377-1379）：

```c
SDL_RenderClear(renderer);
if (is->audio_st && is->show_mode != SHOW_MODE_VIDEO)
    video_audio_display(is);      // 波形或频谱
else if (is->video_st)
    video_image_display(is);      // 视频画面
```

而在 `video_refresh()` 中，音频可视化模式有独立的刷新频率控制（ffplay.c 行 1596-1597）：

```c
if (!display_disable && is->show_mode != SHOW_MODE_VIDEO && is->audio_st) {
    time = av_gettime_relative() / 1000000.0;
    if (is->force_refresh || is->last_vis_time + rdftspeed < time) {
        video_display(is);
        is->last_vis_time = time;
    }
    // ...
}
```

其中 `rdftspeed` 默认为 0.02 秒，即音频可视化的刷新率约为 **50 FPS**。

## 2. update_sample_display()：采样数据缓存

音频可视化的数据来源是 `sample_array`——一个存储在 `VideoState` 中的环形缓冲区。

### 2.1 数据结构

```c
#define SAMPLE_ARRAY_SIZE (8 * 65536)   // 524288 个采样点

// VideoState 中的相关字段
int16_t sample_array[SAMPLE_ARRAY_SIZE];  // 采样数据环形缓冲区
int sample_array_index;                    // 当前写入位置
```

`SAMPLE_ARRAY_SIZE = 524288`，按 44100Hz 立体声计算，可以缓存约 `524288 / (44100 * 2) ≈ 5.9 秒` 的音频数据。

### 2.2 数据写入

`update_sample_display()` 在 SDL 音频回调中被调用，将解码后的 PCM 采样拷贝到环形缓冲区（ffplay.c 行 2297-2313）：

```c
/* copy samples for viewing in editor window */
static void update_sample_display(VideoState *is, short *samples, int samples_size)
{
    int size, len;

    size = samples_size / sizeof(short);   // 字节数转为采样点数
    while (size > 0) {
        // 计算本次可以拷贝的长度（到缓冲区末尾的剩余空间）
        len = SAMPLE_ARRAY_SIZE - is->sample_array_index;
        if (len > size)
            len = size;
        // 拷贝采样数据到环形缓冲区
        memcpy(is->sample_array + is->sample_array_index, samples, len * sizeof(short));
        samples += len;
        is->sample_array_index += len;
        // 环形回绕
        if (is->sample_array_index >= SAMPLE_ARRAY_SIZE)
            is->sample_array_index = 0;
        size -= len;
    }
}
```

### 2.3 调用时机

在 `sdl_audio_callback()` 中，只有当显示模式不是纯视频时才会调用（ffplay.c 行 2491-2492）：

```c
if (is->show_mode != SHOW_MODE_VIDEO)
    update_sample_display(is, (int16_t *)is->audio_buf, audio_size);
```

这是一个性能优化——在纯视频模式下，不需要为可视化缓存采样数据。

## 3. video_audio_display()：音频可视化主函数

`video_audio_display()` 是整个音频可视化的核心入口函数。它的结构可以分为三个阶段：公共计算、波形绘制和频谱绘制。

### 3.1 公共部分：计算显示起始位置

函数开头首先做一些公共的准备工作（ffplay.c 行 1058-1109）：

```c
static void video_audio_display(VideoState *s)
{
    int i, i_start, x, y1, y, ys, delay, n, nb_display_channels;
    int ch, channels, h, h2;
    int64_t time_diff;
    int rdft_bits, nb_freq;

    // 确定 RDFT 所需的位数：2^rdft_bits >= 2 * height
    for (rdft_bits = 1; (1 << rdft_bits) < 2 * s->height; rdft_bits++)
        ;
    nb_freq = 1 << (rdft_bits - 1);  // 频率分量数 = 窗口高度对齐到 2 的幂

    /* 计算显示起始索引：居中到当前输出的采样位置 */
    channels = s->audio_tgt.ch_layout.nb_channels;
    nb_display_channels = channels;
    if (!s->paused) {
        // 波形模式需要 width 个采样点，频谱模式需要 2*nb_freq 个
        int data_used = s->show_mode == SHOW_MODE_WAVES ? s->width : (2 * nb_freq);
        n = 2 * channels;
        delay = s->audio_write_buf_size;
        delay /= n;

        /* 修正延迟：减去从上次回调到现在的时间流逝 */
        if (audio_callback_time) {
            time_diff = av_gettime_relative() - audio_callback_time;
            delay -= (time_diff * s->audio_tgt.freq) / 1000000;
        }

        delay += 2 * data_used;
        if (delay < data_used)
            delay = data_used;

        // 从 sample_array 中计算起始位置
        i_start = x = compute_mod(s->sample_array_index - delay * channels,
                                   SAMPLE_ARRAY_SIZE);
```

这里有两个关键点：

**延迟补偿**：`delay` 表示"当前正在播放的采样相对于 `sample_array_index`（最后写入位置）的偏移量"。由于音频设备有缓冲，实际播放位置比最新写入位置要落后一段距离。通过 `audio_write_buf_size` 和时间差修正，让可视化内容尽量与听到的声音同步。

**compute_mod 辅助函数**：

```c
static inline int compute_mod(int a, int b)
{
    return a < 0 ? a%b + b : a%b;
}
```

这是一个始终返回非负数的取模运算，用于在环形缓冲区中安全地回绕负索引。

### 3.2 波形起始点优化：零交叉点检测

对于波形模式，ffplay 不是简单地从计算出的 `i_start` 开始绘制，而是在附近搜索一个"视觉上更稳定"的起始点（ffplay.c 行 1090-1103）：

```c
if (s->show_mode == SHOW_MODE_WAVES) {
    h = INT_MIN;
    for (i = 0; i < 1000; i += channels) {
        int idx = (SAMPLE_ARRAY_SIZE + x - i) % SAMPLE_ARRAY_SIZE;
        int a = s->sample_array[idx];                                    // 当前采样
        int b = s->sample_array[(idx + 4 * channels) % SAMPLE_ARRAY_SIZE]; // 稍后的采样
        int c = s->sample_array[(idx + 5 * channels) % SAMPLE_ARRAY_SIZE]; // 再稍后
        int d = s->sample_array[(idx + 9 * channels) % SAMPLE_ARRAY_SIZE]; // 更后面
        int score = a - d;         // 倾斜度评分
        if (h < score && (b ^ c) < 0) {  // b 和 c 异号 = 零交叉
            h = score;
            i_start = idx;
        }
    }
}
```

这个算法的目的是找到一个**零交叉点**（zero-crossing），使波形看起来更加稳定，不会随机跳动：

1. **零交叉检测**：`(b ^ c) < 0` 判断 `b` 和 `c` 是否异号（一个正一个负），即波形穿过零点
2. **倾斜度评分**：`score = a - d` 表示波形的下降幅度，优先选择从高到低穿越零点的位置
3. **搜索范围**：在 `i_start` 之前的 1000 个采样点内搜索

这种技术类似于示波器的**触发功能**（triggering），让波形显示像"静止"一样，大幅提升视觉体验。

## 4. SHOW_MODE_WAVES：波形绘制

当确定了 `i_start` 后，波形模式开始逐通道绘制（ffplay.c 行 1111-1141）：

```c
if (s->show_mode == SHOW_MODE_WAVES) {
    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);  // 白色波形

    /* total height for one channel */
    h = s->height / nb_display_channels;
    /* graph height / 2 */
    h2 = (h * 9) / 20;   // 每通道可用高度的 45%（上下各 45%，留 10% 间距）
    for (ch = 0; ch < nb_display_channels; ch++) {
        i = i_start + ch;                       // 各通道交错存储
        y1 = s->ytop + ch * h + (h / 2);        // 通道中心线 Y 坐标
        for (x = 0; x < s->width; x++) {
            // 将 16 位采样映射到像素高度：sample * h2 / 32768
            y = (s->sample_array[i] * h2) >> 15;
            if (y < 0) {
                y = -y;
                ys = y1 - y;  // 负值：从中心线向上画
            } else {
                ys = y1;      // 正值：从中心线向下画
            }
            fill_rectangle(s->xleft + x, ys, 1, y);  // 画 1 像素宽的竖线
            i += channels;                             // 交错采样：跳过其他通道
            if (i >= SAMPLE_ARRAY_SIZE)
                i -= SAMPLE_ARRAY_SIZE;
        }
    }

    SDL_SetRenderDrawColor(renderer, 0, 0, 255, 255);  // 蓝色分隔线

    // 绘制通道间的分隔线
    for (ch = 1; ch < nb_display_channels; ch++) {
        y = s->ytop + ch * h;
        fill_rectangle(s->xleft, y, s->width, 1);
    }
```

波形绘制的关键细节：

- **逐像素列绘制**：每个 x 坐标对应一个采样点，绘制一条从中心线到采样值的竖线
- **采样到像素映射**：`>> 15` 等效于除以 32768（int16 最大值），将采样值归一化到像素高度
- **多通道分区**：屏幕纵向均分给每个通道，蓝色线条分隔
- **交错跳步**：立体声数据是 `L R L R ...` 交错的，所以 `i += channels` 可以跳过其他通道

## 5. SHOW_MODE_RDFT：频谱绘制

频谱模式是 ffplay 可视化中最复杂的部分，涉及 DSP（数字信号处理）的多个概念。

### 5.1 DSP 基础：时域与频域

在深入代码之前，先了解几个关键概念。

**什么是 RDFT？**

RDFT（Real Discrete Fourier Transform，实数离散傅里叶变换）是 DFT 的一种优化形式，专门用于实数输入信号。音频 PCM 数据就是实数序列，因此使用 RDFT 比通用 DFT 更高效。

RDFT 将时域信号（随时间变化的振幅值）转换为频域信号（各频率分量的幅度和相位）。

**时域 vs 频域**

- **时域**：横轴是时间，纵轴是振幅。就是我们在波形模式看到的图形
- **频域**：横轴是频率，纵轴是幅度。揭示了信号中各频率成分的强弱

例如，一个钢琴弹奏的 A4 音（440Hz）在时域上是复杂的波形，在频域上会在 440Hz 处出现一个尖峰，加上若干谐波（880Hz、1320Hz 等）。

**窗函数的作用**

直接对有限长度的信号做 FFT 会产生**频谱泄漏**（spectral leakage），因为信号在截断边界处不连续。窗函数通过让信号两端平滑地衰减到零来减轻这个问题。

ffplay 使用的是一种类 Hanning 窗（二次余弦窗）：

```
w(x) = 1 - ((x - N) / N)^2
```

其中 N 是窗口半宽。在窗口中心权重为 1，两端权重为 0，形成钟形曲线。

### 5.2 RDFT 初始化

频谱模式首先检查并初始化 RDFT 上下文（ffplay.c 行 1142-1160）：

```c
} else {
    int err = 0;
    // 分配/重新分配 vis_texture（ARGB8888 格式）
    if (realloc_texture(&s->vis_texture, SDL_PIXELFORMAT_ARGB8888,
                        s->width, s->height, SDL_BLENDMODE_NONE, 1) < 0)
        return;

    if (s->xpos >= s->width)
        s->xpos = 0;               // 绘制位置回绕到最左边
    nb_display_channels = FFMIN(nb_display_channels, 2);  // 频谱模式最多显示 2 通道

    // 当 rdft_bits 改变时（窗口大小变化），重新初始化 RDFT
    if (rdft_bits != s->rdft_bits) {
        const float rdft_scale = 1.0;
        av_tx_uninit(&s->rdft);          // 释放旧的 RDFT 上下文
        av_freep(&s->real_data);          // 释放旧的输入缓冲区
        av_freep(&s->rdft_data);          // 释放旧的输出缓冲区
        s->rdft_bits = rdft_bits;
        // 分配输入缓冲区：每通道 2*nb_freq 个 float（RDFT 输入窗口大小）
        s->real_data = av_malloc_array(nb_freq, 4 * sizeof(*s->real_data));
        // 分配输出缓冲区：每通道 (nb_freq+1) 个 AVComplexFloat
        s->rdft_data = av_malloc_array(nb_freq + 1, 2 * sizeof(*s->rdft_data));
        // 初始化 RDFT：AV_TX_FLOAT_RDFT 类型，正变换（方向 0）
        err = av_tx_init(&s->rdft, &s->rdft_fn, AV_TX_FLOAT_RDFT,
                         0, 1 << rdft_bits, &rdft_scale, 0);
    }
```

这里使用 FFmpeg 7.x 的新 TX（Transform）API 而非旧的 `av_rdft_init`。`AVTXContext` 和 `av_tx_fn` 是更通用的变换框架，支持 FFT、RDFT、DCT 等多种变换类型。

### 5.3 窗函数应用与 RDFT 变换

接下来是 RDFT 计算的核心（ffplay.c 行 1164-1183）：

```c
float *data_in[2];           // 每通道的 RDFT 输入（实数序列）
AVComplexFloat *data[2];     // 每通道的 RDFT 输出（复数序列）
SDL_Rect rect = {.x = s->xpos, .y = 0, .w = 1, .h = s->height};
uint32_t *pixels;
int pitch;

for (ch = 0; ch < nb_display_channels; ch++) {
    data_in[ch] = s->real_data + 2 * nb_freq * ch;   // 输入缓冲区偏移
    data[ch] = s->rdft_data + nb_freq * ch;           // 输出缓冲区偏移
    i = i_start + ch;

    for (x = 0; x < 2 * nb_freq; x++) {
        // 窗函数：w = (x - nb_freq) / nb_freq，范围 [-1, 1]
        double w = (x - nb_freq) * (1.0 / nb_freq);
        // 应用窗函数：sample * (1 - w^2)，类 Hanning 窗
        data_in[ch][x] = s->sample_array[i] * (1.0 - w * w);
        i += channels;
        if (i >= SAMPLE_ARRAY_SIZE)
            i -= SAMPLE_ARRAY_SIZE;
    }
    // 执行 RDFT 变换
    s->rdft_fn(s->rdft, data[ch], data_in[ch], sizeof(float));
    // 特殊处理：Nyquist 频率分量存储在 data[0].im 中
    data[ch][0].im = data[ch][nb_freq].re;
    data[ch][nb_freq].re = 0;
}
```

逐步解析：

1. **窗函数应用**：`(1.0 - w * w)` 是一个开口朝下的抛物线，在 `x = nb_freq`（中心）时值为 1，在 `x = 0` 和 `x = 2*nb_freq`（两端）时值为 0。这有效地减少了频谱泄漏
2. **采样读取**：以通道交错步长 `channels` 从 `sample_array` 中读取数据
3. **RDFT 执行**：`rdft_fn` 是函数指针，调用 FFmpeg TX 框架的高性能 RDFT 实现
4. **Nyquist 处理**：RDFT 的输出中，DC 和 Nyquist 分量的虚部为零，FFmpeg 将 Nyquist 的实部打包到 `data[0].im`，这里将其还原到正确位置

![RDFT 频谱计算流程](https://gitee.com/yuhong1234/ffplay/raw/master/08-rdft-pipeline.png)

### 5.4 频谱数据到颜色的映射

RDFT 输出是复数频谱，需要转换为可见的颜色值（ffplay.c 行 1187-1201）：

```c
/* Least efficient way to do this, we should of course
 * directly access it but it is more than fast enough. */
if (!SDL_LockTexture(s->vis_texture, &rect, (void **)&pixels, &pitch)) {
    pitch >>= 2;              // 字节 pitch 转为像素 pitch（ARGB = 4 bytes）
    pixels += pitch * s->height;  // 从底部开始（低频在下）
    for (y = 0; y < s->height; y++) {
        double w = 1 / sqrt(nb_freq);    // 归一化因子
        // 左声道幅度：对复数取模（sqrt(re^2 + im^2)），再开方（压缩动态范围）
        int a = sqrt(w * sqrt(data[0][y].re * data[0][y].re +
                              data[0][y].im * data[0][y].im));
        // 右声道幅度（单声道时使用左声道值）
        int b = (nb_display_channels == 2)
                ? sqrt(w * hypot(data[1][y].re, data[1][y].im))
                : a;
        a = FFMIN(a, 255);    // 钳制到 [0, 255]
        b = FFMIN(b, 255);
        pixels -= pitch;       // 从下往上填充（低频在底部）
        // ARGB 像素：R = 左声道, G = 右声道, B = (左+右)/2
        *pixels = (a << 16) + (b << 8) + ((a + b) >> 1);
    }
    SDL_UnlockTexture(s->vis_texture);
}
SDL_RenderCopy(renderer, s->vis_texture, NULL, NULL);
```

颜色映射策略的巧妙之处：

- **双重开方**：先对频谱幅度开方（`sqrt(re^2 + im^2)`），再对结果开方。两次开方相当于取四次方根，大幅压缩了动态范围，使得弱信号也能可见
- **颜色编码**：
  - **R 通道**（红色）= 左声道幅度
  - **G 通道**（绿色）= 右声道幅度
  - **B 通道**（蓝色）= 两通道平均
  - 单声道时 a == b，呈现灰白色
  - 左声道强时偏红/品红
  - 右声道强时偏绿/青色
  - 左右均衡时呈白色/灰色
- **纵向倒置**：`pixels -= pitch` 使低频在屏幕底部、高频在顶部，符合直觉

### 5.5 瀑布式显示与纹理管理

频谱图采用"瀑布式"（waterfall）显示——每帧只绘制一列像素，逐步向右推进：

```c
SDL_Rect rect = {.x = s->xpos, .y = 0, .w = 1, .h = s->height};
// ... 在 rect 区域内绘制一列频谱 ...

SDL_RenderCopy(renderer, s->vis_texture, NULL, NULL);  // 渲染整个纹理

if (!s->paused)
    s->xpos++;     // 下一帧的 x 位置右移一列
```

以及开头的回绕检查：

```c
if (s->xpos >= s->width)
    s->xpos = 0;    // 到达右边界后回到最左边
```

`vis_texture` 是一个 `SDL_Texture`，尺寸与窗口相同，格式为 `SDL_PIXELFORMAT_ARGB8888`。它的生命周期：

1. **创建/重建**：每次调用 `video_audio_display()` 时通过 `realloc_texture()` 确保尺寸正确
2. **逐列更新**：每帧锁定 1 像素宽的列区域，写入频谱数据
3. **全量渲染**：通过 `SDL_RenderCopy` 将整个纹理渲染到屏幕
4. **销毁**：在 `stream_close()` 中随 `VideoState` 一起释放

这种设计的效果是频谱图像从左向右"流动"，形成类似于声谱图（spectrogram）的瀑布式显示。旧的频谱数据自然保留在纹理中，新的数据覆盖最左端的旧列。

### 5.6 RDFT 错误降级

如果 RDFT 初始化失败（例如内存分配失败），ffplay 会自动降级到波形模式：

```c
if (err < 0 || !s->rdft_data) {
    av_log(NULL, AV_LOG_ERROR,
           "Failed to allocate buffers for RDFT, switching to waves display\n");
    s->show_mode = SHOW_MODE_WAVES;
}
```

## 6. 完整流程总结

将上述内容串起来，音频可视化的完整数据流如下：

```
sdl_audio_callback()               video_display()
       |                                 |
       v                                 v
  audio_decode_frame()           video_audio_display()
       |                           /           \
       v                     WAVES 模式      RDFT 模式
  update_sample_display()        |               |
       |                    零交叉检测     窗函数 + RDFT 变换
       v                         |               |
  sample_array[]             逐像素绘制      频谱->颜色映射
  (环形缓冲区)                   |               |
                            SDL Renderer    vis_texture 逐列更新
                                 |               |
                                 v               v
                              屏幕输出         屏幕输出
```

核心要点：

1. **数据采集**：`sdl_audio_callback` -> `update_sample_display` -> `sample_array`（环形缓冲区）
2. **延迟补偿**：通过 `audio_write_buf_size` 和时间差计算当前播放位置对应的采样索引
3. **波形模式**：零交叉检测找稳定起始点，逐像素绘制白色柱状波形，多通道垂直分区
4. **频谱模式**：Hanning 窗 -> RDFT 变换 -> 双重开方压缩 -> RGB 颜色映射 -> 逐列纹理更新
5. **显示刷新**：独立于视频帧率，以 `rdftspeed`（默认 50 FPS）控制刷新

## 7. 小结

本篇深入分析了 ffplay 音频可视化的完整实现：

- **三种显示模式**：`SHOW_MODE_VIDEO`（视频）、`SHOW_MODE_WAVES`（波形）、`SHOW_MODE_RDFT`（频谱），通过 `toggle_audio_display()` 循环切换
- **采样缓存**：`update_sample_display()` 使用环形缓冲区 `sample_array` 收集 PCM 数据，在 `sdl_audio_callback` 中按需调用
- **波形绘制**：零交叉点检测稳定显示，逐像素列绘制白色波形，支持多通道
- **频谱绘制**：使用 FFmpeg TX API 的 RDFT，Hanning 窗降低泄漏，双重开方压缩动态范围，RGB 编码双通道信息，瀑布式纹理更新
- **DSP 知识**：理解了时域与频域的区别、窗函数的意义、RDFT 的原理

ffplay 的音频可视化代码量不大（约 150 行），但涵盖了数字信号处理、图形渲染、环形缓冲区等多个领域的知识。其波形模式的零交叉检测和频谱模式的颜色映射方案都是实用且巧妙的工程设计。
