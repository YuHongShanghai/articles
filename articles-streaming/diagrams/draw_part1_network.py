"""第一篇（网络编程基础）全部 13 张插图。

运行方式:
    python draw_part1_network.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

from utils import (
    COLORS,
    save_fig,
    new_fig,
    draw_box,
    draw_arrow,
    draw_sequence_arrow,
    draw_dashed_line,
    draw_timeline_entity,
)


# ── 内部辅助 ────────────────────────────────────────────────────


def _flow_down(ax, cx, y_top, steps, colors, bw=1.3, bh=0.42, gap=0.18, fontsize=8):
    """绘制纵向向下的流程图，返回 [(cx, y_bottom, y_top), ...] 列表。"""
    positions = []
    for i, (label, color) in enumerate(zip(steps, colors)):
        yt = y_top - i * (bh + gap)
        yb = yt - bh
        draw_box(ax, cx - bw / 2, yb, bw, bh, label, color=color, fontsize=fontsize)
        positions.append((cx, yb, yt))
        if i > 0:
            draw_arrow(ax, cx, positions[i - 1][1], cx, yt)
    return positions


def _section_bg(ax, x, y, w, h, label, color):
    """带圆角的半透明背景分区 + 顶部标签。"""
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.2",
        facecolor=color, edgecolor=COLORS["border"],
        alpha=0.45, linewidth=1, zorder=0,
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h + 0.15, label,
        ha="center", va="bottom", fontsize=10,
        fontweight="bold", color=COLORS["dark_text"],
    )


# ═══════════════════════════════════════════════════════════════
# 1. Socket 编程模型
# ═══════════════════════════════════════════════════════════════


def draw_socket_model():
    fig, ax = new_fig(14, 7)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ax.text(3.5, 7.6, "TCP 模型", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["primary"])
    ax.text(10.5, 7.6, "UDP 模型", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["secondary"])
    draw_dashed_line(ax, 7, 0.3, 7, 7.4, color=COLORS["border"], lw=2)

    bw, bh, gap = 1.5, 0.55, 0.25
    y_top = 7.0

    # ── TCP Server ──
    ax.text(2.2, y_top + 0.30, "Server", ha="center", fontsize=11,
            fontweight="bold", color=COLORS["dark_text"])
    srv_labels = ["socket()", "bind()", "listen()", "accept()",
                  "recv/send()", "close()"]
    srv_colors = ([COLORS["primary"]] * 3
                  + [COLORS["info"], COLORS["accent"], COLORS["danger"]])
    srv = _flow_down(ax, 2.2, y_top, srv_labels, srv_colors,
                     bw=bw, bh=bh, gap=gap, fontsize=9)

    # ── TCP Client（与 Server 关键步骤对齐）──
    ax.text(5.0, y_top + 0.30, "Client", ha="center", fontsize=11,
            fontweight="bold", color=COLORS["dark_text"])
    cli_labels = ["socket()", "connect()", "send/recv()", "close()"]
    cli_colors = [COLORS["primary"], COLORS["info"],
                  COLORS["accent"], COLORS["danger"]]
    cli_align = [0, 3, 4, 5]
    cli_pos = []
    for i, (label, color) in enumerate(zip(cli_labels, cli_colors)):
        yt = y_top - cli_align[i] * (bh + gap)
        yb = yt - bh
        draw_box(ax, 5.0 - bw / 2, yb, bw, bh, label,
                 color=color, fontsize=9)
        cli_pos.append((5.0, yb, yt))
        if i > 0:
            draw_arrow(ax, 5.0, cli_pos[i - 1][1], 5.0, yt)

    ya = (srv[3][1] + srv[3][2]) / 2
    draw_sequence_arrow(ax, 5.0 - bw / 2, 2.2 + bw / 2, ya,
                        "建立连接", color=COLORS["warning"], fontsize=7.5)
    yd = (srv[4][1] + srv[4][2]) / 2
    draw_sequence_arrow(ax, 2.2 + bw / 2, 5.0 - bw / 2, yd + 0.12,
                        "", color=COLORS["accent"], fontsize=7.5)
    draw_sequence_arrow(ax, 5.0 - bw / 2, 2.2 + bw / 2, yd - 0.12,
                        "", color=COLORS["accent"], fontsize=7.5)
    ax.text(3.6, yd + 0.32, "数据交换", ha="center", fontsize=7.5,
            color=COLORS["accent"])

    # ── UDP Server ──
    ax.text(9.2, y_top + 0.30, "Server", ha="center", fontsize=11,
            fontweight="bold", color=COLORS["dark_text"])
    udp_bh = 0.65
    udp_gap = 0.60
    udp_srv = _flow_down(
        ax, 9.2, y_top,
        ["socket()", "bind()", "recvfrom/\nsendto()"],
        [COLORS["secondary"], COLORS["secondary"], COLORS["accent"]],
        bw=bw, bh=udp_bh, gap=udp_gap, fontsize=9,
    )

    # ── UDP Client ──
    ax.text(12.0, y_top + 0.30, "Client", ha="center", fontsize=11,
            fontweight="bold", color=COLORS["dark_text"])
    udp_cli_align = [0, 2]
    udp_cli_labels = ["socket()", "sendto/\nrecvfrom()"]
    udp_cli_colors = [COLORS["secondary"], COLORS["accent"]]
    udp_cli = []
    for i, (label, color) in enumerate(zip(udp_cli_labels, udp_cli_colors)):
        yt = y_top - udp_cli_align[i] * (udp_bh + udp_gap)
        yb = yt - udp_bh
        draw_box(ax, 12.0 - bw / 2, yb, bw, udp_bh, label,
                 color=color, fontsize=9)
        udp_cli.append((12.0, yb, yt))
        if i > 0:
            draw_arrow(ax, 12.0, udp_cli[i - 1][1], 12.0, yt)

    yud = (udp_srv[2][1] + udp_srv[2][2]) / 2
    draw_sequence_arrow(ax, 9.2 + bw / 2, 12.0 - bw / 2, yud + 0.12,
                        "", color=COLORS["warning"], fontsize=7.5)
    draw_sequence_arrow(ax, 12.0 - bw / 2, 9.2 + bw / 2, yud - 0.12,
                        "", color=COLORS["warning"], fontsize=7.5)
    ax.text(10.6, yud + 0.35, "数据报交换", ha="center", fontsize=7.5,
            color=COLORS["warning"])

    ax.text(3.5, 0.7, "面向连接 · 可靠传输", ha="center", fontsize=10,
            style="italic", color=COLORS["primary"])
    ax.text(10.5, 0.7, "无连接 · 尽力而为", ha="center", fontsize=10,
            style="italic", color=COLORS["secondary"])

    save_fig(fig, "socket_model")


# ═══════════════════════════════════════════════════════════════
# 2. TCP 三次握手 + 四次挥手
# ═══════════════════════════════════════════════════════════════


def draw_tcp_handshake():
    fig, ax = new_fig(10, 7)
    ax.set_xlim(0, 10)
    ax.set_ylim(1.0, 8.5)
    ax.axis("off")

    CL, SR = 2.5, 7.5
    draw_timeline_entity(ax, CL, 8.0, 1.5, "Client", color=COLORS["primary"])
    draw_timeline_entity(ax, SR, 8.0, 1.5, "Server", color=COLORS["accent"])

    ax.text(5.0, 7.65, "三次握手", ha="center", fontsize=12,
            fontweight="bold", color=COLORS["dark_text"])

    y, dy = 7.1, 0.75
    handshake = [
        (CL, SR, "SYN, seq=x",            COLORS["primary"]),
        (SR, CL, "SYN+ACK, seq=y, ack=x+1", COLORS["accent"]),
        (CL, SR, "ACK, ack=y+1",           COLORS["primary"]),
    ]
    for i, (x1, x2, label, clr) in enumerate(handshake):
        draw_sequence_arrow(ax, x1, x2, y - i * dy, label, color=clr, fontsize=7.5)

    states = [
        (CL - 1.0, y + 0.05,         "CLOSED",      COLORS["mid_text"]),
        (CL - 1.0, y - dy + 0.05,    "SYN_SENT",    COLORS["mid_text"]),
        (CL - 1.0, y - 2 * dy - 0.2, "ESTABLISHED", COLORS["accent"]),
        (SR + 1.0, y + 0.05,         "LISTEN",       COLORS["mid_text"]),
        (SR + 1.0, y - dy - 0.2,     "SYN_RCVD",    COLORS["mid_text"]),
        (SR + 1.0, y - 2 * dy - 0.2, "ESTABLISHED", COLORS["accent"]),
    ]
    for sx, sy, txt, clr in states:
        ha = "right" if sx < 5 else "left"
        fw = "bold" if txt == "ESTABLISHED" else "normal"
        ax.text(sx, sy, txt, fontsize=6.5, color=clr, ha=ha, fontweight=fw)

    y_sep = y - 3 * dy + 0.1
    draw_dashed_line(ax, 1.0, y_sep, 9.0, y_sep, color=COLORS["border"], lw=1.5)
    ax.text(5, y_sep + 0.18, "数据传输 ……", ha="center", fontsize=8,
            color=COLORS["mid_text"], style="italic")

    ax.text(5.0, y_sep - 0.45, "四次挥手", ha="center", fontsize=12,
            fontweight="bold", color=COLORS["dark_text"])

    yt = y_sep - 0.85
    teardown = [
        (CL, SR, "FIN, seq=u",    COLORS["danger"]),
        (SR, CL, "ACK, ack=u+1",  COLORS["warning"]),
        (SR, CL, "FIN, seq=v",    COLORS["danger"]),
        (CL, SR, "ACK, ack=v+1",  COLORS["warning"]),
    ]
    for i, (x1, x2, label, clr) in enumerate(teardown):
        draw_sequence_arrow(ax, x1, x2, yt - i * dy, label, color=clr, fontsize=7.5)

    tear_states = [
        (CL - 1.0, yt + 0.05,         "FIN_WAIT_1", COLORS["mid_text"]),
        (CL - 1.0, yt - dy - 0.2,     "FIN_WAIT_2", COLORS["mid_text"]),
        (CL - 1.0, yt - 3 * dy - 0.2, "TIME_WAIT",  COLORS["danger"]),
        (SR + 1.0, yt - dy + 0.05,    "CLOSE_WAIT",  COLORS["mid_text"]),
        (SR + 1.0, yt - 2 * dy - 0.2, "LAST_ACK",    COLORS["mid_text"]),
        (SR + 1.0, yt - 3 * dy - 0.2, "CLOSED",      COLORS["danger"]),
    ]
    for sx, sy, txt, clr in tear_states:
        ha = "right" if sx < 5 else "left"
        ax.text(sx, sy, txt, fontsize=6.5, color=clr, ha=ha)

    save_fig(fig, "tcp_handshake")


# ═══════════════════════════════════════════════════════════════
# 3. TCP vs UDP 雷达图
# ═══════════════════════════════════════════════════════════════


def draw_tcp_vs_udp():
    categories = ["可靠性", "低延迟", "有序性", "吞吐量", "简洁性"]
    N = len(categories)
    tcp = [5, 2, 5, 3, 2]
    udp = [1, 5, 1, 5, 5]

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    tcp_v = tcp + tcp[:1]
    udp_v = udp + udp[:1]
    angles += angles[:1]

    fig = plt.figure(figsize=(8, 8))
    fig.set_facecolor("white")
    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor("white")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=7,
                       color=COLORS["mid_text"])

    ax.plot(angles, tcp_v, "o-", lw=2, label="TCP", color=COLORS["primary"])
    ax.fill(angles, tcp_v, alpha=0.15, color=COLORS["primary"])
    ax.plot(angles, udp_v, "s-", lw=2, label="UDP", color=COLORS["danger"])
    ax.fill(angles, udp_v, alpha=0.15, color=COLORS["danger"])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11, fontweight="bold",
                       color=COLORS["dark_text"])
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=11)
    fig.suptitle("TCP vs UDP 特性对比", fontsize=14, fontweight="bold",
                 y=0.98, color=COLORS["dark_text"])

    save_fig(fig, "tcp_vs_udp")


# ═══════════════════════════════════════════════════════════════
# 4. 阻塞 IO vs IO 多路复用
# ═══════════════════════════════════════════════════════════════


def draw_blocking_vs_multiplexing():
    fig, ax = new_fig(14, 7)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")

    draw_dashed_line(ax, 7, 0.3, 7, 7.5, color=COLORS["border"], lw=2)

    # ── 左侧：阻塞 IO ──
    ax.text(3.5, 7.5, "阻塞 I/O（每连接一线程）", ha="center", fontsize=12,
            fontweight="bold", color=COLORS["danger"])
    for i in range(4):
        y = 6.2 - i * 1.4
        draw_box(ax, 0.5, y, 1.5, 0.55, f"线程 {i + 1}",
                 color=COLORS["primary"], fontsize=8)
        draw_arrow(ax, 2.0, y + 0.275, 3.2, y + 0.275,
                   color=COLORS["mid_text"])
        draw_box(ax, 3.2, y, 1.5, 0.55, f"连接 {i + 1}",
                 color=COLORS["accent"], fontsize=8)
        ax.text(5.0, y + 0.275, "阻塞等待", fontsize=7,
                color=COLORS["danger"], va="center")
    ax.text(3.5, 0.8, "· · · · · ·", ha="center", fontsize=14,
            color=COLORS["mid_text"])
    ax.text(3.5, 0.3, "线程资源开销大，难以支撑高并发", ha="center",
            fontsize=9, color=COLORS["danger"], style="italic")

    # ── 右侧：IO 多路复用 ──
    ax.text(10.5, 7.5, "I/O 多路复用（epoll）", ha="center", fontsize=12,
            fontweight="bold", color=COLORS["accent"])
    draw_box(ax, 7.8, 4.6, 1.7, 0.9, "单线程\nepoll_wait",
             color=COLORS["primary"], fontsize=9)
    draw_arrow(ax, 9.5, 5.05, 10.2, 5.05, color=COLORS["mid_text"])
    draw_box(ax, 10.2, 4.3, 1.6, 1.5, "epoll\n事件循环",
             color=COLORS["secondary"], fontsize=9)
    for i in range(4):
        y = 6.2 - i * 1.4
        draw_box(ax, 12.4, y, 1.2, 0.55, f"连接 {i + 1}",
                 color=COLORS["accent"], fontsize=8)
        draw_arrow(ax, 11.8, 5.05, 12.4, y + 0.275, color=COLORS["info"])
    ax.text(10.5, 0.3, "单线程高效管理数万连接", ha="center",
            fontsize=9, color=COLORS["accent"], style="italic")

    save_fig(fig, "blocking_vs_multiplexing")


# ═══════════════════════════════════════════════════════════════
# 5. epoll 内部原理
# ═══════════════════════════════════════════════════════════════


def draw_epoll_internals():
    fig, ax = new_fig(12, 8)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(6, 8.7, "epoll 内部结构", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    _section_bg(ax, 0.3, 6.0, 11.4, 2.2, "用户空间", COLORS["light_blue"])
    _section_bg(ax, 0.3, 0.5, 11.4, 5.0, "内核空间", COLORS["light_orange"])

    draw_box(ax, 1.0, 6.5, 2.2, 0.8, "应用程序",
             color=COLORS["primary"], fontsize=10)
    draw_box(ax, 4.2, 6.5, 3.0, 0.8, "epoll_wait()",
             color=COLORS["info"], fontsize=10)
    draw_box(ax, 8.2, 6.5, 2.8, 0.8, "处理就绪事件",
             color=COLORS["accent"], fontsize=10)
    draw_arrow(ax, 3.2, 6.9, 4.2, 6.9, color=COLORS["mid_text"])
    draw_arrow(ax, 7.2, 6.9, 8.2, 6.9, color=COLORS["mid_text"])

    draw_box(ax, 4.2, 4.5, 3.6, 0.7, "epoll 实例 (eventpoll)",
             color=COLORS["secondary"], fontsize=9)
    draw_arrow(ax, 5.7, 6.5, 5.7, 5.2, color=COLORS["secondary"], lw=2)

    draw_box(ax, 0.8, 2.3, 4.0, 1.6, "红黑树\n（存储所有注册的 fd）",
             color=COLORS["danger"], fontsize=9)
    draw_box(ax, 7.2, 2.3, 4.0, 1.6, "就绪链表\n（有事件的 fd）",
             color=COLORS["accent"], fontsize=9)
    draw_arrow(ax, 5.0, 4.5, 2.8, 3.9, color=COLORS["danger"])
    draw_arrow(ax, 6.8, 4.5, 9.2, 3.9, color=COLORS["accent"])

    ax.text(3.2, 4.15, "epoll_ctl()\n增 / 删 / 改", ha="center",
            fontsize=7, color=COLORS["danger"], style="italic")
    ax.text(8.5, 4.15, "回调通知\n加入就绪链表", ha="center",
            fontsize=7, color=COLORS["accent"], style="italic")

    for i, x in enumerate([1.0, 2.3, 3.6]):
        draw_box(ax, x, 1.0, 0.9, 0.5, f"fd {i + 3}",
                 color=COLORS["light_red"], text_color=COLORS["dark_text"],
                 fontsize=7)
    for i, x in enumerate([7.5, 8.8]):
        draw_box(ax, x, 1.0, 0.9, 0.5, f"fd {i + 3}",
                 color=COLORS["light_green"], text_color=COLORS["dark_text"],
                 fontsize=7)
        if i < 1:
            ax.annotate("", xy=(x + 1.1, 1.25), xytext=(x + 0.9, 1.25),
                        arrowprops=dict(arrowstyle="->", color=COLORS["accent"],
                                        lw=1.2))

    draw_arrow(ax, 9.2, 3.9, 9.6, 7.3, color=COLORS["accent"], lw=1.2)
    ax.text(10.0, 5.8, "返回\n就绪 fd", fontsize=7, color=COLORS["accent"])

    save_fig(fig, "epoll_internals")


# ═══════════════════════════════════════════════════════════════
# 6. io_uring 架构
# ═══════════════════════════════════════════════════════════════


def draw_io_uring_arch():
    fig, ax = new_fig(12, 8)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(6, 8.7, "io_uring 架构", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    _section_bg(ax, 0.3, 5.5, 11.4, 2.7, "用户空间", COLORS["light_blue"])
    _section_bg(ax, 0.3, 0.5, 11.4, 4.5, "内核空间", COLORS["light_orange"])

    ax.add_patch(FancyBboxPatch(
        (2.5, 3.0), 7.0, 4.5,
        boxstyle="round,pad=0.1,rounding_size=0.3",
        facecolor=COLORS["light_purple"], edgecolor=COLORS["secondary"],
        alpha=0.3, linewidth=2, linestyle="--", zorder=0,
    ))
    ax.text(6.0, 7.55, "共享内存映射 (mmap)", ha="center", fontsize=9,
            fontweight="bold", color=COLORS["secondary"])

    draw_box(ax, 0.5, 6.3, 1.8, 0.7, "应用程序",
             color=COLORS["primary"], fontsize=9)
    draw_box(ax, 3.0, 6.0, 2.8, 1.0, "提交队列 SQ\n(Submission)",
             color=COLORS["info"], fontsize=8)
    draw_box(ax, 7.2, 6.0, 2.8, 1.0, "完成队列 CQ\n(Completion)",
             color=COLORS["accent"], fontsize=8)

    draw_arrow(ax, 2.3, 6.65, 3.0, 6.5, color=COLORS["info"], lw=2)
    ax.text(2.3, 6.2, "提交\n请求", fontsize=7, color=COLORS["info"],
            ha="center")
    draw_arrow(ax, 7.2, 6.85, 2.3, 6.85, color=COLORS["accent"], lw=2)
    ax.text(4.8, 7.1, "获取完成事件", fontsize=7, color=COLORS["accent"],
            ha="center")

    for i in range(5):
        x = 3.1 + i * 0.52
        draw_box(ax, x, 4.5, 0.45, 0.55, f"SQE", color=COLORS["light_cyan"],
                 text_color=COLORS["dark_text"], fontsize=6, radius=0.08)
    for i in range(5):
        x = 7.3 + i * 0.52
        draw_box(ax, x, 4.5, 0.45, 0.55, f"CQE", color=COLORS["light_green"],
                 text_color=COLORS["dark_text"], fontsize=6, radius=0.08)

    ax.annotate("", xy=(5.6, 4.75), xytext=(3.1, 4.75),
                arrowprops=dict(arrowstyle="->", color=COLORS["info"],
                                lw=1, connectionstyle="arc3,rad=-0.15"))
    ax.annotate("", xy=(9.8, 4.75), xytext=(7.3, 4.75),
                arrowprops=dict(arrowstyle="->", color=COLORS["accent"],
                                lw=1, connectionstyle="arc3,rad=-0.15"))

    draw_box(ax, 4.0, 1.5, 4.0, 1.0, "内核工作线程\n（异步处理 I/O）",
             color=COLORS["secondary"], fontsize=9)
    draw_arrow(ax, 4.3, 4.5, 5.0, 2.5, color=COLORS["info"])
    draw_arrow(ax, 7.0, 2.5, 7.8, 4.5, color=COLORS["accent"])
    ax.text(4.0, 3.5, "消费 SQE", fontsize=7, color=COLORS["info"])
    ax.text(7.4, 3.5, "生产 CQE", fontsize=7, color=COLORS["accent"])

    draw_box(ax, 0.5, 2.8, 1.8, 0.8, "零系统调用\n（轮询模式）",
             color=COLORS["warning"], fontsize=7)

    save_fig(fig, "io_uring_arch")


# ═══════════════════════════════════════════════════════════════
# 7. Reactor 模式架构
# ═══════════════════════════════════════════════════════════════


def draw_reactor_pattern():
    fig, ax = new_fig(12, 6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    ax.text(6, 6.6, "Reactor 模式（事件驱动）", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    for i, label in enumerate(["网络事件", "定时事件", "信号事件"]):
        y = 5.0 - i * 1.3
        draw_box(ax, 0.3, y, 1.5, 0.7, label,
                 color=COLORS["warning"], fontsize=8)
        draw_arrow(ax, 1.8, y + 0.35, 3.0, 3.55, color=COLORS["warning"])

    draw_box(ax, 3.0, 2.7, 2.3, 1.7, "Demultiplexer\n(epoll/kqueue)",
             color=COLORS["primary"], fontsize=9)
    draw_arrow(ax, 5.3, 3.55, 6.3, 3.55, color=COLORS["primary"], lw=2)
    draw_box(ax, 6.3, 2.7, 2.0, 1.7, "Dispatcher\n（事件分发）",
             color=COLORS["secondary"], fontsize=9)

    handlers = ["AcceptHandler", "ReadHandler", "WriteHandler"]
    h_colors = [COLORS["info"], COLORS["accent"], COLORS["danger"]]
    for i, (label, clr) in enumerate(zip(handlers, h_colors)):
        y = 5.0 - i * 1.3
        draw_box(ax, 9.4, y, 2.2, 0.7, label, color=clr, fontsize=8)
        draw_arrow(ax, 8.3, 3.55, 9.4, y + 0.35, color=clr)

    ax.text(6, 0.6, "事件源注册 → 多路复用器监听 → 分发器派发 → 处理器执行",
            ha="center", fontsize=9, color=COLORS["mid_text"], style="italic")

    save_fig(fig, "reactor_pattern")


# ═══════════════════════════════════════════════════════════════
# 8. 单 Reactor 单线程
# ═══════════════════════════════════════════════════════════════


def draw_single_reactor():
    fig, ax = new_fig(12, 6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    ax.text(6, 6.6, "单 Reactor 单线程模型", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    for i in range(3):
        y = 5.3 - i * 1.5
        draw_box(ax, 0.3, y, 1.3, 0.6, f"客户端 {i + 1}",
                 color=COLORS["mid_text"], fontsize=8)
        draw_arrow(ax, 1.6, y + 0.3, 2.8, 3.3, color=COLORS["border"])

    draw_box(ax, 2.8, 2.4, 2.5, 1.8, "Reactor\n（单线程）\nepoll_wait",
             color=COLORS["primary"], fontsize=9)

    draw_arrow(ax, 5.3, 3.8, 6.5, 5.4, color=COLORS["info"], lw=2)
    draw_box(ax, 6.5, 5.0, 2.0, 0.8, "Acceptor\n新连接",
             color=COLORS["info"], fontsize=8)

    draw_arrow(ax, 5.3, 3.3, 6.5, 3.3, color=COLORS["accent"], lw=2)
    draw_box(ax, 6.5, 2.7, 2.0, 1.2, "Handler\n读写 + 业务",
             color=COLORS["accent"], fontsize=8)

    draw_box(ax, 9.3, 2.5, 2.4, 1.6, "⚠ 瓶颈\n单线程处理\n所有事件\n无法利用多核",
             color=COLORS["danger"], fontsize=7.5)
    draw_arrow(ax, 8.5, 3.3, 9.3, 3.3, color=COLORS["danger"])

    ax.text(6, 0.7, "所有操作在同一线程：accept、I/O、业务逻辑",
            ha="center", fontsize=9, color=COLORS["mid_text"], style="italic")

    save_fig(fig, "single_reactor")


# ═══════════════════════════════════════════════════════════════
# 9. 主从 Reactor 多线程
# ═══════════════════════════════════════════════════════════════


def draw_multi_reactor():
    fig, ax = new_fig(14, 7)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ax.text(7, 7.6, "主从 Reactor 多线程模型", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    for i in range(3):
        y = 6.0 - i * 1.5
        draw_box(ax, 0.2, y, 1.2, 0.5, f"客户端{i + 1}",
                 color=COLORS["mid_text"], fontsize=7)
        draw_arrow(ax, 1.4, y + 0.25, 2.2, 4.5, color=COLORS["border"])

    draw_box(ax, 2.2, 3.6, 2.2, 1.8, "Main Reactor\n（主线程）\naccept",
             color=COLORS["primary"], fontsize=8)

    draw_arrow(ax, 4.4, 4.5, 5.5, 4.5, color=COLORS["primary"], lw=2)
    ax.text(4.9, 4.75, "分发连接", fontsize=7, color=COLORS["primary"])

    for i in range(3):
        y = 5.8 - i * 1.5
        draw_box(ax, 5.5, y, 2.3, 0.8, f"Sub Reactor {i + 1}\nI/O 读写",
                 color=COLORS["info"], fontsize=7.5)
        draw_arrow(ax, 7.8, y + 0.4, 9.2, y + 0.4, color=COLORS["info"])

    _section_bg(ax, 9.0, 2.5, 4.5, 4.5, "Worker 线程池",
                COLORS["light_green"])
    for i in range(3):
        y = 5.8 - i * 1.5
        draw_box(ax, 9.5, y, 2.2, 0.7, f"Worker {i + 1}\n业务逻辑",
                 color=COLORS["accent"], fontsize=7.5)

    draw_box(ax, 12.0, 4.0, 1.3, 0.8, "任务\n队列",
             color=COLORS["warning"], fontsize=7)

    ax.text(7, 0.7,
            "Main Reactor accept → Sub Reactor I/O → Worker 业务处理",
            ha="center", fontsize=9, color=COLORS["mid_text"], style="italic")

    save_fig(fig, "multi_reactor")


# ═══════════════════════════════════════════════════════════════
# 10. 传统拷贝 vs 零拷贝
# ═══════════════════════════════════════════════════════════════


def draw_zero_copy():
    fig, ax = new_fig(13, 8)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(6.5, 8.7, "传统拷贝 vs 零拷贝（sendfile）", ha="center",
            fontsize=14, fontweight="bold", color=COLORS["dark_text"])

    # ── 传统方式 ──
    ax.text(6.5, 8.0, "传统方式（4 次拷贝 + 4 次上下文切换）", ha="center",
            fontsize=10, fontweight="bold", color=COLORS["danger"])

    labels_t = ["磁盘", "内核缓冲区", "用户缓冲区", "Socket缓冲区", "网卡"]
    colors_t = [COLORS["mid_text"], COLORS["warning"], COLORS["primary"],
                COLORS["info"], COLORS["accent"]]
    bw, bh = 1.8, 0.6
    gx = 0.55
    x0 = 0.4
    yt = 6.9
    for i, (lb, cl) in enumerate(zip(labels_t, colors_t)):
        x = x0 + i * (bw + gx)
        draw_box(ax, x, yt, bw, bh, lb, color=cl, fontsize=8)
        if i > 0:
            px = x0 + (i - 1) * (bw + gx) + bw
            draw_arrow(ax, px, yt + bh / 2, x, yt + bh / 2,
                       color=COLORS["danger"])
            ax.text((px + x) / 2, yt + bh + 0.08, f"拷贝 {i}",
                    ha="center", fontsize=6.5, color=COLORS["danger"])

    ctx = [("用户→内核", 1), ("内核→用户", 2),
           ("用户→内核", 3), ("内核→用户(DMA)", 4)]
    for txt, idx in ctx[:2]:
        ax.text(x0 + idx * (bw + gx) + bw / 2, yt - 0.25, txt,
                ha="center", fontsize=6, color=COLORS["mid_text"])

    # ── 零拷贝 ──
    ax.text(6.5, 5.0, "sendfile 零拷贝（2 次 DMA 拷贝，不经用户空间）",
            ha="center", fontsize=10, fontweight="bold", color=COLORS["accent"])

    labels_z = ["磁盘", "内核缓冲区", "网卡"]
    colors_z = [COLORS["mid_text"], COLORS["warning"], COLORS["accent"]]
    zbw = 2.8
    zgx = 1.8
    zx0 = 1.3
    yz = 3.8
    for i, (lb, cl) in enumerate(zip(labels_z, colors_z)):
        x = zx0 + i * (zbw + zgx)
        draw_box(ax, x, yz, zbw, bh, lb, color=cl, fontsize=9)
        if i > 0:
            px = zx0 + (i - 1) * (zbw + zgx) + zbw
            draw_arrow(ax, px, yz + bh / 2, x, yz + bh / 2,
                       color=COLORS["accent"], lw=2)
            ax.text((px + x) / 2, yz + bh + 0.08, "DMA 拷贝",
                    ha="center", fontsize=7, color=COLORS["accent"])

    ax.text(6.5, 2.8, "✘  不经过用户空间，CPU 零参与数据搬运",
            ha="center", fontsize=11, color=COLORS["accent"], fontweight="bold")

    ax.text(6.5, 1.5, "零拷贝消除了用户空间与内核空间之间的数据拷贝，\n"
            "显著降低 CPU 开销和延迟，适合大文件 / 流媒体传输",
            ha="center", fontsize=9, color=COLORS["mid_text"], style="italic")

    save_fig(fig, "zero_copy")


# ═══════════════════════════════════════════════════════════════
# 11. 带宽估计原理
# ═══════════════════════════════════════════════════════════════


def draw_bandwidth_estimation():
    fig, ax = new_fig(12, 7)
    ax.set_xlim(-0.5, 12.5)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ax.text(6, 7.6, "带宽估计原理", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    SX, RX = 1.0, 11.0
    ax.plot([SX, SX], [1.5, 6.8], "-", color=COLORS["primary"], lw=2)
    draw_box(ax, SX - 0.7, 6.8, 1.4, 0.5, "发送端",
             color=COLORS["primary"], fontsize=10)
    ax.plot([RX, RX], [1.5, 6.8], "-", color=COLORS["accent"], lw=2)
    draw_box(ax, RX - 0.7, 6.8, 1.4, 0.5, "接收端",
             color=COLORS["accent"], fontsize=10)

    cloud = mpatches.Ellipse(
        (6, 4.8), 4, 1.8, facecolor=COLORS["light_blue"],
        edgecolor=COLORS["info"], lw=2, zorder=0,
    )
    ax.add_patch(cloud)
    ax.text(6, 4.8, "网络链路\n（带宽 B，延迟 d）", ha="center",
            va="center", fontsize=9, color=COLORS["dark_text"])

    pkt_ys = [6.3, 5.8, 5.3, 4.8]
    pkt_yr = [5.6, 4.9, 4.2, 3.4]
    for i in range(4):
        ax.plot(SX, pkt_ys[i], "s", color=COLORS["primary"], ms=6, zorder=5)
        ax.text(SX - 0.55, pkt_ys[i], f"P{i + 1}", fontsize=7,
                color=COLORS["primary"], va="center", ha="right")
        ax.plot(RX, pkt_yr[i], "s", color=COLORS["accent"], ms=6, zorder=5)
        ax.text(RX + 0.55, pkt_yr[i], f"P{i + 1}", fontsize=7,
                color=COLORS["accent"], va="center", ha="left")
        ax.annotate(
            "", xy=(RX, pkt_yr[i]), xytext=(SX, pkt_ys[i]),
            arrowprops=dict(arrowstyle="->", color=COLORS["info"],
                            lw=1, alpha=0.5),
        )

    ax.annotate(
        "", xy=(0.3, pkt_ys[0]), xytext=(0.3, pkt_ys[1]),
        arrowprops=dict(arrowstyle="<->", color=COLORS["primary"], lw=1.5),
    )
    ax.text(-0.3, (pkt_ys[0] + pkt_ys[1]) / 2, "Δt_s\n发送间隔",
            fontsize=7, color=COLORS["primary"], ha="center", va="center")

    ax.annotate(
        "", xy=(11.7, pkt_yr[0]), xytext=(11.7, pkt_yr[1]),
        arrowprops=dict(arrowstyle="<->", color=COLORS["accent"], lw=1.5),
    )
    ax.text(12.3, (pkt_yr[0] + pkt_yr[1]) / 2, "Δt_r\n接收间隔",
            fontsize=7, color=COLORS["accent"], ha="center", va="center")

    ax.text(6, 1.8, "可用带宽估计:  B ≈ 数据包大小 × Δt_s / Δt_r",
            ha="center", fontsize=10, fontweight="bold",
            color=COLORS["dark_text"],
            bbox=dict(boxstyle="round,pad=0.3",
                      facecolor=COLORS["light_purple"],
                      edgecolor=COLORS["secondary"]))
    ax.text(6, 0.9, "若 Δt_r > Δt_s → 链路拥塞，可用带宽下降",
            ha="center", fontsize=9, color=COLORS["mid_text"], style="italic")

    save_fig(fig, "bandwidth_estimation")


# ═══════════════════════════════════════════════════════════════
# 12. Wireshark 抓包流程
# ═══════════════════════════════════════════════════════════════


def draw_wireshark_capture():
    fig, ax = new_fig(13, 7)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ax.text(6.5, 7.6, "Wireshark 抓包流程", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    draw_box(ax, 0.3, 5.0, 2.0, 1.5, "推流端\n(FFmpeg/OBS)",
             color=COLORS["primary"], fontsize=9)
    cloud = mpatches.Ellipse(
        (5.5, 5.75), 3.0, 1.2, facecolor=COLORS["light_blue"],
        edgecolor=COLORS["info"], lw=2, zorder=0,
    )
    ax.add_patch(cloud)
    ax.text(5.5, 5.75, "网络传输", ha="center", va="center",
            fontsize=10, color=COLORS["dark_text"])

    draw_box(ax, 8.2, 5.0, 2.0, 1.5, "流媒体\n服务器",
             color=COLORS["accent"], fontsize=9)
    draw_box(ax, 10.8, 5.0, 1.8, 1.5, "播放端\n(VLC)",
             color=COLORS["secondary"], fontsize=9)

    draw_arrow(ax, 2.3, 5.75, 4.0, 5.75, color=COLORS["primary"], lw=2)
    draw_arrow(ax, 7.0, 5.75, 8.2, 5.75, color=COLORS["accent"], lw=2)
    draw_arrow(ax, 10.2, 5.75, 10.8, 5.75, color=COLORS["secondary"], lw=2)

    ax.text(2.5, 4.7, "RTP/RTMP/SRT", fontsize=7,
            color=COLORS["primary"], style="italic")

    draw_dashed_line(ax, 5.5, 5.0, 5.5, 3.5, color=COLORS["danger"], lw=2)
    ax.text(5.5, 4.85, "▼ 镜像 / 抓包", ha="center", fontsize=8,
            color=COLORS["danger"], fontweight="bold")
    draw_box(ax, 4.0, 2.5, 3.0, 1.0, "tcpdump / tshark\n抓包点",
             color=COLORS["danger"], fontsize=9)

    draw_arrow(ax, 5.5, 2.5, 5.5, 1.8, color=COLORS["warning"], lw=2)
    draw_box(ax, 4.5, 1.0, 2.0, 0.8, ".pcap 文件",
             color=COLORS["warning"], fontsize=9)

    draw_arrow(ax, 6.5, 1.4, 8.0, 1.4, color=COLORS["info"], lw=2)
    draw_box(ax, 8.0, 0.7, 4.0, 1.4, "Wireshark 分析\n协议解析 · 流量统计\n丢包 / 延迟诊断",
             color=COLORS["info"], fontsize=8)

    save_fig(fig, "wireshark_capture")


# ═══════════════════════════════════════════════════════════════
# 13. 性能调优层次
# ═══════════════════════════════════════════════════════════════


def draw_optimization_layers():
    fig, ax = new_fig(10, 8)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(5, 8.7, "性能调优层次", ha="center", fontsize=14,
            fontweight="bold", color=COLORS["dark_text"])

    layers = [
        ("系统内核层", "sysctl 参数 · 文件描述符 · 零拷贝",
         COLORS["primary"]),
        ("网络协议层", "Socket 选项 · TCP 调优 · 拥塞控制",
         COLORS["secondary"]),
        ("应用框架层", "Reactor 模式 · 线程模型 · 连接池",
         COLORS["info"]),
        ("业务逻辑层", "缓冲管理 · 编解码优化 · 调度策略",
         COLORS["accent"]),
    ]

    full_w = 8.0
    bh = 1.3
    gap = 0.25
    y0 = 1.2
    for i, (title, desc, color) in enumerate(layers):
        y = y0 + i * (bh + gap)
        w = full_w - i * 0.8
        x = (10 - w) / 2
        draw_box(ax, x, y, w, bh, "", color=color, fontsize=10, alpha=0.92)
        ax.text(x + w / 2, y + bh / 2 + 0.2, title, ha="center",
                va="center", fontsize=12, color="white",
                fontweight="bold", zorder=3)
        ax.text(x + w / 2, y + bh / 2 - 0.22, desc, ha="center",
                va="center", fontsize=8, color=COLORS["light_bg"], zorder=3)

    top_y = y0 + len(layers) * (bh + gap) - gap + 0.05
    ax.annotate(
        "", xy=(0.6, top_y), xytext=(0.6, y0),
        arrowprops=dict(arrowstyle="->", color=COLORS["dark_text"], lw=2.5),
    )
    mid_y = y0 + (top_y - y0) / 2
    ax.text(0.25, mid_y, "调\n优\n方\n向", ha="center", fontsize=10,
            color=COLORS["dark_text"], fontweight="bold", va="center",
            linespacing=1.6)

    ax.text(5, 0.4, "从底层到上层逐步优化，底层优化效果最显著",
            ha="center", fontsize=9, color=COLORS["mid_text"], style="italic")

    save_fig(fig, "optimization_layers")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════


def main():
    print("正在生成第一篇（网络编程基础）插图 …\n")
    draw_socket_model()
    draw_tcp_handshake()
    draw_tcp_vs_udp()
    draw_blocking_vs_multiplexing()
    draw_epoll_internals()
    draw_io_uring_arch()
    draw_reactor_pattern()
    draw_single_reactor()
    draw_multi_reactor()
    draw_zero_copy()
    draw_bandwidth_estimation()
    draw_wireshark_capture()
    draw_optimization_layers()
    print("\n✔ 全部 13 张插图生成完毕!")


if __name__ == "__main__":
    main()
