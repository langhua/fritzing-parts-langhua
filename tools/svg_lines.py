# -*- coding: utf-8 -*-
r"""svg_lines.py — `tools/` 内部小工具：把 `<text>` 拆成"行"。

为什么需要它：Inkscape 把**多行文字**写成**一个** `<text>` 里若干个
`sodipodi:role="line"` 的 `<tspan>`，每行各自带 `x`/`y`。
如果直接 `"".join(el.itertext())`，两行会被拼成一行
（踩过：`GND` + `/KEY` 两行被拼成 `GND/KEY`）。

byhand_export.py（导出数据表）与 byhand_check.py（核对）**共用这一份**拆分口径，
否则一个按行、一个按整段，核对表里会冒出"手工版缺了 GND"这种假差异。
"""

NS = "{http://www.w3.org/2000/svg}"


def _num(sv, default=0.0):
    import re
    try:
        txt = re.sub(r"[^0-9.\-]", "", sv or "")
        return float(txt) if txt not in ("", "-", ".") else default
    except ValueError:
        return default


def text_lines(el):
    """返回 [(行文字, x, y), ...]（局部坐标，未乘祖先 transform）。

    没有 tspan（或没有多行）时 = 单行，等价于原来的整段取法。
    某行缺 x/y 时沿用上一行的 x/y；只有 `dy` 时在上一行 y 上累加。
    """
    tspans = [c for c in el if c.tag == NS + "tspan"]
    if not tspans:
        return [("".join(el.itertext()).strip(), _num(el.get("x")), _num(el.get("y")))]
    x, y = _num(el.get("x")), _num(el.get("y"))
    out = []
    for ts in tspans:
        x = _num(ts.get("x"), x) if ts.get("x") else x
        if ts.get("y"):
            y = _num(ts.get("y"))
        elif ts.get("dy"):
            y += _num(ts.get("dy"))
        out.append(("".join(ts.itertext()).strip(), x, y))
    return out
