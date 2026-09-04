# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for WS2812B-2020 (2.0x2.0 mm addressable RGB LED).

WS2812B-2020 is a 2.0 x 2.0 mm SMD RGB LED with integrated driver IC, 4 corner pads.

Pinout (from the actual WS2812B-2020 datasheet, 讯华微电子):
    pin 1 = DOUT, pin 2 = VDD, pin 3 = VSS(GND), pin 4 = DIN
Physical layout (breadboard order, matches the bought part):
    GND top-left, DOUT top-right, DIN bottom-left, VDD bottom-right
Pads 0.7 x 0.7 mm, pad pitch 1.83 x 1.1 mm.

Connectors (4):
    connector0 = DOUT (pin 1)
    connector1 = GND  (pin 3 / VSS)
    connector2 = DIN  (pin 4)
    connector3 = VDD  (pin 2)

Views (same design language as the WS2812B-5050 part):
  - white plastic body + circular lens + 4 silver legs
  - breadboard straddles the centre groove (DW01A pattern, 300x400 viewBox)
  - segmented silkscreen clear of pads + '+' polarity mark near VDD
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "WS2812B_2020_1"

PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "WS2812B-2020.fzpz"

PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# PCB pads - 2.0x1.8 mm footprint, viewBox 0 0 4.4 3.4 (mm), centre (2.2, 1.7)
# GND TL / DO TR / DI BL / VDD BR (same order as the breadboard / bought part).
# Pad spacing (edge-to-edge, per the bought 2020 part): GND<->DO = 0.4 mm,
# GND<->DI = 1.13 mm; pads 0.7 x 0.7 mm, centred on (2.2, 1.7).
PCB_PADS = {
    "connector0pin": (2.40, 0.435, 0.7, 0.7),   # DO  top-right
    "connector1pin": (1.30, 0.435, 0.7, 0.7),   # GND top-left
    "connector2pin": (1.30, 2.265, 0.7, 0.7),   # DI  bottom-left
    "connector3pin": (2.40, 2.265, 0.7, 0.7),   # VDD bottom-right
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
    """WS2812B-2020 footprint: 4 x 0.7 mm pads + segmented silkscreen + '+'.

    ViewBox is trimmed to the content (no surrounding whitespace).
    """
    lines = []
    lines.append('<?xml version="1.0" encoding="utf-8"?>\n')
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="2.6mm" height="3.1mm" viewBox="1.05 0.15 2.60 3.10">\n')
    lines.append(' <g id="copper1">\n')
    for cid, (x, y, w, h) in PCB_PADS.items():
        lines.append('  <rect x="%.3f" y="%.3f" width="%.1f" height="%.1f" id="%s" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
                     % (x, y, w, h, cid))
    lines.append(' </g>\n')
    lines.append(' <g id="silkscreen">\n')
    # segmented outline, clear of pads (pads: x 1.30..2.00 / 2.40..3.10,
    # y 0.435..1.135 / 2.265..2.965)
    lines.append('  <line x1="1.10" y1="1.2" x2="1.10" y2="2.0" stroke="#FFFFFF" stroke-width="0.06"/>\n')   # left
    lines.append('  <line x1="3.30" y1="1.2" x2="3.30" y2="2.0" stroke="#FFFFFF" stroke-width="0.06"/>\n')   # right
    lines.append('  <line x1="1.5" y1="0.20" x2="2.9" y2="0.20" stroke="#FFFFFF" stroke-width="0.06"/>\n')    # top
    lines.append('  <line x1="1.5" y1="3.20" x2="2.9" y2="3.20" stroke="#FFFFFF" stroke-width="0.06"/>\n')    # bottom
    # + polarity to the right of VDD (bottom-right pad): bigger and closer
    lines.append('  <line x1="3.20" y1="2.60" x2="3.60" y2="2.60" stroke="#FFFFFF" stroke-width="0.06"/>\n')
    lines.append('  <line x1="3.40" y1="2.40" x2="3.40" y2="2.80" stroke="#FFFFFF" stroke-width="0.06"/>\n')
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
        # VDD (connector3, pin4) - top
        '  <line class="pin" id="connector3pin" connectorname="4" x1="24" y1="8" x2="24" y2="2" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector3terminal" x="24" y="2" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 25.5 5.5)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">VDD</text>\n'
        # GND (connector1, pin2) - bottom
        '  <line class="pin" id="connector1pin" connectorname="2" x1="24" y1="24" x2="24" y2="30" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector1terminal" x="24" y="30" width="0.0001" height="0.0001" fill="none"/>\n'
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
# 2020 breadboard matches the 5050 layout: GND TL / DOUT TR / DIN BL / VDD BR
BB_PIN_RENAME = {
    "connector0pin": "connector2pin",   # BL -> DIN
    "connector2pin": "connector0pin",   # TR -> DOUT
    "connector3pin": "connector1pin",   # TL -> GND
    "connector1pin": "connector3pin",   # BR -> VDD
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


def wrap_icon_horizontal(content, cx, factor):
    """Wrap only the <g id=\"icon\"> group in a horizontal squash about x=cx.

    Leaves the connector-pin groups untouched so the pins keep the full-width
    positions and still line up with breadboard holes (like the 5050).
    """
    lines = content.split("\n")
    out = []
    depth = 0
    active = False
    for l in lines:
        if not active and '<g id="icon">' in l:
            out.append('<g transform="translate(%.4f,21.6) scale(%.4f,1) translate(%.4f,-21.6)">'
                       % (cx, factor, -cx))
            out.append(l)
            depth = 1
            active = True
            continue
        if active:
            depth += l.count("<g") - l.count("</g>")
            out.append(l)
            if depth == 0:
                out.append('</g>')
                active = False
            continue
        out.append(l)
    return "\n".join(out)


def core_breadboard():
    """Core WS2812B breadboard SVG, re-pinned/re-labelled, narrower 2020 board.

    The board body is narrowed but the four pins stay at the full-width
    positions (same as the 5050) so they all land on breadboard holes; the LED
    artwork is shrunk so the 2x2mm 2020 reads smaller than the 5x5mm 5050.
    """
    try:
        with open(CORE_BB, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    content = safe_replace(content, BB_PIN_RENAME)
    content = safe_replace(content, BB_LABEL_RENAME)
    # label font: standard 3.5 (same as the WS2812B-5050 part)
    content = content.replace('font-size="2.75"', 'font-size="3.5"')
    # move the GND label down by about one letter width so it clears the pin
    content = content.replace('matrix(1 0 0 1 62.5355 -158.8074)',
                              'matrix(1 0 0 1 60.54 -158.8074)')
    # shrink the centre LED artwork; sx compensates for the board narrowing so
    # the LED body stays round after the horizontal 0.9 squash. cy re-centres
    # the art on the shorter board (new board height 28.8 -> centre 14.4).
    art = core_led_artwork()
    if art:
        cx, cy, sx, sy = 10.8, 5.7867, 0.55 / 0.9, 0.55
        wrapped = ('<g transform="translate(%.4f,%.4f) scale(%.4f,%.4f) translate(%.4f,%.4f)">\n%s\n</g>'
                   % (cx, cy, sx, sy, -cx, -cy, art))
        content = content.replace(art, wrapped, 1)
    # narrow ONLY the board body (widen by ~half a letter width each side so
    # the corner labels sit inside); pins stay at full width so they still insert
    content = wrap_icon_horizontal(content, cx=10.8, factor=0.9)
    # shorten the board so the two pin rows are 3 breadboard holes apart.
    # Fritzing's breadboard hole pitch is 7.2 units (core rows are 36 = 5 holes
    # apart - what the 5050 keeps; a 9-unit shift is NOT on the grid and leaves
    # the pins between holes). New pin centre = 3.6 + 3*7.2 = 25.2:
    #   bottom pin translate y   325.05 -> 319.648  (centre 30.603 -> 25.2)
    #   bottom label translate y 326.05 -> 320.647  (text stays beside the pin)
    content = content.replace('width="21.6px" height="43.2px"', 'width="19.54px" height="28.8px"')
    content = content.replace('viewBox="0 0 21.6 43.2"', 'viewBox="1.03 0 19.54 28.8"')
    content = content.replace('translate(34.035,334.05)', 'translate(34.035,319.648)')
    content = content.replace('translate(234.035,334.05)', 'translate(234.035,319.648)')
    content = content.replace('translate(63.5,326.05)', 'translate(63.5,320.647)')
    content = content.replace('translate(263.5,326.05)', 'translate(263.5,320.647)')
    content = content.replace('matrix(1 0 0 1 288.1735', 'matrix(1 0 0 1 297.17')
    # re-centre the semicircular notch on the shorter board (old centre ~21.5,
    # new centre 14.4 = 28.8/2): arc top at 12.24 -> v12.24 ... v12.24
    content = content.replace('v19.362', 'v12.24')
    content = content.replace('v19.52', 'v12.24')
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
            '   <rect x="84" y="134" width="100" height="100" rx="10" fill="#f0f0f0" stroke="#777777" stroke-width="2"/>\n'
            '   <circle cx="134" cy="184" r="30" fill="#c8d8ec" stroke="#9aa8bc" stroke-width="2"/>\n'
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
        ' <title>WS2812B-2020</title>\n'
        ' <label>LED</label>\n'
        ' <date>2026-08-24</date>\n'
        ' <tags><tag>LED</tag><tag>RGB</tag><tag>addressable</tag><tag>WS2812B</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">LED</property>\n'
        '  <property name="package">WS2812B-2020 (2.0x2.0mm)</property>\n'
        '  <property name="part number">WS2812B-2020</property>\n'
        ' </properties>\n'
        ' <description>WS2812B-2020 addressable RGB LED, 2.0x2.0 mm, integrated driver.</description>\n'
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
        '  <connector id="connector1" name="GND" type="male">\n'
        '   <description>Pin 3 - ground (VSS)</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector1pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector1pin" terminalId="connector1terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector1pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector2" name="DI" type="male">\n'
        '   <description>Pin 4 - data input</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector2pin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector2pin" terminalId="connector2terminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector2pin"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n'
        '  <connector id="connector3" name="VDD" type="male">\n'
        '   <description>Pin 2 - power supply</description>\n'
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
