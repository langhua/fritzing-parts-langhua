# -*- coding: utf-8 -*-
r"""读**元件 PCB 焊盘**几何（给 PCB 摆位 / 布线 / DRC 用 ✓）2026-09-30 立

★★ 为什么要它 ✓：PCB 上每一条走线、每一个过孔**都必须落在焊盘上** ✓，
   而"焊盘在哪"只有**元件自己**知道 —— `.fzp` 的 `<pcbView>` ＋ 它的 `pcb` svg ✓。
   ⇒ 不许拿"图纸上看着差不多"的数 ✗（§10.8 禁止编数据 ✓），也不许自己编一个 ✗。

数据来源（**都在仓内** ✓ 或**公开的 `fritzing/fritzing-parts`** ✓）：
  · 库内件：`<库仓>/svg/<部件>/part.<id>.fzp` ＋ `svg.pcb.<id>_pcb.svg` ✓
  · `.fzz` 里**内嵌**的 `part.*.fzp` ＋ `svg.pcb.*.svg` ✓（Fritzing 导出时自己打的包 ✓）
  · core 件：`<fritzing-parts>/core/x.fzp` ⇒ svg 在 `<fritzing-parts>/svg/core/pcb/…` ✓
    （本项目的 0603 电阻/电容就是 core 件 ✓，两者**共用** `pcb/SMD_0603.svg` ✓）

认焊盘的规矩 ✓（**照 Fritzing 的约定读，不猜 id** ✗）：
  ① connector 清单来自 `.fzp` 的 `<connectors>` ✓（`id="connectorN"` ＋ `name` ✓）；
  ② 焊盘图形 = pcb svg 里 `id` 为 **`<connectorN><后缀>`** 的那个图元 ✓；
     实测见过的后缀：`pad`（本库 SMD ✓）、`pin`（1010 / 线圈 / core ✓）、`leg`（core ✓）；
     其余后缀 ⇒ **点名报出** ✓（不静默跳过 ✗）；
  ③ 焊盘**在正面还是背面** = 它所在的那层 `<g id="copper0|copper1">` ✓（**按 svg 说** ✓ 不猜 ✗）；
  ④ 位置必须**走完祖先 transform 链** ✓（复用 `part_box.mul/parse_tf/apply` ✓ **不另写一份** ✗）。

⚠️ **通孔件的孔/环口径**：Fritzing 的约定是「`circle` 的 `r` = **孔半径** ✓、
  `stroke-width` = **环宽**」⇒ 外径 = `2r + sw` ✓。本文件**照这个口径报** ✓，
  但**待核**（P0 第 3 步拿 Fritzing 源码钉死 ✓，见 README「PCB 分期」✓）。

用法：
  py -3.13 tools\pcb_pads.py <sketch.fzz>                # 每个件每个焊盘（绝对 sketch 单位 ＋ 相对板角 mm）
  py -3.13 tools\pcb_pads.py <sketch.fzz> --part <标题>   # 只看一个件
  py -3.13 tools\pcb_pads.py <sketch.fzz> --spec          # **对账**：与已知 land pattern 比（出处写在表里 ✓）
"""
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import part_box as PB                                            # noqa: E402

tag = PB.tag
SK = PB.MM                       # 1 mm = 3.5433 sketch 单位 ✓
PAD_SUF = ("pad", "pin", "leg", "terminal", "circle", "ring")
PADLIKE = ("rect", "circle", "ellipse")          # 焊盘形状 ✓（path = 走线/铜箔 ✓）
BOARD_MID = "TwoLayerRectanglePCBModuleID"        # 板框自己 ⇒ **不是元件** ✗（不读焊盘 ✓）
BAD_CAP = 8                                       # 报告封顶 ✓（刷屏的报告等于没报告 ✗）


def num(el, key, d=0.0):
    try:
        return float(el.get(key) or d)
    except (TypeError, ValueError):
        return d


def el_box(el):
    """图元**中心 ＋ 包围盒**（局部用户单位 ✓，**不含**祖先 transform ✓）；认不出 ⇒ (None, None) ✓"""
    t = tag(el)
    try:
        if t == "circle":
            cx, cy, r = num(el, "cx"), num(el, "cy"), num(el, "r")
            return (cx, cy), (cx - r, cy - r, cx + r, cy + r)
        if t == "ellipse":
            cx, cy, rx, ry = num(el, "cx"), num(el, "cy"), num(el, "rx"), num(el, "ry")
            return (cx, cy), (cx - rx, cy - ry, cx + rx, cy + ry)
        if t == "rect":
            x, y, w, h = num(el, "x"), num(el, "y"), num(el, "width"), num(el, "height")
            return (x + w / 2.0, y + h / 2.0), (x, y, x + w, y + h)
        if t == "line":
            x1, y1, x2, y2 = num(el, "x1"), num(el, "y1"), num(el, "x2"), num(el, "y2")
            return ((x1 + x2) / 2.0, (y1 + y2) / 2.0), (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        if t in ("path", "polygon", "polyline"):
            v = PB._path_pts(el.get("d")) if t == "path" else PB._nums(el.get("points"))
            pts = [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
            if not pts:
                return None, None
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0), (min(xs), min(ys), max(xs), max(ys))
    except (TypeError, ValueError):
        return None, None
    return None, None


def copper_shapes(root):
    """pcb svg 里的**每个图元**：它在哪层 ✓、id 是什么 ✓、在哪（**走完 transform ✓**，用户单位 ✓）

    ⇒ `([{layer,id,tag,c,box,r,sw,name}], 认不出的清单 ✓)`
    ★ 层 = **最近的**祖先 `<g id="copper0|copper1|silkscreen|outline">` ✓；
      没有这类祖先 ⇒ `"(root)"` ✓（报出来，别当成铜 ✗）。
    """
    out, bad = [], []

    def walk(el, m, layer):
        for c in el:
            t = tag(c)
            if t == "defs":
                continue
            if t == "svg":                       # 嵌套视口没处理 ⇒ 明说 ✓（别当没事 ✗）
                bad.append("嵌套 <svg> 视口（未处理 ✗）")
                continue
            mc = PB.mul(m, PB.parse_tf(c.get("transform"))) if c.get("transform") else m
            eid = c.get("id") or ""
            lay = eid if eid in ("copper0", "copper1", "silkscreen", "outline") else layer
            if t == "g":
                walk(c, mc, lay)
                continue
            c0, b0 = el_box(c)
            if c0 is None:
                # ★ 只对**有 id**的图元报错 ✓（无 id 的 = 铜箔/走线/装饰 ✓，跳过就好 ✓ ——
                #   面包板 svg 里有几百条无 id 的 path ✗，全报到报告里就没法看了 ✗）
                if eid:
                    bad.append("<%s id=%s> 认不出中心 ✗" % (t, eid))
                continue
            xs, ys = [], []
            for u in (b0[0], b0[2]):             # 包围盒**取四角**搬 ⇒ 能容旋转 ✓
                for v in (b0[1], b0[3]):
                    p = PB.apply(mc, u, v)
                    xs.append(p[0])
                    ys.append(p[1])
            sw = PB._nums(c.get("stroke-width") or "")
            out.append(dict(layer=lay, id=eid, tag=t, c=PB.apply(mc, c0[0], c0[1]),
                            box=(min(xs), min(ys), max(xs), max(ys)),
                            r=num(c, "r") or None, sw=(sw[0] if sw else None),
                            name=c.get("connectorname") or ""))

    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), "(root)")
    return out, bad


def pcb_pads(root, connectors=()):
    """按 **connector id** 把焊盘归好 ✓

    ⇒ `({cid: pad}, 没人认领的铜（焊盘形状 ✓）, 认不出的清单 ✓)`
    ★ 同一 connector 多个候选（如通孔件在 copper0/copper1 各画一份 ✓）⇒ 取**铜层**里的 ✓，
      层数不同 ⇒ `layer="both"` ✓；位置必须**一致** ✓（不一致就该人看 ✓，别硬挑一个 ✗）。
    """
    shapes, bad = copper_shapes(root)
    cand = {}
    for s in shapes:
        m = re.match(r"^(connector\d+)([A-Za-z]*)$", s["id"])
        if not m:
            continue
        cid, suf = m.group(1), m.group(2).lower()
        if suf not in PAD_SUF:
            bad.append("id=`%s` 的后缀 `%s` 不认识（**不猜** ✗）" % (s["id"], suf))
            continue
        cand.setdefault(cid, []).append((PAD_SUF.index(suf), s))
    got = {}
    for cid, lst in sorted(cand.items(), key=lambda kv: int(kv[0][9:])):
        lst.sort(key=lambda x: x[0])
        win = [s for pr, s in lst if pr == lst[0][0]]
        cop = [s for s in win if s["layer"] in ("copper0", "copper1")]
        if cop:
            win = cop
        c0 = win[0]["c"]
        if max(abs(s["c"][0] - c0[0]) + abs(s["c"][1] - c0[1]) for s in win) > 0.02:
            bad.append("%s 有 %d 个候选、位置还不一致 ✗ ⇒ 请人工看" % (cid, len(win)))
        lay = "both" if len({s["layer"] for s in win}) > 1 else win[0]["layer"]
        s = win[0]
        got[cid] = dict(cid=cid, layer=lay, shape=s["tag"], c=s["c"], box=s["box"],
                        r=s["r"], sw=s["sw"], name=s["name"], src=s["id"], n_cand=len(win))
    for cid in connectors:
        if cid not in got:
            bad.append("%s 在 pcb svg 里**找不到焊盘** ✗" % cid)
    extra = [s for s in shapes if not re.match(r"^connector\d+", s["id"])
             and s["layer"] in ("copper0", "copper1") and s["tag"] in PADLIKE]
    n_track = len([s for s in shapes if s["layer"] in ("copper0", "copper1") and s["tag"] not in PADLIKE])
    return got, extra, bad, n_track


# ── 从 .fzz 取实例 ──────────────────────────────────────────────────────────
def read_fzz(zpath):
    """读 `.fzz`：pcbView 里的零件实例 ✓（件定义**优先用包里内嵌的** ✓，core 件回落到磁盘 ✓）"""
    z = zipfile.ZipFile(zpath)
    fzname = [n for n in z.namelist() if n.endswith(".fz")][0]
    root = ET.fromstring(z.read(fzname))
    packed_fzp, packed_svg = {}, {}
    for n in z.namelist():
        if n.startswith("part.") and n.endswith(".fzp"):
            packed_fzp[n[len("part."):-len(".fzp")]] = z.read(n).decode("utf-8", "replace")
        elif n.endswith(".svg"):
            packed_svg[n] = z.read(n).decode("utf-8", "replace")
    board = None
    for b in root.iter("board"):
        board = (b.get("width"), b.get("height"), b.get("moduleId"))
    out = []
    for el in root.iter("instance"):
        mid = el.get("moduleIdRef") or ""
        if mid.startswith("Wire"):
            continue
        vw = next((c for c in el if tag(c) == "views"), None)
        if vw is None:
            continue
        pv = next((c for c in vw if tag(c) == "pcbView"), None)
        if pv is None:
            continue
        g = next((c for c in pv if tag(c) == "geometry"), None)
        if g is None:                     # 不在 PCB 上（例如只在原理图的件 ✓）
            continue
        fzp_text = packed_fzp.get(mid)
        fzp_path = (el.get("path") or "").replace("/", os.sep) or None
        if fzp_text is None and fzp_path and os.path.isfile(fzp_path):
            fzp_text = open(fzp_path, encoding="utf-8").read()
        if fzp_text is None:
            out.append(dict(title=(el.findtext("title") or "").strip(), moduleId=mid, fzp=None,
                            loc=(float(g.get("x") or 0), float(g.get("y") or 0)), M=PB.tf_of(g),
                            geo=dict(g.attrib),
                            why="**找不到件定义** ✗（包里没有、磁盘上也没有：%s）" % fzp_path))
            continue
        fr = ET.fromstring(fzp_text)
        pvz = fr.find(".//pcbView")
        lay = pvz.find("layers") if pvz is not None else None
        image = lay.get("image") if lay is not None else None
        connectors = [c.get("id") for c in fr.findall(".//connectors/connector") if c.get("id")]
        names = {c.get("id"): (c.get("name") or "") for c in fr.findall(".//connectors/connector")}
        svg_text, src = None, "（**没找到 svg** ✗）"
        want = os.path.basename(image or "")
        for n, t in packed_svg.items():
            if want and n.endswith(want):
                svg_text, src = t, n
                break
        if svg_text is None and fzp_path and image:
            sib = os.path.join(os.path.dirname(fzp_path),
                               "svg.pcb.%s_pcb.svg" % os.path.basename(fzp_path)[5:-4])   # part.<id>.fzp ✓
            if os.path.isfile(sib):
                svg_text, src = open(sib, encoding="utf-8").read(), sib
        if svg_text is None:
            cand = PB.resolve_svg(fzp_path, image) if fzp_path else None
            if cand:
                svg_text, src = open(cand, encoding="utf-8").read(), cand
        out.append(dict(title=(el.findtext("title") or "").strip(), moduleId=mid, fzp=fr,
                        image=image, connectors=connectors, names=names,
                        svg_text=svg_text, src=src, loc=(float(g.get("x") or 0), float(g.get("y") or 0)),
                        M=PB.tf_of(g), geo=dict(g.attrib)))
    return out, board


def part_pads(part):
    """实例的焊盘 ⇒ **绝对 sketch 单位** ✓（`loc + M·k·(u − vb0)` ✓ 与渲染器同一套矩阵数学 ✓）"""
    if part.get("svg_text") is None:
        return None, None, ["`%s` 的 svg %s" % (part["title"], part["src"])], 0
    root = ET.fromstring(part["svg_text"])
    k, (ox, oy) = PB.svg_k(root)
    if k is None:
        return None, None, ["`%s` 的 svg 尺寸算不出（`width` 没单位 ✗）⇒ 焊盘位置换算不了 ✗" % part["title"]], 0
    pads, extra, bad, n_track = pcb_pads(root, part["connectors"])
    M = part["M"]

    def abs_of(p):                       # 用户单位 → 绝对 sketch 单位 ✓
        return PB.apply(M, (p[0] - ox) * k, (p[1] - oy) * k)

    out = {}
    for cid, p in pads.items():
        c = abs_of(p["c"])
        w = (p["box"][2] - p["box"][0]) * k / SK           # mm ✓
        h = (p["box"][3] - p["box"][1]) * k / SK
        hole = 2 * p["r"] * k / SK if p["r"] else None
        ring = p["sw"] * k / SK if p["sw"] else None
        if hole and ring:
            # ★ 通孔焊盘：svg 里的 `circle` 是**孔** ✓、`stroke-width` 是**环宽** ✓
            #   ⇒ 报给用户看的尺寸应当是**盘的外径** = 孔 + 环 ✓（照实画出来就是那么大 ✓）
            w = h = hole + ring
        # ★ `absbox`：焊盘在 sketch 绝对坐标下的**矩形** ✓（`pcb_check.py` 判"线端是不是
        #   落在焊盘上"要用它 ✓）—— 取局部包围盒**四角**过矩阵再取 min/max ✓（能容旋转 ✓）
        cor = [PB.apply(M, (u - ox) * k, (v - oy) * k)
               for u in (p["box"][0], p["box"][2]) for v in (p["box"][1], p["box"][3])]
        out[cid] = dict(p, abs=(part["loc"][0] + c[0], part["loc"][1] + c[1]),
                        absbox=(part["loc"][0] + min(v[0] for v in cor),
                                part["loc"][1] + min(v[1] for v in cor),
                                part["loc"][0] + max(v[0] for v in cor),
                                part["loc"][1] + max(v[1] for v in cor)),
                        size_mm=(w, h), hole_mm=hole, ring_mm=ring,
                        nm=part["names"].get(cid, ""))
    ex = [dict(s, abs=tuple(part["loc"][i] + abs_of(s["c"])[i] for i in (0, 1))) for s in extra]
    return out, ex, bad, n_track


# ── 对账表（**出处写在表里** ✓；FAIL = 去查清"谁错了" ✓ 不是"改期望值凑过" ✗）────
SPEC = [
    ("CH32V003F4U6", 21, [("connector0", "connector1", 0.40, "QFN20 脚距（数据手册封装图）")]),
    ("BAS70BRW_SOT363_1", 6, [("connector0", "connector1", 0.65, "SOT-363 脚距（数据手册）")]),
    ("WS2812B_1010_1", 4, [("connector0", "connector1", 0.85, "1010 land pattern（本库 gen_part.py）")]),
    ("SH-1.0-3P-V", 3, [("connector0", "connector1", 1.00, "SH1.0 脚距（图纸 DIM）")]),
    ("NFC_Coil_20mm_6T_0p2_1", 2, [("connector0", "connector1", 7.40, "线圈两端（本库 pcb svg）")]),
    ("lijaenargnn-ResistorModuleID", 2, [("connector0", "connector1", 1.70,
                                         "core `pcb/SMD_0603.svg`（2026-09-30 实测 ✓）")]),
    ("a9b4194c-7731-4413-b04e-5c544638ef28CapacitorModuleID", 2,
     [("connector0", "connector1", 1.70,
       "core `pcb/SMD_0603.svg`（2026-09-30 实测 ✓；与 R **同一个 svg** ✓）")]),
]


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    zpath = argv[0]
    only = argv[argv.index("--part") + 1] if "--part" in argv else None
    spec = "--spec" in argv
    parts, board = read_fzz(zpath)
    print("== %s ==" % os.path.basename(zpath))
    print("   板：%s × %s（%s）" % (board[0], board[1], board[2]) if board else "   板：（没读到 <board>）")
    board_loc = next((p.get("loc") for p in parts
                      if p.get("moduleId") == "TwoLayerRectanglePCBModuleID"), None)
    if board_loc:
        print("   板原点（PCB1 实例 loc）= (%.3f, %.3f) sketch 单位" % board_loc)
    n_bad = 0
    for p in parts:
        if only and p["title"] != only:
            continue
        if p.get("moduleId") == BOARD_MID:
            print("\n## %-8s **板框自己** ✓（不是元件 ⇒ 不读焊盘 ✓；尺寸看上面 `<board>` ✓）" % p["title"])
            continue
        if (p.get("moduleId") or "").startswith("Breadboard"):
            print("\n## %-8s **面包板件** ⇒ PCB 视图不参与 ✓（Fritzing 把实例留在各视图里 ✓、不画）" % p["title"])
            continue
        if p.get("fzp") is None:
            print("\n## %-8s **%s**" % (p["title"], p["why"]))
            n_bad += 1
            continue
        pads, extra, bad, n_track = part_pads(p)
        if pads is None:
            print("\n## %-8s %s" % (p["title"], "; ".join(bad)))
            n_bad += len(bad)
            continue
        print("\n## %-8s %-26s %2d 脚 / %2d 焊盘 %s  image=%s"
              % (p["title"], p["moduleId"][:26], len(p["connectors"]), len(pads),
                 "✓" if len(pads) == len(p["connectors"]) else "✗ 数对不上", p["image"]))
        print("   件 svg 用了：%s（%d 字节；铜层走线条数 %d）" % (p["src"], len(p["svg_text"]), n_track))
        print("   %-22s %-4s %-9s %-22s %-16s %s"
              % ("焊盘 id", "脚名", "层", "中心 sketch(绝对)", "相对板角 mm", "尺寸 mm"))
        for cid, q in sorted(pads.items(), key=lambda kv: int(kv[0][9:])):
            rel = ""
            if board_loc:
                rel = "%.2f, %.2f" % ((q["abs"][0] - board_loc[0]) / SK, (q["abs"][1] - board_loc[1]) / SK)
            sz = "%.2f × %.2f" % q["size_mm"]
            if q["hole_mm"]:
                sz += "（孔 Ø%.2f 环 %.2f）" % (q["hole_mm"], q["ring_mm"] or 0)
            print("   %-22s %-4s %-9s %-22s %-16s %s"
                  % (q["src"], q["nm"], q["layer"],
                     "%.3f, %.3f" % q["abs"], rel, sz))
        if extra:
            print("   ⚠️ **没人认领的铜**（无 connector id ⇒ 布线要当障碍 ✓）：%d 块" % len(extra))
            for s in extra[:8]:
                print("      <%s> 绝对(%.3f, %.3f) sketch 单位 @ %s"
                      % (s["tag"], s["abs"][0], s["abs"][1], s["layer"]))
        for i, b in enumerate(bad):
            if i < BAD_CAP:
                print("   ✗ %s" % b)
            elif i == BAD_CAP:
                print("   …（认不出的图元共 %d 条，只列前 %d ✓）" % (len(bad), BAD_CAP))
        n_bad += len(bad)

    if spec:
        print("\n== 对账（`SPEC` 表；FAIL ⇒ 查清谁错了 ✓ 不是改期望值 ✗）==")
        by_mid = {}
        for p in parts:
            if p.get("fzp") is not None and p["title"] not in by_mid:
                by_mid[p["moduleId"]] = p
        for mid, n_exp, pairs in SPEC:
            p = by_mid.get(mid)
            if p is None:
                print("   %-22s —— 本 sketch 里没有这件" % mid[:22])
                continue
            pads, _e, _b, _t = part_pads(p)
            if pads is None:
                print("   %-22s ✗ 读不出焊盘" % mid[:22])
                n_bad += 1
                continue
            ok = (len(pads) == n_exp)
            print("   %-22s 脚数 %2d / 期望 %2d %s" % (mid[:22], len(pads), n_exp, "✓" if ok else "✗"))
            n_bad += 0 if ok else 1
            for a, b, want, why in pairs:
                if a not in pads or b not in pads:
                    print("      %s↔%s ✗ 焊盘缺失" % (a, b))
                    n_bad += 1
                    continue
                pa, pb = pads[a]["abs"], pads[b]["abs"]
                d = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5 / SK
                if want is None:
                    print("      %s↔%s = **%.3f mm**（实测值 ⇒ 写进 `SPEC` 当基线 ✓）  [%s]"
                          % (a, b, d, why))
                elif abs(d - want) <= 0.01:
                    print("      %s↔%s = %.3f mm ✓（期望 %.2f）  [%s]" % (a, b, d, want, why))
                else:
                    print("      %s↔%s = %.3f mm ✗（期望 %.2f）  [%s] ⇒ **查** !" % (a, b, d, want, why))
                    n_bad += 1
    print("\n判定：%s（问题 %d 条）" % ("✓ 干净" if n_bad == 0 else "✗ 见上", n_bad))
    return 1 if n_bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
