# -*- coding: utf-8 -*-
r"""★★ 原理图**量尺** ✓（2026-10-03 入库 ✓）—— 独立实现 ✓：**不调任何工具的内部函数** ✗

为什么要有它 ✓：
  · 布线器（项目侧 `gen_schematic_wires.py` ✓）**自己会报**"交叉/贴脚/重叠" ✓ ——
    但那是**它自己的口径** ✗。本仓规矩「**不许自证**」✗ ⇒ 结论必须能被**另一个实现**
    或**人的眼睛**复核 ✓。
  · 2026-10-03 用它当场量出：用户手画版（43 根 / 487.7 mm / 交叉 20 ✓）**优于**
    自动布线在同摆位下的结果（47 根 / 641.6 mm / 交叉 35 ✗）⇒ **方向立刻清楚** ✓。

量什么 ✓（口径写死在这 ✓，谁都能复核 ✓）：
  `wires` 导线数 ｜ `parts` 元件数 ｜ `mm` 总长（mm ✓）｜ `crossings` 交叉数 ｜
  `ortho` 正交度 ｜ `worst` 最歪（mm ✓）

★ 2026-10-04 ✓ `crossings` 的“共端点 ⇒ 跳过”改成**带容差** ✗（精确相等会把
  “接在同一个点上、但坐标差 1e-4”的两根线算成**交叉** ✗）；容差 `SHARE_TOL` = 0.05 单位
  = 0.014mm ✓（全仓那个“碰到”的量 ✓）。详见 `crossings()` ✓。
  · 只认**原理图的铜** ✓（`wireFlags & 128` ✓ —— 不懂这个就会把 PCB 走线当成原理图线 ✗；
    面包板 64 ✓、PCB 4 ✓）；
  · **正交度** = 已对齐 / 「本该横平竖直」 ✓：分母 = 另一轴 ≥ **10×** 这一轴的线 ✓
    （真的斜线不算 ✗ —— 那是设计意图 ✓）；分子 = 其中偏差 ≤ **0.25 mm** 的 ✓；
  · **交叉数** = 两条**不同网**的线段：真穿（X ✓）或一条的端点在另一条**内部**（T 搭 ✓）
    各算 1 ✓；**共端点不算** ✗（那是正常连接 ✓）；同一根线的段不算 ✗。

用法 ✓（读多个文件时会多打一张对比表 ✓）：

    py -3.13 sch_metrics.py <a.fzz> [<b.fzz> ...]

库用法 ✓：

    from sch_metrics import metrics
    metrics("x.fzz")        # -> dict(wires, parts, mm, crossings, ortho, worst, ...)
"""
import sys
import zipfile
import xml.etree.ElementTree as ET

KI = 10.0                        # 另一轴 ≥ KI× 这一轴 ⇒ 才算"本该横平竖直" ✓
TOL_MM = 0.25                    # 对齐容差 ✓
# ★ 2026-10-04 ✓ **共端点判据的容差** ✓（= 全仓那个“碰到”的量 **0.05 单位 = 0.014mm** ✓，
#   **不新造数** ✗）—— 见 `crossings()` 里的实测记录 ✓（`.fz` 存相对偏移 ⇒ 加起来留 1e-4 尾巴 ✗）。
SHARE_TOL = 0.05
S2MM = 25.4 / 90.0               # 1 sketch 单位 = 1/90 in ✓
TOL = TOL_MM * S2MM


def fz_text(path):
    """`.fzz`(zip ✓) 与 `.fz`(纯 xml ✓) 都收 —— ★ 用**魔数**认 zip ✗ 别看扩展名 ✗"""
    with open(path, "rb") as fh:
        if fh.read(2) == b"PK":
            z = zipfile.ZipFile(path)
            name = [n for n in z.namelist() if n.endswith(".fz")][0]
            return z.read(name).decode("utf-8")
    return open(path, encoding="utf-8").read()


def fnum(el, k, d=0.0):
    v = el.get(k)
    try:
        return float(v) if v is not None else d
    except ValueError:
        return d


def read(path):
    """→ (wires, parts) ✓；wires = [((ax,ay),(bx,by),title)] ✓"""
    root = ET.fromstring(fz_text(path))
    wires, parts = [], set()
    for inst in root.iter("instance"):
        mid = inst.get("moduleIdRef") or ""
        views = inst.find("views")
        sv = views.find("schematicView") if views is not None else None
        g = sv.find("geometry") if sv is not None else None
        if sv is None or g is None:
            continue
        ttl = (inst.findtext("title") or "").strip()
        if mid.startswith("Wire"):
            fl = g.get("wireFlags")
            if fl is not None and not (int(fl) & 128):
                continue                     # 本视图不算铜 ⇒ 跳过 ✓
            x, y = fnum(g, "x"), fnum(g, "y")
            wires.append(((x + fnum(g, "x1"), y + fnum(g, "y1")),
                          (x + fnum(g, "x2"), y + fnum(g, "y2")), ttl))
        else:
            parts.add(ttl)
    return wires, parts


def _cross(p, q, r, s):
    def o(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    return o(p, q, r) != o(p, q, s) and o(r, s, p) != o(r, s, q)


def _on_seg(p, a, b):
    if abs((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) > 1e-6:
        return False
    return (min(a[0], b[0]) - 1e-9 <= p[0] <= max(a[0], b[0]) + 1e-9
            and min(a[1], b[1]) - 1e-9 <= p[1] <= max(a[1], b[1]) + 1e-9)


def _pair(a, b, c, d):
    """两条线段 ⇒ 0 / 1 ✓（X 真穿 ✓ 或 T 端点搭在别人内部 ✓）"""
    if _cross(a, b, c, d):
        return 1
    for p in (a, b):
        if _on_seg(p, c, d):
            return 1
    for p in (c, d):
        if _on_seg(p, a, b):
            return 1
    return 0


def crossings(wires):
    """★ 跨网交叉数 ✓ —— 同一根线的段不算 ✗、共端点不算 ✗（那是正常连接 ✓）

    ★★ 2026-10-04 ✓ **“共端点”改用容差判** ✗（**量出来的** ✓，不是想的 ✗）：
      ✗ 原来是 `b == c or a == d or a == c or b == d` —— **精确相等** ✗；
        而 `.fz` 里坐标存的是**相对偏移**（`x1 = px − x` ✓）⇒ 存进去再加起来会留
        **1e-4∼1e-13 的尾巴** ✗ ⇒ 两根线**明明接在同一个点上** ✓ 却被算成**交叉** ✗。
        实测（`_work/_cross_tol.py` ✓ 第二份实现 ✓）：`pixel` 的 `M2` **24 → 10** ✓、
        用户手画版 **22 → 10** ✓ ⇒ **两边都虚高** ✓（原先那句“我比手画版多 2 个”✗
        其实是**双方都虚高** ✓，放宽后 **打平** ✓）。
      ✓ 现在：4 个端点两两比，**差值 ≤ `SHARE_TOL` 就算共端点** ✓（跳过 ✓）。
      ★ `SHARE_TOL` = **0.05 单位 = 0.014mm** ✓ —— 就是全仓那个“**碰到**”的量 ✓，**不新造数** ✗。
    """
    n = 0
    for i in range(len(wires)):
        a, b, _t = wires[i]
        for j in range(i + 1, len(wires)):
            c, d, _t2 = wires[j]
            if _same_pt(a, c) or _same_pt(a, d) or _same_pt(b, c) or _same_pt(b, d):
                continue
            n += _pair(a, b, c, d)
    return n


def _same_pt(p, q):
    r"""两点是否**算同一个点** ✓（`SHARE_TOL` 容差 ✓）—— 见 `crossings()` 里的实测记录 ✓"""
    return abs(p[0] - q[0]) <= SHARE_TOL and abs(p[1] - q[1]) <= SHARE_TOL


def metrics(path):
    """→ dict ✓（`file` 由调用方补 ✓）"""
    wires, parts = read(path)
    tot = sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b, _t in wires) * S2MM
    meant = aligned = 0
    worst = 0.0
    for a, b, _t in wires:
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        sm, bg = min(dx, dy), max(dx, dy)
        if bg <= 0 or bg < KI * sm:
            continue                       # 真的斜线 ⇒ 不算分母 ✓
        meant += 1
        if sm <= TOL:
            aligned += 1
        else:
            worst = max(worst, sm * S2MM)
    return dict(wires=len(wires), parts=len(parts), mm=round(tot, 1),
                crossings=crossings(wires), meant=meant, aligned=aligned,
                ortho=round(aligned / meant, 4) if meant else float("nan"),
                worst=round(worst, 4))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("用法: py -3.13 sch_metrics.py <a.fzz> [<b.fzz> ...]  # 多文件会多打一张对比表 ✓")
        return 2
    rows = []
    for p in argv:
        m = metrics(p)
        m["file"] = p.replace("\\", "/").split("/")[-1]
        rows.append(m)
        print("── %s ──" % m["file"])
        print("   导线 %d ✓｜元件 %d ✓｜总长 %.1f mm ✓｜交叉 %d ✓｜正交度 %.4f（%d/%d ✓）｜最歪 %.4f mm ✓"
              % (m["wires"], m["parts"], m["mm"], m["crossings"], m["ortho"],
                 m["aligned"], m["meant"], m["worst"]))
    if len(rows) > 1:
        print("\n★ 对比表 ✓（导线↓ / 总长↓ / 交叉↓ / 正交度↑ 才好 ✓）")
        print("   %-30s%-9s%-10s%-11s%-11s%-10s" %
              ("file", "wires", "mm", "crossings", "ortho", "worst"))
        for r in rows:
            print("   %-30s%-9d%-10.1f%-11d%-11.4f%-10.4f"
                  % (r["file"], r["wires"], r["mm"], r["crossings"], r["ortho"], r["worst"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
