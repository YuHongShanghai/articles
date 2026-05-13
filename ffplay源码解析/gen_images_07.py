#!/usr/bin/env python3
"""第7篇文章图例：字幕处理与渲染"""

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
# 图1: 字幕处理完整数据流图
# ==========================================
def gen_subtitle_data_flow():
    fig, ax = plt.subplots(1, 1, figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7, 8.6, '字幕处理完整数据流', ha='center',
            fontsize=18, fontweight='bold', color='#212121')

    # ---- 第一行：Demux 阶段 ----
    phase_y = 7.2
    ax.text(1.0, phase_y + 0.7, 'Demux', fontsize=11, fontweight='bold',
            color=COLORS['green'], ha='center')

    draw_box(ax, 0.2, phase_y, 1.6, 0.55, '媒体文件', COLORS['grey'], fontsize=9)
    draw_arrow(ax, 1.8, phase_y + 0.27, 2.6, phase_y + 0.27,
               color=COLORS['green'], lw=2)

    draw_box(ax, 2.6, phase_y - 0.1, 2.2, 0.75, 'av_read_frame()\nread_thread',
             COLORS['green'], fontsize=8)
    draw_arrow(ax, 4.8, phase_y + 0.27, 5.6, phase_y + 0.27,
               color=COLORS['green'], lw=2)

    draw_box(ax, 5.6, phase_y, 2.0, 0.55, 'subtitleq\nPacketQueue',
             COLORS['teal'], fontsize=8)

    # ---- 第二行：Decode 阶段 ----
    dec_y = 5.6
    ax.text(1.0, dec_y + 0.7, 'Decode', fontsize=11, fontweight='bold',
            color=COLORS['purple'], ha='center')

    draw_arrow(ax, 6.6, phase_y, 6.6, dec_y + 0.65, color='#BDBDBD', lw=2)

    draw_box(ax, 5.0, dec_y, 3.2, 0.6, 'avcodec_decode_subtitle2()\nsubtitle_thread',
             COLORS['purple'], fontsize=8)
    draw_arrow(ax, 8.2, dec_y + 0.3, 9.2, dec_y + 0.3,
               color=COLORS['purple'], lw=2)

    # format 判断菱形
    diamond_x, diamond_y = 10.3, dec_y + 0.3
    diamond = plt.Polygon([
        [diamond_x, diamond_y + 0.55],
        [diamond_x + 0.9, diamond_y],
        [diamond_x, diamond_y - 0.55],
        [diamond_x - 0.9, diamond_y]
    ], facecolor=COLORS['yellow'], edgecolor='#F9A825', linewidth=2, zorder=2)
    ax.add_patch(diamond)
    ax.text(diamond_x, diamond_y, 'format\n==0 ?', ha='center', va='center',
            fontsize=7, fontweight='bold', color='#424242', zorder=3)

    # bitmap 路径
    draw_arrow(ax, diamond_x, diamond_y - 0.55, diamond_x, dec_y - 0.9,
               color=COLORS['primary'], lw=2)
    ax.text(diamond_x + 0.25, diamond_y - 0.7, 'bitmap', fontsize=7,
            color=COLORS['primary'], fontweight='bold')

    draw_box(ax, 9.3, dec_y - 1.55, 2.0, 0.55, 'subpq\nFrameQueue',
             COLORS['teal'], fontsize=8)

    # text 丢弃路径
    draw_arrow(ax, diamond_x + 0.9, diamond_y, 12.5, diamond_y,
               color=COLORS['red'], lw=2)
    ax.text(12.6, diamond_y + 0.1, 'text: avsubtitle_free()\n丢弃', fontsize=7,
            color=COLORS['red'], ha='left')

    # ---- 第三行：Render 阶段 ----
    ren_y = 3.0
    ax.text(1.0, ren_y + 0.7, 'Render', fontsize=11, fontweight='bold',
            color=COLORS['orange'], ha='center')

    draw_arrow(ax, 10.3, dec_y - 1.55, 10.3, ren_y + 0.65,
               color='#BDBDBD', lw=2)

    # 渲染步骤
    steps_x = 2.0
    step_w = 2.6
    step_h = 0.5
    step_gap = 0.15

    render_steps = [
        ('PAL8 -> BGRA', 'sws_scale 像素转换', COLORS['orange']),
        ('SDL_LockTexture', '写入 sub_texture', COLORS['orange']),
        ('SDL_RenderCopy', '叠加到视频帧上方', COLORS['primary']),
    ]

    for i, (title, desc, color) in enumerate(render_steps):
        sx = steps_x + i * (step_w + 0.5)
        draw_label_box(ax, sx, ren_y, step_w, step_h + 0.15, title, desc, color,
                       title_size=8, desc_size=6.5)
        if i < len(render_steps) - 1:
            draw_arrow(ax, sx + step_w, ren_y + step_h / 2 + 0.07,
                       sx + step_w + 0.5, ren_y + step_h / 2 + 0.07,
                       color='#BDBDBD', lw=2)

    # video_image_display 标签
    box_ren = FancyBboxPatch((1.6, ren_y - 0.25), 9.5, 1.1,
                             boxstyle="round,pad=0.12", facecolor='none',
                             edgecolor=COLORS['orange'], linewidth=1.5,
                             linestyle='--', alpha=0.6, zorder=1)
    ax.add_patch(box_ren)
    ax.text(6.35, ren_y - 0.15, 'video_image_display()', fontsize=8,
            color=COLORS['orange'], ha='center', style='italic')

    # ---- 第四行：Expire 阶段 ----
    exp_y = 1.2
    ax.text(1.0, exp_y + 0.7, 'Expire', fontsize=11, fontweight='bold',
            color=COLORS['red'], ha='center')

    expire_steps = [
        ('serial 检查', 'seek 后旧字幕丢弃', COLORS['red']),
        ('end_display_time\n超时检查', '自然过期', COLORS['red']),
        ('memset 清零', '清除纹理区域', COLORS['grey']),
        ('frame_queue_next', '出队释放', COLORS['grey']),
    ]

    for i, (title, desc, color) in enumerate(expire_steps):
        sx = 2.0 + i * 2.7
        draw_label_box(ax, sx, exp_y, 2.4, step_h + 0.15, title, desc, color,
                       title_size=8, desc_size=6.5)
        if i < len(expire_steps) - 1:
            draw_arrow(ax, sx + 2.4, exp_y + step_h / 2 + 0.07,
                       sx + 2.7, exp_y + step_h / 2 + 0.07,
                       color='#BDBDBD', lw=2)

    box_exp = FancyBboxPatch((1.6, exp_y - 0.25), 11.6, 1.1,
                             boxstyle="round,pad=0.12", facecolor='none',
                             edgecolor=COLORS['red'], linewidth=1.5,
                             linestyle='--', alpha=0.6, zorder=1)
    ax.add_patch(box_exp)
    ax.text(7.4, exp_y - 0.15, 'video_refresh()', fontsize=8,
            color=COLORS['red'], ha='center', style='italic')

    # 阶段连接线
    draw_arrow(ax, 6.35, ren_y, 6.35, exp_y + 1.0, color='#BDBDBD', lw=1.5)

    ax.text(7, 0.3, '图 7-1: 字幕处理完整数据流 (demux -> decode -> render -> expire)',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07-subtitle-data-flow.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 07-subtitle-data-flow.png")


# ==========================================
# 图2: 字幕时间轴与显示窗口示意图
# ==========================================
def gen_subtitle_timeline():
    fig, ax = plt.subplots(1, 1, figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(6.5, 6.6, '字幕时间轴与显示窗口', ha='center',
            fontsize=18, fontweight='bold', color='#212121')

    # ---- 时间轴主线 ----
    timeline_y = 4.5
    ax.annotate('', xy=(12.5, timeline_y), xytext=(0.5, timeline_y),
                arrowprops=dict(arrowstyle='->', color='#424242', lw=2.5))
    ax.text(12.7, timeline_y, 't', fontsize=12, fontweight='bold',
            color='#424242', va='center')
    ax.text(6.5, timeline_y - 0.35, '时间轴 (秒)', fontsize=9,
            color='#757575', ha='center')

    # ---- 字幕1 ----
    sub1_pts = 2.0
    sub1_start = 2.0
    sub1_end = 5.5
    sub1_color = COLORS['primary']

    # pts 标记
    ax.plot([sub1_pts, sub1_pts], [timeline_y - 0.15, timeline_y + 0.15],
            color=sub1_color, lw=2.5)
    ax.text(sub1_pts, timeline_y + 0.3, 'pts1', fontsize=8, fontweight='bold',
            color=sub1_color, ha='center')

    # 显示窗口
    bar_y1 = 5.2
    bar_h = 0.45
    bar1 = FancyBboxPatch((sub1_start, bar_y1), sub1_end - sub1_start, bar_h,
                          boxstyle="round,pad=0.03", facecolor=sub1_color,
                          edgecolor='white', linewidth=1.5, alpha=0.85, zorder=2)
    ax.add_patch(bar1)
    ax.text((sub1_start + sub1_end) / 2, bar_y1 + bar_h / 2,
            '字幕1 显示窗口', fontsize=8, color='white',
            fontweight='bold', ha='center', va='center', zorder=3)

    # start/end 虚线
    ax.plot([sub1_start, sub1_start], [timeline_y + 0.15, bar_y1],
            '--', color=sub1_color, lw=1, alpha=0.6)
    ax.plot([sub1_end, sub1_end], [timeline_y + 0.15, bar_y1],
            '--', color=sub1_color, lw=1, alpha=0.6)

    # 标注 start_display_time
    ax.annotate('', xy=(sub1_start, timeline_y - 0.5),
                xytext=(sub1_pts, timeline_y - 0.5),
                arrowprops=dict(arrowstyle='<->', color=sub1_color, lw=1.5))
    ax.text((sub1_pts + sub1_start) / 2, timeline_y - 0.7,
            'start_display_time\n(0 ms)', fontsize=6.5,
            color=sub1_color, ha='center')

    # 标注 end_display_time
    ax.annotate('', xy=(sub1_end, timeline_y - 1.2),
                xytext=(sub1_pts, timeline_y - 1.2),
                arrowprops=dict(arrowstyle='<->', color=sub1_color, lw=1.5))
    ax.text((sub1_pts + sub1_end) / 2, timeline_y - 1.5,
            'end_display_time (3500 ms)', fontsize=6.5,
            color=sub1_color, ha='center')

    # ---- 字幕2 ----
    sub2_pts = 6.5
    sub2_start = 6.5
    sub2_end = 10.5
    sub2_color = COLORS['green']

    # pts 标记
    ax.plot([sub2_pts, sub2_pts], [timeline_y - 0.15, timeline_y + 0.15],
            color=sub2_color, lw=2.5)
    ax.text(sub2_pts, timeline_y + 0.3, 'pts2', fontsize=8, fontweight='bold',
            color=sub2_color, ha='center')

    # 显示窗口
    bar2 = FancyBboxPatch((sub2_start, bar_y1), sub2_end - sub2_start, bar_h,
                          boxstyle="round,pad=0.03", facecolor=sub2_color,
                          edgecolor='white', linewidth=1.5, alpha=0.85, zorder=2)
    ax.add_patch(bar2)
    ax.text((sub2_start + sub2_end) / 2, bar_y1 + bar_h / 2,
            '字幕2 显示窗口', fontsize=8, color='white',
            fontweight='bold', ha='center', va='center', zorder=3)

    # start/end 虚线
    ax.plot([sub2_start, sub2_start], [timeline_y + 0.15, bar_y1],
            '--', color=sub2_color, lw=1, alpha=0.6)
    ax.plot([sub2_end, sub2_end], [timeline_y + 0.15, bar_y1],
            '--', color=sub2_color, lw=1, alpha=0.6)

    # 标注
    ax.annotate('', xy=(sub2_start, timeline_y - 0.5),
                xytext=(sub2_pts, timeline_y - 0.5),
                arrowprops=dict(arrowstyle='<->', color=sub2_color, lw=1.5))
    ax.text((sub2_pts + sub2_start) / 2, timeline_y - 0.7,
            'start_display_time\n(0 ms)', fontsize=6.5,
            color=sub2_color, ha='center')

    ax.annotate('', xy=(sub2_end, timeline_y - 1.2),
                xytext=(sub2_pts, timeline_y - 1.2),
                arrowprops=dict(arrowstyle='<->', color=sub2_color, lw=1.5))
    ax.text((sub2_pts + sub2_end) / 2, timeline_y - 1.5,
            'end_display_time (4000 ms)', fontsize=6.5,
            color=sub2_color, ha='center')

    # ---- 时间刻度 ----
    for t in range(0, 13):
        tx = 0.5 + t
        if tx <= 12.3:
            ax.plot([tx, tx], [timeline_y - 0.08, timeline_y + 0.08],
                    color='#9E9E9E', lw=1)
            ax.text(tx, timeline_y - 0.25, str(t), fontsize=7,
                    color='#9E9E9E', ha='center')

    # ---- 判断公式说明 ----
    formula_y = 1.6
    formulas = [
        ('渲染判断 (video_image_display):',
         'vp->pts >= sp->pts + start_display_time / 1000',
         COLORS['orange']),
        ('过期判断 (video_refresh):',
         'vidclk.pts > sp->pts + end_display_time / 1000',
         COLORS['red']),
    ]

    for i, (label, formula, color) in enumerate(formulas):
        fy = formula_y - i * 0.7
        box_f = FancyBboxPatch((1.5, fy - 0.05), 10.0, 0.5,
                               boxstyle="round,pad=0.06", facecolor='white',
                               edgecolor=color, linewidth=2, alpha=0.9, zorder=2)
        ax.add_patch(box_f)

        circle = plt.Circle((2.0, fy + 0.2), 0.18, facecolor=color,
                             edgecolor='white', linewidth=1.5, zorder=3)
        ax.add_patch(circle)
        ax.text(2.0, fy + 0.2, str(i + 1), fontsize=8, color='white',
                fontweight='bold', ha='center', va='center', zorder=4)

        ax.text(2.4, fy + 0.28, label, fontsize=8, fontweight='bold',
                color=color, va='center', zorder=3)
        ax.text(2.4, fy + 0.06, formula, fontsize=7.5,
                color='#424242', va='center', zorder=3,
                family='monospace')

    ax.text(6.5, 0.3, '图 7-2: 字幕时间轴与显示窗口 (pts + start/end_display_time)',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07-subtitle-timeline.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 07-subtitle-timeline.png")


if __name__ == '__main__':
    gen_subtitle_data_flow()
    gen_subtitle_timeline()
    print("\n07 done!")
