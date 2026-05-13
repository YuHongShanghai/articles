extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
}

#include <iostream>
#include <fstream>
#include <string>

void save_frame_as_ppm(AVFrame* frame, int width, int height, const std::string& filename) {
    std::ofstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        std::cerr << "无法创建文件: " << filename << std::endl;
        return;
    }
    file << "P6\n" << width << " " << height << "\n255\n";
    for (int y = 0; y < height; y++) {
        file.write(reinterpret_cast<char*>(frame->data[0] + y * frame->linesize[0]),
                   width * 3);
    }
    std::cout << "已保存: " << filename << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <输入文件>" << std::endl;
        return 1;
    }

    const char* input_file = argv[1];
    int ret = 0;

    AVFormatContext* fmt_ctx = nullptr;
    AVCodecContext* video_codec_ctx = nullptr;
    AVPacket* pkt = nullptr;
    AVFrame* frame = nullptr;
    AVFrame* rgb_frame = nullptr;
    SwsContext* sws_ctx = nullptr;
    uint8_t* rgb_buffer = nullptr;

    // 1. 打开文件
    ret = avformat_open_input(&fmt_ctx, input_file, nullptr, nullptr);
    if (ret < 0) {
        char errbuf[AV_ERROR_MAX_STRING_SIZE];
        av_strerror(ret, errbuf, sizeof(errbuf));
        std::cerr << "无法打开文件: " << errbuf << std::endl;
        goto cleanup;
    }

    ret = avformat_find_stream_info(fmt_ctx, nullptr);
    if (ret < 0) {
        std::cerr << "无法获取流信息" << std::endl;
        goto cleanup;
    }

    av_dump_format(fmt_ctx, 0, input_file, 0);

    {
        // 2. 找到视频流
        int video_stream_idx = av_find_best_stream(
            fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
        if (video_stream_idx < 0) {
            std::cerr << "找不到视频流" << std::endl;
            goto cleanup;
        }

        AVStream* video_stream = fmt_ctx->streams[video_stream_idx];
        AVCodecParameters* codecpar = video_stream->codecpar;

        std::cout << "\n视频流: #" << video_stream_idx
                  << " [" << codecpar->width << "x" << codecpar->height << "]" << std::endl;

        // 3. 初始化解码器
        const AVCodec* codec = avcodec_find_decoder(codecpar->codec_id);
        if (!codec) {
            std::cerr << "找不到解码器" << std::endl;
            goto cleanup;
        }
        std::cout << "使用解码器: " << codec->name << std::endl;

        video_codec_ctx = avcodec_alloc_context3(codec);
        if (!video_codec_ctx) {
            std::cerr << "无法分配解码器上下文" << std::endl;
            goto cleanup;
        }

        ret = avcodec_parameters_to_context(video_codec_ctx, codecpar);
        if (ret < 0) goto cleanup;

        ret = avcodec_open2(video_codec_ctx, codec, nullptr);
        if (ret < 0) goto cleanup;

        // 4. 准备格式转换
        int width = video_codec_ctx->width;
        int height = video_codec_ctx->height;

        sws_ctx = sws_getContext(
            width, height, video_codec_ctx->pix_fmt,
            width, height, AV_PIX_FMT_RGB24,
            SWS_BILINEAR, nullptr, nullptr, nullptr);
        if (!sws_ctx) goto cleanup;

        rgb_frame = av_frame_alloc();
        int rgb_buffer_size = av_image_get_buffer_size(AV_PIX_FMT_RGB24, width, height, 1);
        rgb_buffer = static_cast<uint8_t*>(av_malloc(rgb_buffer_size));
        av_image_fill_arrays(rgb_frame->data, rgb_frame->linesize,
                             rgb_buffer, AV_PIX_FMT_RGB24, width, height, 1);

        // 5. 读取并解码第一帧
        pkt = av_packet_alloc();
        frame = av_frame_alloc();
        bool got_frame = false;

        while (av_read_frame(fmt_ctx, pkt) >= 0 && !got_frame) {
            if (pkt->stream_index == video_stream_idx) {
                ret = avcodec_send_packet(video_codec_ctx, pkt);
                if (ret < 0) {
                    av_packet_unref(pkt);
                    goto cleanup;
                }

                while (ret >= 0) {
                    ret = avcodec_receive_frame(video_codec_ctx, frame);
                    if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) break;
                    if (ret < 0) goto cleanup;

                    std::cout << "\n成功解码第一帧!" << std::endl;
                    std::cout << "  格式: " << av_get_pix_fmt_name(video_codec_ctx->pix_fmt) << std::endl;
                    std::cout << "  PTS: " << frame->pts << std::endl;
                    std::cout << "  类型: " << av_get_picture_type_char(frame->pict_type) << " 帧" << std::endl;

                    sws_scale(sws_ctx, frame->data, frame->linesize,
                              0, height, rgb_frame->data, rgb_frame->linesize);

                    save_frame_as_ppm(rgb_frame, width, height, "first_frame.ppm");
                    got_frame = true;
                    av_frame_unref(frame);
                    break;
                }
            }
            av_packet_unref(pkt);
        }

        if (!got_frame) {
            std::cout << "未能解码任何帧" << std::endl;
        }
    }

cleanup:
    if (rgb_buffer) av_free(rgb_buffer);
    if (rgb_frame) av_frame_free(&rgb_frame);
    if (frame) av_frame_free(&frame);
    if (pkt) av_packet_free(&pkt);
    if (sws_ctx) sws_freeContext(sws_ctx);
    if (video_codec_ctx) avcodec_free_context(&video_codec_ctx);
    if (fmt_ctx) avformat_close_input(&fmt_ctx);

    return (ret < 0 && ret != AVERROR_EOF) ? 1 : 0;
}
