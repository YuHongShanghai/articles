#!/usr/bin/env python3
"""第1篇插图生成：OpenGL架构与渲染循环"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def draw_opengl_architecture():
    """图1: OpenGL 软件架构层次图"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('OpenGL 软件架构层次', fontsize=16, fontweight='bold', pad=20)

    layers = [
        (1, 6.2, 8, 1.0, '应用程序 (C/C++)', '#4FC3F7', '你编写的代码：顶点数据、着色器、渲染逻辑'),
        (1, 4.8, 8, 1.0, 'GLFW (窗口/输入管理)', '#81C784', '创建窗口、处理键盘鼠标、管理 OpenGL 上下文'),
        (1, 3.4, 8, 1.0, 'GLAD (函数加载器)', '#FFB74D', '动态加载 GPU 驱动中的 OpenGL 函数指针'),
        (1, 2.0, 8, 1.0, 'OpenGL 驱动 (GPU厂商实现)', '#E57373', 'NVIDIA / AMD / Intel 提供的 OpenGL 实现'),
        (1, 0.6, 8, 1.0, 'GPU 硬件', '#B0BEC5', '图形处理器，执行实际的渲染计算'),
    ]

    for x, y, w, h, label, color, desc in layers:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                             facecolor=color, edgecolor='#333', linewidth=1.5, alpha=0.85)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2 + 0.15, label, ha='center', va='center',
                fontsize=13, fontweight='bold', color='#222')
        ax.text(x + w/2, y + h/2 - 0.2, desc, ha='center', va='center',
                fontsize=8.5, color='#444', style='italic')

    for i in range(4):
        y_start = layers[i][1]
        y_end = layers[i+1][1] + layers[i+1][3]
        ax.annotate('', xy=(5, y_end + 0.05), xytext=(5, y_start - 0.05),
                    arrowprops=dict(arrowstyle='->', lw=2, color='#666'))

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'opengl_architecture.png'), dpi=150, bbox_inches='tight')
    plt.close()


def draw_render_loop():
    """图2: 渲染循环流程图"""
    fig, ax = plt.subplots(1, 1, figsize=(8, 10))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 12)
    ax.axis('off')
    ax.set_title('OpenGL 渲染循环流程', fontsize=16, fontweight='bold', pad=20)

    steps = [
        (4, 10.5, '初始化 GLFW/GLAD', '#4FC3F7', 'rect'),
        (4, 9.2, '窗口是否关闭?', '#FFF176', 'diamond'),
        (4, 7.8, '处理输入事件', '#81C784', 'rect'),
        (4, 6.4, '清除颜色/深度缓冲', '#A5D6A7', 'rect'),
        (4, 5.0, '执行渲染命令', '#FFB74D', 'rect'),
        (4, 3.6, '交换前后缓冲区', '#CE93D8', 'rect'),
        (4, 2.2, '轮询事件', '#90CAF9', 'rect'),
        (4, 0.8, '清理资源 / 退出', '#E57373', 'rect'),
    ]

    for x, y, label, color, shape in steps:
        if shape == 'diamond':
            diamond = plt.Polygon([(x, y+0.5), (x+1.2, y), (x, y-0.5), (x-1.2, y)],
                                  facecolor=color, edgecolor='#333', linewidth=1.5, alpha=0.85)
            ax.add_patch(diamond)
            ax.text(x, y, label, ha='center', va='center', fontsize=10, fontweight='bold')
        else:
            box = FancyBboxPatch((x-1.5, y-0.35), 3.0, 0.7, boxstyle="round,pad=0.08",
                                 facecolor=color, edgecolor='#333', linewidth=1.5, alpha=0.85)
            ax.add_patch(box)
            ax.text(x, y, label, ha='center', va='center', fontsize=11, fontweight='bold')

    connections = [
        (4, 10.15, 4, 9.75),
        (4, 8.7, 4, 8.15),
        (4, 7.45, 4, 6.75),
        (4, 6.05, 4, 5.35),
        (4, 4.65, 4, 3.95),
        (4, 3.25, 4, 2.55),
    ]
    for x1, y1, x2, y2 in connections:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=1.8, color='#555'))

    ax.annotate('', xy=(1.0, 9.2), xytext=(2.8, 9.2),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#D32F2F'))
    ax.annotate('', xy=(4, 0.8+0.35), xytext=(1.0, 9.2),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#D32F2F',
                               connectionstyle='arc3,rad=0'))
    ax.text(1.5, 9.5, '是', fontsize=10, color='#D32F2F', fontweight='bold')
    ax.text(4.3, 8.9, '否', fontsize=10, color='#388E3C', fontweight='bold')

    # loop back arrow
    ax.annotate('', xy=(6.5, 7.8), xytext=(6.5, 2.2),
                arrowprops=dict(arrowstyle='->', lw=2, color='#1565C0',
                               connectionstyle='arc3,rad=-0.3'))
    ax.text(7.0, 5.0, '循环', fontsize=11, color='#1565C0', fontweight='bold', rotation=90)

    bracket = FancyBboxPatch((0.3, 1.8), 0.3, 6.5, boxstyle="round,pad=0.05",
                             facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=1.5, alpha=0.5)
    ax.add_patch(bracket)
    ax.text(0.15, 5.0, '渲\n染\n循\n环', fontsize=11, color='#1565C0',
            fontweight='bold', ha='center', va='center')

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'render_loop.png'), dpi=150, bbox_inches='tight')
    plt.close()


def draw_double_buffer():
    """图3: 双缓冲机制示意图"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_title('双缓冲机制 (Double Buffering)', fontsize=16, fontweight='bold', pad=15)

    front = FancyBboxPatch((0.5, 1), 4, 3.5, boxstyle="round,pad=0.15",
                           facecolor='#C8E6C9', edgecolor='#388E3C', linewidth=2)
    ax.add_patch(front)
    ax.text(2.5, 4.0, '前缓冲 (Front Buffer)', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#2E7D32')
    ax.text(2.5, 2.8, '正在显示的画面', ha='center', va='center', fontsize=10, color='#555')
    ax.text(2.5, 2.2, '用户看到的内容', ha='center', va='center', fontsize=9, color='#888')

    monitor = FancyBboxPatch((0.8, 1.3), 3.4, 1.2, boxstyle="round,pad=0.05",
                             facecolor='#E8F5E9', edgecolor='#66BB6A', linewidth=1)
    ax.add_patch(monitor)
    ax.text(2.5, 1.9, '🖥 显示器', ha='center', va='center', fontsize=10)

    back = FancyBboxPatch((7.5, 1), 4, 3.5, boxstyle="round,pad=0.15",
                          facecolor='#BBDEFB', edgecolor='#1976D2', linewidth=2)
    ax.add_patch(back)
    ax.text(9.5, 4.0, '后缓冲 (Back Buffer)', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#1565C0')
    ax.text(9.5, 2.8, '正在绘制的画面', ha='center', va='center', fontsize=10, color='#555')
    ax.text(9.5, 2.2, 'GPU 渲染目标', ha='center', va='center', fontsize=9, color='#888')

    ax.annotate('', xy=(7.2, 3.0), xytext=(4.8, 3.0),
                arrowprops=dict(arrowstyle='<->', lw=2.5, color='#FF6F00'))
    ax.text(6.0, 3.5, 'glfwSwapBuffers()', ha='center', va='center',
            fontsize=11, fontweight='bold', color='#E65100',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF3E0', edgecolor='#FF6F00'))

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'double_buffer.png'), dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    draw_opengl_architecture()
    draw_render_loop()
    draw_double_buffer()
    print("第1篇插图生成完成！")
