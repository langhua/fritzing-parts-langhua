# -*- coding: utf-8 -*-
r"""把 sketch 的 **pcbView** 画成预览图 ✓（2026-09-30 立）

为什么：PCB 的东西全是坐标和数字 ✓，但**人要看图**才能一眼判断"对不对/美不美" ✓
（同 AGENTS §9 图文并茂 ✓）。它也是每版摆位/布线给用户过目的那张图 ✓。

画什么 ✓（只画**有电学/装配意义**的东西 ✓ + 板框 ✓）：
  · 板框（矩形 PCB 模块 ✓）
  · 焊盘：按 `pcb_pads` 读出的**绝对矩形** ✓，**顶层 `copper1` 红 / 底层 `copper0` 蓝** ✓
    （★ 颜色分工按 Fritzing 的 PCB 惯例 ✓：红 = 顶层 ✓）
  · ★★ **件自己的铜箔原文** ✓（含线圈那 700 多条绕组 ✓）—— **不**只画焊盘 ✗
  · ★★ **丝印** ✓（`<g id="silkscreen">` 原文 ✓）—— 2026-09-30 用户点名补 ✗：
    「渲染器不画孔/丝印，我觉得是错误的，应该画上才是」✓ —— 不画就看不出来
    "丝印有没有出板 / 压到孔"✗（而那正是摆位最常错的两种 ✗）。
  · ★★ **安装孔**（核心 `HoleModuleID` 的**钻孔圆** ✓）—— 同上 ✓；孔心按
    `pcb_pads.HOLE_DRAW_OFF_MM` 换算 ✓（`<geometry>` **不是**孔心 ✗）。
  · 走线：`pcb_wire` 读出的绝对端点 ✓，**同色分两层** ✓
  · 过孔：绿点 ✓
  · 位号：写在它的焊盘**重心**上 ✓（旁边不留白也看得懂 ✓）
★ 几何**一律来自 `pcb_check.collect()`** ✓（= 校验器同一个世界模型 ✓，**不另算一套** ✗）

用法：
  py -3.13 tools\render_pcb.py <sketch.fzz> <out.svg> [--px 12] [--png]
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import part_box as PB                                             # noqa: E402
import pcb_check as PC                                            # noqa: E402
import pcb_pads as PP                                             # noqa: E402
import pcb_wire as PW                                             # noqa: E402

C_TOP, C_BOT = "#d02020", "#2040d0"        # copper1 = 顶层（红 ✓）/ copper0 = 底层（蓝 ✓）
C_VIA, C_TXT = "#118011", "#333333"
C_BRD_FILL, C_BRD_EDGE = "#d9d9d9", "#333333"   # ★ 板画成**灰色** ✓
# ★★ 丝印（2026-09-30 用户点名补 ✗）—— 两层问题：
#   ① 件 svg 里丝印写死了 `stroke="#f0f0f0"` ✗（近白 ✓）—— 那是给**深色板**配的 ✓，
#      而本预览的板是**浅灰** ✗ ⇒ **一个字也看不见** ✗（实测：画了 9 块，图上一片空 ✗）；
#   ② 件里那个颜色是**自己的属性** ✗ ⇒ 在父组上写 fill/stroke **盖不住** ✗
#      ⇒ 必须**逐个改**（`repaint_silk` ✓）。
#   取值：深灰 ✓（浅灰板上看得清 ✓）—— **不为好看，只为看得见** ✓。
C_SILK = "#3f3f3f"
# ★★ 安装孔：孔 = **白圆 + 深描边** ✓（跟 Fritzing 导出的板一样：板白、边 `#111111` ✓）；
#   铜环只有 `hole size` 的外径 > 0 时才画 ✓（咱们的孔是 `2.2mm,0.0mm` ⇒ 无铜盘 ✓）。
C_HOLE_FILL, C_HOLE_EDGE, C_HOLE_RING = "#ffffff", "#111111", "#b8860b"
_OPTS = [set()]                            # `render()` 的开关 ✓（给 bbox 那段判 `--board-only` ✓）
_STATS = {}                                # `render()` 回的计数 ✓（给 `main` 报数用 ✓）


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def layer_inner(svg_text, layer):
    """把件 svg 里某一层（如 `copper0` / `silkscreen` ✓）的内容**原样**取出来 ✓

    ★ 为什么**原样**取 ✗：线圈那种件的铜箔是 **700 多条 path** ✓ —— 自己按包围盒画只会
      画成方块 ✗；照搬原文才和 Fritzing 画的一模一样 ✓。
    ★ 为什么**配平扫描**、不用非贪婪正则 ✗：组里还有嵌套 `<g>` ✓（AGENTS 里踩过：非贪婪
      会截到第一个 `</g>` ✗）。
    ★ 一件里可能有**多个同名层组**（`silkscreen` / `silkscreen0` ✓）⇒ 全都要 ✓。
    """
    out = []
    for m in re.finditer(r'<g\b[^>]*\bid="%s"[^>]*>' % re.escape(layer), svg_text):
        depth, i = 1, m.end()
        while i < len(svg_text) and depth:
            nxt = re.search(r"<(/?)g\b", svg_text[i:])
            if not nxt:
                break
            j = i + nxt.start()
            depth += -1 if nxt.group(1) else 1
            i = i + nxt.end()
            if depth == 0:
                out.append(svg_text[m.end():j])
                break
    return "".join(out)


def repaint_silk(xml, color):
    """把丝印原文里**自带的颜色**换成 `color` ✓（不改就看不见 ✗ —— 见 `C_SILK` 注释 ✓）

    ★ 只改**颜色值** ✓：`stroke="none"` / `fill="none"` **原样保留** ✓
      （那个是"这块不画"的意思 ✓，改了反而画出一个色块 ✗）。
    ★ 两种写法都要盖 ✗：属性式 `stroke="#…"` ✓ 与 内联式 `style="…stroke:#…"` ✓；
      注意 `stroke-width="…"` / `stroke-width:…` 不能被误伤 ✓（正则要求后面紧跟 `=` 或 `:` ✓）。
    """
    def rep(m):
        return m.group(0) if m.group(2).strip().lower() == "none" \
            else '%s="%s"' % (m.group(1), color)

    def rep2(m):
        return m.group(0) if m.group(2).strip().lower() == "none" \
            else '%s:%s' % (m.group(1), color)

    x = re.sub(r'\b(stroke|fill)\s*=\s*"([^"]*)"', rep, xml)
    return re.sub(r'\b(stroke|fill)\s*:\s*([a-zA-Z#0-9]+)', rep2, x)


def copper_inner(svg_text):
    """件 svg 里 **copper0 / copper1** 两组的内容 ✓（两层的画法一样 ✓）"""
    return "".join(layer_inner(svg_text, l) for l in ("copper0", "copper1"))


def holes_of(text):
    """⇒ `[(钻孔心 sketch 单位 ✓, 孔内径 mm ✓, 铜盘外径 mm ✓), …]` ✓（核心孔件 ✓）

    ★ 孔心 = **`<geometry>` + `pcb_pads.HOLE_DRAW_OFF_MM`** ✗ —— 把 `<geometry>` 当孔心 ✗
      会把孔画在离板边 **1.23 mm** 的地方 ✗（实测：用户导出的图里就是那样 ✗，见库里那条注释 ✓）。
    ★ 孔**不在** `model["parts"]` 里 ✗（它没有可解析的 fzp/svg ✓）⇒ 从 sketch 原文里找 ✓。
    """
    out = []
    for m in re.finditer(r'(?ms)<instance\b[^>]*?moduleIdRef="HoleModuleID".*?</instance>', text or ""):
        b = m.group(0)
        sz = re.search(r'name="hole size"\s+value="([^"]+)"', b)
        g = re.search(r'<pcbView\b[^>]*>\s*<geometry\s+([^>]*?)/>', b)
        if not (sz and g):
            continue
        nums = [float(v) for v in re.findall(r"([\d.]+)\s*mm", sz.group(1))]
        inner = nums[0] if nums else 2.2
        outer = nums[1] if len(nums) > 1 else 0.0
        a = dict(re.findall(r'([\w]+)="([^"]*)"', g.group(1)))
        out.append(((float(a.get("x", 0)) + PP.HOLE_DRAW_OFF_MM[0] * PB.MM,
                     float(a.get("y", 0)) + PP.HOLE_DRAW_OFF_MM[1] * PB.MM), inner, outer))
    return out


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
    for p in model.get("parts", []):          # ★ 件的**画布**也包进来 ✓（线圈的铜比它的盘大很多 ✗）
        if p.get("svg_text") is None or "loc" not in p:
            continue
        if (p.get("moduleId") or "").startswith(("Breadboard", "Via")):
            continue
        root = ET.fromstring(p["svg_text"])
        kk, _o = PB.svg_k(root)
        wmm, hmm = PB.canvas_mm(root.attrib)
        if kk and wmm and hmm:
            uv = PB._nums(root.get("viewBox"))
            if len(uv) == 4:
                for cu in (uv[0], uv[0] + uv[2]):
                    for cv in (uv[1], uv[1] + uv[3]):
                        q = PB.apply(p["M"], (cu - uv[0]) * kk, (cv - uv[1]) * kk)
                        xs.append(p["loc"][0] + q[0])
                        ys.append(p["loc"][1] + q[1])
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
         '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
         'stroke="%s" stroke-width="1.2"/>'
         % (X(r[0]), Y(r[1]), (r[2] - r[0]) * k, (r[3] - r[1]) * k, C_BRD_FILL, C_BRD_EDGE)]
    # ★★ 件的**铜箔原文**（含线圈 700 多条绕组 ✓）—— 2026-09-30 用户点名补 ✗：
    #   上一版只画焊盘 ✗ ⇒ 线圈看成一个空框 ✗，没法用眼看"压绕组" ✗。
    T = (k, 0.0, 0.0, k, -x0 * k, -y0 * k)                    # sketch → px ✓
    silk_layers, n_silk, n_parts = [], 0, 0
    for p in model.get("parts", []):
        if p.get("svg_text") is None or "loc" not in p:
            continue
        if (p.get("moduleId") or "").startswith(("Breadboard", "Via")):
            continue
        inner = copper_inner(p["svg_text"])
        root = ET.fromstring(p["svg_text"])
        kk, (ox, oy) = PB.svg_k(root)
        vb = PB._nums(root.get("viewBox"))
        vbw = vb[2] if len(vb) == 4 and vb[2] else None
        flip = ((p.get("pv") or {}).get("bottom") or "").lower() == "true" and vbw
        F = (-1.0, 0.0, 0.0, 1.0, 2.0 * ox + vbw, 0.0) if flip else (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        # ★★ 组合成**一个**矩阵：`T ∘ translate(loc) ∘ M ∘ C` ✓
        #   ✗ 原来是 `<g transform="translate(X(loc),Y(loc)) matrix(S)">` ✗，而 `S` 里的 `T`
        #     **已经含原点平移**（`−x0·k` ✓）⇒ **原点被减了两遍** ✗ ⇒ 整组被推到
        #     约 **−2800 px**（画布外 ✗）⇒ 线圈绕组/连接器本体/丝印**一个都画不出来** ✗
        #     （只有另算绝对坐标的**焊盘**能出来 ✓ —— 2026-09-30 用户说"不画孔/丝印"时暴露 ✓）。
        S = PB.mul(PB.mul(T, (1.0, 0.0, 0.0, 1.0, p["loc"][0], p["loc"][1])),
                   PB.mul(p["M"], PB.mul((kk, 0.0, 0.0, kk, -ox * kk, -oy * kk), F)))
        trans = 'matrix(%s)' % ",".join(PW.fmt(v) for v in S)
        if inner:
            o.append('<g transform="%s">%s</g>' % (trans, inner))
            n_parts += 1
        # ★★ 丝印也**原样**画一份 ✓（`silkscreen` / `silkscreen0` ✓）—— 先存着 ✓，
        #   等焊盘/走线都画完再上 ✓（丝印是**最后印**上去的 ✓，压在铜上是正常的 ✓）；
        #   颜色必须**逐元素改** ✗（件里写死近白的 `#f0f0f0` ✗ ⇒ 不改就看不见 ✗）。
        sk = repaint_silk(layer_inner(p["svg_text"], "silkscreen")
                          + layer_inner(p["svg_text"], "silkscreen0"), C_SILK)
        if sk:
            silk_layers.append('<g transform="%s">%s</g>' % (trans, sk))
            n_silk += 1
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
    # ★★ 丝印（压在铜/焊盘之上 ✓ —— 与 Fritzing 的层序一致 ✓）
    o += silk_layers
    # ★★ 安装孔：**钻孔圆** ✓（白 + 深边 ⇒ 一眼看出"这里是个洞"✓）；有铜盘才多画一个环 ✓
    holes = holes_of(model.get("text"))
    for (hx, hy), inner_mm, outer_mm in holes:
        if outer_mm > inner_mm:
            o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" '
                     'stroke-width="%.2f"/>'
                     % (X(hx), Y(hy), (inner_mm + outer_mm) / 4.0 * PB.MM * k,
                        C_HOLE_RING, (outer_mm - inner_mm) / 2.0 * PB.MM * k))
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" '
                 'stroke-width="%.2f"/>'
                 % (X(hx), Y(hy), inner_mm / 2.0 * PB.MM * k, C_HOLE_FILL, C_HOLE_EDGE,
                    max(0.8, 0.07 * k)))
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
    _STATS.update(pads=len(model["pads"]), traces=len(model["traces"]),
                  vias=len(model["vias"]), copper=n_parts, silk=n_silk, holes=len(holes))
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
    print("✓ 写出 %s（%d 字节）：焊盘 %d / 走线 %d / 过孔 %d / 铜箔块 %d / 丝印块 %d / 孔 %d / 板框 %s"
          % (out, len(svg), _STATS.get("pads", 0), _STATS.get("traces", 0),
             _STATS.get("vias", 0), _STATS.get("copper", 0), _STATS.get("silk", 0),
             _STATS.get("holes", 0),
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
