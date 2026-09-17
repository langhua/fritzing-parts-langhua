#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 SK-12D02VG3 (SPDT 卧式拨动开关, DIP5)。

四个视图（AGENTS.md §2）：icon → breadboard → schematic → pcb。

数据来源
========
1) 规格书 `D:\\Downloads\\SK-12D02VG3.pdf`（碩方 SK-12D02-VG 系列）：
   · `Operation: **DIP3+2PIN** / 卧式二档`、尺寸 **L8.6 × W4.4 × H4.70**、行程 TRAVEL 2mm；
   · 电气 0.3A / 24V DC；端子镀银黄铜；
   · **CIRCUIT DIAGRAM**：三个端子（左空心中实心右空心）——**中间是公共端(COM)**、
     拨柄决定接通左还是右 ⇒ **SPDT**；另有两个固定/定位脚（P.C.B LAYOUT 里两端那两个方焊盘）。
   · P.C.B LAYOUT 尺寸：中间三脚间距 **2**、跨度 **4**、最外侧两脚跨度 **8.2**（mm）。
2) **嘉立创封装**（用户 2026-09-17 提供 `D:\\Downloads\\SW-TH-SK-12D02VG3_2026-09-17.svg`）：
   5 个 TH 焊盘 —— `number 1/2/3` = 三个信号脚（椭圆 1.4×1.2mm、孔 ⌀0.7、间距 2.0mm）、
   `number 5/1`… 两端 = 两个固定脚（椭圆 1.2×2.0mm、孔 ⌀0.7）、最外跨距 **8.20mm**；
   丝印 = 本体框 **8.60 × 4.40mm**（上下两条横线 + 四段 1.10mm 短竖线，让开焊盘）。
   与规格书互证一致（8.2 / 4 / 2 都对得上）。

引脚命名（不猜功能名）：手册的 CIRCUIT DIAGRAM 只给了"中间=公共端"，两侧触点的 NO/NC
   没有明说，所以连接器名就用**嘉立创的脚号 1..5**，描述里写明"3 个 SPDT 端子（中间脚 2 =
   公共端）+ 2 个固定脚"。开关本体上没有丝印可依，故不致别名。

用法：python gen_part.py
"""
import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "SK-12D02VG3"
FZPZ = "SK-12D02VG3.fzpz"

# (connector id, 脚号, 说明) —— 1/2/3 = SPDT 端子（2 = COM）、4/5 = 固定脚
CONN = [(0, "1", "SPDT terminal (throw)"),
        (1, "2", "SPDT terminal (common, COM)"),
        (2, "3", "SPDT terminal (throw)"),
        (3, "4", "mounting / 固定脚"),
        (4, "5", "mounting / 固定脚")]

ICON_LABEL = "SK-12D02"
SCHEM_LABEL = "SK-12D02VG3"
TITLE = "SK-12D02VG3 Slide Switch (SPDT, DIP5)"
LABEL = "SW"
PACKAGE = "DIP3+2PIN (8.6 x 4.4 x 4.7 mm)"
FAMILY = "Slide Switch"

# ---- 几何（mm；立创 + 规格书互证）------------------------------------------
BODY_W, BODY_H = 8.60, 4.40       # 本体（俯视 长 × 宽）
BODY_T = 4.70                     # 本体高（侧面，icon 上看不出来）
PAD_Y = [-4.10, -2.00, 0.00, 2.00, 4.10]   # 5 个焊盘的 x（pin5,1,2,3,4；由 8.2/4/2 推出）
SIG_PAD_W, SIG_PAD_H = 1.40, 1.20          # 信号脚焊盘（pin1/2/3）
MP_PAD_W, MP_PAD_H = 1.20, 2.00            # 固定脚焊盘（pin4/5）
DRILL = 0.70                               # 孔径
SILK_ARM = 1.10                            # 丝印短竖线长（让开焊盘）
ACT_W, ACT_L = 1.60, 2.50                  # 拨柄（宽 × 伸出长度）

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- SK-12D02VG3 -->\n'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """俯视图：深灰本体 8.6 × 4.4 + **下边缘伸出的白色拨柄**（用户 2026-09-17 定）
    + pin1 圆点 + 丝印名。"""
    hw, hh = BODY_W / 2.0, BODY_H / 2.0
    W = BODY_W + 1.0
    H = BODY_H + ACT_L + 1.0
    x0, y0 = -(hw + 0.5), -(hh + 0.5)
    L = [SVG_HDR,
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
         f'viewBox="{x0:.2f} {y0:.2f} {W:.2f} {H:.2f}">\n',
         '  <g id="icon">\n']
    L.append(f'    <rect x="{-ACT_W / 2:.3f}" y="{hh:.3f}" width="{ACT_W:.2f}" '
             f'height="{ACT_L:.2f}" rx="0.2" ry="0.2" fill="#e8e8e8" stroke="none"/>\n')
    L.append(f'    <rect x="{-hw:.3f}" y="{-hh:.3f}" width="{BODY_W:.2f}" height="{BODY_H:.2f}" '
             f'fill="#2b2b2b" stroke="none"/>\n')                              # 本体
    L.append(f'    <circle cx="{-hw + 0.75:.3f}" cy="{-hh + 0.75:.3f}" r="0.30" fill="#c0c0c0" '
             f'stroke="none"/>\n')                                             # pin1 标记
    L.append(f'    <text x="0" y="-0.2" font-size="1.15" fill="#d0d0d0" text-anchor="middle" '
             f'font-family="DroidSans">{ICON_LABEL}</text>\n')
    L.append(f'    <text x="0" y="1.5" font-size="0.85" fill="#9a9a9a" text-anchor="middle" '
             f'font-family="DroidSans">SPDT</text>\n')
    L.append('  </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = 绿色转接板（AGENTS §3b 的精神：本体脚距 2.0/8.2mm **都插不进面包板**，
    所以把 5 个脚各引到一个 2.54mm 排针上）。

    坐标 100 单位 = 2.54mm：排针一排 x=100..500（恰居中于板中线 300）、y=100；
    元件横放在板中部（含拨柄 11.1 × 4.4mm），板 600×700（15.24×17.78mm）。
    """
    U = 39.37
    bw, bh = 600, 700
    cx, cy = 300, 400
    pad_r, hole_r = 1.0 * U, 0.485 * U
    xs = [100, 200, 300, 400, 500]
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
         f'height="{bh / 100 * 2.54:.2f}mm" viewBox="0 0 {bw} {bh}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="0" y="0" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" '
         f'stroke-width="5"/>\n']
    # 元件（1:1）：拨柄朝下
    L.append(f'  <rect x="{cx - ACT_W / 2 * U:.1f}" y="{cy + BODY_H / 2 * U:.1f}" '
             f'width="{ACT_W * U:.1f}" height="{ACT_L * U:.1f}" rx="8" ry="8" fill="#e8e8e8" '
             f'stroke="none"/>\n')
    L.append(f'  <rect x="{cx - BODY_W / 2 * U:.1f}" y="{cy - BODY_H / 2 * U:.1f}" '
             f'width="{BODY_W * U:.1f}" height="{BODY_H * U:.1f}" fill="#2b2b2b" stroke="none"/>\n')
    L.append(f'  <circle cx="{cx - BODY_W / 2 * U + 30:.1f}" cy="{cy - BODY_H / 2 * U + 30:.1f}" '
             f'r="12" fill="#c0c0c0" stroke="none"/>\n')
    for cn, x in zip(range(5), xs):
        L.append(f'  <circle id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                 f'cx="{x}" cy="100" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" '
                 f'stroke-width="4"/>\n')
        L.append(f'  <circle cx="{x}" cy="100" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
        L.append(f'  <text x="{x}" y="176" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x} 176)">{cn + 1}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """原理图（照用户 2026-09-17 给的截图，不用 AGENTS §5 的左右两列矩形框版式）：

    · 矩形框，框内**三个空心圆** = pin1/2/3 的框内端点；
    · 三个圆各向下引线，**穿出框底** ⇒ 底部三脚，框下从左到右 = **3、2、1**；
    · 框内一条横线 = 滑动件：**左半虚线、右半实线**（分界在中间那脚）；
    · 左/右各一个水平脚：左 = **5**、右 = **4**，与圆圈同一高度；
    · 框内只标脚名 5（左下）/ 4（右下）—— 与截图一致。

    引脚线/数字/框线同色黑、整图同字号 35；引脚数字在引线左侧（上下脚）/上方（左右脚）。
    """
    P, WIRE, CH, FN = 100, 130, 35, 35
    BX0, BY0 = 300, 200
    BW, BH = 400, 200
    BX1, BY1 = BX0 + BW, BY0 + BH
    Y_SIDE = BY0 + 80                         # 左右脚与圆圈同一高度
    R_CIRC = 20
    Y_BAR = Y_SIDE + R_CIRC + 15              # 滑动件的横线（在圆圈下方）
    X_MID = BX0 + BW // 2
    VBX, VBY = BX0 - WIRE - 20, BY0 - 20
    VBW, VBH = BW + 2 * WIRE + 40, BH + WIRE + 40
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" '
         f'height="{VBH / 1000:.6f}in" viewBox="{VBX} {VBY} {VBW} {VBH}">\n',
         ' <g id="schematic">\n',
         f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
         f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n']

    def terminal(cn, x, y):
        L.append(f'  <rect class="terminal" id="connector{cn}terminal" x="{x - 11}" y="{y - 11}" '
                 f'width="22" height="22" fill="none" stroke="none"/>\n')

    # 底部三个脚：框下从左到右 = 3、2、1（与截图一致）
    for i, cn in enumerate((2, 1, 0)):
        x = BX0 + 100 + i * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                 f'x1="{x}" y1="{Y_SIDE + R_CIRC}" x2="{x}" y2="{BY1 + WIRE}" stroke="#000000" '
                 f'stroke-width="5"/>\n')
        terminal(cn, x, BY1 + WIRE)
        L.append(f'  <text x="{x - FN}" y="{BY1 + 52}" font-size="{FN}" fill="#000000" '
                 f'font-family="DroidSans">{cn + 1}</text>\n')
        L.append(f'  <circle cx="{x}" cy="{Y_SIDE}" r="{R_CIRC}" fill="none" stroke="#000000" '
                 f'stroke-width="4"/>\n')
    # 左右两个脚：左 = 5、右 = 4
    for cn, sx in ((4, -1), (3, 1)):
        xe = BX0 if sx < 0 else BX1
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                 f'x1="{xe}" y1="{Y_SIDE}" x2="{xe + sx * WIRE}" y2="{Y_SIDE}" stroke="#000000" '
                 f'stroke-width="5"/>\n')
        terminal(cn, xe + sx * WIRE, Y_SIDE)
        L.append(f'  <text x="{xe + sx * WIRE // 2}" y="{Y_SIDE - 12}" font-size="{FN}" '
                 f'fill="#000000" text-anchor="middle" font-family="DroidSans">{cn + 1}</text>\n')
    # 滑动件：左半虚线、右半实线
    L.append(f'  <line x1="{BX0 + 100}" y1="{Y_BAR}" x2="{X_MID}" y2="{Y_BAR}" stroke="#000000" '
             f'stroke-width="5" stroke-dasharray="14 10"/>\n')
    L.append(f'  <line x1="{X_MID}" y1="{Y_BAR}" x2="{BX0 + 300}" y2="{Y_BAR}" stroke="#000000" '
             f'stroke-width="5"/>\n')
    # 框内脚名（照截图：只在左下写 5、右下写 4）
    L.append(f'  <text x="{BX0 + CH}" y="{BY1 - CH}" font-size="{FN}" fill="#000000" '
             f'font-family="DroidSans">5</text>\n')
    L.append(f'  <text x="{BX1 - CH}" y="{BY1 - CH}" font-size="{FN}" fill="#000000" '
             f'text-anchor="end" font-family="DroidSans">4</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图：**按嘉立创封装** —— 5 个 TH 焊盘（信号脚 1.4×1.2 / 固定脚 1.2×2.0、孔 ⌀0.7）
    + 本体丝印框 8.6×4.4（上下横线 + 四段短竖线）+ pin1 实心圆点。"""
    C = 6.0                                   # 画布中心（12×12mm）
    W = H = 12.0
    pads, silk = [], []

    def pad(cn, x, w, h):
        pads.append(f'<ellipse id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                    f'cx="{C + x:.3f}" cy="{C:.3f}" rx="{w / 2:.3f}" ry="{h / 2:.3f}" '
                    f'fill="#F7BD13" stroke="none"/>')
        pads.append(f'<circle cx="{C + x:.3f}" cy="{C:.3f}" r="{DRILL / 2:.3f}" fill="#0b2b3a" '
                    f'stroke="none"/>')

    pad(4, PAD_Y[0], MP_PAD_W, MP_PAD_H)      # pin5（最左）
    pad(0, PAD_Y[1], SIG_PAD_W, SIG_PAD_H)    # pin1
    pad(1, PAD_Y[2], SIG_PAD_W, SIG_PAD_H)    # pin2 = COM
    pad(2, PAD_Y[3], SIG_PAD_W, SIG_PAD_H)    # pin3
    pad(3, PAD_Y[4], MP_PAD_W, MP_PAD_H)      # pin4（最右）
    hw, hh = BODY_W / 2, BODY_H / 2
    silk.append(f'<line x1="{C - hw:.3f}" y1="{C - hh:.3f}" x2="{C + hw:.3f}" y2="{C - hh:.3f}" '
                f'stroke="#f0f0f0" stroke-width="0.1524"/>')
    silk.append(f'<line x1="{C - hw:.3f}" y1="{C + hh:.3f}" x2="{C + hw:.3f}" y2="{C + hh:.3f}" '
                f'stroke="#f0f0f0" stroke-width="0.1524"/>')
    for sx in (-1, 1):
        for sy in (-1, 1):
            silk.append(f'<line x1="{C + sx * hw:.3f}" y1="{C + sy * hh:.3f}" '
                        f'x2="{C + sx * hw:.3f}" y2="{C + sy * (hh - SILK_ARM):.3f}" '
                        f'stroke="#f0f0f0" stroke-width="0.1524"/>')
    silk.append(f'<circle cx="{C - hw + 0.75:.3f}" cy="{C - hh + 0.75:.3f}" r="0.30" '
                f'fill="#f0f0f0" stroke="none"/>')
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
            f' <title>{TITLE}</title>\n <tags>\n  <tag>SK-12D02VG3</tag>\n  <tag>switch</tag>\n'
            f'  <tag>slide switch</tag>\n  <tag>SPDT</tag>\n  <tag>DIP</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">5</property>\n'
            f'  <property name="ratings">0.3A / 24V DC</property>\n </properties>\n'
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
