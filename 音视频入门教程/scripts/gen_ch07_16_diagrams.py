#!/usr/bin/env python3
"""
为第 7~16 章生成配图（统一脚本）
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib
import os

matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

C = {
    'primary': '#2563EB', 'secondary': '#7C3AED', 'accent': '#F59E0B',
    'success': '#10B981', 'danger': '#EF4444', 'pink': '#EC4899',
    'cyan': '#06B6D4', 'bg': '#F8FAFC', 'grid': '#E2E8F0',
    'text': '#1E293B', 'text_light': '#64748B', 'white': '#FFFFFF',
}
OUT = os.path.join(os.path.dirname(__file__), '..', 'images')
DPI = 150

def B(ax, x, y, w, h, label, color, sub=None, fs=11, a=0.85):
    r = FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.05",facecolor=color,edgecolor='white',linewidth=2.5,alpha=a)
    ax.add_patch(r)
    if sub:
        ax.text(x+w/2,y+h/2+0.13,label,ha='center',va='center',fontsize=fs,fontweight='bold',color='white')
        ax.text(x+w/2,y+h/2-0.18,sub,ha='center',va='center',fontsize=fs-2,color='white',alpha=0.85)
    else:
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=fs,fontweight='bold',color='white')

def A(ax, x1, y1, x2, y2, color=None, lw=2):
    if not color: color = C['text_light']
    ax.annotate('',xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle='->',color=color,lw=lw))

def L(ax, x, y, text, color, fs=9):
    ax.text(x,y,text,ha='center',va='center',fontsize=fs,color=color,fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2',facecolor=color,alpha=0.1,edgecolor=color,linewidth=0.8))

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(); print(f'✓ {name}')

# ============================================================
# Ch7: 解封装 + 解码工作流程
# ============================================================
def gen_ch07():
    fig, axes = plt.subplots(1, 2, figsize=(15, 9))
    fig.patch.set_facecolor(C['bg'])
    fig.suptitle('FFmpeg 核心工作流程', fontsize=16, fontweight='bold', color=C['text'], y=1.0)

    # -- 左：解封装流程 --
    ax = axes[0]; ax.axis('off'); ax.set_xlim(-1,10); ax.set_ylim(-1,10)
    ax.set_title('解封装（Demux）流程', fontsize=13, fontweight='bold', color=C['text'], pad=10)
    steps = [
        (9.0, 'avformat_open_input()', '打开文件，探测格式', C['accent']),
        (7.5, 'avformat_find_stream_info()', '分析流信息', C['accent']),
        (6.0, '遍历 streams', '找到视频/音频流索引', C['success']),
        (4.2, 'av_read_frame()', '循环读取 AVPacket', C['primary']),
        (1.5, 'avformat_close_input()', '关闭文件，释放资源', C['text_light']),
    ]
    for y, name, desc, color in steps:
        B(ax, 1, y, 7.5, 0.8, name, color, sub=desc, fs=10)
    for i in range(len(steps)-1):
        sy = steps[i][0]; ny = steps[i+1][0]
        A(ax, 4.75, sy, 4.75, ny+0.8, C['text_light'])

    # 循环标注
    ax.annotate('', xy=(0.8, 4.2+0.4), xytext=(0.8, 4.2+0.8+0.1),
                arrowprops=dict(arrowstyle='->', color=C['primary'], lw=1.5,
                                connectionstyle='arc3,rad=0.8'))
    ax.text(0.2, 5.1, '循环', fontsize=9, color=C['primary'], fontweight='bold', rotation=90)

    # 分发标注
    ax.text(4.75, 3.5, '按 stream_index 分发：视频包 / 音频包', fontsize=9,
            ha='center', color=C['text_light'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=C['grid'], alpha=0.4))

    # -- 右：解码流程 --
    ax = axes[1]; ax.axis('off'); ax.set_xlim(-1,10); ax.set_ylim(-1,10)
    ax.set_title('解码（Decode）流程', fontsize=13, fontweight='bold', color=C['text'], pad=10)
    steps2 = [
        (9.0, 'avcodec_find_decoder()', '查找解码器', C['success']),
        (7.8, 'avcodec_alloc_context3()', '分配解码器上下文', C['success']),
        (6.6, 'avcodec_parameters_to_context()', '填入流参数', C['success']),
        (5.4, 'avcodec_open2()', '打开解码器', C['success']),
        (3.8, 'avcodec_send_packet()', '送入 AVPacket', C['secondary']),
        (2.4, 'avcodec_receive_frame()', '取出 AVFrame', C['pink']),
        (0.5, 'avcodec_free_context()', '释放解码器', C['text_light']),
    ]
    for y, name, desc, color in steps2:
        B(ax, 0.5, y, 8.5, 0.7, name, color, sub=desc, fs=10)
    for i in range(len(steps2)-1):
        sy = steps2[i][0]; ny = steps2[i+1][0]
        A(ax, 4.75, sy, 4.75, ny+0.7, C['text_light'])

    # send/receive 循环
    ax.annotate('', xy=(0.3, 3.8+0.35), xytext=(0.3, 2.4+0.7+0.1),
                arrowprops=dict(arrowstyle='->', color=C['secondary'], lw=1.5,
                                connectionstyle='arc3,rad=0.8'))
    ax.text(-0.5, 3.5, '循环\nsend/\nrecv', fontsize=8, color=C['secondary'],
            fontweight='bold', ha='center')

    # 返回值标注
    ax.text(4.75, 1.7, 'EAGAIN → 需要更多输入    |    0 → 取到一帧    |    EOF → 完成',
            fontsize=8, ha='center', color=C['text_light'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=C['grid'], alpha=0.4))

    plt.tight_layout()
    save(fig, 'diagram-07-demux-decode-flow.png')

# ============================================================
# Ch8: 视频解码 + 格式转换管线
# ============================================================
def gen_ch08():
    fig, ax = plt.subplots(figsize=(13, 4.5))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-0.5, 13); ax.set_ylim(-0.5, 4)
    ax.set_title('视频解码与格式转换流水线', fontsize=15, fontweight='bold', color=C['text'], pad=15)

    boxes = [
        (0, 1.2, 2.5, 1.5, 'av_read_frame()', C['accent'], 'AVPacket\n(H.264)'),
        (3.3, 1.2, 2.8, 1.5, 'send + receive', C['primary'], 'AVFrame\n(YUV420P)'),
        (6.9, 1.2, 2.5, 1.5, 'sws_scale()', C['cyan'], 'AVFrame\n(RGB24)'),
        (10.2, 1.2, 2.5, 1.5, '显示 / 保存', C['text_light'], '渲染输出'),
    ]
    for x, y, w, h, label, color, sub in boxes:
        B(ax, x, y, w, h, label, color, sub=sub, fs=10)
    for i in range(len(boxes)-1):
        x1 = boxes[i][0]+boxes[i][2]; x2 = boxes[i+1][0]
        A(ax, x1+0.05, 1.95, x2-0.05, 1.95, C['text_light'], lw=2.5)

    # 注释
    ax.text(1.25, 0.7, '解封装', fontsize=9, ha='center', color=C['accent'], fontweight='bold')
    ax.text(4.65, 0.7, '解码', fontsize=9, ha='center', color=C['primary'], fontweight='bold')
    ax.text(8.15, 0.7, '像素格式转换', fontsize=9, ha='center', color=C['cyan'], fontweight='bold')

    ax.text(6.5, 3.3, 'libswscale：YUV→RGB / 缩放 / 像素格式转换',
            fontsize=10, ha='center', color=C['cyan'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['cyan'], alpha=0.08))
    save(fig, 'diagram-08-video-decode-pipeline.png')

# ============================================================
# Ch9: 音频解码 + 重采样管线
# ============================================================
def gen_ch09():
    fig, ax = plt.subplots(figsize=(13, 4.5))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-0.5, 13); ax.set_ylim(-0.5, 4)
    ax.set_title('音频解码与重采样流水线', fontsize=15, fontweight='bold', color=C['text'], pad=15)

    boxes = [
        (0, 1.2, 2.5, 1.5, 'av_read_frame()', C['accent'], 'AVPacket\n(AAC)'),
        (3.3, 1.2, 2.8, 1.5, 'send + receive', C['danger'], 'AVFrame\n(FLTP)'),
        (6.9, 1.2, 2.5, 1.5, 'swr_convert()', C['secondary'], 'PCM\n(S16, 目标格式)'),
        (10.2, 1.2, 2.5, 1.5, 'SDL2 播放', C['text_light'], '扬声器输出'),
    ]
    for x, y, w, h, label, color, sub in boxes:
        B(ax, x, y, w, h, label, color, sub=sub, fs=10)
    for i in range(len(boxes)-1):
        x1 = boxes[i][0]+boxes[i][2]; x2 = boxes[i+1][0]
        A(ax, x1+0.05, 1.95, x2-0.05, 1.95, C['text_light'], lw=2.5)

    ax.text(1.25, 0.7, '解封装', fontsize=9, ha='center', color=C['accent'], fontweight='bold')
    ax.text(4.65, 0.7, '解码', fontsize=9, ha='center', color=C['danger'], fontweight='bold')
    ax.text(8.15, 0.7, '重采样/格式转换', fontsize=9, ha='center', color=C['secondary'], fontweight='bold')

    ax.text(6.5, 3.3, 'libswresample：采样率转换 / 声道转换 / 采样格式转换',
            fontsize=10, ha='center', color=C['secondary'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['secondary'], alpha=0.08))
    save(fig, 'diagram-09-audio-decode-pipeline.png')

# ============================================================
# Ch10: SDL2 渲染架构
# ============================================================
def gen_ch10():
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), gridspec_kw={'width_ratios': [1, 1.3]})
    fig.patch.set_facecolor(C['bg'])
    fig.suptitle('SDL2 视频渲染', fontsize=16, fontweight='bold', color=C['text'], y=1.0)

    # 左：嵌套结构
    ax = axes[0]; ax.axis('off'); ax.set_xlim(-0.5, 8); ax.set_ylim(-0.5, 6)
    ax.set_title('SDL2 渲染对象层级', fontsize=13, fontweight='bold', color=C['text'], pad=10)

    layers = [
        (0, 0, 7.5, 5.3, 'SDL_Window', C['text_light'], '操作系统窗口'),
        (0.5, 0.4, 6.5, 4.0, 'SDL_Renderer', C['primary'], '2D 渲染上下文'),
        (1.2, 1.0, 5.0, 2.5, 'SDL_Texture', C['accent'], 'GPU 纹理（图像数据）'),
    ]
    for x, y, w, h, name, color, desc in layers:
        r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                            facecolor=color, alpha=0.1, edgecolor=color, linewidth=2)
        ax.add_patch(r)
        ax.text(x+0.3, y+h-0.35, name, fontsize=11, fontweight='bold', color=color)
        ax.text(x+0.3, y+h-0.7, desc, fontsize=9, color=C['text_light'])

    # 右：两种渲染路径
    ax = axes[1]; ax.axis('off'); ax.set_xlim(-0.5, 10); ax.set_ylim(-0.5, 6)
    ax.set_title('两种渲染路径对比', fontsize=13, fontweight='bold', color=C['text'], pad=10)

    # 传统
    ax.text(0, 5.3, '传统方式（CPU 转换，浪费性能）：', fontsize=10, color=C['danger'], fontweight='bold')
    trad = [('AVFrame\n(YUV)', C['primary']), ('sws_scale\n(CPU)', C['danger']),
            ('RGB 数据', C['danger']), ('SDL_Texture', C['accent'])]
    for i, (t, c) in enumerate(trad):
        B(ax, i*2.3, 4.0, 2.0, 0.9, t, c, fs=9, a=0.7)
        if i < len(trad)-1: A(ax, i*2.3+2.05, 4.45, i*2.3+2.25, 4.45, C['text_light'])

    # 推荐
    ax.text(0, 3.0, '推荐方式（GPU 转换，高性能）：', fontsize=10, color=C['success'], fontweight='bold')
    opt = [('AVFrame\n(YUV)', C['primary']), ('SDL_Texture\n(IYUV)', C['success']),
           ('GPU 转换\n+ 渲染', C['success'])]
    for i, (t, c) in enumerate(opt):
        B(ax, i*3.0, 1.5, 2.5, 0.9, t, c, fs=9)
        if i < len(opt)-1: A(ax, i*3.0+2.55, 1.95, i*3.0+2.95, 1.95, C['text_light'])

    ax.text(5, 0.5, 'SDL_UpdateYUVTexture() 直接上传 YUV 数据到 GPU',
            fontsize=10, ha='center', color=C['success'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['success'], alpha=0.08))

    plt.tight_layout()
    save(fig, 'diagram-10-sdl2-rendering.png')

# ============================================================
# Ch11: SDL2 音频播放模型
# ============================================================
def gen_ch11():
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-0.5, 14); ax.set_ylim(-0.5, 6.5)
    ax.set_title('SDL2 音频播放：回调模型与线程协作', fontsize=15, fontweight='bold', color=C['text'], pad=15)

    # 主线程
    mx = 1.0
    r = FancyBboxPatch((mx-0.3, 0.5), 5.0, 5.2, boxstyle="round,pad=0.1",
                        facecolor=C['primary'], alpha=0.05, edgecolor=C['primary'], linewidth=1.5, linestyle=':')
    ax.add_patch(r)
    ax.text(mx+2.2, 5.35, '主线程', fontsize=12, fontweight='bold', color=C['primary'], ha='center')

    B(ax, mx, 4.0, 4.4, 0.8, 'FFmpeg 解码', C['primary'], sub='send_packet + receive_frame', fs=10)
    A(ax, mx+2.2, 4.0, mx+2.2, 3.5, C['primary'])
    B(ax, mx, 2.5, 4.4, 0.8, 'swr_convert()', C['secondary'], sub='重采样 → 目标 PCM', fs=10)
    A(ax, mx+2.2, 2.5, mx+2.2, 2.0, C['secondary'])
    B(ax, mx, 1.0, 4.4, 0.8, 'buffer.write()', C['success'], sub='写入共享缓冲区', fs=10)

    # 共享缓冲区
    buf_x = 6.5
    r2 = FancyBboxPatch((buf_x, 1.8), 1.5, 2.5, boxstyle="round,pad=0.06",
                         facecolor=C['accent'], alpha=0.15, edgecolor=C['accent'], linewidth=2)
    ax.add_patch(r2)
    ax.text(buf_x+0.75, 3.6, '共享\n缓冲区', fontsize=10, ha='center', color=C['accent'], fontweight='bold')
    ax.text(buf_x+0.75, 2.2, 'thread\nsafe', fontsize=8, ha='center', color=C['text_light'])
    A(ax, mx+4.4+0.1, 1.4, buf_x-0.05, 2.5, C['success'], lw=2)

    # SDL 线程
    sx = 8.8
    r3 = FancyBboxPatch((sx-0.3, 0.5), 5.2, 5.2, boxstyle="round,pad=0.1",
                         facecolor=C['danger'], alpha=0.05, edgecolor=C['danger'], linewidth=1.5, linestyle=':')
    ax.add_patch(r3)
    ax.text(sx+2.3, 5.35, 'SDL 音频线程', fontsize=12, fontweight='bold', color=C['danger'], ha='center')

    B(ax, sx, 4.0, 4.4, 0.8, 'audio_callback()', C['danger'], sub='SDL 定期调用', fs=10)
    A(ax, sx+2.2, 4.0, sx+2.2, 3.5, C['danger'])
    B(ax, sx, 2.5, 4.4, 0.8, 'buffer.read()', C['accent'], sub='从缓冲区读取数据', fs=10)
    A(ax, sx+2.2, 2.5, sx+2.2, 2.0, C['accent'])
    B(ax, sx, 1.0, 4.4, 0.8, '输出到声卡', C['text_light'], sub='播放声音', fs=10)

    A(ax, buf_x+1.55, 2.9, sx-0.05, 2.9, C['accent'], lw=2)

    plt.tight_layout()
    save(fig, 'diagram-11-sdl2-audio.png')

# ============================================================
# Ch12: 播放器完整架构
# ============================================================
def gen_ch12_arch():
    fig, ax = plt.subplots(figsize=(14, 11))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-1, 15); ax.set_ylim(-1, 12)
    ax.set_title('播放器多线程架构设计', fontsize=16, fontweight='bold', color=C['text'], pad=15)

    cx = 7
    # 媒体文件
    B(ax, cx-1.5, 10.8, 3.0, 0.7, '媒体文件', C['text_light'], fs=11)
    A(ax, cx, 10.8, cx, 10.3, C['text_light'])

    # 解封装线程
    B(ax, cx-2.2, 9.2, 4.4, 1.0, '解封装线程', C['accent'], sub='av_read_frame() 循环读包', fs=12)
    A(ax, cx-1, 9.2, cx-3, 8.6, C['primary'])
    A(ax, cx+1, 9.2, cx+3, 8.6, C['danger'])

    # Packet 队列
    B(ax, cx-5.5, 7.5, 3.5, 1.0, 'Video PKT Queue', C['primary'], sub='PacketQueue', fs=10)
    B(ax, cx+2.0, 7.5, 3.5, 1.0, 'Audio PKT Queue', C['danger'], sub='PacketQueue', fs=10)
    A(ax, cx-3.75, 7.5, cx-3.75, 6.9, C['primary'])
    A(ax, cx+3.75, 7.5, cx+3.75, 6.9, C['danger'])

    # 解码线程
    B(ax, cx-5.5, 5.8, 3.5, 1.0, '视频解码线程', C['primary'], sub='send_packet / receive_frame', fs=10)
    B(ax, cx+2.0, 5.8, 3.5, 1.0, '音频解码线程', C['danger'], sub='send_packet / receive_frame', fs=10)
    A(ax, cx-3.75, 5.8, cx-3.75, 5.2, C['primary'])
    A(ax, cx+3.75, 5.8, cx+3.75, 5.2, C['danger'])

    # Frame 队列
    B(ax, cx-5.5, 4.1, 3.5, 1.0, 'Video Frame Queue', C['primary'], sub='FrameQueue', fs=10, a=0.65)
    B(ax, cx+2.0, 4.1, 3.5, 1.0, 'Audio Frame Queue', C['danger'], sub='FrameQueue', fs=10, a=0.65)
    A(ax, cx-3.75, 4.1, cx-3.75, 3.5, C['primary'])
    A(ax, cx+3.75, 4.1, cx+3.75, 3.5, C['danger'])

    # 渲染/播放
    B(ax, cx-5.5, 2.4, 3.5, 1.0, '视频渲染', C['cyan'], sub='主线程 + SDL2', fs=11)
    B(ax, cx+2.0, 2.4, 3.5, 1.0, 'SDL 音频回调', C['secondary'], sub='SDL 音频线程', fs=11)
    A(ax, cx-3.75, 2.4, cx-3.75, 1.8, C['cyan'])
    A(ax, cx+3.75, 2.4, cx+3.75, 1.8, C['secondary'])

    # 输出
    B(ax, cx-5.5, 0.7, 3.5, 1.0, '屏幕显示', C['text_light'], fs=12, a=0.5)
    B(ax, cx+2.0, 0.7, 3.5, 1.0, '扬声器播放', C['text_light'], fs=12, a=0.5)

    # 音频时钟 → 视频同步
    ax.annotate('', xy=(cx-2.0, 2.9), xytext=(cx+2.0, 2.9),
                arrowprops=dict(arrowstyle='->', color=C['success'], lw=2, connectionstyle='arc3,rad=-0.3'))
    ax.text(cx, 2.2, '音频时钟\n同步视频', fontsize=9, ha='center', color=C['success'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor=C['success'], alpha=0.1))

    # 线程标注
    for tx, label, color in [(cx-3.75, '线程 2', C['primary']), (cx+3.75, '线程 3', C['danger'])]:
        ax.text(tx, 8.95, label, fontsize=8, ha='center', color=color, fontweight='bold')
    ax.text(cx, 10.55, '线程 1', fontsize=8, ha='center', color=C['accent'], fontweight='bold')

    plt.tight_layout()
    save(fig, 'diagram-12-player-architecture.png')

# ============================================================
# Ch12: 队列模型
# ============================================================
def gen_ch12_queue():
    fig, ax = plt.subplots(figsize=(13, 4.5))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-0.5, 13); ax.set_ylim(-0.5, 4)
    ax.set_title('生产者 — 消费者队列模型', fontsize=15, fontweight='bold', color=C['text'], pad=15)

    # PacketQueue
    B(ax, 0.5, 2.0, 2.5, 1.2, '解封装线程', C['accent'], sub='生产者', fs=10)
    A(ax, 3.05, 2.6, 4.0, 2.6, C['accent'], lw=2.5)
    ax.text(3.5, 3.0, 'push', fontsize=9, ha='center', color=C['accent'], fontweight='bold')
    B(ax, 4.0, 2.0, 2.8, 1.2, 'PacketQueue', C['success'], sub='线程安全缓冲区', fs=10)
    A(ax, 6.85, 2.6, 7.5, 2.6, C['success'], lw=2.5)
    ax.text(7.2, 3.0, 'pop', fontsize=9, ha='center', color=C['success'], fontweight='bold')
    B(ax, 7.5, 2.0, 2.5, 1.2, '解码线程', C['primary'], sub='消费者', fs=10)

    # 说明
    ax.text(6.5, 0.8, '队列为空 → pop 阻塞等待    |    队列已满 → push 阻塞等待    |    abort → 唤醒所有等待',
            fontsize=9, ha='center', color=C['text_light'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['grid'], alpha=0.3))

    plt.tight_layout()
    save(fig, 'diagram-12-queue-model.png')

# ============================================================
# Ch13: 多线程模型
# ============================================================
def gen_ch13():
    fig, ax = plt.subplots(figsize=(14, 5.5))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-0.5, 14); ax.set_ylim(-0.5, 5.5)
    ax.set_title('多线程解封装与解码 — 线程模型', fontsize=15, fontweight='bold', color=C['text'], pad=15)

    # 主线程
    B(ax, 0.5, 3.5, 13.0, 1.5, '主线程', C['text_light'], fs=13, a=0.3)
    ax.text(7, 4.55, '初始化 → 启动子线程 → 事件循环（渲染视频帧）→ 等待线程退出 → 清理',
            fontsize=10, ha='center', color=C['text'], fontweight='bold')

    # 子线程
    threads = [
        (0.5, '解封装线程', C['accent'], 'av_read_frame()\npush to pkt queues'),
        (5.0, '视频解码线程', C['primary'], 'send_packet / recv_frame\npush to frame queue'),
        (9.5, '音频解码线程', C['danger'], 'send_packet / recv_frame\npush to frame queue'),
    ]
    for x, name, color, desc in threads:
        A(ax, x+2, 3.5, x+2, 2.8, color)
        ax.text(x+2, 3.15, '创建', fontsize=8, ha='center', color=color, fontweight='bold')
        B(ax, x, 1.0, 4.0, 1.7, name, color, sub=desc, fs=10)

    # join
    for x, _, color, _ in threads:
        A(ax, x+2, 2.7, x+2, 3.5, C['text_light'])

    ax.text(7, 0.3, 'abort_request 标志 → 所有队列 abort() → 子线程退出循环 → 主线程 join() 回收',
            fontsize=9, ha='center', color=C['text_light'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['grid'], alpha=0.3))

    plt.tight_layout()
    save(fig, 'diagram-13-thread-model.png')

# ============================================================
# Ch14: 音视频同步逻辑
# ============================================================
def gen_ch14():
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-0.5, 12); ax.set_ylim(-0.5, 7.5)
    ax.set_title('音视频同步 — 以音频时钟为基准', fontsize=15, fontweight='bold', color=C['text'], pad=15)

    # 流程
    B(ax, 3.5, 6.2, 5.0, 0.8, '获取视频帧 PTS（秒）', C['primary'], fs=11)
    A(ax, 6.0, 6.2, 6.0, 5.7, C['text_light'])
    B(ax, 3.5, 4.8, 5.0, 0.8, '获取当前音频时钟', C['danger'], fs=11)
    A(ax, 6.0, 4.8, 6.0, 4.3, C['text_light'])
    B(ax, 2.5, 3.4, 7.0, 0.8, 'diff = video_pts − audio_clock', C['secondary'], fs=12)
    A(ax, 6.0, 3.4, 6.0, 2.9, C['text_light'])

    # 三分支
    ax.text(6.0, 2.65, '根据 diff 决定操作', fontsize=10, ha='center', color=C['text'], fontweight='bold')

    branches = [
        (0.5, 'diff > 0', '视频超前', '延迟显示\n（等一会儿）', C['accent']),
        (4.2, 'diff ≈ 0', '基本同步', '正常显示', C['success']),
        (7.8, 'diff < 0', '视频滞后', '立即显示\n或丢帧', C['danger']),
    ]
    for x, cond, desc, action, color in branches:
        A(ax, 6.0, 2.4, x+1.7, 1.8, color)
        B(ax, x, 0.5, 3.4, 1.2, cond, color, sub=action, fs=11)
        ax.text(x+1.7, 1.9, desc, fontsize=8, ha='center', color=color, fontweight='bold')

    plt.tight_layout()
    save(fig, 'diagram-14-av-sync.png')

# ============================================================
# Ch15: Seek 流程
# ============================================================
def gen_ch15():
    fig, ax = plt.subplots(figsize=(10, 9))
    fig.patch.set_facecolor(C['bg']); ax.axis('off')
    ax.set_xlim(-0.5, 10); ax.set_ylim(-0.5, 10)
    ax.set_title('Seek 跳转流程', fontsize=15, fontweight='bold', color=C['text'], pad=15)

    steps = [
        (8.8, '用户按下 ← / → 键', C['text_light']),
        (7.6, '计算目标时间位置', C['text_light']),
        (6.4, '设置 seek_request 标志', C['accent']),
        (5.2, '解封装线程检测到标志', C['accent']),
        (4.0, '① 清空 PacketQueue', C['primary']),
        (2.8, '② avformat_seek_file() 跳转', C['success']),
        (1.6, '③ avcodec_flush_buffers() 清空解码器', C['secondary']),
        (0.4, '④ 清空 FrameQueue → 继续读取', C['danger']),
    ]
    for y, label, color in steps:
        B(ax, 1.5, y, 7.0, 0.8, label, color, fs=10)
    for i in range(len(steps)-1):
        A(ax, 5.0, steps[i][0], 5.0, steps[i+1][0]+0.8, C['text_light'])

    ax.text(5.0, -0.2, '所有缓冲区都必须清空，否则会播放旧数据！',
            fontsize=10, ha='center', color=C['danger'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C['danger'], alpha=0.08))

    plt.tight_layout()
    save(fig, 'diagram-15-seek-flow.png')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print('开始生成第 7-16 章配图...\n')
    gen_ch07(); gen_ch08(); gen_ch09(); gen_ch10(); gen_ch11()
    gen_ch12_arch(); gen_ch12_queue(); gen_ch13(); gen_ch14(); gen_ch15()
    print('\n全部完成！')
