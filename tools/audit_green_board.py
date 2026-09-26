"""审计（只读 ✓）：全仓"绿色转接板"元件，检查**板边会不会压在孔行/孔列线上** ✓。

判据（部件级、与摆放无关 ✓）：
  面包板孔距 = 2.54mm = **9 草图单位** ✓（1 草图单位 = 1/90 in ✓）
  ⇒ 绿板的宽/高若是 9 的**整数倍** ✗ ⇒ 不管摆在哪一格，板边都**正好落在孔心连线**上 ✗
    ⇒ 那一排孔被压掉一半（插不进线 ✗）—— 违反用户定的"转接板不应影响它之外的孔" ✓
  ⇒ 期望值 = **9 的整数倍 + 4.5**（半格 ✓）⇒ 板边落在两排孔**正中** ✓，离最近孔心 1.27mm ✓

用法：py -3.13 audit_green_board.py [仓根]
"""
import sys
import os
import glob
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import part_box as pb          # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"f:\git\fritzing-parts-langhua"
UNIT_MM = 25.4 / 90.0
PITCH = 9.0                    # 草图单位


def tag(e):
    t = e.tag
    return t.rsplit("}", 1)[-1] if "}" in t else t


def green_bbox(path):
    """整幅 svg 里 fill=#00aa44 的图元合并包围盒（含 transform ✓），单位 = svg 内部单位 ✓"""
    root = ET.parse(path).getroot()
    boxes = []

    def walk(el, m):
        m2 = pb.mul(m, pb.parse_tf(el.get("transform"))) if el.get("transform") else m
        fill = (el.get("fill") or "") or ((el.get("style") or "").split("fill:")[-1].split(";")[0]
                                          if "fill:" in (el.get("style") or "") else "")
        if tag(el) in ("rect", "path", "polygon", "polyline", "circle", "ellipse") \
                and fill.strip().lower() == "#00aa44":
            b = pb.shape_bbox(el)
            if b is not None:
                p0, p1 = pb.apply(m2, b[0], b[1]), pb.apply(m2, b[2], b[3])
                boxes.append((min(p0[0], p1[0]), min(p0[1], p1[1]),
                              max(p0[0], p1[0]), max(p0[1], p1[1])))
        for c in list(el):
            walk(c, m2)
    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def pad_lines(path):
    """元件自己的**针脚行/列**位置（草图单位 ✓）—— 拿 `connectorNpin`/`leg` 的**中心** ✓
    （中心 = 插进面包板孔的那个点 ✓）。★ 判据只能比它 ✓：板边相对针脚的偏移才是相位 ✓；
    比“板宽能不能被 2.54mm 整除”是**错的** ✗（针脚本来就不一定落在板的整数格上 ✓）。
    """
    root = ET.parse(path).getroot()
    vb = [float(x) for x in (root.get("viewBox") or "").split()]
    cm = pb.canvas_mm(root.attrib)
    if not cm[0] or len(vb) != 4 or not vb[2]:
        return [], 0.0
    k = (cm[0] / 25.4 * 90.0) / vb[2]
    xs, ys = [], []
    for el in root.iter():
        eid = el.get("id") or ""
        if not eid.startswith("connector") or not ("pin" in eid or "leg" in eid):
            continue
        b = pb.shape_bbox(el)
        if b is None:
            continue
        m = pb.tf_of(el)
        p0, p1 = pb.apply(m, b[0], b[1]), pb.apply(m, b[2], b[3])
        xs.append((min(p0[0], p1[0]) + max(p0[0], p1[0])) / 2.0 * k)
        ys.append((min(p0[1], p1[1]) + max(p0[1], p1[1])) / 2.0 * k)
    return sorted(set(round(v, 3) for v in xs)), sorted(set(round(v, 3) for v in ys)), k


rows = []
for d in sorted(glob.glob(os.path.join(ROOT, "svg", "*"))):
    for f in sorted(glob.glob(os.path.join(d, "*breadboard*.svg"))):
        if "_byHand" in os.path.basename(f):
            continue
        gb = green_bbox(f)
        if gb is None:
            continue
        xs, ys, k = pad_lines(f)
        if not xs or not ys:
            continue
        cm_x, cm_y = gb[0] * k, gb[1] * k
        w, h = (gb[2] - gb[0]) * k, (gb[3] - gb[1]) * k
        rows.append((os.path.basename(d), xs, ys, k, gb, cm_x, cm_y, w, h))

print("%-22s %-9s %-9s %s" % ("部件", "板宽(草图u)", "板高(草图u)", "判定（板边相对**自己针脚**的相位 ✓；4.5 = 半格 = 好 ✓）"))
bad, partial = [], []
for name, xs, ys, k, gb, x0, y0, w, h in rows:
    def phase(edge, lines):
        """edge（草图单位）到最近针脚线的距离 mod 9 ✓"""
        d = min(abs(edge - L) for L in lines) % PITCH
        return min(d, PITCH - d)
    pa_l, pa_r = phase(x0, xs), phase(x0 + w, xs)
    pa_t, pa_b = phase(y0, ys), phase(y0 + h, ys)
    msg = []
    for tagv, v in (("左", pa_l), ("右", pa_r), ("上", pa_t), ("下", pa_b)):
        if abs(v) < 0.05:            # ★ 正好落在孔列/行上 ✗
            msg.append("%s边压孔线 ✗" % tagv)
        elif abs(v - 4.5) < 0.05:    # ★ 半格 ✓ 最好 ✓
            continue
        else:
            msg.append("%s边偏 %.2f 单位（≠半格 ✗）" % (tagv, v))
    if not msg:
        msg = ["OK ✓"]
    else:
        (bad if any("压孔线" in m for m in msg) else partial).append(name)
    print("%-22s %-9.3f %-9.3f %s（相位 左%.2f 右%.2f 上%.2f 下%.2f）"
          % (name, w, h, "；".join(msg), pa_l, pa_r, pa_t, pa_b))
print("\n共 %d 个绿板元件：**板边压在孔线上**（直接违规 ✗）的 %d 个：%s"
      % (len(rows), len(bad), ", ".join(bad)))
if partial:
    print("**相位不对但没压线**（同样要修 ✗）的 %d 个：%s" % (len(partial), ", ".join(partial)))
