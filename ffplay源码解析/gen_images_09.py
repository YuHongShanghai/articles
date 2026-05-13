#!/usr/bin/env python3
"""第9篇文章图例：音视频同步机制"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc
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
    'yellow': '#F9A825',
    'bg': '#FAFAFA',
    'light_blue': '#E3F2FD',
    'light_green': '#E8F5E9',
    'light_orange': '#FFF3E0',
    'light_purple': '#F3E5F5',
    'light_red': '#FFEBEE',
    'light_teal': '#E0F7FA',
    'dark': '#212121',
    'mid_grey': '#9E9E9E',
}


def draw_box(ax, x, y, w, h, text, color, fontsize=10, text_color='white',
             alpha=0.95, edgecolor=None, linewidth=1.5, style="round,pad=0.08"):
    ec = edgecolor if edgecolor else 'white'
    box = FancyBboxPatch((x, y), w, h, boxstyle=style,
                         facecolor=color, edgecolor=ec, linewidth=linewidth,
                         alpha=alpha, zorder=2)
    ax.add_patch(box)
    lines = text.split('\n')
    if len(lines) == 1:
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
                fontsize=fontsize, color=text_color, fontweight='bold', zorder=3)
    else:
        line_height = fontsize * 0.018
        total_h = (len(lines) - 1) * line_height
        for i, line in enumerate(lines):
            ly = y + h / 2 + total_h / 2 - i * line_height
            fw = 'bold' if i == 0 else 'normal'
            fs = fontsize if i == 0 else fontsize - 1
            ax.text(x + w / 2, ly, line, ha='center', va='center',
                    fontsize=fs, color=text_color, fontweight=fw, zorder=3)


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=1.5, style='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw), zorder=4)


def draw_dashed_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=1.2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                linestyle='dashed'), zorder=4)


# ==========================================
# 图1: 三时钟同步模型图
# ==========================================
def gen_sync_model():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7, 9.5, '三时钟同步模型', ha='center',
            fontsize=20, fontweight='bold', color=COLORS['dark'])

    # --- Master Clock selector (top center) ---
    draw_box(ax, 4.5, 8.0, 5, 1.0, 'get_master_clock()\n主时钟选择器',
             COLORS['dark'], fontsize=11, text_color='white')

    # --- Three clocks ---
    clk_y = 5.8
    clk_w, clk_h = 3.2, 1.6

    # Audio clock
    draw_box(ax, 0.5, clk_y, clk_w, clk_h, 'audclk\n音频时钟',
             COLORS['primary'], fontsize=12)
    ax.text(0.5 + clk_w / 2, clk_y - 0.3, '(默认主时钟)', ha='center',
            fontsize=9, color=COLORS['primary'], style='italic')

    # Video clock
    draw_box(ax, 5.4, clk_y, clk_w, clk_h, 'vidclk\n视频时钟',
             COLORS['green'], fontsize=12)

    # External clock
    draw_box(ax, 10.3, clk_y, clk_w, clk_h, 'extclk\n外部时钟',
             COLORS['orange'], fontsize=12)

    # Arrows from clocks to selector
    draw_arrow(ax, 0.5 + clk_w / 2, clk_y + clk_h, 5.5, 8.0,
               color=COLORS['primary'], lw=2)
    draw_arrow(ax, 5.4 + clk_w / 2, clk_y + clk_h, 7.0, 8.0,
               color=COLORS['green'], lw=2)
    draw_arrow(ax, 10.3 + clk_w / 2, clk_y + clk_h, 8.5, 8.0,
               color=COLORS['orange'], lw=2)

    # --- Clock update sources ---
    src_y = 3.6
    src_h = 1.2
    src_w = 3.2

    # Audio source
    draw_box(ax, 0.5, src_y, src_w, src_h,
             'sdl_audio_callback\n音频输出回调',
             COLORS['primary'], fontsize=9, alpha=0.75)
    draw_arrow(ax, 0.5 + src_w / 2, src_y + src_h, 0.5 + clk_w / 2, clk_y,
               color=COLORS['primary'], lw=1.5)
    ax.text(0.5 + src_w / 2 + 0.15, (src_y + src_h + clk_y) / 2, 'set_clock()',
            fontsize=8, color=COLORS['grey'], ha='left', rotation=90)

    # Video source
    draw_box(ax, 5.4, src_y, src_w, src_h,
             'update_video_pts\nvideo_refresh',
             COLORS['green'], fontsize=9, alpha=0.75)
    draw_arrow(ax, 5.4 + src_w / 2, src_y + src_h, 5.4 + clk_w / 2, clk_y,
               color=COLORS['green'], lw=1.5)
    ax.text(5.4 + src_w / 2 + 0.15, (src_y + src_h + clk_y) / 2, 'set_clock()',
            fontsize=8, color=COLORS['grey'], ha='left', rotation=90)

    # External source
    draw_box(ax, 10.3, src_y, src_w, src_h,
             'check_external\n_clock_speed',
             COLORS['orange'], fontsize=9, alpha=0.75)
    draw_arrow(ax, 10.3 + src_w / 2, src_y + src_h, 10.3 + clk_w / 2, clk_y,
               color=COLORS['orange'], lw=1.5)
    ax.text(10.3 + src_w / 2 + 0.15, (src_y + src_h + clk_y) / 2, 'set_clock_speed()',
            fontsize=8, color=COLORS['grey'], ha='left', rotation=90)

    # --- Sync consumers at bottom ---
    cons_y = 1.3
    cons_h = 1.4
    cons_w = 3.8

    # Video sync
    draw_box(ax, 0.8, cons_y, cons_w, cons_h,
             'compute_target_delay\n视频同步校正',
             '#37474F', fontsize=9)
    draw_dashed_arrow(ax, 0.8 + cons_w / 2, cons_y + cons_h,
                      0.5 + clk_w / 2, src_y,
                      color=COLORS['grey'], lw=1.2)

    # Audio sync
    draw_box(ax, 5.1, cons_y, cons_w, cons_h,
             'synchronize_audio\n音频同步补偿',
             '#37474F', fontsize=9)
    draw_dashed_arrow(ax, 5.1 + cons_w / 2, cons_y + cons_h,
                      5.4 + clk_w / 2, src_y,
                      color=COLORS['grey'], lw=1.2)

    # Frame drop
    draw_box(ax, 9.4, cons_y, cons_w, cons_h,
             'get_video_frame\nEarly/Late Drop',
             '#37474F', fontsize=9)
    draw_dashed_arrow(ax, 9.4 + cons_w / 2, cons_y + cons_h,
                      10.3 + clk_w / 2, src_y,
                      color=COLORS['grey'], lw=1.2)

    # --- Labels ---
    ax.text(2.7, cons_y - 0.35, 'diff = vidclk - master_clock',
            fontsize=8, color=COLORS['red'], ha='center', style='italic')
    ax.text(7.0, cons_y - 0.35, 'diff = audclk - master_clock',
            fontsize=8, color=COLORS['red'], ha='center', style='italic')
    ax.text(11.3, cons_y - 0.35, 'dpts - master_clock',
            fontsize=8, color=COLORS['red'], ha='center', style='italic')

    # --- sync_clock_to_slave arrow ---
    draw_dashed_arrow(ax, 5.4 + clk_w, clk_y + clk_h / 2 + 0.15,
                      10.3, clk_y + clk_h / 2 + 0.15,
                      color=COLORS['orange'], lw=1.5)
    ax.text(8.0, clk_y + clk_h / 2 + 0.45, 'sync_clock_to_slave()',
            fontsize=8, color=COLORS['orange'], ha='center')

    # --- get_clock formula ---
    formula_box = FancyBboxPatch((3.5, 0.2), 7, 0.8, boxstyle="round,pad=0.15",
                                 facecolor=COLORS['light_blue'],
                                 edgecolor=COLORS['primary'],
                                 linewidth=1.5, alpha=0.9, zorder=2)
    ax.add_patch(formula_box)
    ax.text(7, 0.6, 'get_clock() = pts_drift + time = pts + (now - last_updated)',
            ha='center', va='center', fontsize=10, color=COLORS['primary'],
            fontweight='bold', zorder=3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, '09-sync-model.png')
    fig.savefig(path, dpi=180, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close(fig)
    print(f'  [OK] {path}')


# ==========================================
# 图2: video_refresh 核心决策流程图
# ==========================================
def gen_video_refresh_flow():
    fig, ax = plt.subplots(1, 1, figsize=(16, 22))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 22)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(8, 21.4, 'video_refresh() 核心决策流程', ha='center',
            fontsize=20, fontweight='bold', color=COLORS['dark'])

    # Helper for diamond (decision) shape
    def draw_diamond(ax, cx, cy, w, h, text, color, fontsize=9, text_color='white'):
        hw, hh = w / 2, h / 2
        diamond = plt.Polygon(
            [(cx, cy + hh), (cx + hw, cy), (cx, cy - hh), (cx - hw, cy)],
            facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.92, zorder=2
        )
        ax.add_patch(diamond)
        ax.text(cx, cy, text, ha='center', va='center',
                fontsize=fontsize, color=text_color, fontweight='bold', zorder=3)

    # --- Flow nodes ---
    x_main = 8.0
    bw, bh = 4.8, 0.85
    dw, dh = 5.0, 1.0

    # Start
    y = 20.2
    draw_box(ax, x_main - bw / 2, y, bw, bh,
             'video_refresh() entry', COLORS['dark'], fontsize=11)

    # External clock check
    y_ext = 19.0
    draw_box(ax, x_main - bw / 2, y_ext, bw, bh,
             'check_external_clock_speed',
             COLORS['orange'], fontsize=9, alpha=0.8)
    draw_arrow(ax, x_main, y, x_main, y_ext + bh, color=COLORS['grey'])
    ax.text(x_main + 2.8, y_ext + bh / 2,
            '(extclk + realtime)',
            fontsize=8, color=COLORS['grey'], va='center')

    # Queue empty check
    y_qchk = 17.6
    draw_diamond(ax, x_main, y_qchk, dw, dh,
                 'pictq\n为空?', COLORS['grey'], fontsize=9)
    draw_arrow(ax, x_main, y_ext, x_main, y_qchk + dh / 2, color=COLORS['grey'])

    # Queue empty -> display
    ax.text(x_main + dw / 2 + 0.3, y_qchk + 0.1, '是', fontsize=9,
            color=COLORS['red'], fontweight='bold')
    draw_arrow(ax, x_main + dw / 2, y_qchk, 14.0, y_qchk,
               color=COLORS['red'], lw=1.2)

    # Get lastvp and vp
    y_get = 16.0
    draw_box(ax, x_main - bw / 2, y_get, bw, bh,
             'lastvp = peek_last()\nvp = peek()',
             COLORS['primary'], fontsize=9)
    draw_arrow(ax, x_main, y_qchk - dh / 2, x_main, y_get + bh,
               color=COLORS['grey'])
    ax.text(x_main - 0.3, y_qchk - dh / 2 - 0.1, '否', fontsize=9,
            color=COLORS['green'], fontweight='bold', ha='right')

    # Serial check
    y_serial = 14.6
    draw_diamond(ax, x_main, y_serial, dw + 0.3, dh,
                 'vp->serial !=\nvideoq.serial?',
                 COLORS['red'], fontsize=9)
    draw_arrow(ax, x_main, y_get, x_main, y_serial + dh / 2, color=COLORS['grey'])

    # Serial mismatch -> skip & retry
    ax.text(x_main + dw / 2 + 0.1, y_serial + 0.1, '是', fontsize=9,
            color=COLORS['red'], fontweight='bold')
    draw_box(ax, 12.5, y_serial - bh / 2, 2.5, bh,
             'frame_queue_next\ngoto retry',
             COLORS['red'], fontsize=8, alpha=0.7)
    draw_arrow(ax, x_main + dw / 2 + 0.15, y_serial, 12.5, y_serial,
               color=COLORS['red'], lw=1.2)
    # retry arrow going up
    draw_arrow(ax, 13.75, y_serial + bh / 2, 13.75, y_qchk,
               color=COLORS['red'], lw=1.2, style='->')
    draw_arrow(ax, 13.75, y_qchk, x_main + dw / 2, y_qchk,
               color=COLORS['red'], lw=1.0, style='->')

    # Serial change check
    y_serchg = 13.3
    draw_box(ax, x_main - bw / 2, y_serchg, bw, bh,
             'serial变化: 重置frame_timer',
             COLORS['teal'], fontsize=9, alpha=0.85)
    draw_arrow(ax, x_main, y_serial - dh / 2, x_main, y_serchg + bh,
               color=COLORS['grey'])
    ax.text(x_main - 0.3, y_serial - dh / 2 - 0.1, '否', fontsize=9,
            color=COLORS['green'], fontweight='bold', ha='right')

    # Paused check
    y_pause = 11.9
    draw_diamond(ax, x_main, y_pause, dw, dh,
                 'is->paused?', COLORS['purple'], fontsize=10)
    draw_arrow(ax, x_main, y_serchg, x_main, y_pause + dh / 2,
               color=COLORS['grey'])

    # Paused -> goto display
    ax.text(x_main + dw / 2 + 0.3, y_pause + 0.1, '是', fontsize=9,
            color=COLORS['purple'], fontweight='bold')
    draw_arrow(ax, x_main + dw / 2, y_pause, 14.0, y_pause,
               color=COLORS['purple'], lw=1.5)
    ax.text(14.3, y_pause, 'goto display', fontsize=9,
            color=COLORS['purple'], fontweight='bold', va='center')

    # Compute delay
    y_delay = 10.3
    draw_box(ax, x_main - bw / 2 - 0.5, y_delay, bw + 1.0, bh + 0.15,
             'last_duration = vp_duration(lastvp, vp)\ndelay = compute_target_delay(last_duration)',
             COLORS['primary'], fontsize=9)
    draw_arrow(ax, x_main, y_pause - dh / 2, x_main, y_delay + bh + 0.15,
               color=COLORS['grey'])
    ax.text(x_main - 0.3, y_pause - dh / 2 - 0.1, '否', fontsize=9,
            color=COLORS['green'], fontweight='bold', ha='right')

    # Time check
    y_timechk = 8.8
    draw_diamond(ax, x_main, y_timechk, dw + 0.8, dh + 0.1,
                 'time < frame_timer\n+ delay?',
                 COLORS['teal'], fontsize=9)
    draw_arrow(ax, x_main, y_delay, x_main, y_timechk + (dh + 0.1) / 2,
               color=COLORS['grey'])

    # Not time yet -> set remaining_time & display
    ax.text(x_main + (dw + 0.8) / 2 + 0.3, y_timechk + 0.1, '是(还没到)', fontsize=8,
            color=COLORS['teal'], fontweight='bold')
    draw_box(ax, 12.0, y_timechk - bh / 2, 3.2, bh,
             'remaining_time\ngoto display',
             COLORS['teal'], fontsize=8, alpha=0.75)
    draw_arrow(ax, x_main + (dw + 0.8) / 2 + 0.05, y_timechk,
               12.0, y_timechk,
               color=COLORS['teal'], lw=1.5)

    # Display target zone (right side)
    display_y_top = y_pause + 0.7
    display_y_bot = y_timechk - 0.7
    disp_rect = FancyBboxPatch((13.4, display_y_bot), 2.2, display_y_top - display_y_bot,
                                boxstyle="round,pad=0.15",
                                facecolor=COLORS['light_purple'],
                                edgecolor=COLORS['purple'],
                                linewidth=2, alpha=0.35, zorder=1)
    ax.add_patch(disp_rect)
    ax.text(14.5, display_y_top + 0.15, 'goto display',
            fontsize=9, color=COLORS['purple'], ha='center', fontweight='bold')

    # Update frame_timer
    y_upd = 7.3
    draw_box(ax, x_main - bw / 2 - 0.3, y_upd, bw + 0.6, bh,
             'frame_timer += delay\n(过大则重置为time)',
             COLORS['green'], fontsize=9, alpha=0.9)
    draw_arrow(ax, x_main, y_timechk - (dh + 0.1) / 2, x_main, y_upd + bh,
               color=COLORS['grey'])
    ax.text(x_main - 0.3, y_timechk - (dh + 0.1) / 2 - 0.1,
            '否(到时间了)', fontsize=8,
            color=COLORS['green'], fontweight='bold', ha='right')

    # Update video pts
    y_pts = 6.1
    draw_box(ax, x_main - bw / 2, y_pts, bw, bh,
             'update_video_pts(vp->pts)',
             COLORS['primary'], fontsize=9, alpha=0.85)
    draw_arrow(ax, x_main, y_upd, x_main, y_pts + bh, color=COLORS['grey'])

    # Late frame drop check
    y_drop = 4.7
    draw_diamond(ax, x_main, y_drop, dw + 1.0, dh + 0.15,
                 'time > frame_timer\n+ next_duration?',
                 COLORS['red'], fontsize=9)
    draw_arrow(ax, x_main, y_pts, x_main, y_drop + (dh + 0.15) / 2,
               color=COLORS['grey'])

    # Late drop -> retry
    ax.text(x_main - (dw + 1.0) / 2 - 0.3, y_drop + 0.1, '是(丢帧)', fontsize=8,
            color=COLORS['red'], fontweight='bold', ha='right')
    draw_box(ax, 0.8, y_drop - bh / 2, 3.0, bh,
             'frame_drops_late++\ngoto retry',
             COLORS['red'], fontsize=8, alpha=0.75)
    draw_arrow(ax, x_main - (dw + 1.0) / 2, y_drop, 3.8, y_drop,
               color=COLORS['red'], lw=1.5)
    # retry arrow going up
    draw_arrow(ax, 2.3, y_drop + bh / 2, 2.3, y_qchk,
               color=COLORS['red'], lw=1.2)
    draw_arrow(ax, 2.3, y_qchk, x_main - dw / 2, y_qchk,
               color=COLORS['red'], lw=1.0, style='->')

    # Subtitle cleanup
    y_sub = 3.2
    draw_box(ax, x_main - bw / 2, y_sub, bw, bh,
             '字幕过期清理 (subpq)',
             COLORS['grey'], fontsize=9, alpha=0.8)
    draw_arrow(ax, x_main, y_drop - (dh + 0.15) / 2, x_main, y_sub + bh,
               color=COLORS['grey'])
    ax.text(x_main + 0.3, y_drop - (dh + 0.15) / 2 - 0.1, '否', fontsize=9,
            color=COLORS['green'], fontweight='bold', ha='left')

    # Final display
    y_disp = 1.8
    draw_box(ax, x_main - bw / 2, y_disp, bw, bh + 0.1,
             'frame_queue_next()\nvideo_display()',
             '#1B5E20', fontsize=10, text_color='white')
    draw_arrow(ax, x_main, y_sub, x_main, y_disp + bh + 0.1,
               color=COLORS['grey'])

    # End
    y_end = 0.6
    draw_box(ax, x_main - 1.5, y_end, 3.0, 0.7,
             'force_refresh = 0', COLORS['dark'], fontsize=9)
    draw_arrow(ax, x_main, y_disp, x_main, y_end + 0.7,
               color=COLORS['grey'])

    # --- Legend at left ---
    legend_x = 0.5
    legend_y = 20.4
    ax.text(legend_x, legend_y, '图例', fontsize=11, fontweight='bold',
            color=COLORS['dark'])
    items = [
        (COLORS['primary'], '处理节点'),
        (COLORS['teal'], '时间判断'),
        (COLORS['red'], '丢帧/跳帧'),
        (COLORS['purple'], '暂停分支'),
        (COLORS['green'], '更新状态'),
    ]
    for i, (c, label) in enumerate(items):
        iy = legend_y - 0.55 - i * 0.5
        rect = FancyBboxPatch((legend_x, iy - 0.15), 0.4, 0.3,
                               boxstyle="round,pad=0.03",
                               facecolor=c, edgecolor='white',
                               linewidth=0.5, alpha=0.9, zorder=2)
        ax.add_patch(rect)
        ax.text(legend_x + 0.6, iy, label, fontsize=9,
                color=COLORS['dark'], va='center')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, '09-video-refresh-flow.png')
    fig.savefig(path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close(fig)
    print(f'  [OK] {path}')


# ==========================================
# 图3: 帧丢弃策略示意图
# ==========================================
def gen_frame_drop():
    fig, axes = plt.subplots(2, 1, figsize=(14, 11),
                              gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.35})
    fig.patch.set_facecolor(COLORS['bg'])

    fig.text(0.5, 0.97, '帧丢弃策略: Early Drop vs Late Drop',
             ha='center', fontsize=18, fontweight='bold', color=COLORS['dark'])

    # ---- Panel 1: Early Drop ----
    ax1 = axes[0]
    ax1.set_xlim(0, 14)
    ax1.set_ylim(0, 6.5)
    ax1.set_aspect('equal')
    ax1.axis('off')

    # Title
    ax1.text(7, 6.1, 'Early Drop (get_video_frame - 解码线程)',
             ha='center', fontsize=14, fontweight='bold', color=COLORS['red'])

    # Pipeline boxes
    stages_y = 4.0
    stage_h = 1.2

    draw_box(ax1, 0.3, stages_y, 2.5, stage_h,
             'Decoder\n解码器', COLORS['primary'], fontsize=10)
    draw_arrow(ax1, 2.8, stages_y + stage_h / 2, 3.5, stages_y + stage_h / 2,
               color=COLORS['grey'], lw=2)

    draw_box(ax1, 3.5, stages_y, 3.2, stage_h,
             'get_video_frame()\n解码得到AVFrame',
             COLORS['green'], fontsize=9)
    draw_arrow(ax1, 6.7, stages_y + stage_h / 2, 7.4, stages_y + stage_h / 2,
               color=COLORS['grey'], lw=2)

    # Decision diamond
    dc_x, dc_y = 9.3, stages_y + stage_h / 2
    dw2, dh2 = 2.6, 1.1
    diamond = plt.Polygon(
        [(dc_x, dc_y + dh2 / 2), (dc_x + dw2 / 2, dc_y),
         (dc_x, dc_y - dh2 / 2), (dc_x - dw2 / 2, dc_y)],
        facecolor=COLORS['red'], edgecolor='white', linewidth=1.5,
        alpha=0.9, zorder=2
    )
    ax1.add_patch(diamond)
    ax1.text(dc_x, dc_y, 'dpts <\nmaster?', ha='center', va='center',
             fontsize=9, color='white', fontweight='bold', zorder=3)

    # Yes -> Drop
    ax1.text(dc_x, dc_y - dh2 / 2 - 0.15, '是(过期)', fontsize=8,
             color=COLORS['red'], ha='center', fontweight='bold')
    draw_box(ax1, dc_x - 1.5, stages_y - 1.8, 3.0, 0.9,
             'av_frame_unref()\nframe_drops_early++',
             COLORS['red'], fontsize=9, alpha=0.85)
    draw_arrow(ax1, dc_x, dc_y - dh2 / 2, dc_x, stages_y - 1.8 + 0.9,
               color=COLORS['red'], lw=1.5)

    # No -> Queue
    ax1.text(dc_x + dw2 / 2 + 0.3, dc_y + 0.1, '否(有效)', fontsize=8,
             color=COLORS['green'], fontweight='bold')
    draw_box(ax1, 11.5, stages_y, 2.2, stage_h,
             'FrameQueue\npictq', COLORS['teal'], fontsize=10)
    draw_arrow(ax1, dc_x + dw2 / 2, dc_y, 11.5, stages_y + stage_h / 2,
               color=COLORS['green'], lw=2)

    # Condition detail
    cond_box = FancyBboxPatch((0.5, 1.0), 5.8, 1.3, boxstyle="round,pad=0.15",
                               facecolor=COLORS['light_red'],
                               edgecolor=COLORS['red'],
                               linewidth=1.5, alpha=0.8, zorder=2)
    ax1.add_patch(cond_box)
    ax1.text(3.4, 2.0, 'Early Drop 5个条件:', fontsize=9,
             fontweight='bold', color=COLORS['red'], ha='center')
    conditions = [
        '1. diff有效  2. |diff| < 10s',
        '3. diff-filter_delay < 0',
        '4. serial匹配  5. 队列非空'
    ]
    for i, c in enumerate(conditions):
        ax1.text(3.4, 1.65 - i * 0.3, c, fontsize=8,
                 color=COLORS['dark'], ha='center')

    # ---- Panel 2: Late Drop ----
    ax2 = axes[1]
    ax2.set_xlim(0, 14)
    ax2.set_ylim(0, 6.5)
    ax2.set_aspect('equal')
    ax2.axis('off')

    # Title
    ax2.text(7, 6.1, 'Late Drop (video_refresh - 主线程)',
             ha='center', fontsize=14, fontweight='bold', color=COLORS['orange'])

    # Timeline
    tl_y = 4.2
    tl_h = 0.7
    ax2.plot([0.5, 13.5], [tl_y, tl_y], color=COLORS['grey'], lw=2, zorder=1)
    ax2.text(0.5, tl_y + 0.15, '时间轴', fontsize=9, color=COLORS['grey'],
             va='bottom')

    # Frames on timeline
    frame_colors = [COLORS['mid_grey'], COLORS['red'], COLORS['red'], COLORS['green']]
    frame_labels = ['lastvp', 'vp(丢弃)', 'vp(丢弃)', 'vp(显示)']
    frame_status = ['已显示', '过期', '过期', '正常']
    frame_xs = [1.5, 4.0, 6.5, 9.5]
    frame_w = 2.0

    for i, (fx, fc, fl, fs) in enumerate(zip(frame_xs, frame_colors, frame_labels, frame_status)):
        alpha = 0.5 if '丢弃' in fl else 0.9
        draw_box(ax2, fx, tl_y - tl_h - 0.1, frame_w, tl_h,
                 fl, fc, fontsize=9, alpha=alpha)
        ax2.text(fx + frame_w / 2, tl_y - tl_h - 0.35, fs,
                 fontsize=8, color=fc, ha='center')

    # Time marker
    time_x = 8.2
    ax2.plot([time_x, time_x], [tl_y - 0.15, tl_y + 0.7],
             color=COLORS['red'], lw=2.5, zorder=5)
    ax2.text(time_x, tl_y + 0.8, 'time (now)', fontsize=9,
             color=COLORS['red'], ha='center', fontweight='bold')

    # Frame timer markers
    ft_xs = [2.5, 5.0, 7.5, 10.5]
    for ftx in ft_xs:
        ax2.plot([ftx, ftx], [tl_y - 0.05, tl_y + 0.25],
                 color=COLORS['teal'], lw=1.5, zorder=3)
    ax2.text(2.5, tl_y + 0.35, 'ft', fontsize=7, color=COLORS['teal'], ha='center')
    ax2.text(5.0, tl_y + 0.35, 'ft+d', fontsize=7, color=COLORS['teal'], ha='center')
    ax2.text(7.5, tl_y + 0.35, 'ft+2d', fontsize=7, color=COLORS['teal'], ha='center')
    ax2.text(10.5, tl_y + 0.35, 'ft+3d', fontsize=7, color=COLORS['teal'], ha='center')

    # Drop arrows
    for dx in [4.0 + frame_w / 2, 6.5 + frame_w / 2]:
        ax2.annotate('', xy=(dx, tl_y - tl_h - 0.7),
                     xytext=(dx, tl_y - tl_h - 0.15),
                     arrowprops=dict(arrowstyle='->', color=COLORS['red'],
                                     lw=2), zorder=4)
    ax2.text(5.75, tl_y - tl_h - 1.1, 'frame_drops_late++',
             fontsize=9, color=COLORS['red'], ha='center', fontweight='bold')

    # Condition
    cond_box2 = FancyBboxPatch((0.5, 0.6), 5.8, 1.0, boxstyle="round,pad=0.15",
                                facecolor=COLORS['light_orange'],
                                edgecolor=COLORS['orange'],
                                linewidth=1.5, alpha=0.8, zorder=2)
    ax2.add_patch(cond_box2)
    ax2.text(3.4, 1.3, 'Late Drop 条件:', fontsize=9,
             fontweight='bold', color=COLORS['orange'], ha='center')
    ax2.text(3.4, 0.9, 'time > frame_timer + next_duration',
             fontsize=9, color=COLORS['dark'], ha='center')

    # Comparison table
    table_box = FancyBboxPatch((7.5, 0.3), 6.0, 1.6, boxstyle="round,pad=0.15",
                                facecolor='white',
                                edgecolor=COLORS['grey'],
                                linewidth=1.5, alpha=0.9, zorder=2)
    ax2.add_patch(table_box)
    ax2.text(10.5, 1.65, 'Early vs Late 对比', fontsize=10,
             fontweight='bold', color=COLORS['dark'], ha='center')

    table_data = [
        ('Early Drop', '解码线程', '入队前'),
        ('Late Drop', '主线程', '取出后'),
    ]
    col_xs = [8.2, 9.8, 11.8]
    headers = ['类型', '执行线程', '丢弃时机']
    for j, hdr in enumerate(headers):
        ax2.text(col_xs[j], 1.35, hdr, fontsize=8, fontweight='bold',
                 color=COLORS['grey'], ha='center')
    for i, (t, thread, timing) in enumerate(table_data):
        row_y = 1.05 - i * 0.35
        color = COLORS['red'] if i == 0 else COLORS['orange']
        ax2.text(col_xs[0], row_y, t, fontsize=8, color=color,
                 ha='center', fontweight='bold')
        ax2.text(col_xs[1], row_y, thread, fontsize=8,
                 color=COLORS['dark'], ha='center')
        ax2.text(col_xs[2], row_y, timing, fontsize=8,
                 color=COLORS['dark'], ha='center')

    path = os.path.join(OUTPUT_DIR, '09-frame-drop.png')
    fig.savefig(path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close(fig)
    print(f'  [OK] {path}')


# ==========================================
# Main
# ==========================================
if __name__ == '__main__':
    print('Generating images for article 09...')
    gen_sync_model()
    gen_video_refresh_flow()
    gen_frame_drop()
    print('Done!')
