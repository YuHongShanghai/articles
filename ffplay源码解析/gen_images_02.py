#!/usr/bin/env python3
"""第2篇文章图例：核心数据结构详解"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

# ========== 全局字体设置 ==========
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== 配色方案 ==========
COLORS = {
    'primary':    '#1565C0',
    'secondary':  '#2E7D32',
    'accent':     '#E65100',
    'purple':     '#6A1B9A',
    'teal':       '#00838F',
    'red':        '#C62828',
    'grey':       '#546E7A',
    'light_blue': '#E3F2FD',
    'light_green':'#E8F5E9',
    'light_orange':'#FFF3E0',
    'light_purple':'#F3E5F5',
    'light_grey': '#ECEFF1',
    'queue_yellow':'#FFF9C4',
    'bg':         '#FAFAFA',
    'white':      '#FFFFFF',
}


def draw_box(ax, x, y, w, h, text, color, fontsize=10, text_color='white', alpha=0.95, lw=1.5):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                         facecolor=color, edgecolor='white', linewidth=lw, alpha=alpha, zorder=2)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight='bold', zorder=3)
    return box


def draw_box_outline(ax, x, y, w, h, text, color, fontsize=10, lw=2):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                         facecolor='white', edgecolor=color, linewidth=lw, alpha=0.95, zorder=2)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize,
            color=color, fontweight='bold', zorder=3)
    return box


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', style='->', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw), zorder=1)


# ==========================================
# 图1: 核心数据结构关系总图
# ==========================================
def gen_data_structures_overview():
    fig, ax = plt.subplots(1, 1, figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7, 8.6, 'ffplay 核心数据结构关系图', ha='center', va='center',
            fontsize=16, fontweight='bold', color='#212121')

    # VideoState (中心大框)
    vs_rect = FancyBboxPatch((2, 1.5), 10, 6.5, boxstyle="round,pad=0.2",
                              facecolor=COLORS['light_blue'], edgecolor=COLORS['primary'],
                              linewidth=2.5, alpha=0.4, zorder=0)
    ax.add_patch(vs_rect)
    ax.text(7, 7.6, 'VideoState  (播放器核心上下文)', ha='center', va='center',
            fontsize=13, fontweight='bold', color=COLORS['primary'])

    # PacketQueues
    draw_box(ax, 2.5, 5.8, 2.2, 0.7, 'audioq\nPacketQueue', COLORS['secondary'], fontsize=8)
    draw_box(ax, 5.2, 5.8, 2.2, 0.7, 'videoq\nPacketQueue', COLORS['secondary'], fontsize=8)
    draw_box(ax, 7.9, 5.8, 2.2, 0.7, 'subtitleq\nPacketQueue', COLORS['secondary'], fontsize=8)

    # FrameQueues
    draw_box(ax, 2.5, 4.5, 2.2, 0.7, 'sampq\nFrameQueue', COLORS['accent'], fontsize=8)
    draw_box(ax, 5.2, 4.5, 2.2, 0.7, 'pictq\nFrameQueue', COLORS['accent'], fontsize=8)
    draw_box(ax, 7.9, 4.5, 2.2, 0.7, 'subpq\nFrameQueue', COLORS['accent'], fontsize=8)

    # Decoders
    draw_box(ax, 2.5, 3.2, 2.2, 0.7, 'auddec\nDecoder', COLORS['purple'], fontsize=8)
    draw_box(ax, 5.2, 3.2, 2.2, 0.7, 'viddec\nDecoder', COLORS['purple'], fontsize=8)
    draw_box(ax, 7.9, 3.2, 2.2, 0.7, 'subdec\nDecoder', COLORS['purple'], fontsize=8)

    # Clocks
    draw_box(ax, 2.7, 1.9, 1.8, 0.7, 'audclk\nClock', COLORS['teal'], fontsize=8)
    draw_box(ax, 5.4, 1.9, 1.8, 0.7, 'vidclk\nClock', COLORS['teal'], fontsize=8)
    draw_box(ax, 8.1, 1.9, 1.8, 0.7, 'extclk\nClock', COLORS['teal'], fontsize=8)

    # AVFormatContext
    draw_box_outline(ax, 10.5, 5.8, 1.3, 0.7, 'ic\nAVFormat\nContext', COLORS['grey'], fontsize=7)

    # 音频参数
    draw_box_outline(ax, 10.5, 3.2, 1.3, 0.7, 'audio_tgt\naudio_src\nAudioParams', COLORS['red'], fontsize=6)

    # SwrContext
    draw_box_outline(ax, 10.5, 1.9, 1.3, 0.7, 'swr_ctx\nSwrContext', COLORS['red'], fontsize=7)

    # 箭头: PacketQueue → Decoder
    for x in [3.6, 6.3, 9.0]:
        draw_arrow(ax, x, 5.8, x, 3.9, color='#78909C', lw=1.2)

    # 箭头: Decoder → FrameQueue
    for x in [3.6, 6.3, 9.0]:
        draw_arrow(ax, x, 4.5, x, 3.9, color='#78909C', lw=1.2, style='<-')

    # 标签
    ax.text(1.8, 6.1, '包队列层', fontsize=8, color=COLORS['secondary'], fontweight='bold', rotation=90, va='center')
    ax.text(1.8, 4.8, '帧队列层', fontsize=8, color=COLORS['accent'], fontweight='bold', rotation=90, va='center')
    ax.text(1.8, 3.5, '解码器层', fontsize=8, color=COLORS['purple'], fontweight='bold', rotation=90, va='center')
    ax.text(1.8, 2.2, '时钟层', fontsize=8, color=COLORS['teal'], fontweight='bold', rotation=90, va='center')

    # 图例
    legend_items = [
        ('PacketQueue (压缩包队列)', COLORS['secondary']),
        ('FrameQueue (解码帧队列)', COLORS['accent']),
        ('Decoder (解码器)', COLORS['purple']),
        ('Clock (同步时钟)', COLORS['teal']),
    ]
    for i, (label, color) in enumerate(legend_items):
        ax.add_patch(FancyBboxPatch((0.3, 0.4 + i * 0.35), 0.35, 0.25,
                     boxstyle="round,pad=0.03", facecolor=color, edgecolor='white', zorder=2))
        ax.text(0.8, 0.52 + i * 0.35, label, fontsize=8, va='center', color='#424242')

    ax.text(7, 0.15, '图 2-1: ffplay 核心数据结构关系图',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02-data-structures-overview.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("✓ 生成 02-data-structures-overview.png")


# ==========================================
# 图2: PacketQueue 结构与操作
# ==========================================
def gen_packet_queue():
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(6, 6.6, 'PacketQueue 结构与操作示意', ha='center',
            fontsize=16, fontweight='bold', color='#212121')

    # 外框 - PacketQueue
    pq_rect = FancyBboxPatch((1, 1.5), 10, 4.5, boxstyle="round,pad=0.15",
                              facecolor=COLORS['light_green'], edgecolor=COLORS['secondary'],
                              linewidth=2, alpha=0.3, zorder=0)
    ax.add_patch(pq_rect)
    ax.text(6, 5.7, 'PacketQueue', ha='center', fontsize=12, fontweight='bold', color=COLORS['secondary'])

    # AVFifo (pkt_list)
    fifo_y = 3.8
    ax.text(2, fifo_y + 1.0, 'pkt_list (AVFifo)', fontsize=9, color='#424242', fontweight='bold')
    for i in range(6):
        x = 1.5 + i * 1.5
        if i < 4:
            color = '#81C784' if i < 3 else '#E0E0E0'
            label = f'Pkt\nserial={1 if i < 3 else "?"}' if i < 4 else ''
            alpha = 0.9 if i < 3 else 0.4
        else:
            color = '#E0E0E0'
            label = ''
            alpha = 0.3
        box = FancyBboxPatch((x, fifo_y), 1.2, 0.8, boxstyle="round,pad=0.05",
                             facecolor=color, edgecolor='white', linewidth=1.5, alpha=alpha, zorder=2)
        ax.add_patch(box)
        if i < 3:
            ax.text(x + 0.6, fifo_y + 0.4, label, ha='center', va='center',
                    fontsize=7, color='white', fontweight='bold', zorder=3)

    # 属性标签
    props = [
        ('nb_packets = 3', 1.5, 2.5),
        ('size = 24576', 4.0, 2.5),
        ('serial = 1', 6.5, 2.5),
        ('abort_request = 0', 9.0, 2.5),
    ]
    for text, x, y in props:
        ax.text(x, y, text, fontsize=8, color='#424242',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#BDBDBD', alpha=0.9))

    # mutex & cond
    draw_box(ax, 1.5, 1.7, 1.5, 0.5, 'mutex', '#78909C', fontsize=8)
    draw_box(ax, 3.3, 1.7, 1.5, 0.5, 'cond', '#78909C', fontsize=8)

    # 生产者箭头
    ax.annotate('read_thread\n(生产者)', xy=(1.5, 4.2), xytext=(-0.3, 4.5),
                fontsize=9, color=COLORS['secondary'], fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=COLORS['secondary'], lw=2))

    # 消费者箭头
    ax.annotate('解码线程\n(消费者)', xy=(10.2, 4.2), xytext=(11.0, 4.5),
                fontsize=9, color=COLORS['accent'], fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=2))

    # 操作说明
    ops = [
        ('packet_queue_put()', 'white', COLORS['secondary']),
        ('packet_queue_get()', 'white', COLORS['accent']),
        ('packet_queue_flush()', 'white', COLORS['red']),
    ]
    for i, (text, tc, bg) in enumerate(ops):
        ax.text(6.5 + i * 0.0, 1.8 + i * 0.0, '', fontsize=8)

    ax.text(6, 0.6, '图 2-2: PacketQueue 结构与操作示意',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02-packet-queue.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("✓ 生成 02-packet-queue.png")


# ==========================================
# 图3: FrameQueue 环形缓冲区
# ==========================================
def gen_frame_queue():
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_xlim(-5, 5)
    ax.set_ylim(-5, 5)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(0, 4.5, 'FrameQueue 环形缓冲区（以视频队列为例，max_size=3）',
            ha='center', fontsize=13, fontweight='bold', color='#212121')

    # 画环形
    n_slots = 3
    radius = 2.8
    slot_radius = 0.65
    colors_fill = [COLORS['accent'], '#FFA726', '#E0E0E0']
    labels = ['Frame 0\n(lastvp)\nrindex=0', 'Frame 1\n(vp/当前帧)\npeek()', 'Frame 2\n(空闲)\nwindex=2']
    states = ['已显示', '待显示', '可写入']
    state_colors = ['#78909C', COLORS['accent'], COLORS['secondary']]

    for i in range(n_slots):
        angle = 90 - i * (360 / n_slots)
        rad = np.radians(angle)
        x = radius * np.cos(rad)
        y = radius * np.sin(rad)

        circle = plt.Circle((x, y), slot_radius, facecolor=colors_fill[i],
                            edgecolor='white', linewidth=2.5, alpha=0.9, zorder=2)
        ax.add_patch(circle)
        ax.text(x, y, labels[i], ha='center', va='center',
                fontsize=7, color='white', fontweight='bold', zorder=3)

        # 状态标签
        label_x = x * 1.55
        label_y = y * 1.55
        ax.text(label_x, label_y, states[i], ha='center', va='center',
                fontsize=9, color=state_colors[i], fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor=state_colors[i], alpha=0.9))

    # 中心标注
    ax.text(0, 0.15, 'FrameQueue', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#424242')
    ax.text(0, -0.25, 'keep_last=1\nrindex_shown=1', ha='center', va='center',
            fontsize=8, color='#757575')

    # 环形箭头（顺时针方向）
    arc_angles = np.linspace(80, -200, 100)
    arc_x = 1.8 * np.cos(np.radians(arc_angles))
    arc_y = 1.8 * np.sin(np.radians(arc_angles))
    ax.plot(arc_x, arc_y, color='#BDBDBD', lw=1.5, ls='--', zorder=1)
    ax.annotate('', xy=(arc_x[-1], arc_y[-1]), xytext=(arc_x[-3], arc_y[-3]),
                arrowprops=dict(arrowstyle='->', color='#BDBDBD', lw=1.5))

    # 生产者/消费者标注
    ax.text(-4.2, 2.0, '生产者\n(解码线程)', fontsize=10, color=COLORS['secondary'],
            fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['light_green'],
                      edgecolor=COLORS['secondary']))
    ax.annotate('', xy=(radius * np.cos(np.radians(90 - 2*120)) - slot_radius, radius * np.sin(np.radians(90 - 2*120))),
                xytext=(-3.5, 1.5),
                arrowprops=dict(arrowstyle='->', color=COLORS['secondary'], lw=2))

    ax.text(4.2, 2.0, '消费者\n(渲染线程)', fontsize=10, color=COLORS['accent'],
            fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['light_orange'],
                      edgecolor=COLORS['accent']))
    ax.annotate('', xy=(radius * np.cos(np.radians(90 - 120)) + slot_radius * 0.5, radius * np.sin(np.radians(90 - 120))),
                xytext=(3.5, 1.5),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=2))

    # peek 操作说明
    peek_info = [
        'peek_last()  ->  rindex',
        'peek()       ->  rindex + rindex_shown',
        'peek_next()  ->  rindex + rindex_shown + 1',
    ]
    peek_labels = ['(上一帧)', '(当前帧)', '(下一帧)']
    for i, (text, label) in enumerate(zip(peek_info, peek_labels)):
        ax.text(-1.2, -3.0 - i * 0.4, text, ha='left', fontsize=8, color='#424242',
                fontfamily='monospace')
        ax.text(3.0, -3.0 - i * 0.4, label, ha='left', fontsize=8, color='#424242')

    ax.text(0, -4.5, '图 2-3: FrameQueue 环形缓冲区示意（keep_last=1）',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02-frame-queue.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("✓ 生成 02-frame-queue.png")


# ==========================================
# 图4: Clock 时钟工作原理
# ==========================================
def gen_clock():
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(6, 5.6, 'Clock 时钟工作原理', ha='center',
            fontsize=16, fontweight='bold', color='#212121')

    # 时间轴
    ax.annotate('', xy=(11, 3.0), xytext=(1, 3.0),
                arrowprops=dict(arrowstyle='->', color='#424242', lw=2))
    ax.text(11.2, 3.0, '系统时间 t', fontsize=9, va='center', color='#424242')

    # set_clock 时刻
    t_set = 3.0
    ax.plot([t_set, t_set], [2.5, 3.5], color=COLORS['primary'], lw=2, zorder=2)
    ax.plot(t_set, 3.0, 'o', color=COLORS['primary'], markersize=10, zorder=3)
    ax.text(t_set, 3.7, 'set_clock()\npts=5.0, t0=3.0', ha='center', fontsize=8,
            color=COLORS['primary'], fontweight='bold')
    ax.text(t_set, 2.2, 'pts_drift = pts - t0\n= 5.0 - 3.0 = 2.0', ha='center',
            fontsize=8, color=COLORS['primary'])

    # get_clock 时刻
    t_get = 7.5
    ax.plot([t_get, t_get], [2.5, 3.5], color=COLORS['accent'], lw=2, zorder=2)
    ax.plot(t_get, 3.0, 's', color=COLORS['accent'], markersize=10, zorder=3)
    ax.text(t_get, 3.7, 'get_clock()\nt_now=7.5', ha='center', fontsize=8,
            color=COLORS['accent'], fontweight='bold')
    ax.text(t_get, 2.2, 'result = pts_drift + t_now\n= 2.0 + 7.5 = 9.5', ha='center',
            fontsize=8, color=COLORS['accent'])

    # pts 时间轴
    ax.annotate('', xy=(11, 1.0), xytext=(1, 1.0),
                arrowprops=dict(arrowstyle='->', color=COLORS['teal'], lw=2))
    ax.text(11.2, 1.0, '播放时间', fontsize=9, va='center', color=COLORS['teal'])

    # 标注 pts 值
    ax.plot(t_set, 1.0, 'o', color=COLORS['teal'], markersize=8, zorder=3)
    ax.text(t_set, 0.6, 'pts=5.0', ha='center', fontsize=8, color=COLORS['teal'])

    ax.plot(t_get, 1.0, 's', color=COLORS['teal'], markersize=8, zorder=3)
    ax.text(t_get, 0.6, 'pts=9.5', ha='center', fontsize=8, color=COLORS['teal'])

    # 虚线连接
    ax.plot([t_set, t_set], [1.3, 2.2], '--', color='#BDBDBD', lw=1)
    ax.plot([t_get, t_get], [1.3, 2.2], '--', color='#BDBDBD', lw=1)

    # 时间差标注
    ax.annotate('', xy=(t_get, 4.3), xytext=(t_set, 4.3),
                arrowprops=dict(arrowstyle='<->', color='#78909C', lw=1.5))
    ax.text((t_set + t_get) / 2, 4.5, 'Δt = 4.5s（系统时间流逝）',
            ha='center', fontsize=8, color='#78909C')

    ax.text(6, 0.1, '图 2-4: Clock 通过 pts_drift 实时推算播放时间',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02-clock.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("✓ 生成 02-clock.png")


# ==========================================
# 图5: Serial 机制工作原理
# ==========================================
def gen_serial():
    fig, ax = plt.subplots(1, 1, figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(6.5, 6.6, 'Serial 机制工作原理（Seek 场景）', ha='center',
            fontsize=16, fontweight='bold', color='#212121')

    # 时间轴
    ax.annotate('', xy=(12.5, 3.5), xytext=(0.5, 3.5),
                arrowprops=dict(arrowstyle='->', color='#424242', lw=2))
    ax.text(12.7, 3.5, '时间', fontsize=9, va='center', color='#424242')

    # Phase 1: 正常播放 (serial=1)
    phase1_x = 1.0
    for i in range(3):
        x = phase1_x + i * 1.2
        box = FancyBboxPatch((x, 3.8), 1.0, 0.6, boxstyle="round,pad=0.05",
                             facecolor=COLORS['secondary'], edgecolor='white', linewidth=1.5, zorder=2)
        ax.add_patch(box)
        ax.text(x + 0.5, 4.1, f'Pkt\ns=1', ha='center', va='center',
                fontsize=7, color='white', fontweight='bold', zorder=3)

    ax.text(2.2, 5.0, '正常播放\nserial=1', ha='center', fontsize=9,
            color=COLORS['secondary'], fontweight='bold')

    # Seek event
    seek_x = 4.8
    ax.plot([seek_x, seek_x], [2.5, 5.5], '--', color=COLORS['red'], lw=2, zorder=1)
    ax.text(seek_x, 5.7, 'SEEK!', ha='center', fontsize=11,
            color=COLORS['red'], fontweight='bold')
    ax.text(seek_x, 2.2, 'flush → serial++\nserial: 1 → 2', ha='center', fontsize=8,
            color=COLORS['red'])

    # Phase 2: seek 后 (serial=2)
    phase2_x = 5.5
    for i in range(4):
        x = phase2_x + i * 1.2
        box = FancyBboxPatch((x, 3.8), 1.0, 0.6, boxstyle="round,pad=0.05",
                             facecolor=COLORS['primary'], edgecolor='white', linewidth=1.5, zorder=2)
        ax.add_patch(box)
        ax.text(x + 0.5, 4.1, f'Pkt\ns=2', ha='center', va='center',
                fontsize=7, color='white', fontweight='bold', zorder=3)

    ax.text(7.9, 5.0, '新数据\nserial=2', ha='center', fontsize=9,
            color=COLORS['primary'], fontweight='bold')

    # 解码器行为
    ax.text(2.2, 1.5, '解码器正常解码\npkt_serial == queue.serial', ha='center',
            fontsize=8, color=COLORS['secondary'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_green'], edgecolor=COLORS['secondary']))

    ax.text(5.5, 1.5, '检测到 serial 变化\n→ avcodec_flush_buffers()\n→ 丢弃旧帧', ha='center',
            fontsize=8, color=COLORS['red'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFEBEE', edgecolor=COLORS['red']))

    ax.text(9.0, 1.5, '解码器用新 serial 解码\n→ 从 seek 位置开始播放', ha='center',
            fontsize=8, color=COLORS['primary'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_blue'], edgecolor=COLORS['primary']))

    # 箭头
    draw_arrow(ax, 2.2, 2.0, 2.2, 3.0, color=COLORS['secondary'], lw=1.2)
    draw_arrow(ax, 5.5, 2.0, 5.5, 3.0, color=COLORS['red'], lw=1.2)
    draw_arrow(ax, 9.0, 2.0, 9.0, 3.0, color=COLORS['primary'], lw=1.2)

    ax.text(6.5, 0.4, '图 2-5: Serial 机制在 Seek 时的工作原理',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02-serial.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("✓ 生成 02-serial.png")


# ==========================================
# 图6: VideoState 成员分组
# ==========================================
def gen_videostate():
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(6, 7.6, 'VideoState 成员分组', ha='center',
            fontsize=16, fontweight='bold', color='#212121')

    groups = [
        ('线程与控制', 'read_tid, abort_request\npaused, seek_req, ic', COLORS['primary'], 0.5, 5.5),
        ('时钟系统', 'audclk, vidclk\nextclk', COLORS['teal'], 4.0, 5.5),
        ('包队列', 'audioq, videoq\nsubtitleq', COLORS['secondary'], 7.5, 5.5),
        ('解码器', 'auddec, viddec\nsubdec', COLORS['purple'], 0.5, 3.5),
        ('帧队列', 'pictq, sampq\nsubpq', COLORS['accent'], 4.0, 3.5),
        ('音频处理', 'audio_buf, swr_ctx\naudio_tgt, audio_src', COLORS['red'], 7.5, 3.5),
        ('视频渲染', 'vid_texture, frame_timer\nsub_convert_ctx', '#795548', 0.5, 1.5),
        ('滤镜系统', 'agraph, in_video_filter\nout_audio_filter', '#00BCD4', 4.0, 1.5),
    ]

    box_w = 3.2
    box_h = 1.5

    for title, members, color, x, y in groups:
        # 外框
        rect = FancyBboxPatch((x, y), box_w, box_h, boxstyle="round,pad=0.1",
                              facecolor='white', edgecolor=color, linewidth=2.5, alpha=0.95, zorder=2)
        ax.add_patch(rect)
        # 标题栏
        title_rect = FancyBboxPatch((x, y + box_h - 0.45), box_w, 0.45,
                                     boxstyle="round,pad=0.05",
                                     facecolor=color, edgecolor=color, linewidth=0, alpha=0.9, zorder=3)
        ax.add_patch(title_rect)
        ax.text(x + box_w/2, y + box_h - 0.22, title, ha='center', va='center',
                fontsize=9, color='white', fontweight='bold', zorder=4)
        # 成员
        ax.text(x + box_w/2, y + (box_h - 0.45)/2, members, ha='center', va='center',
                fontsize=7, color='#424242', zorder=3, linespacing=1.5)

    ax.text(6, 0.4, '图 2-6: VideoState 的 8 大成员分组',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02-videostate.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("✓ 生成 02-videostate.png")


if __name__ == '__main__':
    gen_data_structures_overview()
    gen_packet_queue()
    gen_frame_queue()
    gen_clock()
    gen_serial()
    gen_videostate()
    print("\n第2篇图例全部生成完毕！")
