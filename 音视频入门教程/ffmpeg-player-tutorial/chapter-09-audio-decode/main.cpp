extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/channel_layout.h>
#include <libswresample/swresample.h>
}

#include <iostream>
#include <fstream>
#include <iomanip>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <输入文件>" << std::endl;
        return 1;
    }

    const char* input_file = argv[1];
    const int OUT_SAMPLE_RATE = 44100;
    const AVSampleFormat OUT_SAMPLE_FMT = AV_SAMPLE_FMT_S16;
    const AVChannelLayout OUT_CH_LAYOUT = AV_CHANNEL_LAYOUT_STEREO;

    AVFormatContext* fmt_ctx = nullptr;
    AVCodecContext* codec_ctx = nullptr;
    SwrContext* swr_ctx = nullptr;
    AVPacket* pkt = nullptr;
    AVFrame* frame = nullptr;

    int ret = avformat_open_input(&fmt_ctx, input_file, nullptr, nullptr);
    if (ret < 0) { std::cerr << "无法打开文件" << std::endl; return 1; }
    avformat_find_stream_info(fmt_ctx, nullptr);

    int audio_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_AUDIO, -1, -1, nullptr, 0);
    if (audio_idx < 0) {
        std::cerr << "找不到音频流" << std::endl;
        avformat_close_input(&fmt_ctx);
        return 1;
    }

    AVStream* audio_stream = fmt_ctx->streams[audio_idx];
    AVCodecParameters* par = audio_stream->codecpar;

    std::cout << "源音频: " << avcodec_get_name(par->codec_id)
              << ", " << par->sample_rate << " Hz, "
              << par->ch_layout.nb_channels << " ch" << std::endl;

    const AVCodec* codec = avcodec_find_decoder(par->codec_id);
    codec_ctx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(codec_ctx, par);
    avcodec_open2(codec_ctx, codec, nullptr);

    AVChannelLayout out_layout = OUT_CH_LAYOUT;
    AVChannelLayout in_layout;
    av_channel_layout_copy(&in_layout, &codec_ctx->ch_layout);
    ret = swr_alloc_set_opts2(&swr_ctx,
        &out_layout, OUT_SAMPLE_FMT, OUT_SAMPLE_RATE,
        &in_layout, codec_ctx->sample_fmt, codec_ctx->sample_rate,
        0, nullptr);
    av_channel_layout_uninit(&in_layout);

    if (ret < 0 || !swr_ctx || swr_init(swr_ctx) < 0) {
        std::cerr << "无法初始化重采样器" << std::endl;
        goto cleanup;
    }

    std::cout << "目标: s16le, " << OUT_SAMPLE_RATE << " Hz, "
              << OUT_CH_LAYOUT.nb_channels << " ch" << std::endl;

    {
        std::ofstream out_file("output.pcm", std::ios::binary);
        pkt = av_packet_alloc();
        frame = av_frame_alloc();
        int total_samples = 0;
        int frame_count = 0;

        while (av_read_frame(fmt_ctx, pkt) >= 0) {
            if (pkt->stream_index != audio_idx) { av_packet_unref(pkt); continue; }

            avcodec_send_packet(codec_ctx, pkt);
            av_packet_unref(pkt);

            while (avcodec_receive_frame(codec_ctx, frame) == 0) {
                int out_samples = av_rescale_rnd(
                    swr_get_delay(swr_ctx, codec_ctx->sample_rate) + frame->nb_samples,
                    OUT_SAMPLE_RATE, codec_ctx->sample_rate, AV_ROUND_UP);

                uint8_t* out_buf = nullptr;
                av_samples_alloc(&out_buf, nullptr, OUT_CH_LAYOUT.nb_channels,
                                 out_samples, OUT_SAMPLE_FMT, 0);

                int converted = swr_convert(swr_ctx, &out_buf, out_samples,
                                            (const uint8_t**)frame->data, frame->nb_samples);
                if (converted > 0) {
                    int data_size = av_samples_get_buffer_size(
                        nullptr, OUT_CH_LAYOUT.nb_channels, converted, OUT_SAMPLE_FMT, 1);
                    out_file.write(reinterpret_cast<char*>(out_buf), data_size);
                    total_samples += converted;
                }
                av_freep(&out_buf);
                frame_count++;
                av_frame_unref(frame);
            }
        }

        // Flush
        avcodec_send_packet(codec_ctx, nullptr);
        while (avcodec_receive_frame(codec_ctx, frame) == 0) {
            int out_samples = av_rescale_rnd(
                swr_get_delay(swr_ctx, codec_ctx->sample_rate) + frame->nb_samples,
                OUT_SAMPLE_RATE, codec_ctx->sample_rate, AV_ROUND_UP);
            uint8_t* out_buf = nullptr;
            av_samples_alloc(&out_buf, nullptr, OUT_CH_LAYOUT.nb_channels,
                             out_samples, OUT_SAMPLE_FMT, 0);
            int converted = swr_convert(swr_ctx, &out_buf, out_samples,
                                        (const uint8_t**)frame->data, frame->nb_samples);
            if (converted > 0) {
                int data_size = av_samples_get_buffer_size(
                    nullptr, OUT_CH_LAYOUT.nb_channels, converted, OUT_SAMPLE_FMT, 1);
                out_file.write(reinterpret_cast<char*>(out_buf), data_size);
                total_samples += converted;
            }
            av_freep(&out_buf);
            av_frame_unref(frame);
        }

        double total_time = (double)total_samples / OUT_SAMPLE_RATE;
        std::cout << "\n完成! " << frame_count << " 帧, "
                  << std::fixed << std::setprecision(2) << total_time << "s" << std::endl;
        char ch_layout_desc[64];
        av_channel_layout_describe(&OUT_CH_LAYOUT, ch_layout_desc, sizeof(ch_layout_desc));
        std::cout << "播放: ffplay -f s16le -ar " << OUT_SAMPLE_RATE
                  << " -ch_layout " << ch_layout_desc << " output.pcm" << std::endl;
    }

cleanup:
    if (frame) av_frame_free(&frame);
    if (pkt) av_packet_free(&pkt);
    if (swr_ctx) swr_free(&swr_ctx);
    if (codec_ctx) avcodec_free_context(&codec_ctx);
    if (fmt_ctx) avformat_close_input(&fmt_ctx);
    return 0;
}
