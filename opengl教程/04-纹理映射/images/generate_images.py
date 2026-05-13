#!/usr/bin/env python3
"""生成第4篇"纹理映射"教程的所有插图。"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.gridspec import GridSpec

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 150


def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✓ {name}")


# ---------- 1. 纹理坐标系 (UV) 示意图 ----------
def gen_texture_coordinates():
    fig, ax = plt.subplots(figsize=(6, 6), facecolor='white')

    checkerboard = np.zeros((8, 8, 3))
    c1 = np.array([0.93, 0.55, 0.25])
    c2 = np.array([0.98, 0.82, 0.60])
    for i in range(8):
        for j in range(8):
            checkerboard[i, j] = c1 if (i + j) % 2 == 0 else c2

    ax.imshow(checkerboard, extent=[0, 1, 0, 1], origin='lower', interpolation='nearest')

    ax.set_xlim(-0.15, 1.15)
    ax.set_ylim(-0.15, 1.15)
    ax.set_xlabel('U', fontsize=14, fontweight='bold')
    ax.set_ylabel('V', fontsize=14, fontweight='bold', rotation=0, labelpad=15)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')

    corners = {
        (0, 0): '(0, 0)', (1, 0): '(1, 0)',
        (0, 1): '(0, 1)', (1, 1): '(1, 1)',
    }
    for (x, y), label in corners.items():
        ax.plot(x, y, 'o', color='#e74c3c', markersize=10, zorder=5)
        offset_x = -0.08 if x == 0 else 0.02
        offset_y = -0.06 if y == 0 else 0.03
        ax.annotate(label, (x, y), (x + offset_x, y + offset_y),
                    fontsize=13, fontweight='bold', color='#c0392b')

    ax.annotate('', xy=(1.12, 0), xytext=(-0.05, 0),
                arrowprops=dict(arrowstyle='->', lw=2, color='#2c3e50'))
    ax.annotate('', xy=(0, 1.12), xytext=(0, -0.05),
                arrowprops=dict(arrowstyle='->', lw=2, color='#2c3e50'))

    ax.set_title('纹理坐标系 (UV)', fontsize=16, fontweight='bold', pad=12)

    rect = mpatches.Rectangle((0, 0), 1, 1, linewidth=2.5,
                                edgecolor='#2c3e50', facecolor='none', zorder=4)
    ax.add_patch(rect)

    ax.text(0.5, 0.5, '纹理图像区域', fontsize=14, ha='center', va='center',
            color='#2c3e50', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85))

    save(fig, 'texture_coordinates.png')


# ---------- 2. 四种环绕模式对比图 ----------
def gen_wrapping_modes():
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5), facecolor='white')
    fig.suptitle('四种纹理环绕模式对比（纹理坐标范围 [-0.5, 1.5]）',
                 fontsize=15, fontweight='bold', y=1.02)

    base = np.zeros((4, 4, 3))
    colors = [
        [0.27, 0.51, 0.71], [0.36, 0.62, 0.80],
        [0.45, 0.73, 0.87], [0.54, 0.81, 0.94]
    ]
    for i in range(4):
        for j in range(4):
            base[i, j] = colors[(i + j) % 4]

    modes = [
        ('GL_REPEAT\n重复平铺', 'repeat'),
        ('GL_MIRRORED_REPEAT\n镜像重复', 'mirrored'),
        ('GL_CLAMP_TO_EDGE\n边缘拉伸', 'clamp_edge'),
        ('GL_CLAMP_TO_BORDER\n边框颜色', 'clamp_border'),
    ]

    for ax, (title, mode) in zip(axes, modes):
        big = np.ones((12, 12, 3)) * 0.15

        for bi in range(12):
            for bj in range(12):
                u = (bj - 2) / 4.0
                v = (bi - 2) / 4.0

                if mode == 'repeat':
                    su = u % 1.0
                    sv = v % 1.0
                    si, sj = int(sv * 4) % 4, int(su * 4) % 4
                    big[bi, bj] = base[si, sj]

                elif mode == 'mirrored':
                    fu = int(np.floor(u))
                    fv = int(np.floor(v))
                    su = u - fu
                    sv = v - fv
                    if fu % 2 != 0:
                        su = 1.0 - su
                    if fv % 2 != 0:
                        sv = 1.0 - sv
                    si = min(int(sv * 4), 3)
                    sj = min(int(su * 4), 3)
                    big[bi, bj] = base[si, sj]

                elif mode == 'clamp_edge':
                    cu = max(0.0, min(u, 0.999))
                    cv = max(0.0, min(v, 0.999))
                    si, sj = int(cv * 4) % 4, int(cu * 4) % 4
                    big[bi, bj] = base[si, sj]

                elif mode == 'clamp_border':
                    if 0 <= u < 1.0 and 0 <= v < 1.0:
                        si, sj = int(v * 4) % 4, int(u * 4) % 4
                        big[bi, bj] = base[si, sj]
                    else:
                        big[bi, bj] = [0.95, 0.85, 0.30]

        ax.imshow(big, origin='lower', interpolation='nearest', extent=[-0.5, 2.5, -0.5, 2.5])

        rect = mpatches.Rectangle((0, 0), 1, 1, linewidth=2, linestyle='--',
                                   edgecolor='#e74c3c', facecolor='none', zorder=4)
        ax.add_patch(rect)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xticks([0, 0.5, 1.0, 1.5])
        ax.set_yticks([0, 0.5, 1.0, 1.5])
        ax.tick_params(labelsize=8)
        ax.set_aspect('equal')

    fig.tight_layout()
    save(fig, 'wrapping_modes.png')


# ---------- 3. Nearest vs Linear 过滤对比 ----------
def gen_filtering_modes():
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), facecolor='white',
                              gridspec_kw={'width_ratios': [1, 1.3, 1.3]})
    fig.suptitle('纹理过滤模式对比', fontsize=15, fontweight='bold', y=1.0)

    np.random.seed(42)
    small = np.zeros((4, 4, 3))
    palette = [
        [0.90, 0.30, 0.25],
        [0.20, 0.65, 0.35],
        [0.25, 0.50, 0.85],
        [0.95, 0.75, 0.20],
    ]
    for i in range(4):
        for j in range(4):
            small[i, j] = palette[(i * 4 + j) % 4]

    ax0 = axes[0]
    ax0.imshow(small, origin='lower', interpolation='nearest',
               extent=[0, 4, 0, 4])
    ax0.set_title('原始纹理\n（4×4 纹素）', fontsize=12, fontweight='bold')
    for i in range(5):
        ax0.axhline(i, color='white', lw=0.5)
        ax0.axvline(i, color='white', lw=0.5)
    ax0.set_xticks(range(5))
    ax0.set_yticks(range(5))
    ax0.set_aspect('equal')

    ax1 = axes[1]
    nearest = np.zeros((16, 16, 3))
    for i in range(16):
        for j in range(16):
            si = min(i // 4, 3)
            sj = min(j // 4, 3)
            nearest[i, j] = small[si, sj]
    ax1.imshow(nearest, origin='lower', interpolation='nearest',
               extent=[0, 4, 0, 4])
    ax1.set_title('GL_NEAREST（最近邻）\n放大后像素边缘锐利', fontsize=12, fontweight='bold')
    for i in range(5):
        ax1.axhline(i, color='white', lw=0.3, alpha=0.5)
        ax1.axvline(i, color='white', lw=0.3, alpha=0.5)
    ax1.set_aspect('equal')

    ax2 = axes[2]
    ax2.imshow(small, origin='lower', interpolation='bilinear',
               extent=[0, 4, 0, 4])
    ax2.set_title('GL_LINEAR（双线性）\n放大后颜色过渡平滑', fontsize=12, fontweight='bold')
    for i in range(5):
        ax2.axhline(i, color='white', lw=0.3, alpha=0.5)
        ax2.axvline(i, color='white', lw=0.3, alpha=0.5)
    ax2.set_aspect('equal')

    fig.tight_layout()
    save(fig, 'filtering_modes.png')


# ---------- 4. 纹理创建和绑定流程图 ----------
def gen_texture_bindflow():
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_aspect('equal')

    box_style = dict(boxstyle='round,pad=0.4', facecolor='#3498db', edgecolor='#2c3e50',
                     linewidth=2, alpha=0.9)
    box_style_alt = dict(boxstyle='round,pad=0.4', facecolor='#2ecc71', edgecolor='#27ae60',
                         linewidth=2, alpha=0.9)
    box_style_gpu = dict(boxstyle='round,pad=0.4', facecolor='#e67e22', edgecolor='#d35400',
                         linewidth=2, alpha=0.9)

    text_props = dict(fontsize=11, fontweight='bold', color='white',
                      ha='center', va='center', zorder=5)

    steps = [
        (5, 9.0, 'glGenTextures(1, &id)\n生成纹理对象', box_style),
        (5, 7.5, 'stbi_load(path, ...)\n加载图片到 CPU 内存', box_style_alt),
        (5, 6.0, 'glBindTexture(GL_TEXTURE_2D, id)\n绑定纹理', box_style),
        (5, 4.5, 'glTexImage2D(...)\n上传像素数据到 GPU', box_style_gpu),
        (5, 3.0, 'glGenerateMipmap(...)\n自动生成 Mipmap 链', box_style_gpu),
        (5, 1.5, 'glTexParameteri(...)\n设置环绕模式与过滤方式', box_style),
    ]

    for x, y, text, style in steps:
        ax.text(x, y, text, **text_props, bbox=style)

    for i in range(len(steps) - 1):
        y_start = steps[i][1] - 0.45
        y_end = steps[i + 1][1] + 0.45
        ax.annotate('', xy=(5, y_end), xytext=(5, y_start),
                    arrowprops=dict(arrowstyle='->', lw=2.5, color='#2c3e50'))

    ax.text(1.2, 7.5, 'CPU 端', fontsize=12, fontweight='bold', color='#27ae60',
            ha='center', va='center',
            bbox=dict(boxstyle='round', facecolor='#eafaf1', edgecolor='#27ae60', lw=1.5))

    ax.text(1.2, 4.5, 'GPU 端', fontsize=12, fontweight='bold', color='#d35400',
            ha='center', va='center',
            bbox=dict(boxstyle='round', facecolor='#fef5e7', edgecolor='#d35400', lw=1.5))

    ax.axhline(y=5.25, xmin=0.05, xmax=0.95, color='#bdc3c7', linestyle='--', lw=1.5)
    ax.text(9.0, 5.25, 'CPU ↔ GPU\n传输边界', fontsize=9, color='#7f8c8d',
            ha='center', va='center')

    ax.text(8.5, 1.5, '别忘了最后\nstbi_image_free(data)\n释放 CPU 内存', fontsize=9,
            color='#e74c3c', ha='center', va='center',
            bbox=dict(boxstyle='round', facecolor='#fdedec', edgecolor='#e74c3c', lw=1))

    ax.set_title('纹理创建与绑定流程', fontsize=16, fontweight='bold', pad=15)

    save(fig, 'texture_bindflow.png')


# ---------- 主入口 ----------
if __name__ == '__main__':
    print("正在生成插图...")
    gen_texture_coordinates()
    gen_wrapping_modes()
    gen_filtering_modes()
    gen_texture_bindflow()
    print("全部完成！")
