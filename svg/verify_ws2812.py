# -*- coding: utf-8 -*-
"""Verify both WS2812B parts (2020 + 5050) for consistency."""
import os
import re
import xml.etree.ElementTree as ET

ROOT = r"f:\git\fritzing-parts-langhua"
PARTS = [
    (os.path.join(ROOT, "svg", "WS2812B", "2020"), "WS2812B_2020_1", "2020"),
    (os.path.join(ROOT, "svg", "WS2812B", "5050"), "WS2812B_5050_1", "5050"),
]

NS = "{http://www.w3.org/2000/svg}"


def svg_root(path):
    tree = ET.parse(path)
    return tree.getroot()


def check(name, ok, detail=""):
    print(("  [OK] " if ok else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""))


for folder, pid, tag in PARTS:
    print("=" * 60)
    print("PART:", tag, pid, "in", folder)
    pcb = svg_root(os.path.join(folder, "svg.pcb.%s_pcb.svg" % pid))
    schem = svg_root(os.path.join(folder, "svg.schematic.%s_schematic.svg" % pid))
    bb = svg_root(os.path.join(folder, "svg.breadboard.%s_breadboard.svg" % pid))

    # --- PCB ---
    print("--- PCB ---")
    pads = {}
    for g in pcb.iter(NS + "g"):
        if g.get("id") == "copper1":
            for r in g.iter(NS + "rect"):
                pads[r.get("id")] = (float(r.get("x")), float(r.get("y")),
                                     float(r.get("width")), float(r.get("height")))
    print("  pads:", pads)
    conn_names = {"connector0pin": "DOUT", "connector1pin": "VDD", "connector2pin": "DIN", "connector3pin": "GND"}
    for cid, cname in conn_names.items():
        check("pad exists " + cname, cid in pads, str(pads.get(cid)))

    # silk lines clear of pads
    silk_lines = []
    for g in pcb.iter(NS + "g"):
        if g.get("id") == "silkscreen":
            for ln in g.iter(NS + "line"):
                silk_lines.append((float(ln.get("x1")), float(ln.get("y1")),
                                   float(ln.get("x2")), float(ln.get("y2"))))
    print("  silk lines:", silk_lines)
    overlap = False
    for (x1, y1, x2, y2) in silk_lines:
        for px, py, pw, ph in pads.values():
            # sample midpoint
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            if px - 0.1 <= mx <= px + pw + 0.1 and py - 0.1 <= my <= py + ph + 0.1:
                overlap = True
                print("    silk overlaps pad at", mx, my)
    check("silk clear of pads", not overlap)

    # --- breadboard ---
    print("--- Breadboard ---")
    pins = {}
    for g in bb.iter(NS + "g"):
        if g.get("transform"):
            m = re.search(r"translate\(([\d.]+),([\d.]+)\)", g.get("transform"))
            for r in g.iter(NS + "rect"):
                if r.get("id") and r.get("id").endswith("pin"):
                    pins[r.get("id")] = (float(m.group(1)), float(m.group(2)))
    print("  pins:", pins)
    for cid, cname in conn_names.items():
        check("pin " + cname, cid in pins, str(pins.get(cid)))

    # --- schematic terminals ---
    print("--- Schematic ---")
    terminals = []
    for r in schem.iter(NS + "rect"):
        if r.get("class") == "terminal":
            terminals.append((r.get("id"), r.get("x"), r.get("y"), r.get("width"), r.get("height")))
    print("  terminals:", terminals)
    bad = [t for t in terminals if t[3] not in ("0.0001",) or t[4] not in ("0.0001",)]
    check("all terminals 0.0001", not bad)

    # --- fzp connectors ---
    print("--- FZP ---")
    fzp_path = os.path.join(folder, "part.%s.fzp" % pid)
    fzp_text = open(fzp_path, encoding="utf-8").read()
    conns = re.findall(r'<connector id="(\w+)" name="(\w+)" type="(\w+)">', fzp_text)
    print("  connectors:", conns)
    check("4 connectors", len(conns) == 4)

    # every connector mapped in each view
    for view in ["breadboardView", "schematicView", "pcbView"]:
        for cid, cname, _ in conns:
            pat = r'<%s><p layer="[^"]+" svgId="%s' % (view, cid)
            check("fzp %s maps %s" % (view, cname), re.search(pat, fzp_text) is not None)

    # schematic terminalId present
    for cid, cname, _ in conns:
        pat = r'<schematicView><p layer="schematic" svgId="%spin" terminalId="%sterminal"' % (cid, cid)
        check("fzp terminal %s" % cname, re.search(pat, fzp_text) is not None)

print("=" * 60)
print("done")
