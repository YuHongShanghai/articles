"""
生成第7篇"基础光照"教程配图
运行: python generate_images.py
依赖: pip install matplotlib numpy
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc, Circle, Wedge
import numpy as np
import os

plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 150


def draw_rounded_box(ax, xy, width, height, text, facecolor, edgecolor='#333333',
                     fontsize=11, textcolor='white', linewidth=1.5):
    x, y = xy
    box = FancyBboxPatch((x, y), width, height,
                         boxstyle="round,pad=0.1",
                         facecolor=facecolor, edgecolor=edgecolor,
                         linewidth=linewidth, zorder=2)
    ax.add_patch(box)
    ax.text(x + width / 2, y + height / 2, text,
            ha='center', va='center', fontsize=fontsize,
            color=textcolor, fontweight='bold', zorder=3)
    return box


# ========================================================================
# 图1: phong_components.png — Phong 三分量效果示意
# ========================================================================
def generate_phong_components():
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.5))
    fig.suptitle('Phong 光照模型三分量', fontsize=16, fontweight='bold', y=1.02)

    titles = ['环境光 (Ambient)', '漫反射 (Diffuse)', '镜面反射 (Specular)', '最终结果 (Result)']
    colors_bg = ['#1a1a2e', '#1a1a2e', '#1a1a2e', '#1a1a2e']

    for idx, (ax, title) in enumerate(zip(axes, titles)):
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_facecolor(colors_bg[idx])
        ax.set_title(title, fontsize=11, fontweight='bold', pad=8)

        theta = np.linspace(0, 2 * np.pi, 200)
        r = 0.85

        if idx == 0:
            base_color = np.array([0.15, 0.12, 0.04])
            for i in range(len(theta) - 1):
                ax.fill_between(
                    [r * np.cos(theta[i]), r * np.cos(theta[i+1])],
                    [r * np.sin(theta[i]), r * np.sin(theta[i+1])],
                    [0, 0],
                    color=base_color, alpha=0.9
                )
            circle = plt.Circle((0, 0), r, color=base_color, ec='#444444', linewidth=1)
            ax.add_patch(circle)

        elif idx == 1:
            for i in range(len(theta) - 1):
                angle = theta[i]
                light_dir_angle = np.pi * 0.75
                cos_factor = max(np.cos(angle - light_dir_angle), 0.0)
                c = np.array([0.75, 0.61, 0.23]) * cos_factor * 0.8
                c = np.clip(c, 0, 1)
                wedge = Wedge((0, 0), r, np.degrees(theta[i]), np.degrees(theta[i+1]),
                              color=c, ec='none')
                ax.add_patch(wedge)
            circle = plt.Circle((0, 0), r, fill=False, ec='#555555', linewidth=0.8)
            ax.add_patch(circle)
            ax.annotate('', xy=(-0.4, 0.4), xytext=(-1.0, 1.0),
                        arrowprops=dict(arrowstyle='->', color='#FFD700', lw=2.5))
            ax.text(-1.05, 1.05, '光线', fontsize=9, color='#FFD700', fontweight='bold')

        elif idx == 2:
            for i in range(len(theta) - 1):
                angle = theta[i]
                spec_angle = np.pi * 0.25
                cos_factor = max(np.cos(angle - spec_angle), 0.0)
                spec = cos_factor ** 32
                c = np.array([0.63, 0.56, 0.37]) * spec
                c = np.clip(c, 0, 1)
                wedge = Wedge((0, 0), r, np.degrees(theta[i]), np.degrees(theta[i+1]),
                              color=c, ec='none')
                ax.add_patch(wedge)
            circle = plt.Circle((0, 0), r, fill=False, ec='#555555', linewidth=0.8)
            ax.add_patch(circle)
            highlight = plt.Circle((0.35, 0.35), 0.12, color='white', alpha=0.6, ec='none')
            ax.add_patch(highlight)
            ax.text(0.85, 0.85, '高光', fontsize=8, color='white', fontweight='bold',
                    ha='center')

        elif idx == 3:
            for i in range(len(theta) - 1):
                angle = theta[i]
                light_dir_angle = np.pi * 0.75
                cos_factor = max(np.cos(angle - light_dir_angle), 0.0)
                spec_angle = np.pi * 0.25
                spec_cos = max(np.cos(angle - spec_angle), 0.0)
                spec = spec_cos ** 32

                ambient = np.array([0.15, 0.12, 0.04])
                diffuse = np.array([0.75, 0.61, 0.23]) * cos_factor * 0.8
                specular = np.array([0.63, 0.56, 0.37]) * spec
                c = np.clip(ambient + diffuse + specular, 0, 1)
                wedge = Wedge((0, 0), r, np.degrees(theta[i]), np.degrees(theta[i+1]),
                              color=c, ec='none')
                ax.add_patch(wedge)
            circle = plt.Circle((0, 0), r, fill=False, ec='#666666', linewidth=0.8)
            ax.add_patch(circle)
            highlight = plt.Circle((0.35, 0.35), 0.1, color='white', alpha=0.4, ec='none')
            ax.add_patch(highlight)

    # "+" 和 "=" 符号
    fig.text(0.275, 0.48, '+', fontsize=24, fontweight='bold', color='#CCCCCC',
             ha='center', va='center')
    fig.text(0.50, 0.48, '+', fontsize=24, fontweight='bold', color='#CCCCCC',
             ha='center', va='center')
    fig.text(0.725, 0.48, '=', fontsize=24, fontweight='bold', color='#CCCCCC',
             ha='center', va='center')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'phong_components.png')
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'✓ {path}')


# ========================================================================
# 图2: light_types.png — 三种光源类型对比
# ========================================================================
def generate_light_types():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('三种光源类型对比', fontsize=16, fontweight='bold', y=1.02)

    # --- 平行光 ---
    ax = axes[0]
    ax.set_xlim(-3, 3)
    ax.set_ylim(-1, 4)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('平行光 (Directional Light)', fontsize=12, fontweight='bold', pad=10)
    ax.set_facecolor('#f8f8fc')

    for x_off in [-1.5, -0.5, 0.5, 1.5]:
        ax.annotate('', xy=(x_off, 0.3), xytext=(x_off + 0.6, 3.5),
                    arrowprops=dict(arrowstyle='->', color='#FFA000', lw=2.0, alpha=0.8))

    rect = mpatches.FancyBboxPatch((-2.0, -0.5), 4.0, 0.6, boxstyle="round,pad=0.05",
                                    facecolor='#78909C', edgecolor='#546E7A', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(0, -0.2, '表面', fontsize=10, ha='center', va='center', color='white',
            fontweight='bold')
    ax.text(0, 3.8, '☀ 太阳（无限远）', fontsize=10, ha='center', color='#E65100',
            fontweight='bold')
    ax.text(0, -0.9, '所有光线方向相同\n无距离衰减', fontsize=9, ha='center',
            color='#666666', style='italic')

    # --- 点光源 ---
    ax = axes[1]
    ax.set_xlim(-3, 3)
    ax.set_ylim(-1, 4)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('点光源 (Point Light)', fontsize=12, fontweight='bold', pad=10)
    ax.set_facecolor('#f8f8fc')

    light_pos = (0, 3.0)
    bulb = plt.Circle(light_pos, 0.2, color='#FFEB3B', ec='#FFC107', linewidth=2, zorder=5)
    ax.add_patch(bulb)
    glow = plt.Circle(light_pos, 0.35, color='#FFEB3B', alpha=0.3, ec='none', zorder=4)
    ax.add_patch(glow)

    for angle_deg in range(0, 360, 30):
        angle = np.radians(angle_deg)
        dx = np.cos(angle) * 2.0
        dy = np.sin(angle) * 2.0
        end_x = light_pos[0] + dx
        end_y = light_pos[1] + dy
        if end_y > -0.3:
            alpha = max(0.2, 1.0 - np.sqrt(dx**2 + dy**2) / 2.5)
            ax.annotate('', xy=(end_x, end_y),
                        xytext=(light_pos[0] + dx*0.15, light_pos[1] + dy*0.15),
                        arrowprops=dict(arrowstyle='->', color='#FFA000', lw=1.5,
                                        alpha=alpha))

    rect = mpatches.FancyBboxPatch((-2.0, -0.5), 4.0, 0.6, boxstyle="round,pad=0.05",
                                    facecolor='#78909C', edgecolor='#546E7A', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(0, -0.2, '表面', fontsize=10, ha='center', va='center', color='white',
            fontweight='bold')
    ax.text(0, -0.9, '向所有方向发光\n有距离衰减', fontsize=9, ha='center',
            color='#666666', style='italic')

    # --- 聚光灯 ---
    ax = axes[2]
    ax.set_xlim(-3, 3)
    ax.set_ylim(-1, 4)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('聚光灯 (Spotlight)', fontsize=12, fontweight='bold', pad=10)
    ax.set_facecolor('#f8f8fc')

    light_pos = (0, 3.5)
    flashlight = mpatches.FancyBboxPatch((-0.25, 3.2), 0.5, 0.4, boxstyle="round,pad=0.05",
                                          facecolor='#455A64', edgecolor='#37474F',
                                          linewidth=1.5, zorder=5)
    ax.add_patch(flashlight)

    inner_cone = Wedge(light_pos, 3.0, 250, 290, color='#FFEB3B', alpha=0.35,
                       ec='none', zorder=2)
    ax.add_patch(inner_cone)
    outer_cone = Wedge(light_pos, 3.2, 240, 300, color='#FFF9C4', alpha=0.15,
                       ec='none', zorder=1)
    ax.add_patch(outer_cone)

    ax.annotate('', xy=(0, 0.3), xytext=(0, 3.2),
                arrowprops=dict(arrowstyle='->', color='#FFA000', lw=2.5))

    inner_angle = 20
    outer_angle = 30
    ax.plot([0, -np.tan(np.radians(inner_angle)) * 2.8],
            [3.2, 3.2 - 2.8], '--', color='#FF9800', lw=1.2, alpha=0.7)
    ax.plot([0, np.tan(np.radians(inner_angle)) * 2.8],
            [3.2, 3.2 - 2.8], '--', color='#FF9800', lw=1.2, alpha=0.7)
    ax.plot([0, -np.tan(np.radians(outer_angle)) * 2.8],
            [3.2, 3.2 - 2.8], ':', color='#FFB74D', lw=1.0, alpha=0.5)
    ax.plot([0, np.tan(np.radians(outer_angle)) * 2.8],
            [3.2, 3.2 - 2.8], ':', color='#FFB74D', lw=1.0, alpha=0.5)

    ax.annotate('cutOff', xy=(0.5, 2.2), fontsize=8, color='#E65100',
                fontweight='bold', style='italic')
    ax.annotate('outerCutOff', xy=(1.2, 1.5), fontsize=8, color='#FF8F00',
                fontweight='bold', style='italic')

    rect = mpatches.FancyBboxPatch((-2.0, -0.5), 4.0, 0.6, boxstyle="round,pad=0.05",
                                    facecolor='#78909C', edgecolor='#546E7A', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(0, -0.2, '表面', fontsize=10, ha='center', va='center', color='white',
            fontweight='bold')
    ax.text(0, -0.9, '锥形范围发光\n有软边缘过渡', fontsize=9, ha='center',
            color='#666666', style='italic')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'light_types.png')
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'✓ {path}')


# ========================================================================
# 图3: attenuation_curve.png — 点光源衰减曲线
# ========================================================================
def generate_attenuation_curve():
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    d = np.linspace(0, 100, 500)

    configs = [
        {'label': '距离 7  (Kl=0.7, Kq=1.8)',     'Kc': 1.0, 'Kl': 0.7,   'Kq': 1.8,    'color': '#E53935'},
        {'label': '距离 20 (Kl=0.22, Kq=0.20)',    'Kc': 1.0, 'Kl': 0.22,  'Kq': 0.20,   'color': '#FB8C00'},
        {'label': '距离 50 (Kl=0.09, Kq=0.032)',   'Kc': 1.0, 'Kl': 0.09,  'Kq': 0.032,  'color': '#43A047'},
        {'label': '距离 100 (Kl=0.045, Kq=0.0075)', 'Kc': 1.0, 'Kl': 0.045, 'Kq': 0.0075, 'color': '#1E88E5'},
        {'label': '距离 200 (Kl=0.022, Kq=0.0019)', 'Kc': 1.0, 'Kl': 0.022, 'Kq': 0.0019, 'color': '#8E24AA'},
    ]

    for cfg in configs:
        attenuation = 1.0 / (cfg['Kc'] + cfg['Kl'] * d + cfg['Kq'] * d * d)
        ax.plot(d, attenuation, label=cfg['label'], color=cfg['color'], linewidth=2.0)

    ax.set_xlabel('距离 (d)', fontsize=13, fontweight='bold')
    ax.set_ylabel('衰减因子 (Fatt)', fontsize=13, fontweight='bold')
    ax.set_title('点光源距离衰减曲线   Fatt = 1 / (Kc + Kl·d + Kq·d²)',
                 fontsize=14, fontweight='bold', pad=15)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=10, loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0.01, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(80, 0.03, '≈ 0 (可忽略)', fontsize=9, color='gray', style='italic')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'attenuation_curve.png')
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'✓ {path}')


# ========================================================================
# 图4: normal_vector.png — 法向量与光线方向的关系
# ========================================================================
def generate_normal_vector():
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    ax.set_xlim(-2, 6)
    ax.set_ylim(-1, 5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('法向量与光照计算', fontsize=16, fontweight='bold', pad=15)

    surface_x = np.array([-1.5, 5.5])
    surface_y = np.array([0.5, 0.5])
    ax.fill_between(surface_x, surface_y - 0.8, surface_y,
                    color='#78909C', alpha=0.4, zorder=1)
    ax.plot(surface_x, surface_y, color='#546E7A', linewidth=2.5, zorder=2)
    ax.text(4.5, 0.0, '表面', fontsize=11, color='#37474F', fontweight='bold')

    frag_pos = (2.0, 0.5)
    ax.plot(*frag_pos, 'o', color='#E53935', markersize=8, zorder=5)
    ax.text(2.0, 0.1, 'P (片段位置)', fontsize=10, color='#E53935',
            fontweight='bold', ha='center')

    # 法向量 N
    n_end = (2.0, 3.5)
    ax.annotate('', xy=n_end, xytext=frag_pos,
                arrowprops=dict(arrowstyle='->', color='#2196F3', lw=3.0))
    ax.text(2.15, 3.6, 'N (法向量)', fontsize=12, color='#2196F3',
            fontweight='bold')

    # 光线方向 L（从片段指向光源）
    light_pos = (4.5, 4.0)
    ax.annotate('', xy=light_pos, xytext=frag_pos,
                arrowprops=dict(arrowstyle='->', color='#FF9800', lw=2.5))
    ax.text(4.6, 4.1, 'L (指向光源)', fontsize=11, color='#FF9800',
            fontweight='bold')

    bulb = plt.Circle((4.5, 4.0), 0.15, color='#FFEB3B', ec='#FFC107',
                       linewidth=2, zorder=5)
    ax.add_patch(bulb)
    glow = plt.Circle((4.5, 4.0), 0.25, color='#FFEB3B', alpha=0.3,
                       ec='none', zorder=4)
    ax.add_patch(glow)

    # 观察方向 V
    view_pos = (-0.5, 3.5)
    ax.annotate('', xy=view_pos, xytext=frag_pos,
                arrowprops=dict(arrowstyle='->', color='#4CAF50', lw=2.5))
    ax.text(-0.6, 3.7, 'V (观察方向)', fontsize=11, color='#4CAF50',
            fontweight='bold')
    eye = plt.Circle((-0.5, 3.5), 0.15, color='#81C784', ec='#388E3C',
                      linewidth=2, zorder=5)
    ax.add_patch(eye)
    ax.text(-0.5, 3.5, '👁', fontsize=10, ha='center', va='center', zorder=6)

    # 反射方向 R
    r_end = (-0.3, 3.0)
    ax.annotate('', xy=r_end, xytext=frag_pos,
                arrowprops=dict(arrowstyle='->', color='#9C27B0', lw=2.0,
                                linestyle='dashed'))
    ax.text(-0.7, 2.7, 'R (反射方向)', fontsize=10, color='#9C27B0',
            fontweight='bold')

    # θ 角标注
    arc = Arc(frag_pos, 1.4, 1.4, angle=0, theta1=56, theta2=90,
              color='#FF5722', linewidth=1.5, zorder=3)
    ax.add_patch(arc)
    ax.text(1.6, 2.0, 'θ', fontsize=16, color='#FF5722', fontweight='bold',
            style='italic')

    # 公式
    formula_box = dict(boxstyle='round,pad=0.4', facecolor='#ECEFF1',
                       edgecolor='#90A4AE', linewidth=1.5)
    ax.text(0.2, -0.7, 'diffuse = max(N · L, 0)    specular = max(V · R, 0)^shininess',
            fontsize=11, fontweight='bold', color='#333333',
            family='monospace', bbox=formula_box)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'normal_vector.png')
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'✓ {path}')


if __name__ == '__main__':
    print('生成第7篇教程配图...')
    generate_phong_components()
    generate_light_types()
    generate_attenuation_curve()
    generate_normal_vector()
    print('全部完成！')
