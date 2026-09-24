# -*- coding: utf-8 -*-
"""CH32V003F4U6 -- QFN20 3x3 mm, IDENTICAL geometry to CH32V002F4U6
(same package + same pin numbering per the datasheets), so this script reuses
the CH32V002F4U6 generator (repo-internal cross-folder reference is allowed)
and only overrides the identity strings:

  part id / title / moduleId   -> CH32V003F4U6
  icon + breadboard top mark   -> V003
  schematic symbol label       -> CH32V003
  fzp description / tags       -> 10-bit ADC + internal OPA, pin compatible
                                  with CH32V002F4U6 (drop-in)

Datasheet: D:\\Downloads\\CH32V003DS0.PDF (V1.8) -- ch.4 lists
"QFN20 3.0*3.0mm 0.4mm 15.7mil  CH32V003F4U6"; pin table 2-1 = same numbering.
"""

import importlib.util
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.normpath(os.path.join(HERE, "..", "CH32V002F4U6"))
FZPZ_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "fzpz"))

PART_ID = "CH32V003F4U6"
TOP_MARK = "V003"
CHIP = "CH32V003"
SCHEM_NAME = "CH32V003"
TAGS = "<tag>IC</tag><tag>MCU</tag><tag>RISC-V</tag><tag>CH32V003</tag>"
DESC = ("WCH CH32V003F4U6 RISC-V MCU, QFN20 3x3 mm / 0.4 mm pitch, 3.3-5 V, "
        "10-bit ADC (6 channels + 2) and one internal OPA, 18 I/O. Pin compatible "
        "with CH32V002F4U6 (12-bit ADC, no OPA) - drop-in. The exposed pad is VSS "
        "and is tied to pin 4.")


def main():
    spec = importlib.util.spec_from_file_location(
        "ch32v002f4u6_gen", os.path.join(BASE_DIR, "gen_part.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    # override the identity (geometry / pins stay the same)
    g.OUT_DIR = HERE
    g.PART_ID = PART_ID
    g.TITLE = PART_ID
    g.TOP_MARK = TOP_MARK
    g.CHIP = CHIP
    g.SCHEM_NAME = SCHEM_NAME
    files = {
        "svg.icon.%s_icon.svg" % PART_ID: g.icon_svg(),
        "svg.breadboard.%s_breadboard.svg" % PART_ID: g.breadboard_svg(),
        "svg.schematic.%s_schematic.svg" % PART_ID: g.schematic_svg(),
        "svg.pcb.%s_pcb.svg" % PART_ID: g.pcb_svg(),
        "part.%s.fzp" % PART_ID: g.fzp_xml(),
    }
    out = {}
    for fn, text in files.items():
        text = text.replace("CH32V002F4U6", PART_ID).replace("CH32V002", "CH32V003")
        if fn.endswith(".fzp"):
            # only the MODULE description (right after </properties>)
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
