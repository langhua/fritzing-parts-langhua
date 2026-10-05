# -*- coding: utf-8 -*-
r"""**PCB 走线量尺 = 独立实现** ✓（2026-10-05 ✓；对应原理图那把 `sch_metrics.py` ✓）

用法：
```
py -3.13 tools/pcb_metrics.py <a.fzz> [<b.fzz> ...] [--nets=pixel_nets.py] [--worst N]
```
量什么 ✓（都是**从文件几何**算的 ✓，与布线器的成本函数无关 ✗ —— 本仓规矩「不许自证」✓）：
· 走线**条数 / 总长（mm，按层分）** ✓、**过孔数** ✓；
· **角度分布**：每条线自己相对水平是 `0/45/90/其它` ✓（PCB 常见审美：只走 0/45/90 ✓）；
· **拐角分布**：同一层上**共用端点**的两段之间的转角 `0/45/90/其它` ✓；
· ★ **点名单**（前 N 条 ✓）：非 0/45/90 的**线段** ✓、其它角度的**拐角** ✓
  —— 这份名单才是"能改什么"的抓手 ✓（数字只能看出多不多 ✓）。
★ 间距/短接**不在这里** ✗：那是 `pcb_check.py` 的事（它已有那份实现 ✓，别抄第二份 ✗）。
"""
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import pcb_check as PC                              # noqa: E402
import pcb_wire as PW                               # noqa: E402

SK = PW.SK


def load_nets(path):
    spec = importlib.util.spec_from_file_location("nets_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    net = {}
    for n, lst in getattr(mod, "EXPECT", {}).items():
        for key in lst:
            net[key] = n
    return net


def ang_of(a, b):
    """线段方向角（度 ✓，-90 到 90 ✓）"""
    d = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
    return d


def class_ang(d, tol=1.0):
    for v in (0.0, 45.0, 90.0, 135.0, 180.0):
        if abs(d - v) <= tol or abs(d - v + 180.0) <= tol:
            return int(v) % 180
    return None


def metrics(path, nets=None):
    m = PC.collect(path)
    tr, vi = m["traces"], m["vias"]
    out = {"path": path, "n_seg": len(tr), "n_via": len(vi)}
    tot = 0.0
    per_layer, per_net = {}, {}
    ang, ang_other = {}, []
    ends = {}
    seg_info = []
    for i, t in enumerate(tr):
        a, b = t["a"], t["b"]
        ln = math.hypot(b[0] - a[0], b[1] - a[1]) * SK
        tot += ln
        per_layer[t["layer"]] = per_layer.get(t["layer"], 0.0) + ln
        nm = (nets or {}).get(t.get("net") or "", None)
        if nm is None and nets:
            # 用端点去找网名（`pcb_check` 的 traces 里可能没有 net 字段 ✓）
            nm = None
        key = t.get("net") or "?"
        per_net.setdefault(key, [0.0, 0, 0])
        per_net[key][0] += ln
        per_net[key][1] += 1
        d = ang_of(a, b)
        c = class_ang(d)
        if c is None:
            ang_other.append((ln, i, d, a, b, t["layer"]))
        else:
            ang[c] = ang.get(c, 0) + 1
        for k, e in ((0, a), (1, b)):
            ends.setdefault((t["layer"], round(e[0], 2), round(e[1], 2)), []).append((i, k))
        seg_info.append((ln, i, t))
    out.update(total_mm=tot, per_layer=per_layer, ang=ang, ang_other=ang_other,
               ends=ends, seg_info=seg_info, per_net=per_net)
    # 拐角：同一层同一个点上恰好两段 ⇒ 算转角 ✓（180 - 夹角 ✓；0 = 直着 ✓）
    turns, turns_other = {}, []
    for (_lay, _x, _y), hit in ends.items():
        if len(hit) != 2:
            continue
        (i1, k1), (i2, k2) = hit
        if i1 == i2:
            continue
        p = (_x, _y)
        d1 = ang_of(p, tr[i1]["b"] if k1 == 0 else tr[i1]["a"])
        d2 = ang_of(p, tr[i2]["b"] if k2 == 0 else tr[i2]["a"])
        t = abs((d1 - d2) % 180.0)
        t = min(t, 180.0 - t)
        c = class_ang(t)
        if c is None:
            turns_other.append((t, i1, i2))
        else:
            turns[c] = turns.get(c, 0) + 1
    out.update(turns=turns, turns_other=turns_other)
    return out


def show(m, worst=8, nets=None):
    print("== %s ==" % os.path.basename(m["path"]))
    print("   走线 %d 段 ✓｜总长 %.1f mm ✓｜过孔 %d 个 ✓"
          % (m["n_seg"], m["total_mm"], m["n_via"]))
    print("   按层：%s" % "、".join("%s %.1fmm" % (k, v) for k, v in sorted(m["per_layer"].items())))
    print("   线段角度：%s｜**非 0/45/90 的 %d 段** %s"
          % ("、".join("%s°×%d" % (k, v) for k, v in sorted(m["ang"].items())) or "（无）",
             len(m["ang_other"]), "✗" if m["ang_other"] else "✓"))
    for ln, i, d, a, b, lay in sorted(m["ang_other"], reverse=True)[:worst]:
        print("        · #%-3d %.2f° 长 %6.2f mm  %s  (%.1f,%.1f)→(%.1f,%.1f)"
              % (i, d, ln, lay, a[0] * SK, a[1] * SK, b[0] * SK, b[1] * SK))
    print("   拐角：%s｜**其它角度的拐角 %d 处** %s"
          % ("、".join("%s°×%d" % (k, v) for k, v in sorted(m["turns"].items())) or "（无）",
             len(m["turns_other"]), "✗" if m["turns_other"] else "✓"))
    for t, i1, i2 in sorted(m["turns_other"], reverse=True)[:worst]:
        print("        · 转角 %.2f°（段 #%d ↔ #%d）" % (t, i1, i2))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    nets = None
    worst = 8
    for a in sys.argv[1:]:
        if a.startswith("--nets="):
            nets = load_nets(a.split("=", 1)[1])
        if a.startswith("--worst="):
            worst = int(a.split("=", 1)[1])
    if not args:
        raise SystemExit(__doc__)
    for p in args:
        show(metrics(p, nets), worst, nets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
