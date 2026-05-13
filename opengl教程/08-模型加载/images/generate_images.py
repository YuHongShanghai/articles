#!/usr/bin/env python3
"""生成第8篇「模型加载」配套插图。"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

DPI = 150
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def draw_assimp_structure():
    """Assimp 数据结构树形图"""
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(-1, 15)
    ax.set_ylim(-1, 10)
    ax.axis('off')

    def box(x, y, w, h, label, fc, ec, fontsize=10, bold=True):
        b = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.12",
            facecolor=fc, edgecolor=ec, linewidth=2, alpha=0.92, zorder=3
        )
        ax.add_patch(b)
        fw = 'bold' if bold else 'normal'
        ax.text(x + w / 2, y + h / 2, label,
                ha='center', va='center', fontsize=fontsize,
                fontweight=fw, color='#1a1a1a', zorder=4)
        return (x + w / 2, y, x + w / 2, y + h)

    def arrow(x1, y1, x2, y2, color='#555'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.8,
                                    connectionstyle='arc3,rad=0'))

    # aiScene
    box(5.5, 8.2, 3.0, 1.0, 'aiScene\n(场景根节点)', '#BBDEFB', '#1565C0', 12)
    scene_cx = 5.5 + 1.5

    # mRootNode
    box(0.5, 5.8, 3.0, 1.2, 'mRootNode\n(根节点)', '#C8E6C9', '#2E7D32', 10)
    node_cx = 0.5 + 1.5
    arrow(scene_cx, 8.2, node_cx, 7.0)

    # mMeshes array
    box(5.0, 5.8, 4.0, 1.2, 'mMeshes[]\n(所有网格数据)', '#FFE0B2', '#E65100', 10)
    mesh_cx = 5.0 + 2.0
    arrow(scene_cx, 8.2, mesh_cx, 7.0)

    # mMaterials array
    box(10.5, 5.8, 3.5, 1.2, 'mMaterials[]\n(所有材质)', '#E1BEE7', '#7B1FA2', 10)
    mat_cx = 10.5 + 1.75
    arrow(scene_cx, 8.2, mat_cx, 7.0)

    # Node children
    box(0.0, 3.2, 2.0, 1.0, '子节点 A', '#E8F5E9', '#43A047', 9, False)
    arrow(node_cx, 5.8, 1.0, 4.2)
    box(2.5, 3.2, 2.0, 1.0, '子节点 B', '#E8F5E9', '#43A047', 9, False)
    arrow(node_cx, 5.8, 3.5, 4.2)

    ax.text(1.0, 2.5, 'mMeshes[]\n(网格索引)', fontsize=8, ha='center',
            color='#666', style='italic')
    ax.text(3.5, 2.5, 'mMeshes[]\n(网格索引)', fontsize=8, ha='center',
            color='#666', style='italic')

    # Mesh details
    details = [
        ('mVertices[]\n顶点位置', '#FFF3E0', '#EF6C00'),
        ('mNormals[]\n法线', '#FFF3E0', '#EF6C00'),
        ('mTexCoords[]\n纹理坐标', '#FFF3E0', '#EF6C00'),
        ('mFaces[]\n面索引', '#FFF3E0', '#EF6C00'),
    ]
    mesh_cx = 5.0
    for i, (label, fc, ec) in enumerate(details):
        bx = mesh_cx + i * 1.1 - 0.2
        by = 3.5
        b = FancyBboxPatch(
            (bx, by), 1.0, 1.4, boxstyle="round,pad=0.08",
            facecolor=fc, edgecolor=ec, linewidth=1.2, alpha=0.85, zorder=3
        )
        ax.add_patch(b)
        ax.text(bx + 0.5, by + 0.7, label, ha='center', va='center',
                fontsize=7, color='#333', zorder=4)
        arrow(mesh_cx, 5.8, bx + 0.5, by + 1.4)

    # mMaterialIndex arrow
    ax.annotate('mMaterialIndex',
                xy=(mat_cx, 7.0), xytext=(mesh_cx + 2.0, 5.0),
                fontsize=8, color='#7B1FA2', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#7B1FA2', lw=1.5,
                                linestyle='--', connectionstyle='arc3,rad=-0.2'))

    # Material details
    mat_details = [
        ('漫反射贴图\n路径', '#F3E5F5', '#8E24AA'),
        ('镜面反射贴图\n路径', '#F3E5F5', '#8E24AA'),
        ('材质属性', '#F3E5F5', '#8E24AA'),
    ]
    for i, (label, fc, ec) in enumerate(mat_details):
        bx = 10.2 + i * 1.3
        by = 3.5
        b = FancyBboxPatch(
            (bx, by), 1.2, 1.4, boxstyle="round,pad=0.08",
            facecolor=fc, edgecolor=ec, linewidth=1.2, alpha=0.85, zorder=3
        )
        ax.add_patch(b)
        ax.text(bx + 0.6, by + 0.7, label, ha='center', va='center',
                fontsize=7, color='#333', zorder=4)
        arrow(mat_cx, 5.8, bx + 0.6, by + 1.4)

    # Legend
    legend_items = [
        ('Scene (顶层容器)', '#BBDEFB'),
        ('Node (树形节点)', '#C8E6C9'),
        ('Mesh (网格数据)', '#FFE0B2'),
        ('Material (材质)', '#E1BEE7'),
    ]
    for i, (text, color) in enumerate(legend_items):
        lx, ly = 0.5 + i * 3.5, -0.5
        rect = plt.Rectangle((lx, ly), 0.4, 0.4, fc=color, ec='#666', lw=1)
        ax.add_patch(rect)
        ax.text(lx + 0.55, ly + 0.2, text, fontsize=8, va='center', color='#333')

    fig.suptitle('Assimp 数据结构总览', fontsize=16, fontweight='bold',
                 y=0.96, color='#222')
    fig.tight_layout(rect=[0, 0.02, 1, 0.93])
    fig.savefig(os.path.join(OUT_DIR, 'assimp_structure.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] assimp_structure.png')


# ─────────────────────────────────────────────────────────
# 2. model_loading_flow.png — 模型加载流程图
# ─────────────────────────────────────────────────────────
def draw_model_loading_flow():
    """模型加载流程图"""
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_xlim(-0.5, 12.5)
    ax.set_ylim(-0.5, 4.5)
    ax.axis('off')

    steps = [
        ('读取模型文件\n(.obj/.fbx/.gltf)', '#E3F2FD', '#1565C0'),
        ('Assimp 解析\n→ aiScene', '#E8F5E9', '#2E7D32'),
        ('递归遍历\naiNode 树', '#FFF3E0', '#E65100'),
        ('提取 Mesh 数据\n顶点/法线/UV/索引', '#FCE4EC', '#C62828'),
        ('加载材质纹理\n(带缓存去重)', '#F3E5F5', '#7B1FA2'),
        ('上传到 GPU\nVAO/VBO/EBO', '#E0F7FA', '#00838F'),
    ]

    bw, bh = 1.7, 1.5
    gap = 0.3

    for i, (label, fc, ec) in enumerate(steps):
        x = i * (bw + gap)
        b = FancyBboxPatch(
            (x, 1.2), bw, bh, boxstyle="round,pad=0.12",
            facecolor=fc, edgecolor=ec, linewidth=2, alpha=0.92, zorder=3
        )
        ax.add_patch(b)
        ax.text(x + bw / 2, 1.2 + bh / 2, label,
                ha='center', va='center', fontsize=9,
                fontweight='bold', color='#1a1a1a', zorder=4)
        ax.text(x + bw / 2, 0.7, f'Step {i + 1}', ha='center',
                fontsize=8, color='#888')

        if i < len(steps) - 1:
            ax.annotate('', xy=(x + bw + gap, 1.2 + bh / 2),
                        xytext=(x + bw, 1.2 + bh / 2),
                        arrowprops=dict(arrowstyle='->', color='#555',
                                        lw=2))

    fig.suptitle('模型加载流程', fontsize=15, fontweight='bold',
                 y=0.95, color='#222')
    fig.tight_layout(rect=[0, 0.05, 1, 0.90])
    fig.savefig(os.path.join(OUT_DIR, 'model_loading_flow.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] model_loading_flow.png')


# ─────────────────────────────────────────────────────────
# 3. texture_cache.png — 纹理缓存去重示意图
# ─────────────────────────────────────────────────────────
def draw_texture_cache():
    """纹理缓存去重机制"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-0.5, 7)
    ax.axis('off')

    def rbox(x, y, w, h, label, fc, ec, fs=9):
        b = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1",
            facecolor=fc, edgecolor=ec, linewidth=1.8, alpha=0.9, zorder=3
        )
        ax.add_patch(b)
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center',
                fontsize=fs, fontweight='bold', color='#1a1a1a', zorder=4)

    # Meshes
    rbox(0, 5.5, 2.0, 1.0, 'Mesh A\n需要 diffuse.jpg', '#E3F2FD', '#1565C0')
    rbox(0, 3.8, 2.0, 1.0, 'Mesh B\n需要 diffuse.jpg', '#E3F2FD', '#1565C0')
    rbox(0, 2.1, 2.0, 1.0, 'Mesh C\n需要 specular.jpg', '#E3F2FD', '#1565C0')

    # Cache
    rbox(4.0, 3.5, 2.5, 2.5, 'textures_loaded\n(纹理缓存)\n\n① diffuse.jpg\n② specular.jpg',
         '#FFF9C4', '#F9A825', 9)

    # GPU
    rbox(8.0, 4.0, 2.0, 1.5, 'GPU 显存\n\nTexID: 1\nTexID: 2',
         '#E8F5E9', '#2E7D32', 9)

    # Arrows
    ax.annotate('查询', xy=(4.0, 6.0), xytext=(2.0, 6.0),
                arrowprops=dict(arrowstyle='->', color='#1565C0', lw=1.5),
                fontsize=8, color='#1565C0', va='center')
    ax.annotate('命中！复用', xy=(4.0, 4.3), xytext=(2.0, 4.3),
                arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=1.5),
                fontsize=8, color='#2E7D32', va='center')
    ax.annotate('未命中→加载', xy=(4.0, 2.6), xytext=(2.0, 2.6),
                arrowprops=dict(arrowstyle='->', color='#E65100', lw=1.5),
                fontsize=8, color='#E65100', va='center')

    ax.annotate('上传', xy=(8.0, 4.75), xytext=(6.5, 4.75),
                arrowprops=dict(arrowstyle='->', color='#555', lw=1.5),
                fontsize=8, color='#555', va='center')

    # Explanation
    ax.text(5.0, 0.8,
            '相同路径的纹理只加载一次，后续 Mesh 直接复用已有的 OpenGL 纹理 ID',
            ha='center', fontsize=9, color='#666', style='italic',
            bbox=dict(boxstyle='round,pad=0.4', fc='#F5F5F5', ec='#CCC'))

    fig.suptitle('纹理缓存去重机制', fontsize=14, fontweight='bold',
                 y=0.97, color='#222')
    fig.tight_layout(rect=[0, 0.02, 1, 0.93])
    fig.savefig(os.path.join(OUT_DIR, 'texture_cache.png'), dpi=DPI,
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('[✓] texture_cache.png')


if __name__ == '__main__':
    print('正在生成第8篇插图...')
    draw_assimp_structure()
    draw_model_loading_flow()
    draw_texture_cache()
    print('全部完成！')
