# -*- coding: utf-8 -*-
"""BAS70DW-04-7-F: exactly the same die/configuration as BAS70BRW (4 Schottky
diodes = two series pairs, nodes A1/AC1/C1 + A2/AC2/C2), only the pin numbers
attached to the nodes are different:

    pin  1 = A1    2 = C1    3 = AC2    4 = A2    5 = C2    6 = AC1
  (BAS70BRW:        2 = A2    3 = AC2    4 = C2    5 = C1    6 = AC1)

Reuses the BAS70BRW generator (repo-internal reference) and overrides only the
part identity + the pin/node table, so both parts are guaranteed to share the
same SOT-363 geometry, silk, schematic drawing style and breadboard layout.
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.normpath(os.path.join(HERE, "..", "BAS70BRW"))

PART_ID = "BAS70DW_04_SOT363_1"
TITLE = "BAS70DW-04"
FZPZ = "BAS70DW-04.fzpz"
TAGS = ("<tag>diode</tag><tag>Schottky</tag><tag>array</tag><tag>SOT-363</tag>"
        "<tag>BAS70</tag><tag>BAS70DW</tag>")
DESC = ("Diodes BAS70DW-04-7-F: 4 x 70 V Schottky diodes in SOT-363 (SC-70-6), wired as two "
        "series pairs with all six nodes available (A1/AC1/C1 and A2/AC2/C2). "
        "Pin order differs from BAS70BRW; usable as a 4-diode bridge.")

NODE_OF_PIN = ["A1", "C1", "AC2", "A2", "C2", "AC1"]
ICON_MARK = "K74"        # 丝印/顶面打标码


def main():
    spec = importlib.util.spec_from_file_location(
        "bas70brw_gen", os.path.join(BASE_DIR, "gen_part.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    g.PART_ID = PART_ID
    g.TITLE = TITLE
    g.FZPZ = FZPZ
    g.TAGS = TAGS
    g.DESC = DESC
    g.NODE_OF_PIN = NODE_OF_PIN
    g.ICON_MARK = ICON_MARK
    g.build(out_dir=HERE, part_id=PART_ID, fzpz_name=FZPZ)


if __name__ == "__main__":
    main()
