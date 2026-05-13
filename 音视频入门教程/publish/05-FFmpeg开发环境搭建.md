# 【从零手写播放器】第 5 章：FFmpeg 开发环境搭建

> 从本章开始，我们正式进入 FFmpeg 编程阶段。本章将介绍 FFmpeg 的架构和核心库，并带你搭建开发环境，编写第一个 FFmpeg 程序。

## 5.1 FFmpeg 简介

FFmpeg 是一个开源的多媒体框架，能够解码、编码、转码、复用、解复用、过滤几乎所有格式的音视频数据。它包含：

### 命令行工具

- **ffmpeg**：多媒体转码和处理的瑞士军刀
- **ffprobe**：多媒体文件分析工具
- **ffplay**：简易的多媒体播放器

### 开发库（本教程重点）

FFmpeg 提供了 6 个核心库：

| 库 | 全称 | 功能 | 我们是否使用 |
| --- | --- | --- | --- |
| **libavformat** | Audio Video Format | 封装/解封装（Mux/Demux） | 是 |
| **libavcodec** | Audio Video Codec | 编解码 | 是 |
| **libavutil** | Audio Video Utility | 工具函数、数据结构 | 是 |
| **libswscale** | Software Scale | 图像缩放和像素格式转换 | 是 |
| **libswresample** | Software Resample | 音频重采样 | 是 |
| libavfilter | Audio Video Filter | 音视频滤镜 | 本教程不涉及 |

![FFmpeg 六大核心库](https://gitee.com/yuhong1234/ffmpeg-player-tutorial/raw/master/images/diagram-05-ffmpeg-libs.png)

它们在播放器中的分工：

![FFmpeg 核心库协作流程](https://gitee.com/yuhong1234/ffmpeg-player-tutorial/raw/master/images/diagram-05-ffmpeg-pipeline.png)

## 5.2 安装 FFmpeg 开发库

### 5.2.1 Linux（Ubuntu/Debian）

```bash
# 安装 FFmpeg 开发库
sudo apt update
sudo apt install -y libavformat-dev libavcodec-dev libavutil-dev \
  libswscale-dev libswresample-dev libavfilter-dev

# 安装 SDL2 开发库（后续章节使用）
sudo apt install -y libsdl2-dev

# 安装 SDL2_ttf 开发库（第 17 章字幕渲染使用）
sudo apt install -y libsdl2-ttf-dev

# 安装编译工具
sudo apt install -y build-essential cmake pkg-config

# 验证安装
pkg-config --modversion libavformat libavcodec libavutil libswscale libswresample
```

### 5.2.2 macOS

```bash
# 使用 Homebrew 安装
brew install ffmpeg sdl2 sdl2_ttf cmake pkg-config

# 验证
pkg-config --modversion libavformat
```

### 5.2.3 Windows

Windows 上推荐使用 vcpkg 或从 FFmpeg 官网下载预编译的 Shared 库：

```bash
# 方法一：vcpkg
vcpkg install ffmpeg:x64-windows
vcpkg install sdl2:x64-windows
vcpkg install sdl2-ttf:x64-windows

# 方法二：下载预编译库
# 从 https://github.com/BtbN/FFmpeg-Builds/releases 下载
# 解压后配置 include 和 lib 路径
```

### 5.2.4 从源码编译（可选）

如果需要定制编译选项，可以从源码编译：

```bash
git clone https://git.ffmpeg.org/ffmpeg.git
cd ffmpeg
./configure --enable-shared --enable-gpl --enable-libx264 --enable-libx265
make -j$(nproc)
sudo make install
sudo ldconfig
```

## 5.3 配置 CMake 项目

### 5.3.1 项目结构

```
ffmpeg-player-tutorial/
├── CMakeLists.txt          # 顶层 CMake 配置
├── chapter-05-hello-ffmpeg/
│   ├── CMakeLists.txt
│   └── main.cpp
├── chapter-06-media-info/
│   ├── CMakeLists.txt
│   └── main.cpp
└── ... (后续章节)
```

### 5.3.2 顶层 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.16)
project(ffmpeg-player-tutorial LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# 查找 FFmpeg 库
find_package(PkgConfig REQUIRED)
pkg_check_modules(AVFORMAT REQUIRED libavformat)
pkg_check_modules(AVCODEC REQUIRED libavcodec)
pkg_check_modules(AVUTIL REQUIRED libavutil)
pkg_check_modules(SWSCALE REQUIRED libswscale)
pkg_check_modules(SWRESAMPLE REQUIRED libswresample)

# 查找 SDL2（后续章节使用）
pkg_check_modules(SDL2 IMPORTED_TARGET sdl2)

# 添加子目录
add_subdirectory(chapter-05-hello-ffmpeg)
add_subdirectory(chapter-06-media-info)
add_subdirectory(chapter-07-decode-first-frame)
add_subdirectory(chapter-08-video-decode)
add_subdirectory(chapter-09-audio-decode)
add_subdirectory(chapter-10-sdl-video)
add_subdirectory(chapter-11-sdl-audio)
add_subdirectory(chapter-12-queue)
add_subdirectory(chapter-13-multithread)
add_subdirectory(chapter-14-av-sync)
add_subdirectory(chapter-15-controls)
add_subdirectory(chapter-16-final-player)
add_subdirectory(chapter-17-subtitle)
```

### 5.3.3 子目录 CMakeLists.txt（以 chapter-05 为例）

```cmake
add_executable(hello-ffmpeg main.cpp)

target_include_directories(hello-ffmpeg PRIVATE
    ${AVFORMAT_INCLUDE_DIRS}
    ${AVCODEC_INCLUDE_DIRS}
    ${AVUTIL_INCLUDE_DIRS}
)

target_link_libraries(hello-ffmpeg PRIVATE
    ${AVFORMAT_LIBRARIES}
    ${AVCODEC_LIBRARIES}
    ${AVUTIL_LIBRARIES}
)
```

### 5.3.4 编译和运行

```bash
# 创建构建目录
mkdir build && cd build

# 生成构建文件
cmake ..

# 编译
make -j$(nproc)

# 运行
./chapter-05-hello-ffmpeg/hello-ffmpeg
```

## 5.4 FFmpeg 头文件与 C++ 兼容

FFmpeg 是用 C 语言编写的。在 C++ 中使用时，需要用 `extern "C"` 包裹头文件：

```cpp
// 标准做法：用 extern "C" 包裹 FFmpeg 头文件
extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libswscale/swscale.h>
#include <libswresample/swresample.h>
}
```

如果不加 `extern "C"`，C++ 编译器会对函数名进行 name mangling（名称修饰），导致链接时找不到 FFmpeg 的函数。

## 5.5 Demo：第一个 FFmpeg 程序

这个 Demo 演示了最基本的 FFmpeg API 调用：打印版本信息和支持的编解码器列表。

```cpp
// chapter-05-hello-ffmpeg/main.cpp

extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
}

#include <iostream>
#include <iomanip>

int main() {
    // ========== 1. 打印 FFmpeg 版本信息 ==========
    std::cout << "======================================" << std::endl;
    std::cout << "       FFmpeg 版本信息" << std::endl;
    std::cout << "======================================" << std::endl;

    // avutil 版本
    unsigned version = avutil_version();
    std::cout << "libavutil     : " << AV_VERSION_MAJOR(version)
              << "." << AV_VERSION_MINOR(version)
              << "." << AV_VERSION_MICRO(version) << std::endl;

    // avformat 版本
    version = avformat_version();
    std::cout << "libavformat   : " << AV_VERSION_MAJOR(version)
              << "." << AV_VERSION_MINOR(version)
              << "." << AV_VERSION_MICRO(version) << std::endl;

    // avcodec 版本
    version = avcodec_version();
    std::cout << "libavcodec    : " << AV_VERSION_MAJOR(version)
              << "." << AV_VERSION_MINOR(version)
              << "." << AV_VERSION_MICRO(version) << std::endl;

    // FFmpeg 编译配置
    std::cout << "\n编译配置：" << std::endl;
    std::cout << avutil_configuration() << std::endl;

    // ========== 2. 列出支持的视频解码器 ==========
    std::cout << "\n======================================" << std::endl;
    std::cout << "       支持的视频解码器" << std::endl;
    std::cout << "======================================" << std::endl;

    const AVCodec* codec = nullptr;
    void* iter = nullptr;
    int count = 0;

    while ((codec = av_codec_iterate(&iter)) != nullptr) {
        // 只列出视频解码器
        if (av_codec_is_decoder(codec) && codec->type == AVMEDIA_TYPE_VIDEO) {
            std::cout << std::left << std::setw(20) << codec->name
                      << " : " << (codec->long_name ? codec->long_name : "N/A")
                      << std::endl;
            count++;
        }
    }
    std::cout << "\n共 " << count << " 个视频解码器" << std::endl;

    // ========== 3. 列出支持的音频解码器 ==========
    std::cout << "\n======================================" << std::endl;
    std::cout << "       支持的音频解码器" << std::endl;
    std::cout << "======================================" << std::endl;

    iter = nullptr;
    count = 0;

    while ((codec = av_codec_iterate(&iter)) != nullptr) {
        if (av_codec_is_decoder(codec) && codec->type == AVMEDIA_TYPE_AUDIO) {
            std::cout << std::left << std::setw(20) << codec->name
                      << " : " << (codec->long_name ? codec->long_name : "N/A")
                      << std::endl;
            count++;
        }
    }
    std::cout << "\n共 " << count << " 个音频解码器" << std::endl;

    // ========== 4. 列出支持的封装格式（Demuxer） ==========
    std::cout << "\n======================================" << std::endl;
    std::cout << "       支持的封装格式（输入）" << std::endl;
    std::cout << "======================================" << std::endl;

    const AVInputFormat* ifmt = nullptr;
    iter = nullptr;
    count = 0;

    while ((ifmt = av_demuxer_iterate(&iter)) != nullptr) {
        std::cout << std::left << std::setw(15) << ifmt->name
                  << " : " << (ifmt->long_name ? ifmt->long_name : "N/A")
                  << std::endl;
        count++;
    }
    std::cout << "\n共 " << count << " 种输入格式" << std::endl;

    return 0;
}
```

### 运行结果示例

```
======================================
       FFmpeg 版本信息
======================================
libavutil     : 58.2.100
libavformat   : 60.3.100
libavcodec    : 60.3.100

编译配置：
--enable-shared --enable-gpl ...

======================================
       支持的视频解码器
======================================
h264                 : H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
hevc                 : HEVC (High Efficiency Video Coding)
vp8                  : On2 VP8
vp9                  : Google VP9
av1                  : Alliance for Open Media AV1
mpeg4                : MPEG-4 part 2
...

共 XXX 个视频解码器
```

如果你能看到类似输出，说明 FFmpeg 开发环境已经搭建成功了！

## 5.6 代码解析

让我们分析 Demo 中用到的 FFmpeg API：

### `avutil_version()` / `avformat_version()` / `avcodec_version()`

返回各库的版本号，编码为一个 unsigned int，通过宏提取主、次、微版本号。

### `av_codec_iterate()`

```c
const AVCodec *av_codec_iterate(void **opaque);
```

遍历所有注册的编解码器。每次调用返回下一个编解码器，返回 NULL 时遍历结束。`opaque` 是迭代器状态，初始化为 `nullptr`。

### `av_codec_is_decoder()` / `av_codec_is_encoder()`

判断一个 AVCodec 是解码器还是编码器。

### `av_demuxer_iterate()`

遍历所有注册的输入格式（Demuxer）。

> **注意**：在旧版本 FFmpeg（< 4.0）中，需要调用 `av_register_all()` 来注册所有编解码器和格式。新版本已经自动注册，不需要这个调用了。

## 小结

本章我们完成了：

1. **了解 FFmpeg 的 6 大核心库**及其分工
2. **搭建了开发环境**：安装 FFmpeg 开发库、SDL2、CMake
3. **配置了 CMake 项目**：能够编译链接 FFmpeg
4. **编写了第一个 FFmpeg 程序**：打印版本信息和支持的编解码器

下一章，我们将深入学习 FFmpeg 的核心数据结构——它们是编写播放器的基础。
---

> **本教程全套代码**：[https://download.csdn.net/download/qq_29681777/92658569](https://download.csdn.net/download/qq_29681777/92658569)
