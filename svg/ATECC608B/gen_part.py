#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — 生成 Fritzing 自定义元件 ATECC608B（Microchip CryptoAuthentication，I2C，SOIC-8）。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件（part.<id>.fzp + 4 个 svg.<view>.* + 本脚本）同目录，.fzpz 输出到仓库顶层 fzpz/。
打包规则（docs/part-dev-guide.md §2.2）：.fzpz 内部平铺，.fzp 的 image= 用子目录路径。

数据来源：
  · `D:\Downloads\ATECC608B.pdf`（Microchip **Summary** Data Sheet DS40002239A，28 页）
      - 引脚（§Pin Configuration Table 1 + Figure 1，SOIC-8 顶视、pin1 左下、逆时针 1→8）：
        **1=NC 2=NC 3=NC 4=GND 5=SDA 6=SCL 7=NC 8=VCC**
      - 封装（§5.1）：**8-Lead Plastic Small Outline - Narrow, 3.90 mm (.150 In.) Body [SOIC]**，
        Microchip 图号 **C04-057-SWB Rev E**（Atmel legacy code SWB）。
      - ★ **§4 Package Marking Information：加密器件的顶面丝印是「故意模糊」的** ——
        "the part marking ... is intentionally vague. The marking on the top of the package does not
        provide any information as to the actual device type"，且"随装配批号变化"。
        ⇒ **本元件不印型号**（印一个型号就是编造）；照**用户实物的顶面码**印 `CN`
          （2026-09-22 用户指定）—— 它就是 §4 说的那种“制造信息码”，**换批号就不同**。
        ⚠ 完整命令集/机械尺寸表在 NDA 版手册里；本 PDF 是矢量图，数值表抽不出文本 ⇒
          D/e/b/跨距取**窄体 SOIC-8 标准值**（与同库 `AT24C02`（SOP-8）一致，保证库里看着一致）：
          本体 3.90(E) × 4.90~5.05(D)、节距 e=1.27、脚宽 b=0.42、含脚跨距 6.00mm。
  · 参考同族件 `svg/AT24C02/`（同为 SOIC-8 上绿转接板），几何约定直接沿用。

★ 面包板几何的**实物依据**（用户 2026-09-22）：
  · 实物 = 淘宝常见的 **"SOP8 1.27mm 转接板"**（用户提供照片；**照片是第三方素材，不入库**）。
  · 照照片画出来是：**两排排针在左右两侧**（左列 `1..4` 上→下、右列 `8..5` 上→下 = 逆时针），
    两列相距 **7.62mm**；同列相邻脚 2.54mm；板 **10.16×10.16mm**（排针到板边 1.27mm）；
    板中央是 SOIC 的**上下两排**焊盘 ⇒ 芯片引脚朝上下。
  · 8 个脚（含 4 个 NC）**都是可接线的 connector**；四个视图全做。
⚠ 如实两条：
  ① **脚号画在焊盘外侧**（照片里就是外侧）—— 内侧放不下：两列间距被实物定死 7.62mm、
     芯片本体宽 5.05mm ⇒ 每侧只剩 1.28mm，放不下 1.5mm 字号；AGENTS §3b 给内侧放不下时的
     办法是"把排针往板边移"，但**本件间距由实物定死**、移不了 ⇒ 照实物画，字号压到 48（1.22mm）。
  ② AGENTS §3b 说"排针行距 ≥ 元件高 + 2mm"（本芯片含脚总高 6.0mm ⇒ 建议 10.16mm），
     而 7.62mm 是**实物**尺寸 ⇒ 按实物画。代价：2mm 金环（画法约定）与芯片脚端在图上
     重叠约 0.19mm/侧（实物是 1mm 孔，内缘 3.31mm > 脚端 3.0mm，并不冲突）。

用法：
  python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "ATECC608B"
FZPZ = "ATECC608B.fzpz"

# 引脚定义（SOIC-8：下排 1-4 左→右、上排 8-5 左→右；pin1 左下）。
# ⚠ 名字照手册 Table 1 原样：4 个未引出脚就叫 **NC**（不"顺手补全"成 VCC/GND 之类）。
PINS = [
    "NC",   # 1
    "NC",   # 2
    "NC",   # 3
    "GND",  # 4
    "SDA",  # 5
    "SCL",  # 6
    "NC",   # 7
    "VCC",  # 8
]

# 转接板丝印（**默认不印**，别当它是"漏了"）：
#   ① 芯片顶面已经印了实物制造码 `CN`（见 `ICON_MARK`）—— 手册 §4 说那串码不是型号、
#      随批号变 ⇒ 再在板上印个型号反而容易让人把它当“型号丝印”；识别靠 Fritzing 的 label/title。
#   ② 12.70×12.70mm 的板上**没有不与脚号重叠的地方** —— 实测把 `ATECC608B` 放在芯片下沿时
#      正好压在脚号 `1`/`4` 上（AGENTS §3b：丝印必须避开焊盘/引脚）。要印就得加大板子尺寸。
# 想恢复：把下面这行改成 "ATECC608B"，并把 `cy + 95` 那个 y 挪到板外或加高板子（板 = 单源 BOARD_W/H）。
BOARD_LABEL = ""
SCHEM_LABEL = "ATECC608B"
# 芯片顶面丝印（**照用户实物的制造码**，不是型号）：手册 §4 说这串码随装配批号变，
# 所以它只代表这一批的实物；换成别的批号就得改这里（一处常量）。
ICON_MARK = "CN"

# .fzp 元数据
TITLE = "ATECC608B CryptoAuthentication Device (I2C, SOIC-8)"
LABEL = "U"
PACKAGE = "SOIC-8"
FAMILY = "CryptoAuthentication"

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- ATECC608B CryptoAuthentication (I2C) -->\n')

# ---- 几何（mm，除注明外）------------------------------------------------
BODY_D = 5.05      # 本体长（D，沿引脚排布方向）
BODY_E = 3.90      # 本体宽（E，窄体 SOIC = 3.90mm，手册 §5.1）
LEAD_E = 1.27      # 引脚节距
LEAD_B = 0.42      # 引脚宽
LEAD_L = 1.05      # 引脚伸出长度（⇒ 含脚总跨距 3.90 + 2×1.05 = 6.00mm）
SPAN = BODY_E + 2 * LEAD_L
# 面包板视图（100 单位 = 2.54mm）—— **照用户 2026-09-22 给的实物照片**（淘宝 SOP8 1.27mm 转接板）
ROW_U = 300        # ★ 两排排针的间距 = 3×2.54 = **7.62mm**（在左右两侧，不是上下）
COL_U = 100        # 同一列里相邻脚距 = 2.54mm（4 脚 ⇒ 跨 3×2.54 = 7.62mm）
MARGIN = 100       # 排针中心到板边（= 2.54mm）—— **不是**照片上那 1.27mm，理由见 gen_breadboard_svg()
BOARD_W = ROW_U + 2 * MARGIN   # 板宽 = 500 单位 = 12.70mm
BOARD_H = 3 * COL_U + 2 * MARGIN   # 板高 = 500 单位 = 12.70mm
NUM_FS = 48        # 脚号字号（1.22mm）
NUM_OFF = 65       # 脚号中心离焊盘中心 65 单位（= 焊盘半径 39.4 + 字半高 24 + 余量）
U = 39.37          # 1mm = 100/2.54 单位


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装符号（SOIC-8，左右各 4 脚）。按 AGENTS.md §5 矩形原理图规则：
    1. 左右引脚数字在引线上方（不与线相交）：左 1-4 上→下、右 8-5 上→下（逆时针）。
    2. 引脚名在框内、书写方向同数字、与引脚水平中线对齐（手动基线偏移，不用 dominant-baseline）；
       名/数字/引线同色（黑）。
    3. 数字与引脚名整图同字号 FN=35。
    4. 引脚名与边框保持一个字符 CH=FN 间距，居左/右。
    5. 四角无引脚区 CORNER=(最长名宽+1)×int(FN×0.58)，引脚从 CORNER 后开始排，
       框 = 4P + 2×CORNER（完全对称）。
    物理尺寸 width/height(in)，1000 单位 = 1in；viewBox 贴合内容（裁边）。"""
    P = 100                       # 引脚间距（2.54mm）
    WIRE = 130                    # 引脚线长
    CH = 35                       # 一个字符间距（= 字号）
    FN = 35                       # 整图统一字号（数字与引脚名）
    BASELINE_OFF = round(FN * 0.35)   # 手动垂直居中基线偏移
    max_len = max(len(n) for n in PINS)        # 3（NC / GND / SDA / SCL / VCC）
    CORNER = (max_len + 1) * int(FN * 0.58)    # 四角无引脚宽度
    per = len(PINS) // 2                      # 4
    BX0, BY0 = 340, 200
    BW = 800                                  # 框宽
    BH = per * P + 2 * CORNER                 # 框高
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - 5        # viewBox 左上（贴合内容）
    VBW, VBH = BW + 2 * WIRE + 10, BH + 10    # viewBox 宽高
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" height="{VBH / 1000:.6f}in" '
             f'viewBox="{VBX} {VBY} {VBW} {VBH}">\n')
    L.append(' <g id="schematic">\n')
    # 封装体（白底灰边）
    L.append(f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
             f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n')
    # 左 1-4（上→下）：数字在引线上方，名在框内靠左
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
    # 右 8-5（上→下）：数字在引线上方，名在框内靠右
    for i in range(per):
        y = BY0 + CORNER + P // 2 + i * P
        cn = per * 2 - 1 - i          # 顶部 connector7(pin8) → 底部 connector4(pin5)
        col = "#000000"
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{BX1}" y1="{y}" x2="{BX1 + WIRE}" y2="{y}" stroke="{col}" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{BX1 + WIRE}" y="{y - 11}" width="22" height="22" fill="none"/>\n')
        L.append(f'  <text x="{BX1 + WIRE // 2}" y="{y - 24}" font-size="{FN}" fill="{col}" text-anchor="middle" '
                 f'font-family="DroidSans">{per * 2 - i}</text>\n')
        L.append(f'  <text x="{BX1 - CH}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="{col}" text-anchor="end" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')
    # 芯片名（框内居中）
    CHIP_FS = 79
    CHIP_Y = BY0 + BH // 2 + round(CHIP_FS * 0.35)
    L.append(f'  <text x="{BX0 + BW // 2}" y="{CHIP_Y}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(SCHEM_LABEL)}</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def _embed_icon(art, cx, cy, s=1.0, icx=0.0, icy=0.0, text_dy=0.0):
    """把 icon 组内容（mm）放大 s，使 icon 视觉中心 (icx,icy) 映射到 (cx,cy)。
    不旋转（保持 icon 方向：pin1 左下）。烘焙绝对坐标（处理 rect/circle/text）。"""
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
    for cm in re.finditer(r'<circle\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        px = (float(a["cx"]) + tx - icx) * s + cx
        py = (float(a["cy"]) + ty - icy) * s + cy
        out.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["r"]) * s,
            a.get("fill", "#c0c0c0"), a.get("stroke", "none")))
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
    """面包板 = 绿色 SOP8→DIP 转接板 + 8 排针 + 居中 ATECC608B icon（1:1，pin1 左下）。
    ★ 布局**照用户 2026-09-22 给的实物照片**（淘宝 "SOP8 1.27mm 转接板"）：
      · 两排排针在**左右两侧**：左列 = pin1..4（上→下）、右列 = pin8..5（上→下）
        —— 也就是逆时针 1(左上)→4(左下)→5(右下)→8(右上)；
      · 两列相距 **300 单位 = 7.62mm**；同列相邻脚 100 单位 = 2.54mm；
      · 板 **500×500 单位 = 12.70×12.70mm**（排针中心到板边 2.54mm）。
        ⚠ 实物板只有 ~10.2mm（照片上排针到板边约 1.27mm），**这里故意画大**：本仓转接板
        按「2mm 金环 + 0.97mm 孔」画（AGENTS §3b），而 2mm 环半径 1mm ⇒ 7.62mm 间距下
        每侧只剩 1.27mm，环几乎贴到板边、脚号也没地方放（先按 10.16mm 画过一版，渲染里
        脚号被压在环上）。反推：脚号中心要离板边 ≥ 字半高 24、又不量压环 ⇒
        排针中心到板边 ≥ 24 + 39.4 ≈ 90 单位 ⇒ 取 **100**（2.54mm，与同库 AT24C02 同比例）。
        实物板看着更紧凑是因为它的焊盘只有 ~1.5mm、脚号也只有 ~1mm。
      · 8 个脚（含 4 个 NC）**都是可接线的 connector**；四个视图全做。
  · 板中央是 SOIC 的上下两排焊盘（照片里那两排白焊盘）⇒ 芯片按 icon 原样**引脚朝上下**放。
    ⚠ 脚号画在**焊盘外侧**（照片里就是外侧）—— 与 AGENTS §3b「数字要在内侧」的取舍写清楚：
      两列间距被实物固定成 7.62mm，而芯片本体宽 5.05mm ⇒ 每侧只剩 (7.62-5.05)/2 = **1.28mm**，
      放不下 1.5mm（60 单位）的字号；§3b 给内侧放不下时的办法是"把排针往板边移"，但**本件的
      间距由实物定死**、不能动 ⇒ 照实物照片画在外侧，并把字号压到 48（1.22mm）。
      要改回内侧：把 `x_left - NUM_OFF` / `x_right + NUM_OFF` 换成 `+ NUM_OFF` / `- NUM_OFF`
      （会压到芯片边上）。"""
    per = len(PINS) // 2                      # 4
    x_left, x_right = MARGIN, MARGIN + ROW_U  # 100 / 400（排针中心，MARGIN=100、ROW_U=300）
    y_pins = [MARGIN + i * COL_U for i in range(per)]     # 50,150,250,350
    cx, cy = BOARD_W // 2, BOARD_H // 2                   # 芯片中心 (200, 200)
    pad_r = 1.0 * U                           # 2mm 直径焊盘 → 半径 1mm（AGENTS §3b 约定）
    hole_r = 0.485 * U                        # 0.97mm 直径针孔
    icon = gen_icon_svg()
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    art = _m.group(1) if _m else ""
    _vm = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', icon)
    icx = icy = 0.0
    if _vm:
        vx, vy, vw, vh = map(float, _vm.groups())
        icx, icy = vx + vw / 2, vy + vh / 2
    bx0, by0 = 0, 0
    bw, bh = BOARD_W, BOARD_H
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" height="{bh / 100 * 2.54:.2f}mm" '
             f'viewBox="{bx0} {by0} {bw} {bh}">\n')
    s.append(' <g id="breadboard">\n')
    # 绿色转接板（直角）
    s.append(f'  <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    # 芯片 icon（1:1 居中）
    s.append(_embed_icon(art, cx, cy, s=U, icx=icx, icy=icy))
    # 板上的型号标注（**默认不印**，理由见文件头）
    if BOARD_LABEL:
        s.append(f'  <text x="{cx}" y="{cy + 95}" font-size="46" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans">{esc(BOARD_LABEL)}</text>\n')
    # 8 排针：左列 connector0-3（pin1-4 上→下）、右列 connector7-4（pin8-5 上→下）
    for i in range(per):
        y = y_pins[i]
        for xx, cn in ((x_left, i), (x_right, per * 2 - 1 - i)):
            s.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                     f'cx="{xx:.1f}" cy="{y:.1f}" r="{pad_r:.1f}" '
                     f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
            s.append(f'  <circle cx="{xx:.1f}" cy="{y:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    # 脚号：焊盘**外侧**（照片里就是外侧），**不旋转**（水平正着写）
    # ⚠ 旋转这事来回改过：§3b 写的是 `rotate(-90 x y)`（逆时针）→ 用户 2026-09-22 说顺时针
    #   （`rotate(90)`）→ 随即澄清：「文字**不转动**」⇒ 现在**不加 transform**。
    #   位置/字号仍是外侧 48（1.22mm）。水平写时字宽 ±13、字高 ±17，都还在板内且不压焊盘环
    #   （数字 x 22..48 与焊盘环 60.6..139.4 不重叠）。
    nx_l, nx_r = x_left - NUM_OFF, x_right + NUM_OFF
    for i in range(per):
        y = y_pins[i]
        s.append(f'  <text x="{nx_l:.1f}" y="{y:.1f}" font-size="{NUM_FS}" fill="#ffffff" '
                 f'text-anchor="middle" dominant-baseline="central" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
        s.append(f'  <text x="{nx_r:.1f}" y="{y:.1f}" font-size="{NUM_FS}" fill="#ffffff" '
                 f'text-anchor="middle" dominant-baseline="central" '
                 f'font-family="DroidSans">{per * 2 - i}</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（**SOIC-8 真实封装**，同库 AT24C02 的口径）：焊盘 RECT 0.7×1.8mm（x×y）、
    间距 1.27mm、两排中心距 ±2.7mm（跨距 6.0mm 的一半 ≈ 3.0，焊盘中心取 ±2.7）。
    下排 connector0-3（pin1-4）y=+2.7 左→右、上排 connector7-4（pin8-5）y=-2.7 左→右。
    丝印本体线框 5.05×3.9 + pin1 圆点（左下）。
    Fritzing 层结构：copper1 > copper0（空）+ 焊盘；silkscreen。坐标 mm，viewBox 贴合（裁边）。"""
    pw, pl = 0.7, 1.8        # 焊盘宽（x）× 长（y）
    pitch = 1.27             # 引脚间距
    row = 2.7                # 上下排焊盘中心 y = ±2.7
    per = len(PINS) // 2
    x0 = -(per - 1) * pitch / 2        # 最左焊盘中心 x = -1.905
    pads, silk = [], []
    for i in range(per):
        x = x0 + i * pitch
        cn = i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    for i in range(per):
        x = x0 + i * pitch
        cn = per * 2 - 1 - i
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    hx, hy = BODY_D / 2, BODY_E / 2            # 本体半长/半宽 = 2.525 / 1.95
    silk.append(f'<line x1="{-hx}" y1="{-hy}" x2="{-hx}" y2="{hy}" stroke="#f0f0f0" stroke-width="0.15"/>')
    silk.append(f'<line x1="{hx}" y1="{-hy}" x2="{hx}" y2="{hy}" stroke="#f0f0f0" stroke-width="0.15"/>')
    silk.append('<circle cx="-2.955" cy="2.7" r="0.4" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    SX, SY, M = 3.36, 4.1, 0.15
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * (SX + M):.2f}mm" height="{2 * (SY + M):.2f}mm" '
            f'viewBox="{-(SX + M):.2f} {-(SY + M):.2f} {2 * (SX + M):.2f} {2 * (SY + M):.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """SOIC-8（窄体 3.90mm）芯片图标：本体 5.05(D, x) × 3.90(E, y) mm，上下各 4 银引脚
    （宽 0.42、距 1.27、各伸 1.05 → 含脚总跨距 6.00mm），pin1 左下圆形凹点，
    顶面丝印 `ICON_MARK`（= 用户实物的制造码 `CN`，**不是型号**，见文件头与 §4）。
    viewBox 对称居中 5.05×6.0。"""
    e, bw, pl = LEAD_E, LEAD_B, LEAD_L
    half_x, half_y = BODY_D / 2, BODY_E / 2
    xs = [-(3 * e) / 2 + i * e for i in range(4)]   # -1.905, -0.635, 0.635, 1.905
    parts = [SVG_HDR,
             f'<svg xmlns="http://www.w3.org/2000/svg" width="{BODY_D}mm" height="{SPAN:.2f}mm" '
             f'viewBox="{-half_x} {-SPAN / 2:.2f} {BODY_D} {SPAN:.2f}">\n'
             '  <g id="icon">\n']
    # 本体（直角、深色）
    parts.append(f'    <rect x="{-half_x}" y="{-half_y}" width="{2 * half_x}" height="{2 * half_y}" '
                 f'fill="#303030" stroke="none"/>\n')
    # 上、下各 4 个银引脚（从本体上下边各伸 1.05mm）
    for x in xs:
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{-half_y - pl:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')
        parts.append(f'    <rect x="{x - bw / 2:.3f}" y="{half_y:.2f}" width="{bw:.2f}" height="{pl:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')
    # pin1 标记（本体左下角内，圆形凹点）
    parts.append(f'    <circle cx="{-half_x + 0.62:.2f}" cy="{half_y - 0.62:.2f}" r="0.28" '
                 f'fill="#c0c0c0" stroke="none"/>\n')
    # 顶面丝印（实物制造码；字号 0.9mm ⇒ 2 个字符约 1.0mm 宽，本体 5.05mm 装得下）
    if ICON_MARK:
        parts.append(f'    <text x="0" y="0.32" font-size="0.9" fill="#ffffff" text-anchor="middle" '
                     f'font-family="DroidSans">{esc(ICON_MARK)}</text>\n')
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
