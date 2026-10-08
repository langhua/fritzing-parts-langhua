# -*- coding: utf-8 -*-
r"""把 sketch 的 **pcbView** 画成预览图 ✓（2026-09-30 立）

为什么：PCB 的东西全是坐标和数字 ✓，但**人要看图**才能一眼判断"对不对/美不美" ✓
（同 AGENTS §9 图文并茂 ✓）。它也是每版摆位/布线给用户过目的那张图 ✓。

画什么 ✓（只画**有电学/装配意义**的东西 ✓ + 板框 ✓）：
  · 板框（矩形 PCB 模块 ✓）
  · ★★ **只画件 svg 自己的铜箔原文** ✓（含线圈那 700 多条绕组 ✓）—— **不**另画焊盘 ✗
    （2026-10-01 用户定 ✓："Fritzing 里的画法我改不了，我只能看你两者是否一致" ✓
     ⇒ 额外叠的东西都会让两边不一样 ✗；确需时用 `--pad-marks` 找回来 ✓）
  · ★★ **丝印** ✓（`<g id="silkscreen">` 原文 ✓）—— 2026-09-30 用户点名补 ✗：
    「渲染器不画孔/丝印，我觉得是错误的，应该画上才是」✓ —— 不画就看不出来
    "丝印有没有出板 / 压到孔"✗（而那正是摆位最常错的两种 ✗）。
  · ★★ **安装孔**（核心 `HoleModuleID` 的**钻孔圆** ✓）—— 同上 ✓；孔心按
    `pcb_pads.HOLE_DRAW_OFF_MM` 换算 ✓（`<geometry>` **不是**孔心 ✗）。
  · 走线：`pcb_wire` 读出的绝对端点 ✓，**同色分两层** ✓，**线宽 = 实物** ✓
    （`wireExtras@mils` ✓ ⇒ 如 `12 mil` = 0.3048 mm ✓；没写的才回退 0.25 单位 ✓）
    ★★ **弯曲的走线照弧画** ✓（`<bezier><cp0/><cp1/>` ⇒ 三次贝塞尔 ✓，写法同 Fritzing 导出 ✓）
    —— 2026-10-08 用户对图指出 ✗：v59 的 `5V/GND` `24 mil` 粗线里 5 根是弧线 ✓，
    ✗ 旧版画成直弦 ✗ ⇒ 一眼就不一样 ✗。
  · ★★ 过孔：**照 Fritzing 自己导出的画法** ✓ —— **只有环** ✓（`fill="none"` ✓）
    （2026-10-01 二次修 ✗：先修掉了"实心绿点"✗，但我又自己加了个**白心孔**✗ ⇒
     Fritzing 环里是**透的**（透出焊盘铜 ✓）、我的是白点 ✗ ⇒ 同一个孔两种观感 ✗；
     现改为**只画环** ✓，要看得见的孔用 `--via-hole` ✓。几何按导出量出 ✓，见 `VIA_*` ✓）
  · 安装孔：同口径 ✓（`circle fill="black"` ✓ 一个黑盘 ✓，与 Fritzing 一致 ✓）
  · 位号：写在它的焊盘**重心**上 ✓（旁边不留白也看得懂 ✓）
★ 几何**一律来自 `pcb_check.collect()`** ✓（= 校验器同一个世界模型 ✓，**不另算一套** ✗）

用法：
  py -3.13 tools\render_pcb.py <sketch.fzz> <out.svg> [--px 12] [--png]

开关 ✓：
  `--board-only` 只按板框开视口 ✓；`--png` 同时出 png ✓；
  `--pad-marks` 额外叠焊盘方块（调试用 ✗）；`--via-hole` 额外画过孔白心（调试用 ✗）——
  ★ 这两个默认**关** ✓：开了就与 Fritzing 不一致 ✗。
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

# ★★ 铜层配色：**照 Fritzing 源码** ✓（2026-10-01 用户点名改 ✗：顶层黄 ✓ / 底层橘 ✓）
#   出处（可逐行核 ✓）：`fritzing-app/src/viewlayer.cpp` 开头那批常量 ——
#     `copper0`（底层 ✓）：面 `#f9a435`（`Copper0Color` ✓）／线 `#f28a00`（`Copper0WireColor` ✓）
#     `copper1`（顶层 ✓）：面 `#fdde68`（`Copper1Color` ✓）／线 `#f2c600`（`Copper1WireColor` ✓）
#   ★ 面与线是**两套值** ✗（不是一个色 ✓）⇒ 不能只写一个 ✓
#     （旁证 ✓：用户导出的 `pixel-pcb-v47_图示.svg` 里走线 75 条 `#f28a00` + 56 条 `#f2c600` ✓
#       —— 注明：我们 .fzz 里写的是**网色** ✗，Fritzing 渲染走线时按**层**盖掉了 ✓）
#   ★★ “件 svg 里画的是什么色”**不算数** ✓：Fritzing 载入件图时按层改色
#     （`src/items/itembase.cpp` `setUpImage()`：`loadInfo.setColor = Copper0Color / Copper1Color` ✓）
#     ⇒ 件里画成金 `#F7BD13` 也会被它盖成 `#f9a435` / `#fdde68` ✓
#     ⇒ 预览必须**照样改** ✗，否则“我画金、它画橘”两张图永远对不上 ✗。
#   ✗ 旧版自创的红/蓝（`#d02020` / `#2040d0`）已废 ✓ —— 那不是 Fritzing 的任何颜色 ✗。
C_CU0, C_CU1 = "#f9a435", "#fdde68"        # 面（焊盘 / 件铜箔）：底层橘 ✓ / 顶层黄 ✓
C_W0, C_W1 = "#f28a00", "#f2c600"          # 走线：底层橘 ✓ / 顶层黄 ✓
C_TXT = "#333333"
# ★★ 过孔怎么画 ✓（2026-10-01 量 **Fritzing 自己的导出**定死 ✓，不再自己发明 ✗）：
#   导出里每个过孔 = **两个同心圆**，`fill="none"`（= **环** ✗ 不是实心点 ✗）：
#     `<circle r="0.637795" stroke-width="0.425197"/>`
#   一个 `#f9a435`（copper0 底层 ✓）、一个 `#fdde68`（copper1 顶层 ✓）—— **同心、半径相同** ✓
#   ⇒ 1 导出单位 = 0.35277778 mm ✓ ⇒ 中心线半径 **0.225 mm**、环宽 **0.15 mm** ✓
#   ⇒ 孔内径 **0.30 mm**、铜盘外径 **0.60 mm** ✓ —— 正好对上 .fzz 里的 `hole size="0.3mm,0.15mm"` ✓
#   ⇒ **口径 = `<孔直径>,<环宽>`** ✓（内径/外径都能被 Fritzing 的画法反算出来 ✓）
#   ★ 量法/证据：18 个过孔 ×2 层 = 36 个圆，**两层圆心偏差 0.0001 mm**（= 同心 ✓），
#     且 36 个圆相对 .fzz `<geometry>` 点的偏移**投票 36/36 一致** ⇒ 圆心就在声明点上 ✓。
C_VIA_BOT, C_VIA_TOP = "#f9a435", "#fdde68"
VIA_HOLE_MM, VIA_RING_MM = 0.30, 0.15      # 兜底值 ✓（件若没写 `hole size` 才用 ✓）
# ★★ 板框：**照 Fritzing 导出** ✓（2026-10-01 改 ✗）：它画的是 `fill="#ffffff"` +
#   `fill-opacity="0.5"` + `stroke="#111111"` ✓；✗ 我以前画**灰底**（`#d9d9d9`）✗
#   ⇒ 两图底色就不一样 ✗（用户逐张对图时一眼可见 ✓）。
C_BRD_FILL, C_BRD_EDGE, C_BRD_FILL_OP = "#ffffff", "#111111", "0.5"
# ★★ 丝印色：**跟官方一致** ✓（2026-10-01 用户定 ✗：「丝印色跟官方一致吧」✓）
#   出处（同 `viewlayer.cpp` ✓）：`Silkscreen1Color = "#000000"`（顶层 ✓）、
#     `Silkscreen0Color = "#444444"`（底层 ✓）✓
#   ⇒ 与铜层**同一套“按所在面”口径** ✓：背面件的 `silkscreen`（件里写的顶层丝印 ✓）
#     落在**板子的底层** ✓ ⇒ 取 `#444444` ✓（对调 ✓ —— 与 `pcb_pads.part_shapes` 同一条规矩 ✗）。
#   ★ 为什么必须自己改色 ✗（2026-09-30 踩过 ✓）：件 svg 里丝印写死 `stroke="#f0f0f0"`（近白 ✗）
#     —— 那是给**深色板**配的 ✓ ⇒ 在本预览的**浅色板**上**一个字也看不见** ✗；
#     而且那是**元素自己的属性** ✗ ⇒ 在父组上写 fill/stroke 盖不住 ✗ ⇒ 只能逐个改 ✓。
C_SK0, C_SK1 = "#444444", "#000000"        # 丝印：底层 `#444444` ✓ / 顶层 `#000000` ✓
# ★★ 安装孔：**照 Fritzing 的画法** ✓ —— 它导出里就是一个 `circle fill="black" stroke="#f9a435" sw="0"` ✓
#   ✗ 我以前画"白圆 + 深边" ✗ ⇒ 与 Fritzing 看着就不一样 ✗（用户 2026-10-01：
#     "Fritzing 里的画法我改不了，我只能看你两者是否一致" ✓）。
#   `hole size` 的外径 > 内径 时它才多一层铜环 ✓（咱们的孔是 `2.2mm,0.0mm` ⇒ 没铜环 ✓）。
C_HOLE_FILL, C_HOLE_EDGE, C_HOLE_RING = "#000000", "none", "#b8860b"
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
    ★★ 2026-10-01 修 ✗：**层组自己的属性也要带上** ✗ —— ✗ 旧版只返回组**里面**的内容 ✗
      ⇒ 若颜色是写在层组上的（如 `<g id="copper0" fill="#F7BD13">` ✗），**继承链就断了** ✗
      ⇒ 那些焊盘在预览里**没有填充**（发黑 ✗），而 Fritzing 导出里是对的 ✓
      （实测：`U1` 的 21 块焊盘在我这边丢了 `#F7BD13` ✗）。
    """
    out = []
    for m in re.finditer(r'<g\b[^>]*\bid="%s"[^>]*>' % re.escape(layer), svg_text):
        # ★ 自闭合的空层（`<g id="copper1"/>` ✓）⇒ **跳过** ✗
        #   ✗ 不跳会出两个 bug ✗（2026-10-01 实测：整个 svg 变成"标签不配平" ✗）：
        #     ① 配平扫描会去找那个**不存在的** `</g>` ✗ ⇒ 一路吞到文件尾 ✗；
        #     ② 属性里会剩一个 `/` ✗ ⇒ 包出来变成 `<g />` ✗。
        if m.group(0).rstrip().endswith("/>"):
            continue
        # 把层组自己的属性（去掉 `id` ✓、去掉可能残留的 `/` ✓）原样带上 ✓ ⇒ 继承的 fill/stroke 不丢 ✓
        extra = re.sub(r'\s*\bid\s*=\s*"[^"]*"', '', m.group(0)[2:-1]).strip().rstrip("/").strip()
        depth, i = 1, m.end()
        while i < len(svg_text) and depth:
            nxt = re.search(r"<(/?)g\b", svg_text[i:])
            if not nxt:
                break
            j = i + nxt.start()
            if nxt.group(1):
                depth -= 1
            else:
                # ★★ **自闭合的 `<g ... />` 不占层级** ✗✓（2026-10-01 修 ✗，用户报「U1 看不见」✓）：
                #   ✗ 旧扫描见 `<g` 就 +1 ✗ ⇒ 遇到 `<g id="copper0"/>` 这种**空层**（自闭合 ✓、
                #     **没有** `</g>` ✓）就永远回不到 0 ✗ ⇒ `layer_inner` **什么都不返回** ✗
                #     ⇒ 整个件**画不出来** ✗（实测 `U1`：焊盘全在 `<g id="copper1">` 里 ✓、
                #       紧跟一个 `<g id="copper0"/>` ✓ ⇒ `layer_inner(…, "copper1")` = **0 字符** ✗）。
                #   ★ 这是**通病** ✗：底层件常把空层写成自闭合 ✓（`U1` 就是背面件 ✓）。
                k = svg_text.find(">", j)
                if not (k >= 0 and svg_text[j:k].rstrip().endswith("/")):
                    depth += 1
            i = i + nxt.end()
            if depth == 0:
                body = svg_text[m.end():j]
                out.append(('<g %s>%s</g>' % (extra, body)) if extra else body)
                break
    return "".join(out)


def remap_colors(xml, table=None, default=None):
    """按**颜色值**逐项换色 ✓（★ 与 `repaint_colors` **共用这一份实现** ✓，2026-10-07 加 ✓）

    · `table`：`{"#f9a435": "#8ab4f8", …}` ✓ —— **认得出**的颜色按表换 ✓（大小写不敏感 ✓）；
    · `default`：表里**没写到**的颜色换成它 ✓；`None` ⇒ **原样保留** ✗（默认 ✓）。

    ★ 为什么要有它 ✗（用户原话 ✓）：「双面板的**颜色差异看不出来了**」✓ ——
      `repaint_colors` 是"**全部**刷成一个色" ✓（画单版预览正好 ✓），
      但它把 **copper0 / copper1 也刷成一色** ✗ ⇒ 差异图里就分不出顶层/底层了 ✗。
      差异图要的是「**色相 = 层**、**深浅 = 版**」✓ ⇒ 必须先**认得**层色 ✗：
      本渲染器给层的颜色是**固定常量** ✓ ——
        面：`C_CU0` 底橘 ✓ / `C_CU1` 顶黄 ✓；线：`C_W0` 底 ✓ / `C_W1` 顶 ✓；过孔同样两色 ✓
      ⇒ 按这张表逐项换，层就不会糊在一起 ✓。
    """
    tab = {str(k).strip().lower(): v for k, v in (table or {}).items()}

    def pick(c):
        v = tab.get(str(c).strip().lower(), default)
        return None if v is None else str(v)

    def rep(m):
        if m.group(2).strip().lower() == "none":
            return m.group(0)
        v = pick(m.group(2))
        return m.group(0) if v is None else '%s="%s"' % (m.group(1), v)

    def rep2(m):
        if m.group(2).strip().lower() == "none":
            return m.group(0)
        v = pick(m.group(2))
        return m.group(0) if v is None else '%s:%s' % (m.group(1), v)

    x = re.sub(r'\b(stroke|fill)\s*=\s*"([^"]*)"', rep, xml)
    return re.sub(r'\b(stroke|fill)\s*:\s*([a-zA-Z#0-9]+)', rep2, x)


def repaint_colors(xml, color):
    """把原文里**自带的颜色**换成 `color` ✓ —— **丝印**✗ / **铜层** ✓ 共用这一个 ✓

    ★ 丝印不改就看不见 ✗（件里写死近白 `#f0f0f0` ✓ —— 见 `C_SK0` ✓）；
      铜层不改就**与 Fritzing 不一致** ✗（它载入时按层盖色 ✓ —— 见 `C_CU0` ✓）。

    ★ 只改**颜色值** ✓：`stroke="none"` / `fill="none"` **原样保留** ✓
      （那个是"这块不画"的意思 ✓，改了反而画出一个色块 ✗）。
    ★ 两种写法都要盖 ✗：属性式 `stroke="#…"` ✓ 与 内联式 `style="…stroke:#…"` ✓；
      注意 `stroke-width="…"` / `stroke-width:…` 不能被误伤 ✓（正则要求后面紧跟 `=` 或 `:` ✓）。
    ★★ 2026-10-07 ✓：实现**只剩** `remap_colors` 一份 ✓（这里就是"表为空 + 兜底 = color" ✓）——
      ✗ 别在这里再抄一遍正则 ✗（抄一份就多一个错处 ✓）。
    """
    return remap_colors(xml, {}, color)


def holes_of(text):
    """⇒ `[(钻孔心 sketch 单位 ✓, 孔内径 mm ✓, 铜盘外径 mm ✓), …]` ✓（核心孔件 ✓）

    ★★ 实现搬到 `pcb_pads.holes()` 了 ✓（2026-10-01 ✓）—— 因为**布线器与校验器也必须知道**
      这几颗孔 ✗（实测 `v50H.fzz` 有 4 根走线穿过安装孔 ✗）。这里只留一个**薄封装** ✓，
      免得外面（本文件其它地方）改调用 ✓。
    """
    return PP.holes(text)


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
    # ★★ 2026-10-07 实测补的一条 ✓（差异图那件事抳出来的 ✗）：**不带 `--board-only` 时，
    #   下面那个 `stroke=C_BRD_EDGE` 的 rect **不是板框** ✗ —— 因为 `r` 会被第 246 行
    #   **胀成「板框 ∪ 全部墨迹」** ✗ ⇒ 画出来的是**取景框** ✓。
    #   ⇒ ✗ 别拿它当"板框的像素范围"用 ✗（会整体平移 ✗，实测 0.5 mm ✓）；
    #     要对板框定标/对齐 ⇒ 用 `--board-only` 渲 ✓（那时 `r` 就是真板框 ✓）。
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
         'fill-opacity="%s" stroke="%s" stroke-width="1.2"/>'
         % (X(r[0]), Y(r[1]), (r[2] - r[0]) * k, (r[3] - r[1]) * k, C_BRD_FILL,
            C_BRD_FILL_OP, C_BRD_EDGE)]
    # ★★ 件的**铜箔原文**（含线圈 700 多条绕组 ✓）—— 2026-09-30 用户点名补 ✗：
    #   上一版只画焊盘 ✗ ⇒ 线圈看成一个空框 ✗，没法用眼看"压绕组" ✗。
    T = (k, 0.0, 0.0, k, -x0 * k, -y0 * k)                    # sketch → px ✓
    silk_layers, n_silk, n_parts = [], 0, 0
    for p in model.get("parts", []):
        if p.get("svg_text") is None or "loc" not in p:
            continue
        if (p.get("moduleId") or "").startswith(("Breadboard", "Via")):
            continue
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
        # ★★ 铜箔：**按层取、按层改色** ✓（见 `C_CU0` / `C_CU1` ✓）
        #   顺序不变 ✓：`copper0` 先、`copper1` 后 ✓（= Fritzing 的 `PCBViewLayerList` 顺序 ✓
        #   ⇒ 顶层盖在底层上 ✓，哪层在上不会因这次改动而变 ✗）。
        # ★★ **背面件（`bottom="true"`）铜层要对调** ✓（2026-10-01 用户点名 ✗：
        #   「J1/J2 在底面，焊盘应是橘黄色，现在还是浅黄色，看不出来它们在底面」✓）：
        #   背面件 svg 里的 `copper1` 落在**板子的 copper0（背面 ✓）**上 ✓
        #   ⇒ 它取**底层色**（橘 ✓）、`copper0` 取**顶层色**（黄 ✓）✓。
        #   ★ 口径**只有一份** ✗：与 `pcb_pads.part_shapes` 同一判据 ✓
        #     （它的证据 ✓：用户导出的 Fritzing 图里，背面件的 43 个盘全在 `<g id="copper0">` ✓）。
        col0, col1 = (C_CU1, C_CU0) if flip else (C_CU0, C_CU1)
        cu = (repaint_colors(layer_inner(p["svg_text"], "copper0"), col0)
              + repaint_colors(layer_inner(p["svg_text"], "copper1"), col1))
        if cu:
            o.append('<g transform="%s">%s</g>' % (trans, cu))
            n_parts += 1
        # ★★ 丝印也**原样**画一份 ✓（`silkscreen` / `silkscreen0` ✓）—— 先存着 ✓，
        #   等焊盘/走线都画完再上 ✓（丝印是**最后印**上去的 ✓，压在铜上是正常的 ✓）；
        #   颜色必须**逐元素改** ✗（件里写死近白的 `#f0f0f0` ✗ ⇒ 不改就看不见 ✗）。
        # ★ 丝印**按所在面取色** ✓（背面件对调 ✓ —— 见 `C_SK0` / `C_SK1` ✓）
        top_sk, bot_sk = (C_SK0, C_SK1) if flip else (C_SK1, C_SK0)
        sk = (repaint_colors(layer_inner(p["svg_text"], "silkscreen"), top_sk)
              + repaint_colors(layer_inner(p["svg_text"], "silkscreen0"), bot_sk))
        if sk:
            silk_layers.append('<g transform="%s">%s</g>' % (trans, sk))
            n_silk += 1
    # 走线（先画线、后画盘 ✓，盘压线 ✓）
    #   ★★ 线宽按**实物** ✓：`wireExtras@mils` ⇒ sketch 单位 ✓（`part_box.mils_to_units` ✓）
    #     ✗ 旧版写死 `0.25` 单位 = **0.0705 mm** ✗ ⇒ 比实物（v47 = `12 mil` = **0.3048 mm** ✓）
    #     细 **4.3 倍** ✗ ⇒ 线看着像发丝、过孔看着被“放大” ✗（2026-10-01 用户让改 ✓）。
    #     没写 `wireExtras` 的老线 ⇒ 回退到原来的 0.25 ✓（不改变旧行为 ✓）。
    # ★★ 曲线走线 ✓：`<bezier>` 的走线在 Fritzing 里是**三次贝塞尔**（导出也照此写成
    #   `<path d="M…C…">` ✓）—— 实测 v59 的 `5V/GND` `24 mil` 粗线里 **5/15** 根是弧线 ✓。
    #   ✗ 旧版一律画成**直弦** ✗ ⇒ 弧线被拉直，与 Fritzing 一眼就不一样 ✗
    #     （2026-10-08 用户对图点名 ✓）⇒ 有控制点就出 `path`（与导出同一种写法 ✓），没有才是 `line` ✓。
    n_curve, n_curve_drawn = 0, 0
    for t in model["traces"]:
        c = C_W1 if t["layer"] == "copper1" else C_W0
        w = PB.mils_to_units(t.get("mils"), 0.25)
        sw = max(0.6, w * k)
        bz = t.get("bez")
        if bz:
            n_curve += 1
            o.append('<path d="M%.2f,%.2f C%.2f,%.2f %.2f,%.2f %.2f,%.2f" fill="none" '
                     'stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
                     % (X(t["a"][0]), Y(t["a"][1]), X(bz[0][0]), Y(bz[0][1]),
                        X(bz[1][0]), Y(bz[1][1]), X(t["b"][0]), Y(t["b"][1]), c, sw))
            n_curve_drawn += 1
        else:
            o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                     'stroke-width="%.2f" stroke-linecap="round"/>'
                     % (X(t["a"][0]), Y(t["a"][1]), X(t["b"][0]), Y(t["b"][1]), c, sw))
    # ★★ 焊盘：**不再叠自己画的方块** ✗（2026-10-01 按用户要求改 ✓）
    #   ✗ 以前会在"件自己的铜箔原文"之上再画一层半透明矩形 ✗ ⇒
    #     焊盘的**观感尺寸/边缘**与 Fritzing 不一样 ✗ ⇒ 用户看到"过孔与焊盘的相对位置变了" ✗
    #     （实为多画了一层 ✗，坐标本身是对的 ✓）。
    #   ⇒ 默认**啥也不画** ✓（件自己的铜箔已经画了 ✓）；确有需要（比如没有 svg 的件 ✓）
    #     可用 `--pad-marks` 找回来 ✓。
    if "--pad-marks" in _OPTS[0]:
        for q in model["pads"]:
            c = C_CU1 if q["layer"] in ("copper1", "both") else C_CU0
            o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                     'fill-opacity="0.85" stroke="%s" stroke-width="0.4"/>'
                     % (X(q["box"][0]), Y(q["box"][1]),
                        max(1.0, (q["box"][2] - q["box"][0]) * k),
                        max(1.0, (q["box"][3] - q["box"][1]) * k), c, c))
    # ★★ 过孔：**环 + 白心孔** ✓（= Fritzing 导出的画法 ✓，见文件头 `C_VIA_*` 的量化依据 ✓）
    #   ✗ 旧版画一个 `r=0.35*k` 的**实心绿点** ✗ ⇒ 过孔在图上跟焊盘没区别 ✗，
    #     孔眼完全看不出来 ✗（2026-10-01 用户：「过孔都画错了」✓ —— 病根在这儿 ✓）。
    for v in model["vias"]:
        hd = v.get("hole_mm") or VIA_HOLE_MM                   # 孔直径 mm ✓（读件自己的值 ✓）
        rg = v.get("ring_mm") if v.get("ring_mm") is not None else VIA_RING_MM
        rc = (hd + rg) / 2.0 * PB.MM * k                       # 环**中心线**半径 ✓
        sw = max(0.8, rg * PB.MM * k)                          # 环宽 = 描边宽 ✓
        # ★★ 稳定 id ✓（2026-10-01 用户拿 `circleNNNN` 来对账 ✗ —— 那名字是**查看器自己起的** ✗，
        #   文件里根本没有 ✗）⇒ 这里按件的标题（`Via15` ✓）写 id ✓ ⇒ 两边能按**同一个名字**找 ✓。
        vid = esc(v.get("ttl") or "")
        i0 = ' id="%s_ring_bot"' % vid if vid else ""
        i1 = ' id="%s_ring_top"' % vid if vid else ""
        i2 = ' id="%s_hole"' % vid if vid else ""
        o.append('<circle%s cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" '
                 'stroke-width="%.2f"/>'
                 % (i0, X(v["p"][0]), Y(v["p"][1]), rc, C_VIA_BOT, sw))
        o.append('<circle%s cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" '
                 'stroke-width="%.2f"/>'
                 % (i1, X(v["p"][0]), Y(v["p"][1]), rc, C_VIA_TOP, sw))
        # ★ **不再画白心孔** ✗（2026-10-01 按用户要求改 ✓）：Fritzing 的过孔 = 一个
        #   `fill="none"` 的环 ✓ ⇒ 环里是**透的** ✓（透出焊盘铜 ✓）；我加的那个白圆
        #   ⇒ 同一个孔两种观感 ✗。需要"看得见的孔"时用 `--via-hole` 找回来 ✓。
        if "--via-hole" in _OPTS[0]:
            o.append('<circle%s cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" '
                     'stroke-width="%.2f"/>'
                     % (i2, X(v["p"][0]), Y(v["p"][1]), hd / 2.0 * PB.MM * k,
                        C_HOLE_FILL, C_HOLE_EDGE, max(0.8, 0.07 * k)))
    # ★★ 丝印（压在铜/焊盘之上 ✓ —— 与 Fritzing 的层序一致 ✓）
    o += silk_layers
    # ★★ 安装孔：**照 Fritzing 导出画** ✓（一个铜环 + 一个黑实心钻孔盘 ✓）
    #   ✗ 以前是"白圆 + 深边 + 只在 `outer>inner` 才加环" ✗ ⇒ 观感不同 ✗、还少了一个环 ✗。
    holes = holes_of(model.get("text"))
    for hi, ((hx, hy), inner_mm, outer_mm) in enumerate(holes):
        # ★ 安装孔的铜环 ✓：Fritzing 导出里**总有一个**（实测：`环 r=0.550 mm sw=0.500 mm`
        #   = 内 Ø0.6 / 外 Ø1.6 ✓，2 个孔 × 2 层 = 4 个 ✓）——它来自核心 `hole` 件自己的 svg ✓
        #   ⇒ 不管 `hole size` 那栏写多少，**照它画** ✓
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" '
                 'stroke-width="%.2f"/>'
                 % (X(hx), Y(hy), 0.55 * PB.MM * k, C_HOLE_RING, 0.50 * PB.MM * k))
        # ★ 钻孔 = **黑色实心盘** ✓（Fritzing 里就是 `fill="black"` 无描边 ✓）
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="none"/>'
                 % (X(hx), Y(hy), inner_mm / 2.0 * PB.MM * k, C_HOLE_FILL))
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
    # ★ 统计里报过孔尺寸 ✓ —— 但有的文件过孔**没写 `hole size`** ✗（那两项是 `None` ✓）
    #   ⇒ 排序前必须**把 `None` 换掉** ✗（`sorted({(0.3,0.15),(None,None)})` 会在
    #   `float < None` 上抛 `TypeError` ✗ —— 2026-10-01 在单通道板上实测撞到 ✓）。
    szs = sorted({(v.get("hole_mm") or -1.0,
                   v.get("ring_mm") if v.get("ring_mm") is not None else -1.0)
                  for v in model["vias"]})
    if not szs:
        vsz = "—"
    elif len(szs) > 1:
        vsz = "（%d 种尺寸 ✓）" % len(szs)
    elif szs[0][0] < 0:
        vsz = "（件没写 hole size ✗）"
    else:
        vsz = "孔 %.2f / 环 %.2f mm" % szs[0]
    _STATS.update(pads=len(model["pads"]), traces=len(model["traces"]),
                  vias=len(model["vias"]), copper=n_parts, silk=n_silk, holes=len(holes),
                  via_sz=vsz, curve=n_curve)
    # ★ 自检 ✓：模型里带控制点的走线**每条都要落成一个 `<path>`** ✗ ——
    #   `n_curve` 是模型侧数的 ✓、`n_curve_drawn` 是**写进 svg 的** ✓ ⇒ 两个数必须相等 ✓
    #   （✗ 不等 = 有人又把弧过滤掉了 ✗ —— 这正是 2026-10-08 那个 bug 的样子 ✓）。
    if n_curve != n_curve_drawn:
        print("⚠ 弯曲走线 %d 条，但只写出 %d 条 `<path>` ✗ ⇒ 有弧被丢了 ✗（检查 `bez` 传递 ✓）"
              % (n_curve, n_curve_drawn))
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
    svg = render(model, px, [a for a in argv if a.startswith("--")])
    open(out, "w", encoding="utf-8", newline="\n").write(svg)
    print("✓ 写出 %s（%d 字节）：焊盘 %d / 走线 %d（其中弯曲 %d ✓）/ 过孔 %d（%s）/ 铜箔块 %d / 丝印块 %d / 孔 %d / 板框 %s"
          % (out, len(svg), _STATS.get("pads", 0), _STATS.get("traces", 0),
             _STATS.get("curve", 0), _STATS.get("vias", 0), _STATS.get("via_sz", "—"),
             _STATS.get("copper", 0), _STATS.get("silk", 0), _STATS.get("holes", 0),
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
