# FFmpeg 音视频开发入门教程 —— 从零构建视频播放器

本项目是一套系统的音视频开发入门教程的配套代码，目标是带领读者使用 FFmpeg C++ API + SDL2 从零构建一个功能完备的视频播放器。

## 教程结构

| 章节 | 目录 | 可执行文件 | 功能 |
| --- | --- | --- | --- |
| 第 5 章 | chapter-05-hello-ffmpeg | hello-ffmpeg | 打印 FFmpeg 版本和编解码器列表 |
| 第 6 章 | chapter-06-media-info | media-info | 打印视频文件详细信息（类似 ffprobe） |
| 第 7 章 | chapter-07-decode-first-frame | decode-first-frame | 解码第一帧视频并保存为 PPM 图片 |
| 第 8 章 | chapter-08-video-decode | video-decode | 连续视频解码，保存 BMP 图片序列 |
| 第 9 章 | chapter-09-audio-decode | audio-decode | 音频解码和重采样，保存 PCM 文件 |
| 第 10 章 | chapter-10-sdl-video | sdl-video | SDL2 窗口实时视频渲染 |
| 第 11 章 | chapter-11-sdl-audio | sdl-audio | SDL2 实时音频播放 |
| 第 12 章 | chapter-12-queue | queue-test | 线程安全队列测试 |
| 第 13 章 | chapter-13-multithread | multithread-decode | 多线程解封装和解码 |
| 第 14 章 | chapter-14-av-sync | av-sync-player | 音视频同步播放器 |
| 第 15 章 | chapter-15-controls | player-controls | 带播放控制的播放器 |
| 第 16 章 | chapter-16-final-player | final-player | 最终版完整播放器 |
| 第 17 章 | chapter-17-subtitle | subtitle-demo | 字幕渲染演示 |

## 依赖

- CMake >= 3.16
- C++17 编译器
- FFmpeg 开发库（libavformat, libavcodec, libavutil, libswscale, libswresample）
- SDL2
- SDL2_ttf（可选，第 17 章需要）

## 快速开始

```bash
# Ubuntu/Debian 安装依赖
sudo apt install -y build-essential cmake pkg-config \
    libavformat-dev libavcodec-dev libavutil-dev \
    libswscale-dev libswresample-dev \
    libsdl2-dev libsdl2-ttf-dev

# 编译
mkdir build && cd build
cmake ..
make -j$(nproc)

# 生成测试视频
ffmpeg -y \
    -f lavfi -i "testsrc2=size=1280x720:rate=24:duration=30" \
    -f lavfi -i "sine=frequency=440:duration=30:sample_rate=48000" \
    -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k \
    test_video.mp4

# 运行最终版播放器
./chapter-16-final-player/final-player test_video.mp4
```

## 最终播放器快捷键

| 按键 | 功能 |
| --- | --- |
| 空格 | 暂停/恢复 |
| ← | 快退 10 秒 |
| → | 快进 10 秒 |
| ↑ | 音量增加 |
| ↓ | 音量减少 |
| ESC / Q | 退出 |
| 鼠标点击进度条 | 跳转 |

## 配套文章

完整教程文章位于上级目录，共 18 章 + 4 个附录。

## 许可

教程代码仅供学习参考。
