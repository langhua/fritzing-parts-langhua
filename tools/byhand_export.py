#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
byhand_export.py — **开发辅助**：把"Inkscape 手工对齐版"的面包板图，导出成 **数据表模块**。

用途（fritzing-parts-langhua 的"照片对齐"工作流，用户 2026-09-15 定）：
  ① 用户在 Inkscape 里拿实物照片当底，把排针/元件摆好，存成
        svg/<部件>/svg.breadboard.<部件>_breadboard_byHand.svg
     （该文件带照片、是草稿 → 已在 .gitignore 里：`*_byHand.svg`）
  ② 跑本脚本 → 生成 svg/<部件>/byHand_tables.py（**纯数据**，入库）
  ③ gen_part.py `import byHand_tables` 渲染；以后挪位置 = 改这张表

用法：
    C:\Python313\python.exe tools\byhand_export.py svg\CH347F
    （在仓库根跑；也可以给绝对路径）

做了什么：
  · 把嵌套 transform **累乘展开**，每个元素都换成等效绝对几何
  · 单位统一成**内部单位**（100 单位 = 2.54mm；位置/尺寸/字号/描边宽一律 ×元素缩放×INV）
  · `style="fill:…;stroke:…"` 也读（Inkscape 常只写 style，漏读会让两脚件变透明）；
    同理读 `font-weight` —— 手工版里丝印普遍是 bold，丢了会“整体变细”
  · 组件图标：按"图标自身 viewBox 尺寸"自动匹配仓库里同级的部件目录（不靠 g214 这种会变的 id）
  · 照片 `<image>`、Inkscape 壳（sodipsi/defs/namedview）一律丢掉
  · **多行文字拆成多条记录**（Inkscape 把多行写成同个 `<text>` 里的多个 tspan，
    拼起来会把 `GND`+`/KEY` 变成一行）；口径见 tools/svg_lines.py
  · FS_UNIFORM：**全板丝印统一成一个字号**（用户 2026-09-15 定）；FS_KEEP 里的除外
  · LINE_PITCH：多行丝印的**行距倍率**（用户 2026-09-15 定 0.5，比手工版更紧凑）
"""
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

from svg_lines import text_lines

NS = "{http://www.w3.org/2000/svg}"
S = 0.072                     # 内部单位 → viewBox 单位（本仓库面包板图约定）
INV = 1.0 / S

# 全板丝印**统一字号**（内部单位 = 手工版里 "SDA" 那一条的字号，用户 2026-09-15 定）。
#   手工对齐时字号会随手变得有大有小（34/31.8/30/28…）→ 程序生成一律归到这一个数。
#   换一块板子：先在手工版里量一个丝印字号，改这一个数。
FS_UNIFORM = 30.0
# 这些矩形由别处**单源生成**，不进数据表（否则会画出重复图形）：
#   #c9c9c9 / #b5b5b5 = USB-B01 的金属片 → gen_part 的 _usb_b01_icon()
#   #002d68           = 板框 → gen_part 的 BOARD_W/H + 圆角（板框带 rx，直角重复会盖掉圆角）
SKIP_RECT_FILL = {"#c9c9c9", "#b5b5b5", "#002d68"}
# 例外：**左下角两行**（板名 / 网址），按手工版原样保留 —— 它们本来就该比丝印大
FS_KEEP = {"CH347F-EVT-R0-1v0", "http://wch.cn"}
# 多行丝印的**行距倍率**：1.0 = 照手工版；用户 2026-09-15 定 **0.5**（两行靠得更紧）
LINE_PITCH = 0.5


def mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2, a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def parse_tf(text):
    m = (1, 0, 0, 1, 0, 0)
    for fn, args in re.findall(r'(matrix|translate|scale|rotate)\s*\(([^)]*)\)', text or ""):
        v = [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]
        if fn == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif fn == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif fn == "rotate":
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                t = mul((1, 0, 0, 1, v[1], v[2]), mul(t, (1, 0, 0, 1, -v[1], -v[2])))
        else:
            t = tuple(v)
        m = mul(m, t)
    return m


def ap(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def scl(m):
    return (math.hypot(m[0], m[1]), math.hypot(m[2], m[3]))


def ang(m):
    return round(math.degrees(math.atan2(m[1], m[0])), 1)


def styled(el, key, default=None):
    """先读同名属性，再读 style="a:b;c:d"（Inkscape 常只写 style）。"""
    v = el.get(key)
    if v:
        return v
    for kv in (el.get("style") or "").split(";"):
        if ":" in kv:
            k, v2 = kv.split(":", 1)
            if k.strip() == key:
                return v2.strip()
    return default


def num(sv, default=0.0):
    try:
        return float(re.sub(r"[^0-9.\-]", "", sv or "") or default)
    except ValueError:
        return default


def u(v):
    """外层单位 → 内部单位（100 = 2.54mm）"""
    return round(v * INV, 2)


def icon_sizes(repo_svg_dir):
    """同级部件目录里的 icon：{部件名: (宽mm, 高mm, 中心x_mm, 中心y_mm)} —— 用来按尺寸认图标。"""
    out = {}
    for name in sorted(os.listdir(repo_svg_dir)):
        p = os.path.join(repo_svg_dir, name, "svg.icon.%s_icon.svg" % name)
        if not os.path.isfile(p):
            continue
        a = open(p, encoding="utf-8").read()
        vb = re.search(r'viewBox="([-\d.eE]+) ([-\d.eE]+) ([-~\d.eE]+) ([-~\d.eE]+)"', a)
        if not vb:
            continue
        x0, y0, w, h = (float(v) for v in vb.groups())
        out[name] = (w, h, x0 + w / 2.0, y0 + h / 2.0)
    return out


def run(part_dir):
    repo_svg = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(part_dir)), ""))
    part_dir = os.path.abspath(part_dir)
    part = os.path.basename(part_dir)
    src = os.path.join(part_dir, "svg.breadboard.%s_breadboard_byHand.svg" % part)
    if not os.path.isfile(src):
        raise SystemExit("没找到手工版：%s" % src)
    sizes = icon_sizes(repo_svg)
    pads, texts, rects, circles, lines, icons, unknown = [], [], [], [], [], [], []
    used = set()

    def match_icon(w, h, ccx, ccy, tol=0.35):
        """按尺寸（宽高 & 中心偏移）认图标；找不到就返回 None。"""
        best, bd = None, 1e9
        for name, (iw, ih, icx, icy) in sizes.items():
            if name in used:
                continue
            d = abs(iw - w) + abs(ih - h)
            if d < bd and abs(ccx - icx) < 0.4 and abs(ccy - icy) < 0.4:
                best, bd = name, d
        return best if bd < tol else None

    def walk(el, m):
        tag = el.tag.replace(NS, "")
        m2 = mul(m, parse_tf(el.get("transform"))) if el.get("transform") else m
        sc = scl(m2)
        if tag == "image":
            return
        # 组件图标：一个组里装着 rect/circle/text 且缩放明显不是 0.072
        if tag == "g" and abs(sc[0] - sc[1]) < 1e-6 and sc[0] > 0.3 and len(el):
            tags = {c.tag.replace(NS, "") for c in el.iter() if c is not el}
            if tags and tags <= {"rect", "circle", "text"}:
                xs, ys = [], []
                for c in el.iter():
                    if c.tag == NS + "rect":
                        x = float(c.get("x", 0) or 0); y = float(c.get("y", 0) or 0)
                        w = float(c.get("width", 0) or 0); h = float(c.get("height", 0) or 0)
                        xs += [x, x + w]; ys += [y, y + h]
                    elif c.tag == NS + "circle":
                        cx2 = float(c.get("cx", 0) or 0); cy2 = float(c.get("cy", 0) or 0)
                        r2 = float(c.get("r", 0) or 0)
                        xs += [cx2 - r2, cx2 + r2]; ys += [cy2 - r2, cy2 + r2]
                if xs:
                    w, h = max(xs) - min(xs), max(ys) - min(ys)
                    ccx, ccy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
                    name = match_icon(w, h, ccx, ccy)
                    if name:
                        used.add(name)
                        iw, ih, icx, icy = sizes[name]
                        # 摆放按**图标自身 viewBox 中心**（_bake_icon 就是这么对准的）
                        p = ap(m2, icx, icy)
                        icons.append((name, u(p[0]), u(p[1]), ang(m2)))
                        return
        if tag == "circle":
            p = ap(m2, float(el.get("cx", 0)), float(el.get("cy", 0)))
            r = float(el.get("r", 0)) / INV
            cid = el.get("id") or ""
            if "connector" in cid:
                pads.append((cid, el.get("connectorname"), u(p[0]), u(p[1])))
            else:
                sw3 = styled(el, "stroke-width")
                circles.append((u(p[0]), u(p[1]), round(r, 2), styled(el, "fill"),
                                styled(el, "stroke"),
                                round(num(sw3) * (sc[0] + sc[1]) / 2.0 * INV, 3) if sw3 else None))
        elif tag == "rect":
            x, y = float(el.get("x", 0) or 0), float(el.get("y", 0) or 0)
            w, h = float(el.get("width", 0) or 0), float(el.get("height", 0) or 0)
            if (styled(el, "fill") or "") in SKIP_RECT_FILL:
                return                       # 单源生成的那些矩形（见 SKIP_RECT_FILL）
            ps = [ap(m2, x, y), ap(m2, x + w, y), ap(m2, x, y + h), ap(m2, x + w, y + h)]
            xs = [p[0] for p in ps]; ys = [p[1] for p in ps]
            sw = styled(el, "stroke-width")
            rects.append((u(min(xs)), u(min(ys)), u(max(xs) - min(xs)), u(max(ys) - min(ys)),
                          styled(el, "fill"), ang(m2), styled(el, "stroke"),
                          round(num(sw) * (sc[0] + sc[1]) / 2.0 * INV, 3) if sw else None))
        elif tag == "text":
            fs = num(styled(el, "font-size")) * (sc[0] + sc[1]) / 2.0 * INV
            fw = "bold" if (styled(el, "font-weight") or "").lower() in \
                 ("bold", "bolder", "600", "700", "800", "900") else None
            # 多行文字（Inkscape 写成多个 role="line" 的 tspan）→ **一行一条记录**，
            # 不能拼成一串（踩过：GND + /KEY 被拼成 GND/KEY）
            tlines = text_lines(el)
            if len(tlines) > 1:
                y0 = tlines[0][2]           # 行距沿**局部 y**（换行方向），首行不动
                tlines = [(t, x, y0 + (y - y0) * LINE_PITCH) for t, x, y in tlines]
            for txt, lx, ly in tlines:
                if not txt:
                    continue
                p = ap(m2, lx, ly)
                fs2 = fs
                if txt not in FS_KEEP:
                    if abs(fs - FS_UNIFORM) > 0.5:
                        unknown.append((txt, round(fs, 1)))   # 手工版里的原字号，仅作提示
                    fs2 = FS_UNIFORM
                texts.append((txt, u(p[0]), u(p[1]), round(fs2, 2), el.get("text-anchor"),
                              ang(m2), styled(el, "fill"), fw))
        elif tag == "line":
            p0 = ap(m2, float(el.get("x1", 0)), float(el.get("y1", 0)))
            p1 = ap(m2, float(el.get("x2", 0)), float(el.get("y2", 0)))
            lines.append((u(p0[0]), u(p0[1]), u(p1[0]), u(p1[1]), styled(el, "stroke"),
                          round(num(styled(el, "stroke-width")) * (sc[0] + sc[1]) / 2.0 * INV, 3)))
        for c in el:
            walk(c, m2)

    walk(ET.parse(src).getroot(), (1, 0, 0, 1, 0, 0))

    out = ["# -*- coding: utf-8 -*-",
           "# 由 tools/byhand_export.py 自动生成 —— **请不要手改**，改完手工版重跑脚本即可。",
           "# 源：svg/%s/svg.breadboard.%s_breadboard_byHand.svg（照片底稿，不入库）" % (part, part),
           "# 单位：内部单位（100 单位 = 2.54mm）",
           "", "# 排针焊盘：(图元 id, 丝印名, x, y)", "PADS = ["]
    for cid, nm, x, y in sorted(pads, key=lambda t: (t[2], t[3])):
        cid = re.sub(r"pin.*$", "pin", cid)
        out.append('    ("%s", "%s", %s, %s),' % (cid, nm, x, y))
    out += ["]", "", "# 板上元件：(部件目录, 中心x, 中心y, 旋转°)", "ICONS = ["]
    for name, x, y, a in icons:
        out.append('    ("%s", %s, %s, %s),' % (name, x, y, a))
    out += ["]", "", "# 板面丝印：(文本, x, y, 字号, anchor, 旋转, fill, 字重)", "TEXTS = ["]
    for t, x, y, fs, anchor, a, fill, fw in sorted(texts, key=lambda t: (t[2], t[1])):
        out.append('    ("%s", %s, %s, %s, "%s", %s, "%s", %s),'
                   % (t, x, y, fs, anchor, a, fill, "'bold'" if fw else "None"))
    out += ["]", "", "# 其它矩形（两脚件/跳线/LED/丝印外框；已是旋转后外接框）：",
            "# (x, y, w, h, fill, 旋转, stroke, stroke-width)", "EXTRA_RECTS = ["]
    for r in sorted(rects, key=lambda r: (r[1], r[0])):
        out.append('    (%s, %s, %s, %s, "%s", %s, "%s", "%s"),' % r)
    out += ["]", "", "# 其它圆：(x, y, r, fill, stroke, stroke-width)", "EXTRA_CIRCLES = ["]
    for c in sorted(circles, key=lambda c: (c[1], c[0])):
        out.append('    (%s, %s, %s, "%s", "%s", %s),' % c)
    out += ["]", "", "# 分隔线：(x1, y1, x2, y2, stroke, stroke-width)", "EXTRA_LINES = ["]
    for l in lines:
        out.append('    (%s, %s, %s, %s, "%s", %s),' % l)
    out += ["]", ""]
    dst = os.path.join(part_dir, "byHand_tables.py")
    open(dst, "w", encoding="utf-8").write("\n".join(out))
    print("焊盘 %d / 图标 %d %s / 丝印 %d / 矩形 %d / 圆 %d / 线 %d"
          % (len(pads), len(icons), [i[0] for i in icons], len(texts), len(rects),
             len(circles), len(lines)))
    print("写出:", dst)
    if unknown:
        print("  · 手工版里非统一字号(%.1f)的丝印 %d 条 → 已统一：%s"
              % (FS_UNIFORM, len(unknown), ", ".join("%s=%.1f" % t for t in unknown)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    run(sys.argv[1])
