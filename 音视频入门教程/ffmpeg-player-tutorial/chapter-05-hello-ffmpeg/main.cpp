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

    unsigned version = avutil_version();
    std::cout << "libavutil     : " << AV_VERSION_MAJOR(version)
              << "." << AV_VERSION_MINOR(version)
              << "." << AV_VERSION_MICRO(version) << std::endl;

    version = avformat_version();
    std::cout << "libavformat   : " << AV_VERSION_MAJOR(version)
              << "." << AV_VERSION_MINOR(version)
              << "." << AV_VERSION_MICRO(version) << std::endl;

    version = avcodec_version();
    std::cout << "libavcodec    : " << AV_VERSION_MAJOR(version)
              << "." << AV_VERSION_MINOR(version)
              << "." << AV_VERSION_MICRO(version) << std::endl;

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

    // ========== 4. 列出支持的封装格式 ==========
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
