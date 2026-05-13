#pragma once

extern "C" {
#include <libavutil/frame.h>
}

#include <queue>
#include <mutex>
#include <condition_variable>

class FrameQueue {
public:
    FrameQueue() = default;
    ~FrameQueue() { flush(); }

    FrameQueue(const FrameQueue&) = delete;
    FrameQueue& operator=(const FrameQueue&) = delete;

    bool push(AVFrame* frame) {
        std::unique_lock<std::mutex> lock(mutex_);
        cond_push_.wait(lock, [this] { return abort_ || size_ < max_size_; });
        if (abort_) return false;

        AVFrame* new_frame = av_frame_alloc();
        av_frame_move_ref(new_frame, frame);
        queue_.push(new_frame);
        size_++;

        cond_pop_.notify_one();
        return true;
    }

    bool pop(AVFrame* frame) {
        std::unique_lock<std::mutex> lock(mutex_);
        cond_pop_.wait(lock, [this] { return abort_ || !queue_.empty(); });
        if (abort_ && queue_.empty()) return false;

        AVFrame* front = queue_.front();
        queue_.pop();
        av_frame_move_ref(frame, front);
        av_frame_free(&front);
        size_--;

        cond_push_.notify_one();
        return true;
    }

    void flush() {
        std::lock_guard<std::mutex> lock(mutex_);
        while (!queue_.empty()) {
            AVFrame* f = queue_.front();
            queue_.pop();
            av_frame_free(&f);
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
    std::queue<AVFrame*> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cond_pop_;
    std::condition_variable cond_push_;
    int size_ = 0;
    int max_size_ = 16;
    bool abort_ = false;
};
