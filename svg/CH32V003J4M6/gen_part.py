# -*- coding: utf-8 -*-
"""Generate the CH32V003J4M6 (SOP8) Fritzing part.

Geometry is IDENTICAL to CH32V002J4M6 -- same package (SOP8 3.9 x 5.0 mm,
1.27 mm pitch) and same pinout (the two chips are pin compatible / drop-in),
so this script reuses the CH32V002J4M6 generator (repo-internal import, the
repo allows cross-part references) and only overrides the variant strings:

  part id / title / moduleId   -> CH32V003J4M6
  icon + breadboard top mark    -> CH32V003
  schematic symbol label       -> CH32V003
  fzp description / tags       -> 10-bit ADC + internal OPA (V003),
                                  pin compatible with CH32V002J4M6

Datasheet: D:\\Downloads\\CH32V003DS0.PDF (V1.8)
  - SOP8 = CH32V003J4M6, body 3.9 x 5.0 mm, pitch 1.27 mm        [ch.4]
  - pin table 2-1 = same pin numbering as CH32V002J4M6
  - 16 KB flash / 2 KB SRAM / 1x10-bit ADC / 1 set of OPA / 3.3 or 5 V

Also usable as a drop-in replacement for CH32V002J4M6 (12-bit ADC, no OPA).
"""

import importlib.util
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.normpath(os.path.join(HERE, "..", "CH32V002J4M6"))
FZPZ_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "fzpz"))

PART_ID = "CH32V003J4M6"
TAGS = "<tag>IC</tag><tag>MCU</tag><tag>RISC-V</tag><tag>CH32V003</tag>"
DESC = ("WCH CH32V003J4M6 RISC-V MCU, SOP8 3.9x5.0 mm / 1.27 mm pitch, 3.3-5 V, "
        "10-bit ADC and one internal OPA. Pin compatible with CH32V002J4M6 "
        "(12-bit ADC, no OPA) - drop-in. Pin 1 = PD6/PA1 and pin 8 = "
        "PD1/PD4/PD5 are shorted inside the package, input use only.")


def _load_base():
    """Load the CH32V002J4M6 generator by explicit file path (no name clash)."""
    path = os.path.join(BASE_DIR, "gen_part.py")
    spec = importlib.util.spec_from_file_location("ch32v002j4m6_gen", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build():
    g = _load_base()
    parts = {
        "svg.icon.%s_icon.svg" % PART_ID: g.icon_svg(),
        "svg.breadboard.%s_breadboard.svg" % PART_ID: g.breadboard_svg(),
        "svg.schematic.%s_schematic.svg" % PART_ID: g.schematic_svg(),
        "svg.pcb.%s_pcb.svg" % PART_ID: g.pcb_svg(),
        "part.%s.fzp" % PART_ID: g.fzp_xml(),
    }
    out = {}
    for fn, text in parts.items():
        text = text.replace("CH32V002J4M6", PART_ID).replace("CH32V002", "CH32V003")
        if fn.endswith(".fzp"):
            # only the MODULE description (the one right after </properties>);
            # the 8 per-connector descriptions must stay untouched
            text = re.sub(r"(</properties>\s*)<description>.*?</description>",
                          lambda m: m.group(1) + "<description>%s</description>" % DESC,
                          text, count=1, flags=re.S)
            text = re.sub(r"<tags>.*?</tags>", "<tags>%s</tags>" % TAGS, text, flags=re.S)
        out[fn] = text
    return out


def main():
    files = build()
    for fn, text in files.items():
        with open(os.path.join(HERE, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %-46s %6d bytes" % (fn, len(text.encode("utf-8"))))
    os.makedirs(FZPZ_DIR, exist_ok=True)
    dst = os.path.join(FZPZ_DIR, PART_ID + ".fzpz")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(files):                 # flat zip, subdir refs live in the fzp
            z.write(os.path.join(HERE, fn), fn)
    print("wrote %s  (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    main()
