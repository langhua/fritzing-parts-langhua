# -*- coding: utf-8 -*-
r"""BQ25570（VQFN-20 / RGR，3.5×3.5 mm）—— 生成脚本

★ 数据来源（全部引自手册，不是估的 ✓）：
  · 封装：**VQFN-20 = RGR**、本体 **3.5×3.5 mm**（p43 PACKAGE OUTLINE：3.35–3.65 取中 ✓）
  · 脚距 **0.50 mm**（每边 5 脚 ✓）、引脚号↔名字取自**第 4 页 Pin Functions** ✓
  · land pattern（PCB 视图用 ✓）—— ★ **用户 2026-10-17 定：按“Example Board Layout”那张图** ✓
    焊盘 **20X 0.28** 宽 × **0.85** 长 ｜ **焊盘区总宽 4.30 × 4.30** ｜ 内缘距 **2.60**
    ｜ **R0.14** 圆角（圆角矩形）｜ 散热盘 **2.05** ｜ 阻焊 0.07 全周、相邻掩膜间隙 0.08
    ⇒ 焊盘中心半径 = (4.30 − 0.85)/2 = **1.725**、内缘 1.725 − 0.425 = **1.30** ✓
    （自洽核：2×1.30 = 2.60 ✓；0.5 − 0.28 − 2×0.07 = **0.08** ✓）
  · ⚠ 本仓中文版手册（ZHCSBK4G）自己的 p44 写的是 0.24×0.6 / 3.3 —— 与用户给的图**不是同一版**，
    以**用户给的图**为准 ✓
★ 画法照库里 QFN 件的既有风格（`CH32V002D4U6` ✓）：
  icon 32×32 px viewBox、本体 `#303030` 17×17 rx0.3、引脚金色 `#f7bf13`、1 脚圆点 `#c0c0c0` r1、
  中间打型号字 ✓；**不加底色/高光/阴影** ✗（§1 工业风 ✓）。
  原理图 = 四边排脚方框符号 ✓；PCB = VQFN-20 land pattern（mm、焊盘 `#F7BD13`、角括号丝印）✓

用法： py -3.13 -u -X utf8 gen_part.py     # 在**本目录**生成 icon / 面包板 / 原理图 / PCB
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ID = "BQ25570"
HERE = os.path.dirname(os.path.abspath(__file__))

# ── icon 几何（px，viewBox 32×32；1 px = 3.5mm/17 = 0.2059 mm ⇒ 0.5mm 脚距 = 2.4286px?? ✗）
#   ★ 照库里的画法：本体 17px、脚距 **3.40px**（= 0.5mm ✓，与 CH32V002D4U6 同一套比例 ✓）
BODY = 17.0            # 本体边长（px）
CB = 16.0              # 画布中心
PITCH = 3.40           # 0.5 mm ✓（库里同一套 ✓）
PAD_W = 1.70           # 脚宽（0.28mm×6.07 ≈ 1.70 ✓ 与兄弟件一致 ✓）
PAD_L = 4.68           # 脚长（伸出体外的可见段 ✓，兄弟件一致 ✓）
GAP = 0.96             # 本体边到脚内端的空隙（兄弟件：7.50 − (3.04+4.68) = −0.22 ⇒ 脚压进本体 ✓）
PIN1_CX, PIN1_CY = 9.60, 22.40   # 1 脚圆点（**左下** ✓ —— 手册顶视图 pin1 在左下 ✓）
TXT_H = 2.30           # 中间型号字：**用户 2026-10-17 定 → 写 `BQ25570`** ✓（7 字符，字号看着缩到 2.3 ✓）

# ══════════════ 面包板视图 = CJMCU-2557 模块（**尺寸按用户 2026-10-17 实测：30×28** ✓）
#   排针 2.54 ✓、超级电容 Ø≈19.5（推定 ✗，照片估的）；安装孔 Ø2.0（推定 ✗）。
BB_W, BB_H = 30.00, 28.00          # 板 **30 × 28 mm**（用户 2026-10-17 给定 ✓）
BB_COLOR = "#5B2A86"               # 紫色阻焊（照片 ✓）
PAD_R, HOLE_R = 1.00, 0.485        # 2mm 焊盘 + Ø0.97 针孔 ✓（§3b ✓）
HOLE_D = 2.00                      # 安装孔 Ø2.0（推定 ✗）
CAP_D = 19.50                      # 5.5V 0.22F 超级电容外径（推定 ✗）
CAP_C = (17.80, 10.16)             # 电容中心（推定 ✗：板改 28 高后位置未变，等照片定）
# 引脚： (名字, x, y) —— 左缘 4 针 ✓ / 右缘 3 对 ✓（全部 2.54 网格 ✓）
BB_PINS = [("GND", 1.27, 3.81), ("V_EN", 1.27, 6.35), ("EN", 1.27, 8.89), ("V_OK", 1.27, 11.43),
           ("OUTPUT+", 28.73, 3.81), ("OUTPUT-", 26.19, 3.81),
           ("BAT+", 28.73, 6.35), ("BAT-", 26.19, 6.35),
           ("INPUT+", 28.73, 8.89), ("INPUT-", 26.19, 8.89)]
# ★ 模块针 → **芯片连接器号**（AGENTS §3：面包板画整块板、原理图/PCB 画芯片，按信号名映射 ✓）
#   21/22/23 = **只在面包板视图存在**的接地针（模块的 OUTPUT- / BAT- / INPUT-）
BB_CONN = [0, 5, 4, 12, 13, 21, 17, 22, 1, 23]
#   GND→VSS(0) ｜ V_EN→VOUT_EN(5) ｜ EN→EN(4) ｜ V_OK→VBAT_OK(12)
#   OUTPUT+→VOUT(13) ｜ OUTPUT-→21 ｜ BAT+→VBAT(17) ｜ BAT-→22 ｜ INPUT+→VIN_DC(1) ｜ INPUT-→23


def breadboard_svg():
    L = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %.2f %.2f">' % (BB_W, BB_H, BB_W, BB_H),
         ' <g id="breadboard">']
    L.append('  <rect x="0" y="0" width="%.2f" height="%.2f" rx="0.4" fill="%s" '
             'stroke="#2b1a3a" stroke-width="0.20"/>' % (BB_W, BB_H, BB_COLOR))
    # 电容位置用**丝印圈**（它在板背面 ✓，面包板视图是俯视 ✓）
    L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="#e8e8e8" '
             'stroke-width="0.25"/>' % (CAP_C[0], CAP_C[1], CAP_D / 2.0))
    # 2 个安装孔
    for hx, hy in ((1.27, 1.27), (1.27, BB_H - 1.27)):
        L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="#c8a227" '
                 'stroke-width="0.55"/>' % (hx, hy, HOLE_D / 2.0 - 0.275))
        L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="#1a1a1a"/>'
                 % (hx, hy, HOLE_D / 2.0 - 0.55))
    # 10 个针：焊盘环 + 针孔 + 丝印名（竖排 ✓ 同照片 ✓）+ connectorNpin / connectorNleg
    for i, (name, x, y) in enumerate(BB_PINS):
        cn = BB_CONN[i]
        L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="#c8a227"/>' % (x, y, PAD_R))
        L.append('  <circle id="connector%dpin" cx="%.2f" cy="%.2f" r="%.2f" fill="#1a1a1a"/>'
                 % (cn, x, y, HOLE_R))
        L.append('  <line id="connector%dleg" x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" '
                 'stroke="#8c8c8c" stroke-width="0.45" stroke-linecap="round"/>'
                 % (cn, x, y, x, y + 2.54))
        if x > BB_W / 2:                 # ★ 右缘的针**不逐个标名** ✗（成对 ⇒ 由下面每对一个名字 ✓）
            continue
        tx = x + 2.10
        L.append('  <text x="%.2f" y="%.2f" font-size="1.55" font-family="DroidSans" '
                 'fill="#ffffff" transform="rotate(-90 %.2f %.2f)" text-anchor="middle">%s</text>'
                 % (tx, y, tx, y, name))
    # ★ 右缘是**成对的**（两针同 y ✓）⇒ 每对只标**一个名字**（同照片 ✓），放两列左边 ✓
    #   （逐针标会两个竖排标签叠在一起 ✗）
    for y, nm in ((3.81, "OUTPUT"), (6.35, "BAT"), (8.89, "INPUT")):
        L.append('  <text x="24.10" y="%.2f" font-size="1.55" font-family="DroidSans" '
                 'fill="#ffffff" transform="rotate(-90 24.10 %.2f)" text-anchor="middle">%s</text>'
                 % (y, y, nm))
    L += [' </g>', '</svg>', '']
    return "\n".join(L)

half = BODY / 2.0
body_lo, body_hi = CB - half, CB + half          # 7.50 .. 24.50 ✓
centers = [CB + PITCH * (i - 2) for i in range(5)]   # 5 个脚位：9.20, 12.60, 16.00, 19.40, 22.80 ✓
lo = body_lo - PAD_L                             # 3.04 ✓
hi = body_hi                                     # 24.50 ⇒ 外侧脚 x = 24.50 − 0.22 hmm


def pads():
    out = []
    for c in centers:
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (body_lo - PAD_L, c - PAD_W / 2, PAD_L, PAD_W))            # 左
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (body_hi, c - PAD_W / 2, PAD_L, PAD_W))                    # 右
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (c - PAD_W / 2, body_lo - PAD_L, PAD_W, PAD_L))            # 上
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (c - PAD_W / 2, body_hi, PAD_W, PAD_L))                    # 下
    return out


def icon_svg():
    L = ['<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">',
         ' <g id="icon">']
    L += ["  " + p for p in pads()]
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="0.3" ry="0.3" '
             'fill="#303030" stroke="none"/>' % (body_lo, body_lo, BODY, BODY))
    L.append('  <circle cx="%.2f" cy="%.2f" r="1.0" fill="#c0c0c0" stroke="none"/>'
             % (PIN1_CX, PIN1_CY))
    L.append('  <text x="%.1f" y="%.1f" font-size="%.1f" font-family="DroidSans" fill="#c0c0c0" '
             'text-anchor="middle" dominant-baseline="central">%s</text>' % (CB, CB, TXT_H, ID))
    L += [' </g>', '</svg>', '']
    return "\n".join(L)


# ══════════════ 原理图（四边排脚 ✓；脚名照 TI bq25570.pdf 第 4 页 Pin Functions 表 ✓）
#   手册顶视图（p4）实测的四边归属（按坐标核过 ✓）：
#     左 上→下 1..5 ｜ 下 左→右 6..10 ｜ 右 下→上 11..15 ｜ 上 右→左 16..20
#   （与库里 QFN 件（CH32V002F4U6 / CH347F）的排法完全一致：逆时针一圈 ✓）
#   单位 = 1000 单位/英寸（库里芯片符号的既有口径 ✓）：字号 35、脚距 100、引线 130、
#   四角留白 CORNER = (最长名+1) × int(FN×0.58) ⇒ 框 = 5×100 + 2×CORNER ✓
S_NAMES = ["VSS", "VIN_DC", "VOC_SAMP", "VREF_SAMP", "EN",          # 1..5   左
           "VOUT_EN", "VBAT_OV", "VRDIV", "NC", "OK_HYST",          # 6..10  下
           "OK_PROG", "VOUT_SET", "VBAT_OK", "VOUT", "VSS",         # 11..15 右
           "LBUCK", "NC", "VBAT", "VSTOR", "LBOOST"]                # 16..20 上
#   裸露焊盘：手册 p4 顶视图标 "Thermal Pad"（无脚号）、Pin Functions 里 NC 9/17 写
#   "Connect to ground using the IC's PowerPAD™"、p34 写 "The PowerPAD should not be used
#   as a power ground return path" ⇒ ★ 用户 2026-10-17 定：**直接显示原厂名 `PowerPAD`** ✓
#   （尊重原厂命名 ✓；`fzp_check` 第 ⑥ 条只硬认 EPAD/EP，其它名字只提示、不判错 ⚠）
#   连接器 20 号、脚号画 `0`、**独立成网**、description 里写清要接地 ✓
S_PAD = "PowerPAD"
S_PER_SIDE = 5

# ══════════════ PCB（VQFN-20 = RGR land pattern ✓；单位 = mm、1:1、原点 = 本体中心）
#   出处 = 用户 2026-10-17 给的 "Example Board Layout" 图 ✓：
#     焊盘区 **4.30 × 4.30** ｜ 焊盘 **20X 0.28 × 0.85** ｜ 内缘距 **2.60**
#     ｜ 圆角 **R0.14**（= 宽的一半 ⇒ 两端半圆，与图上的 U 形一致 ✓）
#     ｜ 散热盘 **2.05** ｜ 阻焊 0.07 全周、相邻掩膜间隙 **0.08**
#   ★ 丝印只画**四个角括号**（本体 3.5 的边会被焊盘跨过 ⇒ 整圈框会压焊盘 ✗）
PCB_BODY = 3.50
PCB_PITCH = 0.50
PCB_PAD_W, PCB_PAD_L = 0.28, 0.85
PCB_PAD_R = (4.30 - PCB_PAD_L) / 2.0   # = 1.725（焊盘中心半径 ✓）
PCB_PAD_RAD = 0.14               # 焊盘圆角 R0.14（= 宽/2，两端半圆）
PCB_PAD = 2.05                   # 散热盘（PowerPAD）
PCB_SILK_ARM = 0.22              # 角括号臂长（同库里 CH32V00x 一族 ✓）
PCB_DOT_R = 0.22                 # 1 脚圆点半径
PCB_DOT_CLEAR = 0.08             # 圆点到 1 脚焊盘的间隙
# ── 散热 / 接地（用户 2026-10-17 定 ✓，依据英文手册 p34 的布局示例）
#   · PowerPAD **双面铜**（2.05）⇒ 底层也要有铜接住热 ✗ 否则过孔等于没做 ✓
#   · 热过孔 **3×3 = 9 个**（截图 ✓），间距 **0.50**（按截图比例量：盘 2.05 ↔ 孔心 ±0.5 ✓）
#     ｜ 孔径 **⌀0.20**（用户第一张图 4×⌀0,2 ✓）｜ 环厚 **0.10** ⇒ 铜盘 ⌀0.40
#     ｜ 间距 0.5 − 铜盘 0.4 = 0.1 间隙 ✓（环厚 <0.1 会踩板厂工艺下限 ✗）
#   · **VSS(1/15) 与 NC(9/17) 用顶层铜接到 PowerPAD** ✓（p34 原文：the remaining pins are
#     either NC pins, that should be connected to the PowerPAD as shown below ✓）
PCB_VIA_DRILL = 0.20
PCB_VIA_RING = 0.10
PCB_VIA_PITCH = 0.50
PCB_VIA_N = 3
PCB_VIA_CID0 = 24                # 9 个过孔各成一个连接器 ⇒ connector24..32（两面可布线 ✓）
PCB_TIE_W = 0.28                 # 与焊盘**同宽** ⇒ 从焊盘直通进入散热盘，没有宽度变化 ✓
PCB_TIE_PINS = (1, 15, 9, 17)    # VSS×2 + NC×2


def schematic_svg():
    FN, P, STUB, VB = 35, 100, 130, 60
    mx = max(len(x) for x in S_NAMES + [S_PAD])
    CORNER = (mx + 1) * int(FN * 0.58)          # (9+1)*20 = 200
    BOX = S_PER_SIDE * P + 2 * CORNER           # 900
    n = len(S_NAMES)
    cn = n                                      # EPAD 的连接器号 = 20
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.4fin" height="%.4fin" '
         'viewBox="%d %d %d %d">'
         % ((BOX + 2 * STUB + 2 * VB) / 1000.0, (BOX + 2 * STUB + 2 * VB) / 1000.0,
            -STUB - VB, -STUB - VB, BOX + 2 * STUB + 2 * VB, BOX + 2 * STUB + 2 * VB),
         ' <g id="schematic">',
         '  <rect x="0" y="0" width="%d" height="%d" fill="#FFFFFF" stroke="#000000" '
         'stroke-width="5"/>' % (BOX, BOX)]

    def pin(cid, name, x1, y1, x2, y2):
        L.append('  <line class="pin" id="connector%dpin" connectorname="%s" '
                 'x1="%d" y1="%d" x2="%d" y2="%d" stroke="#000000" stroke-width="5"/>'
                 % (cid, name, x1, y1, x2, y2))
        L.append('  <rect class="terminal" id="connector%dterminal" x="%d" y="%d" '
                 'width="0.0001" height="0.0001" fill="none"/>' % (cid, x2, y2))

    def num(txt, x, y, rot):
        r = ' transform="rotate(270 %d %d)"' % (x, y) if rot else ''
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                 'font-family="DroidSans"%s>%s</text>' % (x, y, FN, r, txt))

    def nam(txt, x, y, anchor, rot):
        r = ' transform="rotate(270 %d %d)"' % (x, y) if rot else ''
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="%s" '
                 'font-family="DroidSans"%s>%s</text>' % (x, y, FN, anchor, r, txt))

    # 左：1..5 上→下（脚号在引线上方，名在框内、距左边一个字符）
    for k in range(S_PER_SIDE):
        pno = 1 + k
        y = CORNER + P // 2 + k * P
        pin(pno - 1, S_NAMES[pno - 1], 0, y, -STUB, y)
        num(str(pno), -STUB // 2, y - 24, False)
        nam(S_NAMES[pno - 1], FN, y + 12, "start", False)
    # 下：6..10 左→右（名按靠边框那一端锚定 ⇒ 长短名内端都齐 ✓）
    for k in range(S_PER_SIDE):
        pno = 1 + S_PER_SIDE + k
        x = CORNER + P // 2 + k * P
        pin(pno - 1, S_NAMES[pno - 1], x, BOX, x, BOX + STUB)
        num(str(pno), x - 24, BOX + 55, True)
        nam(S_NAMES[pno - 1], x + 12, BOX - FN, "start", True)
    # 右：11..15 下→上
    for k in range(S_PER_SIDE):
        pno = 1 + 2 * S_PER_SIDE + k
        y = BOX - (CORNER + P // 2 + k * P)
        pin(pno - 1, S_NAMES[pno - 1], BOX, y, BOX + STUB, y)
        num(str(pno), BOX + STUB // 2, y - 24, False)
        nam(S_NAMES[pno - 1], BOX - FN, y + 12, "end", False)
    # 上：16..20 右→左
    for k in range(S_PER_SIDE):
        pno = 1 + 3 * S_PER_SIDE + k
        x = BOX - (CORNER + P // 2 + k * P)
        pin(pno - 1, S_NAMES[pno - 1], x, 0, x, -STUB)
        num(str(pno), x - 24, -50, True)
        nam(S_NAMES[pno - 1], x + 12, FN, "end", True)
    # 裸露焊盘（EPAD）：上边、紧挨 20 脚左侧（一个脚距 ✓ 同库里 QFN 件）
    px = CORNER + P // 2 - P
    pin(cn, S_PAD, px, 0, px, -STUB)
    num("0", px - 24, -50, True)
    nam(S_PAD, px + 12, FN, "end", True)
    # 符号名下画在框中央
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans">%s</text>' % (BOX // 2, BOX // 2 + 12, FN, ID))
    L += [' </g>', '</svg>', '']
    return "\n".join(L)


# ══════════════ PCB ≈ VQFN-20 land pattern（mm、原点 = 本体中心、y 向下）
def pcb_pad_xy(pno):
    """脚号 → 焊盘中心（mm）。四边与手册顶视图一致（逆时针）：
    1..5 左(上→下) ｜ 6..10 下(左→右) ｜ 11..15 右(下→上) ｜ 16..20 上(右→左)"""
    idx = pno - 1
    side, k = idx // S_PER_SIDE, idx % S_PER_SIDE
    off = [(j - (S_PER_SIDE - 1) / 2.0) * PCB_PITCH for j in range(S_PER_SIDE)]
    if side == 0:                                   # 左
        return -PCB_PAD_R, off[k]
    if side == 1:                                   # 下
        return off[k], PCB_PAD_R
    if side == 2:                                   # 右
        return PCB_PAD_R, off[S_PER_SIDE - 1 - k]
    return off[S_PER_SIDE - 1 - k], -PCB_PAD_R      # 上


def pcb_pad_d(cx, cy, side):
    """焊盘轮廓（mm）：**内端 R0.14 半圆、外端方角** —— 同截图里 U 形焊盘 ✓
    side: 0 左 / 1 下 / 2 右 / 3 上（内端 = 朝本体中心那一端）"""
    r = PCB_PAD_W / 2.0                     # 0.14 = R0.14 ✓
    h = PCB_PAD_L / 2.0                     # 0.425
    if side in (0, 2):                      # 长轴沿 X
        out = cx - h if side == 0 else cx + h          # 外端（方）
        c = cx + h - r if side == 0 else cx - h + r    # 半圆圆心
        y0, y1 = cy - r, cy + r
        sweep = 0 if side == 0 else 1
        return ("M%.3f %.3f L%.3f %.3f L%.3f %.3f A%.3f %.3f 0 0 %d %.3f %.3f Z"
                % (out, y0, out, y1, c, y1, r, r, sweep, c, y0))
    out = cy - h if side == 3 else cy + h              # 外端（方）
    c = cy + h - r if side == 3 else cy - h + r        # 半圆圆心
    x0, x1 = cx - r, cx + r
    sweep = 1 if side == 3 else 0
    return ("M%.3f %.3f L%.3f %.3f L%.3f %.3f A%.3f %.3f 0 0 %d %.3f %.3f Z"
            % (x0, out, x1, out, x1, c, r, r, sweep, x0, c))


def pcb_powerpad_d(hole_r=PCB_VIA_DRILL / 2.0):
    """2.05 方形散热盘，**按甚至奇规则挖掉 9 个钻孔**（3×3、0.50 间距）。

    ★ 为什么不能只画 9 个 `<circle>`（2026-10-17 用户实测）：铜盘是**实心填充**，
      同色的细圆圈画在它上面**根本看不出来**（截图里中央就是一块纯色）✗。
      真实焊盘是“铜被钻孔挖掉”，所以只要把孔**从铜里挖掉**，看到的就是板背景 ⇒
      和实物一样是 9 个孔 ✓（QC 也能一眼看出位置/孔径）。
    ★ 钻孔本身仍由 `<circle>` 提供（`svg2gerber.cpp:344`：元件里每个 circle 都是一个孔），
      两处半径对得上：铜孔 r = 0.100，钻孔圆 r = 0.150 / stroke 0.100 ⇒ 2r−sw = 0.20 ✓，
      且描边内缘正好压在铜孔边上 ✓。
    """
    s = PCB_PAD / 2.0
    d = ["M%.3f %.3f L%.3f %.3f L%.3f %.3f L%.3f %.3f Z"
         % (-s, -s, s, -s, s, s, -s, s)]
    half = (PCB_VIA_N - 1) / 2.0
    for iy in range(PCB_VIA_N):
        for ix in range(PCB_VIA_N):
            cx = (ix - half) * PCB_VIA_PITCH
            cy = (iy - half) * PCB_VIA_PITCH
            d.append("M%.3f %.3f a%.3f %.3f 0 1 0 %.3f 0 a%.3f %.3f 0 1 0 %.3f 0 Z"
                     % (cx - hole_r, cy, hole_r, hole_r, 2 * hole_r,
                        hole_r, hole_r, -2 * hole_r))
    return " ".join(d)


def pcb_svg():
    n = len(S_NAMES)
    lim = PCB_PAD_R + PCB_PAD_L / 2.0 + 0.55        # 2.70
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<!-- %s -->' % ID,
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="%.2f %.2f %.2f %.2f">' % (2 * lim, 2 * lim, -lim, -lim, 2 * lim, 2 * lim),
         '  <g id="copper1">']
    for pno in range(1, n + 1):
        cx, cy = pcb_pad_xy(pno)
        side = (pno - 1) // S_PER_SIDE
        L.append('   <path id="connector%dpad" d="%s" fill="#F7BD13" stroke="none" '
                 'connectorname="%s"/>'
                 % (pno - 1, pcb_pad_d(cx, cy, side), S_NAMES[pno - 1]))
    L.append('   <path id="connector%dpad" d="%s" fill="#F7BD13" fill-rule="evenodd" '
             'stroke="none" connectorname="%s"/>'
             % (n, pcb_powerpad_d(), S_PAD))
    # ── 热过孔（3×3）+ 底层散热铜：copper0 嵌在 copper1 里 ⇒ 两面都有铜 ✓
    #   ★ 元件里的 <circle> 默认就会被当成钻孔（svg2gerber.cpp:344）：孔径 = 2r − stroke-width
    #     ⇒ 2×0.150 − 0.100 = 0.20 ✓（stroke=0 会变成非镀铜孔 ✗）
    L.append('   <g id="copper0">')
    L.append('    <path d="%s" fill="#F7BD13" fill-rule="evenodd" stroke="none"/>'
             % pcb_powerpad_d())
    vo = PCB_VIA_DRILL + 2 * PCB_VIA_RING             # 铜盘外径 0.40
    vr = (vo + PCB_VIA_DRILL) / 4.0                  # 0.150
    vw = (vo - PCB_VIA_DRILL) / 2.0                  # 0.100
    half = (PCB_VIA_N - 1) / 2.0                     # 1（3 个孔 ⇒ ±1 格）
    for iy in range(PCB_VIA_N):
        for ix in range(PCB_VIA_N):
            cid = PCB_VIA_CID0 + iy * PCB_VIA_N + ix
            L.append('    <circle id="connector%dpad" connectorname="%s_VIA%d" '
                     'cx="%.3f" cy="%.3f" r="%.3f" stroke="#F7BD13" '
                     'stroke-width="%.3f" fill="none"/>'
                     % (cid, S_PAD, iy * PCB_VIA_N + ix + 1,
                        (ix - half) * PCB_VIA_PITCH, (iy - half) * PCB_VIA_PITCH, vr, vw))
    L.append('   </g>')
    # ── VSS / NC → PowerPAD 的顶层连接铜（p34：NC 应接到 PowerPAD ✓）
    #   ★ 三条要求（用户 2026-10-17）：① **全程 0.28 = 焊盘宽**（用**描边**画连接线，
    #     线宽天然恒定，不会出现颈缩）；② 从焊盘**直段**起步 ⇒ 与焊盘侧边齐平；
    #     ③ VSS 焊盘中心 y = ±1.0 比散热盘上缘高 0.025 ⇒ 用**两段相切圆弧**先下折到
    #     y = ∓0.885（= 散热盘上缘 + 0.14），再**满宽**进入散热盘 ⇒ 入口处上下缘
    #     正好压在“盘上缘 / 盘内 0.28”上，既无台阶也不收窄 ✓
    t = PCB_PAD / 2.0                                # 1.025（散热盘半边）
    hw = PCB_TIE_W / 2.0                             # 0.140
    start = PCB_PAD_R - PCB_PAD_L / 2.0 + hw + 0.02  # 1.460（焊盘直段内 0.02）
    y_in = -(t - hw)                                 # −0.885（带子上缘贴盘上缘）
    RUN = 0.38                                       # 下折的水平长度
    for pno in PCB_TIE_PINS:
        cx, cy = pcb_pad_xy(pno)
        side = (pno - 1) // S_PER_SIDE
        if side in (0, 2):                           # VSS：直线 → 双圆弧下折 → 满宽进盘
            drop = cy - y_in                         # −0.115
            r = (RUN * RUN + drop * drop) / (4.0 * abs(drop))
            x0 = (-start) if side == 0 else start
            xb0 = (-start + 0.04) if side == 0 else (start - 0.04)
            xb1 = (xb0 + RUN) if side == 0 else (xb0 - RUN)
            xm, ym = (xb0 + xb1) / 2.0, (cy + y_in) / 2.0
            xe = (-0.95) if side == 0 else 0.95
            s1, s2 = (1, 0) if side == 0 else (0, 1)
            d_path = ("M%.3f %.3f L%.3f %.3f A%.3f %.3f 0 0 %d %.3f %.3f "
                      "A%.3f %.3f 0 0 %d %.3f %.3f L%.3f %.3f"
                      % (x0, cy, xb0, cy, r, r, s1, xm, ym,
                         r, r, s2, xb1, y_in, xe, y_in))
            L.append('   <path d="%s" fill="none" stroke="#F7BD13" stroke-width="%.3f" '
                     'stroke-linecap="butt" stroke-linejoin="round"/>' % (d_path, PCB_TIE_W))
        else:                                        # NC：垂直直通，满宽进盘
            y_out = -start if side == 3 else start
            y_end = -(t - 0.05) if side == 3 else (t - 0.05)
            L.append('   <line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#F7BD13" '
                     'stroke-width="%.3f" stroke-linecap="butt"/>'
                     % (cx, y_out, cx, y_end, PCB_TIE_W))
    L.append('  </g>')
    # 丝印：四个角括号 + 1 脚圆点（本体边会被焊盘跨过 ⇒ 不画整圈框 ✗）
    L.append('  <g id="silkscreen">')
    b = PCB_BODY / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            L.append('   <line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#f0f0f0" '
                     'stroke-width="0.12"/>' % (sx * b, sy * b, sx * b, sy * (b - PCB_SILK_ARM)))
            L.append('   <line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#f0f0f0" '
                     'stroke-width="0.12"/>' % (sx * b, sy * b, sx * (b - PCB_SILK_ARM), sy * b))
    p1x, p1y = pcb_pad_xy(1)                        # 1 脚：左列最上面那只
    # 1 脚圆点放在**焊盘外侧**（同 CH347F 的口径 ✓）：本件焊盘跨过本体边，
    # 放"焊盘上方"会压到左上角的丝印括号 ✗ ⇒ 放焊盘左边、留 0.08 间隙 ✓
    L.append('   <circle cx="%.3f" cy="%.3f" r="%.2f" fill="#f0f0f0" stroke="none"/>'
             % (p1x - PCB_PAD_L / 2.0 - PCB_DOT_CLEAR - PCB_DOT_R, p1y, PCB_DOT_R))
    L.append('  </g>')
    L += ['</svg>', '']
    return "\n".join(L)


# ══════════════ fzp（连接器表：0..19 = 芯片 20 脚、20 = PowerPAD、21..23 = 面包板专用地针）
FZP_DESC = {
    1: "power ground for the boost charger",
    2: "DC input from the harvesting source (>= 4.7 uF to pin 1)",
    3: "MPPT sampling pin (VSTOR = 80%, GND = 50%, or divider)",
    4: "MPPT sample-and-hold capacitor (0.01 uF low leakage)",
    5: "active-low enable - connect to GND to enable the IC",
    6: "active-high buck enable - connect to VSTOR to enable",
    7: "VBAT overvoltage threshold divider (VRDIV / GND)",
    8: "divider bias output (high side of the resistor dividers)",
    9: "no connect - tie to the PowerPAD (datasheet p34)",
    10: "VBAT_OK hysteresis divider (VRDIV / GND)",
    11: "VBAT_OK threshold divider (VRDIV / GND)",
    12: "buck output voltage setting divider (VRDIV / GND)",
    13: "battery good digital output (referenced to VSTOR)",
    14: "buck converter output (>= 22 uF to pin 15)",
    15: "power ground for the buck converter / analog ground",
    16: "buck inductor (>= 4.7 uH to pin 14)",
    17: "no connect - tie to the PowerPAD (datasheet p34)",
    18: "storage element (super-cap / battery), >= 100 uF",
    19: "boost charger output (>= 4.7 uF + 0.1 uF to pin 1)",
    20: "boost inductor (22 uH to pin 2)",
}


def fzp_xml():
    n = len(S_NAMES)                                    # 20
    bb_ids = {BB_CONN[i]: BB_PINS[i][0] for i in range(len(BB_PINS))}
    conns = []
    for pno in range(1, n + 1):
        cid = pno - 1
        v = []
        if cid in bb_ids:
            v.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/>'
                     '</breadboardView>' % cid)
        v.append('    <schematicView><p layer="schematic" svgId="connector%dpin" '
                 'terminalId="connector%dterminal"/></schematicView>' % (cid, cid))
        v.append('    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>' % cid)
        conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                     '   <description>pin %d - %s</description>\n   <views>\n%s\n   </views>\n'
                     '  </connector>\n'
                     % (cid, S_NAMES[cid], pno, FZP_DESC.get(pno, S_NAMES[cid]), "\n".join(v)))
    # PowerPAD：独立成网（不进 bus ✓ AGENTS §5），三个视图都有
    conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                 '   <description>exposed thermal pad (datasheet: Thermal Pad / TI PowerPAD, '
                 'no pin number) - solder it and route it to GND; 3x3 0.2 mm thermal vias and '
                 'the bottom copper land are part of the footprint</description>\n'
                 '   <views>\n'
                 '    <schematicView><p layer="schematic" svgId="connector%dpin" '
                 'terminalId="connector%dterminal"/></schematicView>\n'
                 '    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n'
                 '   </views>\n  </connector>\n'
                 % (n, S_PAD, n, n, n))
    # 面包板专用地针（只在面包板视图）
    for cid in (21, 22, 23):
        conns.append('  <connector id="connector%d" name="GND" type="male">\n'
                     '   <description>module header ground pin (%s) - same net as VSS</description>\n'
                     '   <views>\n'
                     '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/>'
                     '</breadboardView>\n'
                     '   </views>\n  </connector>\n' % (cid, bb_ids[cid], cid))
    # ★ 9 个热过孔各成一个连接器（用户 2026-10-17 定）：它们与 PowerPAD 是**同一块铜**，
    #   物理上等价 ⇒ 进同一条总线；且每个都在 copper0/copper1 **两面**声明，
    #   面上都能拉线过去（对应 AGENTS §5「多焊盘同网络 = 每 pad 独立 connector + buses」✓）
    for i in range(PCB_VIA_N * PCB_VIA_N):
        cid = PCB_VIA_CID0 + i
        conns.append('  <connector id="connector%d" name="%s_VIA%d" type="male">\n'
                     '   <description>thermal via %d of the PowerPAD copper - plated through, '
                     'same net as the PowerPAD, routable on both copper layers</description>\n'
                     '   <views><pcbView>\n'
                     '    <p layer="copper0" svgId="connector%dpad"/>\n'
                     '    <p layer="copper1" svgId="connector%dpad"/>\n'
                     '   </pcbView></views>\n  </connector>\n'
                     % (cid, S_PAD, i + 1, i + 1, cid, cid))
    via_members = "".join('   <nodeMember connectorId="connector%d"/>\n'
                          % (PCB_VIA_CID0 + i) for i in range(PCB_VIA_N * PCB_VIA_N))
    # ★ 2026-10-17 用户定：引脚里的 GND/VSS 都要与散热盘连上（做法同 VSS/NC 连桥）⇒
    #   VSS(0)、VSS(14)、面包板地针(21/22/23)、PowerPAD(20) 与 9 个热过孔**同一条 GND 总线**。
    bus = (' <buses>\n  <bus id="GND">\n'
           '   <nodeMember connectorId="connector0"/>\n'
           '   <nodeMember connectorId="connector14"/>\n'
           '   <nodeMember connectorId="connector21"/>\n'
           '   <nodeMember connectorId="connector22"/>\n'
           '   <nodeMember connectorId="connector23"/>\n'
           '   <nodeMember connectorId="connector%d"/>\n%s'
           '  </bus>\n </buses>\n' % (n, via_members))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n <label>U</label>\n <date>2026-10-17</date>\n'
        ' <tags><tag>IC</tag><tag>PMIC</tag><tag>energy harvesting</tag><tag>TI</tag>'
        '<tag>VQFN-20</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">TI energy harvester</property>\n'
        '  <property name="chip">BQ25570</property>\n'
        '  <property name="pins">20</property>\n'
        '  <property name="part number">BQ25570RGR</property>\n'
        '  <property name="package">VQFN-20 (RGR)</property>\n'
        ' </properties>\n'
        ' <description>Texas Instruments bq25570 nanopower boost charger with MPPT plus '
        'nano-power buck converter, VQFN-20 RGR 3.5x3.5 mm / 0.5 mm pitch. The exposed '
        'PowerPAD (no pin number) must be soldered and routed to GND; NC pins 9/17 and both '
        'VSS pins are tied to it in this footprint. 3x3 0.2 mm thermal vias and the bottom-side '
        'thermal land are part of the PCB artwork.</description>\n'
        ' <views>\n'
        '  <iconView><layers image="icon/%s_icon.svg"><layer layerId="icon"/></layers></iconView>\n'
        '  <breadboardView><layers image="breadboard/%s_breadboard.svg">'
        '<layer layerId="breadboard"/></layers></breadboardView>\n'
        '  <schematicView><layers image="schematic/%s_schematic.svg">'
        '<layer layerId="schematic"/></layers></schematicView>\n'
        '  <pcbView><layers image="pcb/%s_pcb.svg"><layer layerId="silkscreen"/>'
        '<layer layerId="copper0"/><layer layerId="copper1"/></layers></pcbView>\n'
        ' </views>\n <connectors>\n%s </connectors>\n%s</module>\n'
        % (ID, ID, ID, ID, ID, ID, "".join(conns), bus))


def main():
    p = os.path.join(HERE, "svg.icon.%s_icon.svg" % ID)
    open(p, "w", encoding="utf-8", newline="\n").write(icon_svg())
    print("写入 %s ✓" % os.path.basename(p))
    q = os.path.join(HERE, "svg.breadboard.%s_breadboard.svg" % ID)
    open(q, "w", encoding="utf-8", newline="\n").write(breadboard_svg())
    print("写入 %s ✓（板 %.2f×%.2f mm ✓ 估算值 ✗）" % (os.path.basename(q), BB_W, BB_H))
    r = os.path.join(HERE, "svg.schematic.%s_schematic.svg" % ID)
    open(r, "w", encoding="utf-8", newline="\n").write(schematic_svg())
    print("写入 %s ✓（四边排脚：1..5 左 / 6..10 下 / 11..15 右 / 16..20 上 + %s ✓）"
          % (os.path.basename(r), S_PAD))
    s = os.path.join(HERE, "svg.pcb.%s_pcb.svg" % ID)
    open(s, "w", encoding="utf-8", newline="\n").write(pcb_svg())
    print("写入 %s ✓（land pattern：焊盘 %.2f×%.2f R%.2f、焊盘区 %.2f、散热盘 %.2f、"
          "%d 个 ⌀%.2f 热过孔、VSS/NC 已连 PowerPAD ✓）"
          % (os.path.basename(s), PCB_PAD_W, PCB_PAD_L, PCB_PAD_RAD,
             2 * (PCB_PAD_R + PCB_PAD_L / 2.0), PCB_PAD,
             PCB_VIA_N * PCB_VIA_N, PCB_VIA_DRILL))
    t = os.path.join(HERE, "part.%s.fzp" % ID)
    open(t, "w", encoding="utf-8", newline="\n").write(fzp_xml())
    print("写入 %s ✓（21 个芯片连接器 + 3 个面包板专用地针 + 9 个过孔连接器；"
          "PowerPAD 与 9 个过孔同网、两面都可布线 ✓）"
          % os.path.basename(t))
    import zipfile
    out_dir = os.path.normpath(os.path.join(HERE, "..", "..", "fzpz"))
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "%s.fzpz" % ID)
    files = sorted(["part.%s.fzp" % ID, "svg.icon.%s_icon.svg" % ID,
                    "svg.breadboard.%s_breadboard.svg" % ID,
                    "svg.schematic.%s_schematic.svg" % ID,
                    "svg.pcb.%s_pcb.svg" % ID])
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in files:
            z.write(os.path.join(HERE, fn), fn)
    print("写入 %s ✓（%d 字节；记得再跑 tools\\repack_fzpz.py 统一 LF）"
          % (os.path.basename(dst), os.path.getsize(dst)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
