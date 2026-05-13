#!/usr/bin/env python3
"""
为 05-FFmpeg开发环境搭建.md 生成配图
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib
import os

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


def draw_box(ax, x, y, w, h, label, color, sublabel=None, alpha=0.85, fontsize=11):
    rect = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.06",
                           facecolor=color, edgecolor='white',
                           linewidth=2.5, alpha=alpha)
    ax.add_patch(rect)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 + 0.15, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white')
        ax.text(x + w / 2, y + h / 2 - 0.2, sublabel, ha='center', va='center',
                fontsize=fontsize - 2, color='white', alpha=0.85)
    else:
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white')


def draw_arrow(ax, x1, y1, x2, y2, color=None, lw=2):
    if color is None:
        color = COLORS['text_light']
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                connectionstyle='arc3,rad=0'))


def draw_data_label(ax, x, y, text, color):
    ax.text(x, y, text, ha='center', va='center', fontsize=9,
            color=color, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.25', facecolor=color, alpha=0.1,
                      edgecolor=color, linewidth=1))


# ============================================================
# 图1：FFmpeg 核心库在播放器中的协作流程
# ============================================================
def gen_ffmpeg_pipeline():
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-1, 15)
    ax.set_ylim(-1, 11)
    ax.set_title('FFmpeg 核心库在播放器中的协作流程', fontsize=16,
                 fontweight='bold', color=COLORS['text'], pad=15)

    cx = 7  # center x

    # === 输入文件 ===
    draw_box(ax, cx - 1.8, 9.5, 3.6, 0.9, '输入文件（如 .mp4）', COLORS['text_light'],
             fontsize=11)

    draw_arrow(ax, cx, 9.5, cx, 8.9, COLORS['text_light'], lw=2)

    # === libavformat ===
    draw_box(ax, cx - 2.0, 7.8, 4.0, 1.0, 'libavformat', COLORS['accent'],
             sublabel='解封装（Demux）', fontsize=12)

    # 分叉箭头
    draw_arrow(ax, cx - 0.5, 7.8, cx - 3.0, 7.1, COLORS['primary'], lw=2)
    draw_arrow(ax, cx + 0.5, 7.8, cx + 3.0, 7.1, COLORS['danger'], lw=2)

    # 数据标签
    draw_data_label(ax, cx - 2.5, 7.35, 'AVPacket（视频压缩包）', COLORS['primary'])
    draw_data_label(ax, cx + 2.5, 7.35, 'AVPacket（音频压缩包）', COLORS['danger'])

    # === 视频路径（左侧） ===
    vx = cx - 3.5  # 视频路径中心

    # libavcodec 视频
    draw_box(ax, vx - 2.0, 5.5, 4.0, 1.0, 'libavcodec', COLORS['primary'],
             sublabel='视频解码', fontsize=12)

    draw_arrow(ax, vx, 5.5, vx, 4.9, COLORS['primary'], lw=2)
    draw_data_label(ax, vx, 4.65, 'AVFrame（YUV 原始图像）', COLORS['primary'])

    # libswscale
    draw_box(ax, vx - 2.0, 3.2, 4.0, 1.0, 'libswscale', COLORS['cyan'],
             sublabel='图像缩放 / 像素格式转换', fontsize=12)

    draw_arrow(ax, vx, 3.2, vx, 2.6, COLORS['cyan'], lw=2)
    draw_data_label(ax, vx, 2.35, 'RGB / YUV 显示数据', COLORS['cyan'])

    # SDL2 视频
    draw_box(ax, vx - 2.0, 0.9, 4.0, 1.0, 'SDL2 视频渲染', COLORS['text_light'],
             sublabel='窗口 + 纹理显示', fontsize=12, alpha=0.6)

    draw_arrow(ax, vx, 0.9, vx, 0.3, COLORS['text_light'], lw=2)
    ax.text(vx, 0.0, '屏幕画面', fontsize=10, ha='center', color=COLORS['text_light'],
            fontweight='bold')

    # === 音频路径（右侧） ===
    ax_r = cx + 3.5  # 音频路径中心

    # libavcodec 音频
    draw_box(ax, ax_r - 2.0, 5.5, 4.0, 1.0, 'libavcodec', COLORS['danger'],
             sublabel='音频解码', fontsize=12)

    draw_arrow(ax, ax_r, 5.5, ax_r, 4.9, COLORS['danger'], lw=2)
    draw_data_label(ax, ax_r, 4.65, 'AVFrame（PCM 原始音频）', COLORS['danger'])

    # libswresample
    draw_box(ax, ax_r - 2.0, 3.2, 4.0, 1.0, 'libswresample', COLORS['secondary'],
             sublabel='音频重采样 / 格式转换', fontsize=12)

    draw_arrow(ax, ax_r, 3.2, ax_r, 2.6, COLORS['secondary'], lw=2)
    draw_data_label(ax, ax_r, 2.35, 'PCM 播放数据', COLORS['secondary'])

    # SDL2 音频
    draw_box(ax, ax_r - 2.0, 0.9, 4.0, 1.0, 'SDL2 音频播放', COLORS['text_light'],
             sublabel='音频回调输出', fontsize=12, alpha=0.6)

    draw_arrow(ax, ax_r, 0.9, ax_r, 0.3, COLORS['text_light'], lw=2)
    ax.text(ax_r, 0.0, '扬声器声音', fontsize=10, ha='center', color=COLORS['text_light'],
            fontweight='bold')

    # === libavutil 横跨底部标注 ===
    util_rect = FancyBboxPatch((cx - 6.5, -0.8), 13.0, 0.55,
                                boxstyle="round,pad=0.04",
                                facecolor=COLORS['success'], alpha=0.12,
                                edgecolor=COLORS['success'], linewidth=1.5,
                                linestyle='--')
    ax.add_patch(util_rect)
    ax.text(cx, -0.53, 'libavutil — 贯穿所有环节的工具库（内存管理、数据结构、数学运算、日志等）',
            ha='center', fontsize=10, color=COLORS['success'], fontweight='bold')

    # === 左右侧标签 ===
    # 视频路径标签
    vid_bg = FancyBboxPatch((vx - 2.3, 0.6), 4.6, 8.3,
                             boxstyle="round,pad=0.1",
                             facecolor=COLORS['primary'], alpha=0.03,
                             edgecolor=COLORS['primary'], linewidth=1,
                             linestyle=':')
    ax.add_patch(vid_bg)
    ax.text(vx, 9.15, '视频处理流水线', fontsize=10, ha='center',
            color=COLORS['primary'], fontweight='bold', fontstyle='italic')

    # 音频路径标签
    aud_bg = FancyBboxPatch((ax_r - 2.3, 0.6), 4.6, 8.3,
                             boxstyle="round,pad=0.1",
                             facecolor=COLORS['danger'], alpha=0.03,
                             edgecolor=COLORS['danger'], linewidth=1,
                             linestyle=':')
    ax.add_patch(aud_bg)
    ax.text(ax_r, 9.15, '音频处理流水线', fontsize=10, ha='center',
            color=COLORS['danger'], fontweight='bold', fontstyle='italic')

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-05-ffmpeg-pipeline.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-05-ffmpeg-pipeline.png')


# ============================================================
# 图2：FFmpeg 六大核心库概览
# ============================================================
def gen_ffmpeg_libs():
    fig, ax = plt.subplots(figsize=(14, 5.5))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 14.5)
    ax.set_ylim(-0.5, 5)
    ax.set_title('FFmpeg 六大核心库', fontsize=16,
                 fontweight='bold', color=COLORS['text'], pad=15)

    libs = [
        ('libavformat', '封装 / 解封装', 'Mux & Demux\n读写容器文件', COLORS['accent']),
        ('libavcodec',  '编码 / 解码',   'Encode & Decode\n压缩与解压缩', COLORS['primary']),
        ('libavutil',   '通用工具',      'Utility\n数据结构、内存、日志', COLORS['success']),
        ('libswscale',  '图像处理',      'Scale & Convert\n缩放、像素格式转换', COLORS['cyan']),
        ('libswresample','音频处理',     'Resample\n重采样、格式转换', COLORS['secondary']),
        ('libavfilter', '滤镜系统',      'Filter\n音视频效果处理', COLORS['text_light']),
    ]

    card_w = 2.0
    card_h = 3.5
    gap = 0.3
    start_x = (14.5 - (len(libs) * (card_w + gap) - gap)) / 2

    for i, (name, role, desc, color) in enumerate(libs):
        x = start_x + i * (card_w + gap)
        y = 0.5

        # 卡片背景
        card = FancyBboxPatch((x, y), card_w, card_h,
                               boxstyle="round,pad=0.06",
                               facecolor=color, alpha=0.08,
                               edgecolor=color, linewidth=2)
        ax.add_patch(card)

        # 顶部色条
        bar = FancyBboxPatch((x, y + card_h - 0.9), card_w, 0.9,
                              boxstyle="round,pad=0.06",
                              facecolor=color, alpha=0.8,
                              edgecolor='white', linewidth=2)
        ax.add_patch(bar)

        # 库名
        ax.text(x + card_w / 2, y + card_h - 0.45, name, ha='center', va='center',
                fontsize=9.5, fontweight='bold', color='white')

        # 角色
        ax.text(x + card_w / 2, y + card_h - 1.25, role, ha='center', va='center',
                fontsize=10, fontweight='bold', color=color)

        # 描述
        ax.text(x + card_w / 2, y + card_h - 2.3, desc, ha='center', va='center',
                fontsize=8.5, color=COLORS['text_light'], linespacing=1.4)

        # 是否本教程使用
        if i < 5:
            ax.text(x + card_w / 2, y + 0.25, '本教程使用', fontsize=8,
                    ha='center', color=COLORS['success'], fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor=COLORS['success'],
                              alpha=0.1, edgecolor=COLORS['success'], linewidth=0.8))
        else:
            ax.text(x + card_w / 2, y + 0.25, '本教程不涉及', fontsize=8,
                    ha='center', color=COLORS['text_light'],
                    bbox=dict(boxstyle='round,pad=0.15', facecolor=COLORS['grid'],
                              alpha=0.5, edgecolor=COLORS['grid'], linewidth=0.8))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-05-ffmpeg-libs.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-05-ffmpeg-libs.png')


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print('开始生成第 5 章配图...\n')
    gen_ffmpeg_pipeline()
    gen_ffmpeg_libs()
    print('\n全部完成！')
