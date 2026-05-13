#!/usr/bin/env python3
"""第6篇文章图例：视频渲染与显示"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    'primary': '#1565C0',
    'green': '#2E7D32',
    'orange': '#E65100',
    'purple': '#6A1B9A',
    'teal': '#00838F',
    'red': '#C62828',
    'grey': '#546E7A',
    'bg': '#FAFAFA',
    'light_blue': '#E3F2FD',
    'light_green': '#E8F5E9',
    'light_orange': '#FFF3E0',
    'light_purple': '#F3E5F5',
    'dark': '#212121',
    'mid_grey': '#78909C',
    'sdl_blue': '#0D47A1',
}


def draw_box(ax, x, y, w, h, text, color, fontsize=10, text_color='white',
             alpha=0.95, edgecolor=None, linewidth=1.5):
    ec = edgecolor if edgecolor else 'white'
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.08",
        facecolor=color, edgecolor=ec, linewidth=linewidth, alpha=alpha, zorder=2
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, fontweight='bold', zorder=3)


def draw_outlined_box(ax, x, y, w, h, text, border_color, fontsize=9,
                      text_color=None, fill='white', linewidth=2.5):
    tc = text_color if text_color else border_color
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.1",
        facecolor=fill, edgecolor=border_color, linewidth=linewidth, alpha=0.95, zorder=2
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=tc, fontweight='bold', zorder=3)


def draw_arrow(ax, x1, y1, x2, y2, color='#455A64', lw=1.8):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw), zorder=1)


# ==========================================
# 图1: 视频渲染流水线
# ==========================================
def gen_video_render_pipeline():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(7, 9.6, '视频渲染流水线', ha='center',
            fontsize=18, fontweight='bold', color=COLORS['dark'])
    ax.text(7, 9.2, 'video_display() -> video_image_display() -> SDL_RenderPresent()',
            ha='center', fontsize=9, color=COLORS['mid_grey'], family='monospace')

    # --- 第一行: 数据源 ---
    draw_box(ax, 0.5, 7.5, 2.5, 1.0, 'FrameQueue\n(pictq)', COLORS['purple'], fontsize=10)
    ax.text(1.75, 7.2, 'frame_queue_peek_last()', ha='center', fontsize=7,
            color=COLORS['purple'], family='monospace')

    draw_arrow(ax, 3.0, 8.0, 4.0, 8.0, color=COLORS['purple'], lw=2)

    # 取帧
    draw_outlined_box(ax, 4.0, 7.5, 2.5, 1.0, 'Frame *vp\n(AVFrame)', COLORS['purple'],
                      fontsize=9, fill=COLORS['light_purple'])

    draw_arrow(ax, 6.5, 8.0, 7.5, 8.0, color=COLORS['grey'], lw=2)

    # --- 格式映射 ---
    draw_outlined_box(ax, 7.5, 7.5, 3.0, 1.0,
                      'get_sdl_pix_fmt\n_and_blendmode()', COLORS['teal'],
                      fontsize=8, fill=COLORS['bg'])
    ax.text(9.0, 7.2, 'AVPixelFormat -> SDL Format', ha='center', fontsize=7,
            color=COLORS['teal'])

    draw_arrow(ax, 10.5, 8.0, 11.5, 8.0, color=COLORS['grey'], lw=2)

    draw_outlined_box(ax, 11.5, 7.5, 2.0, 1.0, 'SDL\nPixelFormat', COLORS['teal'],
                      fontsize=9, fill='#E0F7FA')

    # --- 第二行: 纹理管理 & 上传 ---
    draw_arrow(ax, 9.0, 7.5, 9.0, 6.8, color=COLORS['grey'], lw=2)

    draw_outlined_box(ax, 7.3, 5.5, 3.4, 1.2, 'realloc_texture()\n格式/尺寸变化时重建纹理',
                      COLORS['orange'], fontsize=8, fill=COLORS['light_orange'])

    draw_arrow(ax, 9.0, 5.5, 9.0, 4.8, color=COLORS['grey'], lw=2)

    # upload_texture 大框
    upload_x, upload_y = 3.5, 3.0
    upload_w, upload_h = 8.0, 1.6
    box_bg = FancyBboxPatch(
        (upload_x, upload_y), upload_w, upload_h, boxstyle="round,pad=0.15",
        facecolor='#E8EAF6', edgecolor=COLORS['primary'], linewidth=2.5, alpha=0.9, zorder=1
    )
    ax.add_patch(box_bg)
    ax.text(upload_x + upload_w / 2, upload_y + upload_h - 0.2,
            'upload_texture()', ha='center', fontsize=11,
            fontweight='bold', color=COLORS['primary'], zorder=3)

    # YUV 路径
    draw_box(ax, 4.0, 3.2, 3.2, 0.7, 'SDL_UpdateYUVTexture\nYUV420P (IYUV)',
             COLORS['primary'], fontsize=8, alpha=0.9)

    # RGB 路径
    draw_box(ax, 7.8, 3.2, 3.2, 0.7, 'SDL_UpdateTexture\nRGB/RGBA 等格式',
             COLORS['sdl_blue'], fontsize=8, alpha=0.9)

    # --- 第三行: 色彩空间 & 渲染 ---
    draw_arrow(ax, 7.5, 3.0, 7.5, 2.2, color=COLORS['grey'], lw=2)

    # 色彩空间
    draw_outlined_box(ax, 0.5, 1.0, 3.0, 1.0,
                      'set_sdl_yuv\n_conversion_mode()',
                      COLORS['green'], fontsize=8, fill=COLORS['light_green'])
    ax.text(2.0, 0.7, 'BT.601 / BT.709 / JPEG', ha='center', fontsize=7,
            color=COLORS['green'])

    draw_arrow(ax, 3.5, 1.5, 4.8, 1.5, color=COLORS['green'], lw=2)

    # calculate_display_rect
    draw_outlined_box(ax, 4.8, 1.0, 3.0, 1.0,
                      'calculate_display\n_rect()',
                      COLORS['orange'], fontsize=8, fill=COLORS['light_orange'])
    ax.text(6.3, 0.7, 'SAR -> DAR 宽高比适配', ha='center', fontsize=7,
            color=COLORS['orange'])

    draw_arrow(ax, 7.8, 1.5, 8.8, 1.5, color=COLORS['grey'], lw=2)

    # 最终渲染
    draw_box(ax, 8.8, 1.0, 3.5, 1.0, 'SDL_RenderCopyEx\n-> SDL_RenderPresent',
             COLORS['red'], fontsize=9)
    ax.text(10.55, 0.7, '提交到屏幕', ha='center', fontsize=7, color=COLORS['red'])

    # 屏幕图标
    draw_arrow(ax, 12.3, 1.5, 13.2, 1.5, color=COLORS['red'], lw=2)
    screen_box = FancyBboxPatch(
        (13.0, 0.8, ), 0.8, 1.4, boxstyle="round,pad=0.05",
        facecolor=COLORS['dark'], edgecolor=COLORS['mid_grey'], linewidth=2, zorder=2
    )
    ax.add_patch(screen_box)
    inner = FancyBboxPatch(
        (13.1, 1.0), 0.6, 0.9, boxstyle="round,pad=0.02",
        facecolor='#4FC3F7', edgecolor='none', zorder=3
    )
    ax.add_patch(inner)
    ax.text(13.4, 0.55, '显示', ha='center', fontsize=7, color=COLORS['mid_grey'])

    ax.text(7, 0.15, '图 6-1: 视频渲染流水线 (FrameQueue -> SDL Texture -> Screen)',
            ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '06-video-render-pipeline.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 06-video-render-pipeline.png")


# ==========================================
# 图2: calculate_display_rect 宽高比适配
# ==========================================
def gen_display_rect():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('calculate_display_rect() 宽高比适配示意', fontsize=16,
                 fontweight='bold', color=COLORS['dark'], y=0.97)

    scenarios = [
        {
            'title': '场景一: 宽视频适配窄窗口',
            'subtitle': '视频 16:9, 窗口 4:3',
            'win_w': 4.0, 'win_h': 3.0,
            'vid_w': 4.0, 'vid_h': 2.25,
            'color': COLORS['primary'],
            'label': '上下留黑边 (Letterbox)',
        },
        {
            'title': '场景二: 窄视频适配宽窗口',
            'subtitle': '视频 4:3, 窗口 16:9',
            'win_w': 4.8, 'win_h': 2.7,
            'vid_w': 3.6, 'vid_h': 2.7,
            'color': COLORS['green'],
            'label': '左右留黑边 (Pillarbox)',
        },
        {
            'title': '场景三: 非方形像素 (SAR)',
            'subtitle': 'SAR=32:27, 720x576 -> DAR 16:9',
            'win_w': 4.0, 'win_h': 3.0,
            'vid_w': 4.0, 'vid_h': 2.25,
            'color': COLORS['purple'],
            'label': 'SAR 校正后 Letterbox',
        },
    ]

    for ax, sc in zip(axes, scenarios):
        ax.set_xlim(-0.5, 6.0)
        ax.set_ylim(-1.0, 4.5)
        ax.set_aspect('equal')
        ax.axis('off')

        ax.text(2.75, 4.2, sc['title'], ha='center', fontsize=11,
                fontweight='bold', color=COLORS['dark'])
        ax.text(2.75, 3.8, sc['subtitle'], ha='center', fontsize=9,
                color=COLORS['mid_grey'])

        ww, wh = sc['win_w'], sc['win_h']
        vw, vh = sc['vid_w'], sc['vid_h']

        win_x = (5.5 - ww) / 2
        win_y = (3.0 - wh) / 2 + 0.2

        win_rect = plt.Rectangle(
            (win_x, win_y), ww, wh,
            facecolor='#263238', edgecolor='#455A64', linewidth=2.5, zorder=1
        )
        ax.add_patch(win_rect)

        vid_x = win_x + (ww - vw) / 2
        vid_y = win_y + (wh - vh) / 2

        vid_rect = plt.Rectangle(
            (vid_x, vid_y), vw, vh,
            facecolor=sc['color'], edgecolor='white', linewidth=1.5, alpha=0.85, zorder=2
        )
        ax.add_patch(vid_rect)

        ax.text(vid_x + vw / 2, vid_y + vh / 2, '视频画面',
                ha='center', va='center', fontsize=10, color='white',
                fontweight='bold', zorder=3)

        # 尺寸标注 - 窗口
        ax.annotate('', xy=(win_x + ww, win_y - 0.25), xytext=(win_x, win_y - 0.25),
                    arrowprops=dict(arrowstyle='<->', color='#455A64', lw=1.2))
        ax.text(win_x + ww / 2, win_y - 0.5, f'scr_width',
                ha='center', fontsize=7, color='#455A64')

        ax.annotate('', xy=(win_x - 0.25, win_y + wh), xytext=(win_x - 0.25, win_y),
                    arrowprops=dict(arrowstyle='<->', color='#455A64', lw=1.2))
        ax.text(win_x - 0.45, win_y + wh / 2, f'scr\nheight',
                ha='center', fontsize=6, color='#455A64')

        ax.text(2.75, -0.6, sc['label'], ha='center', fontsize=10,
                fontweight='bold', color=sc['color'])

    fig.text(0.5, 0.02,
             '图 6-2: calculate_display_rect 根据 SAR 计算居中显示矩形',
             ha='center', fontsize=10, color='#757575', style='italic')

    plt.tight_layout(rect=[0, 0.06, 1, 0.93])
    plt.savefig(os.path.join(OUTPUT_DIR, '06-display-rect.png'), dpi=150,
                bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print("OK 06-display-rect.png")


if __name__ == '__main__':
    gen_video_render_pipeline()
    gen_display_rect()
    print("\n06 done!")
