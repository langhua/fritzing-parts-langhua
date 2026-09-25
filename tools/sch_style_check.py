#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
sch_style_check.py — 检查 **sketch 摆得对不对**（电路层规则，见 `docs/schem-drawing-rules.md` A 节）。

与 `fzp_check.py` 的分工：**fzp_check = 元件对不对** ✓ ／ **本脚本 = 图摆得对不对** ✓。

用法：
    py -3.13 tools\sch_style_check.py <sketch.fzz | sketch.fz> [--view schematic] [--pitch 100]

网格**不用猜** ✓：Fritzing 的 sketch 自己带
`<view name="schematicView" gridSize="0.1in" alignToGrid="1"/>`（2026-09-26 实测 1.0.3b 的 `.fz`）
—— `gridSize` **带单位**（`0.1in` / `1mm`），本脚本一律换算成 **mil**（`.fz` 里坐标就是 mil ✓）；
`--pitch` 只在没有 `gridSize` 时才需要 ✓。

`.fz` 结构里两处不显然（都实测过 ✓，别猜 ✗）：
① sketch 级 `<view>` 的 `name` 是**驼峰**：`schematicView` / `breadboardView` / `pcbView` ✓；
② **导线也是 `<instance>`**（`title` 形如 `Wire39` ✓）—— 它的坐标在子视图里的
   `<geometry x1 y1 x2 y2 wireFlags/>`，折点是 `<point x y/>` ✓。

查什么（这几条 Fritzing **都不报错**，只是"读起来乱"/"混了"✓）：
  ① **网格（只作参考** ✓**）**：打印该视图的网格**相位**与偏离点 ——
     ★ 2026-09-26 实测：Fritzing 存的是**连续坐标**，网格只是编辑时的辅助、**相位由画布决定** ✗
     ⇒ 绝对坐标**不必**是 pitch 的整数倍（KiCad 那条"引脚/线端必须落网格"在这不适用 ✓），
     所以这一项**不判 FAIL**，只给人看"摆得齐不齐"✓
  ② **位号**：重复（FAIL ✓）／前缀不像元件类型（提示 ✓）／
     **排号顺序不是"先左后右、先上后下"**（提示 ✓ —— 出处 KiCad Annotate 按 X/Y 排序；
     `Duplicate reference designators` = Error）
  ③ **名字只差大小写**（FAIL ✓）：`DATA_in` vs `DATA_IN` —— KiCad 专门为这种情况报 warning
     （`Labels are similar (lower/upper case difference only)`，疑似拼错 ✓）

▶ 与 KiCad 的一条**模型差异**（值得记）：KiCad 靠"线端落在网格上"才能连上，所以有
  `off connection grid` 这条 ERC ✓；**Fritzing 的连接记在 `<connects>` 里** ⇒
  "看着连上其实没连"在 Fritzing 里**基本不会发生** ✓（那条检查这里不需要 ✗）。

判定：**退出码 0 且输出里没有 `FAIL`**（与 `fzp_check.py` 一致 ✓）。
"""
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

# sketch 级 <view name> 与实例子视图标签**同名（驼峰）**，小写后就是这张表
SUBVIEW = {"breadboardview": "breadboardView",
           "schematicview": "schematicView",
           "pcbview": "pcbView"}
REFDES = re.compile(r"^([A-Za-z]+)(\d+)$")
# 常见位号前缀（不符**只提示** ✓ —— 老件/别家库可能有别的写法，别判错 ✗）
KNOWN_PREFIX = {"R", "C", "L", "D", "U", "Q", "J", "P", "SW", "LED", "Y", "X", "T",
                "FB", "K", "TP", "CN", "M", "F", "BT", "PCB", "IC", "RV", "LS", "MK"}


def tag(el):
    return el.tag.split("}")[-1]


def child(el, name):
    for c in el:
        if tag(c) == name:
            return c
    return None


def read_sketch(path):
    """接受 .fzz（zip）或裸 .fz。"""
    if path.lower().endswith(".fz"):
        with open(path, "rb") as fh:
            return ET.fromstring(fh.read())
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if n.endswith(".fz"))
        if not names:
            raise SystemExit("包内没有 .fz：%s" % path)
        if len(names) > 1:
            print("注: 包内有多个 .fz，用第一个：%s" % names[0])
        return ET.fromstring(z.read(names[0]))


def num(s, default=None):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def parse_len(s):
    """Fritzing 的 gridSize **带单位**（`0.1in` / `1mm`）⇒ 一律换算成 **mil**（坐标的单位 ✓）。"""
    if s is None:
        return None
    t = s.strip().lower()
    v = num(t.rstrip("abcdfghijklmnopqrstuvwxyz"))
    if v is None:
        return None
    if t.endswith("mil"):
        return v
    if t.endswith("mm"):
        return v * 1000.0 / 25.4
    if t.endswith("in"):
        return v * 1000.0
    return v   # 无单位：当 mil 认（老文件）


def is_wire(title, mid):
    """Fritzing 把导线也存成 instance（`Wire39`）—— 它不是元件，别当位号核对 ✗。"""
    return title.startswith("Wire") or "Wire" in mid


def is_board(title, mid):
    """面包板 / PCB 板也是 instance，同样不是元件位号 ✓。"""
    return ("Breadboard" in mid or "RectanglePCB" in mid
            or title.startswith("Breadboard") or title.startswith("PCB"))


def gcd_int(values):
    """所有坐标的整数最大公约数 —— 用来**反推**真实网格（自校准 ✓）。"""
    g = 0
    for v in values:
        n = int(round(v))
        if abs(v - n) > 1e-6:
            return None
        while n:
            g, n = n, g % n
    return g or None


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    path = argv[0]
    only_view, pitch_arg = None, None
    i = 1
    while i < len(argv):
        if argv[i] == "--view" and i + 1 < len(argv):
            n = argv[i + 1].strip().lower()
            only_view = n if n.endswith("view") else n + "view"   # 允许写 `--view schematic` ✓
            i += 2
        elif argv[i] == "--pitch" and i + 1 < len(argv):
            pitch_arg = num(argv[i + 1])
            i += 2
        else:
            raise SystemExit("不认识的参数：%s\n\n%s" % (argv[i], __doc__))

    root = read_sketch(path)
    print("文件: %s" % os.path.relpath(path))
    fails, notes = [], []

    # ── 实例（位号 + 各视图坐标；**导线也是 instance** ✓）────────────────────
    insts = []
    for inst in root.iter("instance"):
        title = (inst.findtext("title") or "").strip()
        mid = inst.get("moduleIdRef") or ""
        pos, wires = {}, {}
        vw = child(inst, "views")
        if vw is not None:
            for sub in vw:
                st = tag(sub)
                for g in sub:          # 同一个子视图里可能有多条 geometry（元件 1 条 + 导线若干）
                    if tag(g) != "geometry":
                        continue
                    if g.get("x") is not None and g.get("y") is not None:
                        pos[st] = (num(g.get("x")), num(g.get("y")), g.get("z"))
                    if g.get("x1") is not None:
                        wires.setdefault(st, []).append(g)
        insts.append((title, mid, pos, wires))

    # ── 逐视图：网格 ────────────────────────────────────────────────────────
    views_el = child(root, "views")
    views = [v for v in (views_el if views_el is not None else []) if tag(v) == "view"]
    if only_view:
        views = [v for v in views if (v.get("name") or "").lower() == only_view]
    if not views:
        notes.append("注: sketch 里没找到 <view> —— 网格没法核（--view 写对了么？）")

    for v in views:
        vname = (v.get("name") or "?").lower()
        gs = parse_len(v.get("gridSize"))
        pitch = pitch_arg or gs or 100.0
        if pitch_arg is None and gs is None:
            notes.append("注: %s 视图没有 gridSize ⇒ 暂按 %g 核（可用 --pitch 指定）" % (vname, pitch))
        if (v.get("alignToGrid") or "").lower() in ("false", "0"):
            notes.append("注: %s 视图没开对齐网格（alignToGrid=false）⇒ 先把网格打开再画 ✓" % vname)

        pts, off = [], []
        sub_tag = SUBVIEW.get(vname)
        n_inst = n_wire = 0
        for title, _mid, pos, wires in insts:
            if sub_tag in pos:
                n_inst += 1
                x, y, _z = pos[sub_tag]
                pts.append(("元件 %s" % (title or "?"), x, y))
            for g in wires.get(sub_tag, []):
                n_wire += 1
                for a, b in (("x1", "y1"), ("x2", "y2")):
                    pts.append(("线 %s" % (title or "?"), num(g.get(a)), num(g.get(b))))
                for p in g.iter():
                    if tag(p) == "point":
                        pts.append(("折点 %s" % (title or "?"), num(p.get("x")), num(p.get("y"))))
        print("\n[%s] gridSize=%s alignToGrid=%s　元件 %d / 线 %d ⇒ 检查 %d 个点"
              % (v.get("name"), v.get("gridSize"), v.get("alignToGrid"), n_inst, n_wire, len(pts)))
        if not pts:
            continue
        # ★ 网格**只作参考**（2026-09-26 实测）：Fritzing 存的是**连续坐标**，网格是编辑辅助、
        #   相位由画布决定 ⇒ 绝对坐标不必是 pitch 的整数倍 ✗（故不判 FAIL ✓）。
        res, samples = {}, []
        for who, x, y in pts:
            for axis, c in (("x", x), ("y", y)):
                if c is None:
                    continue
                samples.append((who, axis, c))
                res.setdefault(round(c - pitch * round(c / pitch), 3), []).append((who, axis, c))
        phase = max(res, key=lambda k: len(res[k])) if res else 0
        odd = [e for r, lst in res.items() if r != phase for e in lst]
        print("  网格(参考): 主相位 ≈ %+g mil（%g mil = %.2f mm；sketch 自报 gridSize=%s）"
              % (phase, pitch, pitch * 25.4 / 1000, v.get("gridSize")))
        top = sorted(res.items(), key=lambda kv: -len(kv[1]))[:3]
        print("     相位分布: %s（共 %d 个坐标）"
              % (", ".join("%+g × %d" % (r, len(lst)) for r, lst in top), len(samples)))
        if odd:
            print("     偏离主相位的坐标 %d/%d（Fritzing 里**不算错** ✗，只是没摆得更整齐 ✓；前 5）"
                  % (len(odd), len(samples)))
            for who, axis, c in odd[:5]:
                print("       %-14s %s=%g" % (who, axis, c))
        else:
            print("     %d 个坐标同一个相位 ✓" % len(samples))
        g_all = gcd_int([c for _w, x, y in pts for c in (x, y)])
        if g_all and g_all >= 1 and abs(g_all - pitch) > 1e-6:
            notes.append("注: %s 视图所有坐标都能被 %d 整除 ⇒ 实际最小格可能是 %d mil"
                         "（sketch 自报 %s ✓）" % (vname, g_all, g_all, v.get("gridSize")))

    # ── ② 位号（跨视图：位号是元件的属性，不是视图的）──────────────────────
    refdes = [(t, mid) for t, mid, _p, _w in insts
              if REFDES.match(t) and not is_wire(t, mid) and not is_board(t, mid)]
    seen = {}
    for t, _mid in refdes:
        seen.setdefault(t.upper(), []).append(t)
    dup = sorted(k for k, v in seen.items() if len(v) > 1)
    if dup:
        fails.append("FAIL 位号重复：%s（一个位号只能一个元件 —— KiCad 里这条是 Error ✓）" % dup)
    bad_prefix = sorted({REFDES.match(t).group(1) for t, _m in refdes
                         if REFDES.match(t).group(1) not in KNOWN_PREFIX})
    if bad_prefix:
        notes.append("注: 位号前缀没见过：%s —— 若是有意的就忽略 ✓（常见：R/C/L/D/U/Q/J/SW/LED…）" % bad_prefix)
    print("\n位号: %d 个（%s）" % (len(refdes), ", ".join(t for t, _m in refdes) or "无"))

    # 排号顺序：先左后右、先上后下（按位号数字递增）—— 只提示，不 FAIL（整图可分段 ✓）
    pos_view = only_view or ("schematicview" if any("schematicView" in p for _t, _m, p, _w in insts) else None)
    if pos_view:
        sub_tag = SUBVIEW.get(pos_view)
        pts = [(t, p[sub_tag][0], p[sub_tag][1]) for t, mid, p, _w in insts
               if sub_tag in p and p[sub_tag][1] is not None
               and not is_wire(t, mid) and not is_board(t, mid)]
        if pts:
            row = max(abs(pitch), 1.0)
            ordered = [t for t, _x, _y in sorted(pts, key=lambda r: (round(r[2] / row), r[1]))]
            nums = [(t, int(REFDES.match(t).group(2))) for t in ordered if REFDES.match(t)]
            bad = [(a, b) for (a, na), (b, nb) in zip(nums, nums[1:]) if nb < na]
            print("顺序（%s，按 上→下、左→右）: %s" % (pos_view, " → ".join(t for t, _n in nums)))
            if bad:
                notes.append("注: 排号顺序有 %d 处逆序（如 %s 在 %s 后面）—— KiCad 的 Annotate 默认"
                             "按位置排号，顺手对齐一下读起来更顺 ✓" % (len(bad), bad[0][1], bad[0][0]))

    # ── ③ 名字只差大小写（KiCad 的 `Labels are similar` 同款 ✓）─────────────
    titles = [t for t, _m, _p, _w in insts if t]
    low = {}
    for t in titles:
        low.setdefault(t.lower(), set()).add(t)
    similar = sorted(v for v in low.values() if len(v) > 1)
    if similar:
        fails.append("FAIL 名字只差大小写：%s ⇒ 十有八九是拼错的同一个网 ✗（KiCad 专门为此报 warning ✓）"
                     % " / ".join(sorted(s) for s in similar))

    # ── 结论 ────────────────────────────────────────────────────────────────
    for n in notes:
        print("\n%s" % n)
    for f in fails:
        print("\n%s" % f)
    print("\n判定: %s（FAIL %d 条，提示 %d 条）"
          % ("不合格 ✗" if fails else "通过 ✓", len(fails), len(notes)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
