#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — CH347F 高速 USB 转 SPI/I2C/JTAG/UART 芯片（WCH）Fritzing 元件生成器。
================================================================================
元件形态（用户 2026-09-14 定）：
  - **芯片**（CH347F）出 icon / 原理图 / PCB 三个视图；
  - **面板上用的那块官方评估板 CH347F-EVT-R0-1v0** 只出现在**面包板视图**，
    板上排针**全部做成可连线 connector**（按信号名映射到芯片脚；3V3/GND/5V 用 <buses> 互通）。

资料（都在本机，不是猜的）：
  · `D:\Downloads\CH347DS1.PDF`（CH347 手册 V1.5）：
      - 封装：**QFN28，塑体 4×4mm，引脚节距 0.4mm**；CH347T = TSSOP20 4.4×6.5mm / 0.65mm；
      - 第 3 页引脚排列图（本脚本的引脚几何/编号顺序来源，TOP VIEW）：
          底边 左→右 = 1..7；右边 下→上 = 8..14；顶边 右→左 = 15..21；左边 上→下 = 22..28；
          **底板 EPAD = 0#（GND，可选但建议接）**；
      - 引脚名（表 4-1..4-6，多功能的按排列图上的写法）：
          0 GND(EPAD) | 1 XI | 2 XO | 3 RST# | 4 TXD1 | 5 RXD1 | 6 VIO | 7 DTR1/TNOW1/SCS1
          8 ACT/SRST | 9 TRST/GPIO3 | 10 DTR0/TNOW0/GPIO2 | 11 CTS1/SCL | 12 RTS1/SDA
          13 SCS0 | 14 SCK | 15 MISO | 16 MOSI | 17 CTS0/GPIO0 | 18 RTS0/GPIO1 | 19 TXD0
          20 GND | 21 VCC | 22 RXD0 | 23 TCK/SWDCLK/GPIO4 | 24 TDO/GPIO5 | 25 TDI/GPIO6
          26 TMS/SWDIO/GPIO7 | 27 UD- | 28 UD+
  · `D:\Downloads\CH347EVT\EVT\PUB\CH347EVT_EN.pdf`（评估板说明 V1.5）：板级单元说明 + 实物照片；
  · `D:\Downloads\CH347EVT\EVT\PCB\CH347SCH.pdf`：评估板原理图（面包板视图的排针定义来源）。

进度（按 fritzing-parts-langhua AGENTS.md §2 芯片类工作流）：
  [x] 1. icon（QFN28 顶视图：黑体 4×4 + 四边金焊盘 + pin1 圆点）
  [x] 2. breadboard（= CH347F-EVT-R0-1v0 整块评估板）
  [x] 3. schematic（矩形 29 脚符号）
  [x] 4. pcb（QFN28 4×4 P0.4 + 底板 EPAD）
  [ ] 5. part.CH347F.fzp + 打包 fzpz
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH347F"
TITLE = "CH347F (USB to SPI/I2C/JTAG/UART, QFN28)"
LABEL = "U"
PACKAGE = "QFN28"
FAMILY = "WCH USB Bridge"
FZPZ = "CH347F.fzpz"
FZP = "part.%s.fzp" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID

# 颜色（与仓库其它芯片 icon 一致）
BODY = "#303030"
PAD = "#f7bf13"
MARK = "#c0c0c0"
TXT = "#c0c0c0"

# ---- 几何（mm，1:1 实物）----------------------------------------------------
# QFN28：塑体 4.0×4.0，节距 0.4，每边 7 脚，焊盘 0.2(沿边) × 0.1(径向外伸)
TOT = 4.2
BODY_SIZE = 4.0
PITCH = 0.4
N_PER_SIDE = 7
PAD_W = 0.2
PAD_LEN = (TOT - BODY_SIZE) / 2.0        # 0.1

# 引脚号（datasheet 第 3 页排列图，TOP VIEW；从底板左侧起逆时针）
#   底边 左→右 = 1..7、右边 下→上 = 8..14、顶边 右→左 = 15..21、左边 上→下 = 22..28
PIN_NAMES = {
    0: "GND", 1: "XI", 2: "XO", 3: "RST#", 4: "TXD1", 5: "RXD1", 6: "VIO",
    7: "DTR1/TNOW1/SCS1", 8: "ACT/SRST", 9: "TRST/GPIO3", 10: "DTR0/TNOW0/GPIO2",
    11: "CTS1/SCL", 12: "RTS1/SDA", 13: "SCS0", 14: "SCK",
    15: "MISO", 16: "MOSI", 17: "CTS0/GPIO0", 18: "RTS0/GPIO1", 19: "TXD0",
    20: "GND", 21: "VCC", 22: "RXD0", 23: "TCK/SWDCLK/GPIO4", 24: "TDO/GPIO5",
    25: "TDI/GPIO6", 26: "TMS/SWDIO/GPIO7", 27: "UD-", 28: "UD+",
}


def _centers():
    """每边 7 个焊盘中心（沿边方向），对称于本体中心。"""
    c0 = TOT / 2.0 - (N_PER_SIDE - 1) * PITCH / 2.0
    return [c0 + i * PITCH for i in range(N_PER_SIDE)]


def icon_svg():
    """QFN28 顶视图 icon：黑体 4×4 + 四边金焊盘 + pin1 圆点 + 丝印名。"""
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" viewBox="0 0 %.1f %.1f">\n'
             % (TOT, TOT, TOT, TOT))
    L.append('  <g id="icon">\n')
    m = PAD_LEN
    L.append('    <rect x="%.3f" y="%.3f" width="%.2f" height="%.2f" '
             'fill="%s" stroke="none"/>\n' % (m, m, BODY_SIZE, BODY_SIZE, BODY))
    for c in _centers():
        L.append('    <rect x="%.3f" y="0" width="%.2f" height="%.3f" fill="%s" stroke="none"/>\n'
                 % (c - PAD_W / 2, PAD_W, PAD_LEN, PAD))                      # 上
        L.append('    <rect x="%.3f" y="%.3f" width="%.2f" height="%.3f" fill="%s" stroke="none"/>\n'
                 % (c - PAD_W / 2, TOT - PAD_LEN, PAD_W, PAD_LEN, PAD))       # 下
        L.append('    <rect x="0" y="%.3f" width="%.3f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (c - PAD_W / 2, PAD_LEN, PAD_W, PAD))                       # 左
        L.append('    <rect x="%.3f" y="%.3f" width="%.3f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (TOT - PAD_LEN, c - PAD_W / 2, PAD_LEN, PAD_W, PAD))        # 右
    # pin1 圆点：左下角（对齐下排首脚 x 与左排末脚 y）
    c0, cN = _centers()[0], _centers()[-1]
    L.append('    <circle cx="%.3f" cy="%.3f" r="0.18" fill="%s" stroke="none"/>\n' % (c0, cN, MARK))
    cx = TOT / 2.0
    L.append('    <text x="%.3f" y="%.2f" font-size="0.62" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">CH347F</text>\n' % (cx, cx - 0.15, TXT))
    L.append('    <text x="%.3f" y="%.2f" font-size="0.34" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">QFN28</text>\n' % (cx, cx + 0.62, TXT))
    L.append('  </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# =============================================================================
# 面包板视图 = 官方评估板 **CH347F-EVT-R0-1v0**（用户 2026-09-14 定：芯片出 icon/原理图/PCB，
# 板子只出现在面包板视图；板上排针全部做成可连线 connector）
#
# 坐标约定（同 ESP32-S3 / nanoCH32V203 / TX-AH）：内部 **100 单位 = 2.54mm**，整板 scale(0.072)
#   → 排针中心落在 Fritzing 面包板孔距上（都取 100 的整数倍）。
# 板尺寸/排针位置**按照片比例起稿**（用户 2026-09-14 同意"我先起稿、他在 Inkscape 里校"）。
# 配色取自实物照片采样：PCB 深蓝 #002d68、丝印白 #ffffff。
#
# 排针定义（用户 2026-09-14 对实物逐条确认）：
#   P4（8 针 = **2 列竖排**，用户 2026-09-15）：左列上→下 = SCS0 / SCK / MISO / MOSI，
#        右列上→下 = 3V3 / GND / GND / SCS1
#        （用户 2026-09-14 原话“从左到底是 SCS0/SCK/MISO/MOSI，从右到底是 SCS1/GND/GND/3V3”）
#   P2（7 针，上→下）= DTR0 / CTS0 / RTS0 / TXD0 / RXD0 / GND / 3V3
#   P3（7 针，上→下）= DTR1 / CTS1 / RTS1 / TXD1 / RXD1 / GND / 3V3
#   P8 = 3 针 FLASH-CS 跳线（选 FLASH 的 CS 走 SCS0 / SCS1）；P1 = USB **方口母座**
#        （其图形**直接复用 USB-B01 元件的 icon**，用户 2026-09-15）；
#   板上**没有 5V 排针脚**；P5 = I2C 4 针（SDA/SCL/GND/3V3）、P6/P7 = JTAG 2×10、
#   VIO = IO 电压选择跳线（VIO↔3V3）—— 这些**下一刀**再加（本次先出 P1/P2/P3/P4 + 丝印）。
#
# connector id 规则：能对上芯片脚的排针脚用**芯片脚号**（`PIN_NAMES` 的键）；
#   同一芯片脚被两个排针引出时（如 pin7 = DTR1/TNOW1/SCS1），只把 id 给"名字与芯片脚主名一致"
#   的那个，另一个用**面包板专用号**（`_rail` 从 29 起）—— 与 SMA 元件同规矩：
#   每个焊盘独立 connector，同网在 `.fzp` 里用 `<buses>` 互联。
# =============================================================================
S = 0.072                                # 内部单位（100 = 2.54mm）→ viewBox 单位
MM_U = 39.37 * S                         # 1mm → viewBox 单位
ICON_U = MM_U                            # 图标里的 mm → viewBox 单位
USB_U = ICON_U                           # 供 _usb_b01_icon 用（同一换算）
# 板尺寸 = 用户卡尺实测 50.2 × 55.5 mm；viewBox 单位 = 内部单位 × S
BOARD_W, BOARD_H = 1976 * S, 2185 * S
BOARD_MM = (50.19, 55.50)
BOARD_RX = 1.5 * MM_U                    # 板框圆角（用户 2026-09-15）；1.5mm 量自实物照片
BOARD_SW = 6 * S                         # 板框描边（手工版里是 6 内部单位 → 必须 ×S；
#                                          漏乘会变成 2.1mm 宽的黑边，见 tools/README.md）
PCB_BLUE = "#002d68"
PCB_EDGE = "#001745"
PIN_FILL = "#d0d0d0"
PIN_EDGE = "#8a8a8a"
SILK = "#ffffff"
SILK_D = "#c8ccd0"
SILK_L = "#f5f5f5"
USB_CX, USB_FACE_Y = 988 * S, BOARD_H    # P1 方口母座：中心 x / 插口面贴板下缘

# 数据表由 tools/byhand_export.py 从"手工对齐版"自动生成（说明见 byHand_tables.py 顶部）
from byHand_tables import (PADS, ICONS, TEXTS, EXTRA_RECTS, EXTRA_CIRCLES, EXTRA_LINES)

# =============================================================================
# 面包板焊盘 → connector 号（**面包板 svg 与 .fzp 的共同单源**）
#
# 规则（用户 2026-09-15 定，沿用 CH32V203C8T6 / SMA 的规矩）：
#   · 能唯一对上一个芯片脚的焊盘 → **用芯片脚号**（0..28）；
#   · 同一芯片脚被多个排针引出（SCS1↔7、SCL↔11、SDA↔12）、或板上额外的电源/地轨
#     （3V3 / VIO / 多余 GND / GND-KEY / VREF / FLASH_CS）→ 用**面包板专用号**（29 起），
#     每个焊盘**各自是一个 connector**（都能接线），同网再用 `.fzp` 的 `<buses>` 互联。
#   · 芯片脚 1/2/3/27/28（XI/XO/RST#/UD-/UD+）在板上没引到排针（直接进 USB 座/晶振）→
#     只有原理图与 PCB 视图，面包板视图里没有它们（CH32V203C8T6 也是这么做的）。
# =============================================================================
_PIN_ALIAS = {}
for _n, _nm in PIN_NAMES.items():
    for _a in _nm.split("/"):
        _PIN_ALIAS.setdefault(_a, _n)
_PIN_ALIAS["3V3"] = 21        # 板上的 3V3 轨就是芯片 VCC(21)
# 例外：x=254.14 那列焊盘（JP1）在手工版里 connectorname 是旧的 —— 是 Ctrl+D 复制 P5 留下的
# SDA/SCL/GND/VIO；板上丝印（x≈300，用户 2026-09-15 对齐时填的）是 GND/VIO/VIO/3V3
# （VIO 选择跳线）。以**丝印**为准，按 y 升序写在这里。
_PAD_NET_FIX = {254.14: ("GND", "VIO", "VIO", "3V3")}


def pad_map():
    """[(原 id, 网名, x, y, connector 号)]：0..28 = 芯片脚，29+ = 面包板专用。

    分配顺序（可复现，且与上面注释的规矩一致）：
      ① 网名**与芯片脚主名一致**的焊盘优先拿该脚号（如 CTS1 拿 11、SCS0 拿 13）；
      ② 其余焊盘按 上→下、左→右：能对上一个还没被占的芯片脚就拿脚号，否则发板级号；
      ③ 地的两个脚号（20 GND / 0 EPAD）发给最先遇到的两个 GND 焊盘，剩下的 GND 发板级号。
    """
    cols = {}
    for cid, nm, x, y in PADS:
        cols.setdefault(x, []).append((y, cid, nm))
    fixed = {}
    for x, names in _PAD_NET_FIX.items():
        for (y, _c, _n), net in zip(sorted(cols.get(x, [])), names):
            fixed[(x, y)] = net
    rows = [[cid, fixed.get((x, y), nm), x, y, None]
            for cid, nm, x, y in sorted(PADS, key=lambda p: (p[3], p[2]))]
    used, rail = {}, [29]
    for row in rows:                                   # ① 主名优先
        pin = _PIN_ALIAS.get(row[1])
        if pin is None or row[1] == "GND" or pin in used:
            continue
        if row[1] == PIN_NAMES[pin].split("/")[0]:
            used[pin], row[4] = pin, pin
    for row in rows:                                   # ② 其余（地除外）
        if row[4] is not None or row[1] == "GND":
            continue
        pin = _PIN_ALIAS.get(row[1])
        if pin is not None and pin not in used:
            used[pin], row[4] = pin, pin
        else:
            row[4] = rail[0]
            rail[0] += 1
    for row in [r for r in rows if r[4] is None]:      # ③ 地
        for pin in (20, 0):
            if pin not in used:
                used[pin], row[4] = pin, pin
                break
        else:
            row[4] = rail[0]
            rail[0] += 1
    return [tuple(r) for r in rows]


# 同网总线（`.fzp` 的 <buses>）：(总线名, 芯片脚号, 板级网名)
BUSES = [("GND", (20, 0), ("GND", "GND/KEY")),      # 20 = GND、0 = EPAD（板上同地）
         ("VCC", (21,), ("3V3",)),                    # 板上 3V3 轨
         ("VIO", (6,), ("VIO",)),
         ("SCL", (11,), ("SCL",)),                    # pin11 = CTS1/SCL
         ("SDA", (12,), ("SDA",)),                    # pin12 = RTS1/SDA
         ("SCS1", (7,), ("SCS1",))]                   # pin7 = DTR1/TNOW1/SCS1


def _usb_b01_icon(fx, fy, u=USB_U):
    """嵌入 USB-B01 的 icon 几何（跨部件复用**仓库内**文件，AGENTS §4 允许）：
    读 `../USB-B01/svg.icon.USB-B01_icon.svg` 里的 <rect>，把 mm 换算成内部单位（u），
    并让**插口面**落在 (fx = 座中心 x, fy = 插口面 y)、后方朝板内（向上）。
    单源：几何只在 USB-B01/gen_part.py 定义，这里不另抄一份。"""
    src = os.path.join(OUT_DIR, "..", "USB-B01", "svg.icon.USB-B01_icon.svg")
    art = open(src, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<rect\s+([^>]*?)/>', art):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        x, y = float(a["x"]), float(a["y"])
        w, h = float(a["width"]), float(a["height"])
        out.append('  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                   'stroke="%s" stroke-width="%.1f"/>\n'
                   % (fx + x * u, fy - (y + h) * u, w * u, h * u,
                      a.get("fill", "#c9c9c9"), a.get("stroke", "#8f8f8f"),
                      float(a.get("stroke-width", 0.1)) * u))
    return "".join(out)


def _bake_icon(part_id, cx, cy, rot=0):
    """把 `../<part_id>/svg.icon.<part_id>_icon.svg` 的 `<g id="icon">` 内容按 1:1 真实尺寸
    **烘成绝对坐标**嵌入（cx, cy 为内部单位、图标自身 viewBox 中心对准它，再绕中心转 rot 度）。

    为什么要烘：AGENTS §5 —— 嵌套 transform 在不同渲染器（Inkscape / Fritzing / VS Code 预览）
    下解释不一致，会出现"芯片缩小到看不见"；烘成绝对值就与其它元件（LD1117/USB-B01）一致。
    rect/circle 全部烘成绝对坐标；只有**文字**保留 rotate()（Fritzing 官方也用这个写法）。
    """
    path = os.path.join(OUT_DIR, "..", part_id, "svg.icon.%s_icon.svg" % part_id)
    art = open(path, encoding="utf-8").read()
    vb = re.search(r'viewBox="([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+)"', art)
    body = re.search(r'<g\s+id="icon">(.*)</g>', art, re.S)
    if not vb or not body:
        raise RuntimeError("图标几何读不到（%s）：需要 viewBox + <g id=\"icon\">" % path)
    x0, y0, w, h = (float(v) for v in vb.groups())
    ccx, ccy = x0 + w / 2.0, y0 + h / 2.0           # 图标几何中心（mm）
    cx, cy = cx * S, cy * S                          # 内部单位 → viewBox 单位
    ca, sa = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1), -90: (0, -1)}[rot]

    def m(px, py):
        """图标局部 mm → 面包板 viewBox 坐标"""
        dx, dy = (px - ccx) * ICON_U, (py - ccy) * ICON_U
        return (cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)

    out = []
    for rm in re.finditer(r'<rect\s+([^>]*?)/>', body.group(1)):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', rm.group(1)))
        rx, ry = float(a["x"]), float(a["y"])
        rw, rh = float(a["width"]), float(a["height"])
        ps = [m(rx, ry), m(rx + rw, ry), m(rx, ry + rh), m(rx + rw, ry + rh)]
        xs = [p[0] for p in ps]; ys = [p[1] for p in ps]
        attrs = ' fill="%s"' % a.get("fill", "none")
        if a.get("stroke") and a["stroke"] != "none":
            attrs += ' stroke="%s" stroke-width="%.3f"' % (a["stroke"],
                                                           float(a.get("stroke-width", 0)) * ICON_U)
        out.append('  <rect x="%.3f" y="%.3f" width="%.3f" height="%.3f"%s/>\n'
                   % (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys), attrs))
    for cm in re.finditer(r'<circle\s+([^>]*?)/>', body.group(1)):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        p = m(float(a["cx"]), float(a["cy"]))
        out.append('  <circle cx="%.3f" cy="%.3f" r="%.3f" fill="%s" stroke="none"/>\n'
                   % (p[0], p[1], float(a["r"]) * ICON_U, a.get("fill", "none")))
    for tm in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', body.group(1), re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tm.group(1)))
        p = m(float(a.get("x", 0)), float(a.get("y", 0)))
        t = '  <text x="%.3f" y="%.3f" font-size="%.3f" font-family="DroidSans" fill="%s"' \
            % (p[0], p[1], float(a.get("font-size", 1)) * ICON_U, a.get("fill", "#c0c0c0"))
        if a.get("text-anchor"):
            t += ' text-anchor="%s"' % a["text-anchor"]
        if rot:
            t += ' transform="rotate(%.1f,%.3f,%.3f)"' % (rot, p[0], p[1])
        out.append(t + '>%s</text>\n' % tm.group(2).strip())
    other = set(re.findall(r'<(\w+)', body.group(1))) - {"rect", "circle", "text"}
    if other:
        raise RuntimeError("%s 的 icon 里有本函数不支持的图元：%s" % (part_id, sorted(other)))
    return "".join(out)


def gen_breadboard_svg():
    """CH347F-EVT-R0-1v0 评估板面包板视图（几何全部来自上面六张表；**零嵌套变换**）。"""
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %.1f %.1f">\n'
         % (BOARD_MM[0], BOARD_MM[1], BOARD_W, BOARD_H),
         ' <g id="breadboard">\n',
         '  <rect x="0" y="0" width="%.1f" height="%.1f" rx="%.2f" ry="%.2f" fill="%s" '
         'stroke="%s" stroke-width="%.2f"/>\n'
         % (BOARD_W, BOARD_H, BOARD_RX, BOARD_RX, PCB_BLUE, PCB_EDGE, BOARD_SW)]
    # 其它图形（两脚件 / 跳线 / LED1 / 丝印外框）——表里已是**旋转后的外接框**，不再加 rotate
    for x, y, w, h, fill, rot, stroke, sw in EXTRA_RECTS:
        a = ' fill="%s"' % fill if fill and fill != "None" else ' fill="none"'
        if stroke and stroke != "None":
            a += ' stroke="%s"' % stroke
            if sw and sw != "None":
                a += ' stroke-width="%.3f"' % (float(sw) * S)
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"%s/>\n'
                 % (x * S, y * S, w * S, h * S, a))
    for x, y, r, fill, stroke, sw in EXTRA_CIRCLES:
        a = ' fill="%s"' % (fill if fill and fill != "None" else "none")
        if stroke and stroke != "None":
            a += ' stroke="%s"' % stroke
            if sw and sw != "None":
                a += ' stroke-width="%.3f"' % (float(sw) * S)
        L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f"%s/>\n' % (x * S, y * S, r * S, a))
    for x1, y1, x2, y2, stroke, sw in EXTRA_LINES:
        L.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                 'stroke-width="%.2f"/>\n'
                 % (x1 * S, y1 * S, x2 * S, y2 * S, stroke,
                    (float(sw) if sw else 1) * S if (float(sw) if sw else 1) > 2
                    else (float(sw) if sw else 1)))
    # 板上元件
    for part, x, y, rot in ICONS:
        L.append(_bake_icon(part, x, y, rot))
    # P1 = USB 方口母座（复用 USB-B01 元件的 icon，插口面贴板下缘）
    L.append(_usb_b01_icon(USB_CX, USB_FACE_Y))
    # 排针脚（id 用 pad_map() 定的**最终 connector 号** → 与 .fzp / 原理图同一套号；
    # 手工版里的 Inkscape id（connector32pin 那种）有重复且与芯片脚对不上，不能用）
    for _cid, net, x, y, cn in pad_map():
        L.append('  <circle id="connector%dpin" connectorname="%s" cx="%.2f" cy="%.2f" r="%.2f" '
                 'fill="%s" stroke="%s" stroke-width="%.2f"/>\n'
                 % (cn, net, x * S, y * S, 26 * S, PIN_FILL, PIN_EDGE, 5 * S))
    # 丝印（只有带旋转的才带 transform）
    for txt, x, y, fs, anchor, rot, fill, fw in TEXTS:
        a = ' fill="%s"' % (fill if fill and fill != "None" else SILK)
        if anchor and anchor != "None":
            a += ' text-anchor="%s"' % anchor
        if fw:
            a += ' font-weight="%s"' % fw
        if rot:
            a += ' transform="rotate(%.1f,%.2f,%.2f)"' % (rot, x * S, y * S)
        L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-family="DroidSans"%s>%s</text>\n'
                 % (x * S, y * S, fs * S, a, txt))
    L += [' </g>\n', '</svg>\n']
    return "".join(L)


# =============================================================================
# 原理图 —— 矩形符号（29 脚；QFN28 逆时针 7/7/7/7 + EPAD 0 号在底边最左）
#
# 排布口径（用户 2026-09-15 定；遵循 AGENTS §2「引脚号逆时针」与仓库先例
# CH340C(SOP16) / CH32V203C8T6(LQFP48)——它们都是**沿方框逆时针**排引脚号）：
#   底边（左→右）= 0 1 2 3 4 5 6 7        右（下→上）= 8..14
#   顶边（右→左）= 15 16 17 18 19 20 21   左（上→下）= 22..28
#   数据手册第 3 页的 QFN28 物理排列本来就是逆时针 7/7/7/7（底 1-7 / 右 8-14 / 顶 15-21 /
#   左 22-28），照搬即可；EPAD(0#) 放底边最左（与 pin1/pin28 相邻，同实物中心热焊盘）。
#   顺带把功能也分开了：下 = 晶振+UART1、右 = JTAG+I2C+SPI、上 = SPI+UART0+电源、左 = JTAG+USB。
#
# 几何口径（AGENTS §5「矩形封装（方框）原理图符号规则」，与 CH340C / CH32V203C8T6 同）：
#   1. 左右引脚数字在**引线上方**（不与引线相交）；上下引脚数字在**引脚左侧**（rotate(270)，从下至上）。
#   2. 引脚名都在框内、书写方向同数字；名/数字/引脚线**同色**（用户 2026-09-15 定：全黑）。
#   3. 整图同字号 FN=35（≈0.889mm ≈ Fritzing 官方引脚数字 0.881944mm）；芯片名 79（2.0mm，醒目）。
#   4. 引脚名中线与引脚对齐：左右用手动基线偏移 BASELINE_OFF=round(FN*0.35)（不用 dominant-baseline，
#      cairosvg/Fritzing 不支持它 → 左右名会不居中）。
#   5. 名与边框保持一个字符 CH=FN，分别居左/右/下/上；数字在线外侧，与名互不重叠。
#   6. 四角无引脚区 CORNER=(最长名+1)×int(FN*0.58)：上下名（竖排）与左右名（横排）靠它隔开；
#      框 = 每边最大脚数×P + 2×CORNER（所以底边 8 脚 → 宽 8P+2C，高 7P+2C）。
#   7. 端点：connectorNterminal = 22×22 **不可见** rect（靠引脚线末端吸附连线，不画夸张黑点）；
#      connectorNpin = class="pin" 的 <line>，stroke-width 5（与 CH340C/CH32V203C8T6 一致）。
#   物理尺寸由 width/height(in) 定：1000 单位 = 1in（AGENTS §5）。
# =============================================================================
SCHEM_INTERIOR = "#787878"       # 框线：Fritzing 官方 IC 符号的浅灰（CH340C/W25Q16JV 同）


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def gen_schematic_svg():
    """矩形符号：4 边逆时针排 29 脚（见上面口径）。"""
    P, WIRE, CH, FN = 100, 130, 35, 35        # 脚距 2.54mm / 引线长 / 一字符间距 / 整图字号
    BASELINE_OFF = round(FN * 0.35)           # 手动垂直居中（不用 dominant-baseline）
    max_len = max(len(PIN_NAMES[i]) for i in range(29))     # 16：DTR0/TNOW0/GPIO2 …
    CORNER = (max_len + 1) * int(FN * 0.58)
    BX0, BY0 = 340, 200
    N_BOT, N_SIDE = 8, 7                      # 底边 8 脚（含 EPAD 0 号）、其它三边各 7 脚
    BW, BH = N_BOT * P + 2 * CORNER, N_SIDE * P + 2 * CORNER
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - WIRE - 5                 # viewBox 贴合内容（裁边）
    VBW, VBH = BW + 2 * WIRE + 10, BH + 2 * WIRE + 10
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.6fin" height="%.6fin" '
         'viewBox="%d %d %d %d">\n' % (VBW / 1000.0, VBH / 1000.0, VBX, VBY, VBW, VBH),
         ' <g id="schematic">\n',
         '  <rect class="interior rect" x="%d" y="%d" width="%d" height="%d" '
         'fill="#FFFFFF" stroke="%s" stroke-width="5"/>\n' % (BX0, BY0, BW, BH, SCHEM_INTERIOR)]

    def wire(cn, x1, y1, x2, y2, tx, ty):
        """一条引脚的**线 + 不可见端点**（端点落在引线末端，靠它吸附连线）。"""
        L.append('  <line class="pin" id="connector%dpin" connectorname="%s" x1="%d" y1="%d" '
                 'x2="%d" y2="%d" stroke="#000000" stroke-width="5"/>\n'
                 % (cn, _esc(PIN_NAMES[cn]), x1, y1, x2, y2))
        L.append('  <rect class="terminal" id="connector%dterminal" x="%d" y="%d" width="22" '
                 'height="22" fill="none" stroke="none"/>\n' % (cn, tx - 11, ty - 11))

    def num_h(cn, x1, x2, y):
        """左右引脚的编号：横排，放引线**上方**（不与引线相交）。"""
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                 'font-family="DroidSans">%d</text>\n' % (x1 + (x2 - x1) // 2, y - 24, FN, cn))

    def num_v(cn, x, y):
        """上下引脚的编号：竖排 rotate(270)，放引脚**左侧**（从下至上）。"""
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                 'font-family="DroidSans" transform="rotate(270 %d %d)">%d</text>\n'
                 % (x - FN, y, FN, x - FN, y, cn))

    def nm_h(cn, x, y, anchor):
        """左右引脚的**名**：框内横排，与引脚水平中线对齐（手动基线偏移）。"""
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="%s" '
                 'font-family="DroidSans">%s</text>\n'
                 % (x, y + BASELINE_OFF, FN, anchor, _esc(PIN_NAMES[cn])))

    def nm_v(cn, x, y):
        """上下引脚的**名**：框内竖排 rotate(270)、以锚点为中心，自边框向内一个字符 CH。"""
        ln = int(len(PIN_NAMES[cn]) * FN * 0.58)      # 文字长度（rotate270+middle → 以锚点居中）
        yy = y - CH - ln // 2 if y > BY0 + BH // 2 else y + CH + ln // 2
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                 'font-family="DroidSans" transform="rotate(270 %d %d)">%s</text>\n'
                 % (x, yy, FN, x, yy, _esc(PIN_NAMES[cn])))

    # 底边 0..7（左→右）
    for i, cn in enumerate(range(0, N_BOT)):
        x = BX0 + CORNER + P // 2 + i * P
        wire(cn, x, BY1, x, BY1 + WIRE, x, BY1 + WIRE)
        num_v(cn, x, BY1 + 55)
        nm_v(cn, x, BY1)
    # 右 8..14（下→上）：接着底边的 7 往右上走，才是**逆时针连续**
    for i, cn in enumerate(range(8, 15)):
        y = BY1 - CORNER - P // 2 - i * P
        wire(cn, BX1, y, BX1 + WIRE, y, BX1 + WIRE, y)
        num_h(cn, BX1, BX1 + WIRE, y)
        nm_h(cn, BX1 - CH, y, "end")
    # 顶 15..21（右→左）
    for i, cn in enumerate(range(15, 22)):
        x = BX1 - CORNER - P // 2 - i * P
        wire(cn, x, BY0, x, BY0 - WIRE, x, BY0 - WIRE)
        num_v(cn, x, BY0 - 50)
        nm_v(cn, x, BY0)
    # 左 22..28（上→下）
    for i, cn in enumerate(range(22, 29)):
        y = BY0 + CORNER + P // 2 + i * P
        wire(cn, BX0, y, BX0 - WIRE, y, BX0 - WIRE, y)
        num_h(cn, BX0 - WIRE, BX0, y)
        nm_h(cn, BX0 + CH, y, "start")
    # 芯片名（框内居中，字号 79 = 2.0mm）
    CHIP_FS = 79
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans">%s</text>\n'
             % (BX0 + BW // 2, BY0 + BH // 2 + round(CHIP_FS * 0.35), CHIP_FS, PART_ID))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# =============================================================================
# PCB —— QFN28（本体 4×4、节距 0.4、底板 EPAD），1 单位 = 1mm
#
# 尺寸出处 = 手册（CH347DS1.PDF）第 12 页 7.1 QFN28 三视图：
#   本体 4.0±0.1 × 4.0±0.1；节距 e=0.4（标称）；脚宽 b=0.2±0.05；**脚长 0.35±0.1**；
#   底焊盘（EPAD）2.7±0.2；总高 0.75±0.05、本体厚 0.55±0.05、脚凸出 0.025±0.025。
# 焊盘（land）由封装尺寸推（手册没给推荐 land）：切向 0.2 × 径向 0.6 ——
#   内缘 体边内 0.15（=1.85）、外缘 体边外 0.45（=2.45）→ 给脚（0.35 + 0.025 凸出）留焊料。
#   0.4 节距下相邻焊盘留 0.2 间隙（不打架）。EPAD land 取与本体焊盘同大：2.7×2.7。
# 排列与 icon 一致（手册第 3 页 TOP VIEW）：底 1-7 左→右、右 8-14 下→上、
#   顶 15-21 右→左、左 22-28 上→下；**connector 号 = 芯片脚号**（0 = EPAD GND）。
# =============================================================================
def gen_pcb_svg():
    """QFN28 4×4 P0.4 + 底板 EPAD（copper1 + silkscreen，viewBox 单位 = mm）。"""
    C = 3.0                                  # 中心（板面外框 6.0 × 6.0，四周留 0.55）
    W = H = 6.0
    PITCH, PAD_W, PAD_L = 0.4, 0.2, 0.6      # 节距 / 切向宽 / 径向长
    R_IN, R_OUT = 2.0 - 0.15, 2.0 - 0.15 + PAD_L    # 内缘 1.85 / 外缘 2.45
    EPAD = 2.7                               # 底板焊盘（手册 2.7±0.2）
    pads, silk = [], []

    def pad(n, x, y, w, h):
        pads.append('<rect id="connector%dpad" connectorname="%s" x="%.3f" y="%.3f" '
                    'width="%.3f" height="%.3f" fill="#F7BD13" stroke="none"/>'
                    % (n, _esc(PIN_NAMES[n]), x, y, w, h))

    def slot(i):                             # 7 脚均匀居中：-1.2 .. +1.2
        return -1.2 + i * PITCH

    # 底 1-7（左→右）
    for i, n in enumerate(range(1, 8)):
        pad(n, C + slot(i) - PAD_W / 2, C + R_IN, PAD_W, PAD_L)
    # 右 8-14（下→上）
    for i, n in enumerate(range(8, 15)):
        pad(n, C + R_IN, C - slot(i) - PAD_W / 2, PAD_L, PAD_W)
    # 顶 15-21（右→左）
    for i, n in enumerate(range(15, 22)):
        pad(n, C - slot(i) - PAD_W / 2, C - R_OUT, PAD_W, PAD_L)
    # 左 22-28（上→下）
    for i, n in enumerate(range(22, 29)):
        pad(n, C - R_OUT, C + slot(i) - PAD_W / 2, PAD_L, PAD_W)
    # 底板 EPAD（= 0 号脚，GND）
    pad(0, C - EPAD / 2, C - EPAD / 2, EPAD, EPAD)
    # 丝印**只留四个角**（用户 2026-09-15 定）：本体轮廓整圈会从焊盘上压过去 ——
    #   焊盘径向从体边内 0.15 一直伸到体边外 0.45，所以 4 条边中间那段必须让开；
    #   四角（|沿边坐标| >= 1.35，焊盘最外沿 1.3）画 L 形角标，长 0.65。
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, y0 = C + sx * 2.0, C + sy * 2.0
            silk.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#f0f0f0" '
                        'stroke-width="0.12"/>' % (x0, y0, x0 - sx * 0.65, y0))
            silk.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#f0f0f0" '
                        'stroke-width="0.12"/>' % (x0, y0, x0, y0 - sy * 0.65))
    # pin1 标记：**实心圆点**，放 1 脚左边（用户 2026-09-15）；位置卡在两处空隙里：
    #   离 1 脚焊盘左缘 0.05（焊盘 x 从 1.70 起）、离左上角那条横丝印 0.04（丝印在 y=5.00）
    #   → 所以比 1 脚中线略低 0.15，才能贴到焊盘旁边而不压在丝印上
    silk.append('<circle cx="%.3f" cy="%.3f" r="0.20" fill="#f0f0f0" stroke="none" '
                'class="other"/>'
                % (C - 1.2 - PAD_W / 2 - 0.25, C + R_IN + PAD_L / 2 + 0.15))
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" '
            'viewBox="0 0 %.1f %.1f">\n'
            '  <g id="copper1">\n    ' % (W, H, W, H)
            + '\n    '.join(pads)
            + '\n  </g>\n  <g id="silkscreen">\n    '
            + '\n    '.join(silk) + '\n  </g>\n</svg>\n')


def gen_fzp():
    """.fzp：芯片 29 脚（0..28）+ 面包板专用连接器（29 起，只上面包板视图）。

    视图分配：
      · 芯片脚 0..28 → 原理图（pin+terminal）+ PCB（pad）都会有；面包板只给"板上真引到排针"的那些
        （XI/XO/RST#/UD-/UD+ 直接进 USB 座/晶振，板上没引出来）。
      · 面包板专用号（29 起）→ **只有面包板视图**（板上额外的 3V3/VIO/地/KEY 轨、跳线中间脚…）。
      · 同网用 <buses> 互联（GND 含 EPAD、3V3 含 VCC、SCL/SDA/SCS1 与芯片复用脚同网）。
    """
    pm = pad_map()
    name_of = {cn: net for _, net, _, _, cn in pm}
    board = sorted(name_of)
    chip_on_board = {cn for cn in board if cn < 29}
    conns = []
    for cn in range(29):
        nm = _esc(PIN_NAMES[cn])
        conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                     '   <description>%s</description>\n   <views>\n' % (cn, nm, nm))
        if cn in chip_on_board:
            conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n' % cn)
        conns.append('    <schematicView><p layer="schematic" svgId="connector%dpin" '
                     'terminalId="connector%dterminal"/></schematicView>\n' % (cn, cn))
        conns.append('    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n' % cn)
        conns.append('   </views>\n  </connector>\n')
    for cn in [c for c in board if c >= 29]:
        nm = _esc(name_of[cn])
        conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                     '   <description>%s (board rail)</description>\n   <views>\n'
                     '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n'
                     '   </views>\n  </connector>\n' % (cn, nm, nm, cn))
    buses = [" <buses>\n"]
    for bid, pins, nets in BUSES:
        members = ['connector%d' % p for p in pins] + \
                  ['connector%d' % c for c in board if c >= 29 and name_of[c] in nets]
        buses.append('  <bus id="%s">\n' % bid)
        for m in members:
            buses.append('   <nodeMember connectorId="%s"/>\n' % m)
        buses.append('  </bus>\n')
    buses.append(' </buses>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<module fritzingVersion="1.0.3" moduleId="%s">\n'
            ' <version>4</version>\n <date>2026-09-15</date>\n'
            ' <label>%s</label>\n <author>Shi Jinghai</author>\n'
            ' <title>%s</title>\n'
            ' <tags><tag>CH347F</tag><tag>USB</tag><tag>SPI</tag><tag>I2C</tag>'
            '<tag>JTAG</tag><tag>UART</tag><tag>WCH</tag></tags>\n'
            ' <properties>\n'
            '  <property name="package">%s</property>\n'
            '  <property name="family">%s</property>\n'
            '  <property name="chip">CH347F</property>\n'
            '  <property name="pins">29</property>\n'
            ' </properties>\n'
            ' <views>\n'
            '  <iconView><layers image="icon/%s_icon.svg"><layer layerId="icon"/></layers></iconView>\n'
            '  <breadboardView fliphorizontal="true" flipvertical="true">'
            '<layers image="breadboard/%s_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>\n'
            '  <schematicView fliphorizontal="true" flipvertical="true">'
            '<layers image="schematic/%s_schematic.svg"><layer layerId="schematic"/></layers></schematicView>\n'
            '  <pcbView><layers image="pcb/%s_pcb.svg"><layer layerId="copper1"/>'
            '<layer layerId="silkscreen"/></layers></pcbView>\n'
            ' </views>\n'
            ' <connectors>\n%s</connectors>\n%s'
            '</module>\n'
            % (PART_ID, LABEL, TITLE, PACKAGE, FAMILY, PART_ID, PART_ID, PART_ID, PART_ID,
               "".join(conns), "".join(buses)))


def main():
    files = {ICON_SVG: icon_svg(), BB_SVG: gen_breadboard_svg(),
             SCHEM_SVG: gen_schematic_svg(), PCB_SVG: gen_pcb_svg(),
             FZP: gen_fzp()}
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(os.path.join(OUT_DIR, name), arcname=name)   # 包里**平铺**，不放子目录
    print("wrote", path)


if __name__ == "__main__":
    main()
