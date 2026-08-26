# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part for the ESP32-S3-WROOM-1 module.

Module: 18.00 x 25.50 mm, castellated SMD module. 40 pads + 1 centre ground
pad (EPAD). Pads on the two long sides + one short (bottom) side; PCB antenna
on the top (keep-out zone). Scale: 1 unit = 1 mm.

Authoritative pinout (Espressif datasheet + official KiCad footprint).
NOTE: the widely-circulated "57-pin" pinout (incl. some CN datasheets) is WRONG;
GPIO26-32 are consumed internally by the SPI flash and are not exposed.
"""

import os
import re
import zipfile
import xml.dom.minidom

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "ESP32-S3-WROOM-1_1"
TITLE = "ESP32-S3-WROOM-1"

BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "ESP32-S3-WROOM-1.fzpz"

BB_REF = "breadboard/%s_breadboard.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
PCB_REF = "pcb/%s_pcb.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID

# --------------------------------------------------------------------------
# Pinout. connector0..13 = LEFT (pins 1-14, top->bottom),
# connector14..25 = BOTTOM (pins 15-26, left->right),
# connector26..39 = RIGHT (pins 27-40, bottom->top),
# connector40 = centre GND pad.
LEFT_PINS = ["GND", "3V3", "EN", "IO4", "IO5", "IO6", "IO7", "IO15",
             "IO16", "IO17", "IO18", "IO8", "IO19", "IO20"]
BOT_PINS = ["IO3", "IO46", "IO9", "IO10", "IO11", "IO12", "IO13", "IO14",
            "IO21", "IO47", "IO48", "IO45"]
RIGHT_PINS = ["IO0", "IO35", "IO36", "IO37", "IO38", "IO39", "IO40", "IO41",
              "IO42", "IO44", "IO43", "IO2", "IO1", "GND"]

FUNC = {
    "GND": "Ground", "3V3": "3.3V power", "EN": "Chip enable / reset (active low)",
    "IO0": "GPIO0 (strapping, ADC1_CH1)", "IO1": "GPIO1 (ADC1_CH0)",
    "IO2": "GPIO2 (ADC1_CH2, TOUCH2)", "IO3": "GPIO3 (strapping, ADC1_CH3)",
    "IO4": "GPIO4 (ADC1_CH4, TOUCH4)", "IO5": "GPIO5 (ADC1_CH5, TOUCH5)",
    "IO6": "GPIO6 (ADC1_CH6, TOUCH6)", "IO7": "GPIO7 (ADC1_CH7, TOUCH7)",
    "IO8": "GPIO8 (ADC1_CH8, TOUCH8)", "IO9": "GPIO9 (ADC1_CH9, TOUCH9)",
    "IO10": "GPIO10 (ADC2_CH1, TOUCH10)", "IO11": "GPIO11 (ADC2_CH2, TOUCH11)",
    "IO12": "GPIO12 (ADC2_CH3, TOUCH12)", "IO13": "GPIO13 (ADC2_CH4, TOUCH13)",
    "IO14": "GPIO14 (ADC2_CH5, TOUCH14)", "IO15": "GPIO15 (ADC2_CH6, TOUCH15)",
    "IO16": "GPIO16 (ADC2_CH7, TOUCH16)", "IO17": "GPIO17 (ADC2_CH8, TOUCH17)",
    "IO18": "GPIO18 (ADC2_CH9, TOUCH18)", "IO19": "GPIO19 (USB_D-)",
    "IO20": "GPIO20 (USB_D+)", "IO21": "GPIO21",
    "IO35": "GPIO35 (reserved on octal-flash)", "IO36": "GPIO36 (reserved on octal-flash)",
    "IO37": "GPIO37 (reserved on octal-flash)", "IO38": "GPIO38",
    "IO39": "GPIO39", "IO40": "GPIO40", "IO41": "GPIO41", "IO42": "GPIO42",
    "IO43": "GPIO43 (U0TXD)", "IO44": "GPIO44 (U0RXD)",
    "IO45": "GPIO45 (strapping)", "IO46": "GPIO46 (strapping)",
    "IO47": "GPIO47", "IO48": "GPIO48",
}

# module geometry (mm)
MW, MH = 18.00, 25.50
PITCH = 1.27
N_L, N_B, N_R = 14, 12, 14

# pad row geometry (module coords, origin = top-left)
# left column: x=0, y 4.49 .. 21.0 (pin1 top)
L_Y0 = (MH - (N_L - 1) * PITCH) / 2          # 4.495
# bottom row: y=25.5, x 2.015 .. 15.985
B_X0 = (MW - (N_B - 1) * PITCH) / 2          # 2.015
# right column: x=18, pin27 bottom (y=21.0) .. pin40 top (y=4.49)
# pad half sizes
PAD_W, PAD_H = 1.5, 0.9    # land pad 1.5 radial x 0.9 along side


def pcb_svg():
    """PCB land pattern per datasheet Figure 11-1 (Recommended PCB Land Pattern).

    Module 18 x 25.5 mm. Edge pads 1.5 x 0.9 mm, pitch 1.27 mm, pad centre
    0.25 mm INSIDE the module outline (extend 0.5 mm outside / 1.0 mm inside).
    Left pads 1-14 top->bottom y = 7.49 + i*1.27; bottom pads 15-26 left->right
    x = 2.015 + i*1.27 (centre y 25.25); right pads 27-40 bottom->top y =
    24.0 - i*1.27 (centre x 17.75). Centre GND = 3x3 grid of 0.9 x 0.9 mm pads,
    pitch 1.4 mm, overall 3.7 x 3.7 mm (x 6.1/7.5/8.9, y 13.81/15.21/16.61),
    with 12 thermal vias (0.25 mm) in the 0.5 mm gaps (datasheet Fig 11-1
    "Via for thermal pad"). 1 unit = 1 mm."""
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    # viewBox trimmed to content (-0.5..18.5 x 0..26.0) + 0.3 mm margin all round
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="19.6mm" height="26.6mm" viewBox="-0.8 -0.3 19.6 26.6">\n')
    L.append(' <g id="silkscreen">\n')
    # module outline silkscreen, BROKEN (with 0.3 mm clearance) where the copper pads
    # sit so silkscreen never overlaps pads (DFM): pads span y 7.04..24.45 on the
    # left/right edges and x 1.565..16.435 on the bottom edge
    CL = 0.3
    L.append('  <path d="M 0 0 L 18 0 L 18 %.2f'
             ' M 18 %.2f L 18 25.5 L %.2f 25.5'
             ' M %.2f 25.5 L 0 25.5 L 0 %.2f'
             ' M 0 %.2f L 0 0" fill="none" stroke="#FFFFFF" stroke-width="0.15"/>\n'
             % (7.04 - CL, 24.45 + CL, 16.435 + CL, 1.565 - CL, 24.45 + CL, 7.04 - CL))
    # antenna keep-out zone (top 6 mm) - dashed
    L.append('  <rect x="0" y="0" width="%.2f" height="6" fill="none" stroke="#FFFFFF" stroke-width="0.12" stroke-dasharray="0.5 0.4"/>\n' % MW)
    L.append('  <text x="9" y="3.6" font-size="1.6" fill="#FFFFFF" text-anchor="middle" font-family="DroidSans">ANTENNA</text>\n')
    # copper1 (top) only - NO copper0 bottom layer. A plain SMD part keeps the
    # footprint clean (the centre 3x3 grid reads as 9 separate pads with board
    # gaps) and avoids the new-parts-editor / bottom-layer rendering surprises.
    # For heat dissipation the user adds their own vias + bottom ground copper
    # while routing (Fritzing via tool + ground fill), which is the standard
    # Fritzing workflow for a castellated SMD module.
    L.append(' </g>\n')   # close silkscreen
    L.append(' <g id="copper1">\n')
    # left pads (pins 1..14, top->bottom): centre x 0.25 -> x -0.5..1.0
    for i in range(N_L):
        yc = 7.49 + i * PITCH
        L.append('  <rect x="-0.5" y="%.3f" width="%.2f" height="%.2f" id="connector%dpin" fill="#f7bf13" fill-opacity="1" stroke="none"/>\n'
                 % (yc - PAD_H / 2, PAD_W, PAD_H, i))
    # bottom pads (pins 15..26, left->right): centre y 25.25 -> y 24.5..26.0
    for i in range(N_B):
        xc = 2.015 + i * PITCH
        cn = N_L + i
        L.append('  <rect x="%.3f" y="24.50" width="%.2f" height="%.2f" id="connector%dpin" fill="#f7bf13" fill-opacity="1" stroke="none"/>\n'
                 % (xc - PAD_H / 2, PAD_H, PAD_W, cn))
    # right pads (pins 27..40, bottom->top): centre x 17.75 -> x 17.0..18.5
    for i in range(N_R):
        yc = 24.0 - i * PITCH
        cn = N_L + N_B + i
        L.append('  <rect x="17.00" y="%.3f" width="%.2f" height="%.2f" id="connector%dpin" fill="#f7bf13" fill-opacity="1" stroke="none"/>\n'
                 % (yc - PAD_H / 2, PAD_W, PAD_H, cn))
    # centre GND (connector40): 3x3 grid of 0.9x0.9, pitch 1.4 (connector id on the
    # centre pad so the id stays unique)
    for gy in (13.81, 15.21, 16.61):
        for gx in (6.1, 7.5, 8.9):
            cid = ' id="connector40pin"' if (gx == 7.5 and gy == 15.21) else ''
            L.append('  <rect x="%.2f" y="%.2f" width="0.90" height="0.90"%s fill="#f7bf13" fill-opacity="1" stroke="none"/>\n'
                     % (gx - 0.45, gy - 0.45, cid))
    # NOTE: no pre-drawn thermal-via holes and no bottom copper in the part - the
    # user adds vias + bottom heatsink copper during PCB routing.
    L.append(' </g>\n')    # end copper1
    L.append('</svg>\n')
    return "".join(L)


def module_art(S, ox, oy, grad):
    """Emit the ESP32-S3-WROOM-1 module artwork (dark scalloped PCB board +
    meander antenna + two gold feed contacts + metallic shield + text/QR code +
    gold castellation pads), scaled by S (the icon is 1 unit = 1 mm; the
    breadboard uses S = 39.37) and translated by (ox, oy). The antenna is at
    the TOP of the module so it can protrude above the host board edge."""
    L = []
    r = 0.275 * S
    # dark PCB board, scalloped with a real 0.55 mm semicircular castellation
    # notch cut into every edge (no stroke, bbox exactly 18S x 25S)
    bd = ['  <path d="M %.2f %.2f' % (ox, oy), ' L %.2f %.2f' % (ox + 18 * S, oy)]
    for i in range(13, -1, -1):
        yc = (23.5 - i * 1.27) * S
        bd.append(' L %.2f %.2f A %.3f %.3f 0 0 0 %.2f %.2f' % (ox + 18 * S, oy + yc - r, r, r, ox + 18 * S, oy + yc + r))
    bd.append(' L %.2f %.2f' % (ox + 18 * S, oy + 25 * S))
    for i in range(11, -1, -1):
        xc = (0.96 + i * 1.38 + 0.45) * S
        bd.append(' L %.2f %.2f A %.3f %.3f 0 0 0 %.2f %.2f' % (ox + xc + r, oy + 25 * S, r, r, ox + xc - r, oy + 25 * S))
    bd.append(' L %.2f %.2f' % (ox, oy + 25 * S))
    for i in range(0, 14):
        yc = (23.5 - i * 1.27) * S
        bd.append(' L %.2f %.2f A %.3f %.3f 0 0 0 %.2f %.2f' % (ox, oy + yc + r, r, r, ox, oy + yc - r))
    bd.append(' L %.2f %.2f Z" fill="#2b2b2b"/>' % (ox, oy))
    L.append(' '.join(bd) + '\n')
    # meander antenna (borrowed from ESP-12F icon, mirrored L/R, top of module)
    ant = [(36.961, 10.969), (28.617, 10.969), (28.617, 3.269), (23.357, 3.269), (23.357, 10.969),
           (15.077, 10.969), (15.077, 3.269), (9.961, 3.269), (9.961, 15.286), (8.741, 15.286),
           (8.741, 3.269), (3.251, 3.269), (3.251, 15.289), (2.049, 15.289), (2.049, 2.049),
           (16.297, 2.049), (16.297, 9.749), (22.137, 9.749), (22.137, 2.049), (29.837, 2.049),
           (29.837, 9.749), (35.741, 9.749), (35.741, 2.049), (43.301, 2.049), (43.301, 15.289),
           (42.081, 15.289), (42.081, 3.269), (36.961, 3.269)]
    s = 0.40
    pts = ["%.2f,%.2f" % (ox + ((45.35 - x - 2.049) * s + 0.75) * S, oy + ((y - 2.049) * s + 0.5) * S)
           for (x, y) in ant]
    L.append('  <polygon points="%s" fill="#9aa0a6"/>\n' % " ".join(pts))
    # two gold feed contacts at the bottom of the two rightmost antenna runs
    L.append('  <circle cx="%.2f" cy="%.2f" r="%.3f" fill="#e3b23c"/>\n' % (ox + 14.33 * S, oy + 5.79 * S, 0.24 * S))
    L.append('  <circle cx="%.2f" cy="%.2f" r="%.3f" fill="#e3b23c"/>\n' % (ox + 17.01 * S, oy + 5.80 * S, 0.24 * S))
    # white metal shield (square corners, metallic gradient, no stroke)
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="url(#%s)"/>\n'
             % (ox + 1.1 * S, oy + 6.35 * S, 15.8 * S, 17.6 * S, grad))
    L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-weight="bold" fill="#111111" text-anchor="middle" font-family="Arial">ESPRESSIF</text>\n'
             % (ox + 9 * S, oy + 12.2 * S, 2.3 * S))
    L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="#333333" text-anchor="middle" font-family="Arial">ESP32-S3-WROOM-1</text>\n'
             % (ox + 9 * S, oy + 14.8 * S, 1.6 * S))
    L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" fill="#555555" text-anchor="middle" font-family="Arial">乐鑫信息科技</text>\n'
             % (ox + 9 * S, oy + 16.8 * S, 1.2 * S))
    # QR code (bottom-right of the shield)
    L.append('  <g fill="#111111">\n')
    for (qx, qy) in [(12.6, 17.6), (13.8, 17.6), (15.0, 17.6), (12.6, 18.8), (13.8, 18.8),
                     (12.6, 20.0), (15.0, 20.0), (13.8, 20.0), (15.0, 18.8), (15.0, 19.4), (12.6, 19.4)]:
        L.append('   <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"/>\n' % (ox + qx * S, oy + qy * S, 1.0 * S, 1.0 * S))
    L.append('  </g>\n')
    # gold edge pads, each with a matching CONCAVE notch on its outer end
    L.append('  <g fill="#e3b23c">\n')
    for i in range(14):
        yc = (23.5 - i * 1.27) * S
        L.append('   <path d="M %.2f %.2f L %.2f %.2f L %.2f %.2f A %.3f %.3f 0 0 1 %.2f %.2f L %.2f %.2f L %.2f %.2f Z"/>\n'
                 % (ox + 0.45 * S, oy + yc - 0.45 * S, ox, oy + yc - 0.45 * S, ox, oy + yc - r, r, r, ox, oy + yc + r,
                    ox, oy + yc + 0.45 * S, ox + 0.45 * S, oy + yc + 0.45 * S))
        L.append('   <path d="M %.2f %.2f L %.2f %.2f L %.2f %.2f A %.3f %.3f 0 0 0 %.2f %.2f L %.2f %.2f L %.2f %.2f Z"/>\n'
                 % (ox + 17.55 * S, oy + yc - 0.45 * S, ox + 18 * S, oy + yc - 0.45 * S, ox + 18 * S, oy + yc - r, r, r,
                    ox + 18 * S, oy + yc + r, ox + 18 * S, oy + yc + 0.45 * S, ox + 17.55 * S, oy + yc + 0.45 * S))
    for i in range(12):
        xc = (0.96 + i * 1.38 + 0.45) * S
        L.append('   <path d="M %.2f %.2f L %.2f %.2f L %.2f %.2f A %.3f %.3f 0 0 1 %.2f %.2f L %.2f %.2f L %.2f %.2f Z"/>\n'
                 % (ox + xc - 0.45 * S, oy + 24.55 * S, ox + xc - 0.45 * S, oy + 25 * S, ox + xc - r, oy + 25 * S, r, r,
                    ox + xc + r, oy + 25 * S, ox + xc + 0.45 * S, oy + 25 * S, ox + xc + 0.45 * S, oy + 24.55 * S))
    L.append('  </g>\n')
    return "".join(L)


# --------------------------------------------------------------------------
# USB Type-C (16-pin) connector art, reused verbatim from the TypeC16Pin part
# (svg/TypeC16Pin/svg.icon.TypeC16Pin_d89a481c23a1ca4ff437422a227ed0bb_1_icon.svg).
# The icon artwork is a real 8.94 mm wide receptacle drawn at ~1 unit =
# 0.3528 mm (content bbox 25.34 x 21.64 units == 8.94 x 7.63 mm). We lift the
# inner drawing group, strip the now-duplicate element ids, and re-emit it
# scaled for the breadboard. The gold contact pads are at the BOTTOM of the
# artwork, so we drop the connector onto the board edge with that edge at
# `bottom_y` (the plug face sits at the board edge).
_TYPEC_PATH = os.path.join(OUT_DIR, "..", "TypeC16Pin",
                           "svg.icon.TypeC16Pin_d89a481c23a1ca4ff437422a227ed0bb_1_icon.svg")
try:
    with open(_TYPEC_PATH, encoding="utf-8") as _tf:
        _typec_src = _tf.read()
    _tm = re.search(r'(<g\s+id="g40446"[^>]*>.*</g>)\s*</svg>', _typec_src, re.S)
    _TYPEC_ART = re.sub(r'\s+id="[^"]*"', '', _tm.group(1))
except Exception:
    _TYPEC_ART = None


def typec_art(cx, bottom_y, width_mm=8.94):
    """Emit the TypeC16Pin USB-C connector art, centred horizontally at cx,
    `width_mm` wide, sitting at the board's bottom edge (`bottom_y`). The
    artwork is rotated 180° about its own centre so the plug opening faces
    DOWN (out of the board edge) while the connector stays in the same box at
    the bottom of the board. Content bbox is 25.34 x 21.64 units = 8.94 x
    7.63 mm at 1:1, so the breadboard scale is width_mm/8.94 * 39.37."""
    s = width_mm * 39.37 / 25.34
    ox = cx - (25.34 / 2.0) * s
    oy = bottom_y - 21.64 * s
    rcx = (25.34 / 2.0) * s      # art centre in the scaled (breadboard) space
    rcy = (21.64 / 2.0) * s
    if _TYPEC_ART is None:
        return ('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#333333" '
                'stroke="#999999" stroke-width="5"/>\\n' % (ox, oy, 25.34 * s, 21.64 * s))
    return ('  <g transform="translate(%.2f %.2f) rotate(180 %.2f %.2f) scale(%.5f)">\n'
            '%s\n  </g>\n' % (ox, oy, rcx, rcy, s, _TYPEC_ART))

# --------------------------------------------------------------------------
# WS2812B 5050 RGB LED art, reused from the WS2812B/5050 part's breadboard view
# (svg/WS2812B/5050/svg.breadboard.WS2812B_5050_1_breadboard.svg). The LED body
# (4 gray SMT pads + dark die + gold bond wires + light lens) is authored at
# 1 unit = 0.3528 mm, so the same 13.89 scale factor as the USB-C art places it
# at true size on the YD board (5.0 x 5.0 mm). The artwork is rotated 180° so
# VDD (bottom-right on the bare 5050) ends up at the top-right corner, i.e. to
# the RIGHT of header pin 9 on the assembled board. Duplicate ids are stripped.
_WS2812_PATH = os.path.join(OUT_DIR, "..", "WS2812B", "5050",
                            "svg.breadboard.WS2812B_5050_1_breadboard.svg")
_WS2812_ART = None
try:
    _wdoc = xml.dom.minidom.parse(_WS2812_PATH)
    _ledg = None
    for _g in _wdoc.getElementsByTagName("g"):
        if _g.getAttribute("transform") == "translate(10.8000,21.6000) rotate(90) translate(-10.8000,-21.6000)":
            _ledg = _g
            break
    if _ledg is not None:
        for _e in _ledg.getElementsByTagName("*"):
            if _e.hasAttribute("id"):
                _e.removeAttribute("id")
        _WS2812_ART = _ledg.toxml()
except Exception:
    _WS2812_ART = None


def ws2812_art(cx, cy):
    """Emit the realistic WS2812B 5050 LED art centred at (cx, cy), scaled to
    true size (5.0 mm = 197 units at 39.37 units/mm), rotated 180° so the VDD
    pad sits at the top-right (toward header pin 9)."""
    s = 13.89
    if _WS2812_ART is None:
        return ('  <rect x="%.0f" y="%.0f" width="197" height="197" rx="12" fill="#1a1a1a" '
                'stroke="#333333" stroke-width="4"/>\n' % (cx - 98, cy - 98))
    return ('  <g transform="translate(%d %d) rotate(180) scale(%.5f) translate(-10.8 -21.6)">\n'
            '%s\n  </g>\n' % (cx, cy, s, _WS2812_ART))

def breadboard_svg():
    """Breadboard view = the user's YD-ESP32-S3 COREBOARD V1.4 dev board.
    Total board size 27.94 x 63.39 mm: the black PCB is 57.15 mm tall with
    SQUARE corners, and the ESP32-S3-WROOM-1 module (drawn with the ICON
    artwork via module_art) sits at the top with its antenna protruding
    6.24 mm above the PCB edge (57.15 + 6.24 = 63.39 mm). The internal
    coordinate space uses 100 units = 2.54 mm; the whole board is wrapped in a
    scale(0.072) group so the final SVG is at the Fritzing breadboard hole
    grid (7.2 units per 2.54 mm) and the two 22-pin header columns (25.4 mm
    apart, centre-to-centre) land on breadboard holes. Layout measured from
    the vendor "ESP32-S3-Metric" placement drawing: module top, WS2812 RGB +
    LDO below, RST/BOOT on the right, CH343P + 2 USB-C at the bottom.
    44 male header pins total: 41 connectors mapped from the module's
    J1/J2 positions that carry a matching signal, plus 3 breadboard-only
    connectors (connector41..43) for the extra power pins J1-2 3V3, J1-21
    5Vin and J2-22 GND. The visible labels are the header SILKSCREEN names
    (J1/J2), rotated vertically (left +90 deg CW reading top->down, right
    -90 deg CCW). No mounting holes (the real board has none)."""
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    W = 1100                      # 27.94 mm (internal 100 units = 2.54 mm)
    HH = 2496                     # 63.39 mm (PCB 57.15 + 6.24 antenna)
    # Fritzing breadboard hole grid = 7.2 units per 2.54 mm hole. Our internal
    # 100-units-per-2.54mm space must be scaled by 7.2/100 = 0.072 so pins land
    # on breadboard holes (verified vs arduino_Uno/NodeMCU core parts + the
    # core breadboard.svg: holes at 7.2 pitch).
    BB_SCALE = 7.2 / 100.0        # 0.072
    PCB_TOP = 246                 # antenna protrusion above the PCB edge
    PCB_H = 2250                  # 57.15 mm PCB
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="27.94mm" height="63.39mm" viewBox="0 0 %.1f %.1f">\n' % (W * BB_SCALE, HH * BB_SCALE))
    L.append(' <defs>\n')
    L.append('  <linearGradient id="bbShield" x1="0" y1="0" x2="0" y2="1">\n')
    L.append('   <stop offset="0" stop-color="#e2e2e2"/>\n')
    L.append('   <stop offset="0.45" stop-color="#b4b4b4"/>\n')
    L.append('   <stop offset="1" stop-color="#7c7c7c"/>\n')
    L.append('  </linearGradient>\n')
    L.append(' </defs>\n')
    L.append(' <g id="breadboard" transform="scale(%g)">\n' % BB_SCALE)
    # black PCB with SQUARE corners (user: the 4 corners are right angles)
    L.append('  <rect x="0" y="%d" width="%d" height="%d" fill="#262626" stroke="#000000" stroke-width="6"/>\n' % (PCB_TOP, W, PCB_H))
    # ESP32-S3-WROOM-1 module at the TOP, antenna protruding above the PCB edge
    # (the module is drawn with the exact ICON artwork, scaled to the board)
    L.append(module_art(39.37, 196.0, 0.0, "bbShield"))
    # CJ6107A33GW 3.3V LDO (SOT-223) right of pins 8/18 + WS2812B 5050 RGB LED
    # (right of pins 9/10). SOT-223 drawn horizontally then rotated 90° CW about
    # its centre so its 3 gull-wing PINS (on the left after rotation) align in X
    # with the WS2812B 5050's left pads (x=201); the heatsink tab ends up on the
    # right. 6.5 x 3.5 mm = 256 x 138 units.
    L.append(ws2812_art(302, 1771))
    CX, CY, BW, BH = 291, 1371, 256, 138
    L.append('  <g transform="rotate(90 %d %d)">\n' % (CX, CY))
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#303030" stroke="#4a4a4a" stroke-width="4"/>\n'
             % (CX - BW // 2, CY - BH // 2, BW, BH))
    # large heatsink tab (top of the unrotated part -> right after rotation)
    L.append('  <rect x="%d" y="%d" width="200" height="46" rx="4" fill="#8c8c8c"/>\n' % (CX - 100, CY - BH // 2 - 48))
    # 3 gull-wing pins at the bottom (-> left after rotation)
    for dx in (-90, 0, 90):
        L.append('  <rect x="%d" y="%d" width="50" height="38" rx="4" fill="#8c8c8c"/>\n' % (CX + dx - 25, CY + BH // 2 + 2))
    L.append('  <text x="%d" y="%d" font-size="28" fill="#ffffff" text-anchor="middle" font-family="DroidSans">CJ6107A33GW</text>\n' % (CX, CY + 8))
    L.append('  </g>\n')
    # RST + BOOT buttons on the right side: RST at the height between pins 38/39
    # (y 1171), BOOT between pins 36/37 (y 1371). Text (font 52 = pin-label size,
    # same as "37") sits to the RIGHT of each button, vertical reading top->down.
    # Cluster kept left of the right-column labels (x>=968).
    #
    # The button artwork is the NTC013-AT1J-A160T 4.2x3.2mm SMD tact switch,
    # copied from the ESP32-S2-DevKitC-1 Fritzing part breadboard (its RESET
    # button): light-grey housing + dark round actuator with a white shine +
    # 4 corner feet + 2 light-grey J-lead pads + dark detail bars. Copied at
    # scale 0.60 so the housing (~90x70 units) fits between the pin rows and
    # stays left of the RST/BOOT labels at x=915 (housing right edge ~895).
    def ntc013_btn(cx, cy):
        """Emit one NTC013 tact switch scaled 0.60 about (cx, cy). Exact
        geometry (relative to the housing centre) from the S2-DevKitC RESET
        button: housing 151x116, actuator ~74x76 centred, feet 8x13 at the
        corners, J-lead pads 26x54 sticking out the sides, 4 dark bars."""
        L.append('  <g transform="translate(%d %d) scale(0.60)">\n' % (cx, cy))
        # housing (light grey)
        L.append('  <rect x="-75.5" y="-58" width="151" height="116" fill="#cccccc"/>\n')
        # 4 dark feet at the corners
        L.append('  <rect x="-78.5" y="-31" width="8" height="13" fill="#333333"/>\n')
        L.append('  <rect x="66.5" y="-31" width="8" height="13" fill="#333333"/>\n')
        L.append('  <rect x="-78.5" y="15" width="8" height="13" fill="#333333"/>\n')
        L.append('  <rect x="66.5" y="15" width="8" height="13" fill="#333333"/>\n')
        # 2 light-grey J-lead pads sticking out left/right
        L.append('  <rect x="-102.5" y="-28" width="26" height="54" fill="#e6e6e6"/>\n')
        L.append('  <rect x="74.5" y="-28" width="26" height="54" fill="#e6e6e6"/>\n')
        # 4 dark detail bars
        L.append('  <rect x="-76.5" y="-58" width="21" height="8" fill="#333333"/>\n')
        L.append('  <rect x="53.5" y="-58" width="21" height="8" fill="#333333"/>\n')
        L.append('  <rect x="-76.5" y="0" width="21" height="8" fill="#333333"/>\n')
        L.append('  <rect x="53.5" y="0" width="21" height="8" fill="#333333"/>\n')
        # round actuator (dark) with white shine arc
        L.append('  <ellipse cx="-2.5" cy="-1" rx="37.766" ry="36.967" fill="#333333" stroke="#1a1a1a" stroke-width="3.03"/>\n')
        L.append('  <path d="m -15.02,-36.72 c 5.29,-2.70 7.93,-2.70 13.19,-2.70 13.19,0 23.78,5.40 29.07,16.19" fill="none" stroke="#ffffff" stroke-width="3.03"/>\n')
        L.append('  </g>\n')
    for cy, lab in ((1171, "RST"), (1371, "BOOT")):
        bx, tx = 788, 863
        ntc013_btn(bx, cy)
        L.append('  <text x="%d" y="%d" font-size="52" fill="#ffffff" text-anchor="middle" font-family="DroidSans" transform="rotate(90 %d %d)">%s</text>\n' % (tx, cy, tx, cy, lab))
    # CH343P USB-UART bridge (QFN16, left of header pins 21/47). 3.5 x 3.5 mm
    # body with 16 edge pads (4 per side) + a central exposed thermal pad.
    # Moved down 1 char (52) from (798, 1867).
    QX, QY, QB = 798, 1919, 138
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#303030" stroke="#4a4a4a" stroke-width="4"/>\n'
             % (QX - QB // 2, QY - QB // 2, QB, QB))
    # 16 edge pads, 4 per side (straddling the body edges)
    for dx in (-45, -15, 15, 45):
        L.append('  <rect x="%d" y="%d" width="16" height="32" fill="#8c8c8c"/>\n' % (QX + dx - 8, QY - QB // 2 - 16))   # top
        L.append('  <rect x="%d" y="%d" width="16" height="32" fill="#8c8c8c"/>\n' % (QX + dx - 8, QY + QB // 2 - 16))   # bottom
    for dy in (-45, -15, 15, 45):
        L.append('  <rect x="%d" y="%d" width="32" height="16" fill="#8c8c8c"/>\n' % (QX - QB // 2 - 16, QY + dy - 8))   # left
        L.append('  <rect x="%d" y="%d" width="32" height="16" fill="#8c8c8c"/>\n' % (QX + QB // 2 - 16, QY + dy - 8))   # right
    # centre exposed thermal pad
    L.append('  <rect x="%d" y="%d" width="48" height="48" fill="#555555"/>\n' % (QX - 24, QY - 24))
    L.append('  <text x="%d" y="%d" font-size="20" fill="#cccccc" text-anchor="middle" font-family="DroidSans">CH343p</text>\n' % (QX, QY - QB // 2 - 22))
    # 2x USB Type-C at the bottom edge (left = OTG native USB, right = CH343p
    # UART), drawn with the real TypeC16Pin connector art (plug face at the
    # board edge, gold pads on the bottom edge of the artwork)
    L.append(typec_art(300, HH, 8.94))   # OTG
    L.append(typec_art(790, HH, 8.94))   # UART
    L.append('  <text x="300" y="2130" font-size="20" fill="#aaaaaa" text-anchor="middle" font-family="DroidSans">OTG</text>\n')
    L.append('  <text x="790" y="2130" font-size="20" fill="#aaaaaa" text-anchor="middle" font-family="DroidSans">UART</text>\n')
    # ---- pins: two 22-pin columns, 25.4 mm apart (centre-to-centre) ----
    PX_L, PX_R = 50, W - 50       # (W-50) - 50 = 1000 units = 25.4 mm
    PY0 = PCB_TOP + 75            # top pin centre on the PCB; pitch 100 = 2.54 mm
    # header silkscreen names printed on the actual YD board (J1 left / J2 right,
    # top->bottom). Labels are shown rotated vertically next to each pin.
    HEADER_L = ["3V3", "3V3", "RST", "4", "5", "6", "7", "15", "16", "17", "18",
                "8", "3", "46", "9", "10", "11", "12", "13", "14", "5Vin", "GND"]
    HEADER_R = ["GND", "TX", "RX", "1", "2", "42", "41", "40", "39", "38", "37",
                "36", "35", "0", "45", "48", "47", "21", "20", "19", "GND", "GND"]
    # connector index -> (col, row); row 0 = top, 21 = bottom.
    # Each module pin sits at the header pin that carries the same net:
    # J1 (left) = module left+bottom side, J2 (right) = module right side.
    POS = [("R", 0), ("L", 0), ("L", 2), ("L", 3), ("L", 4), ("L", 5), ("L", 6),
           ("L", 7), ("L", 8), ("L", 9), ("L", 10), ("L", 11), ("R", 19), ("R", 18),
           ("L", 12), ("L", 13), ("L", 14), ("L", 15), ("L", 16), ("L", 17),
           ("L", 18), ("L", 19), ("R", 17), ("R", 16), ("R", 15), ("R", 14),
           ("R", 13), ("R", 12), ("R", 11), ("R", 10), ("R", 9), ("R", 8),
           ("R", 7), ("R", 6), ("R", 5), ("R", 2), ("R", 1), ("R", 3), ("R", 4),
           ("L", 21), ("R", 20)]

    def header_name(col, row):
        return (HEADER_L if col == "L" else HEADER_R)[row]

    # vertical labels: left rotate +90° (CW, reads top->down), right -90° (CCW).
    # Narrow sans font (DroidSans) + close to the pins, like the real board's
    # silkscreen.
    LBL_OFF = 36
    for i in range(41):
        col, row = POS[i]
        x = PX_L if col == "L" else PX_R
        y = PY0 + row * 100
        L.append('  <circle cx="%d" cy="%d" r="26" fill="#b8b8b8" stroke="#6a6a6a" stroke-width="5" id="connector%dpin"/>\n' % (x, y, i))
        lx = x + LBL_OFF if col == "L" else x - LBL_OFF
        rot = 90 if col == "L" else -90
        L.append('  <text x="%d" y="%d" font-size="52" fill="#ffffff" text-anchor="middle" font-family="DroidSans" transform="rotate(%d %d %d)">%s</text>\n'
                 % (lx, y, rot, lx, y, header_name(col, row)))
    # J1-2 3V3, J1-21 5Vin and J2-22 GND are REAL male header pins on the YD
    # board (extra power pins that don't carry a module signal). Give each a
    # breadboard-only connector (connector41..43) so its hole turns green and it
    # is routable on the breadboard (same pattern as core part m40-1100300).
    for cn, (col, row) in zip((41, 42, 43), (("L", 1), ("L", 20), ("R", 21))):
        x = PX_L if col == "L" else PX_R
        y = PY0 + row * 100
        L.append('  <circle cx="%d" cy="%d" r="26" fill="#b8b8b8" stroke="#6a6a6a" stroke-width="5" id="connector%dpin"/>\n' % (x, y, cn))
        lx = x + LBL_OFF if col == "L" else x - LBL_OFF
        rot = 90 if col == "L" else -90
        L.append('  <text x="%d" y="%d" font-size="52" fill="#ffffff" text-anchor="middle" font-family="DroidSans" transform="rotate(%d %d %d)">%s</text>\n'
                 % (lx, y, rot, lx, y, header_name(col, row)))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def schematic_svg():
    """41-pin symbol in the datasheet Figure-7 style.

    EPAD(41) is a normal horizontal pin at the very top of the right column
    (one row above pin 40). The package is widened so the bottom row shifts
    right: pin 15 sits where 16 used to be (generous left clearance). Bottom
    numbers sit ~10 units inside the bottom edge; names sit just above their
    leads so the line never crosses the text."""
    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="242" height="314" viewBox="87 -1 242 314">\n')
    L.append(' <g id="schematic">\n')
    # package body (196 wide x 290 tall, black frame) - 15/26 margins equal
    BX, BY, BW, BH = 110, 0, 196, 290
    L.append('  <rect x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" stroke="#000000" stroke-width="1.6"/>\n' % (BX, BY, BW, BH))
    L.append('  <text x="208" y="145" font-size="10" fill="#000000" text-anchor="middle" transform="rotate(90 208 145)">ESP32-S3-WROOM-1</text>\n')
    # ---- left pins 1..14 (connector0..13) ----
    step = 230.0 / 13.0
    for i in range(14):
        y = 30 + i * step
        L.append('  <line class="pin" id="connector%dpin" connectorname="%d" x1="110" y1="%.2f" x2="88" y2="%.2f" stroke="#787878" stroke-width="1.0"/>\n' % (i, i, y, y))
        L.append('  <rect class="terminal" id="connector%dterminal" x="88" y="%.2f" width="0.0001" height="0.0001" fill="none"/>\n' % (i, y))
        L.append('  <text x="120" y="%.2f" font-size="7" fill="#000000" text-anchor="start" font-family="DroidSans">%d</text>\n' % (y + 2.5, i + 1))
        L.append('  <text x="99" y="%.2f" font-size="7" fill="#333333" text-anchor="middle" font-family="DroidSans">%s</text>\n' % (y - 2, LEFT_PINS[i]))
    # ---- right column: pin 41 (EPAD) top, then 40 .. 27 (connector26..39) ----
    rstep = 260.0 / 14.0           # 15 pins over 260: y 15 .. 275
    for i in range(15):
        y = 15 + i * rstep
        if i == 0:                  # EPAD (connector40), pin 41
            cn, num, name = 40, 41, "EPAD"
        else:                       # pin 40-i ... pin 27-i+1
            cn = 40 - i
            num = 41 - i
            name = RIGHT_PINS[14 - i]
        L.append('  <line class="pin" id="connector%dpin" connectorname="%d" x1="306" y1="%.2f" x2="328" y2="%.2f" stroke="#787878" stroke-width="1.0"/>\n' % (cn, cn, y, y))
        L.append('  <rect class="terminal" id="connector%dterminal" x="328" y="%.2f" width="0.0001" height="0.0001" fill="none"/>\n' % (cn, y))
        L.append('  <text x="296" y="%.2f" font-size="7" fill="#000000" text-anchor="end" font-family="DroidSans">%d</text>\n' % (y + 2.5, num))
        L.append('  <text x="317" y="%.2f" font-size="7" fill="#333333" text-anchor="middle" font-family="DroidSans">%s</text>\n' % (y - 2, name))
    # ---- bottom pins 15..26 (connector14..25): shifted right, centred, vertical ----
    for i in range(12):
        x = 136.5 + i * 13.0        # 136.5 .. 279.5 (15 at the old 16 position)
        cn = 14 + i
        L.append('  <line class="pin" id="connector%dpin" connectorname="%d" x1="%.1f" y1="290" x2="%.1f" y2="312" stroke="#787878" stroke-width="1.0"/>\n' % (cn, cn, x, x))
        L.append('  <rect class="terminal" id="connector%dterminal" x="%.1f" y="312" width="0.0001" height="0.0001" fill="none"/>\n' % (cn, x))
        L.append('  <text x="%.1f" y="280" font-size="7" fill="#000000" text-anchor="middle" transform="rotate(270 %.1f 280)" font-family="DroidSans">%d</text>\n' % (x, x, 15 + i))
        L.append('  <text x="%.1f" y="300" font-size="7" fill="#333333" text-anchor="middle" transform="rotate(270 %.1f 300)" font-family="DroidSans">%s</text>\n' % (x - 3.5, x - 3.5, BOT_PINS[i]))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def icon_svg():
    """Module icon at 1 unit = 1 mm (18 x 25 mm).
    The whole 18x25 board is a dark PCB with no outline, so the bounding box
    is exactly 18 x 25 mm; its left/right/bottom edges are scalloped with a
    real 0.55 mm dia semicircular castellation notch cut into the board (and
    the matching gold pad) at every pin, so each notch is a true transparent
    gap (no black board, no gold). The metallic silver shield (square corners,
    vertical gradient, no stroke) is 15.8 mm wide x 17.6 mm tall, centred
    horizontally (1.1 mm side margins) with its bottom edge 1.05 mm above the
    board bottom (top edge at y=6.35). The top ~6 mm antenna zone holds a
    meander antenna borrowed from the ESP-12F icon but mirrored left-right and
    scaled to the 18-wide board; all its segments are a uniform ~0.48 mm wide,
    and two gold feed contacts (circle diameter = trace width) sit at the
    bottom of the two rightmost vertical runs. 14 gold pads per side (0.9 x
    0.45 mm, pitch 1.27 mm) + 12 pads along the bottom edge, each with a
    matching concave notch cut into its outer end."""
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="18mm" height="25mm" viewBox="0 0 18 25">\n')
    # metallic silver gradient for the shield (top light -> bottom dark)
    L.append(' <defs>\n')
    L.append('  <linearGradient id="shieldMetal" x1="0" y1="0" x2="0" y2="1">\n')
    L.append('   <stop offset="0" stop-color="#e2e2e2"/>\n')
    L.append('   <stop offset="0.45" stop-color="#b4b4b4"/>\n')
    L.append('   <stop offset="1" stop-color="#7c7c7c"/>\n')
    L.append('  </linearGradient>\n')
    L.append(' </defs>\n')
    L.append(' <g id="icon">\n')
    # the whole module artwork is generated by module_art(scale=1, at origin)
    L.append(module_art(1.0, 0.0, 0.0, "shieldMetal"))
    L.append(' </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def fzp_xml():
    conns = []
    rows = [(LEFT_PINS, range(N_L)),
            (BOT_PINS, range(N_L, N_L + N_B)),
            (RIGHT_PINS, range(N_L + N_B, N_L + N_B + N_R))]
    for pins, ids in rows:
        for label, cn in zip(pins, ids):
            # Male header pins (J1/J2) so Fritzing draws them as male pins that
            # insert into the breadboard holes (verified: S2-DevKitC + NodeMCU
            # both use type="male" on their header connectors).
            conns.append('  <connector id="connector%d" name="%s" type="male">\n' % (cn, label))
            conns.append('   <description>%s</description>\n' % FUNC.get(label, label))
            conns.append('   <views>\n')
            conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/></breadboardView>\n' % cn)
            conns.append('    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n' % (cn, cn))
            conns.append('    <pcbView><p layer="copper1" svgId="connector%dpin"/></pcbView>\n' % cn)
            conns.append('   </views>\n')
            conns.append('  </connector>\n')
    # centre GND pad (SMD on copper1 only - no bottom copper; heat dissipation is
    # handled by the user adding vias + a bottom ground fill while routing). It is
    # mapped to the J2-21 GND header pin on the dev board, so it is type=male so
    # its hole turns green on the breadboard.
    conns.append('  <connector id="connector40" name="GND" type="male">\n')
    conns.append('   <description>Ground (centre thermal pad)</description>\n')
    conns.append('   <views>\n')
    conns.append('    <breadboardView><p layer="breadboard" svgId="connector40pin"/></breadboardView>\n')
    conns.append('    <schematicView><p layer="schematic" svgId="connector40pin" terminalId="connector40terminal"/></schematicView>\n')
    conns.append('    <pcbView><p layer="copper1" svgId="connector40pin"/></pcbView>\n')
    conns.append('   </views>\n')
    conns.append('  </connector>\n')
    # breadboard-only connectors for the dev board's extra male header pins that
    # don't carry a module signal (J1-2 3V3, J1-21 5Vin, J2-22 GND). They are real
    # header pins, so they get breadboard connectors to turn green / be routable.
    # No schematic/pcb pins (the module itself has only 41 pads).
    for cn, label in ((41, "3V3"), (42, "5Vin"), (43, "GND")):
        conns.append('  <connector id="connector%d" name="%s" type="male">\n' % (cn, label))
        conns.append('   <description>Dev-board extra power header pin</description>\n')
        conns.append('   <views>\n')
        conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin" terminalId="connector%dterminal"/></breadboardView>\n' % (cn, cn))
        conns.append('   </views>\n')
        conns.append('  </connector>\n')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>%s</title>\n'
        ' <label>U</label>\n'
        ' <date>2026-08-26</date>\n'
        ' <tags><tag>ESP32</tag><tag>S3</tag><tag>WiFi</tag><tag>BLE</tag><tag>module</tag><tag>WROOM</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">ESP32</property>\n'
        '  <property name="variant">ESP32-S3-WROOM-1</property>\n'
        '  <property name="pins">44</property>\n'
        '  <property name="part number">ESP32-S3-WROOM-1-N8R2/N8R8/N16R8</property>\n'
        ' </properties>\n'
        ' <description>ESP32-S3-WROOM-1 WiFi + BLE module, 18.0x25.5mm, castellated SMD, 40 pads + centre GND. Octal-flash variants reserve GPIO35/36/37.</description>\n'
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
        BB_SVG: breadboard_svg(),
        SCHEM_SVG: schematic_svg(),
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
