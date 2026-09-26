"""诊断（只读 ✓）：把某两根线（某个孔对）的**所有候选走法**独立量一遍 ——
直 / L 形 / Z 形 / U 形，逐条报【真实长 + 形状加权长 + 交集数 + 成本 + 是否合法】，
并报**被哪条规则拒** ✓。

目的：回答"这两根斜线**为什么**没画成折线" —— 是**折线被规则拒了** ✗，
      还是**折线只是排序输了** ✗（`best_link` 的键是 (交集, 折弯, …) ✗ ⇒ 直线必赢 ✗）。

一份实现 ✓：孔坐标 / 判碰 / 遮挡 / 重叠 全调 `bb_compare` ✓（与度量同源 ✓）；
          本体框调 `part_box.body_box` ✓（与生成器同源 ✓）。
★ 唯一**抄**来的是 `shape_factor`（形状罚系数 ✓）—— 只为对照，抄在下面并标明出处 ✗。

用法：py -3.13 diag_pair.py <fzz> <孔A> <孔B> [--drop Wire…] [--top N]
"""
import sys
import os
import math
import xml.etree.ElementTree as ET

LIB = os.path.dirname(os.path.abspath(__file__))     # 与 bb_compare/part_box 同目录 ✓
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import bb_compare as BC                      # noqa: E402
import part_box as pbox                      # noqa: E402
import part_measure as pm                    # noqa: E402

MMU = 25.4 / 90.0                            # 1 sketch 单位 = 1/90 in ✓
K_MM = 10.0                                  # 汇率（与 bb_route4.K_MM 同值 ✓）
K = K_MM / MMU
OBSCURE_LIMIT = BC.OBSCURE_LIMIT
NEAR_DIST = BC.NEAR_DIST


def tag(e):
    t = e.tag
    return t.rsplit("}", 1)[-1] if "}" in t else t


def child(e, n):
    for c in e:
        if tag(c) == n:
            return c
    return None


def simplify(pts):                           # 抄自 bb_route4（去重复点/共线点 ✓）
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) < 1e-9 and abs(p[1] - out[-1][1]) < 1e-9:
            continue
        out.append(p)
    i = 1
    while i < len(out) - 1:
        a, b, c = out[i - 1], out[i], out[i + 1]
        if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) < 1e-9:
            del out[i]
        else:
            i += 1
    return out


def shape_factor(pts):                       # 抄自 bb_route4.shape_factor（斜线罚 1.5 ✓）
    if len(pts) > 2:
        return 1.0
    dx, dy = abs(pts[0][0] - pts[1][0]), abs(pts[0][1] - pts[1][1])
    if dx < 1e-9 or dy < 1e-9:
        return 1.0
    return 1.5


def plen(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def segs_of(pts):
    return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def body_boxes(fzz):
    """从 fzz 里读各元件的**本体框**（与 bb_route4 同一套 ✓：pbox.body_box + pbox.place ✓）"""
    z = __import__("zipfile").ZipFile(fzz)
    name = [n for n in z.namelist() if n.endswith(".fz")][0]
    root = ET.fromstring(z.read(name))
    base_of_fzz = os.path.dirname(fzz)
    out = []
    for e in root.iter("instance"):
        mid = e.get("moduleIdRef") or ""
        if mid.startswith("Wire") or mid.startswith("Breadboard"):
            continue
        sub = child(child(e, "views"), "breadboardView")
        if sub is None:
            continue
        ttl = (e.findtext("title") or "").strip()
        g = child(sub, "geometry")
        if g is None or g.get("x") is None:
            continue
        # 元件目录：fzz 里记的是相对路径（parts/user/…）⇒ 先试 fzz 旁边，再试本仓同级
        fpz = (e.get("path") or "").replace("/", os.sep)
        cands = [os.path.join(base_of_fzz, fpz),
                 os.path.normpath(os.path.join(base_of_fzz, "..", "..", fpz))]
        for c0 in cands:
            if os.path.isfile(c0):
                r2 = ET.parse(c0).getroot()
                lay = r2.find(".//breadboardView/layers")
                if lay is None or not lay.get("image"):
                    break
                b = os.path.dirname(os.path.dirname(c0))
                for s2 in ("", "core", "contrib", "user"):
                    svg = os.path.normpath(os.path.join(b, "svg", s2,
                                                        lay.get("image").replace("/", os.sep)))
                    if os.path.isfile(svg):
                        bd = pbox.body_box(svg)
                        if bd is not None:
                            out.append((ttl, pbox.place((pm.num(g.get("x")), pm.num(g.get("y"))),
                                                        pbox.tf_of(g), bd)))
                        break
                break
    return out


def candidates(p, q, boxes):
    """候选模板（与 bb_route4.routes_pt 同类 ✓；这里把偏移**加密到 4.5 单位** ✓
       —— 为了回答"到底有没有合法折线" ✓，比生成器更细 ✓）"""
    out = [[p, q], [p, (p[0], q[1]), q], [p, (q[0], p[1]), q]]
    o = 4.5
    k = 1
    while o * k <= 171.0:
        for oo in (o * k, -o * k):
            out.append([p, (p[0], q[1] + oo), (q[0], q[1] + oo), q])
            out.append([p, (p[0] + oo, p[1]), (p[0] + oo, q[1]), q])
        k += 1
    for _t, (bx0, by0, bx1, by1) in boxes:
        for xa, xb in ((bx0 - 13.5, bx1 + 13.5), (bx1 + 13.5, bx0 - 13.5)):
            for yy in (by0 - 13.5, by1 + 13.5):
                sa, sb, sy = round(xa / 4.5) * 4.5, round(xb / 4.5) * 4.5, round(yy / 4.5) * 4.5
                out.append([p, (sa, p[1]), (sa, sy), (sb, sy), (sb, q[1]), q])
                out.append([p, (p[0], sy), (sa, sy), (sa, p[1]), (sb, p[1]), q])
    seen, uniq = set(), []
    for r in out:
        if not all(-9.0 <= x <= 576.0 and -9.0 <= y <= 189.0 for x, y in r):
            continue
        s = simplify(r)
        key = tuple((round(x, 3), round(y, 3)) for x, y in s)
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return uniq


def main(argv):
    fzz, ha, hb = argv[0], argv[1], argv[2]
    drop = set()
    top = 8
    if "--drop" in argv:
        drop = set(argv[argv.index("--drop") + 1].split(","))
    if "--top" in argv:
        top = int(argv[argv.index("--top") + 1])

    links, plugged = BC.load(fzz)
    links = [lk for lk in links if not lk.legend]
    boxes = body_boxes(fzz)
    ends_other = set()
    segs_other = []
    for lk in links:
        if any(w in drop for w in lk.wids):
            continue
        segs_other.extend(lk.segs)
        ends_other.update(h[0] for h in lk.holes)
    watch = ends_other | set(plugged)
    print("本体框 %d 个；其它引线 %d 段；要照看的孔（接线孔 + 插脚孔）= %d 个；被剔除的线：%s"
          % (len(boxes), len(segs_other), len(watch), ",".join(sorted(drop)) or "无"))
    for ttl, b in sorted(boxes):             # ★ 与生成器打印的 box 行**逐项对账** ✓
        print("   box %-5s x %7.1f..%7.1f  y %7.1f..%7.1f" % (ttl, b[0], b[2], b[1], b[3]))
    p, q = BC.hole_xy(ha), BC.hole_xy(hb)
    print("孔对 %s(%.0f,%.0f) → %s(%.0f,%.0f)" % (ha, p[0], p[1], hb, q[0], q[1]))

    rows = []
    for pts in candidates(p, q, boxes):
        r = evaluate(pts, segs_other, watch, boxes)
        rows.append((pts, r))
    rows.sort(key=lambda t: (t[1][0] is None, t[1][0] if t[1][0] is not None else 1e9))
    ok = [t for t in rows if t[1][0] is not None]
    bad = [t for t in rows if t[1][0] is None]
    print("\n—— 合法候选（按成本排序，前 %d）——" % top)
    print("  %-3s %-9s %-9s %-4s %-9s %s" % ("段", "真实长mm", "加权长mm", "交集", "成本", "走法"))
    for pts, (c, ln, wln, cr, crowd) in ok[:top]:
        print("  %-3d %-9.1f %-9.1f %-4d %-9.1f %s"
              % (len(pts) - 1, ln * MMU, wln * MMU, cr, c * MMU,
                 " → ".join("(%.0f,%.0f)" % xy for xy in pts)))
    print("\n—— 被拒的候选（按规则归类，各给 1 例）——")
    why = {}
    for pts, r in bad:
        why.setdefault(r[5], []).append(pts)
    for reason, lst in sorted(why.items(), key=lambda kv: -len(kv[1])):
        pts = min(lst, key=plen)
        print("  ✗ %-38s ×%-4d 例：%s" % (reason, len(lst),
                                          " → ".join("(%.0f,%.0f)" % xy for xy in pts)))
    return 0


def evaluate(pts, segs_other, watch, boxes):
    """返回 (成本 or None, 真实长, 加权长, 交集数, 拥挤度[, 拒绝原因])"""
    segs = segs_of(pts)
    ln = plen(pts)
    wln = ln * shape_factor(pts)
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if BC.seg_overlap(*segs[i], *segs[j]) or BC.seg_intersect(*segs[i], *segs[j]):
                return (None, ln, wln, 0, 0.0, "① 路径自交/自叠")
    for a, b in segs:
        for ttl, r in boxes:
            if BC.seg_hits_box(a, b, r):      # ★ 与生成器**同一条**规则 ✓（碰框就拒 ✗）
                return (None, ln, wln, 0, 0.0, "② 碰到元件 %s 的本体框" % ttl)
    cr = 0
    for a, b in segs:
        for c2, d2 in segs_other:
            if BC.seg_overlap(a, b, c2, d2):
                return (None, ln, wln, cr, 0.0, "③ 与现有线段重叠")
            if BC.pair_kind(a, b, c2, d2):
                cr += 1
        for h in watch:
            if BC.same_pt(BC.hole_xy(h), pts[0]) or BC.same_pt(BC.hole_xy(h), pts[-1]):
                continue
            if BC.obscures(a, b, BC.hole_xy(h)) >= OBSCURE_LIMIT:
                return (None, ln, wln, cr, 0.0, "④ 盖住了已接线的孔 %s" % h)
    crowd = 0
    for a, b in segs:
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        for c2, d2 in segs_other:
            if BC.point_seg_dist(mid, c2, d2) < NEAR_DIST or BC.point_seg_dist(c2, a, b) < NEAR_DIST:
                crowd += 1
    crowd /= float(len(segs))
    return (wln * (1.0 + 0.30 * crowd) + K * cr, ln, wln, cr, crowd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
