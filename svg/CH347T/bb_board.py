#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
bb_board.py — CH347T 面包板视图（= 官方评估板 **CH347T-EVT-R0-1v1** 整块板）的几何表 + 出图。
被 `gen_part.py` import（面包板视图专用），不单独运行。

为什么要单开一个文件：和 `svg/CH347F/` 一样，**几何表与出图代码分家** ——
CH347F 的表是 Inkscape 手工对齐后由 `tools/byhand_export.py` 自动生成的；
这里的表是**从官方 PDF 里的实物照片自动标定**出来的（见 `trace_photo.py`），
所以文件头把"数是从哪来的"写清楚，免得以后不知道能不能改。

坐标口径（沿用 AGENTS §5 与 CH347F 的做法）：
  · 排针节距一律 **2.54mm**；本文件里的坐标**全部用 mm**，出图时 ×MM_U 换成 viewBox 单位；
  · `S=0.072`、`MM_U=39.37*S` 与 `svg/CH347F/gen_part.py` 完全一致；
  · **零嵌套 transform**（只有文字保留 rotate()），理由见 AGENTS §5。

数据来源（都是本机资料，不是猜的）：
  · 板尺寸 50.1 × 61.2 mm = 用户 2026-09-15 卡尺实测（含边）；
  · 排针的**位置与根数**：`trace_photo.py` 把 CH347EVT_EN.pdf 第 2 页的实物照片按
    12.4 px/mm 标定后，量**黑色塑料座**的外接框，长边按 2.54mm 栅格反推根数（±0.3mm）；
  · 排针的**网名**：`CH347SCH.pdf` 第 2 页（CH347T 原理图）+ CH347EVT_EN.pdf 第 3/4 页的
    **P9–P14 功能脚配置表**；丝印按实物照片的写法（如印 "RXD" 而非 "RXD0"）。

★ 第 1 版**未做**（如实记录，别当成已完成）：
  · R1–R8 / C1–C10 / F1 等小件及其位号；过孔与铜箔走线；板上红色箭头等图形。
  · 排针丝印名有两处**需要人眼复核**：① P5（JTAG）左右两列到底是 5 行还是 6 行；
    ② 中间 P9–P14 从左到右的块名顺序（照片 OCR 给的是 P14 P13 P12 P10 P11 P9）。
"""

S = 0.072                                # 内部单位（100 = 2.54mm）→ viewBox 单位
MM_U = 39.37 * S                         # 1mm → viewBox 单位
PITCH_MM = 2.54                          # 排针节距

BOARD_MM = (50.1, 61.2)                  # 卡尺实测（含边）
BOARD_R = 1.5                            # 板框圆角半径（mm）
BOARD_SW = 0.35                          # 板框描边（mm）

PCB_BLUE = "#002d68"
PCB_EDGE = "#001745"
PIN_FILL = "#d0d0d0"                     # 焊盘填充（与 CH347F 同）
PIN_EDGE = "#8a8a8a"
PIN_R = 0.85                             # 焊盘半径（mm）
PIN_SW = 0.30
HDR_BODY = "#4d7fe0"                     # 排针塑料座（与 CH347F 手工版同色）
HDR_HALF_W = 1.25                        # 塑料座半宽（mm）
HDR_END = 1.30                           # 塑料座比端针多出的长度（mm）
SILK = "#ffffff"
SILK_D = "#c8ccd0"
FS_SILK = 0.80                           # 脚名丝印字号（mm）
FS_NAME = 0.90                           # 排针块名（P8 这种）
LABEL_GAP = 1.55                         # 标签基线离针中心的水平距离（mm）
BASELINE = 0.33                          # 文字垂直居中补偿（mm）

# 芯片脚名（CH347 手册第 3 页；connector 号 = 脚号-1）
PIN_NAMES = {
    1: "RST#", 2: "CTS1/GPIO6", 3: "TXD1", 4: "RXD1", 5: "DSR0/GPIO2/SCS0/TMS",
    6: "CTS0/GPIO0/SCK/TCK", 7: "RTS0/GPIO1/MISO/TDO", 8: "TXD0/MOSI/TDI",
    9: "TNOW0/DTR0/GPIO5/SCS1/TRST", 10: "TNOW1/DTR1",
    11: "RI0/GPIO3/SCL", 12: "RXD0/SDA", 13: "RTS1/GPIO7", 14: "VCC",
    15: "DCD0/GPIO4/ACT", 16: "UD-", 17: "UD+", 18: "GND", 19: "XI", 20: "XO",
}

# -----------------------------------------------------------------------------
# 排针表：`pins` 自上而下给 (net, silk)
#   net  = 芯片脚名 → 决定 connector 号与 <buses>（见 pad_map()/buses()）
#   silk = 板上印的名字（可以不等于 net，如 RXD / CS0 / CS1）
#   cols = 引脚列的 x（mm）列表（1 列 = 单排；2 列 = 双排）
#   y1   = 第一根针的中心 y（mm）
#   name = 块名（Pn）印在哪头：'top' / 'bottom' / 'none'
# -----------------------------------------------------------------------------
HEADERS = [
    # --- 左上：I2C（P3）+ 模式选择跳线（P2） --------------------------------
    dict(id="P3", cols=[3.42], y1=4.51, side=("left", "right"),
         pins=[("RXD0/SDA", "SDA"), ("RI0/GPIO3/SCL", "SCL"), ("GND", "GND"),
               ("VCC", "3V3")],
         name="bottom"),
    dict(id="P2", cols=[7.08], y1=4.51, side=("right", "right"),
         pins=[("GND", "GND"), ("CFG0", "CFG0"), ("CFG1", "CFG1"), ("GND", "GND")],
         name="bottom"),
    # --- 右上：SPI（P4，7 针） ---------------------------------------------
    dict(id="P4", cols=[44.81], y1=4.12, side=("right", "left"),
         pins=[("VCC", "3V3"), ("GND", "GND"), ("DSR0/GPIO2/SCS0/TMS", "CS0"),
               ("TNOW0/DTR0/GPIO5/SCS1/TRST", "CS1"), ("CTS0/GPIO0/SCK/TCK", "SCK"),
               ("RTS0/GPIO1/MISO/TDO", "MISO"), ("TXD0/MOSI/TDI", "MOSI")],
         name="top"),
    # --- 左侧：TTL UART0（P7，10 针）与 UART1（P8，7 针） -------------------
    #     丝印顺序按**实物照片**（两列都是 3V3、GND 打头；原理图的画法顺序与此相反）
    dict(id="P7", cols=[4.32], y1=19.60, side=("left", "right"),
         pins=[("VCC", "3V3"), ("GND", "GND"), ("RXD0/SDA", "RXD"),
               ("TXD0/MOSI/TDI", "TXD"), ("RTS0/GPIO1/MISO/TDO", "RTS"),
               ("CTS0/GPIO0/SCK/TCK", "CTS"), ("TNOW0/DTR0/GPIO5/SCS1/TRST", "DTR"),
               ("DSR0/GPIO2/SCS0/TMS", "DSR"), ("RI0/GPIO3/SCL", "RI"),
               ("DCD0/GPIO4/ACT", "DCD")],
         name="top"),
    dict(id="P8", cols=[6.86], y1=19.60, side=("right", "right"),
         pins=[("VCC", "3V3"), ("GND", "GND"), ("RXD1", "RXD1"), ("TXD1", "TXD1"),
               ("RTS1/GPIO7", "RTS1"), ("CTS1/GPIO6", "CTS1"),
               ("TNOW1/DTR1", "DTR1")],
         name="top"),
    # --- 中间：P9–P14 功能脚配置区（每块 3 针；丝印只有块名） ---------------
    #     每个块的三根针都并到**同一个芯片脚**的网络上：中针 = 芯片脚，
    #     两头 = 该脚在 UART0 / SPI-I2C 两种用法下要连的去处（靠跳线选）。
    dict(id="P14", cols=[17.18], y1=20.30, side=("none", "none"),
         pins=[("RXD0/SDA", ""), ("RXD0/SDA", ""), ("RXD0/SDA", "")], name="bottom"),
    dict(id="P13", cols=[20.32], y1=20.30, side=("none", "none"),
         pins=[("RI0/GPIO3/SCL", ""), ("RI0/GPIO3/SCL", ""), ("RI0/GPIO3/SCL", "")],
         name="bottom"),
    dict(id="P12", cols=[23.46], y1=20.30, side=("none", "none"),
         pins=[("TXD0/MOSI/TDI", ""), ("TXD0/MOSI/TDI", ""), ("TXD0/MOSI/TDI", "")],
         name="bottom"),
    dict(id="P10", cols=[26.60], y1=20.30, side=("none", "none"),
         pins=[("RTS0/GPIO1/MISO/TDO", ""), ("RTS0/GPIO1/MISO/TDO", ""),
               ("RTS0/GPIO1/MISO/TDO", "")], name="bottom"),
    dict(id="P11", cols=[29.82], y1=20.30, side=("none", "none"),
         pins=[("CTS0/GPIO0/SCK/TCK", ""), ("CTS0/GPIO0/SCK/TCK", ""),
               ("CTS0/GPIO0/SCK/TCK", "")], name="bottom"),
    dict(id="P9", cols=[32.88], y1=20.30, side=("none", "none"),
         pins=[("DSR0/GPIO2/SCS0/TMS", ""), ("DSR0/GPIO2/SCS0/TMS", ""),
               ("DSR0/GPIO2/SCS0/TMS", "")], name="bottom"),
    # --- 右中：JTAG（P5，双排 5 行） ---------------------------------------
    dict(id="P5", cols=[42.55, 45.09], y1=27.12, side=("left", "left"),
         pins_left=[("VCC", "3V3"), ("GND", "GND"), ("GND", "GND"), ("GND", "GND"),
                    ("GND", "GND")],
         pins_right=[("DSR0/GPIO2/SCS0/TMS", "TMS"), ("CTS0/GPIO0/SCK/TCK", "TCK"),
                     ("RTS0/GPIO1/MISO/TDO", "TDO"), ("TXD0/MOSI/TDI", "TDI"),
                     ("TNOW0/DTR0/GPIO5/SCS1/TRST", "TRST")],
         name="top"),
    # --- 右侧小跳线：GND/KEY（与 CH347F 的 P7 同义） -----------------------
    dict(id="P6", cols=[36.90], y1=31.80, side=("right", "left"),
         pins=[("GND/KEY", "GND"), ("GND/KEY", "/KEY")], name="none"),
]

# 板上器件：(部件目录, 中心 x mm, 中心 y mm, 旋转°)；目录下要有 svg.icon.<id>_icon.svg
ICONS = [
    ("AT24C02", 20.00, 8.10, 0.0),        # U3 = 24C02 EEPROM
    ("W25Q16JV", 28.35, 11.90, 0.0),      # U4 = 25Q16 FLASH
    ("CH347T", 25.10, 33.30, 0.0),        # U2 = 主控（本元件自己的 icon）
    ("LD1117", 43.70, 45.20, 180.0),      # U1 = 3.3V 稳压
    ("Crystal-3225", 30.30, 30.40, 0.0),  # X1 = 8MHz 无源晶振
]

# 其它丝印：(文本, x mm, y mm, 字号 mm, anchor, 旋转°, 颜色)
TEXTS_EXTRA = [
    ("CH347T-EVT-R0-1v1", 1.20, 57.60, 1.65, "start", 0, SILK),
    ("http://wch.cn", 2.15, 59.40, 1.65, "start", 0, SILK_D),
    ("BACK", 3.60, 53.20, 0.90, "middle", 0, SILK),
    ("U3", 20.00, 5.60, 0.80, "middle", 0, SILK_D),
    ("U4", 28.35, 7.30, 0.80, "middle", 0, SILK_D),
    ("U2", 25.10, 28.90, 0.80, "middle", 0, SILK_D),
    ("U1", 43.70, 47.60, 0.80, "middle", 0, SILK_D),
    ("X1", 33.10, 30.40, 0.80, "middle", 0, SILK_D),
    ("LED1", 23.60, 44.90, 0.80, "middle", 0, SILK_D),
    ("P1", 42.40, 59.60, 0.90, "middle", 0, SILK_D),
    ("F1 C1 C2 C3 C4", 12.50, 55.10, 0.80, "start", 0, SILK_D),
]

# USB Type-C 母座（板子下缘那只银色座）：(中心 x, 中心 y, 宽, 高)
USB_BODY = (42.40, 53.30, 7.10, 9.70)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hm(v):
    """mm → viewBox 单位。"""
    return v * MM_U


def _pin_rows(h):
    """排针 → [(x_mm, y_mm, net, silk, label_side)]（单列用 `pins`，双列用 `pins_left/right`）。"""
    out = []
    side_l, side_r = h["side"]
    if "pins" in h:
        for i, (net, silk) in enumerate(h["pins"]):
            out.append((h["cols"][0], h["y1"] + i * PITCH_MM, net, silk, side_l))
    else:
        for i, (net, silk) in enumerate(h.get("pins_left", [])):
            out.append((h["cols"][0], h["y1"] + i * PITCH_MM, net, silk, side_l))
        for i, (net, silk) in enumerate(h.get("pins_right", [])):
            out.append((h["cols"][1], h["y1"] + i * PITCH_MM, net, silk, side_r))
    return out


def _all_rows():
    rows = []
    for h in HEADERS:
        rows += _pin_rows(h)
    return rows


# 板上额外网络：**没有对应芯片脚号**（CFG0/CFG1 是模式脚，CH347 手册第 3 页的 20 脚表里
# 没有单列；GND/KEY 是按键扫描线，不是地）→ 一律发板级号，且**不许按 "/" 拆开去猜**
# （拆开 "GND/KEY" 会拆出 "GND" 而误并到地上 —— 这是 CH347F 上踩过的同类坑）。
BOARD_NETS = {"CFG0", "CFG1", "GND/KEY"}


def pad_map():
    """→ [(net, silk, x_mm, y_mm, connector 号, 是否该网的主脚)]

    分配规矩（与 CH347F / CH32V203C8T6 / SMA 一致）：
      · 一个网络在板上被**多个**排针引出时：**第一个**（上→下、左→右）拿**芯片脚号**
        （connector 0..19 = pin1..20）；其余每个焊盘各发一个**板级号**（20 起）；
      · `BOARD_NETS` 里的网络一律用板级号；
      · 每个焊盘都是**独立 connector**（都能接线），同网再用 .fzp 的 <buses> 互联。
    """
    pin_of = {}
    for n, nm in PIN_NAMES.items():
        pin_of[nm] = n - 1                    # 全名（如 "DSR0/GPIO2/SCS0/TMS"）
        for a in nm.split("/"):
            pin_of.setdefault(a, n - 1)       # 别名（如 "SCS0"、"TMS"）
    rows = sorted(_all_rows(), key=lambda r: (r[1], r[0]))          # 上→下、左→右
    used, rail, out = {}, [20], []
    for x, y, net, silk, _side in rows:
        pin = None if net in BOARD_NETS else pin_of.get(net)
        if pin is None or pin in used:
            cn, main = rail[0], False
            rail[0] += 1
        else:
            used[pin] = True
            cn, main = pin, True
        out.append((net, silk, x, y, cn, main))
    return out


def buses():
    """→ [(总线名, [connector 号…])]：同网必并一条总线（AGENTS §5「多焊盘同网络」条）。"""
    grp = {}
    for net, _silk, _x, _y, cn, _main in pad_map():
        grp.setdefault(net, []).append(cn)
    name = {"VCC": "3V3"}
    return [(name.get(net, net), sorted(cns)) for net, cns in sorted(grp.items())]


def _bake_icon(part_id, cx_mm, cy_mm, rot=0, out_dir=None):
    """把 `../<part_id>/svg.icon.<part_id>_icon.svg` 的 `<g id="icon">` 按 1:1 真实尺寸
    **烘成绝对坐标**嵌入（cx/cy 为 mm，图标 viewBox 中心对准它，再绕中心转 rot 度）。

    为什么烘（AGENTS §5）：嵌套 transform 在 Inkscape / Fritzing / VS Code 预览里解释不一致
    （会出现"芯片缩小到看不见"）；烘成绝对值就与别的元件一致。rect/circle 全部烘成绝对坐标，
    只有**文字**保留 rotate()（Fritzing 官方也这么写）。
    """
    import os
    import re
    base = out_dir or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "..", part_id, "svg.icon.%s_icon.svg" % part_id)
    art = open(path, encoding="utf-8").read()
    m = re.search(r'viewBox="([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+)"', art)
    b = re.search(r'<g\s+id="icon">(.*)</g>', art, re.S)
    if not m or not b:
        raise RuntimeError("图标几何读不到（%s）：需要 viewBox + <g id=\"icon\">" % path)
    x0, y0, w, h = (float(v) for v in m.groups())
    ccx, ccy = x0 + w / 2.0, y0 + h / 2.0
    cx, cy = hm(cx_mm), hm(cy_mm)
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


def gen_breadboard_svg(out_dir=None):
    """CH347T-EVT-R0-1v1 面包板视图（几何全部来自上面的表；**零嵌套变换**）。"""
    W, H = BOARD_MM
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %.1f %.1f">\n' % (W, H, hm(W), hm(H)),
         ' <g id="breadboard">\n',
         '  <rect x="0" y="0" width="%.1f" height="%.1f" rx="%.2f" ry="%.2f" fill="%s" '
         'stroke="%s" stroke-width="%.2f"/>\n'
         % (hm(W), hm(H), hm(BOARD_R), hm(BOARD_R), PCB_BLUE, PCB_EDGE, hm(BOARD_SW))]
    # 板上器件（icon 1:1 烘进来）
    for part, x, y, rot in ICONS:
        L.append(_bake_icon(part, x, y, rot, out_dir))
    # USB Type-C 母座（银色外壳 + 深色插口）
    ux, uy, uw, uh = USB_BODY
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" fill="#c9c9c9" '
             'stroke="#8f8f8f" stroke-width="%.2f"/>\n'
             % (hm(ux - uw / 2), hm(uy - uh / 2), hm(uw), hm(uh), hm(0.5), hm(0.15)))
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" fill="#5a5a5a" '
             'stroke="none"/>\n'
             % (hm(ux - uw / 2 + 0.8), hm(uy - uh / 2 + 0.8),
                hm(uw - 1.6), hm(uh - 1.6), hm(0.3)))
    # 排针：先塑料座（带 id，便于人工对照/回读；**不是** connector，fzp_check 只认 connectorNpin/pad/terminal）
    for h in HEADERS:
        rows = _pin_rows(h)
        if not rows:
            continue
        xs = [r[0] for r in rows]
        ys = [r[1] for r in rows]
        L.append('  <rect id="bbhdr_%s" x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                 'stroke="none"/>\n'
                 % (h["id"], hm(min(xs) - HDR_HALF_W), hm(min(ys) - HDR_END),
                    hm(max(xs) - min(xs) + 2 * HDR_HALF_W),
                    hm(max(ys) - min(ys) + 2 * HDR_END), HDR_BODY))
    # 排针脚（id 用 pad_map() 定的**最终 connector 号** → 与 .fzp / 原理图同一套号）
    for net, _silk, x, y, cn, _main in pad_map():
        L.append('  <circle id="connector%dpin" connectorname="%s" cx="%.3f" cy="%.3f" '
                 'r="%.3f" fill="%s" stroke="%s" stroke-width="%.3f"/>\n'
                 % (cn, _esc(net), hm(x), hm(y), hm(PIN_R), PIN_FILL, PIN_EDGE, hm(PIN_SW)))
    # 丝印：脚名
    for h in HEADERS:
        for x, y, _net, silk, side in _pin_rows(h):
            if not silk or side == "none":
                continue
            if side == "left":
                tx, anchor = x - LABEL_GAP, "end"
            else:
                tx, anchor = x + LABEL_GAP, "start"
            L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-family="DroidSans" '
                     'fill="%s" font-weight="bold" text-anchor="%s">%s</text>\n'
                     % (hm(tx), hm(y + BASELINE), hm(FS_SILK), SILK, anchor, _esc(silk)))
    # 丝印：块名（Pn）
    for h in HEADERS:
        rows = _pin_rows(h)
        if not rows or h.get("name") in (None, "none"):
            continue
        cx = (h["cols"][0] + h["cols"][-1]) / 2.0
        if h["name"] == "top":
            ty = min(r[1] for r in rows) - HDR_END - 0.45
        else:
            ty = max(r[1] for r in rows) + HDR_END + 0.95
        L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-family="DroidSans" '
                 'fill="%s" font-weight="bold" text-anchor="middle">%s</text>\n'
                 % (hm(cx), hm(ty), hm(FS_NAME), SILK_D, _esc(h["id"])))
    # 丝印：其它
    for txt, x, y, fs, anchor, rot, fill in TEXTS_EXTRA:
        a = ' fill="%s"' % fill
        if anchor and anchor != "none":
            a += ' text-anchor="%s"' % anchor
        a += ' font-weight="bold"'
        if rot:
            a += ' transform="rotate(%.1f,%.2f,%.2f)"' % (rot, hm(x), hm(y))
        L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-family="DroidSans"%s>%s'
                 '</text>\n' % (hm(x), hm(y), hm(fs), a, _esc(txt)))
    L += [' </g>\n', '</svg>\n']
    return "".join(L)
