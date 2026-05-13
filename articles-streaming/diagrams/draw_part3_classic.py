#!/usr/bin/env python3
"""Part 3: 经典协议 - 生成 RTSP/RTMP/FLV/HTTP-FLV 相关的 8 张技术插图。"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    COLORS, save_fig, new_fig, no_axes,
    draw_box, draw_arrow, draw_brace_text,
    draw_sequence_arrow, draw_dashed_line,
    draw_field_row, draw_timeline_entity,
    plt, np, FancyBboxPatch, mpatches,
)


# ── 1. RTSP 协议栈 ─────────────────────────────────────────────────────────
def draw_rtsp_stack():
    fig, ax = new_fig(10, 6)
    ax = no_axes(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)

    ax.text(5, 7.5, 'RTSP 协议栈', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # 左侧：信令通道
    ax.text(3, 6.8, '信令通道', ha='center', va='center',
            fontsize=10, fontweight='bold', color=COLORS['primary'])
    draw_box(ax, 1.5, 5.6, 3, 0.8, 'RTSP 信令',
             color=COLORS['primary'], fontsize=11)
    draw_box(ax, 1.5, 4.4, 3, 0.8, 'TCP',
             color=COLORS['secondary'], fontsize=11)
    draw_box(ax, 1.5, 3.2, 3, 0.8, 'IP',
             color=COLORS['info'], fontsize=11)

    # 右侧：数据通道
    ax.text(7, 6.8, '数据通道', ha='center', va='center',
            fontsize=10, fontweight='bold', color=COLORS['accent'])
    draw_box(ax, 5.5, 5.6, 3, 0.8, 'RTP / RTCP',
             color=COLORS['accent'], fontsize=11)
    draw_box(ax, 5.5, 4.4, 3, 0.8, 'UDP',
             color=COLORS['warning'], fontsize=11)
    draw_box(ax, 5.5, 3.2, 3, 0.8, 'IP',
             color=COLORS['info'], fontsize=11)

    # 共享底层
    draw_box(ax, 1.5, 2.0, 7, 0.8, '网络接口层（以太网 / Wi-Fi）',
             color=COLORS['mid_text'], fontsize=11)

    draw_dashed_line(ax, 4.5, 6.0, 5.5, 6.0, color=COLORS['border'], lw=1.5)
    ax.text(5, 6.2, '协同', ha='center', va='center',
            fontsize=7, color=COLORS['mid_text'])

    ax.text(3, 1.2, '可靠传输，保证信令到达', ha='center', va='center',
            fontsize=8, color=COLORS['mid_text'], style='italic')
    ax.text(7, 1.2, '低延迟，实时数据传输', ha='center', va='center',
            fontsize=8, color=COLORS['mid_text'], style='italic')
    save_fig(fig, 'rtsp_stack')


# ── 2. RTSP 交互时序图 ─────────────────────────────────────────────────────
def draw_rtsp_sequence():
    fig, ax = new_fig(10, 8)
    ax = no_axes(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    ax.text(5, 9.5, 'RTSP 完整交互时序', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    draw_timeline_entity(ax, 2, 9.0, 0.8, 'Client', color=COLORS['primary'])
    draw_timeline_entity(ax, 8, 9.0, 0.8, 'Server', color=COLORS['accent'])

    steps = [
        ('OPTIONS',  '查询支持的方法',   COLORS['mid_text']),
        ('DESCRIBE', '获取媒体描述(SDP)', COLORS['primary']),
        ('SETUP',    '建立传输通道',      COLORS['secondary']),
        ('PLAY',     '开始播放',          COLORS['accent']),
        ('RTP 数据流 >>>', '音视频数据传输', COLORS['warning']),
        ('TEARDOWN', '结束会话',          COLORS['danger']),
    ]

    y_start, y_step = 8.3, 1.15
    for i, (method, desc, color) in enumerate(steps):
        y = y_start - i * y_step
        if method.startswith('RTP'):
            draw_sequence_arrow(ax, 2, 8, y, label=method,
                                color=color, fontsize=9)
            ax.plot([2, 8], [y, y], '--', color=color, lw=1, alpha=0.3)
        else:
            draw_sequence_arrow(ax, 2, 8, y, label=method,
                                color=color, fontsize=9)
            draw_sequence_arrow(ax, 8, 2, y - 0.45,
                                label='200 OK', color=COLORS['mid_text'],
                                fontsize=7)
        ax.text(9.2, y - 0.1, desc, ha='left', va='center',
                fontsize=7, color=COLORS['mid_text'], style='italic')
    save_fig(fig, 'rtsp_sequence')


# ── 3. live555 架构图 ──────────────────────────────────────────────────────
def draw_live555_arch():
    fig, ax = new_fig(12, 7)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)

    ax.text(6, 8.5, 'live555 架构与核心模块', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # 应用层
    draw_box(ax, 3.5, 7.4, 5, 0.7, '应用层（RTSP Server / Client）',
             color=COLORS['mid_text'], fontsize=10)

    # liveMedia
    lm_bg = FancyBboxPatch((0.5, 3.5), 5.5, 3.5,
                            boxstyle="round,pad=0.1,rounding_size=0.2",
                            facecolor=COLORS['light_blue'],
                            edgecolor=COLORS['primary'], linewidth=2, zorder=0)
    ax.add_patch(lm_bg)
    ax.text(3.25, 6.7, 'liveMedia', ha='center', va='center',
            fontsize=12, fontweight='bold', color=COLORS['primary'])
    for i, cls in enumerate([
        'RTSPServer / RTSPClient',
        'ServerMediaSession',
        'MediaSource / MediaSink',
        'RTPSource / RTPSink',
        'H264VideoStreamFramer',
    ]):
        draw_box(ax, 0.8, 6.2 - i * 0.55, 4.9, 0.45, cls,
                 color=COLORS['primary'], fontsize=7, radius=0.1, alpha=0.85)

    # UsageEnvironment
    ue_bg = FancyBboxPatch((6.3, 5.5), 5.2, 1.5,
                            boxstyle="round,pad=0.1,rounding_size=0.2",
                            facecolor=COLORS['light_purple'],
                            edgecolor=COLORS['secondary'], linewidth=2, zorder=0)
    ax.add_patch(ue_bg)
    ax.text(8.9, 6.7, 'UsageEnvironment', ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['secondary'])
    for i, cls in enumerate([
        'TaskScheduler（事件调度）',
        'UsageEnvironment（抽象接口）',
    ]):
        draw_box(ax, 6.6, 6.1 - i * 0.55, 4.6, 0.45, cls,
                 color=COLORS['secondary'], fontsize=7, radius=0.1, alpha=0.85)

    # BasicUsageEnvironment
    bue_bg = FancyBboxPatch((6.3, 3.5), 5.2, 1.6,
                             boxstyle="round,pad=0.1,rounding_size=0.2",
                             facecolor=COLORS['light_green'],
                             edgecolor=COLORS['accent'], linewidth=2, zorder=0)
    ax.add_patch(bue_bg)
    ax.text(8.9, 4.8, 'BasicUsageEnvironment', ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['accent'])
    for i, cls in enumerate([
        'BasicTaskScheduler（select实现）',
        'BasicUsageEnvironment（具体实现）',
    ]):
        draw_box(ax, 6.6, 4.3 - i * 0.55, 4.6, 0.45, cls,
                 color=COLORS['accent'], fontsize=7, radius=0.1, alpha=0.85)

    # groupsock
    gs_bg = FancyBboxPatch((2.0, 1.0), 8.0, 1.8,
                            boxstyle="round,pad=0.1,rounding_size=0.2",
                            facecolor=COLORS['light_orange'],
                            edgecolor=COLORS['warning'], linewidth=2, zorder=0)
    ax.add_patch(gs_bg)
    ax.text(6, 2.5, 'groupsock', ha='center', va='center',
            fontsize=12, fontweight='bold', color=COLORS['warning'])
    draw_box(ax, 2.3, 1.2, 7.4, 0.5,
             'Groupsock（组播/单播）      NetAddress（网络地址）      Port（端口管理）',
             color=COLORS['warning'], fontsize=8, radius=0.1, alpha=0.85)

    # 模块间箭头
    draw_arrow(ax, 3.25, 3.5, 3.25, 2.8, color=COLORS['dark_text'], lw=1.5)
    draw_arrow(ax, 8.9, 3.5, 8.9, 2.8, color=COLORS['dark_text'], lw=1.5)
    draw_arrow(ax, 6, 7.4, 3.25, 7.0, color=COLORS['dark_text'], lw=1.5)
    draw_arrow(ax, 6, 7.4, 8.9, 7.0, color=COLORS['dark_text'], lw=1.5)
    save_fig(fig, 'live555_arch')


# ── 4. RTMP 协议栈 ─────────────────────────────────────────────────────────
def draw_rtmp_stack():
    fig, ax = new_fig(8, 6)
    ax = no_axes(ax)
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 8)

    ax.text(4, 7.5, 'RTMP 协议栈', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    layers = [
        ('音视频数据（H.264 / AAC）', COLORS['mid_text'],   6.3),
        ('RTMP Message（消息）',       COLORS['primary'],    5.2),
        ('RTMP Chunk（分块传输）',     COLORS['secondary'],  4.1),
        ('TCP（可靠传输）',            COLORS['accent'],     3.0),
        ('IP',                         COLORS['info'],       1.9),
    ]
    for label, color, y in layers:
        draw_box(ax, 1, y, 6, 0.8, label, color=color, fontsize=11)

    ax.annotate('', xy=(7.3, 5.6), xytext=(7.3, 6.7),
                arrowprops=dict(arrowstyle='<->', color=COLORS['warning'], lw=1.5))
    ax.text(7.5, 6.15, '一个 Message\n拆分为多个\nChunk 传输', ha='left', va='center',
            fontsize=8, color=COLORS['warning'])

    ax.text(4, 1.2, 'RTMP 基于 TCP，端口默认 1935',
            ha='center', va='center', fontsize=9, color=COLORS['mid_text'],
            style='italic')
    save_fig(fig, 'rtmp_stack')


# ── 5. RTMP 握手流程 ───────────────────────────────────────────────────────
def draw_rtmp_handshake():
    fig, ax = new_fig(10, 7)
    ax = no_axes(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)

    ax.text(5, 8.5, 'RTMP 三阶段握手', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    draw_timeline_entity(ax, 2, 8.0, 1.0, 'Client', color=COLORS['primary'])
    draw_timeline_entity(ax, 8, 8.0, 1.0, 'Server', color=COLORS['accent'])

    phases = [
        (7.2, 'C0（版本号, 1字节）',
               'S0（版本号, 1字节）',            COLORS['primary'],   '阶段一'),
        (5.7, 'C1（时间戳+随机数, 1536字节）',
               'S1（时间戳+随机数, 1536字节）',  COLORS['secondary'], '阶段二'),
        (4.2, 'C2（S1的回显, 1536字节）',
               'S2（C1的回显, 1536字节）',        COLORS['accent'],    '阶段三'),
    ]
    for y, c_label, s_label, color, phase_name in phases:
        draw_sequence_arrow(ax, 2, 8, y, label=c_label,
                            color=color, fontsize=8)
        draw_sequence_arrow(ax, 8, 2, y - 0.6, label=s_label,
                            color=color, fontsize=8)
        ax.text(0.5, y - 0.3, phase_name, ha='center', va='center',
                fontsize=8, fontweight='bold', color=color,
                bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['white'],
                          edgecolor=color))

    draw_box(ax, 2.5, 2.8, 5, 0.6, '握手完成，开始传输数据',
             color=COLORS['accent'], fontsize=10)

    ax.text(5, 1.8,
            '注意：C0/S0 和 C1/S1 通常一起发送，C2/S2 在收到对方 S1/C1 后发送',
            ha='center', va='center', fontsize=8, color=COLORS['mid_text'],
            style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_bg'],
                      edgecolor=COLORS['border']))
    save_fig(fig, 'rtmp_handshake')


# ── 6. RTMP Chunk 结构图 ───────────────────────────────────────────────────
def draw_rtmp_chunk():
    fig, ax = new_fig(12, 5.5)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)

    ax.text(6, 6.5, 'RTMP Chunk 结构', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    fields = [
        ('Basic Header\n(1-3字节)',               2.5, COLORS['primary'],   COLORS['light_blue']),
        ('Message Header\n(0/3/7/11字节)',         3.5, COLORS['secondary'], COLORS['light_purple']),
        ('Extended Timestamp\n(0/4字节)',           2.0, COLORS['warning'],   COLORS['light_orange']),
        ('Chunk Data',                              3.0, COLORS['accent'],    COLORS['light_green']),
    ]
    x = 0.5
    for label, w, color, bg in fields:
        box = FancyBboxPatch((x, 4.5), w, 1.2,
                              boxstyle="round,pad=0.05,rounding_size=0.1",
                              facecolor=bg, edgecolor=color,
                              linewidth=2, zorder=2)
        ax.add_patch(box)
        ax.text(x + w / 2, 5.1, label, ha='center', va='center',
                fontsize=9, fontweight='bold', color=color, zorder=3)
        x += w + 0.15

    # Basic Header 详情
    ax.text(1.75, 3.7, 'Basic Header 包含:', ha='center', va='center',
            fontsize=8, fontweight='bold', color=COLORS['primary'])
    ax.text(1.75, 3.0,
            'fmt(2bit): 决定 Message Header 长度\n'
            'cs id(6bit~): Chunk Stream ID',
            ha='center', va='center', fontsize=7, color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_blue'],
                      edgecolor=COLORS['primary'], linestyle='--'))

    # Message Header 详情
    ax.text(5.6, 3.7, 'Message Header 长度取决于 fmt:',
            ha='center', va='center', fontsize=8, fontweight='bold',
            color=COLORS['secondary'])
    ax.text(5.6, 2.3,
            'fmt=0: 11字节（完整头）\n'
            'fmt=1: 7字节（省略stream id）\n'
            'fmt=2: 3字节（仅时间戳增量）\n'
            'fmt=3: 0字节（复用前一个头）',
            ha='center', va='center', fontsize=7, color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_purple'],
                      edgecolor=COLORS['secondary'], linestyle='--'))

    # Chunk Data 详情
    ax.text(10.4, 3.7, 'Chunk Data:', ha='center', va='center',
            fontsize=8, fontweight='bold', color=COLORS['accent'])
    ax.text(10.4, 3.0, '实际载荷数据\n默认最大 128 字节',
            ha='center', va='center', fontsize=7, color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_green'],
                      edgecolor=COLORS['accent'], linestyle='--'))
    save_fig(fig, 'rtmp_chunk')


# ── 7. FLV 文件结构 ────────────────────────────────────────────────────────
def draw_flv_structure():
    fig, ax = new_fig(12, 6.5)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.5)

    ax.text(6, 8.0, 'FLV 文件结构', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    # ── 顶层布局 ──
    elements = [
        ('FLV Header\n(9字节)',       1.8, COLORS['primary'],   COLORS['light_blue']),
        ('PrevTagSize0\n(4字节)',      1.5, COLORS['mid_text'],  COLORS['light_bg']),
        ('Tag1',                       1.3, COLORS['accent'],    COLORS['light_green']),
        ('PrevTagSize1\n(4字节)',      1.5, COLORS['mid_text'],  COLORS['light_bg']),
        ('Tag2',                       1.3, COLORS['warning'],   COLORS['light_orange']),
        ('...',                        0.6, COLORS['mid_text'],  COLORS['light_bg']),
        ('TagN',                       1.3, COLORS['secondary'], COLORS['light_purple']),
    ]
    x = 0.3
    for label, w, color, bg in elements:
        box = FancyBboxPatch((x, 6.2), w, 1.0,
                              boxstyle="round,pad=0.03,rounding_size=0.1",
                              facecolor=bg, edgecolor=color,
                              linewidth=1.5, zorder=2)
        ax.add_patch(box)
        ax.text(x + w / 2, 6.7, label, ha='center', va='center',
                fontsize=7, fontweight='bold', color=color, zorder=3)
        x += w + 0.1

    # ── FLV Header 展开 ──
    ax.text(2.5, 5.3, 'FLV Header (9字节)', ha='center', va='center',
            fontsize=9, fontweight='bold', color=COLORS['primary'])
    hdr_fields = [
        ('签名 "FLV"', 1.5, COLORS['primary']),
        ('版本',       0.8, COLORS['secondary']),
        ('标志位',     0.8, COLORS['accent']),
        ('DataOffset', 1.2, COLORS['warning']),
    ]
    hx = 0.5
    for label, w, color in hdr_fields:
        box = FancyBboxPatch((hx, 4.3), w, 0.6,
                              boxstyle="square,pad=0", facecolor=color,
                              edgecolor=COLORS['white'], linewidth=1,
                              alpha=0.85, zorder=2)
        ax.add_patch(box)
        ax.text(hx + w / 2, 4.6, label, ha='center', va='center',
                fontsize=7, fontweight='bold', color=COLORS['white'], zorder=3)
        hx += w

    # ── Tag 内部结构 ──
    ax.text(8.5, 5.3, 'Tag 内部结构', ha='center', va='center',
            fontsize=9, fontweight='bold', color=COLORS['accent'])
    tag_hdr = FancyBboxPatch((5.5, 4.3), 3.0, 0.6,
                              boxstyle="round,pad=0.03,rounding_size=0.08",
                              facecolor=COLORS['accent'],
                              edgecolor=COLORS['accent'], linewidth=1.5, zorder=2)
    ax.add_patch(tag_hdr)
    ax.text(7.0, 4.6, 'Tag Header (11字节)', ha='center', va='center',
            fontsize=8, fontweight='bold', color=COLORS['white'], zorder=3)

    tag_data = FancyBboxPatch((8.6, 4.3), 3.0, 0.6,
                               boxstyle="round,pad=0.03,rounding_size=0.08",
                               facecolor=COLORS['warning'],
                               edgecolor=COLORS['warning'], linewidth=1.5, zorder=2)
    ax.add_patch(tag_data)
    ax.text(10.1, 4.6, 'Tag Data (变长)', ha='center', va='center',
            fontsize=8, fontweight='bold', color=COLORS['white'], zorder=3)

    # Tag Header 细分
    th_fields = [
        ('类型\n(1B)',       0.8, COLORS['primary']),
        ('数据大小\n(3B)',   1.1, COLORS['secondary']),
        ('时间戳\n(3B)',     1.0, COLORS['accent']),
        ('时间戳扩展\n(1B)', 1.1, COLORS['warning']),
        ('StreamID\n(3B)',   1.0, COLORS['danger']),
    ]
    thx = 3.5
    for label, w, color in th_fields:
        box = FancyBboxPatch((thx, 2.7), w, 0.8,
                              boxstyle="square,pad=0", facecolor=color,
                              edgecolor=COLORS['white'], linewidth=1,
                              alpha=0.85, zorder=2)
        ax.add_patch(box)
        ax.text(thx + w / 2, 3.1, label, ha='center', va='center',
                fontsize=6, fontweight='bold', color=COLORS['white'], zorder=3)
        thx += w

    ax.text(6.0, 2.3, '← Tag Header 11字节详细分解 →',
            ha='center', va='center', fontsize=8, color=COLORS['mid_text'])

    ax.text(6, 1.4, 'Tag 类型：8=音频  9=视频  18=脚本数据(metadata)',
            ha='center', va='center', fontsize=9, color=COLORS['dark_text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_bg'],
                      edgecolor=COLORS['border']))
    save_fig(fig, 'flv_structure')


# ── 8. HTTP-FLV 直播架构 ───────────────────────────────────────────────────
def draw_http_flv_arch():
    fig, ax = new_fig(12, 5.5)
    ax = no_axes(ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)

    ax.text(6, 6.5, 'HTTP-FLV 直播架构', ha='center', va='center',
            fontsize=14, fontweight='bold', color=COLORS['dark_text'])

    components = [
        (0.5,  3.0, 2.0, 1.5, '推流端\n(OBS/FFmpeg)',    COLORS['primary']),
        (4.0,  3.0, 2.5, 1.5, '流媒体服务器\n(Nginx-RTMP)', COLORS['accent']),
        (8.5,  3.0, 3.0, 1.5, '播放端\n(浏览器/flv.js)',   COLORS['warning']),
    ]
    for cx, cy, cw, ch, label, color in components:
        bg = FancyBboxPatch((cx, cy), cw, ch,
                             boxstyle="round,pad=0.1,rounding_size=0.3",
                             facecolor=color, edgecolor=color,
                             linewidth=2, alpha=0.15, zorder=1)
        ax.add_patch(bg)
        inner = FancyBboxPatch((cx + 0.15, cy + 0.15), cw - 0.3, ch - 0.3,
                                boxstyle="round,pad=0.1,rounding_size=0.2",
                                facecolor=color, edgecolor='none', zorder=2)
        ax.add_patch(inner)
        ax.text(cx + cw / 2, cy + ch / 2, label, ha='center', va='center',
                fontsize=10, fontweight='bold', color=COLORS['white'], zorder=3)

    # RTMP 推流
    ax.annotate('', xy=(4.0, 3.75), xytext=(2.5, 3.75),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=2.5))
    ax.text(3.25, 4.8, 'RTMP 推流\n(端口 1935)', ha='center', va='center',
            fontsize=9, fontweight='bold', color=COLORS['primary'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['light_blue'],
                      edgecolor=COLORS['primary']))

    # HTTP-FLV 拉流
    ax.annotate('', xy=(8.5, 3.75), xytext=(6.5, 3.75),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=2.5))
    ax.text(7.5, 4.8, 'HTTP 长连接\n(chunked transfer)', ha='center', va='center',
            fontsize=9, fontweight='bold', color=COLORS['accent'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['light_green'],
                      edgecolor=COLORS['accent']))

    ax.text(5.25, 2.5, '转封装: RTMP → FLV Tag', ha='center', va='center',
            fontsize=8, color=COLORS['mid_text'], style='italic')

    advantages = [
        '✓ 兼容 HTTP 基础设施（CDN友好）',
        '✓ 延迟低（1-3秒）',
        '✓ 浏览器可直接播放（flv.js）',
    ]
    for i, adv in enumerate(advantages):
        ax.text(2.0 + i * 3.5, 1.5, adv, ha='center', va='center',
                fontsize=8, color=COLORS['accent'], fontweight='bold')
    save_fig(fig, 'http_flv_arch')


# ── 主入口 ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('=== Part 3: 经典协议 ===')
    draw_rtsp_stack()
    draw_rtsp_sequence()
    draw_live555_arch()
    draw_rtmp_stack()
    draw_rtmp_handshake()
    draw_rtmp_chunk()
    draw_flv_structure()
    draw_http_flv_arch()
    print('=== Part 3 完成 ===')
