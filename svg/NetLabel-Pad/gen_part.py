# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part: NetLabel-Pad.

A net-label style part whose PCB footprint is a round through-hole pad
matching the 2.54mm pin-header footprint of svg/TFTSPI1.9in pcb
(outer ~2.0 mm / hole ~1.0 mm — standard 2.54mm header pad).

Views:
  - schematic: wire stub + junction dot (no label text), compact — right
               blank trimmed.
  - pcb:       round through-hole pad (copper0 > copper1 nesting, single
               pad ellipse ring on both layers).
               Pad = ellipse rx=0.737 / stroke=0.508 -> outer ~1.98 mm /
               hole ~0.97 mm (exact match to svg/TFTSPI1.9in pcb).
  - icon:      32x32 round pad.
  No breadboard view (schematic + PCB only).

Single connector0 (through-hole, maps to copper0 + copper1).

Follows the Fritzing part-dev-guide (docs/part-dev-guide.md) and the
BAT54S gen_part.py conventions:
  - .fzp image refs use subdirectory paths
  - schematic pins class='pin'/connectorname + class='terminal'
  - .fzpz goes to the repo-level fzpz/ directory
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "NetLabel-Pad_1"

# View SVG filenames (flat inside fzpz)
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "NetLabel-Pad.fzpz"

# .fzp image refs (subdirectory style, per guide)
PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# Pad geometry (mm) — exact match to svg/TFTSPI1.9in pcb 2.54mm pin-header
# footprint (circle r=29mil, stroke=20mil, 100mil pitch):
#   outer = r + stroke/2 = 39 mil = 0.991 mm
#   hole  = r - stroke/2 = 19 mil = 0.483 mm
# ellipse ring: outer = rx + stroke/2 = 0.991, hole = rx - stroke/2 = 0.483
#   => rx = 0.737 mm, stroke = 0.508 mm
PAD_R = 0.737        # ellipse centerline radius
PAD_STROKE = 0.508   # copper ring width


# ---------------------------------------------------------------- PCB view
def pcb_svg():
    """Round through-hole pad (TFTSPI1.9in header style): copper0 > copper1
    nesting with a single pad ellipse (stroke ring) on both layers."""
    s = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="3mm" height="3mm" viewBox="-1.5 -1.5 3 3">\n'
        '  <g id="copper0">\n'
        '    <g id="copper1">\n'
        '      <circle id="connector0pad" connectorname="PAD" cx="0" cy="0" r="%g" fill="none" stroke="#f7bf13" stroke-width="%g"/>\n'
        '    </g>\n'
        '  </g>\n'
        '</svg>\n'
    ) % (PAD_R, PAD_STROKE)
    return s


# ---------------------------------------------------------- schematic view
def schematic_svg():
    """Compact symbol: wire stub from the left + junction dot. No label text
    (removed per user), right blank trimmed to fit content."""
    s = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        'x="0px" y="0px" width="9px" height="12px" viewBox="0 0 9 12" xml:space="preserve">\n'
        ' <g id="schematic">\n'
        # wire stub (left) — where the net wire connects
        '  <line class="pin" id="connector0pin" connectorname="PAD" fill="none" stroke="#787878" stroke-width="0.75" stroke-linecap="round" x1="0.35" y1="6" x2="5.5" y2="6"/>\n'
        # junction dot
        '  <circle cx="6" cy="6" r="0.8" fill="none" stroke="#000000" stroke-width="0.5"/>\n'
        # terminal (degenerate rect at pin outer end)
        '  <rect class="terminal" id="connector0terminal" x="0.35" y="6" width="0.0001" height="0.0001" fill="none" stroke="none" stroke-width="0"/>\n'
        ' </g>\n'
        '</svg>\n'
    )
    return s


# ---------------------------------------------------------------- icon view
def icon_svg():
    """32x32 icon = the PCB pad graphic itself (gold ring, open transparent
    hole), using the SAME viewBox as the pcb view so the ring shows at the
    same relative size in the inspector (symmetric with the PCB thumbnail)."""
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="-1.5 -1.5 3 3">\n'
        '  <g id="breadboard">\n'
        '    <circle cx="0" cy="0" r="%g" fill="none" stroke="#f7bf13" stroke-width="%g"/>\n'
        '  </g>\n'
        "</svg>\n"
    ) % (PAD_R, PAD_STROKE)
    return s


# ------------------------------------------------------------------ .fzp
def fzp_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="NetLabel-Pad">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>NET LABEL PAD</title>\n'
        ' <label>P</label>\n'
        ' <date>2026-08-30</date>\n'
        ' <tags><tag>net label</tag><tag>pad</tag><tag>through-hole</tag><tag>header</tag><tag>test point</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">connector</property>\n'
        '  <property name="type">through-hole pad</property>\n'
        '  <property name="part number">NetLabel-Pad</property>\n'
        '  <property name="package">PAD-2.0-H1.0</property>\n'
        ' </properties>\n'
        ' <description>Net label that becomes a round through-hole pad on the PCB (2.0 mm pad / 1.0 mm hole, 2.54mm header-compatible). No breadboard view.</description>\n'
        ' <views>\n'
        '  <iconView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="icon"/>\n'
        '   </layers>\n'
        '  </iconView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true">\n'
        '   <layers image="%s">\n'
        '    <layer layerId="schematic"/>\n'
        '   </layers>\n'
        '  </schematicView>\n'
        '  <pcbView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="copper1"/>\n'
        '    <layer layerId="copper0"/>\n'
        '   </layers>\n'
        '  </pcbView>\n'
        ' </views>\n'
        ' <connectors>\n'
        '  <connector id="connector0" name="PAD" type="male">\n'
        '   <description>Through-hole round pad (header pin capable)</description>\n'
        '   <views>\n'
        '    <schematicView><p layer="schematic" svgId="connector0pin" terminalId="connector0terminal"/></schematicView>\n'
        '    <pcbView>\n'
        '     <p layer="copper0" svgId="connector0pad"/>\n'
        '     <p layer="copper1" svgId="connector0pad"/>\n'
        '    </pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        ' </connectors>\n'
        '</module>\n'
    ) % (ICON_REF, SCHEM_REF, PCB_REF)


def main():
    files = {
        PCB_SVG: pcb_svg(),
        SCHEM_SVG: schematic_svg(),
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
