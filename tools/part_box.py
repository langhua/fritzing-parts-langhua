# -*- coding: utf-8 -*-
r"""零件"本体"在 sketch 里的包围盒（2026-09-26 定稿 ✓）

为什么要它：判"哪些面包板孔被元件挡住"要用**本体** ——
  · 只按 svg 的 width/height（= 画布）会**高估**：画布常带留白 ✗
    （反例：NFC 线圈画布 24×24mm，实际绿色板只画了 20×20mm ⇒ 多遮了一整行孔 ✗）
  · 直接数几何坐标也不行 ✗：`<path d>` 常带**相对命令**、坐标又在 `<g transform>` 里 ✓

本模块干三件事：
  ① `shape_bbox(svg_root)`：把**画出来**的东西（含嵌套 transform ✓）的包围盒算出来，
     单位 = svg 自己的**用户单位**；看不出来/不可信 ⇒ 返回 None ✓（调用方退回画布 ✓）
  ② `to_sketch(box, attrs)`：用户单位 → sketch 单位（Fritzing 惯例：把 svg 的
     width/height 当物理尺寸，viewBox 当坐标系 ✓；1mm = 3.5433 sketch 单位 ✓）
  ③ `place(loc, m, box)`：再按实例的 `<transform>` 矩阵搬到 sketch 绝对坐标 ✓
     —— 零件摆放 = `sketch = loc + M·(局部 sketch 单位) + (m31,m32)` ✓

用法：
    import part_box as pb
    box = pb.body_box(svg_path)              # (x0,y0,x1,y1) sketch 单位（相对画布原点）
    rect = pb.place(loc, tf_matrix, box)     # sketch 绝对矩形
"""
import re
import xml.etree.ElementTree as ET

MM = 3.5433                     # 1 mm = 3.5433 sketch 单位 ✓（1/90 in ✓）
MIL_UNITS = 90.0 / 1000.0       # 1 mil = 1/1000 in ✓、sketch 单位 = 1/90 in ✓ ⇒ ×0.09 ✓

# ★★ 过孔 / 安装孔：`<geometry>` 是 **svg 画布原点**，不是铜的心 ✗（2026-10-01 定案 ✓）
#   来源：用户导出的 `hardware/pixel/pixel-pcb-v48_图示.svg`（权威 ✓）里每个过孔是
#     `<g transform="translate(44.6824,47.1388)"><g id="copper0">
#        <circle cx="2.45039" cy="2.45039" r="0.637795" stroke="#f9a435"/></g></g>`
#   ⇒ `translate` 换算后 **正好等于** 模型算出的过孔坐标 ✓（摆放一致 ✓）
#     铜却画在**局部** `(2.45039, 2.45039)`（画布单位 = 1/72 in）⇒ 真铜心 = geometry + 偏移 ✓
#   同样地：安装孔局部铜心 `(4.71811, 4.71811)` ✓（= 1.66444 mm ✓）。
#   ✗ 后果（踩过 ✓）：把 geometry 当铜心 ⇒ 过孔/孔**整体**差 0.86 / 1.66 mm ✗ ⇒
#     “过孔压别的焊盘”这类硬闸门**测在错点上** ⇒ 真短接也不报警 ✗。
#
# ★★★ 2026-10-02 修 ✗：**这个偏移不是一个常数** ✗ —— 它 = **铜半径 + 画布留白** ✓
#   · 画布留白 = **2 sketch 单位** = **0.56444 mm** ✓（两侧各一份 ⇒ 画布 = 铜外径 + 4 单位 ✓）
#   · ⇒ 偏移(mm) = `孔径/2 + 环宽 + 0.56444` ✓
#   三个**互相独立**的实测点全部逐位对上 ✓：
#     ① 默认过孔 `0.3mm,0.15mm` ⇒ 0.30 + 0.56444 = **0.86444** ✓（= 旧常数 ✓，所以旧文件没露 ✓）
#     ② 安装孔 `2.2mm,0.0mm` ⇒ 1.10 + 0.56444 = **1.66444** ✓
#        （导出 `4.71811` pt ÷ 72 × 25.4 = 1.664444 ✓ ⇒ ✗ 旧常数 `1.66454` 是**转录错**
#          —— 第 4/5 位写反了 ✗，差 1e-4 mm ✓ 已改对 ✓）
#     ③ ★ 用户手加的 `0.4mm,0.3mm` 过孔（外径 1.00）⇒ 0.50 + 0.56444 = **1.06444** ✓
#        ★ 这一条**不靠我的导出读数** ✓：是**用户在 Fritzing 里把线端拖到过孔上**之后
#          文件里存的端点 ✓ —— `pixel-pcb-v57_2_byHand.fzz` 的 `Wire90014056` 端 =
#          (52.491, 24.000) mm，而该过孔 `<geometry>` = (182.222, 81.2693) 单位 =
#          (51.427, 22.936) mm ⇒ 差 **(1.064, 1.064) mm** ✓；
#          另一实例 `Wire90014068` ↔ 过孔 #10 差**同样是 (1.064, 1.064)** ✓
#          （两个实例 × 两个轴 = 4 个独立读数全中 ✓）。
#   ✗ 旧口径（单一常数 0.86444）套到**别的尺寸**的过孔上 ⇒ 铜心偏 `(外径−0.60)/2` mm ✗
#     ⇒ 用户那颗 1.00 mm 过孔被算偏 **0.2 mm/轴（0.283 mm 斜）** ✗ ⇒ 校验器把它报成
#     “孤立过孔 / 悬空端点” ✗，而 **Fritzing 里明明是通的** ✗
#     （用户 2026-10-02 当场指出：「我在 Fritzing 里点击线上节点，显示是通的」✓；
#       文件里也确实写了 `<connect … modelIndex="90014051" layer="copper0"/>` ✓）
#     ⇒ 教训 ✓：**尺寸相关的公式，别拿一个尺寸量出的常数当通则** ✗
#       （与 AGENTS.md §0 第 7 条「`_rev_N` 上量出来的数字只属于那个变体」是同一条 ✓）。
CANVAS_MARGIN_MM = 0.56444      # 画布两侧留白 ✓ = 2 sketch 单位 ✓
VIA_DRAW_OFF_MM = 0.86444       # = ring_off_mm(0.3, 0.15) ✓（默认过孔 ✓）
HOLE_DRAW_OFF_MM = 1.66444      # = ring_off_mm(2.2, 0.0) ✓（核心安装孔 ✓）


def ring_off_mm(hole_mm, ring_mm=None):
    """圆环型核心件（过孔 / 安装孔）**画图原点 → 铜心** 的偏移 ✓（mm ✓）

    ★★ **唯一实现** ✗：`pcb_check`（过孔 ✓）/ `pcb_pads.holes`（安装孔 ✓）/ `render_pcb` 都调它 ✓
    ★ 判据 = **铜半径 + 画布留白** ✓（`CANVAS_MARGIN_MM` ✓）—— 见上面三个实测点 ✓。
    ★ `hole size` 的口径 = **`<孔径>,<环宽>`** ✓（过孔与核心孔件**同口径** ✓，见 F17 ✓）。
    """
    return float(hole_mm) / 2.0 + float(ring_mm or 0.0) + CANVAS_MARGIN_MM


def draw_off_units(kind="via", size_mm=None):
    """把上面那个 mm 偏移换成 **sketch 单位** ✓（给 pcb_check / pcb_route 用 ✓）

    ★ `size_mm = (孔径, 环宽)` ✓ —— ★★ **不是默认尺寸的过孔/孔就必须给** ✗，
      不给只能退回默认常数 ✓（默认尺寸与公式**逐位相同** ✓ ⇒ 旧文件不会漂 ✓）。
    ★ 只留这一份 ✗：`render_pcb.py` 里曾写死 `HOLE_DRAW_OFF_MM = 1.665` ✗、
      `pcb_check` 完全没加 ✗ ⇒ 三处口径不一致 ✗（典型的“两套实现找不到原因” ✗）。
    """
    sz = tuple(size_mm) if size_mm else None
    if sz and sz[0] is not None:
        mm = ring_off_mm(sz[0], sz[1] if len(sz) > 1 else None)
    else:
        mm = HOLE_DRAW_OFF_MM if str(kind).startswith("hole") else VIA_DRAW_OFF_MM
    return mm / (25.4 / 90.0)


def mils_to_units(mils, default=None):
    """`wireExtras@mils` ⇒ **sketch 单位** ✓（线宽/丝印宽度都用它 ✓）

    ★ 公式**只留这一份** ✗：`render_sch.py` 原来就地写着 `mils*90/1000` ✗ ⇒ 改成调这里 ✓
      （两处各写一份 ⇒ 改一处忘一处 ✗）。
    ★ 量过的锚点 ✓：`12 mil` ⇒ 1.08 sketch 单位 = **0.3048 mm** ✓
      （正是 `pixel-pcb-v47.fzz` 全板 131 根走线的宽度 ✓）；
      `22.2222 mil` ⇒ 2.0 单位 = **0.5645 mm** ✓（面包板导线标准宽 ✓）；
      `9.7222 mil` ⇒ 0.875 单位 = **0.247 mm** ✓（原理图导线 ✓）。
    """
    if mils in (None, ""):
        return default
    return float(mils) * MIL_UNITS


def tag(e):
    return e.tag.split("}")[-1]


# ── 2×3 矩阵（SVG 约定：[a,b,c,d,e,f] = (m11,m12,m21,m22,m31,m32) ✓）───────────
def mul(m, n):
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def parse_tf(s):
    """解析 transform 串（translate/scale/matrix/rotate ✓）→ 2×3 矩阵"""
    import math
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, arg in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        v = [float(x) for x in re.split(r"[,\s]+", arg.strip()) if x]
        if name == "translate":
            m = mul(m, (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0))
        elif name == "scale":
            m = mul(m, (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0))
        elif name == "matrix":
            m = mul(m, tuple(v[:6]))
        elif name == "rotate":
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:                        # rotate(a cx cy) ✓
                t = mul(mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
            m = mul(m, t)
    return m


def apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def tf_of(el):
    """实例 geometry 里的 <transform m11…m32> ✓；没有 ⇒ 单位阵 ✓"""
    t = next((c for c in el if tag(c) == "transform"), None)
    if t is None:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    n = lambda k, d: float(t.get(k) or d)          # noqa: E731
    return (n("m11", 1), n("m12", 0), n("m21", 0), n("m22", 1), n("m31", 0), n("m32", 0))


def _nums(s):
    return [float(v) for v in re.findall(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?", s or "")]


def _path_pts(d):
    """把 path 的**坐标点**取出来（只认**参数个数固定**的绝对命令 ✓）
       相对命令（小写 m/l/h/v 等）坐标不是绝对坐标 ⇒ 整条跳过 ✓（宁可少算，由调用方兜底 ✓）"""
    if not d:
        return None
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?", d)
    out, i, cur = [], 0, None
    narg = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
    while i < len(toks):
        c = toks[i]
        if not c.isalpha():
            return None                        # 命令之间夹了裸数字 ⇒ 解析不了 ⇒ 放弃 ✓
        if c not in narg:
            return None                        # 出现相对命令 ⇒ 放弃 ✓
        i += 1
        if c == "Z":
            continue
        while i + narg[c] <= len(toks) and not toks[i].isalpha():
            v = [float(x) for x in toks[i:i + narg[c]]]
            i += narg[c]
            v = list(v)
            if c == "H":
                cur = (v[0], cur[1] if cur else 0.0)
            elif c == "V":
                cur = (cur[0] if cur else 0.0, v[0])
            elif c == "A":
                cur = (v[5], v[6])
            else:
                for k in range(0, len(v) - 1, 2):
                    out.append((v[k], v[k + 1]))
                cur = (v[-2], v[-1])
            if c in ("H", "V", "A"):
                out.append(cur)
            if i < len(toks) and toks[i].isalpha():
                break
            if i + narg[c] > len(toks):
                break
    return out or None


def shape_bbox(root):
    """画出来的一切的包围盒（**用户单位**、含嵌套 transform ✓）；不可信 ⇒ None ✓"""
    xs, ys = [], []

    def walk(el, m):
        t = el.get("transform")
        m = mul(m, parse_tf(t)) if t else m
        if tag(el) == "defs":
            return
        for c in el:
            walk(c, m)

        def add(x, y):
            px, py = apply(m, x, y)
            xs.append(px)
            ys.append(py)

        t2 = tag(el)
        try:
            if t2 == "rect":
                x, y = float(el.get("x") or 0), float(el.get("y") or 0)
                w, h = float(el.get("width") or 0), float(el.get("height") or 0)
                for dx in (0, w):
                    for dy in (0, h):
                        add(x + dx, y + dy)
            elif t2 == "circle":
                cx, cy, r = (float(el.get(k) or 0) for k in ("cx", "cy", "r"))
                for dx, dy in ((-r, -r), (r, r), (r, -r), (-r, r)):
                    add(cx + dx, cy + dy)
            elif t2 == "ellipse":
                cx, cy = float(el.get("cx") or 0), float(el.get("cy") or 0)
                rx, ry = float(el.get("rx") or 0), float(el.get("ry") or 0)
                for dx, dy in ((-rx, -ry), (rx, ry), (rx, -ry), (-rx, ry)):
                    add(cx + dx, cy + dy)
            elif t2 == "line":
                add(float(el.get("x1") or 0), float(el.get("y1") or 0))
                add(float(el.get("x2") or 0), float(el.get("y2") or 0))
            elif t2 in ("polyline", "polygon"):
                v = _nums(el.get("points"))
                for k in range(0, len(v) - 1, 2):
                    add(v[k], v[k + 1])
            elif t2 == "path":
                for p in (_path_pts(el.get("d")) or []):
                    add(p[0], p[1])
            elif t2 == "text":
                add(float(el.get("x") or 0), float(el.get("y") or 0))
        except (TypeError, ValueError):
            pass
    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    if len(xs) < 2:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def pin_points(root):
    """`id="connector<N>pin"` 的**参考点**（根用户单位、走完祖先 transform ✓）

    ⇒ `({id: (x, y)}, 认不出的清单 ✓)`；认不出**要点名报出** ✓（不静默跳过 ✗）。

    ★★ 为什么必须走 transform 链 ✓（2026-09-27 实测 ✓，我为此连错三次 ✗）：
      `WS2812B_1010` 的 4 个焊盘各在一个 `translate(…, …)` 组里 ✓：
        · 组 translate：34.035 → 234.035 ⇒ 差 **200**（**假的** ✗）；
        · 组内 `<rect x>`：−31.584 → −217.184 ⇒ 差 **−186** ✓；
        ⇒ **两个大数互抵**，真脚距只有 **14.401** ✓（21.600 在 y ✓）。
      只看元素自己的 x/y ⇒ 会拿到 200 这种假值 ✗；**相邻两个数字之差 ≠ 几何** ✗。
    """
    got, legs, bad = {}, {}, []

    def ref(el):
        t = tag(el)
        if t in ("circle", "ellipse"):
            return (float(el.get("cx") or 0), float(el.get("cy") or 0))
        if t == "rect":
            return (float(el.get("x") or 0) + float(el.get("width") or 0) / 2.0,
                    float(el.get("y") or 0) + float(el.get("height") or 0) / 2.0)
        if t == "line":
            return ((float(el.get("x1") or 0) + float(el.get("x2") or 0)) / 2.0,
                    (float(el.get("y1") or 0) + float(el.get("y2") or 0)) / 2.0)
        return None

    def ends(el):
        """`<line>` 的两端 ✓（腿只认 line ✓）"""
        if tag(el) != "line":
            return None
        return ((float(el.get("x1") or 0), float(el.get("y1") or 0)),
                (float(el.get("x2") or 0), float(el.get("y2") or 0)))

    def walk(el, m):
        if tag(el) == "defs":
            return
        for c in el:
            if tag(c) == "svg":                 # 嵌套视口没处理 ⇒ 明说 ✓（别当没事 ✗）
                bad.append("<嵌套 <svg> 视口（未处理 ✗）>")
                continue
            t = c.get("transform")
            mc = mul(m, parse_tf(t)) if t else m
            eid = c.get("id") or ""
            if re.match(r"^connector\d+pin$", eid):
                p = ref(c)
                if p is None:
                    bad.append("%s=<%s>（认不出参考点 ✗）" % (eid, tag(c)))
                else:
                    got[eid] = apply(mc, p[0], p[1])
            ml = re.match(r"^(connector\d+)leg$", eid)
            if ml:
                e2 = ends(c)
                if e2 is None:
                    bad.append("%s=<%s>（腿不是 <line> ✗）" % (eid, tag(c)))
                else:
                    legs[ml.group(1)] = (apply(mc, e2[0][0], e2[0][1]),
                                         apply(mc, e2[1][0], e2[1][1]))
            walk(c, mc)

    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    # ★★ 有 `legId`（**core 件约定** ✓）⇒ **连接点在腿尖** ✓（2026-09-27 机验钉死 ✓）：
    #   core 的 .fzp 写的是 `<p layer="breadboard" svgId="connector0pin" legId="connector0leg"/>` ✓
    #   —— "腿尖才是插进孔的那个点" ✓；而 `svgId` 那个小 rect 是**看不见的标记**
    #   （`fill="none"` ✗，宽 3 高 1 ✓）⇒ 拿它当连接点会错 ✓。
    #   证据 ✓：C1 两条腿的**远端** → `pin16J`/`pin17J` ⇒ **Δ=0.00 / 0.02** ✓✓
    #   （若取标记中心 ⇒ Δ=26.55 ✗✗，就是一条假警报 ✗）。
    #   "远端" = 离**图形包围盒中心**较远的那一端 ✓（电容腿朝下 ✓、电阻腿朝左右 ✓ 都成立 ✓）。
    #   ✗ 已知例外（**core 自己的桩画错了** ✗，不是我们的 ✗）：
    #     · `ceramic_capacitor_blue_leg.svg` 的 `connector1leg` 与
    #     · `resistor_220.svg` 的 `connector1leg`
    #     都离**真正的腿尖**差 **10 用户单位（= 9 sketch 单位 = 2.54mm = 1 孔）** ✗
    #     ⇒ 这两个脚仍报 Δ=9 ✓。**判据**：用户自己手工做的 `pixel-breadboard43_byHand.fzz`
    #     里**一模一样** ✓（Fritzing 自己写下的记录与它自己的图形不符 ✓）⇒ 不属于我们的错 ✗。
    bb = shape_bbox(root)
    for cid, (pa, pb) in legs.items():
        if bb is None:
            tip = pa
        else:
            cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
            tip = pb if ((pb[0] - cx) ** 2 + (pb[1] - cy) ** 2) > \
                        ((pa[0] - cx) ** 2 + (pa[1] - cy) ** 2) else pa
        got["%spin" % cid] = tip
    return got, bad


def resolve_svg(fzp_path, image):
    """按 fzp 的 `breadboardView/layers@image` 找到真 svg ✓

    照 Fritzing 的目录约定：`<parts>/svg/{'',core,contrib,user}/<image>` ✓
    （user 件在 `…/Documents/Fritzing/parts/user/x.fzp` ✓，svg 在 `…/parts/svg/user/breadboard/x.svg` ✓）
    找不到 ⇒ None ✓（**不静默** ✓：调用方要报出来 ✓）。
    """
    if not image or not fzp_path:
        return None
    import os                       # ★ 本模块原本不 import os ✓（函数内导入最稳 ✓，不动文件头 ✓）
    base = os.path.dirname(os.path.dirname(fzp_path))
    for s2 in ("", "core", "contrib", "user"):
        cand = os.path.normpath(os.path.join(base, "svg", s2, image.replace("/", os.sep)))
        if os.path.isfile(cand):
            return cand
    return None


def canvas_mm(attrs):
    """svg 的 width/height → mm ✓（mm/cm/in/mil/px/pt ✓），取不到 ⇒ None ✓

    ★★ 2026-09-27 修 ✓：`px` 由 **25.4/96 ✗ 改成 25.4/72** ✓（= 1/72 英寸 ✓）。
      原来按 96dpi 算 ⇒ **px 件的本体小 25%** ✗ ⇒ “本体遮住了哪些孔”**少算** ✗
      ⇒ 可能把线布到元件底下 / 审计漏报 ✗（§5b 第 4 条那条硬规则形同虚设 ✗）。
      证据 ✓（与 `render_bb.scale_of` **同一条规则** ✓，两边都是 1/72 ✓）：
        · 面包板 `468.238px` ⇒ **165.2mm** ✓ ≈ 孔阵 `576 单位 = 162.6mm` ✓；
        · `WS2812B_1010` 面包板 4 脚中心差 `14.401×21.600` 用户单位 → `18×27` sketch
          单位 ✓ = 它插的孔 `col31→col33` / `rowE→rowF` ✓。
      ★ 教训：**同一件事只能有一份口径** ✗ —— 这里曾和渲染器不一致（96 vs 72 ✗）。
      ★ 无单位（`width="25"`）**故意不支持** ✓ ⇒ 返回 None ⇒ 上层视为“不知道” ✓，
        而不是**算一个错的**出来 ✗（宁可少算、由调用方兜底 ✓，与 `shape_bbox` 同一个保守原则 ✓）。
    """
    UNIT = {"mm": 1.0, "cm": 10.0, "in": 25.4, "mil": 0.0254,
            "px": 25.4 / 72.0, "pt": 25.4 / 72.0}

    def one(s):
        if not s:
            return None
        m = re.match(r"\s*(-?[\d.]+)\s*([a-z%]*)\s*$", s)
        if not m:
            return None
        v, u = float(m.group(1)), m.group(2)
        return v * UNIT[u] if u in UNIT else None

    return one(attrs.get("width")), one(attrs.get("height"))


def body_box(svg_path):
    """元件**本体**在 sketch 单位下的矩形（相对画布原点 ✓）；不可信 ⇒ None ✓"""
    root = ET.parse(svg_path).getroot()
    wmm, hmm = canvas_mm(root.attrib)
    if not wmm or not hmm:
        return None
    vb = _nums(root.get("viewBox"))
    if len(vb) == 4 and vb[2] and vb[3]:
        k = wmm / vb[2]                       # mm / 用户单位 ✓
        ox, oy = vb[0], vb[1]
    else:
        k, ox, oy = wmm / (float(root.get("width").rstrip("a-z%") or 1)), 0.0, 0.0
    c = shape_bbox(root)
    if c is None:
        return None
    box = ((c[0] - ox) * k * MM, (c[1] - oy) * k * MM,
           (c[2] - ox) * k * MM, (c[3] - oy) * k * MM)
    # ★★ 2026-09-27 修 ✓：**不要因为"内容超出画布"就返回 None** ✗ ——
    #   core 的 `ceramic_capacitor_blue_leg.svg` / `resistor_220.svg` 都把**引脚腿画到画布外** ✓，
    #   那是**合理的画法** ✓（腿本来就伸出去 ✓）⇒ 旧写法让这两件**永远量不出框** ✗
    #   ⇒ 审计里一直卡在"未验证"✗（是用户报 `Wire90012903` 那一轮才暴露出来的第二个洞 ✓）。
    #   ⇒ 现在**照实返回内容包围盒** ✓（腿占的地方也算它占的 ✓），
    #     只在**离谱**溢出（> 4 倍画布 ✗ = 多半是相对 path 命令没解析对 ✗）时才 None ✓。
    lim = 4.0 * max(wmm * MM, hmm * MM, 1e-6)
    if (box[0] < -lim or box[1] < -lim
            or box[2] > wmm * MM + lim or box[3] > hmm * MM + lim):
        return None
    return box


def place(loc, m, box):
    """把（相对画布原点的）矩形按实例矩阵搬到 sketch 绝对坐标 ✓"""
    xs, ys = [], []
    for u in (box[0], box[2]):
        for v in (box[1], box[3]):
            p = apply(m, u, v)
            xs.append(loc[0] + p[0])
            ys.append(loc[1] + p[1])
    return (min(xs), min(ys), max(xs), max(ys))


# ── PCB：svg 单位 → sketch 单位（2026-09-30 ✓ 焊盘读入器 `pcb_pads.py` 用 ✓）────
def svg_k(root):
    """svg 的 **sketch 单位 / 用户单位** 换算 ＋ `viewBox` 原点 ✓

    ⇒ `(k, (vb_x0, vb_y0))`；算不出（`width` 没单位 / 没宽度 ✗）⇒ `(None, (0, 0))` ✓
      —— **不猜** ✓（宁可让调用方报"不知道" ✓，也不要算一个错的出来 ✗，与 `body_box` 同一个原则 ✓）。

    ★★ 口径与渲染器 `render_bb.scale_of` **必须一致** ✓（同一条规则 ✓）：把 svg 的 `width`
      当**物理尺寸** ✓、`viewBox` 第 3 项当**用户单位宽** ✓、`px`/`pt` = 1/72 in ✓（不是 96dpi ✗）。
      ✗ 那份是**内联写在 CLI 脚本**里的 ✗（它的模块顶层就开跑 ⇒ `import` 不进来 ✗）
      ⇒ 收到共享模块里一份 ✓、**以后改只改这里** ✓（渲染器那份留待一起收拢 ✓，别各改各的 ✗）。
    """
    wmm, _hmm = canvas_mm(root.attrib)
    if not wmm:
        return None, (0.0, 0.0)
    vb = _nums(root.get("viewBox"))
    if len(vb) == 4 and vb[2]:
        return wmm * MM / vb[2], (vb[0], vb[1])
    w = re.sub(r"[a-z%]", "", root.get("width") or "")
    try:
        return wmm * MM / float(w), (0.0, 0.0)
    except ValueError:
        return None, (0.0, 0.0)
