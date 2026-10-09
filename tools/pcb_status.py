# -*- coding: utf-8 -*-
r"""pcb_status：**照 Fritzing 状态栏的算法**逐视图仿真"还剩几条连接没布" ✓（只读 ✓、通用 ✓）

★ 为什么要有它 ✗✓（2026-10-10 ✓）：用户报「三个视图都**布线完成**，可我在三个视图里随意
  删掉任意一根导线，**也还是布线完成**」✗ —— 要回答"这话是真是假"，就必须**照源码**把
  状态栏自己算一遍 ✓。本项目先在项目仓里做了一版（`hardware/pixel/tools/pcb_rats_probe.py` ✓，
  在 v68/v81/v76.4/v82 四个"用户读过状态栏"的文件上**逐字对上** ✓）⇒ 这里把**与项目无关的
  那半**（仿真引擎）上收到库仓 ✓（仓规：通用工具只有一份 ✓，`toolpaths.py` 头里有这条 ✓）。

## 口径（**逐条照源码** ✓，行号可核 ✓）

| 事 | 出处 |
|---|---|
| 状态栏文案 `Routing completed` ／ `%1 of %2 nets routed - %n connector(s) still to be routed` | `mainwindow/mainwindow.cpp:2285` ✓ |
| **每个视图各有一份**状态（各 `SketchAreaWidget` 各有 `routingStatusLabel` ✓） | `mainwindow/mainwindow.cpp:906`、`1216` ✓ |
| 逐视图跑：`updateRoutingStatus`（`sketchwidget.cpp:6968`）遍历**本视图场景**里的连接器项 ✓ | `sketch/sketchwidget.cpp:6968` ✓ |
| 分网 = `ConnectorItem::collectEqualPotential`（BFS：`connectedToItems()` ∪ 件内 bus ∪ 跨层同脚 ✓） | `connectors/connectoritem.cpp:1340` ✓ |
| ★ `connectedToItems()` 在**读盘时**由**本视图**的 `<connect>` 恢复 ✓ | `sketch/sketchwidget.cpp:496`（"now restore connections"）＋ `615 handleConnect` ✓ |
| `<connect>` 的目标**只在本视图里找** ✓ | `items/itembase.cpp:559`（`connector->connectorItem(m_viewID)`）✓ |
| "算不算一张网" = `collectParts` 取**零件类**连接器项（Wire/Note/Logo/Hole/Ruler 丢掉 ✗） | `connectors/connectoritem.cpp:1413` ✓ |
| ＋ `isEverVisible()` 过滤（**PCB 视图：面包板/符号/孔 ✗**；**原理图：面包板/过孔/孔 ✗**；**面包板：孔/过孔/符号 ✗**） | `sketch/pcbsketchwidget.cpp:441`／`schematicsketchwidget.cpp:146`／`breadboardsketchwidget.cpp:170` ✓ |
| **≤1 只零件脚 ⇒ 整张网被跳过**（不计数 ✗） | `sketch/sketchwidget.cpp:7013` ✓ |
| "还剩几条" = `scoreOneNet`：该网**零件项**连通片数 − 1 ✓ | `utils/graphutils.cpp:447`、`573` ✓ |
| scoreOneNet 的边：(a) 跨层同脚 ✓ (b) 两个可见 Symbol ✓ (c) 同件同 bus ✓ (d) 连到 Wire（`wireFlags & myTrace`）⇒ `collectChained` 末端 ✓ (e) 连到 Part 且 `myTrace` 有 NormalFlag ✓ (f) 连到 **可见的** Breadboard ⇒ `collectBreadboard` 末端 ✓ | `utils/graphutils.cpp:464`–`560`／`wire.cpp:1146`／`graphutils.cpp:608` ✓ |

★★ 由此得到两条**可证的结论** ✓（本项目 2026-10-10 量出来的 ✓）：

  ① **PCB 视图 / 原理图视图里，面包板 `setEverVisible(false)`** ⇒ scoreOneNet 的 (f) 分支
     **什么都不加** ✗ ⇒ 跨视图 glue **只把"网"并大** ✗、**不给"铜"补边** ✓
     ⇒ 于是 K = 铜的裂片数 − 1 ✓（这正是 v81「7 中的 5，2 个连接仍然需要布线」的来路 ✓，
     而**删掉那 94 条记录之后 K=0** ✓）；
  ② **删掉任意一根导线之后，状态栏文案必然还是 `Routing completed`** ✗（只要板子本来是通的 ✓）：
     单刀切开一张网 ⇒ 每片**各自内部连通** ⇒ 每片 K=0 ✓；**片里只有 1 只零件脚**的 ⇒ 被 7013
     整片丢弃 ✗ ⇒ `netCount == routedCount` 恒成立 ⇒ 文案恒为 `Routing completed` ✓
     ⇒ **用户的"删任意一根线应报未布"在 Fritzing 里物理上做不到** ✗（不是本文件的病 ✗）。

## API ✓

```python
import pcb_status as ST
st = ST.Status(path, expect=None)          # expect = {网名: {"位号.connectorN", …}} ✓
for v in ST.VIEWS:
    r = st.view(v)                          # dict(M, K, nets=[…], dropped=[…], group_of=…)
st.after_drop(view, modelIndex)             # 虚拟删线后的同一个 dict ✓
ST.pcb_geom_edges(model)                    # PCB 视图的"真几何"连边 ✓（`pcb_check` 的口径 ✓）
```
"""
import collections
import math
import os
import re
import xml.etree.ElementTree as ET

import pcb_wire as PW
import pcb_check as PC

VIEWS = ("breadboardView", "schematicView", "pcbView")

# 逐视图的 `getTraceFlag()` ✓（`pcbsketchwidget.cpp:1983` / `schematicsketchwidget.cpp:357` /
# `sketchwidget.cpp:9165` ✓）——scoreOneNet 只认"本视图那种线" ✓
TRACE_FLAG = {"breadboardView": 64, "schematicView": 128, "pcbView": 4}
NORMAL_FLAG = 64

# 逐视图"这个类算不算零件脚" ✓（= `setNewPartVisible` 里没被 `setEverVisible(false)` 的类 ✓）
EVER = {
    "pcbView": ("part", "via", "board"),
    "schematicView": ("part", "symbol", "board"),
    "breadboardView": ("part", "breadboard", "jumper"),
}

# ★ 核心件（`:/resources/parts/core/*.fzp`）在 Fritzing 里是**编进二进制的资源** ✗ ⇒ 盘上没文件 ✓
#   ⇒ 只把**语义要紧的那一条**写死 ✓：`wire.fzp` 的 `<bus id="wirebus">` 把 `connector0`/`connector1`
#     并成**一根导体** ✓（`collectEqualPotential` 靠它走完"线身" ✓，`scoreOneNet` 也靠它 ✓）。
#   其余核心件（via/hole/netlabel/ground/logo/rectangle_pcb）都**没有多成员的 bus** ✓（可逐条核 ✓）。
CORE_BUS = {"core/wire.fzp": [["connector0", "connector1"]]}

INST_RE = re.compile(r"(?ms)^([ \t]*)<instance\b.*?\n\1</instance>")
CONN_RE = re.compile(r"(?s)<connector\s+([^>]*?)>(.*?)</connector>")
ATTR_RE = re.compile(r'([\w]+)="([^"]*)"')
DECL_RE = re.compile(r'<connect\s+connectorId="([\w]+)"\s+modelIndex="([^"]+)"'
                     r'(?:\s+layer="([\w]+)")?')


def kind_of(module_id):
    """实例 ⇒ 类 ✓（照 `ModelPart::ItemType` + 本项目的件名 ✓）"""
    if module_id.startswith("Wire"):
        return "wire"
    if module_id.startswith("Via"):
        return "via"
    if "readboardLogo" in module_id:
        return "logo"
    if "readboard" in module_id:
        return "breadboard"
    if "Hole" in module_id:
        return "hole"
    if "NetLabel" in module_id or "Ground" in module_id:
        return "symbol"
    return "part"


class UF(object):
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def load_views(text):
    """⇒ 实例表 ✓：`(mi, mod, kind, title, path, {视图: {connectorId: [{layer, decl}]}}, {视图: wireFlags})`"""
    out = []
    for m in INST_RE.finditer(text):
        blk = m.group(0)
        mi = re.search(r'modelIndex="(\d+)"', blk)
        mod = re.search(r'moduleIdRef="([^"]+)"', blk)
        if not (mi and mod):
            continue
        t = re.search(r"<title>([^<]*)</title>", blk)
        pth = re.search(r'\bpath="([^"]*)"', blk)
        views, flags = {}, {}
        for vm in re.finditer(r"(?s)<(\w+View)\b([^>]*)>(.*?)</\1>", blk):
            body = vm.group(3)
            fl = re.search(r'wireFlags="(\d+)"', body)
            conns = collections.OrderedDict()
            for cm in CONN_RE.finditer(body):
                a = dict(ATTR_RE.findall(cm.group(1)))
                conns.setdefault(a.get("connectorId"), []).append(
                    dict(layer=a.get("layer"),
                         decl=[(x.group(1), x.group(2)) for x in DECL_RE.finditer(cm.group(2))]))
            views[vm.group(1)] = conns
            if fl:
                flags[vm.group(1)] = int(fl.group(1))
        out.append(dict(mi=mi.group(1), mod=mod.group(1), kind=kind_of(mod.group(1)),
                        title=(t.group(1) if t else ""),
                        path=(pth.group(1) if pth else None), views=views, flags=flags))
    return out


_BUS_CACHE = {}


def fzp_buses(path):
    """件自己的 `<bus>` ⇒ 每组同 bus 的 connectorId ✓（读 `.fzp` 真文件 ✓，不猜 ✗）"""
    if not path:
        return []
    if path in _BUS_CACHE:
        return _BUS_CACHE[path]
    res, norm = [], path.replace("\\", "/")
    for k, v in CORE_BUS.items():
        if norm.endswith("/" + k) or norm.endswith(k):
            res = [list(x) for x in v]
    p = path.replace("/", os.sep)
    if os.path.isfile(p):
        try:
            root = ET.parse(p).getroot()
            for b in root.iter("bus"):
                mem = []
                for d in b.iter():
                    if d is b:
                        continue
                    for k, v in d.attrib.items():
                        if k in ("connectorId", "connector", "member", "id") and v:
                            mem.append(v)
                mem = sorted(set(mem))
                if len(mem) > 1:
                    res.append(mem)
        except Exception:
            pass
    _BUS_CACHE[path] = res
    return res


def pcb_geom_edges(model):
    """PCB 视图的**真几何**连边 ✓（口径与 `pcb_check.check` 的建边**同一套** ✓：端点落盘 ✓、
    端到端真重合（0.10 mm ✓）、弧的线身 ✓、端点/线身挨过孔 ✓、过孔铜盘挨线 ✓）"""
    pads, traces, vias = model["pads"], model["traces"], model["vias"]
    out = []
    for i, t in enumerate(traces):
        W = (t["inst"], "connector0")
        for k in (0, 1):
            e = t["a"] if k == 0 else t["b"]
            for q in pads:
                if t["layer"] in PC.pad_layers(q) and PC.d_pt_pad(e, q) <= 0:
                    out.append((W, (q["mi"], q["cid"])))
            for j, u in enumerate(traces):
                if j == i or u["layer"] != t["layer"]:
                    continue
                if PC.trace_near_pt(u, e, 0.3543):
                    out.append((W, (u["inst"], "connector0")))
            if k == 1 and t.get("curve"):
                for mid in t["pts"][1:-1]:
                    for q in pads:
                        if t["layer"] in PC.pad_layers(q) and PC.d_pt_pad(mid, q) <= 0:
                            out.append((W, (q["mi"], q["cid"])))
                    for j, u in enumerate(traces):
                        if j == i or u["layer"] != t["layer"]:
                            continue
                        if PC.trace_near_pt(u, mid):
                            out.append((W, (u["inst"], "connector0")))
                    for v in vias:
                        if (abs(v["p"][0] - mid[0]) <= PC.TOL
                                and abs(v["p"][1] - mid[1]) <= PC.TOL):
                            out.append((W, (v["inst"], "connector0")))
            for v in vias:
                if abs(v["p"][0] - e[0]) <= PC.TOL and abs(v["p"][1] - e[1]) <= PC.TOL:
                    out.append((W, (v["inst"], "connector0")))
    for v in vias:
        V = (v["inst"], "connector0")
        rv = ((v.get("hole_mm") or 0.3) / 2.0 + (v.get("ring_mm") or 0.15)) / PW.SK
        for t in traces:
            hw = (t.get("mils") or 12.0) * 0.0254 / 2.0 / PW.SK
            if PC.d_pt_trace(v["p"], t) <= rv + hw + 1e-9:
                out.append((V, (t["inst"], "connector0")))
        for q in pads:
            if PC.d_pt_pad(v["p"], q) <= rv + 1e-9:
                out.append((V, (q["mi"], q["cid"])))
        for w in vias:
            if w is v:
                continue
            rw = ((w.get("hole_mm") or 0.3) / 2.0 + (w.get("ring_mm") or 0.15)) / PW.SK
            if math.hypot(v["p"][0] - w["p"][0], v["p"][1] - w["p"][1]) <= rv + rw + 1e-9:
                out.append((V, (w["inst"], "connector0")))
    return out


class Status(object):
    """一份 sketch 的**逐视图状态栏仿真** ✓（只读 ✓；`drop` = 虚拟删掉一根线 ✓）"""

    def __init__(self, path, expect=None, model=None):
        text, self.inner = PW.read(path)
        self.insts = load_views(text)
        self.by_mi = {i["mi"]: i for i in self.insts}
        self.expect = expect or {}
        self.model = model if model is not None else PC.collect(path)
        self.geom = {"pcbView": pcb_geom_edges(self.model)}
        self._cache = {}

    # ── 一张图的"零件脚"名 ✓（诊断用 ✓）────────────────────────────────────────
    def title_of(self, k):
        i = self.by_mi.get(k[0])
        return i["title"] if i else str(k[0])

    def view(self, view, drop=None):
        key = (view, drop)
        if key in self._cache:
            return self._cache[key]
        r = self._run(view, drop)
        self._cache[key] = r
        return r

    def after_drop(self, view, mi):
        return self.view(view, mi)

    # ── 仿真本体 ✓────────────────────────────────────────────────────────────
    def _run(self, view, drop=None):
        insts, by_mi = self.insts, self.by_mi
        sub = [i for i in insts if view in i["views"]]
        dead = set([drop]) if drop else set()
        nk, flags = {}, {}
        for i in sub:
            if i["mi"] in dead:
                continue
            for cid in i["views"][view]:
                nk[(i["mi"], cid)] = i["kind"]
            if view in i["flags"]:
                flags[i["mi"]] = i["flags"][view]
        adj = collections.defaultdict(set)
        u = UF()
        for k in nk:
            u.find(k)
        dec = 0
        for i in sub:
            if i["mi"] in dead:
                continue
            for cid in i["views"][view]:
                for e in i["views"][view][cid]:
                    for (tcid, tmi) in e["decl"]:
                        if tmi in dead:
                            continue
                        j = by_mi.get(tmi)
                        if j is None or view not in j["views"]:
                            continue          # ★ 目标**只在本视图里找** ✓
                        if tcid not in j["views"][view]:
                            continue
                        a, b = (i["mi"], cid), (tmi, tcid)
                        if a in nk and b in nk:
                            dec += 1
                            adj[a].add(b)
                            adj[b].add(a)
                            u.union(a, b)
            for grp in fzp_buses(i["path"]):   # 件内 bus ✓（线身 = 一根导体 ✓；面包板孔组 ✓）
                ks = [(i["mi"], c) for c in grp if (i["mi"], c) in nk]
                for a in ks[1:]:
                    # ★ 也要进 `adj` ✓：`Wire::collectChained` 是**从线自己的两端**出发的 ✓
                    #   （`wire.cpp:1141` 把 `m_connector0/1` 都过一遍 ✓）⇒ 走线身时必须能从
                    #   一个端点跳到另一个端点 ✓，否则"线身"在仿真里会断 ✗。
                    adj[ks[0]].add(a)
                    adj[a].add(ks[0])
                    u.union(ks[0], a)
        for (a, b) in self.geom.get(view, ()):
            if a in nk and b in nk:
                adj[a].add(b)
                adj[b].add(a)
                u.union(a, b)
        grp = collections.defaultdict(list)
        for k in nk:
            grp[u.find(k)].append(k)

        def chain_ends(start):
            """`Wire::collectChained` ✓：顺着线走 ✓，碰到**不是线**的 ⇒ 端 ✓"""
            seen, ends, q = {start}, set(), [start]
            while q:
                cur = q.pop()
                for to in adj[cur]:
                    if to in seen:
                        continue
                    seen.add(to)
                    if nk.get(to) == "wire":
                        q.append(to)
                    else:
                        ends.add(to)
            return ends

        def bb_ends(hole, pset):
            """`GraphUtils::collectBreadboard` ✓：撞到零件脚就收 ✓，否则顺着 bus/连边继续 ✓"""
            seen, out, q = {hole}, set(), [hole]
            while q:
                cur = q.pop()
                if cur in pset:
                    out.add(cur)
                    continue
                for to in adj[cur]:
                    if to not in seen:
                        seen.add(to)
                        q.append(to)
            return out

        nets, dropped = [], []
        for _r, ks in grp.items():
            parts = sorted(k for k in ks if nk[k] in EVER[view])
            rec = dict(keys=sorted(ks), parts=parts, titles=sorted({self.title_of(k) for k in ks}))
            if len(parts) < 2:
                dropped.append(rec)      # ★ `sketchwidget.cpp:7013`：≤1 只脚 ⇒ 整片跳过 ✗
                continue
            pu = UF()
            for k in parts:
                pu.find(k)
            for k in parts:
                if nk[k] == "symbol":
                    for k2 in parts:
                        if k2 != k:
                            pu.union(k, k2)
                if k[0] in by_mi:
                    for g2 in fzp_buses(by_mi[k[0]]["path"]):
                        for k2 in parts:
                            if k2 > k and k[0] == k2[0] and k[1] in g2 and k2[1] in g2:
                                pu.union(k, k2)
            pset = set(parts)
            for k in parts:
                for to in adj[k]:
                    tk = nk.get(to)
                    if tk == "wire":
                        if not (flags.get(to[0], 0) & TRACE_FLAG[view]):
                            continue
                        for e in chain_ends(to):
                            if e != k and e in pset:
                                pu.union(k, e)
                    elif tk == "part" and view == "breadboardView":
                        if to in pset:
                            pu.union(k, to)
                    elif tk == "breadboard" and view == "breadboardView":
                        for e in bb_ends(to, pset):
                            if e != k and e in pset:
                                pu.union(k, e)
            rec["K"] = len({pu.find(k) for k in parts}) - 1
            nets.append(rec)
        nets.sort(key=lambda z: (-len(z["parts"]), z["parts"]))
        return dict(view=view, M=len(nets), K=sum(n["K"] for n in nets),
                    nets=nets, dropped=dropped, dec=dec, nodes=len(nk), groups=len(grp),
                    # ★ "有脚却被丢掉"的组 ✓ = 那些因为**只有 1 只脚**而 Fritzing 看不见的碎铜 ✓
                    dropped_with_parts=[d for d in dropped if d["parts"]])

    def text(self, view, drop=None):
        """★ 状态栏**文案** ✓（`mainwindow.cpp:2285` 的三分支 ✓）"""
        r = self.view(view, drop)
        if r["M"] == 0:
            return "No connections to route"
        routed = sum(1 for n in r["nets"] if not n["K"])
        if r["M"] == routed:
            return "Routing completed"
        return "%d of %d nets routed - %d connector(s) still to be routed" % (routed, r["M"], r["K"])

    def designed_shortfall(self, view, drop=None):
        """`expect` 里每张网在本视图的"落空"情况 ✓（<2 只脚 ⇒ Fritzing 眼里这张网不存在 ✗）"""
        out, r = [], self.view(view, drop)
        for net in sorted(self.expect):
            want = {s for s in self.expect[net] if isinstance(s, str) and "." in s}
            got = set()
            for n in r["nets"]:
                for k in n["parts"]:
                    s = "%s.%s" % (self.title_of(k), k[1])
                    if s in want:
                        got.add(s)
            if len(got) < 2:
                out.append(dict(net=net, got=sorted(got), want=len(want)))
        return out

    def partition(self, view, drop=None):
        """★ **全部分组**（含被丢弃的 ✓）的"零件身份指纹" ✓ —— 比 `(M,K)` 细一档 ✓

        用来判"删掉某根线，模型到底有没有动" ✓（`(M,K)` 会掩盖"两片都被丢掉"这一档 ✗）。
        """
        r = self.view(view, drop)
        return tuple(sorted(tuple(sorted(k for k in g["parts"])) for g in r["nets"] + r["dropped"]
                            if g["parts"]))

    def net_name(self, view, rec):
        """一张网 ⇒ 用 `expect` 的网名 ✓（认不出 ⇒ 列出位号 ✓）"""
        names = set()
        for k in rec["parts"]:
            s = "%s.%s" % (self.title_of(k), k[1])
            for net, lst in self.expect.items():
                if s in lst:
                    names.add(net)
        return "、".join(sorted(names)) or ("（%s）" % "、".join(sorted(
            {"%s.%s" % (self.title_of(k), k[1]) for k in rec["parts"]})[:3]))
