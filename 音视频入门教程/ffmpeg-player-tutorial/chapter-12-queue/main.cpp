#include "packet_queue.h"
#include "frame_queue.h"

extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
}

#include <iostream>
#include <thread>
#include <atomic>
#include <chrono>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <输入文件>" << std::endl;
        return 1;
    }

    AVFormatContext* fmt_ctx = nullptr;
    avformat_open_input(&fmt_ctx, argv[1], nullptr, nullptr);
    avformat_find_stream_info(fmt_ctx, nullptr);

    int video_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    int audio_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_AUDIO, -1, -1, nullptr, 0);

    std::cout << "视频流: #" << video_idx << ", 音频流: #" << audio_idx << std::endl;

    PacketQueue video_q, audio_q;
    video_q.set_max_size(64);
    audio_q.set_max_size(64);

    std::atomic<bool> finished(false);
    std::atomic<int> v_count(0), a_count(0);

    std::thread producer([&]() {
        AVPacket* pkt = av_packet_alloc();
        while (av_read_frame(fmt_ctx, pkt) >= 0) {
            if (pkt->stream_index == video_idx) {
                if (!video_q.push(pkt)) break;
                v_count++;
            } else if (pkt->stream_index == audio_idx) {
                if (!audio_q.push(pkt)) break;
                a_count++;
            }
            av_packet_unref(pkt);
        }
        av_packet_free(&pkt);
        finished = true;
        video_q.abort();
        audio_q.abort();
    });

    std::thread v_consumer([&]() {
        AVPacket* pkt = av_packet_alloc();
        int n = 0;
        while (video_q.pop(pkt)) { n++; av_packet_unref(pkt); }
        av_packet_free(&pkt);
        std::cout << "[视频消费] " << n << " 包" << std::endl;
    });

    std::thread a_consumer([&]() {
        AVPacket* pkt = av_packet_alloc();
        int n = 0;
        while (audio_q.pop(pkt)) { n++; av_packet_unref(pkt); }
        av_packet_free(&pkt);
        std::cout << "[音频消费] " << n << " 包" << std::endl;
    });

    std::thread monitor([&]() {
        while (!finished) {
            std::cout << "  VQ:" << video_q.size() << " AQ:" << audio_q.size()
                      << " V:" << v_count << " A:" << a_count << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    });

    producer.join();
    v_consumer.join();
    a_consumer.join();
    monitor.join();

    std::cout << "总计: V=" << v_count << " A=" << a_count << std::endl;
    avformat_close_input(&fmt_ctx);
    return 0;
}
