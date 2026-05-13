"""共享绘图工具模块，提供流媒体教程插图的通用绘图原语。"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    'primary':    '#2563EB',
    'secondary':  '#7C3AED',
    'accent':     '#059669',
    'warning':    '#D97706',
    'danger':     '#DC2626',
    'info':       '#0891B2',
    'light_bg':   '#F1F5F9',
    'dark_text':  '#1E293B',
    'mid_text':   '#64748B',
    'border':     '#CBD5E1',
    'white':      '#FFFFFF',
    'light_blue': '#DBEAFE',
    'light_purple': '#EDE9FE',
    'light_green':  '#D1FAE5',
    'light_orange': '#FEF3C7',
    'light_red':    '#FEE2E2',
    'light_cyan':   '#CFFAFE',
}

plt.rcParams.update({
    'font.family': ['WenQuanYi Zen Hei', 'WenQuanYi Micro Hei',
                     'Noto Sans CJK SC', 'SimHei',
                     'Microsoft YaHei', 'DejaVu Sans', 'sans-serif'],
    'axes.unicode_minus': False,
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.3,
})


def save_fig(fig, name):
    path = os.path.join(OUTPUT_DIR, f'{name}.png')
    fig.savefig(path, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f'  [OK] {name}.png')
    return path


def new_fig(width=10, height=6, bg='white'):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.set_facecolor(bg)
    ax.set_facecolor(bg)
    return fig, ax


def no_axes(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    return ax


def draw_box(ax, x, y, w, h, text, color=COLORS['primary'],
             text_color='white', fontsize=10, alpha=1.0, radius=0.3):
    box = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0.1,rounding_size={radius}",
                          facecolor=color, edgecolor='none', alpha=alpha,
                          transform=ax.transData, zorder=2)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, fontweight='bold', zorder=3)
    return box


def draw_arrow(ax, x1, y1, x2, y2, color=COLORS['mid_text'], style='->', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                zorder=1)


def draw_brace_text(ax, x, y, text, fontsize=9, color=COLORS['dark_text']):
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            color=color, zorder=3)


def draw_sequence_arrow(ax, x1, x2, y, label='', color=COLORS['primary'],
                         fontsize=8, label_color=None):
    if label_color is None:
        label_color = COLORS['dark_text']
    ax.annotate('', xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
    mid_x = (x1 + x2) / 2
    offset = 0.15
    ax.text(mid_x, y + offset, label, ha='center', va='bottom',
            fontsize=fontsize, color=label_color)


def draw_dashed_line(ax, x1, y1, x2, y2, color=COLORS['border'], lw=1):
    ax.plot([x1, x2], [y1, y2], '--', color=color, lw=lw, zorder=0)


def draw_field_row(ax, x, y, fields, height=0.5, fontsize=8):
    """Draw a protocol header field row (bit-level diagram)."""
    total_bits = sum(f[1] for f in fields)
    unit_w = 8.0 / total_bits
    cx = x
    colors_cycle = [COLORS['light_blue'], COLORS['light_purple'],
                    COLORS['light_green'], COLORS['light_orange'],
                    COLORS['light_cyan'], COLORS['light_red']]
    for i, (name, bits) in enumerate(fields):
        w = bits * unit_w
        bg = colors_cycle[i % len(colors_cycle)]
        box = FancyBboxPatch((cx, y), w, height,
                              boxstyle="square,pad=0",
                              facecolor=bg, edgecolor=COLORS['border'],
                              linewidth=1, zorder=2)
        ax.add_patch(box)
        label = f"{name}\n({bits}b)" if bits > 1 else name
        ax.text(cx + w/2, y + height/2, label, ha='center', va='center',
                fontsize=fontsize if w > 0.8 else fontsize-1,
                color=COLORS['dark_text'], zorder=3)
        cx += w


def draw_timeline_entity(ax, x, y_top, y_bottom, label, color=COLORS['primary']):
    ax.plot([x, x], [y_top, y_bottom], '-', color=COLORS['border'], lw=1, zorder=0)
    draw_box(ax, x - 0.6, y_top, 1.2, 0.4, label, color=color, fontsize=9)
