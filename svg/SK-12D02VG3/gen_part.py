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

# ★★ 板边相位＝**半格**（AGENTS §3b：转接板不许影响板外孔的插拔 ✓，2026-09-27 ✓）：
#   板框四周各让 50（内部单位 = 半格 = 1.27mm）⇒ 板边落在两排孔正中 ✓；
#   针脚坐标一个不动 ✓ ⇒ 已有 sketch 不用改 ✓。
#   （本行由 tools/bb_inset.py 写入 ✓；改完必跑 audit_green_board.py +
#     check_inside_board.py ✓）
# ⚠ **2026-10-18 起这条不再适用于本件** ✗：面包板视图已改成**直接画本体**（没有绿色转接板 ✓，
#   用户定：现实里没有转接板，2.0mm 脚距直接接杜邦线 ✓）⇒ `INSET` 二字**已不再被用到** ✓；
#   `audit_green_board.py` / `check_inside_board.py` 对本件自然为“不是绿板”✓（不报违规 ✓）。
INSET = 50
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
ACT_W, ACT_L = 2.00, 2.50                  # 拨柄（宽 × 伸出长度）；宽 2 与行程 2 TRAVEL 同为图纸标注

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- SK-12D02VG3 -->\n'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def knob_path(cx, cy, u, body_h, kw, kl, kx_off, notch_w=1.00, notch_d=0.60):
    """拨柄轮廓（用户 2026-09-17 按图纸定）：

    · **左边缘对齐本体中线**（图纸：拨柄左边线 = 本体中心线）⇒ 调用时 kx_off 取 kw/2；
    · 与本体相接的一侧**直角**（拨柄是插进本体的）；
    · 外端**也是直角**（不打圆角），底边中间开一个 **V 型缺口**（与杆帽契合）；
      V 尺寸图纸未给，取宽 1.00 / 深 0.60（= 拨柄宽的一半 / 0.3 倍）。

    cx/cy = 元件中心，kx_off = 拨柄中心相对元件中心的水平偏移。
    """
    y0 = cy + body_h / 2.0 * u                 # 本体下边缘
    y1 = y0 + kl * u                           # 拨柄外端
    xl = cx + (kx_off - kw / 2.0) * u
    xr = cx + (kx_off + kw / 2.0) * u
    xc = (xl + xr) / 2.0
    nw, nd = notch_w * u / 2.0, notch_d * u
    return (f"M {xl:.3f} {y0:.3f} L {xr:.3f} {y0:.3f} L {xr:.3f} {y1:.3f} "
            f"L {xc + nw:.3f} {y1:.3f} L {xc:.3f} {y1 - nd:.3f} L {xc - nw:.3f} {y1:.3f} "
            f"L {xl:.3f} {y1:.3f} Z")


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """俯视图：深灰本体 8.6 × 4.4 + 下边缘伸出的白色拨柄 + pin1 圆点 + 丝印名。

    拨柄（用户 2026-09-17 按图纸定）：宽 2.00、**左边缘对齐本体中线**、与本体相接一侧
    与**外端都是直角**（外端底边中间开 V 型缺口，见 knob_path）。
    """
    hw, hh = BODY_W / 2.0, BODY_H / 2.0
    W = BODY_W + 1.0
    H = BODY_H + ACT_L + 1.0
    x0, y0 = -(hw + 0.5), -(hh + 0.5)
    L = [SVG_HDR,
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
         f'viewBox="{x0:.2f} {y0:.2f} {W:.2f} {H:.2f}">\n',
         '  <g id="icon">\n']
    L.append(f'    <path d="{knob_path(0, 0, 1.0, BODY_H, ACT_W, ACT_L, ACT_W / 2.0)}" '
             f'fill="#e8e8e8" stroke="none"/>\n')                          # 拨柄（左缘对齐本体中线）
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
    """面包板视图 = **直接复用 icon 图形**（用户 2026-10-18 定 ✓）。

    现实里**没有转接板**：这颗开关脚距 2.0mm（最外两脚 8.2mm），插不进面包板孔，
    是**焊上杜邦线**用的 ⇒ 图上就画本体 1:1，五个脚按真实位置标成金色焊盘，
    接线时把杜邦线接到对应焊盘即可。

    坐标 1 单位 = 1 mm（与本库 `PinHeader-1xN` 同一写法，**不做** 100:2.54 的排针换算）；
    `PAD_Y` 与 PCB 视图同一组数（-4.10 / -2.00 / 0 / +2.00 / +4.10 ⇒ 2.0mm 间距、8.2mm 跨度 ✓）。
    """
    W, H = 9.60, 7.90                      # 本体 8.6×4.4 + 拨柄 2.5 + 四周留白
    # ★★ `viewBox` 原点必须是 (0,0) ✓（Fritzing 的摆放口径 = **viewBox 的 min 角** 对齐到
    #   sketch 的 `loc` ✓；拿负原点写会让件的坐标与 sketch 里算的坐标差一个 (|minx|,|miny|) ✗
    #   —— 2026-10-18 实测踩过：导线端点比焊盘偏了 (4.80, 2.70) mm ✗，用户截图指出 ✓）。
    #   ⇒ 图形自己平移到 (OX, OY)：本体中心 = (4.80, 2.70)，焊盘那排仍在中心线上 ✓
    OX, OY = 4.80, 2.70
    hw, hh = BODY_W / 2.0, BODY_H / 2.0
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
         f'viewBox="0 0 {W:.2f} {H:.2f}">\n',
         ' <g id="breadboard">\n']
    # 与 icon 同一套形状：拨柄（左缘对齐本体中线）→ 本体 → pin1 标记
    L.append(f'  <path d="{knob_path(OX, OY, 1.0, BODY_H, ACT_W, ACT_L, ACT_W / 2.0)}" '
             f'fill="#e8e8e8" stroke="none"/>\n')
    L.append(f'  <rect x="{OX - hw:.3f}" y="{OY - hh:.3f}" width="{BODY_W:.2f}" '
             f'height="{BODY_H:.2f}" fill="#2b2b2b" stroke="none"/>\n')
    L.append(f'  <circle cx="{OX - hw + 0.75:.3f}" cy="{OY - hh + 0.75:.3f}" r="0.30" '
             f'fill="#c0c0c0" stroke="none"/>\n')
    L.append(f'  <text x="{OX:.2f}" y="{OY - 1.15:.2f}" font-size="0.75" fill="#d0d0d0" '
             f'text-anchor="middle" font-family="DroidSans">{ICON_LABEL}</text>\n')
    # 五个脚 = 真实焊盘位置（金色环 + 中心孔），编号 1..5 写在焊盘下方（本体里）
    #   ★ 脚号 → x 的映射与 PCB 视图**同一份口径**：PAD_Y 的次序是 (pin5,1,2,3,4) ✓
    x_by_pin = {"1": PAD_Y[1], "2": PAD_Y[2], "3": PAD_Y[3], "4": PAD_Y[4], "5": PAD_Y[0]}
    for cn, num, _desc in CONN:
        x = OX + x_by_pin[num]
        L.append(f'  <circle id="connector{cn}pin" connectorname="{esc(num)}" cx="{x:.2f}" '
                 f'cy="{OY:.2f}" r="0.55" fill="#d4af37" stroke="#8a6d00" stroke-width="0.12"/>\n')
        L.append(f'  <circle cx="{x:.2f}" cy="{OY:.2f}" r="0.28" fill="#2b2b2b"/>\n')
        L.append(f'  <text x="{x:.2f}" y="{OY + 1.66:.2f}" font-size="0.62" fill="#c8c8c8" '
                 f'text-anchor="middle" font-family="DroidSans">{num}</text>\n')
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
    # 框内**不写**脚名（用户 2026-09-17：截图里那个位置的 4/5 是原图细节错误）
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
    # pin1 标记：在 pin1 焊盘**正上方**（用户 2026-09-17 定）
    silk.append(f'<circle cx="{C + PAD_Y[1]:.3f}" cy="{C - hh + 0.75:.3f}" r="0.30" '
                f'fill="#f0f0f0" stroke="none"/>')
    # ★★ 2026-10-18 修 ✗：它是 **THT 开关** ⇒ 5 个焊盘**两层都要有铜** ✓
    #   Fritzing 的写法（与库仓 `PinHeader-1xN` **同构** ✓）：`copper0` **嵌在** `copper1` 里 ✓
    #   ✗ 原来写的是 `<g id="copper0"/>`（**空组** ✗）⇒ 实际是**单面焊盘** ✗
    #   （实测：载板布线时 `part_pads` 报 `layer=copper1, thr=False` ✓）
    pcb = ('  <g id="copper1">\n    <g id="copper0">\n'
           + "\n".join(pads) + '\n    </g>\n  </g>\n  <g id="silkscreen">\n'
           + "\n".join(silk) + "\n  </g>\n")
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" '
            f'viewBox="0 0 {W:.1f} {H:.1f}">\n'
            + pcb + '</svg>\n')


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
            f'    <pcbView>\n     <p layer="copper0" svgId="connector{cn}pin"/>\n'
            f'     <p layer="copper1" svgId="connector{cn}pin"/>\n    </pcbView>\n'
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
            f'    <layer layerId="copper0"/>\n    <layer layerId="copper1"/>\n'
            f'    <layer layerId="silkscreen"/>\n   </layers>\n  </pcbView>\n'
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
