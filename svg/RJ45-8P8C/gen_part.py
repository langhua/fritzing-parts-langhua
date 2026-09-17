#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 RJ45-8P8C (Coorle 8P8C 直插式 PCB 插座, 无屏蔽)。

四个视图（AGENTS.md §2）：icon → breadboard → schematic → pcb。

数据来源
========
1) 图纸 `D:\\Downloads\\CL_RJ45_8P8C_wo-S_DIP_PCB_Plug.pdf`
   （Coorle Technology，图号 SY-A0XX-XX，RJ45 8P8C 90 度插头，REV A0，2024-04-23，1/1 页）：
   · 本体宽 **11.63**（前视）、总深 **27.00±0.2**（侧视）、插口端高 **6.60±0.1**、
     尾部高 **9.00**、顶部凸起 **1.43**、底面离板 **1.05**、尾部台阶长 **7.00**；
   · **8P8C 引脚：脚距 1.02±0.1、跨距 7.14±0.1**（这两条是 8P8C 行业的定义尺寸）；
   · `1.50` / `9.20`（顶视图水平方向）：`9.20` = 引脚排到本体尾端面的距离；
   · 电气：150 VAC RMS、1.5 A、接触电阻 ≤20 mΩ、绝缘 ≥1000 MΩ@500V DC、
     耐压 1000V DC/AC PEAK @0.5mA 50/60Hz 1min；寿命 5000 次、插拔力 30N MAX；
     金片 = 铜合金 T=0.40mm 镀金、外壳 = 尼龙环保料 黑色（文档明确 **无屏蔽 wo-S**）。
2) **图纸未标注、按 8P8C 通用规格推测的部分**（用户 2026-09-17 认可「其它靠你推测」）：
   · 2 个塑料定位柱：柱径取 **1.50**（图纸顶视图那个 1.50 亦可读作柱径），
     对应 PCB 孔 **⌀1.60**；**柱间距 8.89**（0.35"，8P8C 通用值）；
   · 定位柱在引脚排**后方 5.08**（0.2"）；
   · 引脚为扁针 ⇒ 焊盘取**椭圆 0.80(脚距方向) × 1.80(进深方向)**、钻孔 ⌀0.70
     （0.80 < 1.02 脚距，相邻焊盘才不连锡）。

引脚命名：8P8C 的电气含义取决于接线标准（T568A/B），**元件不预定** ⇒ 连接器就叫 1..8。
图纸底视图标 `PIN1` 在下方、`PIN8` 在上方 ⇒ 这里按行业惯例 **pin1 在第 1 位（最左）**。

用法：python gen_part.py
"""
import math
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "RJ45-8P8C"
FZPZ = "RJ45-8P8C.fzpz"

N_PINS = 8
# (connector id, 连接器名 = 原理图上的显示名, 脚号, 说明)
# 名字取 MDI 命名（M0+..M3-），用户 2026-09-17 定；脚号仍按 8P8C 的 1..8 写在 description。
CONN = [(0, "M0+", "1", "8P8C contact 1 (pair 0, +)"),
        (1, "M0-", "2", "8P8C contact 2 (pair 0, -)"),
        (2, "M1+", "3", "8P8C contact 3 (pair 1, +)"),
        (3, "M1-", "4", "8P8C contact 4 (pair 1, -)"),
        (4, "M2+", "5", "8P8C contact 5 (pair 2, +)"),
        (5, "M2-", "6", "8P8C contact 6 (pair 2, -)"),
        (6, "M3+", "7", "8P8C contact 7 (pair 3, +)"),
        (7, "M3-", "8", "8P8C contact 8 (pair 3, -)")]

ICON_LABEL = "RJ45"
TITLE = "RJ45 8P8C PCB Socket (DIP, unshielded)"
LABEL = "J"
PACKAGE = "DIP-8P8C (11.63 x 27.00 mm)"
FAMILY = "RJ45"

# ---- 几何（mm；图纸明示值 + 8P8C 通用值）------------------------------------
PITCH = 1.02                       # 8P8C 脚距（图纸 1.02±0.1）
SPAN = 7.14                        # 8P8C 跨距（图纸 7.14±0.1；= 7 × 1.02）
BODY_W = 11.63                     # 本体宽（图纸）
BODY_L = 27.00                     # 总深（图纸 27.00±0.2）
FRONT_H = 6.60                     # 插口端高（图纸 6.60±0.1）
TAIL_H = 9.00                      # 尾部高（图纸 9.00；= RJ45 口高 8.89 的取整）
DIP_FROM_TAIL = 9.20               # 引脚排中心到本体尾端面（图纸 9.20）
PAD_W, PAD_H = 0.80, 1.80          # 信号脚焊盘（椭圆，推测）
DRILL = 0.70                       # 信号脚钻孔（推测）
POST_D = 1.50                      # 定位柱柱径（图纸 1.50）
POST_HOLE = 1.60                   # 定位柱孔（推测）
POST_PITCH = 8.89                  # 定位柱间距（推测：8P8C 通用 0.35"）
POST_BACK = 5.08                   # 定位柱在引脚排后方（推测：0.2"）

# ---- icon 里的弹片 / 凹槽 / 斜角（用户 2026-09-17 定）--------------------------
BLADE_L, BLADE_W = 14.00, 0.45     # 弹片（长 × 宽）
NOTCH_D = BLADE_W * 2              # 本体凹槽深 = 弹片宽（金属线宽）的 2 倍
WIN_W, WIN_H = 2.20, 4.60          # 尾部两个圆角矩形「窗口」（宽 × 高，用户 2026-09-17 实测）
WIN_FROM_RIGHT = 4.60              # 窗口右边距壳体右边缘
TRIM_W = NOTCH_D * 1.5             # 插口端斜角在**宽度方向**的收进量 = 凹槽深的 1.5 倍
GOLD_LEN = 5.00                    # 镀金段长（用户 2026-09-18；原为「弹片长/2 − 0.5」）
SILVER_FAR, SILVER_NEAR = 9.20, 10.70   # 银色右端距本体**右边缘**（奇/偶数脚交替）
# ↑ 曾于 c9ed02a 改成 7.00/8.50（用户 2026-09-18 判定银线长度错误 → 已回滚）

BLADE_X0 = -BODY_L / 2 + 1.20                     # 弹片起点（插口端内侧）
GOLD_LEN = 5.00                                   # 镀金段长度（用户 2026-09-18）
GOLD_END = BLADE_X0 + GOLD_LEN                    # 镀金/银色分界（x）
SILVER_END = (BODY_L / 2 - SILVER_FAR, BODY_L / 2 - SILVER_NEAR)   # 两根交替的银色右端
NOTCH_L_FROM_LEFT = 7.20           # 凹槽**左缘**距本体左边缘（用户 2026-09-18）
# ⚠ 宽度**不按两端边距定死**：7.2/4.8 那两个边距只是 rev_1 的数（用户 2026-09-18 澄清）。
# 曾错改成「BODY_L − 左 − 右」⇒ 原版凹槽被撑到 15.00（该改动已撤销）。
NOTCH_W = (max(SILVER_END) - GOLD_END) * 0.80     # 凹槽宽 = 银色线长（最长那根）的 80% ⇒ 11.04
NOTCH_X = -BODY_L / 2 + NOTCH_L_FROM_LEFT         # 凹槽左缘（x，相对元件中心）

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- RJ45-8P8C -->\n'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_ICON_RE = re.compile(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', re.S)


def icon_group():
    """取出 icon 的 `<g id="icon">…</g>`，供面包板 1:1 复用（AGENTS §3b：
    面包板上的元件要与 icon 同形，不然两个视图各画一套、迟早漂移）。"""
    m = _ICON_RE.search(gen_icon_svg())
    return m.group(1) if m else ""


def body_path(cx, cy, u, w, ln, skew_w=None, notch=None):
    """俯视本体轮廓：

    · 左端（插口端）两个角按 **30°** 斜切，斜边在宽度方向的收进量 = skew_w；
    · `notch = (x_left, width, depth)`（mm，x 相对元件中心）—— 上下边缘各**挖掉**
      一块 ⇒ 凹槽处不画本体、**透出背景 = 真透明**（用户 2026-09-17：不能拿深色
      去「画」一个槽，那样看不出是透的）。
    """
    x0, x1 = cx - ln / 2 * u, cx + ln / 2 * u
    y0, y1 = cy - w / 2 * u, cy + w / 2 * u
    d = (skew_w or 0) * u                    # 宽度方向的收进量
    c = d / math.tan(math.radians(30))       # 进深方向的收进量（30° 推出）
    if not notch:
        return (f"M {x0 + c:.1f} {y0:.1f} L {x1:.1f} {y0:.1f} L {x1:.1f} {y1:.1f} "
                f"L {x0 + c:.1f} {y1:.1f} L {x0:.1f} {y1 - d:.1f} L {x0:.1f} {y0 + d:.1f} Z")
    nx = cx + notch[0] * u
    nw, nd = notch[1] * u, notch[2] * u
    return (f"M {x0 + c:.1f} {y0:.1f} L {nx:.1f} {y0:.1f} L {nx:.1f} {y0 + nd:.1f} "
            f"L {nx + nw:.1f} {y0 + nd:.1f} L {nx + nw:.1f} {y0:.1f} L {x1:.1f} {y0:.1f} "
            f"L {x1:.1f} {y1:.1f} L {nx + nw:.1f} {y1:.1f} L {nx + nw:.1f} {y1 - nd:.1f} "
            f"L {nx:.1f} {y1 - nd:.1f} L {nx:.1f} {y1:.1f} L {x0 + c:.1f} {y1:.1f} "
            f"L {x0:.1f} {y1 - d:.1f} L {x0:.1f} {y0 + d:.1f} Z")


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """**俯视外观**（照产品图里「一眼能认出是 RJ45」的那一面 = 图纸 C2-3）：

    · 本体：插口端两个角 **30° 斜切**；俯视时上/下边缘各有一条**凹槽**
      （敞开露出金属线），尾部有**两个圆角矩形窗口**（2.20 × 4.60，右边距壳体右边缘 4.60）；
    · **8 根沿进深方向的弹片**（间距 1.02 / 跨度 7.14，PIN1 在下、PIN8 在上）：
      **靠插口那一半镀金**（反复插拔处）、**靠尾部那一半是普通银色金属**
      —— 用户 2026-09-17：「水晶头不是全部镀金」；
    · 尾部两个卡扣；
    · **不写元件名** —— 用户 2026-09-17：「要力争画出来别人一看就是 RJ45，
      而不是写个名字」。
    """
    u = 1.0
    gold, silver = "#d8b45a", "#b9bdc2"
    x0, x1 = -(BODY_L / 2 + 0.3), (BODY_L / 2 + 0.3)
    y0, y1 = -(BODY_W / 2 + 0.3), (BODY_W / 2 + 0.3)
    L = [SVG_HDR,
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0:.2f}mm" height="{y1 - y0:.2f}mm" '
         f'viewBox="{x0:.2f} {y0:.2f} {x1 - x0:.2f} {y1 - y0:.2f}">\n',
         '  <g id="icon">\n',
         f'    <path d="{body_path(0, 0, u, BODY_W, BODY_L, TRIM_W, (NOTCH_X, NOTCH_W, NOTCH_D))}" '
         f'fill="#2b2b2b" stroke="none"/>\n']
    bx = BLADE_X0
    ge = GOLD_END
    ends = SILVER_END
    far = max(ends)
    for i in range(N_PINS):                                                  # 8 根弹片
        yy = -SPAN / 2 + i * PITCH
        xe = ends[i % 2]
        r = BLADE_W / 2
        # 金色：**左端半圆**、右端直角（与银色相接处是直角，用户 2026-09-17）
        L.append(f'    <path d="M {ge:.3f} {yy - r:.3f} L {bx + r:.3f} {yy - r:.3f} '
                 f'A {r:.3f} {r:.3f} 0 0 0 {bx + r:.3f} {yy + r:.3f} '
                 f'L {ge:.3f} {yy + r:.3f} Z" fill="{gold}" stroke="none"/>\n')
        # 银色：左端直角、**右端半圆**
        L.append(f'    <path d="M {ge:.3f} {yy - r:.3f} L {xe - r:.3f} {yy - r:.3f} '
                 f'A {r:.3f} {r:.3f} 0 0 1 {xe - r:.3f} {yy + r:.3f} '
                 f'L {ge:.3f} {yy + r:.3f} Z" fill="{silver}" stroke="none"/>\n')
    for sy in (-1, 1):                                                       # 尾部两个窗口
        L.append(f'    <rect x="{BODY_L / 2 - WIN_FROM_RIGHT - WIN_W:.2f}" y="{sy * 2.6 - WIN_H / 2:.2f}" '
                 f'width="{WIN_W:.2f}" height="{WIN_H:.2f}" rx="0.30" fill="#141414" '
                 f'stroke="none"/>\n')
    L.append('  </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = 绿色转接板（AGENTS §3b：8P8C 脚距 1.02mm 插不进面包板孔网格）。

    坐标 **100 单位 = 2.54mm**。8 个连接器 ⇒ 8 个排针，一排 2.54 间距；
    元件 1:1 **横放**（27.00 × 11.63mm），排针排在元件上方，行距 300 单位 = 7.62mm
    ≥ 元件半高 5.815 + 焊盘半径 1.0 + 余量 ⇒ 排针不压元件。
    """
    U = 39.37
    bw, bh = 1300, 900
    cx, cy = 650, 550
    y_pin = 100          # 排针靠板端（数字要放**内侧**，见 AGENTS §3b）
    pad_r, hole_r = 1.0 * U, 0.485 * U
    xs = [300 + 100 * i for i in range(N_PINS)]
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
         f'height="{bh / 100 * 2.54:.2f}mm" viewBox="0 0 {bw} {bh}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="0" y="0" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" '
         f'stroke-width="5"/>\n']
    # 元件 1:1：直接复用 icon 的 <g id="icon">（icon 的单位是 mm，故 scale=U）
    L.append(f'  <g transform="translate({cx} {cy}) scale({U})">{icon_group()}</g>\n')
    # 8 个排针 + 数字（数字放排针内侧 = 朝板心，AGENTS §3b）
    for i, x in enumerate(xs):
        L.append(f'  <circle id="connector{i}pin" connectorname="{esc(CONN[i][1])}" cx="{x}" '
                 f'cy="{y_pin}" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        L.append(f'  <circle cx="{x}" cy="{y_pin}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
        ty = y_pin + 81
        L.append(f'  <text x="{x}" y="{ty}" font-size="42" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x} {ty})">{esc(CONN[i][1])}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """原理图（用户 2026-09-17）：插口**朝左**、**8 个针脚全在右侧**
    （「rj45 是插头，脚都画在一侧」；插口在左 ⇒ 引脚自然从尾部/右侧出来）。

    · 矩形框竖放，8 个信号脚均从**右边**向右引出，从上到下 = pin8 .. pin1；
    · 引线上方写脚号，框内**靠右**写功能名（名字从 SCH_NAME 取）；
    · 框内左侧画 **RJ45 口的图形**，插口朝左（与 icon / 面包板 / PCB 同向）。
    """
    P, WIRE, FN, CH = 100, 130, 35, 20
    BX0, BY0 = 340, 200
    BW, BH = 440, 7 * P + 2 * P                  # 宽只留「口图形 + 名字」两栏；高：首尾脚占 7P + 上下各 1P
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - 20, BY0 - 20
    VBW, VBH = BW + WIRE + 40, BH + 40
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" '
         f'height="{VBH / 1000:.6f}in" viewBox="{VBX} {VBY} {VBW} {VBH}">\n',
         ' <g id="schematic">\n',
         f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
         f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n']
    # 框内左侧的 RJ45 口图形：插口**朝左**（外壳的右边是竖线，上下横线往左伸）+ 8 条触点线
    gx0, gx1 = BX0 + 160, BX0 + 280
    gy0, gy1 = BY0 + 320, BY0 + 680
    L.append(f'  <path d="M {gx0} {gy0} L {gx1} {gy0} L {gx1} {gy1} L {gx0} {gy1}" '
             f'fill="none" stroke="#000000" stroke-width="5"/>\n')
    for i in range(N_PINS):
        y = gy0 + 40 + i * 40
        L.append(f'  <line x1="{gx0}" y1="{y}" x2="{gx0 - 80}" y2="{y}" '
                 f'stroke="#000000" stroke-width="5"/>\n')
    # 8 个脚全在右侧：从上到下 = pin1 .. pin8（用户 2026-09-17：1 脚应该在上面）
    for k, ci in enumerate(range(N_PINS)):
        y = BY0 + P + k * P
        num, name = CONN[ci][2], CONN[ci][1]
        L.append(f'  <line class="pin" id="connector{ci}pin" connectorname="{esc(name)}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="#000000" '
                 f'stroke-width="5"/>\n')
        L.append(f'  <rect class="terminal" id="connector{ci}terminal" x="{BX1 + WIRE - 11}" '
                 f'y="{y - 11}" width="22" height="22" fill="none" stroke="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" '
                 f'text-anchor="middle" font-family="DroidSans">{esc(num)}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + 12}" font-size="{FN}" fill="#000000" '
                 f'text-anchor="end" font-family="DroidSans">{esc(name)}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（用户 2026-09-17 给的焊盘排列图）：

    · 8 个**通孔圆焊盘**排成 **2 列 × 4 行**：外径 **1.60**、孔径 **1.00**；
    · **两列中心距 1.50**、**同列相邻两脚中心距 2.04**；
    · 丝印方框 **11.68（左右边线）× 12.20（上下边线）**，左侧第一列中心距左边线 **1.50**；
    · 焊盘外径/孔径 **1.20 / 0.70**（用户 2026-09-17 确认实物就这么小）。
    · **左右蛇形排列、只做纵向居中**（用户 2026-09-17）：相邻两脚一左一右交替，
      纵向步距 = 行距 / 2（1.02）⇒ 同侧相邻两脚刚好是 2.04；整体在框内**上下**居中，
      横向不居中 —— 左列中心距左边线 **1.50**（用户定）。
    · 脚序：i=0..7 直接沿蛇形走（pin1 左、pin2 右、pin3 左 …）。
    · 丝印上**不写**元件名、**不画** pin1 点（用户 2026-09-17）。
    """
    PAD_D, HOLE_D = 1.20, 0.70                  # 实物就这么小（用户 2026-09-17 确认）
    COL_P, ROW_P = 1.50, 2.04
    BOX_W, BOX_H = 9.48, 12.20                 # 宽 11.68 − 2.20（右框线左移 2.2，其余不动；用户 2026-09-18）
    COL0 = 1.50                             # 左侧第一列中心距左边线
    M = 1.5                                      # 画布留边
    W, H = BOX_W + 2 * M, BOX_H + 2 * M
    x0, y0 = -W / 2, -H / 2
    bx, by = x0 + M, y0 + M
    step = ROW_P / 2                             # 蛇形纵向步距
    y_top = by + (BOX_H - (N_PINS - 1) * step) / 2   # 只做**纵向**居中
    pads, silk = [], []
    for i in range(N_PINS):
        x = bx + COL0 + (i % 2) * COL_P
        y = y_top + i * step
        pads.append(f'<circle id="connector{i}pin" connectorname="{esc(CONN[i][1])}" '
                    f'cx="{x:.3f}" cy="{y:.3f}" r="{PAD_D / 2:.3f}" fill="#F7BD13" '
                    f'stroke="none"/>')
        pads.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{HOLE_D / 2:.3f}" '
                    f'fill="#0b2b3a" stroke="none"/>')
    silk.append(f'<rect x="{bx:.3f}" y="{by:.3f}" width="{BOX_W:.2f}" height="{BOX_H:.2f}" '
                f'fill="none" stroke="#f0f0f0" stroke-width="0.1524"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" '
            f'viewBox="{x0:.1f} {y0:.1f} {W:.1f} {H:.1f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for cn, name, num, desc in CONN:
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(name)}" type="male">\n'
            f'   <description>pin {num} = {esc(desc)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cn}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{cn}pin" terminalId="connector{cn}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{cn}pin"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>1</version>\n <date>2026-09-17</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>RJ45</tag>\n  <tag>8P8C</tag>\n'
            f'  <tag>ethernet</tag>\n  <tag>socket</tag>\n  <tag>DIP</tag>\n  <tag>PCB mount</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">8</property>\n'
            f'  <property name="ratings">1.5A / 150V AC</property>\n </properties>\n'
            f' <views>\n  <breadboardView>\n   <layers image="breadboard/{PART_ID}_breadboard.svg">\n'
            f'    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            f'  <schematicView>\n   <layers image="schematic/{PART_ID}_schematic.svg">\n'
            f'    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
            f'  <pcbView>\n   <layers image="pcb/{PART_ID}_pcb.svg">\n'
            f'    <layer layerId="copper1"/>\n    <layer layerId="silkscreen"/>\n   </layers>\n  </pcbView>\n'
            f'  <iconView>\n   <layers image="icon/{PART_ID}_icon.svg">\n'
            f'    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n </views>\n'
            f' <connectors>\n' + "\n".join(conns) + '\n </connectors>\n</module>\n')


# ---------------------------------------------------------------- 打包
def main():
    files = {
        "icon": gen_icon_svg(),
        "breadboard": gen_breadboard_svg(),
        "schematic": gen_schematic_svg(),
        "pcb": gen_pcb_svg(),
    }
    for view, content in files.items():
        name = f"svg.{view}.{PART_ID}_{view}.svg"
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("wrote", name)
    fzp_name = f"part.{PART_ID}.fzp"
    with open(os.path.join(OUT_DIR, fzp_name), "w", encoding="utf-8", newline="\n") as f:
        f.write(gen_fzp())
    print("wrote", fzp_name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(OUT_DIR, fzp_name), arcname=fzp_name)
        for view in ("icon", "breadboard", "schematic", "pcb"):
            name = f"svg.{view}.{PART_ID}_{view}.svg"
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
