#!/usr/bin/env python3
"""
为 03-音频基础知识.md 生成配图
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib
import os

# ============================================================
# 全局样式设置
# ============================================================
matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# 配色方案（现代科技感）
COLORS = {
    'primary':    '#2563EB',   # 蓝色
    'secondary':  '#7C3AED',   # 紫色
    'accent':     '#F59E0B',   # 橙色
    'success':    '#10B981',   # 绿色
    'danger':     '#EF4444',   # 红色
    'pink':       '#EC4899',   # 粉色
    'bg':         '#F8FAFC',   # 背景色
    'grid':       '#E2E8F0',   # 网格色
    'text':       '#1E293B',   # 文字色
    'text_light': '#64748B',   # 浅色文字
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')
DPI = 150


def setup_ax(ax, title=None):
    """统一设置坐标轴样式"""
    ax.set_facecolor(COLORS['bg'])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    ax.tick_params(colors=COLORS['text_light'], labelsize=10)
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', color=COLORS['text'], pad=12)


# ============================================================
# 图1：声波示意图
# ============================================================
def gen_sound_wave():
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('声波的三个关键物理参数', fontsize=16, fontweight='bold',
                 color=COLORS['text'], y=1.02)

    t = np.linspace(0, 0.01, 1000)

    # --- 频率对比 ---
    ax = axes[0]
    setup_ax(ax, '频率（Hz）— 决定音调')
    y1 = np.sin(2 * np.pi * 440 * t)
    y2 = np.sin(2 * np.pi * 880 * t)
    ax.plot(t * 1000, y1, color=COLORS['primary'], linewidth=2.2, label='440 Hz（低音）')
    ax.plot(t * 1000, y2, color=COLORS['danger'], linewidth=2.2, alpha=0.8, label='880 Hz（高音）')
    ax.set_xlabel('时间（ms）', fontsize=11, color=COLORS['text_light'])
    ax.set_ylabel('振幅', fontsize=11, color=COLORS['text_light'])
    ax.legend(fontsize=9, loc='upper right', framealpha=0.9)
    ax.set_xlim(0, 10)
    ax.axhline(y=0, color=COLORS['grid'], linewidth=0.8)

    # --- 振幅对比 ---
    ax = axes[1]
    setup_ax(ax, '振幅 — 决定音量')
    y1 = 1.0 * np.sin(2 * np.pi * 440 * t)
    y2 = 0.4 * np.sin(2 * np.pi * 440 * t)
    ax.plot(t * 1000, y1, color=COLORS['primary'], linewidth=2.2, label='大振幅（响）')
    ax.plot(t * 1000, y2, color=COLORS['accent'], linewidth=2.2, label='小振幅（轻）')
    ax.set_xlabel('时间（ms）', fontsize=11, color=COLORS['text_light'])
    ax.legend(fontsize=9, loc='upper right', framealpha=0.9)
    ax.set_xlim(0, 10)
    ax.axhline(y=0, color=COLORS['grid'], linewidth=0.8)

    # 标注振幅
    ax.annotate('', xy=(2.84, 1.0), xytext=(2.84, 0),
                arrowprops=dict(arrowstyle='<->', color=COLORS['primary'], lw=1.5))
    ax.text(3.1, 0.5, '振幅 A', fontsize=9, color=COLORS['primary'], fontweight='bold')

    # --- 波形对比 ---
    ax = axes[2]
    setup_ax(ax, '波形 — 决定音色')
    y_sin = np.sin(2 * np.pi * 440 * t)
    # 合成一个"锯齿感"波形
    y_complex = (np.sin(2 * np.pi * 440 * t)
                 + 0.5 * np.sin(2 * np.pi * 880 * t)
                 + 0.25 * np.sin(2 * np.pi * 1320 * t))
    y_complex = y_complex / np.max(np.abs(y_complex))
    ax.plot(t * 1000, y_sin, color=COLORS['primary'], linewidth=2.2, label='纯正弦波')
    ax.plot(t * 1000, y_complex, color=COLORS['secondary'], linewidth=2.2, alpha=0.85, label='复合波形')
    ax.set_xlabel('时间（ms）', fontsize=11, color=COLORS['text_light'])
    ax.legend(fontsize=9, loc='upper right', framealpha=0.9)
    ax.set_xlim(0, 10)
    ax.axhline(y=0, color=COLORS['grid'], linewidth=0.8)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-03-sound-wave.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-03-sound-wave.png')


# ============================================================
# 图2：采样示意图
# ============================================================
def gen_sampling():
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('声音的数字化：采样过程', fontsize=16, fontweight='bold',
                 color=COLORS['text'], y=1.02)

    t_cont = np.linspace(0, 0.005, 2000)
    signal = np.sin(2 * np.pi * 440 * t_cont) + 0.3 * np.sin(2 * np.pi * 1200 * t_cont)

    # --- 原始模拟信号 ---
    ax = axes[0]
    setup_ax(ax, '① 原始模拟信号（连续）')
    ax.plot(t_cont * 1000, signal, color=COLORS['primary'], linewidth=2)
    ax.fill_between(t_cont * 1000, signal, alpha=0.08, color=COLORS['primary'])
    ax.set_xlabel('时间（ms）', fontsize=11, color=COLORS['text_light'])
    ax.set_ylabel('振幅', fontsize=11, color=COLORS['text_light'])
    ax.axhline(y=0, color=COLORS['grid'], linewidth=0.8)

    # --- 采样 ---
    ax = axes[1]
    setup_ax(ax, '② 采样（在固定时间点取值）')
    ax.plot(t_cont * 1000, signal, color=COLORS['primary'], linewidth=1.2, alpha=0.35)

    # 低采样率采样点
    n_samples = 30
    t_sampled = np.linspace(0, 0.005, n_samples)
    sig_sampled = np.sin(2 * np.pi * 440 * t_sampled) + 0.3 * np.sin(2 * np.pi * 1200 * t_sampled)

    # 竖线
    for ts, ss in zip(t_sampled, sig_sampled):
        ax.plot([ts * 1000, ts * 1000], [0, ss], color=COLORS['accent'], linewidth=1, alpha=0.5)

    ax.scatter(t_sampled * 1000, sig_sampled, color=COLORS['danger'], s=40, zorder=5, edgecolors='white', linewidth=1)
    ax.set_xlabel('时间（ms）', fontsize=11, color=COLORS['text_light'])
    ax.axhline(y=0, color=COLORS['grid'], linewidth=0.8)

    # 标注采样间隔
    idx = 10
    ax.annotate('', xy=(t_sampled[idx] * 1000, -1.15), xytext=(t_sampled[idx + 1] * 1000, -1.15),
                arrowprops=dict(arrowstyle='<->', color=COLORS['text_light'], lw=1.2))
    ax.text((t_sampled[idx] + t_sampled[idx + 1]) / 2 * 1000, -1.35, '采样间隔\n= 1/采样率',
            fontsize=8, ha='center', color=COLORS['text_light'])

    # --- 采样率对比 ---
    ax = axes[2]
    setup_ax(ax, '③ 不同采样率的效果')

    ax.plot(t_cont * 1000, signal, color=COLORS['grid'], linewidth=1.5, alpha=0.5, label='原始信号')

    for n, color, label in [(50, COLORS['success'], '高采样率'),
                             (15, COLORS['danger'], '低采样率')]:
        t_s = np.linspace(0, 0.005, n)
        s_s = np.sin(2 * np.pi * 440 * t_s) + 0.3 * np.sin(2 * np.pi * 1200 * t_s)
        ax.plot(t_s * 1000, s_s, color=color, linewidth=1.5, marker='o', markersize=4,
                alpha=0.85, label=label)

    ax.set_xlabel('时间（ms）', fontsize=11, color=COLORS['text_light'])
    ax.legend(fontsize=9, loc='lower right', framealpha=0.9)
    ax.axhline(y=0, color=COLORS['grid'], linewidth=0.8)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-03-sampling.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-03-sampling.png')


# ============================================================
# 图3：量化示意图
# ============================================================
def gen_quantization():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('量化：将连续幅度值映射到离散级别', fontsize=16, fontweight='bold',
                 color=COLORS['text'], y=1.02)

    t = np.linspace(0, 0.005, 1000)
    signal = np.sin(2 * np.pi * 440 * t)

    for i, (bits, title_suffix) in enumerate([(3, '3-bit 量化（8 级）'), (6, '6-bit 量化（64 级）')]):
        ax = axes[i]
        setup_ax(ax, title_suffix)
        levels = 2 ** bits
        step = 2.0 / levels  # 范围 [-1, 1]

        # 原始信号
        ax.plot(t * 1000, signal, color=COLORS['primary'], linewidth=1.5, alpha=0.35, label='原始信号')

        # 量化
        quantized = np.round(signal / step) * step
        quantized = np.clip(quantized, -1, 1)

        # 画阶梯
        ax.step(t * 1000, quantized, where='mid', color=COLORS['danger'], linewidth=2, label='量化后')

        # 画量化级别
        q_levels = np.arange(-1, 1 + step, step)
        for lv in q_levels:
            ax.axhline(y=lv, color=COLORS['grid'], linewidth=0.5, alpha=0.5)

        # 量化误差填充
        ax.fill_between(t * 1000, signal, quantized, alpha=0.15, color=COLORS['accent'], label='量化误差')

        ax.set_xlabel('时间（ms）', fontsize=11, color=COLORS['text_light'])
        if i == 0:
            ax.set_ylabel('振幅', fontsize=11, color=COLORS['text_light'])
        ax.legend(fontsize=9, loc='upper right', framealpha=0.9)
        ax.set_ylim(-1.3, 1.3)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-03-quantization.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-03-quantization.png')


# ============================================================
# 图4：PCM 数据布局
# ============================================================
def gen_pcm_layout():
    fig, axes = plt.subplots(3, 1, figsize=(14, 7))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('PCM 数据存储布局', fontsize=16, fontweight='bold',
                 color=COLORS['text'], y=0.98)

    def draw_blocks(ax, blocks, title, y_center=0.5):
        """画一行方块表示数据布局"""
        ax.set_xlim(-0.5, len(blocks) + 0.5)
        ax.set_ylim(-0.2, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=13, fontweight='bold', color=COLORS['text'], pad=8, loc='left')

        for i, (label, color) in enumerate(blocks):
            rect = FancyBboxPatch((i, y_center - 0.35), 0.9, 0.7,
                                   boxstyle="round,pad=0.05",
                                   facecolor=color, edgecolor='white',
                                   linewidth=2, alpha=0.85)
            ax.add_patch(rect)
            ax.text(i + 0.45, y_center, label, ha='center', va='center',
                    fontsize=10, fontweight='bold', color='white')

    # 单声道
    mono_blocks = [(f'S{i+1}', COLORS['primary']) for i in range(10)]
    draw_blocks(axes[0], mono_blocks, '单声道（Mono）')
    axes[0].text(5, -0.05, '→ 时间顺序排列 →', ha='center', fontsize=10, color=COLORS['text_light'])

    # 交错存储
    interleaved = []
    for i in range(5):
        interleaved.append((f'L{i+1}', COLORS['primary']))
        interleaved.append((f'R{i+1}', COLORS['danger']))
    draw_blocks(axes[1], interleaved, '双声道 — 交错存储（Interleaved）')
    # 添加图例
    axes[1].plot([], [], 's', color=COLORS['primary'], markersize=10, label='左声道 (L)')
    axes[1].plot([], [], 's', color=COLORS['danger'], markersize=10, label='右声道 (R)')
    axes[1].legend(fontsize=9, loc='upper right', framealpha=0.9, ncol=2)

    # 平面存储
    planar = []
    for i in range(5):
        planar.append((f'L{i+1}', COLORS['primary']))
    for i in range(5):
        planar.append((f'R{i+1}', COLORS['danger']))
    draw_blocks(axes[2], planar, '双声道 — 平面存储（Planar）')
    # 分隔标记
    axes[2].axvline(x=4.95, color=COLORS['text_light'], linewidth=1.5, linestyle='--', ymin=0.1, ymax=0.9)
    axes[2].text(2.5, -0.05, '← 左声道数据 →', ha='center', fontsize=9, color=COLORS['primary'], fontweight='bold')
    axes[2].text(7.5, -0.05, '← 右声道数据 →', ha='center', fontsize=9, color=COLORS['danger'], fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-03-pcm-layout.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-03-pcm-layout.png')


# ============================================================
# 图5：声道布局
# ============================================================
def gen_channel_layout():
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('常见声道布局', fontsize=16, fontweight='bold', color=COLORS['text'], y=1.0)

    def draw_listener(ax):
        """画一个听众（头顶视角）"""
        # 头
        circle = plt.Circle((0, 0), 0.12, facecolor=COLORS['text_light'], alpha=0.25,
                             edgecolor=COLORS['text_light'], linewidth=1.5)
        ax.add_patch(circle)
        # 鼻子朝向
        ax.annotate('', xy=(0, 0.22), xytext=(0, 0.12),
                     arrowprops=dict(arrowstyle='->', color=COLORS['text_light'], lw=1.5))
        # 左右耳
        ear_l = plt.Circle((-0.14, 0), 0.03, facecolor=COLORS['text_light'], alpha=0.4)
        ear_r = plt.Circle((0.14, 0), 0.03, facecolor=COLORS['text_light'], alpha=0.4)
        ax.add_patch(ear_l)
        ax.add_patch(ear_r)
        ax.text(0, -0.25, '听众', fontsize=9, ha='center', va='center',
                color=COLORS['text_light'], fontstyle='italic')

    def draw_speaker(ax, x, y, label, color):
        """画一个音箱"""
        rect = FancyBboxPatch((x - 0.1, y - 0.1), 0.2, 0.2,
                               boxstyle="round,pad=0.03",
                               facecolor=color, edgecolor='white', linewidth=2, alpha=0.85)
        ax.add_patch(rect)
        # 喇叭图案（用同心圆模拟）
        inner = plt.Circle((x, y), 0.04, facecolor='white', alpha=0.5)
        ax.add_patch(inner)
        ax.text(x, y - 0.19, label, fontsize=10, ha='center', va='top',
                color=COLORS['text'], fontweight='bold')

    # --- Mono ---
    ax = axes[0]
    setup_ax(ax, 'Mono（单声道）')
    ax.set_xlim(-1, 1)
    ax.set_ylim(-0.8, 1)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Mono（单声道）', fontsize=13, fontweight='bold', color=COLORS['text'], pad=10)
    draw_listener(ax)
    draw_speaker(ax, 0, 0.65, 'C', COLORS['primary'])

    # --- Stereo ---
    ax = axes[1]
    ax.set_xlim(-1, 1)
    ax.set_ylim(-0.8, 1)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Stereo（立体声）', fontsize=13, fontweight='bold', color=COLORS['text'], pad=10)
    draw_listener(ax)
    draw_speaker(ax, -0.5, 0.6, 'L', COLORS['primary'])
    draw_speaker(ax, 0.5, 0.6, 'R', COLORS['danger'])

    # --- 5.1 ---
    ax = axes[2]
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1, 1.1)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('5.1 环绕声', fontsize=13, fontweight='bold', color=COLORS['text'], pad=10)
    draw_listener(ax)
    # 前左、前右
    draw_speaker(ax, -0.6, 0.7, 'FL', COLORS['primary'])
    draw_speaker(ax, 0.6, 0.7, 'FR', COLORS['danger'])
    # 中置
    draw_speaker(ax, 0, 0.85, 'C', COLORS['success'])
    # 低音
    draw_speaker(ax, 0.0, 0.45, 'LFE', COLORS['accent'])
    # 后左、后右
    draw_speaker(ax, -0.65, -0.45, 'SL', COLORS['secondary'])
    draw_speaker(ax, 0.65, -0.45, 'SR', COLORS['pink'])

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-03-channel-layout.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-03-channel-layout.png')


# ============================================================
# 图6：音频编码对比
# ============================================================
def gen_audio_comparison():
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(COLORS['bg'])
    setup_ax(ax)

    # 数据：1分钟 CD 音质（44100Hz, 16bit, 双声道）的近似文件大小 (MB)
    formats = ['PCM\n（无压缩）', 'FLAC\n（无损）', 'MP3\n（320kbps）', 'AAC\n（256kbps）', 'Opus\n（128kbps）', 'MP3\n（128kbps）']
    sizes =   [10.1,             5.0,             2.4,              1.9,              0.96,             0.96]
    colors =  [COLORS['text_light'], COLORS['success'], COLORS['primary'], COLORS['accent'], COLORS['secondary'], COLORS['danger']]

    bars = ax.barh(range(len(formats)), sizes, color=colors, height=0.6, edgecolor='white', linewidth=2)

    ax.set_yticks(range(len(formats)))
    ax.set_yticklabels(formats, fontsize=11, color=COLORS['text'])
    ax.set_xlabel('文件大小（MB / 分钟）', fontsize=12, color=COLORS['text_light'])
    ax.set_title('常见音频编码 — 1 分钟 CD 音质音频文件大小对比', fontsize=14,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 标注数值
    for bar, size in zip(bars, sizes):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                f'{size:.1f} MB', va='center', fontsize=11, fontweight='bold', color=COLORS['text'])

    # 标注分类
    ax.axvline(x=0, color=COLORS['grid'], linewidth=0.5)
    ax.set_xlim(0, 13)

    # 无损/有损标记
    ax.text(11.5, 0.5, '无压缩 /\n无损压缩', fontsize=9, ha='center', va='center',
            color=COLORS['success'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['success'], alpha=0.1))
    ax.text(11.5, 3.5, '有损压缩', fontsize=9, ha='center', va='center',
            color=COLORS['danger'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['danger'], alpha=0.1))

    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-03-audio-compression.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-03-audio-compression.png')


# ============================================================
# 图7：音频帧概念图
# ============================================================
def gen_audio_frame():
    fig, ax = plt.subplots(figsize=(14, 4))
    fig.patch.set_facecolor(COLORS['bg'])
    ax.axis('off')
    ax.set_xlim(-0.5, 15)
    ax.set_ylim(-1.5, 2.5)
    ax.set_title('音频帧：固定数量的采样点组成一帧', fontsize=14,
                 fontweight='bold', color=COLORS['text'], pad=15)

    # 画连续的采样点
    t = np.linspace(0, 4 * np.pi, 100)
    y = np.sin(t) * 0.6

    # 映射到 x 范围 [0, 14]
    x_vals = np.linspace(0, 14, 100)

    ax.plot(x_vals, y, color=COLORS['primary'], linewidth=1.5, alpha=0.4)
    ax.scatter(x_vals, y, s=12, color=COLORS['primary'], alpha=0.6, zorder=3)

    # 画帧边界
    frame_colors = [COLORS['primary'], COLORS['secondary'], COLORS['success'], COLORS['accent']]
    frame_labels = ['帧 1\n(1024 samples)', '帧 2\n(1024 samples)', '帧 3\n(1024 samples)', '帧 4\n...']
    frame_width = 3.5
    for i in range(4):
        x_start = i * frame_width
        rect = FancyBboxPatch((x_start, -0.95), frame_width - 0.1, 1.9,
                               boxstyle="round,pad=0.05",
                               facecolor=frame_colors[i], alpha=0.08,
                               edgecolor=frame_colors[i], linewidth=2, linestyle='--')
        ax.add_patch(rect)
        ax.text(x_start + frame_width / 2 - 0.05, -1.3, frame_labels[i],
                ha='center', va='top', fontsize=10, color=frame_colors[i], fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'diagram-03-audio-frame.png'),
                dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print('✓ diagram-03-audio-frame.png')


# ============================================================
# 主函数
# ============================================================
if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print('开始生成配图...\n')

    gen_sound_wave()
    gen_sampling()
    gen_quantization()
    gen_pcm_layout()
    gen_channel_layout()
    gen_audio_comparison()
    gen_audio_frame()

    print('\n全部完成！')
