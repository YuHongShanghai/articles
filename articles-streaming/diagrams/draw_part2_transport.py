#!/usr/bin/env python3
"""Part 2: 传输协议 - 生成 RTP/RTCP/SDP/Jitter/FEC 相关的 9 张技术插图。"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    COLORS, save_fig, new_fig, no_axes,
    draw_box, draw_arrow, draw_brace_text,
    draw_sequence_arrow, draw_dashed_line,
    draw_field_row, draw_timeline_entity,
    plt, np, FancyBboxPatch, mpatches,
)


# ── 1. RTP 报文结构比特位图 ─────────────────────────────────────────────────
def draw_rtp_header():
    fig, ax = new_fig(10, 4)
    ax = no_axes(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(1.8, 8.0)

    ax.text(5, 7.5, 'RTP 固定头部结构（12 字节）', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    start_x = 1.0
    for i in range(0, 33, 8):
        bit_x = start_x + i * (8.0 / 32)
        ax.text(bit_x, 6.7, str(i), ha='center', va='center',
                fontsize=7, color=COLORS['mid_text'])

    draw_field_row(ax, start_x, 5.8, [
        ('V', 2), ('P', 1), ('X', 1), ('CC', 4),
        ('M', 1), ('PT', 7), ('序列号', 16),
    ], height=0.7, fontsize=8)

    draw_field_row(ax, start_x, 4.8, [
        ('时间戳 Timestamp', 32),
    ], height=0.7, fontsize=10)

    draw_field_row(ax, start_x, 3.8, [
        ('同步源标识 SSRC', 32),
    ], height=0.7, fontsize=10)

    for i, label in enumerate(['字节 0-3', '字节 4-7', '字节 8-11']):
        ax.text(start_x - 0.15, 6.15 - i, label, ha='right', va='center',
                fontsize=7, color=COLORS['mid_text'])

    annotations = [
        (start_x + 0.25, 3.3, 'V: 版本号(2)'),
        (start_x + 2.0, 3.3, 'P: 填充(1)  X: 扩展(1)'),
        (start_x + 4.5, 3.3, 'CC: CSRC计数(4)  M: 标记(1)'),
    ]
    for x, y, text in annotations:
        ax.text(x, y, text, ha='left', va='center',
                fontsize=7, color=COLORS['mid_text'])

    ax.text(5, 2.5,
            '● 固定头部 12 字节 = 3 × 32 位\n'
            '● 之后可选 CSRC 列表（每个 4 字节，最多 15 个）',
            ha='center', va='center', fontsize=9, color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.5', facecolor=COLORS['light_bg'],
                      edgecolor=COLORS['border']))
    save_fig(fig, 'rtp_header')


# ── 2. 音视频同步时序图 ─────────────────────────────────────────────────────
def draw_av_sync():
    fig, ax = new_fig(12, 6)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)

    ax.text(6, 7.5, '音视频同步原理（基于 RTCP SR）', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # 视频 RTP 流
    ax.text(0.5, 6.2, '视频 RTP 流', ha='left', va='center',
            fontsize=10, fontweight='bold', color=COLORS['primary'])
    ax.plot([1.5, 11], [5.5, 5.5], '-', color=COLORS['border'], lw=1)
    v_times = [2, 3.5, 5, 6.5, 8, 9.5]
    for i, t in enumerate(v_times):
        draw_box(ax, t - 0.25, 5.2, 0.5, 0.6, f'V{i+1}',
                 color=COLORS['primary'], fontsize=7, radius=0.1)

    # 音频 RTP 流
    ax.text(0.5, 4.0, '音频 RTP 流', ha='left', va='center',
            fontsize=10, fontweight='bold', color=COLORS['accent'])
    ax.plot([1.5, 11], [3.3, 3.3], '-', color=COLORS['border'], lw=1)
    a_times = [2, 2.7, 3.4, 4.1, 4.8, 5.5, 6.2, 6.9, 7.6, 8.3, 9.0, 9.7]
    for i, t in enumerate(a_times):
        draw_box(ax, t - 0.2, 3.05, 0.4, 0.5, f'A{i+1}',
                 color=COLORS['accent'], fontsize=6, radius=0.1)

    # RTCP SR 箭头（NTP 时间戳映射）
    for sr_x, y_top in [(5.0, 5.2), (8.0, 3.05)]:
        ax.annotate('', xy=(sr_x, 2.2), xytext=(sr_x, y_top),
                    arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                                    lw=2, linestyle='--'))
    ax.text(5.15, 3.8, 'RTCP SR\nNTP ↔ RTP_ts', ha='left', va='center',
            fontsize=7, color=COLORS['danger'], fontweight='bold')
    ax.text(8.15, 2.6, 'RTCP SR\nNTP ↔ RTP_ts', ha='left', va='center',
            fontsize=7, color=COLORS['danger'], fontweight='bold')

    draw_box(ax, 2.5, 1.4, 7, 0.7, 'NTP 墙钟时间（统一参考基准）',
             color=COLORS['warning'], fontsize=10, radius=0.15)

    ax.text(6, 0.5,
            '通过 RTCP SR 中的 NTP 时间戳，将音频和视频各自的 RTP 时间戳映射到统一墙钟，实现同步对齐',
            ha='center', va='center', fontsize=9, color=COLORS['mid_text'],
            style='italic')
    save_fig(fig, 'av_sync')


# ── 3. RTCP 报文类型 ────────────────────────────────────────────────────────
def draw_rtcp_packets():
    fig, ax = new_fig(12, 5)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)

    ax.text(6, 6.5, 'RTCP 报文类型', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    packets = [
        ('SR (200)',   '发送者报告', '发送端统计：\n发包数、字节数\nNTP/RTP时间戳映射',
         COLORS['primary'], COLORS['light_blue']),
        ('RR (201)',   '接收者报告', '接收端统计：\n丢包率、抖动\n最大序列号',
         COLORS['secondary'], COLORS['light_purple']),
        ('SDES (202)', '源描述',     '参与者信息：\nCNAME、邮箱\n电话、位置等',
         COLORS['accent'], COLORS['light_green']),
        ('BYE (203)',  '离开通知',   '通知其他参与者\n该源已离开会话',
         COLORS['warning'], COLORS['light_orange']),
        ('APP (204)',  '应用自定义', '应用层自定义\n扩展数据',
         COLORS['danger'], COLORS['light_red']),
    ]

    box_w, gap = 2.0, 0.2
    total_w = len(packets) * box_w + (len(packets) - 1) * gap
    start_x = (12 - total_w) / 2

    for i, (name, subtitle, desc, color, bg_color) in enumerate(packets):
        x = start_x + i * (box_w + gap)
        bg = FancyBboxPatch((x, 1.5), box_w, 4.3,
                             boxstyle="round,pad=0.05,rounding_size=0.2",
                             facecolor=bg_color, edgecolor=color,
                             linewidth=2, zorder=1)
        ax.add_patch(bg)
        draw_box(ax, x + 0.1, 4.6, box_w - 0.2, 0.7, name,
                 color=color, fontsize=9, radius=0.15)
        ax.text(x + box_w / 2, 4.1, subtitle, ha='center', va='center',
                fontsize=9, fontweight='bold', color=color)
        ax.text(x + box_w / 2, 2.8, desc, ha='center', va='center',
                fontsize=8, color=COLORS['dark_text'], linespacing=1.5)

    save_fig(fig, 'rtcp_packets')


# ── 4. SDP 结构层次图 ───────────────────────────────────────────────────────
def draw_sdp_structure():
    fig, ax = new_fig(10, 7)
    ax = no_axes(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)

    ax.text(5, 8.5, 'SDP 结构层次', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    session_bg = FancyBboxPatch((0.5, 1.0), 9, 7.0,
                                 boxstyle="round,pad=0.1,rounding_size=0.3",
                                 facecolor=COLORS['light_blue'],
                                 edgecolor=COLORS['primary'], linewidth=2, zorder=0)
    ax.add_patch(session_bg)

    ax.text(5, 7.6, '会话级别 Session Level', ha='center', va='center',
            fontsize=12, fontweight='bold', color=COLORS['primary'])

    session_fields = [
        ('v=0',                            '协议版本'),
        ('o=<username> <sess-id> ...', '会话来源'),
        ('s=<session-name>',               '会话名称'),
        ('c=IN IP4 <address>',             '连接信息'),
        ('t=<start> <stop>',               '时间描述'),
    ]
    for i, (field, desc) in enumerate(session_fields):
        y = 7.0 - i * 0.45
        ax.text(1.2, y, field, ha='left', va='center', fontsize=9,
                fontfamily='monospace', color=COLORS['dark_text'], fontweight='bold')
        ax.text(6.0, y, f'  ← {desc}', ha='left', va='center',
                fontsize=8, color=COLORS['mid_text'])

    for j, (media_label, media_fields, sx) in enumerate([
        ('媒体级别 - 音频', [
            ('m=audio 49170 RTP/AVP 0', '媒体描述'),
            ('a=rtpmap:0 PCMU/8000',    '属性'),
        ], 0.8),
        ('媒体级别 - 视频', [
            ('m=video 51372 RTP/AVP 96', '媒体描述'),
            ('a=rtpmap:96 H264/90000',   '属性'),
        ], 5.2),
    ]):
        media_bg = FancyBboxPatch((sx, 1.3), 4.0, 3.0,
                                   boxstyle="round,pad=0.1,rounding_size=0.2",
                                   facecolor=COLORS['light_green'],
                                   edgecolor=COLORS['accent'], linewidth=1.5, zorder=1)
        ax.add_patch(media_bg)
        ax.text(sx + 2.0, 3.9, media_label, ha='center', va='center',
                fontsize=10, fontweight='bold', color=COLORS['accent'])
        for k, (field, desc) in enumerate(media_fields):
            y = 3.2 - k * 0.55
            ax.text(sx + 0.3, y, field, ha='left', va='center', fontsize=7,
                    fontfamily='monospace', color=COLORS['dark_text'])
            ax.text(sx + 0.3, y - 0.3, f'← {desc}', ha='left', va='center',
                    fontsize=7, color=COLORS['mid_text'])

    save_fig(fig, 'sdp_structure')


# ── 5. Offer/Answer 协商时序 ────────────────────────────────────────────────
def draw_offer_answer():
    fig, ax = new_fig(10, 7)
    ax = no_axes(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)

    ax.text(5, 8.5, 'SDP Offer/Answer 协商模型', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    draw_timeline_entity(ax, 2.5, 7.8, 1.0, 'Offerer',  color=COLORS['primary'])
    draw_timeline_entity(ax, 7.5, 7.8, 1.0, 'Answerer', color=COLORS['accent'])

    draw_sequence_arrow(ax, 2.5, 7.5, 6.5, label='SDP Offer',
                        color=COLORS['primary'], fontsize=10)

    offer_content = ('编解码能力列表:\n'
                     '• H.264, VP8, VP9\n'
                     '• Opus, AAC, G.711\n'
                     '• 分辨率: 1080p, 720p, 480p')
    ax.text(5, 5.8, offer_content, ha='center', va='center', fontsize=8,
            color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['light_blue'],
                      edgecolor=COLORS['primary'], linestyle='--'))

    ax.text(8.8, 4.8, '能力协商\n选择子集', ha='center', va='center',
            fontsize=8, color=COLORS['warning'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_orange'],
                      edgecolor=COLORS['warning']))

    draw_sequence_arrow(ax, 7.5, 2.5, 3.5, label='SDP Answer',
                        color=COLORS['accent'], fontsize=10)

    answer_content = '选定编解码:\n• H.264\n• Opus\n• 分辨率: 720p'
    ax.text(5, 2.7, answer_content, ha='center', va='center', fontsize=8,
            color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['light_green'],
                      edgecolor=COLORS['accent'], linestyle='--'))

    draw_box(ax, 2.5, 1.3, 5, 0.6, '媒体会话建立 ✓',
             color=COLORS['accent'], fontsize=10)
    draw_dashed_line(ax, 2.5, 1.9, 2.5, 2.3, color=COLORS['accent'])
    draw_dashed_line(ax, 7.5, 1.9, 7.5, 2.3, color=COLORS['accent'])
    save_fig(fig, 'offer_answer')


# ── 6. 网络抖动示意图 ───────────────────────────────────────────────────────
def draw_network_jitter():
    fig, ax = new_fig(12, 5)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)

    ax.text(6, 6.5, '网络抖动（Jitter）示意', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # ── 发送端（均匀间隔）──
    ax.text(0.5, 5.5, '发送端', ha='left', va='center',
            fontsize=11, fontweight='bold', color=COLORS['primary'])
    ax.text(0.5, 5.05, '均匀间隔', ha='left', va='center',
            fontsize=8, color=COLORS['mid_text'])
    ax.plot([2, 11], [5.3, 5.3], '-', color=COLORS['border'], lw=1)
    ax.text(11.3, 5.3, 't', ha='left', va='center',
            fontsize=9, color=COLORS['mid_text'])

    send_times = [2.5, 4.0, 5.5, 7.0, 8.5, 10.0]
    for i, t in enumerate(send_times):
        draw_box(ax, t - 0.3, 5.0, 0.6, 0.6, f'P{i+1}',
                 color=COLORS['primary'], fontsize=8, radius=0.1)
        if i < len(send_times) - 1:
            mid = (t + send_times[i + 1]) / 2
            ax.text(mid, 4.6, 'Δt', ha='center', va='center',
                    fontsize=7, color=COLORS['mid_text'])

    # ── 网络 ──
    ax.text(6, 3.7, '☁  网络传输（拥塞、路由变化、排队延迟）  ☁',
            ha='center', va='center', fontsize=9, color=COLORS['warning'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_orange'],
                      edgecolor=COLORS['warning'], linestyle='--'))

    # ── 接收端（不均匀）──
    ax.text(0.5, 2.7, '接收端', ha='left', va='center',
            fontsize=11, fontweight='bold', color=COLORS['danger'])
    ax.text(0.5, 2.25, '间隔不均', ha='left', va='center',
            fontsize=8, color=COLORS['mid_text'])
    ax.plot([2, 11], [2.5, 2.5], '-', color=COLORS['border'], lw=1)
    ax.text(11.3, 2.5, 't', ha='left', va='center',
            fontsize=9, color=COLORS['mid_text'])

    recv_times = [2.8, 4.8, 5.2, 7.5, 8.2, 10.5]
    for i, t in enumerate(recv_times):
        draw_box(ax, t - 0.3, 2.2, 0.6, 0.6, f'P{i+1}',
                 color=COLORS['danger'], fontsize=8, radius=0.1)

    ax.annotate('', xy=(4.8, 1.7), xytext=(2.8, 1.7),
                arrowprops=dict(arrowstyle='<->', color=COLORS['warning'], lw=1.5))
    ax.text(3.8, 1.4, '2.0Δt', ha='center', va='center',
            fontsize=8, color=COLORS['warning'], fontweight='bold')

    ax.annotate('', xy=(5.2, 1.7), xytext=(4.8, 1.7),
                arrowprops=dict(arrowstyle='<->', color=COLORS['danger'], lw=1.5))
    ax.text(5.0, 1.4, '0.4Δt', ha='center', va='center',
            fontsize=8, color=COLORS['danger'], fontweight='bold')

    ax.text(6, 0.7, '抖动 = 相邻包到达间隔的变化量，理想情况下应为 0',
            ha='center', va='center', fontsize=9, color=COLORS['mid_text'],
            style='italic')
    save_fig(fig, 'network_jitter')


# ── 7. Jitter Buffer 工作原理 ───────────────────────────────────────────────
def draw_jitter_buffer():
    fig, ax = new_fig(12, 5.5)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.5)

    ax.text(6, 7.0, 'Jitter Buffer 工作原理', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # 不规则到达
    ax.text(0.3, 5.8, '网络到达\n（不规则）', ha='center', va='center',
            fontsize=8, fontweight='bold', color=COLORS['danger'])

    irregular_x = [1.5, 2.8, 3.1, 4.5, 4.7, 6.0]
    pkt_labels = ['P1', 'P3', 'P2', 'P5', 'P4', 'P6']
    for x, label in zip(irregular_x, pkt_labels):
        draw_box(ax, x - 0.25, 5.5, 0.5, 0.5, label,
                 color=COLORS['danger'], fontsize=7, radius=0.08)

    for x in irregular_x:
        draw_arrow(ax, x, 5.5, x, 4.8, color=COLORS['mid_text'], lw=1)

    # Jitter Buffer
    buf_bg = FancyBboxPatch((1.0, 3.2), 5.5, 1.5,
                             boxstyle="round,pad=0.1,rounding_size=0.2",
                             facecolor=COLORS['light_cyan'],
                             edgecolor=COLORS['info'], linewidth=2, zorder=1)
    ax.add_patch(buf_bg)
    ax.text(3.75, 4.4, 'Jitter Buffer（重排序 + 缓冲）', ha='center', va='center',
            fontsize=10, fontweight='bold', color=COLORS['info'])

    sorted_x = [1.4, 2.3, 3.2, 4.1, 5.0, 5.9]
    for i, x in enumerate(sorted_x):
        draw_box(ax, x - 0.25, 3.4, 0.5, 0.5, f'P{i+1}',
                 color=COLORS['info'], fontsize=7, radius=0.08)

    draw_arrow(ax, 6.5, 3.95, 7.2, 3.95, color=COLORS['info'], lw=2)

    # 均匀输出
    ax.text(9.5, 4.6, '解码器输入\n（均匀输出）', ha='center', va='center',
            fontsize=8, fontweight='bold', color=COLORS['accent'])
    regular_x = [7.5, 8.3, 9.1, 9.9, 10.7]
    for i, x in enumerate(regular_x):
        draw_box(ax, x - 0.25, 3.7, 0.5, 0.5, f'P{i+1}',
                 color=COLORS['accent'], fontsize=7, radius=0.08)

    ax.plot([7.3, 11.2], [3.3, 3.3], '-', color=COLORS['border'], lw=1)
    for x in regular_x:
        ax.plot([x, x], [3.3, 3.7], '-', color=COLORS['accent'], lw=1)
    for i in range(len(regular_x) - 1):
        mid = (regular_x[i] + regular_x[i + 1]) / 2
        ax.text(mid, 3.05, 'Δt', ha='center', va='center',
                fontsize=7, color=COLORS['mid_text'])

    ax.text(6, 2.3,
            '缓冲深度 = 延迟与抗抖动能力的权衡：缓冲越深抗抖动越强，但延迟越大',
            ha='center', va='center', fontsize=9, color=COLORS['mid_text'],
            style='italic',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['light_bg'],
                      edgecolor=COLORS['border']))

    for i, f in enumerate(['接收排序', '去重去乱序', '平滑输出']):
        ax.text(2.0 + i * 2.2, 1.5, f'✓ {f}', ha='center', va='center',
                fontsize=9, color=COLORS['info'], fontweight='bold')
    save_fig(fig, 'jitter_buffer')


# ── 8. FEC 编码原理 ─────────────────────────────────────────────────────────
def draw_fec_encoding():
    fig, ax = new_fig(12, 6.5)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)

    ax.text(6, 8.5, 'FEC 前向纠错编码原理', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # ── 编码端 ──
    ax.text(1, 7.6, '编码端', ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['primary'])
    data_pkts = ['D1', 'D2', 'D3', 'D4']
    data_clrs = [COLORS['primary'], COLORS['secondary'],
                 COLORS['accent'], COLORS['info']]
    for i, (lbl, c) in enumerate(zip(data_pkts, data_clrs)):
        x = 1.5 + i * 1.8
        draw_box(ax, x, 6.8, 1.2, 0.7, lbl, color=c, fontsize=10, radius=0.15)
        draw_arrow(ax, x + 0.6, 6.8, x + 0.6, 6.2, color=COLORS['mid_text'])

    xor_x = 4.6
    draw_box(ax, xor_x - 1, 5.4, 2.0, 0.7, 'XOR 运算',
             color=COLORS['warning'], fontsize=10, radius=0.15)
    draw_arrow(ax, xor_x, 5.4, xor_x, 4.8, color=COLORS['warning'])
    draw_box(ax, xor_x - 0.8, 4.0, 1.6, 0.7, 'FEC冗余包',
             color=COLORS['danger'], fontsize=9, radius=0.15)

    ax.text(8.5, 5.7, 'FEC = D1 ⊕ D2 ⊕ D3 ⊕ D4', ha='center', va='center',
            fontsize=10, fontfamily='monospace', color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_bg'],
                      edgecolor=COLORS['border']))

    # ── 分隔线 ──
    draw_dashed_line(ax, 0.5, 3.3, 11.5, 3.3, color=COLORS['border'], lw=1.5)
    ax.text(6, 3.5, '—— 网络传输（D2 丢失）——', ha='center', va='center',
            fontsize=9, color=COLORS['danger'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['white'],
                      edgecolor='none'))

    # ── 解码端 ──
    ax.text(1, 2.8, '解码端', ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['accent'])

    recv_labels = ['D1', '  ✗  ', 'D3', 'D4', 'FEC']
    recv_colors = [COLORS['primary'], COLORS['light_red'], COLORS['accent'],
                   COLORS['info'], COLORS['danger']]
    recv_tc = ['white', COLORS['danger'], 'white', 'white', 'white']
    for i, (lbl, c, tc) in enumerate(zip(recv_labels, recv_colors, recv_tc)):
        draw_box(ax, 1.0 + i * 1.8, 1.8, 1.2, 0.7, lbl,
                 color=c, text_color=tc, fontsize=9, radius=0.15)

    ax.text(8.5, 2.5, '恢复公式:', ha='center', va='center',
            fontsize=9, fontweight='bold', color=COLORS['dark_text'])
    ax.text(8.5, 1.9, 'D2 = FEC ⊕ D1 ⊕ D3 ⊕ D4', ha='center', va='center',
            fontsize=10, fontfamily='monospace', color=COLORS['accent'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_green'],
                      edgecolor=COLORS['accent']))

    ax.text(6, 0.8,
            '限制：N 个数据包生成 1 个冗余包时，只能恢复 1 个丢失包',
            ha='center', va='center', fontsize=9, color=COLORS['mid_text'],
            style='italic')
    save_fig(fig, 'fec_encoding')


# ── 9. NACK vs FEC 对比 ─────────────────────────────────────────────────────
def draw_nack_vs_fec():
    fig, ax = new_fig(12, 8)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)

    ax.text(6, 9.5, 'NACK 重传 vs FEC 恢复', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # ════ NACK 区域 ════
    nack_bg = FancyBboxPatch((0.3, 5.2), 11.4, 4.0,
                              boxstyle="round,pad=0.1,rounding_size=0.3",
                              facecolor='#FFF7ED', edgecolor=COLORS['warning'],
                              linewidth=1.5, zorder=0)
    ax.add_patch(nack_bg)
    ax.text(6, 8.9, 'NACK 重传方案', ha='center', va='center',
            fontsize=12, fontweight='bold', color=COLORS['warning'])

    ax.text(1.5, 8.4, '发送端', ha='center', fontsize=9,
            fontweight='bold', color=COLORS['primary'])
    ax.text(10.5, 8.4, '接收端', ha='center', fontsize=9,
            fontweight='bold', color=COLORS['accent'])
    ax.plot([1.5, 1.5], [8.2, 5.5], '-', color=COLORS['border'], lw=1)
    ax.plot([10.5, 10.5], [8.2, 5.5], '-', color=COLORS['border'], lw=1)

    draw_sequence_arrow(ax, 1.5, 10.5, 7.8, label='P1',
                        color=COLORS['primary'], fontsize=9)
    ax.annotate('', xy=(7, 7.2), xytext=(1.5, 7.3),
                arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                                lw=1.5, linestyle='--'))
    ax.text(5, 7.5, 'P2 ✗ 丢失', ha='center', va='center',
            fontsize=8, color=COLORS['danger'], fontweight='bold')
    draw_sequence_arrow(ax, 1.5, 10.5, 6.8, label='P3',
                        color=COLORS['primary'], fontsize=9)
    ax.text(10.8, 6.5, '检测到\nP2丢失', ha='left', va='center',
            fontsize=7, color=COLORS['danger'])
    draw_sequence_arrow(ax, 10.5, 1.5, 6.2, label='NACK: 请求重传 P2',
                        color=COLORS['danger'], fontsize=8)
    draw_sequence_arrow(ax, 1.5, 10.5, 5.7, label='重传 P2',
                        color=COLORS['warning'], fontsize=9)

    ax.annotate('', xy=(11.5, 5.7), xytext=(11.5, 7.2),
                arrowprops=dict(arrowstyle='<->', color=COLORS['danger'], lw=1.5))
    ax.text(11.8, 6.45, '+1 RTT\n延迟', ha='left', va='center',
            fontsize=8, color=COLORS['danger'], fontweight='bold')

    # ════ FEC 区域 ════
    fec_bg = FancyBboxPatch((0.3, 0.5), 11.4, 4.3,
                             boxstyle="round,pad=0.1,rounding_size=0.3",
                             facecolor='#F0FDF4', edgecolor=COLORS['accent'],
                             linewidth=1.5, zorder=0)
    ax.add_patch(fec_bg)
    ax.text(6, 4.5, 'FEC 前向纠错方案', ha='center', va='center',
            fontsize=12, fontweight='bold', color=COLORS['accent'])

    ax.text(1.5, 4.0, '发送端', ha='center', fontsize=9,
            fontweight='bold', color=COLORS['primary'])
    ax.text(10.5, 4.0, '接收端', ha='center', fontsize=9,
            fontweight='bold', color=COLORS['accent'])
    ax.plot([1.5, 1.5], [3.8, 0.8], '-', color=COLORS['border'], lw=1)
    ax.plot([10.5, 10.5], [3.8, 0.8], '-', color=COLORS['border'], lw=1)

    draw_sequence_arrow(ax, 1.5, 10.5, 3.4, label='P1',
                        color=COLORS['primary'], fontsize=9)
    ax.annotate('', xy=(7, 2.8), xytext=(1.5, 2.9),
                arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                                lw=1.5, linestyle='--'))
    ax.text(5, 3.1, 'P2 ✗ 丢失', ha='center', va='center',
            fontsize=8, color=COLORS['danger'], fontweight='bold')
    draw_sequence_arrow(ax, 1.5, 10.5, 2.4, label='P3',
                        color=COLORS['primary'], fontsize=9)
    draw_sequence_arrow(ax, 1.5, 10.5, 1.9, label='FEC冗余包',
                        color=COLORS['accent'], fontsize=9)

    ax.text(10.8, 1.3, '用 FEC 直接\n恢复 P2 ✓', ha='left', va='center',
            fontsize=8, color=COLORS['accent'], fontweight='bold')
    ax.text(11.8, 2.5, '零额外\n延迟', ha='left', va='center',
            fontsize=8, color=COLORS['accent'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['light_green'],
                      edgecolor=COLORS['accent']))
    save_fig(fig, 'nack_vs_fec')


# ── 主入口 ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Part 2: 传输协议 ===')
    draw_rtp_header()
    draw_av_sync()
    draw_rtcp_packets()
    draw_sdp_structure()
    draw_offer_answer()
    draw_network_jitter()
    draw_jitter_buffer()
    draw_fec_encoding()
    draw_nack_vs_fec()
    print('=== Part 2 完成 ===')
