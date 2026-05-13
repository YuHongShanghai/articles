#!/usr/bin/env python3
"""生成第9篇「进阶渲染技术」配套插图。"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

DPI = 150
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────
# 1. cubemap.png — 立方体贴图示意图
# ─────────────────────────────────────────────────────────
def draw_cubemap():
    """立方体贴图 6 面展开图"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(-0.5, 13)
    ax.set_ylim(-0.5, 7)
    ax.set_aspect('equal')
    ax.axis('off')

    s = 2.0
    # Cross layout (+Y top / -Y bottom):
    #            [+Y (上)]
    #  [-X (左)] [+Z (前)] [+X (右)] [-Z (后)]
    #            [-Y (下)]
    faces = [
        (s,   2*s, '+Y (上)', '#81D4FA'),
        (0,     s, '-X (左)', '#A5D6A7'),
        (s,     s, '+Z (前)', '#EF9A9A'),
        (2*s,   s, '+X (右)', '#CE93D8'),
        (3*s,   s, '-Z (后)', '#FFE082'),
        (s,     0, '-Y (下)', '#FFAB91'),
    ]

    for x, y, label, color in faces:
        rect = plt.Rectangle((x, y), s, s, fc=color, ec='#333', lw=2,
                              alpha=0.8, zorder=2)
        ax.add_patch(rect)
        ax.text(x + s / 2, y + s / 2, label, ha='center', va='center',
                fontsize=11, fontweight='bold', color='#222', zorder=3)

    cx, cy = s + s / 2, s + s / 2
    ax.plot(cx, cy, 'ko', ms=6, zorder=5)
    ax.annotate('方向向量 (x,y,z)\n→ 采样对应面',
                xy=(cx, cy), xytext=(5.5, 5.5),
                fontsize=9, color='#333', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#999',
                          alpha=0.9),
                arrowprops=dict(arrowstyle='->', color='#666', lw=1.5),
                zorder=5)

    enums = [
        'GL_TEXTURE_CUBE_MAP_POSITIVE_X → 右',
        'GL_TEXTURE_CUBE_MAP_NEGATIVE_X → 左',
        'GL_TEXTURE_CUBE_MAP_POSITIVE_Y → 上',
        'GL_TEXTURE_CUBE_MAP_NEGATIVE_Y → 下',
        'GL_TEXTURE_CUBE_MAP_POSITIVE_Z → 前',
        'GL_TEXTURE_CUBE_MAP_NEGATIVE_Z → 后',
    ]
    for i, e in enumerate(enums):
        ax.text(8.8, 5.0 - i * 0.45, e, fontsize=7.5, color='#555')

    ax.text(9.8, 5.7, 'OpenGL 枚举对照', fontsize=10, fontweight='bold',
            color='#333', ha='center')

    fig.suptitle('立方体贴图 (Cubemap) — 展开示意', fontsize=15,
                 fontweight='bold', y=0.97, color='#222')
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(OUT_DIR, 'cubemap.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] cubemap.png')


# ─────────────────────────────────────────────────────────
# 2. shadow_mapping.png — Shadow Mapping 两阶段原理
# ─────────────────────────────────────────────────────────
def draw_shadow_mapping():
    """Shadow Mapping 原理示意图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # === Pass 1: Depth Map ===
    ax = axes[0]
    ax.set_xlim(-1, 10)
    ax.set_ylim(-1, 8)
    ax.axis('off')
    ax.set_title('Pass 1：从光源视角生成深度图', fontsize=13,
                 fontweight='bold', color='#E65100', pad=15)

    # Light source
    ax.plot(1, 7, '*', ms=20, color='#FFC107', mec='#F57F17', mew=2, zorder=5)
    ax.text(1.8, 7, '光源', fontsize=10, fontweight='bold', color='#F57F17')

    # Light rays
    for tx, ty in [(3, 3), (5, 2), (7, 4)]:
        ax.annotate('', xy=(tx, ty), xytext=(1, 7),
                    arrowprops=dict(arrowstyle='->', color='#FFB300',
                                    lw=1.5, alpha=0.6))

    # Objects
    obj1 = plt.Rectangle((2.5, 2.5), 1.5, 2.0, fc='#90CAF9', ec='#1565C0',
                          lw=2, zorder=3)
    ax.add_patch(obj1)
    ax.text(3.25, 3.5, '物体A', ha='center', va='center', fontsize=9,
            fontweight='bold', color='#1565C0')

    obj2 = plt.Rectangle((6.0, 3.5), 1.5, 1.5, fc='#A5D6A7', ec='#2E7D32',
                          lw=2, zorder=3)
    ax.add_patch(obj2)
    ax.text(6.75, 4.25, '物体B', ha='center', va='center', fontsize=9,
            fontweight='bold', color='#2E7D32')

    # Ground
    ax.plot([0, 9], [1, 1], '-', color='#795548', lw=3)
    ax.text(4.5, 0.5, '地面', ha='center', fontsize=9, color='#795548')

    # Depth map
    depth_data = np.ones((4, 6)) * 0.9
    depth_data[1:3, 1:3] = 0.3
    depth_data[0:2, 4:6] = 0.5

    inset = ax.inset_axes([0.6, 0.02, 0.38, 0.35])
    inset.imshow(depth_data, cmap='gray_r', vmin=0, vmax=1,
                 interpolation='nearest')
    inset.set_title('深度贴图 (Shadow Map)', fontsize=8, fontweight='bold')
    inset.set_xticks([])
    inset.set_yticks([])

    # === Pass 2: Shadow Test ===
    ax = axes[1]
    ax.set_xlim(-1, 10)
    ax.set_ylim(-1, 8)
    ax.axis('off')
    ax.set_title('Pass 2：从摄像机视角进行阴影判定', fontsize=13,
                 fontweight='bold', color='#1565C0', pad=15)

    # Camera
    cam_body = plt.Rectangle((0.5, 6.5), 1.0, 0.7, fc='#FFF9C4',
                              ec='#F57F17', lw=2, zorder=5)
    ax.add_patch(cam_body)
    cam_lens = plt.Polygon(
        [[1.5, 6.6], [1.9, 6.7], [1.9, 7.0], [1.5, 7.1]],
        fc='#FFE082', ec='#F57F17', lw=2, zorder=5
    )
    ax.add_patch(cam_lens)
    ax.text(1.0, 7.5, '摄像机', ha='center', fontsize=9, fontweight='bold',
            color='#E65100')

    # Objects with shadow
    obj1 = plt.Rectangle((2.5, 2.5), 1.5, 2.0, fc='#90CAF9', ec='#1565C0',
                          lw=2, zorder=3)
    ax.add_patch(obj1)
    ax.text(3.25, 3.5, '物体A', ha='center', va='center', fontsize=9,
            fontweight='bold', color='#1565C0')

    obj2 = plt.Rectangle((6.0, 3.5), 1.5, 1.5, fc='#A5D6A7', ec='#2E7D32',
                          lw=2, zorder=3)
    ax.add_patch(obj2)
    ax.text(6.75, 4.25, '物体B', ha='center', va='center', fontsize=9,
            fontweight='bold', color='#2E7D32')

    # Ground
    ax.plot([0, 9], [1, 1], '-', color='#795548', lw=3)

    # Shadow area
    shadow = plt.Polygon(
        [[4.0, 1.0], [4.5, 1.0], [5.8, 1.0], [4.0, 2.5]],
        fc='#424242', alpha=0.4, zorder=2
    )
    ax.add_patch(shadow)
    ax.text(4.8, 0.5, '阴影区域', ha='center', fontsize=9,
            fontweight='bold', color='#C62828')

    # Lit area
    ax.text(7.5, 0.5, '受光区域', ha='center', fontsize=9,
            fontweight='bold', color='#2E7D32')

    # Comparison box
    comp_text = ('对每个片段：\n'
                 '片段深度 > Shadow Map 深度\n'
                 '  → 在阴影中 ✗\n'
                 '片段深度 ≤ Shadow Map 深度\n'
                 '  → 被照亮 ✓')
    ax.text(6.5, 7.0, comp_text, fontsize=8, color='#333',
            va='top',
            bbox=dict(boxstyle='round,pad=0.4', fc='#FFF3E0', ec='#E65100',
                      lw=1.5))

    fig.suptitle('阴影映射 (Shadow Mapping) 原理', fontsize=16,
                 fontweight='bold', y=1.0, color='#222')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'shadow_mapping.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] shadow_mapping.png')


# ─────────────────────────────────────────────────────────
# 3. fbo_pipeline.png — 帧缓冲 + 后处理 渲染管线
# ─────────────────────────────────────────────────────────
def draw_fbo_pipeline():
    """帧缓冲 + 后处理流程图"""
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-0.5, 4.5)
    ax.axis('off')

    passes = [
        ('Pass 1\n渲染场景', '绘制到自定义FBO\n颜色附件=纹理\n深度附件=RBO',
         '#E3F2FD', '#1565C0'),
        ('颜色纹理', '场景渲染结果\n存储为纹理',
         '#FFF3E0', '#E65100'),
        ('Pass 2\n后处理', '全屏四边形\n对纹理做图像处理\n(反相/灰度/卷积核)',
         '#E8F5E9', '#2E7D32'),
        ('屏幕输出', '默认帧缓冲\n最终显示结果',
         '#FCE4EC', '#C62828'),
    ]

    bw, bh = 2.8, 2.5
    gap = 0.7

    for i, (title, desc, fc, ec) in enumerate(passes):
        x = i * (bw + gap)
        b = FancyBboxPatch(
            (x, 0.8), bw, bh, boxstyle="round,pad=0.15",
            facecolor=fc, edgecolor=ec, linewidth=2, alpha=0.92, zorder=3
        )
        ax.add_patch(b)
        ax.text(x + bw / 2, 0.8 + bh - 0.4, title,
                ha='center', va='center', fontsize=11,
                fontweight='bold', color=ec, zorder=4)
        ax.text(x + bw / 2, 0.8 + bh / 2 - 0.3, desc,
                ha='center', va='center', fontsize=8.5,
                color='#333', zorder=4)

        if i < len(passes) - 1:
            ax.annotate('', xy=(x + bw + gap, 0.8 + bh / 2),
                        xytext=(x + bw, 0.8 + bh / 2),
                        arrowprops=dict(arrowstyle='->', color='#555',
                                        lw=2.5))

    fig.suptitle('帧缓冲 (FBO) 后处理渲染管线', fontsize=15,
                 fontweight='bold', y=0.97, color='#222')
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(os.path.join(OUT_DIR, 'fbo_pipeline.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] fbo_pipeline.png')


# ─────────────────────────────────────────────────────────
# 4. kernel_effects.png — 卷积核效果对比
# ─────────────────────────────────────────────────────────
def draw_kernel_effects():
    """展示三种常见卷积核"""
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

    kernels = [
        ('锐化 (Sharpen)',
         np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]),
         '#E65100'),
        ('高斯模糊 (Blur)',
         np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]]) / 16.0,
         '#1565C0'),
        ('边缘检测 (Edge)',
         np.array([[1, 1, 1], [1, -8, 1], [1, 1, 1]]),
         '#2E7D32'),
    ]

    for ax, (title, kernel, color) in zip(axes, kernels):
        ax.set_title(title, fontsize=12, fontweight='bold', color=color,
                     pad=10)

        vmax = max(abs(kernel.max()), abs(kernel.min()), 1)
        im = ax.imshow(kernel, cmap='RdBu_r', vmin=-vmax, vmax=vmax,
                       interpolation='nearest')
        ax.set_xticks([0, 1, 2])
        ax.set_yticks([0, 1, 2])

        for i in range(3):
            for j in range(3):
                val = kernel[i, j]
                text = f'{val:.2f}' if isinstance(val, float) and val != int(val) else f'{int(val)}'
                text_color = 'white' if abs(val) > vmax * 0.6 else 'black'
                ax.text(j, i, text, ha='center', va='center',
                        fontsize=12, fontweight='bold', color=text_color)

        ax.tick_params(length=0)
        ax.set_xticklabels([])
        ax.set_yticklabels([])

    fig.suptitle('后处理卷积核 (Kernel)', fontsize=15, fontweight='bold',
                 y=1.0, color='#222')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'kernel_effects.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] kernel_effects.png')


if __name__ == '__main__':
    print('正在生成第9篇插图...')
    draw_cubemap()
    draw_shadow_mapping()
    draw_fbo_pipeline()
    draw_kernel_effects()
    print('全部完成！')
