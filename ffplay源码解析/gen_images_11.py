#!/usr/bin/env python3
"""第11篇文章图例：事件处理与用户交互"""

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
    'indigo': '#283593',
    'cyan': '#00695C',
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


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=1.5, style='->', zorder=1):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw), zorder=zorder)


def draw_label_box(ax, x, y, w, h, title, desc, color, title_size=9, desc_size=7):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                         facecolor='white', edgecolor=color,
                         linewidth=2.5, alpha=0.95, zorder=2)
    ax.add_patch(box)
    if desc:
        ax.text(x + w / 2, y + h * 0.62, title, fontsize=title_size,
                fontweight='bold', color=color, ha='center', va='center', zorder=3)
        ax.text(x + w / 2, y + h * 0.28, desc, fontsize=desc_size,
                color='#424242', ha='center', va='center', zorder=3)
    else:
        ax.text(x + w / 2, y + h / 2, title, fontsize=title_size,
                fontweight='bold', color=color, ha='center', va='center', zorder=3)


def draw_dashed_box(ax, x, y, w, h, color, linewidth=1.5, label=None, label_pos='bottom'):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                         facecolor='none', edgecolor=color,
                         linewidth=linewidth, linestyle='--', alpha=0.6, zorder=1)
    ax.add_patch(box)
    if label:
        if label_pos == 'bottom':
            ax.text(x + w / 2, y - 0.12, label, fontsize=8,
                    color=color, ha='center', style='italic')
        else:
            ax.text(x + w / 2, y + h + 0.12, label, fontsize=8,
                    color=color, ha='center', style='italic')


# ==========================================
# 图1: event_loop 与 video_refresh 协作关系图
# ==========================================
def gen_event_loop():
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7.5, 9.5, 'event_loop 与 video_refresh 协作关系', ha='center',
            fontsize=18, fontweight='bold', color='#212121')

    # ---- main() 入口 ----
    draw_box(ax, 6.0, 8.6, 3.0, 0.55, 'main()', COLORS['dark'], fontsize=11)
    draw_arrow(ax, 7.5, 8.6, 7.5, 8.15, color=COLORS['dark'], lw=2)

    # ---- event_loop 大框 ----
    el_x, el_y, el_w, el_h = 0.5, 0.6, 14.0, 7.4
    draw_dashed_box(ax, el_x, el_y, el_w, el_h, COLORS['primary'],
                    linewidth=2, label='event_loop() - for(;;) 无限循环', label_pos='top')

    # ---- refresh_loop_wait_event 区域 ----
    rl_x, rl_y, rl_w, rl_h = 1.0, 3.2, 6.5, 4.5
    rlbox = FancyBboxPatch((rl_x, rl_y), rl_w, rl_h,
                           boxstyle="round,pad=0.15",
                           facecolor=COLORS['light_blue'], edgecolor=COLORS['primary'],
                           linewidth=2, alpha=0.4, zorder=0)
    ax.add_patch(rlbox)
    ax.text(rl_x + rl_w / 2, rl_y + rl_h - 0.2,
            'refresh_loop_wait_event()', fontsize=11,
            fontweight='bold', color=COLORS['primary'], ha='center')

    # SDL_PumpEvents
    draw_box(ax, 1.5, 6.6, 2.5, 0.5, 'SDL_PumpEvents()', COLORS['teal'], fontsize=8)
    draw_arrow(ax, 2.75, 6.6, 2.75, 6.2, color=COLORS['teal'], lw=1.5)

    # SDL_PeepEvents 判断
    diamond_x, diamond_y = 2.75, 5.7
    diamond = plt.Polygon([
        [diamond_x, diamond_y + 0.45],
        [diamond_x + 1.1, diamond_y],
        [diamond_x, diamond_y - 0.45],
        [diamond_x - 1.1, diamond_y]
    ], facecolor=COLORS['yellow'], edgecolor='#F9A825', linewidth=2, zorder=2)
    ax.add_patch(diamond)
    ax.text(diamond_x, diamond_y, 'PeepEvents\n有事件?', ha='center', va='center',
            fontsize=7, fontweight='bold', color='#424242', zorder=3)

    # 有事件 -> 返回事件
    draw_arrow(ax, diamond_x + 1.1, diamond_y, 8.0, diamond_y,
               color=COLORS['green'], lw=2)
    ax.text(5.0, diamond_y + 0.12, '有事件', fontsize=8,
            color=COLORS['green'], fontweight='bold')

    # 无事件 -> 睡眠
    draw_arrow(ax, diamond_x, diamond_y - 0.45, diamond_x, 4.75,
               color=COLORS['orange'], lw=2)
    ax.text(diamond_x + 0.15, diamond_y - 0.7, '无事件', fontsize=8,
            color=COLORS['orange'], fontweight='bold')

    # av_usleep(remaining_time)
    draw_box(ax, 1.5, 4.2, 2.5, 0.5, 'av_usleep(remaining_time)',
             COLORS['grey'], fontsize=7.5)
    draw_arrow(ax, 2.75, 4.2, 2.75, 3.85, color='#BDBDBD', lw=1.5)

    # video_refresh
    draw_box(ax, 4.5, 3.45, 2.6, 0.65, 'video_refresh()\n更新 remaining_time',
             COLORS['orange'], fontsize=8)

    draw_arrow(ax, 4.0, 4.45, 4.5, 4.0, color=COLORS['orange'], lw=1.5)

    # video_refresh 回到 PumpEvents (循环)
    ax.annotate('', xy=(2.0, 6.6), xytext=(5.8, 4.1),
                arrowprops=dict(arrowstyle='->', color='#90A4AE', lw=1.5,
                                connectionstyle='arc3,rad=0.4'), zorder=1)
    ax.text(5.2, 5.8, '循环', fontsize=7, color='#78909C', style='italic')

    # ---- SDL_Event 分发区域 ----
    ev_x, ev_y = 8.0, 1.0
    evbox = FancyBboxPatch((ev_x, ev_y), 6.0, 6.2,
                           boxstyle="round,pad=0.15",
                           facecolor=COLORS['light_green'], edgecolor=COLORS['green'],
                           linewidth=2, alpha=0.35, zorder=0)
    ax.add_patch(evbox)
    ax.text(ev_x + 3.0, ev_y + 6.0, 'SDL_Event 事件分发 (switch)',
            fontsize=11, fontweight='bold', color=COLORS['green'], ha='center')

    # 事件类型列表
    events = [
        ('SDL_KEYDOWN', '键盘事件', COLORS['primary']),
        ('SDL_MOUSEBUTTONDOWN', '鼠标按下', COLORS['purple']),
        ('SDL_MOUSEMOTION', '鼠标移动', COLORS['purple']),
        ('SDL_WINDOWEVENT', '窗口事件', COLORS['teal']),
        ('SDL_QUIT', '退出事件', COLORS['red']),
    ]

    ey = 6.2
    for i, (name, desc, color) in enumerate(events):
        by = ey - i * 0.85
        draw_box(ax, 8.5, by, 2.5, 0.55, name, color, fontsize=7.5)
        ax.text(11.2, by + 0.27, desc, fontsize=8, color='#424242', va='center')

    # 键盘事件展开
    kb_items = [
        ('ESC/Q: do_exit()', COLORS['red']),
        ('F: toggle_full_screen()', COLORS['primary']),
        ('P/Space: toggle_pause()', COLORS['green']),
        ('M: toggle_mute()', COLORS['grey']),
        ('0/9: update_volume()', COLORS['amber']),
        ('S: step_to_next_frame()', COLORS['purple']),
        ('A/V/T: stream_cycle_channel()', COLORS['teal']),
        ('Left/Right/Up/Down: stream_seek()', COLORS['orange']),
    ]

    ax.text(12.5, 6.45, '键盘处理:', fontsize=7.5, color=COLORS['primary'],
            fontweight='bold')
    for i, (text, color) in enumerate(kb_items):
        ky = 6.15 - i * 0.36
        ax.plot(12.5, ky, 'o', color=color, markersize=4, zorder=3)
        ax.text(12.75, ky, text, fontsize=6.5, color='#424242', va='center')

    # remaining_time 说明
    info_y = 1.2
    info_items = [
        'REFRESH_RATE = 0.01 (10ms)',
        'CURSOR_HIDE_DELAY = 1s',
        'SDL_VOLUME_STEP = 0.75 dB',
    ]
    draw_dashed_box(ax, 1.0, 0.8, 6.5, 1.9, COLORS['grey'], linewidth=1)
    ax.text(4.25, 2.4, '关键常量', fontsize=9, fontweight='bold',
            color=COLORS['grey'], ha='center')
    for i, text in enumerate(info_items):
        ax.text(1.5, 2.05 - i * 0.35, text, fontsize=8, color='#424242',
                family='monospace')

    ax.text(7.5, 0.15, '图 11-1: event_loop 与 video_refresh 协作关系',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '11-event-loop.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 11-event-loop.png")


# ==========================================
# 图2: Seek 操作完整链路图
# ==========================================
def gen_seek_flow():
    fig, ax = plt.subplots(1, 1, figsize=(15, 9))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7.5, 8.6, 'Seek 操作完整链路', ha='center',
            fontsize=18, fontweight='bold', color='#212121')

    # ---- 阶段1: 用户操作 ----
    ax.text(0.8, 8.0, '1', fontsize=14, fontweight='bold', color='white',
            ha='center', va='center', zorder=4,
            bbox=dict(boxstyle='circle,pad=0.3', facecolor=COLORS['primary'],
                      edgecolor='white', linewidth=2))
    ax.text(1.5, 8.0, '用户操作', fontsize=11, fontweight='bold',
            color=COLORS['primary'], va='center')

    user_actions = [
        ('Left/Right', '快进快退 10s', 3.5),
        ('Up/Down', '快进快退 60s', 6.5),
        ('PageUp/Down', '章节跳转/600s', 9.5),
        ('鼠标右键', '按比例 seek', 12.5),
    ]
    for text, desc, bx in user_actions:
        draw_box(ax, bx - 1.1, 7.5, 2.2, 0.45, text, COLORS['primary'], fontsize=8)
        ax.text(bx, 7.35, desc, fontsize=6.5, color='#757575', ha='center')

    # 箭头：用户操作 -> stream_seek
    for _, _, bx in user_actions:
        draw_arrow(ax, bx, 7.5, bx, 7.1, color='#BDBDBD', lw=1)

    # ---- 阶段2: stream_seek (主线程) ----
    phase2_y = 6.2
    ax.text(0.8, phase2_y + 0.3, '2', fontsize=14, fontweight='bold', color='white',
            ha='center', va='center', zorder=4,
            bbox=dict(boxstyle='circle,pad=0.3', facecolor=COLORS['green'],
                      edgecolor='white', linewidth=2))
    ax.text(1.5, phase2_y + 0.3, '提交请求', fontsize=11, fontweight='bold',
            color=COLORS['green'], va='center')

    # stream_seek 函数框
    ss_x, ss_w = 3.5, 8.0
    ssbox = FancyBboxPatch((ss_x, phase2_y - 0.15), ss_w, 0.9,
                           boxstyle="round,pad=0.1",
                           facecolor='white', edgecolor=COLORS['green'],
                           linewidth=2.5, alpha=0.95, zorder=2)
    ax.add_patch(ssbox)
    ax.text(ss_x + 0.3, phase2_y + 0.5, 'stream_seek()', fontsize=10,
            fontweight='bold', color=COLORS['green'], va='center', zorder=3)

    seek_steps = [
        ('seek_pos = pos', 4.0),
        ('seek_rel = rel', 6.5),
        ('seek_flags', 8.5),
        ('seek_req = 1', 10.2),
    ]
    for text, sx in seek_steps:
        ax.text(sx, phase2_y + 0.1, text, fontsize=7.5, color='#424242',
                ha='center', family='monospace', zorder=3)

    # CondSignal
    draw_box(ax, 11.5, phase2_y - 0.05, 2.5, 0.55,
             'SDL_CondSignal()\n唤醒 read_thread',
             COLORS['green'], fontsize=7.5)

    # 大箭头向下
    draw_arrow(ax, 7.5, phase2_y - 0.15, 7.5, 5.3, color=COLORS['green'], lw=2.5)
    ax.text(7.8, 5.55, '唤醒', fontsize=9, color=COLORS['green'], fontweight='bold')

    # ---- 阶段3: read_thread 处理 ----
    phase3_y = 4.2
    ax.text(0.8, phase3_y + 0.65, '3', fontsize=14, fontweight='bold', color='white',
            ha='center', va='center', zorder=4,
            bbox=dict(boxstyle='circle,pad=0.3', facecolor=COLORS['orange'],
                      edgecolor='white', linewidth=2))
    ax.text(1.5, phase3_y + 0.65, 'read_thread 处理', fontsize=11, fontweight='bold',
            color=COLORS['orange'], va='center')

    # avformat_seek_file
    draw_box(ax, 3.0, phase3_y + 0.3, 3.0, 0.55,
             'avformat_seek_file()', COLORS['orange'], fontsize=9)
    draw_arrow(ax, 6.0, phase3_y + 0.57, 6.8, phase3_y + 0.57,
               color=COLORS['orange'], lw=2)

    # packet_queue_flush x3
    flush_x = 6.8
    queues = [
        ('audioq flush', COLORS['purple']),
        ('videoq flush', COLORS['primary']),
        ('subtitleq flush', COLORS['teal']),
    ]
    for i, (text, color) in enumerate(queues):
        qx = flush_x + i * 2.4
        draw_box(ax, qx, phase3_y + 0.3, 2.1, 0.55, text, color, fontsize=7.5)

    # flush 说明
    ax.text(9.2, phase3_y, 'packet_queue_flush: 清空旧数据 + 推入 flush_pkt (serial++)',
            fontsize=7, color='#757575', ha='center', style='italic')

    # set_clock + 重置状态
    draw_box(ax, 3.0, phase3_y - 0.7, 2.5, 0.5, 'set_clock(extclk)',
             COLORS['grey'], fontsize=8)
    draw_box(ax, 5.8, phase3_y - 0.7, 2.2, 0.5, 'seek_req = 0',
             COLORS['grey'], fontsize=8)
    draw_box(ax, 8.3, phase3_y - 0.7, 1.8, 0.5, 'eof = 0',
             COLORS['grey'], fontsize=8)
    draw_box(ax, 10.4, phase3_y - 0.7, 2.8, 0.5, 'queue_attachments = 1',
             COLORS['grey'], fontsize=8)

    draw_arrow(ax, 4.25, phase3_y + 0.3, 4.25, phase3_y - 0.15,
               color='#BDBDBD', lw=1.5)

    # ---- 阶段4: 解码器响应 ----
    phase4_y = 2.3
    ax.text(0.8, phase4_y + 0.3, '4', fontsize=14, fontweight='bold', color='white',
            ha='center', va='center', zorder=4,
            bbox=dict(boxstyle='circle,pad=0.3', facecolor=COLORS['purple'],
                      edgecolor='white', linewidth=2))
    ax.text(1.5, phase4_y + 0.3, '解码器响应', fontsize=11, fontweight='bold',
            color=COLORS['purple'], va='center')

    draw_arrow(ax, 7.5, phase3_y - 0.7, 7.5, phase4_y + 0.65,
               color=COLORS['purple'], lw=2)

    dec_steps = [
        ('检测到 flush_pkt', '解码器收到 serial\n变化信号', COLORS['purple']),
        ('avcodec_flush_buffers()', '清空解码器\n内部缓冲', COLORS['purple']),
        ('丢弃旧 serial 帧', 'FrameQueue 中旧帧\n被跳过', COLORS['red']),
    ]
    for i, (title, desc, color) in enumerate(dec_steps):
        dx = 3.0 + i * 3.5
        draw_label_box(ax, dx, phase4_y - 0.15, 3.0, 0.75, title, desc, color,
                       title_size=8, desc_size=6.5)
        if i < len(dec_steps) - 1:
            draw_arrow(ax, dx + 3.0, phase4_y + 0.22, dx + 3.5, phase4_y + 0.22,
                       color='#BDBDBD', lw=1.5)

    # ---- 阶段5: 新数据播放 ----
    phase5_y = 0.9
    ax.text(0.8, phase5_y + 0.3, '5', fontsize=14, fontweight='bold', color='white',
            ha='center', va='center', zorder=4,
            bbox=dict(boxstyle='circle,pad=0.3', facecolor=COLORS['cyan'],
                      edgecolor='white', linewidth=2))
    ax.text(1.5, phase5_y + 0.3, '新数据播放', fontsize=11, fontweight='bold',
            color=COLORS['cyan'], va='center')

    draw_arrow(ax, 7.5, phase4_y - 0.15, 7.5, phase5_y + 0.65,
               color=COLORS['cyan'], lw=2)

    final_steps = [
        ('av_read_frame()', '从新位置\n读取数据', COLORS['cyan']),
        ('解码新帧', '新 serial 的\n帧入队', COLORS['green']),
        ('video_refresh()', '渲染新位置\n的画面', COLORS['orange']),
        ('audio_callback()', '输出新位置\n的音频', COLORS['primary']),
    ]
    for i, (title, desc, color) in enumerate(final_steps):
        fx = 3.0 + i * 2.8
        draw_label_box(ax, fx, phase5_y - 0.15, 2.4, 0.75, title, desc, color,
                       title_size=8, desc_size=6.5)
        if i < len(final_steps) - 1:
            draw_arrow(ax, fx + 2.4, phase5_y + 0.22, fx + 2.8, phase5_y + 0.22,
                       color='#BDBDBD', lw=1.5)

    ax.text(7.5, 0.15, '图 11-2: Seek 操作完整链路 (用户操作 -> stream_seek -> read_thread -> flush -> 新数据播放)',
            ha='center', fontsize=9, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '11-seek-flow.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 11-seek-flow.png")


if __name__ == '__main__':
    gen_event_loop()
    gen_seek_flow()
    print("\n11 done!")
