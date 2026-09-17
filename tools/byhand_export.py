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
  · FS_UNIFORM：**全板丝印统一成一个字号**（用户 2026-09-15 定）；FS_KEEP / 大字规则里的除外
  · LINE_PITCH：多行丝印的**行距倍率**（用户 2026-09-15 定 0.5，比手工版更紧凑）
  · **单位跟着文档走**（2026-09-15 修，见 doc_units()）：手工版可能是
      ○ viewBox 空间（CH347F）：内容放在一个有 scale=S 的组里，用户单位 = 内部单位；
      ○ mm 空间（`make_trace_svg.py` 出的稿）：用户单位就是 mm。
    两套差 2.83 倍，认错**不会报错**、只会整块板悄悄缩放 —— 所以判据取根 svg 的
    width/height(mm) ÷ viewBox，而不是写死一个常数。
  · **隐藏图层（style="display:none"）整棵跳过**：那种层是辅助用的（比如
    `make_trace_svg.py` 的 mm 刻度层），不该进数据表。
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
MM_PER_U = 2.54 / 100.0       # 1 内部单位 = 0.0254mm（100 单位 = 2.54mm）
UF = INV                      # 用户单位 → 内部单位；run() 里按文档 width/height 重算
UF_NOTE = ""

# 全板丝印**统一字号**（内部单位 = 手工版里 "SDA" 那一条的字号，用户 2026-09-15 定）。
#   手工对齐时字号会随手变得有大有小（34/31.8/30/28…）→ 程序生成一律归到这一个数。
#   换一块板子：先在手工版里量一个丝印字号，改这一个数。
FS_UNIFORM = 30.0
# 这些矩形由别处**单源生成**，不进数据表（否则会画出重复图形）：
#   #c9c9c9 / #b5b5b5 = USB-B01 的金属片 → gen_part 的 _usb_b01_icon()
#   #002d68           = 板框 → gen_part 的 BOARD_W/H + 圆角（板框带 rx，直角重复会盖掉圆角）
SKIP_RECT_FILL = {"#c9c9c9", "#b5b5b5", "#002d68"}
# 逐部件覆盖（用得上就加一条，并在此写清为什么）：
#   CH347T 的 USB 座是**手工版里自己画的**（没有现成元件 icon 可复用）→
#   不能把 #c9c9c9 丢掉，否则那三块矩形会凭空消失（踩过：整块 USB 不见了）。
SKIP_RECT_FILL_BY_PART = {"CH347T": {"#002d68"}}
# 例外：**左下角两行**（板名 / 网址），按手工版原样保留 —— 它们本来就该比丝印大
FS_KEEP = {"CH347F-EVT-R0-1v0", "http://wch.cn"}
# 大字规则（2026-09-15 加）：原字号 > FS_UNIFORM × 这个倍数 → 按手工版原样保留。
#   换块板子时不用再去改 FS_KEEP 里的板名（CH347T 就是 CH347T-EVT-R0-1v1）。
FS_KEEP_RATIO = 1.3
# 逐部件覆盖：`None` = **不统一**，照手工版的字号直接搬。
#   CH347T 的手工版字号本来就齐（丝印 31.5 / 排针名 35.4 / 板名 65），
#   再拉平到 30 反而会变小（用户 2026-09-15：「文字字号小了，应该跟 byHand 里一致」）。
#   T-Halow-RJ45 同理：整块板是用户 2026-09-18 重画的，字号是**刻意**的（焊盘名比丝印大），
#   拉平会让 10 个焊盘名从 3.26 缩到 2.16 —— 与他的图不一致。
FS_UNIFORM_BY_PART = {"CH347T": None, "T-Halow-RJ45": None}
# 逐部件关闭「按尺寸自动认图标」：
#   T-Halow-RJ45 的图是用户**整块手画**的，里面那些芯片也是手画的（与仓库里同名 icon
#   只是尺寸碰巧相近）—— 一做替换就会把手画的本体/焊盘/丝印丢掉。2026-09-18 实测：
#   IP101GR 被换成仓库 icon 后**灰本体+金焊盘全没了**；手画的 CH340N 被认成 AT24C02，
#   丝印 CH340N 也一起丢了。默认 True（CH347F/CH347T 靠它复用仓库 icon）。
ICON_MATCH_BY_PART = {"T-Halow-RJ45": False}
# 多行丝印的**行距倍率**：1.0 = 照手工版；用户 2026-09-15 定 **0.5**（两行靠得更紧）
LINE_PITCH = 0.5

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def doc_units(root):
    """→ (用户单位 → 内部单位 的系数, 说明)。

    两套约定的差别就在“1 个用户单位是多少 mm”：
      · `width="50.19mm" viewBox="0 0 142.3 157.3"` → 0.3527 mm/单位（viewBox 空间）；
      · `width="50.10mm" viewBox="0 0 50.10 61.20"` → 1.0 mm/单位（mm 空间）。
    只写无单位数字（老式 `width="142.3"`，按 96dpi 解释）时**不敢猜**，退回老常数 INV。
    """
    w, h = root.get("width") or "", root.get("height") or ""
    vb = (root.get("viewBox") or "").replace(",", " ").split()
    try:
        wmm = float(re.sub(r"[^0-9.\-]", "", w))
        hmm = float(re.sub(r"[^0-9.\-]", "", h))
        vw, vh = float(vb[2]), float(vb[3])
    except (IndexError, ValueError):
        return INV, "取不到带单位的 width/height → 退回老常数 INV(=1/S)，请自己核一眼"
    if not (w.endswith("mm") and h.endswith("mm")) or vw <= 0 or vh <= 0:
        return INV, "width/height 不是 mm → 退回老常数 INV(=1/S)，请自己核一眼"
    fx, fy = (wmm / vw) / MM_PER_U, (hmm / vh) / MM_PER_U
    if abs(fx - fy) / fx > 0.02:
        return (fx + fy) / 2.0, "x/y 比例差 %.1f%%（照片或画布不是等比？已取平均值）" \
            % (abs(fx - fy) / fx * 100)
    return fx, "%.4f mm/用户单位（%s 空间）" % (wmm / vw, "mm" if abs(wmm / vw - 1) < 0.01
                                            else "viewBox")


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
    """读元素的某个样式值：**先 `style="a:b;c:d"`，再读同名属性**。

    ★ 优先序不能反（ 2026-09-15 踩到）：SVG/CSS 里 **`style` 的优先级高于表现属性**。
    Inkscape 改颜色时常只改 `style`、把旧的 `fill="…"` 属性留在原地 ——
    先读属性就会拿到旧颜色（实例：CH347T 的塑料座 `fill="#4d7fe0"` 但 `style` 是
    `fill:#e6b53d`，那就是用户画的**跳线**，按老口径会被画成蓝色）。
    """
    for kv in (el.get("style") or "").split(";"):
        if ":" in kv:
            k, v = kv.split(":", 1)
            if k.strip() == key:
                return v.strip()
    v = el.get(key)
    return v if v else default


def num(sv, default=0.0):
    try:
        return float(re.sub(r"[^0-9.\-]", "", sv or "") or default)
    except ValueError:
        return default


def u(v):
    """外层单位 → 内部单位（100 = 2.54mm）—— 系数由 doc_units() 按文档算（见文件头）"""
    return round(v * UF, 2)


def matrix_str(m):
    """累乘矩阵 → SVG 的 `matrix(a,b,c,d,e,f)` 串；单位阵返回 ""（不写 transform）。"""
    if all(abs(a - b) < 1e-9 for a, b in zip(m, (1, 0, 0, 1, 0, 0))):
        return ""
    return "matrix(%s)" % ",".join("%.6g" % v for v in m)


def gradient_defs(root, refs):
    """把被引用到的渐变整理成**干净的 SVG 文本**（丢掉 inkscape/sodipodi 命名空间）。

    为什么需要（2026-09-18，T-Halow-RJ45 的 SMA 螺纹筒）：手工版里金色渐进是用
    `fill="url(#linearGradient10019)"` 引 `<defs>` 里的渐变 —— 只搬形状不搬渐变，
    那几块会**变黑**（fill 取不到 = 回退黑）。
    `xlink:href` 引到的那个（`#thrj_sma_gold`，带 stop 色标）也要一并带上，
    所以这里会**递归追一层**。
    """
    want = set(refs)
    for _ in range(4):                                   # 追 href 链（实测只一层）
        more = set()
        for el in root.iter():
            if (el.get("id") or "") in want:
                h = el.get(XLINK_HREF)
                if h and h.startswith("#"):
                    more.add(h[1:])
        want |= more
    keep = ("x1", "y1", "x2", "y2", "cx", "cy", "r", "fx", "fy",
            "gradientUnits", "gradientTransform", "spreadMethod")
    out = []
    for el in root.iter():
        i = el.get("id") or ""
        tag = el.tag.replace(NS, "")
        if i not in want or tag not in ("linearGradient", "radialGradient"):
            continue
        a = "".join(' %s="%s"' % (k, el.get(k)) for k in keep if el.get(k))
        if el.get(XLINK_HREF):
            a += ' xlink:href="%s"' % el.get(XLINK_HREF)
        kids = "".join('<stop offset="%s" stop-color="%s"%s/>' % (
            s.get("offset"), s.get("stop-color"),
            ' stop-opacity="%s"' % s.get("stop-opacity") if s.get("stop-opacity") else "")
            for s in el if s.tag == NS + "stop")
        out.append('<%s id="%s"%s>%s</%s>' % (tag, i, a, kids, tag))
    return out


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


PIN_G_RE = re.compile(r"^connector\d+pin$")


def splice_pad_groups(root):
    """把「焊盘画成一个组」的手工版摊平：`<g id="connectorNpin">` 里的子元素
    按原次序直接挂到父节点，**id 挪到第一个子元素上**，组上的 transform 累加到每个子元素。

    为什么需要（2026-09-18 用户做 T-Halow-RJ45 手工版时）：
      · CH347F / CH347T 的手工版是**裸 `<circle id="connectorNpin">`**；
      · T-Halow-RJ45 的手工版是**从程序版改出来的**，焊盘沿用了程序版的写法 ——
        `<g id="connectorNpin">` + 外环圆 + 内孔圆（GND 那个还是**方形**的）。
    摊平之后两种写法落到同一段代码上（圆/矩形分支认焊盘），不必再给「组内第一个元素」
    单独写一套。**这不是「替用户对齐」**，只是把一种等价写法归一。
    """
    for parent in list(root.iter()):
        kids = list(parent)
        if not any(k.tag == NS + "g" and PIN_G_RE.match(k.get("id") or "") for k in kids):
            continue
        new_kids = []
        for el in kids:
            if el.tag == NS + "g" and PIN_G_RE.match(el.get("id") or "") and len(el):
                gtf = el.get("transform")
                for j, c in enumerate(list(el)):
                    if gtf:
                        ctf = c.get("transform")
                        c.set("transform", ("%s %s" % (ctf, gtf)).strip() if ctf else gtf)
                    if j == 0:
                        c.set("id", el.get("id"))
                        for k, v in el.attrib.items():
                            if k not in ("id", "transform"):
                                c.set(k, v)
                    new_kids.append(c)
            else:
                new_kids.append(el)
        parent[:] = new_kids


def run(part_dir):
    repo_svg = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(part_dir)), ""))
    part_dir = os.path.abspath(part_dir)
    part = os.path.basename(part_dir)
    src = os.path.join(part_dir, "svg.breadboard.%s_breadboard_byHand.svg" % part)
    if not os.path.isfile(src):
        raise SystemExit("没找到手工版：%s" % src)
    sizes = icon_sizes(repo_svg)
    skip_fill = SKIP_RECT_FILL_BY_PART.get(part, SKIP_RECT_FILL)
    fs_uniform = FS_UNIFORM_BY_PART.get(part, FS_UNIFORM)
    allow_icons = ICON_MATCH_BY_PART.get(part, True)
    pads, texts, rects, circles, lines, icons, unknown = [], [], [], [], [], [], []
    paths = []                               # path 也照搬（d + 累乘 matrix）
    shapes = []                              # ★ **按手工版里的先后顺序**记图元（叠放次序就是画法次序）
    pad_style = []
    pad_col = []                             # 焊盘的 fill / stroke（也从手工版读）
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

    def emit_path(d, el, m2):
        """收一段**局部坐标**的 path（含 polygon / ellipse 转来的）。

        ★ 为什么要"照搬 d + 一个累乘 matrix"而不是"烘坐标"（2026-09-18 加，T-Halow-RJ45）：
          d 里可能有弧（A），fill 又可能是渐变（url(#…)）—— 硬烘要处理 ×scale/×rotate 下的
          rx/ry，很容易错。原样搬是等价的，且不需解释 path 语法。
        ⚠ stroke-width 是**局部单位**（随自带 matrix 一起缩放）⇒ 原值写回，不走 u()/t2()。
        """
        fill, stroke = styled(el, "fill"), styled(el, "stroke")
        sw = styled(el, "stroke-width")
        mtx = matrix_str(m2)
        paths.append((d, mtx, fill, stroke, sw))
        shapes.append(("path", d, mtx, fill, stroke, sw))

    def walk(el, m):
        tag = el.tag.replace(NS, "")
        # 隐藏图层/元素整棵跳过（辅助层，例如刻度）
        if (styled(el, "display") or "").strip() == "none":
            return
        m2 = mul(m, parse_tf(el.get("transform"))) if el.get("transform") else m
        sc = scl(m2)
        if tag == "image":
            return
        # 组件图标：一个组里装着 rect/circle/text 且缩放明显不是 0.072
        if tag == "g" and allow_icons and abs(sc[0] - sc[1]) < 1e-6 and sc[0] > 0.3 and len(el):
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
            # 半径也要跟位置同一套换算（含元素自身的缩放）—— 原来漏了元素缩放，
            # 手工版里当作"焊盘那么大"画的圆会缩成看不见的点
            r = float(el.get("r", 0)) * (sc[0] + sc[1]) / 2.0 * UF
            cid = el.get("id") or ""
            if "connector" in cid:
                pads.append((cid, el.get("connectorname"), u(p[0]), u(p[1])))
                shapes.append(("pad", re.sub(r"pin.*$", "pin", cid), el.get("connectorname"),
                               u(p[0]), u(p[1])))
                if not pad_style:                      # 焊盘样式也以手工版为准（单源）
                    sw0 = styled(el, "stroke-width")
                    pad_style.append(round(r, 2))
                    pad_style.append(round(num(sw0) * (sc[0] + sc[1]) / 2.0 * UF, 2) if sw0 else 0.0)
                    pad_col.append(styled(el, "fill"))
                    pad_col.append(styled(el, "stroke"))
            else:
                sw3 = styled(el, "stroke-width")
                circles.append((u(p[0]), u(p[1]), round(r, 2), styled(el, "fill"),
                                styled(el, "stroke"),
                                round(num(sw3) * (sc[0] + sc[1]) / 2.0 * UF, 3) if sw3 else None))
                shapes.append(("circle", u(p[0]), u(p[1]), round(r, 2), styled(el, "fill"),
                               styled(el, "stroke"),
                               round(num(sw3) * (sc[0] + sc[1]) / 2.0 * UF, 3) if sw3 else None))
        elif tag == "rect":
            x, y = float(el.get("x", 0) or 0), float(el.get("y", 0) or 0)
            w, h = float(el.get("width", 0) or 0), float(el.get("height", 0) or 0)
            if (styled(el, "fill") or "") in skip_fill:
                return                       # 单源生成的那些矩形（见 SKIP_RECT_FILL*）
            if PIN_G_RE.match(el.get("id") or ""):
                # ★ **方形焊盘**（手工版里画成 rect，如 GND 那种）：
                #   表里出 ("pad", id, net, x, y, "square")，生成器照方形画。
                #   ⚠ 判据必须是 `connectorNpin`：手工版里还混着大批 `connector0pad-5`
                #     这类**Ctrl+D 抄来的垃圾 id**（模块焊盘），一并当焊盘就会把
                #     156 个矩形画成 156 个隐形焊盘、图上全没了（2026-09-18 踩过）。
                cid = el.get("id")
                sca = (sc[0] + sc[1]) / 2.0
                pc = ap(m2, x + w / 2.0, y + h / 2.0)
                r2 = max(w, h) * sca * UF / 2.0
                pads.append((cid, el.get("connectorname"), u(pc[0]), u(pc[1])))
                shapes.append(("pad", re.sub(r"pin.*$", "pin", cid), el.get("connectorname"),
                               u(pc[0]), u(pc[1]), "square"))
                if not pad_style:
                    sw0 = styled(el, "stroke-width")
                    pad_style.append(round(r2, 2))
                    pad_style.append(round(num(sw0) * sca * UF, 2) if sw0 else 0.0)
                    pad_col.append(styled(el, "fill"))
                    pad_col.append(styled(el, "stroke"))
                return
            ps = [ap(m2, x, y), ap(m2, x + w, y), ap(m2, x, y + h), ap(m2, x + w, y + h)]
            xs = [p[0] for p in ps]; ys = [p[1] for p in ps]
            sw = styled(el, "stroke-width")
            rr = styled(el, "rx") or styled(el, "ry")
            rd = ang(m2) % 90.0
            if 0.5 < rd < 89.5:
                # ★ **任意角度**的矩形（手工版里少见，T-Halow-RJ45 有 3 个 -139.7°）：
                #   按 bbox 搬会把它**放大**成外框 ⇒ 改成 4 点 path（绝对坐标，不带 matrix），
                #   几何精确；描边宽也一并换算成绝对值（path 不带 matrix，不再被缩放）。
                #   90° 整数倍继续走 bbox：旋转矩形与它的 bbox 重合，不需要变换。
                sca4 = (sc[0] + sc[1]) / 2.0
                d4 = "M %s L %s L %s L %s Z" % tuple(
                    "%.4f %.4f" % (p[0], p[1]) for p in (ps[0], ps[1], ps[3], ps[2]))
                shapes.append(("path", d4, "", styled(el, "fill"), styled(el, "stroke"),
                               round(num(sw) * sca4 * UF, 3) if sw else None))
                paths.append((d4, "", styled(el, "fill"), styled(el, "stroke"), None))
                return
            rect = ("rect", u(min(xs)), u(min(ys)), u(max(xs) - min(xs)), u(max(ys) - min(ys)),
                    styled(el, "fill"), ang(m2), styled(el, "stroke"),
                    round(num(sw) * (sc[0] + sc[1]) / 2.0 * UF, 3) if sw else None)
            if rr:
                # ★ 圆角矩形（2026-09-18 加，T-Halow-RJ45）：手工版里板框/芯片本体都带 rx，
                #   原来不搬 ⇒ 一角变直角。rx 作为**可选第 10 个字段**接在后面
                #   （老表只有 9 个字段，生成器按 `len(sh) > 9` 判，不影响已在库的表）。
                rect += (round(num(rr) * (sc[0] + sc[1]) / 2.0 * UF, 2),)
            rects.append(rect)
            shapes.append(rect)
        elif tag == "text":
            fs = num(styled(el, "font-size")) * (sc[0] + sc[1]) / 2.0 * UF
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
                if fs_uniform is not None and not (txt in FS_KEEP
                                                   or fs > fs_uniform * FS_KEEP_RATIO):
                    if abs(fs - fs_uniform) > 0.5:
                        unknown.append((txt, round(fs, 1)))   # 手工版里的原字号，仅作提示
                    fs2 = fs_uniform
                texts.append((txt, u(p[0]), u(p[1]), round(fs2, 2), el.get("text-anchor"),
                              ang(m2), styled(el, "fill"), fw))
        elif tag == "line":
            p0 = ap(m2, float(el.get("x1", 0)), float(el.get("y1", 0)))
            p1 = ap(m2, float(el.get("x2", 0)), float(el.get("y2", 0)))
            lines.append((u(p0[0]), u(p0[1]), u(p1[0]), u(p1[1]), styled(el, "stroke"),
                          round(num(styled(el, "stroke-width")) * (sc[0] + sc[1]) / 2.0 * UF, 3)))
            shapes.append(("line", u(p0[0]), u(p0[1]), u(p1[0]), u(p1[1]), styled(el, "stroke"),
                           round(num(styled(el, "stroke-width")) * (sc[0] + sc[1]) / 2.0 * UF, 3)))
        elif tag == "path":
            d = (el.get("d") or "").strip()
            if d:
                emit_path(d, el, m2)
        elif tag in ("polygon", "polyline"):
            # ★ 多边形（2026-09-18 加，T-Halow-RJ45 的 LED 卡口就是 polygon）：
            #   原来**不处理 ⇒ 静默丢掉**（图上少块东西，但什么都不报）。
            nums = [float(v) for v in re.split(r"[\s,]+", (el.get("points") or "").strip()) if v]
            if len(nums) >= 4:
                d = "M " + " L ".join("%.4f %.4f" % (nums[i], nums[i + 1])
                                       for i in range(0, len(nums) - 1, 2))
                emit_path(d + (" Z" if tag == "polygon" else ""), el, m2)
        elif tag == "ellipse":
            # ★ 椭圆/圆（2026-09-18 加）：Inkscape 的椭圆工具出的是 <ellipse>，
            #   原来不处理 ⇒ 静默丢（用户报「黑色圆按钮没有了」就是它）。
            #   · **接近正圆**（rx≈ry，误差 <3%）⇒ 直接**烘成普通 `<circle>`**（无任何变换）：
            #     圆心/半径都算成绝对值。为什么非烘不可 —— AGENTS §5：Fritzing 对
            #     `transform="matrix(...)"`（尤其带旋转）的解释与 Inkscape 不一致，
            #     会出现「缩到看不见」；库内 icon 也是这么烘的。圆是旋转不变的，烘完零误差。
            #   · 明显是椭圆 ⇒ 只能走 path（两段 A 弧）+ matrix（少见；Fritzing 里需实测）。
            cx, cy = num(el.get("cx")), num(el.get("cy"))
            erx, ery = num(el.get("rx")), num(el.get("ry"))
            if erx > 0 and ery > 0:
                p = ap(m2, cx, cy)
                sca2 = (sc[0] + sc[1]) / 2.0
                if abs(erx - ery) / max(erx, ery) < 0.03:
                    rr = (erx + ery) / 2.0 * sca2 * UF
                    sw2 = styled(el, "stroke-width")
                    circles.append((u(p[0]), u(p[1]), round(rr, 2), styled(el, "fill"),
                                    styled(el, "stroke"),
                                    round(num(sw2) * sca2 * UF, 3) if sw2 else None))
                    shapes.append(("circle", u(p[0]), u(p[1]), round(rr, 2), styled(el, "fill"),
                                   styled(el, "stroke"),
                                   round(num(sw2) * sca2 * UF, 3) if sw2 else None))
                else:
                    emit_path("M %.4f %.4f A %.4f %.4f 0 1 0 %.4f %.4f "
                              "A %.4f %.4f 0 1 0 %.4f %.4f Z"
                              % (cx - erx, cy, erx, ery, cx + erx, cy, erx, ery, cx - erx, cy),
                              el, m2)
        for c in el:
            walk(c, m2)

    global UF, UF_NOTE
    doc = ET.parse(src)
    UF, UF_NOTE = doc_units(doc.getroot())
    print("单位：%s → 换算系数 %.4f（内部单位）" % (UF_NOTE, UF))
    root = doc.getroot()
    splice_pad_groups(root)          # 「焊盘画成一个组」的手工版先摊平
    walk(root, (1, 0, 0, 1, 0, 0))

    globals_refs = set()
    for s in shapes:
        for v in s:
            if isinstance(v, str):
                globals_refs |= set(re.findall(r"url\(#([^)]+)\)", v))
    defs = gradient_defs(root, globals_refs)

    out = ["# -*- coding: utf-8 -*-",
           "# 由 tools/byhand_export.py 自动生成 —— **请不要手改**，改完手工版重跑脚本即可。",
           "# 源：svg/%s/svg.breadboard.%s_breadboard_byHand.svg（照片底稿，不入库）" % (part, part),
           "# 单位：内部单位（100 单位 = 2.54mm）",
           "",
           "# 焊盘样式（半径 / 描边宽 / 填充 / 描边色，内部单位）—— 也从手工版里读，免得两边各写一份",
           "PAD_R = %s" % (pad_style[0] if pad_style else 26.0),
           "PAD_SW = %s" % (pad_style[1] if len(pad_style) > 1 else 5.0),
           "PAD_FILL = %s" % repr(pad_col[0] if pad_col else "#f2f2f2"),
           "PAD_EDGE = %s" % repr(pad_col[1] if len(pad_col) > 1 else "#a9a9ad"),
           "", "# 被形状引用的渐变定义（原样给出；生成器写进 <defs>，否则渐变填充会变黑）",
           "DEFS = ["]
    for d in defs:
        out.append('    %s,' % repr(d))
    out += ["]", "",
            "# 排针焊盘：(图元 id, 丝印名, x, y)", "PADS = ["]
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
    out += ["]", "", "# ★ 图元（**按手工版里的先后顺序**，就是叠放次序）—— 类型：",
            "#   (\"rect\",   x, y, w, h, fill, rot, stroke, sw[, rx])",
            "#   (\"circle\", x, y, r, fill, stroke, sw)",
            "#   (\"pad\",    id, net, x, y[, \"square\"])  ← 焊盘：出图时要带 connectorNpin",
            "#   (\"line\",   x1, y1, x2, y2, stroke, sw)",
            "#   (\"path\",   d, transform, fill, stroke, stroke-width)",
            "#        ⚠ path 的 stroke-width 与 d 都是**局部单位**（元素自带 matrix）",
            "SHAPES = ["]
    for s in shapes:
        if s[0] in ("rect",):
            if len(s) > 9:
                out.append('    ("rect", %s, %s, %s, %s, "%s", %s, "%s", "%s", %s),' % s[1:])
            else:
                out.append('    ("rect", %s, %s, %s, %s, "%s", %s, "%s", "%s"),' % s[1:])
        elif s[0] == "circle":
            out.append('    ("circle", %s, %s, %s, "%s", "%s", %s),' % s[1:])
        elif s[0] == "pad":
            if len(s) > 5:
                out.append('    ("pad", "%s", "%s", %s, %s, "%s"),' % s[1:])
            else:
                out.append('    ("pad", "%s", "%s", %s, %s),' % s[1:])
        elif s[0] == "path":
            out.append('    ("path", %s, "%s", "%s", "%s", "%s"),'
                       % (repr(s[1]), s[2], s[3] if s[3] else "None",
                          s[4] if s[4] else "None", s[5] if s[5] else "None"))
        else:
            out.append('    ("line", %s, %s, %s, %s, "%s", %s),' % s[1:])
    out += ["]", ""]
    dst = os.path.join(part_dir, "byHand_tables.py")
    open(dst, "w", encoding="utf-8").write("\n".join(out))
    print("焊盘 %d / 图标 %d %s / 丝印 %d / 矩形 %d / 圆 %d / 线 %d / path %d / 渐变 %d"
          % (len(pads), len(icons), [i[0] for i in icons], len(texts), len(rects),
             len(circles), len(lines), len(paths), len(defs)))
    print("写出:", dst)
    if unknown:
        print("  · 手工版里非统一字号(%.1f)的丝印 %d 条 → 已统一：%s"
              % (fs_uniform, len(unknown), ", ".join("%s=%.1f" % t for t in unknown)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    run(sys.argv[1])
