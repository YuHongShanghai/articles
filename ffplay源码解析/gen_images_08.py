#!/usr/bin/env python3
"""第8篇文章图例：音频可视化——波形与频谱显示"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches
import numpy as np
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


# ==========================================
# 图1: 三种显示模式对比示意图
# ==========================================
def gen_show_modes():
    fig = plt.figure(figsize=(15, 8))
    fig.patch.set_facecolor(COLORS['bg'])

    fig.text(0.5, 0.95, '三种显示模式对比', ha='center',
             fontsize=20, fontweight='bold', color='#212121')

    # --- Panel 1: VIDEO mode ---
    ax1 = fig.add_axes([0.03, 0.18, 0.30, 0.65])
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 8)
    ax1.set_aspect('equal')
    ax1.axis('off')

    # Background rectangle simulating video
    video_bg = FancyBboxPatch((0.3, 0.8), 9.4, 6.4, boxstyle="round,pad=0.1",
                               facecolor='#263238', edgecolor='#455A64',
                               linewidth=2.5, alpha=0.95, zorder=1)
    ax1.add_patch(video_bg)

    # Simulated "video frame" content
    scene_colors = ['#1B5E20', '#2E7D32', '#388E3C', '#43A047']
    for i, c in enumerate(scene_colors):
        rect = FancyBboxPatch((1.0 + i * 2.0, 2.0), 1.6, 2.5,
                               boxstyle="round,pad=0.05",
                               facecolor=c, edgecolor='none', alpha=0.7, zorder=2)
        ax1.add_patch(rect)

    # Sky gradient
    sky = FancyBboxPatch((0.5, 4.8), 9.0, 2.2, boxstyle="round,pad=0.05",
                          facecolor='#1565C0', edgecolor='none', alpha=0.35, zorder=2)
    ax1.add_patch(sky)

    # Sun
    sun = plt.Circle((7.5, 5.8), 0.6, facecolor='#FDD835', edgecolor='#F9A825',
                      linewidth=1.5, alpha=0.9, zorder=3)
    ax1.add_patch(sun)

    # Ground
    ground = FancyBboxPatch((0.5, 1.0), 9.0, 1.5, boxstyle="round,pad=0.05",
                             facecolor='#4CAF50', edgecolor='none', alpha=0.4, zorder=2)
    ax1.add_patch(ground)

    ax1.text(5, 0.3, 'SHOW_MODE_VIDEO', ha='center', fontsize=11,
             fontweight='bold', color=COLORS['primary'])

    # --- Panel 2: WAVES mode ---
    ax2 = fig.add_axes([0.35, 0.18, 0.30, 0.65])
    ax2.set_facecolor('#1A1A2E')

    np.random.seed(42)
    t = np.linspace(0, 4 * np.pi, 500)
    signal_l = (0.6 * np.sin(t * 2.5) + 0.3 * np.sin(t * 7.1) +
                0.15 * np.sin(t * 13.3) + 0.08 * np.random.randn(len(t)))
    signal_r = (0.5 * np.sin(t * 2.5 + 0.8) + 0.25 * np.sin(t * 5.7) +
                0.2 * np.sin(t * 11.0) + 0.08 * np.random.randn(len(t)))

    # Channel L
    ax2.fill_between(t, 0.5, 0.5 + signal_l * 0.35, color='white', alpha=0.85, linewidth=0)
    ax2.axhline(y=0.5, color='#42A5F5', linewidth=0.8, alpha=0.4)

    # Channel R
    ax2.fill_between(t, -0.5, -0.5 + signal_r * 0.35, color='white', alpha=0.85, linewidth=0)
    ax2.axhline(y=-0.5, color='#42A5F5', linewidth=0.8, alpha=0.4)

    # Separator line
    ax2.axhline(y=0, color='#2979FF', linewidth=1.5, alpha=0.9)

    # Channel labels
    ax2.text(0.3, 0.85, 'L', fontsize=10, color='#64B5F6', fontweight='bold', alpha=0.7)
    ax2.text(0.3, -0.15, 'R', fontsize=10, color='#64B5F6', fontweight='bold', alpha=0.7)

    ax2.set_xlim(0, 4 * np.pi)
    ax2.set_ylim(-1.0, 1.0)
    ax2.set_xticks([])
    ax2.set_yticks([])
    for spine in ax2.spines.values():
        spine.set_visible(False)

    ax2.text(0.5, -0.18, 'SHOW_MODE_WAVES', ha='center', fontsize=11,
             fontweight='bold', color=COLORS['green'],
             transform=ax2.transAxes)

    # --- Panel 3: RDFT mode ---
    ax3 = fig.add_axes([0.67, 0.18, 0.30, 0.65])
    ax3.set_facecolor('#0D0D1A')

    np.random.seed(123)
    n_cols = 200
    n_rows = 150
    spec = np.zeros((n_rows, n_cols))
    for col in range(n_cols):
        freqs = np.random.randint(3, 8)
        for _ in range(freqs):
            center = np.random.randint(5, n_rows - 5)
            width = np.random.randint(3, 15)
            amp = np.random.uniform(0.3, 1.0)
            spec[max(0, center-width):min(n_rows, center+width), col] += amp * np.exp(
                -0.5 * ((np.arange(max(0, center-width), min(n_rows, center+width)) - center) / (width * 0.5))**2
            )
    # Add some horizontal bands (harmonics)
    for freq_line in [15, 30, 45, 60, 90, 120]:
        if freq_line < n_rows:
            spec[freq_line-2:freq_line+2, :] += np.random.uniform(0.1, 0.5, n_cols)

    spec = np.clip(spec, 0, 1)
    spec = np.sqrt(spec)  # compress dynamic range

    # Build RGB: R=left channel, G=right channel, B=average
    r_ch = spec * 0.9
    g_ch = spec * 0.7 + np.random.uniform(0, 0.15, spec.shape)
    g_ch = np.clip(g_ch, 0, 1)
    b_ch = (r_ch + g_ch) / 2
    rgb = np.stack([r_ch, g_ch, b_ch], axis=-1)
    rgb = np.clip(rgb, 0, 1)

    ax3.imshow(rgb, aspect='auto', origin='lower', interpolation='bilinear')
    ax3.set_xticks([])
    ax3.set_yticks([])
    for spine in ax3.spines.values():
        spine.set_visible(False)

    # Arrow annotations
    ax3.annotate('', xy=(n_cols * 0.95, n_rows * 0.5), xytext=(n_cols * 0.05, n_rows * 0.5),
                 arrowprops=dict(arrowstyle='->', color='white', lw=1.2, alpha=0.5))
    ax3.text(n_cols * 0.5, n_rows * 0.53, 'xpos', fontsize=8, color='white',
             ha='center', alpha=0.6, fontstyle='italic')

    ax3.text(0.5, -0.18, 'SHOW_MODE_RDFT', ha='center', fontsize=11,
             fontweight='bold', color=COLORS['purple'],
             transform=ax3.transAxes)

    # Bottom description boxes
    descs = [
        ('VIDEO', '视频解码帧直接渲染\nvideo_image_display()', COLORS['primary']),
        ('WAVES', '时域波形 -- 逐像素列绘制\n零交叉检测稳定显示', COLORS['green']),
        ('RDFT', '频域频谱 -- RDFT变换\n瀑布式纹理逐列更新', COLORS['purple']),
    ]

    for i, (title, desc, color) in enumerate(descs):
        bx = 0.035 + i * 0.32
        bbox = fig.text(bx + 0.15, 0.05, desc, ha='center', va='center',
                        fontsize=8.5, color='#424242',
                        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                                  edgecolor=color, linewidth=2, alpha=0.95))

    fig.text(0.5, 0.01, '图 8-1: 三种显示模式对比 (w 键切换)',
             ha='center', fontsize=10, color='#757575', style='italic')

    plt.savefig(os.path.join(OUTPUT_DIR, '08-show-modes.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 08-show-modes.png")


# ==========================================
# 图2: RDFT 频谱计算流程图
# ==========================================
def gen_rdft_pipeline():
    fig, ax = plt.subplots(1, 1, figsize=(15, 9))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7.5, 8.6, 'RDFT 频谱计算流程', ha='center',
            fontsize=20, fontweight='bold', color='#212121')

    # ===== 第一行: 数据来源 =====
    row1_y = 7.2

    ax.text(0.5, row1_y + 0.35, '1', fontsize=11, fontweight='bold',
            color='white', ha='center', va='center',
            bbox=dict(boxstyle='circle,pad=0.2', facecolor=COLORS['primary'],
                      edgecolor='white', linewidth=1.5), zorder=4)
    ax.text(1.0, row1_y + 0.35, '数据采集', fontsize=11, fontweight='bold',
            color=COLORS['primary'], va='center')

    draw_box(ax, 0.3, row1_y - 0.5, 2.8, 0.55, 'sdl_audio_callback()', COLORS['grey'], fontsize=9)
    draw_arrow(ax, 3.1, row1_y - 0.22, 3.9, row1_y - 0.22, color=COLORS['grey'], lw=2)

    draw_box(ax, 3.9, row1_y - 0.5, 3.3, 0.55, 'update_sample_display()', COLORS['teal'], fontsize=9)
    draw_arrow(ax, 7.2, row1_y - 0.22, 8.0, row1_y - 0.22, color=COLORS['teal'], lw=2)

    # Ring buffer visualization
    ring_cx, ring_cy = 10.5, row1_y - 0.15
    ring_r = 0.65
    theta = np.linspace(0, 2 * np.pi, 60)
    # Draw ring segments with color gradient
    seg_count = 24
    for si in range(seg_count):
        t1 = 2 * np.pi * si / seg_count
        t2 = 2 * np.pi * (si + 1) / seg_count
        ts = np.linspace(t1, t2, 8)
        xs_outer = ring_cx + ring_r * np.cos(ts)
        ys_outer = ring_cy + ring_r * np.sin(ts)
        xs_inner = ring_cx + (ring_r - 0.2) * np.cos(ts[::-1])
        ys_inner = ring_cy + (ring_r - 0.2) * np.sin(ts[::-1])
        alpha_val = 0.3 + 0.7 * (si / seg_count)
        ax.fill(np.concatenate([xs_outer, xs_inner]),
                np.concatenate([ys_outer, ys_inner]),
                color=COLORS['primary'], alpha=alpha_val, zorder=2)

    ax.text(ring_cx, ring_cy, 'sample_array\n(524288)', fontsize=6.5,
            ha='center', va='center', color=COLORS['primary'],
            fontweight='bold', zorder=3)

    # Write pointer
    ptr_angle = 2 * np.pi * 0.75
    ptr_x = ring_cx + (ring_r + 0.15) * np.cos(ptr_angle)
    ptr_y = ring_cy + (ring_r + 0.15) * np.sin(ptr_angle)
    ax.annotate('write_idx', xy=(ring_cx + ring_r * np.cos(ptr_angle),
                                  ring_cy + ring_r * np.sin(ptr_angle)),
                xytext=(ptr_x + 0.4, ptr_y + 0.3),
                fontsize=6.5, color=COLORS['red'], fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=COLORS['red'], lw=1.2),
                zorder=4)

    # ===== 第二行: 延迟补偿 + 起始位置计算 =====
    row2_y = 5.5

    ax.text(0.5, row2_y + 0.35, '2', fontsize=11, fontweight='bold',
            color='white', ha='center', va='center',
            bbox=dict(boxstyle='circle,pad=0.2', facecolor=COLORS['green'],
                      edgecolor='white', linewidth=1.5), zorder=4)
    ax.text(1.0, row2_y + 0.35, '延迟补偿', fontsize=11, fontweight='bold',
            color=COLORS['green'], va='center')

    # delay calculation box
    delay_box = FancyBboxPatch((0.3, row2_y - 0.7), 4.5, 0.85,
                                boxstyle="round,pad=0.1", facecolor='white',
                                edgecolor=COLORS['green'], linewidth=2, alpha=0.95, zorder=2)
    ax.add_patch(delay_box)
    ax.text(2.55, row2_y - 0.05, 'delay = audio_write_buf_size / (2 * ch)', fontsize=7.5,
            ha='center', va='center', color='#424242', zorder=3)
    ax.text(2.55, row2_y - 0.4, 'delay -= (now - callback_time) * freq / 1e6', fontsize=7.5,
            ha='center', va='center', color='#424242', zorder=3)

    draw_arrow(ax, 4.8, row2_y - 0.28, 5.5, row2_y - 0.28, color=COLORS['green'], lw=2)

    # i_start box
    draw_box(ax, 5.5, row2_y - 0.6, 3.0, 0.65,
             'i_start = compute_mod(\nindex - delay * ch, SIZE)',
             COLORS['green'], fontsize=7.5)

    # ===== 第三行: 窗函数 + RDFT =====
    row3_y = 3.7

    ax.text(0.5, row3_y + 0.35, '3', fontsize=11, fontweight='bold',
            color='white', ha='center', va='center',
            bbox=dict(boxstyle='circle,pad=0.2', facecolor=COLORS['orange'],
                      edgecolor='white', linewidth=1.5), zorder=4)
    ax.text(1.0, row3_y + 0.35, 'RDFT 变换', fontsize=11, fontweight='bold',
            color=COLORS['orange'], va='center')

    # Window function inset
    win_box = FancyBboxPatch((0.3, row3_y - 0.75), 3.6, 1.0,
                              boxstyle="round,pad=0.1", facecolor='white',
                              edgecolor=COLORS['orange'], linewidth=2, alpha=0.95, zorder=2)
    ax.add_patch(win_box)
    ax.text(2.1, row3_y + 0.1, 'Hanning 窗函数', fontsize=8, fontweight='bold',
            ha='center', color=COLORS['orange'], zorder=3)

    # Mini window function plot
    win_x = np.linspace(0.6, 3.6, 80)
    win_cx = 2.1
    win_w = 1.4
    win_y_base = row3_y - 0.6
    win_y_data = win_y_base + 0.4 * (1 - ((win_x - win_cx) / win_w) ** 2)
    win_y_data = np.maximum(win_y_data, win_y_base)
    ax.fill_between(win_x, win_y_base, win_y_data, color=COLORS['orange'],
                    alpha=0.3, zorder=3)
    ax.plot(win_x, win_y_data, color=COLORS['orange'], lw=1.5, zorder=3)
    ax.text(2.1, row3_y - 0.65, 'w(x) = 1 - (x/N)^2', fontsize=6.5,
            ha='center', color='#616161', zorder=3)

    draw_arrow(ax, 3.9, row3_y - 0.25, 4.7, row3_y - 0.25, color=COLORS['orange'], lw=2)

    # Windowed samples
    draw_box(ax, 4.7, row3_y - 0.6, 2.8, 0.7,
             'data_in[ch][x] =\nsample * (1 - w*w)', COLORS['orange'], fontsize=8)

    draw_arrow(ax, 7.5, row3_y - 0.25, 8.3, row3_y - 0.25, color=COLORS['orange'], lw=2)

    # RDFT execution
    rdft_box = FancyBboxPatch((8.3, row3_y - 0.7), 3.0, 0.9,
                               boxstyle="round,pad=0.1", facecolor=COLORS['purple'],
                               edgecolor='white', linewidth=2, alpha=0.95, zorder=2)
    ax.add_patch(rdft_box)
    ax.text(9.8, row3_y - 0.05, 'rdft_fn(rdft,', fontsize=8, fontweight='bold',
            ha='center', color='white', zorder=3)
    ax.text(9.8, row3_y - 0.4, '  data, data_in, ...)', fontsize=8, fontweight='bold',
            ha='center', color='white', zorder=3)

    draw_arrow(ax, 11.3, row3_y - 0.25, 12.0, row3_y - 0.25, color=COLORS['purple'], lw=2)

    # Complex spectrum
    spec_box = FancyBboxPatch((12.0, row3_y - 0.55), 2.5, 0.6,
                               boxstyle="round,pad=0.1", facecolor='white',
                               edgecolor=COLORS['purple'], linewidth=2, alpha=0.95, zorder=2)
    ax.add_patch(spec_box)
    ax.text(13.25, row3_y - 0.25, 'AVComplexFloat\n{re, im}', fontsize=8,
            ha='center', va='center', color=COLORS['purple'], fontweight='bold', zorder=3)

    # ===== 第四行: 颜色映射 + 纹理更新 =====
    row4_y = 1.8

    ax.text(0.5, row4_y + 0.35, '4', fontsize=11, fontweight='bold',
            color='white', ha='center', va='center',
            bbox=dict(boxstyle='circle,pad=0.2', facecolor=COLORS['red'],
                      edgecolor='white', linewidth=1.5), zorder=4)
    ax.text(1.0, row4_y + 0.35, '颜色映射与渲染', fontsize=11, fontweight='bold',
            color=COLORS['red'], va='center')

    # Amplitude calculation
    amp_box = FancyBboxPatch((0.3, row4_y - 0.7), 3.2, 0.85,
                              boxstyle="round,pad=0.1", facecolor='white',
                              edgecolor=COLORS['red'], linewidth=2, alpha=0.95, zorder=2)
    ax.add_patch(amp_box)
    ax.text(1.9, row4_y - 0.05, '幅度计算(双重开方)', fontsize=8, fontweight='bold',
            ha='center', color=COLORS['red'], zorder=3)
    ax.text(1.9, row4_y - 0.4, 'a = sqrt(w * sqrt(re^2 + im^2))', fontsize=7,
            ha='center', color='#424242', zorder=3)

    draw_arrow(ax, 3.5, row4_y - 0.28, 4.2, row4_y - 0.28, color=COLORS['red'], lw=2)

    # RGB mapping
    rgb_w = 3.4
    rgb_box = FancyBboxPatch((4.2, row4_y - 0.7), rgb_w, 0.85,
                              boxstyle="round,pad=0.1", facecolor='white',
                              edgecolor=COLORS['red'], linewidth=2, alpha=0.95, zorder=2)
    ax.add_patch(rgb_box)
    ax.text(4.2 + rgb_w / 2, row4_y - 0.0, 'ARGB 颜色编码', fontsize=8, fontweight='bold',
            ha='center', color=COLORS['red'], zorder=3)

    # R G B labels
    color_labels = [('R', 'a (L)', '#E53935'), ('G', 'b (R)', '#43A047'), ('B', '(a+b)/2', '#1E88E5')]
    for ci, (ch_name, ch_desc, ch_color) in enumerate(color_labels):
        cx = 4.6 + ci * 1.05
        cy = row4_y - 0.5
        circle = plt.Circle((cx, cy), 0.13, facecolor=ch_color, edgecolor='white',
                             linewidth=1, zorder=3)
        ax.add_patch(circle)
        ax.text(cx, cy, ch_name, fontsize=6.5, fontweight='bold', color='white',
                ha='center', va='center', zorder=4)
        ax.text(cx, cy - 0.22, ch_desc, fontsize=5.5, color='#616161',
                ha='center', va='center', zorder=3)

    draw_arrow(ax, 4.2 + rgb_w, row4_y - 0.28, 8.2, row4_y - 0.28,
               color=COLORS['red'], lw=2)

    # Texture update
    tex_box = FancyBboxPatch((8.2, row4_y - 0.7), 3.0, 0.85,
                              boxstyle="round,pad=0.1", facecolor=COLORS['primary'],
                              edgecolor='white', linewidth=2, alpha=0.95, zorder=2)
    ax.add_patch(tex_box)
    ax.text(9.7, row4_y - 0.05, 'SDL_LockTexture', fontsize=8.5, fontweight='bold',
            ha='center', color='white', zorder=3)
    ax.text(9.7, row4_y - 0.4, 'vis_texture 逐列写入', fontsize=7.5,
            ha='center', color='#BBDEFB', zorder=3)

    draw_arrow(ax, 11.2, row4_y - 0.28, 11.9, row4_y - 0.28, color=COLORS['primary'], lw=2)

    # Screen output
    draw_box(ax, 11.9, row4_y - 0.6, 2.5, 0.65,
             'SDL_RenderCopy\n(xpos++)', COLORS['primary'], fontsize=8.5)

    # Vertical connecting arrows
    draw_arrow(ax, 10.5, row1_y - 0.5 - 0.55, 7.0, row2_y - 0.05,
               color='#BDBDBD', lw=1.5)
    draw_arrow(ax, 7.0, row2_y - 0.6, 2.1, row3_y + 0.25,
               color='#BDBDBD', lw=1.5)
    draw_arrow(ax, 13.25, row3_y - 0.55, 1.9, row4_y + 0.15,
               color='#BDBDBD', lw=1.5)

    # Legend box
    legend_y = 0.3
    legend_items = [
        ('sdl_audio_callback 中调用 update_sample_display 填充环形缓冲区', COLORS['grey']),
        ('计算当前播放位置对应的 sample_array 索引', COLORS['green']),
        ('加窗 + av_tx RDFT 变换, 时域转频域', COLORS['orange']),
        ('幅度 -> 双重开方 -> ARGB 颜色 -> 纹理逐列绘制', COLORS['red']),
    ]
    for li, (desc, color) in enumerate(legend_items):
        lx = 0.5 + li * 3.7
        circle = plt.Circle((lx, legend_y), 0.12, facecolor=color,
                             edgecolor='white', linewidth=1, zorder=3)
        ax.add_patch(circle)
        ax.text(lx, legend_y, str(li + 1), fontsize=7, fontweight='bold',
                color='white', ha='center', va='center', zorder=4)
        ax.text(lx + 0.25, legend_y, desc, fontsize=6.5, color='#424242',
                va='center', zorder=3)

    ax.text(7.5, -0.2, '图 8-2: RDFT 频谱计算流程 (sample_array -> Hanning 窗 -> RDFT -> ARGB -> vis_texture)',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '08-rdft-pipeline.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 08-rdft-pipeline.png")


if __name__ == '__main__':
    gen_show_modes()
    gen_rdft_pipeline()
    print("\n08 done!")
