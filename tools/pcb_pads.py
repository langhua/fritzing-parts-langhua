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

# ★★ Fritzing **核心安装孔件**画在哪 ✓：`图上画出来的孔心 = <geometry> + HOLE_DRAW_OFF_MM` ✓
#   ★ 出处（**实测** ✓，不是猜 ✗）：用户导出的 `pixel-pcb-v25_图示.svg` 里，两颗孔的钻孔圆
#     画在他板框的 (2.898, 21.898) / (21.898, 2.898) mm ✓，而该实例的 `<geometry>`
#     写的是 (3.00, 22.00) / (22.00, 3.00) ✓ ⇒ 直接差 **(+1.665, +1.665) mm** ✗。
#     （帧差 0.102 mm 是拿**线圈两个通孔盘**当参照扣的 ✓：模型 (11.90,16.05) vs 图
#      (11.798,15.948) ✓ 两盘一致 ✓ ⇒ 这个参照稳 ✓。）
#   ⇒ 把 `<geometry>` 当孔心 ✗ 会把孔写到离板边 **1.23 mm** ✗（IPC 要 ≥ 3 ✓）。
#   ⚠️ 它是**这个件**的属性 ✗（不是 Fritzing 的通则 ✗，也没有公式可推 ✓）；
#     大板上量到的 (−46.50, −21.11) 是**错的** ✗（不能跳板用 ✗）。
#   ★★ **只有这一份** ✓：`gen_pcb` / `audit_placement` / `render_pcb` 都引用它 ✓
#     （2026-09-30 收拢 ✓ —— 之前是三份字面量 ✗，改一处就漂 ✗）。
def holes(text):
    """⇒ `[(钻孔心 sketch 单位 ✓, 孔内径 mm ✓, 铜盘外径 mm ✓), …]` ✓（核心孔件 ✓）

    ★★ **唯一实现** ✓（2026-10-01 ✓）：`render_pcb.holes_of` 与 `pcb_check.collect`
      都调这里 ✓ —— ✗ 以前只有渲染器会解析 ⇒ **布线器与校验器都不知道有孔** ✗
      ⇒ 实测 `v50H.fzz` 里有 **4 根走线直接穿过安装孔** ✗（距内壁 **−1.100 mm** = 正穿孔心 ✗，
      用户原话：「安装孔附近是不能布线的，更不能穿体」✓）。
    ★ 孔心 = **`<geometry>` + `HOLE_DRAW_OFF_MM`** ✗ —— 把 `<geometry>` 当孔心 ✗
      会把孔画在离板边 1.23 mm 的地方 ✗（实测：用户导出的图里就是那样 ✗）。
    ★ 孔**不在** `model["parts"]` 里 ✗（它没有可解析的 fzp/svg ✓）⇒ 从 sketch 原文里找 ✓。
    """
    out = []
    for m in re.finditer(r'(?ms)<instance\b[^>]*?moduleIdRef="HoleModuleID".*?</instance>',
                         text or ""):
        b = m.group(0)
        sz = re.search(r'name="hole size"\s+value="([^"]+)"', b)
        g = re.search(r'<pcbView\b[^>]*>\s*<geometry\s+([^>]*?)/>', b)
        if not (sz and g):
            continue
        nums = [float(v) for v in re.findall(r"([\d.]+)\s*mm", sz.group(1))]
        inner = nums[0] if nums else 2.2
        outer = nums[1] if len(nums) > 1 else 0.0
        a = dict(re.findall(r'([\w]+)="([^"]*)"', g.group(1)))
        # ★★★ 2026-10-02 修 ✗：偏移 = `孔径/2 + 环宽 + 画布留白` ✓ —— **按本颗的尺寸算** ✗
        #   （✗ 旧版是死的 `HOLE_DRAW_OFF_MM`(1.665) ✗ ⇒ 换过孔/孔尺寸就偏 ✓，
        #    同 `part_box.ring_off_mm` 那三个实测点 ✓；2.2/0.0 ⇒ 1.66444 ✓ 与旧值差 1e-4 mm ✓）
        off = PB.draw_off_units("hole", (inner, outer))
        out.append(((float(a.get("x", 0)) + off, float(a.get("y", 0)) + off), inner, outer))
    return out


# ★★ 2026-10-02 修 ✓：**从唯一实现推导** ✓（= `ring_off_mm(2.2, 0.0)` ✓）——
#   ✗ 旧值是字面量 `(1.665, 1.665)` ✗（把两处口径又分成了两份 ✗，且第 4/5 位写反 ✓）
HOLE_DRAW_OFF_MM = (PB.HOLE_DRAW_OFF_MM, PB.HOLE_DRAW_OFF_MM)
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


def pcb_pads(root, connectors=(), decl=None):
    """按 **connector id** 把焊盘归好 ✓

    ⇒ `({cid: pad}, 没人认领的铜（焊盘形状 ✓）, 认不出的清单 ✓)`
    ★ 同一 connector 多个候选（如通孔件在 copper0/copper1 各画一份 ✓）⇒ 取**铜层**里的 ✓，
      层数不同 ⇒ `layer="both"` ✓；位置必须**一致** ✓（不一致就该人看 ✓，别硬挑一个 ✗）。
    ★★ **所在层以 `.fzp` 的 `<p layer="copper0|copper1" svgId=…>` 声明为准** ✓
      （2026-09-30 修 ✗）：原来只看"焊盘图元最近的 `<g id=copperN>` 祖先" ✗ ⇒
      把 `NFC-Coil` 那种**把 `copper0` 嵌在 `copper1` 里**（两个盘两层都要 ✓）画法
      误报成"只有底层" ✗ ⇒ 害我以为顶层缺环 ✗（虚惊 ✓；官方惯例也确实是两层都声明 ✓）。
      声明与嵌套**不一致** ⇒ 归到声明 ✓ 并**报出来** ✓（不静默 ✗）。
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
        dl = (decl or {}).get(cid)
        if dl:
            want = "both" if len(set(dl)) > 1 else dl[0]
            if want != lay and lay in ("copper0", "copper1", "both"):
                bad.append("%s：`.fzp` 声明 `%s`、svg 嵌套看着是 `%s` ⇒ **按声明** ✓"
                           % (cid, want, lay))
            lay = want
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
def cid_of(names, cids, name):
    """网表里的**脚名** → `connectorN` ✓（**唯一实现** ✓，2026-09-30 收进来 ✓）

    ★ `#N` = **第 N 个脚（1 起算 ✓）** ⇒ `#1` → `connector0` ✓
      （出处：`pixel_nets.py` 表头「`#N` = 第 N 个脚 ✓（core 件没有名字 ✓）」✓；
       第一版把它当 `connectorN` ✗ ⇒ `C1.#2`/`J1.#3` 全映射错 ✗，摆位报告里当场报出来 ✓）
    ★ 具名脚按 `.fzp` 的 `connectorname` ✓ 比（**大小写不敏感** ✓）。
    """
    nm = (name or "").strip().lower()
    if nm.startswith("#"):
        try:
            cid = "connector%d" % (int(nm[1:]) - 1)
        except ValueError:
            return None
        return cid if not cids or cid in cids else None
    for cid, n in (names or {}).items():
        if (n or "").strip().lower() == nm:
            return cid
    return None


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
        # ★ 每个脚在 pcb 上**声明**了哪几层 ✓（`<connector><views><pcbView><p layer=… svgId=…/>` ✓）
        decl = {}
        for c in fr.findall(".//connectors/connector"):
            cid = c.get("id")
            if not cid:
                continue
            lays = [p.get("layer") for p in c.findall("./views/pcbView/p")
                    if p.get("layer") in ("copper0", "copper1")]
            if lays:
                decl[cid] = lays
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
                        mi=(el.get("modelIndex") or ""),
                        image=image, connectors=connectors, names=names, decl=decl,
                        svg_text=svg_text, src=src, loc=(float(g.get("x") or 0), float(g.get("y") or 0)),
                        M=PB.tf_of(g), geo=dict(g.attrib), pv=dict(pv.attrib)))
    return out, board


def _placer(part):
    """一个实例的**换算器** ✓：用户单位 → part 局部 sketch 单位（**不含 loc** ✓）

    ★★ 口径**只留这一份** ✗（2026-10-01 抽出来 ✓）：`part_pads` 原来把这段写在函数体里 ✗，
      新增的 `part_body`（元件占位框 ✓）要用**同一套**矩阵/镜像/画布原点数学 ✓ ——
      抄一份就是“两套实现，找不到原因” ✗（本仓的老坑 ✓）。
    返回 `(root, k, ox, oy, vbw, flip, M, loc, abs_of)` ✓；换算不了 ⇒ `(None, …)` ✓。
    """
    if part.get("svg_text") is None:
        return None
    root = ET.fromstring(part["svg_text"])
    k, (ox, oy) = PB.svg_k(root)
    if k is None:
        return None
    vb = PB._nums(root.get("viewBox"))
    vbw = vb[2] if len(vb) == 4 and vb[2] else None
    flip = ((part.get("pv") or {}).get("bottom") or "").lower() == "true"
    if flip and vbw is None:
        flip = False
    M, loc = part["M"], part["loc"]

    def abs_of(p):                       # 用户单位 → 局部 sketch 单位 ✓（调用方再加 loc ✓）
        x = (2.0 * ox + vbw - p[0]) if flip else p[0]
        return PB.apply(M, (x - ox) * k, (p[1] - oy) * k)

    return root, k, ox, oy, vbw, flip, M, loc, abs_of


def part_body(part):
    """元件在 PCB 上的**占位框**（本体墨迹包围盒 ✓）⇒ sketch 绝对矩形 `(x0,y0,x1,y1)` ✓

    ★ 用途（2026-10-01 用户定 ✓）：**过孔不许打进元件里** ✗ —— 用户原话：
      「我想先实现通孔不能在元件内，并与有安全距离的规则，比如 Via10 在 J1 焊盘上打孔了」✓。
      判据需要的是“这个件占了哪块地方” ✓ ⇒ 用 `part_box.shape_bbox`（**所有**画出来的形状 ✓）
      而不是只算焊盘 ✗：`SH-1.0-3P-V` 这类接插件，焊盘只是它的一小部分 ✗。
    ★ 矩阵数学与 `part_pads` **共用 `_placer`** ✓（含背面件的 x 镜像 ✓、画布原点 `ox/oy` ✓）
      —— 不另写一份 ✗。
    ★ 量不出来（svg 尺寸无单位等 ✓）⇒ **None** ✓（宁可报“不知道”也不编 ✗）。
    """
    pl = _placer(part)
    if pl is None:
        return None
    root, k, ox, oy, vbw, flip, M, loc, _abs_of = pl
    c = PB.shape_bbox(root)
    if c is None:
        return None
    pts = [PB.apply(M, ((ox + vbw - u) if flip else u - ox) * k, (v - oy) * k)
           for u in (c[0], c[2]) for v in (c[1], c[3])]
    return (loc[0] + min(p[0] for p in pts), loc[1] + min(p[1] for p in pts),
            loc[0] + max(p[0] for p in pts), loc[1] + max(p[1] for p in pts))


def part_shapes(part):
    """一个件在 PCB 上**画出来的图元**（铜 `copper0/1` + 丝印 `silkscreen` + `outline` ✓）
    ⇒ `[(layer, (x0,y0,x1,y1)), …]`（**sketch 绝对单位** ✓）；换算不了 ⇒ `[]` ✓

    ★ 共用 `_placer` ✓（画布原点 / 比例 / 背面镜像 / 实例矩阵 ✓ —— 与焊盘**同一套** ✗）。
    ★★ 用途（2026-10-01 用户定 ✓）——**逐图元**判，**不用整体外框** ✗：
      · ⑦b 过孔不许落在**元件画出来的东西**上（例：NFC 线圈是 `copper1` 里几百条螺旋 `<line>` ✓）；
      · ⑧ **同一面**的两个件不许相交（用户：「C1 是不是在同一面跟 U1 位置重叠了？」✓ 实测量到
        C1/U1 都在**背面**、叠 4.48 mm² ✗ ⇒ 必须有规则禁止 ✓）。
      ✗ 用"墨迹外框"会**假报** ✓：线圈的外框是 21.6×22.05 mm（板才 25×25 ✓），而 `LED2`
        本来就坐在线圈**中间的空地**上（天经地义 ✓）⇒ 实测 10 对相交里 8 对是异面正常 ✓、
        1 对是线圈假报 ✗、真违规只有 **C1×U1** ✓。
    ★ 线条（`<line>`）的包围盒是**退化的**（宽或高 = 0 ✗）⇒ 按 `stroke-width/2` 外扩 ✓，
      否则"两根线相交"永远测不出来 ✗（线圈全是线 ✓）。
    """
    pl = _placer(part)
    if pl is None:
        return []
    root, k, ox, oy, vbw, flip, M, loc, _abs_of = pl
    sh, _bad = copper_shapes(root)
    out = []
    for s in sh:
        if s["layer"] not in ("copper0", "copper1", "silkscreen", "outline"):
            continue                                   # `(root)` 等 ⇒ 不当作实体 ✓
        b = s["box"]
        pts = [PB.apply(M, ((ox + vbw - u) if flip else u - ox) * k, (v - oy) * k)
               for u in (b[0], b[2]) for v in (b[1], b[3])]
        g = ((s.get("sw") or 0.0) / 2.0) * k           # ★ 线宽算进去 ✓（细线不再是零面积 ✓）
        lay = s["layer"]
        # ★★ 背面件（`bottom="true"`）的**铜层要对调** ✓ —— 与 `part_pads` 同一口径 ✗：
        #   svg 里的 `copper1` 画在板子的 `copper0`（背面 ✓）上 ✓（证据：用户导出图里
        #   背面件的 43 个盘全在 `<g id="copper0">` ✓）。✗ 不对调 ⇒ ⑧“同层相交”会把
        #   一个件的上下两层当成同一层 ✗（NFC 线圈两面都有铜 ✗ ⇒ 必错）。
        if flip and lay in ("copper0", "copper1"):
            lay = "copper1" if lay == "copper0" else "copper0"
        out.append((lay,
                    (loc[0] + min(p[0] for p in pts) - g, loc[1] + min(p[1] for p in pts) - g,
                     loc[0] + max(p[0] for p in pts) + g, loc[1] + max(p[1] for p in pts) + g),
                    s["id"]))          # ★ 图元 id 也带出去 ✓ —— ⑦ 要据此**跳掉焊盘形状** ✗
    return out


def part_pads(part):
    """实例的焊盘 ⇒ **绝对 sketch 单位** ✓（`loc + M·k·(u − vb0)` ✓ 与渲染器同一套矩阵数学 ✓）

    ★★ **背面件（`bottom="true"`）会被 Fritzing 水平镜像** ✓ —— 2026-09-30 补 ✗：
      证据（不是猜 ✗）：Fritzing 给背面件的 `titleGeometry` 写的是
        `<transform m11="-1" m12="0" … m31="9" …/>` ⇒ **m11 = −1 = x 镜像** ✓，
        而动量 `m31 = 9` 单位 = **画布宽（2.54 mm ✓）** ⇒ 镜像轴 = **画布中线** ✓
        （`x' = 2·vb_x0 + vb_w − x` ✓）。
      ⚠️ 口径待核（P0 第 3 步拿 Fritzing 源码钉死 ✓）；**它是错的就会让 0603 的两个脚
        对调** ✗ ⇒ 摆位不受影响 ✓（0603 两盘对称 ✓），**布线/DRC 会中招** ✗ ⇒ 现在先按
        这个口径做 ✓ 并**逐件报出**哪些件被镜像过 ✓（不静默 ✗）。
    """
    if part.get("svg_text") is None:
        return None, None, ["`%s` 的 svg %s" % (part["title"], part["src"])], 0
    # ★★ 换算（画布原点 / 单位比例 / 背面镜像 / 实例矩阵）**只有 `_placer` 一份** ✓
    #   （2026-10-01 抽出来 ✓）：`part_body`（占位框 ✓）与这里的焊盘**用同一套** ✗，
    #   否则“两套实现找不到原因” ✗（本仓老坑 ✓）。
    pl = _placer(part)
    if pl is None:
        return None, None, ["`%s` 的 svg 尺寸算不出（`width` 没单位 ✗）⇒ 焊盘位置换算不了 ✗"
                            % part["title"]], 0
    root, k, ox, oy, vbw, flip, M, _loc, abs_of = pl
    pads, extra, bad, n_track = pcb_pads(root, part["connectors"], part.get("decl"))
    if flip:
        bad.append("（这件在**背面** ⇒ 按 Fritzing 的口径做了 **x 镜像** ✓ 轴 = 画布中线 ✓）")

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
        #   ★★ 背面件要**一起镜像** ✗（只镜像中心、不镜像包围盒 ⇒ 盘和框会差一整个件宽 ✗）
        #   ★★★ 2026-09-30 **修** ✗：镜像那支原来写的是 `2.0*ox + vbw - u` ✗ ——
        #     两个分支的口径**必须一致** ✓（都要得"**相对画布左上角**"的量 ✓）：
        #       · 非背面：`u - ox` ✓（用户坐标 − 画布原点 ✓）；
        #       · 镜像后：`(2·ox + vbw − u) − ox` = **`ox + vbw − u`** ✓ ← 这才是对的 ✗。
        #     ✗ 旧写法漏了那个 `− ox` ⇒ **整框平移 `ox·k`** ✗（`ox ≠ 0` 的件全中招 ✗）。
        #     ★ 证据（**自洽判据** ✓，不是猜 ✗）：**盘心必须落在自己的盘框里** ✓——
        #       实测 `SH-1.0-3P-V`（viewBox `-3.00 -1.12 6.13 5.47` ⇒ `ox = −3` ✗）
        #       三个盘**全部**"中心不在框里"✗、**正好差 3.00 mm** ✗；而 `ox = 0` 的件（如 0603）
        #       全部 ✓ ⇒ 缺陷量 = `ox` ✓，与"漏减 ox"完全吻合 ✓。修后盘框落进该件**墨迹框**内 ✓。
        #     ⚠️ 90° 朝向的件会把这个 x 方向的错**变成 y 方向**的偏移 ✗（实测 J2 真焊盘在
        #       y = 21.96，旧报 18.96 ✗）⇒ 摆位/DRC 会跟着错 ✗。
        # ★★★ 2026-10-05 修 ✗（**量出来的** ✓，不是猜 ✗）：**通孔盘的 `absbox` 必须含环** ✓
        #   ✗ 旧写法拿 svg 的 `circle` 当框 ✗ —— 而 Fritzing 的约定是 `circle.r = **孔半径**` ✓、
        #     `stroke-width = 环宽` ✓（本文件头就写着 ✓）⇒ 框**只到孔边** ✗
        #     ⇒ 每边少 `环宽/2` ✓。实测本板 `L1.connector0`（孔 Ø1.1 ＋ 环 0.5 ✓）：
        #     `absbox` 半宽 **0.550 mm** ✗ vs 真铜（`circle` ✓）半径 **0.800 mm** ✓ ⇒ 少 **0.25 mm**/边 ✗。
        #   ★ 后果（实测 ✓）：`pcb_route.obstacles` 按 `box` 留障碍 ⇒ 禁落半宽只有
        #     `0.550 + (0.1016 + 0.15) = 0.802 mm` ✗ ⇒ 8 mil 的线走在 0.90 mm 处**没被挡** ✗
        #     ⇒ 铜**叠进 1.6 µm** ✗（`v65` 的 `BR+` 刮 `L1` 的 COIL_A 盘 ✓ = 真短路 ✓）。
        #   ★ 与 `circle` 口径**对齐** ✓：`_r = (2r + sw)/2 = r + sw/2` ✓（同一个数 ✓）。
        u0, u1, v0, v1 = p["box"][0], p["box"][2], p["box"][1], p["box"][3]
        if p.get("r") and p.get("sw"):
            _cx, _cy = p["c"]
            _hw = p["r"] + p["sw"] / 2.0
            u0, u1, v0, v1 = _cx - _hw, _cx + _hw, _cy - _hw, _cy + _hw
        cor = [PB.apply(M, ((ox + vbw - u) if flip else u - ox) * k, (v - oy) * k)
               for u in (u0, u1) for v in (v0, v1)]
        # ★★ `poly`：焊盘**真几何**（四角过矩阵 ⇒ **旋转后的真矩形** ✓）—— 2026-10-02 补 ✓
        #   原因 ✓：`absbox` 是**轴对齐**的包围盒 ✗，45° 摆的件（本板 `C2` ✓）会被**胀大** ✗
        #   ⇒ 「线端落没落在焊盘上」这类判据必须用 **`poly`** ✗（用 `absbox` 会假报"接上了" ✗，
        #   实测本板就是这么把 `C2` 的 5V/GND 并成一个网的 ✗）。
        #   ★ 与 Fritzing 同源 ✓：`connectoritem.cpp:1972` 用的是**场景命中测试** ✓（点落在
        #   元件**自己的形状**里 ✓），形状是旋转后的矩形/圆 ✓ —— 不是"离盘心多近" ✗。
        #   ★ 只有一份实现 ✓：这里算一次，`fz_exact.py` 直接读 ✓（别在各处重算 ✗）。
        loc = part["loc"]
        if p.get("r"):          # 通孔焊盘：svg 画的是**圆** ✓ ⇒ 命中区也是圆 ✓（半径取盘外径/2 ✓）
            _r = (2 * p["r"] + (p["sw"] or 0)) / 2 * k
            geo = dict(circle=((loc[0] + c[0], loc[1] + c[1]), _r))
        else:
            # ★★ 四角必须**沿周长**给 ✗：`(x0,y0),(x0,y1),(x1,y1),(x1,y0)` ✓
            #   ✗ 先写成 `(x0,y0),(x0,y1),(x1,y0),(x1,y1)` ⇒ 那是**蝴蝶结**（自交 ✗）⇒
            #   「点在里面吗」的凸性判据会给出**错的答案** ✗（实测 `C2` 的**盘心**都被判"不在" ✗）。
            #   自检 ✓：矩形**中心**必须在四条边的**同一侧** ✓（不符就说明顺序又错了 ✗）。
            u0, u1, v0, v1 = p["box"][0], p["box"][2], p["box"][1], p["box"][3]
            cor4 = [PB.apply(M, ((ox + vbw - u) if flip else u - ox) * k, (v - oy) * k)
                    for (u, v) in ((u0, v0), (u0, v1), (u1, v1), (u1, v0))]
            _sg = None
            for _i2 in range(4):
                x1, y1 = cor4[_i2]
                x2, y2 = cor4[(_i2 + 1) % 4]
                _cr = (x2 - x1) * (c[1] - y1) - (y2 - y1) * (c[0] - x1)
                if abs(_cr) < 1e-12:
                    continue
                if _sg is None:
                    _sg = _cr > 0
                elif _sg != (_cr > 0):
                    bad.append("%s 的焊盘四角顺序**不是沿周长** ✗（中心点判到了边的两侧 ✗）"
                               % cid)
                    break
            geo = dict(poly=[(loc[0] + v[0], loc[1] + v[1]) for v in cor4])
        out[cid] = dict(p, abs=(part["loc"][0] + c[0], part["loc"][1] + c[1]),
                        absbox=(part["loc"][0] + min(v[0] for v in cor),
                                part["loc"][1] + min(v[1] for v in cor),
                                part["loc"][0] + max(v[0] for v in cor),
                                part["loc"][1] + max(v[1] for v in cor)),
                        size_mm=(w, h), hole_mm=hole, ring_mm=ring,
                        nm=part["names"].get(cid, ""), **geo)
        # ★★ **翻面 ⇒ 层要对调** ✗（2026-09-30 修 ✓，证据 = 用户导出的 Fritzing 图 ✓）：
        #   背面件（`bottom="true"`）的焊盘在**板子**上是 `copper0` ✓ ——
        #   导出图里那 43 个盘全在 `<g id="copper0">` ✓（顶层只剩 LED2 的 4 个 ✓）✓。
        #   ✗ 不改就会让校验器把"线走在 copper0、去接一个背面件的盘"判成**没接上** ✗
        #     ⇒ 报一堆假"悬空端点" ✗。
        if out[cid]["layer"] in ("copper0", "copper1"):
            out[cid]["layer"] = ("copper1" if out[cid]["layer"] == "copper0" else "copper0") \
                if flip else out[cid]["layer"]
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
