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
import zipfile

SC = 2.8346456692913385  # pt per mm —— 与 CH347F / TX-AH-R900PNR_rev_1 / ESP32-S3-DevKitC-1 一致

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FZPZ_DIR = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))

PART_ID = "T-Halow-RJ45"

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

SMA_CX = BW / 2.0               # SMA 座中心（照片里基本居中）
SMA_BASE_Y0, SMA_BASE_Y1 = 0.2, 4.0
SMA_BASE_W = 5.2
SMA_STEM_W = 4.2
SMA_STEM_TOP = -9.0             # 螺纹柱伸出板外（俯视图画成向上伸出的侧影，与照片一致）

KEY_R = 1.7
KEY_L = (2.9, 3.7)              # Connect / PAIR 键
KEY_R_POS = (27.1, 3.7)         # RESET 键

LED_X, LED_W, LED_H = 22.6, 1.7, 0.9
LED_YS = [1.4, 3.6, 5.8, 8.0]
LED_NAMES = ["RSSI3", "RSSI2", "RSSI1", "CONN"]

MOD_X0, MOD_X1 = 6.2, 23.4      # U3 TX-AH-RX00P 模组（含半孔焊盘区）
MOD_Y0, MOD_Y1 = 14.4, 30.0

TYPEC_X0, TYPEC_X1 = 24.2, 29.6
TYPEC_Y0, TYPEC_Y1 = 19.8, 26.6

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
VB_X0, VB_Y0 = -1.0, SMA_STEM_TOP - 1.0
VB_X1, VB_Y1 = BW + 1.0, CAP_Y1 + 1.0


def u(v):
    """mm -> svg 内部单位（pt）"""
    s = f"{v * SC:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


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


def sma_art():
    """SMA 母座：座身方块 + 向上伸出的螺纹柱（照片的姿态）"""
    L = []
    L.append(rect(SMA_CX - SMA_BASE_W / 2.0, SMA_BASE_Y0, SMA_BASE_W,
                  SMA_BASE_Y1 - SMA_BASE_Y0, GOLD, GOLD_EDGE, 0.2, rx=0.35))
    L.append(rect(SMA_CX - SMA_STEM_W / 2.0, SMA_STEM_TOP, SMA_STEM_W,
                  -SMA_STEM_TOP + SMA_BASE_Y0, GOLD, GOLD_EDGE, 0.2, rx=0.3))
    y = SMA_STEM_TOP + 0.6
    while y < -0.4:
        L.append(line(SMA_CX - SMA_STEM_W / 2.0 + 0.15, y, SMA_CX + SMA_STEM_W / 2.0 - 0.15, y, GOLD_EDGE, 0.16))
        y += 0.75
    L.append(rect(SMA_CX - SMA_STEM_W / 2.0 - 0.35, SMA_STEM_TOP - 0.6, SMA_STEM_W + 0.7, 1.0,
                  GOLD, GOLD_EDGE, 0.2, rx=0.2))
    # 座身中心（俯视看进去）
    L.append(circ(SMA_CX, (SMA_BASE_Y0 + SMA_BASE_Y1) / 2.0, 1.5, SILVER, GOLD_EDGE, 0.15))
    L.append(circ(SMA_CX, (SMA_BASE_Y0 + SMA_BASE_Y1) / 2.0, 0.75, LABEL, GOLD_EDGE, 0.12))
    return L


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

    # U3 模组（白标签 + 半孔焊盘一圈）
    L.append(rect(MOD_X0, MOD_Y0, MOD_X1 - MOD_X0, MOD_Y1 - MOD_Y0, "#3d4a63", "#2a3346", 0.2, rx=0.4))
    L.append(rect(MOD_X0 + 1.5, MOD_Y0 + 1.4, MOD_X1 - MOD_X0 - 3.0, MOD_Y1 - MOD_Y0 - 2.8,
                  LABEL, "#c8c8c8", 0.2, rx=0.2))
    L.append(txt(MOD_X0 + 2.6, MOD_Y0 + 4.4, "FCC  CE", 0.95, fill="#3a3a3a"))
    L.append(txt(MOD_X0 + 2.6, MOD_Y0 + 7.6, "FCC ID: 2AXPI-R900", 0.8, fill="#5a5a5a"))
    L.append(txt(MOD_X0 + 2.6, MOD_Y0 + 10.8, "MODEL: T-HALOW", 0.8, fill="#5a5a5a"))
    L.append(txt(MOD_X0 + 2.6, MOD_Y0 + 13.8, "902MHz~928MHz", 0.8, fill="#5a5a5a"))
    L.append(txt(24.2, 16.4, "LILYGO", 1.0, rotate=-90, fill="#8f8f93"))

    # Type-C（USB1）
    L.append(rect(TYPEC_X0, TYPEC_Y0, TYPEC_X1 - TYPEC_X0, TYPEC_Y1 - TYPEC_Y0,
                  SILVER, "#7c7c81", 0.2, rx=0.6))
    L.append(rect(TYPEC_X0 + 0.7, TYPEC_Y0 + 0.9, TYPEC_X1 - TYPEC_X0 - 1.4,
                  TYPEC_Y1 - TYPEC_Y0 - 1.8, "#2a2a2c", "#6f6f74", 0.15, rx=0.3))

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
    L += top_features()
    L += pad_art()
    L += rj45_art()
    # SMA 天线连接器（座身中心）
    L.append(f'<g id="connector18pin">'
             + circ(SMA_CX, (SMA_BASE_Y0 + SMA_BASE_Y1) / 2.0, 1.0, "none", "none", 0)
             + '</g>')
    # Type-C：VBUS / GND（金属壳内两点）
    L.append(f'<g id="connector19pin"><circle cx="{u(TYPEC_X0 + 1.6)}" cy="{u((TYPEC_Y0 + TYPEC_Y1) / 2)}" r="{u(0.45)}" fill="none" stroke="none"/></g>')
    L.append(f'<g id="connector20pin"><circle cx="{u(TYPEC_X1 - 1.6)}" cy="{u((TYPEC_Y0 + TYPEC_Y1) / 2)}" r="{u(0.45)}" fill="none" stroke="none"/></g>')
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
        rect(MOD_X0, MOD_Y0, MOD_X1 - MOD_X0, MOD_Y1 - MOD_Y0, "#3d4a63", "#2a3346", 0.2, rx=0.4),
        rect(MOD_X0 + 1.5, MOD_Y0 + 1.4, MOD_X1 - MOD_X0 - 3.0, MOD_Y1 - MOD_Y0 - 2.8,
             LABEL, "#c8c8c8", 0.2, rx=0.2),
        rect(TYPEC_X0, TYPEC_Y0, TYPEC_X1 - TYPEC_X0, TYPEC_Y1 - TYPEC_Y0, SILVER, "#7c7c81", 0.2, rx=0.6),
        txt(10.6, 42.0, "T-Halow RJ45", 1.6, rotate=-90),
    ]
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
