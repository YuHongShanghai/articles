# 附录 C：项目完整 CMakeLists.txt 与编译指南

## 系统要求

| 依赖 | 最低版本 | 安装方式 |
| --- | --- | --- |
| CMake | 3.16+ | 包管理器或官网下载 |
| C++ 编译器 | 支持 C++17 | GCC 7+ / Clang 5+ / MSVC 2017+ |
| FFmpeg | 5.0+ | 包管理器或源码编译 |
| SDL2 | 2.0.12+ | 包管理器 |
| SDL2_ttf | 2.0.15+（可选） | 包管理器 |

## 安装依赖

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y \
    build-essential cmake pkg-config \
    libavformat-dev libavcodec-dev libavutil-dev \
    libswscale-dev libswresample-dev libavfilter-dev \
    libsdl2-dev libsdl2-ttf-dev
```

### Fedora

```bash
sudo dnf install -y \
    gcc-c++ cmake pkgconfig \
    ffmpeg-devel SDL2-devel SDL2_ttf-devel
```

### macOS

```bash
brew install cmake ffmpeg sdl2 sdl2_ttf pkg-config
```

### Windows (vcpkg)

```bash
vcpkg install ffmpeg:x64-windows sdl2:x64-windows sdl2-ttf:x64-windows
```

## 编译步骤

```bash
# 进入项目目录
cd ffmpeg-player-tutorial

# 创建构建目录
mkdir build && cd build

# 生成构建文件
cmake ..

# 编译所有目标
make -j$(nproc)

# 或者只编译某一章
make hello-ffmpeg
make media-info
make decode-first-frame
make video-decode
make audio-decode
make sdl-video
make sdl-audio
make queue-test
make multithread-decode
make av-sync-player
make player-controls
make final-player
make subtitle-demo
```

## 运行

```bash
# 生成测试视频
ffmpeg -y \
  -f lavfi -i "testsrc2=size=1280x720:rate=24:duration=30" \
  -f lavfi -i "sine=frequency=440:duration=30:sample_rate=48000" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  test_video.mp4

# 运行各章 Demo
./chapter-05-hello-ffmpeg/hello-ffmpeg
./chapter-06-media-info/media-info ../test_video.mp4
./chapter-07-decode-first-frame/decode-first-frame ../test_video.mp4
./chapter-08-video-decode/video-decode ../test_video.mp4 50
./chapter-09-audio-decode/audio-decode ../test_video.mp4
./chapter-10-sdl-video/sdl-video ../test_video.mp4
./chapter-11-sdl-audio/sdl-audio ../test_video.mp4
./chapter-12-queue/queue-test ../test_video.mp4
./chapter-13-multithread/multithread-decode ../test_video.mp4
./chapter-14-av-sync/av-sync-player ../test_video.mp4
./chapter-15-controls/player-controls ../test_video.mp4
./chapter-16-final-player/final-player ../test_video.mp4
```

## 常见编译问题

### 找不到 FFmpeg 头文件

```
error: libavformat/avformat.h: No such file or directory
```

解决：确认 FFmpeg 开发库已安装，检查 pkg-config 能否找到：

```bash
pkg-config --cflags --libs libavformat
```

### 链接错误 "undefined reference"

```
undefined reference to `avformat_open_input'
```

解决：检查 CMakeLists.txt 中的 `target_link_libraries` 是否包含所有需要的库。

### SDL2 相关错误

```
fatal error: SDL2/SDL.h: No such file or directory
```

解决：安装 SDL2 开发库：`sudo apt install libsdl2-dev`

---

> 返回 [第 18 章：回顾与展望](18-回顾与展望.md)
