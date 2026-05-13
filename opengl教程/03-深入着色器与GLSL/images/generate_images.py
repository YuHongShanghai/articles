"""
生成第3篇"深入着色器与GLSL"教程配图
运行: python generate_images.py
依赖: pip install matplotlib
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 150


def draw_rounded_box(ax, xy, width, height, text, facecolor, edgecolor='#333333',
                     fontsize=11, textcolor='white', linewidth=1.5, fontstyle='normal'):
    x, y = xy
    box = FancyBboxPatch((x, y), width, height,
                         boxstyle="round,pad=0.1",
                         facecolor=facecolor, edgecolor=edgecolor,
                         linewidth=linewidth, zorder=2)
    ax.add_patch(box)
    ax.text(x + width / 2, y + height / 2, text,
            ha='center', va='center', fontsize=fontsize,
            color=textcolor, fontweight='bold', fontstyle=fontstyle, zorder=3)
    return box


def draw_arrow(ax, start, end, color='#555555', style='->', linewidth=1.8):
    arrow = FancyArrowPatch(start, end,
                            arrowstyle=style,
                            color=color,
                            linewidth=linewidth,
                            mutation_scale=15,
                            zorder=1)
    ax.add_patch(arrow)


# ========================================================================
# 图1: glsl_data_flow.png — 着色器之间的数据流图
# ========================================================================
def generate_data_flow():
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    ax.set_title('着色器数据流：in / out / uniform 传递关系', fontsize=16, fontweight='bold', pad=20)

    # CPU 应用程序
    draw_rounded_box(ax, (0.3, 5.0), 3.0, 1.2, 'CPU 应用程序\n(C++ 代码)',
                     facecolor='#2196F3', fontsize=12)

    # VBO 顶点数据
    draw_rounded_box(ax, (0.3, 2.8), 3.0, 1.2, 'VBO 顶点数据\n位置 / 颜色 / UV',
                     facecolor='#607D8B', fontsize=11)

    # 顶点着色器
    draw_rounded_box(ax, (4.5, 2.8), 3.0, 1.2, '顶点着色器\n(Vertex Shader)',
                     facecolor='#4CAF50', fontsize=12)

    # 光栅化
    draw_rounded_box(ax, (4.5, 0.5), 3.0, 1.0, '光栅化（插值）',
                     facecolor='#9E9E9E', fontsize=11)

    # 片段着色器
    draw_rounded_box(ax, (8.5, 2.8), 3.0, 1.2, '片段着色器\n(Fragment Shader)',
                     facecolor='#FF9800', fontsize=12)

    # 帧缓冲
    draw_rounded_box(ax, (8.5, 0.5), 3.0, 1.0, '帧缓冲 → 屏幕',
                     facecolor='#795548', fontsize=11)

    # Uniform 标注
    draw_rounded_box(ax, (4.5, 5.0), 3.0, 1.2, 'Uniform 变量\n(全局常量)',
                     facecolor='#9C27B0', fontsize=11)

    # ---- 箭头 ----
    # VBO → 顶点着色器 (in)
    draw_arrow(ax, (3.3, 3.4), (4.5, 3.4), color='#4CAF50', linewidth=2.5)
    ax.text(3.9, 3.7, 'in', fontsize=12, color='#4CAF50', fontweight='bold',
            ha='center', style='italic')

    # 顶点着色器 → 光栅化 (out)
    draw_arrow(ax, (6.0, 2.8), (6.0, 1.5), color='#FF9800', linewidth=2.0)
    ax.text(6.35, 2.2, 'out', fontsize=11, color='#FF9800', fontweight='bold', style='italic')

    # 光栅化 → 片段着色器 (in, 插值后)
    draw_arrow(ax, (7.5, 1.0), (8.5, 2.8), color='#FF9800', linewidth=2.0)
    ax.text(8.3, 1.7, 'in\n(插值后)', fontsize=10, color='#FF9800', fontweight='bold',
            ha='center', style='italic')

    # 片段着色器 → 帧缓冲 (out)
    draw_arrow(ax, (10.0, 2.8), (10.0, 1.5), color='#F44336', linewidth=2.0)
    ax.text(10.4, 2.2, 'out\nFragColor', fontsize=10, color='#F44336',
            fontweight='bold', style='italic')

    # CPU → Uniform
    draw_arrow(ax, (3.3, 5.6), (4.5, 5.6), color='#9C27B0', linewidth=2.5)
    ax.text(3.9, 5.9, 'glUniform*', fontsize=10, color='#9C27B0', fontweight='bold',
            ha='center', style='italic')

    # Uniform → 顶点着色器
    draw_arrow(ax, (5.2, 5.0), (5.2, 4.0), color='#9C27B0', linewidth=2.0)
    ax.text(5.5, 4.5, 'uniform', fontsize=10, color='#9C27B0',
            fontweight='bold', style='italic')

    # Uniform → 片段着色器
    draw_arrow(ax, (7.5, 5.6), (8.5, 3.8), color='#9C27B0', linewidth=2.0)
    ax.text(8.3, 5.0, 'uniform', fontsize=10, color='#9C27B0',
            fontweight='bold', style='italic')

    # CPU → VBO
    draw_arrow(ax, (1.8, 5.0), (1.8, 4.0), color='#2196F3', linewidth=2.0)
    ax.text(2.1, 4.5, 'glBufferData', fontsize=9, color='#2196F3',
            fontweight='bold', style='italic')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'glsl_data_flow.png')
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'✓ {path}')


# ========================================================================
# 图2: shader_compile_flow.png — 着色器编译链接流程图
# ========================================================================
def generate_compile_flow():
    fig, ax = plt.subplots(1, 1, figsize=(11, 8))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('着色器编译与链接流程', fontsize=16, fontweight='bold', pad=20)

    # ---- 左列：顶点着色器分支 ----
    draw_rounded_box(ax, (0.5, 6.5), 3.5, 0.9, '顶点着色器源码\nvertex.glsl',
                     facecolor='#5C6BC0', fontsize=10)
    draw_rounded_box(ax, (0.5, 5.0), 3.5, 0.9, 'glCreateShader\n(GL_VERTEX_SHADER)',
                     facecolor='#42A5F5', fontsize=10)
    draw_rounded_box(ax, (0.5, 3.5), 3.5, 0.9, 'glShaderSource\n+ glCompileShader',
                     facecolor='#26A69A', fontsize=10)

    draw_arrow(ax, (2.25, 6.5), (2.25, 5.9), color='#555')
    draw_arrow(ax, (2.25, 5.0), (2.25, 4.4), color='#555')

    # ---- 右列：片段着色器分支 ----
    draw_rounded_box(ax, (7.0, 6.5), 3.5, 0.9, '片段着色器源码\nfragment.glsl',
                     facecolor='#5C6BC0', fontsize=10)
    draw_rounded_box(ax, (7.0, 5.0), 3.5, 0.9, 'glCreateShader\n(GL_FRAGMENT_SHADER)',
                     facecolor='#42A5F5', fontsize=10)
    draw_rounded_box(ax, (7.0, 3.5), 3.5, 0.9, 'glShaderSource\n+ glCompileShader',
                     facecolor='#26A69A', fontsize=10)

    draw_arrow(ax, (8.75, 6.5), (8.75, 5.9), color='#555')
    draw_arrow(ax, (8.75, 5.0), (8.75, 4.4), color='#555')

    # ---- 检查编译 ----
    ax.text(2.25, 3.15, '检查 GL_COMPILE_STATUS', fontsize=9, ha='center',
            color='#E53935', fontstyle='italic')
    ax.text(8.75, 3.15, '检查 GL_COMPILE_STATUS', fontsize=9, ha='center',
            color='#E53935', fontstyle='italic')

    # ---- 中间：链接阶段 ----
    draw_rounded_box(ax, (3.0, 1.8), 5.0, 1.0, 'glCreateProgram\n+ glAttachShader × 2\n+ glLinkProgram',
                     facecolor='#FF7043', fontsize=11)

    draw_arrow(ax, (2.25, 3.5), (4.5, 2.8), color='#555', linewidth=2.0)
    draw_arrow(ax, (8.75, 3.5), (6.5, 2.8), color='#555', linewidth=2.0)

    ax.text(5.5, 1.45, '检查 GL_LINK_STATUS', fontsize=9, ha='center',
            color='#E53935', fontstyle='italic')

    # ---- 最终产物 ----
    draw_rounded_box(ax, (3.0, 0.2), 5.0, 0.9, 'glUseProgram → 激活着色器程序',
                     facecolor='#4CAF50', fontsize=12)
    draw_arrow(ax, (5.5, 1.8), (5.5, 1.1), color='#4CAF50', linewidth=2.5)

    # 删除着色器标注
    ax.text(1.0, 1.1, 'glDeleteShader\n(释放着色器对象)', fontsize=9, ha='center',
            color='#9E9E9E', fontstyle='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#F5F5F5', edgecolor='#BDBDBD'))

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'shader_compile_flow.png')
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'✓ {path}')


# ========================================================================
# 图3: glsl_types.png — GLSL 常用数据类型速查图
# ========================================================================
def generate_types_chart():
    fig, ax = plt.subplots(1, 1, figsize=(12, 7.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.5)
    ax.axis('off')
    ax.set_title('GLSL 常用数据类型速查', fontsize=16, fontweight='bold', pad=20)

    code_style = dict(fontsize=10, fontweight='bold', color='#333333',
                      ha='left', va='top', zorder=3, family='monospace')
    desc_style = dict(fontsize=9, color='#666666', ha='left', va='top', zorder=3)

    def draw_type_card(ax, x, y_top, width, title, color, bg_color, items):
        draw_rounded_box(ax, (x, y_top), width, 0.7, title,
                         facecolor=color, fontsize=13)
        card_h = len(items) * 0.45 + 0.2
        card_y = y_top - card_h
        box = FancyBboxPatch((x, card_y), width, card_h, boxstyle="round,pad=0.1",
                             facecolor=bg_color, edgecolor=color, linewidth=1.5, zorder=1)
        ax.add_patch(box)
        for i, (name, desc) in enumerate(items):
            row_y = y_top - 0.45 - i * 0.45
            ax.text(x + 0.2, row_y, name, **code_style)
            ax.text(x + width * 0.55, row_y, desc, **desc_style)

    draw_type_card(ax, 0.3, 6.5, 2.7, '标量类型', '#2196F3', '#E3F2FD', [
        ('bool',   '布尔值'),
        ('int',    '32位整数'),
        ('uint',   '无符号整数'),
        ('float',  '32位浮点'),
        ('double', '64位浮点'),
    ])

    draw_type_card(ax, 3.3, 6.5, 2.7, '向量类型', '#4CAF50', '#E8F5E9', [
        ('vec2',      '2D 纹理坐标'),
        ('vec3',      '3D 位置/颜色'),
        ('vec4',      '4D 齐次坐标'),
        ('ivec2/3/4', '整数向量'),
        ('bvec2/3/4', '布尔向量'),
    ])

    draw_type_card(ax, 6.3, 6.5, 2.7, '矩阵类型', '#FF9800', '#FFF3E0', [
        ('mat2',   '2x2 矩阵'),
        ('mat3',   '3x3 矩阵'),
        ('mat4',   '4x4 MVP变换'),
        ('mat2x3', '2列3行矩阵'),
    ])

    draw_type_card(ax, 9.3, 6.5, 2.5, '采样器类型', '#9C27B0', '#F3E5F5', [
        ('sampler2D',   '2D 纹理'),
        ('sampler3D',   '3D 纹理'),
        ('samplerCube', '立方体贴图'),
    ])

    # ---- Swizzle ----
    swizzle_box = FancyBboxPatch((0.3, 0.3), 11.4, 2.5, boxstyle="round,pad=0.15",
                                 facecolor='#FAFAFA', edgecolor='#78909C',
                                 linewidth=1.5, zorder=1)
    ax.add_patch(swizzle_box)
    ax.text(6.0, 2.55, 'Swizzling (分量重排)', fontsize=12, fontweight='bold',
            ha='center', color='#37474F')

    swizzle_code = [
        'vec4 v = vec4(1.0, 2.0, 3.0, 4.0);',
        'v.xy  = vec2(1.0, 2.0)       v.rgb = vec3(1.0, 2.0, 3.0)',
        'v.bgr = vec3(3.0, 2.0, 1.0)  v.xxx = vec3(1.0, 1.0, 1.0)',
    ]
    for i, line in enumerate(swizzle_code):
        ax.text(0.8, 2.1 - i * 0.4, line, fontsize=10, color='#455A64',
                family='monospace', va='top')

    ax.text(0.8, 0.85, '.xyzw (坐标)    .rgba (颜色)    .stpq (纹理)',
            fontsize=10, color='#37474F', va='top', fontweight='bold')
    ax.text(0.8, 0.5, '三组不可混用，例如 v.xg 是非法的',
            fontsize=9, color='#E53935', va='top', fontstyle='italic')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'glsl_types.png')
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'✓ {path}')


if __name__ == '__main__':
    print('生成第3篇教程配图...')
    generate_data_flow()
    generate_compile_flow()
    generate_types_chart()
    print('全部完成！')
