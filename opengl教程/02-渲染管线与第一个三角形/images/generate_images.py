"""
生成第2篇教程所需的插图：
  1. pipeline.png        — OpenGL 渲染管线流程图
  2. vbo_vao_ebo.png     — VBO / VAO / EBO 关系示意图
  3. vertex_attributes.png — 顶点属性交错布局示意图

使用方法:
    python generate_images.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 150


def draw_pipeline():
    """渲染管线流程图"""
    fig, ax = plt.subplots(figsize=(14, 3.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 3.5)
    ax.axis('off')
    fig.patch.set_facecolor('#FAFAFA')

    stages = [
        ("顶点数据",     "#B0BEC5", 0.5),
        ("顶点着色器",   "#42A5F5", 2.5),
        ("图元装配",     "#66BB6A", 4.5),
        ("光栅化",       "#FFA726", 6.5),
        ("片段着色器",   "#EF5350", 8.5),
        ("测试与混合",   "#AB47BC", 10.5),
        ("帧缓冲",       "#78909C", 12.5),
    ]

    box_w, box_h = 1.7, 1.4
    y_center = 1.75

    for label, color, x in stages:
        is_programmable = label in ("顶点着色器", "片段着色器")
        edgecolor = '#1565C0' if is_programmable else '#616161'
        linewidth = 2.5 if is_programmable else 1.2

        box = FancyBboxPatch(
            (x - box_w / 2, y_center - box_h / 2),
            box_w, box_h,
            boxstyle="round,pad=0.1",
            facecolor=color, edgecolor=edgecolor,
            linewidth=linewidth, alpha=0.92
        )
        ax.add_patch(box)

        ax.text(x, y_center, label,
                ha='center', va='center', fontsize=11,
                fontweight='bold', color='white')

        if is_programmable:
            ax.text(x, y_center - box_h / 2 - 0.22, "★ 可编程",
                    ha='center', va='top', fontsize=8,
                    color='#1565C0', fontweight='bold')

    for i in range(len(stages) - 1):
        x_start = stages[i][2] + box_w / 2
        x_end = stages[i + 1][2] - box_w / 2
        ax.annotate('', xy=(x_end, y_center), xytext=(x_start, y_center),
                    arrowprops=dict(arrowstyle='->', color='#424242',
                                   lw=2, connectionstyle='arc3,rad=0'))

    ax.set_title('OpenGL 可编程渲染管线', fontsize=15, fontweight='bold',
                 pad=15, color='#212121')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'pipeline.png')
    plt.savefig(path, dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"已生成: {path}")


def draw_vbo_vao_ebo():
    """VBO / VAO / EBO 关系示意图"""
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor('#FAFAFA')

    # --- VAO 外框 ---
    vao_rect = FancyBboxPatch(
        (1, 0.8), 10, 5.4,
        boxstyle="round,pad=0.15",
        facecolor='#E3F2FD', edgecolor='#1565C0',
        linewidth=2.5, alpha=0.6
    )
    ax.add_patch(vao_rect)
    ax.text(6, 6.0, 'VAO（顶点数组对象）', ha='center', va='center',
            fontsize=14, fontweight='bold', color='#1565C0')
    ax.text(6, 5.55, '记录所有顶点属性配置状态', ha='center', va='center',
            fontsize=9, color='#1565C0', style='italic')

    # --- VBO ---
    vbo_rect = FancyBboxPatch(
        (1.5, 3.5), 9, 1.5,
        boxstyle="round,pad=0.1",
        facecolor='#C8E6C9', edgecolor='#2E7D32',
        linewidth=2
    )
    ax.add_patch(vbo_rect)
    ax.text(6, 4.65, 'VBO（顶点缓冲对象）— GL_ARRAY_BUFFER', ha='center', va='center',
            fontsize=11, fontweight='bold', color='#1B5E20')

    vbo_data = [
        ("x₀", "#A5D6A7"), ("y₀", "#A5D6A7"), ("z₀", "#A5D6A7"),
        ("r₀", "#FFCC80"), ("g₀", "#FFCC80"), ("b₀", "#FFCC80"),
        ("x₁", "#A5D6A7"), ("y₁", "#A5D6A7"), ("z₁", "#A5D6A7"),
        ("r₁", "#FFCC80"), ("g₁", "#FFCC80"), ("b₁", "#FFCC80"),
    ]

    cell_w = 0.7
    start_x = 1.8
    for i, (label, color) in enumerate(vbo_data):
        x = start_x + i * cell_w
        rect = plt.Rectangle((x, 3.65), cell_w - 0.05, 0.65,
                              facecolor=color, edgecolor='#616161', linewidth=0.8)
        ax.add_patch(rect)
        ax.text(x + cell_w / 2 - 0.025, 3.97, label,
                ha='center', va='center', fontsize=8, fontweight='bold')

    ax.text(4.15, 3.35, '位置 (vec3)', ha='center', va='center',
            fontsize=8, color='#2E7D32', fontweight='bold')
    ax.text(6.25, 3.35, '颜色 (vec3)', ha='center', va='center',
            fontsize=8, color='#E65100', fontweight='bold')
    ax.text(9.0, 3.35, '...', ha='center', va='center',
            fontsize=10, color='#616161')

    # --- 顶点属性指针 ---
    attr_y = 2.3
    attr_labels = [
        ("属性 0: 位置", "glVertexAttribPointer(0, 3, ..., stride=24, offset=0)"),
        ("属性 1: 颜色", "glVertexAttribPointer(1, 3, ..., stride=24, offset=12)"),
    ]
    for i, (name, detail) in enumerate(attr_labels):
        y = attr_y - i * 0.65
        box = FancyBboxPatch(
            (2.0, y - 0.2), 8.0, 0.5,
            boxstyle="round,pad=0.05",
            facecolor='#FFF9C4', edgecolor='#F9A825', linewidth=1.2
        )
        ax.add_patch(box)
        ax.text(6, y + 0.05, f'{name}:  {detail}',
                ha='center', va='center', fontsize=8.5, fontweight='bold',
                color='#5D4037')

    # --- EBO ---
    ebo_rect = FancyBboxPatch(
        (2.5, 0.9), 7, 0.65,
        boxstyle="round,pad=0.08",
        facecolor='#F8BBD0', edgecolor='#C2185B',
        linewidth=2
    )
    ax.add_patch(ebo_rect)
    ax.text(6, 1.22, 'EBO（索引缓冲对象）— GL_ELEMENT_ARRAY_BUFFER:  [ 0, 1, 3, 1, 2, 3 ]',
            ha='center', va='center', fontsize=9, fontweight='bold', color='#880E4F')

    ax.set_title('VBO / VAO / EBO 关系示意图', fontsize=15, fontweight='bold',
                 pad=15, color='#212121')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'vbo_vao_ebo.png')
    plt.savefig(path, dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"已生成: {path}")


def draw_vertex_attributes():
    """顶点属性交错布局示意图"""
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5)
    ax.axis('off')
    fig.patch.set_facecolor('#FAFAFA')

    ax.set_title('顶点属性交错布局（Interleaved Layout）', fontsize=15,
                 fontweight='bold', pad=15, color='#212121')

    # 三个顶点的数据
    vertices = [
        [("x₀", "pos"), ("y₀", "pos"), ("z₀", "pos"),
         ("r₀", "col"), ("g₀", "col"), ("b₀", "col")],
        [("x₁", "pos"), ("y₁", "pos"), ("z₁", "pos"),
         ("r₁", "col"), ("g₁", "col"), ("b₁", "col")],
        [("x₂", "pos"), ("y₂", "pos"), ("z₂", "pos"),
         ("r₂", "col"), ("g₂", "col"), ("b₂", "col")],
    ]

    colors = {"pos": "#90CAF9", "col": "#FFAB91"}
    cell_w = 0.65
    cell_h = 0.7
    start_x = 0.6
    start_y = 3.3

    for vi, vertex in enumerate(vertices):
        for ci, (label, attr_type) in enumerate(vertex):
            x = start_x + (vi * 6 + ci) * cell_w
            y = start_y
            rect = plt.Rectangle((x, y), cell_w - 0.04, cell_h,
                                  facecolor=colors[attr_type],
                                  edgecolor='#455A64', linewidth=1)
            ax.add_patch(rect)
            ax.text(x + cell_w / 2 - 0.02, y + cell_h / 2, label,
                    ha='center', va='center', fontsize=8.5, fontweight='bold',
                    color='#212121')

    # 顶点分组标注
    brace_y = start_y + cell_h + 0.15
    for vi in range(3):
        x_left = start_x + vi * 6 * cell_w
        x_right = x_left + 6 * cell_w - 0.04
        x_mid = (x_left + x_right) / 2

        ax.annotate('', xy=(x_left, brace_y), xytext=(x_right, brace_y),
                    arrowprops=dict(arrowstyle='-', color='#455A64', lw=1.5))
        ax.plot([x_left, x_left], [brace_y, brace_y - 0.08], color='#455A64', lw=1.5)
        ax.plot([x_right, x_right], [brace_y, brace_y - 0.08], color='#455A64', lw=1.5)

        ax.text(x_mid, brace_y + 0.15, f'顶点 {vi}',
                ha='center', va='bottom', fontsize=10,
                fontweight='bold', color='#37474F')

    # stride 标注
    stride_y = start_y - 0.35
    x0 = start_x
    x1 = start_x + 6 * cell_w
    ax.annotate('', xy=(x1, stride_y), xytext=(x0, stride_y),
                arrowprops=dict(arrowstyle='<->', color='#D32F2F', lw=2))
    ax.text((x0 + x1) / 2, stride_y - 0.25,
            'stride = 6 × sizeof(float) = 24 字节',
            ha='center', va='top', fontsize=10, fontweight='bold', color='#D32F2F')

    # offset 标注
    offset_y = start_y - 1.0
    pos_end = start_x + 3 * cell_w

    ax.annotate('', xy=(start_x, offset_y + 0.15), xytext=(start_x, offset_y + 0.15),
                arrowprops=dict(arrowstyle='->', color='#1565C0', lw=1.5))
    ax.text(start_x + 0.05, offset_y, 'offset = 0  (位置属性)',
            ha='left', va='top', fontsize=9, fontweight='bold', color='#1565C0')

    ax.annotate('', xy=(pos_end, offset_y - 0.45), xytext=(pos_end, offset_y - 0.45),
                arrowprops=dict(arrowstyle='->', color='#E65100', lw=1.5))
    ax.text(pos_end + 0.05, offset_y - 0.6,
            'offset = 3 × sizeof(float) = 12 字节  (颜色属性)',
            ha='left', va='top', fontsize=9, fontweight='bold', color='#E65100')

    # 小箭头从 offset 文字指向对应单元格
    ax.annotate('', xy=(start_x + 0.3, start_y),
                xytext=(start_x + 0.3, offset_y + 0.15),
                arrowprops=dict(arrowstyle='->', color='#1565C0', lw=1.2,
                                connectionstyle='arc3,rad=0'))
    ax.annotate('', xy=(pos_end + 0.3, start_y),
                xytext=(pos_end + 0.3, offset_y - 0.45),
                arrowprops=dict(arrowstyle='->', color='#E65100', lw=1.2,
                                connectionstyle='arc3,rad=0'))

    # 图例
    legend_patches = [
        mpatches.Patch(facecolor='#90CAF9', edgecolor='#455A64', label='位置 (vec3)'),
        mpatches.Patch(facecolor='#FFAB91', edgecolor='#455A64', label='颜色 (vec3)'),
    ]
    ax.legend(handles=legend_patches, loc='lower right', fontsize=10,
              framealpha=0.9, edgecolor='#BDBDBD')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'vertex_attributes.png')
    plt.savefig(path, dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"已生成: {path}")


if __name__ == '__main__':
    print("正在生成插图...")
    draw_pipeline()
    draw_vbo_vao_ebo()
    draw_vertex_attributes()
    print("全部插图生成完毕！")
