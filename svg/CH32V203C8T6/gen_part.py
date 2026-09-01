#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_part.py — nanoCH32V203 开发板（主控 CH32V203C8T6）Fritzing 部件生成器。

视图模型（参照 svg/ESP32-S3-WROOM-1）：
  - 面包板 = nanoCH32V203 开发板（MUSE LAB，52×30mm）：
      顶部/底部各 20 针排针（40 个可连线连接器）、左侧双 USB-C + RST/BOOT 按键、
      中央 CH32V203C8T6 (LQFP48)、右侧 8MHz + 32.768K 晶振、FPC-12P 排线座、
      若干 LED/阻容。USB/FPC/按键/晶振为板级视觉外观。
  - 原理图 = CH32V203C8T6 芯片符号（48 脚，数据手册表 3-1-1）。
  - icon   = LQFP48 封装（图 5-6）。

连接器模型：connector0..47 = 芯片 48 脚；面包板上排针按信号映射到芯片脚
（GPIO→排针、3V3→VDD_IO_1、G→VSS*），未上排针的芯片脚（VBAT/晶振/USB/复位等）
落在对应功能附近的小测试点；板级 5V 轨与多余 GND 用面包板专用连接器
（connector48..50）。GND/3V3/5V 用 <buses> 在部件内部互通。

坐标约定：面包板内部 100 单位 = 2.54mm，整板套 scale(7.2/100)=0.072，
使排针落在 Fritzing 面包板孔距上。
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH32V203C8T6"
FZPZ = "CH32V203C8T6.fzpz"

TITLE = "nanoCH32V203 (CH32V203C8T6 dev board)"
LABEL = "U"
PACKAGE = "LQFP48"
FAMILY = "WCH RISC-V MCU"

# --------------------------------------------------------------------------
# 芯片 48 脚（LQFP48，数据手册表 3-1-1，WCH 编号 1..48）
PINS = [
    "VBAT", "PC13/TAMPER_RTC", "PC14/OSC32IN", "PC15/OSC32OUT",
    "OSC_IN/PD0", "OSC_OUT/PD1", "NRST", "VSSA", "VDDA",
    "PA0/WKUP/ADC0", "PA1/ADC1", "PA2/ADC2",
    "PA3/ADC3", "PA4/ADC4", "PA5/ADC5", "PA6/ADC6", "PA7/ADC7",
    "PB0/ADC8", "PB1/ADC9", "PB2/BOOT1",
    "PB10", "PB11", "VSS_1", "VDD_VIO_1",
    "PB12", "PB13", "PB14", "PB15", "PA8", "PA9",
    "PA10", "PA11/USB1DM", "PA12/USB1DP", "PA13/SWDIO",
    "VSS_2", "VDD_2",
    "PA14/SWCLK", "PA15", "PB3", "PB4", "PB5",
    "PB6/USB2DP", "PB7/USB2DM", "BOOT0", "PB8", "PB9",
    "VSS_3", "VDD_VIO_3",
]

# 排针丝印（顶部/底部，左→右）
HEADER_TOP = ["G", "5V", "B11", "B10", "B1", "B0", "G", "A7", "A6", "A5",
              "A4", "A3", "A2", "A1", "A0", "C13", "B8", "B9", "3V3", "G"]
HEADER_BOT = ["G", "5V", "B12", "B13", "B14", "B15", "A8", "A9", "A10", "A11",
              "A12", "A13", "A14", "A15", "B3", "B4", "B5", "B6", "B7", "G"]

# 排针标签 -> 芯片脚连接器下标（未列出的 G/5V 在下面按位序指派）
_HDR2CN = {
    "A0": 9, "A1": 10, "A2": 11, "A3": 12, "A4": 13, "A5": 14, "A6": 15, "A7": 16,
    "A8": 28, "A9": 29, "A10": 30, "A11": 31, "A12": 32, "A13": 33, "A14": 36, "A15": 37,
    "B0": 17, "B1": 18, "B3": 38, "B4": 39, "B5": 40, "B6": 41, "B7": 42,
    "B8": 44, "B9": 45, "B10": 20, "B11": 21, "B12": 24, "B13": 25, "B14": 26, "B15": 27,
    "C13": 1, "3V3": 23,
}
# 面包板专用连接器：connector48/49 = 5V 轨（顶部/底部）、connector50 = 多余 GND
# 5 个 G 排针依次接 VSS_1/VSSA/VSS_2/VSS_3，第 5 个用 connector50
G_SEQ = [22, 7, 34, 46]

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- Created for TXW8301 Simulator -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ==========================================================================
# icon —— LQFP48 封装（图 5-6）
# ==========================================================================
def gen_icon_svg():
    """LQFP48 封装 icon（按 CH32V203 数据手册图 5-6）：
    总体 9×9mm、塑体 7×7mm、四边各 12 金焊盘（节距 0.5mm，每脚 1×0.2mm）、
    左下角引脚1 圆点、顶面丝印两行左对齐（CH32V203 / C8T6）。
    比例 2 单位/mm；画布裁到内容 18×18 单位 = 9×9mm（无留边）。"""
    c = 16.0
    body = 14.0
    pitch = 1.0
    pad_w = 0.4
    pad_l = 2.0
    half = body / 2
    parts = []
    parts.append(f'<rect x="{c-half:.3f}" y="{c-half:.3f}" width="{body:.3f}" '
                 f'height="{body:.3f}" rx="0.4" ry="0.4" fill="#303030" stroke="none"/>')
    centers = [c - 5.5 + i * pitch for i in range(12)]
    for a in centers:
        parts.append(f'<rect x="{a-pad_w/2:.3f}" y="{c-half-pad_l:.3f}" '
                     f'width="{pad_w:.3f}" height="{pad_l:.3f}" fill="#f7bf13" stroke="none"/>')
        parts.append(f'<rect x="{a-pad_w/2:.3f}" y="{c+half:.3f}" '
                     f'width="{pad_w:.3f}" height="{pad_l:.3f}" fill="#f7bf13" stroke="none"/>')
        parts.append(f'<rect x="{c-half-pad_l:.3f}" y="{a-pad_w/2:.3f}" '
                     f'width="{pad_l:.3f}" height="{pad_w:.3f}" fill="#f7bf13" stroke="none"/>')
        parts.append(f'<rect x="{c+half:.3f}" y="{a-pad_w/2:.3f}" '
                     f'width="{pad_l:.3f}" height="{pad_w:.3f}" fill="#f7bf13" stroke="none"/>')
    parts.append(f'<circle cx="{c-half+2.2:.3f}" cy="{c+half-2.2:.3f}" r="0.8" '
                 f'fill="#c0c0c0" stroke="none"/>')
    parts.append(f'<text x="10.8" y="13.0" font-size="2.0" font-family="DroidSans" '
                 f'fill="#c0c0c0" text-anchor="start" stroke="none" stroke-width="0">CH32V203</text>')
    parts.append(f'<text x="10.8" y="15.0" font-size="2.0" font-family="DroidSans" '
                 f'fill="#c0c0c0" text-anchor="start" stroke="none" stroke-width="0">C8T6</text>')
    inner = "\n".join(parts)
    return (SVG_HDR +
            '<svg xmlns="http://www.w3.org/2000/svg" width="9mm" height="9mm" '
            'viewBox="7 7 18 18">\n'
            f' <g id="icon">\n{inner}\n </g>\n</svg>\n')


# ==========================================================================
# 原理图 —— 复刻数据手册第 51 页 CH32V203CxT6 引脚图
# ==========================================================================
# 逆时针编号 1..48：左 1-12（上→下）、下 13-24（左→右）、右 25-36（下→上）、上 37-48（右→左）
# 蓝色（数据手册第 51 页仅 1/2/3/4 脚标蓝，cn 下标 0-based）= 0,1,2,3（引脚 1=VBAT,2=PC13,3=PC14,4=PC15），其它全黑
SCHEM_BLUE = {0, 1, 2, 3}
BLUE = "#0000c8"
RED = "#c00000"


def gen_schematic_svg():
    """矩形封装符号（数据手册第 51 页图）。原理图规则：
    1. 左右数字在引线上方（不与线相交）；上下数字在引脚左侧（从下至上 rotate 270）。
    2. 引脚名在框内、方向同数字、整图同字号 FN=14。
    3. （长）方框原理图：引脚名中线与引脚对齐（左右 dominant-baseline=central、上下 text-anchor=middle）。
    4. 引脚名与边框保持一个字符(35)间距，居左/右/下/上。
    5. 名/数字/引线颜色一致（普通黑、数据手册第 51 页标蓝脚 1/2/3/4 为蓝 #0000c8）；数字与名互不重叠。
    6. 四角无引脚宽度 CORNER = 最长名宽 + 1 字符宽；四边引脚从 CORNER 后开始排，四角空白使上下名与左右名不交叉，框对称。
    物理尺寸 width/height(in) 决定，1000 单位 = 1in。"""
    P = 100                       # 引脚间距（0.1in = 2.54mm，标准间距，紧凑排布）
    WIRE = 130                    # 引脚线长
    CH = 35                       # 一个字符间距（= 字号）
    FN = 35                       # 整图统一字号（数字与引脚名；0.889mm ≈ Fritzing 官方引脚数字 0.881944mm）
    BASELINE_OFF = round(FN * 0.35)   # 文字基线偏移（手动垂直居中，避免依赖 dominant-baseline）
    max_len = max(len(n) for n in PINS)        # 最长引脚名字符数（15：PC13/TAMPER_RTC）
    CORNER = (max_len + 1) * int(FN * 0.58)    # 四角无引脚宽度 = 最长名宽 + 1 字符宽（四角空白使上下名与左右名不交叉）
    BX0, BY0 = 340, 200
    BX1, BY1 = BX0 + 12 * P + 2 * CORNER, BY0 + 12 * P + 2 * CORNER   # 框 = 12P + 2×CORNER（对称）
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="2.12in" height="2.12in" '
             'viewBox="200 60 2120 2120">\n')
    L.append(' <g id="schematic">\n')
    # 封装体（白底红边）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" stroke="%s" stroke-width="5"/>\n'
             % (BX0, BY0, BX1 - BX0, BY1 - BY0, RED))
    # 左 1-12（上→下）：数字在引线上方（不与线相交），名在框内居中于引脚、距左边框一个字符
    for i in range(12):
        y = BY0 + CORNER + P // 2 + i * P
        cn = i
        col = BLUE if cn in SCHEM_BLUE else "#000000"
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{col}" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 下 13-24（左→右）：数字在引脚左侧（从下至上），名在框内靠下（从下至上）
    for i in range(12):
        x = BX0 + CORNER + P // 2 + i * P
        cn = 12 + i
        col = BLUE if cn in SCHEM_BLUE else "#000000"
        lab = PINS[cn]
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{x}" y1="{BY1}" x2="{x}" y2="{BY1 + WIRE}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{x - 11}" y="{BY1 + WIRE}" width="22" height="22" fill="none"/>\n')
        # 数字在引脚左侧、从下至上（rotate 270），与名同字号同色
        # 数字右侧距引脚半个字符高（FN/2）→ 锚点 x-FN（右缘 x-FN/2，与名左缘对齐）
        L.append(f'  <text x="{x - FN}" y="{BY1 + 55}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x - FN} {BY1 + 55})">{13 + i}</text>\n')
        ln = int(len(lab) * FN * 0.58)   # 文字高（text-anchor=middle+rotate270 → 文字以锚点为中心，底边=锚点+ln/2）
        L.append(f'  <text x="{x}" y="{BY1 - CH - ln // 2}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x} {BY1 - CH - ln // 2})">{esc(lab)}</text>\n')
    # 右 25-36（下→上）：数字在引线上方（不与线相交，从左至右），名在框内靠右
    for i in range(12):
        y = BY1 - CORNER - P // 2 - i * P
        cn = 24 + i
        col = BLUE if cn in SCHEM_BLUE else "#000000"
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans">{25 + i}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{col}" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 上 37-48（右→左）：数字在引脚左侧（从下至上），名在框内靠上（从下至上）
    for i in range(12):
        x = BX1 - CORNER - P // 2 - i * P
        cn = 36 + i
        col = BLUE if cn in SCHEM_BLUE else "#000000"
        lab = PINS[cn]
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{x}" y1="{BY0}" x2="{x}" y2="{BY0 - WIRE}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{x - 11}" y="{BY0 - WIRE}" width="22" height="22" fill="none"/>\n')
        # 数字在引脚左侧、从下至上（rotate 270），与名同字号同色
        # 数字右侧距引脚半个字符高（FN/2）→ 锚点 x-FN（右缘 x-FN/2，与名左缘对齐）
        L.append(f'  <text x="{x - FN}" y="{BY0 - 50}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x - FN} {BY0 - 50})">{37 + i}</text>\n')
        ln = int(len(lab) * FN * 0.58)   # 文字高（text-anchor=middle+rotate270 → 文字以锚点为中心，顶边=锚点-ln/2）
        L.append(f'  <text x="{x}" y="{BY0 + CH + ln // 2}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x} {BY0 + CH + ln // 2})">{esc(lab)}</text>\n')
    # 芯片名（框内居中，字号 79 = 2.0mm，醒目）
    CHIP_X, CHIP_Y, CHIP_FS = 1260, 1100, 79
    chip_x0 = CHIP_X - int(len(PART_ID) * CHIP_FS * 0.58) // 2   # 芯片名文字左缘
    L.append(f'  <text x="{CHIP_X}" y="{CHIP_Y}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(PART_ID)}</text>\n')
    # 中心电源框：VDD&VIO（黑）、VDD&VBAT（蓝）—— 色块左缘与芯片名左缘对齐、紧贴其下方
    PWR_FX = chip_x0              # 色块方框左缘 = 芯片名文字左缘（左对齐）
    PWR_X = chip_x0 + 45 + 12     # 文字在色块右侧（45 宽 + 12 间距）
    L.append(f'  <rect x="{PWR_FX}" y="1130" width="45" height="45" fill="#000000"/>\n')
    L.append(f'  <text x="{PWR_X}" y="1165" font-size="35" fill="#000000" text-anchor="start" '
             f'font-family="DroidSans">{esc("VDD&VIO power")}</text>\n')
    L.append(f'  <rect x="{PWR_FX}" y="1190" width="45" height="45" fill="{BLUE}"/>\n')
    L.append(f'  <text x="{PWR_X}" y="1225" font-size="35" fill="{BLUE}" text-anchor="start" '
             f'font-family="DroidSans">{esc("VDD&VBAT power")}</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ==========================================================================
# PCB —— LQFP48 焊盘（copper1 + 丝印）
# ==========================================================================
def gen_pcb_svg():
    """LQFP48 (7×7mm, 0.5mm pitch) PCB：copper1 焊盘 1.2×0.3 + 丝印 7×7 体（1 单位 = 1mm）。"""
    pads, silk = _pcb_pads_48()
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    W = H = 10.6
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" '
            f'viewBox="0 0 {W} {H}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


def _pcb_pads_48():
    """LQFP48 (7×7mm, pitch 0.5mm) 焊盘 + 丝印（按 CH32V203 数据手册第 51 页：Pin1 左上）。
    焊盘 切向 0.30 × 径向 1.20mm；内缘半径 3.65（对边 7.3）、外缘半径 4.85（对边 9.7）。
    Pin1(VBAT) 左上角、逆时针：左 1-12(上→下)、下 13-24(左→右)、右 25-36(下→上)、上 37-48(右→左)。
    中心 (5.0,5.0)，1 单位 = 1mm。connectorname = .fzp 连接器下标 0..47。"""
    c = 5.0
    pitch = 0.5
    pad_w, pad_l = 0.30, 1.20
    r_in, r_out = 3.65, 4.85
    pads, silk = [], []
    centers = [-2.75 + i * pitch for i in range(12)]   # -2.75..+2.75（上→下/左→右）
    # 左列 0-11（上→下，pin1 VBAT 最上）：焊盘从 c-r_out 到 c-r_in（径向 1.2，向左伸）
    for i in range(12):
        y = c + centers[i]
        pads.append(f'<rect id="connector{i}pad" x="{c - r_out:.3f}" y="{y - pad_w / 2:.3f}" '
                    f'width="{pad_l:.3f}" height="{pad_w:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{i}"/>')
    # 下列 12-23（左→右）：焊盘从 c+r_in 到 c+r_out（向下伸）
    for j in range(12):
        x = c + centers[j]
        pads.append(f'<rect id="connector{12 + j}pad" x="{x - pad_w / 2:.3f}" y="{c + r_in:.3f}" '
                    f'width="{pad_w:.3f}" height="{pad_l:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{12 + j}"/>')
    # 右列 24-35（下→上，pin25 最下）：焊盘从 c+r_in 到 c+r_out（向右伸）
    for j in range(12):
        y = c + centers[11 - j]
        pads.append(f'<rect id="connector{24 + j}pad" x="{c + r_in:.3f}" y="{y - pad_w / 2:.3f}" '
                    f'width="{pad_l:.3f}" height="{pad_w:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{24 + j}"/>')
    # 上列 36-47（右→左，pin37 最右）：焊盘从 c-r_out 到 c-r_in（向上伸）
    for j in range(12):
        x = c + centers[11 - j]
        pads.append(f'<rect id="connector{36 + j}pad" x="{x - pad_w / 2:.3f}" y="{c - r_out:.3f}" '
                    f'width="{pad_w:.3f}" height="{pad_l:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{36 + j}"/>')
    # 丝印：7×7 体轮廓 + pin1 标记（体左上角内，y 与 pin1 焊盘中心对齐，不与焊盘重叠）
    silk.append(f'<rect x="{c - 3.5}" y="{c - 3.5}" width="7.0" height="7.0" '
                f'fill="none" stroke="#f0f0f0" stroke-width="0.12"/>')
    silk.append(f'<circle cx="{c - 3.5 + 0.6:.3f}" cy="{c + centers[0]:.3f}" r="0.3" '
                f'fill="none" stroke="#f0f0f0" stroke-width="0.12" class="other"/>')
    return pads, silk


# ==========================================================================
# 面包板 —— nanoCH32V203 开发板
# ==========================================================================
BB_SCALE = 7.2 / 100.0          # 0.072
BW = 2047                       # 52 mm
BH = 1181                       # 30 mm
PIN_PITCH = 100
HDR_TOP_Y = 74
HDR_BOT_Y = BH - 74
HDR_X = [74 + i * PIN_PITCH for i in range(20)]

# (排针标签 -> 芯片脚连接器下标见 _HDR2CN；5V/G 在 breadboard 循环内处理)


# TypeC16Pin 真实 USB-C 座图形（复用 svg/TypeC16Pin 的 icon，剥掉重复 id）
_TYPEC_PATH = os.path.join(OUT_DIR, "..", "TypeC16Pin",
                           "svg.icon.TypeC16Pin_d89a481c23a1ca4ff437422a227ed0bb_1_icon.svg")
_TYPEC_ART = None
try:
    with open(_TYPEC_PATH, encoding="utf-8") as _tf:
        _typec_src = _tf.read()
    _tm = re.search(r'(<g\s+id="g40446"[^>]*>.*</g>)\s*</svg>', _typec_src, re.S)
    if _tm:
        _TYPEC_ART = re.sub(r'\s+id="[^"]*"', '', _tm.group(1))
except Exception:
    _TYPEC_ART = None


def _usb_art(cy, width_mm=8.94):
    """TypeC16Pin 真实 USB-C 座图形（视觉，不连线），插口朝左（板左缘），垂直居中于 cy。
    原图 1 单位 = 0.3528mm，bbox 25.344 x 21.572；金焊盘在底部 → 旋转 -90° 使插口到左侧。
    板内 1 单位 = 0.0254mm → 39.37 单位/mm。"""
    if _TYPEC_ART is None:
        w, h = 352, 300
        return (f'  <rect x="0" y="{cy-h//2}" width="{w}" height="{h}" rx="40" fill="#dcdcdc" '
                f'stroke="#9a9a9a" stroke-width="6"/>\n')
    s = width_mm * 39.37 / 25.344
    rcx, rcy = 12.672 * s, 10.786 * s
    tx = -1.886 * s                # 插口(原底部)落到 x=0（板左缘）
    ty = cy - rcy
    return ('  <g transform="translate(%.2f %.2f) rotate(-90 %.2f %.2f) scale(%.5f)">\n'
            '%s\n  </g>\n' % (tx, ty, rcx, rcy, s, _TYPEC_ART))


def _btn_art(cx, cy, scale=0.60):
    """ESP32-S3-DevKitC-1 同款 NTC013 轻触按键（视觉）：灰壳 + 4 脚 + 2 J 焊端 +
    4 暗条 + 深色圆钮 + 白高光。壳左缘距中心 -75.5*scale。"""
    return (
        f'  <g transform="translate({cx} {cy}) scale({scale})">\n'
        '  <rect x="-75.5" y="-58" width="151" height="116" fill="#cccccc"/>\n'
        '  <rect x="-78.5" y="-31" width="8" height="13" fill="#333333"/>\n'
        '  <rect x="66.5" y="-31" width="8" height="13" fill="#333333"/>\n'
        '  <rect x="-78.5" y="15" width="8" height="13" fill="#333333"/>\n'
        '  <rect x="66.5" y="15" width="8" height="13" fill="#333333"/>\n'
        '  <rect x="-102.5" y="-28" width="26" height="54" fill="#e6e6e6"/>\n'
        '  <rect x="74.5" y="-28" width="26" height="54" fill="#e6e6e6"/>\n'
        '  <rect x="-76.5" y="-58" width="21" height="8" fill="#333333"/>\n'
        '  <rect x="53.5" y="-58" width="21" height="8" fill="#333333"/>\n'
        '  <rect x="-76.5" y="0" width="21" height="8" fill="#333333"/>\n'
        '  <rect x="53.5" y="0" width="21" height="8" fill="#333333"/>\n'
        '  <ellipse cx="-2.5" cy="-1" rx="37.766" ry="36.967" fill="#333333" stroke="#1a1a1a" stroke-width="3.03"/>\n'
        '  <path d="m -15.02,-36.72 c 5.29,-2.70 7.93,-2.70 13.19,-2.70 13.19,0 23.78,5.40 29.07,16.19" '
        'fill="none" stroke="#ffffff" stroke-width="3.03"/>\n'
        '  </g>\n'
    )


# 晶振部件 icon 复用（真实 3225/3215 图形，1mm = 39.37 板单位；半宽/半高由 icon 的
# width/height(mm) 解析，内容居中于 (cx,cy)）
_CRYSTAL_ART = {}
for _k in ("3225", "3215"):
    _p = os.path.join(OUT_DIR, "..", "Crystal-%s" % _k, "svg.icon.Crystal-%s_icon.svg" % _k)
    try:
        with open(_p, encoding="utf-8") as _f:
            _src = _f.read()
        _m = re.search(r'(<g\s+id="icon"[^>]*>.*</g>)\s*</svg>', _src, re.S)
        _wh = re.search(r'width="([\d.]+)mm"[^>]*height="([\d.]+)mm"', _src)
        if _m and _wh:
            _CRYSTAL_ART[_k] = (re.sub(r'\s+id="[^"]*"', '', _m.group(1)),
                                float(_wh.group(1)) / 2.0,
                                float(_wh.group(2)) / 2.0)
    except Exception:
        pass


def _crystal_art(cx, cy, kind, rot=0, freq=""):
    """在面包板上以真实尺寸嵌入晶振部件 icon。
    rot=90 时把旋转**烘烤进绝对板坐标**（icon 内 (x,y,w,h) 顺时针转 90° →
    (y, -x-w, h, w)，再 ×s 并平移到 (cx,cy)），不依赖 SVG rotate 变换，
    避免 Fritzing 中本体/焊盘因变换解析问题错位。
    freq 非空时把频率**丝印在晶振本体上**（竖排随 rot=90，深色文字居中），字号自动适配本体。"""
    if kind not in _CRYSTAL_ART:
        return ""
    art, hw, hh = _CRYSTAL_ART[kind]
    s = 39.37
    if rot != 90:
        ox = cx - hw * s
        oy = cy - hh * s
        r = ('  <g transform="translate(%.1f %.1f) scale(%.5f)">\n%s\n  </g>\n'
             % (ox, oy, s, art))
        if freq:
            fs = min(0.98 * 2.0 * hw * s / len(freq), 0.98 * 2.0 * hh * s)
            r += ('  <text x="%.1f" y="%.1f" font-size="%.1f" fill="#333333" '
                  'text-anchor="middle" dominant-baseline="central" '
                  'font-family="DroidSans">%s</text>\n' % (cx, cy, fs, freq))
        return r
    out = []
    for m in re.finditer(r'<rect\s+([^>]*?)\s*/>', art):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        rx, ry = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        rw, rh = float(a["width"]), float(a["height"])
        x = cx + ry * s
        y = cy + (-rx - rw) * s
        w, h = rh * s, rw * s
        attrs = '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"' % (x, y, w, h)
        if "rx" in a:
            attrs += ' rx="%.1f" ry="%.1f"' % (float(a["rx"]) * s, float(a["ry"]) * s)
        attrs += ' fill="%s" stroke="%s"' % (a.get("fill", "#f7bf13"), a.get("stroke", "none"))
        if float(a.get("stroke-width", 0)) > 0:
            attrs += ' stroke-width="%.2f"' % (float(a["stroke-width"]) * s)
        out.append(attrs + '/>\n')
    for m in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', art, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        fs = float(a.get("font-size", 0.9)) * s
        # 标签居中于晶振本体中心 (cx,cy)，竖排（从上向下读）
        out.append('  <text x="%.1f" y="%.1f" font-size="%.1f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans" '
                   'transform="rotate(90 %.1f %.1f)">%s</text>\n'
                   % (cx, cy, fs, a.get("fill", "#333333"), cx, cy, m.group(2)))
    if freq:
        # 频率丝印在晶振本体上（竖排、随 rot=90，深色文字居中），字号自动适配本体
        body_h = 2.0 * hw * s      # 旋转后本体高（文字延伸方向）
        body_w = 2.0 * hh * s      # 旋转后本体宽
        fs = min(0.98 * body_h / len(freq), 0.98 * body_w)
        out.append('  <text x="%.1f" y="%.1f" font-size="%.1f" fill="#333333" '
                   'text-anchor="middle" dominant-baseline="central" '
                   'font-family="DroidSans" transform="rotate(90 %.1f %.1f)">%s</text>\n'
                   % (cx, cy, fs, cx, cy, freq))
    return "".join(out)


# FPC-05F-12P-H15 部件 icon 复用（真实 FPC 连接器图形；内容 bbox 10.1×4.6mm）
_FPC05_ART = None
_fpc05_path = os.path.join(OUT_DIR, "..", "FPC-05F-12P-H15",
                           "svg.icon.FPC-05F-12P-H15_icon.svg")
try:
    with open(_fpc05_path, encoding="utf-8") as _f:
        _fpc05_src = _f.read()
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*</g>)\s*</svg>', _fpc05_src, re.S)
    _vb = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', _fpc05_src)
    if _m and _vb:
        _FPC05_ART = (re.sub(r'\s+id="[^"]*"', '', _m.group(1)),
                      float(_vb.group(3)) / 2.0,          # 半宽 3.4
                      -float(_vb.group(2)),               # 上半高 2.2
                      float(_vb.group(2)) + float(_vb.group(4)))  # 下半高 2.9
except Exception:
    _FPC05_ART = None


def _fpc05_art(cy, x_right):
    """在面包板上以真实尺寸嵌入 FPC-05F-12P-H15 icon：竖放、触点朝右、右缘对齐 x_right。
    旋转 90°CW 烘烤进绝对板坐标（icon 内 (x,y,w,h) → (y,-x-w,h,w)，再 ×s），
    不依赖 SVG rotate 变换，避免 Fritzing 中错位。"""
    if _FPC05_ART is None:
        return ""
    art, hw, hh_hi, hh_lo = _FPC05_ART
    s = 39.37
    # 内容 bbox（mm）: x -hw..hw, y -hh_hi..hh_lo
    # 旋转 90°CW 后: x -hh_hi..hh_lo（+x=触点侧）, y -hw..hw
    tx = x_right - hh_lo * s    # 触点(右)缘对齐 x_right
    ty = cy
    out = []
    for m in re.finditer(r'<rect\s+([^>]*?)\s*/>', art):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        rx, ry = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        rw, rh = float(a["width"]), float(a["height"])
        x = tx + ry * s
        y = ty + (-rx - rw) * s
        w, h = rh * s, rw * s
        attrs = '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"' % (x, y, w, h)
        if "rx" in a:
            attrs += ' rx="%.1f" ry="%.1f"' % (float(a["rx"]) * s, float(a["ry"]) * s)
        attrs += ' fill="%s" stroke="%s"' % (a.get("fill", "#f7bf13"), a.get("stroke", "none"))
        if float(a.get("stroke-width", 0)) > 0:
            attrs += ' stroke-width="%.2f"' % (float(a["stroke-width"]) * s)
        out.append(attrs + '/>\n')
    for m in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', art, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        tx2, ty2 = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        x = tx + ty2 * s
        y = ty + (-tx2) * s
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.1f" y="%.1f" font-size="%.1f" fill="%s" text-anchor="middle" '
                   'font-family="DroidSans" transform="rotate(90 %.1f %.1f)">%s</text>\n'
                   % (x, y, fs, a.get("fill", "#666666"), x, y, m.group(2)))
    return "".join(out)


def _lqfp48_chip_art(cx, cy):
    """开发板中央的 CH32V203C8T6 LQFP48（视觉）：深色体 + 48 金焊盘 + 丝印。
    图标 1 单位 = 0.5mm；板内 1 单位 = 0.0254mm → S = 0.5/0.0254 ≈ 19.685。"""
    S = 19.685
    body = 14.0 * S
    pitch = 1.0 * S
    pad_w = 0.4 * S
    pad_l = 2.0 * S
    half = body / 2
    s_parts = []
    # 芯片本体（深色塑体）
    s_parts.append(f'  <rect x="{cx-half:.1f}" y="{cy-half:.1f}" width="{body:.1f}" height="{body:.1f}" '
                   f'rx="{0.4*S:.1f}" ry="{0.4*S:.1f}" fill="#303030" stroke="none"/>\n')
    # 左右焊盘用垂直中心(cy)，上下焊盘用水平中心(cx)——否则上下焊盘会错位
    vcenters = [cy - 5.5 * pitch + i * pitch for i in range(12)]
    hcenters = [cx - 5.5 * pitch + i * pitch for i in range(12)]
    for a in vcenters:
        s_parts.append(f'  <rect x="{cx-half-pad_l:.1f}" y="{a-pad_w/2:.1f}" '
                       f'width="{pad_l:.1f}" height="{pad_w:.1f}" fill="#f7bf13"/>\n')
        s_parts.append(f'  <rect x="{cx+half:.1f}" y="{a-pad_w/2:.1f}" '
                       f'width="{pad_l:.1f}" height="{pad_w:.1f}" fill="#f7bf13"/>\n')
    for a in hcenters:
        s_parts.append(f'  <rect x="{a-pad_w/2:.1f}" y="{cy-half-pad_l:.1f}" '
                       f'width="{pad_w:.1f}" height="{pad_l:.1f}" fill="#f7bf13"/>\n')
        s_parts.append(f'  <rect x="{a-pad_w/2:.1f}" y="{cy+half:.1f}" '
                       f'width="{pad_w:.1f}" height="{pad_l:.1f}" fill="#f7bf13"/>\n')
    # 引脚1 圆点（左下角，与 icon 一致：距角 2.2 单位、r=0.8 单位 @ 0.5mm）
    dot = 2.2 * S
    s_parts.append(f'  <circle cx="{cx-half+dot:.1f}" cy="{cy+half-dot:.1f}" r="{0.8*S:.1f}" '
                   f'fill="#c0c0c0"/>\n')
    s_parts.append(f'  <text x="{cx}" y="{cy+4:.1f}" font-size="{2.0*S:.1f}" fill="#c0c0c0" '
                   f'text-anchor="middle" font-family="DroidSans">CH32V203</text>\n')
    # 芯片整体逆时针旋转 45° + 再 90° = -135°（SVG rotate 正角为顺时针，负角逆时针）
    return ('  <g transform="rotate(-135 %.1f %.1f)">\n%s\n  </g>\n' % (cx, cy, "".join(s_parts)))


def gen_breadboard_svg():
    """面包板 = nanoCH32V203 开发板。内部 100 单位 = 2.54mm，套 scale(0.072)。"""
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" viewBox="0 0 %.1f %.1f">\n'
             % (BW / 100.0 * 2.54, BH / 100.0 * 2.54, BW * BB_SCALE, BH * BB_SCALE))
    L.append(' <g id="breadboard" transform="scale(%g)">\n' % BB_SCALE)
    # PCB 板
    L.append('  <rect x="0" y="0" width="%d" height="%d" fill="#262626" stroke="#000000" stroke-width="6"/>\n'
             % (BW, BH))
    # 板名（右下）：底部与 BOOT 底线(1003)对齐；左侧与 A13 标签右侧(~1205)对齐；
    # 字号 52（比 A13(34) 大两号再大 3 号）
    L.append('  <text x="1205" y="1003" font-size="52" fill="#7a7a7a" text-anchor="start" '
             'font-family="DroidSans">nanoCH32V203</text>\n')
    # USB-C ×2（板左缘，真实 TypeC16Pin 图形，只画不连）
    L.append(_usb_art(330))       # USB1
    L.append(_usb_art(850))       # USB2
    # USB 标签（竖排，从上向下写，字号与 5V 相同=34，紧挨 USB 右缘~300）
    L.append('  <text x="310" y="330" font-size="34" fill="#aaaaaa" text-anchor="middle" '
             'font-family="DroidSans" transform="rotate(90 310 330)">USB1D</text>\n')
    L.append('  <text x="310" y="850" font-size="34" fill="#aaaaaa" text-anchor="middle" '
             'font-family="DroidSans" transform="rotate(90 310 850)">USB2HD</text>\n')
    # RST / BOOT 按键（壳左缘对齐 B1/B14 = x 474 → 中心 x=519）
    # RST 顶边对齐 USB1 顶边(154) → 中心 y = 154+34.8 ≈ 189
    # BOOT 底边对齐 USB2 底边(1026) → 中心 y = 1026-34.8 ≈ 991
    L.append(_btn_art(519, 189))
    L.append(_btn_art(519, 991))
    # 文字横排在按键右侧（字号与排针标签 5V 一致 = 34；垂直居中对齐按键中心）
    # 基线 = 按键中心 + 0.35*34 ≈ 中心+12：RST 189+12=201，BOOT 991+12=1003
    L.append('  <text x="592" y="201" font-size="34" fill="#aaaaaa" text-anchor="start" '
             'font-family="DroidSans">RST</text>\n')
    L.append('  <text x="592" y="1003" font-size="34" fill="#aaaaaa" text-anchor="start" '
             'font-family="DroidSans">BOOT</text>\n')
    # 中央芯片 LQFP48
    L.append(_lqfp48_chip_art(1024, 590))
    # 晶振 ×2（右侧，真实 3225/3215 部件 icon 图形，竖放 = 顺时针 90°）
    # 频率丝印在晶振本体上（8MHz / 32.768K）
    L.append(_crystal_art(1520, 460, "3225", rot=90, freq="8MHz"))
    L.append(_crystal_art(1520, 730, "3215", rot=90, freq="32.768K"))
    # FPC-05F-12P-H15（右缘，竖放，触点朝右，右缘与板右缘对齐，垂直居中于 590）
    L.append(_fpc05_art(590, BW))
    # 排针连接器 + 丝印标签（顶排标签在下、底排标签在上 = 内侧朝板心）
    g_count = 0
    for row, ys, lst in ((0, HDR_TOP_Y, HEADER_TOP), (1, HDR_BOT_Y, HEADER_BOT)):
        for i in range(20):
            lab = lst[i]
            x = HDR_X[i]
            if lab in _HDR2CN:
                cn = _HDR2CN[lab]
            elif lab == "5V":
                cn = 48 + row          # 顶部 48 / 底部 49（5V 轨）
            else:                      # G
                cn = G_SEQ[g_count] if g_count < 4 else 50
                g_count += 1
            L.append('  <circle cx="%d" cy="%d" r="26" fill="#b8b8b8" stroke="#6a6a6a" stroke-width="5" '
                     'id="connector%dpin"/>\n' % (x, ys, cn))
            # 标签在内侧且不重叠引脚：顶排偏移≥半径(26)+文字高度(~27)+留白；
            # 底排偏移 44 更贴排针，且避开 USB2 下端(1026) 与引脚下缘(1081)
            ly = ys + 60 if row == 0 else ys - 44
            L.append('  <text x="%d" y="%d" font-size="34" fill="#ffffff" text-anchor="middle" '
                     'font-family="DroidSans">%s</text>\n' % (x, ly, lab))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ==========================================================================
# .fzp
# ==========================================================================
def gen_fzp():
    # 不上面包板的芯片脚（无 breadboardView，只出现在原理图/PCB）：
    # VBAT/NRST/VDDA/PB2/VDD_2/VDD_IO_3/BOOT0 + 晶振脚 PC14/PC15/PD0/PD1
    INTERNAL_CN = {0, 2, 3, 4, 5, 6, 8, 19, 35, 43, 47}
    conns = []
    for cn, name in enumerate(PINS):
        conns.append('  <connector id="connector%d" name="%s" type="male">\n' % (cn, name))
        conns.append('   <description>%s</description>\n' % name)
        conns.append('   <views>\n')
        if cn not in INTERNAL_CN:
            conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n' % cn)
        conns.append('    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n' % (cn, cn))
        conns.append('    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n' % cn)
        conns.append('   </views>\n')
        conns.append('  </connector>\n')
    # 面包板专用连接器（5V 轨、多余 GND）
    for cn, name in ((48, "5V"), (49, "5V"), (50, "GND")):
        conns.append('  <connector id="connector%d" name="%s" type="male">\n' % (cn, name))
        conns.append('   <description>%s (board rail)</description>\n' % name)
        conns.append('   <views>\n')
        conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n' % cn)
        conns.append('   </views>\n')
        conns.append('  </connector>\n')
    buses = [
        ("GND", ["connector7", "connector22", "connector34", "connector46", "connector50"]),
        ("3V3", ["connector8", "connector23", "connector35", "connector47"]),
        ("5V", ["connector48", "connector49"]),
    ]
    b = [" <buses>\n"]
    for bid, members in buses:
        b.append('  <bus id="%s">\n' % bid)
        for cid in members:
            b.append('   <nodeMember connectorId="%s"/>\n' % cid)
        b.append("  </bus>\n")
    b.append(" </buses>\n")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="1.0.3" moduleId="%s">\n'
        ' <version>4</version>\n <date>2026-08-31</date>\n'
        ' <label>%s</label>\n <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <tags><tag>CH32V203</tag><tag>RISC-V</tag><tag>dev board</tag></tags>\n'
        ' <properties>\n'
        '  <property name="package">LQFP48</property>\n'
        '  <property name="family">WCH RISC-V MCU</property>\n'
        '  <property name="chip">CH32V203C8T6</property>\n'
        '  <property name="pins">48</property>\n'
        ' </properties>\n'
        ' <views>\n'
        '  <iconView><layers image="icon/%s_icon.svg"><layer layerId="icon"/></layers></iconView>\n'
        '  <breadboardView fliphorizontal="true" flipvertical="true"><layers image="breadboard/%s_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true"><layers image="schematic/%s_schematic.svg"><layer layerId="schematic"/></layers></schematicView>\n'
        '  <pcbView><layers image="pcb/%s_pcb.svg"><layer layerId="copper1"/><layer layerId="silkscreen"/></layers></pcbView>\n'
        ' </views>\n'
        ' <connectors>\n%s</connectors>\n%s'
        '</module>\n'
    ) % (PART_ID, LABEL, TITLE, PART_ID, PART_ID, PART_ID, PART_ID,
         "".join(conns), "".join(b))


# ==========================================================================
# 打包
# ==========================================================================
def main():
    files = {
        "icon": gen_icon_svg(),
        "breadboard": gen_breadboard_svg(),
        "schematic": gen_schematic_svg(),
        "pcb": gen_pcb_svg(),
        "fzp": gen_fzp(),
    }
    for view, content in files.items():
        if view == "fzp":
            name = "part.%s.fzp" % PART_ID
        else:
            name = "svg.%s.%s_%s.svg" % (view, PART_ID, view)
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        for view, content in files.items():
            if view == "fzp":
                name = "part.%s.fzp" % PART_ID
            else:
                name = "svg.%s.%s_%s.svg" % (view, PART_ID, view)
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
