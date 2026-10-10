# -*- coding: utf-8 -*-
r"""★★ 丝印嵌组**扫描器**的**自测** ＋ **全库硬闸门** ✓（2026-10-10 立 ✓）

为什么要有它 ✗：`tools/silk_nest_check.py` 的判据是"**丝印组必须是铜组的兄弟** ✓"——
✗ 但"闸门真能抓病 ✗"这件事**不能靠读代码相信** ✗（第一版就因为**不认自闭合** `<g id="copper0"/>`
把外层 `</g>` 当自己的 ⇒ 一路吞到文件尾 ⇒ **假阳性** ✗，本文件第 ③ 条就是防它回潮 ✓）。

三部分（零第三方依赖 ✓，只用标准库 ✓）：
  ① **合成局** ✓：摆"嵌在 copper1 里 ✗ / 嵌在铜组外的别的组里 ✗ / 嵌在 copper0 里 ✗
     / 与铜组平级 ✓ / 没有丝印组 ✓（不报 ✗）"五种 ⇒ 扫描器的**函数**必须逐一对上 ✓；
  ② **自闭合防假阳性** ✓：`<g id="copper0"/>` ＋ 平级丝印 ⇒ **不许**报 ✓（第一版就错在这 ✓）；
  ③ **全库断言** ✓：本仓 `svg/**/svg.pcb.*.svg` ＋ `fzpz/*.fzpz` 里的 pcb 视图
     **一个违例都不许有** ✓（台账已清空 ✓ ⇒ 从此**任何**零件违例都红灯 ✗）。

用法：`py -X utf8 tools\tests\silk_nest_selftest.py`（或 `tests\run_all.py` 一次跑全部 ✓）；
退出码 0 = 全过 ✓。
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # tools/ ✓
sys.path.insert(0, HERE)
import silk_nest_check as SN                                        # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, ".."))
FAILS = []


def check(name, cond, detail):
    print("   %s %s" % ("✓" if cond else "✗", name))
    print("       %s" % detail)
    if not cond:
        FAILS.append(name)


def pcb(body, tail="</svg>\n"):
    """把 `body` 包成一份最小 pcb svg（`<svg>` 与铜组平级 ✓）。"""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" '
            'viewBox="0 0 10 10">\n' + body + tail)


PAD = '  <rect id="connector0pad" x="0" y="0" width="1" height="1"/>\n'
SILK = '  <rect id="silk0" x="2" y="2" width="1" height="1"/>\n'

print("== ① 合成局：扫描器的函数必须逐个对上 ==")
cases = [
    ("老写法 ✗：丝印嵌在 `<g id=\"copper1\">` 里",
     pcb(' <g id="copper1">\n' + PAD + '  <g id="silkscreen">\n' + SILK + '  </g>\n </g>\n'), "copper1"),
    ("老写法 ✗：丝印嵌在 `<g id=\"copper0\">` 里",
     pcb(' <g id="copper0">\n' + PAD + '  <g id="silkscreen">\n' + SILK + '  </g>\n </g>\n'), "copper0"),
    ("更隐蔽 ✗：丝印嵌在**铜组外的别的组**里（⇒ 仍不是铜组的兄弟 ✗）",
     pcb(' <g id="wrapper">\n <g id="copper1">\n' + PAD + ' </g>\n'
         '  <g id="silkscreen">\n' + SILK + '  </g>\n </g>\n'), "wrapper"),
    ("正确 ✓：丝印与铜组**平级**",
     pcb(' <g id="copper1">\n' + PAD + ' </g>\n <g id="silkscreen">\n' + SILK + ' </g>\n'), None),
    ("合格 ✓：没有丝印组（不是本工具的判据 ✗）",
     pcb(' <g id="copper1">\n' + PAD + ' </g>\n'), None),
]
for title, text, want in cases:
    got = SN.silk_parent(text)
    check(title, got == want, "扫描器判 => 父组 %r（期望 %r）" % (got, want))

print()
print("== ② 自闭合防假阳性 ✓（第一版错在这 ✓）==")
self_closed = pcb(' <g id="copper1">\n' + PAD + '<g id="copper0"/>\n </g>\n'
                  ' <g id="silkscreen">\n' + SILK + ' </g>\n')
pars = SN.group_parents(self_closed)
check("`<g id=\"copper0\"/>` 自闭合 ⇒ 不入栈", pars.get("copper0") == "copper1",
      "copper0 的父组 = %r（它在 copper1 里 ✓）" % pars.get("copper0"))
check("平级丝印 ⇒ **不许**报 ✓", SN.silk_parent(self_closed) is None,
      "丝印的父组 = %r（= None ⇒ 合格 ✓）" % SN.silk_parent(self_closed))

print()
print("== ③ 全库断言：`svg/**/svg.pcb.*.svg` ＋ `fzpz/*.fzpz` 的 pcb 视图，违例 0 ✓ ==")
bad, files = SN.scan([os.path.join(ROOT, "svg"), os.path.join(ROOT, "fzpz")])
views = 0
for p in files:
    if p.endswith(".fzpz"):
        import zipfile
        with zipfile.ZipFile(p) as z:
            views += sum(1 for n in z.namelist()
                         if n.startswith("svg.pcb.") and n.endswith(".svg"))
    elif os.path.basename(p).startswith("svg.pcb."):
        views += 1
check("全库 %d 个 pcb 视图：丝印**不是**铜组兄弟的 = 0" % views, not bad,
      "违例：%s" % (bad if bad else "（无 ✓）"))
check("扫到的文件数 > 0（自测没跑空 ✗）", views > 100, "扫了 %d 个文件 ⇒ %d 个 pcb 视图 ✓"
      % (len(files), views))

print()
if FAILS:
    print("✗ %d 条不过：%s" % (len(FAILS), "、".join(FAILS)))
    raise SystemExit(1)
print("✓ 全部通过：闸门抓得住老写法 ✗、不误伤自闭合/平级写法 ✓、全库违例 0 ✓")
raise SystemExit(0)
