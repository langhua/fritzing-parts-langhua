# -*- coding: utf-8 -*-
r"""★★ **机器自测**（不用任何 `.fzz` ✓）：`sch_body` 的判据逐条钉死 ✓（2026-10-09 ✓）

★ 为什么必须有它 ✗（本仓血的教训 ✓）：旧口径"闸门报 0 违例、用户看见线穿过去了" ✗ ——
  光在真文件上跑**证明不了闸门会响** ✗（可能整张图恰好没有违例 ✓）。⇒ 合成"**该响**"与
  "**不该响**"两类样例 ✓，正反都跑 ✓（与 `pcb_curve_selftest.py` 同一套路 ✓）。

用法：`py -X utf8 tests\sch_body_selftest.py` ⇒ 全过 exit 0 ✓；任一不过 exit 1 ✓（并逐条报出 ✓）。
★ 位置（2026-10-09 用户定 ✓）：**测试一律放 `tools/tests/`** ✓（与 `sch_geom_gap_selftest.py`
  / `pcb_curve_selftest.py` 同一处 ✓）；**命名保留 `*_selftest.py`** ✓ —— ✗ 故意不叫 `test_*.py` ✗
  （pytest 会收集它、被模块级 `SystemExit` 打崩 ✓）。一行跑全部见 `tests\run_all.py` ✓。
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sch_body as SBD                                              # noqa: E402
import sch_box as SB                                                # noqa: E402

# ── 合成一个"符号 svg" ✓（viewBox 与 width 对齐 ⇒ k = 1.0 单位/用户单位 ✓，换算一目了然 ✓）
#    · 本体 = 一个 100×100 的**实心矩形** ✓（(0,0)→(100,100) ✓）
#    · 一条**开放的细线**（描边 2 ✓）在 (0,200)→(100,200) ✓
#    · 一段**圆弧**（`A` ✓）从 (0,300) 到 (100,300)、半径 50 ⇒ 弧顶在 y≈**250** ✓
#      （★ 这正是 `part_box.shape_bbox` 认不出的那种 ✗ —— 复现旧 bug ✓）
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="1.0in" height="4.0in" '
       'viewBox="0 0 90 360">'
       '<g id="schematic">'
       '<rect x="0" y="0" width="100" height="100" fill="#FFFFFF" stroke="#000000" stroke-width="2"/>'
       '<line x1="0" y1="200" x2="100" y2="200" stroke="#000000" stroke-width="2"/>'
       '<path d="M0,300 A50,50 0 0 1 100,300" fill="none" stroke="#000000" stroke-width="2"/>'
       '<line class="pin" id="connector0pin" x1="50" y1="100" x2="50" y2="130" stroke="#787878" stroke-width="4"/>'
       '<rect class="terminal" id="connector0terminal" x="50" y="130" width="0.0001" height="0.0001" fill="none"/>'
       '<text x="50" y="-10">U9</text>'
       '</g></svg>')


def geom(x, y, rot=None):
    """造一个 `<geometry>` 元素 ✓（可带 180° 旋转 ✓ —— 验"含旋转" ✓）"""
    g = ET.fromstring('<geometry x="%s" y="%s" z="1"/>' % (x, y))
    if rot == 180:
        t = ET.SubElement(g, "transform")
        t.set("m11", "-1")
        t.set("m12", "0")
        t.set("m21", "0")
        t.set("m22", "-1")
        t.set("m31", "0")
        t.set("m32", "0")
    return g


FAIL = []


def check(name, got, want):
    ok = (got == want)
    print("  %-58s got=%-6s want=%-6s %s" % (name, got, want, "✓" if ok else "✗✗ FAIL"))
    if not ok:
        FAIL.append(name)


print("== sch_body 自测（合成样例 ✓，单位 = sketch ✓，k = 1.0 ✓）==")

print("\n① 区域判据（实心矩形 100×100 ✓）—— **该响** vs 「容差内不算」 ✓")
shp = SBD.shapes_of(SVG, geom(0.0, 0.0))
check("本体盒 y0（矩形 + 细线 + 弧顶 ✓ —— 若弧没展平会少一截 ✗）",
      round(SBD.bbox(shp)[1], 3), 0.0)
check("弧**自己**的盒 y0 = 250（弧顶 ✓；`shape_bbox` 认不出弧 ⇒ 会得 300 ✗）",
      round(SBD.bbox([shp[2]])[1]), 250)
check("全部外形合起来的盒 y1 = 300 ✓（弧两端的 y ✓）", round(SBD.bbox(shp)[3], 1), 300.0)
check("段 (10,10)→(90,10) 从矩形肚子里穿过 ⇒ **命中** ✗", SBD.seg_hit((10, 10), (90, 10), shp), True)
check("段 (10,0.2)→(90,0.2) 只在容差 0.5 内擦上边界 ⇒ **不算** ✓",
      SBD.seg_hit((10, 0.2), (90, 0.2), shp), False)
check("段 (-50,150)→(150,150) 从矩形外经过（离下边界 50 ✓）⇒ **不算** ✓",
      SBD.seg_hit((-50, 150), (150, 150), shp), False)

print("\n② 描边判据（细线 y=200、描边 2 ✓）—— 只按**半线宽 + eps** 判 ✓")
check("段 (10,200)→(90,200) **压在细线上** ⇒ 命中 ✗", SBD.seg_hit((10, 200), (90, 200), shp), True)
check("段 (10,204)→(90,204) 离细线 4 单位 ⇒ **不算** ✓",
      SBD.seg_hit((10, 204), (90, 204), shp), False)

print("\n③ 圆弧（`A` ✓）—— 旧实现把 `A` 的参数当坐标读 ✗ ⇒ 弧顶丢了 ✗")
check("段 (10,252)→(90,252) 只在**弧顶**那一带穿过 ⇒ 命中 ✗（旧 `shape_bbox` 看不见 ✗）",
      SBD.seg_hit((10, 252), (90, 252), shp), True)
check("段 (10,320)→(90,320) 离弧远（>eps ✓）⇒ **不算** ✓",
      SBD.seg_hit((10, 320), (90, 320), shp), False)

print("\n④ 旋转 180° ✓（`<transform m11=-1 …/>` ✓ ⇒ 本体盒要跟着翻到**负半轴** ✓）")
shp2 = SBD.shapes_of(SVG, geom(1000.0, 1000.0, rot=180))
b2 = SBD.bbox(shp2)
check("旋转后本体盒 x1 = 1000 ✓（矩形 0..100 翻成 900..1000 ✓）", round(b2[2], 3), 1000.0)
check("旋转后本体盒 x0 = **900** ✓", round(b2[0], 3), 900.0)
check("旋转后 段 (910,910)→(990,910) 穿矩形 ⇒ 命中 ✗",
      SBD.seg_hit((910, 910), (990, 910), shp2), True)
check("旋转后 段 (10,10)→(90,10)（原位置 ✓）⇒ 不命中 ✓",
      SBD.seg_hit((10, 10), (90, 10), shp2), False)

print("\n⑤ 豁免**只按位置** ✓（`PIN_R = %.1f` ✓）—— ✗ 不是「整段豁免」 ✗" % SBD.PIN_R)
PINS = [(0.0, 50.0)]
check("段 (0,50)→(0,100) 起脚在脚上、但**整段沿左边界外侧走** ⇒ 不算 ✓",
      SBD.seg_hit((0, 50), (0, 100), shp, PINS), False)
check("★ 段 (0,50)→(60,50) **从脚上横穿本体 60 单位** ⇒ **必须命中** ✗"
      "（旧的「整段豁免」会放它过去 ✗✗）", SBD.seg_hit((0, 50), (60, 50), shp, PINS), True)
check("段 (0,50)→(0.8,50) 只走 `PIN_R` 以内 ⇒ 放行 ✓（= 从脚上接下来的那一小点 ✓）",
      SBD.seg_hit((0, 50), (0.8, 50), shp, PINS), False)

print("\n⑥ `label_region` / `poly_region` ✓")
check("`poly_region` 给 4 点 ⇒ 1 段区域 ✓", len(SBD.poly_region([(0, 0), (5, 0), (5, 5), (0, 5)])), 1)
check("`label_region` 给盒 ⇒ 段内的点在盒心命中 ✓",
      SBD.seg_hit((1, 1), (2, 1), SBD.label_region((0, 0, 4, 4)) if False else
                  SBD.label_region((0, 0, 4, 4))), True)
check("空外形 ⇒ 永不命中 ✓", SBD.seg_hit((0, 0), (100, 100), []), False)

print("\n⑦ ★★ **引脚引线也算本体外形** ✗✓（2026-10-09 改正 ✓ —— 渲染器当场点出来的 ✓）")
check("外形表 = 矩形 + 细线 + 弧 + **引脚引线** = 4 段 ✓（`*terminal` 零尺寸锚点仍跳过 ✓）",
      len(shp), 4)
_PP = [(50.0, 130.0)]
check("★ 脚点 (50,130) 上**垂直往外**走 (50,130)→(80,130) ⇒ 放行 ✓"
      "（`pin_r` 自动抬到 半线宽 2 + eps 0.5 = 2.5 ✓）",
      SBD.seg_hit((50, 130), (80, 130), shp, _PP), False)
check("★ 脚点 (50,130) 上**竖直往外**走 (50,130)→(50,160) ⇒ 放行 ✓",
      SBD.seg_hit((50, 130), (50, 160), shp, _PP), False)
check("★ 引脚引线**被横穿**：段 (20,115)→(80,115) ⇒ **命中** ✗"
      "（引线 x=50、y 100→130 ✓ —— 这就是「线从引脚上横着过去」✗）",
      SBD.seg_hit((20, 115), (80, 115), shp, _PP), True)
check("离引线 4 单位（> 半线宽 2 + eps 0.5 ✓）的横线 (20,134)→(80,134) ⇒ **不算** ✓",
      SBD.seg_hit((20, 134), (80, 134), shp, _PP), False)

print("\n== %s ==" % ("全部通过 ✓" if not FAIL else "**%d 条不过** ✗：%s" % (len(FAIL), FAIL)))
raise SystemExit(1 if FAIL else 0)
