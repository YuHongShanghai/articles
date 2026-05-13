# 【从零手写播放器】附录 B：FFmpeg 常见错误码与排查指南

## 错误码处理方法

```cpp
// 将错误码转为可读字符串
char errbuf[AV_ERROR_MAX_STRING_SIZE];
av_strerror(ret, errbuf, sizeof(errbuf));
std::cerr << "错误: " << errbuf << " (code: " << ret << ")" << std::endl;
```

## 常见错误码

| 错误码 | 宏 | 含义 | 常见原因 |
| --- | --- | --- | --- |
| -2 | `AVERROR(ENOENT)` | No such file | 文件路径错误 |
| -5 | `AVERROR(EIO)` | I/O error | 文件损坏或网络中断 |
| -12 | `AVERROR(ENOMEM)` | Cannot allocate memory | 内存不足 |
| -22 | `AVERROR(EINVAL)` | Invalid argument | 参数无效 |
| | `AVERROR_EOF` | End of file | 到达文件末尾（正常） |
| | `AVERROR(EAGAIN)` | Resource temporarily unavailable | 需要更多输入（正常） |
| | `AVERROR_INVALIDDATA` | Invalid data | 数据损坏 |
| | `AVERROR_PATCHWELCOME` | Not yet implemented | 功能未实现 |
| | `AVERROR_DECODER_NOT_FOUND` | Decoder not found | 缺少解码器 |
| | `AVERROR_ENCODER_NOT_FOUND` | Encoder not found | 缺少编码器 |
| | `AVERROR_DEMUXER_NOT_FOUND` | Demuxer not found | 不支持的格式 |

## 常见问题排查

### 1. "No such file or directory"

```
原因：文件路径错误或文件不存在
排查：
  - 检查路径是否正确（注意中文路径、空格）
  - 检查文件权限
  - 对于网络 URL，检查网络连接
```

### 2. "Decoder not found"

```
原因：FFmpeg 编译时未包含所需解码器
排查：
  - 运行 ffmpeg -decoders | grep h264 检查是否支持
  - 重新编译 FFmpeg 时 --enable-libx264 等
  - 安装完整版 FFmpeg（非精简版）
```

### 3. "Invalid data found when processing input"

```
原因：文件损坏或格式不匹配
排查：
  - 用 ffprobe 检查文件是否能正常解析
  - 尝试用 ffmpeg -i input.mp4 -c copy repaired.mp4 修复
  - 检查是否错误指定了输入格式
```

### 4. 解码后画面花屏/绿屏

```
原因：
  - 未正确处理 linesize（使用了 width 而非 linesize）
  - 解码器未初始化完成就开始解码
  - Seek 后未 flush 解码器
排查：
  - 检查 sws_scale 的参数
  - 确保 avcodec_open2 调用成功
  - Seek 后调用 avcodec_flush_buffers
```

### 5. 音频杂音/爆音

```
原因：
  - 采样格式不匹配（如 float 数据按 s16 播放）
  - 采样率不匹配
  - SDL 回调中阻塞时间过长
排查：
  - 检查重采样配置是否与 SDL AudioSpec 一致
  - 回调函数中避免耗时操作
  - 缓冲区不足时填充静音而非阻塞
```

### 6. 音视频不同步

```
原因：
  - PTS 时间基转换错误
  - 音频时钟更新不及时
  - 丢帧阈值设置不当
排查：
  - 打印 video_pts 和 audio_clock 的差值
  - 确保 av_q2d(time_base) 转换正确
  - 检查音频时钟的 update 时机
```

### 7. Seek 后画面卡住

```
原因：
  - 未清空队列中的旧数据
  - 未 flush 解码器缓冲
  - 线程阻塞在旧的 pop 操作上
排查：
  - Seek 后先 flush 队列，再 flush 解码器
  - 确保队列的 flush 能唤醒阻塞的消费者
```

### 8. 内存泄漏

```
常见泄漏点：
  - AVPacket 使用后未 av_packet_unref
  - AVFrame 使用后未 av_frame_unref
  - AVFormatContext 未 avformat_close_input
  - AVCodecContext 未 avcodec_free_context
  - SwsContext 未 sws_freeContext
  - SwrContext 未 swr_free
  - av_malloc 的内存未 av_free

检查工具：
  - Valgrind: valgrind --leak-check=full ./player video.mp4
  - AddressSanitizer: 编译时加 -fsanitize=address
```

## 调试技巧

### 设置 FFmpeg 日志级别

```cpp
// 详细日志
av_log_set_level(AV_LOG_DEBUG);

// 只显示错误
av_log_set_level(AV_LOG_ERROR);

// 自定义日志回调
av_log_set_callback([](void* ptr, int level, const char* fmt, va_list vl) {
    if (level <= AV_LOG_WARNING) {
        vfprintf(stderr, fmt, vl);
    }
});
```

### 使用 av_dump_format

```cpp
// 打印文件格式详情（快速诊断工具）
av_dump_format(fmt_ctx, 0, filename, 0);  // 0 = 输入
```

