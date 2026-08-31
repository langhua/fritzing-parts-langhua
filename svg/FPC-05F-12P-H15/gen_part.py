#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_part.py — FPC-05F-12P-H15（FFC/FPC 连接器 0.5mm/12P，翻盖式/前翻，下接，H1.5）。

封装（mm）：
  - 间距 0.5mm，12 脚 → 接触中心跨距 5.5mm
  - 本体 10.1 × 4.1（长×深），高 1.5（H1.5）
视图模型：
  - icon = 顶视（白色壳 + 12 金触点 + 翻盖条 + 12P 标签）
  - 面包板 = 同封装 + 12 个可连线焊盘
  - 原理图 = 矩形符号 + 左 12 脚
  - PCB = 0.5 间距 12 焊盘 + 2 安装焊盘 + 丝印外形
坐标单位 mm；icon/面包板画布裁到内容。
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "FPC-05F-12P-H15"
FZPZ = "FPC-05F-12P-H15.fzpz"
TITLE = "FFC/FPC Connector 0.5mm 12P front-flip bottom-contact H1.5"
LABEL = "J"
PITCH = 0.5
N = 12
SPAN = (N - 1) * PITCH          # 5.5
BODY_L, BODY_W = 10.1, 4.1      # 本体长×宽（翻盖关闭后整体宽 4.1）
PAD_W, PAD_H = 0.3, 0.8         # 焊盘宽 0.3、露出 0.8（比引脚多露出 0.3）
PIN_W, PIN_H = 0.2, 0.5         # 引脚宽 0.2、露出 0.5
FLIP_L, FLIP_W = 6.57, 1.1      # 黑色翻盖：沿长度 6.57、沿深度宽 1.1（>0.8）

# 内容范围（icon/面包板）：x ±5.05, y -2.85..2.05（银焊盘在上缘露出 0.8、引脚露出 0.5）
X0, X1 = -BODY_L / 2.0, BODY_L / 2.0
Y0, Y1 = -BODY_W / 2.0 - PAD_H, BODY_W / 2.0
CW, CH = X1 - X0, Y1 - Y0


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _cx():
    return [-SPAN / 2.0 + i * PITCH for i in range(N)]


def gen_icon_svg():
    """icon = 顶视：白色直角本体 10.1×4.1mm + 12 金焊盘（宽 0.3、露出 0.8，上缘）+
    12 金属银引脚（宽 0.2、露出 0.5，叠在焊盘内侧）+ 黑色直角翻盖（长 6.57、宽 1.1，下缘）。"""
    s = []
    s.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW:.2f}mm" height="{CH:.2f}mm" '
             f'viewBox="{X0:.2f} {Y0:.2f} {CW:.2f} {CH:.2f}">\n')
    s.append(' <g id="icon">\n')
    # 本体（白色壳，直角）
    s.append(f'  <rect x="{X0:.2f}" y="{Y0 + PAD_H:.2f}" width="{BODY_L:.2f}" height="{BODY_W:.2f}" '
             f'fill="#f2f2f2" stroke="#9a9a9a" stroke-width="0.08"/>\n')
    # 12 金焊盘（上缘露出 0.8；宽 0.3，中心 -2.75..2.75 跨 5.5）
    for i, x in enumerate(_cx()):
        s.append(f'  <rect x="{x - PAD_W / 2:.2f}" y="{Y0:.2f}" width="{PAD_W:.2f}" height="{PAD_H:.2f}" '
                 f'fill="#f7bf13" stroke="none"/>\n')
    # 12 银引脚（叠在焊盘内侧，露出 0.5；宽 0.2）
    for i, x in enumerate(_cx()):
        s.append(f'  <rect x="{x - PIN_W / 2:.2f}" y="{Y0 + PAD_H - PIN_H:.2f}" width="{PIN_W:.2f}" height="{PIN_H:.2f}" '
                 f'fill="#c9c9c9" stroke="none"/>\n')
    # 黑色翻盖（沿长度 6.57 居中、沿深度宽 1.1，贴下缘，直角）
    s.append(f'  <rect x="{-FLIP_L / 2:.2f}" y="{BODY_W / 2 - FLIP_W:.2f}" width="{FLIP_L:.2f}" height="{FLIP_W:.2f}" '
             f'fill="#2b2b2b" stroke="none"/>\n')
    # 12P 标签
    s.append(f'  <text x="0.00" y="{-1.2:.2f}" font-size="0.9" fill="#666666" text-anchor="middle" '
             f'font-family="DroidSans">12P</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def _rot_embed(art, cx, cy, s=39.37):
    """把 icon 组内容（mm，内容中心非 0,0）绕自身中心顺时针转 90°、放大 s、居中于 (cx,cy)。
    烘焙绝对坐标，避免 Fritzing 中 rotate 变换导致错位；FPC icon 内容中心 y=-0.4。"""
    rects, texts = [], []
    minx = miny = float('inf')
    maxx = maxy = float('-inf')
    for m in re.finditer(r'<rect\s+([^>]*?)\s*/>', art):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        rx, ry = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        rw, rh = float(a["width"]), float(a["height"])
        rects.append((rx, ry, rw, rh, a))
        minx, miny = min(minx, rx), min(miny, ry)
        maxx, maxy = max(maxx, rx + rw), max(maxy, ry + rh)
    for m in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', art, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        tx, ty = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        texts.append((tx, ty, a, m.group(2)))
        minx, miny = min(minx, tx), min(miny, ty)
        maxx, maxy = max(maxx, tx), max(maxy, ty)
    if not rects and not texts:
        return ""
    ccx, ccy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    out = []
    for rx, ry, rw, rh, a in rects:
        dx, dy = rx - ccx, ry - ccy
        nx, ny = dy, -dx - rw          # 顺时针 90°
        x, y = cx + nx * s, cy + ny * s
        w, h = rh * s, rw * s
        attrs = '  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"' % (x, y, w, h)
        if "rx" in a:
            attrs += ' rx="%.2f" ry="%.2f"' % (float(a["rx"]) * s, float(a["ry"]) * s)
        attrs += ' fill="%s" stroke="%s"' % (a.get("fill", "#f7bf13"), a.get("stroke", "none"))
        if float(a.get("stroke-width", 0)) > 0:
            attrs += ' stroke-width="%.2f"' % (float(a["stroke-width"]) * s)
        out.append(attrs + '/>\n')
    for tx, ty, a, content in texts:
        dx, dy = tx - ccx, ty - ccy
        nx, ny = dy, -dx
        x, y = cx + nx * s, cy + ny * s
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans" '
                   'transform="rotate(90 %.2f %.2f)">%s</text>\n'
                   % (x, y, fs, a.get("fill", "#333333"), x, y, content))
    return "".join(out)


def _embed(art, cx, cy, s=39.37):
    """把 icon 组内容（mm，内容中心非 0,0）放大 s、居中于 (cx,cy)，不旋转（横放）。
    烘焙绝对坐标，避免 Fritzing 中 transform 错位。"""
    rects, texts = [], []
    minx = miny = float('inf')
    maxx = maxy = float('-inf')
    for m in re.finditer(r'<rect\s+([^>]*?)\s*/>', art):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        rx, ry = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        rw, rh = float(a["width"]), float(a["height"])
        rects.append((rx, ry, rw, rh, a))
        minx, miny = min(minx, rx), min(miny, ry)
        maxx, maxy = max(maxx, rx + rw), max(maxy, ry + rh)
    for m in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', art, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        tx, ty = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        texts.append((tx, ty, a, m.group(2)))
        minx, miny = min(minx, tx), min(miny, ty)
        maxx, maxy = max(maxx, tx), max(maxy, ty)
    if not rects and not texts:
        return ""
    ccx, ccy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    out = []
    for rx, ry, rw, rh, a in rects:
        x, y = cx + (rx - ccx) * s, cy + (ry - ccy) * s
        w, h = rw * s, rh * s
        attrs = '  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"' % (x, y, w, h)
        if "rx" in a:
            attrs += ' rx="%.2f" ry="%.2f"' % (float(a["rx"]) * s, float(a["ry"]) * s)
        attrs += ' fill="%s" stroke="%s"' % (a.get("fill", "#f7bf13"), a.get("stroke", "none"))
        if float(a.get("stroke-width", 0)) > 0:
            attrs += ' stroke-width="%.2f"' % (float(a["stroke-width"]) * s)
        out.append(attrs + '/>\n')
    for tx, ty, a, content in texts:
        x, y = cx + (tx - ccx) * s, cy + (ty - ccy) * s
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans">%s</text>\n'
                   % (x, y, fs, a.get("fill", "#333333"), content))
    return "".join(out)


def gen_breadboard_svg():
    """面包板 = 真实打样转接板（0.5座转2.54双排针）：FPC 座横放 + 2×6 双排针并排 + 丝印。
    坐标 100 单位 = 2.54mm（Fritzing 约定），排针中心落在 100 单位整数倍 → 对准面包板孔。
    板 600×700 单位 = 15.24×17.78mm；FPC 座横放底部(300,540)，焊盘朝上；
    双排针并排顶部：上排 connector0..5 y=100 / 下排 connector6..11 y=200（x=50..550）；
    丝印：中央 FPC-12P 0.5MM、底部 J1、大字号引脚号 1-12 在排针上下两侧。"""
    U = 39.37
    bw, bh = 600, 700
    fcx, fcy = 300, 540
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*</g>)\s*</svg>', gen_icon_svg(), re.S)
    art = re.sub(r'\s+id="[^"]*"', '', _m.group(1)) if _m else ""
    pad_r = 1.0 * U                  # 2mm 直径焊盘 → 半径 1mm
    hole_r = 0.485 * U               # 0.97mm 直径针孔 → 半径 0.485mm
    xs = [50 + i * 100 for i in range(6)]
    dy = -0.4 * U                    # 板上移 0.4mm = -15.75 单位
    vh = bh - dy                     # viewBox 高度 715.75（板上移后仍完整可见）
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" height="{vh / 100 * 2.54:.2f}mm" '
             f'viewBox="0 {dy:.2f} {bw} {vh:.2f}">\n')
    s.append(' <g id="breadboard">\n')
    # 绿色转接板（直角，完整可见且整体上移 0.4mm；其它元件坐标不动）
    s.append(f'  <rect x="0" y="{dy:.2f}" width="{bw}" height="{bh}" '
             f'fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    # FPC 座（icon 横放 1:1，居中底部，焊盘朝上）
    s.append(_embed(art, fcx, fcy, s=U))
    # 2×6 双排针：上排 connector0..5 y=100、下排 connector6..11 y=200；x=50..550
    for i, px in enumerate(xs):
        s.append(f'  <circle id="connector{i}pin" cx="{px:.1f}" cy="100.0" r="{pad_r:.1f}" '
                 f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        s.append(f'  <circle cx="{px:.1f}" cy="100.0" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    for i, px in enumerate(xs):
        j = i + 6
        s.append(f'  <circle id="connector{j}pin" cx="{px:.1f}" cy="200.0" r="{pad_r:.1f}" '
                 f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        s.append(f'  <circle cx="{px:.1f}" cy="200.0" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    # 丝印：中央 FPC-12P、引脚号上下交替（1右下/2右上/3左下…旋转90°竖排），
    # 数字 x 中心 = 焊盘 x 中心，数字在焊盘上边(y=25)/下边(y=270)、不与焊盘重叠
    s.append(f'  <text x="300" y="380" font-size="54" fill="#ffffff" text-anchor="middle" '
             f'font-family="DroidSans">FPC-12P 0.5MM</text>\n')
    # 上排（偶数 2,4,6,8,10,12）：x=焊盘中心从右到左（550..50），y=25（焊盘顶 60.6 上方），旋转90°；
    # dominant-baseline=central 使文字垂直中心=y，旋转后 x 中心=焊盘 x 中心
    for px, num in zip(reversed(xs), [2, 4, 6, 8, 10, 12]):
        s.append(f'  <text x="{px:.1f}" y="25" font-size="46" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" transform="rotate(90 {px:.1f} 25)" '
                 f'font-family="DroidSans">{num}</text>\n')
    # 下排（奇数 1,3,5,7,9,11）：x=焊盘中心从右到左（550..50），y=270（焊盘底 239.4 下方），旋转90°
    for px, num in zip(reversed(xs), [1, 3, 5, 7, 9, 11]):
        s.append(f'  <text x="{px:.1f}" y="270" font-size="46" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" transform="rotate(90 {px:.1f} 270)" '
                 f'font-family="DroidSans">{num}</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def gen_schematic_svg():
    """原理图符号：完全采用 FPC05-2H10PX 参考几何（viewBox 204.49×1173.05，12 引脚间距 100）。
    宽度/高度带 in 单位（1000 单位=1in，同参考）：宽 5.194mm、高 29.795mm（参考 10 脚 24.715mm 高 +2脚5.08mm）。
    每引脚 = connectorNpin 左线 + connectorNterminal + 箭头 polyline + 右线 line + 编号。"""
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append('<svg xmlns="http://www.w3.org/2000/svg" width="0.20448959in" height="1.17305in" '
             'viewBox="0 0 204.48965 1173.05">\n')
    s.append(' <g id="schematic">\n')
    for i in range(N):
        y = 38.9544 + i * 100
        # 左线（可连线 connectorNpin）
        s.append(f'  <line class="pin" id="connector{i}pin" connectorname="{i}" '
                 f'x1="8.6529312" y1="{y:.4f}" x2="107.55747" y2="{y:.4f}" '
                 f'stroke="#000000" stroke-width="9.72223" stroke-linecap="round" stroke-linejoin="round"/>\n')
        # terminal
        s.append(f'  <rect id="connector{i}terminal" x="0" y="{y - 1.333:.4f}" '
                 f'width="7.5834675" height="2.8889401" fill="none"/>\n')
        # 箭头 polyline（尖端朝右，变换同参考）
        mid = 3.6 + i * 7.2
        s.append(f'  <polyline points="9.898,{mid - 1.957:.3f} 14.1,{mid:.1f} 9.898,{mid + 1.956:.3f}" '
                 f'stroke="#000000" stroke-width="0.699988" stroke-linecap="round" stroke-linejoin="round" '
                 f'fill="none" transform="matrix(13.889135,0,0,13.889129,3.7917338,-11.046493)"/>\n')
        # 右线 line
        s.append(f'  <line stroke="#000000" x1="199.62854" y1="{y:.4f}" x2="70.195686" y2="{y:.4f}" '
                 f'stroke-width="9.72223" stroke-linecap="round" stroke-linejoin="round"/>\n')
        # 编号（在线上方，居中对齐右线起点附近）
        s.append(f'  <text x="75" y="{y - 14:.1f}" font-size="20" fill="#8c8c8c" text-anchor="middle" '
                 f'font-family="DroidSans">{i + 1}</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def gen_pcb_svg():
    """推荐 PCB 焊盘布局（按用户数据，mm）：
    - 12 小焊盘 0.3×0.9，间距 0.5（中心跨 ±2.75），位于上部 y 3.15..4.05
    - 2 大焊盘 1.1×1.8，中心 x ±4.9（外缘 ±5.45，距最外侧小焊盘中心 2.7），位于下部 y 0..1.8
    - 丝印：方框尺寸不变（高 4.4，x ±5.20，y -1.15..3.25），但**分成多段**避开焊盘：
      顶边整段；左右侧边在大焊盘处断开；底边在小焊盘处断开；每段与焊盘留 0.1mm 安全距离。"""
    MP = 4.9                     # 大焊盘中心 x
    MPW, MPH = 1.1, 1.8          # 大焊盘 1.1×1.8
    PW, PH = 0.3, 0.9            # 小焊盘 0.3×0.9
    PAD_Y = 3.15                 # 小焊盘底部 y（顶部 4.05）
    # 丝印方框（尺寸不变）：高 4.4，底边 = 小焊盘露出 0.8 → 3.25，侧边 = 小焊盘外缘向外 2.3 → ±5.20
    SS_H = 4.4
    SS_BOT = PAD_Y + PH - 0.8    # 3.25（底边）
    SS_TOP = SS_BOT - SS_H       # -1.15（顶边）
    SS_HALF = 2.90 + 2.3         # 5.20（左右侧边）
    GAP = 0.1                    # 丝印与焊盘的安全距离
    big_top, big_bot = 0.0, 1.8  # 大焊盘 y 范围
    small_edge = 2.90            # 最外侧小焊盘外缘
    # 分段的丝印轮廓（7 段，避开大小焊盘）
    path = ' '.join([
        f'M {-SS_HALF:.2f} {SS_TOP:.2f} L {SS_HALF:.2f} {SS_TOP:.2f}',                   # 顶边
        f'M {SS_HALF:.2f} {SS_TOP:.2f} L {SS_HALF:.2f} {big_top - GAP:.2f}',             # 右边上段
        f'M {SS_HALF:.2f} {big_bot + GAP:.2f} L {SS_HALF:.2f} {SS_BOT:.2f}',             # 右边下段
        f'M {SS_HALF:.2f} {SS_BOT:.2f} L {small_edge + GAP:.2f} {SS_BOT:.2f}',           # 底边右段
        f'M {-small_edge - GAP:.2f} {SS_BOT:.2f} L {-SS_HALF:.2f} {SS_BOT:.2f}',         # 底边左段
        f'M {-SS_HALF:.2f} {SS_BOT:.2f} L {-SS_HALF:.2f} {big_bot + GAP:.2f}',           # 左边下段
        f'M {-SS_HALF:.2f} {big_top - GAP:.2f} L {-SS_HALF:.2f} {SS_TOP:.2f}',           # 左边上段
    ])
    vx = -5.65
    vy = SS_TOP - 0.30           # viewBox 顶部留 0.3 边距
    vw = 11.30
    vh = (PAD_Y + PH + 0.30) - vy   # 底部小焊盘顶 4.05 + 0.3 边距 → 5.80
    s = []
    s.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
             f'viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}">\n')
    s.append(' <g id="copper1">\n')
    # 12 小焊盘（信号，可连线 connector0..11）
    for i, x in enumerate(_cx()):
        s.append(f'  <rect id="connector{i}pad" x="{x - PW / 2:.3f}" y="{PAD_Y:.2f}" '
                 f'width="{PW:.2f}" height="{PH:.2f}" fill="#F7BD13" stroke="none"/>\n')
    # 2 大焊盘（机械安装，不连线）
    for sx in (-MP, MP):
        s.append(f'  <rect x="{sx - MPW / 2:.3f}" y="0.0" width="{MPW:.2f}" height="{MPH:.2f}" '
                 f'fill="#F7BD13" stroke="none"/>\n')
    s.append('  <g id="silkscreen">\n')
    s.append(f'   <path d="{path}" fill="none" stroke="#f0f0f0" stroke-width="0.08"/>\n')
    s.append('  </g>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def gen_fzp():
    conns = []
    for cn in range(N):
        name = str(cn + 1)
        conns.append('  <connector id="connector%d" name="%s" type="male">\n' % (cn, name))
        conns.append('   <description>pad %s</description>\n' % name)
        conns.append('   <views>\n')
        conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n' % cn)
        conns.append('    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n' % (cn, cn))
        conns.append('    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n' % cn)
        conns.append('   </views>\n')
        conns.append('  </connector>\n')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="1.0.3" moduleId="%s">\n'
        ' <version>1</version>\n <date>2026-08-31</date>\n'
        ' <label>%s</label>\n <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <tags><tag>fpc</tag><tag>connector</tag><tag>0.5mm</tag></tags>\n'
        ' <properties>\n'
        '  <property name="package">FPC-05F-12P-H15</property>\n'
        '  <property name="family">connector</property>\n'
        '  <property name="pitch">0.5mm</property>\n'
        '  <property name="pins">12</property>\n'
        '  <property name="height">1.5mm</property>\n'
        ' </properties>\n'
        ' <views>\n'
        '  <iconView><layers image="icon/%s_icon.svg"><layer layerId="icon"/></layers></iconView>\n'
        '  <breadboardView fliphorizontal="true" flipvertical="true"><layers image="breadboard/%s_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true"><layers image="schematic/%s_schematic.svg"><layer layerId="schematic"/></layers></schematicView>\n'
        '  <pcbView><layers image="pcb/%s_pcb.svg"><layer layerId="copper1"/><layer layerId="silkscreen"/></layers></pcbView>\n'
        ' </views>\n'
        ' <connectors>\n%s</connectors>\n'
        '</module>\n'
    ) % (PART_ID, LABEL, TITLE, PART_ID, PART_ID, PART_ID, PART_ID, "".join(conns))


def main():
    files = {
        "icon": gen_icon_svg(),
        "breadboard": gen_breadboard_svg(),
        "schematic": gen_schematic_svg(),
        "pcb": gen_pcb_svg(),
        "fzp": gen_fzp(),
    }
    for view, content in files.items():
        name = ("part.%s.fzp" % PART_ID) if view == "fzp" else ("svg.%s.%s_%s.svg" % (view, PART_ID, view))
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        for view, content in files.items():
            name = ("part.%s.fzp" % PART_ID) if view == "fzp" else ("svg.%s.%s_%s.svg" % (view, PART_ID, view))
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
