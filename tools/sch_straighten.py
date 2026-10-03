# -*- coding: utf-8 -*-
r"""★★ 原理图**后处理**：把"本该横平竖直"的线拉直 ✓（2026-10-03 用户提议 ✓）

══ 为什么要有它（实测病例 ✓）═════════════════════════════════════════════

用户指着 `u270b_routed.fzz` 的 `C1` 那一段说「**线不直**」✗。实测：
那条竖直干线由 4 段拼成 ✓，其中 2 段各斜 **0.6721 单位 = 0.19 mm** ✗ ——
`R1` 的脚 / 横向线右端 / 地线 都在 **x = 161.3279** ✓，只有 `C1` 那一列在 **x = 162.0** ✗。
0.19 mm 整图看不出、**一放大就露** ✗ —— 典型"手工画得出来、却很难自己发现"的毛病 ✓。

判据既然能**量**（脚在哪 ✓ 端点在哪 ✓，都是既有唯一实现 ✓：`sch_box.pins_of` / `A_of` ✓），
就该**机器守** ✓：本工具把这类"差一点点"按固定规则吸齐 ✓，并**逐条报出改了什么** ✓（不静默 ✗）。

══ 规则 ════════════════════════════════════════════════════════════════

  R1 端点吸脚 ✓：线端**声明**接了某只脚（`<connects>` ✓）且相距 ≤ `TOL` ⇒ 吸到脚心 ✓。
     ★ 只吸**声明过的**那只脚 ✗ —— 靠近**别的网**的脚不吸 ✓（那是布线问题，留给人 ✓，
       见 `render_sch` 的 (B) 判据 ✓）；否则会把"看着接上其实没接"变成"真接上" ✗✗。
  R4 端点归并 ✓：**同网**内相距 ≤ `TOL` 的线端 ⇒ 统一到一点 ✓（清掉浮点噪声 ✓）。
  R2 近轴归正 ✓：一轴差 ≤ `TOL`、另一轴 ≥ `KI`×`TOL` ⇒ 把小的那轴归零 ✓
     （"这根线本来该横/竖" ✓）。挪**份量小**的那端（份量 = 该点**几根线相遇** ✓）。
  R3 零件归列 ✓（R2 办不到的：两端都钉在脚上 ⇒ **是零件摆偏了** ✗）：
     按"哪端相遇的线多"定谁让谁 ✓ ⇒ 平移**该零件**（+ 它的位号 ✓ + 挂在它脚上的线端 ✓）。

  ★ 安全阀（命中任一 ⇒ **不动、只报** ✓）：
    · 对端是**脚位未知**的零件（核心库网标签 / 接地符号 / via ✗）⇒ 不动 ✓（吸过去没法核对 ✗）；
    · R3 要平移的零件，其**挂线的脚**在目标轴上不一致（`U1` 那类多脚件 ✗）⇒ 不动 ✓；
    · 挂在该零件脚上的线端是**结点** ⇒ 不动 ✓（会撕开结点 ✗）；
    · 两端**份量相同** ⇒ 不动 ✓（谁偏了只有人知道 ✓，老老实实报出来 ✓）。
  ★ 噪声地板 `NOISE`（0.002 单位 = 0.6 µm ✓）：小于它的差**不算差** ✓ ⇒ 已经直的文件
    再跑一遍**一条都不报** ✓（幂等 ✓，也不会来回蹭 ✗）。

══ 用法 ════════════════════════════════════════════════════════════════

    py -3.13 sch_straighten.py <sketch.fz|sketch.fzz>                 # ★ 只检查（默认 ✓）
    py -3.13 sch_straighten.py <sketch.fzz> --apply                   # 原地改 + `.bak-straighten` ✓
    py -3.13 sch_straighten.py <sketch.fzz> --out <new.fzz>           # 写到别处 ✓（原文件不动 ✓）
    py -3.13 sch_straighten.py <sketch.fzz> --tol-mm 0.25 --view schematicView

★ 收尾自检（都打印 ✓）：V1 线端在不在它声明的脚上 ✓；V3 还剩几处"该直没直" ✓；
  V4 声明表条数（变了就**直接不写文件** ✗）。
★ **不许自证** ✗：本工具只"改几何 + 报账" ✓ —— 落地的图要用 `render_sch.py` 渲出来**给人看** ✓，
  数字再用独立脚本（如 `_work/sch_xy.py`）核 ✓。
"""
import collections
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

import sch_box as SB

TOL_MM_DEF = 0.25                 # 多大的偏差算"本该对齐" ✓（病例 0.19mm ✓）
KI = 10.0                         # "该是横/竖"：另一轴至少是这一轴的 KI 倍 ✓
NOISE = 0.002                     # 0.002 单位 = 0.57 µm ✓ ⇒ 小于它不算差 ✓（幂等 ✓）
EPS = 1e-9


def fmt(v):
    return ("%d" % round(v)) if abs(v - round(v)) < 1e-9 else ("%.10g" % v)


def keep_or_fmt(orig, v):
    """值没变就**原样保留原字符串** ✓ —— 把 diff 压到最小 ✓（只改真变了的那几个属性 ✓；
    ✗ 否则每跑一次都会把 45 根线重排一遍写法 ✗，实测"0 处改动"却也"改了 47 个标签" ✗）"""
    try:
        if orig is not None and abs(float(orig) - v) <= 1e-9:
            return orig
    except (TypeError, ValueError):
        pass
    return fmt(v)


def parse_args(argv):
    args, opts, i = [], {}, 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            if "=" in a:
                k, v = a[2:].split("=", 1)
                opts[k] = v
                i += 1
            else:
                opts[a[2:]] = argv[i + 1] if i + 1 < len(argv) else ""      # ★ 空格式 ✓
                i += 2
        else:
            args.append(a)
            i += 1
    return args, opts


args, opts = parse_args(sys.argv[1:])
if not args:
    raise SystemExit("用法见文件头：py -3.13 sch_straighten.py <sketch.fz|.fzz> [--apply] [--out x]")
SRC, VIEW = args[0], opts.get("view", "schematicView")
TOL = float(opts.get("tol-mm", TOL_MM_DEF)) * SB.SK_U_PER_MM
BIT = 128 if VIEW == "schematicView" else (64 if VIEW == "breadboardView" else 4)


def load(path):
    """★ 看**魔数**判是不是 zip ✓（别只看扩展名 ✗ —— 备份常叫 `.prestraight` ✓ / `.bak` ✓）"""
    head = open(path, "rb").read(4)
    if head[:2] == b"PK":
        z = zipfile.ZipFile(path)
        name = [n for n in z.namelist() if n.endswith(".fz")][0]
        return z.read(name).decode("utf-8"), z, name
    return open(path, encoding="utf-8").read(), None, None


def save(path, text, pack, name):
    """★ 绝不"边读边写同一个 zip" ✗（本仓踩过 `BadZipFile` ✓）⇒ 先写临时文件 ✓"""
    tmp = path + ".tmp"
    if pack is None:
        open(tmp, "w", encoding="utf-8").write(text)
        os.replace(tmp, path)
        return
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in pack.namelist():
            zo.writestr(n, text.encode("utf-8") if n == name else pack.read(n))
    pack.close()
    os.replace(tmp, path)


def attrs(tagtext):
    return collections.OrderedDict(re.findall(r'([\w:-]+)="([^"]*)"', tagtext))


def fnum(d, k, dflt=0.0):
    try:
        return float(d[k])
    except (KeyError, TypeError, ValueError):
        return dflt


def dist(p, q):
    return max(abs(p[0] - q[0]), abs(p[1] - q[1]))


# ────────────────────── 解析：实例 / 视图 / 实例自己的 geometry ──────────────────────
text, pack, fzname = load(SRC)
print("== %s ▶ %s（%d 字节 ✓）" % (SRC, fzname or "（纯 .fz ✓）", len(text)))

INSTS, pos = [], 0
while True:
    i = text.find("<title>", pos)
    if i < 0:
        break
    j = text.find("</title>", i)
    s = text.rindex("<instance", 0, i)
    e = text.index("</instance>", j) + len("</instance>")
    INSTS.append(dict(ttl=text[i + 7:j], s=s, e=e, blk=text[s:e]))
    pos = e

PARTS, PINS, UNKNOWN, WIRES = {}, {}, set(), []
for it in INSTS:
    blk = it["blk"]
    mi = (re.search(r'<instance[^>]*modelIndex="([^"]*)"', blk) or [None, "?"])[1]
    ot = re.search(r"<%s\b[^>]*>" % VIEW, blk)
    if not ot:
        continue
    seg_a = it["s"] + ot.end()
    rest = text[seg_a:it["e"]]
    cl = re.search(r"</%s>" % VIEW, rest)
    seg = text[seg_a:seg_a + (cl.start() if cl else len(rest))]

    # ★ 实例自己的 `<geometry>`：视图子块里**第一个** ✓（`connectors/*/geometry` 是相对偏移 ✗）
    #   带子节点（`<transform>` ✓）⇒ 要连内容一起解析 ✓，否则旋转的件会算错 ✗
    gm = re.search(r"(?s)<geometry\b([^>]*?)(?:/>|>(.*?)</geometry>)", seg)
    if not gm:
        continue
    gtag = ("<geometry%s/>" % gm.group(1)) if gm.group(2) is None \
        else ("<geometry%s>%s</geometry>" % (gm.group(1), gm.group(2)))
    g_el = ET.fromstring(gtag)
    ga = attrs(gm.group(1))
    gend = seg_a + gm.end()
    # ★ 只改**开标签** ✓（子节点/闭合标签原样留着 ✓）
    g_open_end = seg_a + gm.start() + len("<geometry%s>" % gm.group(1)) \
        if gm.group(2) is not None else gend
    tspan = None
    tm = re.search(r"<titleGeometry\b([^>]*?)(/?)>", seg)
    if tm:
        # ★ 第 4 格 = 「自己是自闭合的吗」✓（**布尔** ✓ —— ✗ 以前存的是一段内容/斜杠字符串 ✗，
        #   写回时真假反了 ⇒ 写出畸形 XML ✗✗，见下面 `SC` 的教训 ✓）
        tspan = (seg_a + tm.start(), seg_a + tm.end(), tm.group(1), tm.group(2) == "/")

    if re.search(r'moduleIdRef="Wire', blk):
        fl = ga.get("wireFlags")
        if fl is not None and not (int(fl) & BIT):
            continue                                          # 本视图不算铜 ⇒ 不动 ✓
        con = {}
        for cm in re.finditer(r'(?s)<connector\b([^>]*)>(.*?)</connector>', seg):
            cid = (re.search(r'connectorId="([^"]*)"', cm.group(1)) or [None, "?"])[1]
            con[cid] = [(a.get("modelIndex"), a.get("connectorId"))
                        for a in (attrs(x.group(1))
                                  for x in re.finditer(r"<connect\b([^>]*)/>", cm.group(2)))]
        x, y = fnum(ga, "x"), fnum(ga, "y")
        WIRES.append(dict(ttl=it["ttl"], mi=mi, ga=ga, con=con,
                          span=(seg_a + gm.start(), g_open_end, gm.group(1), gm.group(2) is None),
                          A=(x + fnum(ga, "x1"), y + fnum(ga, "y1")),
                          B=(x + fnum(ga, "x2"), y + fnum(ga, "y2"))))
        continue

    # ★ 面包板本体跳过 ✓ —— ✗ 原来写成 `"breadboardbreadboard" in blk` ✗ ⇒ **每个零件**都中招 ✗
    #   （它们的 `<connect … layer="breadboardbreadboard"/>` 里就有这串 ✗）⇒ 零件全被跳过 ✗
    #   （实测：`零件 0 ✓` ✓）。改按**模块名**判 ✓；万一漏网，`not pins` 那道闸门也拦得住 ✓。
    if re.search(r'moduleIdRef="[^"]*[Bb]readboard', blk):
        continue
    pm = re.search(r'path="([^"]*)"', blk)
    if not pm:
        UNKNOWN.add(mi)
        continue
    fzp = pm.group(1)
    # ★ `image=` 在 **fzp** 里 ✓ 不在 sketch 里 ✗（sketch 的 `<schematicView>` 没有 `<layers>` ✓）
    image = None
    try:
        lay = ET.parse(fzp).getroot().find(".//%s/layers" % VIEW)
        image = lay.get("image") if lay is not None else None
    except Exception:
        image = None
    svg = SB.part_svg_text(fzp, None, image)[0] if image else None
    pins, kind, _bad = SB.pins_of(svg) if svg else ({}, "none", [])
    A = SB.A_of(svg, g_el) if svg else None
    if not pins or A is None:
        UNKNOWN.add(mi)                                       # 脚位未知 ⇒ 一律不动 ✓
        continue
    box = SB.box_of(svg, g_el, A)[0]
    PARTS[mi] = dict(ttl=it["ttl"], ga=ga, span=(seg_a + gm.start(), g_open_end,
                                                 gm.group(1), gm.group(2) is None),
                     tspan=tspan, pins={}, box=box)
    for cid, p in pins.items():
        q = SB.to_sketch(g_el, A, p)
        PINS[(mi, cid)] = q
        PARTS[mi]["pins"][cid] = q

print("   零件 %d ✓（脚位已知 %d 只 ✓）｜**脚位未知** %d 件 ⇒ 一律不动 ✓｜导线 %d 根 ✓"
      % (len(PARTS), len(PINS), len(UNKNOWN), len(WIRES)))

# 线端 ↔ 端点：实测 **connector0 ⇒ 第一个端点（A）** ✓；逐根**验** ✓ 验不过的那根不动 ✓
END = {}
for i, w in enumerate(WIRES):
    for cid, which in (("connector0", 0), ("connector1", 1)):
        if cid in w["con"]:
            END[(w["mi"], cid)] = (i, which)

SUSPECT = set()
for w in WIRES:
    for cid, which in (("connector0", 0), ("connector1", 1)):
        for (m, c) in w["con"].get(cid, []):
            if (m, c) in PINS:
                q = PINS[(m, c)]
                na, nb = dist(w["A"], q), dist(w["B"], q)
                if (which == 0 and nb < na - EPS) or (which == 1 and na < nb - EPS):
                    SUSPECT.add(w["ttl"])
if SUSPECT:
    print("   ⚠ %d 根线的「connector0 ⇒ 第一个端点」对不上 ⇒ 这几根**不动** ✓：%s"
          % (len(SUSPECT), sorted(SUSPECT)))

HANG = collections.defaultdict(list)
for k in END:
    wi, _ = END[k]
    for (m, c) in WIRES[wi]["con"].get(k[1], []):
        if (m, c) in PINS and (m, c) != k:
            HANG[(m, c)].append(k)


def endpt(k):
    wi, which = END[k]
    return WIRES[wi]["A"] if which == 0 else WIRES[wi]["B"]


def setend(k, p):
    wi, which = END[k]
    if which == 0:
        WIRES[wi]["A"] = tuple(p)
    else:
        WIRES[wi]["B"] = tuple(p)


par = {}


def find(k):
    par.setdefault(k, k)
    while par[k] != k:
        par[k] = par[par[k]]
        k = par[k]
    return k


for w in WIRES:
    for cid, mates in w["con"].items():
        if (w["mi"], cid) not in END:
            continue
        for (m, c) in mates:
            if (m, c) in END:
                ru, rv = find((w["mi"], cid)), find((m, c))
                if ru != rv:
                    par[ru] = rv
            else:
                # ★★ 同一个**脚**（零件脚 / 脚位未知的脚 ✓）上的线端 = **同一个网** ✓
                #   ✗ 2026-10-03 漏了这一步 ⇒ `Wire90012772.B`（R1 脚）与 `Wire90012778.A`（同一只脚 ✗）
                #     分到两个网 ✗ ⇒ 两端"份量"都算 1 ✗ ⇒ R3 判成"两端相同 ⇒ 不动" ✗✗
                #     （实测：改前备份一条都不改 ✗ —— 正确结果应当是把 C1 挪过去 ✓）。
                ru, rv = find((w["mi"], cid)), find(("PIN", m, c))
                if ru != rv:
                    par[ru] = rv

by_root = collections.defaultdict(list)
for k in END:
    by_root[find(k)].append(k)
CLUST = []
for keys in by_root.values():
    left = list(keys)
    while left:
        grp = [left.pop(0)]
        again = True
        while again:
            again = False
            for k in list(left):
                if any(dist(endpt(k), endpt(g)) <= TOL for g in grp):
                    grp.append(k)
                    left.remove(k)
                    again = True
        CLUST.append(grp)
cl_of = {k: gi for gi, grp in enumerate(CLUST) for k in grp}


def cluster(k):
    return CLUST[cl_of[k]]


def deg(k):
    return len(cluster(k))


def declared_pin(k):
    w = WIRES[END[k][0]]
    return [(m, c) for (m, c) in w["con"].get(k[1], []) if (m, c) in PINS]


def unknown_partner(k):
    w = WIRES[END[k][0]]
    for (m, c) in w["con"].get(k[1], []):
        if (m, c) not in PINS and m in UNKNOWN:
            return m
    return None


# ────────────────────────────── 规则 ──────────────────────────────
LOG, SKIP = [], []


def v1_off_pin():
    """线端不在它声明的脚上（> NOISE ✓）的**个数** ✓ —— ★ 先用**改动前**的值打个底 ✓
    （改完**不许变多** ✗ —— 否则就是我又把线从脚上扯下来了 ✗，见下面 R2 的教训 ✓）"""
    n = 0
    for k in END:
        for (m, c) in declared_pin(k):
            if dist(endpt(k), PINS[(m, c)]) > NOISE:
                n += 1
    return n


V1_BEFORE = v1_off_pin()

# R1 端点吸脚 + R4 端点归并（每个簇 → 一个目标点 ✓）
for grp in CLUST:
    pts = [endpt(k) for k in grp]
    if len(grp) == 1:
        k = grp[0]
        if unknown_partner(k):
            continue
        dp = declared_pin(k)
        if len(dp) == 1 and NOISE < dist(pts[0], PINS[dp[0]]) <= TOL:
            setend(k, PINS[dp[0]])
            LOG.append("R1 %s.%s 吸到 %s 的脚 ✓（%.4f 单位 = %.3f mm ✓）"
                       % (WIRES[END[k][0]]["ttl"], k[1], PARTS[dp[0][0]]["ttl"],
                          dist(pts[0], PINS[dp[0]]), dist(pts[0], PINS[dp[0]]) * 25.4 / 90.0))
        continue
    bad = next((b for k in grp for b in [unknown_partner(k)] if b), None)
    if bad:
        SKIP.append("一簇 %d 个端点：对端是**脚位未知**的零件（%s）⇒ 不动 ✓" % (len(grp), bad))
        continue
    anchors = [PINS[(m, c)] for k in grp for (m, c) in declared_pin(k)
               if dist(endpt(k), PINS[(m, c)]) <= TOL]
    # ★ 安全阀：簇里有端**声明了脚、却离脚超出 TOL** ✗ ⇒ 这簇本来就不干净 ⇒ 不动 ✓
    far = [(m, c) for k in grp for (m, c) in declared_pin(k)
           if dist(endpt(k), PINS[(m, c)]) > TOL]
    if far:
        SKIP.append("一簇 %d 个端点：有端离它声明的脚超出 %.2fmm ⇒ 不干净 ⇒ 不动 ✓"
                    % (len(grp), TOL * 25.4 / 90.0))
        continue
    if anchors:
        if any(dist(anchors[0], q) > NOISE for q in anchors[1:]):
            SKIP.append("一簇 %d 个端点：声明接的几只脚**彼此不一致** ⇒ 不动 ✓" % len(grp))
            continue
        tgt = anchors[0]
    else:
        tgt = (sorted(p[0] for p in pts)[len(pts) // 2], sorted(p[1] for p in pts)[len(pts) // 2])
    if all(dist(p, tgt) <= NOISE for p in pts):
        continue
    for k in grp:
        setend(k, tgt)
    LOG.append("R4 %d 个端点归并到 (%.4f, %.4f) ✓（原最大差 %.4f 单位 ✓）"
               % (len(grp), tgt[0], tgt[1], max(dist(p, tgt) for p in pts)))

# R2 近轴归正（重复到不动 ✓）
for _r in range(4):
    n0 = len(LOG)
    for w in WIRES:
        k0, k1 = (w["mi"], "connector0"), (w["mi"], "connector1")
        if k0 not in END or k1 not in END or w["ttl"] in SUSPECT:
            continue
        p0, p1 = endpt(k0), endpt(k1)
        axis = 0 if abs(p1[0] - p0[0]) <= abs(p1[1] - p0[1]) else 1
        small = abs(p1[axis] - p0[axis])
        big = abs(p1[1 - axis] - p0[1 - axis])
        if small <= NOISE or small > TOL or big < KI * TOL:
            continue
        d0, d1 = deg(k0), deg(k1)
        if d0 == d1:
            continue                                        # 交给 R3 / 人 ✓
        mv, keep = (k0, k1) if d0 < d1 else (k1, k0)
        # ★★ 钉在脚上的端**任何情况下都不许单独挪** ✗✗（2026-10-03 实测教训 ✓：
        #   先跑了 R2 ⇒ 把 `Wire90012756` 靠 C1 的那端从 162.0 挪到 161.3279 ✗
        #   ⇒ **线从 C1 的脚上扯下来了** ✗ ⇒ V1 从 0 变 1 ✗ ⇒ 自检当场报出来 ✓）。
        #   正确做法 = 挪**零件**（R3 ✓）⇒ 线端跟着零件走 ✓。
        if any(declared_pin(k) for k in cluster(mv)):
            continue
        if unknown_partner(mv):
            SKIP.append("%s：要挪的那端脚位未知 ⇒ 不动 ✓" % w["ttl"])
            continue
        old = endpt(mv)[axis]
        p = list(endpt(mv))
        p[axis] = endpt(keep)[axis]
        setend(mv, tuple(p))
        LOG.append("R2 %s：%s 轴归零 ✓（%.4f → %.4f ✓，%.3f mm ✓）"
                   % (w["ttl"], "xy"[axis], old, p[axis], small * 25.4 / 90.0))
    if len(LOG) == n0:
        break

# R3 零件归列（两端都钉在脚上、却还差一点点 ⇒ **零件摆偏了** ✓）
for w in WIRES:
    k0, k1 = (w["mi"], "connector0"), (w["mi"], "connector1")
    if k0 not in END or k1 not in END or w["ttl"] in SUSPECT:
        continue
    if not (declared_pin(k0) and declared_pin(k1)):
        continue
    p0, p1 = endpt(k0), endpt(k1)
    axis = 0 if abs(p1[0] - p0[0]) <= abs(p1[1] - p0[1]) else 1
    small = abs(p1[axis] - p0[axis])
    big = abs(p1[1 - axis] - p0[1 - axis])
    if small <= NOISE or small > TOL or big < KI * TOL:
        continue
    d0, d1 = deg(k0), deg(k1)
    if d0 == d1:
        SKIP.append("%s：两端份量相同（各 %d）⇒ 差 %.4f 单位 = %.3f mm 的歪 ✗ 请人看 ✓"
                    % (w["ttl"], d0, small, small * 25.4 / 90.0))
        continue
    mv, keep = (k0, k1) if d0 < d1 else (k1, k0)
    if not declared_pin(mv):
        # ✗ 例：`Wire90012778` 的远端是核心库 `RC` 网标签（磁盘上没有它的 fzp ✗）
        #   ⇒ 脚位**不可知** ⇒ 吸过去没法核对 ⇒ **不动**，但要说清楚 ✓（留给人的 0.04mm ✓）
        unk = unknown_partner(mv) or "（脚位未知 ✓）"
        SKIP.append("%s：要挪的那端是 %s ⇒ 脚位未知 ⇒ 不动 ✓（差 %.4f 单位 = %.3f mm，请人看 ✓）"
                    % (w["ttl"], unk, small, small * 25.4 / 90.0))
        continue
    part_mi = declared_pin(mv)[0][0]
    if part_mi in UNKNOWN or part_mi not in PARTS:
        continue
    P = PARTS[part_mi]
    att = sorted({cid for (m, cid) in HANG if m == part_mi and cid in P["pins"]})
    if not att:
        continue
    vals = {round(P["pins"][c][axis], 4) for c in att}
    if len(vals) > 1:
        SKIP.append("跳过 %s：它挂线的脚在 %s 轴上不一致 %s ⇒ 平移会拆坏别的脚 ✗"
                    % (P["ttl"], "xy"[axis], sorted(vals)))
        continue
    hangs = [k for c in att for k in HANG.get((part_mi, c), [])]
    if any(deg(k) > 1 for k in hangs):
        SKIP.append("跳过 %s：挂在它脚上的线端是**结点** ⇒ 平移会撕开结点 ✗" % P["ttl"])
        continue
    delta = endpt(keep)[axis] - endpt(mv)[axis]
    was = endpt(mv)[axis]
    P["ga"]["xy"[axis]] = fmt(fnum(P["ga"], "xy"[axis]) + delta)
    P["moved"] = True
    # ★★ 零件挪了 ⇒ **它的脚位也要跟着挪** ✗（✗ 2026-10-03 漏了这步 ⇒ V1 拿**旧脚位**比 ⇒
    #   明明线端跟着零件走了 ✓，自检却报"2 处线端离开脚" ✗ ⇒ 自己把自己拦住 ✗✗）
    for c in list(P["pins"]):
        q = P["pins"][c]
        P["pins"][c] = (q[0] + delta, q[1]) if axis == 0 else (q[0], q[1] + delta)
        PINS[(part_mi, c)] = P["pins"][c]
    if P["tspan"]:
        na = attrs(P["tspan"][2])
        na["xy"[axis]] = fmt(fnum(na, "xy"[axis]) + delta)
        P["tspan_new"] = na
    for k in hangs:
        p = list(endpt(k))
        p[axis] += delta
        setend(k, tuple(p))
    LOG.append("R3 零件 %s 沿 %s 轴平移 %.4f ✓（脚 %.4f → %.4f ✓，与干线 %.4f 对齐 ✓，%.3f mm ✓）"
               % (P["ttl"], "xy"[axis], delta, was, was + delta, endpt(keep)[axis],
                  abs(delta) * 25.4 / 90.0))

# ────────────────────────────── 自检 ──────────────────────────────
#   ★ `v1_off_pin()` 已经在规则段开头定义过 ✓（用它量了 `V1_BEFORE` ✓）—— 这里**不再重定义** ✗
def v3_slanted():
    out = []
    for w in WIRES:
        k0, k1 = (w["mi"], "connector0"), (w["mi"], "connector1")
        if k0 not in END or k1 not in END:
            continue
        p0, p1 = endpt(k0), endpt(k1)
        small = min(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
        big = max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
        if NOISE < small <= TOL and big >= KI * TOL:
            out.append((w["ttl"], small * 25.4 / 90.0))
    return out


print("── 改动 %d 处 ✓" % len(LOG))
for x in LOG:
    print("   · %s" % x)
for x in SKIP:
    print("   ⊘ 未动：%s" % x)
left = v3_slanted()
V1_AFTER = v1_off_pin()
print("── 自检：V1 线端不在它声明的脚上 **%d 处** ✓（改前 %d 处 ⇒ **不许变多** ✗）"
      "｜V3 还「该直没直」 **%d 处** ✓" % (V1_AFTER, V1_BEFORE, len(left)))
for t, mm in left[:10]:
    print("     ⚑ %s 还差 %.3f mm ✗（R2/R3 之外的情况 ⇒ 请人看 ✓）" % (t, mm))
if V1_AFTER > V1_BEFORE:
    raise SystemExit("✗✗ 方案会让 %d 条线端离开它声明的脚（改前 %d）⇒ **不写文件** ✗"
                     % (V1_AFTER, V1_BEFORE))
if not LOG:
    print("   ✓ 无需改动（已经横平竖直 ✓）")
    raise SystemExit(0)

# ────────────────────────── 写回（只改那几个**开标签** ✓）──────────────────────────
EDITS = []
for w in WIRES:
    new = collections.OrderedDict(w["ga"])
    new["x"], new["y"] = keep_or_fmt(w["ga"].get("x"), w["A"][0]), keep_or_fmt(w["ga"].get("y"), w["A"][1])
    if "x1" in new:
        new["x1"], new["y1"] = keep_or_fmt(w["ga"].get("x1"), 0.0), keep_or_fmt(w["ga"].get("y1"), 0.0)
        new["x2"], new["y2"] = (keep_or_fmt(w["ga"].get("x2"), w["B"][0] - w["A"][0]),
                                keep_or_fmt(w["ga"].get("y2"), w["B"][1] - w["A"][1]))
    tag = "<geometry%s%s>" % ("".join(' %s="%s"' % (a, b) for a, b in new.items()),
                              "/" if w["span"][3] else "")
    if text[w["span"][0]:w["span"][1]] != tag:
        EDITS.append((w["span"][0], w["span"][1], tag, w["ttl"]))
for mi, P in PARTS.items():
    if P.get("moved"):
        tag = "<geometry%s%s>" % ("".join(' %s="%s"' % (a, b) for a, b in P["ga"].items()),
                                  "/" if P["span"][3] else "")
        if text[P["span"][0]:P["span"][1]] != tag:
            EDITS.append((P["span"][0], P["span"][1], tag, P["ttl"] + "（本体）"))
    if P.get("tspan_new"):
        tag = "<titleGeometry%s%s>" % ("".join(' %s="%s"' % (a, b) for a, b in P["tspan_new"].items()),
                                       "/" if P["tspan"][3] else "")
        if text[P["tspan"][0]:P["tspan"][1]] != tag:
            EDITS.append((P["tspan"][0], P["tspan"][1], tag, P["ttl"] + "（位号）"))

new_text = text
for s, e, tag, why in sorted(EDITS, key=lambda t: -t[0]):
    new_text = new_text[:s] + tag + new_text[e:]
n_before = len(re.findall(r"<connect\b[^>]*/>", text))
n_after = len(re.findall(r"<connect\b[^>]*/>", new_text))
if n_before != n_after:
    raise SystemExit("✗✗ 声明表 %d → %d 条 ⇒ 不写文件 ✗（V4 守 ✓）" % (n_before, n_after))
# ★★ 机器守：改完必须**还能解析** ✓（2026-10-03 实测教训 ✗：存"是否自闭合"的那一格真假反了 ✗
#   ⇒ 写线时漏了 `/>` ✗、写零件本体时反多一个 `/>` ✗ ⇒ 文件变成**畸形 XML** ✗✗，
#   而我当时只比了"声明表条数"✓、看不出这种坏 ✗ ⇒ 现在**先解析、解析不了就不写** ✓。）
try:
    ET.fromstring(new_text)
except Exception as _ex:
    raise SystemExit("✗✗ 改出来的 XML 解析不了（%s）⇒ **不写文件** ✗" % _ex)
print("   V4 声明表 %d 条 → %d 条 ✓（**0 条被动过** ✓）｜改了 %d 个几何开标签 ✓｜XML 可解析 ✓"
      % (n_before, n_after, len(EDITS)))

if not (opts.get("apply") or opts.get("out")):
    print("（默认只检查 ✓ —— 加 `--apply` 才写 ✓）")
    raise SystemExit(0)
dst = opts.get("out") or SRC
if dst == SRC:
    bak = SRC + ".bak-straighten"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("   备份 → %s ✓" % os.path.basename(bak))
save(dst, new_text, pack, fzname)
print("   写入 %s ✓" % dst)
