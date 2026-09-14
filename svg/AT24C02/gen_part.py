#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — 生成 Fritzing 自定义元件 AT24C02 (I2C 串行 EEPROM 2Kb, SOP-8)。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件（part.<id>.fzp + 4 个 svg.<view>.* + 本脚本）同目录，.fzpz 输出到仓库顶层 fzpz/。
打包规则（docs/part-dev-guide.md §2.2）：.fzpz 内部平铺，.fzp 的 image= 用子目录路径。

数据来源：`D:\Downloads\AT24C02.pdf`（英锐芯 AT24C02 手册）
  - 封装 **SOP-8**（手册第 12 页封装图）：本体 A/E = 3.80–4.00 × D = 4.95–5.15mm，
    引脚节距 e = **1.27mm**，脚宽 b = 0.37–0.47mm，跨距（含脚） 5.80–6.20mm。
  - 引脚（顶视、pin1 左下、逆时针 1→8）：1=A0 2=A1 3=A2 4=GND 5=SDA 6=SCL 7=WP 8=VCC。
  - 顶面丝印：24C02（本元件用 24C02 作为 icon 上的 marking）。

进度：
  [x] 1. icon（SOP-8 顶视图）
  [ ] 2. breadboard（绿色 SOP-8 转接板 + 8 排针）
  [ ] 3. schematic（矩形 8 脚符号）
  [ ] 4. pcb（SOP-8 150mil 焊盘）
  [ ] 5. part.AT24C02.fzp + 打包 fzpz

用法：
  python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "AT24C02"
FZPZ = "AT24C02.fzpz"

# 引脚定义（SOP-8：下排 1-4 左→右、上排 8-5 左→右；pin1=A0 左下）
PINS = [
    "A0",   # 1
    "A1",   # 2
    "A2",   # 3
    "GND",  # 4
    "SDA",  # 5
    "SCL",  # 6
    "WP",   # 7
    "VCC",  # 8
]

# 顶面丝印 / 原理图里的器件名
ICON_LABEL = "24C02"
SCHEM_LABEL = "AT24C02"

# .fzp 元数据
TITLE = "AT24C02 I2C Serial EEPROM 2Kb"
LABEL = "U"
PACKAGE = "SOP-8"
FAMILY = "I2C EEPROM"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- AT24C02 I2C EEPROM -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装符号（SOIC-8，左右各 4 脚）。按 AGENTS.md §5 矩形原理图规则：
    1. 左右引脚数字在引线上方（不与线相交）：左 1-4 上→下、右 8-5 上→下。
    2. 引脚名在框内、书写方向同数字、与引脚水平中线对齐（手动基线偏移，不用
       dominant-baseline）；名/数字/引线同色（黑）。
    3. 数字与引脚名整图同字号 FN=35。
    4. 引脚名与边框保持一个字符 CH=FN 间距，居左/右。
    5. 四角无引脚区 CORNER=(最长名宽+1)×int(FN×0.58)，引脚从 CORNER 后开始排，
       框 = 4P + 2×CORNER（完全对称）。
    物理尺寸 width/height(in)，1000 单位 = 1in；viewBox 贴合内容（裁边）。"""
    P = 100                       # 引脚间距（2.54mm）
    WIRE = 130                    # 引脚线长
    CH = 35                       # 一个字符间距（= 字号）
    FN = 35                       # 整图统一字号（数字与引脚名）
    BASELINE_OFF = round(FN * 0.35)   # 手动垂直居中基线偏移
    max_len = max(len(n) for n in PINS)        # 11（/HOLD (IO3)）
    CORNER = (max_len + 1) * int(FN * 0.58)    # 四角无引脚宽度
    per = len(PINS) // 2                      # 4
    BX0, BY0 = 340, 200
    BW = 800                                  # 框宽
    BH = per * P + 2 * CORNER                 # 框高
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - 5        # viewBox 左上（贴合内容）
    VBW, VBH = BW + 2 * WIRE + 10, BH + 10    # viewBox 宽高
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" height="{VBH / 1000:.6f}in" '
             f'viewBox="{VBX} {VBY} {VBW} {VBH}">\n')
    L.append(' <g id="schematic">\n')
    # 封装体（白底灰边）
    L.append(f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
             f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n')
    # 左 1-4（上→下）：数字在引线上方，名在框内靠左
    for i in range(per):
        y = BY0 + CORNER + P // 2 + i * P
        cn = i
        col = "#000000"
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{col}" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 右 8-5（上→下）：数字在引线上方，名在框内靠右
    for i in range(per):
        y = BY0 + CORNER + P // 2 + i * P
        cn = per * 2 - 1 - i          # 顶部 connector7(pin8) → 底部 connector4(pin5)
        col = "#000000"
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans">{per * 2 - i}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{col}" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 芯片名（框内居中）
    CHIP_FS = 79
    CHIP_Y = BY0 + BH // 2 + round(CHIP_FS * 0.35)
    L.append(f'  <text x="{BX0 + BW // 2}" y="{CHIP_Y}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(SCHEM_LABEL)}</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def _embed_icon(art, cx, cy, s=1.0, icx=0.0, icy=0.0, text_dy=0.0):
    """把 icon 组内容（mm）放大 s，使 icon 视觉中心 (icx,icy) 映射到 (cx,cy)。
    不旋转（保持 icon 方向：pin1 左下）。烘焙绝对坐标（处理 rect/circle/text）。"""
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
        attrs = '  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"' % (
            px, py, float(a["width"]) * s, float(a["height"]) * s)
        attrs += ' fill="%s" stroke="%s"' % (a.get("fill", "#f7bf13"), a.get("stroke", "none"))
        if float(a.get("stroke-width", 0)) > 0:
            attrs += ' stroke-width="%.2f"' % (float(a["stroke-width"]) * s)
        out.append(attrs + '/>\n')
    for cm in re.finditer(r'<circle\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        px = (float(a["cx"]) + tx - icx) * s + cx
        py = (float(a["cy"]) + ty - icy) * s + cy
        out.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["r"]) * s,
            a.get("fill", "#c0c0c0"), a.get("stroke", "none")))
    for tm2 in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', content, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tm2.group(1)))
        px = (float(a.get("x", 0.0)) + tx - icx) * s + cx
        py = (float(a.get("y", 0.0)) + ty - icy) * s + cy + text_dy
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans">%s</text>\n'
                   % (px, py, fs, a.get("fill", "#333333"), tm2.group(2)))
    return "".join(out)


def gen_breadboard_svg():
    """面包板 = 绿色 SOP-8 转接板 + 8 排针（上下各 4）+ 居中 AT24C02 icon（1:1，pin1 左下）。
    坐标 100 单位 = 2.54mm，排针中心落在 100 整数倍 → 对准面包板孔。
    排针行距 400 单位（10.16mm）≥ 芯片总高 6.0mm + 2mm；绿板对称包住焊盘，边距 20。
    （比 W25Q16JV 那张矮 100 单位：它的芯片总高 7.9mm 才需要 500。）"""
    U = 39.37
    per = len(PINS) // 2                      # 4
    x_pins = [100 + i * 100 for i in range(per)]
    y_top, y_bot = 100, 500                   # 上排（pin8-5）、下排（pin1-4）
    cx, cy = 250, 300                         # 芯片中心
    pad_r = 1.0 * U                           # 2mm 直径焊盘 → 半径 1mm
    hole_r = 0.485 * U                        # 0.97mm 直径针孔
    icon = gen_icon_svg()
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    art = _m.group(1) if _m else ""
    _vm = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', icon)
    icx = icy = 0.0
    if _vm:
        vx, vy, vw, vh = map(float, _vm.groups())
        icx, icy = vx + vw / 2, vy + vh / 2
    # 绿板：包住排针焊盘 + 100 边距（与 CH340C 同约定，焊盘 r=39.37 不被裁切）
    bx0, bx1 = 0, 500
    by0, by1 = 0, 600
    bw, bh = bx1 - bx0, by1 - by0
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" height="{bh / 100 * 2.54:.2f}mm" '
             f'viewBox="{bx0} {by0} {bw} {bh}">\n')
    s.append(' <g id="breadboard">\n')
    # 绿色转接板（直角）
    s.append(f'  <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    # 芯片 icon（1:1 居中）
    s.append(_embed_icon(art, cx, cy, s=U, icx=icx, icy=icy))
    # 8 排针：下排 connector0-3（pin1-4 左→右）、上排 connector7-4（pin8-5 左→右）
    for i in range(per):
        x = x_pins[i]
        for yy, cn in ((y_bot, i), (y_top, per * 2 - 1 - i)):
            s.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                     f'cx="{x:.1f}" cy="{yy:.1f}" r="{pad_r:.1f}" '
                     f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
            s.append(f'  <circle cx="{x:.1f}" cy="{yy:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    # 引脚数字（绿板上、焊盘与芯片之间；白字，字号 60，逆时针旋转 90°）
    for i in range(per):
        x = x_pins[i]
        s.append(f'  <text x="{x:.1f}" y="150" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 150)">{per * 2 - i}</text>\n')
        s.append(f'  <text x="{x:.1f}" y="450" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 450)">{i + 1}</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（SOP-8 150mil 真实封装）：焊盘 RECT 0.7×1.8mm（x×y）、间距 1.27mm、
    行中心距 ±2.7mm（5.4mm；手册跨距 5.80–6.20mm 取中）。下排 connector0-3（pin1-4）y=+2.7 左→右、
    上排 connector7-4（pin8-5）y=-2.7 左→右。丝印本体 5.05×3.9 + pin1 圆点（左下角内）。
    Fritzing 层结构：copper1 > copper0（空）+ 焊盘；silkscreen。坐标 mm，viewBox 贴合（裁边）。"""
    pw, pl = 0.7, 1.8        # 焊盘宽（x）× 长（y）
    pitch = 1.27             # 引脚间距
    row = 2.7                # 上下排焊盘中心 y = ±2.7
    per = len(PINS) // 2
    x0 = -(per - 1) * pitch / 2        # 最左焊盘中心 x = -1.905
    pads, silk = [], []
    # 下排 pin1-4（connector0-3）：y=+row，x 左→右
    for i in range(per):
        x = x0 + i * pitch
        cn = i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 上排 pin8-5（connector7-4）：y=-row，x 左→右
    for i in range(per):
        x = x0 + i * pitch
        cn = per * 2 - 1 - i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 丝印本体线框：左右两条竖线（本体边 x=±2.525、y=±1.95 = 本体 5.05×3.9）；
    #   上下横边落在焊盘区不画（同 W25Q16JV 的做法）
    silk.append('<line x1="-2.525" y1="-1.95" x2="-2.525" y2="1.95" stroke="#f0f0f0" stroke-width="0.15"/>')
    silk.append('<line x1="2.525" y1="-1.95" x2="2.525" y2="1.95" stroke="#f0f0f0" stroke-width="0.15"/>')
    # pin1 实心圆：直径 0.8mm（r=0.4），在 1 脚焊盘左侧，右缘距焊盘左缘（-2.255）0.3mm → 圆心 x=-2.955
    silk.append('<circle cx="-2.955" cy="2.7" r="0.4" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    # viewBox 贴合（裁边）：内容 x±3.36（pin1 圆左缘 -3.355）、y±4.1（焊盘），各留 0.15 边距
    SX, SY, M = 3.36, 4.1, 0.15
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * (SX + M):.2f}mm" height="{2 * (SY + M):.2f}mm" '
            f'viewBox="{-(SX + M):.2f} {-(SY + M):.2f} {2 * (SX + M):.2f} {2 * (SY + M):.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """SOP-8（150mil）芯片图标：本体 5.05(D, x) × 3.90(E, y) mm，上下各 4 银引脚
    （宽 0.42、距 1.27、各伸 1.05 → 总高 6.0mm，对齐手册 p12 的 3.80–4.00 × 4.95–5.15 / 跨距 5.80–6.20），
    pin1 左下圆形凹点，丝印 24C02。viewBox 对称居中 5.05×6.0。"""
    e, bw, pl = 1.27, 0.42, 1.05
    half_x, half_y = 2.525, 1.95          # 本体半宽（x=D/2）/ 半高（y=E/2）
    xs = [-(3 * e) / 2 + i * e for i in range(4)]   # -1.905, -0.635, 0.635, 1.905
    parts = [SVG_HDR,
             '<svg xmlns="http://www.w3.org/2000/svg" width="5.05mm" height="6.0mm" '
             'viewBox="-2.525 -3.0 5.05 6.0">\n'
             '  <g id="icon">\n']
    # 本体（直角、深色）
    parts.append(f'    <rect x="{-half_x}" y="{-half_y}" width="{2 * half_x}" height="{2 * half_y}" '
                 f'fill="#303030" stroke="none"/>\n')
    # 上、下各 4 个银引脚（从本体上下边各伸 1.05mm）
    for x in xs:
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{-half_y - pl:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 上排
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{half_y:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 下排
    # pin1 标记（本体左下角内，圆形凹点）
    parts.append(f'    <circle cx="{-half_x + 0.62:.2f}" cy="{half_y - 0.62:.2f}" r="0.28" '
                 f'fill="#c0c0c0" stroke="none"/>\n')
    # 丝印
    parts.append('    <text x="0" y="0.26" font-size="0.72" fill="#ffffff" text-anchor="middle" '
                 'font-family="DroidSans">24C02</text>\n')
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
        "schematic": gen_schematic_svg(),
        "breadboard": gen_breadboard_svg(),
        "pcb": gen_pcb_svg(),
        "icon": gen_icon_svg(),
    }
    for view, content in files.items():
        name = f"svg.{view}.{PART_ID}_{view}.svg"
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
        for view in ("breadboard", "schematic", "pcb", "icon"):
            name = f"svg.{view}.{PART_ID}_{view}.svg"
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
