#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_part.py — Crystal-3225（3.2×2.5mm SMD 石英晶振，4 焊盘；按封装尺寸定义，同尺寸多频通用）。

接线（datasheet）：脚 1、3 为晶片有效脚（原理图只出 1、3）；脚 2、4 接金属外壳 → 原理图 NC。
焊盘布局（SOLDER PAD LAYOUT）：四焊盘 2×2，横向中心距 2.2mm，纵向中心距 1.5mm，焊盘 1.1×1.2mm。
视图模型：
  - icon = 3225 封装俯视（银灰体 + 2×2 金焊盘 + 频率标签）
  - 面包板 = 同封装 + 4 个可连线焊盘
  - 原理图 = 标准晶振符号（方框 + 两条晶片竖线），只出脚 1（左）/ 脚 3（右）
  - PCB = 3225 焊盘 footprint（2×2，1/3 有效、2/4 NC）
坐标单位 mm；icon/面包板画布裁到内容。
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "Crystal-3225"
FZPZ = "Crystal-3225.fzpz"
TITLE = "Crystal 3225 (3.2x2.5mm SMD)"
LABEL = "Y"

# 封装尺寸（mm）
L, W = 3.2, 2.5                 # 本体
PAD_W, PAD_H = 1.1, 1.2         # 焊盘 1.1×1.2（datasheet）
PITCH_X, PITCH_Y = 2.2, 1.5     # 横向/纵向中心距
PX, PY = PITCH_X / 2.0, PITCH_Y / 2.0

# 焊盘（连接器顺序）：0=脚1 左上, 1=脚2 右上(NC), 2=脚3 右下, 3=脚4 左下(NC)
# 注意：rect 以中心为基准放置（x=中心-宽/2），否则焊盘会整体偏移导致本体/焊盘错位
PADS = [
    (-PX - PAD_W/2.0, -PY - PAD_H/2.0, PAD_W, PAD_H),  # 0 脚1 左上
    (+PX - PAD_W/2.0, -PY - PAD_H/2.0, PAD_W, PAD_H),  # 1 脚2 右上 NC
    (+PX - PAD_W/2.0, +PY - PAD_H/2.0, PAD_W, PAD_H),  # 2 脚3 右下
    (-PX - PAD_W/2.0, +PY - PAD_H/2.0, PAD_W, PAD_H),  # 3 脚4 左下 NC
]

# 内容范围（icon/面包板/PCB viewBox 裁到内容）
X0, X1 = -PX - PAD_W / 2.0, +PX + PAD_W / 2.0   # -1.65..1.65
Y0, Y1 = -PY - PAD_H / 2.0, +PY + PAD_H / 2.0   # -1.35..1.35
CW, CH = X1 - X0, Y1 - Y0                        # 3.30 × 2.70


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def body_geo():
    return (-L / 2.0, -W / 2.0, L, W)


def _rot_embed(art, cx, cy, s=1.0):
    """把 icon 组内容（mm，绕自身中心 0,0）顺时针转 90°、放大 s、居中于 (cx,cy)。
    烘焙绝对坐标，避免 Fritzing 中 rotate 变换导致错位。"""
    out = []
    for m in re.finditer(r'<rect\s+([^>]*?)\s*/>', art):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        rx, ry = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        rw, rh = float(a["width"]), float(a["height"])
        x = cx + ry * s
        y = cy + (-rx - rw) * s
        w, h = rh * s, rw * s
        attrs = '  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"' % (x, y, w, h)
        if "rx" in a:
            attrs += ' rx="%.2f" ry="%.2f"' % (float(a["rx"]) * s, float(a["ry"]) * s)
        attrs += ' fill="%s" stroke="%s"' % (a.get("fill", "#f7bf13"), a.get("stroke", "none"))
        if float(a.get("stroke-width", 0)) > 0:
            attrs += ' stroke-width="%.2f"' % (float(a["stroke-width"]) * s)
        out.append(attrs + '/>\n')
    for m in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', art, re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        tx2, ty2 = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        x = cx + ty2 * s
        y = cy + (-tx2) * s
        fs = float(a.get("font-size", 0.9)) * s
        out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" '
                   'dominant-baseline="central" font-family="DroidSans" '
                   'transform="rotate(90 %.2f %.2f)">%s</text>\n'
                   % (x, y, fs, a.get("fill", "#333333"), x, y, m.group(2)))
    return "".join(out)


def gen_icon_svg():
    bx, by, bw, bh = body_geo()
    s = []
    s.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW:.2f}mm" height="{CH:.2f}mm" '
             f'viewBox="{X0:.2f} {Y0:.2f} {CW:.2f} {CH:.2f}">\n')
    s.append(' <g id="icon">\n')
    # 焊盘（金，2×2）
    for x, y, w, h in PADS:
        s.append(f'  <rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#f7bf13" stroke="none"/>\n')
    # 本体（银灰，带圆角）
    s.append(f'  <rect x="{bx:.2f}" y="{by:.2f}" width="{bw:.2f}" height="{bh:.2f}" rx="0.25" ry="0.25" '
             f'fill="#d9d9d9" stroke="#8a8a8a" stroke-width="0.08"/>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def gen_breadboard_svg():
    """面包板 = 绿色 PCB 转接板 + 4 排针（上下各二）。
    坐标 100 单位 = 2.54mm（Fritzing 面包板约定），排针落在 100 单位整数倍 → 对准面包板孔。
    板 200×500 单位 = 5.08×12.7mm（2mm 焊盘与晶振不冲突）；元件用自身 icon（1:1 竖放居中）。"""
    U = 39.37
    bw, bh = 200, 500
    cx, cy = 100, 250
    _m = re.search(r'(<g\s+id="icon"[^>]*>.*</g>)\s*</svg>', gen_icon_svg(), re.S)
    art = re.sub(r'\s+id="[^"]*"', '', _m.group(1)) if _m else ""
    pad_r = 1.0 * U                  # 2mm 直径焊盘 → 半径 1mm
    hole_r = 0.485 * U               # 0.97mm 直径针孔 → 半径 0.485mm
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw/100*2.54:.2f}mm" height="{bh/100*2.54:.2f}mm" '
             f'viewBox="0 0 {bw} {bh}">\n')
    s.append(' <g id="breadboard">\n')
    # 绿色转接板（直角）
    s.append(f'  <rect x="0" y="0" width="{bw}" height="{bh}" '
             f'fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n')
    # 自身 icon（1:1 竖放居中，mm→单位 ×39.37）
    s.append(_rot_embed(art, cx, cy, s=U))
    # 4 个排针（上 connector0/1 y=100、下 connector2/3 y=400；x=50/150，行距 300=3×100=7.62mm，避开 2mm 焊盘）
    for i, (px, py) in enumerate(((50, 100), (150, 100), (150, 400), (50, 400))):
        s.append(f'  <circle id="connector{i}pin" cx="{px:.1f}" cy="{py:.1f}" r="{pad_r:.1f}" '
                 f'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n')
        s.append(f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def gen_schematic_svg():
    """晶振原理图符号：直接复用 Fritzing 官方 core crystal.svg 几何（viewBox 15.1×10.8），
    与官方晶振元件同尺寸同比例；只出脚 1（左）/ 脚 3（右），脚 2、4 NC。
    绘制顺序同官方：先灰线（引脚）后黑线（本体），黑线压灰线。"""
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>\n')
    s.append('<svg xmlns="http://www.w3.org/2000/svg" width="15.1" height="10.8" viewBox="0 0 15.1 10.8">\n')
    s.append(' <g id="schematic">\n')
    # 先灰线（引脚导线，脚 1 / 脚 3）+ 端子
    s.append('  <line class="pin" id="connector0pin" connectorname="0" x1="0.35" y1="5.4" x2="4.67" y2="5.4" '
             'stroke="#8c8c8c" stroke-width="0.75" stroke-linecap="round"/>\n')
    s.append('  <rect class="terminal" id="connector0terminal" x="0.35" y="5.4" width="0.0001" height="0.0001" fill="none"/>\n')
    s.append('  <line class="pin" id="connector2pin" connectorname="2" x1="10.43" y1="5.4" x2="14.75" y2="5.4" '
             'stroke="#8c8c8c" stroke-width="0.75" stroke-linecap="round"/>\n')
    s.append('  <rect class="terminal" id="connector2terminal" x="14.75" y="5.4" width="0.0001" height="0.0001" fill="none"/>\n')
    # 后黑线（本体：左片 / 方框 / 右片），黑线压灰线
    s.append('  <line x1="4.67" y1="0.36" x2="4.67" y2="10.44" stroke="#000000" stroke-width="0.9" stroke-linecap="round"/>\n')
    s.append('  <line x1="6.47" y1="1.08" x2="6.47" y2="9.72" stroke="#000000" stroke-width="0.9" stroke-linecap="round"/>\n')
    s.append('  <line x1="6.47" y1="9.72" x2="8.63" y2="9.72" stroke="#000000" stroke-width="0.9" stroke-linecap="round"/>\n')
    s.append('  <line x1="8.63" y1="9.72" x2="8.63" y2="1.08" stroke="#000000" stroke-width="0.9" stroke-linecap="round"/>\n')
    s.append('  <line x1="8.63" y1="1.08" x2="6.47" y2="1.08" stroke="#000000" stroke-width="0.9" stroke-linecap="round"/>\n')
    s.append('  <line x1="10.43" y1="0.36" x2="10.43" y2="10.44" stroke="#000000" stroke-width="0.9" stroke-linecap="round"/>\n')
    # 引脚编号（导线上方，不被导线穿过；字体字号同官方）
    s.append('  <text x="1.5364" y="4.3486" font-size="2.5" fill="#8c8c8c" font-family="Noto Sans">1</text>\n')
    s.append('  <text x="12.4036" y="4.3486" font-size="2.5" fill="#8c8c8c" font-family="Noto Sans">3</text>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def gen_pcb_svg():
    """3225 PCB footprint（datasheet 焊盘布局）：copper1 4 焊盘（2×2）+ 丝印外形（方框在焊盘之外）。"""
    s = []
    s.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    sx, sy = X0 - 0.15, Y0 - 0.15
    sw, sh = (X1 - X0) + 0.30, (Y1 - Y0) + 0.30
    vx, vy = X0 - 0.30, Y0 - 0.30
    vw, vh = (X1 - X0) + 0.60, (Y1 - Y0) + 0.60
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
             f'viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}">\n')
    s.append(' <g id="copper1">\n')
    for i, (x, y, w, h) in enumerate(PADS):
        s.append(f'  <rect id="connector{i}pad" x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                 f'fill="#F7BD13" stroke="none"/>\n')
    s.append('  <g id="silkscreen">\n')
    s.append(f'   <rect x="{sx:.2f}" y="{sy:.2f}" width="{sw:.2f}" height="{sh:.2f}" fill="none" '
             f'stroke="#f0f0f0" stroke-width="0.08"/>\n')
    s.append('  </g>\n')
    s.append(' </g>\n</svg>\n')
    return "".join(s)


def gen_fzp():
    conns = []
    names = ["1", "2", "3", "4"]
    schem = {0, 2}  # 脚 1、3 出原理图；脚 2、4 NC（只出面包板/PCB 焊盘）
    for cn, name in enumerate(names):
        conns.append('  <connector id="connector%d" name="%s" type="male">\n' % (cn, name))
        conns.append('   <description>pad %s</description>\n' % name)
        conns.append('   <views>\n')
        conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n' % cn)
        if cn in schem:
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
        ' <tags><tag>crystal</tag><tag>3225</tag><tag>SMD</tag></tags>\n'
        ' <properties>\n'
        '  <property name="package">3225</property>\n'
        '  <property name="family">crystal</property>\n'
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
