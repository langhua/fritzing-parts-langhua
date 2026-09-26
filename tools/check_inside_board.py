"""探针：绿板里"**本体是不是还在板框内**" ✓（改板边后必查：别把本体切到板外 ✗）。

做法：把 `fill=#00aa44` 的矩形当板 ✓，其余图元的合并包围盒当本体 ✓（都含 transform ✓），
看本体是否完全落在板内 ✓，并报四边余量（内部单位 ✓）。
用法：py -3.13 check_inside_board.py <breadboard.svg> ...
"""
import sys
import os
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import part_box as pb          # noqa: E402

SHAPES = ("rect", "path", "circle", "ellipse", "polygon", "polyline", "line", "text")


def tag(e):
    t = e.tag
    return t.rsplit("}", 1)[-1] if "}" in t else t


def scan(path):
    root = ET.parse(path).getroot()
    green, other = [], []

    def walk(el, m):
        m2 = pb.mul(m, pb.parse_tf(el.get("transform"))) if el.get("transform") else m
        fill = (el.get("fill") or "").strip().lower()
        if tag(el) in SHAPES:
            b = pb.shape_bbox(el)
            if b is not None:
                p0, p1 = pb.apply(m2, b[0], b[1]), pb.apply(m2, b[2], b[3])
                box = (min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1]))
                (green if fill == "#00aa44" else other).append(box)
        for c in list(el):
            walk(c, m2)
    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    return green, other


for f in sys.argv[1:]:
    g, o = scan(f)
    if not g or not o:
        print("%-22s 跳过（绿板 %d / 其它 %d）" % (os.path.basename(f), len(g), len(o)))
        continue
    gb = (min(b[0] for b in g), min(b[1] for b in g), max(b[2] for b in g), max(b[3] for b in g))
    ob = (min(b[0] for b in o), min(b[1] for b in o), max(b[2] for b in o), max(b[3] for b in o))
    m_l, m_r = ob[0] - gb[0], gb[2] - ob[2]
    m_t, m_b = ob[1] - gb[1], gb[3] - ob[3]
    ok = m_l > 0 and m_r > 0 and m_t > 0 and m_b > 0
    print("%-22s 板 %s | 本体 %s | 余量 左%.1f 右%.1f 上%.1f 下%.1f ⇒ %s"
          % (os.path.basename(f).replace("svg.breadboard.", "").replace("_breadboard.svg", ""),
             tuple(round(v, 1) for v in gb), tuple(round(v, 1) for v in ob),
             m_l, m_r, m_t, m_b, "本体在板内 ✓" if ok else "**本体超出板框 ✗**"))
