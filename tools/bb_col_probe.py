# -*- coding: utf-8 -*-
r"""诊断（只读 ✓）：**某几列孔上插了什么元件脚** ✓ —— 看电气拓扑用 ✓。

目的（2026-09-27 入库 ✓）："某个网为什么这样接"这类问题，**先看脚在哪** ✓ ——
  实测用途 ✓：用户手版把 GND 从 `pin13A→pin13X`（col13 拉到 X 轨 ✗ 7.6mm）改成
  `pin12D→pin13D`（col13 搭到**隔壁 col12** ✓ 2.5mm ✓）；
  跑一遍这个工具就看出**为什么这一手成立** ✓：
    `pin12E = D3.connector0(GND)` ✓、`pin13E = D3.connector1(GND)` ✓
    ⇒ D3 的两个地脚正好分在 col12 / col13 ✓，而 col12 本来就已接地 ✓
    ⇒ 把 col13 搭到 col12 **电气上完全等价** ✓，且省 5.1mm ✓。

一份实现 ✓：孔坐标 / 元件脚归属（`plugged` ✓）全调 `bb_compare` ✓。

用法：py -3.13 bb_col_probe.py <sketch.fzz> 12 13 14 [更多列…]
"""
import os
import sys

LIB = os.path.dirname(os.path.abspath(__file__))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import bb_compare as BC                       # noqa: E402

ROWS = "ZYXABCDEFGHIJ"      # 与 bb_compare.hole_xy 认得的那套行名一致 ✓


def main(path, cols):
    _links, plugged = BC.load(path)
    print("== %s" % path)
    for col in cols:
        out = []
        for r in ROWS:
            h = "pin%s%s" % (col, r)
            if BC.hole_xy(h) is None:
                continue
            out.append("%s=%s" % (h, plugged.get(h, "-")))
        if out:
            print("  " + "  ".join(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
