# -*- coding: utf-8 -*-
r"""★★★ **“符号本体外形”的唯一实现** ✓（2026-10-09 ✓）

★★ 为什么要有这个文件 ✗（用户 2026-10-09 报的**严重缺陷** ✓）：
  用户原话 ✓：「新文件**地线穿过 U1 了**啊！这完全不可接受啊，请修改。」✓
  实测（`_work/diag_body.py` ✓，逐点量出来的 ✓）：`_work/v76.4_byHand.fzz` 的原理图视图里
  有 **3 段导线真的进了器件本体的肚子里** ✗（清单见 README §六十 ✓）。

★ 旧口径**两处都不对** ✗ —— 这正是"闸门报了 0 违例"的原因 ✓：
  ① **几何取自"占位墨迹"** ✗：旧闸门与渲染器都用 `part_box.shape_bbox()` ✓ ——
     它把 **引脚引线 ✓ ＋ `*terminal` 端子 ✓ ＋ 位号文字 ✓** 全算进去 ✗ ⇒
     · 盒比本体**大一圈** ✗（实测 `U1`：盒 **24.38 × 24.38 mm** vs 本体 **17.78 × 17.78 mm** ✓，
       每边多 **11.7 单位 = 3.30 mm** ✗；`J2`：盒左缘 244.58 vs 本体左缘 **253.58** ⇒ 多 **9 单位 =
       2.54 mm** ✗）；
     · 更糟的是它**认不出圆弧** ✗（`part_box._path_pts()` 把 `A` 命令的参数当坐标读 ✗）
       ⇒ `L1`（线圈，8 段圆弧）的盒**连弧顶都框不住** ✗（盒 y0 = 72.000 vs 真实弧 y0 = **71.562** ✓）。
     ⇒ 一句话 ✓：它是"**墨迹近似**"✗，不是"**该视图实际绘制的符号外形**"✓。
  ② **豁免按"整段"给** ✗：旧判据是"这一段**任一端点**落在某件的脚上（≤0.05 ✓）⇒ **整段**对
     **该件**放行" ✗ ⇒ 只要**起脚**挂在 `U1.VSS` 上 ✓，这一整段就能**横穿 U1 的身体** ✗✗
     （实测一段从 `U1.VSS`(58.58,9.00) 径直钻进本体到 (74.78,9.00) ✓、另一段再从 (74.78,9.00)
     一路穿到 `U1.EPAD`(74.78,-43.20) ✗）。

★ 本文件的**口径**（与用户的要求一字对应 ✓）：
  · 几何**只取该视图（`schematicView`）实际绘制的符号 svg** ✓（`sch_box.part_svg_text` ✓，
    磁盘优先 ✓、包内副本兜底 ✓）；
  · **剔除** `class="pin"` 引线 ✓／`id=connector<N>terminal` 端子 ✓／`id=connector<N>pin` ✓／`<text>` ✓
    —— 它们**不是本体** ✗（是"接线柱与字"✓）；
  · **闭合外形 = 区域**（`rect` ✓／`circle`/`ellipse` ✓／`polygon` ✓／首尾重合的
    `polyline`/`path` ✓／带 `fill` 的 `path` ✓）⇒ 命中判据 = **点在多边形内且离边界 > `eps`** ✓；
  · **开放外形 = 描边**（`line` ✓／开放的 `polyline`/`path` ✓）⇒ 命中判据 = **点离折线 ≤ 半线宽 + `eps`** ✓
    （线圈/锯齿这类"细墨迹"就是这样 ✓ —— 它们**没有"肚子"** ✗，只能按描边判 ✓）；
  · **旋转/镜像** ✓：一律走 `sch_box.A_of()`（= `tf_of(<geometry>) × (k,…)` ✓，`m11/m12/m21/m22`
    全用上 ✓）⇒ 坐标是**该视图的绝对 sketch 坐标** ✓；
  · **唯一豁免 = 位置**（不是"整段" ✗）：命中点若落在**本件某只脚 `pin_r` 单位以内** ⇒ 放行 ✓
    （"从脚上接下"这一段必然贴着自己的脚 ✓ —— 而 `pin_r` 很小 ✓，钻进去 1 mm 以上就算穿 ✗）。
"""

import math
import re
import xml.etree.ElementTree as ET

import part_box as PB
import sch_box as SB

# ── 判据常数（写死 ✓，可复核 ✓）────────────────────────────────────────────
EPS = 0.5          # 穿透容差：进本体**超过** 0.5 单位（= 0.141 mm ✓）才算穿 ✗
                   # ★ 与渲染器既有那条"至少 4 个采样点落在内缩 0.5 的框里"**同量级** ✓
PIN_R = 0.9        # 唯一豁免半径：命中点离本件的脚 ≤ 0.9 单位（= 0.254 mm ✓）⇒ 放行 ✓
ARC_SEGS = 16      # `A` 弧展平段数 ✓


def _tag(e):
    return e.tag.split("}")[-1]


def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


_NUM_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _is_skip(el):
    """这个元素**不画**、也不进本体外形吗 ✓

    ★★ 2026-10-09 ✓ **判据改正** ✗（渲染器 ④b 当场点出来的 ✓）：原来把 `class="pin"` 的**引脚引线**
      一起跳过了 ✗ ⇒ 本体只剩"方块" ✗ ⇒ `U1` 引脚那一带的**3.3 mm 走廊**变成可走 ✗
      ⇒ 实测产出一根 `(64.5,9.0)→(64.5,-62.6)` 的竖线**横穿 U1 那一排引脚引线** ✗
      （渲染器用旧盒判：**穿体 1 段 ✗**）—— 用户看的是**画出来的东西** ✓，引脚引线**画出来了** ✓
      ⇒ 它就是符号外形的一部分 ✓（本仓规矩：判据要跟画出来的东西同一个 ✓）。
    ★ 仍然跳过 ✓：`<text>`（位号/脚名 ✓ —— 有**另一条**判据管"字被划掉" ✓）、
      `connector<N>terminal`（0.0001 的**零尺寸锚点** ✓，不是墨迹 ✓）。
    """
    eid = el.get("id") or ""
    return (_tag(el) == "text") or bool(re.match(r"^connector\d+terminal$", eid))


# ── SVG path（`d`）→ 折线 ✓（M/L/H/V/C/S/Q/T/A/Z ✓；`A` 真展平 ✓）───────────
_CMD_N = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def _path_subpaths(d):
    """返回 `[(pts, closed)]` ✓。★ `A` 真展平 ✓（旧实现把它的参数当坐标读 ⇒ 弧顶丢了 ✗）"""
    if not d:
        return []
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[+-]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)
    out, cur, start, pos, prev_c = [], [], None, (0.0, 0.0), None
    cmd, i = None, 0
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
        if cmd is None:
            i += 1
            continue
        c = cmd.upper()
        rel = cmd.islower()
        k = _CMD_N.get(c)
        if k is None or i + k > len(toks):
            i += 1
            continue
        v = [_num(toks[i + j]) for j in range(k)]
        i += k
        if c == "M":
            if len(cur) >= 2:
                out.append((cur, False))
            px = pos[0] + v[0] if rel else v[0]
            py = pos[1] + v[1] if rel else v[1]
            pos, start, cur, prev_c = (px, py), (px, py), [(px, py)], None
            cmd = "l" if rel else "L"
        elif c == "L":
            px = pos[0] + v[0] if rel else v[0]
            py = pos[1] + v[1] if rel else v[1]
            pos, prev_c = (px, py), None
            cur.append(pos)
        elif c == "H":
            px = pos[0] + v[0] if rel else v[0]
            pos, prev_c = (px, pos[1]), None
            cur.append(pos)
        elif c == "V":
            py = pos[1] + v[0] if rel else v[0]
            pos, prev_c = (pos[0], py), None
            cur.append(pos)
        elif c in ("C", "S", "Q", "T"):
            if rel:
                v = [v[j] + (pos[0] if j % 2 == 0 else pos[1]) for j in range(k)]
            if c == "C":
                p1, p2, p3 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            elif c == "S":
                p1 = (2 * pos[0] - prev_c[0], 2 * pos[1] - prev_c[1]) if prev_c else pos
                p2, p3 = (v[0], v[1]), (v[2], v[3])
            elif c == "Q":
                p1, p2, p3 = (v[0], v[1]), (v[0], v[1]), (v[2], v[3])
            else:
                p1 = (2 * pos[0] - prev_c[0], 2 * pos[1] - prev_c[1]) if prev_c else pos
                p2, p3 = p1, (v[0], v[1])
            b = pos
            for s in range(1, 9):
                u = s / 8.0
                mu = 1 - u
                cur.append((mu ** 3 * b[0] + 3 * mu * mu * u * p1[0] + 3 * mu * u * u * p2[0]
                            + u ** 3 * p3[0],
                            mu ** 3 * b[1] + 3 * mu * mu * u * p1[1] + 3 * mu * u * u * p2[1]
                            + u ** 3 * p3[1]))
            pos, prev_c = p3, p2
        elif c == "A":
            rx, ry, _rot, laf, sf, x2, y2 = v
            if rel:
                x2, y2 = pos[0] + x2, pos[1] + y2
            cur.extend(_arc_pts(pos, rx, ry, laf, sf, (x2, y2)))
            pos, prev_c = (x2, y2), None
        else:                                   # Z
            if start is not None:
                cur.append(start)
                out.append((cur, True))
                cur = []
                pos = start
            prev_c = None
    if len(cur) >= 2:
        out.append((cur, False))
    return out


def _arc_pts(p0, rx, ry, laf, sf, p1):
    """`A` 弧 → 折线 ✓（端点参数化 ✓，标准实现 ✓）"""
    rx, ry = abs(rx), abs(ry)
    if rx < 1e-12 or ry < 1e-12 or p0 == p1:
        return [p1]
    x1p, y1p = (p0[0] - p1[0]) / 2.0, (p0[1] - p1[1]) / 2.0
    lam = x1p * x1p / (rx * rx) + y1p * y1p / (ry * ry)
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den > 1e-18 else 0.0
    if laf == sf:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = cxp + (p0[0] + p1[0]) / 2.0, cyp + (p0[1] + p1[1]) / 2.0

    def ang(ux, uy, vx, vy):
        d = (ux * vx + uy * vy) / (math.hypot(ux, uy) * math.hypot(vx, vy) + 1e-18)
        a = math.acos(max(-1.0, min(1.0, d)))
        return -a if (ux * vy - uy * vx) < 0 else a

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    th1 = ang(1, 0, ux, uy)
    dth = ang(ux, uy, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if sf == 0 and dth > 0:
        dth -= 2 * math.pi
    elif sf == 1 and dth < 0:
        dth += 2 * math.pi
    return [(cx + rx * math.cos(th1 + dth * k / ARC_SEGS),
             cy + ry * math.sin(th1 + dth * k / ARC_SEGS))
            for k in range(1, ARC_SEGS + 1)]


# ── 主入口 ────────────────────────────────────────────────────────────────
def shapes_of(svg_text, g_el):
    """符号 svg → `[(kind, pts, w)]` ✓（**绝对 sketch 坐标** ✓；kind ∈ {`region`,`stroke`} ✓）"""
    A = SB.A_of(svg_text, g_el)
    if A is None:
        return []
    k, _org, _note = SB.scale_of(svg_text)
    if k is None:
        return []
    ax, ay = _num(g_el.get("x")), _num(g_el.get("y"))
    try:
        root = ET.fromstring(svg_text)
    except Exception:
        return []
    out = []

    def put(pts, w_user, closed):
        if len(pts) < 2:
            return
        abs_pts = []
        for (x, y) in pts:
            abs_pts.append((ax + (A[0] * x + A[2] * y + A[4]),
                            ay + (A[1] * x + A[3] * y + A[5])))
        out.append(("region" if closed else "stroke", abs_pts, w_user * k))

    def emit(el, m):
        t = _tag(el)
        wid = _num(el.get("stroke-width"), 1.0)
        fill = (el.get("fill") or "").lower()
        ap = lambda x, y: PB.apply(m, x, y)              # noqa: E731
        if t == "rect":
            x, y = _num(el.get("x")), _num(el.get("y"))
            w, h = _num(el.get("width")), _num(el.get("height"))
            put([ap(x, y), ap(x + w, y), ap(x + w, y + h), ap(x, y + h), ap(x, y)], wid, True)
        elif t == "circle":
            cx, cy, r = _num(el.get("cx")), _num(el.get("cy")), _num(el.get("r"))
            put([ap(cx + r * math.cos(2 * math.pi * i / 24), cy + r * math.sin(2 * math.pi * i / 24))
                 for i in range(25)], wid, True)
        elif t == "ellipse":
            cx, cy = _num(el.get("cx")), _num(el.get("cy"))
            rx, ry = _num(el.get("rx")), _num(el.get("ry"))
            put([ap(cx + rx * math.cos(2 * math.pi * i / 24), cy + ry * math.sin(2 * math.pi * i / 24))
                 for i in range(25)], wid, True)
        elif t == "line":
            put([ap(_num(el.get("x1")), _num(el.get("y1"))),
                 ap(_num(el.get("x2")), _num(el.get("y2")))], wid, False)
        elif t in ("polyline", "polygon"):
            v = [_num(s) for s in _NUM_RE.findall(el.get("points") or "")]
            pts = [ap(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
            closed = (t == "polygon"
                      or (len(pts) > 2 and math.dist(pts[0], pts[-1]) <= 1e-6))
            put(pts, wid, closed)
        elif t == "path":
            for pts, cl in _path_subpaths(el.get("d")):
                put([ap(x, y) for (x, y) in pts], wid, bool(cl or fill not in ("", "none")))

    def walk(el, m):
        if _tag(el) == "defs":
            return
        t = el.get("transform")
        mc = PB.mul(m, PB.parse_tf(t)) if t else m
        if _tag(el) != "text" and not _is_skip(el):
            emit(el, mc)
        for c in el:
            walk(c, mc)

    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    return out


def bbox(shapes):
    xs, ys = [], []
    for _k, pts, _w in shapes:
        for x, y in pts:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _emit_into(out, el, m, wscale):
    """把**已经摆好位**的 svg 片段里的绘制元素转成外形段 ✓（`wscale` = 该处的累积缩放 ✓）"""
    t = _tag(el)
    wid = _num(el.get("stroke-width"), 1.0) * wscale
    fill = (el.get("fill") or "").lower()
    ap = lambda x, y: PB.apply(m, x, y)                  # noqa: E731

    def put(pts, closed):
        if len(pts) >= 2:
            out.append(("region" if closed else "stroke", pts, wid))

    if t == "rect":
        x, y = _num(el.get("x")), _num(el.get("y"))
        w, h = _num(el.get("width")), _num(el.get("height"))
        put([ap(x, y), ap(x + w, y), ap(x + w, y + h), ap(x, y + h), ap(x, y)], True)
    elif t == "circle":
        cx, cy, r = _num(el.get("cx")), _num(el.get("cy")), _num(el.get("r"))
        put([ap(cx + r * math.cos(2 * math.pi * i / 24), cy + r * math.sin(2 * math.pi * i / 24))
             for i in range(25)], True)
    elif t == "ellipse":
        cx, cy = _num(el.get("cx")), _num(el.get("cy"))
        rx, ry = _num(el.get("rx")), _num(el.get("ry"))
        put([ap(cx + rx * math.cos(2 * math.pi * i / 24), cy + ry * math.sin(2 * math.pi * i / 24))
             for i in range(25)], True)
    elif t == "line":
        put([ap(_num(el.get("x1")), _num(el.get("y1"))),
             ap(_num(el.get("x2")), _num(el.get("y2")))], False)
    elif t in ("polyline", "polygon"):
        v = [_num(s) for s in _NUM_RE.findall(el.get("points") or "")]
        pts = [ap(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
        put(pts, t == "polygon" or (len(pts) > 2 and math.dist(pts[0], pts[-1]) <= 1e-6))
    elif t == "path":
        for pts, cl in _path_subpaths(el.get("d")):
            put([ap(x, y) for (x, y) in pts], bool(cl or fill not in ("", "none")))


def shapes_of_markup(markup):
    """★ **已经摆好位**的 svg 片段（如 `sch_net.ground_art()` ✓）→ 外形段表 ✓

    ★ 与 `shapes_of()` 的区别 ✗：这里的变换**已经含**平移/缩放 ✓（片段自带 `transform` ✓）
      ⇒ 不再乘 `<geometry>` 那套仿射 ✓，但**线宽要按这里的累积缩放**换算 ✓
      （接地符号的素材在**内层单位** ✓，靠 `scale(1.25)` 换到 sketch ✓）。
    """
    if not markup:
        return []
    try:
        el = ET.fromstring(markup)
    except Exception:
        return []
    out = []

    def walk(e, m):
        if _tag(e) == "defs":
            return
        t = e.get("transform")
        mc = PB.mul(m, PB.parse_tf(t)) if t else m
        # ★ 累积缩放 = sqrt(|det|) ✓（`shape_bbox` 那边不认圆弧 ✗，这里按矩阵来 ✓）
        det = mc[0] * mc[3] - mc[1] * mc[2]
        ws = math.sqrt(abs(det)) if abs(det) > 1e-18 else 1.0
        if _tag(e) != "text" and not _is_skip(e):
            _emit_into(out, e, mc, ws)
        for c in e:
            walk(c, mc)

    walk(el, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    return out


def poly_region(pts):
    """一串**已经摆好位**的顶点 ⇒ 一个闭合区域 ✓（网标签的旗标就是这样 ✓）"""
    if not pts or len(pts) < 3:
        return []
    return [("region", [(p[0], p[1]) for p in pts] + [(pts[0][0], pts[0][1])], 0.0)]


def _pt_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xt = x0 + (y - y0) * (x1 - x0) / (y1 - y0 + 1e-300)
            if x < xt:
                inside = not inside
    return inside


def _d_seg(pt, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    if L2 <= 1e-18:
        return math.dist(pt, a)
    t = max(0.0, min(1.0, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / L2))
    return math.dist(pt, (ax + t * dx, ay + t * dy))


def _poly_dist(pt, pts, closed):
    n = len(pts)
    m = n if closed else n - 1
    return min(_d_seg(pt, pts[i], pts[(i + 1) % n]) for i in range(m))


def _pt_hit(pt, shape, eps):
    kind, pts, w = shape
    if kind == "region":
        if not _pt_in_poly(pt, pts):
            return False
        return _poly_dist(pt, pts, True) > eps
    return _poly_dist(pt, pts, False) <= w / 2.0 + eps


_PREP = {}


def _prep(shapes):
    got = _PREP.get(id(shapes))
    if got is not None and got[0] is shapes:
        return got[1]
    rows = []
    for sh in shapes:
        bb = bbox([sh])
        pad = EPS + (sh[2] / 2.0 if sh[0] == "stroke" else 0.0) + 1.0
        rows.append((sh, bb, pad))
    _PREP[id(shapes)] = (shapes, rows)
    return rows


def seg_hit(p, q, shapes, pins=(), pin_r=PIN_R, eps=EPS, step=None):
    """★ **一段导线** 是否**穿进**这些外形 ✓ —— 真穿才算 ✗（`eps` 容差内不算 ✓）

    ★ 豁免**唯一**且**按位置** ✓：命中点离 `pins`（**本件自己的脚** ✓）任一 ≤ `pin_r` ⇒ 放行 ✓。
      ✗ **不是**"整段豁免" ✗ —— 那正是用户这轮报的毛病的根 ✓（见文件头 ✓）。
    ★★ `pin_r` 会被**自动抬到**「本件最粗那条描边的半宽 ＋ `eps`」✓（2026-10-09 ✓）——
      ✗ 不然会出现**刀锋假阳性** ✗：一根线从脚上**垂直**往外走时，它在**自己那条引脚引线**
      的墨迹里要走 `半线宽 + eps` 那么远才脱离 ✓ ⇒ 豁免半径比它小就会误报 ✗（L1 实测就差 0.038 ✓）。
    """
    if not shapes:
        return False
    rows = _prep(shapes)
    if pins and pin_r > 0:
        pin_r = max(pin_r, max((sh[2] / 2.0 for sh in shapes), default=0.0) + eps)
    L = math.dist(p, q)
    step = step or max(eps, 0.25)
    n = max(2, int(L / step) + 1)
    for i in range(n + 1):
        t = i / n
        pt = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        if pins and pin_r > 0 and any(math.dist(pt, pp) <= pin_r for pp in pins):
            continue
        for sh, bb, pad in rows:
            if not (bb[0] - pad <= pt[0] <= bb[2] + pad
                    and bb[1] - pad <= pt[1] <= bb[3] + pad):
                continue
            if _pt_hit(pt, sh, eps):
                return True
    return False


def label_region(box):
    """core 件（网标签/接地符号）没有可读 svg 文本 ✗ ⇒ 用**它自己的本体框**当区域 ✓（一处实现 ✓）"""
    if not box:
        return []
    x0, y0, x1, y1 = box
    return [("region", [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], 0.0)]
