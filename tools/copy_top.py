"""把 PDF 顶视图的矢量复制出来，剪掉中间若干个「脚位宽」，得到 3P 的 icon 片段。

思路（用户 2026-09-24 定）：图纸画的是 6P ⇒ 总宽 12.40mm（= 规格表 C(6P)）；
**去掉引脚时必须同时去掉它占的宽度**：剪掉 3 个脚位宽（3×1.25=3.75）⇒ 12.40−3.75 = **8.65mm = C(3P)** ✓

用法：copy_top.py <pdf> <out.svg> <部件目录>/icon_art.py
      [--region x0,y0,x1,y1]   只抄这个区域内的图元（★ 必须把整套图**完全包住**，
                               否则线条会被边界静默截掉 —— 本工具会逐条报出被裁掉的图元）
      [--pitch 34.41] [--pad1 679.245] [--norig 6] [--nnew 3]
      [--nocut]                原样照搬（不剪脚位、不改尺寸）—— 用户 2026-09-24「先照抄，别改动」
坐标输出为 mm，原点 = 内容中心 / 前缘（与 PCB 焊盘对齐：焊盘尖端在前缘）。
"""
import sys

import pymupdf

PDF, OUT = sys.argv[1], sys.argv[2]


def opt(name, dflt):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else dflt


PITCH_PT = opt("--pitch", 34.41)      # 图纸上 1.25mm 的长度（实测）
N_ORIG = int(opt("--norig", 6))
N_NEW = int(opt("--nnew", 3))
SCALE = PITCH_PT / 1.25               # pt per mm

# ★ 线宽：图纸是 CAD 导出的细线（0.705pt ≈ **0.026mm 实物**，印在大图上才看得见），
#   缩到 icon 尺寸（几十像素）就没了 ⇒ 必须重新定线宽（用户 2026-09-24：icon 打开什么都没有）。
STROKE = opt("--stroke", 0.0)        # >0 ⇒ 输出线宽（mm）用这个值，不用图纸原线宽
STROKE_COLOR = (sys.argv[sys.argv.index("--color") + 1] if "--color" in sys.argv
                else "#000000")    # 线色（上色后常用中性灰，免得黑线抢眼）


def region_opt(name, dflt):
    if name in sys.argv:
        return tuple(float(v) for v in sys.argv[sys.argv.index(name) + 1].split(","))
    return dflt


REGION = region_opt("--region", (590, 765, 940, 890))  # 默认 = 立贴顶视图（左列第二张）的紧包围盒
PAD_X0 = opt("--pad1", 679.245)       # 脚 1 中心（实测）
NO_CUT = "--nocut" in sys.argv         # 原样照搬：一个脚位都不剪（用户 2026-09-24：先照抄，别改动）

PAD_XS = [PAD_X0 + i * PITCH_PT for i in range(N_ORIG)]
CUT0 = PAD_XS[N_NEW - 1] + PITCH_PT / 2          # 保留 pad 1..N_NEW
CUT1 = PAD_XS[-1] + PITCH_PT / 2                 # 一直到最后一个 pad 右缘
SHIFT = 0.0 if NO_CUT else CUT1 - CUT0           # 右侧整体左移这么多


def reddish(c):
    return c is not None and c[0] > 0.5 and c[1] < 0.5 and c[2] < 0.5


def annot_like(d):
    """尺寸标注：箭头（小的黑色实心三角）或尺寸数字（小的多段字形）。"""
    r = d["rect"]
    if d.get("fill") is not None and 8 <= r.width <= 22 and 3 <= r.height <= 9 and len(d["items"]) <= 4:
        return True                       # 箭头（含 DIM A/B/C 两端的实心三角）
    if r.width <= 26 and r.height <= 26 and len(d["items"]) >= 6:
        return True                       # 字形（数字/字母轮廓）
    return False


page = pymupdf.open(PDF)[0]
items, clipped = [], []
for d in page.get_drawings():
    r = d["rect"]
    if not (r.x0 >= REGION[0] and r.y0 >= REGION[1] and r.x1 <= REGION[2] and r.y1 <= REGION[3]):
        # 只记「与本区域相交但没被完全包住」的：这些是被区域边界**静默裁掉**的图元
        # （多为尺寸线/延长线/引出线；若真是图形线条，就是区域框错了 —— 必须报出来）
        if r.x1 >= REGION[0] and r.x0 <= REGION[2] and r.y1 >= REGION[1] and r.y0 <= REGION[3]:
            clipped.append(d)
        continue
    if reddish(d.get("color")) or reddish(d.get("fill")):
        continue                                  # 尺寸线/红色中心线（pin 虚线）
    if annot_like(d):
        continue                                  # 箭头 / 尺寸数字
    if max(r.width, r.height) < 2.5 and abs(r.width - r.height) < 1.0:
        continue                                  # × 记号
    items.append(d)
print(f"# 黑色图元 {len(items)}；脚位 x = {[round(v, 1) for v in PAD_XS]}")
if NO_CUT:
    print("# 原样照搬（--nocut）：不剪脚位、不改尺寸")
else:
    print(f"# 剪窗 x = [{CUT0:.2f}, {CUT1:.2f}]（宽 {SHIFT:.2f}pt = {SHIFT / SCALE:.2f}mm）")
if clipped:
    print(f"# ★ 被区域边界裁掉 {len(clipped)} 个图元（本工具只收「完全落在区域内」的）——逐一列出：")
    for d in clipped:
        r = d["rect"]
        print(f"#    → bbox=({r.x0:8.2f},{r.y0:8.2f})-({r.x1:8.2f},{r.y1:8.2f}) "
              f"w={r.width:7.2f} h={r.height:7.2f} segs={len(d['items'])}")


def pts_of(d):
    """把图元折成点列（曲线只取首尾，够用）。"""
    out = []
    for it in d["items"]:
        if it[0] == "l":
            out += [(it[1].x, it[1].y), (it[2].x, it[2].y)]
        elif it[0] == "re":
            r = it[1]
            out += [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)]
        elif it[0] == "c":
            out += [(it[1].x, it[1].y), (it[4].x, it[4].y)]
        elif it[0] == "qu":
            q = it[1]
            out += [(q.ul.x, q.ul.y), (q.lr.x, q.lr.y)]
    return out


def _split_seg(p, q):
    """把线段 p→q 在 CUT0 / CUT1 处切开，返回按参数 t 递增的子段列表。"""
    ts = [0.0, 1.0]
    if p[0] != q[0]:
        for xb in (CUT0, CUT1):
            t = (xb - p[0]) / (q[0] - p[0])
            if 0.0 < t < 1.0:
                ts.append(t)
    ts.sort()
    return [((p[0] + t0 * (q[0] - p[0]), p[1] + t0 * (q[1] - p[1])),
             (p[0] + t1 * (q[0] - p[0]), p[1] + t1 * (q[1] - p[1])))
            for t0, t1 in zip(ts, ts[1:])]


def clip_open(pts):
    """把折线按 x ≤ CUT0（左段原样）/ x ≥ CUT1（右段整体左移 SHIFT）裁开，剪窗内的段丢掉。

    ★ 逐段裁剪 + 边界插值 ⇒ 跨越剪窗的长线（本体上下边、底部长线）会**天然接上**，
      不会像以前那样整条消失（用户 2026-09-24：底部线条缺失）。
    ★ 两侧的耳（卡耳/闩钩）都在剪窗之外 ⇒ 整块保留，只跟着左移（用户 2026-09-24：不要裁两边的耳）。
    """
    out = []
    for p, q in zip(pts, pts[1:]):
        for a, b in _split_seg(p, q):
            if a == b:
                continue
            mx = (a[0] + b[0]) / 2.0
            if mx <= CUT0:
                out.append([a, b])
            elif mx >= CUT1:
                out.append([(a[0] - SHIFT, a[1]), (b[0] - SHIFT, b[1])])
    return out


pieces = []      # 每段 = (点列, 是否闭合, fill, color, width)
for d in items:
    pts = pts_of(d)
    if len(pts) < 2:
        continue
    xs = [p[0] for p in pts]
    x0, x1 = min(xs), max(xs)
    fill, color = d.get("fill"), d.get("color")
    lw = d.get("width") or 0.7
    closed = bool(d.get("closePath")) or fill is not None
    if NO_CUT or x1 <= CUT0:
        pieces.append((pts, closed, fill, color, lw))                      # 剪窗左侧：原样
    elif x0 >= CUT1:
        pieces.append(([(x - SHIFT, y) for x, y in pts], closed, fill, color, lw))   # 右侧：整体左移
    elif closed:
        print(f"# !! 跨剪窗的闭合/填充图元整块丢掉（无法切成两半）：{d['rect']}")
    else:
        pieces += [([a, b], False, fill, color, lw) for a, b in clip_open(pts)]

# 归一化：x 居中、y 以前缘为 0；单位 mm
allx = [p[0] for pts, *_ in pieces for p in pts]
ally = [p[1] for pts, *_ in pieces for p in pts]
cx = (min(allx) + max(allx)) / 2.0
y0 = min(ally)
W, H = (max(allx) - min(allx)) / SCALE, (max(ally) - min(ally)) / SCALE
if NO_CUT:
    print(f"# 抄图尺寸 = {W:.3f} × {H:.3f} mm（照图纸，不缩放）")
else:
    print(f"# 剪完尺寸 = {W:.3f} × {H:.3f} mm"
          f"（剪掉 {SHIFT / SCALE:.2f}mm = {N_ORIG - N_NEW}×{PITCH_PT / SCALE:.2f}；不凑数，只报实测）")


def num(v):
    return f"{v:.3f}".rstrip("0").rstrip(".")


body = []
for pts, closed, fill, color, lw in pieces:
    d_pts = [((x - cx) / SCALE, (y - y0) / SCALE) for x, y in pts]
    dstr = "M " + " L ".join(f"{num(px)} {num(py)}" for px, py in d_pts) + (" Z" if closed else "")
    f = "none" if fill is None else "#000000"
    s = "none" if color is None or reddish(color) else STROKE_COLOR
    sw = STROKE if STROKE > 0 else lw / SCALE        # 输出线宽（mm）
    body.append(f'<path d="{dstr}" fill="{f}" stroke="{s}" stroke-width="{num(sw)}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" '
       f'viewBox="{-W / 2:.3f} {-0.0:.3f} {W:.3f} {H:.3f}">\n' + "\n".join(body) + "\n</svg>\n")
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(svg)
print(f"# 写出 {OUT}（{len(body)} 段）")
if STROKE > 0:
    print(f"# 线宽强制 {STROKE:.3f}mm（图纸原线宽 ≈0.026mm，在 icon 尺寸下看不见）")

# 顺便写一个**纯数据模块**（放进部件目录、随部件入库），供 gen_part.py 使用
if len(sys.argv) > 3:
    mod = sys.argv[3]
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""顶视图矢量数据 —— 由 tools/copy_top.py 从厂商图纸（1.25 立贴，抄的是 6P 那张）抄出。',
        "",
        "纯数据、勿手改：重新抄图请跑 `py -3.13 tools/copy_top.py <pdf> <out.svg> <本文件>`。",
        '"""',
        "",
        f"W_MM = {W:.3f}     # {'照图纸总宽（6P = DIM C(6P) 12.40）' if NO_CUT else '剪完总宽（= DIM C(3P) 8.65）'}",
        f"H_MM = {H:.3f}     # {'照图纸总深（含端子外伸，图纸标 4.12）' if NO_CUT else '剪完总深（含焊盘外伸）'}",
        "PATHS = [",
    ]
    lines += [f"    {p!r}," for p in body]
    lines += ["]", ""]
    with open(mod, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"# 写出数据模块 {mod}")
