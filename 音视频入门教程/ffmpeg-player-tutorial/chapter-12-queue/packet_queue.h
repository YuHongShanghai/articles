#pragma once

extern "C" {
#include <libavcodec/avcodec.h>
}

#include <queue>
#include <mutex>
#include <condition_variable>

class PacketQueue {
public:
    PacketQueue() = default;
    ~PacketQueue() { flush(); }

    PacketQueue(const PacketQueue&) = delete;
    PacketQueue& operator=(const PacketQueue&) = delete;

    bool push(AVPacket* pkt) {
        std::unique_lock<std::mutex> lock(mutex_);
        cond_push_.wait(lock, [this] { return abort_ || size_ < max_size_; });
        if (abort_) return false;

        AVPacket* new_pkt = av_packet_alloc();
        av_packet_ref(new_pkt, pkt);
        queue_.push(new_pkt);
        size_++;

        cond_pop_.notify_one();
        return true;
    }

    bool pop(AVPacket* pkt) {
        std::unique_lock<std::mutex> lock(mutex_);
        cond_pop_.wait(lock, [this] { return abort_ || !queue_.empty(); });
        if (abort_ && queue_.empty()) return false;

        AVPacket* front = queue_.front();
        queue_.pop();
        av_packet_move_ref(pkt, front);
        av_packet_free(&front);
        size_--;

        cond_push_.notify_one();
        return true;
    }

    void flush() {
        std::lock_guard<std::mutex> lock(mutex_);
        while (!queue_.empty()) {
            AVPacket* pkt = queue_.front();
            queue_.pop();
            av_packet_free(&pkt);
        }
        size_ = 0;
        cond_push_.notify_all();
    }

    void abort() {
        std::lock_guard<std::mutex> lock(mutex_);
        abort_ = true;
        cond_pop_.notify_all();
        cond_push_.notify_all();
    }

    void start() {
        std::lock_guard<std::mutex> lock(mutex_);
        abort_ = false;
    }

    int size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return size_;
    }

    void set_max_size(int max) {
        std::lock_guard<std::mutex> lock(mutex_);
        max_size_ = max;
        cond_push_.notify_all();
    }

private:
    std::queue<AVPacket*> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cond_pop_;
    std::condition_variable cond_push_;
    int size_ = 0;
    int max_size_ = 128;
    bool abort_ = false;
};
