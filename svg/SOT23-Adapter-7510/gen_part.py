# -*- coding: utf-8 -*-
"""Generate a Fritzing part for the **SOT-23 → 2.54 mm 转接小板（7.5 × 10 mm）**。

用户买到的现货（`佳芯维电子`）：绿油小板 **7.5 × 10 mm**，一端是 SOT-23 的 3 个 SMD 焊盘，
另一端是 3 个 2.54 mm 过孔焊盘；**丝印左→右读 = `2 3 1`** ✓：

    ┌──────────────┐   ↑ 10 mm
    │   ▪     ▪    │   SOT-23 两个焊盘（pin 2 / pin 1）
    │      ▪       │   SOT-23 一个焊盘（pin 3）
    │  2   3   1   │   丝印编号：左 = pad 2、中 = pad 3、右 = pad 1
    │  ○   ○   ○   │   3 个 2.54 mm 过孔（插面包板）
    └──────────────┘
        ← 7.5 mm →

⇒ 插进面包板以后，**三个脚落在同一行、脚序是 `2 3 1`**（不是 `1 2 3` ✗）——
  这跟"裸 SOT-23 直接插面包板"的假图完全不一样 ✗，也是本件存在的理由 ✓。

Connectors (3) —— **按丝印编号**，方便对图查线：
    connector0 = pad **1**（右）
    connector1 = pad **2**（左）
    connector2 = pad **3**（中）
⇒ 板子上装 `BAT54S` 时：pad1 = `A1`、pad2 = `K2`、pad3 = 中点（`K1+A2`）✓
   （与 `BAT54S_SOT23_1` 的连接器编号一致 ✓ ⇒ 台架图上可以直接换件 ✓）

Follows the Fritzing part-dev-guide (docs/part-dev-guide.md):
  - .fzp image refs use subdirectory paths
  - schematic pins need class='pin'/connectorname + class='terminal'
  - PCB 是**过孔**件 ⇒ 焊盘同时出现在 copper0 / copper1（口径同 `PinHeader-1x3` ✓）
  - .fzpz goes to the repo-level fzpz/ directory
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "SOT23-Adapter-7510"

PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "%s.fzpz" % PART_ID

PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# ── 面包板视图几何（单位 = 0.001 in，与 core 件同口径：1 单位 = 0.072 单位/sketch）──
BB_W, BB_H = 295.2756, 393.7008          # 7.5 mm × 10 mm
PAD_Y = 50.0                             # 过孔焊盘那一行贴画布上缘 ⇒ 板子往**下**挂 ✓
PAD_X = {"connector1pin": 47.6378,       # 左  = pad 2
         "connector2pin": 147.6378,      # 中  = pad 3
         "connector0pin": 247.6378}      # 右  = pad 1
PAD_NAME = {"connector0pin": "1", "connector1pin": "2", "connector2pin": "3"}


# ---------------------------------------------------------- breadboard view
def breadboard_svg():
    """7.5×10 mm 绿板 + 3 个 2.54 mm 过孔 + 丝印 `2 3 1` + SOT-23 焊盘与走线。"""
    s = '<?xml version="1.0" encoding="utf-8"?>\n'
    s += ('<svg xmlns="http://www.w3.org/2000/svg" width="7.5mm" height="10mm" '
          'viewBox="0 0 %.4f %.4f">\n' % (BB_W, BB_H))
    s += ' <g id="breadboard">\n'
    s += ('  <rect x="0" y="0" width="%.4f" height="%.4f" fill="#00aa44" '
          'stroke="#00772f" stroke-width="3"/>\n' % (BB_W, BB_H))
    # 绿油下的铜（比板面略深）
    s += ('  <path d="M 47.6378,84 L 47.6378,180 L 110.3,232 L 110.3,268" fill="none" '
          'stroke="#0a9b46" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>\n')
    s += ('  <path d="M 247.6378,84 L 247.6378,180 L 185,232 L 185,268" fill="none" '
          'stroke="#0a9b46" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>\n')
    s += ('  <line x1="147.6378" y1="84" x2="147.6378" y2="268" stroke="#0a9b46" '
          'stroke-width="16" stroke-linecap="round"/>\n')
    # SOT-23 三个焊盘（上二下一）
    for cx, cy in ((110.3, 290.0), (185.0, 290.0), (147.6378, 212.0)):
        s += ('  <rect x="%.4f" y="%.4f" width="44" height="46" rx="4" fill="#c9c9c9" '
              'stroke="#8c8c8c" stroke-width="2"/>\n' % (cx - 22, cy - 23))
    # 丝印：pin1 圆点 + 编号 2 / 3 / 1（左→右）
    s += '  <circle cx="%.4f" cy="188" r="8" fill="#ffffff" stroke="none"/>\n' % 147.6378
    for cid, cx in sorted(PAD_X.items()):
        s += ('  <text x="%.4f" y="132" font-family="OCRA" font-size="58" fill="#ffffff" '
              'text-anchor="middle" stroke="none">%s</text>\n' % (cx, PAD_NAME[cid]))
    # 过孔焊盘（连接点 = 圆心 ✓）
    for cid, cx in sorted(PAD_X.items()):
        s += ('  <circle id="%s" connectorname="%s" cx="%.4f" cy="%.1f" r="32" fill="#f7bf13" '
              'stroke="#b98900" stroke-width="4"/>\n' % (cid, PAD_NAME[cid], cx, PAD_Y))
        s += ('  <circle cx="%.4f" cy="%.1f" r="14" fill="#eeeeee" stroke="#b98900" '
              'stroke-width="2"/>\n' % (cx, PAD_Y))
    s += ' </g>\n</svg>\n'
    return s


# ---------------------------------------------------------- schematic view
def schematic_svg():
    """`BAT54S` 的双串联肖特基符号（1 →|>|→ 3 →|>|→ 2），脚号与丝印一致 ✓"""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" '
        'width="0.6477778in" height="0.3278889in" viewBox="0 0 58.3 29.51" '
        'xml:space="preserve">\n'
        ' <g id="schematic">\n'
        '  <polygon fill="#FFFFFF" stroke="#000000" stroke-width="0.9" stroke-linecap="round" '
        'points="14.75,14.76 29.15,14.76 43.55,14.76 43.55,7.56 43.55,0.36 14.75,0.36 14.75,7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="14.75" y1="7.56" x2="19.07" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="19.07" y1="7.56" x2="19.07" y2="4.68"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="19.07" y1="4.68" x2="24.11" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="24.11" y1="7.56" x2="19.07" y2="10.44"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="19.07" y1="10.44" x2="19.07" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="24.11" y1="4.68" x2="24.11" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="24.11" y1="7.56" x2="24.11" y2="10.44"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="39.23" y1="4.68" x2="39.23" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="39.23" y1="7.56" x2="39.23" y2="10.44"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="39.23" y1="7.56" x2="34.19" y2="10.44"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="34.19" y1="4.68" x2="39.23" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="34.19" y1="10.44" x2="34.19" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="34.19" y1="7.56" x2="34.19" y2="4.68"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="34.19" y1="7.56" x2="29.15" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="29.15" y1="7.56" x2="24.11" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="43.55" y1="7.56" x2="39.23" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
        'x1="29.15" y1="14.76" x2="29.15" y2="7.56"/>\n'
        '  <line class="pin" id="connector0pin" connectorname="1" fill="none" '
        'stroke="#787878" stroke-width="0.75" stroke-linecap="round" '
        'x1="0.35" y1="7.56" x2="14.75" y2="7.56"/>\n'
        '  <rect class="terminal" id="connector0terminal" x="0.35" y="7.56" width="0.0001" '
        'height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 6.86 6.51)" fill="#8C8C8C" font-family="DroidSans" '
        'font-size="2.5">1</text>\n'
        '  <line class="pin" id="connector1pin" connectorname="2" fill="none" '
        'stroke="#787878" stroke-width="0.75" stroke-linecap="round" '
        'x1="57.951" y1="7.56" x2="43.55" y2="7.56"/>\n'
        '  <rect class="terminal" id="connector1terminal" x="57.951" y="7.56" width="0.0001" '
        'height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 50.06 6.51)" fill="#8C8C8C" font-family="DroidSans" '
        'font-size="2.5">2</text>\n'
        '  <line class="pin" id="connector2pin" connectorname="3" fill="none" '
        'stroke="#787878" stroke-width="0.75" stroke-linecap="round" '
        'x1="29.15" y1="29.159" x2="29.15" y2="14.76"/>\n'
        '  <rect class="terminal" id="connector2terminal" x="29.15" y="29.159" width="0.0001" '
        'height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 26.0 27.8)" fill="#8C8C8C" font-family="DroidSans" '
        'font-size="2.5">3</text>\n'
        ' </g>\n'
        '</svg>\n'
    )


# ----------------------------------------------------------------- pcb view
def pcb_svg():
    """过孔件：3 个 2.0 mm 焊盘 / 1.0 mm 孔，2.54 mm 脚距；丝印 7.5×10 外廓 ✓"""
    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += ('<svg xmlns="http://www.w3.org/2000/svg" width="7.5mm" height="10mm" '
          'viewBox="-3.75 -5 7.5 10">\n')
    s += ' <g id="copper1">\n  <g id="copper0">\n'
    for cid, name, cx in (("connector0pad", "1", 2.54),
                          ("connector1pad", "2", -2.54),
                          ("connector2pad", "3", 0.0)):
        s += ('   <circle id="%s" connectorname="%s" cx="%.2f" cy="3.5" r="1.0" '
              'fill="none" stroke="#f7bf13" stroke-width="0.5"/>\n' % (cid, name, cx))
        s += ('   <circle cx="%.2f" cy="3.5" r="0.45" fill="#0d0d0d" stroke="none"/>\n' % cx)
    s += '  </g>\n </g>\n'
    s += ' <g id="silkscreen">\n'
    s += ('  <rect x="-3.75" y="-5" width="7.5" height="10" fill="none" stroke="#f0f0f0" '
          'stroke-width="0.12"/>\n')
    for txt, tx in (("2", -2.54), ("3", 0.0), ("1", 2.54)):
        s += ('  <text x="%.2f" y="1.6" font-family="OCRA" font-size="0.9" fill="#f0f0f0" '
              'text-anchor="middle" stroke="none">%s</text>\n' % (tx, txt))
    s += ' </g>\n</svg>\n'
    return s


# ---------------------------------------------------------------- icon view
def icon_svg():
    """32×32 icon：绿小板 + 3 个金焊盘，一眼能认出是什么 ✓"""
    s = ('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n')
    s += '  <g id="breadboard">\n'
    s += ('    <rect x="9" y="3" width="14" height="26" rx="1" ry="1" fill="#00aa44" '
          'stroke="#00772f" stroke-width="0.8"/>\n')
    s += '    <rect x="12.4" y="6" width="3" height="3.4" fill="#c9c9c9"/>\n'
    s += '    <rect x="16.6" y="6" width="3" height="3.4" fill="#c9c9c9"/>\n'
    s += '    <rect x="15" y="11.5" width="2" height="2.4" fill="#c9c9c9"/>\n'
    for cx in (11.6, 16.0, 20.4):
        s += ('    <circle cx="%.1f" cy="24.4" r="1.9" fill="#f7bf13" stroke="#b98900" '
              'stroke-width="0.5"/>\n' % cx)
    s += '  </g>\n</svg>\n'
    return s


# ------------------------------------------------------------------- .fzp
def fzp_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>SOT-23 Adapter 7.5x10</title>\n'
        ' <label>U</label>\n'
        ' <date>2026-11-27</date>\n'
        ' <tags><tag>adapter</tag><tag>SOT-23</tag><tag>SOT23</tag>'
        '<tag>breakout</tag><tag>2.54mm</tag><tag>through-hole</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">breakout board</property>\n'
        '  <property name="package">THT 3-pin (2.54mm)</property>\n'
        '  <property name="size">7.5 x 10 mm</property>\n'
        '  <property name="pin order">2 3 1 (left to right)</property>\n'
        '  <property name="part number">SOT23-Adapter-7510</property>\n'
        ' </properties>\n'
        ' <description>SOT-23 to 2.54 mm breakout carrier, 7.5 x 10 mm. '
        'The three through-hole pads sit in ONE breadboard row; the order from left to '
        'right is 2-3-1 (pad 1 = SOT-23 pin 1, pad 2 = pin 2, pad 3 = pin 3).</description>\n'
        ' <views>\n'
        '  <iconView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="icon"/>\n'
        '   </layers>\n'
        '  </iconView>\n'
        '  <breadboardView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="breadboard"/>\n'
        '   </layers>\n'
        '  </breadboardView>\n'
        '  <schematicView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="schematic"/>\n'
        '   </layers>\n'
        '  </schematicView>\n'
        '  <pcbView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="copper1"/>\n'
        '    <layer layerId="copper0"/>\n'
        '    <layer layerId="silkscreen"/>\n'
        '   </layers>\n'
        '  </pcbView>\n'
        ' </views>\n'
        ' <connectors>\n'
        '  <connector id="connector0" name="1" type="male">\n'
        '   <description>Pad 1 (right) - SOT-23 pin 1</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector0pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector0pin" '
        'terminalId="connector0terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper0" svgId="connector0pad"/>'
        '<p layer="copper1" svgId="connector0pad"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector1" name="2" type="male">\n'
        '   <description>Pad 2 (left) - SOT-23 pin 2</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector1pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector1pin" '
        'terminalId="connector1terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper0" svgId="connector1pad"/>'
        '<p layer="copper1" svgId="connector1pad"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector2" name="3" type="male">\n'
        '   <description>Pad 3 (middle) - SOT-23 pin 3</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector2pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector2pin" '
        'terminalId="connector2terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper0" svgId="connector2pad"/>'
        '<p layer="copper1" svgId="connector2pad"/></pcbView>\n'
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
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as f:
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
