#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 CN3165 (如韵电子 单节锂电充电管理, DFN-8)。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件同目录，.fzpz 输出到仓库顶层 fzpz/（内部平铺，.fzp 的 image= 用子目录路径）。

数据来源：`D:\\Downloads\\CN3165.pdf`（如韵电子 CONSONANCE，REV 1.0）
  - 第 4 页「管脚功能描述」表（9 项，逐条与 T-Halow-RJ45 原理图 U1 的网标一致）：
      1 TEMP（电池温度检测输入，接电池 NTC；接地则禁止温度检测）
      2 ISET（恒流充电电流设置 / 监测，Rsiet 到地）
      3 GND（电源地）
      4 VIN（输入电源正端，4.4~6V）
      5 BAT（电池正极，提供充电电流与 4.2V 恒压）
      6 DONE（漏极开路：充电结束指示）
      7 CHRG（漏极开路：充电中指示）
      8 FB（电池电压检测输入；与 BAT 间加电阻可上调恒压值）
      9 PAD（芯片背面**散热片**，手册写明「需要接到地(GND)」）
  - 第 1 页「管脚排列」图：**左列 1-4（上→下 TEMP/ISET/GND/VIN）、右列 5-8（下→上 BAT/DONE/CHRG/FB）**
    ⇒ 即左 1-4、右 8-5，与 AGENTS §5「两排封装用左右两列」一致。
  - 第 12 页「封装信息」DFN-8 机械图（Dimensions In Millimeters）：
      D = E = **2.900 ~ 3.100**（本体 3.0mm 见方）、A = 0.700~0.900（高）
      **e = 0.500 TYP**（脚距）、b = 0.180~0.300（脚宽）、L = 0.300~0.500（脚长）
      D1 = 2.300~2.500 × E1 = 1.600~1.800（**底部散热盘**）
  - 订购信息：封装形式 **DFN-8**，表面印记 THY（第 3 页）

⚠ 焊盘尺寸（land pattern）**手册没给**，本脚本按「手册封装尺寸 + 常规外扩」**推导**，推导过程写在
  gen_pcb_svg() 的注释里（引脚端点 = D/2 + L；焊盘中心取引脚中点；散热盘比芯片盘外扩 0.05/侧）。
  等你拿到嘉立创/立创EDA 的 DFN-8(3×3) 封装数据后，再按它校一遍。

用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CN3165"
FZPZ = "CN3165.fzpz"

# 引脚定义 pin1..9（手册「管脚功能描述」表；9 = 背面散热片 PAD）
PINS = [
    "TEMP",   # 1
    "ISET",   # 2
    "GND",    # 3
    "VIN",    # 4
    "BAT",    # 5
    "DONE",   # 6
    "CHRG",   # 7
    "FB",     # 8
    "EPAD",   # 9 = PAD（散热片，需接 GND；不进任何 <bus>，见 AGENTS §5）
]
BOT = [0, 1, 2, 3]        # 左列 connector：pin1..4（上→下）
TOP = [7, 6, 5, 4]        # 右列 connector：pin8,7,6,5（上→下）
EPAD_CN = 8               # 9 脚（底边单独一个）

ICON_LABEL = "CN3165"
SCHEM_LABEL = "CN3165"
TITLE = "CN3165 Li-Ion Charger (DFN-8)"
LABEL = "U"
PACKAGE = "DFN-8"
FAMILY = "Consonance Charger"

BODY = 3.0                 # 本体见方（mm，手册 D=E 2.9~3.1）
PIN_PITCH = 0.5            # 脚距（手册 e = 0.500 TYP）
PIN_W = 0.25               # 引脚宽（手册 b 0.18~0.30 取中）
PIN_OUT = 0.5              # 图标上引脚伸出本体的视觉长度（手册 L 0.3~0.5）

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- CN3165 DFN-8 -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pin_x(i):
    """左/右列第 i 个（i=0..3，上→下）的 x 坐标：pitch 0.5，居中"""
    return -(len(BOT) - 1) * PIN_PITCH / 2 + i * PIN_PITCH      # -0.75 .. 0.75


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """矩形封装符号：左列 pin1-4 上→下、右列 pin8-5 上→下，**9 脚（EPAD/PAD）在底边中央**
    （AGENTS §5 矩形规则；散热片单独画下方，符合「裸露焊盘独立成网」的表达）。
    名/数字/引线同色黑、整图同字号 FN=35；四角无引脚区 CORNER=(最长名+1)×int(FN×0.58)。
    物理尺寸 width/height(in)，1000 单位 = 1in。"""
    P = 100
    WIRE = 130
    CH = 35
    FN = 35
    BASELINE_OFF = round(FN * 0.35)
    max_len = max(len(n) for n in PINS)        # 4（TEMP/ISET/CHRG/DONE/EPAD）
    CORNER = (max_len + 1) * int(FN * 0.58)    # 5×20 = 100
    BX0, BY0 = 340, 200
    BW = 720
    BH = 4 * P + 2 * CORNER                    # 600
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - WIRE - 5   # 上/左留引线；下方还要给 EPAD 引脚
    VBW = BW + 2 * WIRE + 10
    VBH = BH + 2 * WIRE + 10
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{VBW / 1000:.6f}in" height="{VBH / 1000:.6f}in" '
             f'viewBox="{VBX} {VBY} {VBW} {VBH}">\n')
    L.append(' <g id="schematic">\n')
    L.append(f'  <rect class="interior rect" x="{BX0}" y="{BY0}" width="{BW}" height="{BH}" '
             f'fill="#FFFFFF" stroke="#787878" stroke-width="5"/>\n')

    def side(cn, y, left):
        px0 = BX0 if left else BX1
        px1 = px0 - WIRE if left else px0 + WIRE
        anchor = "start" if left else "end"
        tx = BX0 + CH if left else BX1 - CH
        L.append(f'  <line class="pin" id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'x1="{px0}" y1="{y}" x2="{px1}" y2="{y}" stroke="#000000" stroke-width="5"/>\n')
        L.append(f'  <rect id="connector{cn}terminal" x="{min(px0, px1)}" y="{y - 11}" width="{WIRE}" height="22" fill="none"/>\n')
        L.append(f'  <text x="{(px0 + px1) // 2}" y="{y - 24}" font-size="{FN}" fill="#000000" text-anchor="middle" '
                 f'font-family="DroidSans">{cn + 1}</text>\n')
        L.append(f'  <text x="{tx}" y="{y + BASELINE_OFF}" font-size="{FN}" fill="#000000" text-anchor="{anchor}" '
                 f'font-family="DroidSans">{esc(PINS[cn])}</text>\n')

    for i, cn in enumerate(BOT):
        side(cn, BY0 + CORNER + P // 2 + i * P, True)
    for i, cn in enumerate(TOP):
        side(cn, BY0 + CORNER + P // 2 + i * P, False)
    # 9 脚（散热片）：底边中央，引脚线向下；数字在引脚左侧（rotate 270）；名在框内、底边上方一个字符
    y = BY1
    L.append(f'  <line class="pin" id="connector{EPAD_CN}pin" connectorname="EPAD" '
             f'x1="{BX0 + BW // 2}" y1="{y}" x2="{BX0 + BW // 2}" y2="{y + WIRE}" stroke="#000000" stroke-width="5"/>\n')
    L.append(f'  <rect id="connector{EPAD_CN}terminal" x="{BX0 + BW // 2 - 11}" y="{y + WIRE}" width="22" height="22" fill="none"/>\n')
    L.append(f'  <text x="{BX0 + BW // 2 - 24}" y="{y + WIRE // 2}" font-size="{FN}" fill="#000000" '
             f'text-anchor="middle" font-family="DroidSans" '
             f'transform="rotate(270 {BX0 + BW // 2 - 24} {y + WIRE // 2})">9</text>\n')
    L.append(f'  <text x="{BX0 + BW // 2}" y="{BY1 - CH}" font-size="{FN}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">EPAD</text>\n')
    CHIP_FS = 79
    CHIP_Y = BY0 + BH // 2 - round(CHIP_FS * 0.6)
    L.append(f'  <text x="{BX0 + BW // 2}" y="{CHIP_Y}" font-size="{CHIP_FS}" fill="#000000" text-anchor="middle" '
             f'font-family="DroidSans">{esc(SCHEM_LABEL)}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def _embed_icon(art, cx, cy, s=1.0, icx=0.0, icy=0.0):
    """把 icon 的 <g id="icon"> 重画到面包板坐标系"""
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
        out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["width"]) * s, float(a["height"]) * s,
            a.get("fill", "#303030"), a.get("stroke", "none")))
    for cm in re.finditer(r'<circle\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        px = (float(a["cx"]) + tx - icx) * s + cx
        py = (float(a["cy"]) + ty - icy) * s + cy
        out.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["r"]) * s, a.get("fill", "#c0c0c0"), a.get("stroke", "none")))
    for tm2 in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', content, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tm2.group(1)))
        px = (float(a.get("x", 0.0)) + tx - icx) * s + cx
        py = (float(a.get("y", 0.0)) + ty - icy) * s + cy
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans">%s</text>\n'
                   % (px, py, fs, a.get("fill", "#333333"), tm2.group(2)))
    return "".join(out)


def gen_breadboard_svg():
    """面包板 = 绿色 DFN-8 转接板（AGENTS §3b）：上排 4 个 + 下排 5 个 2.54mm 排针，
    9 脚（EPAD）**插在下排正中间**（= 板中线 x=300），芯片居中。

    板为什么是 600 宽（15.24mm）：用户 2026-09-17 要求“9 脚居中”，而焊盘必须落在
    2.54mm 网格上 → **板中线本身得落在网格上**（板宽要为 2 格 = 5.08mm 的整数倍）。
    板宽 500 时中线在 x=250（半格），EPAD 无论放 200 还是 300 都只能“偏半格”，
    而且会撞上芯片（DFN-8 图标 4mm 高）或引脚数字 —— 所以取 600，把 EPAD 摆在下排中间。
    排针：上排 pin5..8 在 x=100/200/300/400、下排（左→右）= pin1/2/**9(EPAD)**/3/4
    在 x=100..500，两排 y=100/500。
    """
    U = 39.37
    x_top = [100 + i * 100 for i in range(4)]           # 上排 4 个
    x_bot = [100 + i * 100 for i in range(5)]           # 下排 5 个（中间那个是 EPAD）
    bot_seq = [BOT[0], BOT[1], EPAD_CN, BOT[2], BOT[3]]  # TEMP/ISET/EPAD/GND/VIN
    y_top, y_bot = 100, 500
    cx, cy = 300, 300
    pad_r = 1.0 * U
    hole_r = 0.485 * U
    icon = gen_icon_svg()
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    art = _m.group(1) if _m else ""
    _vm = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', icon)
    icx = icy = 0.0
    if _vm:
        vx, vy, vw, vh = map(float, _vm.groups())
        icx, icy = vx + vw / 2, vy + vh / 2
    bw, bh = 600, 600
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" height="{bh / 100 * 2.54:.2f}mm" '
             f'viewBox="0 0 {bw} {bh}">\n')
    s.append(' <g id="breadboard">\n')
    s.append(f'  <rect x="0" y="0" width="{bw}" height="{bh}" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    s.append(_embed_icon(art, cx, cy, s=U, icx=icx, icy=icy))

    def pad(cn, x, y):
        s.append(f'  <circle id="connector{cn}pin" connectorname="{esc(PINS[cn])}" '
                 f'cx="{x:.1f}" cy="{y:.1f}" r="{pad_r:.1f}" '
                 f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        s.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')

    def num(cn, x, y):
        s.append(f'  <text x="{x:.1f}" y="{y}" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x:.1f} {y})">{cn + 1}</text>\n')

    for cn, x in zip(TOP, x_top):
        pad(cn, x, y_top)
        num(cn, x, 176)
    for cn, x in zip(bot_seq, x_bot):
        pad(cn, x, y_bot)
        num(cn, x, 424)
    s.append(' </g>\n</svg>\n')
    return "".join(s)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图（DFN-8 3×3，真实封装）。

    尺寸来源与推导（手册第 12 页「封装信息」DFN-8 机械图 + 常规外扩）：
      · 本体 D = E = 3.0mm（2.9~3.1）、脚距 e = 0.500 TYP、脚宽 b = 0.25（0.18~0.30）、
        脚长 L = 0.4（0.300~0.500）、散热盘 D1×E1 = 2.4×1.7（2.3~2.5 × 1.6~1.8）
      · 引脚端点 = 本体/2 + L = 1.5 + 0.4 = 1.9；
      ⚠ 以上是**推导**值。**2026-09-17 已按嘉立创/立创EDA 实际封装对齐**（用户提供
        `D:\\Downloads\\DFN-8-L3.0-W3.0-P0.50-BL-EP_2026-09-17.svg`）：用实测值
        焊盘 **0.280×0.665**、焊盘中心 **±1.407**（跳距 2.814）、散热盘 **2.45×1.65**。
        （立创把焊盘中心放在引脚中点附近，而不是 IPC 那种“中心=引脚端点”，
        所以推导的 row=1.70 偏大；两者都能焊，但用户板上的封装是嘉立创的，以它为准。）
    丝印：本体四角 L 形角标（避开焊盘）+ pin1 实心圆点（本体左下角内）。
    """
    pw, pl = 0.28, 0.665     # 引脚焊盘：宽(x) × 长(y) —— 嘉立创实测
    pitch = 0.5              # 脚距（手册 + 嘉立创）
    row = 1.407              # 上下排焊盘中心 y = ±1.407 → 跳距 2.814mm（嘉立创实测）
    ep_w, ep_h = 2.45, 1.65  # 散热盘焊盘（嘉立创实测，与芯片 D1/E1 = 2.4×1.7 基本一致）
    pads = []
    for i, cn in enumerate(BOT):        # 下排 pin1-4（y=+row）
        x = pin_x(i)
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    for i, cn in enumerate(TOP):        # 上排 pin8-5（y=-row）
        x = pin_x(i)
        pads.append(f'<rect id="connector{cn}pad" x="{x - pw / 2:.3f}" y="{-row - pl / 2:.3f}" '
                    f'width="{pw:.3f}" height="{pl:.3f}" fill="#F7BD13" stroke="none" '
                    f'connectorname="{esc(PINS[cn])}"/>')
    # 9 脚：底部散热盘焊盘（单独成网）
    pads.append(f'<rect id="connector{EPAD_CN}pad" x="{-ep_w / 2:.3f}" y="{-ep_h / 2:.3f}" '
                f'width="{ep_w:.3f}" height="{ep_h:.3f}" fill="#F7BD13" stroke="none" '
                f'connectorname="EPAD"/>')
    silk = []
    # 本体四角 L 形角标（本体边 ±1.5，段长 0.45；不压任何焊盘）
    K, SEG = 1.5, 0.45
    for sx in (-1, 1):
        for sy in (-1, 1):
            silk.append(f'<line x1="{sx * K:.3f}" y1="{sy * (K - SEG):.3f}" x2="{sx * K:.3f}" y2="{sy * K:.3f}" '
                        f'stroke="#f0f0f0" stroke-width="0.12"/>')
            silk.append(f'<line x1="{sx * (K - SEG):.3f}" y1="{sy * K:.3f}" x2="{sx * K:.3f}" y2="{sy * K:.3f}" '
                        f'stroke="#f0f0f0" stroke-width="0.12"/>')
    # pin1 实心圆点（本体左下角内）
    silk.append('<circle cx="-1.15" cy="1.15" r="0.16" fill="#f0f0f0" stroke="none"/>')
    inner = ("\n".join(pads) + "\n  </g>\n  <g id=\"silkscreen\">\n" + "\n".join(silk))
    M = 0.15
    vb_x0, vb_x1 = -(row + pl / 2) - M, (row + pl / 2) + M
    vb_y0, vb_y1 = vb_x0, vb_x1
    vw = vh = vb_x1 - vb_x0
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
            f'viewBox="{vb_x0:.2f} {vb_y0:.2f} {vw:.2f} {vh:.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """DFN-8 图标：本体 3.0×3.0mm，上下各 4 银脚（宽 0.25、距 0.5、各伸 0.5mm → 总高 4.0mm），
    pin1 圆点在本体左下，丝印 CN3165。底部散热盘在俯视图看不到，故不画。"""
    half = BODY / 2.0                                  # 1.5
    parts = [SVG_HDR,
             f'<svg xmlns="http://www.w3.org/2000/svg" width="{BODY + 1:.1f}mm" height="{BODY + 1:.1f}mm" '
             f'viewBox="{-half - 0.5:.2f} {-half - 0.5:.2f} {BODY + 1:.1f} {BODY + 1:.1f}">\n'
             '  <g id="icon">\n']
    for i in range(4):
        x = pin_x(i) - PIN_W / 2.0
        parts.append(f'    <rect x="{x:.3f}" y="{-half - PIN_OUT:.2f}" width="{PIN_W:.2f}" height="{PIN_OUT:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')          # 上排
        parts.append(f'    <rect x="{x:.3f}" y="{half:.2f}" width="{PIN_W:.2f}" height="{PIN_OUT:.2f}" '
                     f'fill="#c0c0c0" stroke="none"/>\n')          # 下排
    parts.append(f'    <rect x="{-half:.2f}" y="{-half:.2f}" width="{BODY:.1f}" height="{BODY:.1f}" '
                 f'fill="#303030" stroke="none"/>\n')
    parts.append('    <circle cx="-1.15" cy="1.15" r="0.16" fill="#c0c0c0" stroke="none"/>\n')
    parts.append('    <text x="0" y="0.38" font-size="0.72" fill="#ffffff" text-anchor="middle" '
                 'font-family="DroidSans">CN3165</text>\n')
    parts.append('  </g>\n</svg>\n')
    return "".join(parts)


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for i, name in enumerate(PINS):
        desc = name
        if name == "EPAD":
            desc = "EPAD (exposed thermal pad) - route to GND"
        conns.append(
            f'  <connector id="connector{i}" name="{esc(name)}" type="male">\n'
            f'   <description>{esc(desc)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{i}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{i}pin" terminalId="connector{i}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{i}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>1</version>\n <date>2026-09-17</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>CN3165</tag>\n  <tag>DFN-8</tag>\n'
            f'  <tag>charger</tag>\n  <tag>Li-Ion</tag>\n  <tag>Consonance</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">{len(PINS)}</property>\n </properties>\n'
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
