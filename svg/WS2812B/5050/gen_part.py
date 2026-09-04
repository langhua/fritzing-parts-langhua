# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for WS2812B-5050 (5.0x5.0 mm addressable RGB LED).

WS2812B-5050 is a 5.0 x 5.0 mm SMD RGB LED with integrated driver IC and 4 side legs.

Pinout (5050): 1=DOUT, 2=VDD, 3=DIN, 4=GND
Physical layout (from the real part / photos, user confirmed):
    GND top-left, DOUT top-right, DIN bottom-left, VDD bottom-right

Connectors (4):
    connector0 = pin 1 (DOUT)
    connector1 = pin 2 (VDD)
    connector2 = pin 3 (DIN)
    connector3 = pin 4 (GND)

PCB footprint (improved over the Fritzing core part, which renders only ~4.05 mm):
  - proper real-size 5.0 x 5.0 mm body drawn in mm units (viewBox 0 0 5.4 5.4)
  - 4 x 1.0 mm corner pads at +/-1.9 mm from centre (KiCad LED_WS2812B PLCC4 5050 style)
  - segmented silkscreen clear of pads + '+' polarity mark near VDD

Other views keep the design language of the WS2812B-2020 part:
  white plastic body + circular lens, DW01A straddle breadboard, IC-box schematic.
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "WS2812B_5050_1"

PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "WS2812B-5050.fzpz"

PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# PCB pads - 5050 footprint (per datasheet), pads 1.5 x 1.0 mm.
# Horizontal: inner edges of top pads 3.4 mm apart -> centre pitch 4.9 mm.
# Vertical: outer span 4.2 mm (incl. 1.0 pads) -> centre pitch 4.2-1.0=3.2 mm.
# GND TL / DO TR / DI BL / VDD BR.
PCB_PADS = {
    "connector3pin": (0.0, 0.0, 1.5, 1.0),   # GND top-left
    "connector0pin": (4.9, 0.0, 1.5, 1.0),   # DO  top-right
    "connector2pin": (0.0, 3.2, 1.5, 1.0),   # DI  bottom-left
    "connector1pin": (4.9, 3.2, 1.5, 1.0),   # VDD bottom-right
}

# Fritzing 官方 core 的 ws2812b 面包板 svg（仓库内资产副本，见 svg/_assets/）
CORE_BB = os.path.normpath(os.path.join(OUT_DIR, "..", "..", "_assets",
                                        "ws2812b_core_breadboard.svg"))


# LED artwork bounding box in the core SVG (body 14.172 x 14.174 at 3.714,14.36,
# centre 10.8,21.447) - used to scale it into our 300x400 breadboard.
ART_CENTER = (10.8, 21.447)
ART_W = 14.172
ART_H = 14.174


def core_led_artwork():
    """Extract the realistic LED artwork block from Fritzing core's ws2812b breadboard."""
    try:
        with open(CORE_BB, encoding="utf-8") as f:
            lines = f.read().split("\n")
        din = next(i for i, l in enumerate(lines) if ">DIN</text>" in l)
        start = next(i for i in range(din, len(lines)) if lines[i].strip() == "<g>")
        depth = 0
        end = None
        for i in range(start, len(lines)):
            depth += lines[i].count("<g") - lines[i].count("</g>")
            if depth == 0:
                end = i + 1
                break
        return "\n".join(lines[start:end])
    except Exception:
        return None


def pcb_svg():
    """WS2812B-5050 footprint: 4 x 1.5x1.0 mm pads + segmented silkscreen + '+'."""
    lines = []
    lines.append('<?xml version="1.0" encoding="utf-8"?>\n')
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="7.2mm" height="4.7mm" viewBox="-0.25 -0.25 7.20 4.70">\n')
    lines.append(' <g id="copper1">\n')
    for cid, (x, y, w, h) in PCB_PADS.items():
        lines.append('  <rect x="%.3f" y="%.3f" width="%.1f" height="%.1f" id="%s" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
                     % (x, y, w, h, cid))
    lines.append(' </g>\n')
    lines.append(' <g id="silkscreen">\n')
    # segmented outline AROUND the pads (0.2 clearance), like the 2020 part.
    # pads: x 0..1.5 / 4.9..6.4, y 0..1.0 / 3.2..4.2
    lines.append('  <line x1="-0.2" y1="1.2" x2="-0.2" y2="3.0" stroke="#FFFFFF" stroke-width="0.06"/>\n')   # left
    lines.append('  <line x1="6.6" y1="1.2" x2="6.6" y2="3.0" stroke="#FFFFFF" stroke-width="0.06"/>\n')     # right
    lines.append('  <line x1="1.7" y1="-0.2" x2="4.7" y2="-0.2" stroke="#FFFFFF" stroke-width="0.06"/>\n')   # top
    lines.append('  <line x1="1.7" y1="4.4" x2="4.7" y2="4.4" stroke="#FFFFFF" stroke-width="0.06"/>\n')     # bottom
    # + polarity to the right of VDD (bottom-right pad)
    lines.append('  <line x1="6.5" y1="3.7" x2="6.9" y2="3.7" stroke="#FFFFFF" stroke-width="0.06"/>\n')
    lines.append('  <line x1="6.7" y1="3.5" x2="6.7" y2="3.9" stroke="#FFFFFF" stroke-width="0.06"/>\n')
    lines.append(' </g>\n')
    lines.append('</svg>\n')
    return "".join(lines)


def schematic_svg():
    """4-pin IC-box symbol: DIN(left) DOUT(right) VDD(top) GND(bottom)."""
    s = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        'x="0px" y="0px" width="48px" height="32px" viewBox="0 0 48 32" xml:space="preserve">\n'
        ' <g id="schematic">\n'
        '  <rect x="14" y="8" width="20" height="16" fill="#FFFFFF" stroke="#000000" stroke-width="0.9"/>\n'
        # DIN (connector2, pin3) - left
        '  <line class="pin" id="connector2pin" connectorname="3" x1="3" y1="13" x2="14" y2="13" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector2terminal" x="3" y="13" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 4.5 11.9)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">DI</text>\n'
        # DOUT (connector0, pin1) - right
        '  <line class="pin" id="connector0pin" connectorname="1" x1="34" y1="13" x2="45" y2="13" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector0terminal" x="45" y="13" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 34.8 11.9)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">DO</text>\n'
        # VDD (connector1, pin2) - top
        '  <line class="pin" id="connector1pin" connectorname="2" x1="24" y1="8" x2="24" y2="2" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector1terminal" x="24" y="2" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 25.5 5.5)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">VDD</text>\n'
        # GND (connector3, pin4) - bottom
        '  <line class="pin" id="connector3pin" connectorname="4" x1="24" y1="24" x2="24" y2="30" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector3terminal" x="24" y="30" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 25.5 28.8)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">GND</text>\n'
        # body text
        '  <text transform="matrix(1 0 0 1 24 16.6)" fill="#000000" font-family="DroidSans" font-size="4.2" text-anchor="middle">WS2812B</text>\n'
        '  <text transform="matrix(1 0 0 1 24 21.0)" fill="#000000" font-family="DroidSans" font-size="3.4" text-anchor="middle">RGB LED</text>\n'
        ' </g>\n'
        '</svg>\n'
    )
    return s


# Breadboard: reuse the core WS2812B breadboard file directly, but re-pin and
# re-label it for THIS part. Core pin positions (verified from the file):
#   connector0pin@BL, connector1pin@BR, connector2pin@TR, connector3pin@TL
# 5050 target: GND TL / DOUT TR / DIN BL / VDD BR
BB_PIN_RENAME = {
    "connector0pin": "connector2pin",   # BL -> DIN
    "connector2pin": "connector0pin",   # TR -> DOUT
    # connector1pin@BR stays VDD, connector3pin@TL stays GND
}
BB_LABEL_RENAME = {
    ">VDD</text>": ">DI</text>",        # BL -> DI
    ">DOUT</text>": ">VDD</text>",      # BR -> VDD
    ">VSS</text>": ">DO</text>",        # TR -> DO
    ">DIN</text>": ">GND</text>",       # TL -> GND
}


def safe_replace(text, mapping):
    """Replace every key with its value atomically (no key/value collisions)."""
    phs = {}
    for i, old in enumerate(mapping):
        ph = "@@P%d@@" % i
        phs[old] = ph
        text = text.replace(old, ph)
    for old, new in mapping.items():
        text = text.replace(phs[old], new)
    return text


def core_breadboard():
    """Core WS2812B breadboard SVG, re-pinned/re-labelled for this part."""
    try:
        with open(CORE_BB, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    content = safe_replace(content, BB_PIN_RENAME)
    content = safe_replace(content, BB_LABEL_RENAME)
    # enlarge the edge pin labels (core uses tiny 2.75pt text)
    content = content.replace('font-size="2.75"', 'font-size="3.5"')
    # move the GND label down by about one letter width so it clears the pin
    content = content.replace('matrix(1 0 0 1 62.5355 -158.8074)',
                              'matrix(1 0 0 1 60.54 -158.8074)')
    # rotate the LED chip artwork 90 deg clockwise (matches the bought part)
    art = core_led_artwork()
    if art:
        cx, cy = 10.8, 21.6
        wrapped = ('<g transform="translate(%.4f,%.4f) rotate(90) translate(%.4f,%.4f)">\n%s\n</g>'
                   % (cx, cy, -cx, -cy, art))
        content = content.replace(art, wrapped, 1)
    return content


def breadboard_svg():
    """Breadboard view = core WS2812B file, with our pins/labels and larger text."""
    content = core_breadboard()
    if content is None:
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="0.3in" height="0.4in" viewBox="0 0 300 400">\n'
            ' <g id="breadboard">\n'
            '  <g id="icon">\n'
            '   <path d="M0,0L0,170A30,30 0 0 1 0,230L0,400L300,400L300,0L0,0z" fill="#1F7A34" stroke="none" stroke-width="0"/>\n'
            '   <rect x="59" y="109" width="150" height="150" rx="12" fill="#f0f0f0" stroke="#777777" stroke-width="2"/>\n'
            '   <circle cx="134" cy="184" r="38" fill="#c8d8ec" stroke="#9aa8bc" stroke-width="2"/>\n'
            '  </g>\n'
            ' </g>\n'
            '</svg>\n'
        )
    return content


def icon_svg():
    """32x32 icon: core's realistic LED artwork + green board + 4 corner pads."""
    art = core_led_artwork()
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n'
        ' <g id="breadboard">\n'
        '  <rect x="1" y="1" width="30" height="30" rx="4" fill="#1F7A34"/>\n'
    )
    if art:
        # embed core LED artwork as an ~18x18 body centred at (16,16)
        scale = 18.0 / ART_W
        tx = 16 - ART_CENTER[0] * scale
        ty = 16 - ART_CENTER[1] * scale
        s += '  <g transform="translate(%.3f,%.3f) scale(%.5f)">\n' % (tx, ty, scale)
        s += art + "\n"
        s += '  </g>\n'
    else:
        s += '  <circle cx="16" cy="16" r="8" fill="#c8d8ec" stroke="#9aa8bc" stroke-width="0.6"/>\n'
    for px, py in ((1.5, 1.5), (26.0, 1.5), (1.5, 26.0), (26.0, 26.0)):
        s += '  <rect x="%.1f" y="%.1f" width="4.5" height="4.5" rx="0.5" fill="#8D8C8C"/>\n' % (px, py)
    s += ' </g>\n'
    s += '</svg>\n'
    return s


def fzp_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>WS2812B-5050</title>\n'
        ' <label>LED</label>\n'
        ' <date>2026-08-24</date>\n'
        ' <tags><tag>LED</tag><tag>RGB</tag><tag>addressable</tag><tag>WS2812B</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">LED</property>\n'
        '  <property name="package">WS2812B-5050 (5.0x5.0mm)</property>\n'
        '  <property name="part number">WS2812B-5050</property>\n'
        ' </properties>\n'
        ' <description>WS2812B-5050 addressable RGB LED, 5.0x5.0 mm, integrated driver.</description>\n'
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
        '  <connector id="connector0" name="DO" type="male">\n'
        '   <description>Pin 1 - data output</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector0pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector0pin" terminalId="connector0terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector0pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector1" name="VDD" type="male">\n'
        '   <description>Pin 2 - power supply</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector1pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector1pin" terminalId="connector1terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector1pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector2" name="DI" type="male">\n'
        '   <description>Pin 3 - data input</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector2pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector2pin" terminalId="connector2terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector2pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector3" name="GND" type="male">\n'
        '   <description>Pin 4 - ground</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector3pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector3pin" terminalId="connector3terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector3pin"/></pcbView>\n'
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

    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
