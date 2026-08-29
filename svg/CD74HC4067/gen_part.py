# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for the CD74HC4067 16-channel analog
multiplexer / demultiplexer. The BREADBOARD view shows the generic 16-channel
analog MUX dev board used in the Aurora Tessellation project (Taobao generic
board), so it drops straight onto a breadboard for prototyping; the icon /
schematic / PCB views show the actual TSSOP-24 chip.

The dev board exposes the chip's 16 channels (C0..C15), the common line
(SIG, labelled DIG on some boards), the 4 address selects (S0..S3), the
active-low enable (EN) and power (VCC, GND) as two rows of 2.54mm male
header pins, so it plugs straight into a breadboard.

Terminals are named after the BOARD silkscreen (C0..C15 / SIG / S0..S3 /
EN / VCC / GND), NOT the bare-chip pin numbers -- the schematic-spec.md
explicitly asks for this so the prototype wiring matches the board labels.

Connector model (connector0..23):
  connector0..15  = C0..C15   (left header, top->bottom)
  connector16     = SIG
  connector17..20 = S0..S3
  connector21     = EN
  connector22     = VCC
  connector23     = GND

Follows the repo part-dev-guide + verified conventions:
  - .fzp image refs use subdirectory paths (icon/, breadboard/, schematic/, pcb/)
  - schematic pins use class='pin'/connectorname + class='terminal'
  - breadboard: RIGHT header (SIG..GND) sits on the Fritzing 7.2-unit hole
    grid (holes at 3.6+7.2k -> internal 50+100k with the scale(0.072) wrapper)
    and plugs in; the LEFT header (C0..C15) is intentionally OFF-grid so it
    can NOT be inserted into breadboard holes (user, 2026-08-29)
  - SMD PCB land pattern (TSSOP-24, datasheet p.21): 24 pads in 2 cols x 12,
    1.5 x 0.45 mm (R0.05), column centre distance 5.8 mm, pitch 0.65 mm, on
    copper1 only (matches TS3A44159 style); silkscreen lines + pin-1 dot
  - .fzpz goes to the repo-level fzpz/ directory (flat zip, subdir refs)
  - schematic svg is 裁边'd (content margin 3) like the other parts
"""

import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CD74HC4067"
TITLE = "CD74HC4067"
FZPZ = "CD74HC4067.fzpz"

BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID

BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
PCB_REF = "pcb/%s_pcb.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# Connector signal names (board silkscreen order).
NAMES = ["C%d" % i for i in range(16)] + ["SIG", "S0", "S1", "S2", "S3", "EN", "VCC", "GND"]

DESC = {
    "SIG": "Common line (COM)",
    "S0": "Address select 0 (LSB)", "S1": "Address select 1",
    "S2": "Address select 2", "S3": "Address select 3 (MSB)",
    "EN": "Enable (active low)", "VCC": "Power 2..6V", "GND": "Ground",
}
for i in range(16):
    DESC["C%d" % i] = "Channel %d" % i

# ---- geometry (internal units: 100 = 2.54 mm) ----
BB_SCALE = 0.072          # 7.2 breadboard units per 100 internal units
W, H = 750, 1600          # board overall incl. headers (19.05 x 40.64 mm)
# board body is WIDER than the two header columns (real CD74HC4067 dev board),
# sized just enough for headers + chip + mounting holes + small top/bottom margin
BOARD_X0, BOARD_X1 = 35, W - 35     # board body edges
# Left header (C0..C15): OFF the breadboard hole grid (on-grid internal x is
# 50+100k; 90 -> 6.48 rendered -> NOT in a hole) so it can NOT be inserted.
PX_L = 90
# Right header (SIG..GND): ON the breadboard hole grid (X=650 = 50+100*6, Y=
# 450+100j = 50+100k) so it plugs straight into the breadboard holes.
PX_R = 650
PY0 = 50                  # C15 top-left pin centre y (ON the 100-unit grid so
                          # the left header sits in clean breadboard rows)
PITCH = 100               # 2.54 mm
N_L = 16                  # C0..C15
N_R = 8                   # SIG,S0..S3,EN,VCC,GND
RIGHT_Y0 = 450            # first right pin y (450 = 50+100*4 -> ON the grid)


def _pin_y(i):
    return PY0 + i * PITCH


def _rpin_y(i):
    return RIGHT_Y0 + i * PITCH


# ------------------------------------------------------------------ breadboard
ICON_SCALE = 100.0 / (2.54 * 3.0)   # icon units (3/mm) -> internal (100/2.54mm) = 13.1234


def _icon_inner():
    """Inner drawing of the icon (the <g id="icon">...</g> block) so the real
    TSSOP-24 chip can be embedded in the breadboard at its true physical size."""
    m = re.search(r'<g id="icon">\n(.*?)</g>\n', icon_svg(), re.S)
    return m.group(1)


def _board_path_with_holes(x0, y0, x1, y1, rr, hr, holes):
    """Board outline (rounded if rr>0, else SQUARE) + mounting-hole cut-outs
    (fill-rule evenodd), internal units. holes = list of (cx, cy) cut-out
    centres, hr = hole radius. Matches the TFTSPI1.9in breadboard style."""
    if rr > 0:
        p = "M%.1f %.1f L%.1f %.1f A%d %d 0 0 1 %.1f %.1f L%.1f %.1f A%d %d 0 0 1 %.1f %.1f " \
            "L%.1f %.1f A%d %d 0 0 1 %.1f %.1f L%.1f %.1f A%d %d 0 0 1 %.1f %.1f Z" % (
                x0 + rr, y0, x1 - rr, y0, rr, rr, x1, y0 + rr,
                x1, y1 - rr, rr, rr, x1 - rr, y1,
                x0 + rr, y1, rr, rr, x0, y1 - rr,
                x0, y0 + rr, rr, rr, x0 + rr, y0)
    else:
        p = "M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z" % (x0, y0, x1, y0, x1, y1, x0, y1)
    for (hx, hy) in holes:
        p += " M%.1f %.1f A%d %d 0 1 1 %.1f %.1f A%d %d 0 1 1 %.1f %.1f Z" % (
            hx, hy - hr, hr, hr, hx, hy + hr, hr, hr, hx, hy - hr)
    return p


def _smd0603(cx, cy, body, vertical=False):
    """0603 SMD passive (1.6 x 0.8 mm = 63 x 31 units): 2 silver end pads +
    dark body. vertical=True lays it tall (31 x 63, pads top/bottom). No label."""
    w, h = (31, 63) if vertical else (63, 31)
    pad = 12
    if vertical:
        return (
            '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#d8d8d8" stroke="none"/>\n' % (cx - w / 2, cy - h / 2 - pad, w, pad) +
            '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="none"/>\n' % (cx - w / 2, cy - h / 2, w, h, body) +
            '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#d8d8d8" stroke="none"/>\n' % (cx - w / 2, cy + h / 2, w, pad))
    return (
        '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#d8d8d8" stroke="none"/>\n' % (cx - w / 2 - pad, cy - h / 2, pad, h) +
        '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="none"/>\n' % (cx - w / 2, cy - h / 2, w, h, body) +
        '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#d8d8d8" stroke="none"/>\n' % (cx + w / 2, cy - h / 2, pad, h))


def breadboard_svg():
    """Realistic DARK-BLUE breakout board (matches the Taobao board): SQUARE
    board (no rounded corners); the real TSSOP-24 chip (the icon drawing at
    true 1:1 size, rotated 90 deg CCW so it sits landscape with the label
    reading horizontally) in the middle; silkscreen pin labels INSIDE the board
    (left header reversed: C15 top-left, C0 bottom-left; right header S-pins
    ordered S3..S0 so S0 is at the bottom), two mounting holes on the RIGHT
    side, a vertical 0603 resistor left of S3 and a vertical 0603 capacitor
    left of GND (no labels), and the '16-Channel Analog Multiplexer' legend
    near the bottom edge. The RIGHT header (SIG..GND) sits exactly ON the
    breadboard hole grid (X=650, Y=450+100j) and plugs in; the LEFT header
    (C0..C15) is intentionally OFF-grid (cannot be inserted). The viewBox is
    trimmed (裁边) tightly around the board."""
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    # trim (裁边): crop the viewBox tightly around the board body
    VB_M = 3.0                              # internal margin around the board
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" viewBox="%.2f %.2f %.2f %.2f">\n'
             % (W * 0.0254, H * 0.0254,
                (BOARD_X0 - VB_M) * BB_SCALE, 0.0,
                (BOARD_X1 - BOARD_X0 + 2 * VB_M) * BB_SCALE, H * BB_SCALE))
    L.append(' <g id="breadboard" transform="scale(%g)">\n' % BB_SCALE)
    # ---- board body: DARK BLUE solder mask (#2c5086, matches TFTSPI1.9in),
    #     SQUARE corners (rr=0), small top/bottom margins (pins stay on the
    #     breadboard hole grid), 2 mounting-hole
    #     cut-outs (r=1mm, TFTSPI1.9in style). Holes right-aligned with the
    #     right-header pins (right edge = PX_R+PIN_R); bottom hole's bottom edge
    #     aligned with C0's pin bottom ----
    PIN_R, HOLE_R = 26, 39
    right_edge = PX_R + PIN_R
    hole_cx = right_edge - HOLE_R
    c0_bottom = _pin_y(N_L - 1) + PIN_R          # C0 (bottom-left) pin bottom = 1592
    holes = [(hole_cx, 70), (hole_cx, c0_bottom - HOLE_R)]   # top-right + bottom-right
    L.append('  <path d="%s" fill="#2c5086" fill-rule="evenodd" stroke="#1d3a61" stroke-width="8"/>\n'
             % _board_path_with_holes(BOARD_X0, 0, BOARD_X1, H, 0, HOLE_R, holes))
    # ---- chip: the icon drawing at true 1:1 size, rotated 90 deg CCW (landscape,
    #     leads on top/bottom, label reads horizontally) ----
    cx, cy = (BOARD_X0 + BOARD_X1) // 2, H // 2
    L.append('  <g transform="translate(%.3f,%.3f) scale(%.5f) rotate(-90 16 16)">\n' % (cx - 16 * ICON_SCALE, cy - 16 * ICON_SCALE, ICON_SCALE))
    L.append(_icon_inner())
    L.append('  </g>\n')
    # ---- silkscreen legend near the BOTTOM board edge; 'Multiplexer' bottom
    #     aligned with C0's pin bottom (y = 1576) ----
    L.append('  <text x="%d" y="%d" font-size="50" font-family="DroidSans" fill="#ffffff" text-anchor="middle">16-Channel</text>\n' % (cx, 1466))
    L.append('  <text x="%d" y="%d" font-size="50" font-family="DroidSans" fill="#ffffff" text-anchor="middle">Analog</text>\n' % (cx, 1521))
    L.append('  <text x="%d" y="%d" font-size="50" font-family="DroidSans" fill="#ffffff" text-anchor="middle">Multiplexer</text>\n' % (cx, 1576))
    # ---- SMD passives (0603), no labels, VERTICAL: resistor left of S3,
    #     capacitor left of GND (photo) ----
    L.append(_smd0603(510, 550, "#3a3a3a", vertical=True))    # resistor, left of S3
    L.append(_smd0603(510, 1150, "#5a4632", vertical=True))   # capacitor, left of GND
    # (mounting holes are evenodd cut-outs in the board path above)
    # ---- left header: C0..C15 (male pins, OFF the breadboard grid); REVERSED
    #     so C15 sits top-left and C0 sits bottom-left ----
    for i in range(N_L):
        x, y = PX_L, _pin_y(N_L - 1 - i)
        L.append('  <circle cx="%d" cy="%d" r="26" fill="#b8b8b8" stroke="#6a6a6a" stroke-width="5" id="connector%dpin"/>\n' % (x, y, i))
        L.append('  <text x="%d" y="%d" font-size="34" font-family="DroidSans" fill="#ffffff" text-anchor="start">%s</text>\n'
                 % (PX_L + 45, y + 9, NAMES[i]))
    # ---- right header (male pins, ON the breadboard grid); S-pin order matches
    #     the real board: SIG, S3, S2, S1, S0, EN, VCC, GND (S0 at the bottom) ----
    right_order = [16, 20, 19, 18, 17, 21, 22, 23]   # SIG,S3,S2,S1,S0,EN,VCC,GND
    for j in range(N_R):
        cn = right_order[j]
        x, y = PX_R, _rpin_y(j)
        L.append('  <circle cx="%d" cy="%d" r="26" fill="#b8b8b8" stroke="#6a6a6a" stroke-width="5" id="connector%dpin"/>\n' % (x, y, cn))
        L.append('  <text x="%d" y="%d" font-size="34" font-family="DroidSans" fill="#ffffff" text-anchor="end">%s</text>\n'
                 % (PX_R - 45, y + 9, NAMES[cn]))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
# Datasheet p.4 Fig 4-1 (24-pin TSSOP/SOIC/PDIP, top view): 12 pins per side,
# pin 1 = COMMON INPUT/OUTPUT at top-left. Each entry maps a schematic pin to
# (fzp connector id, chip function label shown in the symbol, pin number).
# The chip's I0..I15 correspond to the board's C0..C15 (I0=C0 ... I15=C15),
# COM=SIG, E=EN.
SCHEM_LEFT = [   # (connector_id, chip_label, pin_number)
    (16, "COM",  1), (7, "I7", 2), (6, "I6", 3), (5, "I5", 4),
    (4,  "I4",  5), (3, "I3", 6), (2, "I2", 7), (1, "I1", 8),
    (0,  "I0",  9), (17, "S0", 10), (18, "S1", 11), (23, "GND", 12),
]
SCHEM_RIGHT = [  # (connector_id, chip_label, pin_number)
    (22, "VCC", 24), (8, "I8", 23), (9, "I9", 22), (10, "I10", 21),
    (11, "I11", 20), (12, "I12", 19), (13, "I13", 18), (14, "I14", 17),
    (15, "I15", 16), (21, "Ē", 15), (19, "S2", 14), (20, "S3", 13),  # Ē = active-low enable
]


def schematic_svg():
    """Chip symbol matching the datasheet p.4 Fig 4-1: 12 pins LEFT + 12 RIGHT,
    pin 1 (COMMON INPUT/OUTPUT = COM) at top-left, pin 24 (V_CC) at top-right.
    Visible labels are the CHIP function names
    (I0..I15, COM, S0..S3, E, VCC, GND) with pin numbers outside; each pin maps
    to the board connector via SCHEM_LEFT/RIGHT (I0=C0, ..., I15=C15)."""
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="175" height="230" viewBox="0 0 175 230">\n')
    L.append(' <g id="schematic">\n')
    BL, BR, BT, BB = 42, 128, 8, 214
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" stroke="#000000" stroke-width="1.6"/>\n'
             % (BL, BT, BR - BL, BB - BT))
    mid = (BL + BR) // 2
    # chip name, rotated 90 deg CLOCKWISE; nudged RIGHT by one char-width (6)
    # and UP by half a char-width (3) per the user
    mcy = (BT + BB) // 2
    txc, tyc = mid - 7, mcy + 3
    L.append('  <text x="%d" y="%d" font-size="10" fill="#000000" text-anchor="middle" font-family="DroidSans" transform="rotate(90 %d %d)">CD74HC4067</text>\n'
             % (txc, tyc, txc, tyc))
    # 12 pins each side, 16-unit pitch; the pin block is centred in the box so
    # the top gap (box edge to COM) equals the bottom gap (box edge to GND)
    PITCH = 16
    PIN_Y0 = int(BT + (BB - BT - 11 * PITCH) / 2)   # first pin y = 23
    for i, (cn, lab, num) in enumerate(SCHEM_LEFT):
        y = PIN_Y0 + i * PITCH
        L.append('  <line class="pin" id="connector%dpin" connectorname="%d" x1="%d" y1="%d" x2="%d" y2="%d" stroke="#787878" stroke-width="1.0"/>\n'
                 % (cn, cn, BL, y, 14, y))
        L.append('  <rect class="terminal" id="connector%dterminal" x="14" y="%d" width="0.0001" height="0.0001" fill="none"/>\n' % (cn, y))
        L.append('  <text x="%d" y="%d" font-size="6.5" fill="#333333" text-anchor="start" font-family="DroidSans">%s</text>\n'
                 % (BL + 4, y + 4, lab))
        # pin number directly ABOVE the pin line, centred on it
        L.append('  <text x="%d" y="%d" font-size="6.5" fill="#333333" text-anchor="middle" font-family="DroidSans">%d</text>\n'
                 % ((14 + BL) // 2, y - 3, num))
    for i, (cn, lab, num) in enumerate(SCHEM_RIGHT):
        y = PIN_Y0 + i * PITCH
        L.append('  <line class="pin" id="connector%dpin" connectorname="%d" x1="%d" y1="%d" x2="%d" y2="%d" stroke="#787878" stroke-width="1.0"/>\n'
                 % (cn, cn, BR, y, 158, y))
        L.append('  <rect class="terminal" id="connector%dterminal" x="158" y="%d" width="0.0001" height="0.0001" fill="none"/>\n' % (cn, y))
        L.append('  <text x="%d" y="%d" font-size="6.5" fill="#333333" text-anchor="end" font-family="DroidSans">%s</text>\n'
                 % (BR - 4, y + 4, lab))
        # pin number directly ABOVE the pin line, centred on it
        L.append('  <text x="%d" y="%d" font-size="6.5" fill="#333333" text-anchor="middle" font-family="DroidSans">%d</text>\n'
                 % ((BR + 158) // 2, y - 3, num))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ PCB
def pcb_svg():
    """TSSOP-24 SMD LAND PATTERN (datasheet p.21): 24 pads in 2 columns x 12,
    pad 1.5 x 0.45 mm (R0.05 corners), column centre distance 5.8 mm, pitch
    0.65 mm, in mm units. Left column = pads 1..12 (top->bottom) mapped to
    connectors COM,I7..I0,S0,S1,GND; right column = pads 24..13 mapped to
    VCC,I8..I15,E,S2,S3. SMD pads on copper1 (matches TS3A44159 style)."""
    PAD_W, PAD_H, PITCH, COL, RR = 1.5, 0.45, 0.65, 5.8, 0.05
    y0 = -(11 * PITCH) / 2                       # top pad centre y = -3.575
    xl, xr = -COL / 2 - PAD_W / 2, COL / 2 - PAD_W / 2   # -3.65, 2.15
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="7.9mm" height="8.8mm" viewBox="-3.95 -4.4 7.9 8.8">\n')
    L.append(' <g id="silkscreen">\n')
    L.append('  <line x1="-2.2" y1="4.1" x2="2.2" y2="4.1" stroke="#FFFFFF" stroke-width="0.15" fill="none"/>\n')
    L.append('  <line x1="-2.2" y1="-4.1" x2="2.2" y2="-4.1" stroke="#FFFFFF" stroke-width="0.15" fill="none"/>\n')
    L.append('  <circle cx="-1.5" cy="-3.35" r="0.25" fill="#FFFFFF" stroke="none"/>\n')
    L.append(' </g>\n')
    L.append(' <g id="copper1">\n')
    for i, (cn, lab, num) in enumerate(SCHEM_LEFT):
        y = y0 + i * PITCH
        L.append('  <rect x="%.3f" y="%.3f" width="%.2f" height="%.2f" rx="%.2f" ry="%.2f" id="connector%dpin" fill="#f7bf13" fill-opacity="1" stroke="none"/>\n'
                 % (xl, y - PAD_H / 2, PAD_W, PAD_H, RR, RR, cn))
    for i, (cn, lab, num) in enumerate(SCHEM_RIGHT):
        y = y0 + i * PITCH
        L.append('  <rect x="%.3f" y="%.3f" width="%.2f" height="%.2f" rx="%.2f" ry="%.2f" id="connector%dpin" fill="#f7bf13" fill-opacity="1" stroke="none"/>\n'
                 % (xr, y - PAD_H / 2, PAD_W, PAD_H, RR, RR, cn))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ icon
def icon_svg():
    """32x32 chip icon following the datasheet p.20 PW0024A (TSSOP-24)
    package outline: body 7.8 x 4.4 mm, 12 leads per long side at 0.65 mm
    pitch, lead width 0.30 mm, pin-1 index area, top mark. 3 units/mm.
    Per the user (2026-08-29): ONLY the black chip body and the label are
    rotated 90 deg CLOCKWISE (body becomes portrait, label reads top-to-
    bottom); the gold leads stay on the left/right sides as horizontal
    gull-wing bars (they are NOT rotated)."""
    S = 3.0                        # units per mm
    BW, BH = 7.8 * S, 4.4 * S      # body 23.4 x 13.2 (landscape source)
    # rotate ONLY the body 90 deg CW about the 32x32 centre -> portrait
    BWW, BHH = BH, BW              # body portrait 13.2 x 23.4
    BX, BY = (32 - BWW) / 2, (32 - BHH) / 2      # 9.4, 4.3
    PITCH = 0.65 * S               # lead pitch 1.95
    PW, PL = 0.3 * S, 1.0 * S      # lead width 0.9, lead length 3.0
    yc0 = 16 - 11 * PITCH / 2      # first lead centre y (5.275) -- UNCHANGED
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n')
    L.append(' <g id="icon">\n')
    # chip body, rounded corners (0.1 mm = 0.3) -- portrait (rotated 90 CW)
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="0.3" ry="0.3" fill="#303030" stroke="none"/>\n' % (BX, BY, BWW, BHH))
    # 24 gold gull-wing leads: 12 left + 12 right (horizontal bars, NOT rotated)
    for i in range(12):
        yc = yc0 + i * PITCH
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>\n' % (BX - PL, yc - PW / 2, PL, PW))
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>\n' % (BX + BWW, yc - PW / 2, PL, PW))
    # pin-1 index dot (top-left of the portrait body, matching "PIN 1 INDEX AREA")
    L.append('  <circle cx="%.2f" cy="%.2f" r="0.9" fill="#c0c0c0" stroke="none"/>\n' % (BX + 1.9, BY + 1.9))
    # top mark text, rotated 90 CW (reads top-to-bottom), centred on body
    L.append('  <text x="16" y="16" font-size="2.4" font-family="DroidSans" fill="#c0c0c0" text-anchor="middle" transform="rotate(90 16 16)" stroke="none" stroke-width="0">HP4067</text>\n')
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ fzp
def fzp_xml():
    conns = []
    for cn in range(len(NAMES)):
        name = NAMES[cn]
        conns.append(
            '  <connector id="connector%d" name="%s" type="male">\n'
            '   <description>%s</description>\n'
            '   <views>\n'
            '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n'
            '    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n'
            '    <pcbView><p layer="copper1" svgId="connector%dpin"/></pcbView>\n'
            '   </views>\n'
            '  </connector>\n' % (cn, name, DESC.get(name, name), cn, cn, cn, cn))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <label>U</label>\n'
        ' <date>2026-08-29</date>\n'
        ' <tags><tag>IC</tag><tag>MUX</tag><tag>analog</tag><tag>CD74HC4067</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">MUX</property>\n'
        '  <property name="chip">CD74HC4067</property>\n'
        '  <property name="pins">24</property>\n'
        '  <property name="part number">CD74HC4067</property>\n'
        ' </properties>\n'
        ' <description>16-channel analog/digital multiplexer (CD74HC4067), terminals C0-C15 / SIG / S0-S3 / EN / VCC / GND.</description>\n'
        ' <views>\n'
        '  <iconView><layers image="%s"><layer layerId="icon"/></layers></iconView>\n'
        '  <breadboardView fliphorizontal="true" flipvertical="true"><layers image="%s"><layer layerId="breadboard"/></layers></breadboardView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true"><layers image="%s"><layer layerId="schematic"/></layers></schematicView>\n'
        '  <pcbView><layers image="%s"><layer layerId="silkscreen"/><layer layerId="copper1"/></layers></pcbView>\n'
        ' </views>\n'
        ' <connectors>\n%s</connectors>\n'
        '</module>\n'
    ) % (PART_ID, TITLE, ICON_REF, BB_REF, SCHEM_REF, PCB_REF, "".join(conns))


# -------------------------------------------------- schematic 裁边 (trim)
def _num_attrs(tag, names):
    out = {}
    for n in names:
        m = re.search(r'\b%s="(-?[\d.]+)"' % n, tag)
        if m:
            out[n] = float(m.group(1))
    return out


def content_bbox(text):
    xs, ys = [], []
    for m in re.finditer(r'<(rect|circle|ellipse|line|polygon|polyline|path|text)(\b[^>]*?)/?>', text):
        tag, attrs = m.group(1), m.group(2)
        a = _num_attrs(attrs, ["x", "y", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "width", "height"])
        if tag == "rect":
            if "x" in a and "y" in a:
                xs += [a["x"], a["x"] + a.get("width", 0)]
                ys += [a["y"], a["y"] + a.get("height", 0)]
        elif tag in ("circle", "ellipse"):
            if "cx" in a and "cy" in a:
                r = a.get("r", max(a.get("rx", 0), a.get("ry", 0)))
                xs += [a["cx"] - r, a["cx"] + r]; ys += [a["cy"] - r, a["cy"] + r]
        elif tag == "line":
            for k in ("x1", "x2"):
                if k in a: xs.append(a[k])
            for k in ("y1", "y2"):
                if k in a: ys.append(a[k])
        elif tag in ("polygon", "polyline"):
            pts = re.search(r'\bpoints="([^"]+)"', attrs)
            if pts:
                nums = [float(z) for z in re.findall(r'-?[\d.]+', pts.group(1))]
                xs += nums[::2]; ys += nums[1::2]
        elif tag == "text":
            if "x" in a:
                fs = 10.0
                fsm = re.search(r'\bfont-size="(-?[\d.]+)"', attrs)
                if fsm:
                    fs = float(fsm.group(1))
                anc = "start"
                am = re.search(r'\btext-anchor="(\w+)"', attrs)
                if am:
                    anc = am.group(1)
                cm = re.search(r'>([^<]*)</text>', text[m.end():m.end() + 400])
                s = cm.group(1) if cm else ""
                w = len(s) * fs * 0.6           # rough glyph width estimate
                if anc == "middle":
                    xs += [a["x"] - w / 2, a["x"] + w / 2]
                elif anc == "end":
                    xs += [a["x"] - w, a["x"]]
                else:
                    xs += [a["x"], a["x"] + w]
            if "y" in a:
                ys.append(a["y"])
    return (min(xs), min(ys), max(xs), max(ys))


def _shift_attr(tag, sx, sy):
    def sh(attr, dx, dy):
        def rep(m):
            v = float(m.group(1)) - (dx if attr in ("x", "cx", "x1", "x2") else dy)
            return f'{attr}="{v:.4f}"'
        return re.sub(r'\b%s="(-?[\d.]+)"' % attr, rep, tag)
    for attr in ("x", "y", "cx", "cy", "x1", "y1", "x2", "y2"):
        tag = sh(attr, sx, sy)
    # also shift coordinate args inside transform="rotate(a cx cy)" / translate(tx ty)
    def rep_tr(m):
        content = m.group(1)
        if '(' not in content:
            return 'transform="%s"' % content
        op = content[:content.find('(')]
        inner = content[content.find('(') + 1:content.rfind(')')]
        nums = [float(z) for z in inner.split()]
        if op == 'rotate' and len(nums) >= 3:
            nums[1] -= sx; nums[2] -= sy
        elif op == 'translate' and len(nums) >= 2:
            nums[0] -= sx; nums[1] -= sy
        return 'transform="%s(%s)"' % (op, ' '.join('%.4f' % n for n in nums))
    return re.sub(r'transform="([^"]*)"', rep_tr, tag)


def trim_svg(text, margin=3.0):
    """裁边: shift content so its bbox starts at `margin` and set the svg
    width/height/viewBox to "0 0 W H" (content + 2*margin). Preserves
    self-closing tags. Returns (new_text, bbox, shift, size)."""
    mnx, mny, mxx, mxy = content_bbox(text)
    sx, sy = mnx - margin, mny - margin
    w, h = (mxx - mnx) + 2 * margin, (mxy - mny) + 2 * margin

    def shift_element(m):
        tag, attrs, selfclose = m.group(1), m.group(2), m.group(3)
        attrs2 = _shift_attr(attrs, sx, sy)
        pm = re.search(r'\bpoints="([^"]+)"', attrs2)
        if pm and tag in ("polygon", "polyline"):
            nums = [float(z) for z in re.findall(r'-?[\d.]+', pm.group(1))]
            new = []
            for i in range(0, len(nums), 2):
                new.append(f"{nums[i] - sx:.4f},{nums[i + 1] - sy:.4f}")
            attrs2 = re.sub(r'\bpoints="[^"]+"', f'points="{" ".join(new)}"', attrs2)
        return f"<{tag}{attrs2}{selfclose}>"

    out = re.sub(r'<(rect|circle|ellipse|line|polygon|polyline|path|text)(\b[^>]*?)(/?)>', shift_element, text)
    out = re.sub(r'\bviewBox="[^"]*"', f'viewBox="0 0 {w:.4f} {h:.4f}"', out, count=1)
    out = re.sub(r'\bwidth="[^"]*"', f'width="{w:.4f}"', out, count=1)
    out = re.sub(r'\bheight="[^"]*"', f'height="{h:.4f}"', out, count=1)
    return out, (mnx, mny, mxx, mxy), (sx, sy), (w, h)


def main():
    files = {
        BB_SVG: breadboard_svg(),
        SCHEM_SVG: trim_svg(schematic_svg())[0],
        PCB_SVG: pcb_svg(),
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
