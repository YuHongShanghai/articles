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
#include <vector>
#include <cstring>
#include <iomanip>

#pragma pack(push, 1)
struct BMPHeader {
    uint16_t type = 0x4D42;
    uint32_t size;
    uint16_t reserved1 = 0;
    uint16_t reserved2 = 0;
    uint32_t offset = 54;
    uint32_t header_size = 40;
    int32_t  width;
    int32_t  height;
    uint16_t planes = 1;
    uint16_t bpp = 24;
    uint32_t compression = 0;
    uint32_t image_size;
    int32_t  x_ppm = 0;
    int32_t  y_ppm = 0;
    uint32_t colors_used = 0;
    uint32_t colors_important = 0;
};
#pragma pack(pop)

void save_frame_as_bmp(AVFrame* frame, int width, int height, const std::string& filename) {
    int row_size = ((width * 3 + 3) / 4) * 4;
    int image_size = row_size * height;

    BMPHeader header;
    header.size = 54 + image_size;
    header.width = width;
    header.height = -height;
    header.image_size = image_size;

    std::ofstream file(filename, std::ios::binary);
    if (!file.is_open()) return;

    file.write(reinterpret_cast<char*>(&header), sizeof(header));

    std::vector<uint8_t> row_buf(row_size, 0);
    for (int y = 0; y < height; y++) {
        uint8_t* src = frame->data[0] + y * frame->linesize[0];
        std::memcpy(row_buf.data(), src, width * 3);
        file.write(reinterpret_cast<char*>(row_buf.data()), row_size);
    }
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <输入文件> [最大帧数]" << std::endl;
        return 1;
    }

    const char* input_file = argv[1];
    int max_frames = (argc >= 3) ? std::atoi(argv[2]) : 100;

    AVFormatContext* fmt_ctx = nullptr;
    AVCodecContext* codec_ctx = nullptr;
    SwsContext* sws_ctx = nullptr;
    AVPacket* pkt = nullptr;
    AVFrame* frame = nullptr;
    AVFrame* bgr_frame = nullptr;
    uint8_t* bgr_buffer = nullptr;

    int ret = avformat_open_input(&fmt_ctx, input_file, nullptr, nullptr);
    if (ret < 0) { std::cerr << "无法打开文件" << std::endl; return 1; }
    avformat_find_stream_info(fmt_ctx, nullptr);

    int video_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    if (video_idx < 0) { std::cerr << "找不到视频流" << std::endl; goto cleanup; }

    {
        AVCodecParameters* par = fmt_ctx->streams[video_idx]->codecpar;
        const AVCodec* codec = avcodec_find_decoder(par->codec_id);
        codec_ctx = avcodec_alloc_context3(codec);
        avcodec_parameters_to_context(codec_ctx, par);
        avcodec_open2(codec_ctx, codec, nullptr);

        int width = codec_ctx->width;
        int height = codec_ctx->height;

        std::cout << "视频: " << width << "x" << height
                  << ", 格式: " << av_get_pix_fmt_name(codec_ctx->pix_fmt) << std::endl;

        sws_ctx = sws_getContext(width, height, codec_ctx->pix_fmt,
                                 width, height, AV_PIX_FMT_BGR24,
                                 SWS_BILINEAR, nullptr, nullptr, nullptr);

        bgr_frame = av_frame_alloc();
        int buf_size = av_image_get_buffer_size(AV_PIX_FMT_BGR24, width, height, 1);
        bgr_buffer = static_cast<uint8_t*>(av_malloc(buf_size));
        av_image_fill_arrays(bgr_frame->data, bgr_frame->linesize,
                             bgr_buffer, AV_PIX_FMT_BGR24, width, height, 1);

        pkt = av_packet_alloc();
        frame = av_frame_alloc();
        int frame_count = 0;

        std::cout << "开始解码前 " << max_frames << " 帧..." << std::endl;

        while (av_read_frame(fmt_ctx, pkt) >= 0 && frame_count < max_frames) {
            if (pkt->stream_index == video_idx) {
                avcodec_send_packet(codec_ctx, pkt);
                while (avcodec_receive_frame(codec_ctx, frame) == 0) {
                    sws_scale(sws_ctx, frame->data, frame->linesize,
                              0, height, bgr_frame->data, bgr_frame->linesize);

                    if (frame_count % 10 == 0) {
                        std::string filename = "frame_" + std::to_string(frame_count) + ".bmp";
                        save_frame_as_bmp(bgr_frame, width, height, filename);
                    }

                    frame_count++;
                    if (frame_count >= max_frames) break;

                    if (frame_count % 10 == 0) {
                        double pts_sec = frame->pts *
                            av_q2d(fmt_ctx->streams[video_idx]->time_base);
                        std::cout << "已解码 " << frame_count << " 帧, PTS="
                                  << std::fixed << std::setprecision(3)
                                  << pts_sec << "s" << std::endl;
                    }
                    av_frame_unref(frame);
                }
            }
            av_packet_unref(pkt);
        }

        std::cout << "\n解码完成！共 " << frame_count << " 帧" << std::endl;
    }

cleanup:
    if (bgr_buffer) av_free(bgr_buffer);
    if (bgr_frame) av_frame_free(&bgr_frame);
    if (frame) av_frame_free(&frame);
    if (pkt) av_packet_free(&pkt);
    if (sws_ctx) sws_freeContext(sws_ctx);
    if (codec_ctx) avcodec_free_context(&codec_ctx);
    if (fmt_ctx) avformat_close_input(&fmt_ctx);
    return 0;
}
