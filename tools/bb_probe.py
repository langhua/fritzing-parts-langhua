# -*- coding: utf-8 -*-
r"""面包板视图的**网表核对**（= 面包板版的 `check_netlist` ✓，2026-10-16 立 ✓）

★ 为什么要有它 ✗✓（实测撞出来的 ✓）：`check_netlist.py` 文件头写明
  **"只认原理图层的连接、把面包板整个排除"** ✓ ⇒ 拿它去判面包板视图会得到
  "分量共 0 个" ✗（= 尺子不对 ✗，而不是图不对 ✓）；而库仓 `AGENTS.md` §5b 点名的
  面包板尺子 `bb_probe` **当时并不存在** ✗ ⇒ 面包板**只剩布线器自己的话** ✓
  （= §13 说的"自证"✗）⇒ 本工具就是补这个空 ✓。

★★ 口径 = **只看 Fritzing 自己声明的连接** ✓（**完全不看几何** ✗）：
  · 导通关系一律取 `<connect … layer=…>` ✓ —— 与 Fritzing 同语义 ✓（§13 ✓）、
    与 `bb_route4` 内部那套"孔↔孔几何"**不是同一份实现** ✓（⇒ 它能推翻布线器 ✓）；
  · 孔之间的互通取**板子部件自己的 `<buses>`** ✓（同一列 5 孔是同一块铜片 ✓）；
  · `layer` 的含义照 §5b E3 ✓：`breadboardbreadboard` ⇒ 目标是**板上的孔** ✓、
    `breadboard` ⇒ 目标是**零件上的脚** ✓、`breadboardWire` ⇒ 目标是**导线** ✓。
  ⇒ 于是**导线中段压过焊盘不算连** ✓（Fritzing 也只认端点 ✓，`items/wire.cpp:1133` ✓）。

判据（退出码 0/1 ✓，与 `check_netlist.py` 同习惯 ✓）：
  ① **每张网各自连通成一片** ✓（`EXPECT` 里的脚 ⇒ 一个分量 ✓）；
  ② **不许短接** ✓（两张网的脚落在同一分量 = 同一块铜片 ✗）；
  ③ **不许有"图上没有这只脚"** ✗（`EXPECT` 写了、草图里找不到 ⇒ 表与图对不上 ✓）；
  ④ 单脚分量（没连到任何东西的脚）**只报告** ✓（有些件本来就孤立 ✓，判据是①②③ ✓）。

用法::

    py -3.13 bb_probe.py <sketch.fzz> [--nets=<项目数据.py>]
    py -3.13 bb_probe.py <sketch.fzz> --show        # 额外把每张网的**实际连通情况**打出来 ✓
"""
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

import projdata as PD

CORE_FZP = "breadboard2.fzp"


def tag(e):
    return e.tag.split("}")[-1]


def child(e, n):
    for c in e:
        if tag(c) == n:
            return c
    return None


def read_fz(path):
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".fz")]
    if not name:
        raise SystemExit("✗ %s 里没有 .fz ✗" % path)
    return ET.fromstring(z.read(name[0]))


def resolve_fzp(p):
    """部件的 `.fzp` 路径 ✓（`:/resources/parts/…` 这种**核心件写法**要映射到安装目录 ✓）"""
    if not p:
        return None
    raw = p.replace("/", os.sep)
    if os.path.isfile(raw):
        return raw
    if raw.startswith(":"):
        # `:/resources/parts/core/x.fzp` ⇒ `<fritzing-parts>/core/x.fzp` ✓
        m = re.match(r":\\?resources\\?parts\\?(?:core|contrib|obsolete)?\\?(.+)$", raw)
        if m:
            tail = m.group(1)
            for base in (os.environ.get("FRITZING_PARTS"), ):
                if base:
                    cand = os.path.join(base, tail)
                    if os.path.isfile(cand):
                        return cand
    return raw                      # 交回调用方去报"找不到"✓（不静默 ✗）


class UF(object):
    def __init__(self):
        self.p = {}

    def add(self, a):
        self.p.setdefault(a, a)

    def find(self, a):
        self.add(a)
        r = a
        while self.p[r] != r:
            r = self.p[r]
        while self.p[a] != r:
            self.p[a], a = r, self.p[a]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def main(argv):
    nets_file, argv = PD.strip_argv(argv)
    show = "--show" in argv
    argv = [a for a in argv if not a.startswith("--")]
    if not argv:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    mod = PD.load(nets_file, need=("EXPECT",))
    EXPECT = mod.EXPECT
    all_expected = {p for v in EXPECT.values() for p in v}      # `EXPECT` 里点过名的脚 ✓
    fzz = argv[0]
    print("== 面包板网表核对（`bb_probe` ✓ 只看 `<connect>` 与 `<buses>` ✓ 不看几何 ✗）==")
    print("   %s" % fzz)
    root = read_fz(fzz)
    host = child(root, "instances") or root

    # ── ① 板子部件：孔集 与 bus ─────────────────────────────────────────────
    board = None
    for e in root.iter("instance"):
        mid = (e.get("moduleIdRef") or "")
        if mid.startswith("Wire") or mid.endswith("BreadboardLogoTextModuleID"):
            continue
        if "breadboard" in mid.lower() and child(child(e, "views"), "breadboardView") is not None:
            board = e
            break
    if board is None:
        raise SystemExit("✗ 这张图里没有面包板实例 ✗（没画面包板视图就没得核 ✓）")
    bpath = resolve_fzp(board.get("path"))
    if not os.path.isfile(bpath):
        raise SystemExit("✗ 找不到板子部件的 fzp：%s ✗" % bpath)
    broot = ET.parse(bpath).getroot()
    holes = {c.get("id") for c in broot.iter("connector")
             if re.fullmatch(r"pin\w+", c.get("id") or "")}
    if len(holes) < 800:
        raise SystemExit("✗ 板子 fzp 里只读到 %d 颗孔（应 800+）✗ —— 是不是拿错部件了？" % len(holes))
    bus_list = []
    for b in broot.iter("bus"):
        mem = set()
        for d in b.iter():
            if d is b:
                continue
            for k, v in d.attrib.items():
                if k in ("id", "connectorId", "connector", "member") and v in holes:
                    mem.add(v)
        if mem:
            bus_list.append(mem)
    print("   板孔 %d 颗 ✓｜bus %d 条 ✓（126×5 + 4×50 = 830 ✓）" % (len(holes), len(bus_list)))

    # ── ② 实例索引 ─────────────────────────────────────────────────────────
    by_mi, by_title = {}, {}
    for e in root.iter("instance"):
        by_mi[e.get("modelIndex")] = e
        t = (e.findtext("title") or "").strip()
        if t and not (e.get("moduleIdRef") or "").startswith("Wire"):
            by_title[t] = e
    bmi = board.get("modelIndex")
    wire_mis = {e.get("modelIndex") for e in root.iter("instance")
                if (e.get("moduleIdRef") or "").startswith("Wire")
                and child(child(e, "views"), "breadboardView") is not None}
    # ★ 本视图里**真的在的件** ✓（有面包板视图且不是导线/图例 ✓）：
    #   `EXPECT` 里点到**不在本视图**的件（如 `BT1`：脚距 6.00 mm ✗ 插不进孔 ✓）
    #   ⇒ 那是**不适用** ✓，✗ 不是"表图不符"✗（2026-10-16 实测把它误报过一次 ✗）
    in_view = {(e.findtext("title") or "").strip() for e in root.iter("instance")
               if child(child(e, "views"), "breadboardView") is not None
               and not (e.get("moduleIdRef") or "").startswith("Wire")
               and not (e.get("moduleIdRef") or "").endswith("BreadboardLogoTextModuleID")}
    in_view.discard("")

    def node_of(mi, cid):
        """目标 → 统一节点名 ✓（孔 / 导线 / 零件脚 三类 ✓）"""
        if mi is None:
            return None
        if mi == bmi:
            return "H:" + cid
        if mi in wire_mis:
            return "W:" + mi                      # 导线整根 = 一个导体 ✓（两端短接 ✓）
        e = by_mi.get(mi)
        if e is None:
            return None
        t = (e.findtext("title") or "").strip()
        return "P:%s.%s" % (t, cid)

    # ── ③ 并查集：一律按"谁声明接了谁" ✓ ────────────────────────────────────
    uf = UF()
    for h in holes:
        uf.add("H:" + h)
    for mem in bus_list:
        first = sorted(mem)[0]
        for h in sorted(mem)[1:]:
            uf.union("H:" + first, "H:" + h)
    n_edge, n_bad_target, dangling = 0, [], []
    all_pins = set()                     # ★ 这张图上**真的画到的脚** ✓（用来区分"没接"与"没这只脚" ✓）
    for e in root.iter("instance"):
        mi = e.get("modelIndex")
        mid = (e.get("moduleIdRef") or "")
        vb = child(child(e, "views"), "breadboardView")
        if vb is None:
            continue
        is_board = (mi == bmi)
        is_wire = mid.startswith("Wire")
        for cm in vb.iter("connector"):
            cid = cm.get("connectorId")
            if is_board:
                me = "H:" + cid
                if cid not in holes:              # 板子连接器名不是孔名 ⇒ 不管（板子自己还有别的脚 ✓）
                    continue
            elif is_wire:
                me = "W:" + mi
            else:
                t = (e.findtext("title") or "").strip()
                me = "P:%s.%s" % (t, cid)
                all_pins.add(me)
                if me not in {"P:" + p for p in all_expected}:
                    dangling.append(me)           # 图上有的脚、EXPECT 里没写 ⇒ 只报告 ✓（表可能不全 ✓）
            for c in cm.iter("connect"):
                tg = node_of(c.get("modelIndex"), c.get("connectorId"))
                if tg is None:
                    n_bad_target.append("%s → %s.%s" % (me, c.get("modelIndex"), c.get("connectorId")))
                    continue
                uf.union(me, tg)
                n_edge += 1
    print("   声明（`<connect>`）%d 条 ✓｜指向不存在目标的 %d 条 %s" %
          (n_edge, len(n_bad_target), "✓" if not n_bad_target else "✗ " + "; ".join(n_bad_target[:5])))

    # ── ④ 按 EXPECT 判 ─────────────────────────────────────────────────────
    #   ★★ 掉过的坑（2026-10-16 ✗）：`EXPECT` 里的脚名是 `U1.connector20` ✓、
    #     而并查集里的节点名带类型前缀 `P:U1.connector20` ✓ ⇒ 不换算就变成
    #     "图上没有这只脚" （全误报 ✗）＋ 每张网的分量都是**空组** ⇒ `len<=1`
    #     恒成立 ⇒ **空转也报通过** ✗✗（是尺子错了，不是图对了 ✓）
    #     ⇒ 统一走 `pnode()` ✓，并在下面把"量到了几只脚"打出来当**非空转的凭据** ✓。
    def pnode(p):
        return p if p.startswith("P:") else "P:" + p

    node2net, short = {}, []
    for net, pins in EXPECT.items():
        for p in pins:
            q = pnode(p)
            if q in node2net and node2net[q] != net:
                short.append("%s 同时出现在 %s / %s" % (p, node2net[q], net))
            node2net[q] = net
    rep_of = {}
    expect_missing, split, na_list, single = [], [], [], []
    ok = 0
    n_seen = 0
    for net, pins in EXPECT.items():
        pins = sorted(pins)
        away = [p for p in pins if p.split(".")[0] not in in_view]      # 该件不在本视图 ✓
        if away:
            na_list.append("%s：%s 不在本视图（不适用 ✓）" % (net, ", ".join(away)))
        on = [p for p in pins if p not in away]
        have = [p for p in on if pnode(p) in uf.p]
        miss = [p for p in on if pnode(p) not in uf.p]
        n_seen += len(have)
        #   ★★ 两种"没连上"要分开说 ✓（2026-10-16 ✓）：
        #     · 脚在图上、但没声明接通 ⇒ **图没接** ✗（如拆掉 U1 的 EPAD ✓ —— 实测就报这个 ✓）；
        #     · 连脚都没有 ⇒ **表与图对不上** ✗（表写错 / 拿错稿 ✓）。
        #     ⚠ 原来一律说成"图上没有这只脚" ✗ ⇒ 拿错尺子的人会去查部件，白跑 ✓。
        for p in miss:
            if pnode(p) in all_pins:
                expect_missing.append("%s：%s **图上有这只脚、但没声明接通**（= 没接任何东西 ✗）" % (net, p))
            else:
                expect_missing.append("%s：图上没有 %s（表与图对不上 ✗）" % (net, p))
        groups = {}
        for p in have:
            groups.setdefault(uf.find(pnode(p)), []).append(p)
        rep_of[net] = groups
        if len(groups) == 1 and len(have) >= 2:
            ok += 1
        elif len(groups) == 1 and len(have) == 1:
            single.append("%s（图上只 1 只脚 ⇒ **看不出来** ✓ 不判 ✓）" % net)
        elif len(groups) > 1:
            split.append((net, sorted(groups.values(), key=lambda g: -len(g))))
    # 短接：两张网的脚落在同一个分量 ✓
    rep_net = {}
    for net, groups in rep_of.items():
        for r in groups:
            if r in rep_net and rep_net[r] != net:
                short.append("分量里有 %s 与 %s 的脚（同一块铜片 ✓ = 短接 ✗）" % (rep_net[r], net))
            rep_net[r] = net
    #   ★★ 又掉一个坑（2026-10-16 ✗）：原来把"**它是分量的根**"当成"单脚分量"✗ ——
    #     根只是**代表** ✓ ⇒ 每张网的代表都被列成"孤立" ✗（14 只全误报 ✗）
    #     ⇒ 改成按**组大小**判 ✓（`sizes[find(p)] == 1` ✓）。
    sizes = {}
    for p in uf.p:
        sizes[uf.find(p)] = sizes.get(uf.find(p), 0) + 1
    lone = sorted(p for p in uf.p
                  if p.startswith("P:") and sizes[uf.find(p)] == 1 and p in node2net)
    print("   网 %d 张 ✓｜图上出现的脚 %d 只 ✓｜`EXPECT` 里点名的脚 **量到 %d / %d** 只 ✓"
          % (len(EXPECT), len([p for p in uf.p if p.startswith("P:")]),
             n_seen, sum(len(v) for v in EXPECT.values())))
    if n_seen == 0:
        print("   ✗✗ 一只脚都没量到 ⇒ 这不是「图对了」、是**尺子坏了** ✗（先看脚名对不对 ✓）")
    for net, pins in sorted(EXPECT.items()):
        groups = rep_of.get(net, {})
        if len(groups) == 1 and sum(len(g) for g in groups.values()) >= 2:
            print("   %-9s ✓  应有 %2d 只（图上 %d 只 ✓）"
                  % (net, len(pins), sum(len(g) for g in groups.values())))
        elif len(groups) == 1:
            print("   %-9s ·  应有 %2d 只、但图上只 1 只 ⇒ **看不出来** ✓ 不判 ✓" % (net, len(pins)))
        else:
            print("   %-9s ✗  应有 %2d 只 ⇒ **断成 %d 片** ✗：%s"
                  % (net, len(pins), len(groups),
                     " | ".join("(%d) %s" % (len(g), ", ".join(sorted(g)[:4])) for g in groups)))
        if show and len(groups) == 1:
            print("        ↳ %s" % ", ".join(sorted(list(groups.values())[0])))
    if expect_missing:
        print("   ✗ 表与图对不上（或图没接）：")
        for s in expect_missing:
            print("      %s" % s)
    if short:
        print("   ✗ 短接：")
        for s in sorted(set(short)):
            print("      %s" % s)
    if na_list:
        print("   · 不适用（该件不在本视图 ✓）：")
        for s in na_list:
            print("      %s" % s)
    if single:
        print("   · 只有 1 只脚在图上 ⇒ 连通性看不出（✓ 不判）：%s" % "、".join(single))
    if lone:
        print("   · 单脚分量（没连到任何东西 ✓ 仅报告）：%s" % ", ".join(lone))
    if dangling:
        print("   · 图上还有 `EXPECT` 没写的脚 %d 只（仅报告 ✓）：%s"
              % (len(dangling), ", ".join(dangling[:8])))
    bad = len(split) + len(expect_missing) + len(set(short)) + len(n_bad_target)
    print("判定: %s（%d/%d 张网连通成一片 ✓）"
          % ("✓ 与项目数据一致" if not bad else "✗ %d 处对不上（断 %d、表图不符 %d、短接 %d、悬空目标 %d）"
             % (bad, len(split), len(expect_missing), len(set(short)), len(n_bad_target)),
             ok, len(EXPECT)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
