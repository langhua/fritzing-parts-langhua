#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — Fritzing 自定义元件 DPDT7x7-6P（7x7mm 双刀 6 脚自锁按键开关，KFC-22Z77-GT-PBTK）。

来源图纸：D:\\Downloads\\KFC-22Z77-GT-PBTK.pdf（浙江创都 KFC-22Z77-GT-PBTK，7.0 自锁按键开关）
识别结论：
  - 7.0×7.0 方体、黑底座(PBT)+白盖(POM)+蓝柄(POM)；柄顶面 3×2mm、中央 1mm 槽
  - 引脚 = 两排 2mm 针距，左右两侧各 3 脚（0.6 宽 × 3mm 长，圆头）
  - 6 脚电气 = DPDT（2026-09-06 用户定：刀1=脚 1/2/3 公共1、刀2=脚 4/5/6 公共4；自锁=闭态，缺省 1-2、4-5 通）
  - 真实脚印：2 排×3 孔 Ø1.0，排距 5.0、列距 2.0；1 脚在左下（用户定）
视图设计（2026-09-06 用户逐步确认）：
  - icon：顶视图（黑 7×7 + 白盖 + 蓝柄两级凸起 + 杆顶 3×2 中央 1mm 槽）
  - breadboard：本体顶视 + 左右各 3 根圆头银脚（2mm 针距，无焊盘；银脚即 connector pin）
  - schematic：DPDT 双刀开关符号（左 1/3/4/6、右 2/5；1-2、4-5 缺省通；3/6 开路；虚线联动）
  - pcb：6 通孔金环焊盘（外径1.5/孔0.9，铜0+铜1），丝印 7×7 框 + 1脚白点(Φ0.8, 距框0.4)
源文件=同目录正式视图 `svg.<view>.<PART_ID>_<view>.svg`（icon/breadboard/schematic 为静态定稿，
由本脚本读入复制；pcb 由代码参数化生成双面铜层）。`.fzpz` 输出到仓库顶层 fzpz/。用法：python gen_part.py
"""
import os
import zipfile
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "DPDT7x7-6P"
TITLE = "DPDT"
LABEL = "S"
PACKAGE = "DPDT7x7-6P"
FAMILY = "Pushbutton Switch"
FZPZ = "DPDT7x7-6P.fzpz"

# 6 个 connector：编号 1..6（DPDT：刀1=1/2/3 公共1，刀2=4/5/6 公共4）
CONN = ["1", "2", "3", "4", "5", "6"]
PAD_GOLD = "#F7BD13"

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'


def _read_view(name):
    with open(os.path.join(OUT_DIR, name), encoding="utf-8") as f:
        return f.read()


# ==================================================================== icon
def gen_icon_svg():
    # icon/breadboard/schematic 为静态定稿 svg（设计过程中经 _*_draft.svg 草稿迭代定稿后转正），
    # 脚本读正式文件返回，不再依赖草稿源。
    return _read_view(f"svg.icon.{PART_ID}_icon.svg")


# ================================================================ breadboard
def gen_breadboard_svg():
    return _read_view(f"svg.breadboard.{PART_ID}_breadboard.svg")


# ================================================================ schematic
def gen_schematic_svg():
    return _read_view(f"svg.schematic.{PART_ID}_schematic.svg")


# ======================================================================== pcb
def gen_pcb_svg():
    """PCB：6 通孔金环焊盘。Fritzing 渲染 THT 焊盘按「外径≈2r+线宽、孔≈2r−线宽」，
    故取 r=0.6/stroke=0.3 → 外 0.75? 不，外径 2*0.6+0.3=1.5mm、孔 2*0.6-0.3=0.9mm
    （2026-09-06 按用户两次实测校准；焊盘仅一个圆环，无额外暗孔圆）。
    排距 5.0（y=±2.5）、列距 2.0（x=-2,0,+2）；编号 上排4/5/6、下排1/2/3（1脚在左下）。
    双面：铜0(copper0)+铜1(copper1)；丝印 7×7 框 + 1脚白点(Φ0.8，距框底0.4)。"""
    def ring(n, x, y):
        return (f'<circle id="connector{n}pad" connectorname="{n}" cx="{x}" cy="{y}" '
                f'r="0.6" fill="none" stroke="{PAD_GOLD}" stroke-width="0.3"/>')
    def ring_b(n, x, y):
        return (f'<circle id="connector{n}padB" connectorname="{n}" cx="{x}" cy="{y}" '
                f'r="0.6" fill="none" stroke="{PAD_GOLD}" stroke-width="0.3"/>')
    # (num, x, y)：上排 y=-2.5 → 4/5/6；下排 y=+2.5 → 1/2/3
    top = [(4, -2, -2.5), (5, 0, -2.5), (6, 2, -2.5)]
    bot = [(1, -2, 2.5), (2, 0, 2.5), (3, 2, 2.5)]
    c1 = "\n".join(ring(n, x, y) for n, x, y in top + bot)
    c0 = "\n".join(ring_b(n, x, y) for n, x, y in top + bot)
    silk = ('<rect x="-3.5" y="-3.5" width="7" height="7" rx="0.35" fill="none" '
            'stroke="#f0f0f0" stroke-width="0.15"/>\n'
            # pin1 白点：Fritzing 丝印层只描边不填充 → 用「粗白描边(r0.2/stroke0.4)+白填充」呈实心点，
            # 外径≈r+stroke/2=0.4（Φ0.8mm），点心 y=4.3
            '<circle cx="-2" cy="4.3" r="0.2" fill="#f0f0f0" stroke="#f0f0f0" stroke-width="0.4"/>')
    return (SVG_HDR +
            '<svg xmlns="http://www.w3.org/2000/svg" width="8.0mm" height="9.2mm" '
            'viewBox="-4.0 -4.0 8.0 9.2">\n'
            '  <g id="copper0">\n' + c0 + '\n  </g>\n'
            '  <g id="copper1">\n' + c1 + '\n  </g>\n'
            '  <g id="silkscreen">\n' + silk + '\n  </g>\n</svg>\n')


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for i in range(6):
        n = CONN[i]                       # 脚号 1..6（svg 内 connector<n>pin/pad）
        conns.append(
            f'  <connector id="connector{i}" name="{n}" type="male">\n'
            f'   <description>{n}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{n}pin"/>\n    </breadboardView>\n'
            f'    <schematicView>\n     <p layer="schematic" svgId="connector{n}pin" '
            f'terminalId="connector{n}terminal"/>\n    </schematicView>\n'
            f'    <pcbView>\n     <p layer="copper1" svgId="connector{n}pad"/>\n'
            f'     <p layer="copper0" svgId="connector{n}padB"/>\n    </pcbView>\n'
            f'   </views>\n'
            f'  </connector>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>4</version>\n <date>2026-09-06</date>\n'
            f' <label>{LABEL}</label>\n <author>fritzing-parts-langhua</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>switch</tag>\n  <tag>DPDT</tag>\n  <tag>pushbutton</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n'
            f'  <property name="part number">DPDT</property>\n'
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
            + '</module>\n')


# -------------------------------------------------------------------- 打包
def main():
    files = {
        "breadboard": gen_breadboard_svg(),
        "schematic": gen_schematic_svg(),
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
