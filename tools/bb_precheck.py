# -*- coding: utf-8 -*-
r"""★ 前置闸门：**摆位先于入网**（规则正文：库仓 `docs/breadboard-routing-rules.md` §A.4 ＋ §A.5 ✓）

用户 2026-10-15 定 ✓：「**入网的前提是摆位到位，而不是随意都可以入网**」✓ ＋
「**物理上管脚没有插入孔……能把物理模型放在第一位吗？**」✓
⇒ 布线**之前**跑本脚本 ✓：不过 ⇒ **不许布线** ✗（`bb_route_guarded.py` 挂在 `bb_route4` 前 ✓）。

七条判据（★ **判据 = 几何** ✓，✗ 不是"有没有 `<connect>`"✗ —— §A.5 第 4 条 ✓）：

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
  ⑥ **脚不能"缩进本体"** ✓（2026-10-16 加 ✓，用户定"加"✓）：同件内**脚与脚的间距**
     必须等于**元件自称的间距** ✓（容差见 `SHAPE_TOL_MM` ✓）——
     起因 = 用户报「`R3.2 位置错误`」✓：实测那只电阻的两只脚在 `.fz` 里被压扁成 **14.266 单位** ✗
     （元件自称 **36.887** ✗）⇒ 画出来的引线**缩进本体** ＋ 拖出一条 **5.9 mm 橡皮筋** ✗
     ＋ ★ **Fritzing 里那只脚的可点位置不对** ✗。✗ ①–⑤ **全都看不见它** ✗（只认"腿端落孔"✓）。
     ⚠ 范围如实 ✓：它抓的是**形状**（脚距）✗，**不抓**整体小平移 ✓（那是"盘心 vs 引脚原点"的固有差 ✓）
     ⇒ 若整体挪了而形状没变 ⇒ **本闸门不报** ✗（那是别的判据的事 ✓）。
  ⑦ **接了导线的脚：导线端点必须真的落在它的接线点上** ✓（2026-10-18 加 ✗，用户点出来的）：
     原来这一支是**无条件豁免** ✗（`if not tg: exempt`）—— 只看"有没有 `<connect>`" ✓，
     **从没核过导线端点到底在哪** ✗ ⇒ 截图上线头偏在焊盘**左上 4.80/2.70 mm**（合成 5.51 mm）
     时，①–⑥ 与 `bb_probe`/`file_sanity` **全部绿** ✗✗ —— 而**物理上就是没接上** ✗。
     ⇒ 现在对每只"接线不插孔"的脚，把它声明的每根导线的**那一端坐标**取出来，
     与它的**接线点**（＝ `anchors()` 算出的 `connectorNpin` 中心，即 Fritzing 的
     `calcTerminalPoint` 口径 ✓）比距离，超 `WIRE_TOL_MM` 就报 ✗。

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

# ★ 本脚本打印中文/✓✗ ⇒ 必须自己重设编码 ✓（✗ 不靠调用方加 `-X utf8` ✗）
#   2026-10-18 实测 ✗：被 `run_checks.py`（`sys.executable` 直起、无 `-X utf8`）调用时，
#   在 Windows GBK 控制台上直接 `UnicodeEncodeError` 崩掉 ✗ ⇒ 闸门红得莫名其妙 ✓。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bb_compare as BC                                             # noqa: E402
import part_box as pbox                                             # noqa: E402

SK_MM = 25.4 / 90.0        # 1 sketch 单位 = 1/90 in ✓（唯一口径见 AGENTS §15 ✓）
MM = 1.0 / SK_MM
DEFAULT_TOL_MM = 0.6       # ★ 0.6 mm = 孔距 2.54 mm 的 24% ✓ ⇒ 不会与邻孔混淆 ✓；
                           #   而 R0603 那种"图形跨度 4.098 孔"的件第二脚天然偏 0.25 mm ✓ ⇒ 放得过 ✓
SHAPE_TOL_MM = 2.0         # ★ ⑥ 的容差 = "**同件内**脚距 vs 元件自称脚距"的**残差** ✓
                           #   （先把每只脚 `geometry − 自称脚位` 的**平均值**减掉 ⇒ 整体平移不算错 ✓
                           #    —— 那正是"盘心 vs 引脚原点"的固有差 ✓）。实测定值 ✓（2026-10-16 ✓）：
                           #   · **用户亲手在 Fritzing 里画的 9 张台架图**：最大 **0.22 mm** ✓（零误报 ✓）
                           #   · 用户认可、明确说"不用改"的 `R1/R2`：**0.50 mm** ✓
                           #   · 用户报"位置错误"的 `R3`（修前）：**3.19 mm** ✗ ⇒ 取 2.0 落在空档里 ✓
                           #   ★ 灵敏度如实 ✓：两脚件"脚距被压扁 P mm" ⇒ 残差 = P/2 ⇒
                           #     本阈值抓的是 **脚距错 ≥ 4 mm** ✗（1 mm 级的小压扁**有意放过**✓ ——
                           #     用户对 `R1` 就判"没问题"✓，机器不该比人更严 ✗）。
WIRE_TOL_MM = 0.10         # ★ ⑦ 的容差 = "导线自己那一端 vs 该脚的接线点" ✓
                           #   取 0.10mm（= 半个线宽）：Fritzing 里手拖的线会**吸附**到引脚上 ✓，
                           #   生成的线是算出来的（误差 ~1e-6）✓ ⇒ 0.10 已经很宽 ✓；
                           #   真出错时是 mm 级（实测那次 5.51mm ✗）⇒ 不会误报也不会漏 ✓。
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


_LEG_CACHE = {}


def leg_tips(fzp_path):
    """⇒ {connectorId: (x, y)} —— svg 里 `connectorNleg` **引线的另一端**（局部 sketch 单位 ✓）

    ★ 为什么 ⑦ 要用它 ✗（2026-10-18 实测 ✓）：**橡皮筋引线件**（`.fzp` 写了 `legId` ✓，
      如 `SC155` 超容 / 核心电阻）—— 导线是接在**引线末端**的 ✓，**不是**焊盘中心 ✗。
      证据 ✓：`BT1` 的 svg 里 `connector0leg` 是 `(8.75,11)→(8.75,13.54)`（往下 2.54mm ✓），
      而实例转了 180° ⇒ 引线末端落在焊盘**上方 2.54mm** ✓；草图里两根线的端点
      正好在那里（`(278.9820, 211.0000)` vs 焊盘 `(278.9820, 219.9998)` ✓）。
      ⇒ 拿焊盘中心去比就会**误报 2.54mm** ✗（第一版就误报了 ✓）。
    ★ 取"离焊盘**远**的那个端点" ✓（line 的首/尾哪个都行 ✓，不赌书写次序 ✓）。
    """
    if fzp_path in _LEG_CACHE:
        return _LEG_CACHE[fzp_path]
    out = {}
    if fzp_path and os.path.isfile(fzp_path):
        root = ET.parse(fzp_path).getroot()
        has_leg = set()
        for c in root.iter("connector"):
            for p in c.iter("p"):
                if p.get("layer") == "breadboard" and p.get("legId"):
                    has_leg.add(c.get("id"))
        lay = root.find(".//breadboardView/layers")
        img = lay.get("image") if lay is not None else None
        svg = pbox.resolve_svg(fzp_path, img) if img else None
        if svg and has_leg:
            sroot = ET.parse(svg).getroot()
            wmm, _hmm = pbox.canvas_mm(sroot.attrib)
            vb = pbox._nums(sroot.get("viewBox"))
            if wmm and len(vb) == 4 and vb[2]:
                k = wmm / vb[2] * MM
                ox, oy = vb[0], vb[1]
                anc = anchors(fzp_path)

                def walk(el, m):
                    for c in el:
                        t = c.get("transform")
                        mc = pbox.mul(m, pbox.parse_tf(t)) if t else m
                        mm = re.match(r"^(connector\d+)leg$", c.get("id") or "")
                        if mm and _tag(c) == "line":
                            a = pbox.apply(mc, _num(c.get("x1")), _num(c.get("y1")))
                            b = pbox.apply(mc, _num(c.get("x2")), _num(c.get("y2")))
                            a = ((a[0] - ox) * k, (a[1] - oy) * k)
                            b = ((b[0] - ox) * k, (b[1] - oy) * k)
                            pin = anc.get(mm.group(1))
                            if pin:
                                da = (a[0] - pin[0]) ** 2 + (a[1] - pin[1]) ** 2
                                db = (b[0] - pin[0]) ** 2 + (b[1] - pin[1]) ** 2
                                out[mm.group(1)] = a if da > db else b
                        walk(c, mc)
                walk(sroot, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    _LEG_CACHE[fzp_path] = out
    return out


def holes_of(sketch_text):
    """⇒ (board_mi, {孔名: (x,y)}, {孔名: bus根}) ✓（板子自己的 .fzp ＝ Fritzing 的口径 ✓）"""
    sroot = ET.fromstring(sketch_text)
    # ★ 2026-10-19 修 ✗：原来只判「moduleIdRef 里含 `breadboard`」✗ ——
    #   `BreadboardLogoTextModuleID`（用户加了 12 个文字标签 ✓）也含 ✓ ⇒ 选错 ✗，
    #   而它的 `path` 是 Qt 资源路径 `:/resources/parts/core/breadboardlogotext.fzp` ✗
    #   ⇒ `ET.parse` 直接报 `OSError: ':\resources\…'` ✗，**整个闸门跑不起来** ✗。
    board = next((e for e in sroot.iter("instance")
                  if "breadboard" in (e.get("moduleIdRef") or "").lower()
                  and "logo" not in (e.get("moduleIdRef") or "").lower()
                  and "text" not in (e.get("moduleIdRef") or "").lower()
                  and not (e.get("moduleIdRef") or "").startswith("Wire")), None)
    if board is None:
        return None
    broot = ET.parse((board.get("path") or "").replace("/", os.sep)).getroot()
    ids = {c.get("id") for c in broot.iter("connector")
           if re.fullmatch(r"pin\w+", c.get("id") or "")}
    # ★★ 孔位要带**这张图自己的板位偏移** ✓（2026-10-16 根治 ✓）：
    #   板子一平移（用户为了把某件靠最左 ✓），写死的孔位就整体错位 ✗
    #   ⇒ 会报一堆"腿端差 3.59mm"的**假报警** ✗（实测 ✓）。缺省 (0,0) = 老行为 ✓。
    off = BC.board_off_root(sroot)
    hole = {}
    for h in sorted(ids):
        xy = BC.hole_xy(h, off)
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

def wire_ends_of(sroot):
    """⇒ {(件 modelIndex, 脚 connectorId): [(导线标题, 该导线**这一端**的坐标)]} ✓

    ★ 导线的两端：`connector0` = (x + x1, y + y1)、`connector1` = (x + x2, y + y2) ✓
      （`x1/y1` 多数件是 0 ✓，但不能假定 0 ✗ —— 实测见过非零的 ✓）。
    ★ 为什么需要它 ✗（2026-10-18 ✓）：`⑦` 要判的是**物理上碰没碰上** ✓，
      ✗ 不是"`<connect>` 里写没写"✗（`bb_probe` 已经管了那一半 ✓）。
    """
    out = {}
    for e in sroot.iter("instance"):
        if not (e.get("moduleIdRef") or "").startswith("Wire"):
            continue
        ttl = (e.findtext("title") or "").strip()
        bv = _child(_child(e, "views"), "breadboardView")
        g = _child(bv, "geometry") if bv is not None else None
        if g is None:
            continue
        bx, by = _num(g.get("x")), _num(g.get("y"))
        ends = {"connector0": (bx + _num(g.get("x1")), by + _num(g.get("y1"))),
                "connector1": (bx + _num(g.get("x2")), by + _num(g.get("y2")))}
        for cm in bv.iter("connector"):
            p = ends.get(cm.get("connectorId"))
            if p is None:
                continue
            for cc in cm.iter("connect"):
                out.setdefault((cc.get("modelIndex"), cc.get("connectorId")), []).append((ttl, p))
    return out


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
    opened = []                         # 网表里就没有这只脚 ⇒ 悬空是设计如此 ✓（只报告 ✓）
    dup, plug_net, n_inst = {}, {}, 0
    sh, sh_ck, sh_zero = [], [0], [0]   # ⑥：脚距残差／参与比对的脚数／`(0,0)` 跳过数 ✓
    wired, wire_noref = [], []          # ⑦：接线脚的（导线, 偏差 mm）／拿不到接线点的脚 ✓
    wends = wire_ends_of(sroot)         # ⑦：导线两端坐标表 ✓（上面那个函数 ✓）
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
        g6 = []                        # ⑥ 用：本件每只脚的 `(geometry − 自称脚位)` ✓
        g = _child(bv, "geometry")
        if g is None:
            continue
        loc = (_num(g.get("x")), _num(g.get("y")))
        tf = pbox.tf_of(g)
        fzp = (e.get("path") or "").replace("/", os.sep)
        anc = anchors(fzp)
        lg_tips = leg_tips(fzp)
        name2cid = {}
        if os.path.isfile(fzp):
            for c in ET.parse(fzp).getroot().iter("connector"):
                if c.get("name"):
                    name2cid[c.get("name")] = c.get("id")

        def _net_of(ttl, cid):
            """脚 → 网名 ✓（先按 connectorId ✓；网表里可能写的是**脚名**（如 `1`/`2`）⇒ 再按名字 ✓）"""
            nm = net_of_pin.get((ttl, cid))
            if nm is None:
                for pname, c2 in name2cid.items():
                    if c2 == cid:
                        nm = net_of_pin.get((ttl, pname))
                        break
            return nm
        for cm in bv.iter("connector"):
            cid = cm.get("connectorId")
            key = "%s.%s" % (ttl, cid)
            # ★ ⑥ 收数**必须在最前面** ✓ —— 下面的 `continue`（没声明孔／孔名不对…）会让它收不到 ✗，
            #   而 ⑥ 是**独立**的一条判据 ✓（实测踩过 ✗：台架那张报"全是 (0,0)"✗ 其实是先被 continue 了 ✗）。
            cg6 = _child(cm, "geometry")
            if cg6 is not None and cid in anc:
                gx6, gy6 = _num(cg6.get("x")), _num(cg6.get("y"))
                if abs(gx6) < 1e-9 and abs(gy6) < 1e-9:
                    sh_zero[0] += 1          # `(0,0)` = Fritzing **没改写** ✓ ⇒ 这只脚没可比对的 ✗
                else:
                    g6.append((cid, gx6 - anc[cid][0], gy6 - anc[cid][1]))
            allc = list(cm.iter("connect"))
            tg = [c.get("connectorId") for c in allc
                  if (c.get("layer") or "") == "breadboardbreadboard"]
            # ★ 豁免（2026-10-15 ✓）：**裸焊盘**（如 `U1` 的 `EPAD` ✓）本来就不插孔 ✓
            #   ⇒ 判据用「**既没落孔、也没接线**」✗（✗ 不是"没落孔"✗ —— 那会把 EPAD 误报 ✗）
            if not allc:
                # ★★ 2026-10-18（用户：物理优先 ✓）：**要么插孔要么接线** ✓；两者都没有 = 悬空 ✗。
                #   但**网表里本来就没有这只脚** ⇒ 悬空是设计如此 ✓（例：`SW1` 的备用极 3/4/5 ✓）
                #   ⇒ 只**报告**不算错 ✓；有网表却没接 ⇒ 判错 ✗（那是真漏接 ✓）。
                if nets_path and _net_of(ttl, cid) is None:
                    opened.append(key)
                else:
                    nopad.append(key)                    # 既没落孔、也没接线 ⇒ 没到位 ✗
                continue
            if not tg:
                # ★★ 2026-10-18 修 ✗（用户点出来的）：这里原来是**无条件豁免** ✗ ——
                #   `exempt.append(key); continue` 只看"有没有 `<connect>`" ✓，
                #   **从没核过导线端点到底落在哪** ✗ ⇒ 端点偏 4.80/2.70 mm（合成 5.51 mm）
                #   时，①–⑥ ＋ `bb_probe` ＋ `file_sanity` **全绿** ✗✗，
                #   而**物理上就是没接上** ✗（图上的线头悬在焊盘旁边 ✓）。
                #   ⇒ ⑦：拿该脚声明的每根导线的**这一端**，与它的接线点比距离 ✓。
                ws = wends.get((e.get("modelIndex"), cid)) or []
                # ★ 接线点 = **引线末端**（有 `legId` 时 ✓）／否则焊盘中心 ✓
                #   （不加这一条就会把"橡皮筋引线件"的 2.54mm 引线当成错 ✗ —— 实测误报过 ✓）
                pb7 = None
                if cid in lg_tips:
                    p = pbox.apply(tf, lg_tips[cid][0], lg_tips[cid][1])
                    pb7 = (loc[0] + p[0], loc[1] + p[1])
                elif cid in anc:
                    p = pbox.apply(tf, anc[cid][0], anc[cid][1])
                    pb7 = (loc[0] + p[0], loc[1] + p[1])
                if pb7 is None:
                    wire_noref.append(key)          # 拿不到接线点（件 svg 里没这个脚）⇒ 如实不判 ✓
                elif not ws:
                    wire_noref.append("%s（有小 connect 但不是导线）" % key)
                for wt, wp in ws:
                    if pb7 is None:
                        break
                    wired.append(("%s←%s" % (key, wt),
                                  (((wp[0] - pb7[0]) ** 2 + (wp[1] - pb7[1]) ** 2) ** 0.5) * SK_MM))
                exempt.append(key)
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

        # ⑥ 本件收尾：≥2 只脚才比得出"形状" ✓（一只脚／全是 `(0,0)` ⇒ 判不了 ⇒ 如实不判 ✓）
        if len(g6) >= 2:
            mx6 = sum(d[1] for d in g6) / len(g6)
            my6 = sum(d[2] for d in g6) / len(g6)
            for d in g6:
                sh.append(("%s.%s" % (ttl, d[0]),
                           (((d[1] - mx6) ** 2 + (d[2] - my6) ** 2) ** 0.5) * SK_MM))
            sh_ck[0] += len(g6)

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
    sh_bad = [d for d in sh if d[1] > SHAPE_TOL_MM]
    ok &= rep("⑥", "同件内脚与脚的间距 = 元件自称的间距（容差 %.1f mm ✓）" % SHAPE_TOL_MM,
              sh_bad, "；".join("%s 形状偏 %.2f mm" % (d[0], d[1]) for d in sh_bad[:6]))
    # ★★ ⑦ 接线到位（2026-10-18 加 ✓）：**物理上碰上了没有** ✓ —— 不是"写没写 `<connect>`" ✗
    w_bad = [d for d in wired if d[1] > WIRE_TOL_MM]
    ok &= rep("⑦", "接线的脚：导线端点落在它的接线点上 ≤ %.2f mm" % WIRE_TOL_MM, w_bad,
              "；".join("%s 差 %.2f mm" % (k, d) for k, d in w_bad[:6]))
    if wired:
        print("      —— ⑦ 量到 **%d 处**接线 ✓（最大 %.3f mm ✓）"
              % (len(wired), max(d for _k, d in wired)))
    else:
        print("      —— ⑦ 本图没有\"接线不插孔\"的脚 ⇒ 不判 ✓")
    if wire_noref:
        print("      ⚠ ⑦ 跳过 %d 只（拿不到接线点／声明的不是导线）：%s"
              % (len(wire_noref), ", ".join(wire_noref[:6])))
    if sh_ck[0]:
        print("      —— ⑥ 量到 **%d 只脚**参与比对 ✓（另有 %d 只 `geometry=(0,0)`＝没改写 ⇒ 跳过 ✓）"
              % (sh_ck[0], sh_zero[0]))
    else:
        print("      —— ⑥ **本次没量到可比对的脚**（每件里可比脚的 < 2 只：要么全是 `(0,0)`＝没改写 ✓、"
              "要么那件没在这张图的面包板视图里 ✓）⇒ 不判 ✓")
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
    if opened:
        print("   · 悬空 %d 只（**网表里没有它** ⇒ 设计如此 ✓ 不算错）：%s"
              % (len(opened), ", ".join(opened[:6])))
    print("⇒ %s **%s**" % ("✓" if ok else "✗",
                          "允许布线（摆位到位 ✓）" if ok else
                          "不准布线（先把脚落到孔上／把重叠的挪开 —— §A.4／§A.5 ✗）"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
