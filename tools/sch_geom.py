# -*- coding: utf-8 -*-
r"""原理图几何的**唯一实现**（布线器与渲染器共用 ✓）

★ 为什么要独立成模块 ✗（2026-09-27 ✓）：交叉/搭线这两个判据**必须只有一份** ✓ ——
  面包板那边的教训就是"两份实现 ⇒ 数字对不上、找不到原因" ✗；
  而且这一次更严重 ✗：渲染器的旧判据**只认正交** ✗ ⇒ 一放开斜线，
  量出来的"交叉数"就是**假的** ✗✗（斜线交叉一个都不算 ✗）⇒ 会拿假数据下结论 ✗。

口径（与面包板一致 ✓）：
  · `seg_cross`：**两段内部真正相交**（含斜线 ✓）⇒ 算 1 次交叉 ✓；
    ✗ 共端点（接头 ✓）、共线重叠、端点搭在别人中段（搭线 = 接头 ✓）**都不算交叉** ✗
    —— 后两类在面包板规则里是**另外两类"交集"** ✓，这里先分开管 ✓（`near_overlap` ✓）。
  · `on_seg`：点是否落在某段的**内部** ✓（两端不算 ✓）。
  · `near_overlap`：两段是否**几乎压在一起** ✗（同向、间距小、且有重叠区间 ✓）
    —— 手改版里那几根 `0.08° / 0.28°` 的"平行线"就是这种 ✓（看着像一根 ✓）。
"""


import math


def _orient(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _bbox_hit(a, b, c, d, eps=0.0):
    return not (max(a[0], b[0]) < min(c[0], d[0]) - eps
                or max(c[0], d[0]) < min(a[0], b[0]) - eps
                or max(a[1], b[1]) < min(c[1], d[1]) - eps
                or max(c[1], d[1]) < min(a[1], b[1]) - eps)


def seg_cross(a, b, c, d, eps=0.05):
    """两段**内部**真正相交 ⇒ True ✓（正交、斜线都能判 ✓）

    ★ 用**叉积符号严格相反**做判据 ✓ ⇒ 相交点对**两段**都是内部的 ✓
      ⇒ 共端点 / 共线 / 端点搭中段**自动排除** ✗（那些是"接头" ✓，不是交叉 ✓）。
    ★★ 2026-09-28 ✓ **补上文档承诺、代码里却没实现的那一步** ✗（用户点名的"假交叉" ✓）：
      ✗ 只用"严格反号" ⇒ **浮点末位 / 存盘取整**就会把**接头**判成交叉 ✗✗（实测 ✓）：
        `Wire90012753` 端点 `y=157.8005` 与 `Wire90012773` 的 `y=157.8` 差
        **0.0005 单位 = 0.00013 mm** ⇒ 本函数判 **True** ⇒ 报"交叉 **15**"✗；
        而自动版里两条**都是** 157.8005（严格重合 ✓）⇒ 判 **T** ✓ 报 **14** ✓
        ⇒ **同一个形状**（同一处搭接 ✓）给出**两个数** ✗✗（手改版里另有过 `1e-13` 级噪声 ✓）。
      ✓ 判据：**只要有一端贴着对方**（落在**端点**上 ✓ 或落在**中段**上 ✓，容差 = 全仓既有的
        `eps = 0.05` ✓，**不新造数** ✗）⇒ 那是**接头（T）** ✓ ⇒ 直接 `False` ✓。
      ★ 与 `xcheck.py` 的 ③ 类「端点搭线（T，接头 ✓ **不算毛病** ✓）」**同一口径** ✓；
      ★ 也只影响"离端点 0.05 以内"的判定 ✓ ⇒ 真正的 X（四个端点都远）一条不少 ✓。
    """
    if not _bbox_hit(a, b, c, d):
        return False
    if (p2seg(c, a, b) <= eps or p2seg(d, a, b) <= eps
            or p2seg(a, c, d) <= eps or p2seg(b, c, d) <= eps):
        return False                       # ★ 有端点贴着对方 ⇒ 接头（T）✓ 不是交叉 ✗
    return (_orient(a, b, c) * _orient(a, b, d) < 0
            and _orient(c, d, a) * _orient(c, d, b) < 0)


def on_seg(p, a, b, tol=0.05):
    """点 p 是否落在段 a→b 的**内部** ✓（两端不算 ✓；斜线也能判 ✓）"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return False
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
    if not (0.02 < t < 0.98):
        return False
    return ((p[0] - (a[0] + t * dx)) ** 2 + (p[1] - (a[1] + t * dy)) ** 2) ** 0.5 < tol


def seg_hits_box(a, b, box, eps=0.0):
    """线段 `a-b` 与**轴对齐方框** `box=(x0,y0,x1,y1)` 有没有交 ✓（端点在框内也算 ✓）

    ★ 用途 ✓：**标签是一个元件** ✓（`fritzing-parts-langhua/docs/schem-drawing-rules.md`
      **B3.1.1** ✓，2026-09-29 用户定 ✓）⇒ 导线**不许穿**标签本体 ✗
      ⇒ 生成器挑标签朝向时要拿它当闸门 ✓（与批量判据**同一份实现** ✓，不给标签另写一套 ✗）。
    """
    x0, y0, x1, y1 = box
    x0, x1 = min(x0, x1) - eps, max(x0, x1) + eps
    y0, y1 = min(y0, y1) - eps, max(y0, y1) + eps
    if x0 <= a[0] <= x1 and y0 <= a[1] <= y1:
        return True
    if x0 <= b[0] <= x1 and y0 <= b[1] <= y1:
        return True
    _c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i in range(4):
        if seg_cross(a, b, _c[i], _c[(i + 1) % 4]):
            return True
    return False


def hits_box(p, q, box, need=4, inset=0.5):
    r"""段 p→q 是否**真的**穿进 box ✓（★ **擦边不算** ✗）—— ★ **全仓唯一实现** ✓

    ★ 口径**逐字搬自** `render_sch.py` 的 `_hits_box` ✓（2026-09-30 ✓ 抽成共用 ✓，
      “一个判据一份实现” ✗✓）：以前 `snap_rails` **自己偷偷写了一份** ✗
      （盒子缩 2 单位 ✗、认 ≥3 个采样点 ✗）⇒ **两把尺子** ✗ ⇒ 好候选被更严的那把误否决 ✗。
    ★ 为什么要“擦边不算” ✓（2026-09-27 ✓）：原来**有一个采样点在框里**就算 ✗
      ⇒ 导线**从元件旁边过**（离框 0.28mm ✓）也被算成“穿过” ✗（假警报 ✗）⇒
      现在要求**至少 `need` 个采样点**落在**内缩 `inset`** 的框里 ✓（≈ 进到里面 0.14mm 以上 ✓）。
    """
    x0, y0, x1, y1 = box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset
    if x0 >= x1 or y0 >= y1:
        x0, y0, x1, y1 = box
    n = max(2, int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) + 1)
    hit = 0
    for i in range(n + 1):
        t = i / n
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if x0 <= x <= x1 and y0 <= y <= y1:
            hit += 1
            if hit >= need:
                return True
    return False


def p2seg(p, a, b):
    """点 p 到线段 a→b 的**最短距离** ✓（含两端 ✓）—— ★ **全仓唯一实现** ✓
    （2026-09-28 ✓ 从 `render_sch.py` 的 `_p2seg` **逐字搬来** ✓：可读性判据 ✓、
      “假连线”判据 ✓、布线器的“线不许落在别的脚上”硬闸门 ✓ 都用它 ✓）。
    """
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return ((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2) ** 0.5
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return ((p[0] - (a[0] + t * dx)) ** 2 + (p[1] - (a[1] + t * dy)) ** 2) ** 0.5


def near_overlap(a, b, c, d, tol=0.6):
    """两段是否**几乎压在一条线上** ✗（同向 ✓、间距 ≤ tol ✓、且有重叠区间 ✓）

    ★ 为什么要它 ✓（2026-09-27 手改版实测 ✓）：手改版里有两根**近乎平行**的线
      （斜率 0.08° 与 0.28°、相隔不到 0.3 单位 ✓）—— 图上看着像一根线 ✓，
      读图的人分不清 ✓ ⇒ 算一类毛病报出来 ✓。
    """
    L1 = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
    L2 = ((d[0] - c[0]) ** 2 + (d[1] - c[1]) ** 2) ** 0.5
    # ★★ 退化段（长度 ≈ 0 的“**点接头** / **跨视图残留**”✓）**不参与**“压在一起”判定 ✓
    #   （2026-09-28 ✓ 用户手改版实测的**误报** ✗）：`pixel-schematic-v16_byHand` 里的
    #    `Wire90012908` 是一根 **0.000 单位**的点接头 ✓，它就落在 `U1.PD0` 引脚上 ✓
    #    ⇒ 按原判据会被算成“与 `Wire90012974` 几乎压在一起” ✗✗ —— 图上根本没有重叠 ✓。
    #   ★ 阈值取 **0.05 单位**（= 0.014 mm ✓）= 全仓“碰到/落在”的**同一个容差** ✓
    #     （**不新造第三个数** ✗）；真实导线没有这么短的 ✓ ⇒ 不会漏掉真重叠 ✓。
    if L1 < 0.05 or L2 < 0.05:
        return False
    # 方向夹角（用 |sin| 判平行 ✓）
    cr = ((b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])) / (L1 * L2)
    if abs(cr) > 0.06:                       # ≈ 3.5° 以内算平行 ✓
        return False
    # 间距：c、d 到直线 ab 的距离都要小 ✓
    def dist(p):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = (dx * dx + dy * dy) ** 0.5
        return abs(dx * (a[1] - p[1]) - (a[0] - p[0]) * dy) / L
    if dist(c) > tol or dist(d) > tol:
        return False
    # 重叠区间（投影到 ab 方向上 ✓）
    def t_of(p):
        dx, dy = b[0] - a[0], b[1] - a[1]
        return ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    t0, t1 = sorted((t_of(c), t_of(d)))
    return min(t1, 1.0) - max(t0, 0.0) > 0.05


def para_tol(a, b, c, d):
    r"""两段的 **|sin(夹角)|** ✓（0 = 完全平行 ✓；≈1 = 垂直 ✓）—— ★ 唯一实现 ✓

    ★ 为什么要它 ✗（2026-10-09 ✓ 第四十六轮 ✓）：`near_overlap` 里那段“|sin| ≤ 0.06 ⇒ 平行”
      与「端点搭在对方上是不是**接头**」共用同一个量 ✗ ⇒ 抽出来 ✓
      （判据只许一份 ✗；抄第二份早晚对不上 ✓ —— 面包板那天的教训 ✓）。
    """
    L1 = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
    L2 = ((d[0] - c[0]) ** 2 + (d[1] - c[1]) ** 2) ** 0.5
    if L1 < 1e-9 or L2 < 1e-9:
        return 0.0
    return abs((b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])) / (L1 * L2)


def seg_seg_dist(a, b, c, d):
    r"""两段**最短距离** ✓（含端点 ✓；真交叉 ⇒ 0 ✓）—— ★ 全仓唯一实现 ✓

    ★ 用途 ✓（2026-10-09 ✓ 第四十六轮 ✓）：「**线↔线最小净距**」参数化硬闸门（`--wire-gap` ✓）＋
      验收探针 ⑪ ✓＋ 本轮中间脚本 `_gap_measure.py` ✓ 全调它 ✓ ⇒ 一个数一把尺子 ✓。
    ★ 判据分解 ✓：真交叉（`seg_cross` ✓）⇒ 0 ✓；否则 = **四只端点各自到对方段**的距离取最小 ✓
      （两段不交时，最近点必有一只落在端点或“端点对内部” ✓ —— 平行段的垂距由端点投影给出 ✓，
        投影落在对方段外时由“另一段的端点投影”给出 ✓ ⇒ 取四者最小恒正确 ✓）。
    ★ 复用 `p2seg` ✓（点到段 ✓，全仓唯一实现 ✓）—— **不新写第二份点到段公式** ✗。
    """
    if seg_cross(a, b, c, d):
        return 0.0
    return min(p2seg(a, c, d), p2seg(b, c, d), p2seg(c, a, b), p2seg(d, a, b))


def merge_conductors(items, sin_tol=0.06, tol=0.05):
    r"""把「**同网 ＋ 共端点 ＋ 近共线**」的一串段并成**一条直线段** ✓（= 同一根**导体** ✓）

    ★ 为什么必须有它 ✗（2026-10-09 ✓ 第四十六轮 ✓）：一条「轨」在文件里是**一串** `<instance>` ✓
      （`365 (22.83,−57.60)→(180.00,−57.60)` ＋ `366 →(180.38,−57.60)` ＋ `367 →(244.58,−57.60)` ✓）。
      ✗ 逐根比“净距”时：`365` 与 `367` **首尾相接、共线**、中间只隔一根 0.378 单位的 `366` ✗
      ⇒ 量出来 **0.378 单位 = 0.107 mm** ✗ —— 可**它们本来就是同一根线** ✓
      （`366` 把那段缝**填满**了 ✓、图上就是一条连续的直线 ✓）⇒ 这是**假警报** ✗。
      ⇒ 先把同一根导体并起来再量 ✓（用户口径 ✓：「**线距**」说的是**两条线之间** ✓，
        不是同一条线**自己那几节之间** ✗）。
    ★ 判据（与 `near_overlap` / `joined` 同一个 `sin_tol` ✓ —— 不新造数 ✗）：
      两点 ①同网 ✓ ②**共端点**（≤ `tol` ✓）③**近共线**（`para_tol` ≤ `sin_tol` ✓）
      ⇒ 连一条边 ✓；每个**连通分量**就是一条直线 ✓ ⇒ 取该分量里**最远的两只端点** ✓
      （共线且连通 ⇒ 所有点在同一条直线上 ✓ ⇒ 最远那对就是整条 ✓）。
    ★ 输入/输出都是 `[(p, q, net), …]`（2 元组也收 ✓，网名补 `None` ✓）；**不碰文件** ✓、只算 ✓。
    """
    segs = [(it[0], it[1], (it[2] if len(it) > 2 else None)) for it in items]
    n = len(segs)
    if n < 2:
        return segs
    par = list(range(n))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if segs[i][2] != segs[j][2]:
                continue
            ai, bi, _ = segs[i]
            aj, bj, _ = segs[j]
            if para_tol(ai, bi, aj, bj) > sin_tol:
                continue
            if not (math.dist(ai, aj) <= tol or math.dist(ai, bj) <= tol
                    or math.dist(bi, aj) <= tol or math.dist(bi, bj) <= tol):
                continue
            ra, rb = find(i), find(j)
            if ra != rb:
                par[rb] = ra
    grp = {}
    for i in range(n):
        grp.setdefault(find(i), []).append(i)
    out = []
    for _r, idxs in sorted(grp.items()):
        net = segs[idxs[0]][2]
        pts = []
        for i in idxs:
            pts.append(segs[i][0])
            pts.append(segs[i][1])
        best = (pts[0], pts[1])
        bd = math.dist(pts[0], pts[1])
        for x in range(len(pts)):
            for y in range(x + 1, len(pts)):
                dd = math.dist(pts[x], pts[y])
                if dd > bd:
                    bd, best = dd, (pts[x], pts[y])
        if bd >= tol:
            out.append((best[0], best[1], net))
    return out


def conductor_clearance(items, gap=0.0, tol=0.05):
    r"""★ **全图「线↔线最小净距」清单** ✓ —— ★ 唯一一份 ✓（生成器闸门 ✓ / 验收探针 ⑪ ✓ /
    `_work/_gap_measure.py` ✓ 共用 ✓）

    ★ 口径（**与用户定的规则逐条对应** ✓，2026-10-09 ✓）：
      ① 先 `merge_conductors()` ✓（同一条**导体**的几节并成一条 ✓ ⇒ 不自己跟自己比 ✗）；
      ② **同网接头**（`joined` ✓：共端点 / 不平行的一端搭在对方上 ✓）**跳过** ✓（搭接/并线 ✓）；
      ③ **横穿**（`seg_cross` ✓ 真交叉 ✓）**跳过** ✗（那是「交叉」✓，另有账 ✓）；
      ④ 其余 ⇒ 量 `seg_seg_dist` ✓；`< gap` ⇒ 记一条**不足** ✗。
    返回 `(min_d, min_pair, bad_list, cross_n)` ✓：`min_d` = 最小净距（单位 ✓，没有可比对 ⇒ `None` ✓）、
      `min_pair` = 那一对（（i,j）下标 ✓，指向**并入后**的表 ✓）、`bad_list` = 低于 `gap` 的对 ✓、
      `cross_n` = 横穿对数 ✓。
    """
    segs = merge_conductors(items, tol=tol)
    m = len(segs)
    min_d, min_pair = None, None
    bad, ncross = [], 0
    for i in range(m):
        for j in range(i + 1, m):
            ai, bi, ni = segs[i]
            aj, bj, nj = segs[j]
            same = (ni == nj)
            if same and joined(ai, bi, aj, bj, tol=tol):
                continue
            if seg_cross(ai, bi, aj, bj):
                ncross += 1
                continue
            d = seg_seg_dist(ai, bi, aj, bj)
            if min_d is None or d < min_d:
                min_d, min_pair = d, (i, j)
            if d < gap:
                bad.append((d, i, j))
    return min_d, min_pair, bad, ncross, segs


def joined(a, b, c, d, tol=0.05, sin_tol=0.06):
    r"""两段**是不是在一点上接起来** ✓（= **电气接头** ✓，不是“压在一起/离太近” ✗）

    ★ 为什么要区分 ✗（2026-10-09 ✓ 第四十六轮 ✓，**用户点名** ✓）：「线距 ≥ `wire_gap`」这道闸门
      **绝不能**去罚**合法的连接** ✗ —— `--mst-merge` 的**同网搭接**（端点接端点 ✓）、
      「簇主干」合并（共端点、共线的连续段 ✓）、电源轨的 **T 形接头**（端点落在轨上 ✓）
      都是**同一导体** ✓ ⇒ 罚它们等于**把搭接功能打死** ✗✗（用户原话 ✓：「**例外** ✓ …必须放行 ✓」）。
    ★ 口径（三条 ✓，不许含糊 ✗）：
      ① **共端点**（≤ `tol` ✓）⇒ **接头** ✓ —— 覆盖搭接 / 主管合并 / 连续段 / T 形 ✓；
      ② 一端落在对方**内部**、且两段**不平行**（`|sin| > sin_tol` ✓ ≈ > 3.5° ✓）⇒ **T 形接头** ✓
         （电源轨支线那类 ✓）；
      ③ 其余 ⇒ **不是接头** ✗ —— ★ **共线重叠**（平行 ✓ 且端点落在对方内部 ✓）**故意**不算接头 ✓
         （那是 `near_overlap` 报的“**压在一起**” ✗ ＋ 本轮「线距不足」 ✗，两者都要罚 ✓）。
    """
    if (p2seg(a, c, d) <= tol or p2seg(b, c, d) <= tol
            or p2seg(c, a, b) <= tol or p2seg(d, a, b) <= tol):
        # ① 共端点 ⇒ 接头 ✓ —— ★ **但“共线且同侧”不算接头** ✗（那是**压在一起** ✗，
        #   正是 `near_overlap` 报的那类病 ✓；同网共线重叠必须 0 ✓，不许被这里放行 ✗）。
        if (math.dist(a, c) <= tol or math.dist(a, d) <= tol
                or math.dist(b, c) <= tol or math.dist(b, d) <= tol):
            if math.dist(a, c) <= tol:
                S, O1, O2 = a, b, d
            elif math.dist(a, d) <= tol:
                S, O1, O2 = a, b, c
            elif math.dist(b, c) <= tol:
                S, O1, O2 = b, a, d
            else:
                S, O1, O2 = b, a, c
            u = (O1[0] - S[0], O1[1] - S[1])
            v = (O2[0] - S[0], O2[1] - S[1])
            if para_tol(a, b, c, d) <= sin_tol and (u[0] * v[0] + u[1] * v[1]) > 0:
                return False          # 共线 ＋ 同侧 ⇒ **重叠** ✗（不是接头 ✗）
            return True               # 反向延展（连续段 ✓）/ 折角 ✓ ⇒ 接头 ✓
        return para_tol(a, b, c, d) > sin_tol               # ② 不平行 ⇒ T 形 ✓
    return False


def gap_pair_bad(a, b, c, d, gap, same_net=False):
    r"""这一对段「**线距不足**」吗 ✗ —— ★ **唯一一份判据** ✓（生成器闸门 ✓ 与验收探针 ⑪ ✓ 共用 ✓）

    ★ 三条口径 ✓（2026-10-09 ✓ 第四十六轮 ✓ **用户定** ✓：默认 1.0 mm ✓、范围 [0.254, 2.54] mm ✓）：
      · **接头放行** ✗（**同网**且 `joined()` ✓ ⇒ `False` ✓ —— 搭接/并线/T 形/接管 ✓ 都要活着 ✓）；
      · **横穿不算** ✗（真交叉 ⇒ `seg_cross` ✓ ⇒ `False` ✓ —— 那是「**交叉**」✓，另有账 ✓ ＋
        用户只要求“**平行/邻近**”那种贴太近 ✓）；
      · 其余 ⇒ **最短距离 < `gap`**（单位 = sketch ✓）⇒ **不足** ✗。
    """
    if same_net and joined(a, b, c, d):
        return False
    if seg_cross(a, b, c, d):
        return False
    return seg_seg_dist(a, b, c, d) < gap
