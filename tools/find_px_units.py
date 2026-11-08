# -*- coding: utf-8 -*-
"""扫描仓里所有用 `px` 写 width/height 的元件 svg，并按 `px → N/90 in` 给出换算。

用法：
  py tools/find_px_units.py            # 只报告
  py tools/find_px_units.py --apply    # 顺手改 svg（生成器另见报告里的 gen 列）

口径（2026-11-08 实测 ✓，两件都对上）：
  Fritzing 把 **1px 当 1 个 sketch 单位**（1/90 in）⇒ `N px` ⇔ `N/90 in`。
  证据：`render_sch.py --verify-export` ⑤「同一零件内脚向量」
    · `48px`（LED2）/`66px`（D3）改前 我 42.00 ↔ 导出 33.60（导出 = sketch×0.8）
      ⇒ 导出反推回 sketch = 42.00 ⇒ k = 1.0 sketch/viewBox单位 = 1px。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
SVGDIR = os.path.join(REPO, "svg")

RX_SVG = re.compile(r"<svg\b[^>]*>", re.S)
RX_WH = re.compile(r'\b(width|height)="([0-9]*\.?[0-9]+)px"')


def fmt(v):
    s = "%.7f" % v
    s = s.rstrip("0")
    return s + "in" if s.endswith(".") else s + "in"


def scan():
    """→ [(部件名, 相对路径, [(attr, px, in), …])]"""
    rows = []
    for part in sorted(os.listdir(SVGDIR)):
        d = os.path.join(SVGDIR, part)
        if not os.path.isdir(d):
            continue
        for sub in ("",):
            pass
        for root, _dirs, files in os.walk(d):
            for f in sorted(files):
                if not f.endswith(".svg") or f.endswith("_byHand.svg"):
                    continue
                p = os.path.join(root, f)
                txt = open(p, encoding="utf-8", errors="replace").read()
                m = RX_SVG.search(txt)
                if not m:
                    continue
                hits = RX_WH.findall(m.group(0))
                if not hits:
                    continue
                rows.append((part, os.path.relpath(p, SVGDIR),
                             [(a, float(v), fmt(float(v) / 90.0)) for a, v in hits]))
    return rows


def gen_px(part):
    """生成器里还剩几处 px 字面量（改 svg 不改生成器的话，G3 会红）。"""
    n = 0
    for root, _dirs, files in os.walk(os.path.join(SVGDIR, part)):
        for f in files:
            if f == "gen_part.py":
                n += len(re.findall(r'px"', open(os.path.join(root, f),
                                                 encoding="utf-8", errors="replace").read()))
    return n


def apply(rows):
    done = 0
    for _part, rel, hits in rows:
        p = os.path.join(SVGDIR, rel)
        raw = open(p, "rb").read()
        txt = raw.decode("utf-8")
        m = RX_SVG.search(txt)
        head = m.group(0)
        new_head = RX_WH.sub(lambda mm: '%s="%s"' % (mm.group(1), fmt(float(mm.group(2)) / 90.0)),
                             head)
        if new_head != head:
            txt = txt[:m.start()] + new_head + txt[m.end():]
            open(p, "wb").write(txt.encode("utf-8"))
            done += 1
    return done


def main():
    rows = scan()
    do_apply = "--apply" in sys.argv
    if not rows:
        print("没有用 px 写 width/height 的 svg ✓")
        return 0
    print("用 px 的 svg：%d 个（部件 %d 个）" % (rows and sum(len(r[2]) and 1 or 0 for r in rows),
                                          len({r[0] for r in rows})))
    print("%-26s %-52s %-30s %s" % ("部件", "文件", "改法", "生成器里剩余 px"))
    for part, rel, hits in rows:
        conv = "，".join("%s=%gpx→%s" % (a, v, s) for a, v, s in hits)
        print("%-26s %-52s %-30s %d" % (part, rel, conv, gen_px(part)))
    if do_apply:
        n = apply(rows)
        print("\n已改 %d 个 svg ✓（生成器列 >0 的部件：改了 svg 也过不了 G3，必须改生成器再重生成）" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
