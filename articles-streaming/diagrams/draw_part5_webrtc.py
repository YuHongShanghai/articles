#!/usr/bin/env python3
"""第五篇：WebRTC 技术体系 —— 生成 14 张技术插图。"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

from utils import (COLORS, save_fig, new_fig, no_axes, draw_box, draw_arrow,
                   draw_brace_text, draw_sequence_arrow, draw_dashed_line,
                   draw_field_row, draw_timeline_entity)

C = COLORS


# ── 1. webrtc_stack.png ─────────────────────────────────────────────────────
def draw_webrtc_stack():
    fig, ax = new_fig(12, 8)
    no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.set_title('WebRTC 协议栈全景图', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    layers = [
        (0.8, 'UDP / TCP（传输层）', C['primary'], 10.4),
        (2.2, 'ICE（STUN / TURN）', C['info'], 10.4),
        (3.6, 'DTLS', C['accent'], 10.4),
    ]
    for y, label, color, w in layers:
        draw_box(ax, 0.8, y, w, 1.0, label, color=color, fontsize=13)

    top_y = 5.2
    top_h = 1.0
    draw_box(ax, 0.8, top_y, 3.2, top_h, 'SRTP\n(音频)', color=C['secondary'], fontsize=11)
    draw_box(ax, 4.2, top_y, 3.2, top_h, 'SRTP\n(视频)', color=C['secondary'], fontsize=11)
    draw_box(ax, 7.6, top_y, 3.6, top_h, 'SCTP\n(数据通道)', color=C['warning'], fontsize=11)

    app_y = 6.8
    app_h = 1.0
    draw_box(ax, 0.8, app_y, 3.2, app_h, 'Audio Engine\n(Opus/G.711)', color=C['danger'], fontsize=10)
    draw_box(ax, 4.2, app_y, 3.2, app_h, 'Video Engine\n(VP8/VP9/H.264)', color=C['danger'], fontsize=10)
    draw_box(ax, 7.6, app_y, 3.6, app_h, 'DataChannel\nAPI', color='#6366F1', fontsize=10)

    app2_y = 8.4
    draw_box(ax, 0.8, app2_y, 10.4, 0.8, 'PeerConnection API（JavaScript / Native）',
             color=C['dark_text'], fontsize=12)

    for y_base in [0.8, 2.2, 3.6]:
        for x_c in [2.4, 5.8, 9.4]:
            draw_arrow(ax, x_c, y_base + 1.0, x_c, y_base + 1.2, color=C['border'], lw=1.2)

    for x_c in [2.4, 5.8, 9.4]:
        draw_arrow(ax, x_c, top_y + top_h, x_c, top_y + top_h + 0.2, color=C['border'], lw=1.2)
        draw_arrow(ax, x_c, app_y + app_h, x_c, app_y + app_h + 0.2, color=C['border'], lw=1.2)

    save_fig(fig, 'webrtc_stack')


# ── 2. webrtc_flow.png ──────────────────────────────────────────────────────
def draw_webrtc_flow():
    fig, ax = new_fig(12, 10)
    no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 12)
    ax.set_title('WebRTC 通信建连流程', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    peer_a_x, peer_b_x = 2.0, 10.0
    signal_x = 6.0

    draw_timeline_entity(ax, peer_a_x, 11.0, 0.5, 'Peer A', C['primary'])
    draw_timeline_entity(ax, signal_x, 11.0, 0.5, '信令服务器', C['accent'])
    draw_timeline_entity(ax, peer_b_x, 11.0, 0.5, 'Peer B', C['primary'])

    steps = [
        (peer_a_x, signal_x, 10.2, 'createOffer → SDP Offer', C['secondary']),
        (signal_x, peer_b_x, 9.6, '转发 SDP Offer', C['accent']),
        (peer_b_x, signal_x, 9.0, 'createAnswer → SDP Answer', C['secondary']),
        (signal_x, peer_a_x, 8.4, '转发 SDP Answer', C['accent']),
        (peer_a_x, signal_x, 7.6, 'ICE Candidate (A)', C['warning']),
        (signal_x, peer_b_x, 7.0, '转发 ICE Candidate (A)', C['warning']),
        (peer_b_x, signal_x, 6.4, 'ICE Candidate (B)', C['warning']),
        (signal_x, peer_a_x, 5.8, '转发 ICE Candidate (B)', C['warning']),
    ]
    for x1, x2, y, label, color in steps:
        draw_sequence_arrow(ax, x1, x2, y, label, color=color, fontsize=8)

    rect_y = 4.0
    rect = FancyBboxPatch((3.5, rect_y), 5.0, 1.2, boxstyle="round,pad=0.15",
                           facecolor=C['light_green'], edgecolor=C['accent'],
                           linewidth=1.5, linestyle='--', zorder=1)
    ax.add_patch(rect)
    ax.text(6.0, rect_y + 0.6, 'P2P 直连（ICE 连通性检查成功）',
            ha='center', va='center', fontsize=10, color=C['accent'], fontweight='bold')

    draw_sequence_arrow(ax, peer_a_x, peer_b_x, 3.2, 'DTLS 握手', color=C['info'], fontsize=9)
    draw_sequence_arrow(ax, peer_b_x, peer_a_x, 2.6, 'DTLS 完成 → 密钥导出', color=C['info'], fontsize=9)

    draw_sequence_arrow(ax, peer_a_x, peer_b_x, 1.6, 'SRTP 加密媒体流 ⇄', color=C['danger'], fontsize=9)
    draw_sequence_arrow(ax, peer_b_x, peer_a_x, 1.0, 'SRTP 加密媒体流 ⇄', color=C['danger'], fontsize=9)

    save_fig(fig, 'webrtc_flow')


# ── 3. nat_types.png ────────────────────────────────────────────────────────
def draw_nat_types():
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.set_facecolor('white')
    fig.suptitle('NAT 四种类型对比', fontsize=16, fontweight='bold', color=C['dark_text'])

    titles = [
        '完全锥形 NAT (Full Cone)',
        '受限锥形 NAT (Address Restricted)',
        '端口受限锥形 NAT (Port Restricted)',
        '对称型 NAT (Symmetric)',
    ]
    descs = [
        '内部主机映射后，任何外部主机\n均可通过映射地址访问',
        '仅曾通信过的外部 IP\n可通过映射地址回传',
        '仅曾通信过的外部 IP:Port\n可通过映射地址回传',
        '每个目标 IP:Port 使用不同映射\n最难穿越',
    ]
    allow_marks = [
        [True, True],
        [True, False],
        [True, False],
        [False, False],
    ]

    for idx, ax_cur in enumerate(axes.flat):
        ax_cur.set_xlim(0, 10)
        ax_cur.set_ylim(0, 8)
        ax_cur.axis('off')
        ax_cur.set_facecolor('white')
        ax_cur.set_title(titles[idx], fontsize=11, fontweight='bold', color=C['dark_text'], pad=8)

        draw_box(ax_cur, 0.3, 3.0, 2.0, 1.5, '内部主机\n192.168.1.2\n:5000',
                 color=C['primary'], fontsize=8)
        draw_box(ax_cur, 3.5, 2.8, 2.5, 2.0, 'NAT\n公网映射\n1.2.3.4:X',
                 color=C['warning'], fontsize=8)

        draw_arrow(ax_cur, 2.3, 3.75, 3.5, 3.75, color=C['primary'], lw=1.5)

        draw_box(ax_cur, 7.2, 5.0, 2.3, 1.2, '外部主机 A\n5.6.7.8:80',
                 color=C['accent'], fontsize=8)
        draw_box(ax_cur, 7.2, 2.2, 2.3, 1.2, '外部主机 B\n9.10.11.12:90',
                 color=C['secondary'], fontsize=8)

        draw_arrow(ax_cur, 6.0, 4.0, 7.2, 5.6, color=C['accent'], lw=1.3)

        mark_a = allow_marks[idx][0]
        color_a = C['accent'] if mark_a else C['danger']
        style_a = '->' if mark_a else '->'
        draw_arrow(ax_cur, 7.2, 5.3, 6.0, 4.2, color=color_a, lw=1.3)
        ax_cur.text(7.0, 4.65, '✓ 允许' if mark_a else '✗ 拒绝',
                    fontsize=8, color=color_a, fontweight='bold')

        mark_b = allow_marks[idx][1]
        color_b = C['accent'] if mark_b else C['danger']
        draw_arrow(ax_cur, 7.2, 3.1, 6.0, 3.9, color=color_b, lw=1.3)
        ax_cur.text(7.0, 3.0, '✓ 允许' if mark_b else '✗ 拒绝',
                    fontsize=8, color=color_b, fontweight='bold')

        if idx == 3:
            ax_cur.text(4.75, 5.5, '映射1: :X₁', fontsize=7, color=C['warning'], ha='center')
            ax_cur.text(4.75, 1.8, '映射2: :X₂', fontsize=7, color=C['warning'], ha='center')

        ax_cur.text(5.0, 0.5, descs[idx], ha='center', va='center',
                    fontsize=8, color=C['mid_text'], style='italic')

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'nat_types')


# ── 4. stun_protocol.png ────────────────────────────────────────────────────
def draw_stun_protocol():
    fig, ax = new_fig(12, 7)
    no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_title('STUN 工作原理', fontsize=16, fontweight='bold', color=C['dark_text'], pad=20)

    draw_box(ax, 0.5, 3.0, 2.5, 2.0, '客户端\n(NAT 内)\n192.168.1.2:5000',
             color=C['primary'], fontsize=10)
    draw_box(ax, 4.5, 3.0, 2.5, 2.0, 'NAT 网关\n映射为\n1.2.3.4:12345',
             color=C['warning'], fontsize=10)
    draw_box(ax, 8.5, 3.0, 3.0, 2.0, 'STUN 服务器\nstun.example.com\n(公网)',
             color=C['accent'], fontsize=10)

    draw_sequence_arrow(ax, 2.6, 4.5, 6.2, 'Binding Request', color=C['primary'], fontsize=9)
    draw_sequence_arrow(ax, 7.0, 8.5, 6.2, '经过 NAT 转换', color=C['warning'], fontsize=8)

    draw_sequence_arrow(ax, 8.5, 7.0, 1.8, 'Binding Response', color=C['accent'], fontsize=9)
    draw_sequence_arrow(ax, 4.5, 3.0, 1.8, '经过 NAT 转换', color=C['warning'], fontsize=8)

    info_box = FancyBboxPatch((3.0, 0.3), 6.0, 1.0, boxstyle="round,pad=0.15",
                               facecolor=C['light_green'], edgecolor=C['accent'],
                               linewidth=1.5, zorder=2)
    ax.add_patch(info_box)
    ax.text(6.0, 0.8, 'Response 包含: XOR-MAPPED-ADDRESS = 1.2.3.4:12345\n'
            '客户端由此得知自己的公网 IP 和端口',
            ha='center', va='center', fontsize=10, color=C['dark_text'])

    save_fig(fig, 'stun_protocol')


# ── 5. turn_relay.png ───────────────────────────────────────────────────────
def draw_turn_relay():
    fig, ax = new_fig(12, 7)
    no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_title('TURN 中继转发原理', fontsize=16, fontweight='bold', color=C['dark_text'], pad=20)

    draw_box(ax, 0.3, 3.0, 2.2, 2.0, 'Peer A\n(对称NAT后)',
             color=C['primary'], fontsize=10)
    draw_box(ax, 4.8, 2.5, 2.8, 3.0, 'TURN\n中继服务器\n(公网IP)',
             color=C['danger'], fontsize=11)
    draw_box(ax, 9.3, 3.0, 2.2, 2.0, 'Peer B\n(对称NAT后)',
             color=C['primary'], fontsize=10)

    draw_sequence_arrow(ax, 2.5, 4.8, 5.0, '媒体数据', color=C['secondary'], fontsize=9)
    draw_sequence_arrow(ax, 7.6, 9.3, 5.0, '媒体数据', color=C['secondary'], fontsize=9)

    draw_sequence_arrow(ax, 9.3, 7.6, 3.5, '媒体数据', color=C['info'], fontsize=9)
    draw_sequence_arrow(ax, 4.8, 2.5, 3.5, '媒体数据', color=C['info'], fontsize=9)

    p2p_y = 7.0
    ax.annotate('', xy=(9.3, p2p_y), xytext=(2.5, p2p_y),
                arrowprops=dict(arrowstyle='<->', color=C['danger'],
                                lw=1.5, linestyle='dashed'))
    ax.text(6.0, p2p_y + 0.3, 'P2P 直连失败（双方均为对称NAT）', ha='center',
            fontsize=10, color=C['danger'], fontweight='bold')
    ax.text(6.0, p2p_y - 0.3, '✗', ha='center', fontsize=14, color=C['danger'])

    info = FancyBboxPatch((2.5, 0.3), 7.0, 1.0, boxstyle="round,pad=0.15",
                           facecolor=C['light_orange'], edgecolor=C['warning'],
                           linewidth=1.5, zorder=2)
    ax.add_patch(info)
    ax.text(6.0, 0.8, '当 P2P 穿越失败时，TURN 服务器充当中继角色\n'
            '所有媒体数据经由 TURN 服务器中转，延迟和带宽成本较高',
            ha='center', va='center', fontsize=9, color=C['dark_text'])

    save_fig(fig, 'turn_relay')


# ── 6. ice_process.png ──────────────────────────────────────────────────────
def draw_ice_process():
    fig, ax = new_fig(14, 9)
    no_axes(ax)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_title('ICE 候选收集与连通性检查', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    # ── 左侧：候选收集 ──
    ax.text(3.5, 9.5, '① 候选收集阶段', fontsize=13, fontweight='bold',
            ha='center', color=C['dark_text'])

    draw_box(ax, 1.5, 7.8, 4.0, 1.0, '本地主机 (host candidate)\n优先级最高',
             color=C['primary'], fontsize=9)
    draw_box(ax, 1.5, 6.2, 4.0, 1.0, 'STUN 反射 (srflx candidate)\n通过 STUN 获取公网地址',
             color=C['info'], fontsize=9)
    draw_box(ax, 1.5, 4.6, 4.0, 1.0, 'TURN 中继 (relay candidate)\n通过 TURN 分配中继地址',
             color=C['warning'], fontsize=9)

    ax.text(0.5, 8.3, '高', fontsize=10, color=C['accent'], fontweight='bold')
    ax.text(0.5, 6.7, '中', fontsize=10, color=C['warning'], fontweight='bold')
    ax.text(0.5, 5.1, '低', fontsize=10, color=C['danger'], fontweight='bold')
    ax.annotate('', xy=(0.7, 5.3), xytext=(0.7, 8.5),
                arrowprops=dict(arrowstyle='->', color=C['mid_text'], lw=2))
    ax.text(0.7, 4.2, '优先级', fontsize=9, ha='center', color=C['mid_text'])

    # ── 右侧：连通性检查 ──
    ax.text(10.5, 9.5, '② 连通性检查阶段', fontsize=13, fontweight='bold',
            ha='center', color=C['dark_text'])

    pairs = [
        ('host ↔ host', C['primary'], 8.5),
        ('host ↔ srflx', C['info'], 7.6),
        ('srflx ↔ srflx', C['info'], 6.7),
        ('host ↔ relay', C['warning'], 5.8),
        ('srflx ↔ relay', C['warning'], 4.9),
        ('relay ↔ relay', C['danger'], 4.0),
    ]
    for label, color, y in pairs:
        draw_box(ax, 7.8, y, 3.5, 0.6, label, color=color, fontsize=9, alpha=0.85)
        ax.text(11.6, y + 0.3, '→ STUN 检查', fontsize=8, color=C['mid_text'], va='center')

    ax.annotate('', xy=(9.5, 3.6), xytext=(9.5, 9.0),
                arrowprops=dict(arrowstyle='->', color=C['mid_text'], lw=2))
    ax.text(12.8, 6.3, '按优先级\n逐对检查', fontsize=9, ha='center', color=C['mid_text'])

    # ── 底部：结果 ──
    result_box = FancyBboxPatch((2.5, 1.0), 9.0, 1.8, boxstyle="round,pad=0.2",
                                 facecolor=C['light_green'], edgecolor=C['accent'],
                                 linewidth=2, zorder=2)
    ax.add_patch(result_box)
    ax.text(7.0, 2.2, '③ 选择最优候选对', fontsize=12, ha='center',
            fontweight='bold', color=C['accent'])
    ax.text(7.0, 1.5, '首个通过连通性检查的最高优先级候选对被选为传输路径',
            fontsize=10, ha='center', color=C['dark_text'])

    draw_arrow(ax, 3.5, 4.6, 7.0, 3.0, color=C['accent'], lw=1.5)
    draw_arrow(ax, 10.5, 4.0, 7.5, 3.0, color=C['accent'], lw=1.5)

    save_fig(fig, 'ice_process')


# ── 7. dtls_handshake.png ───────────────────────────────────────────────────
def draw_dtls_handshake():
    fig, ax = new_fig(11, 9)
    no_axes(ax)
    ax.set_xlim(0, 11)
    ax.set_ylim(0.2, 10.8)
    ax.set_title('DTLS 握手流程', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    cx, sx = 2.0, 9.0
    draw_timeline_entity(ax, cx, 10.5, 0.5, 'Client', C['primary'])
    draw_timeline_entity(ax, sx, 10.5, 0.5, 'Server', C['accent'])

    msgs = [
        (cx, sx, 9.6, 'ClientHello', C['primary']),
        (sx, cx, 8.8, 'HelloVerifyRequest (+cookie)', C['accent']),
        (cx, sx, 8.0, 'ClientHello (+cookie)', C['primary']),
        (sx, cx, 7.2, 'ServerHello', C['accent']),
        (sx, cx, 6.5, 'Certificate', C['accent']),
        (sx, cx, 5.8, 'ServerKeyExchange', C['accent']),
        (sx, cx, 5.1, 'CertificateRequest (可选)', C['info']),
        (sx, cx, 4.4, 'ServerHelloDone', C['accent']),
        (cx, sx, 3.6, 'Certificate (可选)', C['info']),
        (cx, sx, 2.9, 'ClientKeyExchange', C['primary']),
        (cx, sx, 2.2, 'ChangeCipherSpec', C['primary']),
        (cx, sx, 1.5, 'Finished', C['primary']),
        (sx, cx, 0.8, 'ChangeCipherSpec + Finished', C['accent']),
    ]
    for x1, x2, y, label, color in msgs:
        draw_sequence_arrow(ax, x1, x2, y, label, color=color, fontsize=8)

    rect = FancyBboxPatch((0.5, 8.4), 2.2, 2.0, boxstyle="round,pad=0.1",
                           facecolor='none', edgecolor=C['warning'],
                           linewidth=1.5, linestyle='--', zorder=0)
    ax.add_patch(rect)
    ax.text(1.6, 8.5, 'Cookie\n防 DoS', fontsize=7, color=C['warning'],
            ha='center', va='bottom')

    save_fig(fig, 'dtls_handshake')


# ── 8. srtp_structure.png ───────────────────────────────────────────────────
def draw_srtp_structure():
    fig, ax = new_fig(12, 8)
    no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.set_title('SRTP 报文结构对比', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    # ── RTP Header ──
    ax.text(6.0, 8.2, '普通 RTP 报文', fontsize=13, fontweight='bold',
            ha='center', color=C['primary'])
    rtp_fields = [
        ('V', 2), ('P', 1), ('X', 1), ('CC', 4), ('M', 1), ('PT', 7),
        ('Seq Number', 16),
    ]
    draw_field_row(ax, 1.5, 7.2, rtp_fields, height=0.6, fontsize=7)
    rtp_fields2 = [('Timestamp', 32)]
    draw_field_row(ax, 1.5, 6.5, rtp_fields2, height=0.6, fontsize=9)
    rtp_fields3 = [('SSRC', 32)]
    draw_field_row(ax, 1.5, 5.8, rtp_fields3, height=0.6, fontsize=9)
    rtp_payload = [('RTP Payload (音/视频数据)', 32)]
    draw_field_row(ax, 1.5, 5.1, rtp_payload, height=0.6, fontsize=9)

    # ── SRTP ──
    ax.text(6.0, 4.0, 'SRTP 报文（加密 + 认证）', fontsize=13, fontweight='bold',
            ha='center', color=C['danger'])
    draw_field_row(ax, 1.5, 3.0, [('RTP Header (不加密)', 32)], height=0.6, fontsize=9)
    draw_field_row(ax, 1.5, 2.3, [('加密的 Payload', 32)], height=0.6, fontsize=9)
    draw_field_row(ax, 1.5, 1.6, [('MKI (可选)', 12), ('Auth Tag', 20)], height=0.6, fontsize=9)

    brace_x = 10.2
    ax.annotate('', xy=(brace_x, 1.6), xytext=(brace_x, 3.6),
                arrowprops=dict(arrowstyle='-', color=C['danger'], lw=2))
    ax.text(brace_x + 0.5, 2.6, 'SRTP\n新增', fontsize=9, color=C['danger'],
            fontweight='bold', va='center')

    ax.annotate('', xy=(10.0, 2.3), xytext=(10.0, 2.9),
                arrowprops=dict(arrowstyle='<->', color=C['danger'], lw=2))
    ax.text(10.8, 2.6, '加密\n范围', fontsize=8, color=C['danger'], va='center')

    ax.annotate('', xy=(0.8, 1.6), xytext=(0.8, 3.6),
                arrowprops=dict(arrowstyle='<->', color=C['accent'], lw=2))
    ax.text(0.3, 2.6, '认证\n范围', fontsize=8, color=C['accent'], va='center', ha='center')

    save_fig(fig, 'srtp_structure')


# ── 9. dtls_wireshark.png ───────────────────────────────────────────────────
def draw_dtls_wireshark():
    fig, ax = new_fig(12, 8)
    no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.set_title('UDP 端口协议复用与首字节判断逻辑', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    draw_box(ax, 4.0, 7.5, 4.0, 1.0, 'UDP 数据包到达', color=C['dark_text'], fontsize=12)
    draw_arrow(ax, 6.0, 7.5, 6.0, 7.0, color=C['mid_text'], lw=2)

    draw_box(ax, 3.5, 5.8, 5.0, 1.0, '检查首字节 (First Byte)', color=C['info'], fontsize=11)
    draw_arrow(ax, 6.0, 5.8, 6.0, 5.3, color=C['mid_text'], lw=2)

    branches = [
        (1.0, 3.5, '[0, 3]', 'STUN\n(Binding Request/\nResponse)', C['primary']),
        (4.0, 3.5, '[16, 19]', 'ZRTP', C['secondary']),
        (6.5, 3.5, '[20, 63]', 'DTLS\n(握手/告警)', C['accent']),
        (9.2, 3.5, '[128, 191]', 'SRTP / SRTCP\n(媒体数据)', C['danger']),
    ]

    for bx, by, cond, proto, color in branches:
        draw_box(ax, bx, by, 2.4, 1.5, proto, color=color, fontsize=9)
        ax.text(bx + 1.2, by + 1.7, cond, fontsize=8, ha='center',
                color=C['dark_text'], fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor=C['light_bg'],
                          edgecolor=C['border']))
        draw_arrow(ax, 6.0, 5.3, bx + 1.2, by + 1.5, color=C['border'], lw=1.2)

    info = FancyBboxPatch((1.5, 0.5), 9.0, 1.5, boxstyle="round,pad=0.2",
                           facecolor=C['light_blue'], edgecolor=C['primary'],
                           linewidth=1.5, zorder=2)
    ax.add_patch(info)
    ax.text(6.0, 1.55, 'WebRTC 在同一 UDP 端口上复用多种协议',
            ha='center', fontsize=11, fontweight='bold', color=C['primary'])
    ax.text(6.0, 0.95, '通过 UDP payload 首字节的值域区间即可快速区分协议类型',
            ha='center', fontsize=9, color=C['dark_text'])

    save_fig(fig, 'dtls_wireshark')


# ── 10. cc_comparison.png ───────────────────────────────────────────────────
def draw_cc_comparison():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.set_facecolor('white')
    fig.suptitle('TCP 拥塞控制 vs 实时通信拥塞控制', fontsize=16,
                 fontweight='bold', color=C['dark_text'])

    t = np.linspace(0, 10, 200)

    # ── TCP CC ──
    ax1.set_title('TCP 拥塞控制', fontsize=13, fontweight='bold', color=C['primary'])
    saw = np.zeros_like(t)
    cycle = 3.0
    for i, ti in enumerate(t):
        phase = ti % cycle
        saw[i] = 2.0 + 3.0 * (phase / cycle)
        if phase > cycle * 0.9:
            saw[i] = 2.0
    saw += 0.15 * np.random.randn(200)
    ax1.plot(t, saw, color=C['primary'], lw=2, label='发送速率')
    ax1.fill_between(t, saw, alpha=0.15, color=C['primary'])
    ax1.set_xlabel('时间', fontsize=11)
    ax1.set_ylabel('吞吐量', fontsize=11, color=C['primary'])
    ax1.set_ylim(0, 7)
    ax1_r = ax1.twinx()
    delay = 50 + 30 * np.sin(0.8 * t) + 100 * (saw - 2) / 3
    ax1_r.plot(t, delay, color=C['danger'], lw=1.5, linestyle='--', label='延迟')
    ax1_r.set_ylabel('延迟 (ms)', fontsize=11, color=C['danger'])
    ax1_r.set_ylim(0, 350)
    ax1.text(5, 6.2, '目标：最大化吞吐量', fontsize=11, ha='center',
             color=C['primary'], fontweight='bold')
    ax1.legend(loc='upper left', fontsize=9)
    ax1_r.legend(loc='upper right', fontsize=9)

    # ── RTC CC ──
    ax2.set_title('实时通信拥塞控制', fontsize=13, fontweight='bold', color=C['accent'])
    rtc_rate = 2.5 + 0.3 * np.sin(0.5 * t) + 0.1 * np.random.randn(200)
    ax2.plot(t, rtc_rate, color=C['accent'], lw=2, label='发送速率')
    ax2.fill_between(t, rtc_rate, alpha=0.15, color=C['accent'])
    ax2.axhline(y=2.5, color=C['accent'], linestyle=':', lw=1, alpha=0.5)
    ax2.set_xlabel('时间', fontsize=11)
    ax2.set_ylabel('码率 (Mbps)', fontsize=11, color=C['accent'])
    ax2.set_ylim(0, 7)
    ax2_r = ax2.twinx()
    rtc_delay = 30 + 5 * np.sin(t) + 3 * np.random.randn(200)
    ax2_r.plot(t, rtc_delay, color=C['danger'], lw=1.5, linestyle='--', label='延迟')
    ax2_r.set_ylabel('延迟 (ms)', fontsize=11, color=C['danger'])
    ax2_r.set_ylim(0, 350)
    ax2.text(5, 6.2, '目标：低延迟 + 稳定码率', fontsize=11, ha='center',
             color=C['accent'], fontweight='bold')
    ax2.legend(loc='upper left', fontsize=9)
    ax2_r.legend(loc='upper right', fontsize=9)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'cc_comparison')


# ── 11. gcc_algorithm.png ───────────────────────────────────────────────────
def draw_gcc_algorithm():
    fig, ax = new_fig(14, 7)
    no_axes(ax)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_title('GCC (Google Congestion Control) 算法流程', fontsize=16,
                 fontweight='bold', color=C['dark_text'], pad=20)

    boxes = [
        (0.3, 3.5, 2.2, 1.5, '接收端\n到达时间', C['primary']),
        (3.0, 3.5, 2.2, 1.5, '延迟梯度\n计算\n(Δdelay)', C['info']),
        (5.7, 3.5, 2.2, 1.5, '卡尔曼\n滤波器', C['secondary']),
        (8.4, 3.5, 2.2, 1.5, '过载\n检测器', C['warning']),
        (11.1, 3.5, 2.2, 1.5, '速率\n控制器', C['accent']),
    ]
    for x, y, w, h, text, color in boxes:
        draw_box(ax, x, y, w, h, text, color=color, fontsize=10)

    for i in range(len(boxes) - 1):
        x1 = boxes[i][0] + boxes[i][2]
        x2 = boxes[i + 1][0]
        cy = boxes[i][1] + boxes[i][3] / 2
        draw_arrow(ax, x1, cy, x2, cy, color=C['dark_text'], lw=2)

    states_y = 1.0
    states = [
        (9.0, states_y, 'Increase\n(增加码率)', C['accent']),
        (11.0, states_y, 'Decrease\n(降低码率)', C['danger']),
        (13.0, states_y, 'Hold\n(保持)', C['warning']),
    ]
    for x, y, text, color in states:
        draw_box(ax, x - 0.9, y, 1.8, 1.0, text, color=color, fontsize=8)

    draw_arrow(ax, 12.2, 3.5, 9.0, 2.0, color=C['accent'], lw=1.3)
    draw_arrow(ax, 12.2, 3.5, 11.0, 2.0, color=C['danger'], lw=1.3)
    draw_arrow(ax, 12.2, 3.5, 13.0, 2.0, color=C['warning'], lw=1.3)

    ax.text(7.0, 7.0, '发送端基于 RTCP 反馈进行基于延迟的带宽估计',
            ha='center', fontsize=11, color=C['dark_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['light_blue'],
                      edgecolor=C['primary'], lw=1.5))

    ax.text(7.0, 6.0, '接收端测量包间到达时间差，计算延迟梯度，经滤波后判断网络状态',
            ha='center', fontsize=9, color=C['mid_text'])

    save_fig(fig, 'gcc_algorithm')


# ── 12. twcc_feedback.png ───────────────────────────────────────────────────
def draw_twcc_feedback():
    fig, ax = new_fig(13, 8)
    no_axes(ax)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.set_title('TWCC (Transport-Wide Congestion Control) 反馈机制',
                 fontsize=15, fontweight='bold', color=C['dark_text'], pad=20)

    sx, rx = 2.5, 10.5
    draw_timeline_entity(ax, sx, 8.5, 0.5, '发送端', C['primary'])
    draw_timeline_entity(ax, rx, 8.5, 0.5, '接收端', C['accent'])

    pkts_y = 7.5
    for i, seq in enumerate([101, 102, 103, 104, 105]):
        y = pkts_y - i * 0.7
        draw_sequence_arrow(ax, sx, rx, y, f'RTP Seq#{seq}',
                            color=C['primary'], fontsize=8)

    ax.text(rx + 0.5, 5.5, '记录每个包\n的到达时间', fontsize=8, color=C['accent'],
            ha='left', va='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor=C['light_green'],
                      edgecolor=C['accent']))

    draw_sequence_arrow(ax, rx, sx, 3.5, 'RTCP TWCC Feedback\n(序号 + 到达时间差)',
                        color=C['danger'], fontsize=9)

    info_y = 1.5
    info = FancyBboxPatch((1.5, info_y - 0.5), 10.0, 1.5, boxstyle="round,pad=0.2",
                           facecolor=C['light_blue'], edgecolor=C['primary'],
                           linewidth=1.5, zorder=2)
    ax.add_patch(info)
    ax.text(6.5, info_y + 0.5, '发送端根据 TWCC 反馈计算带宽估计',
            ha='center', fontsize=11, fontweight='bold', color=C['primary'])
    ax.text(6.5, info_y - 0.05, '对比发送时间间隔 vs 到达时间间隔 → 判断网络拥塞程度 → 调整发送码率',
            ha='center', fontsize=9, color=C['dark_text'])

    save_fig(fig, 'twcc_feedback')


# ── 13. simulcast_svc.png ───────────────────────────────────────────────────
def draw_simulcast_svc():
    fig, ax = new_fig(14, 8)
    no_axes(ax)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_title('Simulcast vs SVC 对比', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    ax.plot([7, 7], [0.5, 8.5], '--', color=C['border'], lw=1.5, zorder=0)
    ax.text(3.5, 8.3, 'Simulcast（联播）', fontsize=14, fontweight='bold',
            ha='center', color=C['primary'])
    ax.text(10.5, 8.3, 'SVC（可伸缩编码）', fontsize=14, fontweight='bold',
            ha='center', color=C['secondary'])

    # ── Simulcast 左侧 ──
    enc_x = 0.5
    draw_box(ax, enc_x, 6.3, 2.2, 1.2, '高分辨率\n编码器', color=C['primary'], fontsize=9)
    draw_box(ax, enc_x, 4.6, 2.2, 1.2, '中分辨率\n编码器', color=C['info'], fontsize=9)
    draw_box(ax, enc_x, 2.9, 2.2, 1.2, '低分辨率\n编码器', color=C['accent'], fontsize=9)

    sfu_lx = 4.0
    draw_box(ax, sfu_lx, 4.2, 2.0, 2.5, 'SFU\n选择\n转发', color=C['warning'], fontsize=10)

    for ey in [6.9, 5.2, 3.5]:
        draw_arrow(ax, enc_x + 2.2, ey, sfu_lx, 5.5, color=C['mid_text'], lw=1.3)

    draw_arrow(ax, sfu_lx + 2.0, 6.0, sfu_lx + 2.5, 6.5, color=C['primary'], lw=1.3)
    ax.text(sfu_lx + 2.7, 6.5, '高', fontsize=9, color=C['primary'], fontweight='bold')
    draw_arrow(ax, sfu_lx + 2.0, 5.5, sfu_lx + 2.5, 5.5, color=C['info'], lw=1.3)
    ax.text(sfu_lx + 2.7, 5.5, '中', fontsize=9, color=C['info'], fontweight='bold')
    draw_arrow(ax, sfu_lx + 2.0, 5.0, sfu_lx + 2.5, 4.5, color=C['accent'], lw=1.3)
    ax.text(sfu_lx + 2.7, 4.5, '低', fontsize=9, color=C['accent'], fontweight='bold')

    ax.text(3.5, 1.5, '三路独立编码\nSFU 根据接收端带宽\n选择转发对应分辨率流',
            ha='center', fontsize=9, color=C['mid_text'], style='italic')

    # ── SVC 右侧 ──
    enc_rx = 7.8
    draw_box(ax, enc_rx, 6.3, 2.5, 1.2, '增强层 2\n(高分辨率)', color=C['primary'],
             fontsize=9, alpha=0.7)
    draw_box(ax, enc_rx, 4.6, 2.5, 1.2, '增强层 1\n(中分辨率)', color=C['info'],
             fontsize=9, alpha=0.8)
    draw_box(ax, enc_rx, 2.9, 2.5, 1.2, '基础层\n(低分辨率)', color=C['accent'], fontsize=9)

    ax.annotate('', xy=(enc_rx + 2.8, 3.5), xytext=(enc_rx + 2.8, 7.5),
                arrowprops=dict(arrowstyle='<->', color=C['secondary'], lw=2))
    ax.text(enc_rx + 3.2, 5.5, '一路\n分层\n编码', fontsize=9, color=C['secondary'],
            fontweight='bold', va='center')

    sfu_rx = 11.5
    draw_box(ax, sfu_rx, 4.2, 2.0, 2.5, 'SFU\n按层\n转发', color=C['warning'], fontsize=10)

    for ey in [6.9, 5.2, 3.5]:
        draw_arrow(ax, enc_rx + 2.5, ey, sfu_rx, 5.5, color=C['mid_text'], lw=1.3)

    ax.text(10.5, 1.5, '单路分层编码\nSFU 丢弃高层即可降低码率\n无需重新编码',
            ha='center', fontsize=9, color=C['mid_text'], style='italic')

    save_fig(fig, 'simulcast_svc')


# ── 14. libwebrtc_api.png ───────────────────────────────────────────────────
def draw_libwebrtc_api():
    fig, ax = new_fig(14, 9)
    no_axes(ax)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_title('libwebrtc API 层次与线程模型', fontsize=16, fontweight='bold',
                 color=C['dark_text'], pad=20)

    draw_box(ax, 3.5, 8.0, 5.0, 1.2, 'PeerConnectionFactory',
             color=C['primary'], fontsize=13)

    draw_arrow(ax, 6.0, 8.0, 6.0, 7.5, color=C['mid_text'], lw=2)
    ax.text(6.3, 7.7, 'Create()', fontsize=8, color=C['mid_text'])

    draw_box(ax, 3.5, 5.8, 5.0, 1.2, 'PeerConnection',
             color=C['secondary'], fontsize=13)

    targets = [
        (1.0, 3.5, 3.0, 1.2, 'AudioTrack', C['danger']),
        (5.0, 3.5, 3.0, 1.2, 'VideoTrack', C['accent']),
        (9.0, 3.5, 3.0, 1.2, 'DataChannel', C['warning']),
    ]
    for x, y, w, h, text, color in targets:
        draw_box(ax, x, y, w, h, text, color=color, fontsize=12)
        draw_arrow(ax, 6.0, 5.8, x + w / 2, y + h, color=C['mid_text'], lw=1.5)

    sub_items = [
        (1.0, 2.0, 3.0, 1.0, 'AudioSource\nAudioSink', C['danger'], 0.6),
        (5.0, 2.0, 3.0, 1.0, 'VideoSource\nVideoSink', C['accent'], 0.6),
        (9.0, 2.0, 3.0, 1.0, 'Send() / OnMessage\nOrdered/Unordered', C['warning'], 0.6),
    ]
    for x, y, w, h, text, color, alpha in sub_items:
        draw_box(ax, x, y, w, h, text, color=color, fontsize=8, alpha=alpha)

    # ── 线程模型 ──
    thread_x = 11.5
    threads = [
        (thread_x, 8.0, 'Signaling\nThread', C['primary']),
        (thread_x, 6.2, 'Worker\nThread', C['secondary']),
        (thread_x, 4.4, 'Network\nThread', C['accent']),
    ]
    for x, y, text, color in threads:
        draw_box(ax, x, y, 2.2, 1.2, text, color=color, fontsize=9)

    ax.text(thread_x + 1.1, 9.5, '三线程模型', fontsize=11, ha='center',
            fontweight='bold', color=C['dark_text'])

    descs = [
        (thread_x + 2.5, 8.6, 'SDP/ICE\n信令处理'),
        (thread_x + 2.5, 6.8, '编解码\n媒体处理'),
        (thread_x + 2.5, 5.0, '网络收发\nSocket I/O'),
    ]
    for x, y, text in descs:
        ax.text(x, y, text, fontsize=7, color=C['mid_text'], va='center')

    draw_dashed_line(ax, 11.0, 3.0, 11.0, 9.5, color=C['border'], lw=1)

    save_fig(fig, 'libwebrtc_api')


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    print('=== 第五篇：WebRTC 技术体系 ===')
    draw_webrtc_stack()
    draw_webrtc_flow()
    draw_nat_types()
    draw_stun_protocol()
    draw_turn_relay()
    draw_ice_process()
    draw_dtls_handshake()
    draw_srtp_structure()
    draw_dtls_wireshark()
    draw_cc_comparison()
    draw_gcc_algorithm()
    draw_twcc_feedback()
    draw_simulcast_svc()
    draw_libwebrtc_api()
    print('=== 第五篇完成 ===\n')


if __name__ == '__main__':
    main()
