// 带播放控制的播放器 - 在第 14 章基础上添加暂停、Seek、音量控制
// 详见第 15 章文章说明

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

class AudioClock {
public:
    void update(double pts) {
        std::lock_guard<std::mutex> lock(m_);
        pts_ = pts; t_ = av_gettime_relative() / 1e6;
    }
    double get() const {
        std::lock_guard<std::mutex> lock(m_);
        return pts_ + (av_gettime_relative() / 1e6 - t_);
    }
    // 刷新墙上时钟参考点（暂停恢复时调用，消除暂停期间的时间漂移）
    void refresh() {
        std::lock_guard<std::mutex> lock(m_);
        t_ = av_gettime_relative() / 1e6;
    }
private:
    double pts_ = 0, t_ = 0;
    mutable std::mutex m_;
};

struct Ctx {
    std::atomic<bool> quit{false}, paused{false};
    std::atomic<bool> seek_req{false};
    std::atomic<int64_t> seek_pos{0};
    std::atomic<int> volume{SDL_MIX_MAXVOLUME};
    std::atomic<bool> flush_video{false}, flush_audio{false};

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
    std::vector<uint8_t> tmp(len);
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
        memcpy(tmp.data() + w, c->abuf.data() + c->abuf_idx, n);
        w += n; c->abuf_idx += n;
    }
    if (w > 0) SDL_MixAudioFormat(stream, tmp.data(), AUDIO_S16SYS, w, c->volume);
}

void demux_fn(Ctx* c) {
    AVPacket* p = av_packet_alloc();
    while (!c->quit) {
        if (c->seek_req) {
            int64_t target = c->seek_pos;
            avformat_seek_file(c->fmt, -1, INT64_MIN, target, INT64_MAX, 0);
            c->vpq.flush(); c->apq.flush();
            c->vfq.flush(); c->afq.flush();
            // 将音频时钟设置到 seek 目标位置，避免 seek 后视频同步错乱
            c->aclk.update(target / (double)AV_TIME_BASE);
            // 通知解码线程在各自线程中 flush 编解码器，避免跨线程访问 AVCodecContext
            c->flush_video = true;
            c->flush_audio = true;
            c->seek_req = false;
        }
        if (c->paused) { std::this_thread::sleep_for(std::chrono::milliseconds(10)); continue; }
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
        // seek 后在本线程安全地 flush 编解码器
        if (c->flush_video) {
            avcodec_flush_buffers(c->vc);
            c->flush_video = false;
            av_packet_unref(p);
            continue;
        }
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
        // seek 后在本线程安全地 flush 编解码器
        if (c->flush_audio) {
            avcodec_flush_buffers(c->ac);
            c->flush_audio = false;
            av_packet_unref(p);
            continue;
        }
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
    c.win = SDL_CreateWindow("Player (Space=暂停 ←→=Seek ↑↓=音量)",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, w, h,
        SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    c.ren = SDL_CreateRenderer(c.win, -1, SDL_RENDERER_ACCELERATED);
    c.tex = SDL_CreateTexture(c.ren, SDL_PIXELFORMAT_IYUV, SDL_TEXTUREACCESS_STREAMING, w, h);

    SDL_AudioSpec want{}, got{};
    want.freq = 44100; want.format = AUDIO_S16SYS; want.channels = 2;
    want.samples = 1024; want.callback = audio_cb; want.userdata = &c;
    c.adev = SDL_OpenAudioDevice(nullptr, 0, &want, &got, 0);
    SDL_PauseAudioDevice(c.adev, 0);

    std::cout << "空格=暂停/恢复  ←→=快退/快进10s  ↑↓=音量  ESC=退出" << std::endl;

    std::thread td(demux_fn, &c), tv(vdec_fn, &c), ta(adec_fn, &c);

    AVFrame* f = av_frame_alloc();
    double fps = c.vs ? av_q2d(c.vs->avg_frame_rate) : 25;
    if (fps <= 0) fps = 25;
    double dur = 1.0 / fps;

    while (!c.quit) {
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT) c.quit = true;
            else if (ev.type == SDL_KEYDOWN) {
                switch (ev.key.keysym.sym) {
                    case SDLK_ESCAPE: c.quit = true; break;
                    case SDLK_SPACE:
                        c.paused = !c.paused;
                        SDL_PauseAudioDevice(c.adev, c.paused ? 1 : 0);
                        if (!c.paused) c.aclk.refresh();
                        break;
                    case SDLK_LEFT:
                        c.seek_pos = (int64_t)((c.aclk.get() - 10) * AV_TIME_BASE);
                        c.seek_req = true; break;
                    case SDLK_RIGHT:
                        c.seek_pos = (int64_t)((c.aclk.get() + 10) * AV_TIME_BASE);
                        c.seek_req = true; break;
                    case SDLK_UP:
                        c.volume = std::min((int)c.volume + 8, (int)SDL_MIX_MAXVOLUME); break;
                    case SDLK_DOWN:
                        c.volume = std::max((int)c.volume - 8, 0); break;
                }
            }
        }
        if (c.quit) break;
        if (c.paused) { SDL_Delay(10); continue; }

        if (!c.vfq.pop(f)) break;
        double vpts = f->pts * av_q2d(c.vs->time_base);
        double diff = vpts - c.aclk.get();
        if (diff < -0.1 && c.vfq.size() > 0) { av_frame_unref(f); continue; }
        double delay = dur;
        if (diff > 0.04) delay = dur + diff;
        else if (diff < -0.04) delay = std::max(0.001, dur + diff);
        av_usleep((unsigned)(delay * 1e6));

        SDL_UpdateYUVTexture(c.tex, nullptr,
            f->data[0], f->linesize[0], f->data[1], f->linesize[1],
            f->data[2], f->linesize[2]);
        SDL_RenderClear(c.ren);
        SDL_RenderCopy(c.ren, c.tex, nullptr, nullptr);
        SDL_RenderPresent(c.ren);
        av_frame_unref(f);
    }

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
