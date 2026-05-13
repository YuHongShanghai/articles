#!/usr/bin/env python3
"""
生成第06篇「摄像机系统」所需的示意图：
  1. camera_vectors.png  — 摄像机向量示意图
  2. euler_angles.png    — 欧拉角（Yaw / Pitch）示意图
  3. lookat_matrix.png   — LookAt 矩阵构成示意图
"""

import sys

_user_mpl = '/home/yh/.local/lib/python3.10/site-packages'

# Must fix mpl_toolkits path BEFORE matplotlib loads its projections
import mpl_toolkits
mpl_toolkits.__path__ = [_user_mpl + '/mpl_toolkits']

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 150


def draw_arrow_3d(ax, origin, direction, color, label, fontsize=11):
    """在 3D 坐标系中绘制一个带标签的箭头。"""
    o = np.array(origin)
    d = np.array(direction)
    ax.quiver(*o, *d, color=color, arrow_length_ratio=0.12,
              linewidth=2.5, zorder=5)
    tip = o + d
    ax.text(tip[0], tip[1], tip[2], f'  {label}',
            color=color, fontsize=fontsize, fontweight='bold', zorder=6)


# ═══════════════════════════════════════════════════════
# 图 1：摄像机向量示意图
# ═══════════════════════════════════════════════════════
def generate_camera_vectors():
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection='3d')

    pos = np.array([0.0, 0.0, 0.0])
    front = np.array([0.0, 0.0, -1.0])
    up    = np.array([0.0, 1.0,  0.0])
    right = np.array([1.0, 0.0,  0.0])
    target = pos + front * 2.5

    draw_arrow_3d(ax, pos, front * 2.0,  '#E74C3C', 'Front (前方向)')
    draw_arrow_3d(ax, pos, up * 1.3,     '#27AE60', 'Up (上向量)')
    draw_arrow_3d(ax, pos, right * 1.3,  '#2980B9', 'Right (右向量)')

    ax.scatter(*pos, color='#F39C12', s=120, zorder=10,
              edgecolors='black', linewidths=1.2)
    ax.text(pos[0] - 0.15, pos[1] - 0.25, pos[2] + 0.1,
            'Position\n(摄像机位置)', fontsize=10, color='#F39C12',
            fontweight='bold')

    ax.scatter(*target, color='#E74C3C', s=60, zorder=10,
              marker='x', linewidths=2)
    ax.text(target[0] + 0.1, target[1] + 0.1, target[2],
            'Target (目标点)', fontsize=9, color='#E74C3C')

    lim = 2.5
    ax.set_xlim([-lim, lim])
    ax.set_ylim([-lim, lim])
    ax.set_zlim([-lim, lim])
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('摄像机坐标系向量关系', fontsize=14, fontweight='bold', pad=15)
    ax.view_init(elev=22, azim=-55)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'camera_vectors.png')
    plt.savefig(out, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'[OK] {out}')


# ═══════════════════════════════════════════════════════
# 图 2：欧拉角（Yaw / Pitch）示意图
# ═══════════════════════════════════════════════════════
def generate_euler_angles():
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection='3d')

    yaw_deg = -45
    pitch_deg = 25
    yaw = np.radians(yaw_deg)
    pitch = np.radians(pitch_deg)

    front_xz = np.array([np.cos(yaw), 0.0, np.sin(yaw)])
    front = np.array([
        np.cos(yaw) * np.cos(pitch),
        np.sin(pitch),
        np.sin(yaw) * np.cos(pitch)
    ])

    origin = np.array([0.0, 0.0, 0.0])

    draw_arrow_3d(ax, origin, front * 2.0, '#E74C3C', 'Front 方向')
    draw_arrow_3d(ax, origin, front_xz * 1.8, '#95A5A6', 'XZ 投影')

    theta_yaw = np.linspace(0, yaw, 40)
    r_arc = 0.9
    arc_x = r_arc * np.cos(theta_yaw)
    arc_z = r_arc * np.sin(theta_yaw)
    arc_y = np.zeros_like(theta_yaw)
    ax.plot(arc_x, arc_y, arc_z, color='#2980B9', linewidth=2.5)
    mid_yaw = yaw / 2
    ax.text(r_arc * np.cos(mid_yaw) + 0.15, -0.15,
            r_arc * np.sin(mid_yaw),
            f'Yaw ({yaw_deg}°)', color='#2980B9', fontsize=11,
            fontweight='bold')

    theta_pitch = np.linspace(0, pitch, 30)
    arc_p_x = r_arc * np.cos(yaw) * np.cos(theta_pitch)
    arc_p_y = r_arc * np.sin(theta_pitch)
    arc_p_z = r_arc * np.sin(yaw) * np.cos(theta_pitch)
    ax.plot(arc_p_x, arc_p_y, arc_p_z, color='#27AE60', linewidth=2.5)
    mid_pitch = pitch / 2
    ax.text(r_arc * np.cos(yaw) * np.cos(mid_pitch) + 0.1,
            r_arc * np.sin(mid_pitch) + 0.12,
            r_arc * np.sin(yaw) * np.cos(mid_pitch),
            f'Pitch ({pitch_deg}°)', color='#27AE60', fontsize=11,
            fontweight='bold')

    axis_len = 2.2
    for vec, lbl, c in [([axis_len, 0, 0], '+X', '#888'),
                         ([0, axis_len, 0], '+Y', '#888'),
                         ([0, 0, axis_len], '+Z', '#888')]:
        ax.quiver(0, 0, 0, *vec, color=c, arrow_length_ratio=0.05,
                  linewidth=1.0, alpha=0.5)
        ax.text(vec[0]*1.08, vec[1]*1.08, vec[2]*1.08, lbl,
                color=c, fontsize=9)

    ax.scatter(*origin, color='#F39C12', s=100, zorder=10)

    lim = 2.5
    ax.set_xlim([-lim, lim])
    ax.set_ylim([-lim, lim])
    ax.set_zlim([-lim, lim])
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('欧拉角 Yaw（偏航）与 Pitch（俯仰）', fontsize=14,
                 fontweight='bold', pad=15)
    ax.view_init(elev=20, azim=-50)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'euler_angles.png')
    plt.savefig(out, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'[OK] {out}')


# ═══════════════════════════════════════════════════════
# 图 3：LookAt 矩阵构成示意图（2D 矩阵可视化）
# ═══════════════════════════════════════════════════════
def generate_lookat_matrix():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-1.5, 6.5)
    ax.set_aspect('equal')
    ax.axis('off')

    box_w, box_h = 1.2, 0.8

    def draw_matrix(ax, x0, y0, data, title, title_color='#2C3E50'):
        rows = len(data)
        cols = len(data[0])
        total_w = cols * box_w
        total_h = rows * box_h

        ax.text(x0 + total_w / 2, y0 + total_h + 0.35, title,
                ha='center', va='bottom', fontsize=13,
                fontweight='bold', color=title_color)

        bracket_lw = 2.5
        bk = 0.15
        ax.plot([x0 - bk, x0 - bk], [y0 - bk, y0 + total_h + bk],
                color='#2C3E50', lw=bracket_lw)
        ax.plot([x0 - bk, x0 + 0.15], [y0 - bk, y0 - bk],
                color='#2C3E50', lw=bracket_lw)
        ax.plot([x0 - bk, x0 + 0.15], [y0 + total_h + bk, y0 + total_h + bk],
                color='#2C3E50', lw=bracket_lw)

        rx = x0 + total_w
        ax.plot([rx + bk, rx + bk], [y0 - bk, y0 + total_h + bk],
                color='#2C3E50', lw=bracket_lw)
        ax.plot([rx + bk, rx - 0.15], [y0 - bk, y0 - bk],
                color='#2C3E50', lw=bracket_lw)
        ax.plot([rx + bk, rx - 0.15], [y0 + total_h + bk, y0 + total_h + bk],
                color='#2C3E50', lw=bracket_lw)

        colors_row = ['#FADBD8', '#D5F5E3', '#D6EAF8', '#F9E79F']
        for r in range(rows):
            for c in range(cols):
                cx = x0 + c * box_w + box_w / 2
                cy = y0 + (rows - 1 - r) * box_h + box_h / 2
                fc = colors_row[r] if r < len(colors_row) else '#F0F0F0'
                rect = plt.Rectangle(
                    (cx - box_w/2 + 0.02, cy - box_h/2 + 0.02),
                    box_w - 0.04, box_h - 0.04,
                    facecolor=fc, edgecolor='#AAB7B8',
                    linewidth=1, zorder=3, alpha=0.85)
                ax.add_patch(rect)
                ax.text(cx, cy, data[r][c], ha='center', va='center',
                        fontsize=9, fontweight='bold', color='#2C3E50',
                        zorder=4)

    rotation_data = [
        ['Rx', 'Ry', 'Rz', '0'],
        ['Ux', 'Uy', 'Uz', '0'],
        ['Dx', 'Dy', 'Dz', '0'],
        ['0',  '0',  '0',  '1'],
    ]

    translation_data = [
        ['1', '0', '0', '-Px'],
        ['0', '1', '0', '-Py'],
        ['0', '0', '1', '-Pz'],
        ['0', '0', '0', '1'],
    ]

    draw_matrix(ax, 0.3, 1.0, rotation_data,
                '旋转矩阵 (方向对齐)', '#E74C3C')

    ax.text(5.35, 3.2, '×', ha='center', va='center', fontsize=22,
            fontweight='bold', color='#7F8C8D')

    draw_matrix(ax, 5.8, 1.0, translation_data,
                '平移矩阵 (移到原点)', '#2980B9')

    ax.text(0.3, 0.15,
            'R = Right 向量    U = Up 向量    D = Direction (Front的反方向)    P = 摄像机位置',
            fontsize=9, color='#7F8C8D', style='italic')

    ax.set_title('LookAt 矩阵 = 旋转 × 平移', fontsize=15,
                 fontweight='bold', pad=20, color='#2C3E50')

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'lookat_matrix.png')
    plt.savefig(out, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'[OK] {out}')


if __name__ == '__main__':
    print('正在生成插图...')
    generate_camera_vectors()
    generate_euler_angles()
    generate_lookat_matrix()
    print('全部完成！')
