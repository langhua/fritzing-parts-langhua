# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for the NFC sensing coil.

Produces the four view SVGs + .fzp manifest + .fzpz package so the coil
can be dropped into the Fritzing part library and used in breadboard /
schematic / PCB views (2 connectors: inner end, outer end).

Files are written next to this script.

Connector layout:
    connector0 = coil inner end  (pad at r = INNER_R)
    connector1 = coil outer end  (pad at r = OUTER_R)
"""

import math
import os
import zipfile

# ---- coil geometry (must match gen_coil.py) ----
OUTER_R = 10.0      # mm
INNER_R = 4.0       # mm
TURNS = 6
TRACE_W = 0.2       # mm
PAD_R = 0.5         # mm
# single-coil breadboard/PCB artwork uses the array-safe outer radius
ARRAY_OUTER_R = 9.5  # mm (OD 19)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "NFC_Coil_20mm_6T_0p2_1"

# View SVG filenames (Fritzing convention inside fzpz: flat svg.* files)
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "NFC-Coil.fzpz"

# Standard Fritzing .fzp references images by SUBDIRECTORY path
# (icon/, breadboard/, schematic/, pcb/) even though the zip stores them
# as flat svg.* files. Fritzing relocates them on import.
ICON_REF = "icon/%s_icon.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
PCB_REF = "pcb/%s_pcb.svg" % PART_ID


def spiral_centerline(outer_r=OUTER_R):
    a = (outer_r - INNER_R) / (2.0 * math.pi * TURNS)
    n = int(TURNS * 120)
    pts = []
    for i in range(n + 1):
        theta = 2.0 * math.pi * TURNS * i / n
        r = INNER_R + a * theta
        pts.append((r * math.cos(theta), r * math.sin(theta)))
    return pts


def ribbon_path(outer_r=OUTER_R):
    pts = spiral_centerline(outer_r)
    half = TRACE_W / 2.0
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == len(pts) - 1:
            dx, dy = x - pts[-2][0], y - pts[-2][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(dx, dy)
        tx, ty = dx / L, dy / L
        nx, ny = -ty, tx
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))
    d = ["M %.3f %.3f" % left[0]]
    d += ["L %.3f %.3f" % p for p in left[1:]]
    d += ["L %.3f %.3f" % p for p in reversed(right)]
    d.append("Z")
    return " ".join(d), pts


# ---------------------------------------------------------------- PCB view
def pcb_svg():
    """Spiral coil as a through-hole PCB part.

    Mirrors the built-in inductor's PCB structure exactly:
      <g id="copper0">
        <g id="copper1">
          ...artwork + connector pins (each id ONCE)...
        </g>
      </g>
    The nested copper0>copper1 structure tells Fritzing these are
    through-hole vias connecting both layers - do NOT duplicate
    connector ids across separate layer groups.

    viewBox -12 -12 24 24 (24x24 mm), same as breadboard view.
    """
    d, pts = ribbon_path(OUTER_R)
    p_in = pts[0]      # inner end at r=4 -> connector0
    p_out = pts[-1]    # outer end at r=10 -> connector1
    size = OUTER_R * 2 + 4
    # move pads AWAY from the neighbouring spiral turns:
    #   inner pad pulled inward  r=4 -> r=3.3
    #   outer pad pushed outward r=10 -> r=10.7
    # short copper stubs keep electrical contact with the coil ends.
    INNER_PAD_R = 3.3
    OUTER_PAD_R = 10.7
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="%dmm" height="%dmm" viewBox="%d %d %d %d">\n'
        % (size, size, -size / 2, -size / 2, size, size)
    )
    # copper0 wraps copper1 (through-hole convention)
    s += '  <g id="copper0">\n'
    s += '    <g id="copper1">\n'
    s += '      <path d="%s" fill="#f7bf13" stroke="none"/>\n' % d
    # connection stubs from the coil ends to the displaced pads
    s += '      <path d="M %.3f %.3f L %.3f %.3f" fill="none" stroke="#f7bf13" stroke-width="0.4"/>\n' % (p_in[0], p_in[1], INNER_PAD_R, 0.0)
    s += '      <path d="M %.3f %.3f L %.3f %.3f" fill="none" stroke="#f7bf13" stroke-width="0.4"/>\n' % (p_out[0], p_out[1], OUTER_PAD_R, 0.0)
    # through-hole pads, each id appears ONCE
    s += '      <circle cx="%.3f" cy="0.000" r="0.55" id="connector0pin" fill="none" stroke="#f7bf13" stroke-width="0.5"/>\n' % INNER_PAD_R
    s += '      <circle cx="%.3f" cy="0.000" r="0.55" id="connector1pin" fill="none" stroke="#f7bf13" stroke-width="0.5"/>\n' % OUTER_PAD_R
    s += '    </g>\n'
    s += '  </g>\n'
    # silkscreen: a thin outline circle
    s += '  <g id="silkscreen">\n'
    s += '    <circle cx="0" cy="0" r="%.2f" fill="none" stroke="#ffffff" stroke-width="0.2" stroke-dasharray="1 0.6"/>\n' % (OUTER_R + 0.8)
    s += '  </g>\n'
    s += "</svg>\n"
    return s


# ---------------------------------------------------------- schematic view
def schematic_svg():
    """Standard inductor / sensing-coil symbol.

    This is the exact SVG used by Fritzing's built-in inductor part
    (svg/core/schematic/inductor.svg): a vertical coil of arcs with a
    pin line + terminal at top (connector0) and bottom (connector1).
    Using the official symbol guarantees a standard, wireable schematic.
    """
    return (
        "<?xml version='1.0' encoding='UTF-8' standalone='no'?>\n"
        "<!-- NFC sensing coil (standard inductor symbol) -->\n"
        "<svg xmlns:svg='http://www.w3.org/2000/svg' xmlns='http://www.w3.org/2000/svg' "
        "version='1.2' baseProfile='tiny' x='0in' y='0in' width='0.06in' height='0.609722in' "
        "viewBox='0 0 1.524 15.4869' >\n"
        "<g id='schematic'>\n"
        "<path class='other' fill='none' d='M0.127,2.66347 A1.27,1.27 0 0 1 1.397,3.93347' stroke-width='0.254' stroke='#000000' />\n"
        "<path class='other' fill='none' d='M0.127,5.20347 A1.27,1.27 0 0 0 1.397,3.93347' stroke-width='0.254' stroke='#000000' />\n"
        "<path class='other' fill='none' d='M0.127,5.20347 A1.27,1.27 0 0 1 1.397,6.47347' stroke-width='0.254' stroke='#000000' />\n"
        "<path class='other' fill='none' d='M0.127,7.74347 A1.27,1.27 0 0 0 1.397,6.47347' stroke-width='0.254' stroke='#000000' />\n"
        "<path class='other' fill='none' d='M0.127,7.74347 A1.27,1.27 0 0 1 1.397,9.01347' stroke-width='0.254' stroke='#000000' />\n"
        "<path class='other' fill='none' d='M0.127,10.2835 A1.27,1.27 0 0 0 1.397,9.01347' stroke-width='0.254' stroke='#000000' />\n"
        "<path class='other' fill='none' d='M0.127,10.2835 A1.27,1.27 0 0 1 1.397,11.5535' stroke-width='0.254' stroke='#000000' />\n"
        "<path class='other' fill='none' d='M0.127,12.8235 A1.27,1.27 0 0 0 1.397,11.5535' stroke-width='0.254' stroke='#000000' />\n"
        "<line class='pin' id='connector0pin' connectorname='1' x1='0.127' y1='0.123472' x2='0.127' y2='2.66347' stroke='#787878' stroke-width='0.246944' stroke-linecap='round'/>\n"
        "<rect class='terminal' id='connector0terminal' x='0.127' y='0.123472' width='0.0001' height='0.0001' stroke='none' stroke-width='0' fill='none'/>\n"
        "<line class='pin' id='connector1pin' connectorname='2' x1='0.127' y1='15.3635' x2='0.127' y2='12.8235' stroke='#787878' stroke-width='0.246944' stroke-linecap='round'/>\n"
        "<rect class='terminal' id='connector1terminal' x='0.127' y='15.3635' width='0.0001' height='0.0001' stroke='none' stroke-width='0' fill='none'/>\n"
        "</g>\n"
        "</svg>\n"
    )


# --------------------------------------------------------- breadboard view
def breadboard_svg():
    """Realistic planar PCB spiral coil for the breadboard view.

    - viewBox is 24x24 mm, the SAME size as the PCB view (gray frame
      matches the PCB footprint, per user request).
    - Square green FR4 board 20x20 mm (x=2..22, y=2..22).
    - Golden spiral phi19 (ARRAY_OUTER_R=9.5) centered at (12,12), NOT
      scaled, fits inside the board with ~0.5 mm margin.
    - Two small solid grey metal pads (2x2 mm), spaced EXACTLY
      7 * 2.54 = 17.78 mm so they plug into a standard breadboard.
    """
    d, pts = ribbon_path(ARRAY_OUTER_R)

    def pin_block(cid, cx, cy):
        # small solid grey metal pad 2x2 mm with simple facets (SHC0420 style)
        return (
            '    <g transform="translate(%.2f %.2f)">\n'
            '      <rect fill="#8d8c8c" height="2" id="%s" width="2" x="0" y="0"/>\n'
            '      <rect fill="#8c8663" height="1" width="1" x="0.5" y="0.5"/>\n'
            '      <polygon fill="#b8af82" points="0.5,0.4 0,0 0,2 0.5,1.6"/>\n'
            '      <polygon fill="#80795b" points="0,0 2,0 1.6,0.5 0.5,0.5"/>\n'
            '      <polygon fill="#5e5b43" points="2,0 2,2 1.6,1.6 1.6,0.5"/>\n'
            '      <polygon fill="#9a916c" points="1.6,1.6 2,2 0,2 0.5,1.6"/>\n'
            '    </g>\n'
        ) % (cx, cy, cid)

    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="24mm" height="24mm" viewBox="0 0 24 24">\n'
    )
    s += '  <g id="breadboard">\n'
    # square PCB board 20x20 mm (same footprint as the PCB view)
    s += '    <rect x="2" y="2" width="20" height="20" rx="1.5" ry="1.5" fill="#2f7d32" stroke="#1d4d1f" stroke-width="0.6"/>\n'
    # golden spiral phi19, centered, NOT scaled (fits with ~0.5 mm margin)
    s += '    <g transform="translate(12 12)">\n'
    s += '      <path d="%s" fill="#f7bf13" stroke="none"/>\n' % d
    s += '    </g>\n'
    # two small metal pads, 2x2 mm, spaced exactly 7*2.54 = 17.78 mm
    # centers at x = 12 - 8.89 and 12 + 8.89, y = 18.5
    spacing = 7 * 2.54          # 17.78 mm
    half = spacing / 2.0        # 8.89
    s += pin_block("connector0pin", 12 - half - 1.0, 17.5)
    s += pin_block("connector1pin", 12 + half - 1.0, 17.5)
    s += '  </g>\n'
    s += "</svg>\n"
    return s


# ---------------------------------------------------------------- icon view
def icon_svg():
    """32x32 icon: same square-board spiral as the breadboard view."""
    d, pts = ribbon_path(ARRAY_OUTER_R)
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n'
    )
    s += '  <g id="breadboard">\n'
    # square board
    s += '    <rect x="5" y="6" width="22" height="20" rx="1" ry="1" fill="#2f7d32" stroke="#1d4d1f" stroke-width="0.8"/>\n'
    # golden spiral (scaled: ARRAY_OUTER_R=9.5 -> fit within 22x20)
    s += '    <g transform="translate(16 16) scale(0.85)">\n'
    s += '      <path d="%s" fill="#f7bf13" stroke="none"/>\n' % d
    s += '    </g>\n'
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
        ' <title>NFC Coil</title>\n'
        ' <label>L</label>\n'
        ' <date>2026-08-24</date>\n'
        ' <tags><tag>coil</tag><tag>inductor</tag><tag>nfc</tag><tag>sensor</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">coil</property>\n'
        '  <property name="type">PCB spiral</property>\n'
        '  <property name="part number">NFC-Coil-20-6T</property>\n'
        '  <property name="package">PCB</property>\n'
        '  <property name="outer diameter (mm)">20</property>\n'
        '  <property name="inner diameter (mm)">8</property>\n'
        '  <property name="turns">6</property>\n'
        ' </properties>\n'
        ' <description>13.56 MHz NFC sensing coil (PCB spiral, 20 mm OD, 6 turns)</description>\n'
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
        '  <schematicView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="schematic"/>\n'
        '   </layers>\n'
        '  </schematicView>\n'
        '  <pcbView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="silkscreen"/>\n'
        '    <layer layerId="copper0"/>\n'
        '    <layer layerId="copper1"/>\n'
        '   </layers>\n'
        '  </pcbView>\n'
        ' </views>\n'
        ' <connectors>\n'
        '  <connector id="connector0" name="inner" type="male">\n'
        '   <description>Coil inner end</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector0pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector0pin" terminalId="connector0terminal"/></schematicView>\n'
        '    <pcbView>\n'
        '     <p layer="copper0" svgId="connector0pin"/>\n'
        '     <p layer="copper1" svgId="connector0pin"/>\n'
        '    </pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector1" name="outer" type="male">\n'
        '   <description>Coil outer end</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector1pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector1pin" terminalId="connector1terminal"/></schematicView>\n'
        '    <pcbView>\n'
        '     <p layer="copper0" svgId="connector1pin"/>\n'
        '     <p layer="copper1" svgId="connector1pin"/>\n'
        '    </pcbView>\n'
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

    # .fzpz goes to the repo-level fzpz/ directory (../fzpz from the part
    # folder), matching where every other packaged part lives.
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
