"""探针：把某件绿板的**四条边**和**针脚线**打成"草图单位"，并给出**未折叠**的原始偏移 ✓。

为什么需要它 ✓：`audit_green_board.py` 报的是**折叠后**的相位（`min(d, 9-d)` ✗）——
  0.28 到底是"差 0.28"还是"差 8.72"看不出来 ✗，而补半格要按**方向**挪 ✓。
用法：py -3.13 bb_phase_raw.py <breadboard.svg>
输出：每条边到**最近针脚线**的有符号偏移（草图单位 ✓）+ 建议挪动量（挪到 ±4.5 ✓，取小者 ✓）
"""
import sys
import os
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import part_box as pb          # noqa: E402

PITCH = 9.0                    # 2.54mm = 9 草图单位 ✓


def tag(e):
    t = e.tag
    return t.rsplit("}", 1)[-1] if "}" in t else t


def scan(path):
    root = ET.parse(path).getroot()
    cm = pb.canvas_mm(root.attrib)
    vb = [float(v) for v in (root.get("viewBox") or "").split()]
    k = (cm[0] / 25.4 * 90.0) / vb[2] if len(vb) == 4 and vb[2] else 0.09
    ox, oy = (vb[0] if len(vb) == 4 else 0.0), (vb[1] if len(vb) == 4 else 0.0)
    green, pads_x, pads_y = [], [], []

    def walk(el, m):
        m2 = pb.mul(m, pb.parse_tf(el.get("transform"))) if el.get("transform") else m
        fill = (el.get("fill") or "").strip().lower()
        b = pb.shape_bbox(el)
        if b is not None:
            p0, p1 = pb.apply(m2, b[0], b[1]), pb.apply(m2, b[2], b[3])
            box = (min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1]))
            if tag(el) in ("rect", "path", "polygon") and fill == "#00aa44":
                green.append(box)
            eid = el.get("id") or ""
            if eid.startswith("connector") and ("pin" in eid or "leg" in eid):
                pads_x.append((box[0] + box[2]) / 2.0)
                pads_y.append((box[1] + box[3]) / 2.0)
        for c in list(el):
            walk(c, m2)
    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    return k, ox, oy, green, pads_x, pads_y


for f in sys.argv[1:]:
    k, ox, oy, green, px, py = scan(f)
    if not green or not px:
        print("%s：绿板 %d / 针脚 %d ⇒ 跳过" % (os.path.basename(f), len(green), len(px)))
        continue
    gb = (min(b[0] for b in green), min(b[1] for b in green),
          max(b[2] for b in green), max(b[3] for b in green))
    # ★ 草图单位 = (svg 坐标 − viewBox 原点) × k ✓（原点必须减掉 ✓，否则整体偏 ✗）
    ex = [((gb[0] - ox) * k), ((gb[2] - ox) * k)]
    ey = [((gb[1] - oy) * k), ((gb[3] - oy) * k)]
    plx = sorted(set(round((v - ox) * k, 4) for v in px))
    ply = sorted(set(round((v - oy) * k, 4) for v in py))
    print("%s（k=%.4f，viewBox 原点 %.2f,%.2f）" % (os.path.basename(f), k, ox, oy))
    print("   针脚列 %s" % plx)
    print("   针脚行 %s" % ply)
    for name, e, lines in (("左边", ex[0], plx), ("右边", ex[1], plx),
                           ("上边", ey[0], ply), ("下边", ey[1], ply)):
        d = min((e - L for L in lines), key=abs)          # 有符号偏移 ✓
        r = abs(d) % PITCH
        move = (PITCH / 2 - (abs(d) % PITCH)) % PITCH
        if abs(r) < 0.02 or abs(r - PITCH) < 0.02:
            print("   %s %.3f ⇒ 偏移 %+.3f ⇒ **压在孔线上 ✗** ⇒ 往内挪 %.3f 单位 ✓"
                  % (name, e, d, min(PITCH / 2, PITCH - PITCH / 2)))
        else:
            print("   %s %.3f ⇒ 偏移 %+.3f（余 %.3f）⇒ 再挪 %.3f 单位到半格 ✓"
                  % (name, e, d, r, min(move, move - PITCH, key=abs)))
