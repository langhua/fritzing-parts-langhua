# -*- coding: utf-8 -*-
r"""`fix_silk_group` 的**独立尺子**自测 ✓（2026-10-19 用户定「加」✓）

★★ 起因（LED-0603 事故 ✓）：修具的复验调的是**修它用的同一个** `SNC.silk_span` ✓ ⇒ **自证** ✗。
   `LED-0603` 的 pcb 用**单引号** `<g id='silkscreen'>` ✓，旧扫描器认不出 ⇒
   (1) 误报"丝印在组外" (2) 再包一层 ⇒ **5 层同名嵌套** (3) 复验全过 ⇒ 写盘。
   ⇒ 补一条**与正则扫描器毫无共用**的尺子：`silk_depth()`（xml.etree 按**树**数层数 ✓）。

四部分（零第三方依赖 ✓）：
  1 **量得准** ✓：0 / 1 / 2 / 5 层都数对；单引号也认；坏 XML ⇒ None；
  2 **不误伤** ✓：正常装组（0 => 1 层）放行 ✓、几何一字未动 ✓；
  3 **拦得住** ✓：修具产出 3 层结果 ⇒ `process()` 必须**拒写** ✗、文件原样 ✓；
  4 **全库** ✓：真跑一遍 dry-run ⇒ 待改 0 ✓。

★ 素材**必须带 `xmlns="http://www.w3.org/2000/svg"`** ✓（真元件都带 ✓）——
  ✗ 不带的话 `ET` 的 tag 是裸 `g`，比 `== "g"` 也能过 ⇒ **命名空间 bug 测不出来** ✗
  （2026-10-19 实测：第一版就是因为素材太干净而假绿 ✗）。

用法：`py -X utf8 tools\tests\fix_silk_group_selftest.py`（或 `tests\run_all.py` ✓）；exit 0 = 全过 ✓。
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # tools/
sys.path.insert(0, HERE)
import fix_silk_group as FSG                                        # noqa: E402

W = 'xmlns="http://www.w3.org/2000/svg"'
FAILS = []


def check(name, cond, detail):
    print("   %s %s" % ("V" if cond else "X", name))
    print("       %s" % detail)
    if not cond:
        FAILS.append(name)


def svg(body, q='"'):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg %s width="10mm" height="10mm" viewBox="0 0 10 10">\n' % W
            + body.replace('"', q) + '</svg>\n')


PAD = '  <rect id="connector0pad" x="0" y="0" width="1" height="1"/>\n'
LEAF = '   <rect id="silkoutline" fill="none" stroke="#f0f0f0" x="2" y="2" width="1" height="1"/>\n'
LOOSE = svg(' <g id="copper1">\n' + PAD + ' </g>\n'
            '  <rect id="silkscreen" fill="none" stroke="#ffffff" '
            'x="2.25" y="2.5" width="1.5" height="0.75"/>\n')


def nested(k):
    b = ''.join('  ' + '  ' * i + '<g id="silkscreen">\n' for i in range(k))
    return svg(b + LEAF + ''.join('  ' + '  ' * i + '</g>\n' for i in reversed(range(k))))


print("== 1 量得准 ==")
for nm, t, want in [("没有丝印组", svg(' <g id="copper1">\n' + PAD + ' </g>\n'), 0),
                    ("1 层（正常）", svg('  <g id="silkscreen">\n' + LEAF + '  </g>\n'), 1),
                    ("2 层", nested(2), 2),
                    ("5 层（LED-0603 事故）", nested(5), 5),
                    ("单引号 1 层", svg('  <g id="silkscreen">\n' + LEAF + '  </g>\n', q="'"), 1),
                    ("不是合法 XML", "<svg><g>", None)]:
    got = FSG.silk_depth(t)
    check(nm, got == want, "silk_depth => %r（期望 %r）" % (got, want))

print()
print("== 2 不误伤：正常装组（0 => 1 层）必须放行 ==")
d = tempfile.mkdtemp()
p = os.path.join(d, "t.svg")


def put(text):
    io.open(p, "w", encoding="utf-8", newline="").write(text)
    return text


def get():
    return io.open(p, encoding="utf-8", newline="").read()


put(LOOSE)
okp, why = FSG.process(p, do=True)
after = get()
check("process 放行 ✓", okp, why)
check("改后层数 = 1（只多一层 ✓）", FSG.silk_depth(after) == 1,
      "层数 => %r" % FSG.silk_depth(after))
geom = all(s in after for s in ('x="2.25"', 'y="2.5"', 'width="1.5"', 'height="0.75"'))
check("几何一字未动 ✓", geom, "x/y/width/height 原样保留 = %s" % geom)

print()
print("== 3 拦得住：修具产出 3 层结果 => 必须拒写 ==")
before = put(LOOSE)
orig = FSG.fix_text
FSG.fix_text = lambda t: (nested(3), 1)
try:
    okp2, why2 = FSG.process(p, do=True)
finally:
    FSG.fix_text = orig
check("process 拒写 ✓", not okp2, why2)
check("文件原样未动 ✓", get() == before, "改前改后逐字节相同 = %s" % (get() == before))

print()
print("== 4 全库：dry-run 待改必须 0 ==")
r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "fix_silk_group.py")],
                   capture_output=True, text=True, encoding="utf-8")
tail = [ln for ln in r.stdout.splitlines() if "待改" in ln or "复扫" in ln]
check("退出码 0 ✓ 且待改 0 ✓", r.returncode == 0 and not any("待改 **0**" not in ln and "待改" in ln for ln in tail),
      " | ".join(tail) or "（无输出 ✗）")

print()
if FAILS:
    print("X %d 条不过：%s" % (len(FAILS), "、".join(FAILS)))
    raise SystemExit(1)
print("V 全部通过：量得准 ✓、不误伤 ✓、拦得住 ✓、全库待改 0 ✓")
raise SystemExit(0)
