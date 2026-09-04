#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 RT6150AGQW (rev.1, Richtek WDFN-10L 3x3 Buck-Boost DC/DC)。

这是 RT6150AGQW 的修订版（写实工业风）：moduleId=RT6150AGQW_rev_1，与 svg/RT6150AGQW/ 旧 hash 版并存。
芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
数据来源：D:\\Downloads\\RT6150AGQW.pdf（DS6150A/B-05, W-Type 10L DFN 3x3, D=E=3.0, e=0.5, b≈0.24, L≈0.4, EP≈2.4×1.6）。
引脚（顶视逆时针 1→10）：
  1 VOUT  2 LX2  3 GND  4 LX1  5 VIN  6 EN  7 PS  8 VINA  9 GND  10 FB
  物理排布：左列 1-5 上→下 / 右列 10-6 上→下（pcb 验证布局一致）；EP(connector10) 散热焊盘。
  EP 命名=EP（独立网络，需手动接 GND）；原理图按库内惯例画成右侧第 11 脚（FB10 上方）；
  pcb 本体框丝印只画上/下两条横线（WDFN 焊盘在左右两侧，竖线会压盘）。
用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "RT6150AGQW_rev_1"
FZPZ = "RT6150AGQW_rev_1.fzpz"

# 引脚定义（connector0..9 = pin1..10；EP=connector10）
PINS = [
    "VOUT",   # 1
    "LX2",    # 2
    "GND",    # 3
    "LX1",    # 4
    "VIN",    # 5
    "EN",     # 6
    "PS",     # 7
    "VINA",   # 8
    "GND",    # 9
    "FB",     # 10
]
EP_NAME = "EP"      # connector10 = EP 散热焊盘（独立网络，使用时接 GND）

ICON_LABEL = "RT6150"
SCHEM_LABEL = "RT6150AGQW"
PACKAGE = "WDFN-10L 3x3"
TITLE = "RT6150AGQW Current Mode Buck-Boost DC/DC (rev.1)"
LABEL = "U"
FAMILY = "Richtek Buck-Boost DC/DC"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- RT6150AGQW rev.1 WDFN-10L 3x3 (Buck-Boost DC/DC) -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装符号（10 信号脚 + EP）。按 AGENTS.md §5 矩形规则：
    左列 1-5 上→下（整体下移一行，使 VIN(5) 与右列 EN(6) 平齐）；
    右列 EP(11) 在上、10-6 其下（右列共 6 根，EP 在 FB10 上方）。
    EP 按库内惯例作为普通编号引脚：connectorname=EP、编号 11；名/数字/引线同色黑，字号 FN=35。"""
    P = 100
    WIRE = 130
    FN = 35
    CH = 35
    BASELINE_OFF = round(FN * 0.35)
    max_len = max([len(n) for n in PINS] + [len(EP_NAME)])   # 4 (VOUT/VINA/...)
    CORNER = (max_len + 1) * int(FN * 0.58)      # 5*20 = 100
    per = len(PINS) // 2                         # 左列 5
    perR = per + 1                               # 右列 6（含 EP）
    BX0, BY0 = 340, 200
    BW = 720
    BH = perR * P + 2 * CORNER                   # 6*100+200 = 800
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - 5
    VBW = BW + 2 * WIRE + 10
    VBH = BH + 10
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" height="{VBH / 1000:.6f}in" '
             f'viewBox="{VBX} {VBY} {VBW} {VBH}">\n')
    L.append(' <g id="schematic">\n')
    L.append(f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
             f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n')
    # 左列 pin1-5 (connector0..4) 上→下；整体下移 1 行（i+1）使 VIN 与右列 EN 平齐
    for i in range(per):
        y = BY0 + CORNER + P // 2 + (i + 1) * P
        cn = i
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 右列：EP(11) 最上，然后 connector9..5 (10..6)
    right_ids = [10] + [per * 2 - 1 - i for i in range(per)]   # [10,9,8,7,6,5]
    right_nums = [11] + [per * 2 - i for i in range(per)]       # [11,10,9,8,7,6]
    for i, cn in enumerate(right_ids):
        y = BY0 + CORNER + P // 2 + i * P
        name = EP_NAME if cn == 10 else PINS[cn]
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(name)}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{right_nums[i]}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="end" '
                 f'font-family="DroidSans">{esc(name)}</text>\n')
    CHIP_FS = 79
    CHIP_Y = BY0 + BH // 2 + round(CHIP_FS * 0.35)
    L.append(f'  <text x="{BX0 + BW // 2}" y="{CHIP_Y}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(SCHEM_LABEL)}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def _embed_icon(art, cx, cy, s=1.0, icx=0.0, icy=0.0):
    m = re.search(r'<g\s+id="icon"([^>]*)>(.*?)</g>', art, re.S)
    if not m:
        return ""
    gattrs, content = m.group(1), m.group(2)
    tm = re.search(r'translate\(([^)]+)\)', gattrs)
    tx = ty = 0.0
    if tm:
        vals = re.split(r'[,\s]+', tm.group(1).strip())
        tx, ty = float(vals[0]), float(vals[1] if len(vals) > 1 else 0)
    out = []
    for rm in re.finditer(r'<rect\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', rm.group(1)))
        px = (float(a.get("x", 0.0)) + tx - icx) * s + cx
        py = (float(a.get("y", 0.0)) + ty - icy) * s + cy
        out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["width"]) * s, float(a["height"]) * s,
            a.get("fill", "#f7bf13"), a.get("stroke", "none")))
    for cm in re.finditer(r'<circle\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        px = (float(a["cx"]) + tx - icx) * s + cx
        py = (float(a["cy"]) + ty - icy) * s + cy
        out.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["r"]) * s, a.get("fill", "#c0c0c0"), a.get("stroke", "none")))
    for tm2 in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', content, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tm2.group(1)))
        px = (float(a.get("x", 0.0)) + tx - icx) * s + cx
        py = (float(a.get("y", 0.0)) + ty - icy) * s + cy
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans">%s</text>\n'
                   % (px, py, fs, a.get("fill", "#333333"), tm2.group(2)))
    return "".join(out)


def gen_breadboard_svg():
    """面包板 = 绿色 WDFN-10 转接板。真实封装引脚在左/右两侧（左列 pin1-5 上→下 / 右列 pin6-10 下→上），
    故排针也分左右两列竖排（每列 5 针，2.54mm 网格），EP 单独一根排针(GND)置于底部中央。
    坐标 100 单位 = 2.54mm。左列 x=100 (pin1-5, y 100..500)；右列 x=600 (pin10-6, y 100..500)；
    芯片 icon 1:1 居中 (350,350)；EP 排针 x=400,y=600。板 700×700 单位 (17.78mm)。"""
    U = 39.37
    per = len(PINS) // 2
    yp = [100 + i * 100 for i in range(per)]       # 100..500
    xl, xr = 100, 600
    cx, cy = 350, 350
    pad_r = 1.0 * U
    hole_r = 0.485 * U
    icon = gen_icon_svg()
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    art = _m.group(1) if _m else ""
    _vm = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', icon)
    icx = icy = 0.0
    if _vm:
        vx, vy, vw, vh = map(float, _vm.groups())
        icx, icy = vx + vw / 2, vy + vh / 2
    bx0, bx1, by0, by1 = 0, 700, 0, 700
    bw, bh = bx1 - bx0, by1 - by0
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" height="{bh / 100 * 2.54:.2f}mm" '
             f'viewBox="{bx0} {by0} {bw} {bh}">\n')
    s.append(' <g id="breadboard">\n')
    s.append(f'  <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    s.append(_embed_icon(art, cx, cy, s=U, icx=icx, icy=icy))
    # 左列 pin1-5 (connector0..4) 上→下
    for i in range(per):
        x, y = xl, yp[i]
        cn = i
        s.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'cx="{x:.1f}" cy="{y:.1f}" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        s.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
        s.append(f'  <text x="{x + 62}" y="{y:.1f}" font-size="45" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans">{i + 1}</text>\n')
    # 右列 pin10-6 (connector9..5) 上→下
    for i in range(per):
        x, y = xr, yp[i]
        cn = per * 2 - 1 - i
        s.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'cx="{x:.1f}" cy="{y:.1f}" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        s.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
        s.append(f'  <text x="{x - 62}" y="{y:.1f}" font-size="45" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans">{per * 2 - i}</text>\n')
    # EP 排针 (connector10) 底部中央
    ex, ey = 400, 600
    s.append(f'  <circle id="connector10pin" connectorname="{esc(EP_NAME)}" '
             f'cx="{ex:.1f}" cy="{ey:.1f}" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
    s.append(f'  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    s.append(f'  <text x="{ex:.1f}" y="{ey - 70}" font-size="42" fill="#ffffff" text-anchor="middle" '
             f'dominant-baseline="central" font-family="DroidSans">EP</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图：真实 WDFN-10L 3x3 封装，居中对称。
    WDFN-10L 3x3 (D=E=3.0, e=0.5)：10 焊盘分左右两列竖排（左列 pin1-5 上→下，
    右列 pin10-6 上→下，本体两侧；VOUT/pin1 左上、FB/pin10 右上），
    中央 EP(connector10) 大焊盘 1.625×2.475。
    焊盘 0.65×0.28、列中心 x=±1.5（左右列中心间距 3mm）。
    丝印：本体 3×3 只画上/下两条横线（WDFN 焊盘在左右两侧，不画左右竖线以免压盘）
    + pin1 白色圆点放在 1 脚(VOUT)焊盘左侧、与焊盘同高、间隙 0.15mm。"""
    pw, pl = 0.65, 0.28
    pitch = 0.5
    per = len(PINS) // 2                        # 5
    xcol = 1.5                                  # 左右列中心 x（间距 3mm）
    # 焊盘中心 y（上→下 -1.0..1.0；connector0/pin1 VOUT 在左上）
    def yc(i):
        return -1.0 + i * pitch
    pads = []
    for i in range(per):                        # 左列 pin1-5 (connector0..4) 上→下
        cn = i
        pads.append(f'<rect id="connector{cn}pad" x="{-xcol - pw / 2:.3f}" y="{yc(i) - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    for i in range(per):                        # 右列 pin10-6 (connector9..5) 上→下
        cn = per * 2 - 1 - i
        pads.append(f'<rect id="connector{cn}pad" x="{xcol - pw / 2:.3f}" y="{yc(i) - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # EP 中心焊盘（露铜 1.625×2.475 居中）
    pads.append(f'<rect id="connector10pad" x="-0.8125" y="-1.2375" width="1.625" height="2.475" '
                f'fill="#F7BD13" stroke="none" connectorname="{esc(EP_NAME)}"/>')
    # 丝印：只画上/下两条横线（本体 y=±1.5，避开左右焊盘列）
    silk = []
    silk.append('<line x1="-1.5" y1="-1.5" x2="1.5" y2="-1.5" stroke="#f0f0f0" stroke-width="0.12"/>')
    silk.append('<line x1="-1.5" y1="1.5" x2="1.5" y2="1.5" stroke="#f0f0f0" stroke-width="0.12"/>')
    # pin1 圆：VOUT(connector0, 左列最上 y=-1.0) 焊盘左侧，同 y，圆右缘距焊盘左缘 0.15mm
    pr = 0.25                                   # 圆半径（直径 0.5mm）
    p1cx = -xcol - pw / 2 - 0.15 - pr           # 焊盘左缘 -1.825 -0.15 -0.25 = -2.225
    p1cy = yc(0)                                # -1.0
    silk.append(f'<circle cx="{p1cx:.3f}" cy="{p1cy:.3f}" r="{pr:.3f}" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    # 裁边：x 左含 pin1 圆 -2.275，右焊盘外缘 xcol+pw/2=1.825；y 上下含丝印横线 ±1.5 与 EP ±1.2375
    M = 0.18
    vb_x0 = min(-xcol - pw / 2, p1cx - pr) - M
    vb_x1 = xcol + pw / 2 + M
    vb_y0 = min(-1.5, -1.2375, p1cy - pr) - M
    vb_y1 = max(1.5, 1.2375, p1cy + pr) + M
    vw, vh = vb_x1 - vb_x0, vb_y1 - vb_y0
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
            f'viewBox="{vb_x0:.2f} {vb_y0:.2f} {vw:.2f} {vh:.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """WDFN-10L 3x3 芯片图标（顶视图，写实工业风）：
    本体 3.0×3.0 直角深灰 #303030 盖住焊盘内侧；金焊盘 #f7bf13 左右各 5（0.5 间距，只露外侧金边）；
    pin1 圆点左上银色；两行丝印 RT6150 / AGQW。"""
    e, padw, padh = 0.5, 0.24, 0.28
    xs = [(-1.0 + i * e) for i in range(5)]        # -1.0..1.0
    parts = [SVG_HDR,
             '<svg xmlns="http://www.w3.org/2000/svg" width="3.3mm" height="3.3mm" '
             'viewBox="-1.65 -1.65 3.3 3.3">\n'
             '  <g id="icon">\n']
    # 焊盘先画（被本体盖住内侧，只露外侧金边 0.12）
    for y in xs:
        parts.append(f'    <rect x="{-1.62:.2f}" y="{y - padh / 2:.2f}" width="{padw:.2f}" height="{padh:.2f}" '
                     f'fill="#f7bf13" stroke="none"/>\n')
        parts.append(f'    <rect x="{1.38:.2f}" y="{y - padh / 2:.2f}" width="{padw:.2f}" height="{padh:.2f}" '
                     f'fill="#f7bf13" stroke="none"/>\n')
    parts.append('    <rect x="-1.5" y="-1.5" width="3.0" height="3.0" fill="#303030" stroke="none"/>\n')
    parts.append('    <circle cx="-1.0" cy="-1.0" r="0.13" fill="#c0c0c0" stroke="none"/>\n')
    parts.append('    <text x="0" y="-0.10" font-size="0.42" fill="#c0c0c0" text-anchor="middle" '
                 'font-family="DroidSans">RT6150</text>\n')
    parts.append('    <text x="0" y="0.30" font-size="0.34" fill="#c0c0c0" text-anchor="middle" '
                 'font-family="DroidSans">AGQW</text>\n')
    parts.append('  </g>\n</svg>\n')
    return "".join(parts)


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for i, name in enumerate(PINS):
        conns.append(
            f'  <connector id="connector{i}" name="{esc(name)}" type="male">\n'
            f'   <description>{esc(name)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{i}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{i}pin" terminalId="connector{i}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{i}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    # connector10 = EP
    conns.append(
        f'  <connector id="connector10" name="{esc(EP_NAME)}" type="pad">\n'
        f'   <description>{esc(EP_NAME)} (exposed thermal pad, connect to GND)</description>\n'
        f'   <views>\n'
        f'    <breadboardView>\n     <p layer="breadboard" svgId="connector10pin"/>\n    </breadboardView>\n'
        f'    <schematicView>\n     <p layer="schematic" svgId="connector10pin" terminalId="connector10terminal"/>\n    </schematicView>\n'
        f'    <pcbView>\n     <p layer="copper1" svgId="connector10pad"/>\n    </pcbView>\n'
        f'   </views>\n'
        f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>4</version>\n <date>2026-09-04</date>\n'
            f' <label>{LABEL}</label>\n <author>fritzing-parts-langhua</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>{LABEL}</tag>\n  <tag>{PACKAGE}</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="part number">{PART_ID}</property>\n </properties>\n'
            f' <views>\n  <breadboardView>\n   <layers image="breadboard/{PART_ID}_breadboard.svg">\n'
            f'    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            f'  <schematicView>\n   <layers image="schematic/{PART_ID}_schematic.svg">\n'
            f'    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
            f'  <pcbView>\n   <layers image="pcb/{PART_ID}_pcb.svg">\n'
            f'    <layer layerId="copper1"/>\n    <layer layerId="silkscreen"/>\n   </layers>\n  </pcbView>\n'
            f'  <iconView>\n   <layers image="icon/{PART_ID}_icon.svg">\n'
            f'    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n </views>\n'
            f' <connectors>\n' + "\n".join(conns) + '\n </connectors>\n</module>\n')


# -------------------------------------------------------------------- 打包
def main():
    files = {
        "icon": gen_icon_svg(),
        "schematic": gen_schematic_svg(),
        "breadboard": gen_breadboard_svg(),
        "pcb": gen_pcb_svg(),
    }
    for view in ("icon", "schematic", "breadboard", "pcb"):
        content = files[view]
        name = f"svg.{view}.{PART_ID}_{view}.svg"
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    fzp_name = f"part.{PART_ID}.fzp"
    with open(os.path.join(OUT_DIR, fzp_name), "w", encoding="utf-8") as f:
        f.write(gen_fzp())
    print("wrote", fzp_name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(OUT_DIR, fzp_name), arcname=fzp_name)
        for view in ("icon", "schematic", "breadboard", "pcb"):
            name = f"svg.{view}.{PART_ID}_{view}.svg"
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
