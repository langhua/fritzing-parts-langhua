# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for WS2812B-1010 (XL-1010RGBC-WS2812B, 1.0x1.0 mm).

WS2812B-1010 is a 1.0 x 1.0 x 0.8 mm SMD addressable RGB LED with integrated
driver IC, 4 bottom pads (2 x 2 grid), 0.28 mm side step.

Pinout (from the XL-1010RGBC-WS2812B datasheet, 外形尺寸/引脚图, top view with the
pin-1 corner notch at the LOWER-LEFT; numbering is counter-clockwise):
    ① DOUT (bottom-left)   ② VDD (bottom-right)
    ③ GND  (top-right)     ④ DI  (top-left)
So on the PCB (top view, svg y grows downward):
    DOUT = bottom-left, VDD = bottom-right, GND = top-right, DI = top-left

Footprint (建议焊盘尺寸):
    pad 0.45 x 0.45 mm, edge-to-edge gap between neighbouring pads 0.40 mm
    -> pad centre pitch 0.85 x 0.85 mm, pad field 1.30 x 1.30 mm, i.e. the pad
       field is LARGER than the 1.0 x 1.0 mm body (the pads stick out ~0.15 mm
       on each side), so the silkscreen outline marks the pad field, not the body.
    NB "0.40" is the edge-to-edge gap, not the centre pitch: 0.45 mm pads on a
    0.40 mm centre pitch would overlap and short neighbouring pads.
    Pin-1 marker: dot outside the lower-left corner (datasheet notch).

Connectors (same ids/order as the WS2812B-2020 / -5050 parts):
    connector0 = DO  (pin 1, data output)
    connector1 = GND (pin 3)
    connector2 = DI  (pin 4, data input)
    connector3 = VDD (pin 2)

Views (same design language as the 2020/5050 parts):
  - icon: green board + core LED artwork + 4 corner pads
  - breadboard: core WS2812B carrier board (4 pins on the 2.54 mm grid), 1010 art
  - schematic: 4-pin IC box, DI left / DO right / VDD top / GND bottom
  - pcb: 1 x 1 mm body outline + 4 pads + pin-1 dot
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "WS2812B_1010_1"

PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "WS2812B-1010.fzpz"

PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# ---------------------------------------------------------------- footprint --
PAD_W = 0.45        # mm, pad width  (x)
PAD_H = 0.45        # mm, pad height (y)
GAP = 0.40          # mm, edge-to-edge gap between neighbouring pads
PITCH_X = PAD_W + GAP   # 0.85 mm, pad centre to centre, horizontal
PITCH_Y = PAD_H + GAP   # 0.85 mm, pad centre to centre, vertical
BODY = 1.00         # mm, body size (for reference: the pad field is larger)
SILK_CLEAR = 0.13   # mm, silkscreen outline sits this far outside the pad field

PX = PITCH_X / 2.0
PY = PITCH_Y / 2.0
FIELD = PITCH_X / 2.0 + PAD_W / 2.0     # 0.65 mm, pad field half size
SILK = FIELD + SILK_CLEAR               # 0.78 mm, silkscreen half size

# top view: DOUT BL / VDD BR / GND TR / DI TL
PCB_PADS = {
    "connector0pin": (-PX, +PY),    # DO  (DOUT) bottom-left
    "connector3pin": (+PX, +PY),    # VDD        bottom-right
    "connector1pin": (+PX, -PY),    # GND        top-right
    "connector2pin": (-PX, -PY),    # DI (DIN)   top-left
}

# Fritzing 官方 core 的 ws2812b 面包板 svg（仓库内资产副本，见 svg/_assets/）
CORE_BB = os.path.normpath(os.path.join(OUT_DIR, "..", "..", "_assets",
                                        "ws2812b_core_breadboard.svg"))

# LED artwork bounding box in the core SVG (body 14.172 x 14.174 at 3.714,14.36,
# centre 10.8,21.447) - used to scale it into our breadboard.
ART_CENTER = (10.8, 21.447)
ART_W = 14.172
ART_H = 14.174

# icon artwork size (same nominal glyph as the 2020/5050 parts)
ICON_ART = 18.0


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
    """WS2812B-1010 footprint: 4 x 0.45 mm pads on a 0.85 mm grid + silk + dot.

    The pad field (1.30 x 1.30 mm) is larger than the 1.0 x 1.0 mm body, so the
    silkscreen marks the pad field boundary (four segments, corners left open).
    ViewBox is symmetric about the part centre so Fritzing rotates it in place.
    """
    half_w = PAD_W / 2.0
    half_h = PAD_H / 2.0
    s = SILK
    seg = 0.35         # silk segment half length (corners stay open)
    margin = s + 0.27  # room for the pin-1 dot outside the lower-left corner
    lines = []
    lines.append('<?xml version="1.0" encoding="utf-8"?>\n')
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
                 'viewBox="%.2f %.2f %.2f %.2f">\n'
                 % (2 * margin, 2 * margin, -margin, -margin, 2 * margin, 2 * margin))
    lines.append(' <g id="copper1">\n')
    for cid, (cx, cy) in PCB_PADS.items():
        lines.append('  <rect x="%.3f" y="%.3f" width="%.2f" height="%.2f" id="%s" '
                     'style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
                     % (cx - half_w, cy - half_h, PAD_W, PAD_H, cid))
    lines.append(' </g>\n')
    lines.append(' <g id="silkscreen">\n')
    # pad field outline (clear of the pads: they end at 0.65), corners open
    lines.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
                 % (-s, -seg, -s, seg))
    lines.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
                 % (s, -seg, s, seg))
    lines.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
                 % (-seg, -s, seg, -s))
    lines.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
                 % (-seg, s, seg, s))
    # pin-1 (DOUT) marker: dot outside the lower-left corner, like the datasheet notch
    dot = s + 0.12
    lines.append('  <circle cx="%.2f" cy="%.2f" r="0.07" fill="#FFFFFF" stroke="none"/>\n'
                 % (-dot, dot))
    lines.append(' </g>\n')
    lines.append('</svg>\n')
    return "".join(lines)


def schematic_svg():
    """4-pin IC-box symbol: DI(left) DO(right) VDD(top) GND(bottom)."""
    s = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        'x="0px" y="0px" width="48px" height="32px" viewBox="0 0 48 32" xml:space="preserve">\n'
        ' <g id="schematic">\n'
        '  <rect x="14" y="8" width="20" height="16" fill="#FFFFFF" stroke="#000000" stroke-width="0.9"/>\n'
        # DI (connector2, pin 4) - left
        '  <line class="pin" id="connector2pin" connectorname="4" x1="3" y1="13" x2="14" y2="13" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector2terminal" x="3" y="13" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 4.5 11.9)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">DI</text>\n'
        # DOUT (connector0, pin 1) - right
        '  <line class="pin" id="connector0pin" connectorname="1" x1="34" y1="13" x2="45" y2="13" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector0terminal" x="45" y="13" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 34.8 11.9)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">DO</text>\n'
        # VDD (connector3, pin 2) - top
        '  <line class="pin" id="connector3pin" connectorname="2" x1="24" y1="8" x2="24" y2="2" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector3terminal" x="24" y="2" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 25.5 5.5)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">VDD</text>\n'
        # GND (connector1, pin 3) - bottom
        '  <line class="pin" id="connector1pin" connectorname="3" x1="24" y1="24" x2="24" y2="30" stroke="#787878" stroke-width="0.75"/>\n'
        '  <rect class="terminal" id="connector1terminal" x="24" y="30" width="0.0001" height="0.0001" fill="none"/>\n'
        '  <text transform="matrix(1 0 0 1 25.5 28.8)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">GND</text>\n'
        # body text
        '  <text transform="matrix(1 0 0 1 24 16.6)" fill="#000000" font-family="DroidSans" font-size="4.2" text-anchor="middle">WS2812B</text>\n'
        '  <text transform="matrix(1 0 0 1 24 21.0)" fill="#000000" font-family="DroidSans" font-size="3.4" text-anchor="middle">1010</text>\n'
        ' </g>\n'
        '</svg>\n'
    )
    return s


# Breadboard: reuse the core WS2812B breadboard file, but re-pin and re-label it
# for THIS part. Core pin positions (verified from the file):
#   connector0pin@BL, connector1pin@BR, connector2pin@TR, connector3pin@TL
# Core labels:            BL=VDD,      BR=DOUT,     TR=VSS,        TL=DIN
# 1010 wants (datasheet top view): BL=DOUT, BR=VDD, TR=GND, TL=DI
BB_PIN_RENAME = {
    "connector1pin": "connector3pin",   # BR -> VDD
    "connector2pin": "connector1pin",   # TR -> GND
    "connector3pin": "connector2pin",   # TL -> DI
}
BB_LABEL_RENAME = {
    ">VDD</text>": ">DOUT</text>",      # BL -> DOUT
    ">DOUT</text>": ">VDD</text>",      # BR -> VDD
    ">VSS</text>": ">GND</text>",       # TR -> GND
    ">DIN</text>": ">DI</text>",        # TL -> DI
}

# LED artwork scale on the breadboard carrier: the 2020 part uses 0.55 for a
# 2.0 mm body, so a 1.0 mm body is half of that.
BB_ART_SCALE = 0.55 / 2.0
BB_NEW_CY = 14.4     # centre of the shortened carrier board (28.8 high)


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
    positions and still line up with breadboard holes (like the 5050/2020).
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
    """Core WS2812B breadboard SVG, re-pinned/re-labelled, narrower carrier."""
    try:
        with open(CORE_BB, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    content = safe_replace(content, BB_PIN_RENAME)
    content = safe_replace(content, BB_LABEL_RENAME)
    # label font: standard 3.5 (same as the other WS2812B parts)
    content = content.replace('font-size="2.75"', 'font-size="3.5"')
    # shrink the centre LED artwork (1.0 mm part -> half the 2020's scale) and
    # re-centre it on the shortened board; sx compensates the 0.9 board squash
    # so the LED body stays round.
    art = core_led_artwork()
    if art:
        sy = BB_ART_SCALE
        sx = sy / 0.9
        cx = ART_CENTER[0]
        cy = (BB_NEW_CY - sy * ART_CENTER[1]) / (1.0 - sy)
        wrapped = ('<g transform="translate(%.4f,%.4f) scale(%.4f,%.4f) translate(%.4f,%.4f)">\n%s\n</g>'
                   % (cx, cy, sx, sy, -cx, -cy, art))
        content = content.replace(art, wrapped, 1)
    # narrow ONLY the carrier body (pins stay at full width so they still insert)
    content = wrap_icon_horizontal(content, cx=10.8, factor=0.9)
    # shorten the carrier so the two pin rows are 3 breadboard holes apart
    # (Fritzing hole pitch 7.2 units; same geometry as the 2020 part)
    content = content.replace('width="21.6px" height="43.2px"', 'width="19.54px" height="28.8px"')
    content = content.replace('viewBox="0 0 21.6 43.2"', 'viewBox="1.03 0 19.54 28.8"')
    content = content.replace('translate(34.035,334.05)', 'translate(34.035,319.648)')
    content = content.replace('translate(234.035,334.05)', 'translate(234.035,319.648)')
    content = content.replace('translate(63.5,326.05)', 'translate(63.5,320.647)')
    content = content.replace('translate(263.5,326.05)', 'translate(263.5,320.647)')
    content = content.replace('matrix(1 0 0 1 288.1735', 'matrix(1 0 0 1 297.17')
    content = content.replace('v19.362', 'v12.24')
    content = content.replace('v19.52', 'v12.24')
    return content


def breadboard_svg():
    """Breadboard view = core WS2812B carrier file, with our pins/labels."""
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
        scale = ICON_ART / ART_W
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
        ' <title>WS2812B-1010</title>\n'
        ' <label>LED</label>\n'
        ' <date>2026-09-24</date>\n'
        ' <tags><tag>LED</tag><tag>RGB</tag><tag>addressable</tag><tag>WS2812B</tag><tag>1010</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">LED</property>\n'
        '  <property name="package">WS2812B-1010 (1.0x1.0mm)</property>\n'
        '  <property name="part number">WS2812B-1010</property>\n'
        ' </properties>\n'
        ' <description>WS2812B-1010 addressable RGB LED, 1.0x1.0x0.8 mm, integrated driver, 4 bottom pads on a 0.40 mm grid.</description>\n'
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
        '   <description>Pin 3 - ground</description>\n'
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
