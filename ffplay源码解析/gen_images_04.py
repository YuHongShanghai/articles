#!/usr/bin/env python3
"""第4篇文章图例：解码核心机制——音视频字幕解码线程"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import os

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    'primary': '#1565C0',
    'green': '#2E7D32',
    'orange': '#E65100',
    'purple': '#6A1B9A',
    'teal': '#00838F',
    'red': '#C62828',
    'grey': '#546E7A',
    'light_grey': '#ECEFF1',
    'yellow': '#F9A825',
    'bg': '#FAFAFA',
    'phase1': '#1565C0',
    'phase2': '#2E7D32',
    'phase3': '#E65100',
}


def draw_box(ax, x, y, w, h, text, color, fontsize=10, text_color='white',
             alpha=0.95, style="round,pad=0.08", lw=1.5, edgecolor='white'):
    box = FancyBboxPatch((x, y), w, h, boxstyle=style,
                         facecolor=color, edgecolor=edgecolor, linewidth=lw,
                         alpha=alpha, zorder=2)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, fontweight='bold', zorder=3)


def draw_outlined_box(ax, x, y, w, h, title, desc, color, title_size=9, desc_size=7.5):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                         facecolor='white', edgecolor=color, linewidth=2.5,
                         alpha=0.95, zorder=2)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h - 0.22, title, ha='center', va='top',
            fontsize=title_size, fontweight='bold', color=color, zorder=3)
    if desc:
        ax.text(x + w / 2, y + h - 0.52, desc, ha='center', va='top',
                fontsize=desc_size, color='#424242', zorder=3)


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw), zorder=1)


def draw_diamond(ax, cx, cy, rx, ry, text, fill_color='#FFF9C4', edge_color='#F9A825',
                 fontsize=8, text_color='#424242'):
    diamond = plt.Polygon(
        [[cx, cy + ry], [cx + rx, cy], [cx, cy - ry], [cx - rx, cy]],
        facecolor=fill_color, edgecolor=edge_color, linewidth=2, zorder=2)
    ax.add_patch(diamond)
    ax.text(cx, cy, text, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color=text_color, zorder=3)


# ==========================================
# 图1: decoder_decode_frame 状态机流程图
# ==========================================
def gen_decoder_decode_frame():
    fig, ax = plt.subplots(1, 1, figsize=(12, 18))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 18)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(6, 17.5, 'decoder_decode_frame() 状态机流程', ha='center',
            fontsize=17, fontweight='bold', color='#212121')

    # ---- Phase 1 区域背景 ----
    phase1_bg = FancyBboxPatch((0.3, 12.0), 11.4, 4.8, boxstyle="round,pad=0.15",
                                facecolor='#E3F2FD', edgecolor='#90CAF9', linewidth=1.5,
                                alpha=0.5, zorder=0)
    ax.add_patch(phase1_bg)
    ax.text(0.8, 16.5, '阶段 1: receive_frame', fontsize=11,
            fontweight='bold', color=COLORS['phase1'], zorder=1)

    # ---- Phase 2 区域背景 ----
    phase2_bg = FancyBboxPatch((0.3, 6.2), 11.4, 5.4, boxstyle="round,pad=0.15",
                                facecolor='#E8F5E9', edgecolor='#A5D6A7', linewidth=1.5,
                                alpha=0.5, zorder=0)
    ax.add_patch(phase2_bg)
    ax.text(0.8, 11.3, '阶段 2: 从 PacketQueue 取包', fontsize=11,
            fontweight='bold', color=COLORS['phase2'], zorder=1)

    # ---- Phase 3 区域背景 ----
    phase3_bg = FancyBboxPatch((0.3, 1.2), 11.4, 4.6, boxstyle="round,pad=0.15",
                                facecolor='#FFF3E0', edgecolor='#FFCC80', linewidth=1.5,
                                alpha=0.5, zorder=0)
    ax.add_patch(phase3_bg)
    ax.text(0.8, 5.5, '阶段 3: send_packet', fontsize=11,
            fontweight='bold', color=COLORS['phase3'], zorder=1)

    cx = 6.0
    bw = 4.0
    bh = 0.85

    # ===== Phase 1 nodes =====
    # Entry
    draw_box(ax, cx - 1.2, 16.0, 2.4, 0.6, 'for (;;) 入口', COLORS['grey'],
             fontsize=9, alpha=0.9)
    draw_arrow(ax, cx, 16.0, cx, 15.65, COLORS['grey'], lw=2)

    # Serial check
    draw_diamond(ax, cx, 15.2, 2.2, 0.45, 'serial 匹配?',
                 fill_color='#E3F2FD', edge_color=COLORS['phase1'], fontsize=9,
                 text_color=COLORS['phase1'])
    draw_arrow(ax, cx, 14.75, cx, 14.3, COLORS['phase1'], lw=2)
    ax.text(cx + 0.15, 14.5, '  是', fontsize=8, color=COLORS['green'])

    # No branch to phase 2
    ax.annotate('', xy=(10.0, 10.6), xytext=(cx + 2.2, 15.2),
                arrowprops=dict(arrowstyle='->', color=COLORS['red'], lw=1.5,
                               connectionstyle='arc3,rad=0.25'))
    ax.text(9.3, 13.3, '否\n(跳过)', fontsize=7.5, color=COLORS['red'],
            ha='center', va='center')

    # receive_frame
    draw_outlined_box(ax, cx - bw / 2, 13.3, bw, bh,
                      'avcodec_receive_frame()', '尝试从解码器取出一帧',
                      COLORS['phase1'])
    draw_arrow(ax, cx, 13.3, cx, 12.95, COLORS['phase1'], lw=2)

    # Return check
    draw_diamond(ax, cx, 12.55, 2.0, 0.4, '返回值?',
                 fill_color='#E3F2FD', edge_color=COLORS['phase1'], fontsize=9,
                 text_color=COLORS['phase1'])

    # ret >= 0 -> return 1
    draw_box(ax, 9.3, 12.95, 2.0, 0.55, 'return 1', COLORS['green'],
             fontsize=9, alpha=0.9)
    ax.annotate('', xy=(9.3, 13.2), xytext=(cx + 2.0, 12.7),
                arrowprops=dict(arrowstyle='->', color=COLORS['green'], lw=1.5))
    ax.text(8.1, 13.1, 'ret>=0', fontsize=7.5, color=COLORS['green'])

    # EOF -> return 0
    draw_box(ax, 9.3, 12.25, 2.0, 0.55, 'return 0', COLORS['red'],
             fontsize=9, alpha=0.9)
    ax.annotate('', xy=(9.3, 12.55), xytext=(cx + 2.0, 12.55),
                arrowprops=dict(arrowstyle='->', color=COLORS['red'], lw=1.5))
    ax.text(8.3, 12.45, 'EOF', fontsize=7.5, color=COLORS['red'])

    # EAGAIN -> phase 2
    draw_arrow(ax, cx, 12.15, cx, 10.6, COLORS['phase2'], lw=2)
    ax.text(cx + 0.15, 11.4, 'EAGAIN', fontsize=8, color=COLORS['orange'])

    # ===== Phase 2 nodes =====
    # empty queue signal
    draw_outlined_box(ax, cx - bw / 2, 9.7, bw, bh,
                      '队列空? 发送 empty_queue_cond',
                      '唤醒 read_thread 填充数据',
                      COLORS['phase2'])
    draw_arrow(ax, cx, 9.7, cx, 9.35, COLORS['phase2'], lw=2)

    # packet_pending check
    draw_diamond(ax, cx, 8.95, 2.2, 0.4, 'packet_pending?',
                 fill_color='#E8F5E9', edge_color=COLORS['phase2'], fontsize=8.5,
                 text_color=COLORS['phase2'])

    # pending -> reuse
    draw_box(ax, 9.3, 8.65, 2.2, 0.55, '复用旧 packet', COLORS['teal'],
             fontsize=8, alpha=0.9)
    ax.annotate('', xy=(9.3, 8.95), xytext=(cx + 2.2, 8.95),
                arrowprops=dict(arrowstyle='->', color=COLORS['teal'], lw=1.5))
    ax.text(8.6, 9.1, '是', fontsize=7.5, color=COLORS['teal'])

    # not pending -> get packet
    draw_arrow(ax, cx, 8.55, cx, 8.2, COLORS['phase2'], lw=2)
    ax.text(cx + 0.15, 8.4, '否', fontsize=7.5, color=COLORS['phase2'])

    draw_outlined_box(ax, cx - bw / 2, 7.3, bw, bh,
                      'packet_queue_get()', '阻塞获取 packet + serial',
                      COLORS['phase2'])
    draw_arrow(ax, cx, 7.3, cx, 6.95, COLORS['phase2'], lw=2)

    # serial change check
    draw_diamond(ax, cx, 6.55, 2.2, 0.4, 'serial 变化?',
                 fill_color='#E8F5E9', edge_color=COLORS['phase2'], fontsize=8.5,
                 text_color=COLORS['phase2'])

    draw_box(ax, 0.8, 6.3, 2.5, 0.55, 'flush 解码器\n重置状态', COLORS['red'],
             fontsize=8, alpha=0.85)
    ax.annotate('', xy=(3.3, 6.55), xytext=(cx - 2.2, 6.55),
                arrowprops=dict(arrowstyle='->', color=COLORS['red'], lw=1.5))
    ax.text(3.4, 6.75, '是', fontsize=7.5, color=COLORS['red'])

    # Down to phase 3
    draw_arrow(ax, cx, 6.15, cx, 5.1, COLORS['phase3'], lw=2)

    # ===== Phase 3 nodes =====
    # Subtitle vs Audio/Video
    draw_diamond(ax, cx, 4.7, 2.2, 0.4, '媒体类型?',
                 fill_color='#FFF3E0', edge_color=COLORS['phase3'], fontsize=9,
                 text_color=COLORS['phase3'])

    # Subtitle path (left)
    draw_outlined_box(ax, 0.8, 3.4, 3.8, bh,
                      'avcodec_decode_subtitle2()',
                      '字幕: 旧 API 同步解码',
                      COLORS['purple'])
    ax.annotate('', xy=(2.7, 4.25), xytext=(cx - 2.2, 4.7),
                arrowprops=dict(arrowstyle='->', color=COLORS['purple'], lw=1.5))
    ax.text(2.0, 4.7, '字幕', fontsize=8, color=COLORS['purple'])

    # Audio/Video path (right)
    draw_outlined_box(ax, 7.4, 3.4, 3.8, bh,
                      'avcodec_send_packet()',
                      '音视频: 设置 opaque_ref 后发送',
                      COLORS['phase3'])
    ax.annotate('', xy=(9.3, 4.25), xytext=(cx + 2.2, 4.7),
                arrowprops=dict(arrowstyle='->', color=COLORS['phase3'], lw=1.5))
    ax.text(8.5, 4.7, '音/视频', fontsize=8, color=COLORS['phase3'])

    # EAGAIN handling
    draw_box(ax, 8.0, 2.3, 2.6, 0.6, 'EAGAIN?\npacket_pending=1', '#FF8F00',
             fontsize=7.5, alpha=0.85)
    draw_arrow(ax, 9.3, 3.4, 9.3, 2.9, '#FF8F00', lw=1.5)

    # subtitle result
    draw_box(ax, 1.1, 2.3, 3.2, 0.6, 'got_frame?\nreturn 0 / EAGAIN / EOF', COLORS['purple'],
             fontsize=7.5, alpha=0.85)
    draw_arrow(ax, 2.7, 3.4, 2.7, 2.9, COLORS['purple'], lw=1.5)

    # Loop back arrow (both paths loop back to phase 1)
    ax.annotate('',
                xy=(0.55, 16.0),
                xytext=(0.55, 2.5),
                arrowprops=dict(arrowstyle='->', color='#78909C', lw=2.5,
                               connectionstyle='arc3,rad=0'))
    ax.text(0.15, 9.5, '循\n环', fontsize=10, color='#78909C', fontweight='bold',
            ha='center', va='center', linespacing=1.5)

    ax.text(6, 0.5, '图 4-1: decoder_decode_frame() 三阶段状态机',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '04-decoder-decode-frame.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 04-decoder-decode-frame.png")


# ==========================================
# 图2: 三个解码线程与队列关系图
# ==========================================
def gen_three_decode_threads():
    fig, ax = plt.subplots(1, 1, figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7, 8.5, '三个解码线程与队列关系', ha='center',
            fontsize=17, fontweight='bold', color='#212121')

    # ---- 左侧: PacketQueue 列 ----
    pq_x = 0.5
    pq_w = 2.2
    pq_h = 1.2

    draw_box(ax, pq_x, 6.2, pq_w, pq_h, 'videoq\n(PacketQueue)', COLORS['orange'],
             fontsize=10)
    draw_box(ax, pq_x, 4.2, pq_w, pq_h, 'audioq\n(PacketQueue)', COLORS['purple'],
             fontsize=10)
    draw_box(ax, pq_x, 2.2, pq_w, pq_h, 'subtitleq\n(PacketQueue)', COLORS['teal'],
             fontsize=10)

    # ---- 中间: 解码线程 ----
    dt_x = 4.2
    dt_w = 3.0
    dt_h = 1.2

    # Video thread
    vt_bg = FancyBboxPatch((dt_x - 0.15, 6.05), dt_w + 0.3, dt_h + 0.3,
                            boxstyle="round,pad=0.1",
                            facecolor='#FFF3E0', edgecolor='#FFB74D',
                            linewidth=1.5, alpha=0.5, zorder=1)
    ax.add_patch(vt_bg)
    draw_box(ax, dt_x, 6.2, dt_w, dt_h,
             'video_thread\n\ndecoder_decode_frame()\n+ 滤镜 + 丢帧判断',
             COLORS['orange'], fontsize=8.5, alpha=0.95)

    # Audio thread
    at_bg = FancyBboxPatch((dt_x - 0.15, 4.05), dt_w + 0.3, dt_h + 0.3,
                            boxstyle="round,pad=0.1",
                            facecolor='#F3E5F5', edgecolor='#CE93D8',
                            linewidth=1.5, alpha=0.5, zorder=1)
    ax.add_patch(at_bg)
    draw_box(ax, dt_x, 4.2, dt_w, dt_h,
             'audio_thread\n\ndecoder_decode_frame()\n+ 格式检测 + 滤镜',
             COLORS['purple'], fontsize=8.5, alpha=0.95)

    # Subtitle thread
    st_bg = FancyBboxPatch((dt_x - 0.15, 2.05), dt_w + 0.3, dt_h + 0.3,
                            boxstyle="round,pad=0.1",
                            facecolor='#E0F7FA', edgecolor='#80DEEA',
                            linewidth=1.5, alpha=0.5, zorder=1)
    ax.add_patch(st_bg)
    draw_box(ax, dt_x, 2.2, dt_w, dt_h,
             'subtitle_thread\n\ndecoder_decode_frame()\n(旧 API, 无滤镜)',
             COLORS['teal'], fontsize=8.5, alpha=0.95)

    # ---- 右侧: FrameQueue 列 ----
    fq_x = 8.8
    fq_w = 2.2
    fq_h = 1.2

    draw_box(ax, fq_x, 6.2, fq_w, fq_h, 'pictq\n(FrameQueue)', COLORS['orange'],
             fontsize=10)
    draw_box(ax, fq_x, 4.2, fq_w, fq_h, 'sampq\n(FrameQueue)', COLORS['purple'],
             fontsize=10)
    draw_box(ax, fq_x, 2.2, fq_w, fq_h, 'subpq\n(FrameQueue)', COLORS['teal'],
             fontsize=10)

    # ---- 最右侧: 消费者 ----
    cs_x = 12.0
    cs_w = 1.5
    cs_h = 1.0

    draw_box(ax, cs_x, 6.3, cs_w, cs_h, '视频\n渲染', '#D84315', fontsize=9, alpha=0.85)
    draw_box(ax, cs_x, 4.3, cs_w, cs_h, 'SDL\n音频', '#4A148C', fontsize=9, alpha=0.85)
    draw_box(ax, cs_x, 2.3, cs_w, cs_h, '字幕\n叠加', '#004D40', fontsize=9, alpha=0.85)

    # ---- 箭头: PacketQueue -> 线程 ----
    for y in [6.8, 4.8, 2.8]:
        draw_arrow(ax, pq_x + pq_w, y, dt_x, y, '#455A64', lw=2)

    # ---- 箭头: 线程 -> FrameQueue ----
    for y in [6.8, 4.8, 2.8]:
        draw_arrow(ax, dt_x + dt_w, y, fq_x, y, '#455A64', lw=2)

    # ---- 箭头: FrameQueue -> 消费者 ----
    for y in [6.8, 4.8, 2.8]:
        draw_arrow(ax, fq_x + fq_w, y, cs_x, y, '#455A64', lw=2)

    # ---- 列标签 ----
    ax.text(pq_x + pq_w / 2, 7.8, '压缩数据 (Packet)', ha='center',
            fontsize=10, fontweight='bold', color='#455A64')
    ax.text(dt_x + dt_w / 2, 7.8, '解码线程', ha='center',
            fontsize=10, fontweight='bold', color='#455A64')
    ax.text(fq_x + fq_w / 2, 7.8, '解码数据 (Frame)', ha='center',
            fontsize=10, fontweight='bold', color='#455A64')
    ax.text(cs_x + cs_w / 2, 7.8, '输出', ha='center',
            fontsize=10, fontweight='bold', color='#455A64')

    # ---- 箭头标签 ----
    ax.text(3.3, 7.05, 'AVPacket', fontsize=7.5, color='#78909C', ha='center',
            style='italic')
    ax.text(3.3, 5.05, 'AVPacket', fontsize=7.5, color='#78909C', ha='center',
            style='italic')
    ax.text(3.3, 3.05, 'AVPacket', fontsize=7.5, color='#78909C', ha='center',
            style='italic')

    ax.text(8.0, 7.05, 'AVFrame', fontsize=7.5, color='#78909C', ha='center',
            style='italic')
    ax.text(8.0, 5.05, 'AVFrame', fontsize=7.5, color='#78909C', ha='center',
            style='italic')
    ax.text(8.0, 3.05, 'AVSubtitle', fontsize=7.5, color='#78909C', ha='center',
            style='italic')

    # ---- read_thread 标注 ----
    draw_box(ax, pq_x - 0.2, 0.5, 2.6, 0.8, 'read_thread\n(数据源)', COLORS['grey'],
             fontsize=9, alpha=0.85)
    for ty in [2.8, 4.8, 6.8]:
        ax.annotate('', xy=(pq_x, ty - 0.6), xytext=(pq_x + 1.1, 1.3),
                    arrowprops=dict(arrowstyle='->', color='#90A4AE', lw=1.2,
                                   connectionstyle='arc3,rad=-0.15'))

    # ---- 底部共享核心标注 ----
    share_box = FancyBboxPatch((3.8, 0.3), 7.5, 1.0, boxstyle="round,pad=0.1",
                                facecolor='#ECEFF1', edgecolor='#B0BEC5',
                                linewidth=1.5, alpha=0.8, zorder=1)
    ax.add_patch(share_box)
    ax.text(7.55, 0.8, '三个线程共享核心: decoder_decode_frame()\nserial 同步  |  packet_pending 重试  |  opaque_ref 数据透传',
            ha='center', va='center', fontsize=9, color='#37474F', zorder=2)

    ax.text(7, -0.15, '图 4-2: 三个解码线程与队列关系',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '04-three-decode-threads.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 04-three-decode-threads.png")


if __name__ == '__main__':
    gen_decoder_decode_frame()
    gen_three_decode_threads()
    print("\n04 done!")
