#!/usr/bin/env python3
"""第5篇文章图例：音频输出与处理"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
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
    'light_blue': '#E3F2FD',
    'light_green': '#E8F5E9',
    'light_orange': '#FFF3E0',
    'light_purple': '#F3E5F5',
    'light_teal': '#E0F7FA',
    'bg': '#FAFAFA',
    'dark': '#212121',
    'mid': '#616161',
}


def draw_box(ax, x, y, w, h, text, facecolor, textcolor='white',
             fontsize=10, edgecolor=None, linewidth=2, alpha=0.95, zorder=2):
    if edgecolor is None:
        edgecolor = facecolor
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                         facecolor=facecolor, edgecolor=edgecolor,
                         linewidth=linewidth, alpha=alpha, zorder=zorder)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=textcolor, fontweight='bold', zorder=zorder + 1)


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=2, style='->', zorder=1):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw), zorder=zorder)


def draw_label(ax, x, y, text, color='#616161', fontsize=8, ha='center', va='center'):
    ax.text(x, y, text, ha=ha, va=va, fontsize=fontsize, color=color, zorder=5)


# ==========================================
# 图1: 音频输出完整数据流图
# ==========================================
def gen_audio_data_flow():
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7, 7.6, '音频输出完整数据流', ha='center',
            fontsize=18, fontweight='bold', color=COLORS['dark'])

    bw = 2.0
    bh = 0.85
    row1_y = 5.8
    row2_y = 4.2
    row3_y = 2.6
    row4_y = 1.0

    # --- 第一行: PacketQueue -> audio_thread 解码 -> 滤镜 ---
    draw_box(ax, 0.5, row1_y, bw, bh, 'PacketQueue\n(audioq)', COLORS['grey'], fontsize=9)
    draw_arrow(ax, 0.5 + bw, row1_y + bh / 2, 3.5, row1_y + bh / 2, COLORS['grey'])
    draw_label(ax, 2.95, row1_y + bh / 2 + 0.25, '压缩包', fontsize=7)

    draw_box(ax, 3.5, row1_y, bw + 0.6, bh, 'audio_thread\n解码 AVFrame', COLORS['primary'], fontsize=9)
    draw_arrow(ax, 3.5 + bw + 0.6, row1_y + bh / 2, 7.1, row1_y + bh / 2, COLORS['primary'])
    draw_label(ax, 6.65, row1_y + bh / 2 + 0.25, 'PCM 帧', fontsize=7)

    draw_box(ax, 7.1, row1_y, bw + 0.4, bh, '音频滤镜链\n(AVFilter)', COLORS['purple'], fontsize=9)
    draw_arrow(ax, 7.1 + bw + 0.4, row1_y + bh / 2, 10.5, row1_y + bh / 2, COLORS['purple'])
    draw_label(ax, 10.2, row1_y + bh / 2 + 0.25, '滤镜输出', fontsize=7)

    draw_box(ax, 10.5, row1_y, bw, bh, 'FrameQueue\n(sampq)', COLORS['teal'], fontsize=9)

    # 下箭头: sampq -> audio_decode_frame
    draw_arrow(ax, 11.5, row1_y, 11.5, row2_y + bh, COLORS['teal'])

    # --- 第二行: audio_decode_frame 内部 ---
    # 背景框
    bg_box = FancyBboxPatch((0.3, row2_y - 0.15), 13.2, bh + 0.3,
                            boxstyle="round,pad=0.15", facecolor=COLORS['light_blue'],
                            edgecolor='#90CAF9', linewidth=1.5, alpha=0.5, zorder=0)
    ax.add_patch(bg_box)
    ax.text(0.7, row2_y + bh + 0.05, 'audio_decode_frame()', fontsize=9,
            fontweight='bold', color=COLORS['primary'], va='bottom', zorder=3)

    draw_box(ax, 0.5, row2_y, bw + 0.3, bh, '从 sampq 取帧\nserial 过滤', COLORS['teal'], fontsize=8)
    draw_arrow(ax, 0.5 + bw + 0.3, row2_y + bh / 2, 3.8, row2_y + bh / 2, COLORS['teal'])

    draw_box(ax, 3.8, row2_y, bw + 0.4, bh, 'synchronize_audio\n同步补偿', COLORS['green'], fontsize=8)
    draw_arrow(ax, 3.8 + bw + 0.4, row2_y + bh / 2, 7.2, row2_y + bh / 2, COLORS['green'])

    draw_box(ax, 7.2, row2_y, bw + 0.4, bh, 'swr_convert\n重采样', COLORS['orange'], fontsize=8)
    draw_arrow(ax, 7.2 + bw + 0.4, row2_y + bh / 2, 10.6, row2_y + bh / 2, COLORS['orange'])

    draw_box(ax, 10.6, row2_y, bw + 0.4, bh, '更新\naudio_clock', COLORS['primary'], fontsize=8)

    # 下箭头: audio_decode_frame -> sdl_audio_callback
    draw_arrow(ax, 6.0, row2_y, 6.0, row3_y + bh, '#78909C')
    draw_label(ax, 6.6, row3_y + bh + 0.15, 'audio_buf', fontsize=7, color=COLORS['primary'])

    # --- 第三行: sdl_audio_callback ---
    bg_box2 = FancyBboxPatch((0.3, row3_y - 0.15), 13.2, bh + 0.3,
                             boxstyle="round,pad=0.15", facecolor=COLORS['light_orange'],
                             edgecolor='#FFCC80', linewidth=1.5, alpha=0.5, zorder=0)
    ax.add_patch(bg_box2)
    ax.text(0.7, row3_y + bh + 0.05, 'sdl_audio_callback()  [SDL 音频线程调用]', fontsize=9,
            fontweight='bold', color=COLORS['orange'], va='bottom', zorder=3)

    draw_box(ax, 0.5, row3_y, bw + 0.5, bh, '调用\naudio_decode_frame', COLORS['orange'], fontsize=8)
    draw_arrow(ax, 0.5 + bw + 0.5, row3_y + bh / 2, 4.0, row3_y + bh / 2, COLORS['orange'])

    draw_box(ax, 4.0, row3_y, bw + 0.2, bh, '音量控制\nSDL_MixAudio', COLORS['red'], fontsize=8)
    draw_arrow(ax, 4.0 + bw + 0.2, row3_y + bh / 2, 7.2, row3_y + bh / 2, COLORS['red'])

    draw_box(ax, 7.2, row3_y, bw + 0.2, bh, '填充 SDL\nstream 缓冲', '#455A64', fontsize=8)
    draw_arrow(ax, 7.2 + bw + 0.2, row3_y + bh / 2, 10.4, row3_y + bh / 2, '#455A64')

    draw_box(ax, 10.4, row3_y, bw + 0.6, bh, '更新音频时钟\nset_clock_at', COLORS['primary'], fontsize=8)

    # 下箭头
    draw_arrow(ax, 8.3, row3_y, 8.3, row4_y + bh, '#455A64')

    # --- 第四行: SDL 设备 -> 扬声器 ---
    draw_box(ax, 5.5, row4_y, bw + 1.0, bh, 'SDL 音频设备\n(硬件缓冲区)', '#455A64', fontsize=9)
    draw_arrow(ax, 5.5 + bw + 1.0, row4_y + bh / 2, 10.5, row4_y + bh / 2, '#455A64')
    draw_box(ax, 10.5, row4_y, bw, bh, '扬声器', COLORS['red'], fontsize=11)

    ax.text(7, 0.25, '图 5-1: 音频输出完整数据流',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '05-audio-data-flow.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 05-audio-data-flow.png")


# ==========================================
# 图2: sdl_audio_callback 工作流程图
# ==========================================
def gen_sdl_audio_callback():
    fig, ax = plt.subplots(1, 1, figsize=(10, 14))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(5, 13.6, 'sdl_audio_callback 工作流程', ha='center',
            fontsize=16, fontweight='bold', color=COLORS['dark'])

    cx = 5.0
    bw = 4.2
    bh = 0.75

    steps = [
        ('SDL 音频线程发起回调', '传入 stream 缓冲区和 len 字节需求', COLORS['grey']),
        ('记录 audio_callback_time', '用于音频时钟校正', COLORS['primary']),
        ('len > 0 ?', '检查是否还需要填充数据', '#F9A825'),
        ('audio_buf 已耗尽 ?', 'audio_buf_index >= audio_buf_size', '#F9A825'),
        ('audio_decode_frame()', '从 sampq 取帧, 重采样, 获取 PCM 数据', COLORS['teal']),
        ('获取成功 ?', '检查返回值', '#F9A825'),
        ('计算可拷贝量 len1', 'min(剩余buf, 剩余len)', COLORS['primary']),
        ('音量控制与数据拷贝', '静音: memset 清零\n最大音量: memcpy\n其他: SDL_MixAudioFormat', COLORS['red']),
        ('更新 len / stream / index', '推进读写指针, 回到循环', COLORS['primary']),
        ('更新音频时钟', 'set_clock_at\n校正硬件缓冲延迟', COLORS['green']),
    ]

    gap = 1.2
    y_start = 12.8
    x_start = cx - bw / 2

    for i, (title, desc, color) in enumerate(steps):
        y = y_start - i * gap

        is_decision = ('?' in title)

        if is_decision:
            dw = 1.2
            dh = 0.6
            diamond = plt.Polygon([
                [cx, y + dh + 0.1],
                [cx + dw, y + dh / 2 + 0.1],
                [cx, y + 0.1],
                [cx - dw, y + dh / 2 + 0.1]
            ], facecolor='#FFF9C4', edgecolor='#F9A825', linewidth=2, zorder=2)
            ax.add_patch(diamond)
            ax.text(cx, y + dh / 2 + 0.1, title, ha='center', va='center',
                    fontsize=8, fontweight='bold', color='#424242', zorder=3)
            ax.text(cx + dw + 0.3, y + dh / 2 + 0.1, desc, ha='left', va='center',
                    fontsize=7, color=COLORS['mid'], zorder=3)
        else:
            num_circle = plt.Circle((x_start - 0.5, y + bh / 2), 0.25,
                                    facecolor=color, edgecolor='white', linewidth=1.5, zorder=3)
            ax.add_patch(num_circle)
            ax.text(x_start - 0.5, y + bh / 2, str(i + 1),
                    ha='center', va='center', fontsize=9, color='white',
                    fontweight='bold', zorder=4)

            box = FancyBboxPatch((x_start, y), bw, bh, boxstyle="round,pad=0.1",
                                 facecolor='white', edgecolor=color, linewidth=2.5,
                                 alpha=0.95, zorder=2)
            ax.add_patch(box)
            ax.text(x_start + 0.2, y + bh - 0.15, title, fontsize=9,
                    fontweight='bold', color=color, va='top', zorder=3)
            ax.text(x_start + 0.2, y + bh - 0.40, desc, fontsize=7,
                    color='#424242', va='top', zorder=3)

        if i < len(steps) - 1:
            next_y = y_start - (i + 1) * gap
            is_next_decision = ('?' in steps[i + 1][0])
            target_y = next_y + 0.7 + 0.1 if is_next_decision else next_y + bh
            draw_arrow(ax, cx, y, cx, target_y, color='#BDBDBD', lw=2)

    # "Yes" labels for decisions
    y_decision_1 = y_start - 2 * gap
    ax.text(cx + 0.15, y_decision_1 - 0.1, 'Yes', fontsize=7, color=COLORS['green'],
            fontweight='bold', ha='left')

    y_decision_2 = y_start - 3 * gap
    ax.text(cx + 0.15, y_decision_2 - 0.1, 'Yes', fontsize=7, color=COLORS['green'],
            fontweight='bold', ha='left')

    y_decision_3 = y_start - 5 * gap
    ax.text(cx + 0.15, y_decision_3 - 0.1, 'Yes', fontsize=7, color=COLORS['green'],
            fontweight='bold', ha='left')

    # "No" branch for decision at index 3 (audio_buf 已耗尽)
    y_dec3 = y_start - 3 * gap + 0.4
    ax.annotate('', xy=(x_start + bw + 0.3, y_start - 5 * gap + bh / 2),
                xytext=(cx + 1.2, y_dec3),
                arrowprops=dict(arrowstyle='->', color='#EF5350', lw=1.5,
                               connectionstyle='arc3,rad=-0.3'), zorder=1)
    ax.text(cx + 1.4, y_dec3 + 0.1, 'No(buf 充足)', fontsize=7, color='#EF5350', fontweight='bold')

    # "No" for decision at index 5 (获取成功?)
    y_dec5 = y_start - 5 * gap + 0.4
    ax.annotate('', xy=(x_start - 0.3, y_start - 5 * gap + bh / 2 - 1.3),
                xytext=(cx - 1.2, y_dec5),
                arrowprops=dict(arrowstyle='->', color='#EF5350', lw=1.5,
                               connectionstyle='arc3,rad=0.3'), zorder=1)
    ax.text(cx - 1.4, y_dec5 + 0.1, 'No(静音)', fontsize=7, color='#EF5350',
            fontweight='bold', ha='right')

    # Loop arrow: step 9 -> step 3 (while len > 0)
    loop_x = x_start - 1.0
    step3_y = y_start - 2 * gap + 0.4
    step9_y = y_start - 8 * gap + bh / 2
    ax.annotate('', xy=(loop_x + 0.4, step3_y),
                xytext=(loop_x + 0.4, step9_y),
                arrowprops=dict(arrowstyle='->', color='#78909C', lw=2,
                               connectionstyle='arc3,rad=0.4'), zorder=1)
    ax.text(loop_x - 0.1, (step3_y + step9_y) / 2, 'while\nlen>0', fontsize=8,
            color='#78909C', fontweight='bold', rotation=90, va='center', ha='center')

    # "No" for len > 0 -> go to step 10
    y_dec2 = y_start - 2 * gap + 0.4
    ax.annotate('', xy=(x_start + bw + 0.5, y_start - 9 * gap + bh / 2),
                xytext=(cx + 1.2, y_dec2),
                arrowprops=dict(arrowstyle='->', color='#78909C', lw=1.5,
                               connectionstyle='arc3,rad=-0.2'), zorder=1)
    ax.text(cx + 1.4, y_dec2 + 0.1, 'No(填充完毕)', fontsize=7,
            color='#78909C', fontweight='bold')

    ax.text(5, 0.3, '图 5-2: sdl_audio_callback 工作流程',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '05-sdl-audio-callback.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 05-sdl-audio-callback.png")


if __name__ == '__main__':
    gen_audio_data_flow()
    gen_sdl_audio_callback()
    print("\n05 done!")
