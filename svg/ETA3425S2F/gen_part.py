#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 ETA3425S2F (ETA Solutions 同步降压, SOT23-5 型)。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件同目录，.fzpz 输出到仓库顶层 fzpz/（内部平铺，.fzp 的 image= 用子目录路径）。

数据来源：D:\\Downloads\\ETA3425.pdf
  - ETA3425 = 1uA Iq、0.6A 同步降压；ETA3425S2F 为 SOT23-5 型（ETA3425D2G 为 DFN 型）。
  - 本体 D 2.82~3.02mm、E 1.50~1.70mm、含脚 E1 2.65~2.95mm，脚距 e=0.95mm。
  - 引脚（SOT23-5，逆时针 pin1 左下；顶视图下排 1,2,3 左→右、上排 5,4 左→右）：
      1 EN   2 GND   3 SW   4 VIN   5 FB
    （与官方 core SOT-23-5 布列一致：底部 3 焊盘 + 顶部 2 焊盘、pin1 圆点在左下）

用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "ETA3425S2F"
FZPZ = "ETA3425S2F.fzpz"

# 引脚定义 pin1..5（下排 1,2,3 左→右；上排 5,4 左→右）
PINS = [
    "EN",    # 1
    "GND",   # 2
    "SW",    # 3
    "VIN",   # 4
    "FB",    # 5
]
BOT = [0, 1, 2]        # 下排 connector：pin1,2,3（左→右）
TOP = [4, 3]           # 上排 connector：pin5(FB) 左、pin4(VIN) 右

ICON_LABEL = "ETA3425S2F"
SCHEM_LABEL = "ETA3425S2F"
TITLE = "ETA3425S2F Synchronous Buck (SOT23-5)"
LABEL = "U"
PACKAGE = "SOT23-5"
FAMILY = "ETA Solutions DC-DC"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- ETA3425S2F SOT23-5 -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ icon
def gen_icon_svg():
    """SOT23-5 芯片图标：本体 3.0×1.6mm（#303030 直角），下排 3 脚 + 上排 2 脚
    （#c0c0c0 银脚，各伸 0.6mm 出体、脚宽 0.4、e=0.95），pin1 圆点在本体左下，
    白色丝印分两行：ETA3425 / S2F。viewBox 约 3.4×3.2mm（含伸出脚）。"""
    # 本体
    bx0, by0 = -1.5, -0.8
    bw, bh = 3.0, 1.6
    pw, ph = 0.4, 0.6            # 脚宽、伸出长
    xs = [-0.95, 0.0, 0.95]      # 3 列 x（e=0.95）
    parts = [SVG_HDR,
             '<svg xmlns="http://www.w3.org/2000/svg" width="3.40mm" height="3.20mm" '
             'viewBox="-1.70 -1.60 3.40 3.20">\n'
             '  <g id="icon">\n']
    # 银脚（下排 pin1,2,3 在 y=+0.8..1.4；上排 pin5,4 在 y=-1.4..-0.8）
    for x in xs:
        parts.append(f'    <rect x="{x - pw / 2:.3f}" y="{by0 + bh:.2f}" width="{pw:.3f}" height="{ph:.3f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')     # 下排
    for x in xs:
        if x == 0.0:
            continue                                          # 上排只有左/右列
        parts.append(f'    <rect x="{x - pw / 2:.3f}" y="{by0 - ph:.2f}" width="{pw:.3f}" height="{ph:.3f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')     # 上排
    # 本体
    parts.append(f'    <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" fill="#303030" stroke="none"/>\n')
    # pin1 圆点（本体左下角内侧；SVG y 向下，左下 = x 负、y 正）
    parts.append('    <circle cx="-1.13" cy="0.55" r="0.12" fill="#c0c0c0" stroke="none"/>\n')
    # 丝印分两行：ETA3425（行1，偏上） / S2F（行2，偏下）
    parts.append('    <text x="0" y="-0.24" font-size="0.34" fill="#ffffff" text-anchor="middle" '
                 'font-family="DroidSans">ETA3425</text>\n')
    parts.append('    <text x="0" y="0.18" font-size="0.26" fill="#ffffff" text-anchor="middle" '
                 'font-family="DroidSans">S2F</text>\n')
    parts.append('  </g>\n</svg>\n')
    return "".join(parts)


# -------------------------------------------------------------- breadboard
def _icon_inner():
    icon = gen_icon_svg()
    m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    return m.group(1) if m else ""


def gen_breadboard_svg():
    """面包板 = 绿色 SOT-23-5 转接板（AGENTS §3b）：芯片本体横放居中（引脚朝上下），
    下排 3 个 + 上排 2 个 2.54mm 排针孔，引脚垂直扇出到对应排针；内嵌 ETA3425 icon 1:1。

    坐标系：100 单位 = 2.54mm（内部单位）。板 600×600；
    下排 3 针 EN/GND/SW 在 y=500，上排 2 针 FB/VIN 在 y=100，x 均落 100 整数倍网格。
    """
    U = 39.37
    bw, bh = 600, 600
    pad_r = 1.0 * U
    hole_r = 0.485 * U
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
             f'height="{bh / 100 * 2.54:.2f}mm" viewBox="0 0 {bw} {bh}">\n')
    L.append(' <g id="breadboard">\n')
    # 绿板（直角）
    L.append(f'  <rect x="0" y="0" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    # 内嵌芯片 icon（居中、不旋转：引脚朝上下，与排针自然对应）
    L.append('  <g transform="translate(300 300) scale(%.3f)">\n' % U)
    L.append(_icon_inner())
    L.append('  </g>\n')
    # 排针孔：下排 3（EN/GND/SW = cn0/1/2），上排 2（FB/VIN = cn4/3），左→右 x=100/300/500
    bot_x = [100, 300, 500]
    top_x = [100, 500]
    y_bot, y_top = 500, 100
    def pad(cn, x, y):
        L.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'cx="{x:.1f}" cy="{y:.1f}" r="{pad_r:.1f}" '
                 f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        L.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    for cn, x in zip(BOT, bot_x):
        pad(cn, x, y_bot)
    for cn, x in zip(TOP, top_x):
        pad(cn, x, y_top)
    # 数字标注：竖排（逆时针旋转 90°）、居中于焊盘（与已验证的 CH340E 转接板一致：
    # 文字 fs=60、dominant-baseline="central"、text-anchor="middle"、rotate(-90) 绕文字中心；
    # 数字中心在焊盘中心上方/下方 76 单位：下排焊盘 cy=500 → 锚 y=424；
    # 上排焊盘 cy=100 → 锚 y=176（单字符）。Fritzing 支持字体 DroidSans。
    for cn, x in zip(BOT, bot_x):
        L.append(f'  <text x="{x:.1f}" y="424" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 424)">{cn + 1}</text>\n')
    for cn, x in zip(TOP, top_x):
        L.append(f'  <text x="{x:.1f}" y="176" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} 176)">{cn + 1}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# -------------------------------------------------------------- schematic
def gen_schematic_svg():
    """矩形封装符号（SOT-23-5）。按 datasheet SOT23-5 pinout 图（左侧 1,2,3 上→下、
    右侧 5,4 上→下——与官方 SOT-23-5 core 上下排一致，旋转 90° 表达）。
    AGENTS §5 矩形符号规则：名/数字/引线同色黑、整图同字号 FN=35；
    左列 3 + 右列 2。"""
    P = 100
    WIRE = 130
    CH = 35
    FN = 35
    BASELINE_OFF = round(FN * 0.35)
    max_len = max(len(n) for n in PINS)        # 3 (VIN/GND)
    CORNER = (max_len + 1) * int(FN * 0.58)    # 4×20 = 80
    n_left = len(BOT)                          # 3
    n_right = len(TOP)                         # 2
    h_left = n_left * P + 2 * CORNER
    h_right = n_right * P + 2 * CORNER
    BH = max(h_left, h_right)
    BW = 720
    BX0, BY0 = 340, 200
    BX1 = BX0 + BW
    BY1 = BY0 + BH
    # 左列对齐顶部、右列垂直居中
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
    # 左列 pin1,2,3 上→下
    for i, cn in enumerate(BOT):
        y = BY0 + CORNER + P // 2 + i * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{cn + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 右列 pin5(FB)=cn4 与左 pin1(EN) 平齐、pin4(VIN)=cn3 与左 pin3(SW) 平齐：
    # 右列两脚分别落在左列第 1 行与第 3 行的 y（框高由左列 3 行决定）。
    right_rows = [0, 2]            # 对应 BOT 的行下标（pin5->行1、pin4->行3）
    for cn, i in zip(TOP, right_rows):
        y = BY0 + CORNER + P // 2 + i * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{cn + 1}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    CHIP_FS = 60
    CHIP_Y = BY0 + BH // 2 + round(CHIP_FS * 0.35)
    L.append(f'  <text x="{BX0 + BW // 2}" y="{CHIP_Y}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(SCHEM_LABEL)}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（SOT23-5 真实封装）：本体 2.9×1.6mm 居中；
    焊盘 0.6(宽,x)×1.2(长,y)mm，3 列 x=-0.95/0/+0.95、e=0.95；
    两行焊盘中心距 2.6mm（row=±1.3）：下排 connector0/1/2 = pin1/2/3，
    上排 connector4/3 = pin5/4（pin5 左、pin4 右）。
    丝印：本体左右两侧各一条竖线（x=±1.45，y -0.8..0.8），不画上下横线以避开焊盘；
    pin1 实心圆在 1 脚（EN，下排最左焊盘）左侧，与焊盘中心同一 y。"""
    pw, pl = 0.6, 1.2
    pitch = 0.95
    row = 1.3
    x0 = -pitch                     # 最左列 -0.95
    xs = [x0, x0 + pitch, x0 + 2 * pitch]
    pads, silk = [], []
    # 下排 pin1,2,3 = cn0,1,2（左→右，y=+row）
    for cn, x in zip(BOT, xs):
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 上排 pin5(FB)=cn4 左、pin4(VIN)=cn3 右（y=-row）；跳过中间列(0) —— 只有两列
    top_xs = [xs[0], xs[2]]              # -0.95, +0.95
    for cn, x in zip(TOP, top_xs):
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 本体丝印：左右两条竖线（本体左右边缘，只在本体高度内，不覆盖上下焊盘）
    silk.append('<line x1="-1.45" y1="-0.8" x2="-1.45" y2="0.8" stroke="#f0f0f0" stroke-width="0.12"/>')
    silk.append('<line x1="1.45" y1="-0.8" x2="1.45" y2="0.8" stroke="#f0f0f0" stroke-width="0.12"/>')
    # pin1 实心圆：直径 0.5mm（r=0.25），在 1 脚（EN，下排最左焊盘 x=-0.95,y=1.3）左侧；
    # 焊盘左缘 -1.25，圆点右缘距焊盘 0.12 空隙 → 心 cx=-1.62，cy=1.3
    silk.append('<circle cx="-1.62" cy="1.3" r="0.25" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    M = 0.15
    vb_x0 = -1.62 - 0.25 - M          # pin1 圆左缘 + 边距
    vb_x1 = 1.45 + M
    vb_y0 = -(row + pl / 2) - M          # -(1.3+0.6)-0.15 = -2.05
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
