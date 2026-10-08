# -*- coding: utf-8 -*-
r"""★★ 弯线（三次贝塞尔走线）对账 ✓：`.fzz` ⇔ Fritzing 导出 ⇔ 我们渲的图（2026-10-08 立）

为什么有它 ✗：PCB 走线的**真形状**不在 `<geometry>` 里 ✓ —— 它在同级的
`<wireExtras><bezier><cp0/><cp1/></bezier></wireExtras>` ✓（见 `pcb_wire.ctrl_pts()` ✓）。
2026-10-08 的 bug 就是**渲染器只读端点** ✗ ⇒ 弧被拉直 ✗（v59 的 `5V/GND` `24 mil` 电源线 ✓，
沿弧最大偏离弦 ≈**2.5 mm** ✗ ⇒ 一眼可见 ✓；用户原话：「v59 里的 5V 和 GND 24mil 线」✗）。
⇒ 本工具把"**照弧画了吗**"变成机器判据 ✓（✗ 不靠人眼比对两张图 ✗ = 本仓 F14 的纪律 ✓）。

判据（三条 ✓，任一不过 ⇒ 退出码 1 ✓）：
  ① **条数** ✓：文件里带 `<bezier>` 的走线数 == 导出里"同色同宽"的弯 `path` 数 ✓；
  ② **形状** ✓（**平移无关** ✓）：把每条弯线的 `p0/c0/c1/p3` 化成"相对 `p0` 的 mm 偏移" ✓
     ⇒ 与导出逐点比，最大差 ≤ `--tol`（默认 0.01 mm ✓）。
     ★ 为什么必须去掉平移 ✗：导出那份是**另开的页面** ✓，页面原点**不是**板框左上角 ✓
     （实测按"板框在页原点"读会整体错位 ✓）⇒ 平移无关才站得住 ✓。
  ③ **我们的图** ✓（给了 `--ours=<svg>` 时 ✓）：弯 `path` 条数 == 文件里的弯线数 ✓
     （✗ 少了 = 又有人把弧过滤掉了 ✗）、且形状也要过判据 ② ✓。
     ★ 我们 svg 是 px ✓ ⇒ 靠**板框 rect** 定标回 sketch 单位 ✓（✗ 不复算渲染器的内部公式 ✗）。

用法 ✓：
  py tools\pcb_curve_check.py <sketch.fzz> <fritzing.svg>                   # ① ②
  py tools\pcb_curve_check.py <sketch.fzz> <fritzing.svg> --ours=out.svg    # ① ② ③
  （导出 = `Fritzing.exe -svg <目录>` 的产物 `<名>_pcb.svg` ✓ —— 别拿屏幕截图 ✗：
    屏幕会按层给件改色 + 画鼠线 ✓，见 `docs/fritzing-sketch-format-notes.md` ✓）

★ 单文件里一条弯线都没有 ⇒ 报"没有弯线 ✓"、退出 0 ✓（判据不适用 ✓，不是通过 ✓）。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcb_check as PC                                             # noqa: E402
import pcb_wire as PW                                              # noqa: E402

EXP_MM = 0.0254                      # 导出 1 单位 = 1/1000 in ✓
NUM = r"(-?[\d.]+)[,\s]+(-?[\d.]+)"


def shapes_of_file(fzz):
    """`.fzz` ⇒ `[(层, mils, [相对 p0 的三个 (mm)])]` ✓（只列带 `<bezier>` 的 ✓）"""
    text, _n = PW.read(fzz)
    out = []
    for _i, b in PW.blocks(text):
        m = re.search(r'moduleIdRef="([^"]+)"', b)
        if not m or not m.group(1).startswith("Wire"):
            continue
        t = PW.parse_trace(b)
        if not (t and t.get("bezier")):
            continue
        x, y = float(t["geo"].get("x", 0)), float(t["geo"].get("y", 0))
        c0, c1 = PW.ctrl_pts(t["geo"], t["bezier"])
        pts = [(x + float(t["geo"].get("x1", 0)), y + float(t["geo"].get("y1", 0))),
               c0, c1, (x + float(t["geo"].get("x2", 0)), y + float(t["geo"].get("y2", 0)))]
        p0 = pts[0]
        lay = t["layer"][:-5] if t["layer"].endswith("trace") else t["layer"]   # `copper0trace` ⇒ `copper0` ✓
        out.append((lay, t["mils"],
                    [((p[0] - p0[0]) * PW.SK, (p[1] - p0[1]) * PW.SK) for p in pts[1:]]))
    return out


def shapes_of_export(svg_text):
    """Fritzing 导出 ⇒ `[(颜色, mils, [相对 p0 的三个 (mm)])]` ✓（只列带 `C` 的 `path` ✓）"""
    out = []
    pat = re.compile(r'<path d="M%sC%s,?\s*%s,?\s*%s"[^>]*stroke="(#\w+)"[^>]*'
                     r'stroke-width="([\d.]+)"' % (NUM, NUM, NUM, NUM))
    for m in pat.finditer(svg_text):
        g = [float(v) for v in m.groups()[:8]]
        pts = [(g[0], g[1]), (g[2], g[3]), (g[4], g[5]), (g[6], g[7])]
        p0 = pts[0]
        out.append((m.group(9).lower(), float(m.group(10)),
                    [((p[0] - p0[0]) * EXP_MM, (p[1] - p0[1]) * EXP_MM) for p in pts[1:]]))
    return out


LAYER_COLOR = {"copper0": "#f28a00", "copper1": "#f2c600"}


def key_of(layer, mils, color=None):
    """配对键 ✓：层（导出按颜色认 ✓）× 线宽 ✓"""
    return (LAYER_COLOR.get(layer, color), round(float(mils or 0), 3))


def maxdiff(a, b):
    return max(abs(p[0] - q[0]) for p, q in zip(a, b)) if a and b else 9e9


def shapes_of_ours(svg_text, fzz, tol):
    """我们渲的 svg ⇒ `[(颜色, mils, 形状 mm)]` ✓（px ⇒ sketch 单位靠板框 rect 定标 ✓）"""
    bd = PC.collect(fzz)["board"]
    if not bd:
        raise SystemExit("读不出板框 ✗ ⇒ 没法给我们自己的图定标 ✗")
    m = re.search(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)" '
                  r'fill="#ffffff" fill-opacity="[\d.]+" stroke="#111111"', svg_text)
    if not m:
        raise SystemExit("我们自己的图里找不到板框 rect ✗（✗ 是不是用了 `--board-only` 之外的画法 ✗）")
    rx, ry, rw, rh = [float(v) for v in m.groups()]
    bw, bh = bd[2] - bd[0], bd[3] - bd[1]
    # ★★ 先判"这个 rect 是不是**真板框**"✗：不带 `--board-only` 渲时，`render_pcb` 会把
    #   视口**胀成「板框 ∪ 全部墨迹」** ✓ ⇒ 画出来的是**取景框** ✗ ⇒ 拿它定标会差 ~1% ✓
    #   （2026-10-08 实测踩到 ✓）。判据 = **宽高比**：真板框的比 = 板自己的比 ✓。
    if abs((rw / max(rh, 1e-9)) / (bw / max(bh, 1e-9)) - 1.0) > 0.0015:
        raise SystemExit("✗ 这张图里的板框 rect 宽高比 %.4f ≠ 板的 %.4f ⇒ 它多半是**取景框** ✗"
                         "（请用 `--board-only` 重渲 `--ours` 那张 ✓）"
                         % (rw / max(rh, 1e-9), bw / max(bh, 1e-9)))
    kx, ky = rw / bw, rh / bh
    out = []
    pat = re.compile(r'<path d="M%s C%s %s %s"[^>]*fill="none" stroke="(#\w+)" '
                     r'stroke-width="([\d.]+)"' % (NUM, NUM, NUM, NUM))
    for m in pat.finditer(svg_text):
        g = [float(v) for v in m.groups()[:8]]
        pts = [((g[0] / kx + bd[0]) * PW.SK, (g[1] / ky + bd[1]) * PW.SK),
               ((g[2] / kx + bd[0]) * PW.SK, (g[3] / ky + bd[1]) * PW.SK),
               ((g[4] / kx + bd[0]) * PW.SK, (g[5] / ky + bd[1]) * PW.SK),
               ((g[6] / kx + bd[0]) * PW.SK, (g[7] / ky + bd[1]) * PW.SK)]
        p0 = pts[0]
        out.append((m.group(9).lower(), None,
                    [((p[0] - p0[0]), (p[1] - p0[1])) for p in pts[1:]]))
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opt = dict((a.split("=", 1)[0].lstrip("-"), a.split("=", 1)[1])
               for a in argv if a.startswith("--") and "=" in a)
    if len(args) < 2:
        print(__doc__)
        return 2
    fzz, exp_svg = args[0], args[1]
    tol = float(opt.get("tol", 0.01))
    ours_path = opt.get("ours")

    fz = shapes_of_file(fzz)
    ex = shapes_of_export(open(exp_svg, encoding="utf-8").read())
    print("%s：文件里弯线 **%d** 条；导出里弯 `path` **%d** 条（+ 线宽 %s ✓）"
          % (os.path.basename(fzz), len(fz), len(ex),
             sorted({e[1] for e in ex})))
    if not fz:
        print("✓ 这份草图里**一条弯线都没有** ⇒ 判据不适用 ✓（★ 这不算「通过」✗）")
        return 0

    bad = 0
    print("\n%-9s %-7s | %-34s | %-34s | 差 mm" % ("层", "mils", "文件（相对 p0，mm）", "导出（mm）"))
    print("-" * 104)
    for lay, mils, sh in sorted(fz, key=lambda q: (q[0], q[2][2][0])):
        k = key_of(lay, mils)
        cand = [(at, e) for at, e in ((maxdiff(sh, e[2]), e) for e in ex)
                if key_of(None, e[1], e[0]) == k]
        if not cand:
            print("%-9s %-7s | ✗ 导出里找不到「同色同宽」的弯 path ✗" % (lay, mils))
            bad += 1
            continue
        d, e = min(cand)
        print("%-9s %-7s | %-34s | %-34s | %.6f"
              % (lay, mils,
                 " ".join("(%.4f,%.4f)" % q for q in sh),
                 " ".join("(%.4f,%.4f)" % q for q in e[2]), d))
        if d > tol:
            print("          ✗ 形状差 %.4f mm > 容差 %.4f ✗" % (d, tol))
            bad += 1

    if ours_path:
        txt = open(ours_path, encoding="utf-8").read()
        got = shapes_of_ours(txt, fzz, tol)
        print("\n我们渲的图（%s）：弯 `path` **%d** 条"
              % (os.path.basename(ours_path), len(got)))
        if len(got) != len(fz):
            print("  ✗ 条数不对：文件 %d 条 vs 我们 %d 条 ⇒ **有弧被拉成直弦了** ✗"
                  % (len(fz), len(got)))
            bad += 1
        for color, _mils, sh in sorted(got, key=lambda q: q[2][2][0]):
            d = min((maxdiff(sh, e[2]) for e in ex if e[0] == color), default=9e9)
            print("   %-8s 形状 %-34s vs 导出 差 %.6f mm"
                  % (color, " ".join("(%.4f,%.4f)" % q for q in sh), d))
            if d > tol:
                print("          ✗ 形状对不上 ✗")
                bad += 1

    print("\n%s" % ("✗ %d 项不过 ✗" % bad if bad else "✓ 全过：弧就是那条弧 ✓（形状差 ≤ %.3f mm ✓）" % tol))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
