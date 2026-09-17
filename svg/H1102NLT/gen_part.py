#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 H1102NLT (Pulse 10/100Base-T 单口网络隔离变压器)。

芯片工作流（AGENTS.md §2）：icon → breadboard → schematic → pcb。
源文件同目录，.fzpz 输出到仓库顶层 fzpz/（内部平铺，.fzp 的 image= 用子目录路径）。

数据来源：
  1) 器件手册 `D:\\Downloads\\H1102NLT.pdf`（Pulse H325.R 04/13）：
     · 第 2 页「10/100 Circuit」给出接线：CHIP SIDE 的 TD± / RD±（含初级中心抽头）
       经两组 1:1 变压器到 CABLE SIDE，线侧接 RJ45 的 1/2（TX 对）与 3/6（RX 对），
       线侧中心抽头经 75Ω/1000pF 到地。
     · 第 1 页 Mechanical + SUGGESTED LAND PATTERN：
       本体 **12.70 × 7.11 mm**、含引脚总宽 **9.53 mm MAX**、脚距 **1.27 mm**、8 脚跨度 8.89 mm、
       引脚宽 0.51；推荐焊盘 **1.67 × 0.76**、外缘距 10.20 / 内缘距 6.86（中心跨距 8.53）。
  2) **嘉立创/立创EDA 封装**（用户 2026-09-17 提供 `D:\\Downloads\\20F01_2026-09-17.svg`）：
     实测 16 个 RECT 焊盘 **0.760(y) × 1.660(x)**、两列 x=±4.318（**焊盘中心跨距 8.636**）、
     每列 8 个、脚距 1.270 —— 与手册推荐值互证（差 0.1mm），**按立创取值**（AGENTS 取证顺序）。
  3) **嘉立创/立创EDA 原理图符号**（用户 2026-09-17 提供 `D:\\Downloads\\H1102NLT_2026-09-17.svg`）：
     已收进 `svg/_assets/h1102nlt_sch_symbol.svg`（仓库内，运行时不碰仓库外文件）。
     本脚本**直接内联它的几何**（绕组符号：TX/RX 两组 + 铁芯 + 12 个引脚），按 Fritzing
     原理图网格缩放（立创 20 单位 = 100mil → Fritzing 100 单位），并把立创的深红 #880000
     换成仓库统一的黑，字体 Verdana → DroidSans。

引脚（16 脚封装；手册第 2 页接线图 + 立创符号都只画 12 个用到的脚，
**4/5/12/13 为 NC、不引出**）：
  1 TD+  2 TD_CT  3 TD-    （PHY 侧发送差分 + 初级中心抽头）
  6 RD+  7 RD_CT  8 RD-    （PHY 侧接收差分 + 初级中心抽头）
  16 TX+ 15 TX_CT 14 TX-   （线侧发送 → RJ45 1/2，中心抽头 75Ω 到地）
  11 RX+ 10 RX_CT 9 RX-    （线侧接收 → RJ45 3/6，中心抽头 75Ω 到地）

用法：python gen_part.py
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "H1102NLT"
FZPZ = "H1102NLT.fzpz"

SRA_ASSET = os.path.abspath(os.path.join(OUT_DIR, "..", "_assets", "h1102nlt_sch_symbol.svg"))

# (connector_id, 脚号, 功能名, 立创符号 c_origin, pcb 列, pcb 焊盘 y)
SRA_PINS = [
    (0,  "1",  "TD+",    (-50, -70), "L", -4.445),
    (1,  "2",  "TD_CT",  (-50, -50), "L", -3.175),
    (2,  "3",  "TD-",    (-50, -30), "L", -1.905),
    (3,  "6",  "RD+",    (-50,  30), "L",  1.905),
    (4,  "7",  "RD_CT",  (-50,  50), "L",  3.175),
    (5,  "8",  "RD-",    (-50,  70), "L",  4.445),
    (6,  "9",  "RX-",    ( 60,  70), "R", -4.445),
    (7,  "10", "RX_CT",  ( 60,  50), "R", -3.175),
    (8,  "11", "RX+",    ( 60,  30), "R", -1.905),
    (9,  "14", "TX-",    ( 60, -30), "R",  1.905),
    (10, "15", "TX_CT",  ( 60, -50), "R",  3.175),
    (11, "16", "TX+",    ( 60, -70), "R",  4.445),
]
NC_PINS = ["4", "5", "12", "13"]          # 封装上有焊盘、符号里不画、不引出

ICON_LABEL = "H1102NLT"
TITLE = "H1102NLT 10/100Base-T Isolation Transformer"
LABEL = "T"
PACKAGE = "16-Pin SOIC"
FAMILY = "Pulse Magnetics"

# 封装几何（mm，嘉立创实测 / 手册互证）
BODY_W, BODY_H = 7.11, 12.70       # 本体（宽 x × 长 y）
PAD_X, PAD_L, PAD_W = 4.318, 1.660, 0.760   # 焊盘中心 x / 长(x) / 宽(y)
PAD_Y0, PAD_PITCH = -4.445, 1.27
SCALE_SCH = 5                      # 立创 20 单位 = 100mil → Fritzing 100 单位（0.1in）

SVG_HDR = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           '<!-- H1102NLT -->\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ 素材读取
def read_jlc_symbol():
    """从 svg/_assets/h1102nlt_sch_symbol.svg 抠出立创符号的根组 <g c_origin="5,0" …>…</g>"""
    with open(SRA_ASSET, encoding="utf-8") as fh:
        s = fh.read()
    m = re.search(r'<g c_origin="5,0"', s)
    if not m:
        raise ValueError("找不到立创符号的根组（%s）" % SRA_ASSET)
    start, i, depth = m.start(), m.start(), 0
    while True:
        nopen, nclose = s.find("<g", i), s.find("</g>", i)
        if nclose < 0:
            raise ValueError("立创符号的 <g> 不平衡")
        if 0 <= nopen < nclose:
            depth += 1
            i = nopen + 2
        else:
            depth -= 1
            i = nclose + 4
            if depth == 0:
                return s[start:i]


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """原理图 = **1:1 内联立创EDA 的绕组符号**（svg/_assets 里的那份），只做三件事：
       ① 深红 #880000 → 仓库统一的黑；② Verdana → DroidSans、字号换算成 Fritzing 单位
       （立创 7pt 在 Fritzing 里 ≈ 97 单位，缩放 5 倍后仍要 97 → 写 19.4）；
       ③ 给 12 个引脚组挂上 id="connectorNpin" class="pin" + 外端 0.0001 的 terminal。"""
    g = read_jlc_symbol()
    g = g.replace("#880000", "#000000")
    g = g.replace('font-family="Verdana"', 'font-family="DroidSans"')
    g = g.replace('font-size="7pt"', 'font-size="19.4"')
    for cid, num, name, (sx, sy), _, _ in SRA_PINS:
        pat = re.compile(r'<g ([^>]*c_origin="%d,%d"[^>]*)>' % (sx, sy))

        def rep(m, cid=cid, sx=sx, sy=sy):
            # 先去掉立创自己的 id="ggeNN"（否则与我们的 id 重复，SVG 非法）。
            # 注意要求 id= 前面有空白，否则会把 c_partid="part_pin" 里的 id= 也删掉。
            attrs = re.sub(r'\s+id="[^"]*"', '', m.group(1))
            return ('<g %s id="connector%dpin" class="pin">'
                    '<rect id="connector%dterminal" x="%d" y="%d" width="0.0001" height="0.0001" '
                    'fill="none" stroke="none"/>' % (attrs, cid, cid, sx, sy))

        g, n = pat.subn(rep, g, count=1)
        if n != 1:
            raise ValueError("引脚 %s（c_origin=%d,%d）没挂上 connector id" % (num, sx, sy))
    # 缩放后的内容范围：立创 viewBox 是 -61.8..71.8 × -90.4..90
    x0, y0 = -61.8 * SCALE_SCH - 20, -90.4 * SCALE_SCH - 20
    w, h = (71.8 - -61.8) * SCALE_SCH + 40, (90 - -90.4) * SCALE_SCH + 40
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w / 1000:.6f}in" height="{h / 1000:.6f}in" '
            f'viewBox="{x0:.0f} {y0:.0f} {w:.0f} {h:.0f}">\n'
            ' <g id="schematic">\n'
            f'  <g transform="scale({SCALE_SCH})">\n{g}\n  </g>\n'
            ' </g>\n</svg>\n')


# ---------------------------------------------------------------- breadboard
def _embed_icon(art, cx, cy, s=1.0, icx=0.0, icy=0.0):
    """把 icon 的 <g id="icon"> 内容重画到面包板坐标系（缩放 s、以 icon 的 viewBox 中心对齐 cx,cy）。
    与 svg/CH340N 同一套做法（那个版式已过用户验收）。"""
    m = re.search(r'<g\s+id="icon"([^>]*)>(.*?)</g>', art, re.S)
    if not m:
        return ""
    content = m.group(2)
    out = []
    for rm in re.finditer(r'<rect\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', rm.group(1)))
        px = (float(a.get("x", 0.0)) - icx) * s + cx
        py = (float(a.get("y", 0.0)) - icy) * s + cy
        out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s"/>\n' % (
            px, py, float(a["width"]) * s, float(a["height"]) * s,
            a.get("fill", "#f7bf13"), a.get("stroke", "none")))
    for cm in re.finditer(r'<circle\s+([^>]*?)\s*/>', content):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        px = (float(a["cx"]) - icx) * s + cx
        py = (float(a["cy"]) - icy) * s + cy
        out.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" stroke-width="%.2f"/>\n' % (
            px, py, float(a["r"]) * s, a.get("fill", "#c0c0c0"), a.get("stroke", "none"),
            float(a.get("stroke-width", 0.0)) * s))
    for tm2 in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', content, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tm2.group(1)))
        px = (float(a.get("x", 0.0)) - icx) * s + cx
        py = (float(a.get("y", 0.0)) - icy) * s + cy
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans">%s</text>\n'
                   % (px, py, fs, a.get("fill", "#333333"), tm2.group(2)))
    return "".join(out)


def gen_breadboard_svg():
    """面包板 = 绿色转接板 + **上下两排各 8 个 2.54mm 排针** + 居中本体图形（1:1，不旋转、不加装饰）。
    版式照 AGENTS §3b / svg/CH340N（已过验收），尺寸按本元件（比 SOP-8 高一倍）重算：
      · 坐标 100 单位 = 2.54mm，连接器中心全部落在 100 整数倍上（才插得进面包板孔）；
      · 排针行距 800 单位（20.32mm = 8×2.54）—— 元件含引脚总高 12.70mm 只要求 ≥14.7mm，
        其余留给**脚号**（脚号在焊盘与元件之间，行距不够就会压在元件上，实测过）；
      · 8 个排针横向跨 700 单位（17.78mm = 7×2.54），板 900×1000 单位（22.86×25.40mm）；
      · 焊盘 ⌀2mm + ⌀0.97mm 针孔（半径 1.0 / 0.485mm）。
    脚号顺序与实物丝印同向：下排 pin1..8 左→右、上排 pin16..9 左→右（即 pin1 左下、逆时针）。"""
    U = 39.37
    bw, bh = 900, 1000                  # 22.86 × 25.40mm
    bx0, by0 = 0, 0
    cx, cy = 450, 500                   # 板中心 = 元件中心
    y_top, y_bot = 100, 900             # 行距 800 单位 = 20.32mm
    pad_r, hole_r = 1.0 * U, 0.485 * U
    xs = [100 + i * 100 for i in range(8)]          # 2.54mm 网格
    icon = gen_icon_svg()
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*?</g>)\s*</svg>', icon, re.S)
    art = _m.group(1) if _m else ""
    icx = icy = 0.0                     # icon 的 viewBox 中心就在本体中心
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
         f'height="{bh / 100 * 2.54:.2f}mm" viewBox="{bx0} {by0} {bw} {bh}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}" fill="#00aa44" '
         f'stroke="#00772f" stroke-width="5"/>\n',
         _embed_icon(art, cx, cy, s=U, icx=icx, icy=icy)]
    id_of = {num: cid for cid, num, _, _, _, _ in SRA_PINS}
    bottom = ["1", "2", "3", "4", "5", "6", "7", "8"]
    top = ["16", "15", "14", "13", "12", "11", "10", "9"]
    for num, x, y in ([(n, xs[i], y_bot) for i, n in enumerate(bottom)] +
                      [(n, xs[i], y_top) for i, n in enumerate(top)]):
        cid = id_of.get(num)
        attrs = f' id="connector{cid}pin" connectorname="{esc(num)}"' if cid is not None else ""
        L.append(f'  <circle{attrs} cx="{x}" cy="{y}" r="{pad_r:.1f}" fill="#d4af37" '
                 f'stroke="#8a6d00" stroke-width="4"/>\n')
        L.append(f'  <circle cx="{x}" cy="{y}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
        # 脚号：朝板心、逆时针 90°（AGENTS §3b 的转接板数字规则），距焊盘中心 76 单位
        ty = y + 76 if y < cy else y - 76
        L.append(f'  <text x="{x}" y="{ty}" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {x} {ty})">{num}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图：16 个 RECT 焊盘（**按嘉立创封装**）—— 焊盘 **1.660(x) × 0.760(y)**、
    两列 x=±4.318（焊盘中心跨距 **8.636mm**）、每列 8 个、脚距 **1.270**、y=-4.445..4.445。
    丝印照立创：两条横线（本体宽 7.11）+ 四条竖线（长 1.25）+ pin1 圆圈（左上）。
    左列 pin1..8 上→下、右列 pin9..16 下→上（与实物丝印一致）。"""
    pads, silk = [], []
    for i in range(8):                                  # 左列 1..8
        num = str(i + 1)
        y = PAD_Y0 + i * PAD_PITCH
        cid = {n: c for c, n, _, _, _, _ in SRA_PINS}.get(num)
        attrs = f' id="connector{cid}pad" connectorname="{esc(num)}"' if cid is not None else ""
        pads.append(f'<rect{attrs} x="{-PAD_X - PAD_L / 2:.3f}" y="{y - PAD_W / 2:.3f}" '
                    f'width="{PAD_L:.3f}" height="{PAD_W:.3f}" fill="#F7BD13" stroke="none"/>')
    for i in range(8):                                  # 右列 9..16（下→上）
        num = str(9 + i)
        y = PAD_Y0 + i * PAD_PITCH
        cid = {n: c for c, n, _, _, _, _ in SRA_PINS}.get(num)
        attrs = f' id="connector{cid}pad" connectorname="{esc(num)}"' if cid is not None else ""
        pads.append(f'<rect{attrs} x="{PAD_X - PAD_L / 2:.3f}" y="{y - PAD_W / 2:.3f}" '
                    f'width="{PAD_L:.3f}" height="{PAD_W:.3f}" fill="#F7BD13" stroke="none"/>')
    hw, hh = BODY_W / 2, BODY_H / 2                     # 3.555 × 6.35
    seg = 1.25
    silk.append(f'<line x1="{-hw}" y1="{-hh}" x2="{hw}" y2="{-hh}" stroke="#f0f0f0" stroke-width="0.12"/>')
    silk.append(f'<line x1="{-hw}" y1="{hh}" x2="{hw}" y2="{hh}" stroke="#f0f0f0" stroke-width="0.12"/>')
    for sx in (-1, 1):
        for sy in (-1, 1):
            silk.append(f'<line x1="{sx * hw}" y1="{sy * hh}" x2="{sx * hw}" y2="{sy * (hh - seg)}" '
                        f'stroke="#f0f0f0" stroke-width="0.12"/>')
    silk.append('<circle cx="-2.286" cy="-4.445" r="0.635" fill="none" stroke="#f0f0f0" stroke-width="0.15"/>')
    inner = ("\n".join(pads) + "\n  </g>\n  <g id=\"silkscreen\">\n" + "\n".join(silk))
    M = 0.15
    vx0, vx1 = -(PAD_X + PAD_L / 2) - M, (PAD_X + PAD_L / 2) + M
    vy0, vy1 = -hh - M, hh + M
    vw, vh = vx1 - vx0, vy1 - vy0
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
            f'viewBox="{vx0:.2f} {vy0:.2f} {vw:.2f} {vh:.2f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """变压器图标：本体 7.11 × 12.70mm（深色）+ 左右各 8 银脚（0.76 高 × 1.2 长，
    脚距 1.27）+ pin1 圆点在左上角内 + 丝印。"""
    hw, hh = BODY_W / 2, BODY_H / 2
    out = [SVG_HDR,
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{BODY_W + 2.4:.2f}mm" height="{BODY_H + 1:.2f}mm" '
           f'viewBox="{-hw - 1.2:.2f} {-hh - 0.5:.2f} {BODY_W + 2.4:.2f} {BODY_H + 1:.2f}">\n'
           '  <g id="icon">\n']
    for i in range(8):
        y = PAD_Y0 + i * PAD_PITCH - PAD_W / 2
        out.append(f'    <rect x="{-hw - 1.2:.3f}" y="{y:.3f}" width="1.2" height="{PAD_W:.3f}" '
                   f'fill="#c0c0c0" stroke="none"/>\n')
        out.append(f'    <rect x="{hw:.3f}" y="{y:.3f}" width="1.2" height="{PAD_W:.3f}" '
                   f'fill="#c0c0c0" stroke="none"/>\n')
    out.append(f'    <rect x="{-hw:.3f}" y="{-hh:.3f}" width="{BODY_W:.2f}" height="{BODY_H:.2f}" '
               f'fill="#2b2b2b" stroke="none"/>\n')
    out.append('    <circle cx="-2.286" cy="-4.445" r="0.635" fill="none" stroke="#c0c0c0" stroke-width="0.2"/>\n')
    out.append(f'    <text x="0" y="0.5" font-size="1.3" fill="#ffffff" text-anchor="middle" '
               f'font-family="DroidSans">{ICON_LABEL}</text>\n')
    out.append('  </g>\n</svg>\n')
    return "".join(out)


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for cid, num, name, _, _, _ in SRA_PINS:
        conns.append(
            f'  <connector id="connector{cid}" name="{esc(name)}" type="male">\n'
            f'   <description>pin {num} = {esc(name)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cid}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{cid}pin" terminalId="connector{cid}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{cid}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>1</version>\n <date>2026-09-17</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>H1102NLT</tag>\n  <tag>transformer</tag>\n'
            f'  <tag>magnetics</tag>\n  <tag>10/100Base-T</tag>\n  <tag>ethernet</tag>\n  <tag>Pulse</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">12 (4/5/12/13 = NC)</property>\n'
            f'  <property name="turns ratio">TX 1:1 / RX 1:1</property>\n </properties>\n'
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
