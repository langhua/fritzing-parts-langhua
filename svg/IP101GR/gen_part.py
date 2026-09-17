#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 IP101GR (IC+ 10/100M 以太网 PHY, QFN-32)。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件（part.<id>.fzp + 4 个 svg.<view>.* + 本脚本）同目录，.fzpz 输出到仓库顶层 fzpz/。
打包规则：.fzpz 内部平铺，.fzp 的 image= 用子目录路径。

数据来源
========
1) 器件手册 `D:\\Downloads\\IP101GR.pdf`（IC Plus IP101G Preliminary DS, IP101G-DS-R01）：
   · 第 10 页 **Figure 3 IP101GR/GRI 32 Pin Diagram**（顶视图）—— 引脚几何/编号顺序的**权威**：
       底边 左→右 = 1..8、右边 下→上 = 9..16、顶边 右→左 = 17..24、左边 上→下 = 25..32；
       **pin1 标记在左下角**；图中央注明 `(GND on bottom of chip)` —— 即底板裸露焊盘。
   · 第 16~18 页 §3.2 IP101GR/GRI pin description —— 引脚功能（本脚本的脚名**按 Figure 3
     上的写法**，与表里的写法有出入时以图为准，同 CH347F 的规矩）。
     ★ 图纠正了表里的一个陷阱：表里写 `6,7,8,9 TXD[3:0]` / `15,16,17,18 RXD[3:0]`，
       图上是 **6=TXD3 7=TXD2 8=TXD1 9=TXD0**、**15=RXD3 16=RXD2 17=RXD1 18=RXD0**
       （即标号递减），照着表里的"直觉顺序"写就会把 TXD0/RXD0 放反。
   · 第 64 页 Figure 25 **32-PIN QFN Dimension**（本体 4×4、节距 0.4）。
     ★ 封装名以手册为准 = **QFN-32**（不是 VQFN-32，用户 2026-09-17 指正）；
       下面那份立创封装的**文件名**里带 "VQFN-32" 字样，但那只是它的命名习惯。
   · 底板裸露焊盘 = `GND`（手册原文）—— 但按 AGENTS §5「裸露焊盘必须独立成网」，
     本元件里名字用 **EPAD**、**不进任何 `<bus>`**：布线时要特意接到 GND。
2) **嘉立创/立创EDA 封装**（用户 2026-09-17 提供
   `D:\\Downloads\\VQFN-32-L4.0-W4.0-P0.40-BL-EP_2026-09-17.svg`）：
   16 进制实测（单位 0.254mm）：每边 8 个 OVAL 焊盘、节距 **0.400**、
   焊盘 **0.20(切向) × 0.38(径向)**、中心距本体中心 **±1.9173**（内缘 1.7275 / 外缘 2.1075）；
   中心 EPAD **2.8 × 2.8**；丝印为**四个 L 形角标**（角点 ±2.076、臂长 0.3736、线宽 0.1524）；
   pin1 标记在底边最左焊盘外侧。**PCB 焊盘/丝印按立创取值**（AGENTS §4.3 取证顺序）。

进度（按 AGENTS.md §2 芯片类工作流）：
  [x] 1. icon（QFN32 顶视图：黑体 4×4 + 四边金焊盘 + pin1 圆点）
  [x] 2. breadboard（绿色转接板 + 33 个 2.54mm 排针）
  [x] 3. schematic（矩形符号，四边逆时针 9/8/8/8 脚）
  [x] 4. pcb（QFN-32 4×4 P0.4 + 中心 EPAD，按立创）
  [x] 5. part.IP101GR.fzp + 打包 fzpz

用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "IP101GR"
FZPZ = "IP101GR.fzpz"

# 引脚名（**按 Figure 3 排列图上的写法**；0 = 底板裸露焊盘）
PIN_NAMES = {
    0:  "EPAD",              # 手册写 "GND on bottom of chip"，按 AGENTS §5 用 EPAD、独立成网
    1:  "TXER/FXSD",   2:  "X1",            3:  "X2",          4:  "COL/RMII",
    5:  "TXEN",        6:  "TXD3",          7:  "TXD2",        8:  "TXD1",
    9:  "TXD0",        10: "TXCLK/50M_CLKI", 11: "LED0/PHY_AD0", 12: "LED3/PHY_AD3",
    13: "VDD_IO",      14: "RXCLK/50M_CLKO", 15: "RXD3",       16: "RXD2",
    17: "RXD1",        18: "RXD0",          19: "RXDV/CRS_DV/FX_HEN",
    20: "CRS/LEDMOD",  21: "RXER/INTR_32",  22: "MDC",         23: "MDIO",
    24: "TEST_ON",     25: "ISET",          26: "MDI_RN",      27: "MDI_RP",
    28: "REGOUT",      29: "MDI_TN",        30: "MDI_TP",      31: "AVDD33",
    32: "RESET_N",
}

# 物理排列（Figure 3 顶视图，逆时针；pin1 在底边最左、pin1 标记在左下角）
#   底边 左→右 = 1..8、右边 下→上 = 9..16、顶边 右→左 = 17..24、左边 上→下 = 25..32
#   ❗这四个列表现在**只给 schematic 用**（四边符号）；面包板改成了成品转接板画法，
#     它的孔位另有排法（上排 32..17、下排 1..16），见 gen_breadboard_svg()。
BOTTOM = list(range(1, 9))
RIGHT = list(range(9, 17))
TOP = list(range(17, 25))          # 枚举时 x 从右往左，故此处仍写 17..24
LEFT = list(range(25, 33))
BOTTOM_WITH_PAD = [0] + BOTTOM     # 原理图底边：EPAD(0) 在最左，与 pin1/pin32 相邻（同 CH347F）

ICON_LABEL = "IP101GR"
SCHEM_LABEL = "IP101GR"
TITLE = "IP101GR 10/100M Ethernet PHY (QFN-32)"
LABEL = "U"
PACKAGE = "QFN-32"
FAMILY = "IC+ Ethernet PHY"

# ---- 封装几何（mm；见文件头数据来源 2）--------------------------------------
BODY = 4.0                 # 本体（塑体）4×4
TOT = 4.215                # 含焊盘外缘的总跨距 = 2 × 2.1075
PITCH = 0.4                # 节距
N_PER_SIDE = 8
PAD_W = 0.20               # 焊盘切向宽
PAD_L = 0.38               # 焊盘径向长
PAD_C = 1.9173             # 焊盘中心到本体中心（径向）
EPAD = 2.8                 # 中心裸露焊盘 2.8×2.8
SILK_CORNER = 2.076        # L 形角标的角点位置
SILK_ARM = 0.3736          # 角标臂长
SILK_W = 0.1524            # 角标线宽
PIN1_MARK = (-1.4, 2.51)   # pin1 标记（相对本体中心；立创把圆放在底边首盘的外侧 = SVG 的 +y 方向）

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- IP101GR QFN-32 -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _centers():
    """每边 8 个焊盘中心（沿边方向），对称于本体中心 —— icon 坐标系是 0..TOT。"""
    c0 = TOT / 2.0 - (N_PER_SIDE - 1) * PITCH / 2.0        # 0.7075
    return [c0 + i * PITCH for i in range(N_PER_SIDE)]


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """QFN32 顶视图 icon：黑体 4.0 + 四边金焊盘（体外段）+ pin1 圆点 + 丝印名。
    画法照 svg/CH347F（同族，已过验收）：坐标 0..TOT、焊盘只画露出本体的那一段。"""
    c = _centers()
    m = (TOT - BODY) / 2.0                                 # 0.1075
    out = [SVG_HDR,
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{TOT:.2f}mm" height="{TOT:.2f}mm" '
           f'viewBox="0 0 {TOT:.3f} {TOT:.3f}">\n',
           '  <g id="icon">\n']
    out.append(f'    <rect x="{m:.3f}" y="{m:.3f}" width="{BODY:.1f}" height="{BODY:.1f}" '
               f'fill="#303030" stroke="none"/>\n')
    for x in c:
        out.append(f'    <rect x="{x - PAD_W / 2:.3f}" y="0" width="{PAD_W:.2f}" height="{m:.3f}" '
                   f'fill="#f7bf13" stroke="none"/>\n')                       # 上
        out.append(f'    <rect x="{x - PAD_W / 2:.3f}" y="{TOT - m:.3f}" width="{PAD_W:.2f}" '
                   f'height="{m:.3f}" fill="#f7bf13" stroke="none"/>\n')      # 下
        out.append(f'    <rect x="0" y="{x - PAD_W / 2:.3f}" width="{m:.3f}" height="{PAD_W:.2f}" '
                   f'fill="#f7bf13" stroke="none"/>\n')                       # 左
        out.append(f'    <rect x="{TOT - m:.3f}" y="{x - PAD_W / 2:.3f}" width="{m:.3f}" '
                   f'height="{PAD_W:.2f}" fill="#f7bf13" stroke="none"/>\n')  # 右
    # pin1 圆点：底边最左焊盘的内侧（同 CH347F 的"左下角"位置）
    out.append(f'    <circle cx="{c[0]:.3f}" cy="{TOT - c[0]:.3f}" r="0.18" fill="#c0c0c0" '
               f'stroke="none"/>\n')
    cx = TOT / 2.0
    out.append(f'    <text x="{cx:.3f}" y="{cx - 0.12:.2f}" font-size="0.60" fill="#c0c0c0" '
               f'text-anchor="middle" font-family="DroidSans">{ICON_LABEL}</text>\n')
    out.append(f'    <text x="{cx:.3f}" y="{cx + 0.72:.2f}" font-size="0.32" fill="#c0c0c0" '
               f'text-anchor="middle" font-family="DroidSans">QFN32</text>\n')
    out.append('  </g>\n</svg>\n')
    return "".join(out)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = **淘宝那种成品 QFN32/QFP32 转接板**（用户 2026-09-17 给商品图纠正）。

    商品规格（用户给的参数）：**40.64 × 20.25mm**、孔距 2.54mm、孔径 **1.0mm**、板厚 1.6mm；
    正面引脚间距 0.65mm、反面 0.8mm（本视图画正面那一套）。
    孔位（与实物同序、逆时针）：上排 16 个 = pin32..17 左→右、下排 16 个 = pin1..16 左→右。
    中间是 QFN32 的 32 条指状焊盘（**整体转 45°**）+ 中央散热盘，两者之间**留缝**。

    ★ EPAD 不给孔（用户 2026-09-17 定）：实物中央散热盘上没有引线孔 —— 芯片的 EP 与某个
      接地引脚是**另一面飞线**连通的。所以这里只保留 EPAD 这个 connector（指向中央散热盘，
      要接线时自己从它拉线），不再画引线孔；指状线与中央盘也不相连（同一条道理）。

    坐标 100 单位 = 2.54mm：板 1600×800 单位（40.64×**20.32**mm —— 高取 20.32 是为了让两排孔
    的行距 15.24mm = 6×2.54 落在网格上，与商品标的 20.25 差 0.07mm）。
    孔心 x=100..1600、y=100/700，全部落 100 整数倍；左右边距 1.27mm、上下边距 2.54mm
    （与实物一致：左右紧、上下松）。板厚 1.6mm 是厚度方向，顶视看不出来。
    数字**逆时针转 90°**、放在孔的**内侧**（朝板心），与实物一致。
    """
    U = 39.37
    bw, bh = 1600, 800                   # 40.64 × 20.32mm
    bx0, by0 = 50, 0                     # 板左上角（孔心再由板缘内缩）
    xs = [100 + i * 100 for i in range(16)]
    y_top, y_bot = 100, 700              # 行距 600 单位 = 15.24mm
    pad_r, hole_r = 0.9 * U, 0.5 * U     # 焊盘环外径 1.8mm / 孔径 1.0mm（商品参数）
    top_seq = list(range(32, 16, -1))    # 32,31,…,17（左→右）
    bot_seq = list(range(1, 17))         # 1,2,…,16（左→右）
    CX, CY = 850, 400                    # 焊盘区中心（板中心）
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
         f'height="{bh / 100 * 2.54:.2f}mm" viewBox="{bx0} {by0} {bw} {bh}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" rx="25" ry="25" '
         f'fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n']
    # ---- 中间：中央散热盘 + 四边各 8 条指状焊盘（**整体转 45°**，与实物那个斜星形一致）----
    #   ① 指状内端与中央盘**留缝**（约 1.0mm）：实物上两者是分开的 —— EP 与接地脚靠
    #      **另一面飞线**连通，不靠这里的图形相连（用户 2026-09-17 定的焊接方式）。
    #   ② 整个阵列转 45°；中央盘跟着转就是实物那个菱形。
    r_in, r_out, fw, half, ep_r = 100, 177, 12, 100, 59
    L.append(f'  <g fill="#d4af37" transform="rotate(45 {CX} {CY})">\n')
    L.append(f'   <rect x="{CX - ep_r}" y="{CY - ep_r}" width="{2 * ep_r}" '
             f'height="{2 * ep_r}" rx="8" ry="8"/>\n')
    for i in range(8):
        off = round(-half + (i + 0.5) * (2 * half / 8.0))
        L.append(f'   <rect x="{CX + off - fw // 2}" y="{CY - r_out}" width="{fw}" '
                 f'height="{r_out - r_in}"/>\n')                              # 上
        L.append(f'   <rect x="{CX + off - fw // 2}" y="{CY + r_in}" width="{fw}" '
                 f'height="{r_out - r_in}"/>\n')                              # 下
        L.append(f'   <rect x="{CX - r_out}" y="{CY + off - fw // 2}" width="{r_out - r_in}" '
                 f'height="{fw}"/>\n')                                            # 左
        L.append(f'   <rect x="{CX + r_in}" y="{CY + off - fw // 2}" width="{r_out - r_in}" '
                 f'height="{fw}"/>\n')                                            # 右
    L.append('  </g>\n')

    def hole(cn, x, y, label, ty):
        L.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PIN_NAMES[cn])}" '
                 f'cx="{x}" cy="{y}" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" '
                 f'stroke-width="4"/>\n')
        L.append(f'  <circle cx="{x}" cy="{y}" r="{hole_r:.1f}" fill="#0b2c18"/>\n')
        L.append(f'  <text x="{x}" y="{ty}" font-size="56" fill="#ffffff" '
                 f'text-anchor="middle" dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x} {ty})">{label}</text>\n')

    for num, x in zip(top_seq, xs):
        hole(num, x, y_top, str(num), y_top + 76)   # 上排：数字在孔**内侧**（朝板心），逆时针 90°
    for num, x in zip(bot_seq, xs):
        hole(num, x, y_bot, str(num), y_bot - 76)   # 下排：同样在内侧
    # EPAD 不再单独给孔（见 docstring）：connector 仍保留，指向中央散热盘，要接线时自己拉线。
    L.append(f'  <g id="connector0pin" connectorname="{esc(PIN_NAMES[0])}">'
             f'<circle cx="{CX}" cy="{CY}" r="10" fill="none" stroke="none"/></g>\n')
    # ---- 丝印（照实物：QFN32 在板左，0.65MM 在板右；没有 QFP32 / EP 字样）----
    L.append('  <g fill="#ffffff" font-family="DroidSans" font-size="62" text-anchor="middle">\n')
    L.append('   <text x="400" y="400">QFN32</text>\n')
    L.append('   <text x="1230" y="480">0.65MM</text>\n')
    L.append('  </g>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装原理图符号（AGENTS.md §5）：**四排封装（QFN）用四边**，沿方框逆时针：
       底边（左→右）= EPAD(0) 1 2 3 4 5 6 7 8    右（下→上）= 9..16
       顶边（右→左）= 17..24                      左（上→下）= 25..32
    EPAD(0) 放底边最左（与 pin1/pin32 相邻，同 CH347F）。
    左右引脚数字在引线上方、上下引脚数字在引脚左侧（rotate(270)，从下至上）；
    脚名都在框内（左右手动基线偏移 / 上下 rotate(270) 居中）；名/数字/引线同色黑、整图同字号；
    四角留 CORNER=(最长名18+1)×int(FN×0.58)=380 的空白。物理尺寸 width/height(in)，1000 单位 = 1in。"""
    P, WIRE, CH, FN = 100, 130, 35, 35
    BASELINE_OFF = round(FN * 0.35)
    max_len = max(len(v) for v in PIN_NAMES.values())        # 18：RXDV/CRS_DV/FX_HEN
    CORNER = (max_len + 1) * int(FN * 0.58)                  # 19×20 = 380
    BX0, BY0 = 340, 200
    N_BOT, N_SIDE = len(BOTTOM_WITH_PAD), len(RIGHT)          # 9 / 8
    BW, BH = N_BOT * P + 2 * CORNER, N_SIDE * P + 2 * CORNER
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - WIRE - 5
    VBW, VBH = BW + 2 * WIRE + 10, BH + 2 * WIRE + 10
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" '
         f'height="{VBH / 1000:.6f}in" viewBox="{VBX} {VBY} {VBW} {VBH}">\n',
         ' <g id="schematic">\n',
         f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
         f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n']

    def wire(cn, x1, y1, x2, y2, tx, ty):
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PIN_NAMES[cn])}" '
                 f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect class="terminal" id="connector{cn}terminal" x="{tx - 11}" y="{ty - 11}" '
                 f'width="22" height="22" fill="none" stroke="none"/>\n')

    def num_h(cn, x1, x2, y):
        L.append(f'  <text x="{x1 + (x2 - x1) // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" '
                 f'text-anchor="middle" font-family="DroidSans">{cn}</text>\n')

    def num_v(cn, x, y):
        L.append(f'  <text x="{x - FN}" y="{y}" font-size="{FN}" fill="#000000" '
                 f'text-anchor="middle" font-family="DroidSans" '
                 f'transform="rotate(270 {x - FN} {y})">{cn}</text>\n')

    def nm_h(cn, x, y, anchor):
        L.append(f'  <text x="{x}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" '
                 f'text-anchor="{anchor}" font-family="DroidSans">{esc(PIN_NAMES[cn])}</text>\n')

    def nm_v(cn, x, y):
        ln = int(len(PIN_NAMES[cn]) * FN * 0.58)
        yy = y - CH - ln // 2 if y > BY0 + BH // 2 else y + CH + ln // 2
        L.append(f'  <text x="{x}" y="{yy}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x} {yy})">'
                 f'{esc(PIN_NAMES[cn])}</text>\n')

    for i, cn in enumerate(BOTTOM_WITH_PAD):                 # 底边 EPAD,1..8（左→右）
        x = BX0 + CORNER + P // 2 + i * P
        wire(cn, x, BY1, x, BY1 + WIRE, x, BY1 + WIRE)
        num_v(cn, x, BY1 + 55)
        nm_v(cn, x, BY1)
    for i, cn in enumerate(RIGHT):                           # 右 9..16（下→上）
        y = BY1 - CORNER - P // 2 - i * P
        wire(cn, BX1, y, BX1 + WIRE, y, BX1 + WIRE, y)
        num_h(cn, BX1, BX1 + WIRE, y)
        nm_h(cn, BX1 - CH, y, "end")
    for i, cn in enumerate(TOP):                             # 顶 17..24（右→左）
        x = BX1 - CORNER - P // 2 - i * P
        wire(cn, x, BY0, x, BY0 - WIRE, x, BY0 - WIRE)
        num_v(cn, x, BY0 - 50)
        nm_v(cn, x, BY0)
    for i, cn in enumerate(LEFT):                            # 左 25..32（上→下）
        y = BY0 + CORNER + P // 2 + i * P
        wire(cn, BX0, y, BX0 - WIRE, y, BX0 - WIRE, y)
        num_h(cn, BX0 - WIRE, BX0, y)
        nm_h(cn, BX0 + CH, y, "start")
    CHIP_FS = 79
    L.append(f'  <text x="{BX0 + BW // 2}" y="{BY0 + BH // 2 + round(CHIP_FS * 0.35)}" '
             f'font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" font-family="DroidSans">'
             f'{esc(SCHEM_LABEL)}</text>\n')
    L.append(f'  <text x="{BX0 + BW // 2}" y="{BY0 + BH // 2 + round(CHIP_FS * 0.35) + 90}" '
             f'font-size="{FN}" fill="#000000" text-anchor="middle" font-family="DroidSans">'
             f'QFN-32</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图：**数据全按嘉立创封装**（AGENTS §4.3 取证顺序）。
    封装名用 **QFN-32**（手册 Figure 25 的写法）；立创那份封装的**文件名**叫
    `VQFN-32-L4.0-W4.0-P0.40-BL-EP`，只是它的命名习惯，几何一样。
    坐标 = mm，原点在本体中心。
      焊盘：0.20(切向) × 0.38(径向)，中心 ±1.9173，节距 0.40，每边 8 个；
      底边 1..8 左→右、右边 9..16 下→上、顶边 17..24 右→左、左边 25..32 上→下；
      EPAD 2.8×2.8 居中（connector 0）。
    丝印画法按**仓库 Fritzing 规范**（照 svg/CH347F）：四个 L 形角标 + pin1 **实心**圆点
    （立创原图是空心小圆，按用户 2026-09-17「PCB 按咱规范」改成实心点，位置/尺寸仍取立创）。"""
    C = 2.8                                  # 画布中心（外框 5.6 × 5.6，四周留 0.49）
    W = H = 5.6
    x0 = -PAD_C - PAD_L / 2                  # 左侧焊盘外缘 = -2.1073
    pads, silk = [], []

    def pad(n, x, y, w, h):
        pads.append(f'<rect id="connector{n}pad" connectorname="{esc(PIN_NAMES[n])}" '
                    f'x="{x:.4f}" y="{y:.4f}" width="{w:.3f}" height="{h:.3f}" '
                    f'fill="#F7BD13" stroke="none"/>')

    def slot(i):                             # 8 脚均匀居中：-1.4 .. +1.4
        return -1.4 + i * PITCH

    for i, n in enumerate(BOTTOM):           # 底边 1..8（左→右）：y = +PAD_C
        pad(n, C + slot(i) - PAD_W / 2, C + PAD_C - PAD_L / 2, PAD_W, PAD_L)
    for i, n in enumerate(RIGHT):            # 右边 9..16（下→上）：x = +PAD_C
        pad(n, C + PAD_C - PAD_L / 2, C - slot(i) - PAD_W / 2, PAD_L, PAD_W)
    for i, n in enumerate(TOP):              # 顶边 17..24（右→左）：y = -PAD_C
        pad(n, C - slot(i) - PAD_W / 2, C - PAD_C - PAD_L / 2, PAD_W, PAD_L)
    for i, n in enumerate(LEFT):             # 左边 25..32（上→下）：x = -PAD_C
        pad(n, C - PAD_C - PAD_L / 2, C + slot(i) - PAD_W / 2, PAD_L, PAD_W)
    pad(0, C - EPAD / 2, C - EPAD / 2, EPAD, EPAD)                # 中心裸露焊盘
    for sx in (-1, 1):                                            # 四个 L 形角标（照立创）
        for sy in (-1, 1):
            cx0, cy0 = C + sx * SILK_CORNER, C + sy * SILK_CORNER
            silk.append(f'<line x1="{cx0:.3f}" y1="{cy0:.3f}" x2="{cx0 - sx * SILK_ARM:.3f}" '
                        f'y2="{cy0:.3f}" stroke="#f0f0f0" stroke-width="{SILK_W}"/>')
            silk.append(f'<line x1="{cx0:.3f}" y1="{cy0:.3f}" x2="{cx0:.3f}" '
                        f'y2="{cy0 - sy * SILK_ARM:.3f}" stroke="#f0f0f0" stroke-width="{SILK_W}"/>')
    # pin1 标记：**实心**圆点，位置取立创（底边首盘外侧偏左），半径照 CH347F 的 0.20
    silk.append(f'<circle cx="{C + PIN1_MARK[0]:.3f}" cy="{C + PIN1_MARK[1]:.3f}" r="0.20" '
                f'fill="#f0f0f0" stroke="none" class="other"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" '
            f'viewBox="0 0 {W:.1f} {H:.1f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for cn in sorted(PIN_NAMES):
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(PIN_NAMES[cn])}" type="male">\n'
            f'   <description>pin {cn} = {esc(PIN_NAMES[cn])}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cn}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{cn}pin" terminalId="connector{cn}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{cn}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>1</version>\n <date>2026-09-17</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>IP101GR</tag>\n  <tag>PHY</tag>\n'
            f'  <tag>Ethernet</tag>\n  <tag>10/100M</tag>\n  <tag>MII</tag>\n  <tag>RMII</tag>\n'
            f'  <tag>QFN-32</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">33</property>\n </properties>\n'
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
