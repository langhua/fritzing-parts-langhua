# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for the 4x4 WS2812B-5050 RGB matrix module.

Physical module (user-confirmed 2026-08-28, module in hand + photos):
  - 4x4 WS2812B-5050 white LEDs on a ~30 x 30 mm BLACK board, spread evenly
    across the board (LED pitch 7.5 mm, centres 3.75/11.25/18.75/26.25 mm).
  - 12 SMD bypass caps (0603, 1.6x0.8mm), arranged 3 x 4: one column of caps
    between every two LED columns (columns alternate LED/cap/LED/cap/LED/cap/LED).
  - 4 mounting holes at the centres of the four 2x2 LED quadrants:
        {1,2,7,8} -> (22.5,22.5)mm, {3,4,5,6} -> (7.5,22.5)mm,
        {9,10,15,16} -> (22.5,7.5)mm, {11,12,13,14} -> (7.5,7.5)mm.
  - 8 pins (4 top + 4 bottom), made by soldering 4-pin headers on the back
    pads and bending the pins (pliers) so they plug into a breadboard.
    Each side = a 4-pin single-row header: four 2.54 x 2.54 mm black plastic
    housings touching (one strip) extending 2.54 mm beyond the PCB edge, each
    housing with thin grey lines on BOTH sides (chamfers). + 0.64 mm sq metal
    wires 3.02 mm long. With the 2.54 mm housing and 30 mm board this puts the
    top and bottom wire rows 15 x 2.54 mm apart so both land on breadboard
    holes (a shorter wire would break grid alignment):
        bottom (left->right): GND, VCC, DIN, GND
        top    (left->right): GND, VCC, DOUT, GND
    Pins centred, 2.54 mm pitch, no pin text.
  - LED scan order (each column climbs bottom->top, columns joined at bottom):
        1@BR; right col up: 1 2 3 4; col2 up: 5 6 7 8;
        col1 up: 9 10 11 12; left col up: 13 14 15 16.
        Grid (rows top->bottom, cols left->right):
        16 12 8 4 / 15 11 7 3 / 14 10 6 2 / 13 9 5 1
        (verified against the real module).

Fritzing breadboard view scale (from the LM393 module part, which renders
correctly in Fritzing): viewBox 140.494 units = declared width 49.553791 mm,
so 1 mm = 2.835 units (hole pitch 2.54 mm = 7.2 units).

The 16 LED graphics reuse the existing WS2812B-5050 part's breadboard artwork
(svg/WS2812B/5050/svg.breadboard.WS2812B_5050_1_breadboard.svg), drawn at
natural 5050 size (LED_SIZE_MM=5.0, no scaling).

Connectors (8):
    connector0 = GND   (bottom header pin 1)
    connector1 = VCC   (bottom header pin 2)
    connector2 = DIN   (bottom header pin 3)
    connector3 = GND   (bottom header pin 4)
    connector4 = GND   (top header pin 1)
    connector5 = VCC   (top header pin 2)
    connector6 = DOUT  (top header pin 3)
    connector7 = GND   (top header pin 4)
"""

import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "WS2812B_5050_4x4_1"
TITLE = "WS2812B-5050-4x4"
PART_NUMBER = "WS2812B-5050-4x4"
PKG = "WS2812B-5050 4x4 Module (30x30mm)"

PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "WS2812B-5050-4x4.fzpz"

PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# source of the LED artwork to reuse (existing 5050 part source in this repo)
LED_SRC = os.path.abspath(os.path.join(OUT_DIR, "..", "5050",
                                       "svg.breadboard.WS2812B_5050_1_breadboard.svg"))
LED_MARKER = "translate(10.8000,21.6000) rotate(90) translate(-10.8000,-21.6000)"
LED_ART_CX, LED_ART_CY = 10.8, 21.6     # artwork centre in its own frame

# ---------------- module geometry (mm) ----------------
BOARD_MM = 30.0
LED_CENTRES_MM = [3.75, 11.25, 18.75, 26.25]      # 4x4 LEDs spread over 30mm (pitch 7.5)
LED_SIZE_MM = 5.0                                  # 5050 natural size (no scaling)
CAP_MM = (0.8, 1.6)                                # 0603 SMD cap (0.8x1.6mm), long axis vertical
CAP_X_MM = [7.5, 15.0, 22.5]                       # cap columns between LED columns
MOUNT_R_MM = 1.3                                   # mounting hole radius
MOUNT_HOLES_MM = [(7.5, 7.5), (22.5, 7.5), (7.5, 22.5), (22.5, 22.5)]   # quadrant centres
PIN_X_MM = [15.0 + d * 2.54 for d in (-1.5, -0.5, 0.5, 1.5)]  # centred header
PIN_W_MM = 2.54       # housing width (2.54x2.54mm; 4 housings touch -> header strip)
WIRE_W_MM = 0.64      # metal pin wire width (header PIN 0.64 SQ)
HOUSING_H_MM = 2.54   # black header plastic housing height (2.54 mm header)
HOUSING_OVERLAP_MM = 0.0   # housing flush at the board edge, extends 2.54 mm beyond the PCB
WIRE_H_MM = 3.02      # metal wire; with 2.54mm housing + 30mm board, rows are 15x2.54=38.1mm apart (both on grid)
LED_ROT = 180                                      # rotate each LED 180 deg (vertical)

# pcb footprint pad geometry (mm)
PAD_W_MM = 1.6        # pad width along the board edge
PAD_LEN_MM = 6.0      # pad length perpendicular to the edge
PAD_OVERHANG_MM = 1.5 # pad extends beyond the board edge

# ---------------- Fritzing breadboard units (1 mm = 2.835 units) ----------------
U = 2.835
def UU(v):
    return v * U

BOARD = UU(BOARD_MM)
LED_CENTRES = [UU(v) for v in LED_CENTRES_MM]
LED_SCALE = LED_SIZE_MM / 5.0
CAP_W, CAP_H = UU(CAP_MM[0]), UU(CAP_MM[1])
CAP_X = [UU(v) for v in CAP_X_MM]
MOUNT_R = UU(MOUNT_R_MM)
MOUNT_HOLES = [(UU(x), UU(y)) for x, y in MOUNT_HOLES_MM]
PIN_X = [UU(v) for v in PIN_X_MM]
PIN_W = UU(PIN_W_MM)
WIRE_W = UU(WIRE_W_MM)
HOUSING_H = UU(HOUSING_H_MM)
WIRE_H = UU(WIRE_H_MM)
BOTTOM_Y = BOARD

# (connector id, name, description)
BOTTOM_PINS = [
    ("connector0", "GND",  "Bottom header pin 1 - ground"),
    ("connector1", "VCC",  "Bottom header pin 2 - +5V supply"),
    ("connector2", "DIN",  "Bottom header pin 3 - data input"),
    ("connector3", "GND",  "Bottom header pin 4 - ground"),
]
TOP_PINS = [
    ("connector4", "GND",  "Top header pin 1 - ground"),
    ("connector5", "VCC",  "Top header pin 2 - +5V supply"),
    ("connector6", "DOUT", "Top header pin 3 - data output"),
    ("connector7", "GND",  "Top header pin 4 - ground"),
]
CONN = BOTTOM_PINS + TOP_PINS

# LED scan order: number -> (col_idx, row_idx); row 3 = bottom, col 3 = right
# Verified against the real module: each column climbs bottom->top,
# columns joined at the bottom (1 = bottom-right).
ORDER = {
    1: (3, 3), 2: (3, 2), 3: (3, 1), 4: (3, 0),
    5: (2, 3), 6: (2, 2), 7: (2, 1), 8: (2, 0),
    9: (1, 3), 10: (1, 2), 11: (1, 1), 12: (1, 0),
    13: (0, 3), 14: (0, 2), 15: (0, 1), 16: (0, 0),
}


def led_positions_ordered():
    """Yield (led_number, cx, cy) in serpentine order (units)."""
    for n in range(1, 17):
        ci, ri = ORDER[n]
        yield n, LED_CENTRES[ci], LED_CENTRES[ri]


def cap_positions():
    for x in CAP_X:
        for cy in LED_CENTRES:
            yield x, cy


def extract_led_artwork():
    """Return the 5050 LED artwork (inner group, centred at 10.8,21.6)."""
    with open(LED_SRC, encoding="utf-8") as f:
        lines = f.read().split("\n")
    marker = next(i for i, l in enumerate(lines) if LED_MARKER in l)
    depth = 0
    end = None
    for i in range(marker, len(lines)):
        depth += lines[i].count("<g") - lines[i].count("</g>")
        if depth <= 0:
            end = i + 1
            break
    if end is None:
        raise RuntimeError("LED artwork end not found")
    inner = "\n".join(lines[marker + 1:end - 1])          # drop wrapper open/close
    inner = re.sub(r'\s+id="[^"]*"', "", inner)           # strip ids (avoid dup ids)
    return inner


def schematic_svg():
    """Black-box symbol: left = input header, right = output header (8 pins)."""
    box = (42.0, 8.0, 36.0, 56.0)
    x, y, w, h = box
    left = [("connector0", "GND", 14), ("connector1", "VCC", 26),
            ("connector2", "DIN", 38), ("connector3", "GND", 50)]
    right = [("connector4", "GND", 14), ("connector5", "VCC", 26),
             ("connector6", "DOUT", 38), ("connector7", "GND", 50)]
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>')
    s.append('<svg version="1.1" xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="110px" height="70px" viewBox="0 0 110 70" xml:space="preserve">')
    s.append(' <g id="schematic">')
    s.append('  <rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" fill="#FFFFFF" stroke="#000000" stroke-width="0.9"/>' % (x, y, w, h))
    # pin-1 index dot: on the right of pin 1 (connector0). Dot centre sits 2.5 x radius
    # from the box's left edge (1.5r + one extra radius); the triangles use the same gap.
    pin_r = 1.3
    edge_gap = 2.5 * pin_r
    s.append('  <circle cx="%.2f" cy="%.0f" r="%.1f" fill="#000000" stroke="none"/>' % (x + edge_gap, left[0][2], pin_r))
    s.append('  <text transform="matrix(1 0 0 1 %.1f %.1f)" fill="#000000" font-family="DroidSans" font-size="4.2" text-anchor="middle">WS2812B</text>' % (x + w / 2, y + 20))
    s.append('  <text transform="matrix(1 0 0 1 %.1f %.1f)" fill="#000000" font-family="DroidSans" font-size="3.4" text-anchor="middle">4x4 RGB</text>' % (x + w / 2, y + 28))
    for cid, name, py in left:
        s.append('  <line class="pin" id="%spin" connectorname="%s" x1="24" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#787878" stroke-width="0.75"/>' % (cid, name, py, x, py))
        s.append('  <rect class="terminal" id="%sterminal" x="24" y="%.0f" width="0.0001" height="0.0001" fill="none"/>' % (cid, py))
        s.append('  <text transform="matrix(1 0 0 1 25.5 %.1f)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6">%s</text>' % (py - 0.8, name))
    for cid, name, py in right:
        s.append('  <line class="pin" id="%spin" connectorname="%s" x1="%.0f" y1="%.0f" x2="94" y2="%.0f" stroke="#787878" stroke-width="0.75"/>' % (cid, name, x + w, py, py))
        s.append('  <rect class="terminal" id="%sterminal" x="94" y="%.0f" width="0.0001" height="0.0001" fill="none"/>' % (cid, py))
        s.append('  <text transform="matrix(1 0 0 1 93 %.1f)" fill="#8C8C8C" font-family="DroidSans" font-size="2.6" text-anchor="end">%s</text>' % (py - 0.8, name))
    # DIN/DOUT data-flow triangles INSIDE the box, equilateral, height = pin-1 dot
    # diameter. DIN (left) is placed with its base at edge_gap from the left edge,
    # DOUT (right) with its tip at edge_gap from the right edge - so both use the
    # SAME distance to their side edge as the pin-1 dot centre.
    din_y = left[2][2]    # connector2 = DIN
    dout_y = right[2][2]  # connector6 = DOUT
    dot_d = 2.0 * pin_r
    half_base = dot_d / 3 ** 0.5
    s.append('  <polygon points="%.2f,%.0f %.2f,%.1f %.2f,%.1f" fill="#000000" stroke="none"/>' % (
        x + edge_gap + dot_d, din_y, x + edge_gap, din_y - half_base, x + edge_gap, din_y + half_base))
    s.append('  <polygon points="%.2f,%.0f %.2f,%.1f %.2f,%.1f" fill="#000000" stroke="none"/>' % (
        x + w - edge_gap, dout_y, x + w - edge_gap - dot_d, dout_y - half_base, x + w - edge_gap - dot_d, dout_y + half_base))
    s.append(' </g>')
    s.append('</svg>')
    return "\n".join(s)


def emit_board_content(s, art):
    """Black board (mount holes punched through) + 16 LEDs (numbered) + 12 caps with white frames."""
    r = 2.5
    b = BOARD
    d = ["M {:.2f},0".format(r),
         "H {:.2f}".format(b - r),
         "A {:.2f},{:.2f} 0 0 1 {:.2f},{:.2f}".format(r, r, b, r),
         "V {:.2f}".format(b - r),
         "A {:.2f},{:.2f} 0 0 1 {:.2f},{:.2f}".format(r, r, b - r, b),
         "H {:.2f}".format(r),
         "A {:.2f},{:.2f} 0 0 1 0,{:.2f}".format(r, r, b - r),
         "V {:.2f}".format(r),
         "A {:.2f},{:.2f} 0 0 1 {:.2f},0".format(r, r, r),
         "Z"]
    for mx, my in MOUNT_HOLES:
        d.append("M {:.2f},{:.2f} A {:.2f},{:.2f} 0 1 0 {:.2f},{:.2f} A {:.2f},{:.2f} 0 1 0 {:.2f},{:.2f} Z".format(
            mx - MOUNT_R, my, MOUNT_R, MOUNT_R, mx + MOUNT_R, my, MOUNT_R, MOUNT_R, mx - MOUNT_R, my))
    s.append('  <path d="%s" fill="#161616" fill-rule="evenodd" stroke="#4a4a4a" stroke-width="0.9"/>' % " ".join(d))
    for n, cx, cy in led_positions_ordered():
        s.append('  <g transform="translate(%.3f %.3f) rotate(%d) scale(%.4f) translate(%.2f %.2f)">%s</g>'
                 % (cx, cy, LED_ROT, LED_SCALE, -LED_ART_CX, -LED_ART_CY, art))
        s.append('  <text x="%.2f" y="%.2f" fill="#1f1f1f" font-family="DroidSans" font-size="3.0" text-anchor="middle">%d</text>'
                 % (cx, cy + 1.1, n))
    fm = UU(0.3)
    for cx, cy in cap_positions():
        s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#ffffff" stroke-width="0.4"/>' % (cx - CAP_W / 2 - fm, cy - CAP_H / 2 - fm, CAP_W + 2 * fm, CAP_H + 2 * fm))
        s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#d8d8d8"/>' % (cx - CAP_W / 2, cy - CAP_H / 2, CAP_W, CAP_H * 0.22))
        s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#d8d8d8"/>' % (cx - CAP_W / 2, cy + CAP_H / 2 - CAP_H * 0.22, CAP_W, CAP_H * 0.22))
        s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="0.2" fill="#c8b48a" stroke="#8a744a" stroke-width="0.2"/>' % (cx - CAP_W / 2, cy - CAP_H * 0.28, CAP_W, CAP_H * 0.56))


def breadboard_svg():
    """Black 30x30mm board, 16x 5050 LED art (rot 90, numbered), 12 caps,
    4 mount holes, 8 pins. Coordinates in Fritzing breadboard units (1mm=2.835u)."""
    art = extract_led_artwork()
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>')
    vw, vh = 87.0, 119.0
    s.append('<svg version="1.1" xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" '
             'width="%.2fmm" height="%.2fmm" viewBox="-1 -17 %.1f %.1f" xml:space="preserve">' % (vw / U, vh / U, vw, vh))
    s.append(' <g id="breadboard">')
    # header housing strips BEHIND the board, each housing with grey chamfer lines on both sides
    OVERLAP = UU(HOUSING_OVERLAP_MM)
    thin = 0.5
    bh_y = BOTTOM_Y - OVERLAP            # bottom header top (at/under the board edge)
    th_y = -(HOUSING_H - OVERLAP)        # top header top (above the board edge)
    for hy in (bh_y, th_y):
        for px in PIN_X:                 # 4 housings, each 2.54 wide, touching
            hx = px - PIN_W / 2
            s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#1f1f1f" stroke="none"/>' % (hx, hy, PIN_W, HOUSING_H))
            s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#9a9a9a" stroke="none"/>' % (hx, hy, thin, HOUSING_H))
            s.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#9a9a9a" stroke="none"/>' % (hx + PIN_W - thin, hy, thin, HOUSING_H))
    # board body + LEDs + caps (shared with the icon)
    emit_board_content(s, art)
    # metal pin wires (connector pins) from the housing into the breadboard, no text
    for (cid, _, _), px in zip(BOTTOM_PINS, PIN_X):
        wx = px - WIRE_W / 2
        s.append('  <rect id="%spin" x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#b9b9b9" stroke="#000000" stroke-width="0.4"/>' % (cid, wx, bh_y + HOUSING_H, WIRE_W, WIRE_H))
    for (cid, _, _), px in zip(TOP_PINS, PIN_X):
        wx = px - WIRE_W / 2
        s.append('  <rect id="%spin" x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#b9b9b9" stroke="#000000" stroke-width="0.4"/>' % (cid, wx, th_y - WIRE_H, WIRE_W, WIRE_H))
    s.append(' </g>')
    s.append('</svg>')
    return "\n".join(s)


def pcb_svg():
    """Module footprint: 8 rectangular header pads (1.6 x 6 mm, overhang 1.5 mm), mm units."""
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>')
    s.append('<svg version="1.1" xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="34mm" height="38mm" viewBox="-2 -4 34 38" xml:space="preserve">')
    s.append(' <g id="copper0">')
    s.append('  <g id="copper1">')
    for (cid, _, _), px in zip(BOTTOM_PINS, PIN_X_MM):
        s.append('   <rect id="%spin" x="%.2f" y="%.2f" width="%.2f" height="%.2f" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>' % (cid, px - PAD_W_MM / 2, BOARD_MM + PAD_OVERHANG_MM - PAD_LEN_MM, PAD_W_MM, PAD_LEN_MM))
    for (cid, _, _), px in zip(TOP_PINS, PIN_X_MM):
        s.append('   <rect id="%spin" x="%.2f" y="%.2f" width="%.2f" height="%.2f" style="fill:#f7bf13;fill-opacity:1;stroke:none"/>' % (cid, px - PAD_W_MM / 2, -PAD_OVERHANG_MM, PAD_W_MM, PAD_LEN_MM))
    s.append('  </g>')
    s.append(' </g>')
    s.append(' <g id="silkscreen">')
    # Board outline. The top/bottom edges are left OPEN where the header pads
    # cross the board edge, so silkscreen NEVER overlaps a pad (a silkscreen
    # line on a pad would block soldering / cause poor contact).
    OPEN_L = min(PIN_X_MM) - PAD_W_MM / 2 - 0.3
    OPEN_R = max(PIN_X_MM) + PAD_W_MM / 2 + 0.3
    s.append('  <line x1="0" y1="0" x2="0" y2="%.0f" stroke="#000000" stroke-width="0.2"/>' % BOARD_MM)
    s.append('  <line x1="%.0f" y1="0" x2="%.0f" y2="%.0f" stroke="#000000" stroke-width="0.2"/>' % (BOARD_MM, BOARD_MM, BOARD_MM))
    s.append('  <line x1="0" y1="0" x2="%.2f" y2="0" stroke="#000000" stroke-width="0.2"/>' % OPEN_L)
    s.append('  <line x1="%.2f" y1="0" x2="%.0f" y2="0" stroke="#000000" stroke-width="0.2"/>' % (OPEN_R, BOARD_MM))
    s.append('  <line x1="0" y1="%.0f" x2="%.2f" y2="%.0f" stroke="#000000" stroke-width="0.2"/>' % (BOARD_MM, OPEN_L, BOARD_MM))
    s.append('  <line x1="%.2f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#000000" stroke-width="0.2"/>' % (OPEN_R, BOARD_MM, BOARD_MM, BOARD_MM))
    for mx, my in MOUNT_HOLES_MM:
        s.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="#000000" stroke-width="0.2"/>' % (mx, my, MOUNT_R_MM))
    # pin-1 index dot (connector0 = bottom header pin 1), clear of the pads
    s.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="#000000" stroke="none"/>' % (PIN_X_MM[0], BOARD_MM - 6.0, 0.9))
    # DIN/DOUT data-flow triangles OUTSIDE the board, clear of the pads:
    #   DIN (bottom): tip points up INTO the board (data enters the chip)
    #   DOUT (top):   tip points up AWAY from the board (data exits the chip)
    s.append('  <polygon points="%.2f,%.2f %.2f,%.2f %.2f,%.2f" fill="#000000" stroke="none"/>' % (
        PIN_X_MM[2], BOARD_MM + 1.9, PIN_X_MM[2] - 1.0, BOARD_MM + 3.7, PIN_X_MM[2] + 1.0, BOARD_MM + 3.7))
    s.append('  <polygon points="%.2f,%.2f %.2f,%.2f %.2f,%.2f" fill="#000000" stroke="none"/>' % (
        PIN_X_MM[2], -3.5, PIN_X_MM[2] - 1.0, -1.9, PIN_X_MM[2] + 1.0, -1.9))
    s.append(' </g>')
    s.append('</svg>')
    return "\n".join(s)


def icon_svg():
    """Icon = cropped breadboard board (no housings/pins), scaled into the 32x32 icon box."""
    art = extract_led_artwork()
    s = []
    s.append('<?xml version="1.0" encoding="utf-8"?>')
    s.append('<svg version="1.1" xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="32px" height="32px" viewBox="0 0 32 32" xml:space="preserve">')
    s.append(' <g id="icon">')
    s.append('  <g transform="scale(%.4f)">' % (32.0 / BOARD))
    emit_board_content(s, art)
    s.append('  </g>')
    s.append(' </g>')
    s.append('</svg>')
    return "\n".join(s)


def fzp_xml():
    conn_blocks = []
    for cid, name, desc in CONN:
        conn_blocks.append(
            '  <connector id="%s" name="%s" type="male">\n'
            '   <description>%s</description>\n'
            '   <views>\n'
            '    <breadboardView><p layer="breadboard" svgId="%spin"/></breadboardView>\n'
            '    <schematicView><p layer="schematic" svgId="%spin" terminalId="%sterminal"/></schematicView>\n'
            '    <pcbView>\n'
            '     <p layer="copper0" svgId="%spin"/>\n'
            '     <p layer="copper1" svgId="%spin"/>\n'
            '    </pcbView>\n'
            '   </views>\n'
            '  </connector>' % (cid, name, desc, cid, cid, cid, cid, cid)
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <label>LED</label>\n'
        ' <date>2026-08-28</date>\n'
        ' <tags><tag>LED</tag><tag>RGB</tag><tag>addressable</tag><tag>WS2812B</tag><tag>matrix</tag><tag>4x4</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">LED</property>\n'
        '  <property name="type">LED</property>\n'
        '  <property name="package">%s</property>\n'
        '  <property name="part number">%s</property>\n'
        ' </properties>\n'
        ' <description>4x4 WS2812B-5050 RGB matrix module, black board ~30x30mm, LEDs spread evenly (pitch 7.5mm), 12 bypass caps, 4 mount holes. 8 pins: bottom GND/VCC/DIN/GND, top GND/VCC/DOUT/GND (2.54mm). LED scan order: each column climbs bottom->top from bottom-right (grid top->bottom 16 12 8 4 / 15 11 7 3 / 14 10 6 2 / 13 9 5 1) - verified against the real module.</description>\n'
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
        '    <layer layerId="copper0"/>\n'
        '    <layer layerId="copper1"/>\n'
        '   </layers>\n'
        '  </pcbView>\n'
        ' </views>\n'
        ' <connectors>\n'
        + "\n".join(conn_blocks) + "\n"
        ' </connectors>\n'
        '</module>\n'
    ) % (PART_ID, TITLE, PKG, PART_NUMBER, ICON_REF, BB_REF, SCHEM_REF, PCB_REF)


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
