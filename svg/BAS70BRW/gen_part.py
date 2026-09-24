# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for the BAS70 Schottky barrier diode arrays
in SOT-363 (SC-70-6): BAS70BRW and BAS70DW-04.

Both parts are 4 Schottky diodes wired as TWO SERIES PAIRS with all six nodes
brought out (no internal ties), i.e. D1.A - D1.K/D2.A - D2.K and the same for
D3/D4.  The node names are the datasheet's own: A1 / AC1 / C1 (pair 1) and
A2 / AC2 / C2 (pair 2); only the pin numbers attached to the nodes differ:

    pin    BAS70BRW            BAS70DW-04
    1      A1  (anode D1)      A1  (anode D1)
    2      A2  (anode D3)      C1  (cathode D2)
    3      AC2 (mid D3/D4)     AC2 (mid D3/D4)
    4      C2  (cathode D4)    A2  (anode D3)
    5      C1  (cathode D2)    C2  (cathode D4)
    6      AC1 (mid D1/D2)     AC1 (mid D1/D2)

Pin geometry (SOT-363, top view, same orientation as the datasheet figure):
pins 1,2,3 along the lower row (left -> right), pins 4,5,6 along the upper row
(right -> left), pin pitch 0.65 mm, pad rows 1.90 mm apart.

Package / suggested pad layout from the Diodes datasheet (DS30158) table:
    C = 0.650 (pitch)   X = 0.420 (pad width)   Y = 0.600 (pad length)
    G = 1.300 (gap between the pad rows)  ->  Y1 = 2.500 = 0.6 + 1.3 + 0.6
    body 2.00 x 1.25 mm

Views (BAT54S / CH32V00x style):
  - icon  : SOT-363 top view 1:1-ish (5.33 units/mm, same as BAT54S), pin-1 dot
  - breadb.: green adapter board, 2.54 mm header grid, chip 1:1 in the middle
  - schem. : the two series pairs drawn as real Schottky chains, node names inside
  - pcb   : 6 pads 0.42 x 0.60 on a 0.65 mm grid, body silk + pin-1 dot
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

PART_ID = "BAS70BRW_SOT363_1"
TITLE = "BAS70BRW"
FZPZ = "BAS70BRW.fzpz"
TAGS = "<tag>diode</tag><tag>Schottky</tag><tag>array</tag><tag>SOT-363</tag><tag>BAS70</tag>"
DESC = ("Diodes BAS70BRW-7-F: 4 x 70 V Schottky diodes in SOT-363 (SC-70-6), wired as two "
        "series pairs with all six nodes available (A1/AC1/C1 and A2/AC2/C2). "
        "Suitable as a 4-diode bridge for low-current envelope detection.")

# ---- pin -> node name (index 0 = pin 1) --------------------------------------
NODE_OF_PIN = ["A1", "A2", "AC2", "C2", "C1", "AC1"]

# node -> (human description, which pair it belongs to)
NODE_DESC = {
    "A1": "anode of D1 (pair 1)",
    "AC1": "junction D1.K / D2.A, pair 1 - bridge AC input",
    "C1": "cathode of D2 (pair 1)",
    "A2": "anode of D3 (pair 2)",
    "AC2": "junction D3.K / D4.A, pair 2 - bridge AC input",
    "C2": "cathode of D4 (pair 2)",
}
CHAIN_A = ("A1", "AC1", "C1")
CHAIN_B = ("A2", "AC2", "C2")

# ---- SOT-363 geometry (mm) ---------------------------------------------------
PITCH = 0.65          # lead pitch
ROW = 1.90            # pad row centre to centre  (= Y1 2.50 - pad length 0.60)
PAD_W = 0.42          # pad, along the row
PAD_H = 0.60          # pad, radial
BODY_L = 2.00         # body, along the row
BODY_W = 1.25         # body, across the rows

ICON_MM = 5.33        # icon units per mm (same scale as the repo's BAT54S icon)
ICON_DOT_R = 0.8      # icon pin-1 dot radius
ICON_MARK = "K75"     # icon: top mark / silkscreen marking code of the real part
BB_PAD_R, BB_HOLE_R = 39.4, 19.1      # breadboard header pad / hole (1 unit = 1 mil)


def pad_xy_mm(i):
    """Pad centre of pin i (1..6) in mm, SVG coords (y down), package centred."""
    if i <= 3:                       # lower row, left -> right
        return ((i - 2) * PITCH, +ROW / 2.0)
    return ((5 - i) * PITCH, -ROW / 2.0)   # upper row, right -> left


def pad_rect_1():
    """(x, y, w, h) of pin 1's pad in mm -- used for the pin-1 marker."""
    cx, cy = pad_xy_mm(1)
    return (cx - PAD_W / 2.0, cy - PAD_H / 2.0, PAD_W, PAD_H)


def node(i):
    return NODE_OF_PIN[i - 1]


# ------------------------------------------------------------------ pcb view --
def pcb_svg():
    margin_x = BODY_L / 2.0 + 0.30
    margin_y = ROW / 2.0 + PAD_H / 2.0 + 0.20
    hw, hh = PAD_W / 2.0, PAD_H / 2.0
    sx = BODY_L / 2.0 - 0.05          # silk: just inside the body, clear of pads
    sy = BODY_W / 2.0 - 0.07
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="%.2f %.2f %.2f %.2f">\n'
         % (2 * margin_x, 2 * margin_y, -margin_x, -margin_y, 2 * margin_x, 2 * margin_y),
         ' <g id="copper1">\n']
    for i in range(1, 7):
        cx, cy = pad_xy_mm(i)
        L.append('  <rect x="%.3f" y="%.3f" width="%.2f" height="%.2f" id="connector%dpin" '
                 'style="fill:#f7bf13;fill-opacity:1;stroke:none"/>\n'
                 % (cx - hw, cy - hh, PAD_W, PAD_H, i - 1))
    L.append(' </g>\n <g id="silkscreen">\n')
    L.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
             % (-sx, -sy, -sx, sy))
    L.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
             % (sx, -sy, sx, sy))
    L.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
             % (-sx, -sy, sx, -sy))
    L.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" stroke-width="0.06"/>\n'
             % (-sx, sy, sx, sy))
    # pin-1 dot: left of pin 1's pad, bottom edge flush with the pad's bottom edge
    x0, y0, w0, h0 = pad_rect_1()
    r = 0.10
    L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f" fill="#FFFFFF" stroke="none"/>\n'
             % (x0 - 0.10 - r, y0 + h0 - r, r))
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ----------------------------------------------------------------- icon view --
def icon_svg():
    S = ICON_MM
    hb_l, hb_w = BODY_L / 2.0 * S, BODY_W / 2.0 * S
    hw, hh = PAD_W / 2.0 * S, PAD_H / 2.0 * S
    L = ['<?xml version="1.0" encoding="UTF-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n',
         '  <g id="breadboard">\n',
         '    <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="0.8" ry="0.8" '
         'fill="#303030" stroke="none"/>\n' % (16 - hb_l, 16 - hb_w, 2 * hb_l, 2 * hb_w)]
    for i in range(1, 7):
        cx, cy = pad_xy_mm(i)
        cx, cy = 16 + cx * S, 16 + cy * S
        L.append('    <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#8d8c8c" stroke="none"/>\n'
                 % (cx - hw, cy - hh, 2 * hw, 2 * hh))
    # pin-1 dot (inside the body, on the pin-1 end)
    L.append('    <circle cx="%.2f" cy="%.2f" r="%.1f" fill="#c0c0c0" stroke="none"/>\n'
             % (16 - 0.70 * S, 16 + 0.40 * S, ICON_DOT_R))
    L.append('    <text x="%.2f" y="%.2f" font-family="DroidSans" font-size="3.4" fill="#c0c0c0" '
             'text-anchor="middle" dominant-baseline="central">%s</text>\n'
             % (16 + 0.15 * S, 16, ICON_MARK))
    L.append('  </g>\n</svg>\n')
    return "".join(L)


# ------------------------------------------------------------- schematic view --
def _diode(x0, y):
    """Plain diode pointing right: triangle (base at x0) + cathode bar at x0+5.04."""
    w, h = 5.04, 2.88
    xb = x0 + w
    L = []
    for x1, y1, x2, y2 in ((x0, y - h, xb, y), (x0, y + h, xb, y), (x0, y - h, x0, y + h),
                           (xb, y - h, xb, y + h)):
        L.append('    <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
                 'x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>\n' % (x1, y1, x2, y2))
    return "".join(L)


def schematic_svg():
    """Two series chains: A1-D1-AC1-D2-C1 (upper), A2-D3-AC2-D4-C2 (lower).

    The A node sits on the body's left edge and the C node on the right edge, so
    the pin stubs never cross the outline; the AC node leaves through a gap in
    the top (upper chain) / bottom (lower chain) edge - same idea as BAT54S.
    """
    pin = {}                                     # node -> pin number
    for i in range(1, 7):
        pin[node(i)] = i
    xl, xr, xm = 5.0, 61.0, 33.0                 # body edges and AC node
    tx = 62.5                                    # pin-number text x (right side)
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" '
         'width="66px" height="38px" viewBox="0 0 66 38" xml:space="preserve">\n',
         ' <g id="schematic">\n',
         # body outline: two polylines with gaps where the AC stubs leave
         # closed black frame (the AC pin stubs cross it: grey outside, black inside)
         '  <rect x="5" y="3" width="56" height="32" fill="none" stroke="#000000" '
         'stroke-width="0.9"/>\n']
    for y, chain in ((12.0, CHAIN_A), (26.0, CHAIN_B)):
        a, ac, c = chain
        # chain: A(edge) - D1 - AC(junction) - D2 - C(edge); the middle diode sits
        # well right of the AC junction so the junction stays clear
        xd2 = 41.0
        L.append('    <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
                 'x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>\n' % (xl, y, 9.0, y))
        L.append(_diode(9.0, y))
        L.append('    <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
                 'x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>\n' % (14.04, y, xd2, y))
        L.append('    <circle cx="%.2f" cy="%.2f" r="0.7" fill="#000000" stroke="none"/>\n'
                 % (xm, y))
        L.append(_diode(xd2, y))
        L.append('    <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
                 'x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>\n' % (xd2 + 5.04, y, xr, y))
        # AC pin: BLACK inside the frame, GREY outside it
        yed = 3.0 if chain is CHAIN_A else 35.0
        yl = 0.0 if chain is CHAIN_A else 38.0
        L.append('    <line fill="none" stroke="#000000" stroke-width="0.5" stroke-linecap="round" '
                 'x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>\n' % (xm, y, xm, yed))
        L.append('  <line class="pin" id="connector%dpin" connectorname="%d" fill="none" '
                 'stroke="#787878" stroke-width="0.75" stroke-linecap="round" '
                 'x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>\n'
                 % (pin[ac] - 1, pin[ac], xm, yed, xm, yl))
        L.append('  <rect class="terminal" id="connector%dterminal" x="%.2f" y="%.2f" width="0.0001" '
                 'height="0.0001" stroke="none" fill="none"/>\n' % (pin[ac] - 1, xm, yl))
        L.append('  <text transform="matrix(1 0 0 1 %.2f %.2f)" fill="#8C8C8C" font-family="DroidSans" '
                 'font-size="2.6">%d</text>\n'
                 % (xm - 3.2, 2.2 if chain is CHAIN_A else 37.4, pin[ac]))
        # A pin stub (left edge) and C pin stub (right edge)
        for pn, xe, px in ((pin[a], xl, 0.0), (pin[c], xr, 66.0)):
            L.append('  <line class="pin" id="connector%dpin" connectorname="%d" fill="none" '
                     'stroke="#787878" stroke-width="0.75" stroke-linecap="round" '
                     'x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>\n' % (pn - 1, pn, px, y, xe, y))
            L.append('  <rect class="terminal" id="connector%dterminal" x="%.2f" y="%.2f" width="0.0001" '
                     'height="0.0001" stroke="none" fill="none"/>\n' % (pn - 1, px, y))
            L.append('  <text transform="matrix(1 0 0 1 %.2f %.2f)" fill="#8C8C8C" font-family="DroidSans" '
                     'font-size="2.6">%d</text>\n'
                     % (2.0 if pn == pin[a] else tx, y - 1.2, pn))
        # node names: A / C sit above the chain next to their pin entry; the AC
        # name sits right beside its vertical pin, just inside the frame
        for nm, xt, yt in ((a, 6.0, y - 2.6), (c, 55.5, y - 2.6),
                           (ac, xm + 1.5, 5.5 if chain is CHAIN_A else 32.5)):
            L.append('  <text transform="matrix(1 0 0 1 %.2f %.2f)" fill="#000000" font-family="DroidSans" '
                     'font-size="3.0">%s</text>\n' % (xt, yt, nm))
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------- breadboard view --
def breadboard_svg():
    """Green adapter board: 3 + 3 header pins on the 2.54 mm grid, chip 1:1."""
    y0, y1 = 100.0, 300.0
    bh = y1 + 100.0
    cy = (y0 + y1) / 2.0
    S = 100.0 / 2.54                      # units per mm
    hb_l, hb_w = BODY_L / 2.0 * S, BODY_W / 2.0 * S
    hw, hh = PAD_W / 2.0 * S, PAD_H / 2.0 * S
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 500 %.0f">\n' % (500 * 0.0254, bh * 0.0254, bh),
         ' <g id="breadboard">\n',
         '  <rect x="0" y="0" width="500" height="%.0f" fill="#00aa44" stroke="#00772f" '
         'stroke-width="5"/>\n' % bh,
         '  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#303030" stroke="none"/>\n'
         % (250 - hb_l, cy - hb_w, 2 * hb_l, 2 * hb_w)]
    for i in range(1, 7):
        cx, cyy = pad_xy_mm(i)
        cx, cyy = 250 + cx * S, cy + cyy * S
        L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#c0c0c0" stroke="none"/>\n'
                 % (cx - hw, cyy - hh, 2 * hw, 2 * hh))
    L.append('  <circle cx="%.2f" cy="%.2f" r="5.0" fill="#c0c0c0" stroke="none"/>\n'
             % (250 - hb_l + 10.0, cy + 0.40 * S))
    # top mark / silkscreen marking code on the chip body (same code as the icon)
    L.append('  <text x="250" y="%.2f" font-size="13" fill="#c0c0c0" text-anchor="middle" '
             'dominant-baseline="central" font-family="DroidSans">%s</text>\n' % (cy, ICON_MARK))
    # header pins: left column = pins 1,2,3 (top->bottom), right = 4,5,6 (bottom->top)
    for col, order in ((0, (1, 2, 3)), (1, (6, 5, 4))):
        x = (100.0, 400.0)[col]
        for j, pno in enumerate(order):
            y = y0 + j * 100.0
            L.append('  <circle id="connector%dpin" connectorname="%s" cx="%.1f" cy="%.1f" r="%.1f" '
                     'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n'
                     % (pno - 1, node(pno), x, y, BB_PAD_R))
            L.append('  <circle cx="%.1f" cy="%.1f" r="%.1f" fill="#2b2b2b" stroke="none"/>\n'
                     % (x, y, BB_HOLE_R))
            L.append('  <text x="%.1f" y="%.1f" font-size="40" fill="#ffffff" text-anchor="middle" '
                     'dominant-baseline="central" font-family="DroidSans">%d</text>\n'
                     % (35.0 if col == 0 else 465.0, y, pno))
    L.append(' </g>\n</svg>\n')
    return "".join(L)


# ---------------------------------------------------------------------- fzp --
def fzp_xml(outdir):
    conns = []
    for i in range(1, 7):
        nm = node(i)
        conns.append(
            '  <connector id="connector%d" name="%s" type="male">\n'
            '   <description>pin %d - %s</description>\n'
            '   <views>\n'
            '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n'
            '    <schematicView><p layer="schematic" svgId="connector%dpin" '
            'terminalId="connector%dterminal"/></schematicView>\n'
            '    <pcbView><p layer="copper1" svgId="connector%dpin"/></pcbView>\n'
            '   </views>\n  </connector>\n'
            % (i - 1, nm, i, NODE_DESC[nm], i - 1, i - 1, i - 1, i - 1))
    pid = PART_ID
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <label>D</label>\n'
        ' <date>2026-09-24</date>\n'
        ' <tags>%s</tags>\n'
        ' <properties>\n'
        '  <property name="family">Diode</property>\n'
        '  <property name="package">SOT-363 (SC-70-6)</property>\n'
        '  <property name="part number">%s</property>\n'
        ' </properties>\n'
        ' <description>%s</description>\n'
        ' <views>\n'
        '  <iconView>\n   <layers image="icon/%s_icon.svg">\n'
        '    <layer layerId="breadboard"/>\n   </layers>\n  </iconView>\n'
        '  <breadboardView>\n   <layers image="breadboard/%s_breadboard.svg">\n'
        '    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
        '  <schematicView fliphorizontal="true" flipvertical="true">\n'
        '   <layers image="schematic/%s_schematic.svg">\n'
        '    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
        '  <pcbView>\n   <layers image="pcb/%s_pcb.svg">\n'
        '    <layer layerId="silkscreen"/>\n    <layer layerId="copper1"/>\n   </layers>\n  </pcbView>\n'
        ' </views>\n <connectors>\n%s </connectors>\n</module>\n'
        % (pid, TITLE, TAGS, TITLE, DESC, pid, pid, pid, pid, "".join(conns)))


def build(out_dir=None, part_id=None, fzpz_name=None):
    out = out_dir or OUT_DIR
    pid = part_id or PART_ID
    files = {
        "svg.pcb.%s_pcb.svg" % pid: pcb_svg(),
        "svg.schematic.%s_schematic.svg" % pid: schematic_svg(),
        "svg.breadboard.%s_breadboard.svg" % pid: breadboard_svg(),
        "svg.icon.%s_icon.svg" % pid: icon_svg(),
        "part.%s.fzp" % pid: fzp_xml(out),
    }
    for fn, text in files.items():
        with open(os.path.join(out, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %-46s %6d bytes" % (fn, len(text.encode("utf-8"))))
    fzpz_dir = os.path.normpath(os.path.join(out, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    dst = os.path.join(fzpz_dir, fzpz_name or FZPZ)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(files):
            z.write(os.path.join(out, fn), fn)
    print("wrote %s  (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    build()
