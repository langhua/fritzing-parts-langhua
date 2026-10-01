# -*- coding: utf-8 -*-
r"""PCB 读回校验器（通用 ✓）2026-09-30 立

把 sketch 的 **pcbView** 读成**几何** ⇒ 查六件事 ✓
（PCB 上是**物理**连接 ✗ —— 两根线之间必须有铜，不是"同名即连通" ✓，见 AGENTS §5b 第 5 条 ✓）：

① **悬空端点**：走线端点既没落在焊盘上 ✓、也没挨上别的走线 ⇒ 废线/断线 ✗
② **板外**：走线端点 / 过孔落在**板框外** ⇒ ✗（就是 8 月那次"挪完件冒出远处垃圾走线"的病 ✓）
③ **过孔**：过孔至少要挨到**某一层**的铜 ⇒ 否则是块孤立铜 ✗
④ **同层交叉 / 重叠**：两条走线在**同一层**相交或重叠 ⇒ 物理上就是**短接** ✗
   （★ 不同层交叉 = 正常 ✓）
⑤ **连通性 == 网表** ✓（期望来自项目数据 `EXPECT` ✓）：几何接触 ⇒ 并查集 ⇒ 逐网比 ✓
   ★ **短接会自动在 ⑤ 现形** ✓（两个网被粘成一片 ⇒ 对不上 ✓）
   ★ 判据是**几何**（端点重合 / 端点落在焊盘或别条线上 / 过孔贯通两层 ✓）——
     与 Fritzing 记的 `<connects>` **无关** ✓ ⇒ 这份校验**不共用**生成器的世界模型 ✓（不许自证 ✓）
⑥ ★★ **过孔铜盘不许压到焊盘** ✓（2026-10-01 补 ✗）
   —— ③ 只查"**孔心**落没落在**盘框**里" ✗ ⇒ “孔心在盘外、但**环叠在盘上**”
   这类**全部漏掉** ✗✗（2026-10-01 v47 实测：18 个过孔里 **7 个**的铜盘压到邻盘，
   其中 **6 处是别的网** ⇒ 实物短路 ✗；用户拿图一眼就看出来了 ✗ —— 这条就是那次教训
   补上的机器守 ✓，`pcb_route` 里的 `novia` 只禁了盘内 ✓ 不够 ✗）。
   铜盘外半径 = `(孔直 + 环宽)/2 + 环宽/2` ✓（口径见 `fritzing-sketch-format-notes.md` 的 F17 ✓）。

⚠️ **通孔盘（THT）口径**：`pcb_pads` 报的层 = svg 里画的那层 ✓；但**带孔**的盘物理上**贯通两层** ✓
   ⇒ 这里按"贯通两层"算 ✓，并把"只画了一层"**另行提示** ✓（不静默 ✗；口径待拿 Fritzing 源码核 ✓）。

用法：
  py -3.13 tools\pcb_check.py <sketch.fzz> [--nets=<含 EXPECT 的项目数据.py>]
退出码：0 = 全过 ✓；1 = 有问题 ✗（每条问题都点名 ✓，不静默 ✓）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import part_box as PB                                            # noqa: E402
import pcb_pads as PP                                            # noqa: E402
import pcb_wire as PW                                            # noqa: E402
import projdata                                                  # noqa: E402

TOL = 0.5                    # sketch 单位 ✓（≈ 0.14 mm）：端点重合 / 落在焊盘上的容差 ✓（Fritzing 写 6 位有效数字 ✓）
IND = "  "


# ── 几何小工具（一份实现 ✓）────────────────────────────────────────────────
def d_pt_seg(p, a, b):
    """点到**线段**的距离 ✓"""
    vx, vy = b[0] - a[0], b[1] - a[1]
    wx, wy = p[0] - a[0], p[1] - a[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return ((wx - t * vx) ** 2 + (wy - t * vy) ** 2) ** 0.5


def on_seg(p, a, b, tol=TOL):
    return d_pt_seg(p, a, b) <= tol


def in_rect(p, r, tol=TOL):
    return r[0] - tol <= p[0] <= r[2] + tol and r[1] - tol <= p[1] <= r[3] + tol


def seg_rect(a, b, r, tol=TOL):
    """线段与矩形是否相交 ✓（端点在内 / 穿过 / 贴着都算 ✓）"""
    if in_rect(a, r, tol) or in_rect(b, r, tol):
        return True
    r2 = (r[0] - tol, r[1] - tol, r[2] + tol, r[3] + tol)
    edges = [((r2[0], r2[1]), (r2[2], r2[1])), ((r2[2], r2[1]), (r2[2], r2[3])),
             ((r2[2], r2[3]), (r2[0], r2[3])), ((r2[0], r2[3]), (r2[0], r2[1]))]
    return any(seg_seg(a, b, c, d) for c, d in edges)


def _cr(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def seg_seg(a, b, c, d):
    """两线段是否相交 ✓（含端点相接与共线重叠 ✓）"""
    d1, d2 = _cr(c, d, a), _cr(c, d, b)
    d3, d4 = _cr(a, b, c), _cr(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    return (abs(d1) < 1e-9 and on_seg(a, c, d)) or (abs(d2) < 1e-9 and on_seg(b, c, d)) \
        or (abs(d3) < 1e-9 and on_seg(c, a, b)) or (abs(d4) < 1e-9 and on_seg(d, a, b))


# ★★ 过孔**安全距离**规则 ✓（2026-10-01 用户定 ✓，原话：「我想先实现通孔不能在元件内，
#   并与有安全距离的规则，比如 Via10 在 J1 焊盘上打孔了」✓）
#   围栏（FAIL ✗）两条 —— 都按**过孔铜盘**（Ø = 孔 + 2×环 ✓，本仓 = 0.6 ⇒ 半径 0.30 ✓）算：
#     ⑥a 铜盘压到**任何**焊盘（**含同一张网** ✗✗）⇒ 旧口径把同网的 via-in-pad 当"合法"✗
#         —— 用户点名否掉 ✗（J1 是 1.0 mm 间距的座子，孔打在它盘上 = 打穿了元件 ✗）；
#     ⑦  铜盘与**任何焊盘**的净距 < `VIA_SAFE_MM` ✗；
#         或者碰到**元件画出来的铜**（`copper0/1` ✓ 逐图元 ✓ 含线宽 ✓）✗
#         （= "有安全距离 + 通孔不能在元件内" ✓；净距 = 铜盘边 → 焊盘/铜图形边 ✓）
#         ★ 丝印（`silkscreen`/`outline`）**不算** ✗ —— 孔上盖丝印是印刷问题 ✓，
#           不是"打在元件上"✗（实测把它算进来会多出 13 条噪音 ✗）。
#     ⑧  **同一面**的两个件的**图元不许相交** ✗（异面叠着是**正常**的 ✓）
#         ★ 这边**要**看丝印 ✓ —— 件的丝印轮廓就是它的**本体** ✓（C1×U1 就是这么抓到的 ✓）。
#   ★ 值 = **0.25 mm**（我定的 ✓，可调 ✓）：工艺能力表里 1 oz 铜**最小线间距 0.127 mm**（嘉立创 ✓），
#     0.25 = 给装配/蚀刻留一档余量 ✓；✗ 别跟布线器的 `VIA_PAD_KEEPOUT_MM=0.45`（布局用的**预警**区 ✓）
#     混为一谈 ✗ —— 一个是"量出来合不合法" ✓（本文件 ✓），一个是"布的时候躲多远" ✓（`pcb_route` ✓），
#     **两份实现** ✓（故意的 ✓：互不背书 ⇒ 不会一起错 ✗）。
VIA_SAFE_MM = 0.25
# ★★ EPAD（裸露焊盘）上的**同网 via-in-pad 是允许的** ✓（2026-10-01 用户定 ✓）：
#   用户原话：「是在 EPAD 上开通孔接 GND 吗？这个必须允许」✓
#   —— QFN 的中央散热盘要接地，业界常规就是在 EPAD 上打一簇过孔接到背面地 ✓；
#      ✗ 旧口径把它也当违规 ✗（实测：`U1.connector20` 就是 EPAD ✓，被 ⑥ 报成“压在盘上” ✗）
#      ⇒ 等于禁止了正确做法 ✗。
#   ★ 例外**只限 EPAD** ✓（不扩大到其它焊盘 ✗）：接插件（`J1`/`J2`）、电阻、电容的盘上
#     **仍然禁止打孔** ✗ —— 那才是用户点名的 `Via10` 打在 `J1.connector2` 上那种（机械/装配 ✗）。
#   ★ 判 EPAD 的**依据**（不猜 ✗）：该焊盘的**连接器名**里含 `EPAD`/`EP`/`exposed` ✓
#     （本仓实例：`CH32V003F4U6` 的 `connector20 name="EPAD"` ✓、`RT6150` 的 `EP` ✓、
#      `TX-AH` 的 `EPAD1/2` ✓ —— 都命中 ✓）。
EPAD_EXEMPT = True
# ★★ 「**细间距焊盘**上的同网 via-in-pad」也允许 ✓（2026-10-01 用户选 (ii) ✓：
#   原话「2 吧，我看看啥样」✓），**但接插件 / 电阻 / 电容仍然禁止** ✗。
#   ★ 判据 = **物理量**（不猜 ✗、也不列白名单 ✗）：该焊盘到**同一个件**最近焊盘的中心距
#     ≤ `VIA_INPAD_PITCH_MM = 0.65 mm` ✓ —— 这正是“出口被夹死”的那种脚 ✓。
#     实测本仓：`U1` QFN20 = **0.40** ✓（命中 ✓）、`D3` SOT-363 = 0.65 ✓（命中 ✓）、
#     `LED2` = 0.85 ✗、`J1`/`J2` = **1.00** ✗、`R1`/`C1`（0402）= **0.90** ✗、
#     `C2` �©0603 = 2.07 ✗、`L1` 线圈 = 7.40 ✗ ⇒ **用户禁的那三类全部落在外面** ✓。
#   ★ 工艺提醒（要认账 ✓）：via-in-pad 会**吸锡**✗ ⇒ 制板时要选 **孔塞 / 盖油（tented & filled ✓）**，
#     否则贴片时锡会渗进孔里 ✓（嘉立创、PCBWay 都提供 ✓，可能略加价 ✓）。
VIA_INPAD_PITCH_MM = 0.65
# ★★ 元件之间（**同一层** ✓）要留的**安全间隔** ✓（2026-10-01 用户定 ✓：
#   「规则里还要元件之间保持安全间隔距离」✓）—— 比"不相交"严一档 ✓：
#   两件的图元最近距离必须 ≥ 本值 ✓（相交 ⇒ 负值 ⇒ 必定违规 ✓）。
#   ★ 取 0.25 mm（与 `VIA_SAFE_MM` 同值 ✓，好记 ✓；工艺上贴片件间距通常 ≥ 0.2 ✓）⇒ 一行可调 ✓。
PART_GAP_MM = 0.25
#   ★★ ⑦b / ⑧ 为什么必须**逐图元**判 ✗（2026-10-01 实测 ✓）：
#     ✗ 用"件的**占位框**（墨迹 bbox ✓）"会**大批假报** ✓：`NFC_Coil_20mm_6T_0p2_1`（L1）
#       的框是 **21.6×22.05 mm**（整块线圈 ✓），而板只有 **25×25 mm** ✓ ⇒ 15/16 个过孔
#       全被报成"在元件内" ✗；而 `LED2` 本来就坐在线圈**中间的空地**上 ✓（天线绕着电路 ✓
#       这是标准做法 ✓）⇒ 两件"同面相交"也是假报 ✗。
#     ✓ 改成逐图元（线圈 = `copper1` 里几百条螺旋 `<line>` ✓、按 `stroke-width/2` 外扩 ✓）：
#       过孔只要不碰那些线 ✓、LED2 只要不压到线 ✓ ⇒ 真违规才报 ✓。


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


# ── 读模型 ─────────────────────────────────────────────────────────────────
def is_epad(nm):
    """这个焊盘是不是**裸露焊盘** ✓（判据写在 `EPAD_EXEMPT` 的注释里 ✓）—— 不猜 ✗"""
    s = str(nm or "").lower()
    return ("epad" in s) or ("exposed" in s) or (s.strip() in ("ep", "ep0"))


def collect(path):
    """把一份 sketch 的 PCB 读成几何模型 ✓"""
    parts, board = PP.read_fzz(path)
    pads, warns, bodies = [], [], []
    for p in parts:
        mid = p.get("moduleId") or ""
        # ★ 板框自己 / 面包板件 **不是 PCB 上的元件** ✗（`pcb_pads` 的 main 也是这么分的 ✓）：
        #   面包板件在 pcbView 里挂着 830 个孔脚 ✗ ⇒ 不跳掉就报 830 条假“缺焊盘” ✗
        if mid == PP.BOARD_MID or mid.startswith("Breadboard") or mid.startswith("Via"):
            continue
        if p.get("fzp") is None:
            warns.append("%s: %s" % (p.get("title"), p.get("why")))
            continue
        # ★★ 元件**占位框**（本体墨迹 bbox ✓）—— ⑦「过孔安全距离」要用 ✓
        #   （2026-10-01 用户定 ✓：「通孔不能在元件内，并与有安全距离」✓）
        # ★ 元件**占位框**（本体墨迹 bbox ✓）+ **逐图元**（铜/丝印 ✓）+ **所在面** ✓
        #   （2026-10-01 用户定 ✓：「通孔不能在元件内，并与有安全距离」✓ + 「同面不许重叠」✓）
        #   ★ 逐图元那份（`shapes` ✓）是关键 ✓：外框会把 NFC 线圈的**中间空地**也算成实体 ✗
        #     ⇒ 实测 1 个假报 ✓（`LED2` 坐在线圈中间，天经地义 ✓）。
        bb = PP.part_body(p)
        bot = ((p.get("pv") or {}).get("bottom") or "").lower() == "true"
        bodies.append(dict(title=p.get("title"), box=bb, shapes=PP.part_shapes(p),
                           side="bottom" if bot else "top"))
        got, _ex, bad, _nt = PP.part_pads(p)
        warns += ["%s: %s" % (p["title"], b) for b in (bad or [])][:6]
        if not got:
            continue
        for cid, q in got.items():
            if q["hole_mm"] and q["layer"] != "both":
                warns.append("%s.%s 带孔（Ø%.2f）却只画在 `%s` 一层 ⇒ 按**贯通两层**算 ✓（口径待核 ⚠️）"
                             % (p["title"], cid, q["hole_mm"], q["layer"]))
            pads.append(dict(title=p["title"], cid=cid, nm=q["nm"], c=q["abs"], box=q["absbox"],
                             layer=q["layer"], thr=bool(q["hole_mm"]),
                             # ★ 是不是**裸露焊盘（EPAD）** ✓ —— ⑦/⑥ 的例外要靠它 ✓
                             epad=is_epad(q["nm"]),
                             mi=p.get("mi") or ""))
    # ★★ “细间距焊盘”标记 ✓（2026-10-01 用户选 (ii) ✓，判据见 `VIA_INPAD_PITCH_MM` ✓）：
    #   = 该盘中心到**同一个件**最近另一个盘中心的距离 ≤ 阈值 ✓
    #     （接插件/电阻/电容的间距都比它大 ⇒ 自动落在外面 ✓，不靠白名单 ✗）
    by_title = {}
    for q in pads:
        by_title.setdefault(q["title"], []).append(q)
    for lst in by_title.values():
        for q in lst:
            best = None
            for z in lst:
                if z is q:
                    continue
                d = ((z["c"][0] - q["c"][0]) ** 2 + (z["c"][1] - q["c"][1]) ** 2) ** 0.5 \
                    * 25.4 / 90.0
                best = d if best is None else min(best, d)
            q["fine"] = bool(best is not None and best <= VIA_INPAD_PITCH_MM)
    text, name = PW.read(path)
    traces, vias = [], []
    for _ind, b in PW.blocks(text):
        mr = re.search(r'moduleIdRef="([^"]+)"', b)
        mid = mr.group(1) if mr else ""
        if mid.startswith("Via"):
            m = re.search(r'<pcbView layer="([\w]+)">\s*<geometry ([^>]*)/>', b)
            if m:
                a = dict(re.findall(r'([\w]+)="([^"]*)"', m.group(2)))
                # ★★ 过孔尺寸 = 件属性 `hole size` ✓，口径 **`<孔直径>,<环宽>`** ✓
                #   （2026-10-01 用 **Fritzing 自己的导出**定死 ✓：它给每个过孔画两个同心环
                #    `fill=none r=0.637795 stroke-width=0.425197` ✓ ⇒ 中心线 0.225 mm、
                #    环宽 0.15 mm ⇒ **内径 0.30 / 外径 0.60 mm** ✓，正对 `0.3mm,0.15mm` ✓。
                #    ✗ 别按"环直径"读 ✗ —— 那是内径 + 半环宽，会算错一半 ✓）
                sz = re.search(r'name="hole size"\s+value="([^"]+)"', b)
                mmv = [float(x) for x in re.findall(r"([\d.]+)\s*mm", sz.group(1))] if sz else []
                ttl = re.search(r"<title>([^<]*)</title>", b)
                # ★★ 过孔的 `<geometry>` 是 **svg 画布原点** ✗ —— 真铜心要加 `VIA_DRAW_OFF_MM` ✓
                #   （2026-10-01 定案 ✓，见 `part_box.draw_off_units` 的出处 ✓）
                #   ✗ 旧版直接把 geometry 当铜心 ⇒ 所有过孔差 0.8644 mm ✗ ⇒ “压别的焊盘”测不出来 ✗
                off = PB.draw_off_units("via")
                geo = (float(a.get("x", 0)), float(a.get("y", 0)))
                vias.append(dict(layer=m.group(1),
                                 p=(geo[0] + off, geo[1] + off),      # 真铜心 ✓
                                 geo=geo,                            # 原始 geometry ✓（写文件时用 ✓）
                                 off=off,
                                 # ★ 标题（`Via1`… ✓）也带出来 ⇒ 渲染器能写**稳定 id** ✓
                                 #   （2026-10-01 用户按 "circleNNNN" 对不上账 ✓ —— 那名字是查看器给的 ✗）
                                 ttl=ttl.group(1) if ttl else None,
                                 hole_mm=mmv[0] if mmv else None,
                                 ring_mm=mmv[1] if len(mmv) > 1 else None))
            continue
        if not mid.startswith("Wire"):          # ★ 板框/面包板/零件的 block **不是走线** ✗
            continue
        t = PW.parse_trace(b)
        if t is None:
            continue
        e = PW.abs_ends(t["geo"])
        traces.append(dict(layer=t["layer"][:-5] if t["layer"].endswith("trace") else t["layer"],
                           a=e[0], b=e[1],
                           # ★ 线宽跟着走 ✓（`<wireExtras mils>` ✓）⇒ 渲染器照实物画 ✓
                           #   ✗ 旧版没有它 ⇒ 预览把每根线画成死值 ✗（v47 实宽 0.3048 mm ✓）。
                           mils=t.get("mils")))
    return dict(pads=pads, traces=traces, vias=vias, board=PW.board_rect(text),
                bodies=bodies, text=text, name=name, warns=warns, parts=parts)


def pad_layers(q):
    """这个焊盘**物理上**在哪几层 ✓（THT ⇒ 两层 ✓）"""
    return ("copper0", "copper1") if q["thr"] else (q["layer"],)


# ── 五查 ───────────────────────────────────────────────────────────────────
def check(model, expect=None):
    pads, traces, vias = model["pads"], model["traces"], model["vias"]
    probs, notes = [], []
    uf = UF()

    def end(i, k):
        return ("end", i, k)

    def endpt(t, k):
        return t["a"] if k == 0 else t["b"]

    # ① 悬空端点 ＋ ⑤ 建边（端点↔焊盘 ✓、端点↔别条线 ✓、★端点↔过孔 ✓）
    for i, t in enumerate(traces):
        # ★★ 2026-10-01 补 ✗：**一根线的两个端点必须先并起来** ✓
        #   ✗ 原来从来没有这条边 ✗ ⇒ 如果一根线是"中间过路"的（一端接上游 ✓、另一端接下游 ✓），
        #     它的两端在图上**各属一块铜** ✗ ⇒ ⑤ 会把整张网报成"没连通" ✗✗
        #     （实测 v47：9 张网**全部**误报 ✗，而几何上铜是连着的 ✓）。
        #   ★ 病根：**线身不是节点** ✗ ⇒ 过路就断 ✓；补这一条即可（线两端的铜本来就一体 ✓）。
        uf.union(end(i, 0), end(i, 1))
        for k in (0, 1):
            e = endpt(t, k)
            hit = False
            for q in pads:
                if t["layer"] in pad_layers(q) and in_rect(e, q["box"]):
                    uf.union(end(i, k), ("pad", q["title"], q["cid"]))
                    hit = True
            for j, u in enumerate(traces):
                if j == i or u["layer"] != t["layer"]:
                    continue
                if on_seg(e, u["a"], u["b"]):
                    uf.union(end(i, k), end(j, 0))
                    hit = True
            # ★★ 2026-09-30 补 ✗：端点落在**过孔**上也算接上了 ✓ ——
            #   ✗ 旧版只查"焊盘 + 同层线" ✗ ⇒ **换层的两根线各报一个悬空端点** ✗
            #     （两层当然不同层 ✗）⇒ 实测把 15 个过孔报成 **30 条悬空** ✗
            #     —— 而用户早就说过：「有时候需要添加过孔，来跨层连接」✓。
            #   ★ 过孔**两层都连通** ✓ ⇒ 不挑端点所在层 ✓。
            for vi, v in enumerate(vias):
                if (abs(v["p"][0] - e[0]) <= TOL and abs(v["p"][1] - e[1]) <= TOL):
                    uf.union(end(i, k), ("via", vi))
                    hit = True
            if not hit:
                probs.append("① 悬空端点：走线 #%d（%s 层，(%.2f,%.2f)→(%.2f,%.2f) mm）的 %s 端"
                             "既不在焊盘上、也不挨着别的线 ✗"
                             % (i, t["layer"], t["a"][0] * PW.SK, t["a"][1] * PW.SK,
                                t["b"][0] * PW.SK, t["b"][1] * PW.SK, ("起" if k == 0 else "终")))

    # ④ 同层交叉 / 重叠 ⇒ 短接 ✗（并进连通图 ✓ 让它也在 ⑤ 现形 ✓）
    for i in range(len(traces)):
        for j in range(i + 1, len(traces)):
            ti, tj = traces[i], traces[j]
            if ti["layer"] != tj["layer"]:
                continue
            if not seg_seg(ti["a"], ti["b"], tj["a"], tj["b"]):
                continue
            share = any(abs(endpt(ti, k)[0] - endpt(tj, m)[0]) <= TOL
                        and abs(endpt(ti, k)[1] - endpt(tj, m)[1]) <= TOL
                        for k in (0, 1) for m in (0, 1))
            uf.union(end(i, 0), end(j, 0))
            if not share:
                kind = "重叠" if abs(_cr(ti["a"], ti["b"], tj["a"])) < 1e-6 else "交叉"
                probs.append("④ 同层%s（= 短接）：走线 #%d 与 #%d 都在 %s 层 ✗"
                             % (kind, i, j, ti["layer"]))

    # ③ 过孔挨铜 ＋ 贯通两层 ✓
    for i, v in enumerate(vias):
        touch = []
        for j, t in enumerate(traces):
            if on_seg(v["p"], t["a"], t["b"]):
                uf.union(("via", i), end(j, 0))
                touch.append(t["layer"])
        for q in pads:
            if in_rect(v["p"], q["box"]):
                uf.union(("via", i), ("pad", q["title"], q["cid"]))
                touch.append("pad")
        if not touch:
            probs.append("③ 孤立过孔：过孔 #%d 在 (%.2f,%.2f) mm 没挨到任何铜 ✗"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK))
        else:
            notes.append("过孔 #%d @(%.2f,%.2f) mm 挨到 %s ✓"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK, "/".join(sorted(set(touch)))))

    # ⑥ ★★ 过孔**铜盘**压焊盘 ✓（2026-10-01 补 ✗，见文件头 ⑥ ✓）
    #   ✗ ③ 只问"孔心在不在盘框里" ✗ ⇒ 孔心在盘外、**环压在盘上**的情形它看不见 ✗✗
    #   ★ 判据（2026-10-01 晚定 ✗，与生成器的闸门**各自实现** ✓）：
    #     · 压到**两张不同网**的盘 ⇒ **确定短路** ✗✗ ⇒ FAIL ✓
    #     · 压到**空脚**（网表里没有的脚 ✓）⇒ FAIL ✗（会把空脚拖进这张网 ✗，PC0 那次教训 ✓）
    #     · 压到**同一张网**的一个/几个盘 ⇒ **via-in-pad** ✓ 合法 ✓ ⇒ 只**提示** ✓
    #       （万一它其实属于别的网 ⇒ ⑤ 的连通性会把两张网粘在一起 ⇒ 报"粘上了别的脚" ✓
    #         —— 所以这条放宽**不会**漏掉真短路 ✓）
    net_of = {}
    if expect:
        for net, lst in expect.items():
            for s in lst:
                if isinstance(s, str) and "." in s:
                    net_of[s] = net
    for i, v in enumerate(vias):
        hd, rg = v.get("hole_mm"), v.get("ring_mm")
        if hd is None or rg is None:
            notes.append("过孔 #%d 没写 `hole size` ⇒ ⑥ 铜盘压盘检查**跳过** ✗（别静默 ✗）" % i)
            continue
        r_edge = ((hd + rg) / 2.0 + rg / 2.0) / PW.SK        # mm → 内部单位 ✓
        hit = []
        for q in pads:
            b = q["box"]
            dx = max(b[0] - v["p"][0], 0.0, v["p"][0] - b[2])
            dy = max(b[1] - v["p"][1], 0.0, v["p"][1] - b[3])
            d = (dx * dx + dy * dy) ** 0.5
            if d < r_edge:
                key = "%s.%s" % (q["title"], q["cid"])
                hit.append((key, net_of.get(key), (r_edge - d) * PW.SK,
                            bool(q.get("epad") or q.get("fine"))))
        nets = {n for _k, n, _o, _e in hit}
        if not hit:
            continue
        # ★★ EPAD 例外 ✓（2026-10-01 用户定 ✓，见 `EPAD_EXEMPT` 的注释 ✓）：
        #   压到的**全部**是同网的焊盘、且它们**都是 EPAD** ⇒ via-in-pad ✓ 合法 ✓（EPAD 接地）
        #   ⇒ 报**提示** ✓ 不判违规 ✓；其余（异网 / 空脚 / 同网但非 EPAD）照旧 ✗。
        if None not in nets and len(nets) == 1 and all(h[3] for h in hit):
            notes.append("过孔 #%d 压在**同网**的 %s 上 ⇒ via-in-pad ✓ 合法 ✓"
                         "（EPAD 接地 / 细间距片子的扇出就是这么接的 ✓）"
                         % (i, ", ".join("%s 叠 %.3f mm" % (k, o) for k, _n, o, _e in hit)))
            continue
        if None in nets:
            probs.append("⑥ 过孔铜盘压盘：过孔 #%d @(%.2f,%.2f) mm 压到**空脚**的盘 %s ✗"
                         "（会把空脚拖进某张网 ✗）"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK,
                            ", ".join(k for k, n, _o, _e in hit if n is None)))
        elif len(nets) > 1:
            probs.append("⑥ 过孔铜盘压盘：过孔 #%d @(%.2f,%.2f) mm 同时压到**两张不同网**的盘 "
                         "%s ⇒ **短路** ✗✗"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK,
                            ", ".join("%s（网 %s，叠 %.3f mm）" % (k, n, o)
                                      for k, n, o, _e in hit)))
        else:
            # ★ 同网、但**不是 EPAD** ⇒ 仍然违规 ✗（用户点名的 `Via10`@`J1` 就是这种 ✓）
            probs.append("⑥ 过孔铜盘压盘：过孔 #%d @(%.2f,%.2f) mm 压在**同网**的盘 %s 上 ✗"
                         "（规则：只有 **EPAD** 上允许同网 via-in-pad ✓，接插件/电阻/电容的盘不行 ✗）"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK,
                            ", ".join("%s 叠 %.3f mm" % (k, o) for k, _n, o, _e in hit)))

    # ⑦ ★★ 过孔**安全距离** ✓（2026-10-01 用户定 ✗）：
    #   · 与**任何焊盘**（含同网 ✓）的净距 ≥ `VIA_SAFE_MM` ✓
    #   · 与**元件占位框**（本体墨迹框 ✓ `bodies` ✓）的净距 ≥ `VIA_SAFE_MM` ✓
    #     —— 即"通孔不能在元件内" ✓（在框内 ⇒ 净距 < 0 ⇒ 必定 FAIL ✓）
    #   量法：**矩形到点**的欧氏距离 ✓（在框内 = 0 ✓），再减铜盘半径 ✓ vs `VIA_SAFE_MM` ✓。
    for i, v in enumerate(vias):
        hd, rg = v.get("hole_mm"), v.get("ring_mm")
        if hd is None or rg is None:
            probs.append("⑦ 过孔 #%d 没写 `hole size` ⇒ 安全距离查不了 ✗（别静默跳过 ✗）" % i)
            continue
        r_mm = (hd + rg) / 2.0 + rg / 2.0                      # 铜盘半径 ✓（mm ✓）
        px, py = v["p"][0] * PW.SK, v["p"][1] * PW.SK
        worst = []
        for q in pads:                                         # ① 焊盘
            b = [t * PW.SK for t in q["box"]]
            # ★★ EPAD / 细间距例外 ✓（2026-10-01 修 ✗）：判据 = **这两件事同时成立** ✓
            #     ① 该盘是 EPAD 或**细间距**盘 ✓（`fine` ✓）；
            #     ② 过孔铜盘**确实压在这块盘上** ✓（= ⑥ 判过的那种 ✓）。
            #   ⇒ 这正是“**同网** via-in-pad”✓（⑥ 要求压到的盘**全是同一张网** ✓ 才会放行 ✓）
            #     ⇒ 这里**整块跳过** ✓，由 ⑥ 负责 ✓（不重复判 ✗）。
            #   ✗ 旧写法要求“孔心**落在**盘框内”才跳 ✗ ⇒ 中心在框外 0.09 mm 的**合法**细间距孔
            #     （实测 `#4` 在 `D3.connector4` ✓）被报成“离焊盘 −0.210 mm” ✗ = **假报** ✗。
            dx0 = max(b[0] - px, 0.0, px - b[2])
            dy0 = max(b[1] - py, 0.0, py - b[3])
            if (q.get("epad") or q.get("fine")) and \
                    (dx0 * dx0 + dy0 * dy0) ** 0.5 < r_mm:
                continue
            dx = max(b[0] - px, 0.0, px - b[2])
            dy = max(b[1] - py, 0.0, py - b[3])
            d = (dx * dx + dy * dy) ** 0.5 - r_mm
            if d < VIA_SAFE_MM:
                worst.append(("%s焊盘 %s.%s" % ("EPAD " if q.get("epad") else "",
                                                q["title"], q["cid"]), d))
        for q in model.get("bodies") or ():                    # ② 元件**画出来的铜** ✓
            for lay, b0, sid in q.get("shapes") or ():
                if lay not in ("copper0", "copper1"):
                    continue        # ✗ 丝印只是印油 ✓（孔上盖丝印是印刷问题 ✓，不是"打在元件上"✗）
                if "pad" in str(sid or "") or "pin" in str(sid or ""):
                    # ★★ 焊盘形状**跳掉** ✗（2026-10-01 修口径 ✗）：焊盘由 ⑥ / ⑦-焊盘 管 ✓，
                    #   这里再算一遍 ⇒ EPAD 上的合法 via-in-pad 会被重复报成违规 ✗
                    #   （实测：`过孔 #11 离 元件 U1 的 copper0 铜图形 −0.300 mm` ✗ 就是它 ✓）。
                    continue
                b = [t * PW.SK for t in b0]
                dx = max(b[0] - px, 0.0, px - b[2])
                dy = max(b[1] - py, 0.0, py - b[3])
                d = (dx * dx + dy * dy) ** 0.5 - r_mm
                if d < VIA_SAFE_MM:
                    worst.append(("元件 %s 的 `%s` 铜图形%s"
                                  % (q["title"], lay, "**上**" if d < -r_mm else ""), d))
        if worst:
            worst.sort(key=lambda z: z[1])
            k, d = worst[0]
            probs.append("⑦ 过孔 #%d @(%.2f,%.2f) mm 离 %s 只有 %+.3f mm ✗（需要 ≥ %.2f mm ✓；"
                         "铜盘 Ø%.2f mm ✓）"
                         % (i, px, py, k, d, VIA_SAFE_MM, 2 * r_mm))

    # ⑧ ★★ **同一层**的元件要留**安全间隔** ✓（2026-10-01 用户定 ✓：
    #   「v49 里，C1 是不是在同一面跟 U1 位置重叠了？这也不应该的，也需要一个规则禁止」✓
    #   「规则里还要元件之间保持安全间隔距离」✓）
    #   ★ 判据 = **逐图元 + 逐层**求净距 ✗（不是外框 ✗、也不是只看件的"面" ✗）：
    #     · 外框会把 NFC 线圈的中间空地当实体 ✗ ⇒ 实测假报 `L1×LED2` ✓
    #       （LED2 本来就坐在线圈中间的空地 ✓，天线绕着电路是标准做法 ✓）；
    #     · 只看"面"也不够 ✗ —— 线圈**两面都有铜** ✓（`copper0` 是背面那一圈 ✓）
    #       ⇒ 装在背面的件**不能压到线圈的背面铜** ✗，这只能按层判 ✓。
    #   ★ 层归并：`copper0`/`copper1` = 板的两层 ✓；`silkscreen`/`outline` = 该件所在那一面 ✓。
    #   ★ 相交 ⇒ 净距为负 ⇒ 必定违规 ✓；间隔必须 ≥ `PART_GAP_MM` ✓。
    def _laykey(lay, side):
        return lay if lay in ("copper0", "copper1") else "silk:" + str(side)

    bs = model.get("bodies") or []
    for a in range(len(bs)):
        for b in range(a + 1, len(bs)):
            A, B = bs[a], bs[b]
            worst, wk = None, None
            for la, ra, _ia in A.get("shapes") or ():
                for lb, rb, _ib in B.get("shapes") or ():
                    if _laykey(la, A.get("side")) != _laykey(lb, B.get("side")):
                        continue                               # 不同层 ⇒ 互不相干 ✓
                    ox = min(ra[2], rb[2]) - max(ra[0], rb[0])
                    oy = min(ra[3], rb[3]) - max(ra[1], rb[1])
                    if ox >= 0 and oy >= 0:                    # 相交 ⇒ 净距 = −重叠量 ✓
                        gap = -min(ox, oy) * PW.SK
                    else:
                        dx = max(ra[0] - rb[2], 0.0, rb[0] - ra[2])
                        dy = max(ra[1] - rb[3], 0.0, rb[1] - ra[3])
                        gap = (dx * dx + dy * dy) ** 0.5 * PW.SK if (dx or dy) else 0.0
                    if worst is None or gap < worst:
                        worst, wk = gap, (la, lb)
            if worst is not None and worst < PART_GAP_MM - 1e-9:
                probs.append("⑧ 元件间隔不足：**%s**（%s）与 **%s**（%s）在同一层只有 %+.3f mm ✗"
                             "（需要 ≥ %.2f mm ✓；最近处 `%s` × `%s`）"
                             % (A["title"], ("背面" if A.get("side") == "bottom" else "正面"),
                                B["title"], ("背面" if B.get("side") == "bottom" else "正面"),
                                worst, PART_GAP_MM, wk[0], wk[1]))

    # ② 板外 ✓
    r = model["board"]
    if r is None:
        notes.append("板框读不出 ⇒ **跳过②板外检查** ✗（请给带 `<board>` 与 PCB1 的 sketch ✓）")
    else:
        for i, t in enumerate(traces):
            for k in (0, 1):
                e = endpt(t, k)
                if not in_rect(e, r, 0.0):
                    probs.append("② 板外：走线 #%d 的 %s 端 (%.2f,%.2f) mm 板框是 (%.2f,%.2f)-(%.2f,%.2f) ✗"
                                 % (i, ("起" if k == 0 else "终"), e[0] * PW.SK, e[1] * PW.SK,
                                    r[0] * PW.SK, r[1] * PW.SK, r[2] * PW.SK, r[3] * PW.SK))
        for i, v in enumerate(vias):
            if not in_rect(v["p"], r, 0.0):
                probs.append("② 板外：过孔 #%d (%.2f,%.2f) mm ✗"
                             % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK))

    # ⑤ 连通性 == 网表 ✓
    groups = {}
    for q in pads:
        groups.setdefault(uf.find(("pad", q["title"], q["cid"])), set()).add((q["title"], q["cid"]))
    if expect:
        have = {(q["title"], q["cid"]) for q in pads}
        dup = len(pads) - len(have)
        in_nets = set()
        for net in sorted(expect):
            want = set()
            for m in expect[net]:
                if not isinstance(m, str) or "." not in m:
                    # ★ 2026-10-01 修 ✗：原来直接 `% m` ⇒ `m` 是**元组**时被当成参数列表**自己崩掉** ✗
                    #   （报错信息又把检查器弄崩 ⇒ 什么都看不到 ✗）。这里包一层元组 ✓。
                    probs.append("⑤ 期望表里的 `%s` 不是 `位号.connectorN` 格式 ✗" % (m,))
                    continue
                ref, cid = m.rsplit(".", 1)
                if (ref, cid) not in have:
                    probs.append("⑤ 网表里的脚 `%s` 在板上的焊盘里找不到 ✗（网 `%s`）" % (m, net))
                    continue
                want.add((ref, cid))
            in_nets |= want
            if not want:
                continue
            roots = {uf.find(("pad",) + k) for k in want}
            if len(roots) > 1:
                probs.append("⑤ 网 `%s` **没连通**：%d 个脚散在 %d 块铜里 ✗"
                             % (net, len(want), len(roots)))
            else:
                got = groups.get(roots.pop(), set())
                extra = got - want
                if extra:
                    probs.append("⑤ 网 `%s` **粘上了别的脚**（短接 ✗）：%s"
                                 % (net, ", ".join(sorted("%s.%s" % k for k in extra))[:90]))
        free = sorted(k for s in groups.values() for k in s if k not in in_nets)
        if free:
            notes.append("没有出现在任何网里的焊盘 %d 个：%s"
                         % (len(free), ", ".join("%s.%s" % k for k in free[:8])))
        if dup:
            notes.append("⚠️ 有 %d 个**同名位号**的焊盘多出来 ⇒ 网表按位号对会串 ✗（查位号 ✓）" % dup)
    return probs, notes, groups


def main(argv):
    nets, rest = projdata.strip_argv(argv)
    if not rest:
        print(__doc__)
        return 2
    path = rest[0]
    expect = None
    if nets:
        expect = projdata.load(nets, need=("EXPECT",)).EXPECT
        print("（网表：%s ✓）" % nets)
    else:
        print("（没给 `--nets` ⇒ **只跑 ①–④ · ⑥ 结构检查** ✓、跳过 ⑤ 网表比对 ✓）")
    model = collect(path)
    print("== %s（包内 %s）==" % (os.path.basename(path), model["name"]))
    print("   焊盘 %d 个 ✓（%d 个件）｜走线 %d 条 ✓｜过孔 %d 个 ✓｜板框 %s"
          % (len(model["pads"]), len({(q["title"]) for q in model["pads"]}),
             len(model["traces"]), len(model["vias"]),
             ("(%.2f,%.2f)-(%.2f,%.2f) mm" % tuple(v * PW.SK for v in model["board"]))
             if model["board"] else "读不出 ✗"))
    probs, notes, _g = check(model, expect)
    for n in notes[:12]:
        print("%s· %s" % (IND, n))
    if model["warns"]:
        for w in model["warns"][:4]:
            print("%s⚠️ %s" % (IND, w))
    if probs:
        print("%s✗ 问题 %d 条：" % (IND, len(probs)))
        for p in probs[:20]:
            print("%s  - %s" % (IND, p))
        if len(probs) > 20:
            print("%s  …（共 %d 条，只列前 20 ✓）" % (IND, len(probs)))
    cnt = {}
    for p in probs:
        k = p[:1]
        cnt[k] = cnt.get(k, 0) + 1
    names = {"①": "悬空端点", "②": "板外", "③": "孤立过孔", "④": "同层短接", "⑤": "网表",
             "⑥": "过孔压盘", "⑦": "过孔安全距离", "⑧": "同面元件相交"}
    if cnt:
        print("%s分类：%s" % (IND, "｜".join("%s%s %d" % (k, names.get(k, "?"), cnt[k])
                                     for k in sorted(cnt))))
    print("判定：%s" % ("✓ 全过" if not probs else "✗ 有问题（见上）"))
    return 1 if probs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
