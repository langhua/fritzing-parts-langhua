# -*- coding: utf-8 -*-
"""gen_part.py — T-Halow-RJ45 (Taixin HaLow 802.11ah <-> RJ45 bridge module)

生成 Fritzing 部件（按用户 2026-09-17 要求：只做 icon + breadboard 两个视图）：

  svg.icon.T-Halow-RJ45_icon.svg
  svg.breadboard.T-Halow-RJ45_breadboard.svg
  part.T-Halow-RJ45.fzp
  ../../fzpz/T-Halow-RJ45.fzpz

几何来源（用户实测，2026-09-17）：
  主板 55 x 30 mm；RJ45 舌头板再伸出 18 mm（宽 15 mm）；
  水晶头塑料护套再伸出 13.6 mm；左侧 10 个圆焊盘间距 2.54 mm；
  1.6 与 2.4 两块板 PCB 相同（只是固件不同）。
  照片校准（docs/product.png，6.70 px/mm）：板身 201 px = 30.0 mm、
  10 个焊盘中心跨度 22.9 mm = 9 x 2.54，两点互证，故其余位置按同一比例取自照片。

电气来源（hardware/T-Halow RJ45 V0.1.pdf 原理图）：
  U3 = TX-AH-RX00P 模组(38pin)、U7 = IP101GR PHY、T1 = H1102NLT 变压器、
  U6 = 水晶头插板式、USB1 = TYPE-C 16P、P2 = Header 10（左侧 10 个焊盘）、
  RF1 = BWSMA-KE-P001 天线座、P1 = 电池座(背面，本视图不画)。

丝印以实物为准（照片 + 原理图）：
  10 个焊盘 = MCLR / IOA9 / IOA6 / IOA7 / IOA8 / IOB1 / TX / RX / 3V3 / GND
  按键 = Connect(PAIR) / RESET；LED = RSSI3 / RSSI2 / RSSI1 / CONN
  跳线 = STA / NO / AP；板号 = T-Halow RJ45 V1.0
"""

import os
import re
import zipfile

SC = 2.8346456692913385  # pt per mm —— 与 CH347F / TX-AH-R900PNR_rev_1 / ESP32-S3-DevKitC-1 一致

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FZPZ_DIR = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))

PART_ID = "T-Halow-RJ45"

# 跨部件 1:1 复用的图形素材（AGENTS §4：允许引用仓库内其它部件目录的 svg，
# 但绝不引用仓库外文件；文件缺失就报错，不静默退化）
SMA3_ASSET = os.path.abspath(os.path.join(OUT_DIR, "..", "SMA-PJ1.7-L9.5",
                                          "sma_icon_3pin_clean.svg"))
MOD_ASSET = os.path.abspath(os.path.join(
    OUT_DIR, "..", "TX-AH-R900PNR", "svg.icon.TX-AH-R900PNR_1_icon.svg"))
TYC_ASSET = os.path.abspath(os.path.join(
    OUT_DIR, "..", "TypeC16Pin",
    "svg.icon.TypeC16Pin_d89a481c23a1ca4ff437422a227ed0bb_1_icon.svg"))
# 板上贴片器件（本轮新入库的元件，直接用它们自己的 icon 还原实物外观）
IP101_ASSET = os.path.abspath(os.path.join(OUT_DIR, "..", "IP101GR",
                                           "svg.icon.IP101GR_icon.svg"))
H1102_ASSET = os.path.abspath(os.path.join(OUT_DIR, "..", "H1102NLT",
                                           "svg.icon.H1102NLT_icon.svg"))
SY8089_ASSET = os.path.abspath(os.path.join(OUT_DIR, "..", "SY8089",
                                            "svg.icon.SY8089_icon.svg"))
CN3165_ASSET = os.path.abspath(os.path.join(OUT_DIR, "..", "CN3165",
                                            "svg.icon.CN3165_icon.svg"))

# ---------------------------------------------------------------- 几何常量 (mm)
BW, BH = 30, 55          # 主板（实测）
TW, TL = 15, 18          # RJ45 舌头板：宽 / 长度（伸出主板之外的部分）
CAP_L = 13.6             # 水晶头塑料护套再伸出舌头板末端的长度（实测）
SH_W = 14                # 护套宽（照片 100 px / 6.7 = 14.9，按标准 8P8C 取 14）
SH_Y0, SH_Y1 = BH, 63.5  # 护套主体：包住舌头根部的这一段
CAP_X0, CAP_X1 = 8.5, 21.5
CAP_Y1 = BH + TL + CAP_L  # 86.6 —— 水晶头最前端

X_L = (BW - TW) / 2.0     # 舌头板左缘 7.5

PAD_X = 1.9               # 10 个焊盘中心距左边缘
PAD_Y0 = 11.9             # 第一个焊盘（MCLR）距板顶
PAD_DY = 2.54             # 实测间距
PAD_R = 0.9

PADS = ["MCLR", "IOA9", "IOA6", "IOA7", "IOA8", "IOB1", "TX", "RX", "3V3", "GND"]

RJ45_X0, RJ45_X1 = 66.0, 72.0   # 金手指 y 区间
RJ45_PITCH, RJ45_W = 1.5, 0.9   # 8 条金手指的间距 / 宽度

SMA_CX = BW / 2.0               # 天线座中心（照片里基本居中）
SMA_3PIN_W, SMA_3PIN_PIN = 6.6, 4.0   # 三脚素材：引脚沿本地 y 铺 6.6mm、引脚长（本地 x）4.0mm
SMA_PIN_END_Y = 4.5             # 三个引脚的板内末端 y（螺纹筒 = 4.5 - 13.6 = -9.1mm，照片量 9.5）

TYPEC_Y0 = 19.8                 # USB-C 座：素材旋转 90° 后占 x 23.4..31.0（插口朝板右边缘）/ y 19.8..28.7
TYPEC_X1 = 31.0

KEY_R = 1.7
KEY_L = (2.9, 3.7)              # Connect / PAIR 键
KEY_R_POS = (27.1, 3.7)         # RESET 键

LED_X, LED_W, LED_H = 22.6, 1.7, 0.9
LED_YS = [1.4, 3.6, 5.8, 8.0]
LED_NAMES = ["RSSI3", "RSSI2", "RSSI1", "CONN"]

MOD_X0, MOD_X1 = 6.2, 23.4      # U3 TX-AH-RX00P 模组（含半孔焊盘区）
MOD_Y0, MOD_Y1 = 14.4, 30.0

# 板上贴片器件中心（mm）—— 这几个只是**还原实物外观**，不做 connector
#   依据：IP101GR / H1102NLT 的位置按实物照片量（6.70 px/mm）；
#   SY8089 / CN3165 是 SOT-23-5 / DFN-8 小封装，照片里分不出，位置按原理图的
#   功能分区（DCDC 与 Battery Charger 两块都布置在板中部靠右）**起稿**，
#   待用户在 Inkscape 里对着实物校正（AGENTS §4 的“我先起稿、用户校”模式）。
IP101_CTR = (8.6, 45.7)         # U7 IP101GR PHY（QFN32）
H1102_CTR = (16.3, 61.4)        # T1 H1102NLT 网络变压器（在 RJ45 舌头板上）
SY8089_CTR = (17.0, 32.0)       # U2 SY8089 DCDC（避开左侧竖排板号丝印）
CN3165_CTR = (20.5, 33.0)       # U1 CN3165 充电器

JMP_X = 2.9                     # STA / NO / AP 三针跳线（在板左下）
JMP_YS = [41.5, 47.3, 50.3]

SILK = "#e8e8e8"           # 丝印白
BOARD = "#1c1c1e"          # 哑光黑板
BOARD_EDGE = "#3a3a3c"
PLASTIC = "#2b2b2e"        # 水晶头塑料
PLASTIC_EDGE = "#55555a"
GOLD = "#d8a72a"
GOLD_EDGE = "#8a5d12"
SILVER = "#b8b8bc"
LABEL = "#f2f2f2"

FONT = "DroidSans"

# 画布（mm）：上方留给 SMA 柱，下方到水晶头前端
VB_X0, VB_Y0 = -1.0, SMA_PIN_END_Y - 13.6 - 1.0
VB_X1, VB_Y1 = BW + 4.0, CAP_Y1 + 1.0


def u(v):
    """mm -> svg 内部单位（pt）"""
    s = f"{v * SC:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


def read_group(path, gid):
    """从另一个部件的 svg 里抠出 <g id="gid">…</g> 片段（跨部件 1:1 复用）。
    素材文件缺失/找不到该组 → 直接报错（不静默退化成自画图形）。"""
    with open(path, encoding="utf-8") as fh:
        s = fh.read()
    m = re.search(r'<g\s[^>]*id="%s"' % re.escape(gid), s)
    if not m:
        raise ValueError('no <g id="%s"> in %s' % (gid, path))
    start = m.start()
    i, depth = start, 0
    while True:
        nopen = s.find("<g", i)
        nclose = s.find("</g>", i)
        if nclose < 0:
            raise ValueError("unbalanced <g> in %s" % path)
        if 0 <= nopen < nclose:
            depth += 1
            i = nopen + 2
        else:
            depth -= 1
            i = nclose + 4
            if depth == 0:
                return s[start:i]


def dedupe_defs(g):
    """素材里同一份 <defs> 重复出现多次（id 重复），内联时只留第一份"""
    blocks = re.findall(r"<defs>.*?</defs>", g, re.S)
    for b in blocks[1:]:
        g = g.replace(b, "", 1)
    return g


def txt(x, y, s, size=1.35, anchor=None, rotate=None, fill=SILK, weight=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    t = f' transform="rotate({rotate} {u(x)} {u(y)})"' if rotate is not None else ""
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{u(x)}" y="{u(y)}" font-family="{FONT}" font-size="{u(size)}"'
            f' fill="{fill}"{a}{t}{w}>{s}</text>')


def rect(x, y, w, h, fill, stroke=None, sw=0.15, rx=None, sid=None):
    i = f' id="{sid}"' if sid else ""
    r = f' rx="{u(rx)}"' if rx else ""
    s = f' stroke="{stroke}" stroke-width="{u(sw)}"' if stroke else ' stroke="none"'
    return f'<rect{i} x="{u(x)}" y="{u(y)}" width="{u(w)}" height="{u(h)}"{r} fill="{fill}"{s}/>'


def circ(cx, cy, r, fill, stroke=None, sw=0.15, sid=None):
    i = f' id="{sid}"' if sid else ""
    s = f' stroke="{stroke}" stroke-width="{u(sw)}"' if stroke else ' stroke="none"'
    return f'<circle{i} cx="{u(cx)}" cy="{u(cy)}" r="{u(r)}" fill="{fill}"{s}/>'


def line(x1, y1, x2, y2, stroke, sw):
    return (f'<line x1="{u(x1)}" y1="{u(y1)}" x2="{u(x2)}" y2="{u(y2)}"'
            f' stroke="{stroke}" stroke-width="{u(sw)}" stroke-linecap="round"/>')


def svg_head(w_mm, h_mm, x0, y0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_mm:g}mm" height="{h_mm:g}mm" '
            f'viewBox="{u(x0)} {u(y0)} {u(w_mm)} {u(h_mm)}">')


def board_body():
    """主板 + 舌头板 + 水晶头（两视图共用）"""
    L = []
    # 主板（哑光黑，四角圆角）
    L.append(rect(0, 0, BW, BH, BOARD, BOARD_EDGE, 0.25, rx=1.4))
    # RJ45 舌头板（PCB 舌片）
    L.append(rect(X_L, BH - 0.2, TW, TL + 0.2, BOARD, BOARD_EDGE, 0.25))
    # 金手指（8 条，露在护套之外）
    n = 8
    x0 = SMA_CX - (n - 1) * RJ45_PITCH / 2.0
    for i in range(n):
        L.append(rect(x0 + i * RJ45_PITCH - RJ45_W / 2.0, RJ45_X0, RJ45_W,
                      RJ45_X1 - RJ45_X0, GOLD, GOLD_EDGE, 0.12, rx=0.15))
    # 护套主体（包住舌头根部）
    L.append(rect((BW - SH_W) / 2.0, SH_Y0 - 0.2, SH_W, SH_Y1 - SH_Y0 + 0.2,
                  PLASTIC, PLASTIC_EDGE, 0.3, rx=0.6))
    # 水晶头前端（舌头末端之外的那一段，含卡扣台阶）
    L.append(rect(CAP_X0, BH + TL, CAP_X1 - CAP_X0, CAP_Y1 - BH - TL - 0.5,
                  PLASTIC, PLASTIC_EDGE, 0.3, rx=0.8))
    L.append(rect(CAP_X0 + 1.0, BH + TL - 0.3, CAP_X1 - CAP_X0 - 2.0, 5.4,
                  PLASTIC, PLASTIC_EDGE, 0.25, rx=0.4))
    return L


def reid(g, prefix):
    """给内联片段里的 id 及其 url(#…) 引用加前缀 —— 避免与宿主 svg 的 id 冲突。
    （TX-AH 的 icon 里嵌了 RT6150 / TXW8301 的图形，自带 <defs> 渐变，必须重命名。）"""
    for i in sorted(set(re.findall(r'id="([^"]+)"', g)), key=len, reverse=True):
        g = g.replace('id="%s"' % i, 'id="%s%s"' % (prefix, i))
        g = g.replace("url(#%s)" % i, "url(#%s%s)" % (prefix, i))
    return g


def viewbox_center(path):
    """素材 svg 的 viewBox 中心（mm）—— 用于把图形中心对齐到板上坐标。"""
    s = open(path, encoding="utf-8").read()
    m = re.search(r'viewBox="([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+)"', s)
    if not m:
        raise ValueError("no viewBox in %s" % path)
    x, y, w, h = (float(v) for v in m.groups())
    return x + w / 2.0, y + h / 2.0


def art_centered(path, cx, cy, rot=0, prefix=None):
    """1:1 复用另一个部件 icon 的 <g id="icon">，把**图形中心**对齐到板上 (cx, cy) 再旋转。
    单位：素材 viewBox 单位 = mm，宿主用 pt ⇒ scale(SC)。"""
    g = dedupe_defs(read_group(path, "icon"))
    if prefix:
        g = reid(g, prefix)
    ox, oy = viewbox_center(path)
    return ('<g transform="translate(%s %s) rotate(%d) scale(%s) translate(%s %s)">\n%s\n</g>'
            % (u(cx), u(cy), rot, SC, -ox, -oy, g))


def sma_art():
    """天线座（RF1）：1:1 复用 svg/SMA-PJ1.7-L9.5 的**干净三脚**图形
    `sma_icon_3pin_clean.svg`（与 TX-AH-R900PNR 板上同一个画法，用户 2026-09-17 定）。
    素材 13.6×6.6mm：本地 x 0..4 = 三个金引脚（本地 y 0..6.6 铺开）、x 4..13.6 = 螺纹筒。
    rotate(-90) 后：引脚沿板 x 铺开（居中于 SMA_CX）、螺纹筒朝板上方伸出 9.1mm。"""
    s = open(SMA3_ASSET, encoding="utf-8").read()
    inner = re.sub(r'^.*?<svg[^>]*>\n?', '', s, flags=re.S)
    inner = re.sub(r'</svg>\s*$', '', inner, flags=re.S)
    inner = reid(inner, "thrj_sma_")
    return ['<g transform="translate(%s %s) rotate(-90) scale(%s)">\n%s\n</g>'
            % (u(SMA_CX - SMA_3PIN_W / 2.0), u(SMA_PIN_END_Y), SC, inner)]


def txah_art():
    """U3 TX-AH-RX00P（= LILYGO T-HALOW 模组）。

    ★ 用户 2026-09-17 定：图案用 `svg/TX-AH-R900PNR` 的 icon（15×17mm），
      TH-RJ45 板上用的是**带金属壳**的那个版本 —— 仓库里两个 TX-AH 目录
      （`TX-AH-R900PNR` / `TX-AH-R900PNR_rev_1`）的 icon 都是**裸模组**
      （只有四周半孔焊盘 + 板载器件），所以按实物照片**在 icon 之上再覆一层
      金属屏蔽罩 + 白色标签**：罩把板载器件盖住（与实物所见一致），
      四周半孔焊盘带仍露在罩外。这与 icon 的几何不冲突，只是补上实物的那层壳。
    """
    cx = (MOD_X0 + MOD_X1) / 2.0
    cy = (MOD_Y0 + MOD_Y1) / 2.0
    MW_, MH_ = MOD_X1 - MOD_X0, MOD_Y1 - MOD_Y0          # 17.2 × 15.6
    L = [art_centered(MOD_ASSET, cx, cy, rot=90, prefix="thrj_mod_")]
    # 金属屏蔽罩：模组四周各留 1.2mm 的焊盘带（照片上露出的深色边约这么宽）
    sx0, sy0 = cx - MW_ / 2 + 1.2, cy - MH_ / 2 + 1.2
    sw, sh = MW_ - 2.4, MH_ - 2.4
    L.append(rect(sx0, sy0, sw, sh, "#d5d8db", "#9aa0a6", 0.12, rx=0.35))
    # 白色标签（贴在罩中央；照片上标签占罩面大部分）
    lx0, ly0 = sx0 + 1.1, sy0 + 1.1
    lw, lh = sw - 2.2, sh - 2.2
    L.append(rect(lx0, ly0, lw, lh, "#f4f4f2", "#cfcfcc", 0.1, rx=0.15))
    tx = lx0 + 0.6
    L.append(txt(tx, ly0 + 1.9, "FCC  CE", 1.4, fill="#2b2b2b"))
    L.append(txt(tx, ly0 + 4.2, "FCC ID: 2AXPI-R900", 0.9, fill="#333333"))
    L.append(txt(tx, ly0 + 6.4, "MODEL: T-HALOW", 0.9, fill="#333333"))
    L.append(txt(tx, ly0 + 8.6, "902MHz~928MHz", 0.9, fill="#333333"))
    return L


def chips_art():
    """板上贴片器件：IP101GR / H1102NLT / SY8089 / CN3165 —— 各自 1:1 复用本元件 icon。
    这些只是**还原实物外观**（工业风，不加装饰），不是可连线 connector。"""
    return [
        art_centered(IP101_ASSET, IP101_CTR[0], IP101_CTR[1], rot=0, prefix="thrj_u7_"),
        art_centered(H1102_ASSET, H1102_CTR[0], H1102_CTR[1], rot=90, prefix="thrj_t1_"),
        art_centered(SY8089_ASSET, SY8089_CTR[0], SY8089_CTR[1], rot=0, prefix="thrj_u2_"),
        art_centered(CN3165_ASSET, CN3165_CTR[0], CN3165_CTR[1], rot=0, prefix="thrj_u1_"),
    ]


def typec_art():
    """USB-C（USB1）：1:1 复用 svg/TypeC16Pin 的 icon 图形，旋转 90° 使插口朝板右边缘。"""
    g = dedupe_defs(read_group(TYC_ASSET, "g40446"))
    return ['<g transform="translate(%s %s) rotate(90)">\n%s\n</g>'
            % (u(TYPEC_X1), u(TYPEC_Y0), g)]


def top_features():
    """按键 / LED / 模组 / Type-C / 跳线 / 丝印（面包板视图用）"""
    L = []
    for cx, cy in (KEY_L, KEY_R_POS):
        L.append(circ(cx, cy, KEY_R, SILVER, "#6f6f74", 0.2))
        L.append(circ(cx, cy, KEY_R - 0.5, LABEL, "#c9c9cd", 0.15))
    L.append(txt(0.9, 6.6, "Connect", 1.1, rotate=-90))
    L.append(txt(29.4, 6.6, "RESET", 1.1, rotate=-90))

    for i, (name, y) in enumerate(zip(LED_NAMES, LED_YS)):
        L.append(rect(LED_X, y, LED_W, LED_H, "#fdf3c8", "#c9b96a", 0.15, rx=0.2))
        L.append(txt(LED_X - 0.6, y + LED_H - 0.1, name, 1.05, anchor="end"))

    # U3 模组（1:1 复用 TX-AH-R900PNR 的 icon）
    L += txah_art()

    # STA / NO / AP 跳线（三针）
    for name, y in zip(("STA", "NO", "AP"), JMP_YS):
        L.append(circ(JMP_X, y, 0.8, GOLD, GOLD_EDGE, 0.15))
        L.append(txt(JMP_X + 1.6, y + 0.5, name, 1.15))
    L.append(rect(JMP_X - 0.9, JMP_YS[1] - 1.1, 1.8, 2.2, "#2f2f33", "#6f6f74", 0.15, rx=0.2))

    # 板号丝印（竖排）
    L.append(txt(10.6, 42.0, "T-Halow RJ45", 1.6, rotate=-90))
    L.append(txt(12.8, 39.0, "V1.0  20260909", 1.05, rotate=-90))
    return L


def pad_art(pads_in_group=False):
    L = []
    for i, name in enumerate(PADS):
        y = PAD_Y0 + i * PAD_DY
        sid = f"connector{i}pin"
        if name == "GND":
            L.append(f'<g id="{sid}">' + rect(PAD_X - PAD_R, y - PAD_R, 2 * PAD_R, 2 * PAD_R,
                                              LABEL, "#a9a9ad", 0.15)
                     + rect(PAD_X - PAD_R + 0.35, y - PAD_R + 0.35, 2 * PAD_R - 0.7, 2 * PAD_R - 0.7,
                            "#3a3a3a", None, 0, sid=None) + '</g>')
        else:
            L.append(f'<g id="{sid}">' + circ(PAD_X, y, PAD_R, LABEL, "#a9a9ad", 0.15)
                     + circ(PAD_X, y, PAD_R * 0.42, "#3a3a3a", None, 0) + '</g>')
        L.append(txt(PAD_X + PAD_R + 0.6, y + 0.45, name, 1.15))
    return L


def rj45_art():
    L = []
    n = 8
    x0 = SMA_CX - (n - 1) * RJ45_PITCH / 2.0
    for i in range(n):
        xc = x0 + i * RJ45_PITCH
        L.append(f'<g id="connector{10 + i}pin">'
                 + rect(xc - RJ45_W / 2.0, RJ45_X0 + 0.1, RJ45_W, RJ45_X1 - RJ45_X0 - 0.2,
                        GOLD, GOLD_EDGE, 0.1, rx=0.15)
                 + '</g>')
    return L


def build_breadboard():
    w = VB_X1 - VB_X0
    h = VB_Y1 - VB_Y0
    L = [svg_head(w, h, VB_X0, VB_Y0),
         f'  <g id="breadboard">']
    L += board_body()
    L += sma_art()
    L += chips_art()
    L += top_features()
    L += typec_art()
    L += pad_art()
    L += rj45_art()
    # SMA 天线连接器（座子正下方的板内一点）
    L.append(f'<g id="connector18pin">'
             + circ(SMA_CX, 1.2, 1.0, "none", "none", 0)
             + '</g>')
    # Type-C：VBUS / GND（座子内部两点）
    L.append(f'<g id="connector19pin"><circle cx="{u(27.0)}" cy="{u(21.5)}" r="{u(0.45)}" fill="none" stroke="none"/></g>')
    L.append(f'<g id="connector20pin"><circle cx="{u(27.0)}" cy="{u(27.0)}" r="{u(0.45)}" fill="none" stroke="none"/></g>')
    L.append(f'  </g>\n</svg>\n')
    return "\n".join(L)


def build_icon():
    w = VB_X1 - VB_X0
    h = VB_Y1 - VB_Y0
    L = [svg_head(w, h, VB_X0, VB_Y0),
         '  <g id="icon">']
    L += board_body()
    L += sma_art()
    L += [
        circ(KEY_L[0], KEY_L[1], KEY_R, SILVER, "#6f6f74", 0.2),
        circ(KEY_R_POS[0], KEY_R_POS[1], KEY_R, SILVER, "#6f6f74", 0.2),
    ]
    L += txah_art()
    L += chips_art()
    L += [
        txt(10.6, 42.0, "T-Halow RJ45", 1.6, rotate=-90),
    ]
    L += typec_art()
    for i in range(len(PADS)):
        y = PAD_Y0 + i * PAD_DY
        L.append(circ(PAD_X, y, PAD_R, LABEL, "#a9a9ad", 0.12))
    L.append('  </g>\n</svg>\n')
    return "\n".join(L)


CONNECTORS = (
    [(i, PADS[i], PADS[i]) for i in range(len(PADS))]
    + [(10 + i, str(i + 1), f"RJ45 pin {i + 1}") for i in range(8)]
    + [(18, "ANT", "antenna (SMA)"),
       (19, "VBUS", "USB-C VBUS (charging input)"),
       (20, "GND", "USB-C GND")]
)


def build_fzp():
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">',
         ' <version>1</version>',
         ' <date>2026-09-17</date>',
         ' <label>U</label>',
         ' <author>Shi Jinghai</author>',
         ' <title>T-Halow-RJ45 (Taixin HaLow 802.11ah to RJ45 bridge)</title>',
         ' <tags><tag>HaLow</tag><tag>802.11ah</tag><tag>Taixin</tag><tag>TX-AH</tag>'
         '<tag>TXW8301</tag><tag>RJ45</tag><tag>Ethernet</tag><tag>WLAN</tag></tags>',
         ' <properties>',
         '  <property name="family">Taixin HaLow</property>',
         '  <property name="physical">55 x 30 mm PCB + RJ45 plug</property>',
         '  <property name="variants">v1.6 / v2.4 (same PCB, different firmware)</property>',
         ' </properties>',
         ' <views>',
         f'  <iconView><layers image="icon/{PART_ID}_icon.svg"><layer layerId="icon"/></layers></iconView>',
         f'  <breadboardView fliphorizontal="true" flipvertical="true">'
         f'<layers image="breadboard/{PART_ID}_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>',
         ' </views>',
         ' <connectors>']
    for cid, name, desc in CONNECTORS:
        L.append(f'  <connector id="connector{cid}" name="{name}" type="male">')
        L.append(f'   <description>{desc}</description>')
        L.append('   <views>')
        L.append(f'    <breadboardView><p layer="breadboard" svgId="connector{cid}pin"/></breadboardView>')
        L.append('   </views>')
        L.append('  </connector>')
    L.append(' </connectors>')
    L.append(' <buses>')
    L.append('  <bus id="GND">')
    L.append('   <nodeMember connectorId="connector9"/>')
    L.append('   <nodeMember connectorId="connector20"/>')
    L.append('  </bus>')
    L.append(' </buses>')
    L.append('</module>')
    return "\n".join(L) + "\n"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FZPZ_DIR, exist_ok=True)
    files = {
        f"svg.icon.{PART_ID}_icon.svg": build_icon(),
        f"svg.breadboard.{PART_ID}_breadboard.svg": build_breadboard(),
        f"part.{PART_ID}.fzp": build_fzp(),
    }
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print("wrote %-58s %7d bytes" % (name, len(content.encode("utf-8"))))

    fzpz = os.path.join(FZPZ_DIR, f"{PART_ID}.fzpz")
    with zipfile.ZipFile(fzpz, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(os.path.join(OUT_DIR, name), name)
    print("wrote %s (%d bytes)" % (fzpz, os.path.getsize(fzpz)))


if __name__ == "__main__":
    main()
