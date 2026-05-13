extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
}

#include <SDL2/SDL.h>
#include <iostream>
#include <iomanip>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <输入文件>" << std::endl;
        return 1;
    }

    const char* input_file = argv[1];

    // FFmpeg 初始化
    AVFormatContext* fmt_ctx = nullptr;
    if (avformat_open_input(&fmt_ctx, input_file, nullptr, nullptr) < 0) {
        std::cerr << "无法打开文件" << std::endl; return 1;
    }
    avformat_find_stream_info(fmt_ctx, nullptr);

    int video_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    if (video_idx < 0) { std::cerr << "找不到视频流" << std::endl; return 1; }

    AVStream* video_stream = fmt_ctx->streams[video_idx];
    int width = video_stream->codecpar->width;
    int height = video_stream->codecpar->height;

    const AVCodec* codec = avcodec_find_decoder(video_stream->codecpar->codec_id);
    AVCodecContext* codec_ctx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(codec_ctx, video_stream->codecpar);
    avcodec_open2(codec_ctx, codec, nullptr);

    AVPacket* pkt = av_packet_alloc();
    AVFrame* frame = av_frame_alloc();

    // SDL2 初始化
    SDL_Init(SDL_INIT_VIDEO);

    SDL_Window* window = SDL_CreateWindow(
        "FFmpeg + SDL2 视频渲染",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        width, height,
        SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);

    SDL_Renderer* renderer = SDL_CreateRenderer(window, -1,
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);

    SDL_Texture* texture = SDL_CreateTexture(renderer,
        SDL_PIXELFORMAT_IYUV, SDL_TEXTUREACCESS_STREAMING, width, height);

    std::cout << "视频: " << width << "x" << height << std::endl;

    // 简单帧率控制
    double fps = av_q2d(video_stream->avg_frame_rate);
    if (fps <= 0) fps = 25.0;
    Uint32 frame_delay = static_cast<Uint32>(1000.0 / fps);

    bool running = true;
    int frame_count = 0;

    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT ||
                (event.type == SDL_KEYDOWN && event.key.keysym.sym == SDLK_ESCAPE)) {
                running = false;
            }
        }
        if (!running) break;

        Uint32 frame_start = SDL_GetTicks();

        int ret = av_read_frame(fmt_ctx, pkt);
        if (ret < 0) {
            av_seek_frame(fmt_ctx, video_idx, 0, AVSEEK_FLAG_BACKWARD);
            avcodec_flush_buffers(codec_ctx);
            continue;
        }

        if (pkt->stream_index == video_idx) {
            avcodec_send_packet(codec_ctx, pkt);
            while (avcodec_receive_frame(codec_ctx, frame) == 0) {
                SDL_UpdateYUVTexture(texture, nullptr,
                    frame->data[0], frame->linesize[0],
                    frame->data[1], frame->linesize[1],
                    frame->data[2], frame->linesize[2]);

                SDL_RenderClear(renderer);
                SDL_RenderCopy(renderer, texture, nullptr, nullptr);
                SDL_RenderPresent(renderer);

                frame_count++;
                av_frame_unref(frame);

                // 帧率控制
                Uint32 elapsed = SDL_GetTicks() - frame_start;
                if (elapsed < frame_delay) {
                    SDL_Delay(frame_delay - elapsed);
                }
            }
        }
        av_packet_unref(pkt);
    }

    SDL_DestroyTexture(texture);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();

    av_frame_free(&frame);
    av_packet_free(&pkt);
    avcodec_free_context(&codec_ctx);
    avformat_close_input(&fmt_ctx);
    return 0;
}
