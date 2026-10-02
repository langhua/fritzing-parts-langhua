# -*- coding: utf-8 -*-
r"""sketch 里的 **PCB 走线 / 过孔**：读、改、写 ✓（2026-09-30 立）

★★ 为什么要有它 ✓：PCB 上"连线"= 铜箔走线 ＋ 过孔（**物理**导体 ✓，与原理图的
   "同名即连通"完全不同 ✗，见 §5b 第 5 条 ✓）⇒ 想自动布线、想搬件后不错位、
   想查短路，都得先能**逐字读懂并原样写回**这层 XML ✓。

写法（**证据**：`hardware/subboard_4x4/single-channel/single-channel.fzz` ——
  Fritzing 自己写出来的 ✓，不是我们手搓的 ✓；**不许拿废文件当样本** ✗）：
  · 走线 = `<instance moduleIdRef="WireModuleID" modelIndex="<实例号>" path=":/resources/parts/core/wire.fzp">`
    ⇒ pcbView：`<pcbView layer="copper0trace|copper1trace">`
      `<geometry z x y x1 y1 x2 y2 wireFlags/>`
      ⇒ **绝对端点 = (x + x1, y + y1) / (x + x2, y + y2)** ✓
        （`x,y` = 这条线**自己的 loc** ✓、`x1..y2` = **相对偏移** ✓ ——
         ★ 这就是〈8 月那次"挪件冒出远处的垃圾走线"〉的根因 ✓）
      `<wireExtras mils color opacity banded/>` ✓
      `<connectors><connector connectorId="connector0|1" layer="…trace"><geometry x="0" y="0"/>`
        `<connects><connect connectorId="…" modelIndex="…" layer="copper0|copper1|…trace"/>` ✓
        （`layer="copper0|copper1"` = 接在**零件焊盘**上 ✓；`…trace` = 接在**另一根线**上 ✓；
         `modelIndex` = 对方实例号 ✓）
  · 过孔 = `<instance moduleIdRef="ViaModuleID">` ⇒ `<pcbView layer="copper0|copper1"><geometry z x y wireFlags/>`
    ⇒ 位置 = `(x, y)` ✓；`<property name="hole size" value="0.30mm,0.15mm"/>` ✓
      （口径 = **`<孔直径>,<环宽>`** ✓✓ 2026-10-01 定死 ✓：拿 Fritzing 自己的导出反算
       —— 它画的环中心线半径 = `(孔直+环宽)/2` ✓、圆环宽 = 环宽 ✓ ⇒ 反算出
       内径 **0.30** ✓ / 外径 **0.60** ✓，与属性逐位对上 ✓；证据在
       `docs/fritzing-sketch-format-notes.md` 的 **F17** ✓。
       ✗ 旧版备注写的“外径,钻孔”是**错的** ✗，已删 ✗）
  · ★★ **数字格式 = `%.6g`** ✓（= `QString::number(double)` 的默认精度 ✓）：
    `116.672` / `9.502` / `0` / `68.7266` / `22.2222` / `-966.375` / `5.50214` 全部对得上 ✓
    ⇒ **改数字必须用它** ✓，否则写出字节 diff ✗（`--roundtrip` 就是守这条的 ✓）。

用法：
  py -3.13 tools\pcb_wire.py <sketch.fzz> --roundtrip   # 验：所有数字按 %.6g 重写 ⇒ 必须**逐字节相同** ✓
  py -3.13 tools\pcb_wire.py <sketch.fzz> --dump        # 列 PCB 走线/过孔（绝对坐标 ✓ ＋ 端点接在谁身上 ✓）
"""
import os
import re
import sys
import zipfile

NUM_ATTRS = ("z", "x", "y", "x1", "y1", "x2", "y2", "wireFlags", "mils", "opacity", "banded")
NUM_RE = re.compile(r'\b(' + "|".join(NUM_ATTRS) + r')="([-\d.eE+]+)"')
SK = 25.4 / 90.0            # 1 sketch 单位 = 0.28222 mm ✓


def fmt(v):
    """Fritzing 的数字写法 = `%.6g` ✓（末尾零自动去掉 ✓；`-0` 写成 `0` ✓）"""
    s = "%.6g" % float(v)
    return "0" if s == "-0" else s


def blocks(s):
    """按**同缩进配对**切出每个 `<instance …>…</instance>` ✓（不吃到下一个实例 ✓）

    ★ 不用"非贪婪到第一个 `</instance>`" ✗ —— 那是别处踩过的坑（嵌套就截错 ✓）。
    """
    out = []
    for m in re.finditer(r"(?ms)^([ \t]*)<instance\b.*?\n\1</instance>", s):
        out.append((m.group(1), m.group(0)))
    return out


def rewrite_nums(block):
    """把块里的几何数字按 `%.6g` 重写 ✓ ⇒ `(新文本, 与原不同的清单 ✓)`"""
    diff = []

    def sub(m):
        k, v = m.group(1), m.group(2)
        n = fmt(v)
        if n != v:
            diff.append((k, v, n))
        return '%s="%s"' % (k, n)

    return NUM_RE.sub(sub, block), diff


def parse_trace(block):
    """走线 ⇒ `dict(layer, geo, ends)`；不是 PCB 走线 ⇒ None ✓

    `ends` = `{0: [(connectorId, modelIndex, layer), …], 1: […]}` ✓（端点接在谁身上 ✓）
    """
    # ★★ 2026-10-01 修 ✗：原来要求标签**只有** `layer` 一个属性 ✗ —— 而**用户手画的线**
    #   会被 Fritzing 写成 `<pcbView layer="copper0trace" bottom="true">` ✓
    #   ⇒ 整条线**看不见** ✗（实测：`pixel-pcb-v51_byHand.fzz` 里有 **18** 条手画线 ✓，
    #     旧正则只认出 **1** 条 ✗ —— 而**布线器/校验器都靠这个函数** ✗✗
    #     ⇒ 它们会以为那 17 条不存在 ⇒ 可能压上去布线 ✗）。⇒ 改成**容忍额外属性** ✓。
    m = re.search(r'<pcbView\b[^>]*?\blayer="([\w]+)"[^>]*>(.*?)</pcbView>', block, re.S)
    if not m:
        return None
    lay, body = m.group(1), m.group(2)
    g = re.search(r"<geometry ([^>]*)/>", body)
    if not g:
        return None
    geo = dict(re.findall(r'([\w]+)="([^"]*)"', g.group(1)))
    ends = {}
    for cm in re.finditer(r'<connector connectorId="connector(\d)" layer="[\w]+">(.*?)</connector>',
                          body, re.S):
        lst = [(x.group(1), x.group(2), x.group(3)) for x in
               re.finditer(r'<connect connectorId="([\w]+)" modelIndex="(\d+)" layer="([\w]+)"',
                           cm.group(2))]
        ends[int(cm.group(1))] = lst
    # ★ 线宽在 `<wireExtras mils="…"/>` ✓（与 `<geometry>` 同级 ✓，在**同一个视图**里 ✓）
    #   ⇒ 读出来给渲染/校验用 ✓；没写 ⇒ None ✓（调用方自己定默认值 ✓）。
    #   ★ 量的锚点 ✓：`12 mil` = 1.08 单位 = **0.3048 mm** ✓（v47 全板走线 ✓，见 F17 附近 ✓）。
    we = re.search(r'<wireExtras\b[^>]*?\bmils="([-\d.eE+]+)"', body)
    # ★★★ 2026-10-03 ✓：走线可以是**贝塞尔曲线** ✗ —— 控制点就在
    #   `<wireExtras …><bezier><cp0 x y/><cp1 x y/></bezier></wireExtras>` ✓。
    #   口径来源 = **Fritzing 源码** ✓（`src/utils/bezier.h` ✓）：
    #     `Bezier(QPointF endpoint0, QPointF endpoint1, QPointF cp0, QPointF cp1)` ✓
    #     ⇒ 三次贝塞尔 = **两个端点 ＋ 两个控制点** ✓；端点就是 `<geometry>` 那条线 ✓。
    #   ★ `cp0/cp1` 与 `x1..y2` **同一个局部坐标系** ✓（实测 ✓：`cp0=(0,0)` 正好 = 弦的起点 ✓）。
    #   ✗✗ 只读 `<geometry>` 两端点 ⇒ 把这 17 根曲线**当直线**算 ✗ ⇒ 线间距/交叉/障碍框全失真 ✗
    #     （2026-10-03 实测踩到：假报 0.073 mm、假报“交叉” ✓）。
    bz = re.search(r'<bezier>(.*?)</bezier>', body, re.S)
    bez = None
    if bz:
        c0 = re.search(r'<cp0\b([^>]*)/?>', bz.group(1))
        c1 = re.search(r'<cp1\b([^>]*)/?>', bz.group(1))
        if c0 and c1:
            def _p(s):
                return (float((re.search(r'\bx="([-\d.eE+]+)"', s) or [None, 0])[1]),
                        float((re.search(r'\by="([-\d.eE+]+)"', s) or [None, 0])[1]))
            bez = (_p(c0.group(1)), _p(c1.group(1)))
    return dict(layer=lay, geo=geo, ends=ends, bezier=bez,
                mils=float(we.group(1)) if we else None)


def curve_pts(geo, bezier, n=24):
    """走线的**真实路径** ✓ ⇒ 采样点表（绝对坐标 ✓）

    · `bezier is None` ⇒ 直线 ✓（就两点 ✓）；
    · 否则三次贝塞尔 ✓：`p0` = `(x+x1, y+y1)` ✓、`p3` = `(x+x2, y+y2)` ✓、
      控制点 = `loc + cp0` / `loc + cp1` ✓（与 `x1..y2` 同一局部系 ✓ —— 源码口径见 `parse_trace` ✓）。
    """
    x, y = float(geo.get("x", 0)), float(geo.get("y", 0))
    p0 = (x + float(geo.get("x1", 0)), y + float(geo.get("y1", 0)))
    p3 = (x + float(geo.get("x2", 0)), y + float(geo.get("y2", 0)))
    if not bezier:
        return [p0, p3]
    c0 = (x + bezier[0][0], y + bezier[0][1])
    c1 = (x + bezier[1][0], y + bezier[1][1])
    out = []
    for i in range(n + 1):
        t = i / float(n)
        u = 1.0 - t
        out.append((u * u * u * p0[0] + 3 * u * u * t * c0[0] + 3 * u * t * t * c1[0] + t * t * t * p3[0],
                    u * u * u * p0[1] + 3 * u * u * t * c0[1] + 3 * u * t * t * c1[1] + t * t * t * p3[1]))
    return out


def abs_ends(geo):
    """绝对端点 ✓：`(x,y)` 是 loc ✓、`x1..y2` 是**相对偏移** ✓"""
    x, y = float(geo.get("x", 0)), float(geo.get("y", 0))
    return ((x + float(geo.get("x1", 0)), y + float(geo.get("y1", 0))),
            (x + float(geo.get("x2", 0)), y + float(geo.get("y2", 0))))


def read(path):
    """读一份 sketch ⇒ `(text, [(indent, block)], 包内文件名 ✓)`"""
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".fz")][0]
    return z.read(name).decode("utf-8"), name


def board_rect(text):
    """板框（sketch 单位矩形 ✓）：`<board width height>` ＋ `PCB1` 实例的 loc ✓；缺 ⇒ None ✓

    ★ 板框 = 矩形 PCB 模块 ✓（`TwoLayerRectanglePCBModuleID`）：`width/height` 是**物理尺寸** ✓、
      实例的 `(x, y)` 是**左上角** ✓ ⇒ 矩形 = `(x, y) - (x + w, y + h)` ✓。
    """
    m = re.search(r'<board\b([^>]*)>', text)
    if not m:
        return None
    a = dict(re.findall(r'([\w]+)="([^"]*)"', m.group(1)))

    def to_u(v):
        m2 = re.match(r"([-\d.]+)\s*(cm|mm|in)?", v or "")
        if not m2:
            return None
        k = {"cm": 10.0 / SK, "mm": 1.0 / SK, "in": 25.4 / SK, None: 0.0}[m2.group(2)]
        return float(m2.group(1)) * k if k else None
    w, h = to_u(a.get("width")), to_u(a.get("height"))
    loc = None
    for _ind, b in blocks(text):
        if "TwoLayerRectanglePCBModuleID" not in b:
            continue
        g = re.search(r'<pcbView[^>]*>\s*<geometry ([^>]*)/>', b)
        if g:
            gd = dict(re.findall(r'([\w]+)="([^"]*)"', g.group(1)))
            loc = (float(gd.get("x", 0)), float(gd.get("y", 0)))
        break
    if not w or not h or not loc:
        return None
    return (loc[0], loc[1], loc[0] + w, loc[1] + h)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    path = argv[0]
    text, name = read(path)
    print("== %s（包内 %s，%d 字符）==" % (os.path.basename(path), name, len(text)))
    bs = blocks(text)
    wires = [(i, b) for i, b in bs if "WireModuleID" in b]
    vias = [(i, b) for i, b in bs if "ViaModuleID" in b]
    print("   `<instance>` 共 %d 个；其中 Wire %d ✓ / Via %d ✓" % (len(bs), len(wires), len(vias)))

    if "--roundtrip" in argv:
        bad_all, bad_num = [], 0
        for ind, b in bs:
            nb, diff = rewrite_nums(b)
            if nb != b:
                bad_all.append((ind, b[:60].replace("\n", " "), diff[:4]))
                bad_num += len(diff)
        print("\n== 数字格式回写自检（口径 `%.6g`）==")
        print("   逐字节相同的实例：%d / %d %s" % (len(bs) - len(bad_all), len(bs),
                                              "✓" if not bad_all else "✗"))
        for ind, head, diff in bad_all[:6]:
            print("   ✗ %s…  差异 %s" % (head, diff))
        if bad_all:
            print("   ✗ 共 %d 个实例、%d 个数字对不上 ⇒ **格式口径要改** ✗" % (len(bad_all), bad_num))

    if "--dump" in argv:
        print("\n== PCB 走线 / 过孔 ==")
        tot = 0.0
        by_lay = {}
        on_pad = on_wire = other = 0
        n_trace = 0
        for _i, b in wires:
            t = parse_trace(b)
            if t is None:                    # ★ 只有面包板/原理图视图的线 ⇒ **不算 PCB 走线** ✗
                continue
            n_trace += 1
            (ax, ay), (bx, by) = abs_ends(t["geo"])
            tot += ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
            by_lay[t["layer"]] = by_lay.get(t["layer"], 0) + 1
            for i in (0, 1):
                for cid, mid, lay in t["ends"].get(i, []):
                    if lay in ("copper0", "copper1"):
                        on_pad += 1
                    elif lay.endswith("trace"):
                        on_wire += 1
                    else:
                        other += 1
        print("   走线 %d 条（%s）｜总长 %.2f 单位 = %.1f mm（另 %d 条 Wire 只有面包板/原理图视图 ⇒ 不算 ✓）"
              % (n_trace, "、".join("%s %d" % kv for kv in sorted(by_lay.items())),
                 tot, tot * SK, len(wires) - n_trace))
        print("   端点归属：**落在零件焊盘** %d ✓ / 落在别的走线 %d / 其它 %d"
              % (on_pad, on_wire, other))
        print("   过孔 %d 个 ✓" % len(vias))
        r = board_rect(text)
        if r:
            inside = outside = 0
            for _i, b in wires:
                t = parse_trace(b)
                if t is None:
                    continue
                for p in abs_ends(t["geo"]):
                    if r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]:
                        inside += 1
                    else:
                        outside += 1
            print("   板框 = (%.2f, %.2f)-(%.2f, %.2f) mm｜走线端点在板内 %d ✓ / **在板外 %d**"
                  % (r[0] * SK, r[1] * SK, r[2] * SK, r[3] * SK, inside, outside))
            if inside == 0 and outside:
                print("   ⇒ ⚠️ **这条也没画在板上** ✗：走线坐标是从面包板搬过来的（Fritzing 会同步两视图坐标 ✓）")
        else:
            print("   板框：读不出（没找到 `<board>` 或 PCB1 的 loc ✗）")
        samples = ([b for _i, b in wires if parse_trace(b) is not None][:3]
                   + [b for _i, b in vias[:2]])
        for b in samples:
            isvia = "ViaModuleID" in b
            if isvia:
                m = re.search(r'<pcbView\b[^>]*?\blayer="([\w]+)"[^>]*>\s*<geometry ([^>]*)/>', b)
                a = dict(re.findall(r'([\w]+)="([^"]*)"', m.group(2)))
                print("   [过孔] %-30s 在 (%.3f, %.3f) sketch 单位 = (%.2f, %.2f) mm"
                      % (m.group(1), float(a.get("x", 0)), float(a.get("y", 0)),
                         float(a.get("x", 0)) * SK, float(a.get("y", 0)) * SK))
            else:
                t = parse_trace(b)
                (ax, ay), (bx, by) = abs_ends(t["geo"])
                e0 = t["ends"].get(0) or t["ends"].get(1) or []
                print("   [走线] %-14s (%.2f,%.2f)→(%.2f,%.2f) mm  端点接：%s"
                      % (t["layer"], ax * SK, ay * SK, bx * SK, by * SK,
                         "; ".join("%s#%s" % (c, l) for c, _m, l in e0) or "（无 ✓ 悬空）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
