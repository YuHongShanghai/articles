// 完整的音视频同步播放器 Demo
// 参见第 14 章文章中的完整代码
// 此文件与文章中的代码一致

#include "../chapter-12-queue/packet_queue.h"
#include "../chapter-12-queue/frame_queue.h"

extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/time.h>
#include <libavutil/channel_layout.h>
#include <libswresample/swresample.h>
}

#include <SDL2/SDL.h>
#include <iostream>
#include <thread>
#include <atomic>
#include <mutex>
#include <cstring>
#include <vector>
#include <algorithm>
#include <cstdio>

class AudioClock {
public:
    void update(double pts) {
        std::lock_guard<std::mutex> lock(m_);
        pts_ = pts;
        t_ = av_gettime_relative() / 1000000.0;
    }
    double get() const {
        std::lock_guard<std::mutex> lock(m_);
        return pts_ + (av_gettime_relative() / 1000000.0 - t_);
    }
private:
    double pts_ = 0, t_ = 0;
    mutable std::mutex m_;
};

struct Ctx {
    std::atomic<bool> quit{false};
    AVFormatContext* fmt = nullptr;
    AVCodecContext* vc = nullptr, *ac = nullptr;
    SwrContext* swr = nullptr;
    int vi = -1, ai = -1;
    AVStream* vs = nullptr, *as = nullptr;
    PacketQueue vpq, apq;
    FrameQueue vfq, afq;
    AudioClock aclk;
    std::vector<uint8_t> abuf;
    int abuf_sz = 0, abuf_idx = 0;
    SDL_Window* win = nullptr;
    SDL_Renderer* ren = nullptr;
    SDL_Texture* tex = nullptr;
    SDL_AudioDeviceID adev = 0;
};

void audio_cb(void* ud, Uint8* stream, int len) {
    auto* c = (Ctx*)ud;
    memset(stream, 0, len);
    int w = 0;
    while (w < len && !c->quit) {
        if (c->abuf_idx >= c->abuf_sz) {
            AVFrame* f = av_frame_alloc();
            if (!c->afq.pop(f)) { av_frame_free(&f); break; }
            if (f->pts != AV_NOPTS_VALUE)
                c->aclk.update(f->pts * av_q2d(c->as->time_base));
            int os = av_rescale_rnd(swr_get_delay(c->swr, c->ac->sample_rate) + f->nb_samples,
                44100, c->ac->sample_rate, AV_ROUND_UP);
            c->abuf.resize(os * 4);
            uint8_t* ob = c->abuf.data();
            int cv = swr_convert(c->swr, &ob, os, (const uint8_t**)f->data, f->nb_samples);
            c->abuf_sz = cv * 4; c->abuf_idx = 0;
            av_frame_free(&f);
        }
        int n = std::min(len - w, c->abuf_sz - c->abuf_idx);
        memcpy(stream + w, c->abuf.data() + c->abuf_idx, n);
        w += n; c->abuf_idx += n;
    }
}

void demux_fn(Ctx* c) {
    AVPacket* p = av_packet_alloc();
    while (!c->quit) {
        if (c->vpq.size() > 64 || c->apq.size() > 64) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5)); continue;
        }
        if (av_read_frame(c->fmt, p) < 0) break;
        if (p->stream_index == c->vi) c->vpq.push(p);
        else if (p->stream_index == c->ai) c->apq.push(p);
        av_packet_unref(p);
    }
    av_packet_free(&p);
    c->vpq.abort(); c->apq.abort();
}

void vdec_fn(Ctx* c) {
    AVPacket* p = av_packet_alloc(); AVFrame* f = av_frame_alloc();
    while (!c->quit) {
        if (!c->vpq.pop(p)) break;
        avcodec_send_packet(c->vc, p); av_packet_unref(p);
        int r = 0;
        while (r >= 0) {
            r = avcodec_receive_frame(c->vc, f);
            if (r < 0) break;
            f->pts = f->best_effort_timestamp;
            if (!c->vfq.push(f)) { av_frame_unref(f); break; }
        }
    }
    av_frame_free(&f); av_packet_free(&p); c->vfq.abort();
}

void adec_fn(Ctx* c) {
    AVPacket* p = av_packet_alloc(); AVFrame* f = av_frame_alloc();
    while (!c->quit) {
        if (!c->apq.pop(p)) break;
        avcodec_send_packet(c->ac, p); av_packet_unref(p);
        int r = 0;
        while (r >= 0) {
            r = avcodec_receive_frame(c->ac, f);
            if (r < 0) break;
            f->pts = f->best_effort_timestamp;
            if (!c->afq.push(f)) { av_frame_unref(f); break; }
        }
    }
    av_frame_free(&f); av_packet_free(&p); c->afq.abort();
}

int main(int argc, char* argv[]) {
    if (argc < 2) { std::cerr << "用法: " << argv[0] << " <文件>" << std::endl; return 1; }

    Ctx c;
    avformat_open_input(&c.fmt, argv[1], nullptr, nullptr);
    avformat_find_stream_info(c.fmt, nullptr);

    c.vi = av_find_best_stream(c.fmt, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    c.ai = av_find_best_stream(c.fmt, AVMEDIA_TYPE_AUDIO, -1, -1, nullptr, 0);

    if (c.vi >= 0) {
        c.vs = c.fmt->streams[c.vi];
        auto* cod = avcodec_find_decoder(c.vs->codecpar->codec_id);
        c.vc = avcodec_alloc_context3(cod);
        avcodec_parameters_to_context(c.vc, c.vs->codecpar);
        avcodec_open2(c.vc, cod, nullptr);
    }
    if (c.ai >= 0) {
        c.as = c.fmt->streams[c.ai];
        auto* cod = avcodec_find_decoder(c.as->codecpar->codec_id);
        c.ac = avcodec_alloc_context3(cod);
        avcodec_parameters_to_context(c.ac, c.as->codecpar);
        avcodec_open2(c.ac, cod, nullptr);
        AVChannelLayout ol = AV_CHANNEL_LAYOUT_STEREO, il;
        av_channel_layout_copy(&il, &c.ac->ch_layout);
        swr_alloc_set_opts2(&c.swr, &ol, AV_SAMPLE_FMT_S16, 44100,
            &il, c.ac->sample_fmt, c.ac->sample_rate, 0, nullptr);
        av_channel_layout_uninit(&il);
        swr_init(c.swr);
    }

    int w = c.vc ? c.vc->width : 640, h = c.vc ? c.vc->height : 480;
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO);
    c.win = SDL_CreateWindow("AV Sync", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        w, h, SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    c.ren = SDL_CreateRenderer(c.win, -1, SDL_RENDERER_ACCELERATED);
    c.tex = SDL_CreateTexture(c.ren, SDL_PIXELFORMAT_IYUV, SDL_TEXTUREACCESS_STREAMING, w, h);

    SDL_AudioSpec want{}, got{};
    want.freq = 44100; want.format = AUDIO_S16SYS; want.channels = 2;
    want.samples = 1024; want.callback = audio_cb; want.userdata = &c;
    c.adev = SDL_OpenAudioDevice(nullptr, 0, &want, &got, 0);
    SDL_PauseAudioDevice(c.adev, 0);

    std::thread td(demux_fn, &c), tv(vdec_fn, &c), ta(adec_fn, &c);

    AVFrame* f = av_frame_alloc();
    double fps = c.vs ? av_q2d(c.vs->avg_frame_rate) : 25;
    if (fps <= 0) fps = 25;
    double dur = 1.0 / fps;
    int frame_num = 0;
    int drop_count = 0;
    int log_interval = std::max(1, (int)(fps + 0.5));  // 大约每秒打印一次

    std::printf("\n[SYNC] %-6s  %-10s %-10s %-10s %-8s %s\n",
               "帧号", "视频PTS", "音频时钟", "差值", "动作", "延迟");
    std::printf("[SYNC] ------ ---------- ---------- ---------- -------- --------\n");

    while (!c.quit) {
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT ||
                (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_ESCAPE))
                c.quit = true;
        }
        if (c.quit) break;
        if (!c.vfq.pop(f)) break;

        double vpts = f->pts * av_q2d(c.vs->time_base);
        double aclk = c.aclk.get();
        double diff = vpts - aclk;

        // 视频落后音频太多，丢帧追赶
        if (diff < -0.1 && c.vfq.size() > 0) {
            drop_count++;
            std::printf("[SYNC] #%-5d  %7.3fs   %7.3fs   %+7.3fs   \033[31mDROP\033[0m     (队列剩余: %d, 累计丢帧: %d)\n",
                        frame_num, vpts, aclk, diff, c.vfq.size(), drop_count);
            frame_num++;
            av_frame_unref(f);
            continue;
        }

        // 计算同步延迟
        double delay = dur;
        const char* action;
        const char* color;
        if (diff > 0.04) {
            delay = dur + diff;
            action = "WAIT";    // 视频超前，多等一会儿
            color = "\033[33m"; // 黄色
        } else if (diff < -0.04) {
            delay = std::max(0.001, dur + diff);
            action = "HURRY";   // 视频略落后，加速显示
            color = "\033[36m"; // 青色
        } else {
            action = "OK";      // 同步良好
            color = "\033[32m"; // 绿色
        }

        // 每秒打印一次，或出现非正常同步时打印
        bool should_log = (frame_num % log_interval == 0) ||
                          (diff > 0.04 || diff < -0.04);
        if (should_log) {
            std::printf("[SYNC] #%-5d  %7.3fs   %7.3fs   %+7.3fs   %s%-5s\033[0m  %.1fms\n",
                        frame_num, vpts, aclk, diff, color, action, delay * 1000);
        }

        av_usleep((unsigned)(delay * 1000000));

        SDL_UpdateYUVTexture(c.tex, nullptr,
            f->data[0], f->linesize[0], f->data[1], f->linesize[1],
            f->data[2], f->linesize[2]);
        SDL_RenderClear(c.ren);
        SDL_RenderCopy(c.ren, c.tex, nullptr, nullptr);
        SDL_RenderPresent(c.ren);
        av_frame_unref(f);
        frame_num++;
    }

    std::printf("\n[SYNC] 播放结束，共 %d 帧，丢弃 %d 帧\n", frame_num, drop_count);

    c.quit = true;
    c.vpq.abort(); c.apq.abort(); c.vfq.abort(); c.afq.abort();
    td.join(); tv.join(); ta.join();

    av_frame_free(&f);
    SDL_CloseAudioDevice(c.adev);
    SDL_DestroyTexture(c.tex); SDL_DestroyRenderer(c.ren); SDL_DestroyWindow(c.win);
    SDL_Quit();
    if (c.swr) swr_free(&c.swr);
    if (c.vc) avcodec_free_context(&c.vc);
    if (c.ac) avcodec_free_context(&c.ac);
    avformat_close_input(&c.fmt);
    return 0;
}
