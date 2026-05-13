#!/usr/bin/env python3
"""第10篇文章图例：AVFilter 滤镜系统"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches
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
    'yellow': '#FFF9C4',
    'bg': '#FAFAFA',
    'light_blue': '#E3F2FD',
    'light_green': '#E8F5E9',
    'light_orange': '#FFF3E0',
    'light_purple': '#F3E5F5',
    'light_red': '#FFEBEE',
    'dark': '#263238',
    'amber': '#FF8F00',
    'pink': '#AD1457',
    'indigo': '#283593',
}


def draw_box(ax, x, y, w, h, text, color, fontsize=10, text_color='white',
             alpha=0.95, edgecolor=None, linewidth=1.5):
    ec = edgecolor if edgecolor else 'white'
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                         facecolor=color, edgecolor=ec, linewidth=linewidth,
                         alpha=alpha, zorder=2)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, fontweight='bold', zorder=3)


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw), zorder=1)


def draw_label_box(ax, x, y, w, h, title, desc, color, title_size=9, desc_size=7):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                         facecolor='white', edgecolor=color,
                         linewidth=2.5, alpha=0.95, zorder=2)
    ax.add_patch(box)
    ax.text(x + 0.15, y + h - 0.15, title, fontsize=title_size,
            fontweight='bold', color=color, va='top', zorder=3)
    if desc:
        ax.text(x + 0.15, y + h - 0.45, desc, fontsize=desc_size,
                color='#424242', va='top', zorder=3)


# ==========================================
# 图1: AVFilter 滤镜链拓扑图
# ==========================================
def gen_filter_chain():
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7.5, 9.5, 'AVFilter 滤镜链拓扑图', ha='center',
            fontsize=18, fontweight='bold', color='#212121')

    # ================================================================
    # 上半部分：视频滤镜链
    # ================================================================
    ax.text(7.5, 8.8, '视频滤镜链 (configure_video_filters)', ha='center',
            fontsize=12, fontweight='bold', color=COLORS['primary'])

    video_region = FancyBboxPatch((0.3, 5.7), 14.4, 3.2,
                                  boxstyle="round,pad=0.15", facecolor=COLORS['light_blue'],
                                  edgecolor=COLORS['primary'], linewidth=2,
                                  alpha=0.3, zorder=0)
    ax.add_patch(video_region)

    # 解码器
    draw_box(ax, 0.6, 7.1, 1.6, 0.7, '视频解码器', COLORS['grey'], fontsize=9)

    # buffersrc
    draw_box(ax, 2.8, 6.9, 2.0, 1.1, 'buffersrc\n(buffer)', COLORS['green'], fontsize=9)
    draw_arrow(ax, 2.2, 7.45, 2.8, 7.45, color=COLORS['green'], lw=2)

    # buffersrc 参数标注
    src_params = [
        'video_size, pix_fmt',
        'time_base, pixel_aspect',
        'colorspace, range',
        'frame_rate',
    ]
    for i, p in enumerate(src_params):
        ax.text(3.8, 6.7 - i * 0.28, p, fontsize=6.5,
                color=COLORS['green'], ha='center', style='italic')

    # autorotate 滤镜组
    auto_x = 5.4
    auto_region = FancyBboxPatch((auto_x, 6.5), 2.6, 1.6,
                                  boxstyle="round,pad=0.08", facecolor='white',
                                  edgecolor=COLORS['orange'], linewidth=2,
                                  linestyle='--', alpha=0.8, zorder=1)
    ax.add_patch(auto_region)
    ax.text(auto_x + 1.3, 8.0, 'autorotate', fontsize=8,
            fontweight='bold', color=COLORS['orange'], ha='center')

    draw_box(ax, auto_x + 0.2, 7.15, 2.2, 0.55, 'transpose / rotate', COLORS['orange'], fontsize=8)
    draw_box(ax, auto_x + 0.2, 6.55, 2.2, 0.5, 'hflip / vflip', COLORS['orange'], fontsize=8,
             alpha=0.7)

    draw_arrow(ax, 4.8, 7.45, auto_x + 0.2, 7.42, color=COLORS['orange'], lw=2)

    # 用户滤镜组
    usr_x = 8.5
    usr_region = FancyBboxPatch((usr_x, 6.5), 2.4, 1.6,
                                 boxstyle="round,pad=0.08", facecolor='white',
                                 edgecolor=COLORS['purple'], linewidth=2,
                                 linestyle='--', alpha=0.8, zorder=1)
    ax.add_patch(usr_region)
    ax.text(usr_x + 1.2, 8.0, '-vf 用户滤镜', fontsize=8,
            fontweight='bold', color=COLORS['purple'], ha='center')

    draw_box(ax, usr_x + 0.15, 7.15, 2.1, 0.55, 'scale, crop ...', COLORS['purple'], fontsize=8)
    draw_box(ax, usr_x + 0.15, 6.55, 2.1, 0.5, 'drawtext ...', COLORS['purple'], fontsize=8,
             alpha=0.7)

    draw_arrow(ax, auto_x + 2.4, 7.42, usr_x + 0.15, 7.42, color=COLORS['purple'], lw=2)

    # buffersink
    draw_box(ax, 11.4, 6.9, 2.0, 1.1, 'buffersink\n(buffersink)', COLORS['red'], fontsize=9)
    draw_arrow(ax, usr_x + 2.25, 7.42, 11.4, 7.45, color=COLORS['red'], lw=2)

    # buffersink 参数标注
    sink_params = [
        'pix_fmts (SDL)',
        'color_spaces',
    ]
    for i, p in enumerate(sink_params):
        ax.text(12.4, 6.7 - i * 0.28, p, fontsize=6.5,
                color=COLORS['red'], ha='center', style='italic')

    # 渲染
    draw_box(ax, 13.8, 7.1, 0.9, 0.7, 'SDL\n渲染', COLORS['dark'], fontsize=8)
    draw_arrow(ax, 13.4, 7.45, 13.8, 7.45, color=COLORS['dark'], lw=2)

    # ================================================================
    # 下半部分：音频滤镜链
    # ================================================================
    ax.text(7.5, 5.1, '音频滤镜链 (configure_audio_filters)', ha='center',
            fontsize=12, fontweight='bold', color=COLORS['teal'])

    audio_region = FancyBboxPatch((0.3, 2.0), 14.4, 3.2,
                                  boxstyle="round,pad=0.15", facecolor=COLORS['light_green'],
                                  edgecolor=COLORS['teal'], linewidth=2,
                                  alpha=0.3, zorder=0)
    ax.add_patch(audio_region)

    # 解码器
    draw_box(ax, 0.6, 3.4, 1.6, 0.7, '音频解码器', COLORS['grey'], fontsize=9)

    # abuffer
    draw_box(ax, 2.8, 3.2, 2.0, 1.1, 'abuffer\n(abuffer)', COLORS['green'], fontsize=9)
    draw_arrow(ax, 2.2, 3.75, 2.8, 3.75, color=COLORS['green'], lw=2)

    # abuffer 参数标注
    asrc_params = [
        'sample_rate, sample_fmt',
        'time_base',
        'channel_layout',
    ]
    for i, p in enumerate(asrc_params):
        ax.text(3.8, 3.0 - i * 0.28, p, fontsize=6.5,
                color=COLORS['green'], ha='center', style='italic')

    # 用户音频滤镜
    af_x = 5.8
    af_region = FancyBboxPatch((af_x, 2.8), 3.6, 1.6,
                                boxstyle="round,pad=0.08", facecolor='white',
                                edgecolor=COLORS['purple'], linewidth=2,
                                linestyle='--', alpha=0.8, zorder=1)
    ax.add_patch(af_region)
    ax.text(af_x + 1.8, 4.3, '-af 用户滤镜', fontsize=8,
            fontweight='bold', color=COLORS['purple'], ha='center')

    draw_box(ax, af_x + 0.15, 3.4, 1.5, 0.55, 'volume', COLORS['purple'], fontsize=8)
    draw_box(ax, af_x + 1.9, 3.4, 1.5, 0.55, 'equalizer', COLORS['purple'], fontsize=8)
    draw_box(ax, af_x + 0.6, 2.85, 2.3, 0.45, 'aecho, atempo ...', COLORS['purple'],
             fontsize=7, alpha=0.7)

    draw_arrow(ax, 4.8, 3.75, af_x + 0.15, 3.67, color=COLORS['purple'], lw=2)

    # abuffersink
    draw_box(ax, 10.0, 3.2, 2.2, 1.1, 'abuffersink\n(abuffersink)', COLORS['red'], fontsize=9)
    draw_arrow(ax, af_x + 3.45, 3.67, 10.0, 3.75, color=COLORS['red'], lw=2)

    # abuffersink 参数标注
    asink_params = [
        'sample_fmts (S16)',
        'sample_rates',
        'ch_layouts',
    ]
    for i, p in enumerate(asink_params):
        ax.text(11.1, 3.0 - i * 0.28, p, fontsize=6.5,
                color=COLORS['red'], ha='center', style='italic')

    # SDL 播放
    draw_box(ax, 12.8, 3.4, 1.0, 0.7, 'SDL\n播放', COLORS['dark'], fontsize=8)
    draw_arrow(ax, 12.2, 3.75, 12.8, 3.75, color=COLORS['dark'], lw=2)

    # ================================================================
    # 公共函数标注
    # ================================================================
    common_y = 1.2
    common_box = FancyBboxPatch((2.5, common_y), 10.0, 0.65,
                                 boxstyle="round,pad=0.08", facecolor='white',
                                 edgecolor=COLORS['indigo'], linewidth=2.5,
                                 alpha=0.95, zorder=2)
    ax.add_patch(common_box)
    ax.text(7.5, common_y + 0.33, 'configure_filtergraph():  '
            'avfilter_graph_parse_ptr (有用户滤镜)  /  avfilter_link (直连)  +  avfilter_graph_config',
            ha='center', fontsize=8, fontweight='bold', color=COLORS['indigo'], zorder=3)

    draw_arrow(ax, 7.5, 2.0, 7.5, common_y + 0.65, color='#BDBDBD', lw=1.5)
    draw_arrow(ax, 7.5, 5.7, 7.5, 5.2, color='#BDBDBD', lw=1.5)

    ax.text(7.5, 0.35, '图 10-1: AVFilter 滤镜链拓扑 (buffersrc -> [autorotate] -> [user filters] -> buffersink)',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '10-filter-chain.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 10-filter-chain.png")


# ==========================================
# 图2: 滤镜在解码线程中的集成位置图
# ==========================================
def gen_filter_integration():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7, 9.5, '滤镜在解码线程中的集成位置', ha='center',
            fontsize=18, fontweight='bold', color='#212121')

    # ================================================================
    # 左侧：video_thread
    # ================================================================
    vt_x = 0.4
    vt_w = 6.0
    vt_region = FancyBboxPatch((vt_x, 0.8), vt_w, 8.2,
                                boxstyle="round,pad=0.15", facecolor=COLORS['light_blue'],
                                edgecolor=COLORS['primary'], linewidth=2,
                                alpha=0.25, zorder=0)
    ax.add_patch(vt_region)
    ax.text(vt_x + vt_w / 2, 8.8, 'video_thread', ha='center',
            fontsize=13, fontweight='bold', color=COLORS['primary'])

    # 步骤框
    bw = 4.8
    bx = vt_x + (vt_w - bw) / 2
    steps_v = [
        (8.0, 'get_video_frame()', '解码一帧视频', COLORS['grey']),
        (7.0, '变化检测', '分辨率 / 像素格式 / serial\n/ vfilter_idx 变化?', COLORS['amber']),
        (5.7, 'configure_video_filters()', '重建滤镜图\nautorotate + 用户滤镜', COLORS['orange']),
        (4.5, 'av_buffersrc_add_frame()', '解码帧送入 buffersrc', COLORS['green']),
        (3.2, 'av_buffersink_get_frame_flags()', '从 buffersink 取出处理后的帧\n(while 循环, 一进多出)', COLORS['teal']),
        (1.8, 'queue_picture()', '计算 pts/duration\n入队 pictq', COLORS['primary']),
    ]

    for i, (sy, title, desc, color) in enumerate(steps_v):
        draw_box(ax, bx, sy, bw, 0.7, '', color, alpha=0.0)
        box = FancyBboxPatch((bx, sy), bw, 0.7, boxstyle="round,pad=0.06",
                             facecolor='white', edgecolor=color,
                             linewidth=2, alpha=0.95, zorder=2)
        ax.add_patch(box)

        circle = plt.Circle((bx + 0.35, sy + 0.35), 0.2, facecolor=color,
                             edgecolor='white', linewidth=1.5, zorder=3)
        ax.add_patch(circle)
        ax.text(bx + 0.35, sy + 0.35, str(i + 1), fontsize=9, color='white',
                fontweight='bold', ha='center', va='center', zorder=4)

        ax.text(bx + 0.7, sy + 0.48, title, fontsize=8, fontweight='bold',
                color=color, va='center', zorder=3)
        ax.text(bx + 0.7, sy + 0.18, desc, fontsize=6.5,
                color='#616161', va='center', zorder=3)

        if i < len(steps_v) - 1:
            next_y = steps_v[i + 1][0]
            draw_arrow(ax, bx + bw / 2, sy, bx + bw / 2, next_y + 0.7,
                       color='#BDBDBD', lw=1.5)

    # 变化检测到 configure 的分支标注
    ax.text(bx + bw + 0.1, 6.5, '是', fontsize=8, color=COLORS['amber'],
            fontweight='bold')

    # 无变化跳过标注
    ax.annotate('', xy=(bx + bw + 0.05, 4.85),
                xytext=(bx + bw + 0.05, 7.0),
                arrowprops=dict(arrowstyle='->', color='#BDBDBD',
                                lw=1.2, linestyle='--'))
    ax.text(bx + bw + 0.15, 5.9, '否\n(跳过)', fontsize=7, color='#9E9E9E')

    # ================================================================
    # 右侧：audio_thread
    # ================================================================
    at_x = 7.6
    at_w = 6.0
    at_region = FancyBboxPatch((at_x, 0.8), at_w, 8.2,
                                boxstyle="round,pad=0.15", facecolor=COLORS['light_green'],
                                edgecolor=COLORS['teal'], linewidth=2,
                                alpha=0.25, zorder=0)
    ax.add_patch(at_region)
    ax.text(at_x + at_w / 2, 8.8, 'audio_thread', ha='center',
            fontsize=13, fontweight='bold', color=COLORS['teal'])

    abx = at_x + (at_w - bw) / 2
    steps_a = [
        (8.0, 'decoder_decode_frame()', '解码一帧音频', COLORS['grey']),
        (7.0, '格式变化检测', '采样率 / 采样格式 / 声道布局\n/ serial 变化?', COLORS['amber']),
        (5.7, 'configure_audio_filters()', '重建音频滤镜图\nforce_output_format=1', COLORS['orange']),
        (4.5, 'av_buffersrc_add_frame()', '解码帧送入 abuffer', COLORS['green']),
        (3.2, 'av_buffersink_get_frame_flags()', '从 abuffersink 取出处理后的帧\n(while 循环)', COLORS['teal']),
        (1.8, 'frame_queue_push()', '计算 pts/duration\n入队 sampq', COLORS['primary']),
    ]

    for i, (sy, title, desc, color) in enumerate(steps_a):
        box = FancyBboxPatch((abx, sy), bw, 0.7, boxstyle="round,pad=0.06",
                             facecolor='white', edgecolor=color,
                             linewidth=2, alpha=0.95, zorder=2)
        ax.add_patch(box)

        circle = plt.Circle((abx + 0.35, sy + 0.35), 0.2, facecolor=color,
                             edgecolor='white', linewidth=1.5, zorder=3)
        ax.add_patch(circle)
        ax.text(abx + 0.35, sy + 0.35, str(i + 1), fontsize=9, color='white',
                fontweight='bold', ha='center', va='center', zorder=4)

        ax.text(abx + 0.7, sy + 0.48, title, fontsize=8, fontweight='bold',
                color=color, va='center', zorder=3)
        ax.text(abx + 0.7, sy + 0.18, desc, fontsize=6.5,
                color='#616161', va='center', zorder=3)

        if i < len(steps_a) - 1:
            next_y = steps_a[i + 1][0]
            draw_arrow(ax, abx + bw / 2, sy, abx + bw / 2, next_y + 0.7,
                       color='#BDBDBD', lw=1.5)

    # 变化检测分支标注
    ax.text(abx + bw + 0.1, 6.5, '是', fontsize=8, color=COLORS['amber'],
            fontweight='bold')
    ax.annotate('', xy=(abx + bw + 0.05, 4.85),
                xytext=(abx + bw + 0.05, 7.0),
                arrowprops=dict(arrowstyle='->', color='#BDBDBD',
                                lw=1.2, linestyle='--'))
    ax.text(abx + bw + 0.15, 5.9, '否\n(跳过)', fontsize=7, color='#9E9E9E')

    # ================================================================
    # 底部公共模式标注
    # ================================================================
    ax.text(7, 0.35,
            '图 10-2: 滤镜在 video_thread / audio_thread 中的集成位置 '
            '(decode -> filter -> queue)',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '10-filter-integration.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 10-filter-integration.png")


if __name__ == '__main__':
    gen_filter_chain()
    gen_filter_integration()
    print("\n10 done!")
