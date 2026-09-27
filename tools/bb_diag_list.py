# -*- coding: utf-8 -*-
r"""诊断（只读 ✓）：**斜线清单** —— 一张面包板图里所有斜线逐条点名 ✓；
也可以只看**某一根线**的逐段几何 ✓（`--color`）。

目的（2026-09-27 入库 ✓）：把"斜线多不多"从**一个数字**变成**一份名单** ✓ ——
  · 用户的美学判据是"**斜线少 = 好看**" ✓（见 `hardware/pixel/breadboard-wiring.md` ✓），
    而"总长变短"常常是拿斜线换来的 ✗ ⇒ 必须能**逐条看清**是哪些线在斜 ✗；
  · 对着**用户手画的 byHand 版**逐条比对 ✓ ⇒ 才能回答"为什么没像我这样画" ✓
    （实测用途 ✓：`pixel-breadboard98` 斜线 1→9 ✗、`v99` 0 条 ✗、`v100` 4 条 ✓，
     其中 `DATA_OUT (243,63)->(270,108) 14.8mm` 与用户手版**逐字相同** ✓）。

一份实现 ✓：孔坐标 / 判碰 / 颜色名 全调 `bb_compare` ✓（与度量/优化器同源 ✓）；
  "是不是斜线"的容差**与 `bb_compare` 同一个值** ✓（`DIAG_TOL = 0.25` 单位 ✓，
  它是为了滤掉手绘的 0.01~0.14 单位抖动 ✓，见 `bb_compare.metrics` 的注释 ✓）。

用法：
  py -3.13 bb_diag_list.py <sketch.fzz>                  # 列**全部**斜线 ✓
  py -3.13 bb_diag_list.py <sketch.fzz> --color '#cc1414' # 只看这个颜色的线（逐段 ✓）
"""
import os
import sys

LIB = os.path.dirname(os.path.abspath(__file__))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import bb_compare as BC                       # noqa: E402

DIAG_TOL = 0.25      # ★ 与 bb_compare.metrics 里「斜线段」的判据**同一个值** ✓（别各写一份 ✗）


def is_diag(a, b):
    return abs(a[0] - b[0]) > DIAG_TOL and abs(a[1] - b[1]) > DIAG_TOL


def kind(a, b):
    if is_diag(a, b):
        return "斜线"
    return "水平" if abs(a[1] - b[1]) <= DIAG_TOL else "垂直"


def seg_mm(a, b):
    return ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 * BC.UNIT_MM


def main(path, color=None):
    links, _plugged = BC.load(path)
    wires = [lk for lk in links if lk.holes]        # 有孔的才是真导线 ✓（图例装饰没有孔 ✓）
    print("== %s" % path)
    if color:
        sel = [lk for lk in wires if lk.color.lower() == color.lower()]
        if not sel:
            print("   （没有这个颜色的导线：%s）" % color)
        for lk in sel:
            print("  %-14s %-12s holes=%s" % (lk.wids[0], BC.COLOR_NAME.get(lk.color, lk.color),
                                              [h for h, _m in lk.holes]))
            for (a, b) in sorted(lk.segs):
                print("      (%4.0f,%4.0f)->(%4.0f,%4.0f)  %-4s %5.1fmm"
                      % (a[0], a[1], b[0], b[1], kind(a, b), seg_mm(a, b)))
        return
    n = 0
    for lk in wires:
        for (a, b) in sorted(lk.segs):
            if is_diag(a, b):
                n += 1
                print("  %2d. %-14s %-12s (%4.0f,%4.0f)->(%4.0f,%4.0f)  %5.1fmm  %s"
                      % (n, lk.wids[0], BC.COLOR_NAME.get(lk.color, lk.color),
                         a[0], a[1], b[0], b[1], seg_mm(a, b),
                         [h for h, _m in lk.holes]))
    print("斜线合计 %d 条" % n)


if __name__ == "__main__":
    argv = sys.argv[1:]
    c = None
    if "--color" in argv:
        ix = argv.index("--color")
        c = argv[ix + 1]
        argv = argv[:ix] + argv[ix + 2:]
    main(argv[0], c)
