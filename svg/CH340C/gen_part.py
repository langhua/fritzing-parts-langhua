#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 CH340C (SOP16)。

TXW8301 模拟器 USB 转串口桥接元件。
源文件（part.<id>.fzp + 4 个 svg.<view>.*）与脚本同目录，.fzpz 输出到仓库顶层
fzpz/。打包规则（docs/part-dev-guide.md §2.2）：.fzpz 内部平铺，.fzp 的
image= 引用用子目录路径（breadboard/、schematic/、pcb/、icon/）。

用法：
  python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH340C"
FZPZ = "CH340C.fzpz"

# 引脚定义（SOP16，左右各 8；按 CH340C 数据手册原理图符号：pin1=GND 左上，pin16=VCC 左下）
PINS = [
    "GND",   # 1
    "TXD",   # 2
    "RXD",   # 3
    "V3",    # 4
    "UD+",   # 5
    "UD-",   # 6
    "NC",    # 7 (NC.)
    "OUT#/DTR#",  # 8
    "CTS#",  # 9
    "DSR#",  # 10
    "RI#",   # 11
    "DCD#",  # 12
    "DTR#",  # 13
    "RTS#",  # 14
    "R232",  # 15
    "VCC",   # 16
]

# 几何参数（mm；保持整数，与原始输出一致）
BODY_W, BODY_H, BX, BY = 30, 40, 35, 10
ICON_LABEL = "CH340C"

# .fzp 元数据
TITLE = "CH340C USB to UART Bridge"
LABEL = "U2"
PACKAGE = "SOP16"
FAMILY = "WCH USB-UART"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- Created for TXW8301 Simulator -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装符号（SOP16，左右各 8 脚）。按 AGENTS.md §5 矩形原理图规则：
    1. 左右引脚数字在引线上方（不与线相交）：左 1-8 上→下、右 16-9 上→下。
    2. 引脚名在框内、书写方向同数字、与引脚水平中线对齐（手动基线偏移 BASELINE_OFF，
       不用 dominant-baseline）；名/数字/引线同色（黑）。
    3. 数字与引脚名整图同字号 FN=35（0.889mm ≈ Fritzing 官方 0.881944mm）。
    4. 引脚名与边框保持一个字符 CH=FN 间距，居左/右。
    5. 四角无引脚区 CORNER=(最长名宽+1)×int(FN×0.58)，引脚从 CORNER 后开始排，框 = 8P+2×CORNER。
    物理尺寸 width/height(in)，1000 单位 = 1in；viewBox 贴合内容（Resize to content 裁边）。"""
    P = 100                       # 引脚间距（2.54mm）
    WIRE = 130                    # 引脚线长
    CH = 35                       # 一个字符间距（= 字号）
    FN = 35                       # 整图统一字号（数字与引脚名）
    BASELINE_OFF = round(FN * 0.35)   # 手动垂直居中基线偏移
    max_len = max(len(n) for n in PINS)        # 9（OUT#/DTR#）
    CORNER = (max_len + 1) * int(FN * 0.58)    # 四角无引脚宽度
    per = len(PINS) // 2                      # 8
    BX0, BY0 = 340, 200
    BW = 850                                  # 框宽（用户要求收窄；高度仍 = 8P+2×CORNER = 1200）
    BH = per * P + 2 * CORNER                 # 框高
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - 5        # viewBox 左上（贴合内容，裁边）
    VBW, VBH = BW + 2 * WIRE + 10, BH + 10    # viewBox 宽高
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" height="{VBH / 1000:.6f}in" '
             f'viewBox="{VBX} {VBY} {VBW} {VBH}">\n')
    L.append(' <g id="schematic">\n')
    # 封装体（白底灰边）
    L.append(f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
             f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n')
    # 左 1-8（上→下）：数字在引线上方，名在框内靠左、与引脚中线对齐
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
    # 右 16-9（上→下）：数字在引线上方，名在框内靠右
    for i in range(per):
        y = BY0 + CORNER + P // 2 + i * P
        cn = per * 2 - 1 - i          # 顶部 connector15(pin16) → 底部 connector8(pin9)
        col = "#000000"
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans">{per * 2 - i}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{col}" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 芯片名（框内居中，字号 79 = 2.0mm）
    CHIP_FS = 79
    CHIP_Y = BY0 + BH // 2 + round(CHIP_FS * 0.35)
    L.append(f'  <text x="{BX0 + BW // 2}" y="{CHIP_Y}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(ICON_LABEL)}</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def _embed_icon(art, cx, cy, s=1.0, icx=0.0, icy=0.0, text_dy=0.0):
    """把 icon 组内容（mm，含 g translate）放大 s，使 icon 视觉中心 (icx,icy) 映射到 (cx,cy)。
    不旋转（保持 icon 方向：pin1 左下、丝印横排）。烘焙绝对坐标（处理 rect/circle/text）。
    text_dy：对丝印 text 的 y 额外偏移（单位，用于 Inkscape 手动调整后归一化）。"""
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
    # rect
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
    # circle
    for cm in re.finditer(r'<circle\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        px = (float(a["cx"]) + tx - icx) * s + cx
        py = (float(a["cy"]) + ty - icy) * s + cy
        out.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["r"]) * s,
            a.get("fill", "#c0c0c0"), a.get("stroke", "none")))
    # text
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
    """面包板 = 绿色 SOP-16 转接板 + 16 排针（上下各 8）+ 横放 CH340C icon（pin1 左下、丝印横排）。
    坐标 100 单位 = 2.54mm，排针中心落在 100 整数倍 → 对准面包板孔。
    芯片垂直居中于绿板（cy=400=排针中点）；绿板对称包住焊盘，边距 20。
    板 22.86×18.26mm；viewBox 贴合绿板 40.6..759.4（裁掉上下空白，坐标绝对不变）。"""
    U = 39.37
    bw = 900
    gy0, gbh = 40.6, 718.8         # 绿板 y/h：对称包住排针焊盘 + 20 边距，中心 y=400
    pad_r = 1.0 * U                  # 2mm 直径焊盘 → 半径 1mm
    hole_r = 0.485 * U               # 0.97mm 直径针孔
    icon = gen_icon_svg()
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    art = _m.group(1) if _m else ""
    _vm = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', icon)
    icx = icy = 0.0
    if _vm:
        vx, vy, vw, vh = map(float, _vm.groups())
        icx, icy = vx + vw / 2, vy + vh / 2
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" height="{gbh / 100 * 2.54:.2f}mm" '
             f'viewBox="0 {gy0} {bw} {gbh}">\n')
    s.append(' <g id="breadboard">\n')
    # 绿色转接板（直角）
    s.append(f'  <rect x="0" y="{gy0}" width="{bw}" height="{gbh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    # 芯片 icon（横放，1:1，垂直居中 cy=400）；丝印上移至芯片正中（用户 Inkscape 调整）
    s.append(_embed_icon(art, 450, 400, s=U, icx=icx, icy=icy, text_dy=-20.83))
    # 16 排针：上排 connector8-15（y=100，反向：左 16→右 9）、下排 connector0-7（y=700，正向：左 1→右 8），x=100..800
    for i in range(8):
        x = 100 + i * 100
        for yy, cn in ((100, 15 - i), (700, i)):
            s.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                     f'cx="{x:.1f}" cy="{yy:.1f}" r="{pad_r:.1f}" '
                     f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
            s.append(f'  <circle cx="{x:.1f}" cy="{yy:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    # 引脚数字标注（绿板上、焊盘与芯片之间；白字，字号 60，逆时针旋转 90°）：
    # 上排 16..9（y=180，左→右）、下排 1..8（y=620）——y 微调避开加大后的字宽与焊盘
    for i in range(8):
        x = 100 + i * 100
        s.append(f'  <text x="{x:.1f}" y="180" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 180)">{16 - i}</text>\n')
        s.append(f'  <text x="{x:.1f}" y="620" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 620)">{i + 1}</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（SOP-16 真实封装，参数来自立创EDA下载 D:\\Downloads\\SOP-16_2026-09-01.svg）：
    焊盘 RECT 0.7×2.2mm（x×y）、间距 1.27mm、行距 7.4mm（±3.7）。
    下排 connector0-7（pin1-8）y=+3.7 左→右、上排 connector8-15（pin9-16）y=-3.7 左→右=16..9。
    丝印本体 9.9×6.0mm + pin1 圆点（左下角内）。
    Fritzing 层结构：copper1 > copper0（空）+ 焊盘；silkscreen。坐标 mm，viewBox 贴合（裁边）。"""
    pw, pl = 0.7, 2.2        # 焊盘宽（x）× 长（y）
    pitch = 1.27             # 引脚间距
    row = 3.7                # 行距半宽（上下排中心 y = ±3.7）
    per = len(PINS) // 2
    x0 = -(per - 1) * pitch / 2        # 最左焊盘中心 x = -4.445
    pads, silk = [], []
    # 下排 pin1-8（connector0-7）：y=+row，x 左→右
    for i in range(per):
        x = x0 + i * pitch
        cn = i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 上排 pin16-9（connector15-8）：y=-row，x 左→右 = connector15..8（16..9）
    for i in range(per):
        x = x0 + i * pitch
        cn = per * 2 - 1 - i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 丝印本体（10.4×4.5，中心 0,0；y±2.25 < 焊盘内缘 2.6 → 与焊盘零相交）
    # + pin1 圆点（1 脚焊盘正上方、丝印方框内）
    silk.append('<rect x="-5.2" y="-2.25" width="10.4" height="4.5" fill="none" '
                'stroke="#f0f0f0" stroke-width="0.15"/>')
    silk.append('<circle cx="-4.445" cy="1.9" r="0.25" fill="none" stroke="#f0f0f0" stroke-width="0.15"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    # viewBox 贴合（裁边）：内容 x±5.2（丝印）、y±4.8（焊盘），各留 0.15 边距
    SX, SY, M = 5.2, 4.8, 0.15
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * (SX + M):.2f}mm" height="{2 * (SY + M):.2f}mm" '
            f'viewBox="{-(SX + M):.2f} {-(SY + M):.2f} {2 * (SX + M):.2f} {2 * (SY + M):.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """SOP-16 芯片图标（STC 尺寸）：本体 9.9×3.9mm，上下各 8 银引脚（宽 0.4、距 1.27、
    各伸 1.05mm → 总高 6mm），pin1 左下（-4.2705,1.2751），丝印 CH340C。
    裁边 viewBox 9.9×6，内容 translate(-0.55,-0.5) 居中填满（Inkscape 手动调整后同步）。"""
    e, bw, pl = 1.27, 0.4, 1.05
    xs = [-4.445 + i * e for i in range(8)]          # 8 引脚中心 x（-4.445..4.445）
    parts = [SVG_HDR,
             '<svg xmlns="http://www.w3.org/2000/svg" width="9.9mm" height="6mm" '
             'viewBox="-5.5 -3.5 9.9 6">\n'
             '  <g id="icon" transform="translate(-0.55,-0.5)">\n']
    # 本体（直角，深色）
    parts.append('    <rect x="-4.95" y="-1.95" width="9.9" height="3.9" fill="#303030" stroke="none"/>\n')
    # 上、下各 8 个银引脚（从本体上下边伸出）
    for x in xs:
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="-3" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 上排
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="1.95" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')   # 下排
    # pin1 标记（本体左下角内，Inkscape 手动移动后位置）
    parts.append('    <circle cx="-4.2704968" cy="1.2750731" r="0.4" fill="#c0c0c0" stroke="none"/>\n')
    # 丝印
    parts.append(f'    <text x="0" y="0.6" font-size="1.6" fill="#ffffff" text-anchor="middle" '
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
            f' <version>4</version>\n <date>2026-08-16</date>\n'
            f' <label>{LABEL}</label>\n <author>TXW8301 Simulator</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>{LABEL}</tag>\n  <tag>{PACKAGE}</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n  <property name="chip">{LABEL}</property>\n'
            f'  <property name="layer"></property>\n </properties>\n'
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
