# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for BAT54 (SOT-23 single Schottky).

BAT54 is a SOT-23 package containing ONE Schottky diode; the third lead is
**not connected**. Nexperia pinning (SOT-23 marking codes of this family:
KL1 = BAT54, KL2 = BAT54A, KL3 = BAT54C, KL4 = BAT54S ⇒ 本仓 `BAT54S` 那颗写 KL4 ✓):
    pin 1 = A   (anode)      ← 丝印 KL1 那一面朝上时看，引脚 1 在左下 ✓
    pin 2 = n.c.
    pin 3 = K   (cathode)
⇒ current flows pin1 ->|>|- pin3.

Connectors (3):
    connector0 = pin 1 (A)
    connector1 = pin 2 (n.c.)   ← 本库惯例：空脚也做成连接器、名字写 NC ✓
                                   （同 `ATECC608B` / `BQ25570` / `CH340C` / `DW03` ✓）
    connector2 = pin 3 (K)

★ 三只脚**都要**声明 ✓：`pin 2` 虽然不接，但它是一块真铜（PCB/SMT 都要焊上才稳），
  做成连接器以后布线器能看见它、不会把它当"不存在的脚" ✗。

Follows the Fritzing part-dev-guide (docs/part-dev-guide.md):
  - .fzp image refs use subdirectory paths
  - schematic pins need class='pin'/connectorname + class='terminal'
  - PCB pads appear once, on copper1 (SMD package, no through-hole)
  - .fzpz goes to the repo-level fzpz/ directory

参考件（封装几何直接沿用，改的只是"里面是什么、丝印写什么" ✓）：
  - pcb:        core/pcb/SMD_SOT-23.svg（官方 3-pad SOT-23 ✓）
  - breadboard: core/breadboard/sparkfun-discretesemi_sot23-3_breadboard.svg
  - 本仓 `svg/BAT54S/gen_part.py`（同一个封装、同一套焊盘坐标 ✓）
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "BAT54_SOT23_1"

# View SVG filenames (flat inside fzpz)
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "BAT54.fzpz"

# .fzp image refs (subdirectory style, per guide)
PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID


# ---------------------------------------------------------------- PCB view
def pcb_svg():
    """SOT-23 SMD footprint: 3 copper pads + silkscreen outline.

    Mirrors core/pcb/SMD_SOT-23.svg (viewBox 0 0 300 290, 3 mm x 2.9 mm).
    connector0 = pin1 (bottom-left), connector1 = pin2 (bottom-right),
    connector2 = pin3 (top-center).
    """
    s = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="3.0mm" height="2.9mm" viewBox="0 0 300 290" id="svg2">\n'
        '  <g id="copper1">\n'
        # PCB 视图的连接点由**焊盘本身**（`connectorNpin`）承担，不画 `connectorNterminal` ✓
        '    <rect width="80" height="90" x="15" y="200" id="connector0pin" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
        '    <rect width="80" height="90" x="205" y="200" id="connector1pin" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
        '    <rect width="80" height="90" x="110" y="0" id="connector2pin" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
        '  </g>\n'
        '  <g id="silkscreen">\n'
        '    <rect width="290" height="90" x="5" y="100" style="fill:none;stroke:#ffffff;stroke-width:10;stroke-opacity:1"/>\n'
        '    <circle cx="55" cy="195" r="10" style="fill:#ffffff;fill-opacity:1;stroke:none"/>\n'
        '  </g>\n'
        '</svg>\n'
    )
    return s


# ---------------------------------------------------------- schematic view
def schematic_svg():
    """Single Schottky symbol: A(pin1) left, K(pin3) right.

    `pin 2` 是 n.c. ⇒ 画成一根**与符号不相连**的短引线（一眼看出这只脚不接 ✓），
    它的端子照常落在引线外端 ✓（`fzp_check` 第 ⑩ 条：terminal 必须在引脚线外端 ✓）。

    画布与 `BAT54S` 同尺寸（58.3x29.51 = 0.6478x0.3279 in ✓）⇒ 两件在原理图里**一样大** ✓。
    """
    s = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        'x="0px" y="0px" width="0.6477778in" height="0.3278889in" viewBox="0 0 58.3 29.51" '
        'xml:space="preserve">\n'
        ' <g id="schematic">\n'
        # 引脚 1（A）—— 左侧引线
        '  <line class="pin" id="connector0pin" connectorname="1" fill="none" stroke="#787878" '
        'stroke-width="0.75" stroke-linecap="round" x1="0.35" y1="7.56" x2="16.2" y2="7.56"/>\n'
        '  <rect class="terminal" id="connector0terminal" x="0.35" y="7.56" width="0.0001" height="0.0001" '
        'stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 6.86 6.51)" fill="#8C8C8C" font-family="DroidSans" '
        'font-size="2.5">1</text>\n'
        # 二极管本体：三角形 + 阴极竖线（尖端朝右 = 电流 A→K ✓）
        '  <polygon fill="#000000" stroke="none" points="16.2,4.68 16.2,10.44 21.96,7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.9" stroke-linecap="round" '
        'x1="21.96" y1="4.68" x2="21.96" y2="10.44"/>\n'
        # 阴极之后接到引脚 3
        '  <line fill="none" stroke="#787878" stroke-width="0.75" stroke-linecap="round" '
        'x1="21.96" y1="7.56" x2="43.55" y2="7.56"/>\n'
        # 引脚 3（K）—— 右侧引线
        '  <line class="pin" id="connector2pin" connectorname="3" fill="none" stroke="#787878" '
        'stroke-width="0.75" stroke-linecap="round" x1="43.55" y1="7.56" x2="57.951" y2="7.56"/>\n'
        '  <rect class="terminal" id="connector2terminal" x="57.951" y="7.56" width="0.0001" '
        'height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 50.06 6.51)" fill="#8C8C8C" font-family="DroidSans" '
        'font-size="2.5">3</text>\n'
        # 引脚 2（n.c.）—— 独立短引线，不与符号相连 ✓
        '  <line class="pin" id="connector1pin" connectorname="2" fill="none" stroke="#787878" '
        'stroke-width="0.75" stroke-linecap="round" x1="29.15" y1="17.2" x2="29.15" y2="29.159"/>\n'
        '  <rect class="terminal" id="connector1terminal" x="29.15" y="29.159" width="0.0001" '
        'height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 26.0 27.8)" fill="#8C8C8C" font-family="DroidSans" '
        'font-size="2.5">2</text>\n'
        '  <text transform="matrix(1 0 0 1 31.4 26.9)" fill="#8C8C8C" font-family="DroidSans" '
        'font-size="2.2">nc</text>\n'
        ' </g>\n'
        '</svg>\n'
    )
    return s


# --------------------------------------------------------- breadboard view
def breadboard_svg():
    """SOT-23-3 chip on the breadboard (Sparkfun BAV99 style), marking **KL1**.

    三个焊盘与 `BAT54S` 完全同坐标 ✓（同一个封装 ✓）：
      pin1 (63.5, 334) 左下｜pin2 (163.5, 334) 右下｜pin3 (163.5, 34) 右上
    横向 100 单位 = 2.54 mm（一列）、纵向 300 单位 = 3 行 ✓。
    """
    s = (
        "<?xml version='1.0' encoding='UTF-8' standalone='no'?>\n"
        '<svg xmlns="http://www.w3.org/2000/svg" width="0.259in" x="0in" version="1.2" y="0in" '
        'height="0.4in" viewBox="0 0 259 400" baseProfile="tiny" '
        'xmlns:svg="http://www.w3.org/2000/svg">\n'
        ' <g id="breadboard">\n'
        '  <g id="icon">\n'
        '   <path fill="#1F7A34" stroke="none" stroke-width="0" '
        'd="M0,0L0,170A30,30 0 0 1 0,230L0,400L259,400L259,0L0,0z"/>\n'
        '   <g transform="translate(70.5,129.134)">\n'
        '    <g transform="matrix(1.0, 0, 0, 0.5, 0, 35.4331)">\n'
        '     <rect width="39.3701" x="39.315" y="0" fill="#8c8c8c" connectorname="3" '
        'height="55.118" stroke="none" stroke-linecap="round" stroke-width="0"/>\n'
        '     <rect width="39.3701" x="76.7165" y="86.614" fill="#8c8c8c" connectorname="2" '
        'height="55.118" stroke="none" stroke-linecap="round" stroke-width="0"/>\n'
        '     <rect width="39.3701" x="1.91339" y="86.614" fill="#8c8c8c" connectorname="1" '
        'height="55.118" stroke="none" stroke-linecap="round" stroke-width="0"/>\n'
        '     <rect width="118" x="0" y="19.8661" fill="#303030" height="102" stroke="none" '
        'stroke-width="0"/>\n'
        '     <polygon fill="#1f1f1f" points="0,19.8661 118,19.8661 108,29.8661 10,29.8661"/>\n'
        '     <polygon fill="#1f1f1f" points="0,121.866 118,121.866 108,111.866 10,111.866"/>\n'
        '     <polygon fill="#000000" points="0,19.8661 0,121.866 10,111.866 10,29.8661"/>\n'
        '     <polygon fill="#3d3d3d" points="118,19.8661 118,121.866 108,111.866 108,29.8661"/>\n'
        '    </g>\n'
        '   </g>\n'
        # 丝印：KL1（Nexperia BAT54 的 marking ✓；`BAT54S` 那颗写的是 KL4 ✓）
        '   <text x="129.5" y="285" font-family="OCRA" fill="white" text-anchor="middle" '
        'stroke="none" id="label" stroke-width="0" font-size="50">KL1</text>\n'
        '   <circle fill="#c0c0c0" cx="92.1" cy="200" r="10" stroke="none" stroke-width="0"/>\n'
        '   <g transform="translate(93,326.05)">\n'
        '    <g transform="rotate(-90)">\n'
        '     <text x="0" y="0" font-family="OCRA" fill="white" text-anchor="start" stroke="none" '
        'stroke-width="0" font-size="45">1</text>\n'
        '    </g>\n'
        '   </g>\n'
        '   <g transform="translate(193,326.05)">\n'
        '    <g transform="rotate(-90)">\n'
        '     <text x="0" y="0" font-family="OCRA" fill="white" text-anchor="start" stroke="none" '
        'stroke-width="0" font-size="45">2</text>\n'
        '    </g>\n'
        '   </g>\n'
        '   <g transform="translate(193,73.95)">\n'
        '    <g transform="rotate(-90)">\n'
        '     <text x="0" y="0" font-family="OCRA" fill="white" text-anchor="end" stroke="none" '
        'stroke-width="0" font-size="45">3</text>\n'
        '    </g>\n'
        '   </g>\n'
        '  </g>\n'
    )
    # connector pads（Sparkfun 原图 ✓，与 BAT54S 同一个坐标 ✓）
    pad = (
        '   <rect width="31.93" x="0" y="0" fill="#8D8C8C" height="31.9" id="{0}"/>\n'
        '   <rect width="16.4442" x="7.79153" y="7.73544" fill="#8C8663" height="16.4152"/>\n'
        '   <polygon fill="#B8AF82" points="0,31.9,7.79153,24.1368,7.79153,6.97162,0,0"/>\n'
        '   <polygon fill="#80795B" points="24.2079,7.76321,7.90264,7.76321,0,0,31.93,0"/>\n'
        '   <polygon fill="#5E5B43" points="24.2079,24.1368,24.2079,7.76321,31.93,0,31.93,31.9"/>\n'
        '   <polygon fill="#9A916C" points="0,31.9,7.87486,24.1368,24.2079,24.1368,31.93,31.9"/>\n'
    )
    for cid, (tx, ty) in [('connector0pin', (63.535, 334.05)),
                          ('connector1pin', (163.535, 334.05)),
                          ('connector2pin', (163.535, 34.05))]:
        s += '  <g transform="translate(%s,%s)">\n' % (tx, ty)
        s += pad.format(cid)
        s += '  </g>\n'
    s += ' </g>\n'
    s += "</svg>\n"
    return s


# ---------------------------------------------------------------- icon view
def icon_svg():
    """32x32 icon: SOT-23-3 chip (2.9x1.3 aspect) with 'KL1' top marking."""
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n'
    )
    s += '  <g id="breadboard">\n'
    s += '    <rect x="8" y="11.8" width="16" height="7.2" rx="1" ry="1" fill="#303030" stroke="none"/>\n'
    s += '    <circle cx="11.8" cy="17.6" r="0.8" fill="#c0c0c0" stroke="none"/>\n'
    s += ('    <text x="16.5" y="17.2" font-family="sans-serif" font-size="4.5" font-weight="bold" '
          'fill="#c0c0c0" text-anchor="middle">KL1</text>\n')
    s += '    <rect x="10.6" y="19.0" width="2.4" height="2.4" fill="#8d8c8c"/>\n'
    s += '    <rect x="19.0" y="19.0" width="2.4" height="2.4" fill="#8d8c8c"/>\n'
    s += '    <rect x="14.8" y="9.4" width="2.4" height="2.4" fill="#8d8c8c"/>\n'
    s += '  </g>\n'
    s += "</svg>\n"
    return s


# ------------------------------------------------------------------ .fzp
def fzp_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>BAT54</title>\n'
        ' <label>D</label>\n'
        ' <date>2026-11-27</date>\n'
        ' <tags><tag>diode</tag><tag>schottky</tag><tag>BAT54</tag><tag>SOT-23</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">Diode</property>\n'
        '  <property name="type">Schottky</property>\n'
        '  <property name="part number">BAT54</property>\n'
        '  <property name="package">SOT23-3</property>\n'
        '  <property name="forward voltage">0.32V @ 1mA</property>\n'
        '  <property name="reverse voltage">30V</property>\n'
        '  <property name="forward current">200mA</property>\n'
        ' </properties>\n'
        ' <description>Single Schottky diode, SOT-23 (marking KL1). '
        'Anode = pin 1, cathode = pin 3, pin 2 n.c.</description>\n'
        ' <views>\n'
        '  <iconView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="icon"/>\n'
        '   </layers>\n'
        '  </iconView>\n'
        '  <breadboardView fliphorizontal="true" flipvertical="true">\n'
        '   <layers image="%s">\n'
        '    <layer layerId="breadboard"/>\n'
        '   </layers>\n'
        '  </breadboardView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true">\n'
        '   <layers image="%s">\n'
        '    <layer layerId="schematic"/>\n'
        '   </layers>\n'
        '  </schematicView>\n'
        '  <pcbView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="silkscreen"/>\n'
        '    <layer layerId="copper1"/>\n'
        '   </layers>\n'
        '  </pcbView>\n'
        ' </views>\n'
        ' <connectors>\n'
        '  <connector id="connector0" name="A" type="male">\n'
        '   <description>Pin 1 - anode</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector0pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector0pin" '
        'terminalId="connector0terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector0pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector1" name="NC" type="male">\n'
        '   <description>Pin 2 - not connected</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector1pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector1pin" '
        'terminalId="connector1terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector1pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector2" name="K" type="male">\n'
        '   <description>Pin 3 - cathode</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector2pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector2pin" '
        'terminalId="connector2terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector2pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        ' </connectors>\n'
        '</module>\n'
    ) % (PART_ID, ICON_REF, BB_REF, SCHEM_REF, PCB_REF)


def main():
    files = {
        PCB_SVG: pcb_svg(),
        SCHEM_SVG: schematic_svg(),
        BB_SVG: breadboard_svg(),
        ICON_SVG: icon_svg(),
        FZP: fzp_xml(),
    }
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)

    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
