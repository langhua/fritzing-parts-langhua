# -*- coding: utf-8 -*-
"""Generate Archimedean-spiral PCB coils as filled SVG ribbons.

Outputs:
  1. A single-coil PCB artwork SVG (black filled spiral + pads),
     suitable for Fritzing "Import SVG -> Set as Copper1".
  2. A 4x4 array SVG (16 coils tiled at 20 mm pitch) for direct
     top-copper import on the 80x80 mm subboard.

Files are written next to this script, so the folder is self-contained
and can be copied/moved as a unit.

The spiral is generated as a filled ribbon (centerline offset by +/-
half trace width along the curve normal), which is the SVG equivalent
of Inkscape's "Stroke to Path" and is the form Fritzing reliably treats
as copper.

Parameters (from schematic spec):
    outer diameter = 20 mm  (outer radius 10 mm)  [single-coil reference]
    inner diameter =  8 mm  (inner radius  4 mm)
    turns          = 6
    trace width    = 0.2 mm
    pad diameter   = 1.0 mm (radius 0.5 mm)

Array coils use OD 19 mm (ARRAY_OUTER_R = 9.5) for isolation at 20 mm pitch.
"""

import math
import os

# ---- coil geometry ----
OUTER_R = 10.0      # mm (single-coil part reference)
INNER_R = 4.0       # mm
TURNS = 6
TRACE_W = 0.2       # mm
PAD_R = 0.5         # mm
# ---- array geometry ----
COLS = 4
ROWS = 4
PITCH = 20.0        # mm center-to-center
BOARD_W = 80.0      # mm
BOARD_H = 80.0      # mm
# Array coils must be smaller than pitch so adjacent coils do NOT touch.
# OD 19 mm at 20 mm pitch leaves 1.0 mm gap between coils (0.5 mm/side)
# and 0.5 mm from the 80 mm board edge. OD 20 would short adjacent coils.
ARRAY_OUTER_R = 9.5  # mm (OD 19) for the 4x4 array
# ---- sampling ----
POINTS_PER_TURN = 120

# Output files land next to this script.
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SINGLE_NAME = "svg.pcb.NFC_Coil_20mm_6T_0p2_pcb.svg"
ARRAY_NAME = "coil_4x4_array.svg"


def spiral_centerline(outer_r=OUTER_R):
    """Yield (x, y) on the spiral centerline, theta from 0 to 2*pi*TURNS."""
    a = (outer_r - INNER_R) / (2.0 * math.pi * TURNS)  # mm per radian
    n = int(TURNS * POINTS_PER_TURN)
    pts = []
    for i in range(n + 1):
        theta = 2.0 * math.pi * TURNS * i / n
        r = INNER_R + a * theta
        pts.append((r * math.cos(theta), r * math.sin(theta)))
    return pts


def ribbon_path(outer_r=OUTER_R):
    """Return SVG path 'd' for the filled spiral ribbon + pads."""
    pts = spiral_centerline(outer_r)
    half = TRACE_W / 2.0
    left = []
    right = []
    for i, (x, y) in enumerate(pts):
        # tangent direction
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == len(pts) - 1:
            dx, dy = x - pts[-2][0], y - pts[-2][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(dx, dy)
        tx, ty = dx / L, dy / L
        # normal (rotate tangent by -90 deg -> points "left" of travel)
        nx, ny = -ty, tx
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))

    d = ["M %.3f %.3f" % left[0]]
    d += ["L %.3f %.3f" % p for p in left[1:]]
    d += ["L %.3f %.3f" % p for p in reversed(right)]
    d.append("Z")
    return " ".join(d), pts


def single_coil_svg():
    d, pts = ribbon_path(OUTER_R)
    cx, cy = (0.0, 0.0)
    # inner-end pad and outer-end pad: place on the centerline ends
    p_in = pts[0]
    p_out = pts[-1]
    size = OUTER_R * 2 + 4  # small margin
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="%dmm" height="%dmm" viewBox="%d %d %d %d">\n'
        % (size, size, -size / 2, -size / 2, size, size)
    )
    s += '  <path d="%s" fill="#000000" stroke="none"/>\n' % d
    s += '  <circle cx="%.3f" cy="%.3f" r="%f" fill="#000000"/>\n' % (p_in[0], p_in[1], PAD_R)
    s += '  <circle cx="%.3f" cy="%.3f" r="%f" fill="#000000"/>\n' % (p_out[0], p_out[1], PAD_R)
    s += "</svg>\n"
    return s


def array_svg():
    """Tile a single coil over an 80x80 mm board, 4x4 at 20 mm pitch.

    Uses ARRAY_OUTER_R (OD 19 mm) so adjacent coils keep isolation.
    """
    # coil generated centered at origin; array origin at top-left (10,10)
    d, pts = ribbon_path(ARRAY_OUTER_R)
    s = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="%dmm" height="%dmm" viewBox="0 0 %d %d">\n'
        % (BOARD_W, BOARD_H, BOARD_W, BOARD_H)
    )
    s += '  <rect x="0" y="0" width="%d" height="%d" fill="none" stroke="none"/>\n' % (BOARD_W, BOARD_H)
    p_in = pts[0]
    p_out = pts[-1]
    for row in range(ROWS):
        for col in range(COLS):
            cx = 10 + col * PITCH
            cy = 10 + row * PITCH
            s += '  <g transform="translate(%.3f %.3f)">\n' % (cx, cy)
            s += '    <path d="%s" fill="#000000" stroke="none"/>\n' % d
            s += '    <circle cx="%.3f" cy="%.3f" r="%f" fill="#000000"/>\n' % (p_in[0], p_in[1], PAD_R)
            s += '    <circle cx="%.3f" cy="%.3f" r="%f" fill="#000000"/>\n' % (p_out[0], p_out[1], PAD_R)
            s += "  </g>\n"
    s += "</svg>\n"
    return s


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    single = os.path.join(OUT_DIR, SINGLE_NAME)
    arr = os.path.join(OUT_DIR, ARRAY_NAME)
    with open(single, "w", encoding="utf-8") as f:
        f.write(single_coil_svg())
    with open(arr, "w", encoding="utf-8") as f:
        f.write(array_svg())
    print("Wrote:")
    print("  ", single)
    print("  ", arr)


if __name__ == "__main__":
    main()
