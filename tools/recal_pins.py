# -*- coding: utf-8 -*-
r"""用 Fritzing **自己渲染的**走线反推全局映射 ⇒ 重新标定每个脚的位置 ✓

原理（2026-09-26 ✓）：
  · 我写的导线在 sketch 里的两个端点我**知道** ✓；Fritzing 把它们渲染成 `<line x1 y1 x2 y2/>` ✓
    ⇒ 一一对应就能最小二乘拟合出 `导出 = s·sketch + A` ✓（两个参数/轴 ✓），残差即自检 ✓
  · 有了全局映射，脚的 sketch 坐标 = (脚导出坐标 − A)/s ✓ —— **不再用**逐元件那套公式 ✗
    （那套只是元件内部自洽 ✗，跨元件不成立 ⇒ 端点错开 ✗，用户 2026-09-26 指出 ✓）
  · 注意：导线端点与脚端点重合处 Fritzing 会画一个 `<circle>`（junction 点 ✓）—— 与错开无关 ✓

用法：py -3.13 recal_pins.py <我的.fzz> <Fritzing导出的.svg> [--out pins_fixed.py]
"""
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

SCRATCH = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.environ.get("FRITZING_TOOLS", r"f:\git\fritzing-parts-langhua\tools")
sys.path.insert(0, SCRATCH)
sys.path.insert(0, TOOLS)
import part_measure as pm                        # noqa: E402
from pin_ruler import mul, parse_tf, apply        # noqa: E402


def tag(e):
    return e.tag.split("}")[-1]


def my_wire_ends(fzz):
    """我的导线：mi → 两个端点（sketch ✓）"""
    z = zipfile.ZipFile(fzz)
    root = ET.fromstring(z.read([n for n in z.namelist() if n.endswith(".fz")][0]))
    out = {}
    for e in root.iter("instance"):
        if not (e.get("moduleIdRef") or "").startswith("Wire"):
            continue
        vw = pm.child(e, "views")
        sub = pm.child(vw, "schematicView") if vw is not None else None
        g = pm.child(sub, "geometry") if sub is not None else None
        if g is None or g.get("x") is None:
            continue
        x, y = pm.num(g.get("x")), pm.num(g.get("y"))
        dx = pm.num(g.get("x2")) or 0.0
        dy = pm.num(g.get("y2")) or 0.0
        out[e.get("modelIndex")] = ((x, y), (x + dx, y + dy))
    return out


def svg_ends_and_pins(svg):
    """从导出 SVG 取：导线端点（按 partID=mi+'0' ✓）与各脚的 terminal 坐标（导出坐标 ✓）"""
    root = ET.parse(svg).getroot()
    wires, pins = {}, {}

    def walk(el, m, pid):
        m2 = mul(m, parse_tf(el.get("transform"))) if el.get("transform") else m
        if el.get("partID"):
            pid = el.get("partID")
            # ★ 一根导线在导出里 = 一个**只含一条 <line>** 的组 ✓（2026-09-26 实测 ✓）
            #   （不能只看到 <line> 就收 ✗ —— 零件的引脚线也是 <line> ✗）
            kids = list(el)
            if len(kids) == 1 and tag(kids[0]) == "line" and kids[0].get("x1") is not None:
                ln = kids[0]
                m3 = mul(m2, parse_tf(ln.get("transform"))) if ln.get("transform") else m2
                wires[pid] = [apply(m3, float(ln.get("x1")), float(ln.get("y1"))),
                              apply(m3, float(ln.get("x2")), float(ln.get("y2")))]
        mm = re.fullmatch(r"connector(.+?)terminal", el.get("id") or "")
        if mm and pid and el.get("x") is not None:
            pins.setdefault(pid, {})["connector" + mm.group(1)] = \
                apply(m2, float(el.get("x")), float(el.get("y")))
        for c in el:
            walk(c, m2, pid)
    walk(root, (1, 0, 0, 1, 0, 0), None)
    return wires, pins


def lin_fit(pairs):
    n = len(pairs)
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    den = sum((p[0] - mx) ** 2 for p in pairs)
    s = sum((p[0] - mx) * (p[1] - my) for p in pairs) / den if den else 1.0
    a = my - s * mx
    return s, a, max(abs(p[1] - (a + s * p[0])) for p in pairs)


def main(argv):
    fzz, svg = argv[0], argv[1]
    out_file = argv[argv.index("--out") + 1] if "--out" in argv else None
    mine = my_wire_ends(fzz)
    wires, pins = svg_ends_and_pins(svg)
    print("我的导线 %d 根；导出里认出 %d 根" % (len(mine), len(wires)))

    xp, yp, miss = [], [], []
    for mi, (pa, pb) in mine.items():
        got = wires.get(mi + "0")
        if not got or len(got) != 2:
            miss.append(mi)
            continue
        for (sp, ep) in ((pa, got[0]), (pb, got[1])):
            xp.append((sp[0], ep[0]))
            yp.append((sp[1], ep[1]))
    print("参与拟合的端点 %d 个；没认出的导线 %d 根 %s"
          % (len(xp), len(miss), miss[:4]))
    sx, ax, rx = lin_fit(xp)
    sy, ay, ry = lin_fit(yp)
    print("映射: 导出_x = %.6f·sketch + %.4f（残差 %.4f）" % (sx, ax, rx))
    print("      导出_y = %.6f·sketch + %.4f（残差 %.4f）" % (sy, ay, ry))

    fixed = {}
    for pid, pmap in pins.items():
        mi = pid[:-1]
        name = mi
        fixed[name] = {cid: ((ex - ax) / sx, (ey - ay) / sy) for cid, (ex, ey) in pmap.items()}
    print("\n标定出 %d 个元件的脚（按 modelIndex ✓）" % len(fixed))
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('r"""脚位置（由 recal_pins.py 从 Fritzing 自己的渲染反推 ✓ 勿手改）\n\n')
            f.write('导出 = %.6f·sketch + %.4f（x）／%.6f·sketch + %.4f（y）\n"""\n'
                    % (sx, ax, sy, ay))
            f.write("PINS = {\n")
            for mi, pmap in sorted(fixed.items()):
                f.write("    %r: {\n" % mi)
                for cid, (x, y) in sorted(pmap.items(), key=lambda kv: int(kv[0][9:])):
                    f.write("        %r: (%.6f, %.6f),\n" % (cid, x, y))
                f.write("    },\n")
            f.write("}\n")
        print("写出: %s" % out_file)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
