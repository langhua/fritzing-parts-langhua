#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — USB-B01（SOFNG SOF-G006 / 系列 SD106）卧插 B 型 USB 母座（方口）
=========================================================================
数据来源：`D:\Downloads\USB-B01方口母座.pdf`（TAIWAN SOFNG，DWG NO. SOF-G006，REV A0，
SCALE **1:1**，UNIT mm；材料：胶芯 PBT / 端子磷铜 C5191 镀金 1u" / 外壳黄铜 C2680 镀镍）。
  ★ 该图纸的尺寸标注是**矢量描边文字**（不是文本），抽不出字符串 → 数值由**用户 2026-09-15
    逐条确认**（下方凡标 [用户] 的都是他给的，标 [推定] 的是我按图纸重建的）。

用户确认/实测的基准（本文件全部几何都从这几个出发）：
  [用户] 外壳宽 **12.00±0.15**；含两侧焊耳总宽 **14.50±0.25**；插口内宽 **5.60±0.10**
  [用户] 焊耳（焊在 PCB 上的侧耳）中心距**插口面** **10.35±0.20**
  [用户] **顶视总深 16.30**（= 插口面 → 定位柱外缘；图纸里 16.30 就是"垂直方向总尺寸"）
  [用户] 信号脚 **4×Ø0.92**：2×2 排布，**行内中心距 2.50**、**行距 2.00**
  [用户] 定位柱 **2×Ø2.3**：**水平中心距 12.04±0.10**（⇒ ±6.02）；
         与信号脚**垂直方向最大中心距 4.71**（⇒ 距近排 2.71）
  [用户] 4.77 = 定位柱与信号脚的**水平方向**中心距（0.25+4.77 = 另一端，与 12.04 自洽）
  [用户] 用不到：高度 10.90（侧视）、底视图尺寸 8.10；**图纸没有 11.50**（我先前读错）
  [实测] **顶视（游标卡尺，2026-09-15）**：两块金属片 前 **12.0×12.0** + 后 **4.30×12.0**
         （⇒ 总深 16.30 ✓）；两侧耳朵沿深度 **2.30**、每侧外伸 1.25（⇒ 总宽 14.50 ✓）
         —— 顶视就是这些，**其它没有**（插口槽/金触点/定位柱从上面看不见）
  自洽性核对：12.0+4.30 = 16.30 ✓；12.00+2×1.25 = 14.50 ✓；10.35±1.15 = 9.20~11.50 落在
              前块金属片(0~12.0)内 ✓；12.04/2 = 6.02 = 1.25（行内半距）+ 4.77 ✓；4.71 = 2.00+2.71 ✓

仍标 [推定] 的：本版已经**没有**了 —— 信号脚两排深度改为由「耳朵孔 ↔ 信号脚 2.71 /
4.71」从耳朵孔倒推（7.64 / 5.64），两个大孔也按用户纠正画在耳朵上（±6.02 / 深 10.35）。

进度：
  [x] 1. icon（顶视：前 12.0×12.0 + 后 4.30×12.0 两块金属片 + 两侧耳朵 1.25×2.30）
  [x] 2. breadboard（绿色转接板 700×900 单位；VCC / D- / D+ / GND 四针在 2.54 网格上）
  [x] 3. schematic（4 脚矩形符号：左 1 VCC / 2 D- / 3 D+ / 4 GND，名在框内）
  [x] 4. pcb（4-Ø0.92 信号脚 + 2-Ø2.3 定位柱 + 分段丝印）
  [x] 5. part.USB-B01.fzp + 打包 fzpz
"""
import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "USB-B01"
FZPZ = "USB-B01.fzpz"
TITLE = "USB Type-B Receptacle, right-angle (SOFNG SOF-G006)"
LABEL = "J"
PACKAGE = "USB-B (right-angle)"

# ---- 顶视（用户 2026-09-15 用游标卡尺实测，比图纸好读、以此为准）-------------------
PLATE1_W, PLATE1_D = 12.00, 12.00   # 前块金属片（主外壳）：宽 × 深
PLATE2_W, PLATE2_D = 12.00, 4.30    # 后块金属片 → 总深 **16.30**（与图纸总深一致 ✓）
EAR_D = 2.30                        # 侧耳沿深度方向的尺寸
EAR_OUT = 1.25                      # 侧耳每侧外伸 → 总宽 12.00+2×1.25 = **14.50** ✓
EAR_CD = 10.35                      # 侧耳中心距插口面（用户给）→ 跨 9.20~11.50
TOTAL_D = PLATE1_D + PLATE2_D       # 16.30 [核对 ✓]
TOTAL_W = PLATE1_W + 2 * EAR_OUT    # 14.50 [核对 ✓]

# ---- 图纸/用户给的其余尺寸（顶视看不见，pcb 视图用）-------------------------
INNER_W = 5.60         # 插口内宽
PIN_DX = 2.50          # 信号脚：**宽度方向**中心距（⇒ ±1.25）
PIN_DY = 2.00          # 信号脚：**深度方向**两排的间距
PIN_D = 0.92           # 信号脚孔径 Ø0.92
# 信号脚两排的深度：**在耳朵孔之后**（用户 2026-09-15 给的绝对值）——
#   后排 = 10.35 + 4.71 = **15.06**；前排 = 15.06 − 2.00 = **13.06**（= 10.35 + 2.71 ✓）
ROW_FAR = EAR_CD + 4.71                  # 后排（离插口面远）= 15.06
ROW_NEAR = ROW_FAR - PIN_DY              # 前排 = 13.06
# 焊盘画法照 Fritzing 官方 USB+SHIELD.fzpz（SparkFun usb-b-pth）：**圆环**
# （fill=none + stroke，也是 Fritzing 自己 brd2svg 导出 THT 焊盘的写法）
SIG_OUTER_D = 1.68     # 信号脚焊盘外径（官方那份 r=0.6477 + 描边 0.381 → Ø1.676；
                       # 与数据表 4-Ø0.92 对得上）
# 两个大孔（图纸 "2-Ø2.3"）—— **焊耳朵用的**，不是定位柱（用户 2026-09-15 纠正），
# 就画在耳朵上；同样照官方那份的环画法（r=1.27 + 描边 0.254）。
SHIELD_SPAN = 12.04    # 两孔水平中心距（⇒ ±6.02）
SHIELD_HOLE_D = 2.30   # 孔 Ø2.3
SHIELD_PAD_D = 2.80    # 焊盘环外径

# 颜色（金属外壳 / 侧耳 / 深色孔）
PLATE1 = "#c9c9c9"
PLATE2 = "#b5b5b5"
SHELL_EDGE = "#8f8f8f"
HOLE = "#3a3a3a"
GOLD = "#e0b84a"
POST = "#b8b8b8"

# 局部坐标：x 以外壳中心为 0（右 +），y = 0 在**插口面**、向**后方**递增
X0, X1 = -TOTAL_W / 2.0, TOTAL_W / 2.0
Y0, Y1 = 0.0, TOTAL_D
M = 0.15                                    # viewBox 边距
VX, VY = X0 - M, Y0 - M
VW, VH = X1 - X0 + 2 * M, Y1 - Y0 + 2 * M


def icon_svg():
    """顶视图（卧插平放，插口面在上方）—— 按用户 **游标卡尺实测**：
      · 两块金属片：前 **12.0×12.0**、后 **4.3×12.0**（总深 **16.30** = 图纸总深 ✓）；
      · 两侧耳朵：沿深度 **2.30**、每侧外伸 **1.25**（总宽 **14.50** ✓），中心距插口面 **10.35**。
    用户原话：「就是两块金属片……然后是两侧的耳朵，宽度 2.3mm。其它就没有了」
    → 插口槽、金触点、定位柱在顶视都看不见，**一律不画**；不画 pin1 圆点、不加装饰。"""
    s = ['<?xml version="1.0" encoding="UTF-8"?>\n',
         '<!-- USB-B01 (SOFNG SOF-G006) top view -->\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="%.2f %.2f %.2f %.2f">\n' % (VW, VH, VX, VY, VW, VH),
         ' <g id="icon">\n']
    # 两侧耳朵（先画，贴在前块金属片外侧）
    ear_y = EAR_CD - EAR_D / 2.0
    for sx in (-1, 1):
        ex = (PLATE1_W / 2.0) if sx > 0 else (-TOTAL_W / 2.0)
        s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                 'stroke="%s" stroke-width="0.08"/>\n'
                 % (ex, ear_y, EAR_OUT, EAR_D, PLATE1, SHELL_EDGE))
    # 前块金属片（主外壳）
    s.append('  <rect x="%.2f" y="0.00" width="%.2f" height="%.2f" fill="%s" '
             'stroke="%s" stroke-width="0.10"/>\n'
             % (-PLATE1_W / 2.0, PLATE1_W, PLATE1_D, PLATE1, SHELL_EDGE))
    # 后块金属片
    s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
             'stroke="%s" stroke-width="0.10"/>\n'
             % (-PLATE2_W / 2.0, PLATE1_D, PLATE2_W, PLATE2_D, PLATE2, SHELL_EDGE))
    s += [' </g>\n', '</svg>\n']
    return "".join(s)


def _plate_shapes(s=1.0, dx=0.0, dy=0.0):
    """两块金属片 + 两侧耳朵（**顶视几何的唯一来源**，返回元素列表）。
    s=1.0 时坐标就是 mm（icon 视图直接用）；面包板视图传 s=U、dx/dy 平移，
    **把坐标烘成绝对值**（不依赖 SVG 变换，避免 Fritzing 解析变换时错位）。"""
    ear_y = EAR_CD - EAR_D / 2.0
    sw = 0.10 * s
    out = []
    for sx in (-1, 1):                                   # 两侧耳朵
        ex = (PLATE1_W / 2.0) if sx > 0 else (-TOTAL_W / 2.0)
        out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                   'stroke="%s" stroke-width="%.2f"/>\n'
                   % (dx + ex * s, dy + ear_y * s, EAR_OUT * s, EAR_D * s,
                      PLATE1, SHELL_EDGE, sw))
    out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
               'stroke="%s" stroke-width="%.2f"/>\n'
               % (dx - PLATE1_W / 2.0 * s, dy, PLATE1_W * s, PLATE1_D * s,
                  PLATE1, SHELL_EDGE, sw))               # 前块金属片
    out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
               'stroke="%s" stroke-width="%.2f"/>\n'
               % (dx - PLATE2_W / 2.0 * s, dy + PLATE1_D * s, PLATE2_W * s, PLATE2_D * s,
                  PLATE2, SHELL_EDGE, sw))               # 后块金属片
    return out


def icon_svg():
    """顶视图（卧插平放，插口面在上方）—— 按用户 **游标卡尺实测**：
      · 两块金属片：前 **12.0×12.0**、后 **4.3×12.0**（总深 **16.30** = 图纸总深 ✓）；
      · 两侧耳朵：沿深度 **2.30**、每侧外伸 **1.25**（总宽 **14.50** ✓），中心距插口面 **10.35**。
    用户原话：「就是两块金属片……然后是两侧的耳朵，宽度 2.3mm。其它就没有了」
    → 插口槽、金触点、定位柱在顶视都看不见，**一律不画**；不画 pin1 圆点、不加装饰。"""
    s = ['<?xml version="1.0" encoding="UTF-8"?>\n',
         '<!-- USB-B01 (SOFNG SOF-G006) top view -->\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="%.2f %.2f %.2f %.2f">\n' % (VW, VH, VX, VY, VW, VH),
         ' <g id="icon">\n']
    s += _plate_shapes(1.0, 0.0, 0.0)
    s += [' </g>\n', '</svg>\n']
    return "".join(s)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = 绿色 USB-B 转接板（AGENTS §3b：非插针式元件 → 绿色转接板）。
    板 **700×900 单位 = 17.78×22.86mm**（顶视内容 14.50×16.30mm 放得下，四周留边）。
    四个信号脚 VCC / D- / D+ / GND（= PIN1..4）在**底排** x=200/300/400/500、y=800，
    均在 100 单位（2.54mm）整数倍上 → 能插进面包板孔；顶视图形 1:1 居中于 (350,330)。
    耳朵/定位柱是机械件、不引出针（同 LD1117 散热片的做法）。
    焊盘 = 2mm 圆盘 + 0.97mm 针孔（§3b）；管脚号逆时针转 90°、居中于焊盘列、DroidSans。"""
    U = 39.37                       # 1mm = 39.37 内部单位（100 单位 = 2.54mm）
    pad_r, hole_r = 1.0 * U, 0.485 * U
    bw, bh = 700, 900
    cx, cy = 350, 330
    y_row = 800
    xs = [200 + i * 100 for i in range(4)]
    names = ("VCC", "D-", "D+", "GND")
    s = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %d %d">\n' % (bw / 100 * 2.54, bh / 100 * 2.54, bw, bh),
         ' <g id="breadboard">\n',
         '  <rect x="0" y="0" width="%d" height="%d" fill="#00aa44" stroke="#00772f" '
         'stroke-width="5"/>\n' % (bw, bh)]
    # 顶视图形 1:1（几何 → 绝对坐标烘入：x 中心=cx、y 原点=插口面）
    s += _plate_shapes(U, cx, cy - TOTAL_D / 2.0 * U)
    for i, px in enumerate(xs):
        s.append('  <circle id="connector%dpin" connectorname="%s" cx="%d" cy="%d" r="%.1f" '
                 'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n'
                 % (i, names[i], px, y_row, pad_r))
        s.append('  <circle cx="%d" cy="%d" r="%.1f" fill="#2b2b2b"/>\n' % (px, y_row, hole_r))
        s.append('  <text x="%d" y="750" font-size="52" fill="#ffffff" text-anchor="middle" '
                 'dominant-baseline="central" font-family="DroidSans" '
                 'transform="rotate(-90 %d 750)">%d</text>\n' % (px, px, i + 1))
    s += [' </g>\n', '</svg>\n']
    return "".join(s)


# ---------------------------------------------------------------- schematic
def gen_schematic_svg():
    """矩形连接器符号（4 脚），按 AGENTS.md §5 矩形原理图规则：
    左侧 4 脚从上到下 1 VCC / 2 D- / 3 D+ / 4 GND；数字在引线**上方**、
    引脚名在**框内**、名/数字/引线同色（黑）同字号 FN=35；名与边框留一个字符间距。
    引脚间距 P=100（2.54mm）；物理尺寸用 in 单位（1000 单位 = 1in）。"""
    WIRE, FN, CH, P, CORNER = 130, 35, 35, 100, 70
    BX0, BY0, BW, BH = 300, 200, 600, 4 * P + 2 * CORNER      # 540
    BX1, BY1 = BX0 + BW, BY0 + BH
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.6fin" height="%.6fin" '
         'viewBox="%d %d %d %d">\n'
         % ((BW + 2 * WIRE + 10) / 1000.0, (BH + 2 * WIRE + 10) / 1000.0,
            BX0 - WIRE - 5, BY0 - WIRE - 5, BW + 2 * WIRE + 10, BH + 2 * WIRE + 10),
         ' <g id="schematic">\n',
         '  <rect class="interior rect" x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" '
         'stroke="#787878" stroke-width="5"/>\n' % (BX0, BY0, BW, BH)]
    for i, name in enumerate(("VCC", "D-", "D+", "GND")):
        y = BY0 + CORNER + P // 2 + i * P
        L.append('  <line class="pin" id="connector%dpin" connectorname="%s" x1="%d" y1="%d" '
                 'x2="%d" y2="%d" stroke="#000000" stroke-width="5"/>\n'
                 % (i, name, BX0, y, BX0 - WIRE, y))
        L.append('  <rect id="connector%dterminal" x="%d" y="%d" width="22" height="22" '
                 'fill="none"/>\n' % (i, BX0 - WIRE, y - 11))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                 'font-family="DroidSans">%d</text>\n' % (BX0 - WIRE // 2, y - 24, FN, i + 1))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="start" '
                 'font-family="DroidSans">%s</text>\n'
                 % (BX0 + CH, y + round(FN * 0.35), FN, name))
    L.append('  <text x="%d" y="%d" font-size="55" fill="#000000" text-anchor="start" '
             'font-family="DroidSans">USB-B</text>\n' % (BX0 + CH, BY0 + 55))
    L += [' </g>\n', '</svg>\n']
    return "".join(L)


# ---------------------------------------------------------------------- pcb
PCB_HOLE = "#FFFFFF"
PCB_SILK = "#f0f0f0"


def gen_pcb_svg():
    """PCB 推荐孔位（mm，局部坐标：x 以外壳中心为 0，y=0 在插口面、向后递增）：
      · 4 个信号脚 Ø0.92（= PIN1..4）：2×2；**宽度方向对称 ±1.25（间距 2.50）**、
        **深度方向 13.06 / 15.06（间距 2.00）** —— 都在**耳朵孔之后**，由用户 2026-09-15
        给的绝对值定（10.35 + 4.71 / 10.35 + 2.71）；左右分配也由用户定：
        **后排 VCC(-1.25) / D-(+1.25)**、**前排 D+(+1.25) / GND(-1.25)**；
        焊盘 = **圆环 Ø0.92(孔) ~ Ø1.68(外)**（照 Fritzing 官方 USB+SHIELD 的 r=0.6477
        + 描边 0.381，对应数据表的 4-Ø0.92）；
      · 2 个**耳朵焊孔** Ø2.3（图纸 "2-Ø2.3"）：画在**耳朵上**（x=±6.02、深度 10.35），
        环 Ø2.286(孔) ~ Ø2.794(外)（照官方那份 r=1.27 + 描边 0.254）。
        用户 2026-09-15：“两个大圆圈应该在耳朵处，是焊耳朵用的”。
        **本版不给它们 connector**（同 LD1117 散热片的取舍）—— 若要当屏蔽地接线，
        应各自一个 connector 并用 <bus> 并到 GND（AGENTS §5）。
      · 丝印：外壳外框 12.00 宽 × 16.30 深；左右侧边在**耳朵焊盘处断开**（每侧留 0.1
        间隙），上下两整边 —— 丝印一律避开焊盘（§5）。"""
    sig_r, sig_sw = (PIN_D + SIG_OUTER_D) / 4.0, (SIG_OUTER_D - PIN_D) / 2.0
    sh_r, sh_sp = SHIELD_HOLE_D / 2.0, SHIELD_PAD_D / 2.0
    shield_r, shield_sw = (sh_r + sh_sp) / 2.0, (sh_sp - sh_r)
    # 左右分配（用户 2026-09-15 定）：后排 VCC 在 **左**、D- 在 **右**；前排 D+ 在 **右**、GND 在 **左**
    pads = ((0, "VCC", -1.25, ROW_FAR), (1, "D-", 1.25, ROW_FAR),
            (2, "D+", 1.25, ROW_NEAR), (3, "GND", -1.25, ROW_NEAR))
    SX, SY, M = TOTAL_W / 2.0, TOTAL_D, 0.15
    VX, VY, VW, VH = -SX - M, -M, 2 * (SX + M), SY + 2 * M
    s = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n',
         '<!-- USB-B01 SOFNG SOF-G006 -->\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="%.2f %.2f %.2f %.2f">\n' % (VW, VH, VX, VY, VW, VH),
         ' <g id="copper1">\n']
    for cn, nm, px, py in pads:               # 信号焊盘（可连线）
        s.append('  <circle id="connector%dpad" connectorname="%s" cx="%.2f" cy="%.2f" '
                 'r="%.4f" fill="none" stroke="#F7BD13" stroke-width="%.3f"/>\n'
                 % (cn, nm, px, py, sig_r, sig_sw))
    for sx in (-1, 1):                        # 耳朵焊孔（焊耳朵用；本版不设 connector）
        s.append('  <circle cx="%.2f" cy="%.2f" r="%.4f" fill="none" stroke="#F7BD13" '
                 'stroke-width="%.3f"/>\n'
                 % (sx * SHIELD_SPAN / 2.0, EAR_CD, shield_r, shield_sw))
    y_lo, y_hi = EAR_CD - SHIELD_PAD_D / 2.0 - 0.1, EAR_CD + SHIELD_PAD_D / 2.0 + 0.1
    s.append('  <g id="silkscreen">\n')
    s.append('   <path d="M %.2f 0.00 L %.2f 0.00" fill="none" stroke="%s" stroke-width="0.12"/>\n'
             % (-PLATE1_W / 2.0, PLATE1_W / 2.0, PCB_SILK))
    for sx in (-1, 1):
        for y1, y2 in ((0.0, y_lo), (y_hi, TOTAL_D)):
            s.append('   <path d="M %.2f %.2f L %.2f %.2f" fill="none" stroke="%s" '
                     'stroke-width="0.12"/>\n'
                     % (sx * PLATE1_W / 2.0, y1, sx * PLATE1_W / 2.0, y2, PCB_SILK))
    s.append('   <path d="M %.2f %.2f L %.2f %.2f" fill="none" stroke="%s" stroke-width="0.12"/>\n'
             % (-PLATE1_W / 2.0, TOTAL_D, PLATE1_W / 2.0, TOTAL_D, PCB_SILK))
    s.append('  </g>\n')
    s += [' </g>\n', '</svg>\n']
    return "".join(s)


# --------------------------------------------------------------------- .fzp
def gen_fzp():
    """4 个 connector（PIN1..4）：0 = 1 VCC、1 = 2 D-、2 = 3 D+、3 = 4 GND，三个视图全有。
    耳朵 / 定位柱是机械件（同 LD1117 散热片），**不单独引出 connector**。"""
    names = ("VCC", "D-", "D+", "GND")
    conns = []
    for cn, name in enumerate(names):
        conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                     '   <description>PIN%d %s</description>\n   <views>\n'
                     '    <breadboardView>\n     <p layer="breadboard" svgId="connector%dpin"/>\n'
                     '    </breadboardView>\n'
                     '    <schematicView>\n     <p layer="schematic" svgId="connector%dpin" '
                     'terminalId="connector%dterminal"/>\n    </schematicView>\n'
                     '    <pcbView>\n     <p layer="copper1" svgId="connector%dpad"/>\n'
                     '    </pcbView>\n   </views>\n  </connector>'
                     % (cn, name, cn + 1, name, cn, cn, cn, cn))
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<module fritzingVersion="1.0.3" moduleId="%s">\n'
            ' <version>4</version>\n <date>2026-09-15</date>\n'
            ' <label>%s</label>\n <author>fritzing-parts-langhua</author>\n'
            ' <title>%s</title>\n <tags>\n  <tag>%s</tag>\n  <tag>USB</tag>\n </tags>\n'
            ' <properties>\n  <property name="package">%s</property>\n'
            '  <property name="family">USB Connector</property>\n </properties>\n'
            ' <views>\n  <breadboardView>\n   <layers image="breadboard/%s_breadboard.svg">\n'
            '    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            '  <schematicView>\n   <layers image="schematic/%s_schematic.svg">\n'
            '    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
            '  <pcbView>\n   <layers image="pcb/%s_pcb.svg">\n'
            '    <layer layerId="copper1"/>\n    <layer layerId="silkscreen"/>\n'
            '   </layers>\n  </pcbView>\n'
            '  <iconView>\n   <layers image="icon/%s_icon.svg">\n'
            '    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n </views>\n'
            ' <connectors>\n') % (PART_ID, LABEL, TITLE, PACKAGE, PACKAGE,
                                  PART_ID, PART_ID, PART_ID, PART_ID)
    return head + "\n".join(conns) + '\n </connectors>\n</module>\n'


def main():
    files = (("icon", icon_svg()),
             ("breadboard", gen_breadboard_svg()),
             ("schematic", gen_schematic_svg()),
             ("pcb", gen_pcb_svg()))
    for view, content in files:
        name = "svg.%s.%s_%s.svg" % (view, PART_ID, view)
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    fzp_name = "part.%s.fzp" % PART_ID
    with open(os.path.join(OUT_DIR, fzp_name), "w", encoding="utf-8") as f:
        f.write(gen_fzp())
    print("wrote", fzp_name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(OUT_DIR, fzp_name), arcname=fzp_name)
        for view, _ in files:
            n = "svg.%s.%s_%s.svg" % (view, PART_ID, view)
            z.write(os.path.join(OUT_DIR, n), arcname=n)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
