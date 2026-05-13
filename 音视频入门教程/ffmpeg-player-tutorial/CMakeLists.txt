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

# 添加 FFmpeg 库搜索路径（从源码编译安装到 /usr/local 等非默认路径时需要）
link_directories(
    ${AVFORMAT_LIBRARY_DIRS}
    ${AVCODEC_LIBRARY_DIRS}
    ${AVUTIL_LIBRARY_DIRS}
    ${SWSCALE_LIBRARY_DIRS}
    ${SWRESAMPLE_LIBRARY_DIRS}
)

# 查找 SDL2
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
