# -*- coding: utf-8 -*-
"""
TXW8301 — 泰芯 802.11ah SoC (QFN48) Fritzing 元件生成脚本
=========================================================
进度（fritzing-parts-langhua AGENTS.md 芯片固定工作流）：
  [x] 1. icon svg（用户 2026-09-02 定稿）
  [x] 2. breadboard svg（SMD -> 绿色转接板，用户 2026-09-02 定稿）
  [x] 3. schematic svg（方框符号 + 49 EPAD，用户 2026-09-03 定稿）
  [x] 4. pcb svg（QFN48 焊盘 + EPAD，用户 2026-09-03 定稿）
  [x] 5. part.<id>.fzp + 打包 fzpz

芯片封装（Taixin AH TXW8301 Datasheet V1.2，第 10/11 页）：
  - QFN48，体 6.0 x 6.0 x 0.75 mm，间距 e=0.40，脚 b=0.20
  - 中心散热片 EPAD D2=E2=4.60（底面，顶视图 icon 不画）
  - 48 个边脚（12/边，间距 0.4，中心距 Nd=Ne=4.4）+ EPAD 共 49 脚
  - pin1 在左上角（TOP VIEW 激光标记）

icon（用户 2026-09-02 最终版）：真实比例 1 单位 = 1 mm ——
  体 6.0 x 6.0 mm（本体黑 #303030），四边各 12 个金焊盘 0.1(径向) x 0.2(沿边)，
  间距 0.4；整体含焊盘 6.2 x 6.2 mm；pin1 圆点 r=0.25 在左上角（圆心对齐上/左首脚）；
  文字居中。

breadboard（2026-09-02 v3 定稿）：绿色转接板 32x32 mm（#1F7A34），
  中央 QFN48 芯片顶视图（居 16,16），四边每边 6 列 x 2 排排针（2.54 网格）共 48 脚，
  编号 1..48（同淘宝实物、芯片 pin1 边朝左、逆时针环序：左1-12→下13-24→右25-36→上37-48，
  每边奇=外列/偶=内列）；编号白字 1.3mm（外排朝板边/内排朝板心）；无走线；无 EPAD；
  左上/右下 M2 安装孔。连接器 connector0..47 = 引脚 1..48。
  引脚名按 datasheet 表 3-1（PIN_NAMES）。

schematic（2026-09-02/03）：矩形方框符号，参照 CH32V203C8T6（AGENTS.md §5）。
  连接器 cn 0..47 = 引脚 1..48：左 1-12(上→下)、下 13-24(左→右)、右 25-36(下→上)、上 37-48(右→左)；
  49 EPAD(connector48) 作为顶排正常引脚、紧挨 pin48 左侧。

pcb（2026-09-03）：QFN48 焊盘，几何参照嘉立创 QFN-48-L6.0-W6.0-P0.40-TL-EP4.2
  （svg 内 EasyEDA 导出，1 单位=0.254mm）：边脚 0.2(切向)x1.0(径向)、间距 0.4、中心半径 3.1、
  中央 EPAD 4.2x4.2（connector48）；pin1 左上、逆时针同 schematic。copper1 SMD + 丝印 6x6。
"""
import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "TXW8301_1"
TITLE = "TXW8301 (802.11ah SoC, QFN48)"
LABEL = "U"
PACKAGE = "QFN48"
FAMILY = "Taixin 802.11ah SoC"
FZPZ = "TXW8301.fzpz"
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID

# 颜色（与仓库 CH32V203C8T6 icon 一致）
BODY = "#303030"
PAD  = "#f7bf13"
MARK = "#c0c0c0"
TXT  = "#c0c0c0"

# 几何（单位 mm）
TOT = 6.2            # 含焊盘总宽高（体 6 + 两侧各 0.1 引脚外伸）
BODY_SIZE = 6.0      # 本体
M = (TOT - BODY_SIZE) / 2.0          # 0.1 引脚外伸
PAD_LEN = 0.1        # 径向（外伸）
PAD_W = 0.2          # 沿边
PITCH = 0.4
N_PER_SIDE = 12


def _centers():
    """每边 12 个焊盘中心（沿边方向），对称于本体中心。"""
    c0 = (TOT / 2.0) - (N_PER_SIDE - 1) * PITCH / 2.0   # 1.4
    return [c0 + i * PITCH for i in range(N_PER_SIDE)]


def icon_svg():
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" viewBox="0 0 %.1f %.1f">\n'
             % (TOT, TOT, TOT, TOT))
    L.append(' <g id="icon">\n')
    # 本体 6x6（真实尺寸）
    L.append('<rect x="%.3f" y="%.3f" width="%.2f" height="%.2f" rx="0.15" ry="0.15" fill="%s" stroke="none"/>\n'
             % (M, M, BODY_SIZE, BODY_SIZE, BODY))
    # 四边金焊盘 0.6(径向) x 0.2(沿边)，间距 0.4
    for c in _centers():
        # 上：y 0..0.6（本体上缘 y=0.6），x 居中 c，宽 0.2
        L.append('<rect x="%.3f" y="0" width="%.2f" height="%.3f" fill="%s" stroke="none"/>\n'
                 % (c - PAD_W / 2, PAD_W, PAD_LEN, PAD))
        # 下：y 6.6..7.2
        L.append('<rect x="%.3f" y="%.3f" width="%.2f" height="%.3f" fill="%s" stroke="none"/>\n'
                 % (c - PAD_W / 2, TOT - PAD_LEN, PAD_W, PAD_LEN, PAD))
        # 左：x 0..0.6
        L.append('<rect x="0" y="%.3f" width="%.3f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (c - PAD_W / 2, PAD_LEN, PAD_W, PAD))
        # 右：x 6.6..7.2
        L.append('<rect x="%.3f" y="%.3f" width="%.3f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (TOT - PAD_LEN, c - PAD_W / 2, PAD_LEN, PAD_W, PAD))
    # pin1 圆点（左上角，圆心对齐上排首脚 x=0.9 与左排首脚 y=0.9，r=0.25）
    L.append('<circle cx="0.90" cy="0.90" r="0.25" fill="%s" stroke="none"/>\n' % MARK)
    # 芯片名（居中对齐于本体中心 3.6）
    cx = TOT / 2.0
    L.append('<text x="%.3f" y="3.20" font-size="0.95" font-family="DroidSans" fill="%s"'
             ' text-anchor="middle" stroke="none" stroke-width="0">TXW8301</text>\n' % (cx, TXT))
    L.append('<text x="%.3f" y="4.25" font-size="0.55" font-family="DroidSans" fill="%s"'
             ' text-anchor="middle" stroke="none" stroke-width="0">802.11ah</text>\n' % (cx, TXT))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# 引脚名（datasheet 表 3-1，引脚 1..48；EPAD=49 单独作为 connector48，底部散热焊盘）
PIN_NAMES = [
    "VCC_LO", "VDD13_XO", "XI", "XO", "VCC", "VDD",
    "PA3", "PA0", "PA2", "PA1", "IOA30", "IOA31",
    "MCLR", "PA10", "PA11", "PA7", "PA6", "PA8",
    "PA9", "VCC_SD", "PB0", "PB1", "PB2", "PB3",
    "PB4", "PB5", "PB6", "PB7", "PB10", "PB11",
    "VCC_MIPI", "PA12", "PA13", "VDD13C", "AVCC", "VDD13D",
    "VDD", "VREF", "VDD13A", "PAOUT", "VCC_PA", "EPAOUT",
    "RF_TOUT", "VCC_RF", "VDD13_TRX", "RFIP", "VDD13_BB", "VDD13_CP1",
]

# 转接板几何（单位 mm）——每边 6 列 x 2 排排针，共 48 脚（同淘宝实物，无走线）
GB = 32.0               # 板外框
GREEN = "#1F7A34"
SILK = "#E8F0E4"
HOLER = 1.0             # 排针焊盘半径
HOLE_R = 0.35           # 钻孔
R0 = 3.2                # 每侧外排孔中心距板边
ROW = 2.54              # 内外排间距（2.54 网格）
MOUNT_R = 1.0           # 安装孔半径（M2 螺钉，孔径 2mm，透明空心）
MOUNT_HOLES = [(3.5, 28.5), (28.5, 3.5)]   # 左下角 + 右上角（透明孔）
EPAD_BB = (3.2, 3.2)    # 49 EPAD 排针中心 = (pin1.x, pin47.y) = (R0, R0)，左上角外排网格交点


def _holes_pinorder():
    """48 个排针中心，按引脚号 1..48 顺序排列（同淘宝实物，芯片 pin1 边朝左）。
    逆时针环序：左 1..12（上->下，奇=外列/偶=内列）、下 13..24（左->右，奇=外行/偶=内行）、
    右 25..36（下->上，奇=外列/偶=内列）、上 37..48（右->左，奇=外行/偶=内行）。
    即每个位置先「外」（靠板边）后「内」（靠芯片），行内交替。"""
    c = GB / 2.0
    xs = [c + (i - 2.5) * 2.54 for i in range(6)]   # 9.65..22.35 左->右
    ys = [c + (i - 2.5) * 2.54 for i in range(6)]   # 9.65..22.35 上->下
    h = []
    for k in range(6):                              # 左 1..12 上->下
        h.append((R0, ys[k]))                       # 奇：外列(左)
        h.append((R0 + ROW, ys[k]))                 # 偶：内列
    for k in range(6):                              # 下 13..24 左->右
        h.append((xs[k], GB - R0))                  # 奇：外行(下)
        h.append((xs[k], GB - R0 - ROW))            # 偶：内行
    for k in range(6):                              # 右 25..36 下->上
        h.append((GB - R0, ys[5 - k]))              # 奇：外列(右)
        h.append((GB - R0 - ROW, ys[5 - k]))        # 偶：内列
    for k in range(6):                              # 上 37..48 右->左
        h.append((xs[5 - k], R0))                   # 奇：外行(上)
        h.append((xs[5 - k], R0 + ROW))             # 偶：内行
    return h


def _chip_pad_center(pin, c=16.0):
    """芯片第 pin(1..48) 个边脚的外端中心（芯片中心 c,c，体 6x6，边脚外伸 0.1）。"""
    i = pin - 1
    half = 6.0 / 2.0
    if 1 <= pin <= 12:                    # 上：左->右
        return (c - 2.2 + i * 0.4, c - half - 0.05)
    if 13 <= pin <= 24:                   # 右：上->下
        return (c + half + 0.05, c - 2.2 + (i - 12) * 0.4)
    if 25 <= pin <= 36:                   # 下：右->左
        return (c + 2.2 - (i - 24) * 0.4, c + half + 0.05)
    return (c - half - 0.05, c + 2.2 - (i - 36) * 0.4)         # 左：下->上


def chip_art(c=16.0):
    """中央 QFN48 芯片顶视图（黑体 6x6 + 四边金边脚 0.1x0.2 + pin1 圆点）。"""
    L = []
    L.append('  <rect x="%.3f" y="%.3f" width="6" height="6" rx="0.15" fill="%s"/>\n'
             % (c - 3.0, c - 3.0, BODY))
    for pin in range(1, 49):
        x0, y0 = _chip_pad_center(pin, c)
        if pin <= 12 or 25 <= pin <= 36:  # 上/下：横向矩形
            L.append('  <rect x="%.3f" y="%.3f" width="0.2" height="0.1" fill="%s"/>\n'
                     % (x0 - 0.1, min(y0, c + 3.0) - 0.05, PAD))
        else:                             # 左/右：纵向矩形
            L.append('  <rect x="%.3f" y="%.3f" width="0.1" height="0.2" fill="%s"/>\n'
                     % (min(x0, c + 3.0) - 0.05, y0 - 0.1, PAD))
    L.append('  <circle cx="%.3f" cy="%.3f" r="0.25" fill="%s"/>\n'
             % (c - 3.0 + 0.8, c - 3.0 + 0.8, MARK))           # pin1 圆点（芯片左上）
    return "".join(L)


def breadboard_svg():
    """绿色 QFN48 转接板面包板视图 v4：32x32 板，中央芯片，每边 6 列 x 2 排排针。
    编号 1..48（左 1-12 -> 下 13-24 -> 右 25-36 -> 上 37-48，奇=外/偶=内）；
    49 EPAD 金盘在左上角（connector48，可连线）；左下/右上透明安装孔；无走线。"""
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%dmm" height="%dmm" viewBox="0 0 %d %d">\n'
             % (int(GB), int(GB), int(GB), int(GB)))
    L.append(' <g id="breadboard">\n')
    # 板外框：evenodd 路径挖穿左下/右上安装孔 -> 孔区真正透明，能看到下方面包板
    bpath = "M0 0 H%.2f V%.2f H0 Z" % (GB, GB)
    for (mx, my) in MOUNT_HOLES:
        bpath += (" M%.2f %.2f A%.2f %.2f 0 1 1 %.2f %.2f A%.2f %.2f 0 1 1 %.2f %.2f Z"
                  % (mx, my - MOUNT_R, MOUNT_R, MOUNT_R, mx, my + MOUNT_R,
                     MOUNT_R, MOUNT_R, mx, my - MOUNT_R))
    L.append('  <path d="%s" fill="%s" fill-rule="evenodd" stroke="#0f4d20" stroke-width="0.15"/>\n'
             % (bpath, GREEN))
    # 中央芯片
    L.append(chip_art(16.0))
    # 48 排针（连接器 + 钻孔 + 编号）
    holes = _holes_pinorder()
    for k, (hx, hy) in enumerate(holes):
        L.append('  <circle id="connector%dpin" cx="%.3f" cy="%.3f" r="%.3f" fill="#cbb768" stroke="#4a3f12" stroke-width="0.10"/>\n'
                 % (k, hx, hy, HOLER))
        L.append('  <circle cx="%.3f" cy="%.3f" r="%.3f" fill="#2b2b2b"/>\n' % (hx, hy, HOLE_R))
        # 编号：外排朝板边、内排朝板心，纯轴向偏移（与引脚同列/行居中），不压焊盘
        dL = hx; dR = GB - hx; dT = hy; dB = GB - hy
        m = min(dL, dR, dT, dB)
        if m == dT: ox, oy = 0.0, -1.0            # 上缘 -> 朝上
        elif m == dB: ox, oy = 0.0, 1.0            # 下缘 -> 朝下
        elif m == dL: ox, oy = -1.0, 0.0           # 左缘 -> 朝左
        else: ox, oy = 1.0, 0.0                    # 右缘 -> 朝右
        outer = m <= 4.2
        s = 1.0 if outer else -1.0                 # 外排向板边 / 内排向板心
        off = 1.9 if outer else 1.7
        nx = hx + s * ox * off
        ny = hy + s * oy * off
        L.append('  <text x="%.3f" y="%.3f" font-size="1.3" fill="%s" text-anchor="middle" font-family="Arial">%d</text>\n'
                 % (nx, ny + 0.47, SILK, k + 1))
    # 49 EPAD —— 左上角（同其它排针样式：焊盘环 + 中央钻孔；connector48）
    epx, epy = EPAD_BB
    L.append('  <circle id="connector48pin" cx="%.3f" cy="%.3f" r="%.3f" fill="#cbb768" stroke="#4a3f12" stroke-width="0.10"/>\n'
             % (epx, epy, HOLER))
    L.append('  <circle cx="%.3f" cy="%.3f" r="%.3f" fill="#2b2b2b"/>\n' % (epx, epy, HOLE_R))
    L.append('  <text x="%.3f" y="%.3f" font-size="1.3" fill="%s" text-anchor="middle" font-family="Arial">49</text>\n'
             % (epx, epy + 2.3, SILK))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def schematic_svg():
    """矩形方框原理图符号（48 脚；连接器 cn 0..47 = 引脚 1..48，名取 PIN_NAMES）。
    AGENTS.md §5 规则（参照 CH32V203C8T6）：
      左 1-12(上→下)、下 13-24(左→右)、右 25-36(下→上)、上 37-48(右→左)。
      引脚名在框内、方向同数字；左右数字在引线上方（不与线相交）、上下数字在引脚左侧；
      名/数字/引线同色（无数据手册标蓝要求 -> 全黑）；数字与引脚名整图同字号 FN=35。
      左右名基线手动偏移 y=y+BASELINE_OFF 垂直居中（不用 dominant-baseline）；
      名距边框一个字符 CH；四角留 CORNER 空白（=最长名宽+1字符）使上下名与左右名不交叉；
      上下数字右侧距引脚 FN/2、上下名左缘与数字右缘对齐。
    物理尺寸由 width/height(in) 决定，1000 单位 = 1in。"""
    P = 100                       # 引脚间距（0.1in = 2.54mm）
    WIRE = 130                    # 引脚线长
    CH = FN = 35                  # 一个字符间距 = 整图统一字号
    BASELINE_OFF = round(FN * 0.35)   # 左右名基线手动垂直居中偏移
    max_len = max(len(n) for n in PIN_NAMES)      # 10：VDD13_CP1
    CORNER = (max_len + 1) * int(FN * 0.58)       # 四角无引脚宽度 = 最长名宽 + 1 字符宽
    BOX = 12 * P + 2 * CORNER                     # 框 = 12P + 2×CORNER（对称）
    BX0, BY0 = 300, 200
    BX1, BY1 = BX0 + BOX, BY0 + BOX
    BLK = "#000000"
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    # 裁边：内容 bbox = [BX0-WIRE .. BX1+WIRE] x [BY0-WIRE .. BY1+WIRE]，四周留 20 单位
    M = 20
    VX0, VY0 = BX0 - WIRE - M, BY0 - WIRE - M
    VSIDE = (BX1 - BX0) + 2 * WIRE + 2 * M
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.3fin" height="%.3fin" viewBox="%d %d %d %d">\n'
             % (VSIDE / 1000.0, VSIDE / 1000.0, VX0, VY0, VSIDE, VSIDE))
    L.append(' <g id="schematic">\n')
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" stroke="#c00000" stroke-width="5"/>\n'
             % (BX0, BY0, BOX, BOX))
    # 左 1-12（上→下）：数字在引线上方；名在框内居中于引脚、距左边框一个字符
    for i in range(12):
        cn = i
        y = BY0 + CORNER + P // 2 + i * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{BX0}" y1="{y}" x2="{BX0 - WIRE}" y2="{y}" stroke="{BLK}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX0 - WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX0 - WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        L.append(f'  <text x="{BX0 + CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{BLK}" text-anchor="start" '
                 f'font-family="DroidSans">{esc(PIN_NAMES[cn])}</text>\n')
    # 下 13-24（左→右）：数字在引脚左侧（从下至上 rotate 270）；名在框内靠下
    for i in range(12):
        cn = 12 + i
        x = BX0 + CORNER + P // 2 + i * P
        lab = PIN_NAMES[cn]
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{x}" y1="{BY1}" x2="{x}" y2="{BY1 + WIRE}" stroke="{BLK}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{x - 11}" y="{BY1 + WIRE}" width="22" height="22" fill="none"/>\n')
        # 数字在引脚左侧、从下至上（rotate 270），右侧距引脚 FN/2（锚点 x-FN）
        L.append(f'  <text x="{x - FN}" y="{BY1 + 55}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x - FN} {BY1 + 55})">{13 + i}</text>\n')
        ln = int(len(lab) * FN * 0.58)   # 文字高（rotate270+middle → 文字以锚点为中心，底边=锚点+ln/2）
        L.append(f'  <text x="{x}" y="{BY1 - CH - ln // 2}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x} {BY1 - CH - ln // 2})">{esc(lab)}</text>\n')
    # 右 25-36（下→上）：数字在引线上方；名在框内靠右
    for i in range(12):
        cn = 24 + i
        y = BY1 - CORNER - P // 2 - i * P
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="{BLK}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans">{25 + i}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{BLK}" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PIN_NAMES[cn])}</text>\n')
    # 上 37-48（右→左）：数字在引脚左侧（从下至上 rotate 270）；名在框内靠上
    for i in range(12):
        cn = 36 + i
        x = BX1 - CORNER - P // 2 - i * P
        lab = PIN_NAMES[cn]
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{cn}" '
                 f'x1="{x}" y1="{BY0}" x2="{x}" y2="{BY0 - WIRE}" stroke="{BLK}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{x - 11}" y="{BY0 - WIRE}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{x - FN}" y="{BY0 - 50}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x - FN} {BY0 - 50})">{37 + i}</text>\n')
        ln = int(len(lab) * FN * 0.58)
        L.append(f'  <text x="{x}" y="{BY0 + CH + ln // 2}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
                 f'font-family="DroidSans" transform="rotate(270 {x} {BY0 + CH + ln // 2})">{esc(lab)}</text>\n')
    # 49 EPAD —— 散热焊盘，作为顶排正常引脚，紧挨 pin48（最左顶脚）左侧，样式同顶列
    ep_x = BX1 - CORNER - P // 2 - 12 * P
    L.append(f'  <line class="pin" id="connector48pin" connectorname="48" '
             f'x1="{ep_x}" y1="{BY0}" x2="{ep_x}" y2="{BY0 - WIRE}" stroke="{BLK}" stroke-width="5"/>\n')
    L.append(f'  <rect id="connector48terminal" x="{ep_x - 11}" y="{BY0 - WIRE}" width="22" height="22" fill="none"/>\n')
    L.append(f'  <text x="{ep_x - FN}" y="{BY0 - 50}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
             f'font-family="DroidSans" transform="rotate(270 {ep_x - FN} {BY0 - 50})">49</text>\n')
    epln = int(len("EPAD") * FN * 0.58)
    L.append(f'  <text x="{ep_x}" y="{BY0 + CH + epln // 2}" font-size="{FN}" fill="{BLK}" text-anchor="middle" '
             f'font-family="DroidSans" transform="rotate(270 {ep_x} {BY0 + CH + epln // 2})">EPAD</text>\n')
    # 芯片名（框内居中）
    CHIP_X = (BX0 + BX1) // 2
    L.append(f'  <text x="{CHIP_X}" y="1035" font-size="79" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">TXW8301</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def pcb_svg():
    """QFN48 (6x6, 0.4 pitch) PCB 焊盘 —— 参照嘉立创 QFN-48-L6.0-W6.0-P0.40-TL-EP4.2。
    1 单位 = 1mm，中心 c=4.5，画布 9x9。
      copper1 SMD：边脚 0.2(切向) x 1.0(径向) mm，中心半径 3.1（体 6.0 外缘 0.1/内缘 2.6）；
      中央 EPAD 4.2x4.2（connector48）。
      pin1 左上、逆时针同 schematic：左 1-12(上→下)、下 13-24(左→右)、右 25-36(下→上)、上 37-48(右→左)。
      silkscreen：6x6 体轮廓 + pin1 圆点（近左上角，避开焊盘）。"""
    c = 4.5
    R = 3.1                       # 边脚中心半径（0.2x1.0 焊盘，外缘 3.6）
    PITCH = 0.4
    cen = [c - 2.2 + i * PITCH for i in range(12)]     # c-2.2 .. c+2.2
    PW_T, PW_R = 0.2, 1.0         # 切向 / 径向
    CP = "#F7BD13"
    pads, silk = [], []
    # 左 1-12（上→下）：径向沿 x（外伸向左）
    for i in range(12):
        y = cen[i]
        pads.append(f'<rect id="connector{i}pad" x="{c - R - PW_R / 2:.3f}" y="{y - PW_T / 2:.3f}" '
                    f'width="{PW_R:.3f}" height="{PW_T:.3f}" fill="{CP}" stroke="none" connectorname="{i}"/>')
    # 下 13-24（左→右）：径向沿 y（外伸向下）
    for j in range(12):
        x = cen[j]
        pads.append(f'<rect id="connector{12 + j}pad" x="{x - PW_T / 2:.3f}" y="{c + R - PW_R / 2:.3f}" '
                    f'width="{PW_T:.3f}" height="{PW_R:.3f}" fill="{CP}" stroke="none" connectorname="{12 + j}"/>')
    # 右 25-36（下→上）：径向沿 x（外伸向右）
    for i in range(12):
        y = cen[11 - i]
        pads.append(f'<rect id="connector{24 + i}pad" x="{c + R - PW_R / 2:.3f}" y="{y - PW_T / 2:.3f}" '
                    f'width="{PW_R:.3f}" height="{PW_T:.3f}" fill="{CP}" stroke="none" connectorname="{24 + i}"/>')
    # 上 37-48（右→左）：径向沿 y（外伸向上）
    for j in range(12):
        x = cen[11 - j]
        pads.append(f'<rect id="connector{36 + j}pad" x="{x - PW_T / 2:.3f}" y="{c - R - PW_R / 2:.3f}" '
                    f'width="{PW_T:.3f}" height="{PW_R:.3f}" fill="{CP}" stroke="none" connectorname="{36 + j}"/>')
    # 中央散热焊盘 EPAD 4.2x4.2（connector48）
    pads.append(f'<rect id="connector48pad" x="{c - 2.1:.3f}" y="{c - 2.1:.3f}" width="4.200" height="4.200" '
                f'fill="{CP}" stroke="none" connectorname="48"/>')
    # 丝印：6x6 体画成四角 L 短标（每条只画靠角一段，与首/末脚切线留 0.15 间隙，绝不压焊盘）
    #       + 左上角 pin1 实心点（代替角标，标记 1 脚）。
    R_ = 3.0                          # 体半宽（丝印角标所在体边）
    T = 0.55                          # 角标沿边长度（端到首脚切线留 0.15）
    c0, c1 = c - R_, c + R_
    def silk_line(x1, y1, x2, y2):
        silk.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
                    f'stroke="#f0f0f0" stroke-width="0.12"/>')
    silk_line(c0, c0, c0 + T, c0)          # 上边-左
    silk_line(c1 - T, c0, c1, c0)          # 上边-右
    silk_line(c1, c0, c1, c0 + T)          # 右边-上
    silk_line(c1, c1 - T, c1, c1)          # 右边-下
    silk_line(c1, c1, c1 - T, c1)          # 下边-右
    silk_line(c0 + T, c1, c0, c1)          # 下边-左
    silk_line(c0, c1, c0, c1 - T)          # 左边-下
    silk_line(c0, c0 + T, c0, c0)          # 左边-上
    # pin1 实心点（左上角体角，避开 pad1/pad48）
    silk.append(f'<circle cx="{c0:.3f}" cy="{c0:.3f}" r="0.22" fill="#f0f0f0" stroke="none" class="other"/>')
    inner = "\n".join(pads) + '\n<g id="copper0"/>\n  </g>\n  <g id="silkscreen">\n' + "\n".join(silk)
    # 裁边：内容（焊盘外缘 3.6）bbox = c±3.6 = 0.9..8.1，四周留 0.3
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="7.8mm" height="7.8mm" viewBox="0.6 0.6 7.8 7.8">\n'
            '  <g id="copper1">\n' + inner + '\n  </g>\n</svg>\n')


def gen_fzp():
    """part.<id>.fzp：49 连接器。
    connector0..47 = 引脚 1..48（type=male，转接板排针可连线：breadboard/schematic/pcb 三视图）；
    connector48 = EPAD（type=pad，底部散热焊盘：仅 schematic+pcb，无面包板）。"""
    conns = []
    for i, name in enumerate(PIN_NAMES):
        conns.append(
            f'  <connector id="connector{i}" name="{esc(name)}" type="male">\n'
            f'   <description>{esc(name)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{i}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{i}pin" terminalId="connector{i}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{i}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    # EPAD：散热焊盘（面包板左上角金盘可连线 + schematic + pcb 中心铜区）
    conns.append(
        '  <connector id="connector48" name="EPAD" type="pad">\n'
        '   <description>EPAD (exposed thermal pad, connect to GND)</description>\n'
        '   <views>\n'
        '    <breadboardView>\n     <p layer="breadboard" svgId="connector48pin"/>\n    </breadboardView>\n'
        '    <schematicView>\n     <p layer="schematic" svgId="connector48pin" terminalId="connector48terminal"/>\n    </schematicView>\n'
        '    <pcbView>\n     <p layer="copper1" svgId="connector48pad"/>\n    </pcbView>\n'
        '   </views>\n'
        '  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>4</version>\n <date>2026-09-03</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>{PACKAGE}</tag>\n  <tag>802.11ah</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n  <property name="chip">TXW8301</property>\n'
            f'  <property name="pins">49</property>\n </properties>\n'
            f' <views>\n  <breadboardView>\n   <layers image="breadboard/{PART_ID}_breadboard.svg">\n'
            f'    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            f'  <schematicView>\n   <layers image="schematic/{PART_ID}_schematic.svg">\n'
            f'    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
            f'  <pcbView>\n   <layers image="pcb/{PART_ID}_pcb.svg">\n'
            f'    <layer layerId="copper1"/>\n    <layer layerId="silkscreen"/>\n   </layers>\n  </pcbView>\n'
            f'  <iconView>\n   <layers image="icon/{PART_ID}_icon.svg">\n'
            f'    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n </views>\n'
            f' <connectors>\n' + "\n".join(conns) + '\n </connectors>\n</module>\n')


def main():
    files = {
        "breadboard": breadboard_svg(),
        "schematic": schematic_svg(),
        "pcb": pcb_svg(),
        "icon": icon_svg(),
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
