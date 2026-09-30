# -*- coding: utf-8 -*-
r"""PCB 读回校验器（通用 ✓）2026-09-30 立

把 sketch 的 **pcbView** 读成**几何** ⇒ 查五件事 ✓
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
def collect(path):
    """把一份 sketch 的 PCB 读成几何模型 ✓"""
    parts, board = PP.read_fzz(path)
    pads, warns = [], []
    for p in parts:
        mid = p.get("moduleId") or ""
        # ★ 板框自己 / 面包板件 **不是 PCB 上的元件** ✗（`pcb_pads` 的 main 也是这么分的 ✓）：
        #   面包板件在 pcbView 里挂着 830 个孔脚 ✗ ⇒ 不跳掉就报 830 条假“缺焊盘” ✗
        if mid == PP.BOARD_MID or mid.startswith("Breadboard") or mid.startswith("Via"):
            continue
        if p.get("fzp") is None:
            warns.append("%s: %s" % (p.get("title"), p.get("why")))
            continue
        got, _ex, bad, _nt = PP.part_pads(p)
        warns += ["%s: %s" % (p["title"], b) for b in (bad or [])][:6]
        if not got:
            continue
        for cid, q in got.items():
            if q["hole_mm"] and q["layer"] != "both":
                warns.append("%s.%s 带孔（Ø%.2f）却只画在 `%s` 一层 ⇒ 按**贯通两层**算 ✓（口径待核 ⚠️）"
                             % (p["title"], cid, q["hole_mm"], q["layer"]))
            pads.append(dict(title=p["title"], cid=cid, nm=q["nm"], c=q["abs"], box=q["absbox"],
                             layer=q["layer"], thr=bool(q["hole_mm"])))
    text, name = PW.read(path)
    traces, vias = [], []
    for _ind, b in PW.blocks(text):
        mr = re.search(r'moduleIdRef="([^"]+)"', b)
        mid = mr.group(1) if mr else ""
        if mid.startswith("Via"):
            m = re.search(r'<pcbView layer="([\w]+)">\s*<geometry ([^>]*)/>', b)
            if m:
                a = dict(re.findall(r'([\w]+)="([^"]*)"', m.group(2)))
                vias.append(dict(layer=m.group(1),
                                 p=(float(a.get("x", 0)), float(a.get("y", 0)))))
            continue
        if not mid.startswith("Wire"):          # ★ 板框/面包板/零件的 block **不是走线** ✗
            continue
        t = PW.parse_trace(b)
        if t is None:
            continue
        e = PW.abs_ends(t["geo"])
        traces.append(dict(layer=t["layer"][:-5] if t["layer"].endswith("trace") else t["layer"],
                           a=e[0], b=e[1]))
    return dict(pads=pads, traces=traces, vias=vias, board=PW.board_rect(text),
                text=text, name=name, warns=warns)


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

    # ① 悬空端点 ＋ ⑤ 建边（端点↔焊盘 ✓、端点↔别条线 ✓）
    for i, t in enumerate(traces):
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
                if "." not in m:
                    probs.append("⑤ 期望表里的 `%s` 不是 `位号.connectorN` 格式 ✗" % m)
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
        print("（没给 `--nets` ⇒ **只跑 ①–④ 结构检查** ✓、跳过 ⑤ 网表比对 ✓）")
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
    names = {"①": "悬空端点", "②": "板外", "③": "孤立过孔", "④": "同层短接", "⑤": "网表"}
    if cnt:
        print("%s分类：%s" % (IND, "｜".join("%s%s %d" % (k, names.get(k, "?"), cnt[k])
                                     for k in sorted(cnt))))
    print("判定：%s" % ("✓ 全过" if not probs else "✗ 有问题（见上）"))
    return 1 if probs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
