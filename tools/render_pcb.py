# -*- coding: utf-8 -*-
r"""把 sketch 的 **pcbView** 画成预览图 ✓（2026-09-30 立）

为什么：PCB 的东西全是坐标和数字 ✓，但**人要看图**才能一眼判断"对不对/美不美" ✓
（同 AGENTS §9 图文并茂 ✓）。它也是每版摆位/布线给用户过目的那张图 ✓。

画什么 ✓（只画**有电学意义**的东西 ✓ + 板框 ✓）：
  · 板框（矩形 PCB 模块 ✓）
  · 焊盘：按 `pcb_pads` 读出的**绝对矩形** ✓，**顶层 `copper1` 红 / 底层 `copper0` 蓝** ✓
    （★ 颜色分工按 Fritzing 的 PCB 惯例 ✓：红 = 顶层 ✓）
  · 走线：`pcb_wire` 读出的绝对端点 ✓，**同色分两层** ✓
  · 过孔：绿点 ✓
  · 位号：写在它的焊盘**重心**上 ✓（旁边不留白也看得懂 ✓）
★ 几何**一律来自 `pcb_check.collect()`** ✓（= 校验器同一个世界模型 ✓，**不另算一套** ✗）

用法：
  py -3.13 tools\render_pcb.py <sketch.fzz> <out.svg> [--px 12] [--png]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcb_check as PC                                            # noqa: E402
import pcb_wire as PW                                             # noqa: E402

C_TOP, C_BOT = "#d02020", "#2040d0"        # copper1 = 顶层（红 ✓）/ copper0 = 底层（蓝 ✓）
C_VIA, C_BRD, C_TXT = "#118011", "#7a9a7a", "#333333"
_OPTS = [set()]                            # `render()` 的开关 ✓（给 bbox 那段判 `--board-only` ✓）


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(model, px_per_mm=12.0, opts=()):
    """⇒ svg 文本 ✓（`opts` 里给 `--board-only` ⇒ 只按板框开视口 ✓）"""
    _OPTS[0] = set(opts)
    k = px_per_mm / PW.SK                    # sketch 单位 → px ✓
    xs, ys = [], []
    for q in model["pads"]:
        xs += [q["box"][0], q["box"][2]]
        ys += [q["box"][1], q["box"][3]]
    for t in model["traces"]:
        xs += [t["a"][0], t["b"][0]]
        ys += [t["a"][1], t["b"][1]]
    for v in model["vias"]:
        xs.append(v["p"][0])
        ys.append(v["p"][1])
    r = model["board"] or (min(xs), min(ys), max(xs), max(ys))
    if "--board-only" not in _OPTS[0] and xs:
        # ★★ 视口 = **板框 ∪ 所有焊盘/走线/过孔** ✓（2026-09-30 修 ✗）：
        #   第一版只按**板框**开视口 ✗ ⇒ 落在板外的件**画不出来** ✗ —— 而"件不在板上"
        #   恰恰是**基线最该看见**的事 ✓（Fritzing 新建的 pcbView 里，件的默认位置
        #   离板很远 ✓）⇒ 必须都装进来 ✓，板框在里面**小一点**才对 ✓。
        r = (min(r[0], min(xs)), min(r[1], min(ys)), max(r[2], max(xs)), max(r[3], max(ys)))
    pad = 3.0                                            # 3 sketch 单位留白 ✓
    x0, y0 = r[0] - pad, r[1] - pad
    W, H = (r[2] - r[0] + 2 * pad) * k, (r[3] - r[1] + 2 * pad) * k

    def X(u):
        return (u - x0) * k

    def Y(v):
        return (v - y0) * k

    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" '
         'viewBox="0 0 %.1f %.1f">' % (W, H, W, H),
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#eef6ee" '
         'stroke="%s" stroke-width="1.2"/>'
         % (X(r[0]), Y(r[1]), (r[2] - r[0]) * k, (r[3] - r[1]) * k, C_BRD)]
    # 走线（先画线、后画盘 ✓，盘压线 ✓）
    for t in model["traces"]:
        c = C_TOP if t["layer"] == "copper1" else C_BOT
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                 'stroke-width="%.2f" stroke-linecap="round"/>'
                 % (X(t["a"][0]), Y(t["a"][1]), X(t["b"][0]), Y(t["b"][1]), c, 0.25 * k))
    for q in model["pads"]:
        c = C_TOP if q["layer"] in ("copper1", "both") else C_BOT
        o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                 'fill-opacity="0.85" stroke="%s" stroke-width="0.4"/>'
                 % (X(q["box"][0]), Y(q["box"][1]),
                    max(1.0, (q["box"][2] - q["box"][0]) * k),
                    max(1.0, (q["box"][3] - q["box"][1]) * k), c, c))
    for v in model["vias"]:
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                 % (X(v["p"][0]), Y(v["p"][1]), 0.35 * k, C_VIA))
    # 位号（焊盘重心 ✓）
    per = {}
    for q in model["pads"]:
        per.setdefault(q["title"], []).append(q)
    for ttl, qs in sorted(per.items()):
        cx = sum((q["box"][0] + q["box"][2]) / 2.0 for q in qs) / len(qs)
        cy = sum((q["box"][1] + q["box"][3]) / 2.0 for q in qs) / len(qs)
        o.append('<text x="%.2f" y="%.2f" font-family="DroidSans, sans-serif" '
                 'font-size="%.1f" font-weight="bold" fill="%s" text-anchor="middle">%s</text>'
                 % (X(cx), Y(cy) + 3.2, max(8.0, 1.3 * k), C_TXT, esc(ttl)))
    o.append('</svg>')
    return "\n".join(o)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    fzz, out = argv[0], argv[1]
    px = 12.0
    for i, a in enumerate(argv):
        if a == "--px" and i + 1 < len(argv):
            px = float(argv[i + 1])
    model = PC.collect(fzz)
    svg = render(model, px, [a for a in argv if a.startswith("--board-only")])
    open(out, "w", encoding="utf-8", newline="\n").write(svg)
    print("✓ 写出 %s（%d 字节）：焊盘 %d / 走线 %d / 过孔 %d / 板框 %s"
          % (out, len(svg), len(model["pads"]), len(model["traces"]), len(model["vias"]),
             ("%.2f×%.2f mm" % ((model["board"][2] - model["board"][0]) * PW.SK,
                                (model["board"][3] - model["board"][1]) * PW.SK))
             if model["board"] else "读不出 ✗"))
    if "--png" in argv:
        try:
            import cairosvg
        except ImportError:
            print("（没装 cairosvg ⇒ 只出 svg ✓）")
            return 0
        png = os.path.splitext(out)[0] + ".png"
        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=png, scale=1.0,
                         background_color="white")
        print("✓ 写出 %s" % png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
