#!/usr/bin/env python3
"""生成第5篇「坐标系统与3D变换」配套插图。"""

import sys

_user_mpl = '/home/yh/.local/lib/python3.10/site-packages'

# Must fix mpl_toolkits path BEFORE matplotlib loads its projections
import mpl_toolkits
mpl_toolkits.__path__ = [_user_mpl + '/mpl_toolkits']

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

DPI = 150
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────
# 1. coordinate_spaces.png — 五大坐标空间变换链流程图
# ─────────────────────────────────────────────────────────
def draw_coordinate_spaces():
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.set_xlim(-0.5, 14.5)
    ax.set_ylim(-1.5, 3.0)
    ax.axis('off')

    spaces = [
        ("局部空间\n(Local Space)", "#4FC3F7"),
        ("世界空间\n(World Space)", "#81C784"),
        ("观察空间\n(View Space)", "#FFB74D"),
        ("裁剪空间\n(Clip Space)", "#E57373"),
        ("屏幕空间\n(Screen Space)", "#BA68C8"),
    ]
    transforms = [
        "Model 矩阵",
        "View 矩阵",
        "Projection 矩阵",
        "视口变换\n(Viewport)",
    ]

    box_w, box_h = 2.0, 1.6
    gap = 0.9
    start_x = 0.2

    for i, (label, color) in enumerate(spaces):
        x = start_x + i * (box_w + gap)
        box = FancyBboxPatch(
            (x, 0), box_w, box_h, boxstyle="round,pad=0.15",
            facecolor=color, edgecolor='#333333', linewidth=1.8, alpha=0.92
        )
        ax.add_patch(box)
        ax.text(x + box_w / 2, box_h / 2, label,
                ha='center', va='center', fontsize=11, fontweight='bold',
                color='#1a1a1a')

    for i, t_label in enumerate(transforms):
        x_start = start_x + (i + 1) * (box_w + gap) - gap
        x_end = x_start + gap
        ax.annotate(
            '', xy=(x_end, box_h / 2), xytext=(x_start, box_h / 2),
            arrowprops=dict(arrowstyle='->', color='#333', lw=2.2,
                            connectionstyle='arc3,rad=0')
        )
        ax.text((x_start + x_end) / 2, box_h / 2 + 0.65, t_label,
                ha='center', va='bottom', fontsize=9, color='#444',
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', fc='#FFFDE7',
                          ec='#999', lw=0.8))

    ax.text(7.2, -1.1,
            'gl_Position = projection × view × model × vec4(aPos, 1.0)',
            ha='center', va='center', fontsize=12, fontstyle='italic',
            color='#333',
            bbox=dict(boxstyle='round,pad=0.4', fc='#F5F5F5', ec='#888',
                      lw=1.2))

    fig.suptitle('OpenGL 五大坐标空间变换链', fontsize=16, fontweight='bold',
                 y=0.98, color='#222')
    fig.tight_layout(rect=[0, 0.05, 1, 0.92])
    fig.savefig(os.path.join(OUT_DIR, 'coordinate_spaces.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] coordinate_spaces.png')


# ─────────────────────────────────────────────────────────
# 2. mvp_matrices.png — Model/View/Projection 矩阵说明
# ─────────────────────────────────────────────────────────
def draw_mvp_matrices():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # --- Model 矩阵 ---
    ax = axes[0]
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    ax.set_aspect('equal')
    ax.set_title('Model 矩阵\n(平移 · 旋转 · 缩放)', fontsize=13,
                 fontweight='bold', color='#2E7D32', pad=12)
    ax.axhline(0, color='#ccc', lw=0.8)
    ax.axvline(0, color='#ccc', lw=0.8)
    ax.grid(True, alpha=0.2)

    sq_orig = np.array([[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5], [-.5, -.5]])
    ax.plot(sq_orig[:, 0], sq_orig[:, 1], 'b--', lw=1.5, alpha=0.5, label='原始')

    angle = np.radians(30)
    scale = 1.5
    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle), np.cos(angle)]])
    sq_t = (R @ (sq_orig.T * scale)).T + np.array([1.0, 0.8])
    ax.fill(sq_t[:, 0], sq_t[:, 1], alpha=0.35, color='#4CAF50')
    ax.plot(sq_t[:, 0], sq_t[:, 1], '-', lw=2, color='#2E7D32', label='变换后')
    ax.annotate('', xy=(1.0, 0.8), xytext=(0, 0),
                arrowprops=dict(arrowstyle='->', color='#E65100', lw=2))
    ax.text(0.3, 0.55, '平移', fontsize=9, color='#E65100', fontweight='bold')
    ax.text(1.8, 1.8, '旋转30°\n缩放1.5×', fontsize=9, color='#2E7D32',
            fontweight='bold', ha='center')
    ax.legend(fontsize=9, loc='lower left')
    ax.set_xlabel('X', fontsize=10)
    ax.set_ylabel('Y', fontsize=10)

    # --- View 矩阵 ---
    ax = axes[1]
    ax.set_xlim(-4, 4)
    ax.set_ylim(-3, 4)
    ax.set_aspect('equal')
    ax.set_title('View 矩阵\n(摄像机 / 观察变换)', fontsize=13,
                 fontweight='bold', color='#1565C0', pad=12)
    ax.grid(True, alpha=0.2)

    cube_pts = np.array([[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]])
    ax.fill(cube_pts[:, 0], cube_pts[:, 1], alpha=0.3, color='#42A5F5')
    ax.plot(cube_pts[:, 0], cube_pts[:, 1], '-', lw=2, color='#1565C0')
    ax.text(1.5, 1.5, '物体', ha='center', va='center', fontsize=10,
            fontweight='bold', color='#1565C0')

    cam_x, cam_y = -2.5, -1.5
    cam_body = plt.Polygon(
        [[cam_x - 0.5, cam_y - 0.35], [cam_x + 0.5, cam_y - 0.35],
         [cam_x + 0.5, cam_y + 0.35], [cam_x - 0.5, cam_y + 0.35]],
        fc='#FFF9C4', ec='#F57F17', lw=2
    )
    ax.add_patch(cam_body)
    cam_lens = plt.Polygon(
        [[cam_x + 0.5, cam_y - 0.2], [cam_x + 0.8, cam_y - 0.1],
         [cam_x + 0.8, cam_y + 0.1], [cam_x + 0.5, cam_y + 0.2]],
        fc='#FFE082', ec='#F57F17', lw=2
    )
    ax.add_patch(cam_lens)
    ax.text(cam_x, cam_y + 0.65, '摄像机', ha='center', fontsize=9,
            fontweight='bold', color='#E65100')

    ax.annotate('', xy=(1.0, 1.0), xytext=(cam_x + 0.8, cam_y),
                arrowprops=dict(arrowstyle='->', color='#EF6C00', lw=1.8,
                                linestyle='--'))
    ax.text(-0.3, -0.5, 'lookAt 方向', fontsize=9, color='#EF6C00',
            fontweight='bold', rotation=25)

    ax.text(-2.5, 3.2,
            'glm::lookAt(\n  eye, center, up)',
            fontsize=9, color='#555', family='monospace',
            bbox=dict(boxstyle='round,pad=0.4', fc='#E3F2FD', ec='#90CAF9'))
    ax.set_xlabel('X', fontsize=10)
    ax.set_ylabel('Z', fontsize=10)

    # --- Projection 矩阵 ---
    ax = axes[2]
    ax.set_xlim(-4, 4)
    ax.set_ylim(-1, 6)
    ax.set_aspect('equal')
    ax.set_title('Projection 矩阵\n(透视 / 正交投影)', fontsize=13,
                 fontweight='bold', color='#AD1457', pad=12)
    ax.grid(True, alpha=0.2)

    frustum = np.array([[0, 0], [-2.5, 5], [2.5, 5], [0, 0]])
    ax.fill(frustum[:, 0], frustum[:, 1], alpha=0.15, color='#E91E63')
    ax.plot(frustum[:, 0], frustum[:, 1], '--', lw=1.5, color='#AD1457')

    near_y = 1.2
    hw_near = near_y * 2.5 / 5
    ax.plot([-hw_near, hw_near], [near_y, near_y], '-', lw=2, color='#D81B60')
    ax.text(hw_near + 0.2, near_y, 'near', fontsize=9, color='#AD1457',
            fontweight='bold')

    ax.plot([-2.5, 2.5], [5, 5], '-', lw=2, color='#D81B60')
    ax.text(2.7, 5, 'far', fontsize=9, color='#AD1457', fontweight='bold')

    ax.text(0, 3.2, 'FOV', fontsize=11, ha='center', color='#AD1457',
            fontweight='bold')

    arc = np.linspace(-np.arctan(2.5 / 5), np.arctan(2.5 / 5), 30)
    r_arc = 1.8
    ax.plot(r_arc * np.sin(arc), r_arc * np.cos(arc), '-', color='#E91E63',
            lw=1.5)

    ax.text(0, -0.6, '视点(Eye)', fontsize=9, ha='center', fontweight='bold',
            color='#333')
    ax.plot(0, 0, 'ko', ms=6)

    fig.suptitle('MVP 三大变换矩阵', fontsize=16, fontweight='bold', y=1.02,
                 color='#222')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'mvp_matrices.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] mvp_matrices.png')


# ─────────────────────────────────────────────────────────
# 3. perspective_vs_ortho.png — 透视投影 vs 正交投影对比
# ─────────────────────────────────────────────────────────
def draw_perspective_vs_ortho():
    fig = plt.figure(figsize=(14, 6))

    # --- 透视投影 (左) ---
    ax1 = fig.add_subplot(121, projection='3d')
    ax1.set_title('透视投影 (Perspective)\n近大远小', fontsize=13,
                  fontweight='bold', color='#D84315', pad=15)

    eye = np.array([0, 0, 0])
    near, far = 1.5, 6
    hw_n, hh_n = 0.6, 0.45
    hw_f, hh_f = 2.4, 1.8

    near_pts = np.array([
        [-hw_n, -hh_n, near], [hw_n, -hh_n, near],
        [hw_n, hh_n, near], [-hw_n, hh_n, near]
    ])
    far_pts = np.array([
        [-hw_f, -hh_f, far], [hw_f, -hh_f, far],
        [hw_f, hh_f, far], [-hw_f, hh_f, far]
    ])

    verts_near = [list(near_pts)]
    verts_far = [list(far_pts)]
    ax1.add_collection3d(Poly3DCollection(verts_near, alpha=0.25,
                                          facecolor='#FFAB91',
                                          edgecolor='#BF360C', lw=1.5))
    ax1.add_collection3d(Poly3DCollection(verts_far, alpha=0.15,
                                          facecolor='#FFAB91',
                                          edgecolor='#BF360C', lw=1.5))

    for i in range(4):
        ax1.plot([near_pts[i, 0], far_pts[i, 0]],
                 [near_pts[i, 1], far_pts[i, 1]],
                 [near_pts[i, 2], far_pts[i, 2]],
                 '--', color='#E64A19', lw=1, alpha=0.7)
        ax1.plot([0, near_pts[i, 0]], [0, near_pts[i, 1]],
                 [0, near_pts[i, 2]],
                 ':', color='#999', lw=0.8)

    sizes = [1.2, 1.2, 1.2]
    positions_z = [2.0, 3.5, 5.0]
    colors_cube = ['#42A5F5', '#66BB6A', '#FFA726']
    for s, z, c in zip(sizes, positions_z, colors_cube):
        ratio = z / far
        vis_s = s * (1 - ratio * 0.5)
        hs = vis_s * 0.3
        cube_face = np.array([[-hs, -hs, z], [hs, -hs, z],
                              [hs, hs, z], [-hs, hs, z]])
        ax1.add_collection3d(Poly3DCollection(
            [list(cube_face)], alpha=0.6, facecolor=c, edgecolor='#333', lw=1
        ))

    ax1.scatter([0], [0], [0], color='red', s=60, zorder=5)
    ax1.text(0, 0.3, -0.3, '视点', fontsize=9, color='red', fontweight='bold')
    ax1.text(0, -hh_n - 0.15, near, 'Near', fontsize=8, color='#BF360C')
    ax1.text(0, -hh_f - 0.3, far, 'Far', fontsize=8, color='#BF360C')

    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    ax1.set_zlabel('Z')
    ax1.view_init(elev=18, azim=-60)
    ax1.set_xlim(-3, 3)
    ax1.set_ylim(-2.5, 2.5)
    ax1.set_zlim(0, 7)

    # --- 正交投影 (右) ---
    ax2 = fig.add_subplot(122, projection='3d')
    ax2.set_title('正交投影 (Orthographic)\n平行投影，无近大远小', fontsize=13,
                  fontweight='bold', color='#1565C0', pad=15)

    hw, hh = 2.0, 1.5
    near_o, far_o = 1.0, 6.0
    box_pts_near = np.array([
        [-hw, -hh, near_o], [hw, -hh, near_o],
        [hw, hh, near_o], [-hw, hh, near_o]
    ])
    box_pts_far = np.array([
        [-hw, -hh, far_o], [hw, -hh, far_o],
        [hw, hh, far_o], [-hw, hh, far_o]
    ])

    ax2.add_collection3d(Poly3DCollection(
        [list(box_pts_near)], alpha=0.2, facecolor='#90CAF9',
        edgecolor='#1565C0', lw=1.5
    ))
    ax2.add_collection3d(Poly3DCollection(
        [list(box_pts_far)], alpha=0.12, facecolor='#90CAF9',
        edgecolor='#1565C0', lw=1.5
    ))
    for i in range(4):
        ax2.plot([box_pts_near[i, 0], box_pts_far[i, 0]],
                 [box_pts_near[i, 1], box_pts_far[i, 1]],
                 [box_pts_near[i, 2], box_pts_far[i, 2]],
                 '--', color='#1976D2', lw=1, alpha=0.6)

    for s, z, c in zip(sizes, positions_z, colors_cube):
        hs = s * 0.3
        cube_face = np.array([[-hs, -hs, z], [hs, -hs, z],
                              [hs, hs, z], [-hs, hs, z]])
        ax2.add_collection3d(Poly3DCollection(
            [list(cube_face)], alpha=0.6, facecolor=c, edgecolor='#333', lw=1
        ))

    ax2.text(0, -hh - 0.2, near_o, 'Near', fontsize=8, color='#1565C0')
    ax2.text(0, -hh - 0.2, far_o, 'Far', fontsize=8, color='#1565C0')

    arrows_x = [-hw + 0.3, hw - 0.3]
    for ax_val in arrows_x:
        ax2.plot([ax_val, ax_val], [0, 0], [near_o, far_o],
                 '->', color='#999', lw=0.8, alpha=0.5)

    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    ax2.set_zlabel('Z')
    ax2.view_init(elev=18, azim=-60)
    ax2.set_xlim(-3, 3)
    ax2.set_ylim(-2.5, 2.5)
    ax2.set_zlim(0, 7)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'perspective_vs_ortho.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] perspective_vs_ortho.png')


# ─────────────────────────────────────────────────────────
# 4. depth_buffer.png — 深度测试原理示意图
# ─────────────────────────────────────────────────────────
def draw_depth_buffer():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # --- 左：侧视图展示遮挡关系 ---
    ax = axes[0]
    ax.set_xlim(-1, 6)
    ax.set_ylim(-1, 4)
    ax.set_aspect('equal')
    ax.set_title('① 场景侧视图', fontsize=12, fontweight='bold', color='#333')
    ax.grid(True, alpha=0.15)

    eye_x, eye_y = -0.3, 1.5
    ax.plot(eye_x, eye_y, 'ko', ms=8)
    ax.text(eye_x, eye_y + 0.35, '视点', ha='center', fontsize=9,
            fontweight='bold')

    rect_a = plt.Rectangle((2, 0.5), 1.0, 2.0, fc='#42A5F5', ec='#1565C0',
                            lw=2, alpha=0.8, zorder=3)
    ax.add_patch(rect_a)
    ax.text(2.5, 1.5, 'A', ha='center', va='center', fontsize=14,
            fontweight='bold', color='white', zorder=4)
    ax.text(2.5, -0.1, 'z=0.3', ha='center', fontsize=9, color='#1565C0',
            fontweight='bold')

    rect_b = plt.Rectangle((3.5, 0.2), 1.2, 2.5, fc='#EF5350', ec='#C62828',
                            lw=2, alpha=0.7, zorder=2)
    ax.add_patch(rect_b)
    ax.text(4.1, 1.45, 'B', ha='center', va='center', fontsize=14,
            fontweight='bold', color='white', zorder=4)
    ax.text(4.1, -0.1, 'z=0.7', ha='center', fontsize=9, color='#C62828',
            fontweight='bold')

    ax.annotate('', xy=(2, 1.5), xytext=(eye_x, eye_y),
                arrowprops=dict(arrowstyle='->', color='#666', lw=1.5))
    ax.set_xlabel('深度方向 (Z) →', fontsize=10)
    ax.set_ylabel('Y', fontsize=10)

    # --- 中：深度缓冲 ---
    ax = axes[1]
    ax.set_title('② 深度缓冲 (Depth Buffer)', fontsize=12, fontweight='bold',
                 color='#333')
    grid_size = 8
    depth_data = np.ones((grid_size, grid_size)) * 0.95

    depth_data[1:6, 2:5] = 0.7
    depth_data[2:5, 1:4] = 0.3

    im = ax.imshow(depth_data, cmap='gray_r', vmin=0, vmax=1,
                   interpolation='nearest')
    ax.set_xticks(range(grid_size))
    ax.set_yticks(range(grid_size))
    ax.grid(True, color='#999', lw=0.5)

    for i in range(grid_size):
        for j in range(grid_size):
            val = depth_data[i, j]
            color = 'white' if val > 0.5 else '#333'
            ax.text(j, i, f'{val:.1f}', ha='center', va='center',
                    fontsize=7, color=color, fontweight='bold')

    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='深度值 (0=近, 1=远)')
    ax.set_xlabel('像素 X', fontsize=10)
    ax.set_ylabel('像素 Y', fontsize=10)

    # --- 右：深度测试流程 ---
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('③ 深度测试流程', fontsize=12, fontweight='bold', color='#333')

    flow_items = [
        (5, 9.0, '片段进入', '#E3F2FD', '#1565C0'),
        (5, 7.2, '比较片段深度\n与缓冲区深度', '#FFF3E0', '#E65100'),
        (5, 4.7, '片段深度 <\n缓冲区深度？', '#FCE4EC', '#C62828'),
        (2.5, 2.5, '写入颜色缓冲\n更新深度缓冲', '#E8F5E9', '#2E7D32'),
        (7.5, 2.5, '丢弃片段', '#FFEBEE', '#C62828'),
    ]

    box_w_flow, box_h_flow = 3.2, 1.2
    for i, (x, y, text, fc, ec) in enumerate(flow_items):
        bw = box_w_flow if i != 4 else 2.4
        bh = box_h_flow
        if i == 2:
            diamond = plt.Polygon(
                [[x, y + bh / 2 + 0.2], [x + bw / 2 + 0.2, y],
                 [x, y - bh / 2 - 0.2], [x - bw / 2 - 0.2, y]],
                fc=fc, ec=ec, lw=2
            )
            ax.add_patch(diamond)
            ax.text(x, y, text, ha='center', va='center', fontsize=8.5,
                    fontweight='bold', color=ec)
        else:
            box = FancyBboxPatch(
                (x - bw / 2, y - bh / 2), bw, bh,
                boxstyle="round,pad=0.15", facecolor=fc, edgecolor=ec, lw=2
            )
            ax.add_patch(box)
            ax.text(x, y, text, ha='center', va='center', fontsize=9,
                    fontweight='bold', color=ec)

    ax.annotate('', xy=(5, 7.8), xytext=(5, 8.4),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.8))
    ax.annotate('', xy=(5, 5.9), xytext=(5, 6.6),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.8))
    ax.annotate('', xy=(2.5, 3.5), xytext=(3.8, 4.5),
                arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=1.8))
    ax.text(2.8, 4.2, '是', fontsize=10, color='#2E7D32', fontweight='bold')
    ax.annotate('', xy=(7.5, 3.5), xytext=(6.2, 4.5),
                arrowprops=dict(arrowstyle='->', color='#C62828', lw=1.8))
    ax.text(6.8, 4.2, '否', fontsize=10, color='#C62828', fontweight='bold')

    fig.suptitle('深度测试 (Depth Test) 原理', fontsize=16, fontweight='bold',
                 y=1.02, color='#222')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'depth_buffer.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] depth_buffer.png')


# ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('正在生成第5篇插图...')
    draw_coordinate_spaces()
    draw_mvp_matrices()
    draw_perspective_vs_ortho()
    draw_depth_buffer()
    print('全部完成！')
