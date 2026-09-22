#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — 生成 Fritzing 自定义元件 SMT-SW-PTS-820（C&K PTS820 系列贴片轻触开关）。

四个视图（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件（part.<id>.fzp + 4 个 svg.<view>.* + 本脚本）同目录，.fzpz 输出到仓库顶层 fzpz/。
打包规则（docs/part-dev-guide.md §2.2）：.fzpz 内部平铺，.fzp 的 image= 用子目录路径。

数据来源
========
1) 规格书 `D:\Downloads\SMT_SW_PTS_820.pdf`（C&K **PTS820 Series — Microminiature SMT Top
   Actuated** 轻触开关，2022-04-04）：
   · 功能 **SPST 常开**（"1 make contact = SPST N.O."）、**瞬时动作**、端子 **J 型（SMT）**；
   · 本体 **3.9 × 2.9 mm**；高度 **H = 1.5 / 2.0 / 2.5 mm** 三档（本件按 **H = 2.0 mm** 建，
     用户 2026-09-22 选；型号如 `PTS820 J20M SMTR LFS`，`J20M` = 160gf、无定位柱版）；
   · 行程 **0.2 mm +0.1/−0.05**；寿命 10 万（250gf）/ 20 万次（160gf）；
   · 电气：**12 VDC / 50 mA**、接触电阻 ≤100 mΩ、绝缘 ≥100 MΩ、弹跳 ≤10 ms、−40~85 ℃；
   · 手册 "RECOMMENDED PCB LAYOUT" 给的**焊盘比立创的小**：2.5/2.0mm 版写 `2x 0,8`、
     1.5mm 版写 `2x 0,6`（长 1.4 / 1.5）—— 见下面第 2 条的取舍。
     `Ø2 (0,5)` = 按钮 **Ø2.0 × 伸 0.5**（本件 icon 按这个画按钮）。
2) 用户 2026-09-22 给的**立创（EasyEDA）封装与符号**：
   · `D:\Downloads\SMT-SW-PTS-820_PCB.svg`（画布 1 单位 = 10 mil = 0.254mm，viewBox 41.3×32.6）：
     两个 **RECT 焊盘 4.5×5.9055 单位 = 1.143 × 1.500 mm**，中心 x = ±16.338/2 单位 ⇒
     **中心距 4.150 mm**；丝印 = 上下两条 **4.0 × 0.6 mm** 的带（y = ±(0.9…1.5)mm，
     左右两侧有意留空 —— 两端是 J 型端子，丝印不过端子）；另有两个 `r≈0` 的 MH 标记
     （未电镀定位柱参考点，`P` 版才有）——**本件不画**（J20M 是无柱版）。
     ★ **焊盘尺寸取舍（如实记）**：本件**按立创封装画**（1.143 × 1.5，比手册推荐的大）——
     用户给的是它、且大焊盘好焊；手册的 0.8/0.6 值不用。要改只改 `PAD_W/PAD_H/PAD_X`。
   · `D:\Downloads\SMT-SW-PTS-820_原理图.svg`：符号几何（1 单位 = 0.254mm）——
     引脚线 5 单位 = **1.27 mm**（pin1 朝左、pin2 朝右），两个**接触圆 r = 3 单位 = 0.762 mm**
     圆心在引脚线上方 **0.762 mm**（圆的下缘正好切引脚线），**横杆** 30 单位 = **7.62 mm**、
     厚 1 单位 = **0.254 mm**，**按钮** 8 × 3 单位 = **2.032 × 0.762 mm** 立在横杆上；
     引脚间距 **40 单位 = 10.16 mm**（±5.08）。
     ⚠ 两处**未照抄**（都写在此处，免得以后当成"画错了"）：
     ① 立创那张图里两个接触圆不对称（相对本体中线分别在 −9 / +15 单位），本件按**对称**画
        （都放在横杆两端 x = ±3.81 mm —— 引脚线也正好收在这一点上）；
     ② 立创符号整体用**蓝色** `#0000FF`（那是 EasyEDA 的默认符号色），本件按本仓原理图惯例
        用**黑色**（AGENTS §5：普通脚黑；对照 `svg/Crystal-3225`、`CH340C` 那一派）。
     ★ **本件是常开（NO）—— 横杆与触点之间必须留空隙**（用户 2026-09-22 指出：原先把横杆
       “压在”两个接触圆顶上 ⇒ 画成了**闭合**，与 PTS820 的实际状态相反）。
       立创那张图的横杆正好压在接触圆顶点上（= 闭合的样子），**本件不照抄这一点**：
       横杆整体上提 `SCH_GAP = 0.508` ⇒ 缺省看起来是**断开**。参考 Fritzing 官方 core 的
       `svg/core/schematic/pushbutton.svg`：它用“动触点斜着离开定触点”表达常开；本件用
       **平行留缝** 表达（同 KiCad `SW_Push` 的常见画法），因为本符号的按钮是压在中点上的。
3) 引脚名**就用 1 / 2**（手册 SCHEMATIC 与立创符号都只标 1、2；SPST 两端**无极性**，
   不给它们起 NO/COM 之类功能名）。

引脚朝向：**pin1 在左、pin2 在右**（俯视看本体长边为水平方向：两端就是 J 型端子）。

用法：
  python gen_part.py
"""
import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "SMT-SW-PTS-820"
FZPZ = "SMT-SW-PTS-820.fzpz"

# (connector id, 脚号, 说明)
CONN = [(0, "1", "switch terminal 1 (SPST N.O.)"),
        (1, "2", "switch terminal 2 (SPST N.O.)")]

# 板丝印（绿转接板是**我们加的**，不是实物的一部分 ⇒ 印型号不算编造实物丝印）
BOARD_LABEL = "PTS820"
# 元件顶面丝印：**不印**。本体只有 3.9 × 2.9 mm，而 PTS820 实物顶面也没有型号字
# （C&K 手册图里顶面是空的）⇒ 印上是编造。识别靠 Fritzing 的 label / title。
ICON_MARK = ""

TITLE = "PTS820 Tactile Switch (SPST N.O., SMT, H = 2.0 mm)"
LABEL = "SW"
PACKAGE = "SMD 3.9 x 2.9 x 2.0 mm (J-lead)"
FAMILY = "Tactile Switch"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- SMT-SW-PTS-820 (C&K PTS820 series, SPST N.O. tactile switch) -->\n')

# ---- 几何（mm）----------------------------------------------------------
BODY_W, BODY_H = 3.90, 2.90        # 本体（俯视：长 × 宽）
BODY_T = 2.00                      # 高度 H = 2.0（本件这一档）
TERM_X0, TERM_X1 = 1.95, 2.65      # J 型端子：从本体边缘向外 0.70
TERM_H = 1.50                      # 端子宽（y 方向，= 焊盘长 1.5）
ACT_D, ACT_T = 2.00, 0.50          # 按钮 Ø2.0、伸出 0.5（手册 "Ø2 (0,5)"）
PAD_W, PAD_H = 1.143, 1.500        # PCB 焊盘（立创封装；手册推荐更小，见文件头）
PAD_X = 2.075                      # 焊盘中心 ±x ⇒ 中心距 4.150
SILK_T = 0.15                      # 丝印线宽

# ---- 原理图几何（单位 = mm，与 Crystal-3225 同一套「无单位数字 + viewBox 同刻度」写法）----
SCH_TERM_X = 6.35                  # 引脚端点（= 0.25 in，2 格）
SCH_CONTACT_X = 3.81               # 接触圆中心（= 横杆两端）
SCH_CONTACT_R = 0.762              # 接触圆半径（圆心在引脚线上方 0.762 ⇒ 下缘切引脚线）
SCH_BAR_T = 0.254                  # 横杆厚
SCH_GAP = 0.508                    # ★ 常开：横杆**底边**离接触圆**顶点**的空隙（不碰 ⇒ 读作断开）
SCH_PLUNGER_W, SCH_PLUNGER_H = 2.032, 0.762   # 按钮（立在横杆上）
SCH_FN = 2.5                       # 引脚编号字号（AGENTS §5）
SCH_NUM_X = 5.60                   # 编号中心 x（避开接触圆：圆最右 4.572，字最左 4.85）

# ---- 面包板（100 单位 = 2.54mm）-----------------------------------------
U = 39.37                          # 1mm = 100/2.54 单位
BB_W, BB_H = 300, 450              # 转接板 7.62 × 11.43 mm
BB_CX, BB_CY = 150, 130            # 开关中心
BB_PIN_Y = 350                     # 排针 y（距下边 100 单位 = 2.54mm）
BB_PIN_XS = [100, 200]             # 两根排针：相距 100 单位 = 2.54mm，居中于板中线 150
BB_NUM_DY = 65                     # 脚号中心离焊盘中心（= 环半径 39.4 + 字半高 24 + 余量）
BB_NUM_FS = 48                     # 脚号字号（1.22mm）
BB_LABEL_Y = 216                   # 板丝印 y（在开关下沿与脚号之间那条空带里居中）


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _switch_art(cx, cy, s):
    """开关俯视图形（本体 + 两端 J 型端子 + 中间按钮），(cx,cy) 中心，s = 每 mm 的单位数。"""
    L = []
    # 两端 J 型端子（先画：被本体压住的部分不显示）
    for sx in (-1, 1):
        x0, x1 = sorted((sx * TERM_X0, sx * TERM_X1))
        L.append(f'<rect x="{cx + x0 * s:.2f}" y="{cy - TERM_H / 2 * s:.2f}" '
                 f'width="{(x1 - x0) * s:.2f}" height="{TERM_H * s:.2f}" fill="#c0c0c0" stroke="none"/>')
    # 本体（直角、深色）
    L.append(f'<rect x="{cx - BODY_W / 2 * s:.2f}" y="{cy - BODY_H / 2 * s:.2f}" '
             f'width="{BODY_W * s:.2f}" height="{BODY_H * s:.2f}" fill="#2b2b2b" stroke="none"/>')
    # 按钮（Ø2.0，浅色）
    L.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{ACT_D / 2 * s:.2f}" '
             f'fill="#e8e8e8" stroke="none"/>')
    return L


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """俯视图：深灰本体 3.9 × 2.9 + 两端银色 J 型端子（各伸出 0.70）+ 中间 Ø2.0 按钮。
    顶面**不印字**（实物也不印，见文件头）。viewBox 贴合（本体 + 端子 + 0.25 余量）。"""
    SX = TERM_X1 + 0.25                     # 2.90
    SY = BODY_H / 2 + 0.30                  # 1.75
    L = [SVG_HDR,
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * SX:.2f}mm" height="{2 * SY:.2f}mm" '
         f'viewBox="{-SX:.2f} {-SY:.2f} {2 * SX:.2f} {2 * SY:.2f}">\n',
         ' <g id="icon">\n']
    for line in _switch_art(0, 0, 1.0):
        L.append('  ' + line + '\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = 绿色转接板（AGENTS §3b：SMD 不走面包板）。

    几何（单位，100 = 2.54mm）：
      · 板 **300 × 450** = 7.62 × 11.43 mm（能放下开关 + 两根 2.54 排针，且尽量小）；
      · 两根排针在**同一排** y=350（距下边 100 单位 = 2.54mm）、x=100/200（相距 2.54mm、
        居中于板中线 150）⇒ 落在面包板孔距网格上；
      · 开关（1:1）居中偏上 (150,130)：它的端子最远到 x=150±104.3 单位 ⇒ 距板边 45.7 单位
        （1.16mm）；排针环（r=39.4）与开关最近处（端子下沿 159.5）相距 151 单位 = 3.84mm
        ≥ 元件高 2.9mm/2 + 1mm 环 + 2mm 余量 ⇒ **不重叠**（§3b）；
      · 脚号在焊盘**内侧**（朝板心）＝ 排针上方，字与环留 0.35mm 缝（§3b 要求 ≥0.3mm）；
      · 板丝印 `BOARD_LABEL` 放在开关下沿与脚号之间那条空带里（0.85mm 余量）。"""
    pad_r, hole_r = 1.0 * U, 0.485 * U
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{BB_W / 100 * 2.54:.2f}mm" '
         f'height="{BB_H / 100 * 2.54:.2f}mm" viewBox="0 0 {BB_W} {BB_H}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="0" y="0" width="{BB_W}" height="{BB_H}" fill="#00aa44" '
         f'stroke="#00772f" stroke-width="5"/>\n']
    # 开关（1:1）——放在板上，先画，后面排针/丝印压在上面
    for line in _switch_art(BB_CX, BB_CY, U):
        L.append('  ' + line + '\n')
    # 两根排针：2mm 金环 + 0.97mm 针孔
    for cn, x in enumerate(BB_PIN_XS):
        L.append(f'  <circle id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                 f'cx="{x}" cy="{BB_PIN_Y}" r="{pad_r:.1f}" fill="#d4af37" '
                 f'stroke="#8a6d00" stroke-width="4"/>\n')
        L.append(f'  <circle cx="{x}" cy="{BB_PIN_Y}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    # 脚号（焊盘内侧＝上方；水平字，不旋转）
    for cn, x in enumerate(BB_PIN_XS):
        L.append(f'  <text x="{x}" y="{BB_PIN_Y - BB_NUM_DY}" font-size="{BB_NUM_FS}" '
                 f'fill="#ffffff" text-anchor="middle" dominant-baseline="central" '
                 f'font-family="DroidSans">{esc(CONN[cn][1])}</text>\n')
    # 板丝印
    if BOARD_LABEL:
        L.append(f'  <text x="{BB_CX}" y="{BB_LABEL_Y}" font-size="46" fill="#ffffff" '
                 f'text-anchor="middle" dominant-baseline="central" '
                 f'font-family="DroidSans">{esc(BOARD_LABEL)}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """原理图 = 瞬时轻触开关符号，几何取自用户给的立创符号（见文件头，单位 = mm）：

    · 引脚线：从 ±6.35（端点）到 ±3.81，**灰 `#787878`、圆头、class="pin"**（线宽取
      Fritzing 官方 core 原理图 svg 的 **0.25**——§5 里那个 0.75 是 BAT54S 的 0.254mm 单位制
      下的值，本文件单位是 mm）；
    · 端点 = **极小不可见 rect**（0.0001×0.0001，`stroke/fill=none`）——靠引脚线末端吸附（§5）；
    · 接触圆：r 0.762，圆心在引脚线上方 0.762 ⇒ **下缘正好切引脚线**（照立创符号）；
    · **横杆 7.62 × 0.254：底边离接触圆顶点留 0.508 空隙** ⟹ 缺省读作**断开**（常开，
      见文件头星条）；**按钮** 2.032 × 0.762 立在横杆上（朝上）；
    · 脚号 `1` / `2` 灰 `#8C8C8C`、DroidSans、**字号 2.5**，放在**引线上方**（§5）且避开接触圆
      （圆最右 4.572，字最左 5.60−0.75=4.85 ⇒ 留 0.28mm）。

    ★ 物理尺寸的写法照 **Fritzing 官方 core 原理图 svg**（如 `core/schematic/11LC010_schematic.svg`
      的 `width='1.5in' height='0.5in' viewBox='0 0 38.1 12.7'`）：**viewBox 与几何用 mm，
      width/height 用 in（= mm/25.4）** ⇒ 不给 Fritzing 留“无单位按默认 DPI 解释”的余地
      （`tools/schem_check.py` 会就无单位尺寸报「尺寸会超大」）。"""
    tx, cx_ = SCH_TERM_X, SCH_CONTACT_X
    r = SCH_CONTACT_R
    bar_bot = -(2 * r + SCH_GAP)             # 横杆底边（离接触圆顶点 SCH_GAP）
    bar_top = bar_bot - SCH_BAR_T            # 横杆顶边
    pl_top = bar_top - SCH_PLUNGER_H         # 按钮顶端
    VBX = -(tx + 0.25)
    VBW = 2 * (tx + 0.25)
    VBY = pl_top - 0.10
    VBH = -VBY + (r + 0.30)
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 25.4:.6f}in" '
         f'height="{VBH / 25.4:.6f}in" viewBox="{VBX:.2f} {VBY:.3f} {VBW:.2f} {VBH:.3f}">\n',
         ' <g id="schematic">\n']
    # 引脚线 + 端点 + 编号（pin1 左、pin2 右）
    for cn, sx in ((0, -1), (1, 1)):
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(CONN[cn][1])}" '
                 f'x1="{sx * tx:.2f}" y1="0" x2="{sx * cx_:.2f}" y2="0" stroke="#787878" '
                 f'stroke-width="0.25" stroke-linecap="round"/>\n')
        L.append(f'  <rect class="terminal" id="connector{cn}terminal" x="{sx * tx:.2f}" y="0" '
                 f'width="0.0001" height="0.0001" stroke="none" fill="none"/>\n')
        L.append(f'  <text x="{sx * SCH_NUM_X:.2f}" y="-0.40" font-size="{SCH_FN}" '
                 f'fill="#8C8C8C" font-family="DroidSans" text-anchor="middle">'
                 f'{esc(CONN[cn][1])}</text>\n')
    # 两个接触圆（空心的固定触点）
    for sx in (-1, 1):
        L.append(f'  <circle cx="{sx * cx_:.2f}" cy="{-r:.2f}" r="{r:.2f}" fill="#FFFFFF" '
                 f'stroke="#000000" stroke-width="0.25"/>\n')
    # 横杆（动触点，压在接触圆顶点上）+ 按钮
    L.append(f'  <rect x="{-cx_:.2f}" y="{bar_top:.3f}" width="{2 * cx_:.2f}" '
             f'height="{SCH_BAR_T}" fill="#000000" stroke="none"/>\n')
    L.append(f'  <rect x="{-SCH_PLUNGER_W / 2:.3f}" y="{pl_top:.3f}" width="{SCH_PLUNGER_W}" '
             f'height="{SCH_PLUNGER_H}" fill="#000000" stroke="none"/>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB = 立创封装（焊盘 1.143 × 1.500 mm、中心 ±2.075 ⇒ 中心距 4.150）+
    手册本体轮廓 3.9 × 2.9 的丝印（左右两边在端子处断开 —— 立创那张图就是两侧留空的）。
    Fritzing 层结构：copper1 > copper0（空）+ 焊盘；silkscreen。坐标 mm，viewBox 贴合。"""
    SX = PAD_X + PAD_W / 2 + SILK_T       # 2.793
    SY = BODY_H / 2 + SILK_T              # 1.600
    hw, hh = BODY_W / 2, BODY_H / 2       # 1.95 / 1.45
    pads, silk = [], []
    for cn, sx in ((0, -1), (1, 1)):
        pads.append(f'<rect id="connector{cn}pad" connectorname="{esc(CONN[cn][1])}" '
                    f'x="{sx * PAD_X - PAD_W / 2:.4f}" y="{-PAD_H / 2:.3f}" '
                    f'width="{PAD_W}" height="{PAD_H}" fill="#F7BD13" stroke="none"/>')
    # 本体轮廓：上下两条通长 + 左右两段在焊盘（±0.75）外断开
    silk.append(f'<line x1="{-hw}" y1="{-hh}" x2="{hw}" y2="{-hh}"/>')
    silk.append(f'<line x1="{-hw}" y1="{hh}" x2="{hw}" y2="{hh}"/>')
    for sx in (-1, 1):
        silk.append(f'<line x1="{sx * hw}" y1="{-hh}" x2="{sx * hw}" y2="{-PAD_H / 2 - SILK_T}"/>')
        silk.append(f'<line x1="{sx * hw}" y1="{PAD_H / 2 + SILK_T}" x2="{sx * hw}" y2="{hh}"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\" "
             f'stroke="#f0f0f0" stroke-width="{SILK_T}">\n' + "\n".join(silk))
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * SX:.2f}mm" height="{2 * SY:.2f}mm" '
            f'viewBox="{-SX:.2f} {-SY:.2f} {2 * SX:.2f} {2 * SY:.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for cn, name, desc in CONN:
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(name)}" type="male">\n'
            f'   <description>{esc(desc)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cn}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{cn}pin" terminalId="connector{cn}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{cn}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>4</version>\n <date>2026-09-22</date>\n'
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
