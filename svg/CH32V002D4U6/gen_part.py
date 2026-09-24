# -*- coding: utf-8 -*-
"""CH32V002D4U6 -- QFN12, 2 x 2 mm, 0.4 mm pitch (QFN12 exists for the
CH32V002 only; the CH32V003 has TSSOP20 / QFN20 / SOP16 / SOP8).

Reuses the CH32V002F4U6 generator (repo-internal reference) and overrides the
package config + pin table.  Per datasheet table 2-1 (QFN12 column):

  pin  1 PA1   2 PA2   3 PD0   4 VDD   5 PC0   6 PC3
       7 PC4   8 PC6   9 PC7  10 PD1  11 PD4  12 PD7
  pin 0 (exposed pad) = VSS  -- the QFN12 has NO separate VSS pin, so the pad
  IS the ground connection (no <bus> needed; GND_PINS = []).

Datasheet: D:\\Downloads\\CH32V002DS0.PDF (V1.7), ch.4:
"QFN12 2*2mm 0.4mm 15.7mil Quad Flat No-lead Package CH32V002D4U6"
(silicon/IO: 16K flash, 4K RAM, 12-bit ADC, 11 GPIO)
"""

import importlib.util
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.normpath(os.path.join(HERE, "..", "CH32V002F4U6"))
FZPZ_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "fzpz"))

PART_ID = "CH32V002D4U6"
TOP_MARK = "V002"
CHIP = "CH32V002"
SCHEM_NAME = "CH32V002"
TAGS = "<tag>IC</tag><tag>MCU</tag><tag>RISC-V</tag><tag>CH32V002</tag><tag>QFN12</tag>"
DESC = ("WCH CH32V002D4U6 RISC-V MCU, QFN12 2x2 mm / 0.4 mm pitch, 2.5-5 V, "
        "12-bit ADC, 11 I/O. The exposed pad is VSS (the QFN12 has no separate "
        "VSS pin) - route it to ground.")

# ---- package overrides -------------------------------------------------------
BODY_MM = 2.0
PER_SIDE = 3
EPAD_MM = 1.05
ICON_S = 8.5
GND_PINS = []
PIN_NAMES = ["PA1", "PA2", "PD0", "VDD", "PC0", "PC3",
             "PC4", "PC6", "PC7", "PD1", "PD4", "PD7"]
PIN_DESC = {
    "VDD": "supply 2.5 / 3.3 / 5 V",
    "PA1": "PA1 (ADC_IN1)", "PA2": "PA2 (ADC_IN0)", "PC4": "PC4 (ADC_IN2)",
    "PD1": "PD1 (SWIO debug)", "PD4": "PD4 (ADC_IN7)",
}


def main():
    spec = importlib.util.spec_from_file_location(
        "ch32v002f4u6_gen", os.path.join(BASE_DIR, "gen_part.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    g.OUT_DIR = HERE
    g.PART_ID = PART_ID
    g.TITLE = PART_ID
    g.TOP_MARK = TOP_MARK
    g.CHIP = CHIP
    g.SCHEM_NAME = SCHEM_NAME
    g.BODY_MM = BODY_MM
    g.PER_SIDE = PER_SIDE
    g.EPAD_MM = EPAD_MM
    g.ICON_S = ICON_S
    g.GND_PINS = GND_PINS
    g.PIN_NAMES = PIN_NAMES
    g.PIN_DESC = PIN_DESC
    g.PAD_R_MM = BODY_MM / 2.0 + 0.25
    files = {
        "svg.icon.%s_icon.svg" % PART_ID: g.icon_svg(),
        "svg.breadboard.%s_breadboard.svg" % PART_ID: g.breadboard_svg(),
        "svg.schematic.%s_schematic.svg" % PART_ID: g.schematic_svg(),
        "svg.pcb.%s_pcb.svg" % PART_ID: g.pcb_svg(),
        "part.%s.fzp" % PART_ID: g.fzp_xml(),
    }
    out = {}
    for fn, text in files.items():
        text = text.replace("CH32V002F4U6", PART_ID)
        if fn.endswith(".fzp"):
            text = re.sub(r"(</properties>\s*)<description>.*?</description>",
                          lambda m: m.group(1) + "<description>%s</description>" % DESC,
                          text, count=1, flags=re.S)
            text = re.sub(r"<tags>.*?</tags>", "<tags>%s</tags>" % TAGS, text, flags=re.S)
        out[fn] = text
    for fn, text in out.items():
        with open(os.path.join(HERE, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %-46s %6d bytes" % (fn, len(text.encode("utf-8"))))
    os.makedirs(FZPZ_DIR, exist_ok=True)
    dst = os.path.join(FZPZ_DIR, PART_ID + ".fzpz")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(out):
            z.write(os.path.join(HERE, fn), fn)
    print("wrote %s  (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    main()
