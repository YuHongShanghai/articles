#!/usr/bin/env python3
"""第1篇文章图例：ffplay整体架构与启动流程"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np
import os

# ========== 全局字体设置 ==========
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== 配色方案 ==========
COLORS = {
    'app':       '#2196F3',  # 蓝色 - 应用层
    'avformat':  '#4CAF50',  # 绿色
    'avcodec':   '#FF9800',  # 橙色
    'avutil':    '#9E9E9E',  # 灰色
    'swscale':   '#E91E63',  # 粉色
    'swresample':'#9C27B0',  # 紫色
    'avfilter':  '#00BCD4',  # 青色
    'avdevice':  '#795548',  # 棕色
    'sdl':       '#F44336',  # 红色
    'thread_main':   '#1565C0',
    'thread_read':   '#2E7D32',
    'thread_video':  '#E65100',
    'thread_audio':  '#6A1B9A',
    'thread_sub':    '#00838F',
    'queue':         '#FFF9C4',
    'arrow':         '#455A64',
    'bg':            '#FAFAFA',
}


def draw_rounded_box(ax, x, y, w, h, text, color, fontsize=11, text_color='white', alpha=0.95):
    """绘制圆角矩形方框"""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.1",
                         facecolor=color, edgecolor='white',
                         linewidth=1.5, alpha=alpha, zorder=2)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text,
            ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight='bold', zorder=3)
    return box


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', style='->', lw=1.5):
    """绘制箭头"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                zorder=1)


# ==========================================
# 图1: FFmpeg 库依赖关系图
# ==========================================
def gen_ffmpeg_libs():
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    # 标题
    ax.text(6, 6.6, 'ffplay 依赖的 FFmpeg 库与外部库', ha='center', va='center',
            fontsize=16, fontweight='bold', color='#212121')

    # 最上层: ffplay 应用
    draw_rounded_box(ax, 3.5, 5.5, 5, 0.8, 'ffplay  (应用层)', COLORS['app'], fontsize=14)

    # 中间层: FFmpeg 核心库
    # 第一行
    draw_rounded_box(ax, 0.3, 4.0, 2.5, 0.7, 'libavformat\n(封装/解封装)', COLORS['avformat'], fontsize=9)
    draw_rounded_box(ax, 3.2, 4.0, 2.3, 0.7, 'libavcodec\n(编解码)', COLORS['avcodec'], fontsize=9)
    draw_rounded_box(ax, 5.9, 4.0, 2.3, 0.7, 'libavfilter\n(滤镜处理)', COLORS['avfilter'], fontsize=9)
    draw_rounded_box(ax, 8.6, 4.0, 2.8, 0.7, 'libavdevice\n(设备输入输出)', COLORS['avdevice'], fontsize=9)

    # 第二行
    draw_rounded_box(ax, 1.5, 2.8, 2.5, 0.7, 'libswscale\n(视频缩放/转换)', COLORS['swscale'], fontsize=9)
    draw_rounded_box(ax, 4.5, 2.8, 2.8, 0.7, 'libswresample\n(音频重采样)', COLORS['swresample'], fontsize=9)
    draw_rounded_box(ax, 8.0, 2.8, 2.5, 0.7, 'libavutil\n(通用工具库)', COLORS['avutil'], fontsize=9, text_color='white')

    # 底层: SDL2
    draw_rounded_box(ax, 2.5, 1.2, 7, 0.8, 'SDL2  (窗口管理 / 音频输出 / 事件处理 / 渲染)', COLORS['sdl'], fontsize=11)

    # 绘制连接线 - ffplay 到各库
    for x_center in [1.55, 4.35, 7.05, 10.0]:
        draw_arrow(ax, 6, 5.5, x_center, 4.7, lw=1.2)

    for x_center in [2.75, 5.9, 9.25]:
        draw_arrow(ax, 6, 5.5, x_center, 3.5, lw=1.0, color='#78909C')

    # ffplay 到 SDL2
    draw_arrow(ax, 6, 5.5, 6, 2.0, lw=1.8, color=COLORS['sdl'])

    # 说明标注
    ax.text(6, 0.5, '图 1-1: ffplay 依赖的 FFmpeg 库与 SDL2 外部库',
            ha='center', va='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01-ffmpeg-libs.png'), dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close()
    print("✓ 生成 01-ffmpeg-libs.png")


# ==========================================
# 图2: ffplay 多线程架构与数据流
# ==========================================
def gen_architecture():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    # 标题
    ax.text(7, 9.6, 'ffplay 多线程架构与数据流', ha='center', va='center',
            fontsize=16, fontweight='bold', color='#212121')

    # ---- 最底层: 媒体文件 ----
    draw_rounded_box(ax, 4.5, 0.3, 5, 0.7, '媒体文件 / 网络流', '#607D8B', fontsize=12)

    # ---- Read Thread ----
    rect_read = FancyBboxPatch((1.5, 1.5), 11, 1.5,
                               boxstyle="round,pad=0.15",
                               facecolor=COLORS['thread_read'], edgecolor='white',
                               linewidth=2, alpha=0.15, zorder=1)
    ax.add_patch(rect_read)
    draw_rounded_box(ax, 4.5, 1.7, 5, 0.9, 'Read Thread\n(read_thread)', COLORS['thread_read'], fontsize=11)

    ax.text(11, 2.8, 'demux 解复用线程', fontsize=9, color=COLORS['thread_read'],
            ha='center', va='center', style='italic')

    # 箭头: 媒体文件 → Read Thread
    draw_arrow(ax, 7, 1.0, 7, 1.7, color=COLORS['arrow'], lw=2)
    ax.text(7.5, 1.3, 'av_read_frame()', fontsize=8, color='#455A64', style='italic')

    # ---- PacketQueues ----
    pq_y = 3.6
    draw_rounded_box(ax, 1.2, pq_y, 2.4, 0.65, 'audioq\n(PacketQueue)', COLORS['queue'],
                     fontsize=8, text_color='#333333', alpha=1.0)
    draw_rounded_box(ax, 4.3, pq_y, 2.4, 0.65, 'videoq\n(PacketQueue)', COLORS['queue'],
                     fontsize=8, text_color='#333333', alpha=1.0)
    draw_rounded_box(ax, 7.4, pq_y, 2.6, 0.65, 'subtitleq\n(PacketQueue)', COLORS['queue'],
                     fontsize=8, text_color='#333333', alpha=1.0)

    # 箭头: Read Thread → PacketQueues
    draw_arrow(ax, 5.5, 2.6, 2.4, pq_y, color=COLORS['arrow'], lw=1.5)
    draw_arrow(ax, 7, 2.6, 5.5, pq_y, color=COLORS['arrow'], lw=1.5)
    draw_arrow(ax, 8, 2.6, 8.7, pq_y, color=COLORS['arrow'], lw=1.5)

    # ---- Decode Threads ----
    dt_y = 4.9
    rect_dec = FancyBboxPatch((0.5, dt_y - 0.15), 12.5, 1.4,
                              boxstyle="round,pad=0.12",
                              facecolor='#F5F5F5', edgecolor='#BDBDBD',
                              linewidth=1, alpha=0.8, zorder=0)
    ax.add_patch(rect_dec)
    ax.text(12.2, dt_y + 1.1, '解码线程层', fontsize=9, color='#757575',
            ha='center', va='center', style='italic')

    draw_rounded_box(ax, 0.8, dt_y, 2.8, 0.9, 'Audio Thread\n(audio_thread)', COLORS['thread_audio'], fontsize=10)
    draw_rounded_box(ax, 4.0, dt_y, 2.8, 0.9, 'Video Thread\n(video_thread)', COLORS['thread_video'], fontsize=10)
    draw_rounded_box(ax, 7.2, dt_y, 3.0, 0.9, 'Subtitle Thread\n(subtitle_thread)', COLORS['thread_sub'], fontsize=10)

    # 箭头: PacketQueues → Decode Threads
    draw_arrow(ax, 2.4, pq_y + 0.65, 2.2, dt_y, color=COLORS['thread_audio'], lw=1.5)
    draw_arrow(ax, 5.5, pq_y + 0.65, 5.4, dt_y, color=COLORS['thread_video'], lw=1.5)
    draw_arrow(ax, 8.7, pq_y + 0.65, 8.7, dt_y, color=COLORS['thread_sub'], lw=1.5)

    # ---- FrameQueues ----
    fq_y = 6.5
    draw_rounded_box(ax, 1.0, fq_y, 2.4, 0.65, 'sampq\n(FrameQueue)', COLORS['queue'],
                     fontsize=8, text_color='#333333', alpha=1.0)
    draw_rounded_box(ax, 4.1, fq_y, 2.4, 0.65, 'pictq\n(FrameQueue)', COLORS['queue'],
                     fontsize=8, text_color='#333333', alpha=1.0)
    draw_rounded_box(ax, 7.3, fq_y, 2.6, 0.65, 'subpq\n(FrameQueue)', COLORS['queue'],
                     fontsize=8, text_color='#333333', alpha=1.0)

    # 箭头: Decode Threads → FrameQueues
    draw_arrow(ax, 2.2, dt_y + 0.9, 2.2, fq_y, color=COLORS['thread_audio'], lw=1.5)
    draw_arrow(ax, 5.4, dt_y + 0.9, 5.3, fq_y, color=COLORS['thread_video'], lw=1.5)
    draw_arrow(ax, 8.7, dt_y + 0.9, 8.6, fq_y, color=COLORS['thread_sub'], lw=1.5)

    # ---- Main Thread (Event Loop) ----
    rect_main = FancyBboxPatch((0.5, 7.6), 12.5, 1.6,
                               boxstyle="round,pad=0.15",
                               facecolor=COLORS['thread_main'], edgecolor='white',
                               linewidth=2, alpha=0.12, zorder=0)
    ax.add_patch(rect_main)
    ax.text(1.5, 9.05, 'Main Thread (主线程 / 事件循环)', fontsize=10, color=COLORS['thread_main'],
            fontweight='bold', va='center')

    draw_rounded_box(ax, 0.8, 7.8, 3, 0.9, 'SDL Audio Callback\n(sdl_audio_callback)', '#7B1FA2', fontsize=9)
    draw_rounded_box(ax, 4.2, 7.8, 2.8, 0.9, 'video_refresh()\n视频刷新与渲染', COLORS['thread_main'], fontsize=9)
    draw_rounded_box(ax, 7.4, 7.8, 2.4, 0.9, 'event_loop()\n事件处理', '#1565C0', fontsize=9)
    draw_rounded_box(ax, 10.2, 7.8, 2.5, 0.9, 'SDL Renderer\n画面渲染输出', '#C62828', fontsize=9)

    # 箭头: FrameQueues → Main Thread consumers
    draw_arrow(ax, 2.2, fq_y + 0.65, 2.3, 7.8, color=COLORS['thread_audio'], lw=1.8)
    draw_arrow(ax, 5.3, fq_y + 0.65, 5.6, 7.8, color=COLORS['thread_video'], lw=1.8)
    draw_arrow(ax, 8.6, fq_y + 0.65, 5.8, 7.8, color=COLORS['thread_sub'], lw=1.2, style='->')

    # 箭头: video_refresh → SDL Renderer
    draw_arrow(ax, 7.0, 8.25, 7.4, 8.25, color='#C62828', lw=1.5)
    draw_arrow(ax, 9.8, 8.25, 10.2, 8.25, color='#C62828', lw=1.5)

    # 图注
    ax.text(7, -0.1, '图 1-2: ffplay 多线程架构与数据流向',
            ha='center', va='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01-ffplay-architecture.png'), dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close()
    print("✓ 生成 01-ffplay-architecture.png")


# ==========================================
# 图3: main() 启动流程图
# ==========================================
def gen_main_flow():
    fig, ax = plt.subplots(1, 1, figsize=(8, 14))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 14)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    # 标题
    ax.text(4, 13.6, 'main() 启动流程', ha='center', va='center',
            fontsize=16, fontweight='bold', color='#212121')

    # 流程步骤
    steps = [
        ('初始化与参数解析', 'init_dynload()\nparse_loglevel()\navdevice_register_all()\navformat_network_init()\nparse_options()', '#546E7A'),
        ('SDL 初始化', 'SDL_Init()\n(Video + Audio + Timer)', COLORS['sdl']),
        ('创建 SDL 窗口', 'SDL_CreateWindow()\nSDL_CreateRenderer()\n或 Vulkan Renderer', '#E65100'),
        ('打开媒体流', 'stream_open()\n├─ 初始化各种队列\n├─ 初始化时钟\n└─ 创建 read_thread', COLORS['thread_read']),
        ('进入事件主循环', 'event_loop()\n├─ refresh_loop_wait_event()\n│   ├─ video_refresh() 刷新\n│   └─ SDL_PeepEvents() 检测\n└─ 处理键盘/鼠标事件', COLORS['thread_main']),
    ]

    box_w = 5.5
    box_h = 1.6
    x_start = (8 - box_w) / 2
    y_start = 12.5
    gap = 2.3

    for i, (title, detail, color) in enumerate(steps):
        y = y_start - i * gap

        # 步骤编号圆圈
        circle = plt.Circle((x_start - 0.5, y + box_h/2), 0.3,
                            facecolor=color, edgecolor='white', linewidth=2, zorder=3)
        ax.add_patch(circle)
        ax.text(x_start - 0.5, y + box_h/2, str(i+1),
                ha='center', va='center', fontsize=12, color='white', fontweight='bold', zorder=4)

        # 主体框
        box = FancyBboxPatch((x_start, y), box_w, box_h,
                             boxstyle="round,pad=0.12",
                             facecolor='white', edgecolor=color,
                             linewidth=2.5, alpha=0.95, zorder=2)
        ax.add_patch(box)

        # 标题
        ax.text(x_start + 0.3, y + box_h - 0.25, title,
                fontsize=11, fontweight='bold', color=color, va='top', zorder=3)
        # 详情
        ax.text(x_start + 0.3, y + box_h - 0.55, detail,
                fontsize=8, color='#424242', va='top',
                linespacing=1.4, zorder=3)

        # 箭头连接
        if i < len(steps) - 1:
            next_y = y_start - (i+1) * gap + box_h
            draw_arrow(ax, 4, y, 4, next_y, color='#BDBDBD', lw=2)

    # 注释说明
    # stream_open 展开
    ax.annotate('创建 read_thread\n→ 启动解复用',
                xy=(x_start + box_w, y_start - 3*gap + 0.3),
                xytext=(x_start + box_w + 0.8, y_start - 3*gap - 0.3),
                fontsize=8, color=COLORS['thread_read'], style='italic',
                arrowprops=dict(arrowstyle='->', color=COLORS['thread_read'], lw=1))

    ax.text(4, 0.3, '图 1-3: main() 函数启动流程',
            ha='center', va='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01-main-flow.png'), dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close()
    print("✓ 生成 01-main-flow.png")


if __name__ == '__main__':
    gen_ffmpeg_libs()
    gen_architecture()
    gen_main_flow()
    print("\n第1篇图例全部生成完毕！")
