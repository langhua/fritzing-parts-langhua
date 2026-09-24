# -*- coding: utf-8 -*-
"""Generate a Fritzing part for the WCH CH32V002F4U6 -- QFN20, 3 x 3 mm, 0.4 mm pitch.

Datasheet: D:\\Downloads\\CH32V002DS0.PDF (V1.7), pin table 2-1 (QFN20 column),
           package table ch.4 ("QFN20 3*3mm 0.4mm 15.7mil")
           CH32V003DS0.PDF (V1.8) has the SAME QFN20 pin numbering -- so the
           CH32V003F4U6 part reuses this generator (see ../CH32V003F4U6).

!! The exposed pad (datasheet "pin 0") IS VSS:  QFN20 has pin 4 = VSS *and* the
   pad = VSS (tied together with a <bus>); on the QFN12 (CH32V002D4U6) VSS
   exists ONLY as the exposed pad.

Pin numbering is counterclockwise, pin 1 = top-left, going DOWN the left side.
Per side: pins 1-5 left (top->bottom), 6-10 bottom (left->right),
          11-15 right (bottom->top), 16-20 top (right->left).

Views
  icon       : QFN top view -- body 3 x 3 mm, 4 x 5 edge pads (0.2 x 0.6 mm,
               0.4 mm pitch), pin-1 dot, top mark.  8 units/mm.
  breadboard : ATECC608B style green breakout board (2 columns x 10 pins on the
               2.54 mm hole grid, chip 1:1 in the middle, pin numbers
               HORIZONTAL and OUTSIDE the pads) -- same conventions the user
               approved for CH32V002J4M6.
  schematic  : FOUR-SIDED symbol (QFN = 4-row package, per the repo rule):
               5 pins/side, corners kept blank (CORNER = (max_name+1)*int(FN*0.58)),
               pin numbers above the side pins / rotated 270 for top+bottom,
               names inside, all one font size.
  pcb        : QFN20 land -- 20 pads 0.20 x 0.60 mm at 0.4 mm pitch on the four
               sides (pad centre at body/2 + 0.25) + 1.65 x 1.65 mm exposed pad,
               plain <rect> only (NO rx/ry), body outline + pin-1 dot on silk.

This module is CONFIG-DRIVEN (module globals are read when the emitters run), so
the CH32V003F4U6 / CH32V002D4U6 scripts import it, override the globals and call
main() again -- see those folders.
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FZPZ_DIR = os.path.normpath(os.path.join(OUT_DIR, "..", "..", "fzpz"))

# ---------------------------------------------------------------- part identity
PART_ID = "CH32V002F4U6"
TITLE = "CH32V002F4U6"
CHIP = "CH32V002"
SCHEM_NAME = "CH32V002"
TOP_MARK = "V002"
TAGS = "<tag>IC</tag><tag>MCU</tag><tag>RISC-V</tag><tag>CH32V002</tag>"
DESC = ("WCH CH32V002F4U6 RISC-V MCU, QFN20 3x3 mm / 0.4 mm pitch, 2.5-5 V, "
        "12-bit ADC (8 channels), 18 I/O. Pin compatible with CH32V003F4U6 "
        "(10-bit ADC + OPA). The exposed pad is VSS and is tied to pin 4.")

# ---------------------------------------------------------------- package config
BODY_MM = 3.0            # square body edge
PITCH_MM = 0.4           # pin pitch
PER_SIDE = 5             # pins per side  (4 x 5 = 20)
PAD_W_MM = 0.20          # pad width  (along the edge)
PAD_L_MM = 0.60          # pad length (radially)
PAD_R_MM = BODY_MM / 2.0 + 0.25     # pad centre distance from the centre = 1.75
EPAD_MM = 1.65           # exposed pad, square
ICON_S = 7.0             # icon units per mm  (3 mm body + pads -> 28.7 units of 32)
# 1-pin dot: centred on pin 1's pad row, just inside the body's left edge.
# Kept in view units so every package looks the same (2026-09-24 user's spec).
ICON_DOT_R = 1.0         # icon: dot radius
ICON_DOT_INSET = 2.10    # icon: dot centre, distance from the body's left edge
BB_DOT_R = 5.0           # breadboard: dot radius
BB_DOT_INSET = 10.0      # breadboard: dot centre from the body's left edge
GND_PINS = [4]           # die pins that are VSS (tied to the exposed pad by a bus)
PAD_NAME = "VSS"

PIN_NAMES = ["PD7", "PA1", "PA2", "VSS", "PD0", "VDD", "PC0", "PC1", "PC2", "PC3",
             "PC4", "PC5", "PC6", "PC7", "PD1", "PD2", "PD3", "PD4", "PD5", "PD6"]
PIN_DESC = {
    "VSS": "ground", "VDD": "supply 2.5 / 3.3 / 5 V",
    "PA1": "PA1 (ADC_IN1)", "PA2": "PA2 (ADC_IN0)", "PC4": "PC4 (ADC_IN2)",
    "PD1": "PD1 (SWIO debug)", "PD2": "PD2 (ADC_IN3)", "PD3": "PD3 (ADC_IN4)",
    "PD4": "PD4 (ADC_IN7)", "PD5": "PD5 (ADC_IN5)", "PD6": "PD6 (ADC_IN6)",
}

# breadboard geometry (1 unit = 1 mil; pins on multiples of 100 = 2.54 mm)
BB_PIN_X = (100.0, 400.0)
BB_PITCH = 100.0
BB_PAD_R, BB_HOLE_R = 39.4, 19.1
# PCB silkscreen (2026-09-24 user's spec, all CH32V00x packages):
#   PCB_SILK_CORNERS  - only four corner brackets, so no silk line runs across a pad
#   PCB_DOT_ABOVE_PAD - pin-1 dot sits just above pin 1's pad, left-aligned with it
PCB_SILK_CORNERS = True
PCB_DOT_ABOVE_PAD = True
PCB_SILK_ARM = 0.22        # corner-bracket arm length (mm)
PCB_DOT_R = 0.22           # pin-1 dot radius (mm)
PCB_DOT_CLEAR = 0.08       # gap between the dot and pin 1's pad (mm)
# schematic symbol options (2026-09-24 user's spec, all CH32V00x packages):
#   PAD_PIN_TOP_LEFT  - the exposed pad (pin 0) is drawn on the TOP edge, one
#                       pitch left of the top side's last pin
#   SCHEM_NUM_LEFT    - top/bottom pin numbers go on the LEFT of the pin line
#   SCHEM_NAME_CENTER - top/bottom pin names are centred across the pin line
PAD_PIN_TOP_LEFT = True
SCHEM_NUM_LEFT = True
SCHEM_NAME_CENTER = True


def pad_counts():
    return 4 * PER_SIDE, len(PIN_NAMES)


def pin_name(i):
    """i = 1-based package pin number."""
    return PIN_NAMES[i - 1]


def pad_xy_mm(i):
    """Pad centre of pin i in mm (PCB view), SVG coords (y down), CCW from pin 1."""
    idx = i - 1
    side, k = idx // PER_SIDE, idx % PER_SIDE
    off = [(k2 - (PER_SIDE - 1) / 2.0) * PITCH_MM for k2 in range(PER_SIDE)]
    c = PAD_R_MM
    if side == 0:                       # left, top -> bottom
        return (-c, off[k])
    if side == 1:                       # bottom, left -> right
        return (off[k], c)
    if side == 2:                       # right, bottom -> top
        return (c, off[PER_SIDE - 1 - k])
    return (off[PER_SIDE - 1 - k], -c)  # top, right -> left


def pad_rect_mm(i):
    """(x, y, w, h) of pad i in mm -- radial 0.60, tangential 0.20."""
    idx = i - 1
    cx, cy = pad_xy_mm(i)
    if (idx // PER_SIDE) % 2 == 0:      # left / right -> long axis is X
        return (cx - PAD_L_MM / 2.0, cy - PAD_W_MM / 2.0, PAD_L_MM, PAD_W_MM)
    return (cx - PAD_W_MM / 2.0, cy - PAD_L_MM / 2.0, PAD_W_MM, PAD_L_MM)


# ---------------------------------------------------------------------- icon
def icon_svg():
    """QFN top view: body, 4 x PER_SIDE edge pads, pin-1 dot, top mark."""
    S = ICON_S
    half = BODY_MM / 2.0 * S                       # 12 units for 3 mm at 8/mm
    bx, by = 16 - half, 16 - half
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n')
    L.append(' <g id="icon">\n')
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="0.3" ry="0.3" '
             'fill="#303030" stroke="none"/>\n' % (bx, by, 2 * half, 2 * half))
    w = PAD_W_MM * S                       # 0.2 mm wide
    pl = 0.55 * S                          # visual pad length (straddles the body edge)
    for i in range(1, len(PIN_NAMES) + 1):
        cx, cy = pad_xy_mm(i)
        cx, cy = 16 + cx * S, 16 + cy * S
        if ((i - 1) // PER_SIDE) % 2 == 0:         # left / right
            L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>\n'
                     % (cx - pl / 2, cy - w / 2, pl, w))
        else:                                      # top / bottom
            L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>\n'
                     % (cx - w / 2, cy - pl / 2, w, pl))
    p1 = pad_xy_mm(1)
    L.append('  <circle cx="%.2f" cy="%.2f" r="%.1f" fill="#c0c0c0" stroke="none"/>\n'
             % (bx + ICON_DOT_INSET, 16 + p1[1] * S, ICON_DOT_R))
    L.append('  <text x="16" y="16" font-size="3.0" font-family="DroidSans" fill="#c0c0c0" '
             'text-anchor="middle" dominant-baseline="central">%s</text>\n' % TOP_MARK)
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ----------------------------------------------------------------- breadboard
def breadboard_svg():
    """ATECC608B style: green board, two pin columns, chip 1:1 in the middle,
    pin numbers horizontal and OUTSIDE the pads."""
    n = len(PIN_NAMES)
    n_col = (n + 1) // 2                       # 10 for QFN20, 6 for QFN12
    y0, y1 = 100.0, 100.0 + (n_col - 1) * BB_PITCH
    bh = y1 + 100.0
    cy = (y0 + y1) / 2.0
    S = 100.0 / 2.54                           # units per mm (39.37)
    half = BODY_MM / 2.0 * S
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
             'viewBox="0 0 500 %.0f">\n' % (500 * 0.0254, bh * 0.0254, bh))
    L.append(' <g id="breadboard">\n')
    L.append('  <rect x="0" y="0" width="500" height="%.0f" fill="#00aa44" stroke="#00772f" stroke-width="5"/>\n' % bh)
    # chip body + edge pads (top view, 1:1)
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#303030" stroke="none"/>\n'
             % (250 - half, cy - half, 2 * half, 2 * half))
    pw = PAD_W_MM * S
    for i in range(1, n + 1):
        cx, cyy = pad_xy_mm(i)
        cx, cyy = 250 + cx * S, cy + cyy * S
        if ((i - 1) // PER_SIDE) % 2 == 0:
            L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#c0c0c0" stroke="none"/>\n'
                     % (cx - 0.55 * S / 2, cyy - pw / 2, 0.55 * S, pw))
        else:
            L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#c0c0c0" stroke="none"/>\n'
                     % (cx - pw / 2, cyy - 0.55 * S / 2, pw, 0.55 * S))
    # pin-1 dot inside the body, centred on pin 1's pad row; top mark (horizontal, small)
    p1 = pad_xy_mm(1)
    L.append('  <circle cx="%.2f" cy="%.2f" r="%.1f" fill="#c0c0c0" stroke="none"/>\n'
             % (250 - half + BB_DOT_INSET, cy + p1[1] * S, BB_DOT_R))
    L.append('  <text x="250" y="%.2f" font-size="14" fill="#c0c0c0" text-anchor="middle" '
             'dominant-baseline="central" font-family="DroidSans">%s</text>\n' % (cy, TOP_MARK))
    # pins: left column = 1..n_col top->bottom, right = n..n_col+1 top->bottom
    left = list(range(1, n_col + 1))
    right = list(range(n, n - n_col, -1))
    for col, order in ((0, left), (1, right)):
        x = BB_PIN_X[col]
        for j, pno in enumerate(order):
            y = y0 + j * BB_PITCH
            L.append('  <circle id="connector%dpin" connectorname="%s" cx="%.1f" cy="%.1f" r="%.1f" '
                     'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n'
                     % (pno - 1, pin_name(pno), x, y, BB_PAD_R))
            L.append('  <circle cx="%.1f" cy="%.1f" r="%.1f" fill="#2b2b2b" stroke="none"/>\n'
                     % (x, y, BB_HOLE_R))
            L.append('  <text x="%.1f" y="%.1f" font-size="40" fill="#ffffff" text-anchor="middle" '
                     'dominant-baseline="central" font-family="DroidSans">%d</text>\n'
                     % (35.0 if col == 0 else 465.0, y, pno))
    # exposed pad (pin 0) broken out at the bottom centre
    L.append('  <circle id="connector%dpin" connectorname="%s" cx="250.0" cy="%.1f" r="%.1f" '
             'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n'
             % (n, PAD_NAME, bh - 50.0, BB_PAD_R))
    L.append('  <circle cx="250.0" cy="%.1f" r="%.1f" fill="#2b2b2b" stroke="none"/>\n'
             % (bh - 50.0, BB_HOLE_R))
    L.append('  <text x="250.0" y="%.1f" font-size="40" fill="#ffffff" text-anchor="middle" '
             'dominant-baseline="central" font-family="DroidSans">0</text>\n' % (bh - 130.0))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ------------------------------------------------------------------ schematic
def schematic_svg():
    """Four-sided symbol following the repo precedent
    (svg/CH32V203C8T6/svg.schematic.*): 1000 units = 1 inch, font 35,
    pin pitch 100, stub 130, corners blank (CORNER = (max_name+1)*int(FN*0.58)),
    box = PER_SIDE*pitch + 2*CORNER; numbers outside above the side pins
    (top/bottom ones rotated 270), names inside, one font size."""
    FN, P, STUB = 35, 100, 130
    mx = max(len(x) for x in PIN_NAMES + [PAD_NAME])
    CORNER = (mx + 1) * int(FN * 0.58)
    BOX = PER_SIDE * P + 2 * CORNER
    VB = 60
    n = len(PIN_NAMES)
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.4fin" height="%.4fin" '
             'viewBox="%d %d %d %d">\n'
             % ((BOX + 2 * STUB + 2 * VB) / 1000.0, (BOX + 2 * STUB + 2 * VB) / 1000.0,
                -STUB - VB, -STUB - VB, BOX + 2 * STUB + 2 * VB, BOX + 2 * STUB + 2 * VB))
    L.append(' <g id="schematic">\n')
    L.append('  <rect x="0" y="0" width="%d" height="%d" fill="#FFFFFF" stroke="#000000" stroke-width="5"/>\n'
             % (BOX, BOX))

    def pin(pno, x1, y1, x2, y2):
        cn = pno if pno == 0 else pno          # 0 = exposed pad -> connector n
        cn = n_bus.get(pno, n if pno == 0 else pno - 1)
        nm = PAD_NAME if pno == 0 else pin_name(pno)
        out = ['  <line class="pin" id="connector%dpin" connectorname="%s" x1="%d" y1="%d" x2="%d" y2="%d" '
               'stroke="#000000" stroke-width="5"/>\n' % (cn, nm, x1, y1, x2, y2),
               '  <rect class="terminal" id="connector%dterminal" x="%d" y="%d" width="0.0001" height="0.0001" fill="none"/>\n'
               % (cn, x2, y2)]
        return cn, "".join(out)

    n_bus = {0: n}
    for i in range(1, n + 1):
        n_bus[i] = i - 1

    def num(cn, txt, x, y, rot):
        r = ' transform="rotate(270 %d %d)"' % (x, y) if rot else ''
        return ('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                'font-family="DroidSans"%s>%s</text>\n' % (x, y, FN, r, txt))

    def name(cn, txt, x, y, anchor, rot):
        r = ' transform="rotate(270 %d %d)"' % (x, y) if rot else ''
        return ('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="%s" '
                'font-family="DroidSans"%s>%s</text>\n' % (x, y, FN, anchor, r, txt))

    def off(txt):
        """inward offset for a rotated (top/bottom) label, from the precedent"""
        return 65 + max(0, len(txt) - 4) * int(FN * 0.34)

    # cross-axis offsets of the rotated (top/bottom) number / name texts
    dx_num = -24 if SCHEM_NUM_LEFT else 35          # 脚号：引线左侧，间距同左右脚的 24
    dx_nam = 12 if SCHEM_NAME_CENTER else 35        # 脚名：以引线为中心

    # left: pins 1..PER_SIDE top -> bottom
    for k in range(PER_SIDE):
        pno = 1 + k
        y = CORNER + P // 2 + k * P
        cn, s = pin(pno, 0, y, -STUB, y)
        L.append(s)
        L.append(num(cn, str(pno), -STUB // 2, y - 24, False))
        L.append(name(cn, pin_name(pno), FN, y + 12, "start", False))
    # bottom: next block, left -> right
    for k in range(PER_SIDE):
        pno = 1 + PER_SIDE + k
        x = CORNER + P // 2 + k * P
        cn, s = pin(pno, x, BOX, x, BOX + STUB)
        L.append(s)
        L.append(num(cn, str(pno), x + dx_num, BOX + 55, True))
        L.append(name(cn, pin_name(pno), x + dx_nam, BOX - off(pin_name(pno)), "middle", True))
    # right: next block, bottom -> top
    for k in range(PER_SIDE):
        pno = 1 + 2 * PER_SIDE + k
        y = BOX - (CORNER + P // 2 + k * P)
        cn, s = pin(pno, BOX, y, BOX + STUB, y)
        L.append(s)
        L.append(num(cn, str(pno), BOX + STUB // 2, y - 24, False))
        L.append(name(cn, pin_name(pno), BOX - FN, y + 12, "end", False))
    # top: last block, right -> left
    for k in range(PER_SIDE):
        pno = 1 + 3 * PER_SIDE + k
        x = BOX - (CORNER + P // 2 + k * P)
        cn, s = pin(pno, x, 0, x, -STUB)
        L.append(s)
        L.append(num(cn, str(pno), x + dx_num, -50, True))
        L.append(name(cn, pin_name(pno), x + dx_nam, off(pin_name(pno)), "middle", True))
    # exposed pad (pin 0): top-left (one pitch left of the top side's last pin)
    # or - default - on the bottom side, right of the last pin
    if PAD_PIN_TOP_LEFT:
        px = CORNER + P // 2 - P
        cn, s = pin(0, px, 0, px, -STUB)
        L.append(s)
        L.append(num(cn, "0", px + dx_num, -50, True))
        L.append(name(cn, PAD_NAME, px + dx_nam, off(PAD_NAME), "middle", True))
    else:
        px = BOX - 30
        cn, s = pin(0, px, BOX, px, BOX + STUB)
        L.append(s)
        L.append(num(cn, "0", px + dx_num, BOX + 55, True))
        L.append(name(cn, PAD_NAME, px + dx_nam, BOX - off(PAD_NAME), "middle", True))
    # circuit name in the middle
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans">%s</text>\n' % (BOX // 2, BOX // 2 + 12, FN, SCHEM_NAME))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ----------------------------------------------------------------------- pcb
def pcb_svg():
    """QFN20 land pattern (mm): 20 pads 0.20 x 0.60 at 0.4 mm pitch, exposed pad
    1.65 x 1.65, body outline + pin-1 dot.  Plain <rect> only -- no rx/ry."""
    n = len(PIN_NAMES)
    lim = PAD_R_MM + PAD_L_MM / 2.0 + 0.55      # 2.60
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
    L.append('<!-- %s -->\n' % TITLE)
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
             'viewBox="%.2f %.2f %.2f %.2f">\n' % (2 * lim, 2 * lim, -lim, -lim, 2 * lim, 2 * lim))
    L.append('  <g id="copper1">\n')
    for i in range(1, n + 1):
        x, y, w, h = pad_rect_mm(i)
        L.append('<rect id="connector%dpad" x="%.3f" y="%.3f" width="%.3f" height="%.3f" '
                 'fill="#F7BD13" stroke="none" connectorname="%s"/>\n'
                 % (i - 1, x, y, w, h, pin_name(i)))
    L.append('<rect id="connector%dpad" x="%.3f" y="%.3f" width="%.3f" height="%.3f" '
             'fill="#F7BD13" stroke="none" connectorname="%s"/>\n'
             % (n, -EPAD_MM / 2.0, -EPAD_MM / 2.0, EPAD_MM, EPAD_MM, PAD_NAME))
    L.append('<g id="copper0"/>\n')
    L.append('  </g>\n')
    L.append('  <g id="silkscreen">\n')
    b = BODY_MM / 2.0
    if PCB_SILK_CORNERS:
        # four corner brackets only: every arm stops short of the pads, so no
        # silkscreen line crosses a pad (pads start at PAD_R_MM - PAD_L_MM/2)
        a = PCB_SILK_ARM
        for sx in (-1, 1):
            for sy in (-1, 1):
                L.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#f0f0f0" '
                         'stroke-width="0.12"/>\n' % (sx * b, sy * b, sx * b, sy * (b - a)))
                L.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#f0f0f0" '
                         'stroke-width="0.12"/>\n' % (sx * b, sy * b, sx * (b - a), sy * b))
    else:
        L.append('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="none" '
                 'stroke="#f0f0f0" stroke-width="0.12"/>\n' % (-b, -b, BODY_MM, BODY_MM))
    if PCB_DOT_ABOVE_PAD:
        px, py = pad_rect_mm(1)[0], pad_rect_mm(1)[1]
        L.append('<circle cx="%.3f" cy="%.3f" r="%.2f" fill="#f0f0f0" stroke="none"/>\n'
                 % (px + PCB_DOT_R, py - PCB_DOT_CLEAR - PCB_DOT_R, PCB_DOT_R))
    else:
        L.append('<circle cx="%.3f" cy="%.3f" r="%.2f" fill="#f0f0f0" stroke="none"/>\n'
                 % (pad_xy_mm(1)[0], pad_xy_mm(1)[1], PCB_DOT_R))
    L.append('  </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# ----------------------------------------------------------------------- fzp
def fzp_xml():
    n = len(PIN_NAMES)
    conns = []
    for i in range(1, n + 1):
        cn, name = i - 1, pin_name(i)
        conns.append(
            '  <connector id="connector%d" name="%s" type="male">\n'
            '   <description>pin %d - %s</description>\n'
            '   <views>\n'
            '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n'
            '    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n'
            '    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n'
            '   </views>\n'
            '  </connector>\n' % (cn, name, i, PIN_DESC.get(name, name + " digital I/O"), cn, cn, cn, cn))
    conns.append(
        '  <connector id="connector%d" name="%s" type="male">\n'
        '   <description>exposed pad (datasheet pin 0) - %s, connect to GND</description>\n'
        '   <views>\n'
        '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n'
        '    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n'
        '    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n'
        '   </views>\n'
        '  </connector>\n' % (n, PAD_NAME, PAD_NAME, n, n, n, n))
    bus = ""
    if GND_PINS:
        members = "".join('   <nodeMember connectorId="connector%d"/>\n' % (p - 1) for p in GND_PINS)
        members += '   <nodeMember connectorId="connector%d"/>\n' % n
        bus = ' <buses>\n  <bus id="%s">\n%s  </bus>\n </buses>\n' % (PAD_NAME, members)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <label>U</label>\n'
        ' <date>2026-09-24</date>\n'
        ' <tags>%s</tags>\n'
        ' <properties>\n'
        '  <property name="family">WCH RISC-V MCU</property>\n'
        '  <property name="chip">%s</property>\n'
        '  <property name="pins">%d</property>\n'
        '  <property name="part number">%s</property>\n'
        '  <property name="package">QFN%d</property>\n'
        ' </properties>\n'
        ' <description>%s</description>\n'
        ' <views>\n'
        '  <iconView><layers image="icon/%s_icon.svg"><layer layerId="icon"/></layers></iconView>\n'
        '  <breadboardView fliphorizontal="true" flipvertical="true"><layers image="breadboard/%s_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true"><layers image="schematic/%s_schematic.svg"><layer layerId="schematic"/></layers></schematicView>\n'
        '  <pcbView><layers image="pcb/%s_pcb.svg"><layer layerId="silkscreen"/><layer layerId="copper1"/></layers></pcbView>\n'
        ' </views>\n'
        '%s <connectors>\n%s</connectors>\n'
        '</module>\n'
    ) % (PART_ID, TITLE, TAGS, CHIP, len(PIN_NAMES), PART_ID, 4 * PER_SIDE, DESC,
         PART_ID, PART_ID, PART_ID, PART_ID, bus, "".join(conns))


def main():
    names = {
        "icon": "svg.icon.%s_icon.svg" % PART_ID,
        "breadboard": "svg.breadboard.%s_breadboard.svg" % PART_ID,
        "schematic": "svg.schematic.%s_schematic.svg" % PART_ID,
        "pcb": "svg.pcb.%s_pcb.svg" % PART_ID,
        "fzp": "part.%s.fzp" % PART_ID,
    }
    files = {
        names["icon"]: icon_svg(),
        names["breadboard"]: breadboard_svg(),
        names["schematic"]: schematic_svg(),
        names["pcb"]: pcb_svg(),
        names["fzp"]: fzp_xml(),
    }
    for fn, text in files.items():
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %-46s %6d bytes" % (fn, len(text.encode("utf-8"))))
    os.makedirs(FZPZ_DIR, exist_ok=True)
    dst = os.path.join(FZPZ_DIR, PART_ID + ".fzpz")
    order = [names["fzp"], names["icon"], names["breadboard"], names["schematic"], names["pcb"]]
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in order:                       # flat zip, subdir refs live in the fzp
            z.write(os.path.join(OUT_DIR, fn), fn)
    print("wrote %s  (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    main()
