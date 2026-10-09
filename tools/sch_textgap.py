# -*- coding: utf-8 -*-
r"""★★★ **「文字 ↔ 被绘制对象」净距判据的唯一实现** ✓（2026-10-09 ✓）

★ 为什么要有这个文件 ✗（用户 2026-10-09 报的缺陷 ✓）：
  用户原话 ✓：「**文字和接地符号重叠了**，请制定规则来解决」✓ ——
  截图点名的是 `LED2` 那个**值文字 `WS2812B-1010`** 压在**接地符号**上 ✗。
  本仓**已有**一条"**位号不许压线**"的规则 ✓，但它**没盖住**三件事 ✗：
    ① **值文字**（`titleGeometry` 的**第 2 行之后** ✗ —— 老规则算盒子时用 `label_bbox` 全部行 ✓，
       但**判的对象集**里没有接地/电源符号 ✗、也没有"别的文字" ✗）；
    ② **接地/电源符号件**（`GroundModuleID` —— 它的**真外形**只有 `sch_net.ground_art()` 给得出 ✓；
       老规则用的是一段**量出来的固定 keep-out** ✓，与实际画的符号**对不上** ✗）；
    ③ **文字 ↔ 文字** ✗（老规则只把"已放的位号"算进去 ✓）。

★ 本文件的**口径**（与用户的要求一字对应 ✓）：
  · **文字** = ① 元件位号块（`titleGeometry`：位号行 ＋ `showInLabel` 的值行 ✓，行内容调
    `sch_text.fritzing_lines()` ✓ **唯一实现** ✓）② 网标签旗标（`NetLabelModuleID` ✓
    —— 文字长在旗标本体里 ✓，所以**旗标本体 ＝ 文字外接框** ✓）
    ★ 接地/电源符号**本板不画文字** ✓（`voltage` 属性没进位号 ✓）⇒ 不列为文字 ✓。
  · **被绘制对象** = ① 元件符号本体（`sch_body.shapes_of()` ✓ **实绘制外形** ✓，含引脚引线 ✓）
    ② 导线（`WireModuleID` 的 `schematicTrace` 一段 ✓）③ 接地/电源符号（`sch_net.ground_art()` ✓）
    ④ 网标签旗标 ⑤ **别的文字**（位号块 ✓）。
    ★ **面包板本体不列** ✓（Fritzing 的原理图**不画它** ✓ — 与 `render_sch.py` 同口径 ✓）。
  · **判据** = 两个**轴对齐外接框**的**净距** ≥ `gap` ✓（相交 ⇒ 净距 0 ⇒ 必违例 ✓）。
    净距 = 两框在 x、y 上各自"差多少"，再取欧氏长度 ✓（各轴都 ≤0 的间距记 0 ✓）。
  · **豁免只有一条** ✓（= "**自己的接线柱**" ✓，与 `sch_body` 的"自己的脚"同精神 ✓）：
    · 元件位号块 ↔ **它自己那件**的本体/旗标 ⇒ 不算 ✗（位号本来就贴着本体 ✓）；
    · 网标签旗标 ↔ **它自己在 `.fzz` 里声明连接的那根引线** ⇒ 不算 ✗
      （旗标**必须**坐在切口线端上 ✓ —— 那接触是设计 ✓，不是重叠 ✗）；
    · ★ 别的**一律**算 ✗（跨件、跨网、跨"文字 ↔ 文字" ✓）—— 这正是用户要的那条硬规矩 ✓。

★ 几何来源 ✓（**不新造** ✗）：
  · 元件本体 ⇒ `sch_body` ✓（与生成器的穿体闸门、渲染器 ④b **同一把尺子** ✓）；
  · 接地符号 ⇒ `sch_net.ground_art()` ✓（与渲染器画的是同一份素材 ✓）；
  · 网标签 ⇒ `sch_net.label_flag()` / `sch_net.label_box()` ✓；
  · 旋转/镜像 ⇒ `sch_box.A_of()` / 实例 `<transform>` ✓（`sch_body.shapes_of()` 内部走 ✓）。

用法 ✓：
    import sch_textgap as TG
    texts, objs = TG.items(root, packed)
    bad = TG.violations(root, texts, objs, gap_u)
"""

import math
import os
import re
import xml.etree.ElementTree as ET

import sch_box as SB
import sch_body as SBD
import sch_net
import sch_text as ST

MM = 25.4 / 90.0                     # 1 sketch 单位 = 1/90 in ⇒ 0.282222 mm ✓
DEFAULT_MM = 0.15                    # 缺省净距（mm ✓）
MIN_MM = 0.0                         # 用户定的范围下界 ✓
MAX_MM = 2.54                        # 用户定的范围上界 ✓（= 0.1 in ✓）
LANE = 9.0                           # "一个车道" = 一个 Fritzing 原理图网格步 = 0.1 in ✓


def tag(e):
    return e.tag.split("}")[-1]


def child(e, n):
    for c in e:
        if tag(c) == n:
            return c
    return None


def num(s, d=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return d


def clamp_mm(v):
    """把用户给的 mm 夹进 [0, 2.54] ✓ —— 返回 (值, 说明 ✓)"""
    if v < MIN_MM:
        return MIN_MM, "**小于下界 %.3f mm** ✗ ⇒ 夹到 %.3f" % (MIN_MM, MIN_MM)
    if v > MAX_MM:
        return MAX_MM, "**大于上界 %.3f mm** ✗ ⇒ 夹到 %.3f" % (MAX_MM, MAX_MM)
    return v, None


def rot22(gel):
    for c in gel:
        if tag(c) == "transform" and c.get("m11") is not None:
            return (float(c.get("m11")), float(c.get("m12")),
                    float(c.get("m21")), float(c.get("m22")))
    return sch_net.IDENT


def shape_bbox(shp):
    xs, ys = [], []
    for _k, pts, _w in shp:
        for (x, y) in pts:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def box_dist(a, b):
    """两轴对齐框的**净距** ✓（相交 ⇒ 0 ✓）"""
    dx = max(0.0, max(b[0] - a[2], a[0] - b[2]))
    dy = max(0.0, max(b[1] - a[3], a[1] - b[3]))
    return 0.0 if (dx == 0.0 and dy == 0.0) else math.hypot(dx, dy)


def _ovl(a, b):
    """两框**相交**吗 ✓（判"压在自己本体上"用 ✓ —— 这是**摆放偏好** ✓，不是判据 ✓）"""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def shapes_in_box(shp, box):
    """外形里有没有**墨迹顶点**落进这个框 ✓（用来判"真碰到"而不是"框碰到" ✓）"""
    x0, y0, x1, y1 = box
    for _k, pts, _w in shp:
        for (x, y) in pts:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return True
    return False


def is_breadboard(fzp_path):
    """面包板：**Fritzing 的原理图不画它** ✓ ⇒ 不许当障碍 ✗（与 `render_sch.py` 同口径 ✓）"""
    if not (fzp_path and os.path.isfile(fzp_path)):
        return False
    try:
        fr = ET.parse(fzp_path).getroot()
    except ET.ParseError:
        return False
    tax = (fr.findtext("taxonomy") or "").lower()
    fam = next((p.get("value") for p in fr.iter("property")
                if p.get("name") == "family"), "") or ""
    return "breadboard" in tax or fam.lower() == "breadboard"


def part_svg_for(fzp_path, packed, view="schematicView"):
    """该视图**实际绘制**的符号 svg 文本 ✓（`sch_box.part_svg_text` ✓ 唯一实现 ✓）"""
    if not (fzp_path and os.path.isfile(fzp_path)):
        return None
    try:
        fr = ET.parse(fzp_path).getroot()
    except ET.ParseError:
        return None
    lay = fr.find(".//%s/layers" % view)
    image = lay.get("image") if lay is not None else None
    if not image:
        return None
    txt, _src = SB.part_svg_text(fzp_path, packed or {}, image)
    return txt


# ── 实例扫描 ──────────────────────────────────────────────────────────────
def instances(root):
    """按 `schematicView` 扫实例 ✓ —— 返回 {modelIndex: dict(...)} ✓"""
    out = {}
    for e in root.iter("instance"):
        mi = str(e.get("modelIndex"))
        vw = child(e, "views")
        sv = child(vw, "schematicView") if vw is not None else None
        if sv is None:
            continue
        gel = child(sv, "geometry")
        if gel is None or gel.get("x") is None:
            continue
        out[mi] = dict(
            title=(e.findtext("title") or "").strip(),
            mid=e.get("moduleIdRef") or "", sv=sv, gel=gel,
            loc=(num(gel.get("x")), num(gel.get("y"))),
            path=(e.get("path") or "").replace("/", os.sep),
            vals={c.get("name"): c.get("value") for c in e if tag(c) == "property"})
    return out


def wire_ends(d):
    g = child(d["sv"], "geometry")
    if g is None or g.get("x") is None or g.get("x2") is None:
        return None
    return ((num(g.get("x")), num(g.get("y"))),
            (num(g.get("x")) + num(g.get("x2")), num(g.get("y")) + num(g.get("y2"))))


def items(root, packed=None):
    """★ 把一张图里**所有文字**与**所有被绘制对象**都收齐 ✓（外接框 ＋ 外形 ＋ 归属 ✓）

    返回 `(texts, objs)` ✓，两项都是 list[dict] ✓：
      · text: kind / name / mi / box / lines / el（位号块的 `<titleGeometry>` ✓，网标签为 None ✓）
      · obj : kind / name / mi / box / shapes
    """
    inst = instances(root)
    wires = {mi: d for mi, d in inst.items() if "Wire" in d["mid"]}
    labels = {mi: d for mi, d in inst.items() if sch_net.is_label_module(d["mid"])}
    grounds = {mi: d for mi, d in inst.items() if sch_net.is_ground_symbol(d["mid"])}
    parts = {mi: d for mi, d in inst.items()
             if mi not in wires and mi not in labels and mi not in grounds}

    texts, objs = [], []
    for mi, d in parts.items():
        tg = child(d["sv"], "titleGeometry")
        if tg is None or (tg.get("visible") or "true") == "false":
            continue
        lines = ST.fritzing_lines(d["title"], d["path"], d["vals"])
        if not lines:
            continue
        fs = float(tg.get("fontSize") or 5.0)
        bx = ST.label_bbox(num(tg.get("x")), num(tg.get("y")), fs, lines)
        nm = d["title"] + ("+" + "+".join(lines[1:]) if lines[1:] else "")
        texts.append(dict(kind="位号块", name=nm, mi=mi, box=bx, lines=lines, el=tg))
    objs_flags = {}
    for mi, d in labels.items():
        nm = sch_net.net_name(d["mid"], d["title"]) or d["title"] or "?"
        shp = SBD.poly_region(sch_net.label_flag(d["loc"], nm, rot22(d["gel"])))
        bx = sch_net.label_box(d["loc"], nm, rot22(d["gel"]))
        texts.append(dict(kind="网标签", name=nm, mi=mi, box=bx, lines=[nm], el=None))
        objs_flags[mi] = shp

    for mi, d in parts.items():
        if is_breadboard(d["path"]):
            continue
        txt = part_svg_for(d["path"], packed)
        if not txt:
            continue
        shp = SBD.shapes_of(txt, d["gel"])
        bx = shape_bbox(shp)
        if bx:
            objs.append(dict(kind="器件本体", name=d["title"], mi=mi, box=bx, shapes=shp))
    for mi, shp in objs_flags.items():
        objs.append(dict(kind="网标签符号", name=labels[mi]["title"], mi=mi,
                         box=shape_bbox(shp), shapes=shp))
    for mi, d in grounds.items():
        shp = SBD.shapes_of_markup(sch_net.ground_art(d["loc"]))
        bx = shape_bbox(shp)
        if bx:
            objs.append(dict(kind="接地符号", name=d["title"], mi=mi, box=bx, shapes=shp))
    for mi, d in wires.items():
        pq = wire_ends(d)
        if not pq:
            continue
        p, q = pq
        objs.append(dict(kind="导线", name=d["title"], mi=mi,
                         box=(min(p[0], q[0]), min(p[1], q[1]),
                              max(p[0], q[0]), max(p[1], q[1])),
                         shapes=[("stroke", [p, q], 1.0)]))
    return texts, objs


def declared_pairs(root):
    """`.fzz` 里**声明连接**的实例对 ✓（= "自己的接线柱" ✓ 豁免白名单 ✓）"""
    out = set()
    for mi, d in instances(root).items():
        for c in d["sv"].iter("connect"):
            omi = c.get("modelIndex")
            if omi is not None:
                out.add((mi, str(omi)))
    return out


def exempt(root, t, o, pairs=None):
    """这条"文字 ↔ 对象"要不要放行 ✓（**唯一一处**豁免口径 ✓）"""
    if t["mi"] == o["mi"]:
        return True                                   # 自己的本体 / 自己的旗标 ✓
    if pairs is None:
        pairs = declared_pairs(root)
    # 网标签旗标 ↔ **它自己声明的那根引线** ✓（旗标必须坐在切口线端上 ✓）
    return t["kind"] == "网标签" and o["mi"] != t["mi"] and ((t["mi"], o["mi"]) in pairs
                                                             or (o["mi"], t["mi"]) in pairs)


def bad_vs_objs(root, box, t, objs, gap_u, pairs=None):
    """★ 假定文字 `t` **搬到** `box` ✓ ⇒ 它与**被绘制对象**有几条违例 ✓（`[(对家, 净距)]` ✓）"""
    if pairs is None:
        pairs = declared_pairs(root)
    probe = dict(t, box=box)
    rows = []
    for o in objs:
        if exempt(root, probe, o, pairs):
            continue
        dd = box_dist(box, o["box"])
        if dd < gap_u - 1e-9:
            rows.append((o, dd))
    return rows


def bad_vs_texts(box, t, texts, gap_u):
    """★ 假定文字 `t` **搬到** `box` ✓ ⇒ 它与**别的文字**有几条违例 ✓

    ★ 口径 ✓：**每对只算一次** ✓（文字 × 文字是**对称**的 ✓ —— 逐条点名时按 `i<j` 数 ✓，
      ✗ 不许"我算它、它也算我" ✗ ⇒ 那个数会**翻倍** ✗）。
    """
    rows = []
    for a in texts:
        if a is t or a["mi"] == t["mi"]:
            continue
        dd = box_dist(box, a["box"])
        if dd < gap_u - 1e-9:
            rows.append((a, dd))
    return rows


def bad_for_box(root, box, t, texts, objs, gap_u, pairs=None):
    """★ 假定文字 `t` **搬到** `box` ✓ ⇒ 它会有**几条**违例 ✓（**与 `violations()` 同源** ✓）

    ★ 只做"这一条文字 ↔ 全世界"这一件事 ✓ —— 自动摆放要**试很多候选位** ✓，
      判据必须**只有一份** ✗（试位用一套、验收用另一套 = 两把尺子 ✗）。
    返回 `[(对家, 净距)]` ✓（对家可能是对象 ✓、也可能是**别的文字** ✓）。

    ★★ 试位用这个 ✓（**要**把别的文字也算进来 ✓ —— 挪完不能压到人家 ✓）；
      **逐条点名**用 `violations()` ✓（那边**对象走本函数、文字×文字单列 ✓** ⇒ 每对只数一次 ✓）。
    """
    return (bad_vs_objs(root, box, t, objs, gap_u, pairs)
            + bad_vs_texts(box, t, texts, gap_u))


def violations(root, texts, objs, gap_u, pairs=None, tminfo=True):
    """★ **本判据的主入口** ✓ —— 返回 [(text, obj, 净距, 真墨迹命中 ✓)] ✓

    ★ 口径与 `bad_for_box()` **同源** ✓（对象那一路就是它那个函数 ✓）—— 只是这里还带上
      "真墨迹命中"与"对家是不是文字"这两样**给人看**的信息 ✓。
    """
    if pairs is None:
        pairs = declared_pairs(root)
    rows = []
    for t in texts:
        for o, dd in bad_vs_objs(root, t["box"], t, objs, gap_u, pairs):
            ink = None
            if tminfo and o.get("shapes"):
                ink = shapes_in_box(o["shapes"], t["box"])
            rows.append((t, o, dd, ink))
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            if a["mi"] == b["mi"]:
                continue
            dd = box_dist(a["box"], b["box"])
            if dd < gap_u - 1e-9:
                rows.append((a, b, dd, None))
    return rows


def check(root, packed=None, gap_mm=DEFAULT_MM, pairs=None):
    """一次跑完 ✓ —— 返回 `(violations, texts, objs, gap_u)` ✓"""
    gap_u = gap_mm / MM
    texts, objs = items(root, packed)
    return violations(root, texts, objs, gap_u, pairs), texts, objs, gap_u


def fmt_net(v, gap_u):
    """一条违例的**人话** ✓"""
    t, o, dd, ink = v
    if o["kind"] == "位号块":
        tail = o["name"] + "(文字)"
    else:
        tail = o["name"]
    return ("%-6s %-26s ↔ %-10s %-16s ｜ 净距 %.4f 单位 = %.4f mm（要 ≥ %.4f mm ✓）%s"
            % (t["kind"], t["name"], o["kind"], tail, dd, dd * MM, gap_u * MM,
               "｜ 真墨迹命中 ✓" if ink else ""))


# ── 自动修：① 挪文字 ✓ ────────────────────────────────────────────────────
def owner_box(t, objs):
    """这条文字**挂在哪件**的本体上 ✓（位号 ⇒ 它那件的本体框 ✓；网标签 ⇒ 它自己的旗标 ✓）"""
    want = "网标签符号" if t["kind"] == "网标签" else "器件本体"
    for o in objs:
        if o["mi"] == t["mi"] and o["kind"] == want:
            return o["box"]
    for o in objs:
        if o["mi"] == t["mi"]:
            return o["box"]
    return None


def cand_boxes(ob, w, h, old, lanes=(1, 2, 3, 4, 5), fine=12, step=None):
    r"""文字的**候选位**（盒左上角 ✓）—— 方向族 ✓ ＋ 原位附近的**细档** ✓

    ★ 方向族（既有文字摆放规则那一套 ✓）：**上**·左/中/右 ✓、**下**·左/中/右 ✓、**左** ✓、**右** ✓
      —— 每一档按 `LANE`（= 一个 Fritzing 原理图网格步 = 9 单位 ✓）往外推 ✓。
    ★ 细档 ✓：原位周围 ±`fine` × `step`（缺省 `LANE`/10 = **0.9 单位** ✓）的方格 ✓ ——
      ✗ 没有它就只能"整格整格"跳 ✗ ⇒ 差 0.05 单位（`D3` 那处 ✓）也得跳 9 单位 ✗；
      步长 1.8（半个细档 ✗）实测会让 `LED2` 多挪 0.9 单位 = 0.25 mm ✗。
    """
    x0, y0, x1, y1 = ob
    st = LANE / 10.0 if step is None else step
    out = []
    for k in lanes:
        g = LANE * k
        out += [(x0, y0 - g - h), (x1 - w, y0 - g - h), ((x0 + x1 - w) / 2.0, y0 - g - h),
                (x0, y1 + g), (x1 - w, y1 + g), ((x0 + x1 - w) / 2.0, y1 + g),
                (x0 - g - w, y0), (x1 + g, y0)]
    for i in range(-fine, fine + 1):
        for j in range(-fine, fine + 1):
            out.append((old[0] + i * st, old[1] + j * st))
    seen, uniq = set(), []
    for c in out:
        k = (round(c[0], 3), round(c[1], 3))
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq


def repair(root, texts, objs, gap_u, pairs=None, log=None, rounds=6):
    r"""★★ **自动修：挪文字** ✓（判据与验收**同一份** ✓）

    优先级 ✓（用户 2026-10-09 定 ✓）：**不压任何东西** ✓ > **少移动** ✓ > **贴近原位置** ✓
      ⇒ 打分键 = `(违例条数, 位移)` ✓（先按违例条数，再按位移 ✓ —— 位移天然就是"贴近原位" ✓）。

    ★ 只改**位号块**的位置（`<titleGeometry>` 的 `x/y` ✓ ＋ 跟着更新 `xOffset/yOffset` ✓）：
      · 网标签**不能挪** ✗ —— 它必须坐在**切口线端**上 ✓（挪了就把网切开 ✗，`每网 1 岛` 当场挂 ✗）；
      · 接地/电源符号**也不能乱挪** ✗（同理 ✓ —— 而且要动就得把它的引线端点一起动 ✓，
        那是第二档的事 ✓ 见 `nudge_symbol()` ✓）。
    ★ 返回 `(剩余违例数, 台账 ✓)` ✓。
    """
    if pairs is None:
        pairs = declared_pairs(root)
    moves = []
    for _r in range(rounds):
        bad = violations(root, texts, objs, gap_u, pairs)
        if not bad:
            break
        hot = []
        for t, _o, _d, _i in bad:
            if t["kind"] == "位号块" and t not in hot:
                hot.append(t)
        if not hot:
            break
        # 字块**大的先放** ✓（与 `relabel()` 同一策略 ✓）
        hot.sort(key=lambda t: -(t["box"][3] - t["box"][1]))
        moved_any = False
        for t in hot:
            ob = owner_box(t, objs)
            if ob is None:
                continue
            bx = t["box"]
            w, h = bx[2] - bx[0], bx[3] - bx[1]
            old = (bx[0], bx[1])
            cur = len(bad_for_box(root, bx, t, texts, objs, gap_u, pairs))
            cand = cand_boxes(ob, w, h, old)
            # ★★ 先滤掉"**压在自己本体上**"的候选 ✓（判据本身**豁免**自己本体 ✓ ——
            #   那条豁免是**必须**的 ✓（否则没有一个位号不违例 ✓）；但**摆放**不该往自己身上放 ✗
            #   —— 既有 `relabel()` 的候选族也从不压本体 ✓。★ 滤空了就**退回全量** ✓（不许因此丢解 ✗）。
            keep = [c for c in cand
                    if not _ovl((c[0], c[1], c[0] + w, c[1] + h), ob)]
            if keep:
                cand = keep
            best, bk = None, None
            for c in cand:
                nb = len(bad_for_box(root, c + (c[0] + w, c[1] + h), t, texts, objs, gap_u, pairs))
                mv = math.hypot(c[0] - old[0], c[1] - old[1])
                if bk is None or (nb, mv) < bk:
                    best, bk = c, (nb, mv)
            if best is None or bk[0] > 0 or bk[0] >= cur:
                continue                          # ✗ 挪不到干净处 ⇒ 交给第二档 ✓（不硬塞 ✗）
            el = t["el"]
            fs = float(el.get("fontSize") or 5.0)
            el.set("x", "%g" % best[0])
            el.set("y", "%g" % (best[1] - 0.25 * fs))
            _me = instances(root).get(str(t["mi"]))
            loc = _me["loc"] if _me else (0.0, 0.0)
            el.set("xOffset", "%g" % (best[0] - loc[0]))
            el.set("yOffset", "%g" % (best[1] - 0.25 * fs - loc[1]))
            moves.append((t["name"], old, best))
            t["box"] = (best[0], best[1], best[0] + w, best[1] + h)
            moved_any = True
        if not moved_any:
            break
    bad = violations(root, texts, objs, gap_u, pairs)
    return len(bad), moves


# ── 自动修：② 微调符号（≤ 一个车道 ✓）────────────────────────────────────
def symbol_pin(inst):
    """符号件（接地 / 网标签）**画出来的脚** ✓（视图坐标 ✓）—— 判"哪条线端在它身上"用它 ✓

    ★✗ 踩过的坑 ✓（2026-10-09 ✓）：一开始拿实例的 `<geometry>` 原点当"脚" ✗ ——
      接地符号的 **脚 ≠ 原点** ✗（实测偏 `(+9.001, +0.596)` ✓，`sch_net.GROUND_PIN_*` ✓）
      ⇒ 那一条重合都认不出来 ✗ ⇒ 第二档恒等于"不动" ✗（`--text-gap 5 --text-gap-symbol`
      实测打印的就是"这条认不出" ✗）。
    """
    mid, loc = inst["mid"], inst["loc"]
    if sch_net.is_ground_symbol(mid):
        return sch_net.ground_pin(loc)
    if sch_net.is_label_module(mid):
        nm = sch_net.net_name(mid, inst["title"]) or inst["title"] or "?"
        return sch_net.label_pin(loc, nm, rot22(inst["gel"]))
    return None


def symbol_attachments(root, inst):
    """符号件（接地 / 网标签）那条引线的**对应端点** ✓（= 必须跟着挪的那一头 ✓）

    ★★ 2026-10-09 ✓ **判据改正** ✗（实测踩的 ✓）：原来取"**离符号最近**的那个线端" ✓ ——
      那一支**不是单射** ✗：符号一挪，"最近的那个端"可能**换成另一端** ✗ ⇒ **挪回去挪不回来** ✗
      （`--text-gap 5` 实测：`Wire90015558` 被搞成一条**斜线** `(179.78,17)→(188.78,26)` ✗，
      顺带把"线距"闸门**打破**了 ✗✗）。
    ✓ 现在：只认**与符号画出来的脚重合（≤0.05 ✓）**的线端 ✓，而且**恰好只有一条**才用它 ✓ ——
      0 条（没有接线 ✓）或 >1 条（认不准 ✓）⇒ **一律不动** ✗（宁可不做 ✗）。
      ★ 这样**挪与挪回严格互逆** ✓（重合关系跟着一起走 ✓）。
    ★★ 调用方必须**算一次、apply / revert 共用**这份结果 ✓（✗ 不许每挪一次重算 ✗ —— 那正是上面那个坑 ✗）。
    ★ 返回 `(geometry 元素, "xy" 或 "xy2", 那条导线的 modelIndex)` ✓ ／ `None` ✓。
    """
    pin = symbol_pin(inst)
    if pin is None:
        return None
    att = []
    for omi, d in instances(root).items():
        if "Wire" not in d["mid"]:
            continue
        pq = wire_ends(d)
        if not pq:
            continue
        g = child(d["sv"], "geometry")
        for which, pt in (("xy", pq[0]), ("xy2", pq[1])):
            if math.dist(pt, pin) <= 0.05:
                att.append((g, which, omi))
    return att[0] if len(att) == 1 else None


def nudge_symbol(root, mi, dx, dy, att=None):
    r"""★ 第二档 ✓：把一个**符号件**（接地 / 网标签）挪 **≤ 一个车道** ✓
    —— 同时把**它那条引线的对应端点**一起挪 ✓ ⇒ 接头原地不动 ✓。

    ★ `att` 必须由 `symbol_attachments()` **先算一次** ✓ 并**原样传进来** ✓
      （apply 与 revert 用**同一个**元素 ⇒ 挪与挪回**严格互逆** ✓ —— 见上面那段教训 ✗）。
    ★ 为什么只给符号件 ✓：符号件的脚只有**一条引线** ✓ ⇒ 挪它只牵动**一个线端** ✓；
      而挪一个**器件**要牵动**它所有的脚** ✓ —— 那已经等于重新布线 ✗（本档不做 ✗、但要报出来 ✓）。
    """
    inst = instances(root).get(str(mi))
    if inst is None:
        return False
    if att is None:
        att = symbol_attachments(root, inst)
    if att is None:
        return False
    inst["gel"].set("x", "%g" % (inst["loc"][0] + dx))
    inst["gel"].set("y", "%g" % (inst["loc"][1] + dy))
    g, which, _wmi = att
    if which == "xy":
        g.set("x", "%g" % (num(g.get("x")) + dx))
        g.set("y", "%g" % (num(g.get("y")) + dy))
    else:
        g.set("x2", "%g" % (num(g.get("x2")) + dx))
        g.set("y2", "%g" % (num(g.get("y2")) + dy))
    return True
