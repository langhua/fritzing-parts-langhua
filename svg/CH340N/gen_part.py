#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 CH340N (WCH USB 转串口, SOP-8)。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件（part.<id>.fzp + 4 个 svg.<view>.* + 本脚本）同目录，.fzpz 输出到仓库顶层 fzpz/。
打包规则：.fzpz 内部平铺，.fzp 的 image= 用子目录路径。

数据来源：D:\\Downloads\\CH340数据手册.pdf（版本 3D）
  - 第 1 页「3、封装」表：**CH340N = SOP-8，塑体宽 3.9mm(150mil)，引脚间距 1.27mm(50mil)**，
    备注里写明 CH340C/N/K/E/X/B **内置时钟，无需外部晶振**（所以本型号无 XI/XO）。
  - 第 1~2 页「4、引脚」表（取 **SOP8 那一列**）：
      1 UD+   2 UD-   3 GND   4 RTS#   5 VCC   6 TXD   7 RXD   8 V3
    （表里 SOP8 列对 VCC/GND/V3/UD+/UD-/TXD/RXD/RTS# 都给了值；
      CTS#/DSR#/RI#/DCD#/DTR# 等的 SOP8 列是「无」—— 即 CH340N 不引出）
  - 第 2 页 5.1 节：5V 供电时 VCC 接 5V 且 V3 外接 0.1uF 退耦；3.3V 供电时 V3 与 VCC 相连。
  - 封装几何（本体长 4.9mm、脚宽 0.4mm、脚长 1.05mm、丝印留边）**沿用同族已入库元件**
    svg/CH340C（SOP-16）与 svg/CH340E（MSOP-10）的参数：三者同为 150mil 宽族/同规范，
    行距半宽 row=3.7、焊盘 0.7×2.2 与 CH340C 一致；本体长度按 SOP-8 取 4.9mm。

用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH340N"
FZPZ = "CH340N.fzpz"

# 引脚定义（pin1..8；SOP8 列，见上）
PINS = [
    "UD+",    # 1
    "UD-",    # 2
    "GND",    # 3
    "RTS#",   # 4
    "VCC",    # 5
    "TXD",    # 6
    "RXD",    # 7
    "V3",     # 8
]

ICON_LABEL = "CH340N"
SCHEM_LABEL = "CH340N"

# .fzp 元数据
TITLE = "CH340N USB to UART Bridge (SOP-8)"
LABEL = "U"
PACKAGE = "SOP-8"
FAMILY = "WCH USB-UART"

BODY_W, BODY_H = 3.9, 4.9          # SOP-8 本体（宽 × 长）

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- CH340N SOP-8 -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装符号（8 脚，左右各 4）。按 AGENTS.md §5 矩形原理图规则：
    SOP 两排封装用左右两列 —— 左列 pin1-4 上→下、右列 pin8-5 上→下（即从下往上数）；
    数字在引线上方、名在框内、名/数字/引线同色黑、整图同字号 FN=35；
    四角无引脚区 CORNER=(最长名+1)×int(FN×0.58)；框 = 4P+2×CORNER。
    物理尺寸 width/height(in)，1000 单位 = 1in；viewBox 贴合内容（裁边）。"""
    P = 100                       # 引脚间距（2.54mm）
    WIRE = 130                    # 引脚线长
    CH = 35                       # 一个字符间距（= 字号）
    FN = 35                       # 整图统一字号
    BASELINE_OFF = round(FN * 0.35)
    max_len = max(len(n) for n in PINS)        # 4（RTS#）
    CORNER = (max_len + 1) * int(FN * 0.58)    # 5×20 = 100
    per = len(PINS) // 2                      # 4
    BX0, BY0 = 340, 200
    BW = 720
    BH = per * P + 2 * CORNER                 # 400 + 200 = 600
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
    for i in range(per):          # 左 1-4
        y = BY0 + CORNER + P // 2 + i * P
        cn = i
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    for i in range(per):          # 右 8-5
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
    """把 icon 的 <g id="icon"> 内容重画到面包板坐标系（缩放 s、以 icon 的 viewBox 中心对齐 cx,cy）"""
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
    """面包板 = 绿色 SOP-8 转接板 + 8 排针（上下各 4）+ 居中 CH340N icon（1:1，pin1 左下）。
    坐标 100 单位 = 2.54mm。排针行距 500 单位（12.7mm = 5×2.54，落在面包板孔距网格上）：
    必须 ≥ 芯片总高 6.0mm + 2mm，且要留得下引脚数字（SOP-8 比 MSOP-10 高，400 单位不够 ——
    数字会压在芯片脚上，实测过）。板宽取能放下 4 个排针的最小值 500 单位（12.7mm，AGENTS §3b）。
    下排 y=600（pin1-4 左→右）、上排 y=100（pin8-5 左→右）。"""
    U = 39.37
    per = len(PINS) // 2                      # 4
    x_pins = [100 + i * 100 for i in range(per)]   # 100..400（居中于 0..500）
    y_top, y_bot = 100, 600
    cx, cy = 250, 350
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
    bx0, bx1 = 0, 500
    by0, by1 = 0, 700
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
    # 引脚数字：距焊盘边 0.5mm，逆时针 90°（转接板数字规则，AGENTS §3b）
    for i in range(per):
        x = x_pins[i]
        n_top = per * 2 - i                    # 8,7,6,5
        s.append(f'  <text x="{x:.1f}" y="176" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 176)">{n_top}</text>\n')
        s.append(f'  <text x="{x:.1f}" y="524" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 524)">{i + 1}</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（SOP-8 / SOIC-8 **150mil** 标准盘：IPC-7351 命名 SOIC127P600X175-8N）：
    脚距 1.27mm、**焊盘中心跳距 6.00mm**（row=±3.0）、焊盘 0.60(宽,x)×1.75(长,y)mm；
    本体 3.9(宽,y)×4.9(长,x)，丝印框 4.9×3.9（框边 y±1.95 / x±2.45）——
    与焊盘（y 2.125..3.875、x ±(1.905±0.3)）零相交。
    下排 connector0-3（pin1-4）y=+3.0 左→右、上排 connector7-4（pin8-5）y=-3.0 左→右。

    数据来源（2026-09-17 修正）：
      · 脚距 1.27mm 与塑体宽 3.9mm —— CH340 手册第 1 页「3、封装」表（CH340N = SOP-8）
      · WCH 官方 PCB 工程里给 CH340N 用的封装名就是 `SOP8`
        （D:\\Downloads\\CH340PCB.ZIP → SERIAL/TTL/CH340N4T-R0/…SchDoc 的 ModelName）
      · 跳距 6.00 / 焊盘 1.75：IPC-7351 的标准 SOIC-8 land pattern 名义值
        （封装名 SOIC127P600X175-8N 里就写着 127=1.27mm、600=6.00mm 跳距、175=1.75mm 盘长）
      ⚠ 之前这里照抄了 svg/CH340C（SOP-16）的 row=3.7 / 焊盘 2.2——**无依据**，已修正。
    """
    pw, pl = 0.6, 1.75       # 焊盘宽（x）× 长（y）—— IPC-7351 SOIC-8
    pitch = 1.27             # 引脚间距（手册）
    row = 3.0                # 上下排焊盘中心 y = ±3.0 → 跳距 6.00mm
    per = len(PINS) // 2
    x0 = -(per - 1) * pitch / 2        # 最左焊盘中心 x = -1.905
    pads, silk = [], []
    for i in range(per):     # 下排 pin1-4
        x = x0 + i * pitch
        cn = i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    for i in range(per):     # 上排 pin8-5
        x = x0 + i * pitch
        cn = per * 2 - 1 - i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 丝印本体（4.9×3.9，中心 0,0；框边 y±1.95 < 焊盘内缘 2.125 → 与焊盘零相交）+ pin1 圆点（本体左下角内）
    silk.append('<rect x="-2.45" y="-1.95" width="4.9" height="3.9" fill="none" '
                'stroke="#f0f0f0" stroke-width="0.15"/>')
    silk.append('<circle cx="-2.05" cy="1.55" r="0.25" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    # viewBox 贴合（裁边）：内容 x±2.45（丝印）、y±3.875（焊盘），各留 0.15
    SX, SY, M = 2.45, 3.875, 0.15
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * (SX + M):.2f}mm" height="{2 * (SY + M):.2f}mm" '
            f'viewBox="{-(SX + M):.2f} {-(SY + M):.2f} {2 * (SX + M):.2f} {2 * (SY + M):.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """SOP-8 芯片图标：本体 4.9×3.9mm，上下各 4 银引脚（宽 0.4、距 1.27、各伸 1.05mm
    → 总高 6.0mm），pin1 左下圆点，丝印 CH340N。"""
    e, bw, pl = 1.27, 0.4, 1.05
    half_w, half_h = BODY_H / 2.0, BODY_W / 2.0     # 2.45 / 1.95
    per = len(PINS) // 2
    xs = [-(per - 1) * e / 2 + i * e for i in range(per)]   # -1.905 .. 1.905
    parts = [SVG_HDR,
             f'<svg xmlns="http://www.w3.org/2000/svg" width="{BODY_H:.1f}mm" height="6.3mm" '
             f'viewBox="{-half_w:.2f} -3.15 {BODY_H:.1f} 6.3">\n'
             '  <g id="icon">\n']
    parts.append(f'    <rect x="{-half_w:.2f}" y="{-half_h:.2f}" width="{BODY_H:.1f}" height="{BODY_W:.1f}" '
                 f'fill="#303030" stroke="none"/>\n')
    for x in xs:
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{-half_h - pl:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 上排
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{half_h:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 下排
    # pin1 标记（本体左下角内，距左边 0.68 —— 与 CH340C 同）
    parts.append(f'    <circle cx="{-half_w + 0.68:.3f}" cy="1.275" r="0.34" fill="#c0c0c0" stroke="none"/>\n')
    parts.append(f'    <text x="0" y="0.4" font-size="1.0" fill="#ffffff" text-anchor="middle" '
                 f'font-family="DroidSans">{esc(ICON_LABEL)}</text>\n')
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
            f' <version>1</version>\n <date>2026-09-17</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>CH340N</tag>\n  <tag>USB</tag>\n'
            f'  <tag>UART</tag>\n  <tag>serial</tag>\n  <tag>WCH</tag>\n  <tag>SOP-8</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">{len(PINS)}</property>\n </properties>\n'
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
        for view in ("breadboard", "schematic", "pcb", "icon"):
            name = f"svg.{view}.{PART_ID}_{view}.svg"
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
