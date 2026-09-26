#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 SS34 (3A 40V 肖特基二极管, DO-214AC/SMA)。

四个视图（AGENTS.md §2 元件工作流）：icon → breadboard → schematic → pcb。

数据来源
========
1) 器件手册 `D:\\Downloads\\SS34.pdf`（SS32 THRU SS3200 系列）：
   · 封装 **DO-214AC / SMA**、单极（Unipolar）、Forward Current 3.0A；
   · 第 1 页 PINNING 表：**pin1 = Cathode（阴极 = 彩色带那一端）、pin2 = Anode（阳极）**。
2) **嘉立创封装**（用户 2026-09-17 提供 `D:\\Downloads\\SS34_pcb_2026-09-17.svg`）：
   两个 RECT 焊盘 **1.524(x) × 2.540(y)**、中心距 **4.48mm**（相对本体中心 ±2.24）；
   丝印 = 外框 6.63×3.05 + 三角形 + 阴极竖带 + 两条引出短线。**PCB 焊盘尺寸/间距按立创**。
3) **嘉立创原理图符号**（`D:\\Downloads\\SS34_2026-09-17.svg`）：只作参考（它是蓝线 + Times New
   Roman）。原理图按**仓库规范**画：深色二极管符号 + 灰引脚线（#787878 / width 5）+
   灰编号（#8C8C8C，字号 35）+ 极小不可见 terminal，口径同 svg/BAT54S 与 AGENTS §5
   「原理图引脚端点 / terminal 画法」；物理尺寸用 in（1000 单位 = 1in）。

⚠ 两处与立创原图**不同**的取舍（都已在正文注释里标出）：
   · **脚号的左右**：立创把 `number=1` 的焊盘摆在**左边**、而丝印的三角/带指向**右侧阴极** ——
     两者自相矛盾。手册明确 **pin1 = Cathode**，故本元件按手册：**pin1(K) 在左**、
     丝印的阴极带也画在左（即把立创那幅丝印左右镜像）。
   · 原理图同理：pin1(K) 在左，三角尖朝左（电流 A→K）。

用法：python gen_part.py
"""
import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "SS34"
FZPZ = "SS34.fzpz"

# connector id / 脚号 / 网名（pin1 = K 阴极、pin2 = A 阳极，见手册 PINNING）
CONN = [(0, "1", "K", "Cathode"), (1, "2", "A", "Anode")]

ICON_LABEL = "SS34"
TITLE = "SS34 Schottky Diode (DO-214AC / SMA)"
LABEL = "D"
PACKAGE = "DO-214AC (SMA)"
FAMILY = "Schottky Diode"

# ---- 几何（mm）--------------------------------------------------------------
BODY_W, BODY_H = 4.32, 2.62       # DO-214AC 本体（JEDEC，手册 Mechanical Data）
PAD_W, PAD_H = 1.524, 2.540       # 焊盘（立创实测）
PAD_DX = 2.24                     # 焊盘中心到本体中心（立创实测，中心距 4.48）
SILK_W, SILK_H = 6.63, 3.05       # 丝印外框（立创）
BAND_W = 0.60                     # 阴极带宽度（icon 上画的那条）
BAND_X = -BODY_W / 2 + 0.55       # 阴极带中心 x（左侧 = pin1/K 那一端）

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- SS34 -->\n'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------- icon
def gen_icon_svg():
    """SMA 顶视图：深色本体 4.32×2.62 + 两端银色焊盘 + **左端阴极带** + 丝印名。"""
    hw, hh = BODY_W / 2.0, BODY_H / 2.0
    x0, x1 = -(PAD_DX + PAD_W / 2), PAD_DX + PAD_W / 2
    y0, y1 = -PAD_H / 2, PAD_H / 2
    L = [SVG_HDR,
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0:.2f}mm" height="{PAD_H:.2f}mm" '
         f'viewBox="{x0 - 0.2:.2f} {y0:.2f} {x1 - x0 + 0.4:.2f} {PAD_H:.2f}">\n',
         '  <g id="icon">\n']
    for sx in (-1, 1):                                     # 两个焊盘
        L.append(f'    <rect x="{sx * PAD_DX - PAD_W / 2:.3f}" y="{y0:.3f}" width="{PAD_W:.3f}" '
                 f'height="{PAD_H:.3f}" fill="#c0c0c0" stroke="none"/>\n')
    L.append(f'    <rect x="{-hw:.3f}" y="{-hh:.3f}" width="{BODY_W:.2f}" height="{BODY_H:.2f}" '
             f'fill="#2b2b2b" stroke="none"/>\n')
    L.append(f'    <rect x="{BAND_X - BAND_W / 2:.3f}" y="{-hh:.3f}" width="{BAND_W:.2f}" '
             f'height="{BODY_H:.2f}" fill="#e8e8e8" stroke="none"/>\n')
    L.append(f'    <text x="0" y="0.45" font-size="1.05" fill="#d0d0d0" text-anchor="middle" '
             f'font-family="DroidSans">{ICON_LABEL}</text>\n')
    L.append('  </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = 绿色 SMA 转接板（AGENTS §3b）：本体横放居中 + **左右各 1 个 2.54mm 排针**。

    坐标 100 单位 = 2.54mm：两针间距取 400 单位（10.16mm）—— 元件含焊盘宽 6.63mm，
    排针再近就会压到本体；板 600×400（15.24×10.16mm），针心 (100,200) / (500,200)。
    左侧=pin1(K)、右侧=pin2(A)，与 icon/PCB 同向。
    """
    U = 39.37
    bw, bh = 600, 400
    # ★★ 板边相位＝**半格**（AGENTS §3b：转接板不许影响板外孔的插拔 ✓，2026-09-27 ✓）：
    #   旧做法把板框画成整张画布 ✗ ⇒ 板边到针脚都是 100 的整数倍 ✗ ⇒ 压在孔线上 ✗。
    #   四周各让 50（半格 = 1.27mm）⇒ 板边落在两排孔正中 ✓；针脚一个不动 ✓；
    #   板心仍为 (300,200) ✓ ⇒ 本体不用挪 ✓。
    INSET = 50
    cx, cy = 300, 200
    pad_r, hole_r = 1.0 * U, 0.485 * U
    xs = [100, 500]
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
         f'height="{bh / 100 * 2.54:.2f}mm" viewBox="0 0 {bw} {bh}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="{INSET}" y="{INSET}" width="{bw - 2 * INSET}" height="{bh - 2 * INSET}" '
         f'fill="#00aa44" stroke="#00772f" '
         f'stroke-width="5"/>\n']
    # 本体（1:1，含焊盘 6.63 × 2.54mm）
    m = U
    L.append(f'  <rect x="{cx - PAD_DX * m - PAD_W / 2 * m:.1f}" y="{cy - PAD_H / 2 * m:.1f}" '
             f'width="{(PAD_DX + PAD_W / 2) * 2 * m:.1f}" height="{PAD_H * m:.1f}" '
             f'fill="#c0c0c0" stroke="none"/>\n')
    L.append(f'  <rect x="{cx - BODY_W / 2 * m:.1f}" y="{cy - BODY_H / 2 * m:.1f}" '
             f'width="{BODY_W * m:.1f}" height="{BODY_H * m:.1f}" fill="#2b2b2b" stroke="none"/>\n')
    L.append(f'  <rect x="{cx + BAND_X * m - BAND_W / 2 * m:.1f}" y="{cy - BODY_H / 2 * m:.1f}" '
             f'width="{BAND_W * m:.1f}" height="{BODY_H * m:.1f}" fill="#e8e8e8" stroke="none"/>\n')
    for cn, x, label in ((0, xs[0], "K"), (1, xs[1], "A")):
        L.append(f'  <circle id="connector{cn}pin" connectorname="{esc(CONN[cn][2])}" '
                 f'cx="{x}" cy="{cy}" r="{pad_r:.1f}" fill="#d4af37" stroke="#8a6d00" '
                 f'stroke-width="4"/>\n')
        L.append(f'  <circle cx="{x}" cy="{cy}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
        ty = cy + (76 if x < cx else -76)
        L.append(f'  <text x="{x}" y="{ty}" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans">{label}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
def gen_schematic_svg():
    """二极管符号（AGENTS §5 引脚画法，口径同 BAT54S）：

        1(K) ──┬──|◀──┬── 2(A)      ← 三角尖朝左（电流 A→K），阴极条在尖这一侧

    引脚线 stroke #787878 / width 5、编号 #8C8C8C / 字号 35、端点用 0.0001 的不可见 terminal。
    物理尺寸 width/height 用 in，1000 单位 = 1in。
    """
    WIRE, HALF, TRI = 230, 45, 30          # 引线长 / 三角半高 / 三角“底/尖到中心”
    VX0, VY0 = -(WIRE + 10), -(HALF + 30)
    VW, VH = 2 * (WIRE + 10), 2 * (HALF + 30)
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{VW / 1000:.6f}in" '
         f'height="{VH / 1000:.6f}in" viewBox="{VX0} {VY0} {VW} {VH}">\n',
         ' <g id="schematic">\n']
    # 引线：pin1 止于阴极条(-TRI)、pin2 从三角底(+TRI) 起 —— 不穿过符号
    L.append(f'  <line class="pin" id="connector0pin" connectorname="{esc(CONN[0][2])}" '
             f'x1="{-WIRE}" y1="0" x2="{-TRI}" y2="0" stroke="#787878" stroke-width="5" '
             f'stroke-linecap="round"/>\n')
    L.append(f'  <rect class="terminal" id="connector0terminal" x="{-WIRE}" y="0" width="0.0001" '
             f'height="0.0001" fill="none" stroke="none"/>\n')
    L.append(f'  <line class="pin" id="connector1pin" connectorname="{esc(CONN[1][2])}" '
             f'x1="{TRI}" y1="0" x2="{WIRE}" y2="0" stroke="#787878" stroke-width="5" '
             f'stroke-linecap="round"/>\n')
    L.append(f'  <rect class="terminal" id="connector1terminal" x="{WIRE}" y="0" width="0.0001" '
             f'height="0.0001" fill="none" stroke="none"/>\n')
    # 阴极条（尖这一侧 = 左）
    L.append(f'  <line x1="{-TRI}" y1="{-HALF}" x2="{-TRI}" y2="{HALF}" stroke="#000000" '
             f'stroke-width="5" stroke-linecap="round"/>\n')
    # 三角：底在 +TRI、尖在 -TRI
    L.append(f'  <path d="M {TRI} {-HALF} L {TRI} {HALF} L {-TRI} 0 Z" fill="none" stroke="#000000" '
             f'stroke-width="5" stroke-linejoin="round"/>\n')
    # 编号（引线上方）
    L.append(f'  <text x="{(-WIRE - TRI) // 2}" y="-28" font-size="35" fill="#8C8C8C" '
             f'text-anchor="middle" font-family="DroidSans">1</text>\n')
    L.append(f'  <text x="{(WIRE + TRI) // 2}" y="-28" font-size="35" fill="#8C8C8C" '
             f'text-anchor="middle" font-family="DroidSans">2</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------------ pcb
def gen_pcb_svg():
    """PCB 视图：**焊盘尺寸/间距按立创**（1.524×2.540、中心距 4.48）；
    丝印按立创那套（外框 6.63×3.05 + 三角 + 阴极竖带 + 两条引出短线），
    但**阴极带与三角整体镜像到左侧** —— 立创原图把 number=1 摆在左边、丝印却指向右侧阴极，
    两者自相矛盾；手册写 pin1 = Cathode，故以手册为准（详见文件头）。
    """
    C = 3.6                                    # 画布中心（外框 7.2 × 7.2mm，四周留边）
    pads, silk = [], []
    for cn, num, net, _desc in CONN:
        sx = -1 if cn == 0 else 1
        pads.append(f'<rect id="connector{cn}pad" connectorname="{esc(net)}" '
                    f'x="{C + sx * PAD_DX - PAD_W / 2:.3f}" y="{C - PAD_H / 2:.3f}" '
                    f'width="{PAD_W:.3f}" height="{PAD_H:.3f}" fill="#F7BD13" stroke="none"/>')
    # 外框
    silk.append(f'<rect x="{C - SILK_W / 2:.3f}" y="{C - SILK_H / 2:.3f}" width="{SILK_W:.3f}" '
                f'height="{SILK_H:.3f}" fill="none" stroke="#f0f0f0" stroke-width="0.1524"/>')
    # 三角（底在右侧 x=+0.43、尖朝左 x=-0.712）—— 立创值镜像后的结果
    silk.append(f'<path d="M {C + 0.431:.3f} {C - 0.889:.3f} L {C + 0.431:.3f} {C + 0.889:.3f} '
                f'L {C - 0.712:.3f} {C:.3f}" fill="none" stroke="#f0f0f0" stroke-width="0.1524" '
                f'stroke-linejoin="round"/>')
    # 阴极带（竖线，在尖这一侧）
    silk.append(f'<line x1="{C - 0.558:.3f}" y1="{C - 1.016:.3f}" x2="{C - 0.558:.3f}" '
                f'y2="{C + 1.016:.3f}" stroke="#f0f0f0" stroke-width="0.1524"/>')
    # 两条引出短线（三角外到焊盘的示意引线）
    silk.append(f'<line x1="{C - 0.839:.3f}" y1="{C:.3f}" x2="{C - 1.347:.3f}" y2="{C:.3f}" '
                f'stroke="#f0f0f0" stroke-width="0.1524"/>')
    silk.append(f'<line x1="{C + 0.685:.3f}" y1="{C:.3f}" x2="{C + 1.327:.3f}" y2="{C:.3f}" '
                f'stroke="#f0f0f0" stroke-width="0.1524"/>')
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    W = H = 2 * C
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" '
            f'viewBox="0 0 {W:.1f} {H:.1f}">\n'
            f'  <g id="copper1">\n{inner}\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for cn, num, net, desc in CONN:
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(net)}" type="male">\n'
            f'   <description>pin {num} = {esc(desc)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cn}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{cn}pin" terminalId="connector{cn}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{cn}pad"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>1</version>\n <date>2026-09-17</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>SS34</tag>\n  <tag>Schottky</tag>\n'
            f'  <tag>diode</tag>\n  <tag>SMA</tag>\n  <tag>DO-214AC</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="pins">2</property>\n'
            f'  <property name="ratings">3.0A / 40V</property>\n </properties>\n'
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
