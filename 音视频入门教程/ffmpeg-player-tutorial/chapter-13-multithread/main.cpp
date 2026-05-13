#include "../chapter-12-queue/packet_queue.h"
#include "../chapter-12-queue/frame_queue.h"

extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
}

#include <iostream>
#include <thread>
#include <atomic>
#include <chrono>

struct Context {
    std::atomic<bool> abort{false};
    AVFormatContext* fmt_ctx = nullptr;
    AVCodecContext* v_ctx = nullptr;
    AVCodecContext* a_ctx = nullptr;
    int v_idx = -1, a_idx = -1;
    PacketQueue v_pkt_q, a_pkt_q;
    FrameQueue v_frm_q, a_frm_q;
    std::atomic<int> v_decoded{0}, a_decoded{0};
};

void demux(Context* c) {
    AVPacket* p = av_packet_alloc();
    while (!c->abort) {
        if (c->v_pkt_q.size() > 64 || c->a_pkt_q.size() > 64) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
            continue;
        }
        if (av_read_frame(c->fmt_ctx, p) < 0) break;
        if (p->stream_index == c->v_idx) c->v_pkt_q.push(p);
        else if (p->stream_index == c->a_idx) c->a_pkt_q.push(p);
        av_packet_unref(p);
    }
    av_packet_free(&p);
    c->v_pkt_q.abort();
    c->a_pkt_q.abort();
}

void vdec(Context* c) {
    AVPacket* p = av_packet_alloc();
    AVFrame* f = av_frame_alloc();
    while (!c->abort) {
        if (!c->v_pkt_q.pop(p)) break;
        avcodec_send_packet(c->v_ctx, p);
        av_packet_unref(p);
        int r = 0;
        while (r >= 0) {
            r = avcodec_receive_frame(c->v_ctx, f);
            if (r < 0) break;
            f->pts = f->best_effort_timestamp;
            if (!c->v_frm_q.push(f)) { av_frame_unref(f); break; }
            c->v_decoded++;
        }
    }
    av_frame_free(&f);
    av_packet_free(&p);
    c->v_frm_q.abort();
}

void adec(Context* c) {
    AVPacket* p = av_packet_alloc();
    AVFrame* f = av_frame_alloc();
    while (!c->abort) {
        if (!c->a_pkt_q.pop(p)) break;
        avcodec_send_packet(c->a_ctx, p);
        av_packet_unref(p);
        int r = 0;
        while (r >= 0) {
            r = avcodec_receive_frame(c->a_ctx, f);
            if (r < 0) break;
            f->pts = f->best_effort_timestamp;
            if (!c->a_frm_q.push(f)) { av_frame_unref(f); break; }
            c->a_decoded++;
        }
    }
    av_frame_free(&f);
    av_packet_free(&p);
    c->a_frm_q.abort();
}

int main(int argc, char* argv[]) {
    if (argc < 2) { std::cerr << "用法: " << argv[0] << " <文件>" << std::endl; return 1; }

    Context c;
    avformat_open_input(&c.fmt_ctx, argv[1], nullptr, nullptr);
    avformat_find_stream_info(c.fmt_ctx, nullptr);
    av_dump_format(c.fmt_ctx, 0, argv[1], 0);

    c.v_idx = av_find_best_stream(c.fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    c.a_idx = av_find_best_stream(c.fmt_ctx, AVMEDIA_TYPE_AUDIO, -1, -1, nullptr, 0);

    if (c.v_idx >= 0) {
        auto* par = c.fmt_ctx->streams[c.v_idx]->codecpar;
        auto* cod = avcodec_find_decoder(par->codec_id);
        c.v_ctx = avcodec_alloc_context3(cod);
        avcodec_parameters_to_context(c.v_ctx, par);
        c.v_ctx->thread_count = 2;
        avcodec_open2(c.v_ctx, cod, nullptr);
    }
    if (c.a_idx >= 0) {
        auto* par = c.fmt_ctx->streams[c.a_idx]->codecpar;
        auto* cod = avcodec_find_decoder(par->codec_id);
        c.a_ctx = avcodec_alloc_context3(cod);
        avcodec_parameters_to_context(c.a_ctx, par);
        avcodec_open2(c.a_ctx, cod, nullptr);
    }

    if (c.v_idx < 0 && c.a_idx < 0) {
        std::cerr << "找不到音频流或视频流" << std::endl;
        avformat_close_input(&c.fmt_ctx);
        return 1;
    }

    auto t0 = std::chrono::steady_clock::now();
    std::thread td(demux, &c);
    std::thread tv, ta;

    // 只为存在的流启动解码线程，不存在的流直接 abort 对应队列
    if (c.v_idx >= 0) {
        tv = std::thread(vdec, &c);
    } else {
        c.v_pkt_q.abort();
        c.v_frm_q.abort();
    }
    if (c.a_idx >= 0) {
        ta = std::thread(adec, &c);
    } else {
        c.a_pkt_q.abort();
        c.a_frm_q.abort();
    }

    AVFrame* f = av_frame_alloc();
    int vc = 0, ac = 0;
    bool v_done = (c.v_idx < 0);
    bool a_done = (c.a_idx < 0);
    while (!v_done || !a_done) {
        if (!v_done) {
            if (c.v_frm_q.pop(f)) { vc++; av_frame_unref(f); }
            else v_done = true;
        }
        if (!a_done) {
            if (c.a_frm_q.pop(f)) { ac++; av_frame_unref(f); }
            else a_done = true;
        }
    }

    td.join();
    if (tv.joinable()) tv.join();
    if (ta.joinable()) ta.join();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - t0).count();

    std::cout << "\n=== 结果 ===" << std::endl;
    std::cout << "视频帧: " << vc << ", 音频帧: " << ac << std::endl;
    std::cout << "耗时: " << ms << " ms" << std::endl;

    av_frame_free(&f);
    if (c.v_ctx) avcodec_free_context(&c.v_ctx);
    if (c.a_ctx) avcodec_free_context(&c.a_ctx);
    avformat_close_input(&c.fmt_ctx);
    return 0;
}
