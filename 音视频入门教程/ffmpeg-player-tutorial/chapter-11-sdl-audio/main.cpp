extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/channel_layout.h>
#include <libswresample/swresample.h>
}

#include <SDL2/SDL.h>
#include <iostream>
#include <vector>
#include <mutex>
#include <algorithm>
#include <cstring>
#include <atomic>

class AudioRingBuffer {
public:
    explicit AudioRingBuffer(size_t capacity = 1024 * 1024)
        : buffer_(capacity), write_pos_(0), read_pos_(0), size_(0) {}

    size_t write(const uint8_t* data, size_t len) {
        std::lock_guard<std::mutex> lock(mutex_);
        size_t space = buffer_.size() - size_;
        size_t n = std::min(len, space);
        for (size_t i = 0; i < n; i++) {
            buffer_[write_pos_] = data[i];
            write_pos_ = (write_pos_ + 1) % buffer_.size();
        }
        size_ += n;
        return n;
    }

    size_t read(uint8_t* data, size_t len) {
        std::lock_guard<std::mutex> lock(mutex_);
        size_t n = std::min(len, size_);
        for (size_t i = 0; i < n; i++) {
            data[i] = buffer_[read_pos_];
            read_pos_ = (read_pos_ + 1) % buffer_.size();
        }
        size_ -= n;
        return n;
    }

    size_t available() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return size_;
    }

private:
    std::vector<uint8_t> buffer_;
    size_t write_pos_, read_pos_, size_;
    mutable std::mutex mutex_;
};

struct AudioState {
    AudioRingBuffer buffer;
    int volume = SDL_MIX_MAXVOLUME;
};

void audio_callback(void* userdata, Uint8* stream, int len) {
    auto* state = static_cast<AudioState*>(userdata);
    memset(stream, 0, len);
    std::vector<uint8_t> temp(len);
    size_t got = state->buffer.read(temp.data(), len);
    if (got > 0) {
        SDL_MixAudioFormat(stream, temp.data(), AUDIO_S16SYS, static_cast<Uint32>(got), state->volume);
    }
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <输入文件>" << std::endl;
        return 1;
    }

    const char* input_file = argv[1];
    const int OUT_SAMPLE_RATE = 44100;
    const int OUT_CHANNELS = 2;
    const AVSampleFormat OUT_FMT = AV_SAMPLE_FMT_S16;

    AVFormatContext* fmt_ctx = nullptr;
    avformat_open_input(&fmt_ctx, input_file, nullptr, nullptr);
    avformat_find_stream_info(fmt_ctx, nullptr);

    int audio_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_AUDIO, -1, -1, nullptr, 0);
    if (audio_idx < 0) { std::cerr << "找不到音频流" << std::endl; return 1; }

    AVStream* audio_stream = fmt_ctx->streams[audio_idx];
    const AVCodec* codec = avcodec_find_decoder(audio_stream->codecpar->codec_id);
    AVCodecContext* codec_ctx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(codec_ctx, audio_stream->codecpar);
    avcodec_open2(codec_ctx, codec, nullptr);

    SwrContext* swr_ctx = nullptr;
    AVChannelLayout out_layout = AV_CHANNEL_LAYOUT_STEREO;
    AVChannelLayout in_layout;
    av_channel_layout_copy(&in_layout, &codec_ctx->ch_layout);
    swr_alloc_set_opts2(&swr_ctx,
        &out_layout, OUT_FMT, OUT_SAMPLE_RATE,
        &in_layout, codec_ctx->sample_fmt, codec_ctx->sample_rate, 0, nullptr);
    av_channel_layout_uninit(&in_layout);
    swr_init(swr_ctx);

    std::cout << "音频: " << avcodec_get_name(codec_ctx->codec_id)
              << ", " << codec_ctx->sample_rate << " Hz" << std::endl;

    SDL_Init(SDL_INIT_AUDIO);
    AudioState audio_state;

    SDL_AudioSpec wanted{}, obtained{};
    wanted.freq = OUT_SAMPLE_RATE;
    wanted.format = AUDIO_S16SYS;
    wanted.channels = OUT_CHANNELS;
    wanted.silence = 0;
    wanted.samples = 1024;
    wanted.callback = audio_callback;
    wanted.userdata = &audio_state;

    SDL_AudioDeviceID dev = SDL_OpenAudioDevice(nullptr, 0, &wanted, &obtained, 0);
    if (dev == 0) { std::cerr << "无法打开音频: " << SDL_GetError() << std::endl; return 1; }

    SDL_PauseAudioDevice(dev, 0);
    std::cout << "播放中... 按 Ctrl+C 退出" << std::endl;

    AVPacket* pkt = av_packet_alloc();
    AVFrame* frame = av_frame_alloc();

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index != audio_idx) { av_packet_unref(pkt); continue; }

        avcodec_send_packet(codec_ctx, pkt);
        av_packet_unref(pkt);

        while (avcodec_receive_frame(codec_ctx, frame) == 0) {
            int out_samples = av_rescale_rnd(
                swr_get_delay(swr_ctx, codec_ctx->sample_rate) + frame->nb_samples,
                OUT_SAMPLE_RATE, codec_ctx->sample_rate, AV_ROUND_UP);

            uint8_t* out_buf = nullptr;
            av_samples_alloc(&out_buf, nullptr, OUT_CHANNELS, out_samples, OUT_FMT, 0);
            int converted = swr_convert(swr_ctx, &out_buf, out_samples,
                                        (const uint8_t**)frame->data, frame->nb_samples);
            if (converted > 0) {
                int size = av_samples_get_buffer_size(nullptr, OUT_CHANNELS, converted, OUT_FMT, 1);
                while (audio_state.buffer.available() > 800000) SDL_Delay(10);
                audio_state.buffer.write(out_buf, size);
            }
            av_freep(&out_buf);
            av_frame_unref(frame);
        }

        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) goto done;
        }
    }

done:
    while (audio_state.buffer.available() > 0) SDL_Delay(100);
    SDL_Delay(500);

    SDL_CloseAudioDevice(dev);
    SDL_Quit();
    av_frame_free(&frame);
    av_packet_free(&pkt);
    swr_free(&swr_ctx);
    avcodec_free_context(&codec_ctx);
    avformat_close_input(&fmt_ctx);
    return 0;
}
