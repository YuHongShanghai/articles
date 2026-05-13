#!/usr/bin/env python3
"""
为 02-视频基础知识.md 生成配图
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib
import os

# ============================================================
# 全局样式设置（与音频章节统一）
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


def setup_ax(ax, title=None):
    ax.set_facecolor(COLORS['bg'])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    ax.tick_params(colors=COLORS['text_light'], labelsize=10)
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', color=COLORS['text'], pad=12)


# ============================================================
# 图1：视频帧序列 + 帧率概念
# ============================================================
def gen_video_frames():
    fig, ax = plt.subplots(figsize=(14, 4.5))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-2, 3.5)
    ax.set_title('视频的本质：以固定帧率播放的图像序列', fontsize=15,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 画一排"帧"
    frame_colors = [COLORS['primary'], COLORS['secondary'], COLORS['success'],
                    COLORS['accent'], COLORS['danger'], COLORS['pink'],
                    COLORS['cyan'], COLORS['primary']]
    n_frames = 8
    frame_w, frame_h = 1.3, 1.6
    gap = 0.35

    for i in range(n_frames):
        x = i * (frame_w + gap)
        # 帧矩形
        rect = FancyBboxPatch((x, 0), frame_w, frame_h,
                               boxstyle="round,pad=0.05",
                               facecolor=frame_colors[i], edgecolor='white',
                               linewidth=2, alpha=0.2)
        ax.add_patch(rect)
        # 内部"画面"区域
        inner = FancyBboxPatch((x + 0.1, 0.15), frame_w - 0.2, frame_h - 0.3,
                                boxstyle="round,pad=0.02",
                                facecolor=frame_colors[i], edgecolor=frame_colors[i],
                                linewidth=1.5, alpha=0.5)
        ax.add_patch(inner)
        # 帧编号
        ax.text(x + frame_w / 2, frame_h / 2 + 0.05, f'帧 {i+1}', ha='center', va='center',
                fontsize=11, fontweight='bold', color=COLORS['white'])
        # 箭头
        if i < n_frames - 1:
            ax.annotate('', xy=(x + frame_w + gap - 0.08, frame_h / 2),
                        xytext=(x + frame_w + 0.08, frame_h / 2),
                        arrowprops=dict(arrowstyle='->', color=COLORS['text_light'],
                                        lw=1.5, connectionstyle='arc3'))

    # 时间轴
    total_w = n_frames * (frame_w + gap) - gap
    ax.annotate('', xy=(total_w + 0.3, -0.5), xytext=(-0.3, -0.5),
                arrowprops=dict(arrowstyle='->', color=COLORS['text'], lw=2))
    ax.text(total_w / 2, -0.85, '时间 →', ha='center', fontsize=12, color=COLORS['text_light'])

    # 帧率标注
    # 标注前3帧为"1秒内"（以24fps举例不合适，这里标注概念）
    brace_y = 2.0
    ax.annotate('', xy=(0, brace_y), xytext=(0 + (frame_w + gap) * 3 - gap + frame_w, brace_y),
                arrowprops=dict(arrowstyle='<->', color=COLORS['primary'], lw=1.5))
    ax.text((frame_w + gap) * 1.5 + frame_w / 2, brace_y + 0.25,
            '帧率 = 每秒显示的帧数（FPS）', ha='center', fontsize=11,
            color=COLORS['primary'], fontweight='bold')
    ax.text((frame_w + gap) * 1.5 + frame_w / 2, brace_y + 0.7,
            '24 FPS = 每秒 24 帧 → 电影    |    60 FPS = 每秒 60 帧 → 游戏', ha='center',
            fontsize=10, color=COLORS['text_light'])

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-02-video-frames.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-02-video-frames.png')


# ============================================================
# 图2：分辨率对比
# ============================================================
def gen_resolution():
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-50, 4100)
    ax.set_ylim(-200, 2500)
    ax.set_title('常见视频分辨率对比', fontsize=15, fontweight='bold',
                 color=COLORS['text'], pad=15)

    resolutions = [
        ('8K\n7680×4320', 3840, 2160, COLORS['text_light'], 0.12),
        ('4K (UHD)\n3840×2160', 3840, 2160, COLORS['secondary'], 0.18),
        ('1080p (Full HD)\n1920×1080', 1920, 1080, COLORS['primary'], 0.25),
        ('720p (HD)\n1280×720', 1280, 720, COLORS['success'], 0.3),
        ('480p (SD)\n854×480', 854, 480, COLORS['accent'], 0.35),
    ]

    # 以 4K 为最大参考，按比例缩放显示
    # 8K 太大了，用虚线框表示
    base_x, base_y = 0, 0

    # 8K 虚线框
    rect_8k = plt.Rectangle((base_x, base_y), 3840, 2160,
                              linewidth=1.5, linestyle='--',
                              edgecolor=COLORS['text_light'], facecolor='none', alpha=0.4)
    ax.add_patch(rect_8k)
    ax.text(3840 / 2, 2160 + 50, '8K (7680×4320) — 等比缩放后仍为 2× 此框',
            ha='center', va='bottom', fontsize=9, color=COLORS['text_light'], fontstyle='italic')

    # 4K
    rect_4k = FancyBboxPatch((base_x, base_y), 3840, 2160,
                              boxstyle="round,pad=3",
                              facecolor=COLORS['secondary'], alpha=0.15,
                              edgecolor=COLORS['secondary'], linewidth=2)
    ax.add_patch(rect_4k)
    ax.text(3840 - 10, 2160 - 30, '4K (3840×2160)', ha='right', va='top',
            fontsize=11, color=COLORS['secondary'], fontweight='bold')

    # 1080p
    rect_fhd = FancyBboxPatch((base_x, base_y), 1920, 1080,
                               boxstyle="round,pad=3",
                               facecolor=COLORS['primary'], alpha=0.2,
                               edgecolor=COLORS['primary'], linewidth=2)
    ax.add_patch(rect_fhd)
    ax.text(1920 - 10, 1080 - 25, '1080p (1920×1080)', ha='right', va='top',
            fontsize=11, color=COLORS['primary'], fontweight='bold')

    # 720p
    rect_hd = FancyBboxPatch((base_x, base_y), 1280, 720,
                              boxstyle="round,pad=3",
                              facecolor=COLORS['success'], alpha=0.25,
                              edgecolor=COLORS['success'], linewidth=2)
    ax.add_patch(rect_hd)
    ax.text(1280 - 10, 720 - 25, '720p (1280×720)', ha='right', va='top',
            fontsize=10, color=COLORS['success'], fontweight='bold')

    # 480p
    rect_sd = FancyBboxPatch((base_x, base_y), 854, 480,
                              boxstyle="round,pad=3",
                              facecolor=COLORS['accent'], alpha=0.35,
                              edgecolor=COLORS['accent'], linewidth=2)
    ax.add_patch(rect_sd)
    ax.text(854 / 2, 480 / 2, '480p\n(854×480)', ha='center', va='center',
            fontsize=10, color=COLORS['accent'], fontweight='bold')

    ax.set_aspect('equal')
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-02-resolution.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-02-resolution.png')


# ============================================================
# 图3：RGB 与 YUV 色彩空间
# ============================================================
def gen_rgb_yuv():
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('RGB 与 YUV 色彩空间', fontsize=16, fontweight='bold',
                 color=COLORS['text'], y=1.0)

    # --- RGB 三原色叠加 ---
    ax = axes[0]
    ax.axis('off')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.2, 1.5)
    ax.set_aspect('equal')
    ax.set_title('RGB 色彩空间', fontsize=13, fontweight='bold', color=COLORS['text'], pad=10)

    # 三个重叠的圆
    r_circle = plt.Circle((-0.35, 0.25), 0.7, facecolor='#FF0000', alpha=0.35, edgecolor='none')
    g_circle = plt.Circle((0.35, 0.25), 0.7, facecolor='#00FF00', alpha=0.35, edgecolor='none')
    b_circle = plt.Circle((0, -0.35), 0.7, facecolor='#0000FF', alpha=0.35, edgecolor='none')
    ax.add_patch(r_circle)
    ax.add_patch(g_circle)
    ax.add_patch(b_circle)

    ax.text(-0.85, 0.65, 'R', fontsize=18, fontweight='bold', color='#CC0000', ha='center')
    ax.text(0.85, 0.65, 'G', fontsize=18, fontweight='bold', color='#008800', ha='center')
    ax.text(0, -0.95, 'B', fontsize=18, fontweight='bold', color='#0000CC', ha='center')
    ax.text(0, 0.1, 'W', fontsize=12, fontweight='bold', color='#666666', ha='center')

    ax.text(0, -1.15, '每像素 3 字节（RGB24）\n适合显示，不适合压缩',
            ha='center', fontsize=9, color=COLORS['text_light'])

    # --- YUV 分量展示 ---
    ax = axes[1]
    ax.axis('off')
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(-1.3, 1.5)
    ax.set_aspect('equal')
    ax.set_title('YUV 色彩空间', fontsize=13, fontweight='bold', color=COLORS['text'], pad=10)

    # Y 分量 - 灰度
    y_rect = FancyBboxPatch((0, -0.1), 0.8, 0.8,
                             boxstyle="round,pad=0.03",
                             facecolor='#888888', edgecolor=COLORS['text_light'], linewidth=2)
    ax.add_patch(y_rect)
    # 渐变效果模拟：画多个小条
    for j in range(8):
        gray = int(40 + j * 25)
        gray = min(gray, 255)
        c = f'#{gray:02x}{gray:02x}{gray:02x}'
        bar = plt.Rectangle((0.04 + j * 0.09, 0.0), 0.09, 0.6,
                              facecolor=c, edgecolor='none')
        ax.add_patch(bar)
    ax.text(0.4, 1.0, 'Y（亮度）', ha='center', va='bottom', fontsize=11,
            fontweight='bold', color=COLORS['text'])
    ax.text(0.4, -0.3, '明暗信息', ha='center', fontsize=9, color=COLORS['text_light'])

    # U 分量 - 蓝色色度
    u_rect = FancyBboxPatch((1.2, -0.1), 0.8, 0.8,
                             boxstyle="round,pad=0.03",
                             facecolor='#4488CC', edgecolor=COLORS['primary'], linewidth=2)
    ax.add_patch(u_rect)
    for j in range(8):
        b_val = int(80 + j * 20)
        b_val = min(b_val, 255)
        c = f'#{80:02x}{80:02x}{b_val:02x}'
        bar = plt.Rectangle((1.24 + j * 0.09, 0.0), 0.09, 0.6,
                              facecolor=c, edgecolor='none')
        ax.add_patch(bar)
    ax.text(1.6, 1.0, 'U / Cb', ha='center', va='bottom', fontsize=11,
            fontweight='bold', color=COLORS['primary'])
    ax.text(1.6, -0.3, '蓝色色度', ha='center', fontsize=9, color=COLORS['text_light'])

    # V 分量 - 红色色度
    v_rect = FancyBboxPatch((2.4, -0.1), 0.8, 0.8,
                             boxstyle="round,pad=0.03",
                             facecolor='#CC6644', edgecolor=COLORS['danger'], linewidth=2)
    ax.add_patch(v_rect)
    for j in range(8):
        r_val = int(80 + j * 20)
        r_val = min(r_val, 255)
        c = f'#{r_val:02x}{80:02x}{80:02x}'
        bar = plt.Rectangle((2.44 + j * 0.09, 0.0), 0.09, 0.6,
                              facecolor=c, edgecolor='none')
        ax.add_patch(bar)
    ax.text(2.8, 1.0, 'V / Cr', ha='center', va='bottom', fontsize=11,
            fontweight='bold', color=COLORS['danger'])
    ax.text(2.8, -0.3, '红色色度', ha='center', fontsize=9, color=COLORS['text_light'])

    # 加号
    ax.text(1.0, 0.35, '+', fontsize=18, fontweight='bold', color=COLORS['text_light'],
            ha='center', va='center')
    ax.text(2.2, 0.35, '+', fontsize=18, fontweight='bold', color=COLORS['text_light'],
            ha='center', va='center')

    ax.text(1.6, -0.8, '人眼对 Y（亮度）敏感，对 U/V（色度）不敏感\n→ 可以对 U/V 降采样来节省数据量',
            ha='center', fontsize=9, color=COLORS['text_light'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['success'], alpha=0.1))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-02-rgb-yuv.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-02-rgb-yuv.png')


# ============================================================
# 图4：YUV 色度子采样
# ============================================================
def gen_yuv_subsampling():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('YUV 色度子采样格式对比', fontsize=16, fontweight='bold',
                 color=COLORS['text'], y=1.0)

    grid_size = 4  # 4x4 pixel grid

    def draw_grid(ax, title, y_pattern, uv_pattern, data_pct):
        ax.set_xlim(-0.5, grid_size + 2.5)
        ax.set_ylim(-1.5, grid_size + 0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=13, fontweight='bold', color=COLORS['text'], pad=10)

        # 画 Y 采样点
        for row in range(grid_size):
            for col in range(grid_size):
                if y_pattern[row][col]:
                    circle = plt.Circle((col, grid_size - 1 - row), 0.3,
                                         facecolor=COLORS['text'], alpha=0.7, edgecolor='white', linewidth=1)
                    ax.add_patch(circle)
                    ax.text(col, grid_size - 1 - row, 'Y', ha='center', va='center',
                            fontsize=7, color='white', fontweight='bold')
                # 网格
                rect = plt.Rectangle((col - 0.45, grid_size - 1 - row - 0.45), 0.9, 0.9,
                                      linewidth=0.5, edgecolor=COLORS['grid'], facecolor='none')
                ax.add_patch(rect)

        # 画 UV 采样点
        for row in range(grid_size):
            for col in range(grid_size):
                if uv_pattern[row][col]:
                    circle = plt.Circle((col + 0.15, grid_size - 1 - row - 0.15), 0.2,
                                         facecolor=COLORS['primary'], alpha=0.8,
                                         edgecolor='white', linewidth=0.8)
                    ax.add_patch(circle)

        # 图例
        ax.plot([], [], 'o', color=COLORS['text'], markersize=8, label='Y（亮度）')
        ax.plot([], [], 'o', color=COLORS['primary'], markersize=6, label='UV（色度）')
        ax.legend(fontsize=8, loc='upper right', framealpha=0.9,
                  bbox_to_anchor=(1.6, 1.0))

        # 数据量标注
        ax.text(grid_size / 2 - 0.5, -1.0, f'数据量：RGB 的 {data_pct}%',
                ha='center', fontsize=10, color=COLORS['primary'], fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['primary'], alpha=0.08))

    # 所有 Y 都有
    all_y = [[1]*4 for _ in range(4)]

    # 4:4:4 - 所有 UV 都有
    uv_444 = [[1]*4 for _ in range(4)]
    draw_grid(axes[0], '4:4:4', all_y, uv_444, 100)

    # 4:2:2 - 水平每2个像素取1个UV
    uv_422 = [[1, 0, 1, 0] for _ in range(4)]
    draw_grid(axes[1], '4:2:2', all_y, uv_422, 67)

    # 4:2:0 - 水平和垂直各半
    uv_420 = [[1, 0, 1, 0], [0, 0, 0, 0], [1, 0, 1, 0], [0, 0, 0, 0]]
    draw_grid(axes[2], '4:2:0（最常用）', all_y, uv_420, 50)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-02-yuv-subsampling.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-02-yuv-subsampling.png')


# ============================================================
# 图5：YUV420P 内存布局
# ============================================================
def gen_yuv420p_layout():
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-1, 17)
    ax.set_ylim(-2, 7)
    ax.set_title('YUV420P 内存布局（以 4×4 图像为例）', fontsize=15,
                 fontweight='bold', color=COLORS['text'], pad=15)

    cell = 0.9

    # Y 平面 (4×4)
    y_x0, y_y0 = 0, 2.5
    ax.text(y_x0 + 2 * cell, y_y0 + 4 * cell + 0.3, 'Y 平面（4×4 = 16 字节）',
            ha='center', fontsize=12, fontweight='bold', color=COLORS['text'])
    for r in range(4):
        for c in range(4):
            rect = FancyBboxPatch((y_x0 + c * cell, y_y0 + (3 - r) * cell), cell - 0.05, cell - 0.05,
                                   boxstyle="round,pad=0.02",
                                   facecolor=COLORS['text'], alpha=0.65,
                                   edgecolor='white', linewidth=1.5)
            ax.add_patch(rect)
            ax.text(y_x0 + c * cell + cell / 2, y_y0 + (3 - r) * cell + cell / 2,
                    f'Y{r}{c}', ha='center', va='center', fontsize=8,
                    color='white', fontweight='bold')

    # U 平面 (2×2)
    u_x0, u_y0 = 5.5, 3.3
    ax.text(u_x0 + cell, u_y0 + 2 * cell + 0.3, 'U 平面（2×2 = 4 字节）',
            ha='center', fontsize=12, fontweight='bold', color=COLORS['primary'])
    for r in range(2):
        for c in range(2):
            rect = FancyBboxPatch((u_x0 + c * cell, u_y0 + (1 - r) * cell), cell - 0.05, cell - 0.05,
                                   boxstyle="round,pad=0.02",
                                   facecolor=COLORS['primary'], alpha=0.7,
                                   edgecolor='white', linewidth=1.5)
            ax.add_patch(rect)
            ax.text(u_x0 + c * cell + cell / 2, u_y0 + (1 - r) * cell + cell / 2,
                    f'U{r}{c}', ha='center', va='center', fontsize=8,
                    color='white', fontweight='bold')

    # V 平面 (2×2)
    v_x0, v_y0 = 8.5, 3.3
    ax.text(v_x0 + cell, v_y0 + 2 * cell + 0.3, 'V 平面（2×2 = 4 字节）',
            ha='center', fontsize=12, fontweight='bold', color=COLORS['danger'])
    for r in range(2):
        for c in range(2):
            rect = FancyBboxPatch((v_x0 + c * cell, v_y0 + (1 - r) * cell), cell - 0.05, cell - 0.05,
                                   boxstyle="round,pad=0.02",
                                   facecolor=COLORS['danger'], alpha=0.7,
                                   edgecolor='white', linewidth=1.5)
            ax.add_patch(rect)
            ax.text(v_x0 + c * cell + cell / 2, v_y0 + (1 - r) * cell + cell / 2,
                    f'V{r}{c}', ha='center', va='center', fontsize=8,
                    color='white', fontweight='bold')

    # 映射关系说明
    # Y00,Y01,Y10,Y11 → U00, V00
    ax.annotate('', xy=(5.5, 4.5), xytext=(4 * cell + 0.2, 5.2),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=1.5,
                                connectionstyle='arc3,rad=-0.2'))
    ax.text(4.7, 5.7, '每 2×2 个 Y\n共享一组 UV',
            ha='center', fontsize=9, color=COLORS['accent'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['accent'], alpha=0.1))

    # 内存布局线性展示
    mem_y = 0.5
    ax.text(-0.5, mem_y + 0.4, '实际内存排列:', fontsize=11, fontweight='bold',
            color=COLORS['text_light'])
    # Y 部分
    for i in range(16):
        x = i * 0.65
        rect = FancyBboxPatch((x, mem_y - 0.3), 0.6, 0.6,
                               boxstyle="round,pad=0.01",
                               facecolor=COLORS['text'], alpha=0.5,
                               edgecolor='white', linewidth=1)
        ax.add_patch(rect)
    ax.text(16 * 0.65 / 2, mem_y - 0.7, 'Y (16 字节)', ha='center',
            fontsize=9, color=COLORS['text'], fontweight='bold')

    # U 部分
    u_start = 16 * 0.65 + 0.2
    for i in range(4):
        x = u_start + i * 0.65
        rect = FancyBboxPatch((x, mem_y - 0.3), 0.6, 0.6,
                               boxstyle="round,pad=0.01",
                               facecolor=COLORS['primary'], alpha=0.5,
                               edgecolor='white', linewidth=1)
        ax.add_patch(rect)
    ax.text(u_start + 2 * 0.65, mem_y - 0.7, 'U (4)', ha='center',
            fontsize=9, color=COLORS['primary'], fontweight='bold')

    # V 部分
    v_start = u_start + 4 * 0.65 + 0.2
    for i in range(4):
        x = v_start + i * 0.65
        rect = FancyBboxPatch((x, mem_y - 0.3), 0.6, 0.6,
                               boxstyle="round,pad=0.01",
                               facecolor=COLORS['danger'], alpha=0.5,
                               edgecolor='white', linewidth=1)
        ax.add_patch(rect)
    ax.text(v_start + 2 * 0.65, mem_y - 0.7, 'V (4)', ha='center',
            fontsize=9, color=COLORS['danger'], fontweight='bold')

    # 总大小标注
    ax.text(v_start + 4 * 0.65 + 0.5, mem_y, '= 24 字节\n= W×H×1.5',
            fontsize=10, color=COLORS['success'], fontweight='bold', va='center')

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-02-yuv420p-layout.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-02-yuv420p-layout.png')


# ============================================================
# 图6：I/P/B 帧 + GOP
# ============================================================
def gen_ipb_gop():
    fig, axes = plt.subplots(2, 1, figsize=(15, 7), gridspec_kw={'height_ratios': [1.2, 1]})
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('视频帧类型与 GOP 结构', fontsize=16, fontweight='bold',
                 color=COLORS['text'], y=1.0)

    # === 上半部分：I/P/B 帧类型 ===
    ax = axes[0]
    ax.axis('off')
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-2, 2.5)
    ax.set_title('I 帧、P 帧、B 帧', fontsize=13, fontweight='bold', color=COLORS['text'], pad=8)

    frames = [
        ('I', COLORS['danger'], 1.4),
        ('B', COLORS['success'], 0.7),
        ('B', COLORS['success'], 0.7),
        ('P', COLORS['primary'], 1.0),
        ('B', COLORS['success'], 0.7),
        ('B', COLORS['success'], 0.7),
        ('P', COLORS['primary'], 1.0),
        ('B', COLORS['success'], 0.7),
        ('B', COLORS['success'], 0.7),
        ('I', COLORS['danger'], 1.4),
    ]

    frame_w = 1.1
    gap = 0.3
    y_center = 0.5

    for i, (ftype, color, height) in enumerate(frames):
        x = i * (frame_w + gap)
        h = height
        rect = FancyBboxPatch((x, y_center - h / 2), frame_w, h,
                               boxstyle="round,pad=0.04",
                               facecolor=color, edgecolor='white',
                               linewidth=2, alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + frame_w / 2, y_center, ftype, ha='center', va='center',
                fontsize=14, fontweight='bold', color='white')

    # 参考箭头：P 帧参考前面的 I/P 帧
    arrow_y = -0.6
    # I(0) -> P(3)
    ax.annotate('', xy=(0 * (frame_w + gap) + frame_w / 2, arrow_y + 0.1),
                xytext=(3 * (frame_w + gap) + frame_w / 2, arrow_y + 0.1),
                arrowprops=dict(arrowstyle='<-', color=COLORS['primary'], lw=1.5,
                                connectionstyle='arc3,rad=0.25'))
    # P(3) -> P(6)
    ax.annotate('', xy=(3 * (frame_w + gap) + frame_w / 2, arrow_y - 0.1),
                xytext=(6 * (frame_w + gap) + frame_w / 2, arrow_y - 0.1),
                arrowprops=dict(arrowstyle='<-', color=COLORS['primary'], lw=1.5,
                                connectionstyle='arc3,rad=0.25'))
    ax.text(5 * (frame_w + gap), arrow_y - 0.4, '前向参考', fontsize=8,
            color=COLORS['primary'], ha='center')

    # B 帧双向参考（简化标示）
    ax.annotate('', xy=(0 * (frame_w + gap) + frame_w, y_center - 0.6),
                xytext=(1 * (frame_w + gap), y_center - 0.6),
                arrowprops=dict(arrowstyle='->', color=COLORS['success'], lw=1, alpha=0.6))
    ax.annotate('', xy=(3 * (frame_w + gap), y_center - 0.6),
                xytext=(2 * (frame_w + gap) + frame_w, y_center - 0.6),
                arrowprops=dict(arrowstyle='->', color=COLORS['success'], lw=1, alpha=0.6))

    # 图例
    legend_x = 10.5
    legend_items = [
        ('I 帧（关键帧）', COLORS['danger'], '独立解码，数据量最大'),
        ('P 帧（前向预测）', COLORS['primary'], '参考前面的帧，编码差异'),
        ('B 帧（双向预测）', COLORS['success'], '参考前后帧，压缩率最高'),
    ]
    for j, (label, color, desc) in enumerate(legend_items):
        ly = 2.0 - j * 0.65
        rect = FancyBboxPatch((legend_x, ly - 0.15), 0.4, 0.3,
                               boxstyle="round,pad=0.02",
                               facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.8)
        ax.add_patch(rect)
        ax.text(legend_x + 0.6, ly, f'{label}', fontsize=9, va='center',
                color=COLORS['text'], fontweight='bold')
        ax.text(legend_x + 0.6, ly - 0.25, desc, fontsize=8, va='center',
                color=COLORS['text_light'])

    # === 下半部分：GOP 结构 ===
    ax = axes[1]
    ax.axis('off')
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-1.5, 2)
    ax.set_title('GOP（Group of Pictures）结构', fontsize=13, fontweight='bold',
                 color=COLORS['text'], pad=8)

    # 同样的帧序列
    for i, (ftype, color, _) in enumerate(frames):
        x = i * (frame_w + gap)
        rect = FancyBboxPatch((x, 0), frame_w, 0.8,
                               boxstyle="round,pad=0.03",
                               facecolor=color, edgecolor='white',
                               linewidth=2, alpha=0.75)
        ax.add_patch(rect)
        ax.text(x + frame_w / 2, 0.4, ftype, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')

    # GOP 括号
    gop1_end = 9 * (frame_w + gap)
    ax.annotate('', xy=(0, 1.2), xytext=(gop1_end - gap, 1.2),
                arrowprops=dict(arrowstyle='|-|', color=COLORS['secondary'], lw=2))
    ax.text(gop1_end / 2 - gap / 2, 1.5, 'GOP（从一个 I 帧到下一个 I 帧之前）',
            ha='center', fontsize=11, color=COLORS['secondary'], fontweight='bold')

    # 说明
    ax.text(5, -0.8, 'GOP 越大 → 压缩率越高，但 Seek 越慢    |    GOP 越小 → Seek 越快，但压缩率越低',
            ha='center', fontsize=10, color=COLORS['text_light'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['secondary'], alpha=0.08))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-02-ipb-gop.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-02-ipb-gop.png')


# ============================================================
# 图7：DTS 与 PTS
# ============================================================
def gen_dts_pts():
    fig, ax = plt.subplots(figsize=(14, 5.5))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-1, 14)
    ax.set_ylim(-3.5, 3.5)
    ax.set_title('DTS（解码顺序）与 PTS（显示顺序）', fontsize=15,
                 fontweight='bold', color=COLORS['text'], pad=15)

    frame_w = 1.3
    gap = 0.35

    type_color = {
        'I': COLORS['danger'],
        'P': COLORS['primary'],
        'B': COLORS['success'],
    }

    def draw_frame_row(frames, y, label, ax):
        ax.text(-0.8, y + 0.35, label, fontsize=12, fontweight='bold',
                color=COLORS['text'], ha='right', va='center')
        for i, (ftype, idx) in enumerate(frames):
            x = i * (frame_w + gap)
            color = type_color[ftype]
            rect = FancyBboxPatch((x, y), frame_w, 0.7,
                                   boxstyle="round,pad=0.03",
                                   facecolor=color, edgecolor='white',
                                   linewidth=2, alpha=0.8)
            ax.add_patch(rect)
            ax.text(x + frame_w / 2, y + 0.35, f'{ftype}({idx})', ha='center', va='center',
                    fontsize=11, fontweight='bold', color='white')

    # PTS 顺序（显示顺序）
    pts_frames = [('I', 0), ('B', 1), ('B', 2), ('P', 3), ('B', 4), ('B', 5), ('P', 6)]
    draw_frame_row(pts_frames, 1.5, 'PTS\n(显示)', ax)

    # DTS 顺序（解码顺序）
    dts_frames = [('I', 0), ('P', 3), ('B', 1), ('B', 2), ('P', 6), ('B', 4), ('B', 5)]
    draw_frame_row(dts_frames, -0.5, 'DTS\n(解码)', ax)

    # 连线：PTS 和 DTS 中对应的帧
    pts_positions = {f'{t}{i}': idx for idx, (t, i) in enumerate(pts_frames)}
    dts_positions = {f'{t}{i}': idx for idx, (t, i) in enumerate(dts_frames)}

    for key in pts_positions:
        px = pts_positions[key] * (frame_w + gap) + frame_w / 2
        dx = dts_positions[key] * (frame_w + gap) + frame_w / 2
        py = 1.5
        dy = -0.5 + 0.7

        ax.plot([px, dx], [py, dy], color=COLORS['grid'], linewidth=1, alpha=0.5,
                linestyle='--', zorder=0)

    # 说明
    ax.text(5.5, -2.2, 'PTS（Presentation Time Stamp）决定帧在屏幕上的显示时刻 — 播放器音视频同步的核心依据',
            ha='center', fontsize=10, color=COLORS['danger'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['danger'], alpha=0.08))
    ax.text(5.5, -2.9, 'DTS（Decoding Time Stamp）决定帧被解码器处理的先后顺序 — B 帧需要参考未来帧，所以必须先解码被参考的 P 帧',
            ha='center', fontsize=10, color=COLORS['primary'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['primary'], alpha=0.08))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-02-dts-pts.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-02-dts-pts.png')


# ============================================================
# 主函数
# ============================================================
if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print('开始生成视频章节配图...\n')

    gen_video_frames()
    gen_resolution()
    gen_rgb_yuv()
    gen_yuv_subsampling()
    gen_yuv420p_layout()
    gen_ipb_gop()
    gen_dts_pts()

    print('\n全部完成！')
