# -*- coding: utf-8 -*-
"""
TX-AH-R900PNR — 泰芯 TXW8301 (802.11ah) 贴片模组 Fritzing 元件生成脚本
====================================================================
进度（按 fritzing-parts-langhua AGENTS.md 芯片/模块固定工作流推进）：
  [x] 1. icon svg（本文件目前只生成 icon，后续视图在此脚本基础上扩展）
  [ ] 2. breadboard svg
  [ ] 3. schematic svg
  [ ] 4. pcb svg
  [ ] 5. part.<id>.fzp + 打包 fzpz

模块实物（泰芯 802.11ah TX-AH-Rx00P 系列模组技术规格书 V6.8，20260311 版）：
  - 封装尺寸 (17.00±0.40) x (15.00±0.25) x (2.40±0.20) mm
  - 镀金半孔（castellated）：左 13 / 右 13 / 底 10 = 36 个边脚，
    板背另有 2 个接地散热片 EPAD（顶视图不画，留待 PCB 视图）
  - 无板载天线（R900PNR 用外接天线/ANT 脚）
  - 板上（用户 2026-09-02 版式）：
      TXW8301 主控顺时针旋转 90° 竖放，位于下部偏右（右缘 x=12.0）；
      HS8308E 方形芯片（WDFN-10 3×3，复用 RT6150AGQW_rev_1 icon）在其右上：
      右缘与 TXW8301 右缘对齐（x12.0）、顶边与右侧第 2 个引脚对齐（y=2.2）；
      左缘银色晶振；左下角 P9、右下角 NR（R900PNR 角标）
  - 颜色按实物/官方照片采样：深蓝 PCB ~ #2B3D58，ENIG 金焊盘 #E3B23C。

引脚几何（用户指定，正面看）：每脚 0.7(沿边) x 0.4(径向) mm，缺口半圆直径
0.3 mm（半径 0.15），中心间距 1.2 mm；左/右顶脚中心距上沿 1.0，底行最左脚
中心距左缘 2.1。

比例：1 单位 = 1 mm（icon 与 PCB/面包板视图同几何，便于复用/检查）。
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "TX-AH-R900PNR_1"
TITLE = "TX-AH-R900PNR (Taixin 802.11ah Module)"
LABEL = "U"
PACKAGE = "TX-AH-R900PNR"
FAMILY = "Taixin 802.11ah Module"
FZPZ = "TX-AH-R900PNR.fzpz"

ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID

# 面包板视图 = 泰芯 AH 开发板（V1.6 EVB，70x55mm 圆角）。内部坐标 100 单位=2.54mm
# （ESP32-S3-WROOM-1 同款约定），整板包 scale(0.072) 落到 Fritzing 面包板孔格。
BB_MM_W, BB_MM_H = 70.0, 55.0
BB_SCALE = 7.2 / 100.0   # 0.072

# 左侧 TF 卡板：卡板（冒充 microSD/SD 卡的 PCB，连接 CON3，用于插入其它系统的
# 读卡器，通过 SDIO 与主控通讯）。用户量测：上边沿距主板上边沿 17.3mm、伸出主板
# 22.6mm（向左）。卡板自身高度先按 microSD 卡宽 11mm 起稿（待确认）。
TF_OVER = 22.6        # 伸出主板长度（mm，向左）
TF_TOP = 17.3         # 卡板上边沿距主板上边沿（mm）
TF_H = 11.0           # 卡板高度（mm）＝microSD 卡宽（暂定）

USB_OVER = 16.25      # USB-AM-180 金属壳伸出主板右缘长度（mm，18.75 − 2.5 板内）

ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID

# 模组边脚 1..36（datasheet 表 3-1），EPAD1/2 = 37/38 单独
PINS_EDGE = [
    "GND", "ANT", "GND", "VCC2", "VCC2", "VCC1", "VCC0",
    "IOA3", "IOA0", "IOA2", "IOA1", "IOA30", "IOA31",
    "MCLR", "IOA10", "IOA11", "IOA7", "IOA6", "IOA8", "IOA9",
    "SVCC", "IOB0", "IOB1",
    "IOB2", "IOB3", "IOB4", "IOB5", "IOB6", "IOB7",
    "NC", "NC", "IOA12", "IOA13", "VDD1V3A", "VDD1V3D", "GND",
]
EPADS = ["EPAD1", "EPAD2"]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_TXW_ICON_GROUP = None


def _txw8301_icon_group():
    """复用 svg/TXW8301/svg.icon.TXW8301_1_icon.svg 的 <g id="icon"> 图形（真实
    QFN48 芯片：黑体 6x6 + 四边金焊盘 + pin1 圆点 + TXW8301/802.11ah 文字）。"""
    global _TXW_ICON_GROUP
    if _TXW_ICON_GROUP is None:
        p = os.path.normpath(os.path.join(OUT_DIR, "..", "TXW8301",
                                          "svg.icon.TXW8301_1_icon.svg"))
        src = open(p, encoding="utf-8").read()
        i = src.index('<g id="icon">') + len('<g id="icon">')
        j = src.index('</g>', i)
        _TXW_ICON_GROUP = src[i:j].strip("\n")
    return _TXW_ICON_GROUP

_MODULE_ICON_GROUP = None


def _inner_g_icon(svg_path):
    """取 <g id="icon">...</g> 的内部内容（按深度匹配，正确处理内部嵌套 <g>）。"""
    src = open(svg_path, encoding="utf-8").read()
    tag = '<g id="icon">'
    i = src.index(tag) + len(tag)
    depth, pos = 1, i
    while depth > 0:
        m = re.search(r'<g(?=[\s>])|</g>', src[pos:])
        if not m:
            raise RuntimeError("unbalanced <g id=\"icon\"> in %s" % svg_path)
        depth += -1 if m.group(0).startswith("</") else 1
        pos += m.end()
    return src[i:pos - len("</g>")]


def _module_icon_group():
    """复用本元件自己的 icon 图形（<g id="icon">，15x17mm 模组顶视图），
    面包板视图里当作“板上实物模组”嵌入。"""
    global _MODULE_ICON_GROUP
    if _MODULE_ICON_GROUP is None:
        _MODULE_ICON_GROUP = _inner_g_icon(os.path.join(OUT_DIR, ICON_SVG)).strip("\n")
    return _MODULE_ICON_GROUP


_W25_ICON_GROUP = None


def _w25_icon_group():
    """复用 W25Q16JV 元件 icon（<g id="icon">，SOIC-8，mm 坐标居中原点，
    范围 x±2.64 / y±3.95），面包板视图当板上贴片芯片 1:1 嵌入。"""
    global _W25_ICON_GROUP
    if _W25_ICON_GROUP is None:
        _W25_ICON_GROUP = _inner_g_icon(os.path.normpath(os.path.join(
            OUT_DIR, "..", "W25Q16JV", "svg.icon.W25Q16JV_icon.svg"))).strip("\n")
    return _W25_ICON_GROUP


_RT6150_GROUP = None


def _ch340e_icon_group():
    """复用 CH340E 元件 icon（<g id="icon">，MSOP-10：深体 3×3 + 上下各 5 引脚，
    mm 坐标居中原点，范围 x±1.5 / y±2.5），面包板视图当板上贴片芯片 1:1 嵌入。"""
    global _CH340E_GROUP
    if _CH340E_GROUP is None:
        _CH340E_GROUP = _inner_g_icon(os.path.normpath(os.path.join(
            OUT_DIR, "..", "CH340E", "svg.icon.CH340E_icon.svg"))).strip("\n")
    return _CH340E_GROUP


_CH340E_GROUP = None


def _eta3425s2f_icon_group():
    """复用 ETA3425S2F 元件 icon（<g id="icon">，SOT23-5：黑体 3.0×1.6 +
    上 2 / 下 3 银脚 + pin1 圆点左下，mm 坐标居中原点，
    内容外廓 x±1.5 / y±1.4）。面包板视图当板上贴片芯片 1:1 嵌入。"""
    global _ETA3425_GROUP
    if _ETA3425_GROUP is None:
        _ETA3425_GROUP = _inner_g_icon(os.path.normpath(os.path.join(
            OUT_DIR, "..", "ETA3425S2F", "svg.icon.ETA3425S2F_icon.svg"))).strip("\n")
    return _ETA3425_GROUP


_ETA3425_GROUP = None


def _xc6206_icon_group():
    """复用 XC6206P332MR 元件 icon（<g id="icon">，SOT23-3：黑体 2.9×1.6 +
    上 1 / 下 2 银脚 + pin1 圆点左下，mm 坐标居中原点，
    内容外廓 x±1.45 / y±1.4）。面包板视图当板上贴片芯片 1:1 嵌入。"""
    global _XC6206_GROUP
    if _XC6206_GROUP is None:
        _XC6206_GROUP = _inner_g_icon(os.path.normpath(os.path.join(
            OUT_DIR, "..", "XC6206P332MR", "svg.icon.XC6206P332MR_icon.svg"))).strip("\n")
    return _XC6206_GROUP


_XC6206_GROUP = None


def _rt6150rev_icon_group():
    """复用 svg/RT6150AGQW_rev_1/svg.icon.RT6150AGQW_rev_1_icon.svg 的 <g id="icon">
    图形（WDFN-10 3×3：深体 #303030 + 金焊盘左右各 5 + pin1 点，mm 坐标中心原点，
    体 ±1.5 / 焊盘外露 ±1.62），并去掉其自带的 RT6150/AGQW 丝印文字，
    供模块 icon 右上 HS8308E 芯片复用（HS8308E 封装 = WDFN-10 3×3，同 RT6150AGQW）。"""
    global _RT6150_GROUP
    if _RT6150_GROUP is None:
        c = _inner_g_icon(os.path.normpath(os.path.join(
            OUT_DIR, "..", "RT6150AGQW_rev_1", "svg.icon.RT6150AGQW_rev_1_icon.svg")))
        # 去掉自带丝印 <text ...>..</text>（RT6150 / AGQW），由调用方补 HS8308E
        c = re.sub(r'<text\b[^>]*>.*?</text>', '', c, flags=re.S)
        _RT6150_GROUP = c.strip("\n")
    return _RT6150_GROUP

# ---------------------------------------------------------------------------
# 几何常量（单位 mm，1 单位 = 1 mm）
# ---------------------------------------------------------------------------
MW, MH = 15.0, 17.0          # 板宽(顶/底边) x 板高(左右边)
PITCH = 1.2                  # 引脚中心间距
HALF = 0.35                  # 引脚沿边半长（0.7 全长）
R = 0.15                     # 缺口半圆半径（直径 0.3）
D = 0.25                     # 引脚板内直线段深（径向 0.4 = 0.15 外凸 + 0.25 内伸）

# 颜色
BOARD = "#2B3D58"     # 深蓝 PCB（实物采样）
PAD   = "#E3B23C"     # ENIG 金
CHIP  = "#17171A"     # 磨砂黑芯片
CHIP2 = "#1F1F24"     # 备用芯片深色（HS8308E 现复用 RT6150AGQW_rev_1 icon）
METAL = "#C9CCD1"     # 晶振/滤波金属
TXT_W = "#FFFFFF"     # 板上白丝印
CHIP_TXT = "#F4F4F4"  # 芯片上白字


def _left_right_y():
    """左/右列 13 脚中心 y：顶脚中心距上沿 1.0，间距 1.2。"""
    return [1.0 + i * PITCH for i in range(13)]


def _bottom_x():
    """底行 10 脚中心 x：最左脚中心距左缘 2.1，间距 1.2。"""
    return [2.1 + i * PITCH for i in range(10)]


def icon_svg():
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%dmm" height="%dmm" viewBox="0 0 %d %d">\n'
             % (int(MW), int(MH), int(MW), int(MH)))
    L.append(' <g id="icon">\n')

    # ---- 板体（深蓝矩形；半孔用金色焊盘叠在边上） ----
    L.append('  <rect x="0" y="0" width="%.2f" height="%.2f" fill="%s" stroke="#1b2940" stroke-width="0.10"/>\n'
             % (MW, MH, BOARD))

    # ---- 金色半孔焊盘（左13/右13/底10） ----
    L.append('  <g fill="%s">\n' % PAD)
    for yc in _left_right_y():
        # 左列：边 x=0，向外 -x
        L.append('   <path d="M %.3f %.3f L 0 %.3f L 0 %.3f A %.3f %.3f 0 0 1 0 %.3f'
                 ' L 0 %.3f L %.3f %.3f Z"/>\n'
                 % (D, yc - HALF, yc - HALF, yc - R, R, R, yc + R,
                    yc + HALF, D, yc + HALF))
        # 右列：边 x=MW，向外 +x
        L.append('   <path d="M %.3f %.3f L %.3f %.3f L %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f'
                 ' L %.3f %.3f L %.3f %.3f Z"/>\n'
                 % (MW - D, yc - HALF, MW, yc - HALF, MW, yc - R, R, R, MW, yc + R,
                    MW, yc + HALF, MW - D, yc + HALF))
    for xc in _bottom_x():
        # 底行：边 y=MH，向外 +y
        L.append('   <path d="M %.3f %.3f L %.3f %.3f L %.3f %.3f A %.3f %.3f 0 0 1 %.3f %.3f'
                 ' L %.3f %.3f L %.3f %.3f Z"/>\n'
                 % (xc - HALF, MH - D, xc - HALF, MH, xc - R, MH, R, R, xc + R, MH,
                    xc + HALF, MH, xc + HALF, MH - D))
    L.append('  </g>\n')

    # ---- 板上元器件（无板载天线：R900PNR 用外接天线/ANT 脚） ----
    # 左缘银色晶振
    L.append('  <rect x="1.2" y="4.7" width="2.6" height="1.8" rx="0.2" fill="%s"/>\n' % METAL)
    L.append('  <rect x="2.0" y="4.7" width="1.3" height="1.8" fill="#8f959b"/>\n')

    # ---- HS8308E 方形芯片：右上 —— 封装 = WDFN-10 3×3（同 RT6150AGQW）----
    # 右缘与 TXW8301 右缘对齐(x=12.0)、顶边与右侧第 2 引脚(中心 y=2.2)对齐；
    # 本体 3.0×3.0 (x 9.0..12.0, y 2.2..5.2)。直接复用 RT6150AGQW_rev_1 的
    # icon 图形（mm 中心原点 ±1.65：金焊盘左右各 5 + 直角深体 + pin1 点），
    # 丝印文字 RT6150/AGQW 已由 helper 去掉，此处补标 HS8308E。
    # 芯片（含丝印）绕自身中心逆时针旋转 90°（rotate(-90)，SVG 正角为顺时针）。
    L.append('  <g transform="translate(%.2f %.2f) rotate(-90)">\n' % (10.5, 3.7))
    L.append(_rt6150rev_icon_group())
    # 写实丝印：一行小字（随芯片旋转，仿实物 marking，本体中心略偏下）
    L.append('  <text x="0" y="0.33" font-size="0.5" fill="%s" text-anchor="middle"'
             ' font-family="Arial">HS8308E</text>\n' % CHIP_TXT)
    L.append('  </g>\n')

    # 少量小阻容（浅色），填补空位
    L.append('  <g fill="#c7d0da">\n')
    for (rx, ry) in ((4.4, 5.6), (7.0, 5.4), (12.6, 3.6), (13.8, 5.4),
                     (1.5, 8.4), (3.0, 10.4), (1.5, 12.4), (4.0, 13.4),
                     (2.2, 14.6), (12.8, 8.4), (13.7, 10.4), (12.9, 12.6),
                     (13.6, 14.2)):
        L.append('   <rect x="%.2f" y="%.2f" width="0.9" height="0.6"/>\n' % (rx, ry))
    L.append('  </g>\n')

    # 下部偏右 TXW8301 主控：用真实 QFN48 芯片 icon（<g id="icon">，含焊盘 6.2x6.2），
    # 顺时针旋转 90° 竖放；右缘对齐 x=12.0（与 HS8308E 右缘一致）、中心 y=11.5 -> 中心 (8.9,11.5)，
    # 旋转后占 x 5.8..12.0、y 8.4..14.6。
    TXC, TXCY = 8.9, 11.5
    L.append('  <g transform="translate(%.2f %.2f) rotate(90 3.1 3.1)">\n' % (TXC - 3.1, TXCY - 3.1))
    L.append(_txw8301_icon_group())
    L.append('  </g>\n')

    # ---- 白丝印：左下角 P9 / 右下角 NR（贴角） ----
    L.append('  <g fill="%s" font-family="Arial">\n' % TXT_W)
    L.append('   <text x="0.5" y="16.6" font-size="1.0">P9</text>\n')
    L.append('   <text x="14.5" y="16.6" font-size="1.0" text-anchor="end">NR</text>\n')
    L.append('  </g>\n')

    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def schematic_svg():
    """TX-AH-R900PNR 模组原理图符号（矩形框）。排布按 datasheet 图 3-1 转 90°=icon 同向：
    左列 1-13（上→下，pin1 左上角）、底行 14-23（左→右）、右列 24-36（下→上，pin36 右上）；
    顶边无脚（与实物一致）。EPAD1/2 (37/38) 画在底部中央作独立地焊盘。
    引脚名/编号样式同 TXW8301 芯片符号（AGENTS.md §5）。1000 单位 = 1in。"""
    P = 100
    WIRE = 130
    CH = FN = 35
    BASELINE_OFF = round(FN * 0.35)
    max_len = max(len(n) for n in PINS_EDGE)      # VDD1V3A = 7
    CM = (max_len + 1) * int(FN * 0.58)           # 角部空白（=最长名宽+1字符）
    # 框：宽容纳底行 10 脚（9P + 2CM），高容纳右列 15 脚 24-38（14P + 2CM）
    BX0, BY0 = 300, 200
    BW = 9 * P + 2 * CM
    BH = 14 * P + 2 * CM
    BX1, BY1 = BX0 + BW, BY0 + BH
    BLK = "#000000"
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    M = 20
    # 内容 bbox：左右到引脚线尖(BX±WIRE)，下到底行/EPAD 引线尖(BY1+WIRE)，顶部无引线 -> 只留 M
    VX0, VY0 = BX0 - WIRE - M, BY0 - M
    VSIDE_X = BW + 2 * WIRE + 2 * M
    VSIDE_Y = BH + WIRE + 2 * M
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.3fin" height="%.3fin" viewBox="%d %d %d %d">\n'
             % (VSIDE_X / 1000.0, VSIDE_Y / 1000.0, VX0, VY0, VSIDE_X, VSIDE_Y))
    L.append(' <g id="schematic">\n')
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" stroke="#c00000" stroke-width="5"/>\n'
             % (BX0, BY0, BW, BH))
    # 左列 1-13（上→下）：底部贴底行（pin13 在左下底），左上留空白（右列加高只为容纳 37/38 EPAD）
    for i in range(13):
        cn = i
        y = BY1 - CM - (12 - i) * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="{BLK}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{BLK}" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS_EDGE[cn])}</text>\n')
    # 底行 14-23（左→右）
    for i in range(10):
        cn = 13 + i
        x = BX0 + CM + i * P
        lab = PINS_EDGE[cn]
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{x}" y1="{BY1}" x2="{x}" y2="{BY1 + WIRE}" stroke="{BLK}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{x - 11}" y="{BY1 + WIRE}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{x - FN}" y="{BY1 + 55}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x - FN} {BY1 + 55})">{14 + i}</text>\n')
        ln = int(len(lab) * FN * 0.58)
        L.append(f'  <text x="{x}" y="{BY1 - CH - ln // 2}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x} {BY1 - CH - ln // 2})">{esc(lab)}</text>\n')
    # 右列 24-38（下→上；pin24 底，pin36 中上，37/38=EPAD1/2 顶）
    for i in range(15):
        cn = 23 + i
        y = BY1 - CM - i * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="{BLK}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans">{24 + i}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{BLK}" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PINS_EDGE[cn] if cn < 36 else EPADS[cn - 36])}</text>\n')
    # 型号名（框内居中）
    L.append(f'  <text x="{(BX0 + BX1) // 2}" y="{(BY0 + BY1) // 2 + 10}" font-size="70" fill="#000000" '
             f'text-anchor="middle" font-family="DroidSans">TX-AH-R900PNR</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def pcb_svg():
    """TX-AH-R900PNR 模组 PCB 焊盘（用户按规格书图 8-3 口述，1 单位=1mm，中心为原点）：
      丝印框 15(宽)x17(高)；左/右各 13、底 10 个焊盘 1.5(径向)x0.7(切向)mm、间距 1.2，
      焊盘超出丝印框 0.5mm（径向 1.5 = 0.5 外 + 1.0 内）。
      排布同原理图：左 1-13(上->下)、底 14-23(左->右)、右 24-36(下->上)。
      EPAD1(37) 1.7x3.0 / EPAD2(38) 4.1x4.1 铜区（用户按图 8-3 口述位置）。"""
    HW, HH = 7.5, 8.5          # 丝印半宽/半高（15x17）
    PT, PR = 0.7, 1.5          # 焊盘 切向 x 径向
    PITCH = 1.2
    CP = "#F7BD13"
    pads, silk = [], []
    # 左列 13：cn0..12 = pin1..13，上->下
    for i in range(13):
        y = -HH + 1.3 + i * PITCH          # -7.2 .. 7.2
        pads.append(f'<rect id="connector{i}pad" x="{-HW - 0.5:.3f}" y="{y - PT / 2:.3f}" '
                    f'width="{PR:.3f}" height="{PT:.3f}" fill="{CP}" stroke="none" connectorname="{i}"/>')
    # 底行 10：cn13..22 = pin14..23，左->右
    for j in range(10):
        x = (j - 4.5) * PITCH             # -5.4 .. 5.4
        pads.append(f'<rect id="connector{13 + j}pad" x="{x - PT / 2:.3f}" y="{HH - 1.0:.3f}" '
                    f'width="{PT:.3f}" height="{PR:.3f}" fill="{CP}" stroke="none" connectorname="{13 + j}"/>')
    # 右列 13：cn23..35 = pin24..36，下->上（24 底、36 顶）
    for i in range(13):
        y = HH - 1.3 - i * PITCH           # 7.2 .. -7.2
        pads.append(f'<rect id="connector{23 + i}pad" x="{HW - 1.0:.3f}" y="{y - PT / 2:.3f}" '
                    f'width="{PR:.3f}" height="{PT:.3f}" fill="{CP}" stroke="none" connectorname="{23 + i}"/>')
    # EPAD 画法（规格书图 8-3）：整体铜区分成 2x2 四小块（细十字缝）+ 中心实心圆连接
    # （仿厂商封装图；铜区仍连通，无空洞）。

    def epad(cx, cy, W, H, g, rc, n):
        """以 (cx,cy) 为中心、W x H 的 EPAD：g=十字缝宽、rc=中心连接圆半径。
        输出放到 <g id="connector{n}pad"> 组里。"""
        x0, x1 = cx - W / 2, cx + W / 2
        y0, y1 = cy - H / 2, cy + H / 2
        qw, qh = (W - g) / 2, (H - g) / 2
        shapes = []
        for rx, ry in ((x0, y0), (x1 - qw, y0), (x0, y1 - qh), (x1 - qw, y1 - qh)):
            shapes.append(f'<rect x="{rx:.3f}" y="{ry:.3f}" width="{qw:.3f}" height="{qh:.3f}" '
                          f'fill="{CP}" stroke="none"/>')
        shapes.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{rc:.3f}" fill="{CP}" stroke="none"/>')
        return f'<g id="connector{n}pad" connectorname="{n}">\n' + "\n".join(shapes) + '\n</g>'

    # EPAD1 (37)：3.0(x)x1.7(y)，顶边距丝印上边 2.3、右边距丝印右边 3.9 -> x 0.6..3.6, y -6.2..-4.5
    pads.append(epad(2.100, -5.350, 3.000, 1.700, 0.200, 0.500, 36))
    # EPAD2 (38)：4.1x4.1，底边距丝印下边 3.4、右边距丝印右边 4.7 -> x -1.3..2.8, y 1.0..5.1
    pads.append(epad(0.750, 3.050, 4.100, 4.100, 0.250, 0.500, 37))
    # 丝印：顶部整条 + 四角短线段（去掉焊盘间短线；丝印线距焊盘留 GAP 空隙）
    SILK = "#f0f0f0"
    half = PT / 2          # 0.35（焊盘切向半宽）
    GAP = 0.25             # 丝印线到焊盘的空隙（0.2~0.3mm）
    # 左/右列焊盘 y 范围（13 个，中心 -7.2..7.2）
    y_top = -7.2 - half    # -7.55（pin1 / 左列顶端）
    y_bot = 7.2 + half     # 7.55
    # 底行焊盘 x 范围（10 个，中心 -5.4..5.4）
    xL = -5.4 - half       # -5.75
    xR = 5.4 + half        # 5.75

    def silk_line(x1, y1, x2, y2):
        silk.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
                    f'stroke="{SILK}" stroke-width="0.12"/>')

    # 顶部整条（无焊盘）
    silk_line(-HW, -HH, HW, -HH)
    # 左/右：只画上、下角短线段，与焊盘留 GAP
    silk_line(-HW, -HH, -HW, y_top - GAP)
    silk_line(-HW, y_bot + GAP, -HW, HH)
    silk_line(HW, -HH, HW, y_top - GAP)
    silk_line(HW, y_bot + GAP, HW, HH)
    # 底：只画左、右角短线段，与焊盘留 GAP
    silk_line(-HW, HH, xL - GAP, HH)
    silk_line(xR + GAP, HH, HW, HH)
    # pin1 实心圆点：左上角外侧、贴近 1 脚焊盘（圆边距焊盘 0.3mm）
    silk.append(f'<circle cx="{-HW - 0.40:.3f}" cy="{y_top - 0.62:.3f}" r="0.32" fill="{SILK}" '
                f'stroke="none" class="other"/>')
    inner = "\n".join(pads) + '\n<g id="copper0"/>\n  </g>\n  <g id="silkscreen">\n' + "\n".join(silk)
    # 裁边：内容 x -8.22(pin1点)..8.0(焊盘外缘)、y -8.5(丝印顶)..9.0(底焊盘外缘)，四周留 ~0.2
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="16.6mm" height="17.9mm" viewBox="-8.4 -8.7 16.6 17.9">\n'
            '  <g id="copper1">\n' + inner + '\n  </g>\n</svg>\n')


def buses_xml(gnd_extra=(), vcc_conns=()):
    """显式声明内部互通网：
    - GND：全部 GND 边脚(connector0/2/35) + 面包板专用 GND 针(gnd_extra，CON3 的 connector48) 同网；
    - 面包板专用 VCC 针（CON1 两排 + CON2）同一条 VCC 轨（vcc_conns 传入）；
    - IOB0：CON1 col6 用模组 connector21，CON2 IOB0 用面包板专用 connector38 → 同网。"""
    gnd = [f"connector{i}" for i, n in enumerate(PINS_EDGE) if n == "GND"] + list(gnd_extra)
    L = [" <buses>\n", '  <bus id="GND">\n']
    for cid in gnd:
        L.append(f'   <nodeMember connectorId="{cid}"/>\n')
    L.append("  </bus>\n")
    if vcc_conns:
        L.append('  <bus id="VCC">\n')
        for cid in vcc_conns:
            L.append(f'   <nodeMember connectorId="{cid}"/>\n')
        L.append("  </bus>\n")
    # IOB0 网：CON1 col6 用模组 connector21，CON2 IOB0 用面包板专用 connector38 → 同网
    L.append('  <bus id="IOB0">\n')
    for cid in ("connector21", "connector38"):
        L.append(f'   <nodeMember connectorId="{cid}"/>\n')
    L.append("  </bus>\n")
    L.append(" </buses>\n")
    return "".join(L)


# ---- CON1（底部 11×2 IO 主排）breadboard 针 ↔ 模组边脚 connector 映射（第一步：先能拖上面包板）----
CON1_BB_TOP = ["GND", "IOB1", "IOB6", "IOA11", "IOB7", "NC",
               "IOB4", "NC", "NC", "IOB2", "VCC"]
CON1_BB_BOT = ["GND", "NC", "IOA10", "NC", "NC", "IOB5",
               "IOB0", "NC", "IOB3", "NC", "VCC"]


def _con1_bb_assign():
    """返回 [(connector_idx, x_mm, y_mm, label)]：CON1 22 焊盘全部都有 breadboard 针（2026-09-06 用户：
    NC 位置也焊了针、VCC 也要能接）。GND/IO 名优先挂同名模组边脚（GND→connector0/2，IO 各自）；
    NC 前两处挂模组 NC(connector29/30)，其余 NC 与 VCC 无空闲模组脚 → 面包板专用新增 connector（自 40 起，
    与 CON2 已用的 38/39 不冲突）。位置公式与 breadboard_svg 内一致（CON1_X=14.0、FT=50.36、
    D=(55-FT-2.54)/2、行距2.54）。"""
    x0, ft = 15.16, 50.36
    d = (55 - ft - 2.54) / 2.0
    r1, r2 = ft + d, ft + d + 2.54
    byname = {}
    for i, n in enumerate(PINS_EDGE):
        byname.setdefault(n, []).append(i)
    used, next_extra, out = set(), iter(range(40, 100)), []
    for row, y in ((CON1_BB_TOP, r1), (CON1_BB_BOT, r2)):
        for c, lab in enumerate(row):
            idx = None
            for cand in byname.get(lab, []):
                if cand not in used:
                    idx = cand
                    break
            if idx is None:
                idx = next(next_extra)      # VCC / 多余 NC 无空闲模组边脚 → 面包板专用 connector
            used.add(idx)
            out.append((idx, x0 + c * 2.54, y, lab))
    return out


# ---- CON2（Sleep-IO 1×4：VCC/IOB0/MCLR/GND，与 CON1 下排同线）breadboard 针映射 ----
def _con2_bb_assign():
    """返回 [(connector_idx, x_mm, y_mm, label)]：CON2 4 焊盘 → 面包板 connector。
    位置与 breadboard_svg 内一致（CON2_X0=44.0、y=CON1_Y2）。网络映射：
      GND→connector35（模组 GND 边脚，进 GND bus）；MCLR→connector13（模组 MCLR 边脚，空闲）；
      IOB0→connector38（面包板专用，bus 联模组 connector21）；VCC→connector39（面包板专用，板上 VCC 轨）。"""
    x0, ft = 43.10, 50.36
    d = (55 - ft - 2.54) / 2.0
    y = ft + d + 2.54                     # = CON1_Y2
    return [(39, x0 + 0 * 2.54, y, "VCC"),
            (38, x0 + 1 * 2.54, y, "IOB0"),
            (13, x0 + 2 * 2.54, y, "MCLR"),
            (35, x0 + 3 * 2.54, y, "GND")]


# ---- CON3（SDIO/SPI，左侧纵向 8 针单排）breadboard 针映射 ----
def _con3_bb_assign():
    """返回 [(connector_idx, x_mm, y_mm, label)]：CON3 8 针全部有 breadboard 针（2026-09-06 用户：CON3 也接上）。
    SVCC→模组 connector20（空闲复用）；GND：模组 GND 脚(0/2/35)已被 CON1/CON2 用作 breadboard 针 →
    新增面包板专用 connector48 并入 GND bus；D2/D3/CMD/CLK/D0/D1 无模组同名脚 → 面包板专用
    connector49..54（SDIO↔模组引脚网映射留待连线阶段）。
    位置与 breadboard_svg 一致（CON3_X=5.0、Y0=14-0.66、行距2.54）。"""
    x, y0 = 5.0, 14.0 - 0.66
    names = ["D2", "D3", "CMD", "SVCC", "CLK", "GND", "D0", "D1"]
    idxs = [49, 50, 51, 20, 52, 48, 53, 54]
    return [(idxs[i], x, y0 + i * 2.54, names[i]) for i in range(8)]


# ---- DEBUG-PORT（JST XH 4A，顶部 4 针 GND/A31/A30/VCC）breadboard connector 映射 ----
def _debug_bb_assign():
    """返回 [(connector_idx, x_mm, y_mm, label)]：DEBUG-PORT 4 针可连线（2026-09-06 用户）。
    A31→模组 connector12(IOA31)、A30→connector11(IOA30)（空闲复用，male+breadboard 针）；
    GND/VCC 无空闲同名模组脚 → 面包板专用 connector55/56（GND 进 GND bus、VCC 进 VCC bus）。
    位置：插座左缘 DL=40.4、素材内针 x 2.08/4.62/7.16/9.70、y=5.35（插座下缘针位，避让 y6.65 标签）。"""
    dl, y = 40.4, 5.35
    return [(55, dl + 2.08, y, "GND"),
            (12, dl + 4.62, y, "A31"),
            (11, dl + 7.16, y, "A30"),
            (56, dl + 9.70, y, "VCC")]


def gen_fzp():
    """part.<id>.fzp：38 连接器（无面包板视图——面包板=AH 开发板，待做）。
    connector0..35 = 边脚 1..36（type=pad，贴片半孔/焊盘）；connector36=EPAD1(37)、
    connector37=EPAD2(38)（type=pad）。GND 边脚经 <buses> 显式互通。
    视图：icon / schematic / pcb。"""
    conns = []
    bbmap = {i: lab for i, x, y, lab in _con1_bb_assign()}   # 有 breadboard 针的 connector
    bbmap.update({i: lab for i, x, y, lab in _con2_bb_assign()})
    bbmap.update({i: lab for i, x, y, lab in _con3_bb_assign()})
    bbmap.update({i: lab for i, x, y, lab in _debug_bb_assign()})
    def _bbv(i):
        if i not in bbmap:
            return ""
        return (f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{i}pin"/>\n'
                f'    </breadboardView>\n')
    for i, name in enumerate(PINS_EDGE):
        ctype = "male" if i in bbmap else "pad"   # 有 breadboard 针的边脚要 male 才能吸附面包板孔（Fritzing findConnectorsUnder 跳过 pad）
        conns.append(
            f'  <connector id="connector{i}" name="{esc(name)}" type="{ctype}">\n'
            f'   <description>{esc(name)}</description>\n'
            f'   <views>\n' + _bbv(i) +
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{i}pin" '
            f'terminalId="connector{i}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{i}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    for k, name in enumerate(EPADS):        # EPADS=[EPAD1, EPAD2] -> cn36, cn37
        cn = 36 + k
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(name)}" type="pad">\n'
            f'   <description>{esc(name)} (exposed ground pad)</description>\n'
            f'   <views>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{cn}pin" '
            f'terminalId="connector{cn}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{cn}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    # 面包板专用连接器（无原理图/PCB 视图）：idx>=38 的新增 breadboard connector。
    #   CON2 IOB0/VCC(38/39) + CON1 多余 NC/VCC(40..47) 都在此。type=male 才能插面包板。
    for cn, nm in sorted((i, lab) for i, lab in bbmap.items() if i >= 38):
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(nm)}" type="male">\n'
            f'   <description>{esc(nm)} (breadboard pin)</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cn}pin"/>\n    </breadboardView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>4</version>\n <date>2026-09-03</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>{PACKAGE}</tag>\n  <tag>802.11ah</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n  <property name="chip">TXW8301</property>\n'
            f'  <property name="pins">38</property>\n </properties>\n'
            f' <views>\n'
            f'  <breadboardView>\n   <layers image="breadboard/{PART_ID}_breadboard.svg">\n'
            f'    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            f'  <schematicView>\n   <layers image="schematic/{PART_ID}_schematic.svg">\n'
            f'    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
            f'  <pcbView>\n   <layers image="pcb/{PART_ID}_pcb.svg">\n'
            f'    <layer layerId="copper1"/>\n    <layer layerId="silkscreen"/>\n   </layers>\n  </pcbView>\n'
            f'  <iconView>\n   <layers image="icon/{PART_ID}_icon.svg">\n'
            f'    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n </views>\n'
            f' <connectors>\n' + "\n".join(conns) + '\n </connectors>\n'
            + buses_xml([f"connector{i}" for i, lab in bbmap.items() if i >= 38 and lab == "GND"],
                        [f"connector{i}" for i, lab in bbmap.items() if i >= 38 and lab == "VCC"]) + '</module>\n')


# ---- 外部元件图形复用（DEBUG=JST XH 4A；UART=TypeC16Pin icon） ----
JST_BB_ASSET = os.path.normpath(os.path.join(
    OUT_DIR, "..", "_assets", "jst_xh4a_breadboard.svg"))
TYPEC_ICON_PATH = os.path.normpath(os.path.join(
    OUT_DIR, "..", "TypeC16Pin",
    "svg.icon.TypeC16Pin_d89a481c23a1ca4ff437422a227ed0bb_1_icon.svg"))


def _clean_svg_inner(src):
    """取 <svg...>...</svg> 内部内容，去掉 desc/metadata/defs 与 id/gorn 属性。"""
    i = src.find(">", src.find("<svg")) + 1
    j = src.rfind("</svg>")
    inner = src[i:j]
    inner = re.sub(r"<desc\b.*?</desc>", "", inner, flags=re.S)
    inner = re.sub(r"<metadata\b.*?</metadata>", "", inner, flags=re.S)
    inner = re.sub(r"<defs\b.*?</defs>", "", inner, flags=re.S)
    inner = re.sub(r'\s+(?:id|gorn)="[^"]*"', "", inner)
    return inner.strip("\n")


def _jst_bb_inner():
    """从仓库内资产 svg/_assets/jst_xh4a_breadboard.svg（自 JST XH 4A 2.54mm
    fzpz 提取的面包板 svg，mm 单位）取内部图形。"""
    with open(JST_BB_ASSET, encoding="utf-8") as f:
        return _clean_svg_inner(f.read())


def _jst_bb_debug_inner():
    """DEBUG-PORT 用：取 JST XH4A 素材内部，把 4 个方针(connector0..3pin)保留为 breadboard
    connector 并重映射到本元件 connector id（2026-09-06 用户：方针即连接点，不另画排针）：
      connector0pin→55(GND) 1pin→12(A31/IOA31) 2pin→11(A30/IOA30) 3pin→56(VCC)；
    其余 id/gorn/desc/meta/defs 全部剥掉（避免与板内其它 id 冲突）。"""
    with open(JST_BB_ASSET, encoding="utf-8") as f:
        src = f.read()
    i = src.find(">", src.find("<svg")) + 1
    j = src.rfind("</svg>")
    inner = src[i:j]
    inner = re.sub(r"<desc\b.*?</desc>", "", inner, flags=re.S)
    inner = re.sub(r"<metadata\b.*?</metadata>", "", inner, flags=re.S)
    inner = re.sub(r"<defs\b.*?</defs>", "", inner, flags=re.S)
    # 本体已旋转 180° → 方针位置镜像。按用户（2026-09-06）：从左到右应为 GND/A31/A30/VCC，
    # 故左侧(connector3pin/原素材 x9.70)=GND、其次 A31、A30、最右(connector0pin/原 x2.08)=VCC
    remap = {"connector0pin": "connector56pin",   # VCC（旋转后最右）
             "connector1pin": "connector11pin",   # A30（旋转后右二）
             "connector2pin": "connector12pin",   # A31（旋转后左二）
             "connector3pin": "connector55pin"}   # GND（旋转后最左）
    for k, v in remap.items():
        inner = inner.replace('id="%s"' % k, 'id="%s"' % v)
    inner = re.sub(r'\sgorn="[^"]*"', "", inner)
    inner = re.sub(r'\s+id="(?!connector\d+pin)[^"]*"', "", inner)
    return inner.strip("\n")


# SparkFun 贴片轻触开关 SMD-1101NE 面包板图形（Fritzing 官方 core 部件，
# 原始 1000 单位=1in，与本库面包板内部单位同比例，1:1 复用）——
# 原为独立 btn_smd1101ne.svg（外部来源，2026-09-05 内联进本脚本后删除）。
_BTN_1101NE_INNER = """    <polyline fill="#808080" points="0,71.4028,339.292,71.4028,339.292,69.0694,0,69.0694"/>
    <g>
     <g>
      <polygon fill="#8C8C8C" points="0,34.8194,339.292,34.8194,339.292,69.0694,0,69.0694"/>
      <path fill="#474747" d="M64.2222,102.806c-11.3472,0,-11.6667,-3.86111,-11.6667,-8.95833L52.5556,39.125c-0.0277778,-5.01389,3.70833,-9.02778,15.0417,-9.02778l206.389,0c11.4583,0,15.25,4.05556,15.25,9.25l0,54.5833c0.0833333,5.08333,-3.875,8.93056,-15.25,8.93056L64.2222,102.806L64.2222,102.806z"/>
      <path fill="#666666" d="M64.2222,87.1806c-11.3472,0,-11.6667,-4.01389,-11.6667,-8.94444L52.5556,10.0417C52.5417,5.09722,56.2778,1.08333,67.625,1.08333l206.361,0c11.4861,0,15.25,4.05556,15.25,8.94444l0,68.1944c0.0833333,4.94444,-3.875,8.94444,-15.25,8.94444L64.2222,87.1806L64.2222,87.1806z"/>
      <g>
       <ellipse cx="76.9722" cy="44.0278" rx="9.26389" ry="6.98611"/>
       <ellipse cx="264.083" cy="44.0278" rx="9.26389" ry="6.98611"/>
      </g>
      <path fill="none" stroke="#333333" stroke-width="5.55556" d="M239.306,26.1528l0,41.3194c0.0277778,3.68056,-3.70833,8.19444,-12.125,8.19444L114.333,75.6667c-8.43056,0,-11.9028,-4.48611,-11.9444,-8.19444L102.389,26.1528"/>
      <path fill="#C4C4C4" d="M116.597,73.7639c-8.52778,0,-11.9444,-3.01389,-11.9861,-6.86111l0,-42.6389c0,-3.63889,2.77778,-6.70833,11.2222,-6.70833l110.083,0c8.5,0,11.2639,3.29167,11.2917,6.875l0,42.6806c0.0833333,3.90278,-3.68056,6.875,-12.125,6.875L116.597,73.7639L116.597,73.7639z"/>
      <path fill="#EDEDED" d="M116.597,61.8056c-8.52778,0,-11.9444,-3.01389,-11.9861,-6.875L104.611,15.3889c0,-3.65278,2.77778,-6.65278,11.2222,-6.65278l110.083,0c8.5,0,11.2639,2.98611,11.2917,6.65278l0,39.6944c0.0555556,3.88889,-3.68056,6.86111,-12.125,6.86111L116.597,61.8056L116.597,61.8056z"/>
     </g>
    </g>
    <path opacity="0.2" fill="#FFFFFF" d="M289.236,13.2083c0,-4.88889,-3.76389,-8.94444,-15.25,-8.94444L67.625,4.26389c-11.3472,0,-15.0833,4.01389,-15.0694,8.97222L52.5556,10.0417C52.5417,5.09722,56.2778,1.08333,67.625,1.08333l206.361,0c11.4861,0,15.25,4.05556,15.25,8.94444L289.236,13.2083z"/>
    <path opacity="0.2" d="M52.5556,75.0556c0,4.91667,3.76389,8.95833,15.25,8.95833L274.167,84.0139c11.3333,0,15.0833,-4.01389,15.0694,-8.95833l0,3.18056c0.0138889,4.93056,-3.73611,8.95833,-15.0694,8.95833L67.7917,87.1944c-11.4861,0,-15.25,-4.04167,-15.25,-8.93056L52.5417,75.0556z"/>
    <path opacity="0.2" d="M52.5556,90.7083c0,4.91667,3.76389,8.95833,15.25,8.95833L274.167,99.6667c11.3333,0,15.0833,-4.01389,15.0694,-8.95833L289.236,93.8889c0.0138889,4.93056,-3.73611,8.95833,-15.0694,8.95833L67.7917,102.847c-11.4861,0,-15.25,-4.04167,-15.25,-8.93056L52.5417,90.7083z"/>
"""


def _btn1101ne():
    """SparkFun 贴片轻触开关 SMD-1101NE 面包板图形（内联，见 _BTN_1101NE_INNER）。"""
    return _BTN_1101NE_INNER.strip("\n")


def breadboard_svg():
    """TX-AH-R900PNR 面包板视图（v1 外观稿）：泰芯 AH 模组开发板 V1.6 EVB，
    70x55mm 圆角深蓝 PCB（用户量测）。布局按手册图 2-1 主视图 + 用户锚点：
    CON1 丝印距左边 ~14mm、CON3 距左边 ~5mm、DEBUG-PORT 距右边 ~17mm。
    中央模组直接复用本元件 icon（15x17mm）作板上实物。排针/丝印为 v1 外观，
    引脚连线（连到 connector0..37）待 IO-PORT 映射确认后补。"""
    def u(mm):            # mm -> 内部单位 (100 单位 = 2.54mm)
        return int(round(mm * 100 / 2.54))
    W, H = u(BB_MM_W), u(BB_MM_H)   # 2756 x 2165
    PCB = "#151515"          # 实物黑 PCB
    PCB_E = "#000000"
    SILK = "#f5f5f5"
    SILK_D = "#c8ccd0"
    METAL = "#d8dbdd"
    METAL_D = "#9aa0a6"
    GOLD = "#e6b53d"
    PIN_M = "#d0d0d0"
    PIN_E = "#8a8a8a"
    TOT_W = BB_MM_W + TF_OVER + USB_OVER   # 含左 TF 卡板 + 右 USB 伸出（mm）
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    # 顶部留 10mm 空：SMA 座螺纹筒向上伸出板上沿 9.5mm 的显示空间
    TOP_OVER = 10.0
    view_x, view_y = 0.0, -(u(TOP_OVER) * BB_SCALE)
    view_w = u(TOT_W) * BB_SCALE
    view_h = (H + u(TOP_OVER)) * BB_SCALE
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" viewBox="%.1f %.1f %.1f %.1f">\n'
             % (TOT_W, BB_MM_H + TOP_OVER, view_x, view_y, view_w, view_h))
    L.append(' <g id="breadboard" transform="scale(%g)">\n' % BB_SCALE)

    # 主板内容整体右移 TF_OVER（保持全部原有板内坐标不变）
    L.append('  <g transform="translate(%d 0)">\n' % u(TF_OVER))

    # 深蓝圆角 PCB
    L.append('  <rect x="0" y="0" width="%d" height="%d" rx="%d" fill="%s" stroke="%s" stroke-width="8"/>\n'
             % (W, H, u(4), PCB, PCB_E))
    # 4 个安装孔：金色盘外径 6mm（r=3.0）、内孔孔径 3mm（r=1.5）
    # 2026-09-06 用户定位（按「外圈距主板边沿」约束反推孔心，主板 70x55）：
    #   左孔 x=6.0（外圈距左边 3mm）、右孔 x=66.0（外圈距右边 1mm）
    #   上孔 y=4.5（外圈距顶边 1.5mm）；下孔：左下 y=39.3（外圈距底 12.7mm）、右下 y=43.9（外圈距底 8.1mm）
    HOLES = ((6.0, 4.5), (66.0, 4.5), (6.0, 39.3), (66.0, 43.9))    # TL, TR, BL, BR
    for hx, hy in HOLES:
        L.append('  <circle cx="%d" cy="%d" r="%d" fill="%s"/>\n' % (u(hx), u(hy), u(3.0), GOLD))
        L.append('  <circle cx="%d" cy="%d" r="%d" fill="#0a0d11"/>\n' % (u(hx), u(hy), u(1.5)))
    # 白色丝印文字（一般层）
    def txt(x, y, s, size=1.1, color=SILK, anchor="start", rot=None):
        t = f'<text x="{u(x)}" y="{u(y)}" font-size="{int(size * 39.37)}" fill="{color}" text-anchor="{anchor}" '
        if rot:
            t += f'transform="rotate({rot} {u(x)} {u(y)})" '
        t += 'font-family="DroidSans">%s</text>\n' % s
        L.append('  ' + t)

    # 板上标号（丝印）与版式（v2）

    # ---- 中央 TX-AH-R900PNR 模组（左缘距左 16mm，顺时针旋转 90°） ----
    XC, YC = 23.5, 21.5       # 模组中心（旋转前 15x17，中心同）
    mod = _module_icon_group()
    L.append('  <g transform="translate(%d %d) rotate(90) translate(%d %d) scale(39.37)">\n'
             % (u(XC), u(YC), -u(7.5), -u(8.5)))
    L.append(mod)
    L.append('  </g>\n')
    # 模组编号 U1（原为型号名 TX-AH-R900PNR，用户 2026-09-05 定：直接改为 U1）
    txt(33.6, 21.5, "U1", 0.8, SILK, anchor="middle", rot=-90)

    # ---- W25Q16JV 贴片 SPI Flash（SOIC-8，复用 W25Q16JV icon 1:1，顺时针旋转 90°） ----
    # 2026-09-06 用户定：U2 整体两次右移 0.8mm（避开左上安装孔）
    w25 = _w25_icon_group()
    WX, WY = 14.24, 4.44
    L.append('  <g transform="translate(%d %d) rotate(90) scale(39.37)">\n' % (u(WX), u(WY)))
    L.append(w25)
    L.append('  </g>\n')

    # ---- SMA 天线座（用户 2026-09-06：距主板左边界 27.5mm，螺纹筒向上伸出板上沿 9.5mm；
    #      竖放，复用 SMA-PJ1.7-L9.5 干净三脚图形 sma_icon_3pin_clean.svg）----
    _sma = open(os.path.normpath(os.path.join(
        OUT_DIR, "..", "SMA-PJ1.7-L9.5", "sma_icon_3pin_clean.svg")), encoding="utf-8").read()
    _sma_in = re.sub(r'^.*?<svg[^>]*>\n?', '', _sma, flags=re.S)
    _sma_in = re.sub(r'</svg>\s*$', '', _sma_in, flags=re.S)
    # 内嵌到本 svg 可能与本板其它金渐变 id 冲突 → 改唯一 id
    _sma_in = _sma_in.replace('id="gold"', 'id="tx_sma_gold"').replace('url(#gold)', 'url(#tx_sma_gold)')
    # translate(27.5, 3.94) rotate(-90)：图形左端(本地 x=0)对齐主板左 27.5mm，
    # 螺纹筒(本地 x→13.5)旋转后向上伸到板上沿上方 9.5mm，三引脚贴板内(y 0..3.94)
    L.append('  <g transform="translate(%d %d) rotate(-90) scale(39.37)">\n'
             % (u(27.5), u(3.94)))
    L.append(_sma_in)
    L.append('  </g>\n')

    # ---- USB-AM-180 = USB-A 公头（竖贴右缘，插口朝右） ----
    # 金属壳 18.75×12mm（顶视直角矩形）：后 2.5mm 在板内(x=67.5..70)、前 16.25mm 伸出
    # (x=70..86.25)，中心 y=20 → y 14..26；壳后 4 引脚 1.8×0.6mm、间距 2mm 伸入板内
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="3"/>\n'
             % (u(67.5), u(14.0), u(18.75), u(12.0), METAL, METAL_D))      # 金属壳（直角）
    # 顶视图表现侧视 0.8mm 圆角：距壳上下边线 0.4mm 各画一条横线（贯穿壳全长，深灰）
    L.append('  <line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#54595e" stroke-width="2"/>\n'
             % (u(67.5), u(14.4), u(86.25), u(14.4)))
    L.append('  <line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#54595e" stroke-width="2"/>\n'
             % (u(67.5), u(25.6), u(86.25), u(25.6)))
    # 壳面特征：
    # 两个观察窗（竖放：1.5 宽 x 2.0 高；保持中心 x=80.55，上窗心 y=16.45 / 下窗心 y=23.55）
    # 窗内为白塑料的暗灰色（偏深）
    for wyc in (16.45, 23.55):
        L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#4f5459"/>\n'
                 % (u(80.55 - 0.75), u(wyc - 1.0), u(1.5), u(2.0)))
    # 椭圆形坑（竖放 1.2×1.6，中心 x=69.5,y=20）：坑内浅灰填充（比观察窗浅）
    L.append('  <ellipse cx="%d" cy="%d" rx="%d" ry="%d" fill="#8a8f93" stroke="none"/>\n'
             % (u(69.5), u(20.0), u(0.6), u(0.8)))
    for dy in (-3, -1, 1, 3):
        L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="2"/>\n'
                 % (u(65.7), u(20 + dy - 0.3), u(1.8), u(0.6), PIN_M, PIN_E))   # 4 引脚

    def pin(x, y, r=0.66):
        L.append('  <circle cx="%d" cy="%d" r="%d" fill="%s" stroke="%s" stroke-width="5"/>\n'
                 % (u(x), u(y), u(r), PIN_M, PIN_E))

    # 标准跳线帽（2026-09-05 用户定：J4 的实现记为标准，J7/J8 按它画）
    # 画法（J4 基准，工业写实、无镂空）：跨两针 p1/p2（相距 2.54，可横/竖），
    #   ① 实心圆角塑料体：沿针向长 4.8、垂直向厚 2.3、rx0.3（中心=两针中点）
    #   ② 每针处画银盘 r0.95（帽两端金属接触）
    #   ③ 每针处画深蓝孔 r0.42（帽内孔）
    #   ④ 两针之间金属桥（垂直向厚 0.6、沿针向贯通两盘中心）
    def jumper_cap(p1x, p1y, p2x, p2y, color):
        vertical = (abs(p1x - p2x) < 0.001)
        cx, cy = (p1x + p2x) / 2.0, (p1y + p2y) / 2.0
        if vertical:
            w, h = 2.3, 4.8
        else:
            w, h = 4.8, 2.3
        L.append('  <rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s"/>\n'
                 % (u(cx - w / 2), u(cy - h / 2), u(w), u(h), u(0.3), color))
        for (px, py) in ((p1x, p1y), (p2x, p2y)):
            L.append('  <circle cx="%d" cy="%d" r="%d" fill="#d9dde0"/>\n' % (u(px), u(py), u(0.95)))
            L.append('  <circle cx="%d" cy="%d" r="%d" fill="#33507f"/>\n' % (u(px), u(py), u(0.42)))
        if vertical:
            L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#d9dde0"/>\n'
                     % (u(cx - 0.3), u(min(p1y, p2y)), u(0.6), u(2.54)))
        else:
            L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#d9dde0"/>\n'
                     % (u(min(p1x, p2x)), u(cy - 0.3), u(2.54), u(0.6)))

    # ---- CON3 = SDIO/SPI：纵向 8 针单排 + 直角方框；CON3 文字在框正上方；
    #      焊盘上->下 D2/D3/CMD/5VCC/CLK/GND/D0/D1 ----
    # 2026-09-05 用户定：CON3 整体上移一个焊盘半径(0.66mm)，给下方 J7 让出更多空间
    CON3_X, CON3_Y0 = 5.0, 14.0 - 0.66
    CON3_NAMES = ["D2", "D3", "CMD", "SVCC", "CLK", "GND", "D0", "D1"]
    # breadboard 针：8 针全部挂 connector（SVCC 复用模组边脚 20；GND/其余 SDIO 用面包板专用 48..54）
    for idx, px, py, lab in _con3_bb_assign():
        L.append('  <circle id="connector%dpin" connectorname="%s" cx="%d" cy="%d" '
                 'r="%d" fill="%s" stroke="%s" stroke-width="5"/>\n'
                 % (idx, lab, u(px), u(py), u(0.66), PIN_M, PIN_E))
    # 直角外框（包住 8 针）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="5"/>\n'
             % (u(CON3_X - 1.2), u(CON3_Y0 - 1.2), u(2.4), u(7 * 2.54 + 2.4), SILK))
    txt(CON3_X, CON3_Y0 - 1.45, "CON3", 0.9, SILK, anchor="middle")
    # 焊盘名丝印在框左侧（竖排随焊盘，0.8）
    for i, lab in enumerate(CON3_NAMES):
        txt(CON3_X - 2.4, CON3_Y0 + i * 2.54, lab, 0.8, SILK, anchor="middle", rot=90)

    # ---- CON1 = IO-PORT：11x2 双排；直角外框（底 55 齐板下沿）；CON1 丝印在框左竖排（C 在下）；
    #      第1|2 列、第6|7 列之间有分隔竖线；两排针到上下框线等距 ----
    # 2026-09-06 用户：CON3 固定不可移 → CON1/CON2 列相位对齐 CON3（x=5.0 → 相位 2.46 mod 2.54）。
    #   CON1 首列 14.0(相位1.3) → 15.16 = 2.46+5*2.54；CON2 紧随其后 col11。
    CON1_X = 15.16                     # 首列 x
    CON1_FT = 50.36                    # 外框上边（外框底 = 55）
    CON1_D = (55 - CON1_FT - 2.54) / 2.0   # 排针行到上下框线等距 = 1.05
    CON1_ROW1 = CON1_FT + CON1_D       # 上排中心 y
    CON1_Y2 = CON1_ROW1 + 2.54         # 下排中心 y
    CON1_BX = 14.06                    # 外框左缘（=12.9+1.16）
    # breadboard 针：22 焊盘全部挂 connector（GND/IO 挂模组边脚；NC/VCC 多出部分用面包板专用新增
    # connector 40..47）→ Fritzing 拖上面包板可吸附、插上全绿。
    for idx, px, py, lab in _con1_bb_assign():
        L.append('  <circle id="connector%dpin" connectorname="%s" cx="%d" cy="%d" '
                 'r="%d" fill="%s" stroke="%s" stroke-width="5"/>\n'
                 % (idx, lab, u(px), u(py), u(0.66), PIN_M, PIN_E))
    # 直角外框（右下 = 41.56,55 齐板下沿）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="5"/>\n'
             % (u(CON1_BX), u(CON1_FT), u(41.56 - CON1_BX), u(55 - CON1_FT), SILK))
    # 分隔竖线（焊盘列间隙中点；第1|2 与第6|7 列之间）
    for div_col in (1, 6):
        lx = CON1_X + div_col * 2.54 - 1.27
        L.append('  <line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="5"/>\n'
                 % (u(lx), u(CON1_FT + 0.4), u(lx), u(54.8), SILK))
    # 22 个焊盘名两行白字（0.8），在 CON1 框上方逐列：上行文本=上排脚、下行文本=下排脚
    CON1_TOP = ["GND", "IOB1", "IOB6", "IOA11", "IOB7", "NC",
                "IOB4", "NC", "NC", "IOB2", "VCC"]
    CON1_BOT = ["GND", "NC", "IOA10", "NC", "NC", "IOB5",
                "IOB0", "NC", "IOB3", "NC", "VCC"]
    for i, lab in enumerate(CON1_TOP):
        txt(CON1_X + i * 2.54, CON1_FT - 1.40, lab, 0.8, SILK, anchor="middle")
    for i, lab in enumerate(CON1_BOT):
        txt(CON1_X + i * 2.54, CON1_FT - 0.25, lab, 0.8, SILK, anchor="middle")
    # CON1 丝印：框左侧竖排，字母 C 在下（rotate -90，由下往上读）
    # 2026-09-05 用户定：文字右缘距白框左缘 0.5mm（框左缘 CON1_BX=14.06 → 锚点≈13.56）
    txt(CON1_BX - 0.5, 52.6, "CON1", 0.8, SILK, anchor="middle", rot=-90)

    # ---- DEBUG-PORT = JST XH 4A（4 针插座，顶齐板上沿；右缘距主板右沿 17.3mm） ----
    # JST XH4A 插座宽 12.3mm：右缘 = 70-17.3 = 52.7 → 左缘 DL = 40.4
    DL = 40.4                      # 插座左缘（mm）
    # 2026-09-06 用户定：DEBUG-PORT(JST XH4A) 本体旋转 180°（绕几何中心 6.15,2.875mm 原地翻转，
    #   占位仍 x DL..DL+12.3、y 0..5.75）
    L.append('  <g transform="translate(%d %d) scale(39.37) translate(6.15 2.875) '
             'rotate(180) translate(-6.15 -2.875)">\n' % (u(DL), u(0)))
    # 4 个灰色方针本身即 connector（_jst_bb_debug_inner 已把 id 重映射为 connector55/12/11/56pin）——
    # 不再另画排针；下方标签与方针一一对应（GND/A31/A30/VCC）
    L.append(_jst_bb_debug_inner())
    L.append('  </g>\n')
    # 引脚标签：对位到旋转后各方针正下方（方针中心 x = DL+(12.3-原素材x)，y 基线 6.65）
    for xp, lab in ((DL + 2.60, "GND"), (DL + 5.14, "A31"), (DL + 7.68, "A30"), (DL + 10.22, "VCC")):
        txt(xp, 6.65, lab, 0.8, SILK, anchor="middle")

    # ---- Power LED = 贴片 0603 发光二极管（竖放：0.8 宽 x 1.6 高；右沿距右 10.4、上沿距顶 1.6） ----
    LX1 = 70.0 - 10.4        # 59.6 右沿
    LY0 = 1.6                # 上沿
    LX0 = LX1 - 0.8          # 58.8 左沿（宽 0.8）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="#dedede" stroke="#8f8f8f" stroke-width="3"/>\n'
             % (u(LX0), u(LY0), u(0.8), u(1.6), u(0.15)))
    # 两端银焊端（竖放：上下短边）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#b9bdc1"/>\n' % (u(LX0), u(LY0), u(0.8), u(0.32)))
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#b9bdc1"/>\n' % (u(LX0), u(LY0 + 1.28), u(0.8), u(0.32)))
    # 红色发光芯（中心 x=59.2, y=2.4）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#e02424"/>\n'
             % (u(59.2 - 0.16), u(2.4 - 0.24), u(0.32), u(0.48)))
    txt(60.5, 2.4, "PWR_LED", 0.8, SILK_D, anchor="middle", rot=-90)   # 竖排在 LED 右侧，P 在下

    # ---- 两个贴片轻触开关（SparkFun SMD-1101NE；水平放置，距左 2.7、距底 1.7 / 7.7） ----
    # 2026-09-05 用户定：
    #  - 两按钮整体右移 BTN_SH(0.6mm)，在左侧给 S2/S3 参考文字让出位置；
    #  - PAIR KEY（下方按钮）上移，使其水平中线与 CON1 上排焊盘中心线(51.41)重合；
    #  - S2 放 PAIR KEY 按钮左侧、S3 放 DEBUG 按钮左侧，右缘距按钮左缘 0.3mm，
    #    垂直居中于各按钮中线（baseline 修正 +0.26）。
    BTN = _btn1101ne()
    BTN_SH = 0.6                    # 按钮整体右移量（mm，给左侧 S2/S3 让位）
    BTN_X = u(2.7 + BTN_SH) - 53    # 平移 x：内容 x=0 → 板 x=u(2.7+SH)-53 单位
    # PAIR KEY（下，原 bby=53.3）中线 bby-1.295 = 51.41 → bby=52.705；DEBUG（上，bby=47.3）不变
    for bby in (52.705, 47.3):
        L.append('  <g transform="translate(%d %d)">\n' % (BTN_X, u(bby) - 103))
        L.append(BTN)
        L.append('  </g>\n')
    # 按钮功能丝印：下按钮 PAIR KEY、上按钮 DEBUG，各在其顶边上方 0.3mm（基线）；
    #   PAIR KEY 随按钮上移 0.595
    txt(5.7 + BTN_SH, 50.4 - 0.595, "PAIR KEY", 0.8, SILK, anchor="middle")
    txt(5.7 + BTN_SH, 44.4, "DEBUG", 0.8, SILK, anchor="middle")
    # 参考位号 S2(PAIR KEY)/S3(DEBUG)：按钮左侧 0.3mm（end 锚 → 文字右缘=按钮左缘-0.3）
    BTN_LEFT = BTN_X / 39.37        # 按钮图形最左缘（内容 x=0 → 板 x=BTN_X 单位）
    txt(BTN_LEFT - 0.3, 51.41 + 0.26, "S2", 0.8, SILK, anchor="end")
    txt(BTN_LEFT - 0.3, 46.0 + 0.26, "S3", 0.8, SILK, anchor="end")

    # ---- CON2 = Sleep-IO：4 焊盘与 CON1 下排对齐，直角外框；CON2 文字在框右侧竖排（C 在下）
    #     焊盘左->右 = VCC/IOB0/MCLR/GND（丝印在框上方）----
    # breadboard 针：全部挂到 connector（GND/MCLR 复用模组边脚；IOB0/VCC 为面包板专用 38/39）
    # 2026-09-06 用户：CON3 固定、CON1/CON2 对齐其相位 → CON2 首列 = CON1 首列+11*2.54
    #   = 15.16+27.94 = 43.10（col11..14，与 CON1/CON3 同格）
    CON2_X0 = 43.10
    for idx, px, py, lab in _con2_bb_assign():
        L.append('  <circle id="connector%dpin" connectorname="%s" cx="%d" cy="%d" '
                 'r="%d" fill="%s" stroke="%s" stroke-width="5"/>\n'
                 % (idx, lab, u(px), u(py), u(0.66), PIN_M, PIN_E))
    CON2_BL = CON2_X0 - 1.1
    CON2_BR = CON2_X0 + 3 * 2.54 + 1.1
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="5"/>\n'
             % (u(CON2_BL), u(CON1_Y2 - 1.05), u(CON2_BR - CON2_BL), u(55 - (CON1_Y2 - 1.05)), SILK))
    # 焊盘信号丝印在框上方：文字底边距白框顶 0.25mm
    for xp, lab in ((CON2_X0, "VCC"), (CON2_X0 + 2.54, "IOB0"),
                    (CON2_X0 + 5.08, "MCLR"), (CON2_X0 + 7.62, "GND")):
        txt(xp, CON1_Y2 - 1.30, lab, 0.8, SILK, anchor="middle")
    txt(CON2_BR + 1.35, 53.95, "CON2", 0.8, SILK, anchor="middle", rot=-90)

    # ---- UART = TypeC16 插座（官方 icon；绕自身中心旋转 180°，插口朝下 → 从下往上插线） ----
    UART_X, UART_Y = 55.7, 47.5
    # icon 内容≈占满 viewBox 25.344x21.572，中心≈(12.672,10.786)；s=13.888
    ucx, ucy = 176, 150
    L.append('  <g transform="translate(%d %d) translate(%d %d) rotate(180) translate(%d %d) scale(13.888)">\n'
             % (u(UART_X), u(UART_Y), ucx, ucy, -ucx, -ucy))
    L.append(_clean_svg_inner(open(TYPEC_ICON_PATH, encoding="utf-8").read()))
    L.append('  </g>\n')
    txt(UART_X + 4.5, UART_Y - 0.7, "UART", 1.5, SILK_D, anchor="middle")

    # ---- 4 个 3 针跳线并排（JU 区改造，J4/J5 为主）：GND | J4(A11/A13) | J5(A10/A12) | VCC ----
    # 每列竖向 3 焊盘、间距 2.54；J4/J5 默认中-下戴黄帽（A11/A13、A10/A12 连中间公共）；
    # GND/VCC 新列不戴帽、上下都标 GND/VCC。J 编号(0.8)竖排在 VCC 右侧：J5(上)、J4(下)。
    JU_Y0 = 15.1                      # 各列上排中心 y
    JU_J4 = 44.76                     # J4 列中心 x（=原左列 A11/A13）
    JU_J5 = JU_J4 + 2.54              # J5 列中心 x（=原右列 A10/A12）
    JU_GN = JU_J4 - 2.54              # GND 列中心 x（在 J4 左侧）
    JU_VC = JU_J5 + 2.54              # VCC 列中心 x（在 J5 右侧）
    for cx in (JU_GN, JU_J4, JU_J5, JU_VC):
        for r in range(3):
            pin(cx, JU_Y0 + r * 2.54)
    # JU 外框：4 列并排不留缝，两邻框边融合为一条分隔竖线（外框 1 个 + 内部 3 条竖分隔）
    #   列占宽 = 列距 2.54 → 外框左缘 = GND列心-1.27、右缘 = VCC列心+1.27，总宽 4*2.54；
    #   y = 首针上 1.2 .. 尾针下 1.2（同前高 7.48）
    JU_FX0 = JU_GN - 1.27                     # 外框左缘 40.95
    JU_FY0 = JU_Y0 - 1.2                      # 外框顶 13.9
    JU_FW = 4 * 2.54                          # 10.16
    JU_FH = 7.48
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="5"/>\n'
             % (u(JU_FX0), u(JU_FY0), u(JU_FW), u(JU_FH), SILK))
    for divx in (JU_J4 - 1.27, JU_J5 - 1.27, JU_VC - 1.27):
        L.append('  <line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="5"/>\n'
                 % (u(divx), u(JU_FY0), u(divx), u(JU_FY0 + JU_FH), SILK))
    # 标签（列顶/底，均移到框外）：GND、A11/A13、A10/A12、VCC
    #   顶基线 = 框顶上方 0.3（字形从基线向上伸，距框 0.3）→ JU_Y0-1.5
    #   底基线 = 框底下方 0.3 + 字形高：框底 JU_Y0+6.28；2026-09-05 字号 0.55→0.8，
    #           字形 cap≈0.52 → 基线 = 6.28+0.3+0.52 = JU_Y0+7.10
    txt(JU_GN, JU_Y0 - 1.5, "GND", 0.8, SILK, anchor="middle")
    txt(JU_GN, JU_Y0 + 7.10, "GND", 0.8, SILK, anchor="middle")
    txt(JU_J4, JU_Y0 - 1.5, "A11", 0.8, SILK, anchor="middle")
    txt(JU_J4, JU_Y0 + 7.10, "A13", 0.8, SILK, anchor="middle")
    txt(JU_J5, JU_Y0 - 1.5, "A10", 0.8, SILK, anchor="middle")
    txt(JU_J5, JU_Y0 + 7.10, "A12", 0.8, SILK, anchor="middle")
    txt(JU_VC, JU_Y0 - 1.5, "VCC", 0.8, SILK, anchor="middle")
    txt(JU_VC, JU_Y0 + 7.10, "VCC", 0.8, SILK, anchor="middle")
    # J4/J5 列默认中-下戴标准黄帽（2026-09-05 用户定：J4 实现为标准）——
    # 竖直跨中(JU_Y0+2.54)/下(JU_Y0+5.08)两针，GOLD 色，复用标准 jumper_cap
    for cx in (JU_J4, JU_J5):
        jumper_cap(cx, JU_Y0 + 2.54, cx, JU_Y0 + 5.08, GOLD)
    # J4/J5 编号竖排在 JU 大方框右侧：距框右缘 0.3mm；J5 中心对齐上两排(15.1/17.64)中心 16.37，
    #   J4 中心对齐下两排(17.64/20.18)中心 18.91（框右缘=JU_VC+1.27=51.11；文字右缘→锚=框右+0.3+0.21+0.28）
    txt(JU_VC + 1.27 + 0.79, JU_Y0 + 1.27, "J5", 0.8, SILK, anchor="middle", rot=-90)
    txt(JU_VC + 1.27 + 0.79, JU_Y0 + 3.81, "J4", 0.8, SILK, anchor="middle", rot=-90)

    # ---- 板上其它跳线（装饰，不接线）：2/3 针水平排焊盘 + 跳线帽/标注 ----
    # 蓝色跳线帽
    def hcap(x, y, w, h):
        L.append('  <rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="#4d7fe0" opacity="0.9"/>\n'
                 % (u(x), u(y), u(w), u(h), u(0.2)))
    # 需求 4：J3 —— 距左 12mm、顶 9mm 水平 2 针（无帽）。外接框左上角 (12,9)：
    #          最左焊盘中心 x=12+r、y=9+r，右焊盘 +2.54。
    #          白框 = 同 J8 的 5.4×2.9（中心=两针中点，无帽露出两焊盘，两跳线视觉统一）
    j3r = 0.66
    j3x0 = 12.0 + j3r
    j3y = 9.0 + j3r
    pin(j3x0, j3y); pin(j3x0 + 2.54, j3y)
    j3cx = j3x0 + 1.27                      # 两针中点
    # 用户 2026-09-05 定：J3/J8 方框尺寸 = 5.08×2.54（沿两针方向 2 格 2.54 宽、垂直 1 格 2.54 高，
    #   与 JU 单列(2.54)网格一致；框心=两针中点）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="5"/>\n'
             % (u(j3cx - 2.54), u(j3y - 1.27), u(5.08), u(2.54), SILK))
    # J3 竖排标签：文字左缘距框右缘 0.3mm。
    # 竖排 rot=-90 文字视觉中心比锚点偏左 ~0.21（baseline 不对称），故锚点 = 框右缘+0.3+0.21+半宽0.28
    txt(j3cx + 2.54 + 0.3 + 0.21 + 0.28, j3y, "J3", 0.8, SILK, anchor="middle", rot=-90)

    # 需求 5：J7 —— CON3 下方水平 3 针（SVCC 左侧 / VCC 右侧）；蓝帽跳右侧两针。
    #   2026-09-05 用户定：
    #   - 最左焊盘中心 x = 5.0（与 CON3 竖直焊盘列中心对齐），y 保持正下方 (j7y)；
    #   - 蓝帽改 J8 同款写实（塑料块+两端镂空透焊盘环+金属桥），跨右侧两针；
    #   - 加白框；SVCC 对准最左针、VCC 对准最右针（中心与焊盘中心对齐）
    # 2026-09-05 修正：J7 整体右移 0.5mm（用户定）
    j7r = 0.66
    j7x0 = 5.0 + 0.5               # 最左焊盘中心（原 x=5.0，右移 0.5）
    j7y = 55 - 20.0 - j7r          # 焊盘中心（底缘贴 y=35 → 34.34）
    for i in range(3):
        pin(j7x0 + i * 2.54, j7y)
    # 蓝帽（2026-09-05 用户定：按 J4 标准实现）——水平跨右两针(针2=j7x0+2.54、针3=j7x0+5.08)，
    #   蓝色 #4d7fe0，复用标准 jumper_cap（实心圆角塑料+两端银盘+深蓝孔+金属桥，无镂空）
    jumper_cap(j7x0 + 2.54, j7y, j7x0 + 5.08, j7y, "#4d7fe0")
    # 白框：包住三针 + 帽（同 JU 网格 2.54 比例 → 宽=3×2.54=7.62，高=2.54）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="5"/>\n'
             % (u(j7x0 - 1.27), u(j7y - 1.27), u(7.62), u(2.54), SILK))
    # J7 名称 + SVCC/VCC 标签（2026-09-05 修正版式）：
    # - J7 文字水平放在第二个焊盘(中针 j7x0+2.54)正上方，文字底边距框顶 0.3mm
    #   （框顶 = j7y-1.27 → 文字基线 = 框顶-0.3，锚 middle 于中针）
    # - SVCC 在框左侧、VCC 在框右侧，各距框 0.3mm（用 end/start 锚定，无半宽猜测）
    #   框左缘 = j7x0-1.27、右缘 = j7x0+6.35；文字垂直中心与焊盘行中心对齐
    #   （baseline 到视觉中心 ≈ -0.42 → 基线 = j7y+0.42）
    txt(j7x0 - 1.27 - 0.3, j7y + 0.42, "SVCC", 1.5, SILK, anchor="end")
    txt(j7x0 + 6.35 + 0.3, j7y + 0.42, "VCC", 1.5, SILK, anchor="start")
    # J7 文字基线 = 框顶 - 0.3 - J 字形下探量(~0.08) → 可见文字底边恰距框顶 0.3mm
    txt(j7x0 + 2.54, j7y - 1.27 - 0.3 - 0.08, "J7", 0.8, SILK, anchor="middle")

    # 需求 7：J8 —— 距底 25.8mm、右边 25.5mm 水平 2 针蓝帽；左针上 VCC、右针上 3V3；左侧竖排 J8
    #          组右缘=最右焊盘外缘距右 25.5 → 最右中心 x=70-25.5-r
    j8r = 0.66
    j8y = 55 - 25.8 - j8r       # 焊盘中心（底缘贴 y=29.2）
    j8x1 = 70 - 25.5 - j8r      # 最右焊盘中心（外缘贴 x=44.5）
    j8x0 = j8x1 - 2.54          # 最左焊盘中心
    pin(j8x0, j8y); pin(j8x1, j8y)
    # 蓝帽 = 真实 4.8×2.3mm 塑料短路帽（用户手工实测 2026-09-05），长边沿两针方向；
    #       中心 = 两针中点；2026-09-05 用户定：按 J4 标准实现（实心圆角塑料+两端银盘+
    #       深蓝孔+金属桥，去掉之前 evenodd 镂空「焊盘还原」），复用标准 jumper_cap
    j8cx = (j8x0 + j8x1) / 2.0
    jumper_cap(j8x0, j8y, j8x1, j8y, "#4d7fe0")
    # 白色直角外框：用户 2026-09-05 定 J3/J8 同款 5.08×2.54（两针方向 2 格 2.54、垂直 1 格 2.54）
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="5"/>\n'
             % (u(j8cx - 2.54), u(j8y - 1.27), u(5.08), u(2.54), SILK))
    # 针名丝印在框上方（基线距框顶 0.25，同 CON2）
    txt(j8x0, j8y - 1.27 - 0.25, "VCC", 0.8, SILK, anchor="middle")
    txt(j8x1, j8y - 1.27 - 0.25, "3V3", 0.8, SILK, anchor="middle")
    # J8 竖排标签：文字右缘距框左缘 0.3mm（锚点=框左缘-0.3-半字宽 0.28）
    txt(j8cx - 2.54 - 0.3 - 0.28, j8y, "J8", 0.8, SILK, anchor="middle", rot=-90)

    # 需求 6：J2 —— DEBUG-PORT(JST XH4A, x40.4..52.7, y0..5.75) 框外左上水平标 J2；
    #          文字右缘距白块左缘(DL=40.4) 0.3mm → 锚点=40.4-0.3-半宽0.355=39.745
    txt(39.745, 1.2, "J2", 0.8, SILK, anchor="middle")

    # 需求 1：USB —— 右侧 USB-A 接口(竖贴右缘,壳 x67.5.. y14..26) 左侧加竖排 USB，U 在下，字号同 UART(1.5)
    txt(64.6, 20.0, "USB", 1.5, SILK_D, anchor="middle", rot=-90)

    # ---- 板号丝印：TAIXIN…（V1.7，字号 1.8，对齐插座左缘） ----
    txt(40.4, 9.6, "TAIXIN-AH-RX00P_EVB_V1.7", 1.8, SILK_D)

    # ---- CH340E USB-UART 芯片（MSOP-10，复用 CH340E icon 1:1，无旋转）----
    # 用户指定：含引脚外廓右缘距主板右边 6.5mm、下缘距主板底边 16mm
    # （主板 70×55mm）。外廓 = 中心 ±(1.5,2.5) → 中心 (70-6.5-1.5, 55-16-2.5)
    # = (62.0, 36.5)mm。
    ch340e = _ch340e_icon_group()
    CHX, CHY = 62.0, 36.5
    L.append('  <g transform="translate(%d %d) scale(39.37)">\n' % (u(CHX), u(CHY)))
    L.append(ch340e)
    L.append('  </g>\n')

    # ---- 两颗 ETA3425S2F 同步降压（SOT23-5，复用 ETA3425S2F icon 1:1）----
    # icon 内容外廓（mm，中心原点）：体 3.0×1.6、引脚到 y±1.4 → 外廓 x±1.5/y±1.4；
    # pin1 脚默认左下（焊盘圆点在左下）。
    eta = _eta3425s2f_icon_group()
    # #1 竖放（长轴竖直）、1脚左上：rotate(90) 顺时针 → 外廓变 x±1.4/y±1.5；
    #    外廓右缘距板右 17.6 → cx=70-17.6-1.4=51.0；外廓下缘距板底 22 → cy=55-22-1.5=31.5
    L.append('  <g transform="translate(%d %d) rotate(90) scale(39.37)">\n' % (u(51.0), u(31.5)))
    L.append(eta)
    L.append('  </g>\n')
    # #2 横放、1脚右上：rotate(180) → pin1 左下→右上；外廓仍 x±1.5/y±1.4；
    #    外廓左缘距板左 36.3 → cx=36.3+1.5=37.8；外廓下缘距板底 16.6 → cy=55-16.6-1.4=37.0
    L.append('  <g transform="translate(%d %d) rotate(180) scale(39.37)">\n' % (u(37.8), u(37.0)))
    L.append(eta)
    L.append('  </g>\n')

    # ---- XC6206P332MR 3.3V LDO（SOT23-3，复用 XC6206P332MR icon 1:1，无旋转）----
    # 用户指定：含引脚外廓右缘距主板右边 11mm、下缘距主板底边 23mm（主板 70×55mm）。
    # icon 内容外廓 = 中心 ±(1.45,1.4)（x 以本体 2.9/2=1.45 为界、y 含上/下伸出脚 ±1.4）
    # → 中心 (70-11-1.45, 55-23-1.4) = (57.55, 30.6)mm。
    xc = _xc6206_icon_group()
    XCX, XCY = 57.55, 30.6
    L.append('  <g transform="translate(%d %d) scale(39.37)">\n' % (u(XCX), u(XCY)))
    L.append(xc)
    L.append('  </g>\n')

    # ---- 板上芯片统一编号（U2..U7；U1=模组已标于模组右侧；U4 用户定跳过）----
    # 用户 2026-09-05：编号统一字号 0.8（与 CON1 一致）、白色（SILK）。
    # 放置规则（2026-09-05 定）：
    #   U2 = W25Q16JV 正上方（芯片中心 14.24,4.44 转90°，上沿≈1.86 → 基线 1.3）
    #   U3 = ETA#1（竖放 51.0,31.5，右缘 52.4）右侧竖排贴右缘 0.25、中线对芯片竖直中心 y=31.5
    #   U5 = CH340E（62.0,36.5，右缘 63.5）右侧竖排贴右缘 0.25、中线对芯片竖直中心 y=36.5
    #   U6 = ETA#2（横放 37.8,37.0，右缘 39.3/底缘 38.4）右侧贴右 0.25、底线对芯片底缘 y=38.4
    #   U7 = XC6206（57.55,30.6，左缘 56.1/底缘 32.0）左侧贴左 0.25、底线对芯片底缘 y=32.0
    # 竖排=rot(-90)（U 在下、由下往上读，同 CON1/U1 风格）；水平标签底线即 baseline（无 descender）。
    txt(14.24, 1.3, "U2", 0.8, SILK, anchor="middle")
    txt(53.185, 31.5, "U3", 0.8, SILK, anchor="middle", rot=-90)
    txt(64.238, 36.5, "U5", 0.8, SILK, anchor="middle", rot=-90)
    txt(39.51, 38.4, "U6", 0.8, SILK, anchor="start")
    txt(55.85, 32.0, "U7", 0.8, SILK, anchor="end")
    # ---- DPDT7x7-6P 电源自锁开关（用户 2026-09-06：距右边沿 15.8mm、距底边沿 7mm、不旋转）----
    # 本体右缘 x=70-15.8=54.2 → 左缘 47.2；底缘 y=55-7=48 → 上缘 41；复用其 icon <g id="icon"> 1:1 顶视
    dpdt = _inner_g_icon(os.path.normpath(os.path.join(
        OUT_DIR, "..", "DPDT7x7-6P", "svg.icon.DPDT7x7-6P_icon.svg"))).strip("\n")
    L.append('  <g transform="translate(%d %d) scale(39.37)">\n' % (u(47.2), u(41.0)))
    L.append(dpdt)
    L.append('  </g>\n')
    # S1 丝印：按钮左侧 end 锚。2026-09-06 用户定：整体上移 0.5mm、右移 0.6mm
    # （x 46.7→47.3、y 48.0→47.5）
    txt(47.3, 47.5, "S1", 0.8, SILK, anchor="end")
    L.append('  </g>\n')               # 结束 translate(TF_OVER)

    # ---- 左侧 MicroSD 卡板 v6（最后画=压最上层）：黑主板外伸"舌头" + 端部银灰 microSD 卡 ----
    # 按用户 microsd.png（透明底、15×11mm）像素测量 1:1 还原卡形：
    #   卡 15.0×11.0mm；上边一个缺口（距自由端 7.84~9.6mm、深 0.64mm，右斜 45°左陡）；
    #   自由端上角 microSD 防呆切（上边 x0.5~4.7 下凹 1.24mm，x4.7~6.0 斜接回 17.3）。
    EC_LEN = 15.0                     # 卡长 = 标准 microSD 15mm
    NECK = TF_OVER - EC_LEN           # 黑色脖子的水平长度（mm）
    FL = 3.0                          # 脖子在主板侧向上/下张开的量（mm）
    TF_FILL, TF_EDGE = "#d4d7da", "#9aa0a6"   # 银灰边缘连接器
    yT, yB = TF_TOP, TF_TOP + TF_H
    xS = EC_LEN                       # 脖子短边 x（贴边缘连接器，= 卡宽 11mm）
    # 1) 黑色脖子：直舌头（卡宽 11mm）在左、主板在右；上/下两肩各一个**内凹圆角**
    #    （quarter-arc，sweep=0），圆弧两端分别与舌头边、主板左缘相切 → 平滑内凹。
    r = min(FL, TF_OVER - EC_LEN)     # 内凹圆角半径（mm），不超过脖子长度
    xB = TF_OVER                       # 主板左缘 x（圆角相切于此）
    d_neck = ("M %d,%d L %d,%d A %d,%d 0 0 0 %d,%d L %d,%d A %d,%d 0 0 0 %d,%d L %d,%d Z"
              % (u(xS), u(yT), u(xB - r), u(yT), u(r), u(r), u(xB), u(yT - r),
                 u(xB), u(yB + r), u(r), u(r), u(xB - r), u(yB), u(xS), u(yB)))
    L.append('  <path d="%s" fill="%s"/>\n' % (d_neck, PCB))
    # 2) 银灰 microSD 卡（缺口 + 防呆切 + 自由端圆角），压在脖子短边上（微重叠防缝）
    xR = EC_LEN + 0.2                 # 卡根端 x（压上脖子）
    rc = 0.5                          # 自由端下角圆角（mm）
    # 防呆切（自由端上角）：上边下凹 1.24mm
    BV_X0, BV_X1 = 0.5, 4.7           # 凹平段 x 范围
    BV_Y = yT + 1.24                  # 凹平段 y（18.54）
    CH_X = 6.0                        # 斜接回上边的 x
    # 缺口（上边）：开口 7.84~9.6、深 0.64；右斜 45°、左陡
    NX0, NX1 = 7.84, 8.03             # 左陡边（朝自由端）
    NX2, NX3 = 8.96, 9.60             # 右 45° 边（朝脖子）
    ND = 0.64
    d_ec = ("M %d,%d "
            "L %d,%d L %d,%d L %d,%d "
            "L %d,%d L %d,%d L %d,%d L %d,%d "
            "L %d,%d L %d,%d L %d,%d "
            "A %d,%d 0 0 1 %d,%d L %d,%d Z"
            % (u(0), u(18.88),                       # 自由端上角
               u(BV_X0), u(BV_Y), u(BV_X1), u(BV_Y), u(CH_X), u(yT),   # 防呆切
               u(NX0), u(yT), u(NX1), u(yT + ND), u(NX2), u(yT + ND), u(NX3), u(yT),  # 缺口
               u(xR), u(yT), u(xR), u(yB), u(rc), u(yB),             # 顶/右/底边
               u(rc), u(rc), u(0), u(yB - rc),                       # 自由端下圆角
               u(0), u(18.88)))                                      # 左缘回起点
    L.append('  <path d="%s" fill="%s" stroke="%s" stroke-width="7"/>\n' % (d_ec, TF_FILL, TF_EDGE))
    # 注：脖子上下两条圆弧不再加黑色实线描边（用户：箭头处不应有黑实线），
    # 仅靠填充色边界呈现，弧线自然清晰即可。
    # ---- 过孔阵列（用户 2026-09-06）：银灰 microSD 卡靠右部分打 6行x8列=48 个过孔，
    #      孔径 0.2mm（半径 0.1）；左边为卡接口留空（x<6mm 不打孔），避开防呆切/缺口；
    #      行距 1.2mm＝列距（均匀网格）；整体下移半个行距(0.6mm)与左端对中 ----
    VIA_R = 0.1                         # 过孔半径（mm）＝0.2mm 孔径
    for ry in (20.4, 21.6, 22.8, 24.0, 25.2, 26.4):      # 6 行，间距 1.2mm
        for cx in (6.0, 7.2, 8.4, 9.6, 10.8, 12.0, 13.2, 14.4):   # 8 列，间距 1.2mm
            L.append('  <circle cx="%d" cy="%d" r="%d" fill="#0a0d11"/>\n'
                     % (u(cx), u(ry), u(VIA_R)))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def main():
    files = {BB_SVG: breadboard_svg(), ICON_SVG: icon_svg(), SCHEM_SVG: schematic_svg(), PCB_SVG: pcb_svg()}
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)

    fzp_name = f"part.{PART_ID}.fzp"
    with open(os.path.join(OUT_DIR, fzp_name), "w", encoding="utf-8") as f:
        f.write(gen_fzp())
    print("wrote", fzp_name)

    # .fzpz 内部平铺（repo 约定），image= 仍用子目录路径
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(OUT_DIR, fzp_name), arcname=fzp_name)
        for name in (ICON_SVG, SCHEM_SVG, PCB_SVG, BB_SVG):
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
