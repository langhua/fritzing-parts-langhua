# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for the WCH CH32V002J4M6 (SOP8)

Datasheet: D:\\Downloads\\CH32V002DS0.PDF (V1.7), CH32V003DS0.PDF (V1.8)
  - Package: SOP8, body 3.9 x 5.0 mm, pin pitch 1.27 mm (50 mil)  [ch.4]
  - Pin definition table 2-1 (same pin numbering as CH32V003J4M6)

!!! SOP8 has only SIX electrical I/O nodes: the die pads PD6+PA1 share pin 1,
    and PD1+PD4+PD5 share pin 8 (short connected inside the package, see the
    CH32V002 datasheet notes 3/4).  Those two nodes must NOT be used as
    outputs.  Connector names below therefore name BOTH die pads.

Connector model (connector0..7 = package pin 1..8):
  0 pin1  PD6/PA1        (ADC_IN6/ADC_IN1, input only)
  1 pin2  VSS
  2 pin3  PA2            (ADC_IN0)
  3 pin4  VDD
  4 pin5  PC1
  5 pin6  PC2
  6 pin7  PC4            (ADC_IN2)
  7 pin8  PD1/PD4/PD5    (PD1 = SWIO debug)

Views
  icon       : SOP8 package top view (body 3.9 x 5.0 mm, 4+4 gull-wing leads,
               pin-1 index dot, top mark) -- 4 units/mm, landscape.
  breadboard : GREEN breakout board (2 rows x 4 header pins, 2.54 mm grid) with
               the real chip at 1:1 in the middle; per the repo rules the pin
               numbers are rotated -90, centred on the pad, on the INNER side,
               0.3 mm (11.8 units) clear of the pad ring.
  schematic  : rectangle symbol, TWO rows package -> left column = pins 1..4
               top->bottom, right column = pins 8..5 top->bottom (counter
               clockwise), pin numbers above the pin lines, names inside.
  pcb        : SOP8 SMD land pattern -- 8 plain <rect> pads 1.55 x 0.6 mm,
               pitch 1.27 mm, row centre distance 5.4 mm, on copper1.

Repo rules honoured (see fritzing-parts-langhua/AGENTS.md):
  - plain <rect> only (NO rx/ry -> otherwise Fritzing scan-line fills)
  - breadboard/pcb svg have BOTH width and height in mm
  - breadboard pins sit on the 2.54 mm hole grid (internal 50 + 100*k)
  - .fzp image refs use icon/ breadboard/ schematic/ pcb/ subdirectories
  - .fzpz written flat into the repo level fzpz/ directory
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH32V002J4M6"
TITLE = "CH32V002J4M6"
FZPZ = PART_ID + ".fzpz"
FZPZ_DIR = os.path.normpath(os.path.join(OUT_DIR, "..", "..", "fzpz"))

ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID

ICON_REF = "icon/%s_icon.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
PCB_REF = "pcb/%s_pcb.svg" % PART_ID

# package pin -> die pad name(s)
PIN_NAMES = ["PD6/PA1", "VSS", "PA2", "VDD", "PC1", "PC2", "PC4", "PD1/PD4/PD5"]
DESC = {
    "PD6/PA1": "pin 1 - PD6 (ADC_IN6) / PA1 (ADC_IN1); die pads share this pin, INPUT ONLY",
    "VSS": "pin 2 - ground",
    "PA2": "pin 3 - PA2 (ADC_IN0)",
    "VDD": "pin 4 - supply 2.5 / 3.3 / 5 V",
    "PC1": "pin 5 - PC1",
    "PC2": "pin 6 - PC2",
    "PC4": "pin 7 - PC4 (ADC_IN2)",
    "PD1/PD4/PD5": "pin 8 - PD1 (SWIO debug) / PD4 / PD5; die pads share this pin, output restricted",
}

# ---------------------------------------------------------------- breadboard
# ATECC608B style (reference: svg/ATECC608B/svg.breadboard.ATECC608B_breadboard.svg):
# 500 x 500 units, 1 unit = 1 mil = 0.0254 mm, NO transform; header pins on
# multiples of 100 (= 2.54 mm) so they land on the breadboard hole grid.
BB_W = BB_H = 500.0
PIN_X = (100.0, 400.0)              # left / right header columns
PIN_Y0, PIN_PITCH = 100.0, 100.0    # 2.54 mm
PAD_R, HOLE_R = 39.4, 19.1          # gold pad ring + dark pin hole
BODY_X, BODY_Y = 151.57, 173.23     # chip body 5.0 x 3.9 mm (landscape)
BODY_W, BODY_H = 196.85, 153.54
LEAD_X0, LEAD_W, LEAD_LEN = 166.73, 16.54, 41.34
LEAD_PITCH = 50.0                   # 1.27 mm chip lead pitch (NOT the 100 of the headers)
LEAD_TOP_Y, LEAD_BOT_Y = 131.89, 326.77


def breadboard_svg():
    """Green breakout board following svg/ATECC608B/svg.breadboard.ATECC608B_breadboard.svg:
    chip laid HORIZONTAL with its 4+4 leads pointing UP / DOWN, header pins in two
    vertical columns (left = pins 1..4 top->bottom, right = pins 8..5 top->bottom,
    i.e. counter clockwise), pin NUMBERS horizontal and OUTSIDE the pads (x = 35 / 465),
    top mark horizontal and centred, pin-1 dot at the lower-left of the body."""
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
             'viewBox="0 0 %.0f %.0f">\n' % (BB_W * 0.0254, BB_H * 0.0254, BB_W, BB_H))
    L.append(' <g id="breadboard">\n')
    L.append('  <rect x="0" y="0" width="%.0f" height="%.0f" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n'
             % (BB_W, BB_H))
    # chip body (landscape) + 4+4 gull-wing leads pointing up / down
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#303030" stroke="none"/>\n'
             % (BODY_X, BODY_Y, BODY_W, BODY_H))
    for i in range(4):
        x = LEAD_X0 + i * LEAD_PITCH
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#c0c0c0" stroke="none"/>\n'
                 % (x, LEAD_TOP_Y, LEAD_W, LEAD_LEN))
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#c0c0c0" stroke="none"/>\n'
                 % (x, LEAD_BOT_Y, LEAD_W, LEAD_LEN))
    # pin-1 index dot, lower-left of the body (same as the reference part)
    L.append('  <circle cx="175.20" cy="302.36" r="11.02" fill="#c0c0c0" stroke="none"/>\n')
    # top mark: horizontal, centred in the body
    L.append('  <text x="%.2f" y="262.60" font-size="32" fill="#ffffff" text-anchor="middle" '
             'dominant-baseline="central" font-family="DroidSans">CH32V002</text>\n' % (BB_W / 2))
    # header pads (gold) + horizontal numbers OUTSIDE the pads
    for col, order, tx in ((0, (0, 1, 2, 3), 35.0), (1, (7, 6, 5, 4), 465.0)):
        for i, cn in enumerate(order):
            y = PIN_Y0 + i * PIN_PITCH
            L.append('  <circle id="connector%dpin" connectorname="%s" cx="%.1f" cy="%.1f" r="%.1f" '
                     'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n'
                     % (cn, PIN_NAMES[cn], PIN_X[col], y, PAD_R))
            L.append('  <circle cx="%.1f" cy="%.1f" r="%.1f" fill="#2b2b2b" stroke="none"/>\n'
                     % (PIN_X[col], y, HOLE_R))
            num = i + 1 if col == 0 else 8 - i
            L.append('  <text x="%.1f" y="%.1f" font-size="48" fill="#ffffff" text-anchor="middle" '
                     'dominant-baseline="central" font-family="DroidSans">%d</text>\n' % (tx, y, num))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ----------------------------------------------------------------- schematic
SCHEM_LEFT = [(0, "PD6/PA1", 1), (1, "VSS", 2), (2, "PA2", 3), (3, "VDD", 4)]
SCHEM_RIGHT = [(7, "PD1/PD4/PD5", 8), (6, "PC4", 7), (5, "PC2", 6), (4, "PC1", 5)]


def schematic_svg():
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="104" viewBox="0 0 150 104">\n')
    L.append(' <g id="schematic">\n')
    BL, BR, BT, BB = 34, 118, 10, 90
    FN = 7
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" stroke="#000000" stroke-width="1.6"/>\n'
             % (BL, BT, BR - BL, BB - BT))
    PIN_PITCH = 16
    PIN_Y0 = int(BT + (BB - BT - 3 * PIN_PITCH) / 2)
    for i, (cn, lab, num) in enumerate(SCHEM_LEFT):
        y = PIN_Y0 + i * PIN_PITCH
        L.append('  <line class="pin" id="connector%dpin" connectorname="%s" x1="%d" y1="%d" x2="%d" y2="%d" stroke="#787878" stroke-width="1.0"/>\n'
                 % (cn, cn, BL, y, 10, y))
        L.append('  <rect class="terminal" id="connector%dterminal" x="10" y="%d" width="0.0001" height="0.0001" fill="none"/>\n' % (cn, y))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="start" font-family="DroidSans">%s</text>\n'
                 % (BL + FN, y + int(FN * 0.35), FN, lab))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#8C8C8C" text-anchor="middle" font-family="DroidSans">%d</text>\n'
                 % ((10 + BL) // 2, y - 3, FN, num))
    for i, (cn, lab, num) in enumerate(SCHEM_RIGHT):
        y = PIN_Y0 + i * PIN_PITCH
        L.append('  <line class="pin" id="connector%dpin" connectorname="%s" x1="%d" y1="%d" x2="%d" y2="%d" stroke="#787878" stroke-width="1.0"/>\n'
                 % (cn, cn, BR, y, 142, y))
        L.append('  <rect class="terminal" id="connector%dterminal" x="142" y="%d" width="0.0001" height="0.0001" fill="none"/>\n' % (cn, y))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="end" font-family="DroidSans">%s</text>\n'
                 % (BR - FN, y + int(FN * 0.35), FN, lab))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#8C8C8C" text-anchor="middle" font-family="DroidSans">%d</text>\n'
                 % ((BR + 142) // 2, y - 3, FN, num))
    txc, tyc = (BL + BR) // 2, (BT + BB) // 2
    L.append('  <text x="%d" y="%d" font-size="9" fill="#000000" text-anchor="middle" font-family="DroidSans" '
             'transform="rotate(90 %d %d)">CH32V002</text>\n' % (txc, tyc, txc, tyc))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ----------------------------------------------------------------------- pcb
def pcb_svg():
    """SOP8 SMD land pattern in the ATECC608B style
    (reference: svg/ATECC608B/svg.pcb.ATECC608B_pcb.svg):
      - pads 0.70 x 1.80 mm, pitch 1.27 mm, row centre distance 5.40 mm
      - pad ids = connectorNpad, fill #F7BD13, with the empty <g id="copper0"/>
      - silkscreen = two side lines + pin-1 dot
      - svg 7.02 x 8.50 mm, viewBox "-3.51 -4.25 7.02 8.50"
    Pin 1 sits at the BOTTOM-LEFT (the package is drawn rotated 90 deg, matching
    the breadboard view).  Plain <rect> only -- NO rx/ry, otherwise Fritzing
    falls back to a 1 mil scan-line fill on copper / mask / paste."""
    PAD_W, PAD_H, PITCH = 0.700, 1.800, 1.27
    X0, Y_BOT, Y_TOP = -2.255, 1.800, -3.600
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
    L.append('<!-- %s -->\n' % TITLE)
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="7.02mm" height="8.50mm" '
             'viewBox="-3.51 -4.25 7.02 8.50">\n')
    L.append('  <g id="copper1">\n')
    for i, cn in enumerate((0, 1, 2, 3)):        # bottom row: pins 1..4, left -> right
        L.append('<rect id="connector%dpad" x="%.3f" y="%.3f" width="%.3f" height="%.3f" '
                 'fill="#F7BD13" stroke="none" connectorname="%s"/>\n'
                 % (cn, X0 + i * PITCH, Y_BOT, PAD_W, PAD_H, PIN_NAMES[cn]))
    for i, cn in enumerate((7, 6, 5, 4)):        # top row: pins 8..5, left -> right
        L.append('<rect id="connector%dpad" x="%.3f" y="%.3f" width="%.3f" height="%.3f" '
                 'fill="#F7BD13" stroke="none" connectorname="%s"/>\n'
                 % (cn, X0 + i * PITCH, Y_TOP, PAD_W, PAD_H, PIN_NAMES[cn]))
    L.append('<g id="copper0"/>\n')
    L.append('  </g>\n')
    L.append('  <g id="silkscreen">\n')
    L.append('<line x1="-2.525" y1="-1.95" x2="-2.525" y2="1.95" stroke="#f0f0f0" stroke-width="0.15"/>\n')
    L.append('<line x1="2.525" y1="-1.95" x2="2.525" y2="1.95" stroke="#f0f0f0" stroke-width="0.15"/>\n')
    L.append('<circle cx="-2.955" cy="2.7" r="0.4" fill="#f0f0f0" stroke="none"/>\n')
    L.append('  </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------------- icon
def icon_svg():
    """SOP8 top view, 4 units/mm: body 3.9 x 5.0 mm, 4+4 gull-wing leads at
    1.27 mm pitch, lead 0.5 x 0.95 mm, pin-1 index dot, top mark."""
    S = 4.0
    BW, BH = 3.9 * S, 5.0 * S                  # 15.6 x 20.0
    BX, BY = (32 - BW) / 2, (32 - BH) / 2      # 8.2, 6.0
    PITCH, PW, PL = 1.27 * S, 0.5 * S, 0.95 * S
    yc0 = 16 - 3 * PITCH / 2
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n')
    L.append(' <g id="icon">\n')
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="0.3" ry="0.3" fill="#303030" stroke="none"/>\n'
             % (BX, BY, BW, BH))
    for i in range(4):
        yc = yc0 + i * PITCH
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>\n'
                 % (BX - PL, yc - PW / 2, PL, PW))
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>\n'
                 % (BX + BW, yc - PW / 2, PL, PW))
    L.append('  <circle cx="%.2f" cy="%.2f" r="0.9" fill="#c0c0c0" stroke="none"/>\n' % (BX + 1.7, BY + 1.7))
    L.append('  <text x="16" y="16" font-size="2.2" font-family="DroidSans" fill="#c0c0c0" '
             'text-anchor="middle" transform="rotate(90 16 16)">CH32V002</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ----------------------------------------------------------------------- fzp
def fzp_xml():
    conns = []
    for cn in range(8):
        name = PIN_NAMES[cn]
        conns.append(
            '  <connector id="connector%d" name="%s" type="male">\n'
            '   <description>%s</description>\n'
            '   <views>\n'
            '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n'
            '    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n'
            '    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n'
            '   </views>\n'
            '  </connector>\n' % (cn, name, DESC[name], cn, cn, cn, cn))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <label>U</label>\n'
        ' <date>2026-09-23</date>\n'
        ' <tags><tag>IC</tag><tag>MCU</tag><tag>RISC-V</tag><tag>CH32V002</tag><tag>CH32V003</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">MCU</property>\n'
        '  <property name="chip">CH32V002</property>\n'
        '  <property name="pins">8</property>\n'
        '  <property name="part number">CH32V002J4M6</property>\n'
        '  <property name="package">SOP8</property>\n'
        ' </properties>\n'
        ' <description>WCH CH32V002J4M6 RISC-V MCU, SOP8 3.9x5.0 mm / 1.27 mm pitch, 2.5-5 V, 12-bit ADC. Pin compatible with CH32V003J4M6 (10-bit ADC + OPA) - drop-in. Pin 1 = PD6/PA1 and pin 8 = PD1/PD4/PD5 are shorted inside the package, input use only.</description>\n'
        ' <views>\n'
        '  <iconView><layers image="%s"><layer layerId="icon"/></layers></iconView>\n'
        '  <breadboardView fliphorizontal="true" flipvertical="true"><layers image="%s"><layer layerId="breadboard"/></layers></breadboardView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true"><layers image="%s"><layer layerId="schematic"/></layers></schematicView>\n'
        '  <pcbView><layers image="%s"><layer layerId="silkscreen"/><layer layerId="copper1"/></layers></pcbView>\n'
        ' </views>\n'
        ' <connectors>\n%s</connectors>\n'
        '</module>\n'
    ) % (PART_ID, TITLE, ICON_REF, BB_REF, SCHEM_REF, PCB_REF, "".join(conns))


def main():
    files = {
        ICON_SVG: icon_svg(),
        BB_SVG: breadboard_svg(),
        SCHEM_SVG: schematic_svg(),
        PCB_SVG: pcb_svg(),
        FZP: fzp_xml(),
    }
    for fn, text in files.items():
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %-46s %6d bytes" % (fn, len(text.encode("utf-8"))))
    os.makedirs(FZPZ_DIR, exist_ok=True)
    dst = os.path.join(FZPZ_DIR, FZPZ)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in (FZP, ICON_SVG, BB_SVG, SCHEM_SVG, PCB_SVG):   # flat, no folders
            z.write(os.path.join(OUT_DIR, fn), fn)
    print("wrote %s  (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    main()
