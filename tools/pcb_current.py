# -*- coding: utf-8 -*-
r"""**电源走线的电流核算 = 独立实现** ✓（2026-10-08 立 ✓）

为什么有它 ✗：布线器（`gen_routes` / `pcb_route`）**只管几何通不通** ✗，从不算电流 ✓ ——
而"一串像素"这种负载最后必须落在**铜的截面积**上 ✓：每段过多少安 ✓、够不够 ✓、
从注入点掉到段末端多少伏 ✓、连接器针超没超额定 ✓。
★ 本仓规矩 ✓：**量尺不许自证** ✗ ⇒ 本工具**自己从 `.fzz` 读** ✓（✗ 不调生成器 ✗）。

**怎么算** ✓（两条腿各管一头 ✓，谁也不替谁圆场 ✗）：
 ① **拓扑**：走文件里**声明的连接**（`<connect … modelIndex=…>` ✓）—— 从注入针出发，
    顺着"走线 → 走线/过孔/焊盘"做生成树 ✓；
 ② **数值**：长度/线宽**从几何读** ✓（`<geometry>` 两点（有弧按弧 ✓）＋ `<wireExtras mils>` ✓）；
 ③ **两者必须对得上** ✓：每一次声明跳转都去量**真铜的净距** ✓ ⇒ 声明接了、铜没接上 ⇒
    当场报 ✗（与 `pcb_check` ⑩ 同一条纪律 ✓）。
 ★ 为什么用声明、不用"几何闭环" ✗（**第一版栽过** ✓）：几何闭环要先定"什么算接上" ✓ ——
   容差松（0.14 mm ✗）⇒ `5V` 与 `GND` 的铜被并成一块 ✗（实测注入针电流报成 **0.002 A** ✗，
   真值 0.43 A ✓）；容差紧 ⇒ 漏接 ✗。**声明是"谁接谁"的唯一无歧义来源** ✓
   （Fritzing 自己写自己读 ✓），而"声明兑现没有"由 ③ 单独量 ✓。

**电气口径** ✓（都写出来 ✓，可逐条核 ✓）：
 · 载流：IPC-2221 **外层** `I = 0.048·ΔT^0.44·A^0.725`（A 用 mil² ✓）——
   ★ 两层板**两面都算外层** ✓（内层系数 0.024 只对多层板芯板层 ✓）；
 · 压降：`ρ(50 °C) = 1.92e-8 Ω·m` ✓（20 °C 的 1.72e-8 ＋ α = 0.0039/°C ✓）；
 · 过孔：孔壁截面积 ✓（周长 × 镀层 25 µm ✓）；
 · **整段**：本板只是段里的一块 ✓ ⇒ 段压降 = 本板路径压降 × `(S+1)/2` ✓
   （电流逐块递减 ⇒ `Σ_{k=1..S}(S−k+1)/S = (S+1)/2` ✓；前提"段内每块板一样" ✓）；
 · ★ 5V 与 GND **两程都算** ✓（负载看到的是**差** ✓）。

用法 ✓：
  py tools\pcb_current.py <sketch.fzz> --nets=<项目数据.py> [--seg-boards=8]
                          [--pixel-amps=0.06] [--misc-amps=0.002] [--oz=1] [--board-mm=1.6]
                          [--rail=5.0] [--drop-pct=5] [--connector-amps=1.0] [--temp-rise=10]
                          [--ports=J1.connector0,J2.connector0] [--power=5V,GND]
  ★ 项目数据里写 `POWER_SPEC = dict(...)` ✓ ⇒ 默认值从它来 ✓（CLI 覆盖 ✓）。

判据 ✓（任一不过 ⇒ 退出码 1 ✓）：
 · 每条边的电流 ≤ 它自己的载流 ✓（`ΔT = --temp-rise` ✓，默认 10 °C ✓）；
 · **段**压降（5V ＋ GND ✓）≤ `--drop-pct` % × `--rail` ✓；
 · 注入针电流 ≤ `--connector-amps` ✓（= **连接器**额定 ✓，不是铜的 ✓）；
 · 声明↔几何**对不上**的跳转 ⇒ 报 ✗（那是接线错误 ✓，不是电气超限 ✓）。
★ 两个方向都算 ✓（两口同型、随便插 ✓ ⇒ 报**较坏**那个 ✓，两个都列 ✓）。
★ 局限（说清楚 ✗）：① 焊盘自身的铜不算 ✓（远宽于走线 ✓）；② 有**并联回路**时树形流
 **偏保守** ✓（并联那条没分流 ⇒ 报的电流偏大 ✓）；③ 温度按 50 °C 固定 ✓（不迭代自热 ✓）；
 ④ 段压降的 `(S+1)/2` 是**假设** ✓。
"""
import importlib.util
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcb_check as PC                                             # noqa: E402
import pcb_wire as PW                                              # noqa: E402

SK = PW.SK                      # mm / sketch 单位 ✓
RHO50 = 1.92e-8                 # Ω·m ✓（20 °C 的 1.72e-8 ＋ α = 0.0039/°C × 30 °C ✓）
OZ_MM = 0.035                   # 1 oz 铜 = 35 µm ✓（两层板标准 ✓；外层另有镀铜 ⇒ 偏保守 ✓）
PLATE_MM = 0.025                # 过孔孔壁镀层 ✓（常规 25 µm ✓）
K_EXT = 0.048                   # IPC-2221 **外层**系数 ✓（内层 0.024 ✓；两层板两面都是外层 ✓）
DEF_MIL = 12.0                  # 走线没写 `WireExtras@mils` 时的兜底 ✓（与 `pcb_check` 同值 ✓）
GEO_TOL_MM = 0.05               # "声明兑现了没有"的几何容差 ✓（比 `pcb_check` ⑩ 的 5 µm 松 ✓）
CONN_RE = r"SH-1\.0|MX-1\.25|JST"      # "哪个件算连接器"的缺省判据 ✓（`POWER_SPEC` 可覆盖 ✓）


# ── 电气公式 ✓ ──────────────────────────────────────────────────────────────
def amp_at(w_mm, oz, dT):
    a = (w_mm / 0.0254) * (oz * OZ_MM / 0.0254)
    return 0.0 if a <= 0 else K_EXT * (dT ** 0.44) * (a ** 0.725)


def temp_rise(i_a, w_mm, oz):
    a = (w_mm / 0.0254) * (oz * OZ_MM / 0.0254)
    return 0.0 if (i_a <= 0 or a <= 0) else (i_a / (K_EXT * (a ** 0.725))) ** (1.0 / 0.44)


def r_mm2(a_mm2, length_mm):
    return RHO50 * (length_mm * 1e-3) / (a_mm2 * 1e-6)


def via_area_mm2(hole_mm):
    return math.pi * hole_mm * PLATE_MM


def via_eq_w_mm(hole_mm, oz):
    return via_area_mm2(hole_mm) / (oz * OZ_MM)


# ── 从**电气规格**反推线宽 ✓（`gen_routes.py` 的缺省宽度就是它给的 ✓）──────────────
LINK_DETOUR = 1.5      # 一块板自己那条 5V 链路的**绕行系数** ✓（板距 25 mm ⇒ 等效 37.5 mm ✓）
SPEC_MARGIN = 1.25     # 估算 → 预算的余量 ✓（实测估算偏乐观 ~8% ✓ ⇒ 留 25% ✓）

MIL_TIERS = (8, 12, 16, 24, 32, 48)      # Fritzing 宽度下拉那六档 ✓


def link_ohm(mil, link_mm, oz, detour=LINK_DETOUR):
    return r_mm2(mil * 0.0254 * oz * OZ_MM, link_mm * detour)


def pick_mil(sp, link_mm=25.0, tiers=MIL_TIERS):
    """按规格挑**最细够用**的档 ✓ ⇒ `(mil, 说明)` ✓

    两条硬条件 ✓：① 本档载流 / 温升够段电流 ✓；② **整段**压降 ≤ `drop_pct` ✓ ——
    压降按"一块板那条链路"折算 ✓：梯形注入下 ✓ 段内等效电流 = 段电流 × (S+1)/2 ✓，
    两程（5V ＋ GND ✓）各算一遍 ✓。✗ 这是**估算** ✗（真实长度看布线结果 ✓，验算交给本工具 ✓）。
    """
    i_seg = sp["seg_boards"] * (sp["pixel_amps"] + sp["misc_amps"])
    budget = sp["rail"] * sp["drop_pct"] / 100.0 / SPEC_MARGIN
    half = (sp["seg_boards"] + 1) / 2.0
    rows, pick = [], None
    for mil in tiers:
        w = mil * 0.0254
        amp = amp_at(w, sp["oz"], sp["temp_rise"])
        d = 2.0 * i_seg * half * link_ohm(mil, link_mm, sp["oz"])
        ok = amp >= i_seg - 1e-9 and d <= budget
        rows.append((mil, amp, d, ok))
        if ok and pick is None:
            pick = mil
    why = ("段电流 %.3f A ✓｜链路 %.0f mm × 绕行 %.1f ✓ ⇒ %s"
           % (i_seg, link_mm, LINK_DETOUR,
              "、".join("%d mil → %.3f V%s" % (m, d, "✓" if ok else "✗") for (m, _a, d, ok) in rows)))
    return (pick or tiers[-1]), why


# ── 读文件：走线的形状 / 声明 ✓ ──────────────────────────────────────────────
def trace_pts(t):
    """走线的**采样点**（sketch 单位 ✓；有弧按弧 ✓ —— 与渲染同一个 `pcb_wire` ✓）"""
    a, b = PW.abs_ends(t["geo"])
    return PW.curve_pts(t["geo"], t.get("bezier"), 24) if t.get("bezier") else [a, b]


def trace_len_mm(t):
    return PW.poly_len(trace_pts(t)) * SK


CONN_BLOCK = re.compile(r'<connector\s+connectorId="([\w]+)"[^>]*?>(.*?)</connector>', re.S)
CONNECT_IN = re.compile(r'<connect\s+connectorId="([\w]+)"\s+modelIndex="(\d+)"\s+layer="([\w]+)"')
COPPER_RE = re.compile(r"^copper")     # ⇒ 只认 PCB 那两层的声明 ✓（`copper0`/`copper1`/…trace ✓）


def read_decls(text, vias):
    """⇒ `(wires, adj)` ✓

    · `wires[mi]` = `pcb_wire.parse_trace` 的结果 ✓（`ends` 已按**自己那个脚**分好 ✓）；
    · `adj[节点]` = **无向**邻接表 ✓；节点 = `("w", 走线 mi)` / `("v", 过孔 mi)` /
      `("p", 件 mi, 脚号)` ✓（脚号已去掉 `connector` 前缀 ✓）

    ★★ 三条**实测**踩出来的坑 ✓（2026-10-05，`pixel-pcb-v76.fzz` ✓）：

    ① **逐个 connector 分** ✗ —— 按整个实例收 `<connect>` ✗ ⇒ 从 `J1.0` 会跳到 J1 **三根针**
       上的所有东西 ✗（GND / DATA 全跳过去 ✗）⇒ 实测报出"铜还差 0.448 mm"的**假**跳转 ✗、
       两个方向算出的压降一个 0.0064 V 一个 0.0000 V ✗（后者只跳 0 段 —— "乱跳"的指纹 ✓）。
    ② **只看 `pcbView` 那一段** ✗ —— 实例里三个视图**各有一份** `<connector><connects>` ✗
       ⇒ 整块一起收就会把**面包板视图**的连线当成 PCB 的 ✗。同一条病 `fz_deglue_views.py`
       里也写着 ✓。
    ③ **还要按层筛** ✗＋**边要双向** ✗ —— 即使只取 `pcbView` ✓，J1 那一段里仍留着面包板的
       **胶水残留** `<connect layer="breadboardbreadboard"/>` ✗ ⇒ 从 `J1.1` 一跳进 `Breadboard1`
       的孔 ✗；而且 XML **常常只声明一头** ✗（实测 `90014282` 只声明 `connector0` ⇒ 只要不反向
       建边，`GND` 从 `J1.1` 出发**只能走 3 个节点** ⇒ 9 个脚全报"走不到" ✗）。
    """
    raw, wires = [], {}
    for _ind, blk in PW.blocks(text):
        m = re.search(r'modelIndex="(\d+)"', blk)
        if not m:
            continue
        mi = m.group(1)
        mid = re.search(r'moduleIdRef="([^"]+)"', blk)
        if mid and mid.group(1).startswith("Wire"):
            t = PW.parse_trace(blk)
            if t is not None:
                wires[mi] = t
        mv = re.search(r"<pcbView\b[^>]*>(.*?)</pcbView>", blk, re.S)
        if not mv:
            continue
        for (own, body) in CONN_BLOCK.findall(mv.group(1)):
            raw.append((mi, own, CONNECT_IN.findall(body)))

    def node(mi, cid):
        if mi in wires:
            return ("w", mi)
        if mi in vias:
            return ("v", mi)
        return ("p", mi, str(cid).replace("connector", ""))

    adj = {}
    for (mi, own, lst) in raw:
        a = node(mi, own)
        for (cid, peer, lay) in lst:
            if not COPPER_RE.match(lay):           # ★ 坑 ③：面包板 / 原理图的残留 ✗
                continue
            b = node(peer, cid)
            adj.setdefault(a, set()).add(b)        # ★ 坑 ③：双向 ✓（XML 常只声明一头 ✓）
            adj.setdefault(b, set()).add(a)
    return wires, {k: sorted(v) for k, v in adj.items()}


def radius_v_mm(vd):
    return (vd.get("hole_mm") or 0.3) / 2.0 + (vd.get("ring_mm") or 0.15)


def half_w_mm(t):
    return (t.get("mils") or DEF_MIL) * 0.0254 / 2.0


# ── ③ 声明 ↔ 几何：这一跳的**铜净距** ✓ ─────────────────────────────────────
def gap_mm(na, nb, wires, vias, pads):
    """两个节点之间**铜的净距** ✓（mm ✓；≤0 ⇒ 真碰上 ✓；None ⇒ 算不了 ✓）

    `na`/`nb` = 节点键 ✓（`("p", mi, cid)` 焊盘 / `("w", mi)` 走线 / `("v", mi)` 过孔 ✓）
    """
    wa = wires.get(na[1]) if na[0] == "w" else None
    wb = wires.get(nb[1]) if nb[0] == "w" else None
    va = vias.get(na[1]) if na[0] == "v" else None
    vb = vias.get(nb[1]) if nb[0] == "v" else None
    pa = pads.get((na[1], na[2])) if na[0] == "p" else None
    pb = pads.get((nb[1], nb[2])) if nb[0] == "p" else None

    if wa and wb:                                     # 线 ↔ 线
        A, B = trace_pts(wa), trace_pts(wb)
        for i in range(len(A) - 1):
            for j in range(len(B) - 1):
                if PC.seg_seg(A[i], A[i + 1], B[j], B[j + 1]):
                    return 0.0
        d = min([PC.d_pt_seg(p, B[i], B[i + 1]) for p in (A[0], A[-1])
                 for i in range(len(B) - 1)]
                + [PC.d_pt_seg(p, A[i], A[i + 1]) for p in (B[0], B[-1])
                   for i in range(len(A) - 1)])
        return d * SK - half_w_mm(wa) - half_w_mm(wb)
    if wa and vb is not None:                          # 线 ↔ 过孔
        A = trace_pts(wa)
        d = min(PC.d_pt_seg(vb["p"], A[i], A[i + 1]) for i in range(len(A) - 1))
        return d * SK - radius_v_mm(vb) - half_w_mm(wa)
    if wb and va is not None:
        return gap_mm(nb, na, wires, vias, pads)
    if va is not None and vb is not None:               # 过孔 ↔ 过孔
        d = math.hypot(va["p"][0] - vb["p"][0], va["p"][1] - vb["p"][1]) * SK
        return d - radius_v_mm(va) - radius_v_mm(vb)
    for (w, p, other_v) in ((wa, pb, None), (wb, pa, None)):      # 线 ↔ 焊盘
        if w and p:
            A = trace_pts(w)
            hw = half_w_mm(w)
            if p.get("circle"):
                (cx, cy), r = p["circle"]
                d = min(PC.d_pt_seg((cx, cy), A[i], A[i + 1]) for i in range(len(A) - 1))
                return d * SK - r * SK - hw
            d = min(PC.d_pt_rect(A[i], p["box"]) for i in range(len(A)))
            return d * SK - hw
    for (v, p) in ((va, pb), (vb, pa)):                            # 过孔 ↔ 焊盘
        if v is not None and p:
            return PC.d_pt_pad(v["p"], p) * SK - radius_v_mm(v)
    return None


# ── ① 声明图上的生成树 ✓ ────────────────────────────────────────────────────
def node_box(k, wires, vias, pads, grow=0.0):
    """节点的包围盒 ✓（mm ✓）—— 几何补跳的**粗筛** ✓（✗ 不筛就得 3 万对 × 576 次线段判 ✗）"""
    if k[0] == "w":
        t = wires.get(k[1])
        if not t:
            return None
        pts, h = trace_pts(t), half_w_mm(t) + grow
        return (min(p[0] for p in pts) * SK - h, min(p[1] for p in pts) * SK - h,
                max(p[0] for p in pts) * SK + h, max(p[1] for p in pts) * SK + h)
    if k[0] == "v":
        v = vias.get(k[1])
        if not v:
            return None
        r = radius_v_mm(v) + grow
        return (v["p"][0] * SK - r, v["p"][1] * SK - r,
                v["p"][0] * SK + r, v["p"][1] * SK + r)
    p = pads.get((k[1], k[2]))
    if not p:
        return None
    if p.get("circle"):
        (cx, cy), r = p["circle"]
        r = r * SK + grow
        return (cx * SK - r, cy * SK - r, cx * SK + r, cy * SK + r)
    r = p["box"]
    return (r[0] * SK - grow, r[1] * SK - grow, r[2] * SK + grow, r[3] * SK + grow)


def geom_adj(wires, vias, pads, tol=GEO_TOL_MM):
    """**几何贴上**的边 ✓（声明只写了一头 / 干脆没写的时候补 ✓；`gap ≤ tol` 才算 ✓）

    ★ 为什么要它 ✓：Fritzing 里"铜贴上了"就算连通 ✓，而 XML 的 `<connect>` **只声明
      Fritzing 自己记下的那些** ✗ —— 实测 `pixel-pcb-v76.fzz` 的 `GND` 网就有半条没声明 ✓
      ⇒ 只看声明会把它算成"走不到" ✗（假红 ✗）。补出来的边在报告里**单列** ✓，不当默认 ✓。
    """
    nodes = ([("w", mi) for mi in wires] + [("v", mi) for mi in vias]
             + [("p", mi, cid) for (mi, cid) in pads])
    box = {k: node_box(k, wires, vias, pads, tol) for k in nodes}
    out = {}
    for i, a in enumerate(nodes):
        ba = box[a]
        if not ba:
            continue
        for b in nodes[i + 1:]:
            bb = box[b]
            if not bb or ba[2] < bb[0] or bb[2] < ba[0] or ba[3] < bb[1] or bb[3] < ba[1]:
                continue
            g = gap_mm(a, b, wires, vias, pads)
            if g is not None and g <= tol:
                out.setdefault(a, []).append(b)
                out.setdefault(b, []).append(a)
    return out


def merge_adj(a, b):
    out = {k: set(v) for k, v in a.items()}
    for k, vs in b.items():
        out.setdefault(k, set()).update(vs)
    return {k: sorted(v) for k, v in out.items()}


def neighbors(adj, node):
    """这个节点**声明**接到的邻居 ✓（按**自己那个脚**分 ✓，✗ 不是整个实例 ✗）"""
    return list(adj.get(node, ()))


def build_tree(root, adj):
    """从注入针出发 ✓ ⇒ `(parent, order)` ✓（生成树 ✓）"""
    parent, order, seen = {root: None}, [root], {root}
    stack = [root]
    while stack:
        u = stack.pop()
        for v in neighbors(adj, u):
            if v in seen:
                continue
            seen.add(v)
            parent[v] = u
            order.append(v)
            stack.append(v)
    return parent, order


def path_to(parent, node):
    out, u = [], node
    while parent.get(u):
        out.append(u)
        u = parent[u]
    return out


# ── 主流程 ──────────────────────────────────────────────────────────────────
def load_mod(path):
    s = importlib.util.spec_from_file_location("_pc_nets", path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def spec_of(mod, opt):
    sp = dict(getattr(mod, "POWER_SPEC", {}) or {}) if mod else {}
    out = dict(seg_boards=float(sp.get("seg_boards", 8)),
               pixel_amps=float(sp.get("pixel_amps", 0.06)),
               misc_amps=float(sp.get("misc_amps", 0.002)),
               oz=float(sp.get("oz", 1)), rail=float(sp.get("rail", 5.0)),
               drop_pct=float(sp.get("drop_pct", 5.0)),
               conn_amps=float(sp.get("connector_amps", 1.0)),
               temp_rise=float(sp.get("temp_rise", 10.0)),
               board_mm=float(sp.get("board_mm", 1.6)),
               power=tuple(sp.get("power", ("5V", "GND"))),
               ports=list(sp.get("ports", [])),
               pixel_re=sp.get("pixel_re", r"WS2812"),
               conn_re=sp.get("connector_re", CONN_RE))
    for k, name in (("seg-boards", "seg_boards"), ("pixel-amps", "pixel_amps"),
                    ("misc-amps", "misc_amps"), ("oz", "oz"), ("rail", "rail"),
                    ("drop-pct", "drop_pct"), ("connector-amps", "conn_amps"),
                    ("temp-rise", "temp_rise"), ("board-mm", "board_mm")):
        if k in opt:
            out[name] = float(opt[k])
    if "power" in opt:
        out["power"] = tuple(x.strip() for x in opt["power"].split(",") if x.strip())
    if "ports" in opt:
        out["ports"] = [x.strip() for x in opt["ports"].split(",") if x.strip()]
    return out


def analyse_net(net, pads, sp, M, pads_by_mi, vias_by_mi, wires, adj, gadj, mi2title):
    """一个方向一遍 ✓ ⇒ `[dict(drop, path, worst, gaps, missing, glue, feed, out)]` ✓

    `pads` = `[((mi, cid), pad), …]` ✓（**已按网表解析好** ✓）；`mi` = 实例号 ✓
    """
    per_board = sp["pixel_amps"] + sp["misc_amps"]
    port_keys = [k for (k, q) in pads if _is_conn(M, q, sp)]
    if len(port_keys) < 2:
        return None
    loads0 = {k: (sp["pixel_amps"] if re.search(sp["pixel_re"], _mid(M, q) or "")
                  else sp["misc_amps"]) for (k, q) in pads}
    rows = []
    for feed_key, out_key in ((port_keys[0], port_keys[1]), (port_keys[1], port_keys[0])):
        root = ("p",) + feed_key
        parent, order = build_tree(root, adj)
        loads = {("p",) + out_key: (sp["seg_boards"] - 1) * per_board}
        for k, a in loads0.items():
            if k != feed_key and k != out_key:
                loads[("p",) + k] = a
        # ★ 声明补不齐的时候 ✓，再用**几何贴铜**补一次 ✓（报告里单列 ✓，✗ 不当默认 ✓）
        glue, gset = [], {(u, v) for u, vs in gadj.items() for v in vs
                          if v not in adj.get(u, ())}
        if gset and [k for k in loads if k not in parent]:
            parent, order = build_tree(root, merge_adj(adj, gadj))
        for v in order:
            u = parent.get(v)
            if u is not None and (u, v) in gset:
                glue.append((u, v, gap_mm(v, u, wires, vias_by_mi, pads_by_mi)))
        missing = [k for k in loads if k not in parent]
        sub = {u: 0.0 for u in order}
        for u, a in loads.items():
            if u in sub:
                sub[u] += a
        for u in reversed(order):                       # ★ 子先于父 ✓（顺序错了会少算 ✓）
            if parent.get(u):
                sub[parent[u]] += sub[u]
        path = path_to(parent, ("p",) + out_key)        # 从出线针倒着数 ✓
        path = list(reversed(path))                     # ⇒ 从进线针到出线针 ✓
        drop, hops = 0.0, []
        worst = (0.0, "（没有载流边 ✗）", 0.0, 9e9, 0.0)
        for v in path:
            i = sub.get(v, 0.0) if v in sub else 0.0
            if v[0] == "w":
                t = wires[v[1]]
                w, L = (t.get("mils") or DEF_MIL) * 0.0254, trace_len_mm(t)
                drop += i * r_mm2(w * sp["oz"] * OZ_MM, L)
                amp = amp_at(w, sp["oz"], sp["temp_rise"])
                lbl = "走线 %s：%.0f mil（%.3f mm ✓）× %.1f mm ✓" % (v[1], w / 0.0254, w, L)
                hops.append((i, L, None))
            elif v[0] == "v":
                vd = vias_by_mm = vias_by_mi.get(v[1], {})
                a2 = via_area_mm2(vd.get("hole_mm") or 0.3)
                drop += i * r_mm2(a2, sp["board_mm"])
                weq = via_eq_w_mm(vd.get("hole_mm") or 0.3, sp["oz"])
                amp = amp_at(weq, sp["oz"], sp["temp_rise"])
                lbl = "过孔 %s：孔 Ø%.2f mm ✓ 孔壁 %.4f mm²（等效 %.3f mm 宽 ✓）" % (
                    v[1], vd.get("hole_mm") or 0.3, a2, weq)
                hops.append((i, None, a2))
            else:
                continue
            if amp / max(i, 1e-9) < worst[3]:
                worst = (i, lbl, amp, amp / max(i, 1e-9), temp_rise(i, w if v[0] == "w" else weq,
                                                                   sp["oz"]))
        gaps = []
        for v in path:
            u = parent[v]
            if u is None:
                continue
            g = gap_mm(v, u, wires, vias_by_mi, pads_by_mi)
            if g is not None:
                gaps.append((g, v))
        rows.append(dict(drop=drop, path=path, worst=worst, gaps=gaps, missing=missing,
                         hops=hops, glue=glue, feed=feed_key, out=out_key))
    return rows


def drop_at(hops, mil, sp):
    """**同一条路径**换个线宽重算段压降 ✓（mm ✓；`mil=None` ⇒ 只算过孔那几跳 ✓）

    ★ 为什么不重新布线 ✓：这一栏答的是"**这条走法**换个宽度会掉多少" ✓ ——
      ✗ 不是"换成这个宽度会布成什么样" ✗（那要真跑一遍布线器 ✓，`gen_routes.py` 干 ✓）。
    """
    v = 0.0
    for (i, L, a2) in hops:
        if L is None:
            v += i * r_mm2(a2, sp["board_mm"])
        else:
            v += i * r_mm2(mil * 0.0254 * sp["oz"] * OZ_MM, L)
    return v


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opt = {}
    for a in argv:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            opt[k] = v
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    if "nets" not in opt:
        print("✗ 要 `--nets=<项目数据.py>`（里面的 `EXPECT` ＝ 网表 ✓）⇒ 算不了 ✓")
        return 2
    mod = load_mod(opt["nets"])
    sp = spec_of(mod, opt)
    trymils = [int(x) for x in opt.get("try-mil", "").replace(" ", "").split(",") if x]
    EXPECT = dict(getattr(mod, "EXPECT", {}) or {})
    M = PC.collect(path)
    mi2title = {p.get("mi"): p.get("title") for p in M["parts"] if p.get("mi")}
    pads_by_mi = {(q["mi"], str(q["cid"]).replace("connector", "")): q for q in M["pads"]}
    vias_by_mi = {v["inst"]: v for v in M["vias"] if v.get("inst")}
    for v in vias_by_mi.values():
        v["hole_mm"] = v.get("hole_mm") or 0.3
        v["ring_mm"] = v.get("ring_mm") or 0.15
    wires, adj = read_decls(M["text"], vias_by_mi)
    gadj = geom_adj(wires, vias_by_mi, pads_by_mi)

    per_board = sp["pixel_amps"] + sp["misc_amps"]
    seg_a = sp["seg_boards"] * per_board
    print("== %s（包内 %s）==" % (os.path.basename(path), M["name"]))
    print("   规格：一段 **%g** 块 × 每块 **%.3f A**（像素 %.3f ＋ 其它 %.3f ✓）⇒ 段电流 "
          "**%.3f A** ✓｜铜 %.2g oz ✓｜走线 %d 根 / 过孔 %d 颗 ✓"
          % (sp["seg_boards"], per_board, sp["pixel_amps"], sp["misc_amps"], seg_a, sp["oz"],
             len(wires), len(vias_by_mi)))
    print("   预算：段压降 ≤ **%.1f%%** × %.2f V = %.3f V ✓｜温升 ≤ %g °C ✓｜针 ≤ %.2f A ✓｜"
          "声明↔几何容差 %.2f mm ✓"
          % (sp["drop_pct"], sp["rail"], sp["rail"] * sp["drop_pct"] / 100.0,
             sp["temp_rise"], sp["conn_amps"], GEO_TOL_MM))
    _mil, _why = pick_mil(sp)
    print("   规格反推线宽：**%d mil** ✓（%s ✓）" % (_mil, _why))

    fails, seg_drop = [], 0.0
    title2mi = {t: mi for mi, t in mi2title.items()}
    for net in sp["power"]:
        keys = [(m.rsplit(".", 1)[0], m.rsplit(".", 1)[1].replace("connector", ""))
                for m in EXPECT.get(net, []) if isinstance(m, str) and "." in m]
        pads = []
        for (_t, _c) in keys:
            mi = title2mi.get(_t)
            q = pads_by_mi.get((mi, _c))
            if q is not None:
                pads.append(((mi, _c), q))
        rows = analyse_net(net, pads, sp, M, pads_by_mi, vias_by_mi, wires, adj, gadj, mi2title)
        if not rows:
            print("\n   ── 网 `%s`：认不出两个连接器针 / 走线没布 ⇒ 跳过 ✓（`--ports=` 可指名 ✓）"
                  % net)
            continue
        print("\n   ── 网 `%s` ──" % net)
        for r in rows:
            print("      方向 `%s.%s` ⇒ `%s.%s`：IN→OUT 压降 %.4f V ✓（沿路 %d 段导线 ＋ %d 颗过孔 ✓）"
                  % (mi2title.get(r["feed"][0]) or r["feed"][0], r["feed"][1],
                     mi2title.get(r["out"][0]) or r["out"][0], r["out"][1], r["drop"],
                     sum(1 for v in r["path"] if v[0] == "w"),
                     sum(1 for v in r["path"] if v[0] == "v")))
        best = max(rows, key=lambda r: r["drop"])
        print("      ★ 注入针电流 **%.3f A** ≤ %.2f A（连接器额定 ✓）%s"
              % (seg_a, sp["conn_amps"], "✓" if seg_a <= sp["conn_amps"] + 1e-9 else "✗ 超"))
        print("      ★ 最坏那条边过 **%.3f A** ✓ %s ⇒ 载流 %.2f A、温升 %.1f °C ⇒ 余量 **%.2f×** %s"
              % (best["worst"][0], best["worst"][1], best["worst"][2], best["worst"][4],
                 best["worst"][3], "✓" if best["worst"][3] >= 1 else "✗"))
        print("      ★ 取较坏方向 ✓｜整段折算（×%.1f ✓）**%.4f V** ✓"
              % ((sp["seg_boards"] + 1) / 2.0,
                 best["drop"] * (sp["seg_boards"] + 1) / 2.0))
        seg_drop += best["drop"] * (sp["seg_boards"] + 1) / 2.0
        if trymils:
            print("      ── 同一条路径换档重算 ✓（✗ 不是重新布线 ✗；下表 = **本网**段压降 ✓"
                  "，取较坏方向 ✓ —— 整段合计要把 5V＋GND 两张网加起来 ✓）")
            wr = max(rows, key=lambda r: r["drop"])
            iw = max(r["worst"][0] for r in rows)
            for mil in trymils:
                d = drop_at(wr["hops"], mil, sp) * (sp["seg_boards"] + 1) / 2.0
                amp = amp_at(mil * 0.0254, sp["oz"], sp["temp_rise"])
                dt = temp_rise(iw, mil * 0.0254, sp["oz"])
                print("         %2d mil（%.3f mm ✓）⇒ 本网段压降 **%.4f V**（%.2f%% ✓）｜"
                      "本档载流 %.2f A ≥ 最坏边 %.3f A ⇒ %s｜最坏边温升 %.1f °C ⇒ %s"
                      % (mil, mil * 0.0254, d, 100.0 * d / sp["rail"], amp, iw,
                         "✓" if amp >= iw else "✗ 超", dt,
                         "✓" if dt <= sp["temp_rise"] else "✗ 超"))
        badd = [(g, v) for r in rows for (g, v) in r["gaps"] if g > GEO_TOL_MM]
        print("      声明↔几何复核：查了 %d 跳 ✓、**对不上 %d 处** %s"
              % (sum(len(r["gaps"]) for r in rows), len(badd), "✓" if not badd else "✗"))
        for g, v in sorted(badd)[:4]:
            print("         ✗ 跳到 `%s %s` 这一跳，铜还差 **%.3f mm** ✗" % (v[0], v[1], g))
        miss = sorted({k for r in rows for k in r["missing"]},
                      key=lambda k: (mi2title.get(k[1]) or k[1], k[2]))
        if miss:
            print("      ✗ 声明上**走不到**的脚 %d 个：%s"
                  % (len(miss), "、".join("%s.%s" % (mi2title.get(k[1]) or k[1], k[2])
                                          for k in miss[:5])))
            fails.append("网 `%s`：%d 个脚在声明图上走不到 ✗（拿 `pcb_check` ⑩/⑫ 复核 ✓）"
                         % (net, len(miss)))
        glue = sorted({(min(u, v), max(u, v)) for r in rows for (u, v, _g) in r["glue"]})
        if glue:
            print("      · 声明只写了一头 / 没写的贴铜跳 **%d 处** ✓（`gap ≤ %.2f mm` ✓，"
                  "Fritzing 里也算连通 ✓；✗ 不算不过 ✓）"
                  % (len(glue), GEO_TOL_MM))
        if badd:
            fails.append("网 `%s`：%d 处声明跳转**铜没接上** ✗（最差 %.3f mm ✓）"
                         % (net, len(badd), max(g for g, _v in badd)))
        if seg_a > sp["conn_amps"] + 1e-9:
            fails.append("网 `%s`：注入针 %.3f A > 连接器额定 %.2f A ✗" % (net, seg_a, sp["conn_amps"]))
        if best["worst"][3] < 1:
            fails.append("网 `%s`：最坏边 %.3f A > 载流 %.2f A ✗"
                         % (net, best["worst"][0], best["worst"][2]))
        if best["worst"][4] > sp["temp_rise"]:
            fails.append("网 `%s`：温升 %.1f °C > %g °C ✗" % (net, best["worst"][4], sp["temp_rise"]))

    budget = sp["rail"] * sp["drop_pct"] / 100.0
    print("\n   ── 整段（%g 块 ✓ 5V ＋ GND **两程** ✓）──" % sp["seg_boards"])
    print("      段压降合计 **%.4f V**（%.2f%% of %.2f V ✓）｜预算 %.3f V ⇒ %s"
          % (seg_drop, 100.0 * seg_drop / sp["rail"], sp["rail"], budget,
             "✓" if seg_drop <= budget else "✗ 超"))
    if seg_drop > budget:
        fails.append("段压降 %.4f V > 预算 %.3f V ✗" % (seg_drop, budget))
    print("\n   %s" % ("✓ 全过：载流 / 压降 / 针电流 / 声明兑现 都在预算内 ✓" if not fails
                       else "✗ %d 条不过：" % len(fails)))
    for f in fails:
        print("      - %s" % f)
    print("CURRENT ok=%d segdrop_v=%.4f budget_v=%.3f seg_a=%.3f"
          % (0 if fails else 1, seg_drop, budget, seg_a))
    return 1 if fails else 0


def _mid(M, q):
    for p in M["parts"]:
        if p.get("title") == q.get("title"):
            return p.get("moduleId") or ""
    return ""


def _is_conn(M, q, sp):
    return bool(q) and bool(re.search(sp["conn_re"], _mid(M, q) or ""))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
