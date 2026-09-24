#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""gen_part.py — PH-2.0-3P-V：2.0mm 3P **立贴母座**（板端插座，PH200 系列）。

数据来源（外部图纸，不入库）：`D:\Downloads\PH2.0 立贴.PDF`（型号 **ZL-PH200-nAB**，1 页）。
  · 图纸规格表 3P 行：**DIM A=4.00  B=6.80  C=9.95**（脚距 ▲2.00±0.15）
  · 矢量图实测（用 2.00mm = 55.815pt、DIM B 6.80 = 189.9pt 双重标定 ⇒ 比例 **27.905 pt/mm**）：
      顶视图（图纸左上，本来就画 3P）**9.956 × 7.452mm** —— 横向 = 规格表 **DIM C(3P) 9.95** ✓；
      纵向 = 本体 5.402 + 端子伸出 2.049（图纸前视图标本体 **5.40** ✓）。
  · 坐标系沿用图纸：y 向下，端子（出脚）朝 −y；y=0 = 端子尖端。
  · 焊盘尺寸/位置采用**嘉立创封装** `CONN-SMD-PH2.0-1X3PW`（0.254mm 单位，÷3.937 得 mm）：
    信号 pad **1.00 × 3.00**（x = 0, ±2.00；内端与**本体前缘**齐平、外端比端子尖端外伸 0.95mm）、
    固定 pad **2.00 × 3.50**（x = ±5.064 —— **压在卡耳底下**，图纸卡耳列 3.95..4.98mm ✓）；
    `pad_hole r=0` ⇒ 确为 SMD。
  · 丝印 = **本体轮廓**，凡有焊盘跨过的边都**挖缺口**（缺口 = 焊盘 + 两侧各 0.23mm 余量）——
    照嘉立创的做法，丝印不压焊盘；**不画 1 脚圆点**（用户 2026-09-25 要求，嘉立创也没有）。
    PCB 只用 3 个信号焊盘（宽 = 端子实测 0.50，长 = 端子伸出实测 2.05）。

视图模型（AGENTS §3b / 房规）：
  · icon      = **厂商图纸俯视图的原样矢量**（1:1；不加焊盘/不加底色、不改尺寸）
  · breadboard= 绿色转接板（直角 #00aa44）+ 3 个 2.54mm 排针（落孔距网格）+ 本体 1:1 居中
  · schematic = 3 脚连接器符号（灰引线 + 极小 terminal + 插线方向箭头）
  · PCB       = 信号焊盘 + 本体丝印角标 + 1 脚圆点
"""
import os
import math
import re
import sys
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FZPZ_DIR = os.path.normpath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
if OUT_DIR not in sys.path:
    sys.path.insert(0, OUT_DIR)
import icon_art          # noqa: E402  顶视图矢量（tools/copy_top.py 从厂商图纸抄出）
try:                     # ★ 手工版 icon（用户亲手改的 = 权威，逐字照搬；见 tools/byhand_icon.py）
    from byHand_icon import (WIDTH_MM as _HAND_W, HEIGHT_MM as _HAND_H,
                             VIEWBOX as _HAND_VB, INNER as _HAND_INNER)
except ImportError:      # 没有手工版就用生成版
    _HAND_INNER = None

# ------------------------------------------------------------------ 身份（包装脚本覆盖）
PART_ID = "PH-2.0-3P-V"
FZPZ = "PH-2.0-3P-V.fzpz"
TITLE = "2.0mm 3P vertical SMD socket (ZL-PH200-3AB)"
SERIES = "PH2.0"          # 丝印/图标上的系列名（= 市场通用叫法）
MODEL = "ZL-PH200-3AB"    # 图纸规格表 3P 行（DIM A/B/C = 4.00 / 6.80 / 9.95）
LABEL = "J"
DATE = "2026-09-24"

# ------------------------------------------------------------------ 几何（mm，KiCad 坐标）
PITCH = 2.00                    # 脚距（图纸 ▲2.00±0.15）
BODY_W = 9.95                   # **DIM C：3P 总宽（含左右闩钩）**
PAD_W, PAD_H = 1.00, 3.00       # 信号**焊盘**（land，不是图纸上的端子原宽）：采用嘉立创
                                #  CONN-SMD-PH2.0-1X3PW 封装（0.254mm 单位：11.811×3.937）。
                                #  ★ 内端与**本体前缘**齐平、外端比端子尖端外伸 0.95mm（嘉立创的取值）
PAD_OVER = 2.05                 # 本体前缘距端子尖端（图纸实测；只给 PCB/丝印用，icon 不引用）
BODY_D = icon_art.H_MM - PAD_OVER       # 本体深 = 7.452 − 2.05 = 5.402 ≈ 图纸前视图 5.40 ✓
MP_PAD_W, MP_PAD_H = 2.00, 3.50  # 固定（锚定）焊盘：取自嘉立创封装（13.779×7.874）——
                                #  位置在**卡耳底下**（图纸卡耳列 3.95..4.98mm ✓）
MP_PAD_X = 5.064                 # 固定焊盘中心 x（嘉立创：离中线 19.937 单位 = 5.064mm）
MP_PAD_Y = 1.080                 # 固定焊盘**后缘**距本体后缘（嘉立创：跨 1.080..4.580mm）

GOLD, GOLD_EDGE = "#f7bf13", "#b98900"

# 上色（用户 2026-09-24：照实物照片上色）—— 颜色只在这里定，`icon_art.py` 里存的是**角色**
ROLE_FILL = {
    "body": "#f0e9d8",         # 本体：米白色塑料（顶面 / 腔壁 / 腔底）
    "cavity": "#e2d8c0",       # 开口腔体内部（比顶面略深一点，看得出“看进去”）
    "metal": "#c9c9c9",        # 针脚 / 焊盘 / 触点：银色金属
    "bevel": "#a3a3a3",        # 斜的金属面：银灰
}
SILK = "#f0f0f0"                # PCB 丝印色（房规）
BB_GREEN, BB_EDGE = "#00aa44", "#00772f"

U = 39.37                       # 100 单位 = 2.54mm（面包板坐标系）
ICON_MARGIN = 0.0               # icon 画布裁到内容 ⇒ 尺寸就是真实尺寸（8.65 × 3.90）


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pad_x(i):
    """第 i 个信号焊盘（0/1/2 → 脚 1/2/3）的 x。"""
    return (i - 1) * PITCH


# ------------------------------------------------------------------ 内容范围
def icon_bbox():
    """icon/面包板/PCB 共用的内容范围（y=0 = 针脚尖端）；有手工版就用它的 viewBox。"""
    if _HAND_INNER is not None:
        return (_HAND_VB[0], _HAND_VB[1],
                _HAND_VB[0] + _HAND_VB[2], _HAND_VB[1] + _HAND_VB[3])
    return (-icon_art.W_MM / 2.0, 0.0, icon_art.W_MM / 2.0, icon_art.H_MM)


# ------------------------------------------------------------------ 面上色（用户 2026-09-24）
def _poly_area(ps):
    return sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(ps, ps[1:] + ps[:1])) / 2.0


def _icon_segments():
    """把 icon_art.PATHS 的 `<path d="M.. L..">` 拆成线段（mm）。"""
    segs = []
    for p in icon_art.PATHS:
        ps = [(float(a), float(b)) for a, b in re.findall(r"[ML]\s*(-?[\d.]+)\s+(-?[\d.]+)", p)]
        for a, b in zip(ps, ps[1:]):
            segs.append((a, b))
        if p.rstrip().endswith("Z") and len(ps) > 2:
            segs.append((ps[-1], ps[0]))
    return segs


def _on_seg(p, a, b, tol=0.006):
    """点 p 是否落在线段 a-b 的**内部**（不含两端）—— 用来平面化 T 型接点。"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return False
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
    if not 0.02 < t < 0.98:
        return False
    return (a[0] + t * dx - p[0]) ** 2 + (a[1] + t * dy - p[1]) ** 2 <= tol * tol


def _planar_faces(grid=0.02):
    """把抄图的线段当作**平面图**，用「左侧规则」遍历取面 —— 面来自图纸自己的线，不是另画的形状。

    返回 [(点列, 面积)]；负面积 = 顺时针（同向的孔/外轮廓），最外层那个负面积面会被丢掉。
    """
    def key(p):
        return (round(p[0] / grid), round(p[1] / grid))

    nodes = {}
    for a, b in _icon_segments():
        for p in (a, b):
            nodes.setdefault(key(p), p)
    # ★ 平面化：把「端点落在别人线段内部」的地方切开（T 型接点），
    #   否则卡耳这种接到本休边线中段上的区域永远围不成面。
    raw = [(nodes[key(a)], nodes[key(b)]) for a, b in _icon_segments()]
    raw = [(a, b) for a, b in raw if key(a) != key(b)]
    allpts = list({key(p): p for a, b in raw for p in (a, b)}.values())
    segs = []
    for a, b in raw:
        cuts = sorted(((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2, p)
                      for p in allpts if _on_seg(p, a, b))
        chain = [a] + [p for _, p in cuts] + [b]
        segs += [(p, q) for p, q in zip(chain, chain[1:]) if key(p) != key(q)]
    out = {}
    for i, (a, b) in enumerate(segs):
        out.setdefault(key(a), []).append(i)
        out.setdefault(key(b), []).append(i)

    def other(i, k):
        return segs[i][1] if key(segs[i][0]) == k else segs[i][0]

    for k, lst in out.items():                       # 每节点按角度排序（逆时针）
        lst.sort(key=lambda i: math.atan2(other(i, k)[1] - nodes[k][1],
                                         other(i, k)[0] - nodes[k][0]))
    nxt = {}
    for k, lst in out.items():
        for i in lst:
            d = key(other(i, k))                     # 走到对面节点…
            dl = out[d]                              # …再取那里的「顺时针邻居」
            nxt[(k, i)] = (d, dl[(dl.index(i) - 1) % len(dl)])
    seen, faces = set(), []
    for i0 in range(len(segs)):
        for k0 in (key(segs[i0][0]), key(segs[i0][1])):
            if (k0, i0) in seen:
                continue
            path, k, i = [], k0, i0
            while (k, i) not in seen:
                seen.add((k, i))
                path.append(nodes[k])
                k, i = nxt[(k, i)]
                if (k, i) == (k0, i0):
                    break
            if len(path) >= 3:
                faces.append((path, _poly_area(path)))
    faces = [f for f in faces if abs(f[1]) > 0.008]   # 太小的（线毛）不要
    if faces and max(faces, key=lambda f: abs(f[1]))[1] < 0:
        faces.remove(max(faces, key=lambda f: abs(f[1])))    # 去掉最外层那个「无限面」
    return faces


def _poly_d(ps):
    return "M " + " L ".join(f"{p[0]:.3f} {p[1]:.3f}" for p in ps) + " Z"


def _w_h(ps):
    xs = [p[0] for p in ps]
    ys = [p[1] for p in ps]
    return min(xs), min(ys), max(xs), max(ys)


def _diag(ps):
    """面里有没有斜边（两个方向都有分量）——斜边的面 = 斜的金属面。"""
    return any(abs(q[0] - p[0]) > 0.02 and abs(q[1] - p[1]) > 0.02
               for p, q in zip(ps, ps[1:] + ps[:1]))


def _fill_ratio(ps):
    """面积占 bbox 的比例：≈1 = 实心面，明显 <1 = 环/壁。"""
    x0, y0, x1, y1 = _w_h(ps)
    return abs(_poly_area(ps)) / max(1e-9, (x1 - x0) * (y1 - y0))


def _body_rect():
    """本体轮廓（x0,y0,x1,y1）—— 取那个「环状」大面（顶面）的 bbox。"""
    ring = None
    for ps, a in _planar_faces():
        x0, y0, x1, y1 = _w_h(ps)
        if x1 - x0 > 3.0 and y1 - y0 > 1.0 and _fill_ratio(ps) < 0.55:
            if ring is None or abs(a) > abs(ring[1]):
                ring = (ps, a)
    return _w_h(ring[0]) if ring else (-icon_art.W_MM / 2.0, 0.0,
                                       icon_art.W_MM / 2.0, icon_art.H_MM)


def _ear_columns():
    """卡耳竖列 → 两张表（左/右）：[(x0, x1, y0, y1, role)]。

    列边界取抄图里的**竖线**；纵向范围取两条边界竖线的**交集**（不会盖到倒角外面）；
    角色按用户 2026-09-24 指定：最外列 = 米黄（塑料）、次列 = 银（金属卡脚）、
    再列 = 银灰（斜的金属面）。
    """
    bx0, by0, bx1, by1 = _body_rect()
    segs = _icon_segments()
    V = [(p[0], min(s[0][1], s[1][1]), max(s[0][1], s[1][1]))
         for s in segs for p in s if abs(s[0][0] - s[1][0]) < 1e-6]
    out = {}
    for sgn, edge in ((-1, bx0), (1, bx1)):
        xs = sorted({round(x, 3) for x, _, _ in V if sgn * x >= abs(edge) - 1e-9},
                    key=lambda x: -sgn * x)
        cols = []
        for i in range(len(xs) - 1):
            a, b = xs[i], xs[i + 1]
            ys = [(lo, hi) for x, lo, hi in V if abs(x - a) < 1e-6 or abs(x - b) < 1e-6]
            y0 = max(lo for lo, _ in ys) if ys else by0
            y1 = min(hi for _, hi in ys) if ys else by1
            cols.append((min(a, b), max(a, b), y0, y1,
                         ("body", "metal", "bevel")[min(i, 2)]))
        out[sgn] = cols
    return out


def _face_role(ps):
    """按位置给面定角色；None = 不用单独画（米白底面已铺过）。

    坐标 = 抄图自己的坐标系（x 居中、y=0 = 针脚尖端）：
      · 金属 = 三个针脚（y 小）/ 腔内三个触点（y 大）；
      · 金属面里**带斜边的** = 斜的金属面（银灰）；
      · 本体内的宽面 = 腔体（比顶面略深，看得出“看进去”）；
      · **卡耳**里的面按竖列分：最外米黄 / 次列银 / 再列银灰。
    """
    x0, y0, x1, y1 = _w_h(ps)
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    bx0, by0, bx1, by1 = _body_rect()
    if cx < bx0 - 0.001 or cx > bx1 + 0.001:                 # 在卡耳里
        if w > 0.9:
            return None                                      # 横跨整卡的横带 = 塑料
        if _diag(ps):
            return "bevel"                                   # 卡耳里的斜的金属面
        for c0, c1, cy0, cy1, role in _ear_columns()[-1 if cx < 0 else 1]:
            if c0 - 1e-6 <= cx <= c1 + 1e-6:
                return None if role == "body" else role
        return None
    near_pin = min(abs(cx - pad_x(i)) for i in range(3)) <= 0.25
    # 金属 = 针脚 / 腔内触点 / 靠近本体两端的小面（焊板卡脚与它的内机）
    if (near_pin and not (w > 3.0 and h > 1.0)) or 1.9 <= abs(cx) <= 3.0:
        return "bevel" if _diag(ps) and max(w, h) <= 1.4 else "metal"
    if w > 3.0 and h > 1.0 and _fill_ratio(ps) >= 0.55:
        return "cavity"
    return None


def _icon_base():
    """米白底面 = 本体 + 左右卡耳（三段矩形，全部从抄图的极值推出来，不另编尺寸）。"""
    bx0, by0, bx1, by1 = _body_rect()
    out = [(bx0, by0, bx1, by1)]
    segs = _icon_segments()
    for pts, inner in (([p for s in segs for p in s if p[0] <= bx0 - 0.001], bx0),
                       ([p for s in segs for p in s if p[0] >= bx1 + 0.001], bx1)):
        if not pts:
            continue
        xs = [p[0] for p in pts] + [inner]
        ys = [p[1] for p in pts]
        out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def _pin_blocks():
    """每个针脚块（x0, x1, 斜切线 y, 与本体相接的 y）—— 四个数全从抄图的线里读。"""
    out = []
    for i in range(3):
        px = pad_x(i)
        segs = [s for s in _icon_segments()
                if max(abs(s[0][0] - px), abs(s[1][0] - px)) <= 0.45
                and max(s[0][1], s[1][1]) <= 1.20]
        if not segs:
            continue
        xs = [p[0] for s in segs for p in s]
        ys = [p[1] for s in segs for p in s]
        hor = [p[1] for s in segs for p in s
               if abs(s[0][1] - s[1][1]) < 1e-6 and p[1] > 0.01]     # 斜切线 = 最靠尖端的那条横线
        out.append((min(xs), max(xs), min(hor), max(ys)))
    return out


def _icon_fills():
    """图纸自己的面（`<path fill-rule="evenodd">`）：大面积先铺底，小面随后叠上去。

    ★ 只画**正面积**的面：负面积的是「洞/互补」面，同一块地方往往已经有正面在画，
      再叠一层就会把整块涂错色（用户 2026-09-24：中间那个触点被涂成深灰色）。
    """
    faces = sorted(_planar_faces(), key=lambda f: abs(f[1]), reverse=True)
    out = []
    for ps, a in faces:
        if a <= 0:
            continue
        role = _face_role(ps)
        if role:
            out.append((role, _poly_d(ps)))
    return out


def icon_svg():
    """icon = **厂商图纸俯视图的原样矢量**（`tools/copy_top.py` 从 `1.25 立贴.PDF` 抄出，剪掉 3 个脚位宽）。

    用户 2026-09-24 定（已写进 AGENTS §10）：
      · **严格按图纸** ⇒ 不自作主张加焊盘、加底色、改尺寸；就是这个俯视图的线条，
        尺寸 = 图纸实测（见 `icon_art.W_MM / H_MM`）；
      · 剪脚位只剪**中间 3 个脚位的宽度**（3×1.25mm），**两侧卡耳整块保留**，
        跟在剪窗右侧的图形一起左移 —— 界面上就变成一只 3P 的插座。
    """
    x0, y0, x1, y1 = icon_bbox()
    vw, vh = x1 - x0, y1 - y0
    if _HAND_INNER is not None:
        # ★ 手工版优先：内容**逐字照搬**，不加工（用户 2026-09-24：手工版是权威）
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" '
                f'height="{vh:.2f}mm" viewBox="{x0:.2f} {y0:.2f} {vw:.2f} {vh:.2f}">\n'
                ' <g id="icon">\n' + _HAND_INNER + '\n </g>\n</svg>\n')
    L = ['<?xml version="1.0" encoding="UTF-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
         f'viewBox="{x0:.2f} {y0:.2f} {vw:.2f} {vh:.2f}">\n',
         ' <g id="icon">\n']
    # 上色（用户 2026-09-24）：① 米白底面（本体 + 卡耳）→ ② 图纸自己的面（腔体/金属/斜面）
    #   → ③ 卡耳竖列矩形兜底 + 针脚块（**针尖浅色 + 针尖下面深灰斜面**）→ ④ 图纸的线压在最上面
    for bx0, by0, bx1, by1 in _icon_base():
        L.append(f'  <rect x="{bx0:.3f}" y="{by0:.3f}" width="{bx1 - bx0:.3f}" '
                 f'height="{by1 - by0:.3f}" fill="{ROLE_FILL["body"]}" stroke="none"/>\n')
    for role, d in _icon_fills():
        L.append(f'  <path d="{d}" fill="{ROLE_FILL[role]}" fill-rule="evenodd" stroke="none"/>\n')
    # 卡耳竖列：除了由「面」上色，再用**矩形兜底**一遍（不依赖面的剖分，换渲染器也不会丢）
    for cols in _ear_columns().values():
        for c0, c1, cy0, cy1, role in cols:
            if role == "body":
                continue
            L.append(f'  <rect x="{c0:.3f}" y="{cy0:.3f}" width="{c1 - c0:.3f}" '
                     f'height="{cy1 - cy0:.3f}" fill="{ROLE_FILL[role]}" stroke="none"/>\n')
    for x0, x1, yc, yb in _pin_blocks():
        L.append(f'  <rect x="{x0:.3f}" y="0.000" width="{x1 - x0:.3f}" height="{yb:.3f}" '
                 f'fill="{ROLE_FILL["metal"]}" stroke="none"/>\n')
        L.append(f'  <rect x="{x0:.3f}" y="0.000" width="{x1 - x0:.3f}" height="{yc:.3f}" '
                 f'fill="{ROLE_FILL["bevel"]}" stroke="none"/>\n')
    L += [f'  {p}\n' for p in icon_art.PATHS]
    L.append(' </g>\n</svg>\n')
    return "".join(L)


def _icon_inner():
    """取 icon 图层整段（手工版里可能**嵌套 group**，所以按标签配平扫描，不能非贪心一把括）。"""
    s = icon_svg()
    m = re.search(r'<g\b[^>]*\bid="icon"[^>]*>', s, re.S)
    if not m:
        return ""
    depth, i = 1, m.end()
    for t in re.finditer(r"</?g\b", s[i:]):
        depth += -1 if t.group(0) == "</g" else 1
        if depth == 0:
            return s[m.start():i + t.start()] + "</g>"
    return ""


def _embed(cx, cy):
    """把 icon 内容按 1:1（mm → 单位）嵌到面包板坐标 (cx, cy)。"""
    x0, y0, x1, y1 = icon_bbox()
    icx, icy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return (f'  <g transform="translate({cx:.1f} {cy:.1f}) scale({U}) '
            f'translate({-icx:.3f} {-icy:.3f})">\n' + _icon_inner() + '  </g>\n')


def breadboard_svg():
    """面包板 = 绿色转接板（AGENTS §3b）：本体 1:1 居中在上，下方一排 3 个 2.54mm 排针。

    单位：100 单位 = 2.54mm。排针中心 x=100/200/300（间距恰好 2.54mm、落面包板孔网格），
    y = 100 的整数倍；引脚号白色、逆时针 90°、居中于焊盘上方 80 单位（朝板心一侧）。
    """
    x0, y0, x1, y1 = icon_bbox()
    h_u = (y1 - y0) * U                      # 本体高（单位）
    margin = 40
    cy_socket = margin + h_u / 2.0           # 本体中心 y
    socket_bot = margin + h_u
    pin_y = 100 * max(3, int((socket_bot + 140) / 100.0 + 0.9999))   # 落 100 的整数倍
    # 板宽取 100 的偶数倍（保证中间 3 个针位也落在 100 的整数倍上），并容下本体
    w_u = (x1 - x0) * U
    bw = 100 * max(4, 2 * int((w_u / 2 + 55) / 100.0 + 0.9999))
    pin_x = (bw // 2 - 100, bw // 2, bw // 2 + 100)
    bh = pin_y + 100
    pad_s, hole_r = 78.0, 0.485 * U          # 2mm 焊盘 + 0.97mm 针孔
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw / 100 * 2.54:.2f}mm" '
         f'height="{bh / 100 * 2.54:.2f}mm" viewBox="0 0 {bw} {bh}">\n',
         ' <g id="breadboard">\n',
         f'  <rect x="0" y="0" width="{bw}" height="{bh}" fill="{BB_GREEN}" stroke="{BB_EDGE}" stroke-width="5"/>\n']
    # 本体（1:1，居中于板宽，位于上部）
    L.append(_embed(bw / 2.0, cy_socket))
    # 3 个排针焊盘 + 中央针孔
    for i, px in enumerate(pin_x):
        L.append(f'  <rect id="connector{i}pin" connectorname="{i + 1}" '
                 f'x="{px - pad_s / 2:.1f}" y="{pin_y - pad_s / 2:.1f}" width="{pad_s:.1f}" '
                 f'height="{pad_s:.1f}" fill="{GOLD}" stroke="{GOLD_EDGE}" stroke-width="4" rx="6"/>\n')
        L.append(f'  <circle cx="{px:.1f}" cy="{pin_y:.1f}" r="{hole_r:.1f}" fill="#2b2b2b"/>\n')
    # 引脚号（逆时针 90°、居中、朝板心一侧、与焊盘留 0.3mm）
    for i, px in enumerate(pin_x):
        ty = pin_y - 80
        L.append(f'  <text x="{px:.1f}" y="{ty:.1f}" font-size="60" fill="#ffffff" text-anchor="middle" '
                 f'dominant-baseline="central" font-family="DroidSans" '
                 f'transform="rotate(-90 {px:.1f} {ty:.1f})">{i + 1}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


def schematic_svg():
    """原理图 = 3 脚连接器符号。

    房规：**连接器不画芯片那种矩形符号框**（库里 SMA-PJ1.7-L9.5 / FPC-05F-12P-H15 /
    TypeC16Pin / NetLabel-Pad 都是这种非矩形符号，`tools/schem_check.py` 判「不适用」）。
    这里左列 3 条灰引线（`class="pin"` + terminal）+ 引线上方脚号 + 右侧插座外壳轮廓。
    """
    WIRE, P, DEPTH = 2.54, 2.54, 1.80      # 引线长 / 脚距 / 外壳示意深度（mm）
    FN = 1.30                              # 脚号字号
    top = 0.80
    ys = [top + P / 2.0 + i * P for i in range(3)]     # 脚 1/2/3 的引线 y
    hx0, hx1 = WIRE, WIRE + DEPTH                      # 外壳 x 范围（左缘贴引线末端）
    hy0, hy1 = ys[0] - 1.10, ys[2] + 1.10
    vx, vy = 0.0, top - 1.30
    # 画布要同时容下：引线上的脚号（上）、外壳（右）、下方系列名（下）
    vw = max(hx1 + 0.50, 5.60)
    vh = (hy1 - hy0) + 3.00
    L = ['<?xml version="1.0" encoding="UTF-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
         f'viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}">\n',
         ' <g id="schematic">\n']
    # 外壳轮廓（polyline 直角外形；不用 <rect>，别让它被当成芯片符号框）
    L.append(f'  <polyline points="{hx0:.2f},{hy0:.2f} {hx1:.2f},{hy0:.2f} {hx1:.2f},{hy1:.2f} '
             f'{hx0:.2f},{hy1:.2f} {hx0:.2f},{hy0:.2f}" fill="none" stroke="#000000" '
             f'stroke-width="0.30" stroke-linejoin="round"/>\n')
    for i, y in enumerate(ys):
        # 引线（可连线；末端吸附靠 terminal）
        L.append(f'  <line class="pin" id="connector{i}pin" connectorname="{i + 1}" '
                 f'x1="0" y1="{y:.2f}" x2="{hx0:.2f}" y2="{y:.2f}" stroke="#787878" '
                 f'stroke-width="0.75" stroke-linecap="round" stroke-linejoin="round"/>\n')
        # terminal：极小不可见矩形，贴在引线末端（房规：不画大黑点）
        L.append(f'  <rect id="connector{i}terminal" x="0" y="{y:.4f}" width="0.0001" height="0.0001" '
                 f'stroke="none" fill="none"/>\n')
        # 脚号（引线上方、居中）
        L.append(f'  <text x="{WIRE / 2.0:.2f}" y="{y - 0.28:.2f}" font-size="{FN:.2f}" fill="#8C8C8C" '
                 f'text-anchor="middle" font-family="DroidSans">{i + 1}</text>\n')
    # 系列名（外壳下方居中，灰色小字）
    L.append(f'  <text x="{(hx0 + hx1) / 2.0:.2f}" y="{hy1 + 1.15:.2f}" font-size="1.00" '
             f'fill="#8C8C8C" text-anchor="middle" font-family="DroidSans">{esc(SERIES)}</text>\n')
    L.append(' </g>\n</svg>\n')
    return "".join(L)


def pcb_svg():
    """PCB = 焊盘（信号可连线 + 2 个固定）+ 本体丝印轮廓（照嘉立创：压到焊盘的边留缺口）。

    ★ 方向**与 icon 一致**（2026-09-25 修正）：icon 是图纸原样 —— y=0 是本体**后缘**、
      端子朝下（y 增大方向）。信号焊盘从**本体前缘**往外（外端比端子尖端多伸 0.95mm，同嘉立创）。
    ★ 丝印**不许压焊盘**（2026-09-25 用户指出）：改成嘉立创的做法 —— 画本体轮廓，
      凡有焊盘跨过的那条边就**挖缺口**（缺口宽 = 焊盘 + 两侧各 0.23mm 余量）。
      另：按用户要求**去掉 1 脚圆点**（嘉立创也没有）。
    """
    x0, y0, x1, y1 = icon_bbox()
    yf = y1                                 # icon 下缘 = 端子（尾巴）尖端
    body_f = yf - PAD_OVER                  # 本体前缘 = 焊盘内端
    lw, m, clr = 0.12, 0.35, 0.23           # 丝印线宽 / 画布余量 / 缺口余量
    hw = (MP_PAD_X + MP_PAD_W / 2.0) if MP_PAD_W > 0 else BODY_W / 2.0   # 固定焊盘比本体宽
    sx = BODY_W / 2.0                       # 丝印按本体轮廓（半宽）
    py = MP_PAD_Y if MP_PAD_W > 0 else y0
    vx, vy = min(x0, -hw) - m, min(y0, py) - m
    vw, vh = max(x1, hw) + m - vx, (body_f + PAD_H + m) - vy

    def cut(a, b, holes):
        """把 [a,b] 按 holes = [(中心, 宽), …] 切成若干段（缺口挖掉）。"""
        out, cur = [], a
        for hc, hwid in sorted(holes):
            g0, g1 = hc - hwid / 2.0, hc + hwid / 2.0
            if g0 > cur:
                out.append((cur, min(g0, b)))
            cur = max(cur, g1)
        if cur < b:
            out.append((cur, b))
        return out

    def line(a, b, c, d):
        return (f'   <line x1="{a:.3f}" y1="{b:.3f}" x2="{c:.3f}" y2="{d:.3f}" '
                f'stroke="{SILK}" stroke-width="{lw}" stroke-linecap="round"/>\n')

    L = ['<?xml version="1.0" encoding="UTF-8"?>\n',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}mm" height="{vh:.2f}mm" '
         f'viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}">\n',
         ' <g id="copper1">\n']
    # 固定（锚定）焊盘（机械；不加 id ⇒ 不产生连接器）
    for cx in ((-MP_PAD_X, MP_PAD_X) if MP_PAD_W > 0 else ()):
        L.append(f'  <rect x="{cx - MP_PAD_W / 2:.3f}" y="{MP_PAD_Y:.3f}" '
                 f'width="{MP_PAD_W:.2f}" height="{MP_PAD_H:.2f}" fill="{GOLD}" stroke="none"/>\n')
    # 信号焊盘 = 连接器（copper1）：内端 = 本体前缘，往外伸
    for i in range(3):
        L.append(f'  <rect id="connector{i}pad" connectorname="{i + 1}" '
                 f'x="{pad_x(i) - PAD_W / 2:.3f}" y="{body_f:.3f}" '
                 f'width="{PAD_W:.2f}" height="{PAD_H:.2f}" fill="{GOLD}" stroke="none"/>\n')
    # 丝印：本体轮廓，压到焊盘的边挖缺口（照嘉立创）
    L.append('  <g id="silkscreen">\n')
    pad_holes = [(pad_x(i), PAD_W + 2 * clr) for i in range(3)]
    mech_holes = ([(MP_PAD_Y + MP_PAD_H / 2.0, MP_PAD_H + 2 * clr)] if MP_PAD_W > 0 else [])
    for a, b in cut(-sx, sx, pad_holes):                 # 前缘（被 3 个信号焊盘穿过）
        L.append(line(a, body_f, b, body_f))
    for a, b in cut(y0, body_f, mech_holes):             # 两条侧边（被固定焊盘穿过）
        L.append(line(-sx, a, -sx, b))
        L.append(line(sx, a, sx, b))
    L.append(line(-sx, y0, sx, y0))                      # 后缘（无焊盘）
    L.append('  </g>\n </g>\n</svg>\n')
    return "".join(L)


def fzp_xml():
    conns = []
    for cn in range(3):
        conns.append(f'  <connector id="connector{cn}" name="{cn + 1}" type="female">\n')
        conns.append(f'   <description>pin {cn + 1}</description>\n')
        conns.append('   <views>\n')
        conns.append(f'    <breadboardView><p layer="breadboard" svgId="connector{cn}pin"/></breadboardView>\n')
        conns.append(f'    <schematicView><p layer="schematic" svgId="connector{cn}pin" '
                     f'terminalId="connector{cn}terminal"/></schematicView>\n')
        conns.append(f'    <pcbView><p layer="copper1" svgId="connector{cn}pad"/></pcbView>\n')
        conns.append('   </views>\n  </connector>\n')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
        ' <version>1</version>\n'
        f' <author>Shi Jinghai</author>\n <title>{TITLE}</title>\n'
        f' <label>{LABEL}</label>\n <date>{DATE}</date>\n'
        f' <tags><tag>connector</tag><tag>{esc(SERIES)}</tag>'
        f'<tag>socket</tag><tag>3P</tag><tag>vertical</tag><tag>SMD</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">connector</property>\n'
        f'  <property name="series">{esc(SERIES)}</property>\n'
        f'  <property name="part number">{esc(MODEL)}</property>\n'
        f'  <property name="pitch">{PITCH:g}mm</property>\n'
        '  <property name="pins">3</property>\n'
        '  <property name="mounting">SMD vertical</property>\n'
        ' </properties>\n'
        f' <description>{esc(SERIES)} {PITCH:g}mm 3P vertical SMD socket ({esc(MODEL)}), '
        'board side. Breadboard view = green adapter board with 3 header pins on the 2.54mm grid '
        '(the SMD socket itself cannot plug into a breadboard). Pads follow the manufacturer drawing.</description>\n'
        ' <views>\n'
        f'  <iconView><layers image="icon/{PART_ID}_icon.svg"><layer layerId="icon"/></layers></iconView>\n'
        f'  <breadboardView><layers image="breadboard/{PART_ID}_breadboard.svg">'
        '<layer layerId="breadboard"/></layers></breadboardView>\n'
        f'  <schematicView><layers image="schematic/{PART_ID}_schematic.svg">'
        '<layer layerId="schematic"/></layers></schematicView>\n'
        f'  <pcbView><layers image="pcb/{PART_ID}_pcb.svg">'
        '<layer layerId="copper1"/><layer layerId="silkscreen"/></layers></pcbView>\n'
        f' </views>\n <connectors>\n{"".join(conns)}</connectors>\n</module>\n'
    )


def build(out_dir, part_id, fzpz_name):
    svgs = {
        "icon": icon_svg(),
        "breadboard": breadboard_svg(),
        "schematic": schematic_svg(),
        "pcb": pcb_svg(),
    }
    files = {}
    for view, text in svgs.items():
        name = f"svg.{view}.{part_id}_{view}.svg"
        files[name] = text
    files[f"part.{part_id}.fzp"] = fzp_xml().replace(PART_ID, part_id)
    for name, text in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"wrote {name:<52} {len(text.encode()):>7} bytes")
    os.makedirs(FZPZ_DIR, exist_ok=True)
    dst = os.path.join(FZPZ_DIR, fzpz_name)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, text)
    print(f"wrote {dst}  ({os.path.getsize(dst)} bytes)")


def main():
    build(OUT_DIR, PART_ID, FZPZ)


if __name__ == "__main__":
    main()
