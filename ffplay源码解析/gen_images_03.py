#!/usr/bin/env python3
"""第3篇文章图例：解复用线程与数据读取"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    'primary': '#1565C0', 'green': '#2E7D32', 'orange': '#E65100',
    'purple': '#6A1B9A', 'teal': '#00838F', 'red': '#C62828',
    'grey': '#546E7A', 'yellow': '#FFF9C4', 'bg': '#FAFAFA',
}


def draw_box(ax, x, y, w, h, text, color, fontsize=10, text_color='white', alpha=0.95):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                         facecolor=color, edgecolor='white', linewidth=1.5, alpha=alpha, zorder=2)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight='bold', zorder=3)


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw), zorder=1)


# ==========================================
# 图1: read_thread 主循环流程图
# ==========================================
def gen_read_thread_flow():
    fig, ax = plt.subplots(1, 1, figsize=(10, 16))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 16)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(5, 15.6, 'read_thread 主循环流程', ha='center',
            fontsize=16, fontweight='bold', color='#212121')

    steps = [
        ('avformat_open_input()', '打开输入文件/网络流', COLORS['green']),
        ('avformat_find_stream_info()', '探测流参数', COLORS['green']),
        ('av_find_best_stream()', '选择最佳音/视频/字幕流', COLORS['green']),
        ('stream_component_open()', '打开解码器，启动解码线程', COLORS['purple']),
        ('abort_request?', '检查退出请求', COLORS['grey']),
        ('seek_req?', '处理 Seek 请求\nflush 队列, serial++', COLORS['red']),
        ('队列已满?', '背压控制\n等待 10ms', COLORS['orange']),
        ('av_read_frame()', '读取一个 AVPacket', COLORS['primary']),
        ('分发 Packet', '按 stream_index\n分发到 audioq/videoq/subtitleq', COLORS['teal']),
    ]

    box_w = 4.5
    box_h = 0.9
    x_center = 5
    x_start = x_center - box_w / 2
    y_start = 14.8
    gap = 1.5

    for i, (title, desc, color) in enumerate(steps):
        y = y_start - i * gap

        # 步骤编号
        circle = plt.Circle((x_start - 0.6, y + box_h/2), 0.3,
                            facecolor=color, edgecolor='white', linewidth=2, zorder=3)
        ax.add_patch(circle)
        ax.text(x_start - 0.6, y + box_h/2, str(i+1),
                ha='center', va='center', fontsize=10, color='white', fontweight='bold', zorder=4)

        # 主框
        box = FancyBboxPatch((x_start, y), box_w, box_h, boxstyle="round,pad=0.1",
                             facecolor='white', edgecolor=color, linewidth=2.5, alpha=0.95, zorder=2)
        ax.add_patch(box)
        ax.text(x_start + 0.2, y + box_h - 0.2, title, fontsize=9,
                fontweight='bold', color=color, va='top', zorder=3)
        ax.text(x_start + 0.2, y + box_h - 0.45, desc, fontsize=7,
                color='#424242', va='top', zorder=3)

        # 箭头
        if i < len(steps) - 1:
            next_y = y_start - (i+1) * gap + box_h
            draw_arrow(ax, x_center, y, x_center, next_y, color='#BDBDBD', lw=2)

    # 循环箭头 (step 9 -> step 5)
    loop_x = x_start + box_w + 0.5
    step5_y = y_start - 4 * gap + box_h / 2
    step9_y = y_start - 8 * gap + box_h / 2
    ax.annotate('', xy=(loop_x - 0.2, step5_y),
                xytext=(loop_x - 0.2, step9_y),
                arrowprops=dict(arrowstyle='->', color='#78909C', lw=2,
                               connectionstyle='arc3,rad=0.3'))
    ax.text(loop_x + 0.3, (step5_y + step9_y) / 2, '循环', fontsize=9,
            color='#78909C', fontweight='bold', rotation=90, va='center')

    # 分隔线：初始化 vs 主循环
    sep_y = y_start - 3.5 * gap
    ax.plot([0.5, 9.5], [sep_y, sep_y], '--', color='#BDBDBD', lw=1.5)
    ax.text(9.2, sep_y + 0.15, '初始化阶段', fontsize=8, color='#78909C', ha='right')
    ax.text(9.2, sep_y - 0.25, '主循环阶段', fontsize=8, color='#78909C', ha='right')

    ax.text(5, 0.3, '图 3-1: read_thread 主循环流程',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '03-read-thread-flow.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 03-read-thread-flow.png")


# ==========================================
# 图2: Packet 分发流向
# ==========================================
def gen_packet_dispatch():
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(6, 6.6, 'read_thread Packet 分发流向', ha='center',
            fontsize=16, fontweight='bold', color='#212121')

    # 媒体文件
    draw_box(ax, 0.5, 2.5, 2.2, 1.2, '媒体文件\n网络流', COLORS['grey'], fontsize=10)

    # av_read_frame
    draw_box(ax, 3.5, 2.5, 2.5, 1.2, 'av_read_frame()\n读取 AVPacket', COLORS['primary'], fontsize=9)
    draw_arrow(ax, 2.7, 3.1, 3.5, 3.1, color=COLORS['primary'], lw=2)

    # 判断 stream_index
    diamond_x, diamond_y = 7.5, 3.1
    diamond = plt.Polygon([[diamond_x, diamond_y + 0.7],
                           [diamond_x + 1.0, diamond_y],
                           [diamond_x, diamond_y - 0.7],
                           [diamond_x - 1.0, diamond_y]],
                          facecolor='#FFF9C4', edgecolor='#F9A825', linewidth=2, zorder=2)
    ax.add_patch(diamond)
    ax.text(diamond_x, diamond_y, 'stream\nindex?', ha='center', va='center',
            fontsize=8, fontweight='bold', color='#424242', zorder=3)
    draw_arrow(ax, 6.0, 3.1, diamond_x - 1.0, 3.1, color=COLORS['primary'], lw=2)

    # 三个队列
    draw_box(ax, 9.5, 5.0, 2.0, 0.8, 'audioq', COLORS['purple'], fontsize=10)
    draw_box(ax, 9.5, 3.2, 2.0, 0.8, 'videoq', COLORS['orange'], fontsize=10)
    draw_box(ax, 9.5, 1.4, 2.0, 0.8, 'subtitleq', COLORS['teal'], fontsize=10)

    # 箭头
    draw_arrow(ax, diamond_x + 0.5, diamond_y + 0.5, 9.5, 5.4, color=COLORS['purple'], lw=2)
    draw_arrow(ax, diamond_x + 1.0, diamond_y, 9.5, 3.6, color=COLORS['orange'], lw=2)
    draw_arrow(ax, diamond_x + 0.5, diamond_y - 0.5, 9.5, 1.8, color=COLORS['teal'], lw=2)

    # 标签
    ax.text(8.8, 5.5, 'audio', fontsize=8, color=COLORS['purple'], fontweight='bold')
    ax.text(8.8, 3.7, 'video', fontsize=8, color=COLORS['orange'], fontweight='bold')
    ax.text(8.8, 1.6, 'subtitle', fontsize=8, color=COLORS['teal'], fontweight='bold')

    # 丢弃
    ax.text(diamond_x, 1.8, '其他流\nav_packet_unref()\n丢弃', ha='center', fontsize=7,
            color='#9E9E9E', style='italic')
    draw_arrow(ax, diamond_x, diamond_y - 0.7, diamond_x, 2.2, color='#BDBDBD', lw=1)

    ax.text(6, 0.4, '图 3-2: read_thread 按 stream_index 分发 Packet',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '03-packet-dispatch.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 03-packet-dispatch.png")


if __name__ == '__main__':
    gen_read_thread_flow()
    gen_packet_dispatch()
    print("\n03 done!")
