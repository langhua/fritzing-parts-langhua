#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — CH347T 高速 USB 转 SPI/I2C/JTAG/UART 芯片（WCH）Fritzing 元件生成器。
================================================================================
元件形态（用户 2026-09-14 定）：
  - **芯片**（CH347T）出 icon / 原理图 / PCB 三个视图；
  - **面板上用的那块官方评估板 CH347T-EVT-R0-1v1** 只出现在**面包板视图**，
    板上排针**全部做成可连线 connector**（按信号名映射到芯片脚；同网用 <buses> 互联）。

资料（都在本机，不是猜的）：
  · `D:\Downloads\CH347DS1.PDF`（CH347 手册 V1.5）：
      - 封装：**TSSOP20，塑体 4.4×6.5mm，引脚节距 0.65mm**；CH347F = QFN28 4×4mm / 0.4mm；
      - 第 3 页引脚排列图（TOP VIEW，本脚本 PIN_NAMES 的来源）：
          左侧 上→下 = 1..10；右侧 下→上 = 11..20；
          1 RST# | 2 CTS1/GPIO6 | 3 TXD1 | 4 RXD1 | 5 DSR0/GPIO2/SCS0/TMS |
          6 CTS0/GPIO0/SCK/TCK | 7 RTS0/GPIO1/MISO/TDO | 8 TXD0/MOSI/TDI |
          9 TNOW0/DTR0/GPIO5/SCS1/TRST | 10 TNOW1/DTR1 |
          11 RI0/GPIO3/SCL | 12 RXD0/SDA | 13 RTS1/GPIO7 | 14 VCC | 15 DCD0/GPIO4/ACT |
          16 UD- | 17 UD+ | 18 GND | 19 XI | 20 XO
      - CH347T 靠 **CFG0/CFG1 引脚上电时的电平** 选工作模式：
          0 = 双 UART；1 = 单 UART(VCP)+SPI+I2C；2 = 单 UART(HID)+SPI+I2C；3 = 单 UART+JTAG/SWD
  · `D:\Downloads\CH347EVT\EVT\PUB\CH347EVT_EN.pdf`（评估板说明 V1.5）：
      第 2/3/5 页的板级单元表 + 第 3/4 页的 **P9–P14 功能脚配置表**；第 2 页有实物照片。
  · `D:\Downloads\CH347EVT\EVT\PCB\CH347SCH.pdf` 第 2 页：CH347T 评估板原理图（网名来源）。

面包板视图的几何**不在这里**（与 svg/CH347F 一样分成三个文件）：
  ① 用户在 Inkscape 里拿实物照片当底手工对齐 → `svg.breadboard.CH347T_breadboard_byHand.svg`
     （带照片的草稿，已在 .gitignore 里）；
  ② `tools/byhand_export.py svg\CH347T` → **`byHand_tables.py`**（纯数据，入库）；
  ③ 本文件只负责**照着表出图**。以后挪排针 = 改手工版重跑 ②，不要在本文件里改坐标。

进度（按 fritzing-parts-langhua AGENTS.md §2 芯片类工作流）：
  [x] 1. icon（TSSOP20 顶视图：黑体 4.4×6.5 + 两侧金脚 + pin1 圆点）
  [x] 2. breadboard（= CH347T-EVT-R0-1v1 整块评估板）
  [ ] 3. schematic（矩形 20 脚符号）
  [ ] 4. pcb（TSSOP20 4.4×6.5 P0.65）
  [ ] 5. part.CH347T.fzp + 打包 fzpz
"""
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH347T"
TITLE = "CH347T (USB to SPI/I2C/JTAG/UART, TSSOP20)"
LABEL = "U"
PACKAGE = "TSSOP20"
FAMILY = "WCH USB Bridge"
FZPZ = "CH347T.fzpz"
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID

# 颜色（与仓库其它芯片 icon 一致）
BODY = "#303030"
PAD = "#f7bf13"
MARK = "#c0c0c0"
TXT = "#c0c0c0"

# ---- icon 几何（mm，1:1 实物）------------------------------------------------
BODY_W = 4.4          # 塑体宽（引脚在左右两侧伸出）
BODY_H = 6.5          # 塑体高
LEAD_L = 1.0          # 引脚伸出长度（用户 2026-09-14：0.25 x 1mm）
LEAD_W = 0.25         # 引脚宽
PITCH = 0.65          # 节距
N_PER_SIDE = 10       # 每侧 10 脚
TOT_W = BODY_W + 2 * LEAD_L
TOT_H = BODY_H

# 引脚名（datasheet 第 3 页排列图）—— **面包板的网名/connector 号也按它算**（见 pad_map）
PIN_NAMES = {
    1: "RST#", 2: "CTS1/GPIO6", 3: "TXD1", 4: "RXD1", 5: "DSR0/GPIO2/SCS0/TMS",
    6: "CTS0/GPIO0/SCK/TCK", 7: "RTS0/GPIO1/MISO/TDO", 8: "TXD0/MOSI/TDI",
    9: "TNOW0/DTR0/GPIO5/SCS1/TRST", 10: "TNOW1/DTR1",
    11: "RI0/GPIO3/SCL", 12: "RXD0/SDA", 13: "RTS1/GPIO7", 14: "VCC",
    15: "DCD0/GPIO4/ACT", 16: "UD-", 17: "UD+", 18: "GND", 19: "XI", 20: "XO",
}

# 板上额外网络：**没有对应芯片脚号**（CFG0/CFG1 是模式脚，CH347 手册第 3 页的 20 脚表里
# 没有单列；GND/KEY 是按键扫描线，不是地）→ 一律发板级号，且**不许按 "/" 拆开去猜**
# （拆开 "GND/KEY" 会拆出 "GND" 而误并到地上 —— CH347F 上踩过的同类坑）。
BOARD_NETS = {"CFG0", "CFG1", "GND/KEY"}


def _centers():
    """每侧 10 个引脚中心（沿边方向，从上到下），对称于本体中心。"""
    c0 = TOT_H / 2.0 - (N_PER_SIDE - 1) * PITCH / 2.0
    return [c0 + i * PITCH for i in range(N_PER_SIDE)]


def icon_svg():
    """TSSOP20 顶视图 icon：黑体 4.4×6.5 + 左右各 10 金脚 + pin1 圆点 + 丝印名。"""
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.1fmm" '
             'viewBox="0 0 %.2f %.1f">\n' % (TOT_W, TOT_H, TOT_W, TOT_H))
    L.append('  <g id="icon">\n')
    for c in _centers():
        L.append('    <rect x="0" y="%.3f" width="%.2f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (c - LEAD_W / 2, LEAD_L, LEAD_W, PAD))                       # 左
        L.append('    <rect x="%.2f" y="%.3f" width="%.2f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (LEAD_L + BODY_W, c - LEAD_W / 2, LEAD_L, LEAD_W, PAD))      # 右
    L.append('    <rect x="%.2f" y="0" width="%.2f" height="%.1f" '
             'fill="%s" stroke="none"/>\n' % (LEAD_L, BODY_W, BODY_H, BODY))
    L.append('    <circle cx="%.2f" cy="%.2f" r="0.18" fill="%s" stroke="none"/>\n'
             % (LEAD_L + 0.45, _centers()[0] + 0.45, MARK))                     # pin1 圆点
    cx = TOT_W / 2.0
    L.append('    <text x="%.2f" y="%.2f" font-size="0.62" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">CH347T</text>\n' % (cx, TOT_H / 2 - 0.15, TXT))
    L.append('    <text x="%.2f" y="%.2f" font-size="0.34" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">TSSOP20</text>\n' % (cx, TOT_H / 2 + 0.62, TXT))
    L.append('  </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# =============================================================================
# 面包板视图 —— CH347T-EVT-R0-1v1 评估板
#
# 几何**全部来自 byHand_tables.py**（用户手工对齐 → tools/byhand_export.py 导出）。
# 本文件只负责照表出图；换位置请改手工版重跑导出，**不要在这里改坐标**。
#
# 坐标口径（沿用 AGENTS §5 与 CH347F）：内部单位 100 = 2.54mm；输出时 ×S 换成 viewBox 单位。
# 板尺寸：用户 2026-09-15 卡尺实测 50.1 × 61.2 mm（含边）。
# =============================================================================
S = 0.072                                # 内部单位（100 = 2.54mm）→ viewBox 单位
MM_U = 39.37 * S                         # 1mm → viewBox 单位

BOARD_MM = (50.1, 61.2)                  # 卡尺实测（含边）
BOARD_W, BOARD_H = BOARD_MM[0] * MM_U, BOARD_MM[1] * MM_U
BOARD_RX = 1.5 * MM_U                    # 板框圆角半径（1.5mm，量自实物照片）
BOARD_SW = 0.35 * MM_U                   # 板框描边（mm）
PCB_BLUE = "#002d68"
PCB_EDGE = "#001745"
PIN_FILL = "#d0d0d0"
PIN_EDGE = "#8a8a8a"

from byHand_tables import (PAD_R, PAD_SW, PADS, ICONS, TEXTS,         # noqa: E402
                           EXTRA_RECTS, EXTRA_CIRCLES, EXTRA_LINES)


def pad_map():
    """[(原 id, 网名, x, y, connector 号)]：0..19 = 芯片脚 pin1..20，20+ = 面包板专用。

    分配顺序（可复现，与 CH347F / CH32V203C8T6 / SMA 同一套规矩）：
      ① 网名**与芯片脚主名一致**的焊盘优先拿该脚号（如 CTS1/GPIO6 拿 2、VCC 拿 14）；
      ② 其余焊盘按 上→下、左→右：能对上一个还没被占的芯片脚就拿脚号，否则发板级号；
      ③ 地的脚号（18 GND）发给最先遇到的 GND 焊盘，剩下的 GND 发板级号；
      ④ `BOARD_NETS` 里的网络一律板级号。
    每个焊盘**各自是一个 connector**（都能接线），同网再用 .fzp 的 <buses> 互联。
    """
    pin_of = {}
    for n, nm in PIN_NAMES.items():
        pin_of[nm] = n - 1                    # 全名（如 "DSR0/GPIO2/SCS0/TMS"）
        for a in nm.split("/"):
            pin_of.setdefault(a, n - 1)       # 别名（如 "SCS0"、"TMS"）
    rows = [[cid, nm, x, y, None] for cid, nm, x, y in sorted(PADS, key=lambda p: (p[3], p[2]))]
    used, rail = {}, [20]
    for row in rows:                                   # ① 主名优先
        pin = None if row[1] in BOARD_NETS else pin_of.get(row[1])
        if pin is None or pin in used or row[1] == "GND":
            continue
        if row[1] == PIN_NAMES[pin + 1].split("/")[0]:
            used[pin], row[4] = pin, pin
    for row in rows:                                   # ② 其余（地除外）
        if row[4] is not None or row[1] == "GND":
            continue
        pin = None if row[1] in BOARD_NETS else pin_of.get(row[1])
        if pin is not None and pin not in used:
            used[pin], row[4] = pin, pin
        else:
            row[4] = rail[0]
            rail[0] += 1
    for row in [r for r in rows if r[4] is None]:      # ③ 地
        pin = 18 - 1                                   # 18 = GND
        if pin not in used:
            used[pin], row[4] = pin, pin
        else:
            row[4] = rail[0]
            rail[0] += 1
    return [tuple(r) for r in rows]


def buses():
    """→ [(总线名, [connector 号…])]：同网必并一条总线（AGENTS §5「多焊盘同网络」条）。"""
    grp = {}
    for _cid, net, _x, _y, cn in pad_map():
        grp.setdefault(net, []).append(cn)
    return [(net if net != "VCC" else "3V3", sorted(cns)) for net, cns in sorted(grp.items())]


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _bake_icon(part_id, cx, cy, rot=0):
    """把 `../<part_id>/svg.icon.<part_id>_icon.svg` 的 `<g id="icon">` 按 1:1 真实尺寸
    **烘成绝对坐标**嵌入（cx, cy 为内部单位，图标 viewBox 中心对准它，再绕中心转 rot 度）。

    为什么烘（AGENTS §5）：嵌套 transform 在 Inkscape / Fritzing / VS Code 预览里解释不一致
    （会出现"芯片缩小到看不见"）；烘成绝对值就与别的元件一致。rect/circle 全烘成绝对坐标，
    只有**文字**保留 rotate()（Fritzing 官方也这么写）。
    （本元件的手工版里器件是"烘进去的矩形"，所以 ICONS 现在是空的；表里出现图标时会走这里。）
    """
    import re
    path = os.path.join(OUT_DIR, "..", part_id, "svg.icon.%s_icon.svg" % part_id)
    art = open(path, encoding="utf-8").read()
    m = re.search(r'viewBox="([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+)"', art)
    b = re.search(r'<g\s+id="icon">(.*)</g>', art, re.S)
    if not m or not b:
        raise RuntimeError("图标几何读不到（%s）：需要 viewBox + <g id=\"icon\">" % path)
    x0, y0, w, h = (float(v) for v in m.groups())
    ccx, ccy = x0 + w / 2.0, y0 + h / 2.0
    cx, cy = cx * S, cy * S
    ca, sa = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1), -90: (0, -1)}[rot]

    def mp(px, py):
        dx, dy = (px - ccx) * MM_U, (py - ccy) * MM_U
        return (cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)

    out = []
    for rm in re.finditer(r'<rect\s+([^>]*?)/>', b.group(1)):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', rm.group(1)))
        rx, ry = float(a["x"]), float(a["y"])
        rw, rh = float(a["width"]), float(a["height"])
        ps = [mp(rx, ry), mp(rx + rw, ry), mp(rx, ry + rh), mp(rx + rw, ry + rh)]
        xs = [p[0] for p in ps]
        ys = [p[1] for p in ps]
        attrs = ' fill="%s"' % a.get("fill", "none")
        if a.get("stroke") and a["stroke"] != "none":
            attrs += ' stroke="%s" stroke-width="%.3f"' % (
                a["stroke"], float(a.get("stroke-width", 0)) * MM_U)
        out.append('  <rect x="%.3f" y="%.3f" width="%.3f" height="%.3f"%s/>\n'
                   % (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys), attrs))
    for cm in re.finditer(r'<circle\s+([^>]*?)/>', b.group(1)):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        p = mp(float(a["cx"]), float(a["cy"]))
        out.append('  <circle cx="%.3f" cy="%.3f" r="%.3f" fill="%s" stroke="none"/>\n'
                   % (p[0], p[1], float(a["r"]) * MM_U, a.get("fill", "none")))
    for tm in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', b.group(1), re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tm.group(1)))
        p = mp(float(a.get("x", 0)), float(a.get("y", 0)))
        t = ('  <text x="%.3f" y="%.3f" font-size="%.3f" font-family="DroidSans" fill="%s"'
             % (p[0], p[1], float(a.get("font-size", 1)) * MM_U, a.get("fill", "#c0c0c0")))
        if a.get("text-anchor"):
            t += ' text-anchor="%s"' % a["text-anchor"]
        if rot:
            t += ' transform="rotate(%.1f,%.3f,%.3f)"' % (rot, p[0], p[1])
        out.append(t + '>%s</text>\n' % tm.group(2).strip())
    other = set(re.findall(r'<(\w+)', b.group(1))) - {"rect", "circle", "text"}
    if other:
        raise RuntimeError("%s 的 icon 里有本函数不支持的图元：%s" % (part_id, sorted(other)))
    return "".join(out)


def gen_breadboard_svg():
    """CH347T-EVT-R0-1v1 面包板视图（几何来自 byHand_tables.py；**零嵌套变换**）。

    板框在**这里**画（手工版那块 #002d68 的矩形被 byHand_export 的 SKIP_RECT_FILL 丢掉了，
    免得直角框盖掉圆角）；USB 座等其它图形由 EXTRA_RECTS/CIRCLES 带过来。
    """
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %.1f %.1f">\n'
         % (BOARD_MM[0], BOARD_MM[1], BOARD_W, BOARD_H),
         ' <g id="breadboard">\n',
         '  <rect id="board" x="0" y="0" width="%.1f" height="%.1f" rx="%.2f" ry="%.2f" '
         'fill="%s" stroke="%s" stroke-width="%.2f"/>\n'
         % (BOARD_W, BOARD_H, BOARD_RX, BOARD_RX, PCB_BLUE, PCB_EDGE, BOARD_SW)]
    # 其它矩形（排针塑料座 / 两脚件 / 器件烘出来的形状）—— 表里已是**旋转后的外接框**
    for x, y, w, h, fill, rot, stroke, sw in EXTRA_RECTS:
        a = ' fill="%s"' % fill if fill and fill != "None" else ' fill="none"'
        if stroke and stroke != "None":
            a += ' stroke="%s"' % stroke
            if sw and sw != "None":
                a += ' stroke-width="%.3f"' % (float(sw) * S)
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"%s/>\n'
                 % (x * S, y * S, w * S, h * S, a))
    for x1, y1, x2, y2, stroke, sw in EXTRA_LINES:
        w = (float(sw) if sw else 1.0)
        L.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                 'stroke-width="%.2f"/>\n' % (x1 * S, y1 * S, x2 * S, y2 * S, stroke, w * S))
    # 板上器件（手工版里若做成"带缩放的组"，byhand_export 会认出来放进 ICONS）
    for part, x, y, rot in ICONS:
        L.append(_bake_icon(part, x, y, rot))
    # 排针脚（id 由 pad_map() 定的**最终 connector 号** → 与 .fzp / 原理图同一套号）
    for _cid, net, x, y, cn in pad_map():
        L.append('  <circle id="connector%dpin" connectorname="%s" cx="%.2f" cy="%.2f" '
                 'r="%.2f" fill="%s" stroke="%s" stroke-width="%.2f"/>\n'
                 % (cn, _esc(net), x * S, y * S, PAD_R * S, PIN_FILL, PIN_EDGE, PAD_SW * S))
    # ★ 叠放次序照**手工版**来：矩形（排针塑料座等）在下，焊盘居中，**circle 表在最上**
    #   —— 手工版里那几圈"同心圆焊盘"是后来加的、盖在焊盘上；先画圆圈会把它们埋掉
    #   （实测：顺序反了会让 P14/P2 那几颗针看着与手工版不一样）。
    for x, y, r, fill, stroke, sw in EXTRA_CIRCLES:
        a = ' fill="%s"' % (fill if fill and fill != "None" else "none")
        if stroke and stroke != "None":
            a += ' stroke="%s"' % stroke
            if sw and sw != "None":
                a += ' stroke-width="%.3f"' % (float(sw) * S)
        L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f"%s/>\n' % (x * S, y * S, r * S, a))
    # 丝印（只有带旋转的才带 transform）
    for txt, x, y, fs, anchor, rot, fill, fw in TEXTS:
        a = ' fill="%s"' % (fill if fill and fill != "None" else "#ffffff")
        if anchor and anchor != "None":
            a += ' text-anchor="%s"' % anchor
        if fw:
            a += ' font-weight="%s"' % fw
        if rot:
            a += ' transform="rotate(%.1f,%.2f,%.2f)"' % (rot, x * S, y * S)
        L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-family="DroidSans"%s>%s'
                 '</text>\n' % (x * S, y * S, fs * S, a, _esc(txt)))
    L += [' </g>\n', '</svg>\n']
    return "".join(L)


def main():
    files = {ICON_SVG: icon_svg(), BB_SVG: gen_breadboard_svg()}
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)


if __name__ == "__main__":
    main()
