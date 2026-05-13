#!/usr/bin/env python3
"""
为 04-封装格式与多媒体容器.md 生成配图
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib
import os

# ============================================================
# 全局样式（与前两章统一）
# ============================================================
matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

COLORS = {
    'primary':    '#2563EB',
    'secondary':  '#7C3AED',
    'accent':     '#F59E0B',
    'success':    '#10B981',
    'danger':     '#EF4444',
    'pink':       '#EC4899',
    'cyan':       '#06B6D4',
    'bg':         '#F8FAFC',
    'grid':       '#E2E8F0',
    'text':       '#1E293B',
    'text_light': '#64748B',
    'white':      '#FFFFFF',
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')
DPI = 150


def draw_box(ax, x, y, w, h, label, color, sublabel=None, alpha=0.8, fontsize=11, radius=0.06):
    """画一个带标签的圆角矩形"""
    rect = FancyBboxPatch((x, y), w, h,
                           boxstyle=f"round,pad={radius}",
                           facecolor=color, edgecolor='white',
                           linewidth=2, alpha=alpha)
    ax.add_patch(rect)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 + 0.12, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white')
        ax.text(x + w / 2, y + h / 2 - 0.15, sublabel, ha='center', va='center',
                fontsize=fontsize - 2, color='white', alpha=0.85)
    else:
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white')
    return rect


def draw_arrow(ax, x1, y1, x2, y2, color=None, lw=2):
    """画一个箭头"""
    if color is None:
        color = COLORS['text_light']
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw))


# ============================================================
# 图1：容器 vs 编码
# ============================================================
def gen_container_vs_codec():
    fig, ax = plt.subplots(figsize=(15, 6.5))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 15)
    ax.set_ylim(-1, 6.5)
    ax.set_title('容器（Container）与编码（Codec）的关系', fontsize=16,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 编码格式（左侧）
    ax.text(1.5, 5.8, '编码格式（Codec）', fontsize=13, fontweight='bold',
            color=COLORS['text'], ha='center')
    ax.text(1.5, 5.35, '"数据的压缩方式"', fontsize=10, color=COLORS['text_light'], ha='center')

    codecs = [
        ('H.264', COLORS['primary']),
        ('H.265', COLORS['secondary']),
        ('AAC',   COLORS['danger']),
        ('Opus',  COLORS['pink']),
        ('VP9',   COLORS['cyan']),
    ]
    for i, (name, color) in enumerate(codecs):
        draw_box(ax, 0.3, 4.3 - i * 0.85, 2.4, 0.65, name, color, fontsize=11)

    # 容器格式（右侧）
    ax.text(7.5, 5.8, '容器格式（Container）', fontsize=13, fontweight='bold',
            color=COLORS['text'], ha='center')
    ax.text(7.5, 5.35, '"文件的封装方式"', fontsize=10, color=COLORS['text_light'], ha='center')

    containers = [
        ('MP4',  COLORS['accent'],    'H.264 + AAC'),
        ('MKV',  COLORS['success'],   '几乎所有编码'),
        ('FLV',  COLORS['danger'],    'H.264 + AAC/MP3'),
        ('TS',   COLORS['primary'],   'H.264/H.265 + AAC'),
        ('WebM', COLORS['cyan'],      'VP9/AV1 + Opus'),
    ]
    for i, (name, color, desc) in enumerate(containers):
        y = 4.3 - i * 0.85
        draw_box(ax, 5.5, y, 1.5, 0.65, name, color, fontsize=11)
        ax.text(7.2, y + 0.32, desc, fontsize=9, color=COLORS['text_light'], va='center')

    # 连线（展示多对多关系）
    # H.264 → MP4, MKV, FLV, TS
    connections = [
        (0, 0), (0, 1), (0, 2), (0, 3),  # H.264
        (1, 0), (1, 1), (1, 3),            # H.265
        (2, 0), (2, 1), (2, 2), (2, 3),   # AAC
        (3, 1), (3, 4),                     # Opus
        (4, 4),                             # VP9
    ]
    for ci, coi in connections:
        cy = 4.3 - ci * 0.85 + 0.32
        coy = 4.3 - coi * 0.85 + 0.32
        ax.plot([2.7, 5.5], [cy, coy],
                color=COLORS['grid'], linewidth=1, alpha=0.6, zorder=0)

    # 右侧举例框
    example_x = 10.5
    ax.text(example_x + 1.8, 5.8, '举例', fontsize=13, fontweight='bold',
            color=COLORS['text'], ha='center')

    # MP4 示例
    ey = 3.5
    outer = FancyBboxPatch((example_x, ey), 3.6, 2.2,
                            boxstyle="round,pad=0.08",
                            facecolor=COLORS['accent'], alpha=0.12,
                            edgecolor=COLORS['accent'], linewidth=2)
    ax.add_patch(outer)
    ax.text(example_x + 1.8, ey + 1.85, 'movie.mp4', fontsize=11,
            fontweight='bold', color=COLORS['accent'], ha='center')

    draw_box(ax, example_x + 0.2, ey + 0.9, 1.5, 0.6, 'H.264', COLORS['primary'],
             sublabel='视频流', fontsize=9)
    draw_box(ax, example_x + 1.9, ey + 0.9, 1.5, 0.6, 'AAC', COLORS['danger'],
             sublabel='音频流', fontsize=9)
    draw_box(ax, example_x + 0.2, ey + 0.15, 3.2, 0.55, '元数据 + 索引 + 时间戳',
             COLORS['text_light'], fontsize=9, alpha=0.5)

    # MKV 示例
    ey2 = 0.8
    outer2 = FancyBboxPatch((example_x, ey2), 3.6, 2.4,
                             boxstyle="round,pad=0.08",
                             facecolor=COLORS['success'], alpha=0.12,
                             edgecolor=COLORS['success'], linewidth=2)
    ax.add_patch(outer2)
    ax.text(example_x + 1.8, ey2 + 2.05, 'movie.mkv', fontsize=11,
            fontweight='bold', color=COLORS['success'], ha='center')

    draw_box(ax, example_x + 0.15, ey2 + 1.1, 1.05, 0.6, 'H.264', COLORS['primary'],
             sublabel='视频', fontsize=8)
    draw_box(ax, example_x + 1.3, ey2 + 1.1, 1.05, 0.6, 'FLAC', COLORS['secondary'],
             sublabel='音频', fontsize=8)
    draw_box(ax, example_x + 2.45, ey2 + 1.1, 1.0, 0.6, 'SRT', COLORS['pink'],
             sublabel='字幕', fontsize=8)
    draw_box(ax, example_x + 0.15, ey2 + 0.15, 3.3, 0.55, '元数据 + 章节 + 索引',
             COLORS['text_light'], fontsize=9, alpha=0.5)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-04-container-vs-codec.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-04-container-vs-codec.png')


# ============================================================
# 图2：容器文件内部结构
# ============================================================
def gen_container_structure():
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-0.5, 8)
    ax.set_title('多媒体容器文件内部结构', fontsize=16,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 外框
    outer = FancyBboxPatch((0.5, 0.2), 8.5, 7.2,
                            boxstyle="round,pad=0.1",
                            facecolor=COLORS['text'], alpha=0.04,
                            edgecolor=COLORS['text'], linewidth=2.5)
    ax.add_patch(outer)
    ax.text(4.75, 7.0, '容器文件（如 .mp4）', fontsize=14,
            fontweight='bold', color=COLORS['text'], ha='center')

    # 各部分
    sections = [
        (6.0, 0.8, '文件头 / 元数据', COLORS['text_light'],
         ['容器格式信息', '流的数量和类型', '时长、码率等全局信息']),
        (4.6, 1.0, '视频流 #0', COLORS['primary'],
         ['编码：H.264 | 分辨率：1920×1080', '帧率：24fps | 压缩数据包序列（带时间戳）']),
        (3.2, 1.0, '音频流 #1', COLORS['danger'],
         ['编码：AAC | 采样率：48000Hz', '声道：Stereo | 压缩数据包序列（带时间戳）']),
        (1.8, 1.0, '字幕流 #2（可选）', COLORS['secondary'],
         ['格式：SRT / ASS', '字幕文本数据']),
        (0.5, 0.9, '索引 / 目录信息', COLORS['success'],
         ['支持 Seek 跳转', '数据包位置映射']),
    ]

    current_y = 6.0
    for y_start, height, title, color, items in sections:
        rect = FancyBboxPatch((1.0, y_start), 7.5, height,
                               boxstyle="round,pad=0.04",
                               facecolor=color, alpha=0.12,
                               edgecolor=color, linewidth=1.5)
        ax.add_patch(rect)
        # 左侧色条
        bar = plt.Rectangle((1.0, y_start), 0.15, height,
                              facecolor=color, alpha=0.7)
        ax.add_patch(bar)
        ax.text(1.4, y_start + height - 0.22, title, fontsize=11,
                fontweight='bold', color=color, va='top')
        for j, item in enumerate(items):
            ax.text(1.6, y_start + height - 0.5 - j * 0.3, item, fontsize=9,
                    color=COLORS['text_light'], va='top')

    # 右侧标注
    ax.text(10.0, 5.5, '每个容器文件\n可包含多个流\n（Stream）', fontsize=11,
            color=COLORS['text'], ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['primary'], alpha=0.08),
            fontweight='bold')
    ax.annotate('', xy=(8.7, 5.0), xytext=(9.3, 5.3),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=1.5))

    ax.text(10.0, 2.5, '每个流有独立的\n编码格式和参数', fontsize=11,
            color=COLORS['text'], ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['danger'], alpha=0.08),
            fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-04-container-structure.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-04-container-structure.png')


# ============================================================
# 图3：Mux / Demux 流程
# ============================================================
def gen_mux_demux():
    fig, axes = plt.subplots(2, 1, figsize=(14, 7), gridspec_kw={'height_ratios': [1, 1]})
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('封装（Mux）与解封装（Demux）', fontsize=16,
                 fontweight='bold', color=COLORS['text'], y=1.0)

    # === 上：Mux ===
    ax = axes[0]
    ax.axis('off')
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-0.5, 3.5)
    ax.set_title('封装 / 多路复用（Mux）', fontsize=13, fontweight='bold',
                 color=COLORS['text'], pad=8)

    # 输入
    draw_box(ax, 0, 2.0, 2.8, 0.8, '视频编码数据', COLORS['primary'], sublabel='H.264', fontsize=10)
    draw_box(ax, 0, 0.8, 2.8, 0.8, '音频编码数据', COLORS['danger'], sublabel='AAC', fontsize=10)

    # 箭头
    draw_arrow(ax, 2.9, 2.4, 4.2, 1.9, COLORS['primary'])
    draw_arrow(ax, 2.9, 1.2, 4.2, 1.5, COLORS['danger'])

    # Muxer
    muxer = FancyBboxPatch((4.2, 0.8), 3.0, 2.0,
                            boxstyle="round,pad=0.08",
                            facecolor=COLORS['accent'], alpha=0.85,
                            edgecolor='white', linewidth=2)
    ax.add_patch(muxer)
    ax.text(5.7, 1.8, 'Muxer', fontsize=14, fontweight='bold', color='white', ha='center')
    ax.text(5.7, 1.35, '封装器', fontsize=10, color='white', ha='center', alpha=0.85)

    # 箭头
    draw_arrow(ax, 7.3, 1.8, 8.5, 1.8, COLORS['accent'], lw=2.5)

    # 输出
    output = FancyBboxPatch((8.5, 0.8), 3.5, 2.0,
                             boxstyle="round,pad=0.08",
                             facecolor=COLORS['success'], alpha=0.15,
                             edgecolor=COLORS['success'], linewidth=2)
    ax.add_patch(output)
    ax.text(10.25, 2.3, 'output.mp4', fontsize=12, fontweight='bold',
            color=COLORS['success'], ha='center')
    # 内部小块
    draw_box(ax, 8.7, 1.0, 1.4, 0.65, 'H.264', COLORS['primary'], fontsize=8, alpha=0.6)
    draw_box(ax, 10.2, 1.0, 1.4, 0.65, 'AAC', COLORS['danger'], fontsize=8, alpha=0.6)

    # 功能说明
    ax.text(5.7, 0.3, '交错排列音视频包 | 写入文件头和索引 | 生成时间戳',
            fontsize=9, color=COLORS['text_light'], ha='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['accent'], alpha=0.08))

    # === 下：Demux ===
    ax = axes[1]
    ax.axis('off')
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-0.5, 3.5)
    ax.set_title('解封装 / 解多路复用（Demux）— 播放器第一步', fontsize=13,
                 fontweight='bold', color=COLORS['text'], pad=8)

    # 输入
    input_box = FancyBboxPatch((0, 0.8), 3.2, 2.0,
                                boxstyle="round,pad=0.08",
                                facecolor=COLORS['success'], alpha=0.15,
                                edgecolor=COLORS['success'], linewidth=2)
    ax.add_patch(input_box)
    ax.text(1.6, 2.3, 'input.mp4', fontsize=12, fontweight='bold',
            color=COLORS['success'], ha='center')
    draw_box(ax, 0.2, 1.0, 1.3, 0.65, 'H.264', COLORS['primary'], fontsize=8, alpha=0.6)
    draw_box(ax, 1.6, 1.0, 1.3, 0.65, 'AAC', COLORS['danger'], fontsize=8, alpha=0.6)

    # 箭头
    draw_arrow(ax, 3.3, 1.8, 4.5, 1.8, COLORS['success'], lw=2.5)

    # Demuxer
    demuxer = FancyBboxPatch((4.5, 0.8), 3.0, 2.0,
                              boxstyle="round,pad=0.08",
                              facecolor=COLORS['secondary'], alpha=0.85,
                              edgecolor='white', linewidth=2)
    ax.add_patch(demuxer)
    ax.text(6.0, 1.8, 'Demuxer', fontsize=14, fontweight='bold', color='white', ha='center')
    ax.text(6.0, 1.35, '解封装器', fontsize=10, color='white', ha='center', alpha=0.85)

    # 箭头（分叉）
    draw_arrow(ax, 7.6, 2.2, 8.8, 2.7, COLORS['primary'])
    draw_arrow(ax, 7.6, 1.8, 8.8, 1.6, COLORS['danger'])
    draw_arrow(ax, 7.6, 1.4, 8.8, 0.7, COLORS['text_light'])

    # 输出
    draw_box(ax, 8.8, 2.3, 3.8, 0.8, '视频数据包', COLORS['primary'],
             sublabel='AVPacket（带 PTS/DTS）', fontsize=10)
    draw_box(ax, 8.8, 1.2, 3.8, 0.8, '音频数据包', COLORS['danger'],
             sublabel='AVPacket（带 PTS/DTS）', fontsize=10)
    draw_box(ax, 8.8, 0.2, 3.8, 0.7, '字幕数据（可选）', COLORS['text_light'], fontsize=10, alpha=0.5)

    # 功能说明
    ax.text(6.0, 0.25, '读取文件头 | 按顺序读取数据包 | 标记时间戳和所属流',
            fontsize=9, color=COLORS['text_light'], ha='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['secondary'], alpha=0.08))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-04-mux-demux.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-04-mux-demux.png')


# ============================================================
# 图4：时间基（TimeBase）概念
# ============================================================
def gen_timebase():
    fig, ax = plt.subplots(figsize=(14, 5.5))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-2, 4.5)
    ax.set_title('时间基（TimeBase）— 时间戳的"刻度单位"', fontsize=16,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 尺子比喻：不同时间基 = 不同刻度的尺子
    # === 时间基 1/10 ===
    ruler_y = 3.0
    ax.text(-0.3, ruler_y + 0.3, 'TimeBase = 1/10', fontsize=11, fontweight='bold',
            color=COLORS['primary'])
    ax.text(-0.3, ruler_y - 0.05, '每个刻度 = 0.1 秒', fontsize=9, color=COLORS['text_light'])

    for i in range(11):
        x = 3 + i * 1.0
        ax.plot([x, x], [ruler_y - 0.15, ruler_y + 0.15], color=COLORS['primary'], lw=2)
        ax.text(x, ruler_y - 0.3, str(i), fontsize=8, ha='center', color=COLORS['primary'])
    ax.plot([3, 13], [ruler_y, ruler_y], color=COLORS['primary'], lw=2)
    # PTS=5 标注
    ax.plot(8, ruler_y + 0.25, 'v', color=COLORS['danger'], markersize=12)
    ax.text(8, ruler_y + 0.55, 'PTS = 5', fontsize=10, ha='center',
            color=COLORS['danger'], fontweight='bold')
    ax.text(8, ruler_y + 0.95, '实际时间 = 5 × 1/10 = 0.5 秒', fontsize=9,
            ha='center', color=COLORS['text_light'])

    # === 时间基 1/90000 ===
    ruler_y2 = 1.2
    ax.text(-0.3, ruler_y2 + 0.3, 'TimeBase = 1/90000', fontsize=11, fontweight='bold',
            color=COLORS['secondary'])
    ax.text(-0.3, ruler_y2 - 0.05, '每个刻度 = 1/90000 秒', fontsize=9, color=COLORS['text_light'])

    # 画更密的刻度
    for i in range(51):
        x = 3 + i * 0.2
        h = 0.15 if i % 10 == 0 else 0.08
        ax.plot([x, x], [ruler_y2 - h, ruler_y2 + h], color=COLORS['secondary'],
                lw=1.5 if i % 10 == 0 else 0.8)
        if i % 10 == 0:
            val = i * 9000
            ax.text(x, ruler_y2 - 0.3, f'{val}', fontsize=7, ha='center', color=COLORS['secondary'])
    ax.plot([3, 13], [ruler_y2, ruler_y2], color=COLORS['secondary'], lw=2)
    # PTS=450000 标注
    ax.plot(8, ruler_y2 + 0.25, 'v', color=COLORS['danger'], markersize=12)
    ax.text(8, ruler_y2 + 0.55, 'PTS = 450000', fontsize=10, ha='center',
            color=COLORS['danger'], fontweight='bold')
    ax.text(8, ruler_y2 + 0.95, '实际时间 = 450000 × 1/90000 = 5.0 秒', fontsize=9,
            ha='center', color=COLORS['text_light'])

    # 底部说明
    ax.text(7, -0.7, '不同的流可能使用不同的时间基', fontsize=12,
            ha='center', color=COLORS['text'], fontweight='bold')

    # 示例框
    examples = [
        ('视频流', '1/90000', COLORS['primary']),
        ('音频流', '1/48000', COLORS['danger']),
        ('FFmpeg 内部', '1/1000000 (微秒)', COLORS['secondary']),
    ]
    for i, (name, tb, color) in enumerate(examples):
        bx = 2.0 + i * 3.8
        rect = FancyBboxPatch((bx, -1.6), 3.4, 0.65,
                               boxstyle="round,pad=0.04",
                               facecolor=color, alpha=0.1,
                               edgecolor=color, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(bx + 1.7, -1.28, f'{name}: TimeBase = {tb}',
                fontsize=9, ha='center', color=color, fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-04-timebase.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-04-timebase.png')


# ============================================================
# 图5：MP4 Box 结构
# ============================================================
def gen_mp4_structure():
    fig, ax = plt.subplots(figsize=(12, 9.5))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-3, 8.5)
    ax.set_title('MP4 文件结构（Box / Atom 嵌套）', fontsize=16,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 树状结构
    indent_w = 0.8
    box_h = 0.5
    gap = 0.12

    items = [
        (0, 'ftyp',  '文件类型标识',           COLORS['text_light']),
        (0, 'moov',  '元数据和索引（最关键）',  COLORS['accent']),
        (1, 'mvhd',  '全局头（时长、时间基等）', COLORS['accent']),
        (1, 'trak',  '视频轨道',               COLORS['primary']),
        (2, 'tkhd',  '轨道头（宽高、时长）',    COLORS['primary']),
        (2, 'mdia',  '媒体信息',               COLORS['primary']),
        (3, 'mdhd', '媒体头（时间基）',         COLORS['primary']),
        (3, 'hdlr', '处理器类型（vide）',       COLORS['primary']),
        (3, 'minf', '媒体详细信息',             COLORS['primary']),
        (4, 'stbl', '采样表（关键！）',          COLORS['primary']),
        (1, 'trak',  '音频轨道',               COLORS['danger']),
        (2, 'tkhd',  '轨道头',                 COLORS['danger']),
        (2, 'mdia',  '媒体信息',               COLORS['danger']),
        (3, 'mdhd', '媒体头（时间基）',         COLORS['danger']),
        (3, 'hdlr', '处理器类型（soun）',       COLORS['danger']),
        (0, 'mdat',  '实际的音视频压缩数据',    COLORS['success']),
    ]

    y = 7.8
    for depth, name, desc, color in items:
        x = 0.5 + depth * indent_w
        w = 8.5 - depth * indent_w

        # Box 背景
        alpha = 0.65 - depth * 0.1
        rect = FancyBboxPatch((x, y), w, box_h,
                               boxstyle="round,pad=0.03",
                               facecolor=color, alpha=max(alpha, 0.15),
                               edgecolor='white', linewidth=1.5)
        ax.add_patch(rect)

        # 名称（加粗等宽）
        ax.text(x + 0.15, y + box_h / 2, name, fontsize=10, fontweight='bold',
                color='white', va='center', family='monospace')

        # 描述
        ax.text(x + 1.2 + depth * 0.1, y + box_h / 2, desc, fontsize=9,
                color='white' if alpha > 0.3 else color, va='center', alpha=0.9)

        # 层级缩进线
        if depth > 0:
            line_x = x - 0.15
            ax.plot([line_x, line_x, x], [y + box_h, y + box_h / 2, y + box_h / 2],
                    color=color, lw=1, alpha=0.4)

        y -= (box_h + gap)

    # 右侧注解
    note_x = 9.5
    notes = [
        (6.5, 'moov 在文件尾部 →\n网络播放需先下载完\n才能开始播放', COLORS['accent']),
        (4.5, 'faststart 将 moov\n移到文件头部 →\n支持边下边播', COLORS['success']),
    ]
    for ny, text, color in notes:
        ax.text(note_x + 0.8, ny, text, fontsize=9, color=color, fontweight='bold',
                va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.08))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-04-mp4-structure.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-04-mp4-structure.png')


# ============================================================
# 主函数
# ============================================================
if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print('开始生成第 4 章配图...\n')

    gen_container_vs_codec()
    gen_container_structure()
    gen_mux_demux()
    gen_timebase()
    gen_mp4_structure()

    print('\n全部完成！')
