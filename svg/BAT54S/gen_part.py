# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for BAT54S (SOT-23 dual Schottky).

BAT54S is a SOT-23 package containing TWO series-connected Schottky
diodes:
    pin 1 = D1 anode (A1)
    pin 3 = internal node (D1 cathode + D2 anode)
    pin 2 = D2 cathode (K2)
So current flows pin1 ->[D1]-> pin3 ->[D2]-> pin2.

Connectors (3):
    connector0 = pin 1 (A1)
    connector1 = pin 2 (K2)
    connector2 = pin 3 (node)

Follows the Fritzing part-dev-guide (docs/part-dev-guide.md):
  - .fzp image refs use subdirectory paths
  - schematic pins need class='pin'/connectorname + class='terminal'
  - PCB pads appear once, on copper1 (SMD package, no through-hole)
  - .fzpz goes to the repo-level fzpz/ directory

Reference parts:
  - pcb:      core/pcb/SMD_SOT-23.svg (official 3-pad SOT-23)
  - breadboard: core/breadboard/sparkfun-discretesemi_sot23-3_breadboard.svg
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "BAT54S_SOT23_1"

# View SVG filenames (flat inside fzpz)
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "BAT54S.fzpz"

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
        # bottom-left pad (pin1)
        '    <rect width="80" height="90" x="15" y="200" id="connector0pin" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
        '    <rect width="0" height="0" x="55" y="245" id="connector0terminal" style="fill:none;stroke-width:0"/>\n'
        # bottom-right pad (pin2)
        '    <rect width="80" height="90" x="205" y="200" id="connector1pin" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
        '    <rect width="0" height="0" x="245" y="245" id="connector1terminal" style="fill:none;stroke-width:0"/>\n'
        # top-center pad (pin3)
        '    <rect width="80" height="90" x="110" y="0" id="connector2pin" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
        '    <rect width="0" height="0" x="150" y="45" id="connector2terminal" style="fill:none;stroke-width:0"/>\n'
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
    """Dual series diode symbol inside a SOT-23 package box (Sparkfun BAV99 style).

    White package outline with the two series-connected diodes inside:
        connector0 (pin1/A1) --[D1]-- node --[D2]-- connector1 (pin2/K2)
    connector2 (pin3/node) leaves the bottom of the box.
    Connector pins carry class='pin' + class='terminal' (per guide).
    """
    s = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        'x="0px" y="0px" width="58.3px" height="29.51px" viewBox="0 0 58.3 29.51" xml:space="preserve">\n'
        ' <g id="schematic">\n'
        # package outline (SOT-23 box)
        '  <polygon fill="#FFFFFF" stroke="#000000" stroke-width="0.9" stroke-linecap="round" points="14.75,14.76 29.15,14.76 43.55,14.76 43.55,7.56 43.55,0.36 14.75,0.36 14.75,7.56"/>\n'
        # D1 (left diode): A1 -> anode -> bar -> node
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="14.75" y1="7.56" x2="19.07" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="19.07" y1="7.56" x2="19.07" y2="4.68"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="19.07" y1="4.68" x2="24.11" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="24.11" y1="7.56" x2="19.07" y2="10.44"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="19.07" y1="10.44" x2="19.07" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="24.11" y1="4.68" x2="24.11" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="24.11" y1="7.56" x2="24.11" y2="10.44"/>\n'
        # D2 (right diode): node -> anode -> bar -> K2
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="39.23" y1="4.68" x2="39.23" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="39.23" y1="7.56" x2="39.23" y2="10.44"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="39.23" y1="7.56" x2="34.19" y2="10.44"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="34.19" y1="4.68" x2="39.23" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="34.19" y1="10.44" x2="34.19" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="34.19" y1="7.56" x2="34.19" y2="4.68"/>\n'
        # node bus inside the box
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="34.19" y1="7.56" x2="29.15" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="29.15" y1="7.56" x2="24.11" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="43.55" y1="7.56" x2="39.23" y2="7.56"/>\n'
        '  <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" x1="29.15" y1="14.76" x2="29.15" y2="7.56"/>\n'
        # connector0 = pin1 (A1) on the left
        '  <line class="pin" id="connector0pin" connectorname="1" fill="none" stroke="#787878" stroke-width="0.75" stroke-linecap="round" x1="0.35" y1="7.56" x2="14.75" y2="7.56"/>\n'
        '  <rect class="terminal" id="connector0terminal" x="0.35" y="7.56" width="0.0001" height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 6.86 6.51)" fill="#8C8C8C" font-family="DroidSans" font-size="2.5">1</text>\n'
        # connector1 = pin2 (K2) on the right
        '  <line class="pin" id="connector1pin" connectorname="2" fill="none" stroke="#787878" stroke-width="0.75" stroke-linecap="round" x1="57.951" y1="7.56" x2="43.55" y2="7.56"/>\n'
        '  <rect class="terminal" id="connector1terminal" x="57.951" y="7.56" width="0.0001" height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 50.06 6.51)" fill="#8C8C8C" font-family="DroidSans" font-size="2.5">2</text>\n'
        # connector2 = pin3 (node) at the bottom
        '  <line class="pin" id="connector2pin" connectorname="3" fill="none" stroke="#787878" stroke-width="0.75" stroke-linecap="round" x1="29.15" y1="29.159" x2="29.15" y2="14.76"/>\n'
        '  <rect class="terminal" id="connector2terminal" x="29.15" y="29.159" width="0.0001" height="0.0001" stroke="none" stroke-width="0" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 26.0 27.8)" fill="#8C8C8C" font-family="DroidSans" font-size="2.5">3</text>\n'
        ' </g>\n'
        '</svg>\n'
    )
    return s


# --------------------------------------------------------- breadboard view
def breadboard_svg():
    """SOT-23-3 chip drawn directly on the breadboard (Sparkfun BAV99 style).

    Faithfully mirrors the proven Sparkfun part
    'sparkfun-discretesemi_sot23_breadboard.svg' (viewBox 0 0 259 400):
    the SOT-23 chip straddles the breadboard centre channel and its three
    leads land on the breadboard grid:
      - pin1 connector at (63.5, 334)  bottom-left
      - pin2 connector at (163.5, 334) bottom-right
      - pin3 connector at (163.5, 34)  top-right
    horizontal pitch 100 units = 2.54 mm, vertical 300 units = 3 rows.
    Customised for BAT54S: silver 'KL4' marking on the body and a silver
    pin-1 dot directly above the pin-1 pad.
    """
    s = (
        "<?xml version='1.0' encoding='UTF-8' standalone='no'?>\n"
        '<svg xmlns="http://www.w3.org/2000/svg" width="0.259in" x="0in" version="1.2" y="0in" height="0.4in" viewBox="0 0 259 400" baseProfile="tiny" xmlns:svg="http://www.w3.org/2000/svg">\n'
        ' <g id="breadboard">\n'
        '  <g id="icon">\n'
        '   <path fill="#1F7A34" stroke="none" stroke-width="0" d="M0,0L0,170A30,30 0 0 1 0,230L0,400L259,400L259,0L0,0z"/>\n'
        '   <g transform="translate(70.5,129.134)">\n'
        '    <g transform="matrix(1.0, 0, 0, 0.5, 0, 35.4331)">\n'
        '     <rect width="39.3701" x="39.315" y="0" fill="#8c8c8c" connectorname="3" height="55.118" stroke="none" stroke-linecap="round" stroke-width="0"/>\n'
        '     <rect width="39.3701" x="76.7165" y="86.614" fill="#8c8c8c" connectorname="2" height="55.118" stroke="none" stroke-linecap="round" stroke-width="0"/>\n'
        '     <rect width="39.3701" x="1.91339" y="86.614" fill="#8c8c8c" connectorname="1" height="55.118" stroke="none" stroke-linecap="round" stroke-width="0"/>\n'
        '     <rect width="118" x="0" y="19.8661" fill="#303030" height="102" stroke="none" stroke-width="0"/>\n'
        '     <polygon fill="#1f1f1f" points="0,19.8661 118,19.8661 108,29.8661 10,29.8661"/>\n'
        '     <polygon fill="#1f1f1f" points="0,121.866 118,121.866 108,111.866 10,111.866"/>\n'
        '     <polygon fill="#000000" points="0,19.8661 0,121.866 10,111.866 10,29.8661"/>\n'
        '     <polygon fill="#3d3d3d" points="118,19.8661 118,121.866 108,111.866 108,29.8661"/>\n'
        '    </g>\n'
        '   </g>\n'
        '   <circle fill="#c0c0c0" cx="92.1" cy="200" r="10" stroke="none" stroke-width="0"/>\n'
        '   <text x="129.5" y="285" font-family="OCRA" fill="white" text-anchor="middle" stroke="none" id="label" stroke-width="0" font-size="50">SOT23</text>\n'
        '   <g transform="translate(93,326.05)">\n'
        '    <g transform="rotate(-90)">\n'
        '     <text x="0" y="0" font-family="OCRA" fill="white" text-anchor="start" stroke="none" stroke-width="0" font-size="45">1</text>\n'
        '    </g>\n'
        '   </g>\n'
        '   <g transform="translate(193,326.05)">\n'
        '    <g transform="rotate(-90)">\n'
        '     <text x="0" y="0" font-family="OCRA" fill="white" text-anchor="start" stroke="none" stroke-width="0" font-size="45">2</text>\n'
        '    </g>\n'
        '   </g>\n'
        '   <g transform="translate(193,73.95)">\n'
        '    <g transform="rotate(-90)">\n'
        '     <text x="0" y="0" font-family="OCRA" fill="white" text-anchor="end" stroke="none" stroke-width="0" font-size="45">3</text>\n'
        '    </g>\n'
        '   </g>\n'
        '  </g>\n'
    )
    # connector pads (verbatim Sparkfun pad artwork)
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
    """32x32 icon: SOT-23-3 chip (2.9x1.3 aspect) with 'KL4' top marking."""
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n'
    )
    s += '  <g id="breadboard">\n'
    s += '    <rect x="8" y="11.8" width="16" height="7.2" rx="1" ry="1" fill="#303030" stroke="none"/>\n'
    s += '    <circle cx="11.8" cy="17.6" r="0.8" fill="#c0c0c0" stroke="none"/>\n'
    s += '    <text x="16.5" y="17.2" font-family="sans-serif" font-size="4.5" font-weight="bold" fill="#c0c0c0" text-anchor="middle">KL4</text>\n'
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
        ' <title>BAT54S</title>\n'
        ' <label>D</label>\n'
        ' <date>2026-08-24</date>\n'
        ' <tags><tag>diode</tag><tag>schottky</tag><tag>BAT54S</tag><tag>SOT-23</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">diode</property>\n'
        '  <property name="type">Schottky</property>\n'
        '  <property name="part number">BAT54S</property>\n'
        '  <property name="package">SOT23-3</property>\n'
        ' </properties>\n'
        ' <description>Dual series Schottky diode, SOT-23. Two diodes: pin1->pin3->pin2.</description>\n'
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
        '  <connector id="connector0" name="A1" type="male">\n'
        '   <description>Pin 1 - diode 1 anode</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector0pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector0pin" terminalId="connector0terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector0pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector1" name="K2" type="male">\n'
        '   <description>Pin 2 - diode 2 cathode</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector1pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector1pin" terminalId="connector1terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector1pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector2" name="node" type="male">\n'
        '   <description>Pin 3 - internal node (D1 cathode + D2 anode)</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector2pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector2pin" terminalId="connector2terminal"/></schematicView>\n'
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
