#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — Fritzing 自定义元件 SMA-PJ1.7-L9.5 (SMA Female Jack, PCB Through-Hole)。

来源图纸：D:\\Downloads\\SMA-PJ1.7-L9.5.pdf（莱联 LAIL-SMA-PJ1.7-L9.5-L，立创 C55497804）
识别结论：
  - SMA female jack（母座/内针，中心 socket 接收公头 pin），板端直插，镀金，50Ω DC-6GHz
  - 螺纹 1/4-36UNS-2A（SMA 标准），筒高/长 8.0mm，总长 13.5mm
  - 本体方形法兰 6.5×6.5（SQ6.5）；底部两大地脚中心距 5.3mm、脚宽 0.8
  - 电气（2026-09-06 用户定）：原理图/breadboard = 2 脚（+ 与 GND）；PCB 保留 5 焊盘
    （connector0=+ 中心脚、connector1=GND、connector2/3/4=GND2/3/4 仅 pcb，buses 互联为地）

视图设计（2026-09-05/06 用户确认）：
  - icon：图纸“横置图”（轴向剖视侧图，左基座→筒→螺纹段→右端帽）矢量线稿直接转 SVG
    （银色写实/手绘候选均废弃；2026-09-06 用户改为直接采用图纸线稿）
  - breadboard：绿色转接板 + 边装三脚 SMA（墨绿板、左右分叉银灰条各 30 孔、
    + 在上灰区 / GND 在下灰区接线，布局同 _bb_draft.py）
  - schematic：屏蔽壳矩形 + 中心 + 引线 + 单个 GND stub（2 脚）
  - pcb：+ 中心 pad + 4 GND pad 正交十字（左右大地脚 ±2.65、上下地 pad）
源文件与脚本同目录；.fzpz 输出到仓库顶层 fzpz/（docs/part-dev-guide.md §2.2）。
用法：python gen_part.py
"""
import os
import re
import zipfile
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "SMA-PJ1.7-L9.5"
TITLE = "SMA Female Jack (PCB Through-Hole)"
LABEL = "J"
PACKAGE = "SMA-PJ1.7-L9.5"
FAMILY = "RF SMA Connector"
FZPZ = "SMA-PJ1.7-L9.5.fzpz"

# 连接器（2026-09-06 用户定）：原理图/breadboard 2 脚 = SIG 与 GND；PCB 每个焊盘独立可接线。
#   connector0 = SIG（顶层中心）；connector1..4 = GND/GND2/GND3/GND4 对应顶左/顶右/底左/底右四个地 pad
#   （4 个 GND 各自独立 connector、都能接线；<buses> 互联为同一地网 → 点任一 GND 其它全亮）
CONN = ["SIG", "GND", "GND2", "GND3", "GND4"]
PCB_ONLY = {2, 3, 4}  # 仅 pcb 出现的 connector（schematic/breadboard 只显示 SIG 与 GND）

# 配色（工业写实：镀金黄铜 + PTFE 白 + 绿转接板）
GOLD = "#e6b53d"
GOLD_D = "#b8860b"
GOLD_H = "#f7d77e"
SILVER = "#d8dbdd"
SILVER_D = "#9aa0a6"
DARK = "#333333"
PTFE = "#f2efe6"
PTFE_H = "#fcfbf5"
BB_GREEN = "#00aa44"
BB_GREEN_D = "#00772f"
PAD_GOLD = "#d4af37"
PAD_GOLD_D = "#8a6d00"
PCB_PAD = "#F7BD13"

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ==================================================================== icon
# icon = 图纸“横置图”（轴向剖视侧图：左基座→筒→螺纹段→右端帽）的矢量线稿，
# 直接从 D:\Downloads\SMA-PJ1.7-L9.5.pdf 抽取矢量转换为 svg（用户 2026-09-06 定，
# 线稿风，非金色写实重绘）。产物已存为同目录 svg.icon.SMA-PJ1.7-L9.5_icon.svg，
# gen_part 直接采用该静态文件（抽取工具 _trace_svg/_fig_clean/_make_icon 已删）。
def gen_icon_svg():
    p = os.path.join(OUT_DIR, "svg.icon.SMA-PJ1.7-L9.5_icon.svg")
    with open(p, encoding="utf-8") as f:
        return f.read()


# ================================================================ breadboard
def gen_breadboard_svg():
    """面包板 = 绿色转接板 + 边装干净三脚 SMA（2026-09-06 用户定稿，逻辑同 _bb_draft.py）。
    坐标 mm：板 x-12.6..10.4 / y-2.2..7.4，板体墨绿 #003d1e（板体=描边，0.1mm）；
    左端分叉成上/下银灰条（各 30 个孔径 0.12mm 小孔）；右端深绿 L 形(#005c2f) + 右上 5×3.1 块；
    SMA 干净三脚图形 translate(6.65,-0.65)，筒伸出板右缘；三银灰焊盘 4.5×1.2 直角。
    丝印：+ 在 L 型竖块、GND 在底部绿长条。
    接线端点（connector pin）：上叉银灰条中心 = connector0(+)，下叉银灰条中心 = connector1(GND)。
    """
    GREEN = "#003d1e"    # 板体/描边墨绿
    SOLDER = "#c6cbd0"   # 银灰
    SOLDER_D = "#8a9298" # 银灰描边
    DARKGREEN = "#005c2f"  # 深绿块
    HOLE = "#3a3a3a"     # 孔色
    WHITE = "#ffffff"
    PINK_GOLD = "#e6b53d"   # 接线盘（与 SMA 金一致）
    PINK_GOLD_D = "#b8860b"
    # 读干净三脚 SMA 图形（同目录静态资产），剥离 <svg...> 头尾
    clean = open(os.path.join(OUT_DIR, "sma_icon_3pin_clean.svg"), encoding="utf-8").read()
    clean_content = re.sub(r'^.*?<svg[^>]*>\n?', '', clean, flags=re.S)
    clean_content = re.sub(r'</svg>\s*$', '', clean_content, flags=re.S)

    L = []
    L.append(SVG_HDR)
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="33.375mm" height="10.3mm" '
             'viewBox="-12.95 -2.55 33.375 10.3">\n')
    L.append('  <g id="breadboard">\n')
    # 绿色转接板（左端分叉，凹槽内端圆角 r=1.0）
    BX0, BY0, FX, R = -12.6, -2.2, -0.6, 1.0
    L.append(f'<path d="M -12.6 7.4 L {FX} 7.4 L 10.4 7.4 L 10.4 -2.2 L {FX} -2.2 '
             f'L -12.6 -2.2 L -12.6 1.0 L {FX-R} 1.0 '
             f'A {R} {R} 0 0 1 {FX} {1.0+R} L {FX} {4.2-R} '
             f'A {R} {R} 0 0 1 {FX-R} 4.2 L -12.6 4.2 Z" '
             f'fill="{GREEN}" stroke="{GREEN}" stroke-width="0.1"/>\n')
    # 上叉银灰(y -2.2..1.0) + 下叉左段银灰(y 4.2..7.4)，各 12mm
    L.append(f'<rect x="-12.6" y="-2.2" width="12.0" height="3.2" fill="{SOLDER}" stroke="none"/>\n')
    L.append(f'<rect x="-12.6" y="4.2" width="12.0" height="3.2" fill="{SOLDER}" stroke="none"/>\n')
    # 每个灰色区域打 3行x10列=30 个小孔（孔径 0.12）
    for x0, y0 in ((-12.6, -2.2), (-12.6, 4.2)):
        for r in range(3):
            for c in range(10):
                cx = x0 + (c + 0.5) * 1.2
                cy = y0 + (r + 0.5) * (3.2 / 3)
                L.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="0.06" fill="{HOLE}" stroke="none"/>\n')
    # 下叉右段深绿带（到板右缘）
    L.append(f'<rect x="-0.6" y="4.2" width="11.0" height="3.2" fill="{DARKGREEN}" stroke="none"/>\n')
    # 右上深绿块 5x3.1
    L.append(f'<rect x="5.4" y="-2.2" width="5.0" height="3.1" fill="{DARKGREEN}" stroke="none"/>\n')
    # 深绿 L 形：竖块 + 横条一体
    L.append(f'<rect x="-0.6" y="-2.2" width="5.6" height="6.0" fill="{DARKGREEN}" stroke="none"/>\n')
    L.append(f'<rect x="5.0" y="1.3" width="5.4" height="2.5" fill="{DARKGREEN}" stroke="none"/>\n')
    # 三个银灰焊盘(4.5x1.2 直角)与引脚 y 中心对齐
    ix, iy = 6.65, -0.65
    pad_x, pad_w, pad_h = 5.90, 4.5, 1.2
    for local_cy in (0.4, 3.35, 6.1):
        py = local_cy - pad_h / 2 - 0.65
        L.append(f'<rect x="{pad_x:.2f}" y="{py:.2f}" width="{pad_w}" height="{pad_h}" '
                 f'fill="{SOLDER}" stroke="{SOLDER_D}" stroke-width="0.1"/>\n')
    # 干净三脚 SMA
    L.append(f'<g transform="translate({ix},{iy})">\n')
    L.append(clean_content + '\n')
    L.append('</g>\n')
    # 丝印 SIG 与 GND（去掉 text-anchor，见 AGENTS.md §5；y 已做读数校准；SIG x 与 GND 对齐）
    L.append(f'<text x="0.65" y="-0.31" font-size="1.3" fill="{WHITE}" '
             f'font-family="DroidSans">SIG</text>\n')
    L.append(f'<text x="0.65" y="6.191" font-size="1.3" fill="{WHITE}" '
             f'font-family="DroidSans">GND</text>\n')
    # 接线端点：上叉银灰条 = connector0(+)、下叉银灰条 = connector1(GND)。
    # 两盘同列(x-6.6)，y 距 5.08 = 2×2.54mm → Fritzing 面包板两脚都能插入孔
    L.append(f'<circle id="connector0pin" connectorname="SIG" cx="-6.6" cy="0.0" '
             f'r="0.85" fill="{PINK_GOLD}" stroke="{PINK_GOLD_D}" stroke-width="0.2"/>\n')
    L.append(f'<circle cx="-6.6" cy="0.0" r="0.45" fill="{HOLE}"/>\n')
    L.append(f'<circle id="connector1pin" connectorname="GND" cx="-6.6" cy="5.08" '
             f'r="0.85" fill="{PINK_GOLD}" stroke="{PINK_GOLD_D}" stroke-width="0.2"/>\n')
    L.append(f'<circle cx="-6.6" cy="5.08" r="0.45" fill="{HOLE}"/>\n')
    L.append('  </g>\n</svg>\n')
    return "".join(L)


# ================================================================ schematic
def gen_schematic_svg():
    """原理图符号：参考 SparkFun「SMA Antenna Connector」风格自绘（同心圆 SMA 端面 +
    中心正极(SIG)右引 + 外壳 GND 向下引脚线）。自绘实现，几何仅作风格参考。
    （2026-09-06 用户定：原理图 2 脚；删除底部水平灰线；短竖黑线改为 2 脚(GND)短灰引脚线；
    编号 1=SIG、2=GND，不写名称文字；裁边。）"""
    L = []
    L.append(SVG_HDR)
    # 内容 bbox x0.36..21.96 / y0.36..21.96 → viewBox 0 0 22.3 22.3
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="7.87mm" height="7.87mm" '
             'viewBox="0 0 22.3 22.3">\n')
    L.append('  <g id="schematic">\n')
    # SMA 端面：外圆（外壳端面）+ 内圆（中心孔/PTFE）
    L.append('   <circle cx="7.56" cy="7.56" r="7.2" fill="#ffffff" stroke="#000000" stroke-width="0.9"/>\n')
    L.append('   <circle cx="7.56" cy="7.56" r="3.22" fill="none" stroke="#000000" stroke-width="0.9"/>\n')
    # connector0 "SIG"(脚1)：中心正极从圆心向右引出
    L.append(f'   <line id="connector0pin" connectorname="SIG" class="pin" '
             f'x1="7.56" y1="7.56" x2="21.96" y2="7.56" '
             f'stroke="#787878" stroke-linecap="round" stroke-width="0.75"/>\n')
    # terminal 用极小的 rect（BAT54S 式端点，几乎不可见，靠线端吸附，不画夸张黑点）
    L.append(f'   <rect id="connector0terminal" x="21.96" y="7.56" width="0.0001" height="0.0001" '
             f'stroke="none" stroke-width="0" fill="none"/>\n')
    # connector1 "GND"(脚2)：外壳地 = 外圆底部向下的一小段引脚线（短灰竖线）
    L.append(f'   <line id="connector1pin" connectorname="GND" class="pin" '
             f'x1="7.56" y1="14.76" x2="7.56" y2="21.96" '
             f'stroke="#787878" stroke-linecap="round" stroke-width="0.75"/>\n')
    L.append(f'   <rect id="connector1terminal" x="7.56" y="21.96" width="0.0001" height="0.0001" '
             f'stroke="none" stroke-width="0" fill="none"/>\n')
    # 引脚编号（SparkFun 灰色小数字）：1=SIG(右线)、2=GND(竖线右侧)
    L.append('   <text x="17.0" y="6.5" font-size="2.5" fill="#8c8c8c" '
             'font-family="DroidSans">1</text>\n')
    L.append('   <text x="8.4" y="19.6" font-size="2.5" fill="#8c8c8c" '
             'font-family="DroidSans">2</text>\n')
    L.append('  </g>\n</svg>\n')
    return "".join(L)


# ======================================================================== pcb
def gen_pcb_svg():
    """PCB 视图：按 PDF「建议 PCB 尺寸」重画（2026-09-06 用户定，旧 5 pad 作废）。
      PDF：3-1.2 / 2-1.2 —— 1.2 宽 × 4.5 高竖条，相邻 pitch 2.825。
      顶层(copper1)：3 盘 = SIG(中心 x0) + GND(左 -2.825) + GND2(右 +2.825)
      底层(copper0)：2 盘 = GND/GND2，与顶层左右两盘同位置同尺寸（双面过孔，中心 SIG 仅顶层）
      （2026-09-06 用户：焊盘无圆点；丝印仅留比焊盘稍大的长方框。）
      坐标 mm。"""
    PAD = PCB_PAD
    W, H = 1.2, 4.5
    Y0 = -H / 2
    top, bot = [], []
    # 5 个独立可接线 pad（每 connector 一个）
    # SIG(connector0) 顶层中心 x0；GND(1)/GND2(2) 顶层左/右 ±2.825；GND3(3)/GND4(4) 底层左/右 ±2.825
    top.append(f'<rect id="connector0pad" x="-0.6" y="{Y0}" width="{W}" height="{H}" '
               f'fill="{PAD}" stroke="none" connectorname="SIG"/>')
    for cn, gx in ((1, -2.825), (2, 2.825)):
        top.append(f'<rect id="connector{cn}pad" x="{gx - 0.6}" y="{Y0}" width="{W}" height="{H}" '
                   f'fill="{PAD}" stroke="none" connectorname="{CONN[cn]}"/>')
    for cn, gx in ((3, -2.825), (4, 2.825)):
        bot.append(f'<rect id="connector{cn}pad" x="{gx - 0.6}" y="{Y0}" width="{W}" height="{H}" '
                   f'fill="{PAD}" stroke="none" connectorname="{CONN[cn]}"/>')
    # 丝印：仅长方框，比焊盘外轮廓(±3.425 / ±2.25)每边大 ~0.3mm
    silk = [
        f'<rect x="-3.7" y="-2.55" width="7.4" height="5.1" fill="none" stroke="#f0f0f0" stroke-width="0.15"/>',
    ]
    SX, SY = 4.0, 3.0
    return (SVG_HDR +
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * SX:.2f}mm" height="{2 * SY:.2f}mm" '
            f'viewBox="{-SX:.2f} {-SY:.2f} {2 * SX:.2f} {2 * SY:.2f}">\n'
            f'  <g id="copper0">\n' + "\n".join(bot) + '\n  </g>\n'
            f'  <g id="copper1">\n' + "\n".join(top) + '\n  </g>\n'
            f'  <g id="silkscreen">\n' + "\n".join(silk) + '\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    # 每个 connector 的 pcb 引用（svgId, layer）：每个 pad 独立可接线
    PPCB = {
        0: [("copper1", "connector0pad")],  # SIG 顶中
        1: [("copper1", "connector1pad")],  # GND 顶左
        2: [("copper1", "connector2pad")],  # GND2 顶右
        3: [("copper0", "connector3pad")],  # GND3 底左
        4: [("copper0", "connector4pad")],  # GND4 底右
    }
    conns = []
    for i, name in enumerate(CONN):
        bb = sch = ""
        if i not in PCB_ONLY:
            bb = (f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{i}pin"/>\n    </breadboardView>\n')
            sch = (f'    <schematicView>\n     <p layer="schematic" svgId="connector{i}pin" terminalId="connector{i}terminal"/>\n    </schematicView>\n')
        pcb = ''.join(f'    <p layer="{ly}" svgId="{sid}"/>\n' for ly, sid in PPCB[i])
        conns.append(
            f'  <connector id="connector{i}" name="{esc(name)}" type="male">\n'
            f'   <description>{esc(name)}</description>\n'
            f'   <views>\n' + bb + sch + f'    <pcbView>\n{pcb}    </pcbView>\n' + '   </views>\n'
            f'  </connector>')
    # buses：4 个 GND 焊盘(connector1..4) 内部互联为同一地网络（物理一体，点击全亮）。
    # Fritzing 规范子元素为 <nodeMember>（不是 <node>）
    buses = (' <buses>\n  <bus id="GND">\n'
             + "".join(f'   <nodeMember connectorId="connector{i}"/>\n' for i in (1, 2, 3, 4))
             + '  </bus>\n </buses>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>4</version>\n <date>2026-09-05</date>\n'
            f' <label>{LABEL}</label>\n <author>fritzing-parts-langhua</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>SMA</tag>\n  <tag>RF</tag>\n  <tag>Antenna</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n  <property name="variant">female jack</property>\n'
            f'  <property name="part number">LAIL-SMA-PJ1.7-L9.5-L</property>\n'
            f'  <property name="layer"></property>\n </properties>\n'
            f' <views>\n  <breadboardView>\n   <layers image="breadboard/{PART_ID}_breadboard.svg">\n'
            f'    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            f'  <schematicView>\n   <layers image="schematic/{PART_ID}_schematic.svg">\n'
            f'    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
            f'  <pcbView>\n   <layers image="pcb/{PART_ID}_pcb.svg">\n'
            f'    <layer layerId="copper0"/>\n    <layer layerId="copper1"/>\n    <layer layerId="silkscreen"/>\n   </layers>\n  </pcbView>\n'
            f'  <iconView>\n   <layers image="icon/{PART_ID}_icon.svg">\n'
            f'    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n </views>\n'
            f' <connectors>\n' + "\n".join(conns) + '\n </connectors>\n'
            + buses + '</module>\n')


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
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)

    fzp_name = f"part.{PART_ID}.fzp"
    with open(os.path.join(OUT_DIR, fzp_name), "w", encoding="utf-8") as f:
        f.write(gen_fzp())
    print("wrote", fzp_name)

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
