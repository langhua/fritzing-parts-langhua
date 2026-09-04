#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 XC6206P332MR（Torex XC6206 系列低压差
线性稳压器 LDO，SOT-23-3，3.3V 固定输出）。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件同目录，.fzpz 输出到仓库顶层 fzpz/（内部平铺，.fzp 的 image= 用子目录路径）。

数据来源：D:\\Downloads\\XC6206P332MR.pdf（Torex XC6206 系列 datasheet，17 页）
  - XC6206 = 高精度低功耗 3 端正稳压器（LDO）。最大输出 200mA(3.0V 型)、
    Dropout 250mV@100mA、VIN max 6V、静态 1uA、-40~+85℃。
  - 型号解码 XC6206P332MR：P 系列、输出 3.3V（①=3 ②=3）、精度 ±2%（③=2）、
    MR = SOT-23 封装（3000/盘）。
  - SOT-23 顶视引脚（datasheet PIN CONFIGURATION 页）：下排 1=VSS(GND)、2=VOUT，
    上排单脚 3=VIN（本体 2.9x1.6mm，下排两脚中心距 1.9mm，datasheet 封装图标注
    1.9±0.2、括号 (0.95)=半距）。命名沿用本库惯例：GND（datasheet VSS）。
  - 与仓库 BAT54S（官方 SOT-23-3 布局）几何一致：connector0=pin1(GND) 左下、
    connector1=pin2(VOUT) 右下、connector2=pin3(VIN) 顶中。

用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "XC6206P332MR"
FZPZ = "XC6206P332MR.fzpz"

# 引脚定义 pin1..3：下排 1,2 左→右（GND/VOUT）；上排单脚 3 = VIN
PINS = [
    "GND",    # 1 (datasheet VSS)
    "VOUT",   # 2
    "VIN",    # 3
]
BOT = [0, 1]        # 下排 connector：pin1(GND)、pin2(VOUT) 左→右
TOP = [2]           # 上排 connector：pin3(VIN)

ICON_LABEL1 = "XC6206P"
ICON_LABEL2 = "332MR"
SCHEM_LABEL = "XC6206P332MR"
TITLE = "XC6206P332MR 3.3V LDO (SOT-23-3)"
LABEL = "U"
PACKAGE = "SOT-23-3"
FAMILY = "Torex XC6206 LDO"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- XC6206P332MR SOT-23-3 -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ icon
def gen_icon_svg():
    """SOT-23-3 芯片图标：本体 2.9x1.6mm（#303030 直角），下排 2 脚（pin1 左 /
    pin2 右）+ 上排单脚（pin3 中，银脚 #c0c0c0，各伸 0.6mm 出体、脚宽 0.4），
    pin1 圆点在本体左下，白色丝印两行 XC6206P / 332MR。viewBox 约 3.4x3.2mm。"""
    # 本体（SOT-23：2.9x1.6mm，居中原点）
    bx0, by0 = -1.45, -0.8
    bw, bh = 2.9, 1.6
    pw, ph = 0.4, 0.6            # 脚宽、伸出长
    # 下排两脚 pin1/pin2：x=±0.95（中心距 1.9mm，datasheet 标注 1.9±0.2）；
    # 上排单脚 pin3：x=0（居中，相对下排两脚中点）
    xs_bot = [-0.95, 0.95]
    xs_top = [0.0]
    parts = [SVG_HDR,
             '<svg xmlns="http://www.w3.org/2000/svg" width="3.40mm" height="3.20mm" '
             'viewBox="-1.70 -1.60 3.40 3.20">\n'
             '  <g id="icon">\n']
    # 银脚
    for x in xs_bot:
        parts.append(f'    <rect x="{x - pw / 2:.3f}" y="{by0 + bh:.2f}" width="{pw:.3f}" '
                     f'height="{ph:.3f}" fill="#c0c0c0" stroke="none"/>\n')     # 下排
    for x in xs_top:
        parts.append(f'    <rect x="{x - pw / 2:.3f}" y="{by0 - ph:.2f}" width="{pw:.3f}" '
                     f'height="{ph:.3f}" fill="#c0c0c0" stroke="none"/>\n')     # 上排单脚
    # 本体
    parts.append(f'    <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" fill="#303030" stroke="none"/>\n')
    # pin1 圆点（本体下缘内侧、与 1 脚水平居中对齐；1 脚中心 x=-0.95、y=0.8..1.4）
    # 圆点 x 与 1 脚中心同轴（cx=-0.95），cy=0.55 位于黑体内贴近脚，SVG y 向下
    parts.append('    <circle cx="-0.95" cy="0.55" r="0.12" fill="#c0c0c0" stroke="none"/>\n')
    # 丝印分两行：XC6206P（行1，偏上） / 332MR（行2，偏下）
    parts.append(f'    <text x="0" y="-0.24" font-size="0.34" fill="#ffffff" text-anchor="middle" '
                 f'font-family="DroidSans">{ICON_LABEL1}</text>\n')
    parts.append(f'    <text x="0" y="0.18" font-size="0.28" fill="#ffffff" text-anchor="middle" '
                 f'font-family="DroidSans">{ICON_LABEL2}</text>\n')
    parts.append('  </g>\n</svg>\n')
    return "".join(parts)


# -------------------------------------------------------------- breadboard
def _icon_inner():
    icon = gen_icon_svg()
    m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    return m.group(1) if m else ""


def gen_breadboard_svg():
    """面包板 = 绿色 SOT-23-3 转接板（AGENTS §3b，仿淘宝成品形态）：竖条小板，
    芯片垂直居中于板（转 180°：pin1 GND 圆点落右上、pin3 VIN 单脚朝下），
    底部 3 个 2.54mm 排针孔并排（无走线、无顶部型号字）。

    坐标系：100 单位 = 2.54mm（内部单位）。板 400x560（约 10.2x14.2mm，紧凑）。
    排针从左到右 = VOUT(pin2)/VIN(pin3)/GND(pin1)，丝印数字 2/3/1（与淘宝板一致）。
    三焊盘水平居中（x=100/200/300，中心=200=板中心），芯片贴近顶部（cy=80）。
    """
    U = 39.37
    bw, bh = 400, 560
    pad_s = 78.0            # 方形排针焊盘边长 ≈ 2mm（78.7 单位）
    hole_r = 0.485 * U      # 中央针孔 ≈0.97mm 直径
    cx = bw // 2            # 200
    # 芯片转 180° 后置于板中上部（中心 y=170，顶部留 ~107、不与下方数字区重叠），水平居中
    chip_cx, chip_cy = 200, 170
    # 底部排针（从左到右 VOUT/VIN/GND）：y 500，x 100/200/300（2.54 网格、水平居中）
    pin_x = {1: 100, 2: 200, 0: 300}
    pin_y = 500
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
             f'height="{bh / 100 * 2.54:.2f}mm" viewBox="0 0 {bw} {bh}">\n')
    L.append(' <g id="breadboard">\n')
    # 绿板（直角）
    L.append(f'  <rect x="0" y="0" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    # 芯片 icon（转 180°，1 脚 GND 落右上；垂直居中于板）
    L.append('  <g transform="translate(%.1f %.1f) rotate(180) scale(%.3f)">\n' % (chip_cx, chip_cy, U))
    L.append(_icon_inner())
    L.append('  </g>\n')
    # 底部 3 个方形排针焊盘（VOUT/VIN/GND = cn1/cn2/cn0），+ 中央针孔
    def pad(cn, x, y):
        L.append(f'  <rect id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x="{x - pad_s / 2:.1f}" y="{y - pad_s / 2:.1f}" width="{pad_s:.1f}" height="{pad_s:.1f}" '
                 f'fill="#d4af37" stroke="#8a6d00" stroke-width="4" rx="6"/>\n')
        L.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    for cn in (1, 2, 0):          # 左→右 VOUT/VIN/GND
        pad(cn, pin_x[cn], pin_y)
    # 数字标注：竖排（逆时针旋转 90°）、居中于焊盘上方 76 单位（AGENTS §3b）；
    # 显示引脚号 2/3/1（cn+1）
    for cn in (1, 2, 0):
        x = pin_x[cn]
        L.append(f'  <text x="{x:.1f}" y="{pin_y - 76}" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} {pin_y - 76})">{cn + 1}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# -------------------------------------------------------------- schematic
def gen_schematic_svg():
    """矩形封装符号（SOT-23-3 三端 LDO）。按 XC6206 LDO 拓扑：左列上=GND(pin1)、
    下=VOUT(pin2)，右列=VIN(pin3)。AGENTS §5 矩形符号规则（同 ETA3425S2F）：
    名/数字/引线同色黑、整图同字号；左列 2 + 右列 1，右侧引脚垂直居中。"""
    P = 100
    WIRE = 130
    CH = 35
    FN = 35
    BASELINE_OFF = round(FN * 0.35)
    max_len = max(len(n) for n in PINS)        # 4 (VOUT/VIN/GND → 4)
    CORNER = (max_len + 1) * int(FN * 0.58)    # 5×20 = 100
    n_left = len(BOT)                          # 2
    n_right = len(TOP)                         # 1
    h_left = n_left * P + 2 * CORNER
    h_right = n_right * P + 2 * CORNER
    BH = max(h_left, h_right)
    BW = 720
    BX0, BY0 = 340, 200
    BX1 = BX0 + BW
    BY1 = BY0 + BH
    VBX = BX0 - WIRE - 5
    VBY = BY0 - 5
    VBW = BW + 2 * WIRE + 10
    VBH = BH + 10
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" height="{VBH / 1000:.6f}in" '
             f'viewBox="{VBX} {VBY} {VBW} {VBH}">\n')
    L.append(' <g id="schematic">\n')
    L.append(f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
             f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n')
    # 左列 pin1(GND)、pin2(VOUT) 上→下
    for i, cn in enumerate(BOT):
        y = BY0 + CORNER + P // 2 + i * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{cn + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 右列 pin3(VIN) 垂直居中（相对左列总高）
    y_r = BY0 + BH // 2
    L.append(f'  <line class="pin" id="connector2pin" connectorname="{esc(PINS[2])}" '
             f'x1="{BX1}" y1="{y_r}" x2="{BX1 + WIRE}" y2="{y_r}" stroke="#000000" stroke-width="5"/>\n')
    L.append(f'  <rect id="connector2terminal" x="{BX1 + WIRE}" y="{y_r - 11}" width="22" height="22" fill="none"/>\n')
    L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y_r - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">3</text>\n')
    L.append(f'  <text x="{BX1 - CH}" y="{y_r + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="end" '
             f'font-family="DroidSans">{esc(PINS[2])}</text>\n')
    CHIP_FS = 48
    cy = BY0 + BH // 2
    # 芯片名分两行（与 icon 丝印一致：XC6206P / 332MR），居中；SVG y 为基线
    # 两行字高各≈CHIP_FS，行距 4 → 总高 2*CHIP_FS+4；首行基线上移半块、次行基线下移半块
    y1 = cy - round(CHIP_FS * 0.5)
    y2 = cy + round(CHIP_FS * 0.55)
    L.append(f'  <text x="{BX0 + BW // 2}" y="{y1}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(ICON_LABEL1)}</text>\n')
    L.append(f'  <text x="{BX0 + BW // 2}" y="{y2}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(ICON_LABEL2)}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（SOT-23-3 真实封装）：本体 2.9x1.6mm 居中；
    焊盘 0.6(宽,x)x1.2(长,y)mm，下排两焊盘中心 x=±0.95、中心距 1.9mm，
    上排单焊盘 x=0；两行焊盘中心距 2.6mm（row=±1.3）。
    下排 connector0/1 = pin1/2（GND/VOUT）、上排 connector2 = pin3（VIN）。
    丝印：本体左右两侧竖线 + pin1 圆点（直径 0.5mm）在 1 脚（GND，下排最左焊盘）左侧。"""
    pw, pl = 0.6, 1.2
    pitch = 1.9                     # 下排两脚中心距（SOT-23-3）
    row = 1.3
    x0 = -pitch / 2.0                # -0.95
    bot_xs = [x0, x0 + pitch]        # -0.95, +0.95
    top_xs = [0.0]                   # 上排单脚 VIN（居中）
    pads, silk = [], []
    # 下排 pin1,2 = cn0,1（左→右，y=+row）
    for cn, x in zip(BOT, bot_xs):
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 上排 pin3(VIN)=cn2（y=-row，居中 x=0）
    for cn, x in zip(TOP, top_xs):
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 本体丝印：左右两条竖线（本体左右边缘，只在本体高度内，不覆盖上下焊盘）
    silk.append('<line x1="-1.45" y1="-0.8" x2="-1.45" y2="0.8" stroke="#f0f0f0" stroke-width="0.12"/>')
    silk.append('<line x1="1.45" y1="-0.8" x2="1.45" y2="0.8" stroke="#f0f0f0" stroke-width="0.12"/>')
    # pin1 实心圆：直径 0.5mm（r=0.25），在 1 脚（GND，下排最左焊盘 x=-0.95,y=1.3）左侧；
    # 焊盘左缘 -1.25，圆点右缘距焊盘 0.12 空隙 → 心 cx≈-1.62，cy=1.3
    silk.append('<circle cx="-1.62" cy="1.3" r="0.25" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    M = 0.15
    vb_x0 = -1.62 - 0.25 - M         # pin1 圆左缘 + 边距
    vb_x1 = 1.45 + M
    vb_y0 = -(row + pl / 2) - M      # -(1.3+0.6)-0.15 = -2.05
    vb_y1 = (row + pl / 2) + M
    vw, vh = vb_x1 - vb_x0, vb_y1 - vb_y0
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
            f'viewBox="{vb_x0:.2f} {vb_y0:.2f} {vw:.2f} {vh:.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ------------------------------------------------------------------ .fzp
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
            f' <version>4</version>\n <date>2026-09-05</date>\n'
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
