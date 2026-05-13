#!/usr/bin/env python3
"""第六篇：综合实战项目 —— 生成 8 张技术插图。"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

from utils import (COLORS, save_fig, new_fig, no_axes, draw_box, draw_arrow,
                   draw_brace_text, draw_sequence_arrow, draw_dashed_line,
                   draw_field_row, draw_timeline_entity)

C = COLORS


# ── 1. live_system_arch.png ─────────────────────────────────────────────────
def draw_live_system_arch():
    fig, ax = new_fig(16, 8)
    no_axes(ax)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.set_title('直播系统端到端架构', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    nodes = [
        (0.3, 3.5, 1.8, 1.8, '采集端\n(摄像头/\n麦克风)', C['primary']),
        (2.7, 3.5, 1.8, 1.8, '编码\n(H.264/\nAAC)', C['secondary']),
        (5.1, 3.5, 1.8, 1.8, 'RTMP\n推流', C['warning']),
        (7.5, 3.0, 2.4, 2.8, '流媒体\n服务器\n(SRS)', C['danger']),
    ]
    for x, y, w, h, text, color in nodes:
        draw_box(ax, x, y, w, h, text, color=color, fontsize=9)

    for i in range(len(nodes) - 1):
        x1 = nodes[i][0] + nodes[i][2]
        x2 = nodes[i + 1][0]
        cy = nodes[i][1] + nodes[i][3] / 2
        draw_arrow(ax, x1, cy, x2, cy, color=C['dark_text'], lw=2)

    proto_x = 10.5
    protocols = [
        (proto_x, 6.5, 1.8, 0.9, 'HLS', C['accent']),
        (proto_x, 5.2, 1.8, 0.9, 'HTTP-FLV', C['info']),
        (proto_x, 3.9, 1.8, 0.9, 'WebRTC', C['primary']),
        (proto_x, 2.6, 1.8, 0.9, 'SRT', C['secondary']),
    ]
    for x, y, w, h, text, color in protocols:
        draw_box(ax, x, y, w, h, text, color=color, fontsize=9)
        draw_arrow(ax, 9.9, 4.4, x, y + h / 2, color=C['mid_text'], lw=1.3)

    cdn_x = 13.0
    draw_box(ax, cdn_x, 3.5, 1.5, 1.8, 'CDN\n分发', color=C['warning'], fontsize=10)
    for p in protocols:
        draw_arrow(ax, p[0] + p[2], p[1] + p[3] / 2, cdn_x, 4.4, color=C['mid_text'], lw=1.2)

    play_x = 15.0
    draw_box(ax, play_x - 0.3, 3.5, 1.2, 1.8, '播放\n端', color=C['primary'], fontsize=10)
    draw_arrow(ax, cdn_x + 1.5, 4.4, play_x - 0.3, 4.4, color=C['dark_text'], lw=2)

    ax.text(8.0, 0.8, '端到端数据流：采集 → 编码 → 推流 → 服务器 → 分发协议 → CDN → 播放',
            ha='center', fontsize=10, color=C['mid_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['light_bg'],
                      edgecolor=C['border']))

    save_fig(fig, 'live_system_arch')


# ── 2. srs_cluster.png ──────────────────────────────────────────────────────
def draw_srs_cluster():
    fig, ax = new_fig(12, 9)
    no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.set_title('SRS 集群架构：Origin + Edge', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    origin_x, origin_y = 5.0, 6.5
    draw_box(ax, origin_x, origin_y, 2.5, 1.5, 'Origin\nServer',
             color=C['danger'], fontsize=12)

    ax.text(6.25, 9.0, '推流端', fontsize=11, fontweight='bold',
            ha='center', color=C['primary'])
    draw_box(ax, 4.75, 8.3, 1.2, 0.6, 'RTMP', color=C['primary'], fontsize=9)
    draw_box(ax, 6.25, 8.3, 1.2, 0.6, 'SRT', color=C['primary'], fontsize=9)
    draw_arrow(ax, 5.35, 8.3, 5.8, origin_y + 1.5, color=C['primary'], lw=1.5)
    draw_arrow(ax, 6.85, 8.3, 6.5, origin_y + 1.5, color=C['primary'], lw=1.5)

    edges = [
        (0.5, 3.0, 'Edge 1\n(北京)'),
        (3.5, 3.0, 'Edge 2\n(上海)'),
        (6.5, 3.0, 'Edge 3\n(广州)'),
        (9.5, 3.0, 'Edge 4\n(成都)'),
    ]
    for ex, ey, label in edges:
        draw_box(ax, ex, ey, 2.0, 1.5, label, color=C['accent'], fontsize=9)
        draw_arrow(ax, origin_x + 1.25, origin_y, ex + 1.0, ey + 1.5,
                   color=C['warning'], lw=1.5)

    ax.text(6.0, 5.6, '回源拉流', fontsize=9, color=C['warning'],
            ha='center', fontweight='bold')

    for ex, ey, _ in edges:
        cx = ex + 1.0
        draw_box(ax, cx - 0.6, 1.0, 1.2, 0.8, '观众', color=C['info'], fontsize=8)
        draw_arrow(ax, cx, 1.8, cx, ey, color=C['info'], lw=1.2)

    ax.text(6.0, 0.3, '用户就近接入 Edge 节点，Edge 按需从 Origin 回源，'
            '实现缓存 + 负载分担',
            ha='center', fontsize=9, color=C['mid_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['light_bg'],
                      edgecolor=C['border']))

    save_fig(fig, 'srs_cluster')


# ── 3. sfu_mcu.png ──────────────────────────────────────────────────────────
def draw_sfu_mcu():
    fig, ax = new_fig(14, 8)
    no_axes(ax)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_title('SFU vs MCU 架构对比', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    ax.plot([7, 7], [0.5, 8.5], '--', color=C['border'], lw=1.5, zorder=0)
    ax.text(3.5, 8.3, 'SFU（选择性转发）', fontsize=14, fontweight='bold',
            ha='center', color=C['primary'])
    ax.text(10.5, 8.3, 'MCU（多点控制单元）', fontsize=14, fontweight='bold',
            ha='center', color=C['secondary'])

    # ── SFU ──
    sfu_cx, sfu_cy = 3.5, 4.5
    draw_box(ax, sfu_cx - 1.0, sfu_cy - 0.7, 2.0, 1.4, 'SFU',
             color=C['primary'], fontsize=13)

    sfu_clients = [
        (0.5, 7.0, 'A'),
        (5.5, 7.0, 'B'),
        (0.5, 2.0, 'C'),
        (5.5, 2.0, 'D'),
    ]
    for cx, cy, name in sfu_clients:
        draw_box(ax, cx, cy, 1.2, 0.8, f'客户端 {name}', color=C['info'], fontsize=8)
        draw_arrow(ax, cx + 0.6, cy + 0.4 + (0.0 if cy < 5 else 0.0),
                   sfu_cx, sfu_cy, color=C['accent'], lw=1.2)
        draw_arrow(ax, sfu_cx, sfu_cy, cx + 0.6,
                   cy + 0.4, color=C['warning'], lw=1.2)

    ax.text(3.5, 0.8, '服务器只转发，不解码/编码\n每个客户端收到 N-1 路流\n'
            '服务器负载低，灵活性高',
            ha='center', fontsize=8, color=C['mid_text'], style='italic')

    # ── MCU ──
    mcu_cx, mcu_cy = 10.5, 4.5
    draw_box(ax, mcu_cx - 1.2, mcu_cy - 0.7, 2.4, 1.4, 'MCU\n(混流)',
             color=C['secondary'], fontsize=12)

    mcu_clients = [
        (7.8, 7.0, 'A'),
        (12.2, 7.0, 'B'),
        (7.8, 2.0, 'C'),
        (12.2, 2.0, 'D'),
    ]
    for cx, cy, name in mcu_clients:
        draw_box(ax, cx, cy, 1.2, 0.8, f'客户端 {name}', color=C['info'], fontsize=8)
        draw_arrow(ax, cx + 0.6, cy + 0.4, mcu_cx, mcu_cy,
                   color=C['accent'], lw=1.2)
        draw_arrow(ax, mcu_cx, mcu_cy, cx + 0.6, cy + 0.4,
                   color=C['danger'], lw=1.2)

    ax.text(10.5, 0.8, '服务器解码所有流并混合为一路\n每个客户端只收 1 路混合流\n'
            '客户端带宽低，但服务器 CPU 开销大',
            ha='center', fontsize=8, color=C['mid_text'], style='italic')

    save_fig(fig, 'sfu_mcu')


# ── 4. janus_arch.png ───────────────────────────────────────────────────────
def draw_janus_arch():
    fig, ax = new_fig(13, 8)
    no_axes(ax)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.set_title('Janus 网关架构', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    draw_box(ax, 3.5, 4.5, 6.0, 2.0, 'Janus 核心引擎\n(WebRTC 协议栈 / 会话管理)',
             color=C['primary'], fontsize=12)

    transports = [
        (0.3, 7.0, 'HTTP/\nWebSocket', C['info']),
        (2.5, 7.0, 'RabbitMQ', C['accent']),
        (4.7, 7.0, 'MQTT', C['accent']),
    ]
    for x, y, text, color in transports:
        draw_box(ax, x, y, 1.8, 1.0, text, color=color, fontsize=8)
        draw_arrow(ax, x + 0.9, y, x + 0.9, 6.5, color=C['mid_text'], lw=1.3)

    ax.text(2.5, 8.3, '传输层 (Transport)', fontsize=11, fontweight='bold',
            ha='center', color=C['dark_text'])

    plugins = [
        (1.0, 1.5, 'VideoRoom\n(视频会议)', C['danger']),
        (3.5, 1.5, 'Streaming\n(流媒体)', C['warning']),
        (6.0, 1.5, 'AudioBridge\n(音频混合)', C['secondary']),
        (8.5, 1.5, 'SIP\n(VoIP)', C['info']),
        (11.0, 1.5, '自定义\n插件', C['accent']),
    ]
    for x, y, text, color in plugins:
        draw_box(ax, x, y, 2.0, 1.5, text, color=color, fontsize=9)

    for x, y, _, _ in plugins:
        draw_arrow(ax, x + 1.0, y + 1.5, x + 1.0, 4.5, color=C['mid_text'], lw=1.3)

    ax.text(6.5, 0.5, 'Plugin API（可插拔插件架构）', fontsize=12, ha='center',
            fontweight='bold', color=C['dark_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['light_purple'],
                      edgecolor=C['secondary']))

    ax.text(10.5, 5.5, 'Event\nHandler',
            fontsize=9, ha='center', color=C['mid_text'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=C['light_bg'],
                      edgecolor=C['border']))
    draw_arrow(ax, 9.5, 5.5, 10.0, 5.5, color=C['border'], lw=1.2)

    save_fig(fig, 'janus_arch')


# ── 5. sfu_cascade.png ──────────────────────────────────────────────────────
def draw_sfu_cascade():
    fig, ax = new_fig(13, 8)
    no_axes(ax)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.set_title('SFU 级联架构', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    sfus = [
        (2.0, 5.5, 'SFU-北京'),
        (6.0, 7.0, 'SFU-上海'),
        (10.0, 5.5, 'SFU-广州'),
        (6.0, 3.0, 'SFU-成都'),
    ]
    for sx, sy, label in sfus:
        draw_box(ax, sx - 1.0, sy - 0.5, 2.0, 1.0, label,
                 color=C['primary'], fontsize=10)

    pairs = [(0, 1), (1, 2), (0, 3), (2, 3), (1, 3)]
    for i, j in pairs:
        x1, y1 = sfus[i][0], sfus[i][1]
        x2, y2 = sfus[j][0], sfus[j][1]
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='<->', color=C['secondary'],
                                    lw=2, connectionstyle='arc3,rad=0.1'))

    ax.text(6.0, 5.0, '内部级联链路\n(媒体转发)', fontsize=9, ha='center',
            color=C['secondary'], fontweight='bold')

    users = [
        (0.2, 7.5, sfus[0]), (0.2, 4.0, sfus[0]),
        (4.5, 8.5, sfus[1]), (7.5, 8.5, sfus[1]),
        (11.5, 7.5, sfus[2]), (11.5, 4.0, sfus[2]),
        (4.5, 1.5, sfus[3]), (7.5, 1.5, sfus[3]),
    ]
    for ux, uy, (sx, sy, _) in users:
        draw_box(ax, ux, uy, 1.0, 0.6, '用户', color=C['accent'], fontsize=7)
        draw_arrow(ax, ux + 0.5, uy + 0.3, sx, sy, color=C['info'], lw=1.0)

    ax.text(6.5, 0.4, '用户就近接入最近的 SFU 节点，多个 SFU 之间通过级联链路互联',
            ha='center', fontsize=10, color=C['mid_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['light_bg'],
                      edgecolor=C['border']))

    save_fig(fig, 'sfu_cascade')


# ── 6. latency_waterfall.png ────────────────────────────────────────────────
def draw_latency_waterfall():
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_title('端到端延迟组成瀑布图', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=15)

    stages = ['采集', '编码', '推流/上行', '服务器处理', '分发/下行', '缓冲/解码']
    durations = [30, 50, 50, 10, 100, 200]
    colors = [C['primary'], C['secondary'], C['warning'],
              C['accent'], C['info'], C['danger']]

    starts = []
    s = 0
    for d in durations:
        starts.append(s)
        s += d

    bars = ax.barh(stages, durations, left=starts, color=colors,
                   edgecolor='white', height=0.6, zorder=2)

    for bar, dur, start in zip(bars, durations, starts):
        cx = start + dur / 2
        ax.text(cx, bar.get_y() + bar.get_height() / 2,
                f'{dur}ms', ha='center', va='center', fontsize=11,
                color='white', fontweight='bold', zorder=3)

    total = sum(durations)
    ax.axvline(x=total, color=C['danger'], linestyle='--', lw=2, zorder=1)
    ax.text(total + 5, len(stages) / 2, f'总延迟\n≈{total}ms',
            fontsize=13, fontweight='bold', color=C['danger'], va='center')

    ax.set_xlabel('延迟 (ms)', fontsize=12)
    ax.set_xlim(0, total + 80)
    ax.invert_yaxis()
    ax.grid(axis='x', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    fig.tight_layout()
    save_fig(fig, 'latency_waterfall')


# ── 7. latency_comparison.png ───────────────────────────────────────────────
def draw_latency_comparison():
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_title('各直播方案延迟范围对比', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=15)

    protocols = ['WebRTC', 'SRT', 'LL-HLS', 'HTTP-FLV', 'RTMP', 'HLS']
    mins =  [0.2,  0.5,  2.0,  2.0,  3.0, 10.0]
    maxs =  [0.5,  2.0,  3.0,  4.0,  5.0, 30.0]
    colors = [C['accent'], C['primary'], C['info'],
              C['warning'], C['secondary'], C['danger']]

    y_pos = np.arange(len(protocols))
    ranges = [mx - mn for mn, mx in zip(mins, maxs)]

    bars = ax.barh(y_pos, ranges, left=mins, color=colors,
                   edgecolor='white', height=0.55, zorder=2)

    for i, (mn, mx, bar) in enumerate(zip(mins, maxs, bars)):
        cx = (mn + mx) / 2
        ax.text(cx, bar.get_y() + bar.get_height() / 2,
                f'{mn}–{mx}s', ha='center', va='center',
                fontsize=10, color='white', fontweight='bold', zorder=3)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(protocols, fontsize=12)
    ax.set_xlabel('延迟 (秒)', fontsize=12)
    ax.set_xlim(0, 35)
    ax.grid(axis='x', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.axvline(x=1.0, color=C['accent'], linestyle=':', lw=1.5, alpha=0.7)
    ax.text(1.0, len(protocols) - 0.3, '实时交互\n阈值 1s', fontsize=8,
            ha='center', color=C['accent'])

    fig.tight_layout()
    save_fig(fig, 'latency_comparison')


# ── 8. whip_whep.png ────────────────────────────────────────────────────────
def draw_whip_whep():
    fig, ax = new_fig(14, 7)
    no_axes(ax)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_title('WHIP / WHEP 推拉流架构', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    draw_box(ax, 0.5, 3.0, 2.5, 2.0, '推流端\n(OBS/浏览器)',
             color=C['primary'], fontsize=10)

    draw_box(ax, 5.5, 2.5, 3.0, 3.0, 'WebRTC\nSFU\n服务器',
             color=C['danger'], fontsize=12)

    draw_box(ax, 11.0, 3.0, 2.5, 2.0, '拉流端\n(浏览器/App)',
             color=C['accent'], fontsize=10)

    draw_sequence_arrow(ax, 3.0, 5.5, 5.8, 'WHIP: HTTP POST + SDP Offer',
                        color=C['primary'], fontsize=9)
    draw_sequence_arrow(ax, 5.5, 3.0, 5.0, '201 Created + SDP Answer',
                        color=C['primary'], fontsize=8)

    draw_sequence_arrow(ax, 3.0, 5.5, 3.5, 'WebRTC 媒体流 (SRTP)',
                        color=C['secondary'], fontsize=9)

    draw_sequence_arrow(ax, 11.0, 8.5, 5.8, 'WHEP: HTTP POST + SDP Offer',
                        color=C['accent'], fontsize=9)
    draw_sequence_arrow(ax, 8.5, 11.0, 5.0, '200 OK + SDP Answer',
                        color=C['accent'], fontsize=8)

    draw_sequence_arrow(ax, 8.5, 11.0, 3.5, 'WebRTC 媒体流 (SRTP)',
                        color=C['secondary'], fontsize=9)

    ax.text(3.5, 7.0, 'WHIP\n(WebRTC-HTTP Ingestion Protocol)',
            fontsize=10, ha='center', fontweight='bold', color=C['primary'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['light_blue'],
                      edgecolor=C['primary'], lw=1.5))

    ax.text(10.5, 7.0, 'WHEP\n(WebRTC-HTTP Egress Protocol)',
            fontsize=10, ha='center', fontweight='bold', color=C['accent'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['light_green'],
                      edgecolor=C['accent'], lw=1.5))

    info = FancyBboxPatch((2.5, 0.3), 9.0, 1.2, boxstyle="round,pad=0.15",
                           facecolor=C['light_orange'], edgecolor=C['warning'],
                           linewidth=1.5, zorder=2)
    ax.add_patch(info)
    ax.text(7.0, 0.9, 'WHIP/WHEP 用标准 HTTP 接口替代自定义信令\n'
            '简化 WebRTC 推拉流对接，支持 CDN 集成',
            ha='center', va='center', fontsize=9, color=C['dark_text'])

    save_fig(fig, 'whip_whep')


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    print('=== 第六篇：综合实战项目 ===')
    draw_live_system_arch()
    draw_srs_cluster()
    draw_sfu_mcu()
    draw_janus_arch()
    draw_sfu_cascade()
    draw_latency_waterfall()
    draw_latency_comparison()
    draw_whip_whep()
    print('=== 第六篇完成 ===\n')


if __name__ == '__main__':
    main()
