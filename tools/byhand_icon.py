#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把**手工改过的 icon**（`svg.icon.<部件>_icon_byHand.svg`，Inkscape 存的那种）逐字照搬成数据模块。

用法：py -3.13 tools/byhand_icon.py <部件目录>

输出：<部件目录>/byHand_icon.py（纯数据、随部件入库）：
      WIDTH_MM / HEIGHT_MM / VIEWBOX / INNER

★ 只做「逐字照搬」，**不动用户的图**：
  · 取 `<g id="icon">…</g>` 的**全部内容**（嵌套 group / transform / 样式原样保留）；
  · 取 `<svg>` 的 width / height / viewBox；
  · Inkscape 的 `defs` / `sodipodi` / 命名空间等外包装不带走（与手绘版无关）。

★ **图层里面**的 Inkscape 命名空间也要清（2026-09-25 踩到，PH-2.0-3P-V）：
  手工版里一个 `<path>` 带着 `sodipodi:nodetypes="cccc"` ⇒ 生成的 icon 是**非法 XML**
  （`unbound prefix`）⇒ cairosvg / `make_preview.py` 整张炸（与 make_preview 里那个坑同理）。
  所以：删掉所有 `前缀:名字` 的**属性**与**元素标签**（内容保留），再用 ET 自检一遍。
（与 `tools/byhand_export.py`（面包板）同一路子；那个管面包板，这个管 icon。）
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS_ATTR = re.compile(r'\s+[A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*\s*=\s*"[^"]*"')
NS_ELEM_SELF = re.compile(r"<[A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*\b[^>]*?/>")
NS_ELEM_PAIR = re.compile(r"</?[A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*\b[^>]*?>")


def strip_ns(inner):
    """清掉图层内的命名空间属性/元素（Inkscape 壳），否则生成的 svg 不是合法 XML。"""
    inner = NS_ELEM_SELF.sub("", inner)          # 自闭合的 <inkscape:xxx .../>
    inner = NS_ELEM_PAIR.sub("", inner)          # 成对标签：只去标签、内容留下
    return NS_ATTR.sub("", inner)


def svg_attr(text, name):
    m = re.search(name + r'\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def icon_group(text):
    """返回 (整个 <g id="icon">…</g> 的内容, 该 group 的完整文本)；支持嵌套 group。"""
    m = re.search(r'<g\b[^>]*\bid="icon"[^>]*>', text, re.S)
    if not m:
        return None, None
    depth, i = 1, m.end()
    for t in re.finditer(r"</?g\b", text[i:]):
        depth += -1 if t.group(0) == "</g" else 1
        if depth == 0:
            end = i + t.end() + 1
            return text[m.end():i + t.start()], text[m.start():end]
    return None, None


def main():
    part = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    if part.is_file():
        part = part.parent
    name = None
    for p in sorted(part.glob("*_icon_byHand.svg")):
        name = p
        break
    if name is None:
        print(f"没找到 *_icon_byHand.svg（目录：{part}）")
        return 1
    text = name.read_text(encoding="utf-8")
    inner, whole = icon_group(text)
    if inner is None:
        print(f"✗ {name.name} 里没有 <g id=\"icon\"> 图层 —— Fritzing 的 icon 必须有这个图层")
        return 1
    w = float(re.sub(r"[^\d.]", "", svg_attr(text, "width")))
    h = float(re.sub(r"[^\d.]", "", svg_attr(text, "height")))
    vb = [float(v) for v in svg_attr(text, "viewBox").replace(",", " ").split()]
    inner = strip_ns(inner).strip("\n")
    try:                                     # ★ 自检：非法的 svg 会让 Fritzing/cairosvg 整张炸
        ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg">' + inner + "</svg>")
    except ET.ParseError as e:
        print(f"✗ 图层内容不是合法 XML：{e}\n  看是不是还有没清干净的 Inkscape 命名空间")
        return 1
    out = part / "byHand_icon.py"
    out.write_text(
        "# -*- coding: utf-8 -*-\n"
        '"""手工版 icon 的**逐字**数据 —— 由 tools/byhand_icon.py 从\n'
        f"`{name.name}` 导出。\n\n"
        "纯数据、勿手改：要改图请改那个 *_byHand.svg，再重跑 tools/byhand_icon.py。\n"
        '"""\n\n'
        f"SOURCE = {name.name!r}\n"
        f"WIDTH_MM = {w:g}\n"
        f"HEIGHT_MM = {h:g}\n"
        f"VIEWBOX = ({vb[0]:g}, {vb[1]:g}, {vb[2]:g}, {vb[3]:g})\n\n"
        "# icon 图层的**全部内容**（逐字照搬，含嵌套 group / transform / style）\n"
        f"INNER = {inner!r}\n",
        encoding="utf-8")
    print(f"从 {name.name} 导出 -> {out.name}")
    print(f"  width/height = {w:g} × {h:g} mm   viewBox = {vb}")
    print(f"  INNER {len(inner)} 字符，{inner.count('<')} 个元素，"
          f"嵌套 group {max(0, inner.count('<g') - inner.count('</g'))} 层")
    return 0


if __name__ == "__main__":
    sys.exit(main())
