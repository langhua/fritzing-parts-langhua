#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""给 `svg/Resistor-*` **补回橡皮筋引线（legs）** ✓（2026-10-03 ✓）

★ 为什么要补（**证据 ✓，不是猜 ✗**）：
  · 核心库 `core/SMD_resistor_0402.fzp` 的 breadboard 映射**有**
    `legId="connector0leg"` / `legId="connector1leg"` ✓；
    它的 `svg/core/breadboard/resistor_220.svg` 里也**有**
    `<line id="connector0leg">` / `<line id="connector1leg">` ✓。
  · **我们仓库这 10 档全丢了** ✗（实测：`fzp.legId=False` + `svg.leg=False`）
    ⇒ 面包板上的电阻**没有橡皮筋引线** ✗ ⇒ 两个脚被图形**钉死** ✗
    ⇒ 声明孔与图形间距不一致时**够不到** ✗
    （实测 pixel 板 `R1` 声明 `pin11J↔pin16I` 跨 **45.9 单位**，图形只有 **36 单位**
     ⇒ 悬空 **3.53 mm** ✗）。
  ⇒ 按**原厂口径**补回 ✓（不是自创新画法 ✗）。

★ 引线几何怎么定（照核心库同比例 ✓）：核心库 `resistor_220.svg` 里
  · 引线 = **从 lead 线的端点起、朝本体方向**的一小段（`connector0leg` 向 +x ✓、
    `connector1leg` 向 −x ✓），线与 lead **共线同宽** ✓；
  · 长度 / lead 跨度 = `1.455 / 39.398` = **0.03693** ✓（同一比例套到各档 ✓）。
  本脚本一律**从各档自己的 breadboard svg 里读** lead 端点/线宽 ✓（不写死数 ✗）。

用法：py -3.13 tools/add_resistor_legs.py            # 改文件 + 重打 .fzpz ✓
      py -3.13 tools/add_resistor_legs.py --check    # 只报现状 ✓（不写 ✓）
"""
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SVG_ROOT = os.path.join(REPO, "svg")
FZPZ = os.path.join(REPO, "fzpz")

LEG_RATIO = 1.455 / 39.398          # ★ 核心库实测比例 ✓（引线长 / lead 跨度 ✓）
LEG_COLOR = "#8C8C8C"               # ★ 与核心库一致 ✓（灰引线 ✓）


def find(d, pat):
    for n in sorted(os.listdir(d)):
        if re.match(pat, n):
            return os.path.join(d, n)
    return None


def read_lead(txt):
    """⇒ (x0, x1, y, stroke_width) ✓ —— 从 lead 那条 path 里读 ✓（各档自己一份 ✓）"""
    m = re.search(r'<path\s+d="M\s*([\d.]+)\s*,\s*([\d.]+)\s*H\s*([\d.]+)"[^>]*'
                  r'stroke-width="([\d.]+)"', txt)
    if not m:
        m2 = re.search(r'<path[^>]*d="M\s*([\d.]+),([\d.]+)\s*H\s*([\d.]+)"[^>]*>', txt)
        if not m2:
            return None
        x0, y, x1 = float(m2.group(1)), float(m2.group(2)), float(m2.group(3))
        sw = re.search(r'stroke-width:\s*([\d.]+)', m2.group(0))
        return x0, x1, y, float(sw.group(1)) if sw else 28.9794
    return float(m.group(1)), float(m.group(3)), float(m.group(2)), float(m.group(4))


def add_svg_legs(path, check):
    txt = open(path, encoding="utf-8").read()
    if 'id="connector0leg"' in txt:
        return txt, "已就位 ✓"
    lead = read_lead(txt)
    if lead is None:
        return txt, "✗ 认不出 lead 线（没改）"
    x0, x1, y, sw = lead
    L = round((x1 - x0) * LEG_RATIO, 6)
    legs = ('<line  id="connector0leg" stroke-linecap="round" x1="%g" y1="%g" '
            'x2="%g" y2="%g" stroke="%s" fill="none" stroke-width="%g" />\n'
            '        <line  id="connector1leg" stroke-linecap="round" x1="%g" y1="%g" '
            'x2="%g" y2="%g" stroke="%s" fill="none" stroke-width="%g" />\n        '
            % (x0, y, x0 + L, y, LEG_COLOR, sw, x1, y, x1 - L, y, LEG_COLOR, sw))
    # 插在 lead 那条 path 之后 ✓（与核心库同序：pin → leg → lead ✓）
    m = re.search(r'(<path\s+d="M\s*[\d.]+\s*,\s*[\d.]+\s*H\s*[\d.]+"[^>]*/>\s*\n)', txt)
    if not m:
        return txt, "✗ lead path 定位失败（没改）"
    new = txt[:m.end()] + "        " + legs + txt[m.end():]
    return new, "补引线 ✓（L=%.3f）" % L


def add_fzp_legs(path, check):
    txt = open(path, encoding="utf-8").read()
    if "legId=" in txt:
        return txt, "已就位 ✓"
    n = 0
    for k in ("0", "1"):
        old = '<p layer="breadboard" svgId="connector%spin"/>' % k
        new = '<p layer="breadboard" svgId="connector%spin" legId="connector%sleg"/>' % (k, k)
        if old in txt:
            txt = txt.replace(old, new)
            n += 1
    return (txt, "补 legId ✓（%d 个）" % n if n else "✗ 没找到 breadboard <p>（没改）")

def repack(d, check):
    """把 `svg/Resistor-<size>/` 的 5 个文件**平铺**重打成 `fzpz/Resistor-<size>.fzpz` ✓"""
    size = os.path.basename(d)
    out = os.path.join(FZPZ, size + ".fzpz")
    if check:
        return
    names = sorted(n for n in os.listdir(d) if n.endswith(".fzp") or n.endswith(".svg"))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as w:
        for n in names:
            w.write(os.path.join(d, n), n)
    return out


def main(argv):
    check = "--check" in argv
    dirs = sorted(os.path.join(SVG_ROOT, n) for n in os.listdir(SVG_ROOT)
                  if n.startswith("Resistor-") and os.path.isdir(os.path.join(SVG_ROOT, n)))
    print("== 电阻件补引线（%d 档）%s ==" % (len(dirs), "（只查 ✓）" if check else ""))
    for d in dirs:
        svg = find(d, r"svg\.breadboard\..*\.svg$")
        fzp = find(d, r"part\..*\.fzp$")
        st_svg = st_fzp = "—"
        if svg:
            txt, st_svg = add_svg_legs(svg, check)
            if not check and txt != open(svg, encoding="utf-8").read():
                open(svg, "w", encoding="utf-8", newline="").write(txt)
        if fzp:
            txt, st_fzp = add_fzp_legs(fzp, check)
            if not check and txt != open(fzp, encoding="utf-8").read():
                open(fzp, "w", encoding="utf-8", newline="").write(txt)
        repack(d, check)
        print("   %-16s svg: %-22s fzp: %s" % (os.path.basename(d), st_svg, st_fzp))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
