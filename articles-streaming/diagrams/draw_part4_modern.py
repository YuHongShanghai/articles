#!/usr/bin/env python3
"""第四篇：现代流媒体协议 —— 全部 11 张技术插图。"""

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
    no_axes,
    draw_box,
    draw_arrow,
    draw_brace_text,
    draw_sequence_arrow,
    draw_dashed_line,
    draw_timeline_entity,
)

C = COLORS


# ── 共用小工具 ──────────────────────────────────────────────────────────

def _setup(ax, w, h):
    """关闭坐标轴并设定画布范围。"""
    ax.axis("off")
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)


def _bg(ax, x, y, w, h, color, alpha=0.25):
    r = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.12",
        facecolor=color, edgecolor="none", alpha=alpha, zorder=0,
    )
    ax.add_patch(r)


def _text(ax, x, y, s, **kw):
    kw.setdefault("ha", "center")
    kw.setdefault("va", "center")
    kw.setdefault("fontsize", 9)
    kw.setdefault("color", C["dark_text"])
    ax.text(x, y, s, **kw)


def _title(ax, cx, y, s, fs=14):
    ax.text(cx, y, s, ha="center", va="center",
            fontsize=fs, fontweight="bold", color=C["dark_text"])


def _bracket_h(ax, x1, x2, y, label, color=C["danger"], offset=0.25, fs=9):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="<->", color=color, lw=2))
    ax.text((x1 + x2) / 2, y + offset, label, ha="center", va="bottom",
            fontsize=fs, fontweight="bold", color=color)


# ================================================================
# 1. HLS 架构图
# ================================================================
def draw_hls_architecture():
    W, H = 14, 7
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.5, "HLS 协议架构")

    # 三段背景
    _bg(ax, 0.3, 0.3, 3.9, 5.2, C["light_blue"])
    _text(ax, 2.25, 5.8, "服务端 (Server)", fontsize=11,
          fontweight="bold", color=C["primary"])

    _bg(ax, 4.6, 0.3, 4.6, 5.2, C["light_green"])
    _text(ax, 6.9, 5.8, "CDN 分发网络", fontsize=11,
          fontweight="bold", color=C["accent"])

    _bg(ax, 9.6, 0.3, 4.1, 5.2, C["light_purple"])
    _text(ax, 11.65, 5.8, "客户端 (Client)", fontsize=11,
          fontweight="bold", color=C["secondary"])

    # Server
    draw_box(ax, 0.6, 3.8, 3.3, 0.8, "音视频编码器", C["primary"], fontsize=10)
    draw_box(ax, 0.6, 2.3, 3.3, 0.8, "流切片器 (Segmenter)", C["info"], fontsize=9)
    draw_box(ax, 0.6, 0.7, 1.4, 0.9, ".ts 切片", C["warning"], fontsize=9)
    draw_box(ax, 2.5, 0.7, 1.4, 0.9, ".m3u8", C["accent"], fontsize=9)

    draw_arrow(ax, 2.25, 3.8, 2.25, 3.1, C["mid_text"])
    draw_arrow(ax, 1.6, 2.3, 1.3, 1.6, C["mid_text"])
    draw_arrow(ax, 2.9, 2.3, 3.2, 1.6, C["mid_text"])

    # CDN
    draw_box(ax, 5.2, 3.8, 3.4, 0.8, "源站 (Origin)", C["accent"])
    draw_box(ax, 5.0, 1.8, 1.7, 0.7, "边缘节点 A", C["accent"], fontsize=8)
    draw_box(ax, 7.1, 1.8, 1.7, 0.7, "边缘节点 B", C["accent"], fontsize=8)
    draw_box(ax, 6.05, 0.6, 1.7, 0.7, "边缘节点 C", C["accent"], fontsize=8)

    draw_arrow(ax, 3.9, 4.2, 5.2, 4.2, C["mid_text"], lw=2)
    _text(ax, 4.55, 4.45, "HTTP", fontsize=7, color=C["mid_text"])

    draw_arrow(ax, 6.9, 3.8, 5.85, 2.5, C["mid_text"])
    draw_arrow(ax, 6.9, 3.8, 7.95, 2.5, C["mid_text"])
    draw_arrow(ax, 6.9, 3.8, 6.9, 1.3, C["mid_text"])

    # Client
    draw_box(ax, 10.0, 3.3, 3.3, 1.0, "HLS 播放器", C["secondary"], fontsize=11)
    draw_box(ax, 10.0, 1.6, 3.3, 0.9, "ABR 自适应引擎", C["secondary"],
             fontsize=9, alpha=0.8)

    draw_arrow(ax, 8.8, 2.15, 10.0, 3.8, C["mid_text"], lw=2)
    draw_arrow(ax, 11.65, 3.3, 11.65, 2.5, C["mid_text"])

    save_fig(fig, "hls_architecture")


# ================================================================
# 2. HLS 多码率自适应
# ================================================================
def draw_hls_abr():
    W, H = 14, 8
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.4, "HLS 多码率自适应 (ABR)")

    # Master Playlist
    draw_box(ax, 0.5, 3.2, 2.8, 1.5, "Master\nPlaylist", C["primary"], fontsize=11)

    # 四级 Media Playlist + segments
    profiles = [
        ("1080p  5 Mbps", C["danger"]),
        ("720p   3 Mbps", C["warning"]),
        ("480p   1.5 Mbps", C["accent"]),
        ("360p   0.8 Mbps", C["info"]),
    ]
    y0 = 6.2
    dy = 1.5
    for i, (label, color) in enumerate(profiles):
        y = y0 - i * dy
        draw_box(ax, 4.5, y, 3.6, 0.9, f"Media Playlist  {label}", color, fontsize=8)
        for j in range(4):
            sx = 8.6 + j * 1.2
            draw_box(ax, sx, y + 0.05, 1.0, 0.8, f"seg{j + 1}", color,
                     fontsize=7, alpha=0.7)
        draw_arrow(ax, 3.3, 3.95, 4.5, y + 0.45, C["mid_text"], lw=1.2)

    # 播放器
    draw_box(ax, 0.3, 0.5, 3.2, 1.2, "HLS 播放器", C["secondary"], fontsize=11)
    _text(ax, 1.9, 0.2, "根据网络带宽自动切换码率 ↕", fontsize=8, color=C["mid_text"])

    draw_arrow(ax, 1.9, 1.7, 1.9, 3.2, C["secondary"], style="<->", lw=2)
    _text(ax, 2.8, 2.45, "带宽\n检测", fontsize=8, color=C["secondary"])

    save_fig(fig, "hls_abr")


# ================================================================
# 3. LL-HLS vs 传统 HLS 延迟对比
# ================================================================
def draw_ll_hls():
    W, H = 14, 9
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.4, "LL-HLS  vs  传统 HLS  延迟对比")

    # ── 上半：传统 HLS ──
    _bg(ax, 0.3, 4.6, 13.4, 3.5, C["light_red"])
    _text(ax, 2.0, 7.8, "传统 HLS", fontsize=12, fontweight="bold", color=C["danger"])

    # 时间轴
    ax.annotate("", xy=(13.2, 5.0), xytext=(0.6, 5.0),
                arrowprops=dict(arrowstyle="->", color=C["mid_text"], lw=1))
    _text(ax, 13.5, 5.0, "t", fontsize=9, color=C["mid_text"])

    # 完整切片
    for i in range(3):
        x = 1.0 + i * 3.8
        c = C["primary"] if i % 2 == 0 else C["info"]
        draw_box(ax, x, 6.5, 3.4, 0.7, f"完整切片 #{i + 1}  (6 s)", c, fontsize=9)

    # 下载表示
    draw_box(ax, 1.0, 5.3, 3.4, 0.6, "等待完整切片下载", C["warning"], fontsize=8)
    _bracket_h(ax, 1.0, 8.6, 5.15, "", C["danger"], offset=0.0)
    _text(ax, 10.5, 6.9, "端到端延迟", fontsize=9, color=C["danger"])
    _text(ax, 10.5, 6.4, "15 – 30 秒", fontsize=13, fontweight="bold", color=C["danger"])

    # ── 下半：LL-HLS ──
    _bg(ax, 0.3, 0.3, 13.4, 3.8, C["light_green"])
    _text(ax, 2.0, 3.8, "LL-HLS", fontsize=12, fontweight="bold", color=C["accent"])

    ax.annotate("", xy=(13.2, 0.7), xytext=(0.6, 0.7),
                arrowprops=dict(arrowstyle="->", color=C["mid_text"], lw=1))
    _text(ax, 13.5, 0.7, "t", fontsize=9, color=C["mid_text"])

    # Partial segments
    for i in range(11):
        x = 1.0 + i * 1.05
        c = C["accent"] if i % 2 == 0 else C["info"]
        draw_box(ax, x, 2.6, 0.85, 0.6, f"P{i + 1}", c, fontsize=7)
    _text(ax, 7.0, 2.15, "Partial Segments  +  Preload Hints", fontsize=9,
          color=C["accent"])

    draw_box(ax, 1.0, 1.0, 1.05, 0.5, "下载", C["accent"], fontsize=7)
    _bracket_h(ax, 1.0, 2.3, 0.85, "", C["accent"], offset=0.0)
    _text(ax, 10.5, 2.9, "端到端延迟", fontsize=9, color=C["accent"])
    _text(ax, 10.5, 2.4, "2 – 3 秒", fontsize=13, fontweight="bold", color=C["accent"])

    save_fig(fig, "ll_hls")


# ================================================================
# 4. DASH 架构图
# ================================================================
def draw_dash_architecture():
    W, H = 14, 7
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.5, "DASH 协议架构")

    # 三段
    _bg(ax, 0.3, 0.3, 4.0, 5.2, C["light_blue"])
    _text(ax, 2.3, 5.8, "内容准备\n(Content Preparation)", fontsize=10,
          fontweight="bold", color=C["primary"])

    _bg(ax, 4.7, 0.3, 4.4, 5.2, C["light_green"])
    _text(ax, 6.9, 5.8, "分发 (CDN)", fontsize=10,
          fontweight="bold", color=C["accent"])

    _bg(ax, 9.5, 0.3, 4.2, 5.2, C["light_purple"])
    _text(ax, 11.6, 5.8, "DASH 客户端", fontsize=10,
          fontweight="bold", color=C["secondary"])

    # Content Preparation
    draw_box(ax, 0.6, 3.8, 3.4, 0.8, "编码 + 封装", C["primary"])
    draw_box(ax, 0.6, 2.2, 1.5, 0.8, "MPD 描述", C["info"], fontsize=9)
    draw_box(ax, 2.5, 2.2, 1.5, 0.8, "Segments", C["warning"], fontsize=9)
    draw_box(ax, 0.6, 0.7, 3.4, 0.8, "HTTP 服务器", C["primary"], alpha=0.8)

    draw_arrow(ax, 1.6, 3.8, 1.35, 3.0, C["mid_text"])
    draw_arrow(ax, 2.7, 3.8, 3.25, 3.0, C["mid_text"])
    draw_arrow(ax, 2.3, 2.2, 2.3, 1.5, C["mid_text"])

    # CDN
    draw_box(ax, 5.1, 3.8, 3.6, 0.8, "CDN 源站", C["accent"])
    draw_box(ax, 5.1, 1.8, 1.6, 0.7, "边缘节点", C["accent"], fontsize=8)
    draw_box(ax, 7.1, 1.8, 1.6, 0.7, "边缘节点", C["accent"], fontsize=8)

    draw_arrow(ax, 4.0, 1.1, 5.1, 4.2, C["mid_text"], lw=2)
    draw_arrow(ax, 6.9, 3.8, 5.9, 2.5, C["mid_text"])
    draw_arrow(ax, 6.9, 3.8, 7.9, 2.5, C["mid_text"])

    # DASH Client
    draw_box(ax, 9.8, 3.8, 3.6, 0.8, "DASH 播放器", C["secondary"])
    draw_box(ax, 9.8, 2.2, 3.6, 0.8, "ABR 控制器", C["secondary"], alpha=0.8)
    draw_box(ax, 9.8, 0.7, 3.6, 0.8, "解码 / 渲染", C["secondary"], alpha=0.6)

    draw_arrow(ax, 8.7, 2.15, 9.8, 4.2, C["mid_text"], lw=2)
    draw_arrow(ax, 11.6, 3.8, 11.6, 3.0, C["mid_text"])
    draw_arrow(ax, 11.6, 2.2, 11.6, 1.5, C["mid_text"])

    _text(ax, 4.35, 4.6, "HTTP", fontsize=7, color=C["mid_text"])

    save_fig(fig, "dash_architecture")


# ================================================================
# 5. MPD 层次结构（树形）
# ================================================================
def draw_mpd_hierarchy():
    W, H = 14, 9
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.3, "MPD 文件层次结构")

    bw = 2.0
    bh = 0.65

    def _node(cx, cy, label, color, w=bw, h=bh, fs=9):
        draw_box(ax, cx - w / 2, cy - h / 2, w, h, label, color, fontsize=fs)

    def _conn(px, py, cx, cy):
        draw_arrow(ax, px, py - bh / 2, cx, cy + bh / 2, C["mid_text"])

    # Level 0
    _node(7, 7.5, "MPD", C["primary"], fs=11)

    # Level 1 – Periods
    p_xs = [3.5, 7, 10.5]
    for cx, lab in zip(p_xs, ["Period 1", "Period 2", "Period …"]):
        _node(cx, 6.0, lab, C["info"])
        _conn(7, 7.5, cx, 6.0)

    # Level 2 – AdaptationSets (展开 Period 1)
    as_xs = [2.0, 5.0]
    as_labels = ["AdaptationSet\n(视频)", "AdaptationSet\n(音频)"]
    as_colors = [C["accent"], C["warning"]]
    for cx, lab, col in zip(as_xs, as_labels, as_colors):
        _node(cx, 4.3, lab, col, w=2.2, h=0.8, fs=8)
        _conn(3.5, 6.0, cx, 4.3)

    _text(ax, 8.5, 4.3, "…", fontsize=14, color=C["mid_text"])

    # Level 3 – Representations (展开视频 AS)
    rep_xs = [0.8, 2.0, 3.2]
    rep_labels = ["1080p\n5 Mbps", "720p\n3 Mbps", "480p\n1.5 Mbps"]
    for cx, lab in zip(rep_xs, rep_labels):
        _node(cx, 2.5, lab, C["secondary"], w=1.1, h=0.8, fs=7)
        _conn(2.0, 4.3, cx, 2.5)

    # Level 4 – Segments (展开 1080p)
    seg_xs = [0.2, 0.8, 1.4]
    for i, cx in enumerate(seg_xs):
        _node(cx, 1.0, f"Seg {i + 1}", C["danger"], w=0.55, h=0.55, fs=6)
        _conn(0.8, 2.5, cx, 1.0)

    # 层级标注
    levels = [
        (7.5, "根文档"),
        (6.0, "时间段"),
        (4.3, "自适应集"),
        (2.5, "码率表示"),
        (1.0, "媒体分段"),
    ]
    for ly, lab in levels:
        _text(ax, 12.8, ly, f"← {lab}", fontsize=8, ha="left", color=C["mid_text"])

    save_fig(fig, "mpd_hierarchy")


# ================================================================
# 6. ABR 算法对比
# ================================================================
def draw_abr_algorithms():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.set_facecolor("white")
    fig.suptitle("ABR 算法对比", fontsize=14, fontweight="bold",
                 color=C["dark_text"], y=0.97)

    # ── 左图：BBA（基于缓冲区水位） ──
    ax1 = axes[0]
    ax1.set_facecolor("white")
    ax1.set_title("BBA — 基于缓冲区水位", fontsize=11, fontweight="bold",
                  color=C["primary"], pad=10)
    ax1.set_xlabel("缓冲区水位 (秒)", fontsize=9)
    ax1.set_ylabel("选择码率 (Mbps)", fontsize=9)

    buf = np.array([0, 5, 10, 15, 20, 30, 40, 50, 60])
    rate = np.array([0.5, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 5.0])

    ax1.fill_between(buf, rate, alpha=0.15, color=C["primary"])
    ax1.plot(buf, rate, "-o", color=C["primary"], lw=2.5, markersize=5)

    ax1.axvspan(0, 10, alpha=0.08, color=C["danger"])
    ax1.axvspan(10, 40, alpha=0.08, color=C["warning"])
    ax1.axvspan(40, 60, alpha=0.08, color=C["accent"])

    ax1.text(5, 4.5, "低水位\n保守", ha="center", fontsize=8, color=C["danger"])
    ax1.text(25, 4.5, "线性增长区", ha="center", fontsize=8, color=C["warning"])
    ax1.text(50, 4.5, "高水位\n激进", ha="center", fontsize=8, color=C["accent"])

    ax1.set_xlim(0, 60)
    ax1.set_ylim(0, 5.5)
    ax1.grid(True, alpha=0.3)

    # ── 右图：MPC（模型预测控制） ──
    ax2 = axes[1]
    ax2.set_facecolor("white")
    ax2.set_title("MPC — 模型预测控制", fontsize=11, fontweight="bold",
                  color=C["secondary"], pad=10)
    ax2.set_xlabel("时间 (切片序号)", fontsize=9)
    ax2.set_ylabel("码率 (Mbps)", fontsize=9)

    t = np.arange(1, 21)
    bw_actual = 3.0 + 1.5 * np.sin(t * 0.5) + np.random.RandomState(42).randn(20) * 0.3
    bw_predict = np.convolve(bw_actual, np.ones(3) / 3, mode="same")
    chosen = np.clip(np.round(bw_predict * 0.8 * 2) / 2, 0.5, 5.0)

    ax2.plot(t, bw_actual, "--", color=C["mid_text"], lw=1.2, label="实际带宽")
    ax2.plot(t, bw_predict, "-", color=C["warning"], lw=2, label="预测带宽")
    ax2.step(t, chosen, "-", color=C["secondary"], lw=2.5, where="mid", label="选择码率")

    ax2.fill_between(t, chosen, alpha=0.12, step="mid", color=C["secondary"])
    ax2.set_xlim(1, 20)
    ax2.set_ylim(0, 6)
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, "abr_algorithms")


# ================================================================
# 7. SRT 协议架构（分层）
# ================================================================
def draw_srt_architecture():
    W, H = 12, 8
    fig, ax = new_fig(W, 6.5)
    _setup(ax, W, H)
    ax.set_ylim(0.5, H)
    _title(ax, W / 2, H - 0.3, "SRT 协议架构")

    layers = [
        ("应用层 (Application)", C["secondary"], 6.2),
        ("SRT 协议层", C["primary"], 4.8),
        ("UDP", C["accent"], 3.4),
        ("IP 网络层", C["info"], 2.0),
    ]

    lw, lh = 5.0, 0.9
    lx = 1.5
    for label, color, y in layers:
        draw_box(ax, lx, y, lw, lh, label, color, fontsize=11)

    for i in range(len(layers) - 1):
        draw_arrow(ax, lx + lw / 2, layers[i][2], lx + lw / 2, layers[i + 1][2] + lh,
                   C["mid_text"], lw=2)

    # SRT 核心特性标注（右侧）
    features = [
        (5.5, "ARQ 选择性重传"),
        (5.1, "AES-128/256 加密"),
        (4.7, "拥塞控制 & 流控"),
        (4.3, "延迟管理 (Latency)"),
    ]
    rx = 7.2
    for fy, ftxt in features:
        _text(ax, rx + 1.5, fy, f"● {ftxt}", fontsize=9, ha="left", color=C["primary"])

    ax.annotate("", xy=(6.5, 5.25), xytext=(rx, 5.25),
                arrowprops=dict(arrowstyle="-[", color=C["primary"], lw=1.5))

    # 左侧对比注释
    _text(ax, 0.7, 5.25, "对比\nTCP", fontsize=8, color=C["danger"], fontweight="bold")
    ax.annotate("", xy=(1.5, 5.25), xytext=(1.1, 5.25),
                arrowprops=dict(arrowstyle="->", color=C["danger"], lw=1.5))

    _text(ax, 6, 1.2, "SRT = 基于 UDP 的可靠传输，专为低延迟实时流媒体设计",
          fontsize=9, color=C["mid_text"])

    save_fig(fig, "srt_architecture")


# ================================================================
# 8. SRT ARQ 重传机制
# ================================================================
def draw_srt_arq():
    W, H = 14, 8
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.3, "SRT ARQ 选择性重传机制")

    sx, rx = 2.5, 11.5
    y_top, y_bot = 7.0, 0.8

    # 时间线
    draw_timeline_entity(ax, sx, y_top, y_bot, "发送端", C["primary"])
    draw_timeline_entity(ax, rx, y_top, y_bot, "接收端", C["accent"])

    # 正常包
    pkts = [
        (6.2, "Pkt #1", C["primary"], True),
        (5.4, "Pkt #2", C["primary"], True),
        (4.6, "Pkt #3 ✗", C["danger"], False),
        (3.8, "Pkt #4", C["primary"], True),
    ]
    for y, label, color, arrives in pkts:
        if arrives:
            draw_sequence_arrow(ax, sx, rx, y, label, color, fontsize=8)
        else:
            ax.annotate("", xy=(rx - 1.5, y - 0.3), xytext=(sx, y),
                        arrowprops=dict(arrowstyle="->", color=color,
                                        lw=1.5, linestyle="dashed"))
            _text(ax, (sx + rx) / 2, y + 0.15, label, fontsize=8,
                  color=C["danger"], fontweight="bold")
            ax.plot((sx + rx) / 2, y - 0.15, "x", color=C["danger"],
                    markersize=12, markeredgewidth=2.5, zorder=5)

    # NAK (接收端 → 发送端)
    draw_sequence_arrow(ax, rx, sx, 2.8, "NAK #3", C["warning"], fontsize=8)
    _text(ax, (sx + rx) / 2 + 0.5, 2.55, "← 丢包检测", fontsize=7,
          color=C["warning"])

    # 重传
    draw_sequence_arrow(ax, sx, rx, 1.8, "重传 Pkt #3 ✓", C["accent"], fontsize=8)

    # Latency 窗口
    draw_dashed_line(ax, 0.5, 6.4, 13.5, 6.4, C["border"])
    draw_dashed_line(ax, 0.5, 1.5, 13.5, 1.5, C["border"])
    _bracket_h(ax, 13.0, 13.0, 1.5, "", C["info"], offset=0)
    ax.annotate("", xy=(13.3, 6.4), xytext=(13.3, 1.5),
                arrowprops=dict(arrowstyle="<->", color=C["info"], lw=2))
    _text(ax, 13.6, 3.95, "Latency\n窗口", fontsize=8, color=C["info"],
          fontweight="bold", ha="left")

    save_fig(fig, "srt_arq")


# ================================================================
# 9. QUIC vs TCP 连接建立对比
# ================================================================
def draw_quic_vs_tcp():
    W, H = 14, 9
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.3, "QUIC  vs  TCP+TLS  连接建立对比")

    # ── 左侧：TCP + TLS 1.3 (3-RTT) ──
    _bg(ax, 0.2, 0.2, 6.4, 7.8, C["light_red"], alpha=0.15)
    _text(ax, 3.4, 8.3, "TCP + TLS 1.3", fontsize=11, fontweight="bold",
          color=C["danger"])

    cl, sr = 1.5, 5.5
    y = 7.4
    draw_timeline_entity(ax, cl, y, 0.5, "客户端", C["danger"])
    draw_timeline_entity(ax, sr, y, 0.5, "服务端", C["danger"])

    rtt_labels = [
        (6.5, "SYN", "SYN-ACK", "TCP 握手"),
        (5.3, "ClientHello", "ServerHello", "TLS 握手"),
        (4.1, "Finished", "Finished", "TLS 完成"),
        (2.9, "HTTP 请求", "HTTP 响应", "数据传输"),
    ]
    for y_pos, fwd, bck, note in rtt_labels:
        draw_sequence_arrow(ax, cl, sr, y_pos, fwd, C["danger"], fontsize=7)
        draw_sequence_arrow(ax, sr, cl, y_pos - 0.5, bck, C["danger"], fontsize=7)
        _text(ax, 0.6, y_pos - 0.25, note, fontsize=7, color=C["mid_text"], ha="left")

    _text(ax, 3.4, 1.1, "总计 3 RTT", fontsize=11, fontweight="bold", color=C["danger"])

    # ── 右侧：QUIC (1-RTT / 0-RTT) ──
    _bg(ax, 7.0, 0.2, 6.8, 7.8, C["light_green"], alpha=0.15)
    _text(ax, 10.5, 8.3, "QUIC", fontsize=11, fontweight="bold",
          color=C["accent"])

    cl2, sr2 = 8.5, 12.5

    draw_timeline_entity(ax, cl2, 7.4, 0.5, "客户端", C["accent"])
    draw_timeline_entity(ax, sr2, 7.4, 0.5, "服务端", C["accent"])

    draw_sequence_arrow(ax, cl2, sr2, 6.5, "Initial (加密握手)", C["accent"], fontsize=7)
    draw_sequence_arrow(ax, sr2, cl2, 5.7, "Handshake + 1-RTT Keys", C["accent"],
                        fontsize=7)
    draw_sequence_arrow(ax, cl2, sr2, 4.9, "HTTP/3 请求 (加密)", C["accent"], fontsize=7)
    draw_sequence_arrow(ax, sr2, cl2, 4.1, "HTTP/3 响应 (加密)", C["accent"], fontsize=7)

    _text(ax, 7.8, 6.1, "握手 +\n传输", fontsize=7, color=C["mid_text"], ha="left")
    _text(ax, 7.8, 4.5, "数据", fontsize=7, color=C["mid_text"], ha="left")

    _text(ax, 10.5, 2.6, "首次: 1 RTT", fontsize=11, fontweight="bold", color=C["accent"])

    # 0-RTT 注释
    _bg(ax, 7.6, 0.8, 5.6, 1.2, C["light_cyan"], alpha=0.4)
    _text(ax, 10.4, 1.4, "0-RTT 恢复连接：客户端可直接发送数据",
          fontsize=9, color=C["info"], fontweight="bold")
    _text(ax, 10.4, 1.0, "利用缓存的 TLS 会话密钥，跳过握手",
          fontsize=8, color=C["mid_text"])

    save_fig(fig, "quic_vs_tcp")


# ================================================================
# 10. 队头阻塞对比
# ================================================================
def draw_hol_blocking():
    W, H = 14, 9
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.3, "队头阻塞 (Head-of-Line Blocking) 对比")

    # ── 上方：HTTP/2 over TCP ──
    _bg(ax, 0.3, 4.8, 13.4, 3.5, C["light_red"], alpha=0.2)
    _text(ax, 3.0, 8.0, "HTTP/2  over  TCP", fontsize=11, fontweight="bold",
          color=C["danger"])

    stream_colors = [C["primary"], C["accent"], C["warning"]]
    labels = ["流 A", "流 B", "流 C"]

    for i in range(3):
        y = 7.0 - i * 0.7
        _text(ax, 1.2, y + 0.15, labels[i], fontsize=8, color=stream_colors[i])
        for j in range(6):
            x = 2.0 + j * 1.7
            if i == 0 and j == 2:
                draw_box(ax, x, y, 1.4, 0.45, "✗ 丢包", C["danger"], fontsize=7)
            elif j >= 2:
                draw_box(ax, x, y, 1.4, 0.45, "阻塞等待", C["border"],
                         text_color=C["mid_text"], fontsize=7, alpha=0.6)
            else:
                draw_box(ax, x, y, 1.4, 0.45, f"数据 {j + 1}", stream_colors[i],
                         fontsize=7, alpha=0.7)

    _text(ax, 12.0, 5.3, "TCP 单连接\n一个丢包阻塞\n所有流 !", fontsize=9,
          fontweight="bold", color=C["danger"])

    # ── 下方：HTTP/3 over QUIC ──
    _bg(ax, 0.3, 0.3, 13.4, 4.0, C["light_green"], alpha=0.2)
    _text(ax, 3.0, 4.0, "HTTP/3  over  QUIC", fontsize=11, fontweight="bold",
          color=C["accent"])

    for i in range(3):
        y = 3.2 - i * 0.7
        _text(ax, 1.2, y + 0.15, labels[i], fontsize=8, color=stream_colors[i])
        for j in range(6):
            x = 2.0 + j * 1.7
            if i == 0 and j == 2:
                draw_box(ax, x, y, 1.4, 0.45, "✗ 丢包", C["danger"], fontsize=7)
            elif i == 0 and j > 2:
                draw_box(ax, x, y, 1.4, 0.45, "等待重传", C["warning"],
                         fontsize=7, alpha=0.6)
            else:
                draw_box(ax, x, y, 1.4, 0.45, f"数据 {j + 1}", stream_colors[i],
                         fontsize=7, alpha=0.7)

    _text(ax, 12.0, 1.2, "QUIC 独立流\n其他流不受\n影响 ✓", fontsize=9,
          fontweight="bold", color=C["accent"])

    save_fig(fig, "hol_blocking")


# ================================================================
# 11. MoQ 架构图
# ================================================================
def draw_moq_architecture():
    W, H = 14, 8
    fig, ax = new_fig(W, H)
    _setup(ax, W, H)
    _title(ax, W / 2, H - 0.3, "MoQ (Media over QUIC) 架构")

    # Publisher
    _bg(ax, 0.3, 2.5, 3.0, 3.5, C["light_blue"])
    _text(ax, 1.8, 6.2, "发布者 (Publisher)", fontsize=10, fontweight="bold",
          color=C["primary"])
    draw_box(ax, 0.6, 4.5, 2.4, 0.8, "编码器", C["primary"], fontsize=10)
    draw_box(ax, 0.6, 3.0, 2.4, 0.8, "MoQ 发布端", C["info"], fontsize=9)
    draw_arrow(ax, 1.8, 4.5, 1.8, 3.8, C["mid_text"])

    # Relay Network
    _bg(ax, 4.2, 1.5, 5.6, 5.2, C["light_green"])
    _text(ax, 7.0, 6.9, "中继网络 (Relay Network)", fontsize=10,
          fontweight="bold", color=C["accent"])
    draw_box(ax, 5.5, 4.5, 3.0, 0.9, "Relay 节点", C["accent"], fontsize=10)
    draw_box(ax, 4.6, 2.5, 2.0, 0.7, "Relay A", C["accent"], fontsize=8)
    draw_box(ax, 7.4, 2.5, 2.0, 0.7, "Relay B", C["accent"], fontsize=8)

    draw_arrow(ax, 7.0, 4.5, 5.6, 3.2, C["mid_text"])
    draw_arrow(ax, 7.0, 4.5, 8.4, 3.2, C["mid_text"])

    draw_arrow(ax, 3.0, 3.4, 5.5, 4.9, C["mid_text"], lw=2)
    _text(ax, 4.1, 4.5, "PUBLISH", fontsize=8, color=C["primary"], fontweight="bold")

    # Subscriber
    _bg(ax, 10.5, 2.5, 3.2, 3.5, C["light_purple"])
    _text(ax, 12.1, 6.2, "订阅者 (Subscriber)", fontsize=10,
          fontweight="bold", color=C["secondary"])
    draw_box(ax, 10.8, 4.5, 2.6, 0.8, "MoQ 订阅端", C["secondary"], fontsize=9)
    draw_box(ax, 10.8, 3.0, 2.6, 0.8, "播放器", C["secondary"], fontsize=10)
    draw_arrow(ax, 12.1, 4.5, 12.1, 3.8, C["mid_text"])

    draw_arrow(ax, 8.5, 4.9, 10.8, 4.9, C["mid_text"], lw=2)
    _text(ax, 9.7, 5.2, "SUBSCRIBE", fontsize=8, color=C["secondary"],
          fontweight="bold")

    # 底部概念注释
    _bg(ax, 1.0, 0.3, 12.0, 1.5, C["light_cyan"], alpha=0.4)
    _text(ax, 7.0, 1.35, "核心概念", fontsize=10, fontweight="bold", color=C["info"])
    concepts = "Track (媒体轨道)  →  Group (GOP 组)  →  Object (单个帧/数据单元)"
    _text(ax, 7.0, 0.75, concepts, fontsize=9, color=C["dark_text"])

    save_fig(fig, "moq_architecture")


# ================================================================
# main
# ================================================================
def main():
    print("=== 第四篇：现代流媒体协议 ===")
    draw_hls_architecture()
    draw_hls_abr()
    draw_ll_hls()
    draw_dash_architecture()
    draw_mpd_hierarchy()
    draw_abr_algorithms()
    draw_srt_architecture()
    draw_srt_arq()
    draw_quic_vs_tcp()
    draw_hol_blocking()
    draw_moq_architecture()
    print("=== 全部 11 张图生成完毕 ===")


if __name__ == "__main__":
    main()
