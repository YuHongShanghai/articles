#!/usr/bin/env python3
"""
为 06-FFmpeg核心数据结构详解.md 生成配图
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib
import os

matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

COLORS = {
    'primary':    '#2563EB',
    'secondary':  '#7C3AED',
    'accent':     '#F59E0B',
    'success':    '#10B981',
    'danger':     '#EF4444',
    'pink':       '#EC4899',
    'cyan':       '#06B6D4',
    'bg':         '#F8FAFC',
    'grid':       '#E2E8F0',
    'text':       '#1E293B',
    'text_light': '#64748B',
    'white':      '#FFFFFF',
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')
DPI = 150


def draw_box(ax, x, y, w, h, label, color, sublabel=None, alpha=0.85, fontsize=11, mono=False):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                           facecolor=color, edgecolor='white', linewidth=2.5, alpha=alpha)
    ax.add_patch(rect)
    family = 'monospace' if mono else None
    if sublabel:
        ax.text(x + w / 2, y + h / 2 + 0.15, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white', family=family)
        ax.text(x + w / 2, y + h / 2 - 0.2, sublabel, ha='center', va='center',
                fontsize=fontsize - 2, color='white', alpha=0.85)
    else:
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white', family=family)


def draw_arrow(ax, x1, y1, x2, y2, color=None, lw=2, style='->', rad=0):
    if color is None:
        color = COLORS['text_light']
    cs = f'arc3,rad={rad}' if rad else 'arc3,rad=0'
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, connectionstyle=cs))


def draw_label(ax, x, y, text, color, fontsize=9):
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            color=color, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor=color, alpha=0.1,
                      edgecolor=color, linewidth=0.8))


# ============================================================
# 图1：核心数据结构全景图
# ============================================================
def gen_data_structures():
    fig, ax = plt.subplots(figsize=(15, 12))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-1, 16)
    ax.set_ylim(-1.5, 13)
    ax.set_title('FFmpeg 核心数据结构全景关系图', fontsize=17,
                 fontweight='bold', color=COLORS['text'], pad=18)

    # === AVFormatContext 大框 ===
    outer = FancyBboxPatch((0.5, 8.0), 14, 4.2, boxstyle="round,pad=0.12",
                            facecolor=COLORS['accent'], alpha=0.07,
                            edgecolor=COLORS['accent'], linewidth=2.5)
    ax.add_patch(outer)
    ax.text(7.5, 11.85, 'AVFormatContext', fontsize=15, fontweight='bold',
            color=COLORS['accent'], ha='center', family='monospace')
    ax.text(7.5, 11.45, '封装格式上下文 — 一切的起点', fontsize=10,
            color=COLORS['text_light'], ha='center')

    # 左侧字段
    fields_left = ['url: "video.mp4"', 'nb_streams: 2', 'duration, bit_rate']
    for i, f in enumerate(fields_left):
        ax.text(1.3, 10.8 - i * 0.4, f, fontsize=9, color=COLORS['accent'],
                family='monospace')

    # AVStream[0] 视频
    vs_rect = FancyBboxPatch((5.5, 8.5), 4.0, 2.5, boxstyle="round,pad=0.06",
                              facecolor=COLORS['primary'], alpha=0.1,
                              edgecolor=COLORS['primary'], linewidth=1.5)
    ax.add_patch(vs_rect)
    ax.text(7.5, 10.65, 'AVStream[0]  视频流', fontsize=11, fontweight='bold',
            color=COLORS['primary'], ha='center')
    stream_fields = ['index = 0', 'time_base = 1/12288', 'codecpar → ...']
    for i, f in enumerate(stream_fields):
        ax.text(6.0, 10.1 - i * 0.4, f, fontsize=9, color=COLORS['primary'],
                family='monospace')

    # AVStream[1] 音频
    as_rect = FancyBboxPatch((10.0, 8.5), 4.0, 2.5, boxstyle="round,pad=0.06",
                              facecolor=COLORS['danger'], alpha=0.1,
                              edgecolor=COLORS['danger'], linewidth=1.5)
    ax.add_patch(as_rect)
    ax.text(12.0, 10.65, 'AVStream[1]  音频流', fontsize=11, fontweight='bold',
            color=COLORS['danger'], ha='center')
    stream_fields_a = ['index = 1', 'time_base = 1/48000', 'codecpar → ...']
    for i, f in enumerate(stream_fields_a):
        ax.text(10.5, 10.1 - i * 0.4, f, fontsize=9, color=COLORS['danger'],
                family='monospace')

    # === AVCodecParameters ===
    draw_arrow(ax, 7.5, 8.5, 7.5, 7.6, COLORS['primary'], lw=2)
    draw_label(ax, 5.0, 7.9, 'codecpar', COLORS['primary'], fontsize=9)

    draw_box(ax, 5.0, 6.5, 5.0, 1.0, 'AVCodecParameters', COLORS['success'],
             sublabel='编解码参数（codec_id, width, height, sample_rate...）', fontsize=11)

    # === AVCodec ===
    draw_arrow(ax, 7.5, 6.5, 7.5, 5.8, COLORS['success'], lw=2)
    draw_label(ax, 3.5, 6.1, 'avcodec_find_decoder()', COLORS['success'], fontsize=8)

    draw_box(ax, 5.5, 4.7, 4.0, 1.0, 'AVCodec', COLORS['text_light'],
             sublabel='解码器描述（"h264", "aac"...）', fontsize=11)

    # === AVCodecContext ===
    draw_arrow(ax, 7.5, 4.7, 7.5, 4.0, COLORS['secondary'], lw=2)
    draw_label(ax, 3.0, 4.35, 'alloc + params_to_context + open2', COLORS['secondary'], fontsize=8)

    draw_box(ax, 4.5, 2.8, 6.0, 1.1, 'AVCodecContext', COLORS['secondary'],
             sublabel='解码器上下文（运行时状态）', fontsize=12)

    # === AVPacket → AVFrame ===
    draw_arrow(ax, 7.5, 2.8, 7.5, 2.2, COLORS['secondary'], lw=2)
    draw_label(ax, 3.8, 2.5, 'send_packet / receive_frame', COLORS['secondary'], fontsize=8)

    # AVPacket
    draw_box(ax, 2.0, 0.5, 4.5, 1.2, 'AVPacket', COLORS['cyan'],
             sublabel='压缩数据包（pts, dts, data, size）', fontsize=11)

    # 箭头
    draw_arrow(ax, 6.5, 1.1, 8.5, 1.1, COLORS['text'], lw=2.5)
    ax.text(7.5, 1.5, '解码', fontsize=11, ha='center', fontweight='bold',
            color=COLORS['text'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['accent'], alpha=0.15))

    # AVFrame
    draw_box(ax, 8.5, 0.5, 5.0, 1.2, 'AVFrame', COLORS['pink'],
             sublabel='原始数据帧（YUV/RGB 或 PCM）', fontsize=11)

    # === 右侧流程注解 ===
    steps = [
        (12.2, 11.0, '① 打开文件', 'avformat_open_input()', COLORS['accent']),
        (12.2, 7.0, '② 获取流信息', 'avformat_find_stream_info()', COLORS['success']),
        (12.2, 3.3, '③ 打开解码器', 'avcodec_open2()', COLORS['secondary']),
        (12.2, 1.1, '④ 读包+解码', 'av_read_frame() → decode', COLORS['pink']),
    ]
    # 连接线（右侧虚线）
    for i in range(len(steps)):
        sy = steps[i][1]
        ax.plot(14.8, sy, 'o', color=steps[i][4], markersize=8, zorder=5)
        ax.text(14.8, sy, str(i + 1), ha='center', va='center', fontsize=7,
                color='white', fontweight='bold', zorder=6)
    for i in range(len(steps) - 1):
        ax.plot([14.8, 14.8], [steps[i][1] - 0.3, steps[i + 1][1] + 0.3],
                color=COLORS['grid'], lw=1.5, linestyle='--', zorder=1)

    # === 底部说明 ===
    ax.text(7.5, -0.5, 'AVPacket 和 AVFrame 均使用引用计数管理内存，避免不必要的数据拷贝',
            ha='center', fontsize=10, color=COLORS['text_light'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['grid'], alpha=0.3))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-06-data-structures.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-06-data-structures.png')


# ============================================================
# 图2：AVFrame data/linesize 内存布局
# ============================================================
def gen_avframe_layout():
    fig, axes = plt.subplots(1, 2, figsize=(15, 6),
                              gridspec_kw={'width_ratios': [1.2, 1]})
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('AVFrame 的 data[] 与 linesize[] 内存布局', fontsize=16,
                 fontweight='bold', color=COLORS['text'], y=1.0)

    # === 左：YUV420P 视频帧 ===
    ax = axes[0]
    ax.axis('off')
    ax.set_xlim(-0.5, 11)
    ax.set_ylim(-2.5, 6)
    ax.set_title('视频帧（YUV420P）', fontsize=13, fontweight='bold',
                 color=COLORS['text'], pad=10)

    # Y 平面
    y_w, y_h = 6.0, 2.5
    y_rect = FancyBboxPatch((0, 3.0), y_w, y_h, boxstyle="round,pad=0.04",
                             facecolor=COLORS['text'], alpha=0.15,
                             edgecolor=COLORS['text'], linewidth=1.5)
    ax.add_patch(y_rect)

    # 有效数据区
    eff_w = 4.8
    eff_rect = plt.Rectangle((0.1, 3.1), eff_w, y_h - 0.2,
                               facecolor=COLORS['primary'], alpha=0.3, edgecolor='none')
    ax.add_patch(eff_rect)
    # padding 区
    pad_rect = plt.Rectangle((0.1 + eff_w, 3.1), y_w - eff_w - 0.2, y_h - 0.2,
                               facecolor=COLORS['danger'], alpha=0.15, edgecolor='none',
                               hatch='///')
    ax.add_patch(pad_rect)

    ax.text(0.1 + eff_w / 2, 4.3, 'data[0] → Y 有效数据\n(width 字节)', ha='center',
            fontsize=9, color=COLORS['primary'], fontweight='bold')
    ax.text(0.1 + eff_w + (y_w - eff_w - 0.2) / 2, 4.3, '对齐\n填充', ha='center',
            fontsize=8, color=COLORS['danger'])

    # linesize 标注
    ax.annotate('', xy=(y_w, 5.7), xytext=(0, 5.7),
                arrowprops=dict(arrowstyle='<->', color=COLORS['text'], lw=1.5))
    ax.text(y_w / 2, 5.95, 'linesize[0]（每行总字节数，含 padding）',
            ha='center', fontsize=9, color=COLORS['text'], fontweight='bold')

    ax.annotate('', xy=(eff_w, 3.0 - 0.15), xytext=(0, 3.0 - 0.15),
                arrowprops=dict(arrowstyle='<->', color=COLORS['primary'], lw=1.2))
    ax.text(eff_w / 2, 2.6, 'width', ha='center', fontsize=9,
            color=COLORS['primary'], fontweight='bold')

    # U/V 平面
    uv_w, uv_h = 3.0, 1.2
    for i, (label, color, desc) in enumerate([
        ('data[1] → U', COLORS['primary'], 'U 平面'),
        ('data[2] → V', COLORS['danger'], 'V 平面'),
    ]):
        ux = i * (uv_w + 0.5)
        uy = 0.5
        uv_rect = FancyBboxPatch((ux, uy), uv_w, uv_h, boxstyle="round,pad=0.03",
                                  facecolor=color, alpha=0.2,
                                  edgecolor=color, linewidth=1.5)
        ax.add_patch(uv_rect)
        ax.text(ux + uv_w / 2, uy + uv_h / 2, f'{label}\n(width/2 × height/2)',
                ha='center', va='center', fontsize=8, color=color, fontweight='bold')

    # 说明
    ax.text(5.5, -0.3, 'linesize 可能 > width（内存对齐）\n拷贝时不能直接用 width×height！',
            ha='center', fontsize=9, color=COLORS['danger'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['danger'], alpha=0.08))

    # === 右：音频帧 ===
    ax = axes[1]
    ax.axis('off')
    ax.set_xlim(-0.5, 8)
    ax.set_ylim(-2.5, 6)
    ax.set_title('音频帧（Planar vs Interleaved）', fontsize=13,
                 fontweight='bold', color=COLORS['text'], pad=10)

    # Planar 格式
    ax.text(3.5, 5.5, 'Planar（如 FLTP）', fontsize=11, fontweight='bold',
            color=COLORS['secondary'], ha='center')

    draw_box(ax, 0, 4.2, 7, 0.8, 'data[0] → 左声道  [L0][L1][L2][L3]...',
             COLORS['primary'], fontsize=9)
    draw_box(ax, 0, 3.1, 7, 0.8, 'data[1] → 右声道  [R0][R1][R2][R3]...',
             COLORS['danger'], fontsize=9)

    # Interleaved 格式
    ax.text(3.5, 2.3, 'Interleaved（如 S16）', fontsize=11, fontweight='bold',
            color=COLORS['accent'], ha='center')

    draw_box(ax, 0, 1.0, 7, 0.8, 'data[0] → [L0][R0][L1][R1][L2][R2]...',
             COLORS['accent'], fontsize=9)
    ax.text(3.5, 0.6, '所有声道交错排列在 data[0] 中', fontsize=8,
            ha='center', color=COLORS['text_light'])

    # nb_samples 标注
    ax.text(3.5, -0.5, 'nb_samples = 该帧的采样点数\nsample_rate = 采样率',
            ha='center', fontsize=9, color=COLORS['text_light'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['grid'], alpha=0.3))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-06-avframe-layout.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-06-avframe-layout.png')


# ============================================================
# 图3：引用计数机制
# ============================================================
def gen_refcount():
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 13)
    ax.set_ylim(-1, 5.5)
    ax.set_title('AVPacket / AVFrame 引用计数内存管理', fontsize=16,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 三个阶段
    stages = [
        (0.3, '① 创建', 'ref_count = 1'),
        (4.5, '② av_packet_ref()', 'ref_count = 2'),
        (8.8, '③ av_packet_unref(B)', 'ref_count = 1'),
    ]

    for sx, title, rc in stages:
        # 阶段标题
        ax.text(sx + 1.8, 5.0, title, fontsize=11, fontweight='bold',
                color=COLORS['text'], ha='center')

    # === 阶段1 ===
    sx = 0.3
    # 数据缓冲区
    buf1 = FancyBboxPatch((sx + 0.5, 2.5), 2.6, 1.2, boxstyle="round,pad=0.05",
                           facecolor=COLORS['success'], alpha=0.2,
                           edgecolor=COLORS['success'], linewidth=2)
    ax.add_patch(buf1)
    ax.text(sx + 1.8, 3.3, '数据缓冲区', fontsize=9, ha='center',
            color=COLORS['success'], fontweight='bold')
    ax.text(sx + 1.8, 2.85, 'ref_count = 1', fontsize=9, ha='center',
            color=COLORS['success'], family='monospace')

    # Packet A
    draw_box(ax, sx + 0.8, 0.5, 2.0, 0.8, 'Packet A', COLORS['cyan'], fontsize=10)
    draw_arrow(ax, sx + 1.8, 1.3, sx + 1.8, 2.5, COLORS['cyan'], lw=1.5)

    # === 阶段2 ===
    sx = 4.5
    buf2 = FancyBboxPatch((sx + 0.5, 2.5), 2.6, 1.2, boxstyle="round,pad=0.05",
                           facecolor=COLORS['success'], alpha=0.2,
                           edgecolor=COLORS['success'], linewidth=2)
    ax.add_patch(buf2)
    ax.text(sx + 1.8, 3.3, '数据缓冲区', fontsize=9, ha='center',
            color=COLORS['success'], fontweight='bold')
    ax.text(sx + 1.8, 2.85, 'ref_count = 2', fontsize=9, ha='center',
            color=COLORS['danger'], family='monospace', fontweight='bold')

    draw_box(ax, sx, 0.5, 1.6, 0.8, 'Packet A', COLORS['cyan'], fontsize=9)
    draw_box(ax, sx + 2.0, 0.5, 1.6, 0.8, 'Packet B', COLORS['secondary'], fontsize=9)
    draw_arrow(ax, sx + 0.8, 1.3, sx + 1.4, 2.5, COLORS['cyan'], lw=1.5)
    draw_arrow(ax, sx + 2.8, 1.3, sx + 2.2, 2.5, COLORS['secondary'], lw=1.5)

    ax.text(sx + 1.8, 4.2, '共享同一数据\n无需拷贝', fontsize=9, ha='center',
            color=COLORS['text_light'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['accent'], alpha=0.1))

    # === 阶段3 ===
    sx = 8.8
    buf3 = FancyBboxPatch((sx + 0.5, 2.5), 2.6, 1.2, boxstyle="round,pad=0.05",
                           facecolor=COLORS['success'], alpha=0.2,
                           edgecolor=COLORS['success'], linewidth=2)
    ax.add_patch(buf3)
    ax.text(sx + 1.8, 3.3, '数据缓冲区', fontsize=9, ha='center',
            color=COLORS['success'], fontweight='bold')
    ax.text(sx + 1.8, 2.85, 'ref_count = 1', fontsize=9, ha='center',
            color=COLORS['success'], family='monospace')

    draw_box(ax, sx + 0.8, 0.5, 2.0, 0.8, 'Packet A', COLORS['cyan'], fontsize=10)
    draw_arrow(ax, sx + 1.8, 1.3, sx + 1.8, 2.5, COLORS['cyan'], lw=1.5)

    # B 已释放
    ax.text(sx + 3.5, 0.9, 'B 已释放\n(unref)', fontsize=9, ha='center',
            color=COLORS['text_light'], fontstyle='italic')

    # 底部说明
    ax.text(6.5, -0.5,
            'ref_count 降为 0 时自动释放数据  |  av_packet_ref() 共享  |  av_packet_move_ref() 转移所有权',
            ha='center', fontsize=9, color=COLORS['text_light'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['grid'], alpha=0.3))

    # 阶段间箭头
    ax.annotate('', xy=(4.3, 1.8), xytext=(3.5, 1.8),
                arrowprops=dict(arrowstyle='->', color=COLORS['text_light'], lw=2))
    ax.annotate('', xy=(8.6, 1.8), xytext=(7.8, 1.8),
                arrowprops=dict(arrowstyle='->', color=COLORS['text_light'], lw=2))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-06-refcount.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-06-refcount.png')


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print('开始生成第 6 章配图...\n')
    gen_data_structures()
    gen_avframe_layout()
    gen_refcount()
    print('\n全部完成！')
