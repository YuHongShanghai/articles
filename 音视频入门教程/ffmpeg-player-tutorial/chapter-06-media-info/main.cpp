extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/channel_layout.h>
#include <libavutil/pixdesc.h>
}

#include <iostream>
#include <iomanip>
#include <string>

std::string format_time(int64_t duration, AVRational time_base) {
    if (duration == AV_NOPTS_VALUE) return "N/A";
    double seconds = duration * av_q2d(time_base);
    int hours = static_cast<int>(seconds / 3600);
    int mins = static_cast<int>((seconds - hours * 3600) / 60);
    double secs = seconds - hours * 3600 - mins * 60;
    char buf[64];
    snprintf(buf, sizeof(buf), "%02d:%02d:%06.3f", hours, mins, secs);
    return buf;
}

std::string get_channel_layout_desc(const AVChannelLayout* ch_layout) {
    char buf[128];
    av_channel_layout_describe(ch_layout, buf, sizeof(buf));
    return buf;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <输入文件>" << std::endl;
        return 1;
    }

    const char* input_file = argv[1];

    AVFormatContext* fmt_ctx = nullptr;
    int ret = avformat_open_input(&fmt_ctx, input_file, nullptr, nullptr);
    if (ret < 0) {
        char errbuf[AV_ERROR_MAX_STRING_SIZE];
        av_strerror(ret, errbuf, sizeof(errbuf));
        std::cerr << "无法打开文件: " << errbuf << std::endl;
        return 1;
    }

    ret = avformat_find_stream_info(fmt_ctx, nullptr);
    if (ret < 0) {
        std::cerr << "无法获取流信息" << std::endl;
        avformat_close_input(&fmt_ctx);
        return 1;
    }

    // 打印文件级信息
    std::cout << "================================================" << std::endl;
    std::cout << "  文件信息" << std::endl;
    std::cout << "================================================" << std::endl;
    std::cout << "文件名    : " << input_file << std::endl;
    std::cout << "封装格式  : " << fmt_ctx->iformat->name
              << " (" << fmt_ctx->iformat->long_name << ")" << std::endl;

    AVRational global_tb = {1, AV_TIME_BASE};
    std::cout << "时长      : " << format_time(fmt_ctx->duration, global_tb) << std::endl;

    if (fmt_ctx->bit_rate > 0) {
        std::cout << "总码率    : " << fmt_ctx->bit_rate / 1000 << " kbps" << std::endl;
    }
    std::cout << "流数量    : " << fmt_ctx->nb_streams << std::endl;

    // 遍历每个流
    for (unsigned int i = 0; i < fmt_ctx->nb_streams; i++) {
        AVStream* stream = fmt_ctx->streams[i];
        AVCodecParameters* par = stream->codecpar;

        std::cout << std::endl;
        std::cout << "------------------------------------------------" << std::endl;
        std::cout << "  Stream #" << i << ": "
                  << av_get_media_type_string(par->codec_type) << std::endl;
        std::cout << "------------------------------------------------" << std::endl;

        const AVCodec* codec = avcodec_find_decoder(par->codec_id);
        std::cout << "编码格式  : " << avcodec_get_name(par->codec_id);
        if (codec && codec->long_name) {
            std::cout << " (" << codec->long_name << ")";
        }
        std::cout << std::endl;

        if (par->bit_rate > 0) {
            std::cout << "码率      : " << par->bit_rate / 1000 << " kbps" << std::endl;
        }

        std::cout << "时间基    : " << stream->time_base.num
                  << "/" << stream->time_base.den << std::endl;
        std::cout << "时长      : " << format_time(stream->duration, stream->time_base)
                  << std::endl;

        switch (par->codec_type) {
            case AVMEDIA_TYPE_VIDEO: {
                std::cout << "分辨率    : " << par->width << "x" << par->height << std::endl;
                const char* pix_fmt_name = av_get_pix_fmt_name(
                    static_cast<AVPixelFormat>(par->format));
                std::cout << "像素格式  : " << (pix_fmt_name ? pix_fmt_name : "unknown")
                          << std::endl;
                if (stream->avg_frame_rate.den && stream->avg_frame_rate.num) {
                    double fps = av_q2d(stream->avg_frame_rate);
                    std::cout << "帧率      : " << std::fixed << std::setprecision(2)
                              << fps << " fps" << std::endl;
                }
                if (stream->nb_frames > 0) {
                    std::cout << "总帧数    : " << stream->nb_frames << std::endl;
                }
                break;
            }
            case AVMEDIA_TYPE_AUDIO: {
                std::cout << "采样率    : " << par->sample_rate << " Hz" << std::endl;
                std::cout << "声道      : "
                          << get_channel_layout_desc(&par->ch_layout)
                          << " (" << par->ch_layout.nb_channels << " channels)"
                          << std::endl;
                const char* sample_fmt_name = av_get_sample_fmt_name(
                    static_cast<AVSampleFormat>(par->format));
                std::cout << "采样格式  : " << (sample_fmt_name ? sample_fmt_name : "unknown")
                          << std::endl;
                if (par->frame_size > 0) {
                    std::cout << "每帧采样数: " << par->frame_size << std::endl;
                }
                break;
            }
            default:
                break;
        }
    }

    std::cout << std::endl;
    std::cout << "================================================" << std::endl;
    std::cout << "  av_dump_format 输出" << std::endl;
    std::cout << "================================================" << std::endl;
    av_dump_format(fmt_ctx, 0, input_file, 0);

    avformat_close_input(&fmt_ctx);
    return 0;
}
