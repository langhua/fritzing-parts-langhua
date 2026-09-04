#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 CH340E (WCH USB转串口, MSOP-10)。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件（part.<id>.fzp + 4 个 svg.<view>.* + 本脚本）同目录，.fzpz 输出到仓库顶层 fzpz/。
打包规则：.fzpz 内部平铺，.fzp 的 image= 用子目录路径。

数据来源：D:\\Downloads\\CH340数据手册.pdf
  - CH340E = MSOP-10：本体 3.0×3.0mm（118mil），脚距 0.50mm，内置时钟（无 XI/XO）。
  - 引脚（手册第 0 页 CH340E 引脚图，顶视逆时针 1→10）：
      1 UD+  2 UD-  3 GND  4 RTS#  5 CTS#  6 TNOW  7 VCC  8 TXD  9 RXD  10 V3
    （左 1-5 上→下 / 右 10-6 上→下；无 0# 底板脚——与 CH340K 不同）

用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH340E"
FZPZ = "CH340E.fzpz"

# 引脚定义（pin1..10；左 1-5 上→下、右 10-6 上→下）
PINS = [
    "UD+",    # 1
    "UD-",    # 2
    "GND",    # 3
    "RTS#",   # 4
    "CTS#",   # 5
    "TNOW",   # 6
    "VCC",    # 7
    "TXD",    # 8
    "RXD",    # 9
    "V3",     # 10
]

ICON_LABEL = "CH340E"
SCHEM_LABEL = "CH340E"

# .fzp 元数据
TITLE = "CH340E USB to UART Bridge (MSOP-10)"
LABEL = "U"
PACKAGE = "MSOP-10"
FAMILY = "WCH USB-UART"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- CH340E MSOP-10 -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装符号（10 脚，左右各 5）。按 AGENTS.md §5 矩形原理图规则：
    左 1-5 上→下、右 10-6 上→下；名/数字/引线同色黑；整图同字号 FN=35；
    四角无引脚区 CORNER=(最长名+1)×int(FN×0.58)；框 = 5P+2×CORNER。"""
    P = 100                       # 引脚间距（2.54mm）
    WIRE = 130                    # 引脚线长
    CH = 35
    FN = 35
    BASELINE_OFF = round(FN * 0.35)
    max_len = max(len(n) for n in PINS)        # 4（RTS#/CTS#/TNOW）
    CORNER = (max_len + 1) * int(FN * 0.58)    # 5×20 = 100
    per = len(PINS) // 2                      # 5
    BX0, BY0 = 340, 200
    BW = 720
    BH = per * P + 2 * CORNER                 # 500 + 200 = 700
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - 5
    VBW, VBH = BW + 2 * WIRE + 10, BH + 10
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" height="{VBH / 1000:.6f}in" '
             f'viewBox="{VBX} {VBY} {VBW} {VBH}">\n')
    L.append(' <g id="schematic">\n')
    L.append(f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
             f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n')
    for i in range(per):          # 左 1-5
        y = BY0 + CORNER + P // 2 + i * P
        cn = i
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    for i in range(per):          # 右 10-6
        y = BY0 + CORNER + P // 2 + i * P
        cn = per * 2 - 1 - i
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{per * 2 - i}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
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
    """面包板 = 绿色 MSOP-10 转接板 + 10 排针（上下各 5）+ 居中 CH340E icon（1:1，pin1 左下）。
    坐标 100 单位 = 2.54mm。排针行距 400 单位（10.16mm）≥ 芯片总高 5.0mm + 2mm；
    排针 x=100..500，上排 y=100（pin10-6）、下排 y=500（pin1-5）。"""
    U = 39.37
    per = len(PINS) // 2                      # 5
    x_pins = [100 + i * 100 for i in range(per)]
    y_top, y_bot = 100, 500
    cx, cy = 300, 300
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
    bx0, bx1 = 0, 600
    by0, by1 = 0, 600
    bw, bh = bx1 - bx0, by1 - by0
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" height="{bh / 100 * 2.54:.2f}mm" '
             f'viewBox="{bx0} {by0} {bw} {bh}">\n')
    s.append(' <g id="breadboard">\n')
    s.append(f'  <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    s.append(_embed_icon(art, cx, cy, s=U, icx=icx, icy=icy))
    for i in range(per):
        x = x_pins[i]
        for yy, cn in ((y_bot, i), (y_top, per * 2 - 1 - i)):
            s.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                     f'cx="{x:.1f}" cy="{yy:.1f}" r="{pad_r:.1f}" '
                     f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
            s.append(f'  <circle cx="{x:.1f}" cy="{yy:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    # 引脚数字：距焊盘 0.5mm（焊盘边→数字顶端；按位数中心微调：1位 y=176，2位“10” y=192）
    for i in range(per):
        x = x_pins[i]
        n_top = per * 2 - i                    # 10,9,8,7,6
        ytop = 176 if n_top < 10 else 192
        s.append(f'  <text x="{x:.1f}" y="{ytop}" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} {ytop})">{n_top}</text>\n')
        s.append(f'  <text x="{x:.1f}" y="424" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 424)">{i + 1}</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（MSOP-10 真实封装）：焊盘 RECT 0.3×1.1mm、间距 0.5mm、行中心 y=±2.35
    （顶排上沿 -2.9 到底排下沿 +2.9 = 总高 5.8mm）。
    下排 connector0-4（pin1-5）y=+2.35 左→右、上排 connector9-5（pin10-6）y=-2.35 左→右。
    丝印：左右两段竖线（本体 x=±1.5）+ pin1 实心圆（直径0.8，pin1 左下）。"""
    pw, pl = 0.3, 1.1
    pitch = 0.5
    row = 2.35
    per = len(PINS) // 2
    x0 = -(per - 1) * pitch / 2        # -1.0
    pads, silk = [], []
    for i in range(per):
        x = x0 + i * pitch
        cn = i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    for i in range(per):
        x = x0 + i * pitch
        cn = per * 2 - 1 - i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 丝印：左右竖线（本体宽 ±1.5，跨全高 ±1.5，不画上下横线避开焊盘）
    silk.append('<line x1="-1.5" y1="-1.5" x2="-1.5" y2="1.5" stroke="#f0f0f0" stroke-width="0.12"/>')
    silk.append('<line x1="1.5" y1="-1.5" x2="1.5" y2="1.5" stroke="#f0f0f0" stroke-width="0.12"/>')
    # pin1 实心圆：直径0.8（r0.4），在 1 脚焊盘左侧，右缘距焊盘左缘（-1.15）0.3 → 心 x=-1.85
    silk.append('<circle cx="-1.85" cy="2.35" r="0.4" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    # 裁边：内容 x -2.25(pin1圆左)..1.5(丝印右)、y ±(row+pl/2)=±2.9，各留 0.15
    M = 0.15
    vb_x0, vb_x1 = -2.25 - M, 1.5 + M
    vb_y0, vb_y1 = -(row + pl / 2) - M, (row + pl / 2) + M
    vw, vh = vb_x1 - vb_x0, vb_y1 - vb_y0
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
            f'viewBox="{vb_x0:.2f} {vb_y0:.2f} {vw:.2f} {vh:.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """MSOP-10 芯片图标：本体 3.0×3.0mm，上/下各 5 银引脚（宽 0.22、距 0.5、各伸 1.0mm →
    总高 5.0mm），pin1 左下圆点，丝印 CH340E。viewBox 3.0×5.0。"""
    e, bw, pl = 0.5, 0.22, 1.0
    half = 1.5
    xs = [-1.0 + i * e for i in range(5)]        # -1.0..1.0
    parts = [SVG_HDR,
             '<svg xmlns="http://www.w3.org/2000/svg" width="3.0mm" height="5.0mm" '
             'viewBox="-1.5 -2.5 3.0 5.0">\n'
             '  <g id="icon">\n']
    parts.append(f'    <rect x="{-half}" y="{-half}" width="3.0" height="3.0" fill="#303030" stroke="none"/>\n')
    for x in xs:
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{-half - pl:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 上排
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{half:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 下排
    parts.append('    <circle cx="-1.1" cy="1.12" r="0.22" fill="#c0c0c0" stroke="none"/>\n')  # pin1 圆点
    parts.append('    <text x="0" y="0.15" font-size="0.45" fill="#ffffff" text-anchor="middle" '
                 'font-family="DroidSans">CH340E</text>\n')
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
