# -*- coding: utf-8 -*-
r"""★ 前置闸门：**摆位先于入网**（规则正文：库仓 `docs/breadboard-routing-rules.md` §A.4 ＋ §A.5 ✓）

用户 2026-10-15 定 ✓：「**入网的前提是摆位到位，而不是随意都可以入网**」✓ ＋
「**物理上管脚没有插入孔……能把物理模型放在第一位吗？**」✓
⇒ 布线**之前**跑本脚本 ✓：不过 ⇒ **不许布线** ✗（`bb_route_guarded.py` 挂在 `bb_route4` 前 ✓）。

五条判据（★ **判据 = 几何** ✓，✗ 不是"有没有 `<connect>`"✗ —— §A.5 第 4 条 ✓）：

  ① 每个脚**恰好**声明了**一颗真实的孔** ✓（没声明 / 孔名不在板上 ⇒ 没到位 ✗）
  ② **接点**落孔 ✓ —— 有 `<leg>` 的脚用**腿端**（＝ 那只脚真正伸进孔里的点 ✓，
     `render_bb` 判"脚落在孔上"用的是**同一份数据** ✓）；没有 `<leg>` 的退化为**盘心**
     （svg 里 `connectorNpin` 元素的中心 ✓ ＝ Fritzing `calcTerminalPoint` 的口径 ✓）；
     离声明的那颗孔 ≤ 容差 ✓
  ③ **盘心落孔** —— ★ 只作**报告** ✗、**不作判据** ✓：**橡皮筋引线件**（`.fzp` 写了 `legId`）
     的接点就是**腿端** ✓，盘心是图形上那个"盘"的位置、离孔天然差 7~10 mm ✓。
     证据 ✓：**用户自己手做**的 `pixel-breadboard43_byHand.fzz` —— C1/C2/R1 六只脚
     **腿端 6/6 落孔（≤0.005 mm ✓）**、盘心差 7.5 mm ✗；U1/D3/J1/J2/LED2/L1 **无引线**
     ⇒ 盘心 38/38 落孔（0.000 mm ✓）。
  ④ 一个孔**只能被一只脚**占用 ✓（= `bb_probe` ⑦ 同口径 ✓）
  ⑤ **一 bus 一网** ✓（= `bb_probe` ①b 同口径 ✓）：同一列 5 孔是同一块铜片 ⇒
     两个网 = **实物短接** ✗

几何一律**调库里的同一份实现** ✓：孔坐标 `bb_compare.hole_xy` ✓（与 `bb_probe`／`bb_compare`
同源 ✓）、元件盘心与 svg 尺寸 `part_box` ✓（与 `bb_route4`／`render_pcb` 同源 ✓）——
✗ 本脚本**不自己造一套几何** ✗。

★ 已知**豁免** ✓：**裸焊盘**（`EPAD` ✓）本来就不插孔 ✓ ⇒ 判据取「既没落孔、**也没接线**」✗
  （✗ 不是"没落孔"✗ —— 那会把 EPAD 误报 ✗）。

用法 ✓：
    py -3.13 tools\bb_precheck.py <sketch.fzz> [--nets=<nets.py>] [--tol-mm=0.6] [--part=R1,R2]
退出码：0 = 摆位到位（允许布线 ✓）｜1 = 没到位（不准布线 ✗）｜2 = 用法错
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bb_compare as BC                                             # noqa: E402
import part_box as pbox                                             # noqa: E402

SK_MM = 25.4 / 90.0        # 1 sketch 单位 = 1/90 in ✓（唯一口径见 AGENTS §15 ✓）
MM = 1.0 / SK_MM
DEFAULT_TOL_MM = 0.6       # ★ 0.6 mm = 孔距 2.54 mm 的 24% ✓ ⇒ 不会与邻孔混淆 ✓；
                           #   而 R0603 那种"图形跨度 4.098 孔"的件第二脚天然偏 0.25 mm ✓ ⇒ 放得过 ✓
SKIP = ("Breadboard", "Logo", "Ground", "NetLabel", "TXT", "PCB", "Wire")


def _tag(e):
    return e.tag.split("}")[-1]


def _child(e, n):
    for c in e:
        if _tag(c) == n:
            return c
    return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_ANCHOR_CACHE = {}


def anchors(fzp_path):
    """⇒ {connectorId: (x, y)} —— svg 里 `connectorNpin` 元素的**中心**（局部 sketch 单位 ✓）

    ★ 这就是 Fritzing 的 `calcTerminalPoint` 口径 ✓（`fsvgrenderer.cpp:757-799`：
      terminalId 为空时 ⇒ 取 `svgId` 元素的 bounds 中心 ✓；我们的 `.fzp` 面包板
      `<p>` 只写 `svgId="connectorNpin" legId="connectorNleg"`、**不写 terminalId** ✓）
      ⇒ 与 `bb_probe`／`bb_route4` 的"盘心"**同一份几何** ✓。
    """
    if fzp_path in _ANCHOR_CACHE:
        return _ANCHOR_CACHE[fzp_path]
    out = {}
    if fzp_path and os.path.isfile(fzp_path):
        root = ET.parse(fzp_path).getroot()
        lay = root.find(".//breadboardView/layers")
        img = lay.get("image") if lay is not None else None
        svg = pbox.resolve_svg(fzp_path, img) if img else None
        if svg:
            sroot = ET.parse(svg).getroot()
            wmm, _hmm = pbox.canvas_mm(sroot.attrib)
            vb = pbox._nums(sroot.get("viewBox"))
            if wmm and len(vb) == 4 and vb[2]:
                k = wmm / vb[2] * MM
                ox, oy = vb[0], vb[1]

                def walk(el, m):
                    for c in el:
                        t = c.get("transform")
                        mc = pbox.mul(m, pbox.parse_tf(t)) if t else m
                        eid = c.get("id") or ""
                        mm = re.match(r"^(connector\d+)pin$", eid)
                        if mm:
                            tg = _tag(c)
                            if tg == "rect":
                                p = (_num(c.get("x")) + _num(c.get("width")) / 2.0,
                                     _num(c.get("y")) + _num(c.get("height")) / 2.0)
                            elif tg in ("circle", "ellipse"):
                                p = (_num(c.get("cx")), _num(c.get("cy")))
                            elif tg == "line":
                                p = ((_num(c.get("x1")) + _num(c.get("x2"))) / 2.0,
                                     (_num(c.get("y1")) + _num(c.get("y2"))) / 2.0)
                            else:
                                p = None
                            if p:
                                a = pbox.apply(mc, p[0], p[1])
                                out[mm.group(1)] = ((a[0] - ox) * k, (a[1] - oy) * k)
                        walk(c, mc)
                walk(sroot, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    _ANCHOR_CACHE[fzp_path] = out
    return out


def holes_of(sketch_text):
    """⇒ (board_mi, {孔名: (x,y)}, {孔名: bus根}) ✓（板子自己的 .fzp ＝ Fritzing 的口径 ✓）"""
    sroot = ET.fromstring(sketch_text)
    board = next((e for e in sroot.iter("instance")
                  if "breadboard" in (e.get("moduleIdRef") or "").lower()
                  and not (e.get("moduleIdRef") or "").startswith("Wire")), None)
    if board is None:
        return None
    broot = ET.parse((board.get("path") or "").replace("/", os.sep)).getroot()
    ids = {c.get("id") for c in broot.iter("connector")
           if re.fullmatch(r"pin\w+", c.get("id") or "")}
    hole = {}
    for h in sorted(ids):
        xy = BC.hole_xy(h)
        if xy:
            hole[h] = xy
    par = {}

    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for b in broot.iter("bus"):
        mem, seen = [], set()
        for d in b.iter():
            if d is b:
                continue
            for k, v in d.attrib.items():
                if k in ("id", "connectorId", "connector", "member") and v and v not in seen:
                    seen.add(v)
                    mem.append(v)
        for m in mem[1:]:
            ra, rb = find(mem[0]), find(m)
            if ra != rb:
                par[ra] = rb
    return board, hole, {h: find(h) for h in hole}

def main(argv):
    pos = [a for a in argv if not a.startswith("--")]
    if not pos:
        print(__doc__)
        return 2
    tol, only, nets_path = DEFAULT_TOL_MM, None, None
    for a in argv:
        if a.startswith("--tol-mm="):
            tol = float(a.split("=", 1)[1])
        elif a.startswith("--part="):
            only = {s.strip() for s in a.split("=", 1)[1].split(",") if s.strip()}
        elif a.startswith("--nets="):
            nets_path = a.split("=", 1)[1]

    z = zipfile.ZipFile(pos[0])
    text = z.read([n for n in z.namelist() if n.endswith(".fz")][0]).decode("utf-8")
    got = holes_of(text)
    if got is None:
        print("✗ 找不到面包板实例 ✗")
        return 1
    board, hole, hole_bus = got
    bmi = board.get("modelIndex").strip()
    sroot = ET.fromstring(text)

    net_of_pin = {}
    if nets_path:
        import projdata as PD
        for net, pins in PD.load(nets_path, need=("NETS",)).NETS.items():
            for ref, pname in pins:
                net_of_pin[(str(ref), str(pname))] = net

    nopad, miss, notreal, far, farpin, exempt = [], [], [], [], [], []
    dup, plug_net, n_inst = {}, {}, 0
    for e in sroot.iter("instance"):
        mid = e.get("moduleIdRef") or ""
        if mid.startswith("Wire") or e is board:
            continue
        ttl = (e.findtext("title") or "").strip()
        if any(ttl.startswith(s) for s in SKIP):
            continue
        if only and ttl not in only:
            continue
        bv = _child(_child(e, "views"), "breadboardView")
        if bv is None:
            continue
        n_inst += 1
        g = _child(bv, "geometry")
        if g is None:
            continue
        loc = (_num(g.get("x")), _num(g.get("y")))
        tf = pbox.tf_of(g)
        fzp = (e.get("path") or "").replace("/", os.sep)
        anc = anchors(fzp)
        name2cid = {}
        if os.path.isfile(fzp):
            for c in ET.parse(fzp).getroot().iter("connector"):
                if c.get("name"):
                    name2cid[c.get("name")] = c.get("id")
        for cm in bv.iter("connector"):
            cid = cm.get("connectorId")
            key = "%s.%s" % (ttl, cid)
            allc = list(cm.iter("connect"))
            tg = [c.get("connectorId") for c in allc
                  if (c.get("layer") or "") == "breadboardbreadboard"]
            # ★ 豁免（2026-10-15 ✓）：**裸焊盘**（如 `U1` 的 `EPAD` ✓）本来就不插孔 ✓
            #   ⇒ 判据用「**既没落孔、也没接线**」✗（✗ 不是"没落孔"✗ —— 那会把 EPAD 误报 ✗）
            if not allc:
                nopad.append(key)                        # 既没落孔、也没接线 ⇒ 没到位 ✗
                continue
            if not tg:
                exempt.append(key)                       # 接了导线、但没插孔 ⇒ 豁免 ✓
                continue
            if len(tg) != 1:
                miss.append("%s（声明 %d 个孔 ✗）" % (key, len(tg)))
                continue
            H = hole.get(tg[0])
            if H is None:
                notreal.append("%s→%s" % (key, tg[0]))
                continue
            lt = None                                     # ② 腿端（件自己记的那条 <leg> 末点 ✓）
            cg, lg = _child(cm, "geometry"), _child(cm, "leg")
            if cg is not None and lg is not None:
                pt = list(lg.iter("point"))
                if pt:
                    p = pbox.apply(tf, _num(cg.get("x")) + _num(pt[-1].get("x")),
                                   _num(cg.get("y")) + _num(pt[-1].get("y")))
                    lt = (loc[0] + p[0], loc[1] + p[1])
            pb = None                                     # ③ 盘心（Fritzing 的连接点基准 ✓）
            if cid in anc:
                p = pbox.apply(tf, anc[cid][0], anc[cid][1])
                pb = (loc[0] + p[0], loc[1] + p[1])

            def _mm(p):
                return None if p is None else \
                    (((p[0] - H[0]) ** 2 + (p[1] - H[1]) ** 2) ** 0.5) * SK_MM
            d_leg, d_pin = _mm(lt), _mm(pb)
            d_eff = d_pin if d_leg is None else (d_leg if d_pin is None else min(d_leg, d_pin))
            if d_eff is not None and d_eff > tol:
                far.append((key, tg[0], d_eff, d_leg, d_pin))
            if d_pin is not None and d_pin > tol:
                farpin.append((key, tg[0], d_pin))
            dup.setdefault(tg[0], []).append(key)
            nm = net_of_pin.get((ttl, cid))
            if nm is None:
                for pname, c2 in name2cid.items():
                    if c2 == cid:
                        nm = net_of_pin.get((ttl, pname))
                        break
            if nm:
                plug_net.setdefault(tg[0], set()).add(nm)

    dups = {h: v for h, v in dup.items() if len(v) > 1}
    busnets = {}
    for h, ns in plug_net.items():
        busnets.setdefault(hole_bus.get(h, h), set()).update(ns)
    conn = sorted((str(b), sorted(s)) for b, s in busnets.items() if len(s) > 1)

    print("== 摆位闸门（§A.4 摆位先于入网 ＋ §A.5 物理在前）==  %s" % pos[0])
    print("   件 %d 个 ✓｜板孔 %d 个 ✓｜容差 %.2f mm ✓｜用孔 %d 个 ✓"
          % (n_inst, len(hole), tol, len(dup)))

    def rep(no, name, bad, extra=""):
        print("   %s %s %s%s" % (no, "✗" if bad else "✓", name,
                                  (" = %d —— %s" % (len(bad), extra)) if bad else ""))
        return not bad

    ok = True
    ok &= rep("①", "每个脚都声明了一颗真实的孔", nopad + miss + notreal,
              ", ".join((nopad + miss + notreal)[:6]))
    ok &= rep("②", "腿端（或盘心）落在声明的那颗孔上 ≤ %.2f mm" % tol, far,
              "；".join("%s→%s 差 %.2f mm" % (k, h, d) for k, h, d, _l, _p in far[:6]))
    ok &= rep("④", "一个孔只被一只脚占用", list(dups.items()),
              "；".join("%s←%s" % (h, "+".join(v)) for h, v in list(dups.items())[:4]))
    ok &= rep("⑤", "一 bus 一网（没把两张网并到一起）", conn, str(conn[:3]))
    # ★★ 「盘心」只作**报告**✗ 不作判据 ✓（2026-10-15 实测定 ✓）：
    #   **橡皮筋引线件**（C0603 / core 电阻类 ✓，`.fzp` 写了 `legId` ✓）的接点 = **腿端** ✓；
    #   盘心是图形上那个「盘」的位置 ✓、离孔天然差 7~10 mm ✓ ——
    #   证据 ✓：**用户自己手做**的 `pixel-breadboard43_byHand.fzz`：
    #     C1/C2/R1 六只脚 **腿端 6/6 落孔（≤0.005 mm ✓）**、盘心差 7.5 mm ✗；
    #     U1/D3/J1/J2/LED2/L1 **无引线** ⇒ 盘心 38/38 落孔（0.000 mm ✓）。
    if farpin:
        print("   ③ ✓ 盘心落孔（仅报告 ✓）：%d/%d 只脚 > %.2f mm；最大 %.2f mm"
              % (len(farpin), len(dup), tol, max(d for _k, _h, d in farpin)))
        print("      —— 有 `legId` 的件（%s）接点就是**腿端** ✓，盘心远是正常的 ✓"
              % ", ".join(sorted({k.split(".")[0] for k, _h, _d in farpin})))
    if exempt:
        print("   ✓ 豁免（接导线、不插孔）%d 只：%s" % (len(exempt), ", ".join(exempt[:6])))
    print("⇒ %s **%s**" % ("✓" if ok else "✗",
                          "允许布线（摆位到位 ✓）" if ok else
                          "不准布线（先把脚落到孔上／把重叠的挪开 —— §A.4／§A.5 ✗）"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
