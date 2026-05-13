// 带字幕的视频播放器 - 第 17 章
// 在第 16 章播放器基础上增加外挂 SRT 字幕渲染
// 需要安装 SDL2_ttf: sudo apt install libsdl2-ttf-dev

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
#include <SDL2/SDL_ttf.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <thread>
#include <atomic>
#include <mutex>
#include <algorithm>
#include <cstring>
#include <cmath>

// ============ 工具函数 ============

// 去除 file:// URI 前缀，转为本地路径
std::string strip_file_uri(const std::string& path) {
    if (path.substr(0, 7) == "file://") return path.substr(7);
    return path;
}

// ============ SRT 字幕解析 ============

struct SubEntry {
    double start, end;
    std::string text;
};

double parse_srt_time(const std::string& s) {
    int h, m, sec, ms;
    sscanf(s.c_str(), "%d:%d:%d,%d", &h, &m, &sec, &ms);
    return h * 3600.0 + m * 60.0 + sec + ms / 1000.0;
}

std::vector<SubEntry> load_srt(const std::string& path) {
    std::vector<SubEntry> subs;
    std::ifstream file(path);
    if (!file.is_open()) {
        std::cerr << "无法打开字幕文件: " << path << std::endl;
        return subs;
    }

    std::string line;
    while (std::getline(file, line)) {
        while (!line.empty() && (line.back() == '\r' || line.back() == '\n'))
            line.pop_back();
        if (line.empty()) continue;

        bool all_digit = !line.empty() && std::all_of(line.begin(), line.end(), ::isdigit);
        if (all_digit) continue;

        if (line.find("-->") != std::string::npos) {
            SubEntry entry;
            auto arrow = line.find("-->");
            entry.start = parse_srt_time(line.substr(0, arrow));
            std::string after = line.substr(arrow + 4);
            auto space = after.find(' ');
            if (space != std::string::npos) after = after.substr(0, space);
            entry.end = parse_srt_time(after);

            std::string text;
            while (std::getline(file, line)) {
                while (!line.empty() && (line.back() == '\r' || line.back() == '\n'))
                    line.pop_back();
                if (line.empty()) break;
                if (!text.empty()) text += " ";
                text += line;
            }
            entry.text = text;
            if (!entry.text.empty())
                subs.push_back(entry);
        }
    }

    std::cout << "加载了 " << subs.size() << " 条字幕" << std::endl;
    return subs;
}

// ============ 音频时钟 ============

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
    void refresh() {
        std::lock_guard<std::mutex> lock(m_);
        t_ = av_gettime_relative() / 1e6;
    }
private:
    double pts_ = 0, t_ = 0;
    mutable std::mutex m_;
};

// ============ 播放器上下文 ============

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

// ============ 画面/进度条/字幕 渲染 ============

SDL_Rect calc_rect(int ww, int wh, int vw, int vh) {
    float va = (float)vw / vh, wa = (float)ww / wh;
    SDL_Rect r;
    if (va > wa) { r.w = ww; r.h = (int)(ww / va); }
    else { r.h = wh; r.w = (int)(wh * va); }
    r.x = (ww - r.w) / 2; r.y = (wh - r.h) / 2;
    return r;
}

void draw_bar(SDL_Renderer* ren, int ww, int wh, double cur, double total) {
    if (total <= 0) return;
    double p = std::max(0.0, std::min(1.0, cur / total));
    int bw = ww - 40, bh = 4, by = wh - 14;
    SDL_SetRenderDrawBlendMode(ren, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(ren, 80, 80, 80, 160);
    SDL_Rect bg = {20, by, bw, bh};
    SDL_RenderFillRect(ren, &bg);
    SDL_SetRenderDrawColor(ren, 255, 255, 255, 200);
    SDL_Rect fg = {20, by, (int)(bw * p), bh};
    SDL_RenderFillRect(ren, &fg);
    SDL_SetRenderDrawColor(ren, 255, 255, 255, 255);
    int ds = 10;
    SDL_Rect dot = {20 + (int)(bw * p) - ds / 2, by - 3, ds, ds};
    SDL_RenderFillRect(ren, &dot);
}

void render_subtitle(SDL_Renderer* ren, TTF_Font* font,
                     const std::string& text, int ww, int wh) {
    if (text.empty() || !font) return;

    // 阴影
    SDL_Color black = {0, 0, 0, 255};
    SDL_Surface* shadow = TTF_RenderUTF8_Blended(font, text.c_str(), black);
    if (shadow) {
        SDL_Texture* stex = SDL_CreateTextureFromSurface(ren, shadow);
        SDL_SetTextureAlphaMod(stex, 160);
        SDL_Rect sr = {(ww - shadow->w) / 2 + 2, wh - shadow->h - 48, shadow->w, shadow->h};
        SDL_RenderCopy(ren, stex, nullptr, &sr);
        SDL_DestroyTexture(stex);
        SDL_FreeSurface(shadow);
    }

    // 正文
    SDL_Color white = {255, 255, 255, 255};
    SDL_Surface* surf = TTF_RenderUTF8_Blended(font, text.c_str(), white);
    if (surf) {
        SDL_Texture* ttex = SDL_CreateTextureFromSurface(ren, surf);
        SDL_Rect dr = {(ww - surf->w) / 2, wh - surf->h - 50, surf->w, surf->h};
        SDL_RenderCopy(ren, ttex, nullptr, &dr);
        SDL_DestroyTexture(ttex);
        SDL_FreeSurface(surf);
    }
}

// ============ 音频回调 ============

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

// ============ 解封装/解码线程 ============

void demux_fn(Ctx* c) {
    AVPacket* p = av_packet_alloc();
    while (!c->quit) {
        if (c->seek_req) {
            avformat_seek_file(c->fmt, -1, INT64_MIN, c->seek_pos, INT64_MAX, 0);
            c->vpq.flush(); c->apq.flush();
            c->vfq.flush(); c->afq.flush();
            c->aclk.update(c->seek_pos / (double)AV_TIME_BASE);
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

// ============ 主函数 ============

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <视频文件> [字幕文件.srt]" << std::endl;
        return 1;
    }

    const char* video_file = argv[1];
    std::string srt_file = argc >= 3 ? strip_file_uri(argv[2]) : "";

    // 加载字幕
    std::vector<SubEntry> subs;
    if (!srt_file.empty()) {
        subs = load_srt(srt_file);
    }

    // ---- FFmpeg 初始化 ----
    Ctx c;
    avformat_open_input(&c.fmt, video_file, nullptr, nullptr);
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

    int vw = c.vc ? c.vc->width : 640, vh = c.vc ? c.vc->height : 480;
    double total_dur = c.fmt->duration > 0 ? c.fmt->duration / (double)AV_TIME_BASE : 0;

    // ---- SDL 初始化 ----
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO);
    TTF_Init();

    c.win = SDL_CreateWindow("FFmpeg Player + 字幕",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, vw, vh,
        SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    c.ren = SDL_CreateRenderer(c.win, -1, SDL_RENDERER_ACCELERATED);
    c.tex = SDL_CreateTexture(c.ren, SDL_PIXELFORMAT_IYUV, SDL_TEXTUREACCESS_STREAMING, vw, vh);

    SDL_AudioSpec want{}, got{};
    want.freq = 44100; want.format = AUDIO_S16SYS; want.channels = 2;
    want.samples = 1024; want.callback = audio_cb; want.userdata = &c;
    c.adev = SDL_OpenAudioDevice(nullptr, 0, &want, &got, 0);
    SDL_PauseAudioDevice(c.adev, 0);

    // ---- 加载字体 ----
    const char* font_paths[] = {
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    };

    TTF_Font* font = nullptr;
    for (const auto* path : font_paths) {
        font = TTF_OpenFont(path, 28);
        if (font) {
            std::cout << "使用字体: " << path << std::endl;
            break;
        }
    }
    if (!font) {
        std::cerr << "无法加载字体，字幕功能将不可用" << std::endl;
    }

    std::cout << "空格=暂停  ←→=±10s  ↑↓=音量  鼠标点击=跳转  ESC=退出" << std::endl;
    if (subs.empty()) {
        std::cout << "未加载字幕（可通过第二个参数指定 .srt 文件）" << std::endl;
    }

    // ---- 启动线程 ----
    std::thread td(demux_fn, &c), tv(vdec_fn, &c), ta(adec_fn, &c);

    AVFrame* f = av_frame_alloc();
    double fps = c.vs ? av_q2d(c.vs->avg_frame_rate) : 25;
    if (fps <= 0) fps = 25;
    double dur = 1.0 / fps;

    // ---- 主循环 ----
    while (!c.quit) {
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT) c.quit = true;
            else if (ev.type == SDL_KEYDOWN) {
                switch (ev.key.keysym.sym) {
                    case SDLK_ESCAPE: case SDLK_q: c.quit = true; break;
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
                    case SDLK_UP: c.volume = std::min((int)c.volume + 8, 128); break;
                    case SDLK_DOWN: c.volume = std::max((int)c.volume - 8, 0); break;
                }
            } else if (ev.type == SDL_MOUSEBUTTONDOWN && ev.button.button == SDL_BUTTON_LEFT) {
                int ww, wh; SDL_GetWindowSize(c.win, &ww, &wh);
                if (ev.button.y >= wh - 24 && total_dur > 0) {
                    double ratio = std::max(0.0, std::min(1.0,
                        (double)(ev.button.x - 20) / (ww - 40)));
                    c.seek_pos = (int64_t)(ratio * total_dur * AV_TIME_BASE);
                    c.seek_req = true;
                }
            }
        }
        if (c.quit) break;
        if (c.paused) { SDL_Delay(10); continue; }

        if (!c.vfq.pop(f)) break;
        double vpts = f->pts * av_q2d(c.vs->time_base);
        double aclk_val = c.aclk.get();
        double diff = vpts - aclk_val;
        if (diff < -0.1 && c.vfq.size() > 0) { av_frame_unref(f); continue; }
        double delay = dur;
        if (diff > 0.04) delay = dur + diff;
        else if (diff < -0.04) delay = std::max(0.001, dur + diff);
        av_usleep((unsigned)(delay * 1e6));

        int ww, wh; SDL_GetWindowSize(c.win, &ww, &wh);
        SDL_Rect rect = calc_rect(ww, wh, vw, vh);

        // 渲染视频帧
        SDL_UpdateYUVTexture(c.tex, nullptr,
            f->data[0], f->linesize[0], f->data[1], f->linesize[1],
            f->data[2], f->linesize[2]);
        SDL_SetRenderDrawColor(c.ren, 0, 0, 0, 255);
        SDL_RenderClear(c.ren);
        SDL_RenderCopy(c.ren, c.tex, nullptr, &rect);

        // 渲染字幕（根据音频时钟查找当前字幕）
        double cur_time = c.aclk.get();
        std::string sub_text;
        for (const auto& s : subs) {
            if (cur_time >= s.start && cur_time <= s.end) {
                sub_text = s.text;
                break;
            }
        }
        render_subtitle(c.ren, font, sub_text, ww, wh);

        // 渲染进度条
        draw_bar(c.ren, ww, wh, cur_time, total_dur);
        SDL_RenderPresent(c.ren);
        av_frame_unref(f);
    }

    // ---- 清理 ----
    c.quit = true;
    c.vpq.abort(); c.apq.abort(); c.vfq.abort(); c.afq.abort();
    td.join(); tv.join(); ta.join();
    av_frame_free(&f);
    SDL_CloseAudioDevice(c.adev);
    if (font) TTF_CloseFont(font);
    TTF_Quit();
    SDL_DestroyTexture(c.tex); SDL_DestroyRenderer(c.ren); SDL_DestroyWindow(c.win);
    SDL_Quit();
    if (c.swr) swr_free(&c.swr);
    if (c.vc) avcodec_free_context(&c.vc);
    if (c.ac) avcodec_free_context(&c.ac);
    avformat_close_input(&c.fmt);
    return 0;
}
