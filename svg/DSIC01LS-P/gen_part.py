#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 DSIC01LS-P (XKB 贴片 1 位 DIP 开关, SPST)。

四个视图（AGENTS.md §2）：icon → breadboard → schematic → pcb。

数据来源
========
1) 规格书 `D:\\Downloads\\DSIC01LS-P.pdf`（XKB Connection，DSIC01~DSIC12 系列，1/1 页）：
   · 型号表：`DSIC01LS-P` → NO.OF POS = **1**、DIM.A = 2.54（= 1 位 × 2.54 位距）、
     Projection(P) 型（**侧拨**，拨柄从侧面伸出）；
   · 规格：Contact Rating 25mA/24V DC、Travel 1.0mm、Life 3000 cycles、−20~+70°C；
   · 材质：Cover = Pa66 黑、Keystake = Pa66 白、Base = Pa9t 白、Terminal = 铜合金镀锡；
   · 图纸上的引脚/丝印：0.60 脚宽、0.90 脚厚、1.54 首脚到边、本体宽 6.10、
     P.C.B LAYOUT 焊盘 **1.10(宽) × 1.70(高)**；
   · 剖视图里的 "1 2 3 4 5" 与那张 LAYOUT 都是**多位的示例图**，1 位型只有 **2 个脚**（SPST）。
2) **嘉立创封装**（用户 2026-09-17 提供 `D:\\Downloads\\SW-SMD-DSIC01LS-P_2026-09-17.svg`）：
   2 个 RECT 焊盘 **1.10(x) × 1.80(y)**、中心距 **9.20mm**（相对本体中心 ±4.60，pin1 在下）；
   丝印 = 本体外框 **4.056 × 6.20mm** + 拨柄滑槽框 1.27×3.556 + 拨柄位置框 1.27×1.143
   + 文字 `ON`（左上）与 `1`（下侧，pin1 那一端）。**PCB 按立创取值**（与图纸的
   1.10/1.70 互证，高差 0.1mm 取立创）。

引脚命名：1 位 SPST，无极性也无功能名，连接器就叫 **1 / 2**（2 脚）。

用法：python gen_part.py
"""
import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "DSIC01LS-P"
FZPZ = "DSIC01LS-P.fzpz"

# (connector id, 脚号, 说明)：立创把 number=1 的焊盘放在**下方**（y=+4.6），丝印 "1" 也在下方
CONN = [(0, "1", "SPST terminal 1 (side marked '1')"),
        (1, "2", "SPST terminal 2 (other end)")]

ICON_LABEL = "DSIC01"
TITLE = "DSIC01LS-P DIP Switch (SMD, 1 position, SPST)"
LABEL = "SW"
PACKAGE = "SMD DIP-2 (4.06 x 6.20 mm)"
FAMILY = "DIP Switch"

# ---- 几何（mm）--------------------------------------------------------------
# 本体尺寸与引脚宽度：用户 2026-09-17 实测（1 位时本体宽 = 一个位距 2.54、长 6.10，
# 引脚宽 1.54）。注意立创丝印框量出来是 4.056 × 6.20，比实物宽不少（大概是含拨柄
# 行程余量），这里以**实物**为准。
BODY_W, BODY_H = 2.54, 6.10       # 本体（俯视 宽 × 长）
PAD_W, PAD_H = 1.54, 1.80         # 焊盘：宽 = 引脚宽 1.54（实测），长 1.80（立创）
PAD_DY = 4.60                     # 焊盘中心到本体中心（中心距 9.20 - 6.10 = 两侧各 1.55）
SLOT_W, SLOT_H = 1.27, 3.556      # 拨柄滑槽框（立创）
KNOB_W, KNOB_H = 1.27, 1.143      # 拨柄位置框（立创）

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- DSIC01LS-P -->\n'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """贴片 DIP 开关俯视图：黑本体 + 白色拨柄 + 丝印 ON/1（**水平居中**）+ 两端焊盘。

    拨柄（用户 2026-09-17）：拨动方向是**上下** ⇒ 拨柄在**上**，「**底线**」齐本体中线
    （整体落在中线上方）；滑槽框表示行程范围，保持居中。
    """
    hw, hh = BODY_W / 2.0, BODY_H / 2.0
    x0, x1 = -(BODY_W / 2 + 0.2), (BODY_W / 2 + 0.2)
    y0, y1 = -(PAD_DY + PAD_H / 2 + 0.2), (PAD_DY + PAD_H / 2 + 0.2)
    L = [SVG_HDR,
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0:.2f}mm" height="{y1 - y0:.2f}mm" '
         f'viewBox="{x0:.2f} {y0:.2f} {x1 - x0:.2f} {y1 - y0:.2f}">\n',
         '  <g id="icon">\n']
    for sy in (-1, 1):                                     # 两端焊盘
        L.append(f'    <rect x="{-PAD_W / 2:.3f}" y="{sy * PAD_DY - PAD_H / 2:.3f}" '
                 f'width="{PAD_W:.2f}" height="{PAD_H:.2f}" fill="#c0c0c0" stroke="none"/>\n')
    L.append(f'    <rect x="{-hw:.3f}" y="{-hh:.3f}" width="{BODY_W:.3f}" height="{BODY_H:.2f}" '
             f'fill="#2b2b2b" stroke="none"/>\n')
    L.append(f'    <rect x="{-SLOT_W / 2:.3f}" y="{-SLOT_H / 2:.3f}" width="{SLOT_W:.2f}" '
             f'height="{SLOT_H:.2f}" fill="none" stroke="#7a7a7a" stroke-width="0.10"/>\n')
    L.append(f'    <rect x="{-KNOB_W / 2:.3f}" y="{-KNOB_H:.3f}" width="{KNOB_W:.2f}" '
             f'height="{KNOB_H:.2f}" fill="#e8e8e8" stroke="none"/>\n')      # 拨柄：在上、底线齐中线
    L.append(f'    <text x="0" y="{-hh + 1.05:.2f}" font-size="0.85" '
             f'fill="#d0d0d0" text-anchor="middle" font-family="DroidSans">ON</text>\n')
    L.append(f'    <text x="0" y="{hh - 0.35:.2f}" font-size="0.85" '
             f'fill="#d0d0d0" text-anchor="middle" font-family="DroidSans">1</text>\n')
    L.append('  </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = 绿色转接板（AGENTS §3b：SMD 元件不能直插面包板）：本体竖放居中 +
    **上下各 1 个 2.54mm 排针**。

    坐标 100 单位 = 2.54mm：实物焊盘中心距 9.20mm → 取最近的 2.54 整倍数 **10.16mm**
    （针 y=100 / 900，间距 800 单位 = 20.32mm，比元件含焊盘的 11mm 宽得多）；这个行距是
    为了让**数字能落在焊盘内侧**（AGENTS §3b，用户 2026-09-17 定为硬规则）：数字占焊盘
    内侧约 81 单位，元件含焊盘半高 216 单位，两者之间才留得下（各留 72 单位 ≈ 1.8mm）。
    板 400×1000（10.16×25.40mm），pin1 在**下**（与 icon/PCB 同向）。
    """
    U = 39.37
    bw, bh = 400, 1000
    # ★★ 板边相位＝**半格**（AGENTS §3b：转接板不许影响板外孔的插拔 ✓，2026-09-27 ✓）：
    #   四周各让 50（半格）⇒ 板边落在两排孔正中 ✓；针脚一个不动 ✓；
    #   板心仍为 (200,500) ✓ ⇒ 本体不用挪 ✓。
    INSET = 50
    cx, cy = 200, 500
    pad_r, hole_r = 1.0 * U, 0.485 * U
    y_pins = [100, 900]
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
         f'height="{bh / 100 * 2.54:.2f}mm" viewBox="0 0 {bw} {bh}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="{INSET}" y="{INSET}" width="{bw - 2 * INSET}" height="{bh - 2 * INSET}" '
         f'fill="#00aa44" stroke="#00772f" '
         f'stroke-width="5"/>\n']
    # 元件（1:1）：两端焊盘各一条 + 本体 + 拨柄槽/拨柄
    for sy in (-1, 1):
        yy = cy - sy * PAD_DY * U
        L.append(f'  <rect x="{cx - PAD_W / 2 * U:.1f}" y="{yy - PAD_H / 2 * U:.1f}" '
                 f'width="{PAD_W * U:.1f}" height="{PAD_H * U:.1f}" fill="#c0c0c0" '
                 f'stroke="none"/>\n')
    L.append(f'  <rect x="{cx - BODY_W / 2 * U:.1f}" y="{cy - BODY_H / 2 * U:.1f}" '
             f'width="{BODY_W * U:.1f}" height="{BODY_H * U:.1f}" fill="#2b2b2b" stroke="none"/>\n')
    L.append(f'  <rect x="{cx - SLOT_W / 2 * U:.1f}" y="{cy - SLOT_H / 2 * U:.1f}" '
             f'width="{SLOT_W * U:.1f}" height="{SLOT_H * U:.1f}" fill="none" stroke="#7a7a7a" '
             f'stroke-width="4"/>\n')
    L.append(f'  <rect x="{cx - KNOB_W / 2 * U:.1f}" y="{cy - KNOB_H * U:.1f}" '
             f'width="{KNOB_W * U:.1f}" height="{KNOB_H * U:.1f}" fill="#e8e8e8" stroke="none"/>\n')
    for cn, y, label in ((0, y_pins[1], "1"), (1, y_pins[0], "2")):
        L.append(f'  <circle id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                 f'cx="{cx}" cy="{y}" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" '
                 f'stroke-width="4"/>\n')
        L.append(f'  <circle cx="{cx}" cy="{y}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
        ty = y + 81 if y < cy else y - 81       # 数字放排针**内侧**（朝板心，AGENTS §3b）
        L.append(f'  <text x="{cx}" y="{ty}" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {cx} {ty})">{label}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """原理图：**开关图形符号**（照用户 2026-09-17 给的截图）—— 上下两个空心圆
    （pin1 在下、pin2 在上）+ 一条斜线作开关刀（从 pin1 圆边向右上斜出、**不接** pin2）；
    **不画本体框**。引脚线从圆圈外侧竖直引出，脚号标在引线左侧。

    引脚线 / 圆圈 / 脚号同色黑、整图同字号 35；物理尺寸用 in（1000 单位 = 1in）。
    """
    P, WIRE, FN, R = 100, 130, 35, 12
    BX = 400                                  # 两脚同轴（竖直）
    Y1 = 560                                  # pin1（下）
    Y2 = Y1 - P                               # pin2（上）
    VBX, VBY = BX - 90, Y2 - R - WIRE - 20
    VBW, VBH = 200, (Y1 + R + WIRE + 20) - VBY
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" '
         f'height="{VBH / 1000:.6f}in" viewBox="{VBX} {VBY} {VBW} {VBH}">\n',
         ' <g id="schematic">\n']
    for cn, y, sy in ((0, Y1, 1), (1, Y2, -1)):     # sy：+1 向下（pin1）、-1 向上（pin2）
        y_end = y + sy * (R + WIRE)
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                 f'x1="{BX}" y1="{y + sy * R}" x2="{BX}" y2="{y_end}" stroke="#000000" '
                 f'stroke-width="5"/>\n')
        L.append(f'  <rect class="terminal" id="connector{cn}terminal" x="{BX - 11}" '
                 f'y="{y_end - 11}" width="22" height="22" fill="none" stroke="none"/>\n')
        L.append(f'  <circle cx="{BX}" cy="{y}" r="{R}" fill="none" stroke="#000000" '
                 f'stroke-width="5"/>\n')
        L.append(f'  <text x="{BX - FN}" y="{y + sy * (R + WIRE // 2) + 12}" font-size="{FN}" '
                 f'fill="#000000" font-family="DroidSans">{cn + 1}</text>\n')
    # 开关刀：从 pin1 圆边向右上斜出（不接 pin2）
    L.append(f'  <line x1="{BX + 9}" y1="{Y1 - 9}" x2="{BX + 40}" y2="{Y1 - 100}" '
             f'stroke="#000000" stroke-width="5"/>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图：**按嘉立创封装** —— 2 个 RECT 焊盘 1.10×1.80（中心距 9.20，pin1 在下）、
    丝印外框 4.056×6.20 + 拨柄滑槽框 + 拨柄位置框 + `ON` / `1` 文字。"""
    C = 6.0                                   # 画布中心（12 × 12mm）
    W = H = 12.0
    pads, silk = [], []
    for cn, sy in ((0, 1), (1, -1)):          # pin1 在下方（y 正）
        pads.append(f'<rect id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                    f'x="{C - PAD_W / 2:.3f}" y="{C + sy * PAD_DY - PAD_H / 2:.3f}" '
                    f'width="{PAD_W:.2f}" height="{PAD_H:.2f}" fill="#F7BD13" stroke="none"/>')
    hw, hh = BODY_W / 2, BODY_H / 2
    silk.append(f'<rect x="{C - hw:.3f}" y="{C - hh:.3f}" width="{BODY_W:.3f}" '
                f'height="{BODY_H:.2f}" fill="none" stroke="#f0f0f0" stroke-width="0.1524"/>')
    silk.append(f'<rect x="{C - SLOT_W / 2:.3f}" y="{C - SLOT_H / 2:.3f}" width="{SLOT_W:.2f}" '
                f'height="{SLOT_H:.2f}" fill="none" stroke="#f0f0f0" stroke-width="0.1524"/>')
    silk.append(f'<rect x="{C - KNOB_W / 2:.3f}" y="{C:.3f}" width="{KNOB_W:.2f}" '
                f'height="{KNOB_H:.2f}" fill="none" stroke="#f0f0f0" stroke-width="0.1524"/>')
    # ON / 1：立创给的是相对本体中心的 (-1.524, -2.032) 与 (-0.127, +2.921)，但那套坐标
    # 是基于它 4.056 宽的丝印框；实物本体只有 2.54 宽 ⇒ 照抄会溢出到体外，故 x 改居中。
    silk.append(f'<text x="{C:.2f}" y="{C - 2.032:.2f}" font-size="0.85" '
                f'fill="#f0f0f0" text-anchor="middle" font-family="DroidSans">ON</text>')
    silk.append(f'<text x="{C:.2f}" y="{C + 2.921:.2f}" font-size="0.85" '
                f'fill="#f0f0f0" text-anchor="middle" font-family="DroidSans">1</text>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" '
            f'viewBox="0 0 {W:.1f} {H:.1f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for cn, num, desc in CONN:
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(num)}" type="male">\n'
            f'   <description>pin {num} = {esc(desc)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cn}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{cn}pin" terminalId="connector{cn}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{cn}pin"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>1</version>\n <date>2026-09-17</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>DSIC01LS-P</tag>\n  <tag>DIP switch</tag>\n'
            f'  <tag>switch</tag>\n  <tag>SMD</tag>\n  <tag>SPST</tag>\n  <tag>XKB</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">2</property>\n'
            f'  <property name="ratings">25mA / 24V DC</property>\n </properties>\n'
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
        for view in ("icon", "breadboard", "schematic", "pcb"):
            name = f"svg.{view}.{PART_ID}_{view}.svg"
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
