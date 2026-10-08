# -*- coding: utf-8 -*-
"""把 .fzz 的**面包板视图**渲染成 PNG ✓（为了"看得见" ✓）

做法（不自创几何 ✓，全部按 Fritzing 的摆放规矩来 ✓）：
  · 零件摆放 = `sketch = loc + M·(k·局部用户单位) + (m31,m32)` ✓ —— 矩阵与缩放
    直接用 `part_box.py`（`tf_of` / `parse_tf` / `mul` ✓）那套 ✓，
    它算"本体包围盒"时用的同一套数学 ✓（**不另写一份** ✗）；
  · 导线 = `geometry x/y/x2/y2`（x2/y2 是**相对** ✓）+ `wireExtras/@color` ✓，线宽 2 单位 ✓；
  · 零件/板子的 svg 从 .fzz 包里取 ✓；包里没有（core 件）就从它的 fzp 路径旁边取 ✓。

用法：py -3.13 f:\\git\\_scratch\\render_bb.py <sketch.fzz> <out.png> [<px宽>]
"""
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

# ★★ 2026-09-27（用户定 ✓）：**通用工具只有一份，就在元件库仓 `tools/`** ✓
#   （`part_box` / `bb_compare` ✓）；本项目里不再留副本 ✗。
#   我在这里犯过两个反例 ✓ 记下来别再犯 ✗：
#     ① 把 `f:\git\_scratch` 插进 import 路径 ✗ ⇒ 草稿区旧副本顶掉当前那份 ✗，
#        而且**不报错** ✗，只让脚位自检静静退化成"未验证" ✗；
#     ② 又把库仓的模块拷了一份进项目 ✗ ⇒ 又是"两份实现" ✗。
#   ⇒ 本文件**已在库仓内** ✓ ⇒ 直接 import 同目录的模块即可 ✓（不需要 `toolpaths` 定位器 ✓）。
import part_box as PB                                             # noqa: E402
import bb_compare as BC                                           # ★ 孔位/遮挡同一份实现 ✓

path, out = sys.argv[1], sys.argv[2]
PXW = float(sys.argv[3]) if len(sys.argv) > 3 else 1800.0
SK = 3.5433                    # 1mm = 3.5433 sketch 单位 ✓


def tag(e):
    return e.tag.split("}")[-1]


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def inner(svg_text):
    t = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", svg_text)
    m = re.search(r"<svg\b[^>]*>", t, flags=re.S)
    if not m:
        return ""
    body = t[m.end():]
    body = body[:body.rfind("</svg>")] if "</svg>" in body else body
    return body


UNIT_MM = {"": 25.4 / 1000.0,          # ★ 无单位 = 1/1000 英寸 ✓（Fritzing 零件约定 ✓）
           "px": 25.4 / 72.0,          # ★★ `px` = **1/72 英寸** ✓（2026-09-27 实测钉死 ✓）
           "pt": 25.4 / 72.0,
           "mm": 1.0, "cm": 10.0, "in": 25.4}
MM = 3.5433                    # 1mm = 3.5433 sketch 单位 ✓（件的 `width`/`height` 属性是 mm ✓）


def xml_unesc(s):
    """把 fz 属性里那一串**转义过的 svg** 还原 ✓（`&amp;` 必须**最后**换 ✗，否则二次转义 ✓）。"""
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            .replace("&#10;", "\n").replace("&#13;", "\r").replace("&#9;", "\t")
            .replace("&apos;", "'").replace("&amp;", "&"))


def xml_esc(t):
    """文字里可能要写 `&` / `<` ⇒ 转义 ✓（反过来的那个 `xml_unesc` 只管属性 ✓）。"""
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def logo_text(props, g):
    r"""`TXT*` 图例文字件 ⇒ `(一段 <text> 的 svg, 说明)` ✓ —— 就是色条旁边那行说明字 ✓。

    ★★ 2026-10-08 用户报「**图例文字都没有显示出来**」✗ —— 原来这里直接 `continue` 掉了 ✗
      （旧理由「免得挡住视图」✗ —— 那时图例件在图上乱摆 ✓）。现在它是**设计的一部分** ✓：
      实测本板 **10 件** ✓（「图例：」＋ 9 个网名 ✓：GND / 5V / DATA_IN / DATA_OUT /
      LED_DIN / RC / BR+ / COIL_A / COIL_B ✓），正好配 **9 条色条** ✓。

    ★ 画法**不另创几何** ✗：件自己的 `shape` 属性里就带着那份 svg ✓
      （`<svg viewBox="0 0 <10n> 13"><text x="1" y="9" font-size="10">…</text></svg>` ✓）
      ⇒ 把它**整块按盒子缩放**画出来 ✓ —— 比例 / 字号 / 基线全是件自己声明的 ✓（✗ 我不算 ✗）。
      `x` / `y` / `font-size` / `text-anchor` / `font-family` 一律照抄 ✓，只换 `fill` ✓
      （件把文字颜色存在 `color` 属性里 ✓）并**丢掉 `id`** ✗（10 件全叫 `label` ✓ ⇒ 重复 id ✓）。

    ★ 锚点 = **盒子左上角** ✓（实测钉死 ✓，**不是中点** ✗）：`bb_legend3.py` 给的色条
      x=590 / 长 9 / 间隙 3 ⇒ 文字件的几何 x = **602** ✓（= 左缘 ✓）；y 也一算就合 ✓ ——
      盒心 32.05 − 字墨心（盒内基线 9、字号 10 ⇒ 墨心 ≈ 4.5/13 ✓）1.25 ≈ **色条 y=31** ✓
      正好竖向居中 ✓（若是中点约定，盒子会**压到色条上** ✗、字也偏上 4 单位 ✗）。

    ★ 盒子 = `width`/`height` 两个属性（**mm** ✓）× `MM` ✓；★ 两条边的缩放**必须相等** ✓
      （件自己的 viewBox 就是按这个比例做的 ✓）⇒ 不等 ⇒ 画出来是**拉伸**的 ✗ ⇒ 调用方当场报 ✓。
    """
    shape = xml_unesc(props.get("shape") or "")
    mt = re.search(r"<text\b([^>]*)>(.*?)</text>", shape, re.S)
    if mt is None:
        return None, "`shape` 里没有 `<text>` ✗"
    vb = re.search(r'viewBox="([-\d.eE\s,]+)"', shape)
    if vb is None:
        return None, "`shape` 里没有 `viewBox` ✗"
    v = [float(t) for t in re.split(r"[ ,]+", vb.group(1).strip()) if t]
    if len(v) != 4 or not v[2] or not v[3]:
        return None, "`viewBox` 不完整：%s ✗" % vb.group(1)
    w_mm, h_mm = num(props.get("width")), num(props.get("height"))
    if not w_mm or not h_mm:
        return None, "`width`/`height` 缺（盒子的 mm 尺寸 ✓）✗"
    sx, sy = w_mm * MM / v[2], h_mm * MM / v[3]        # 盒内单位 → sketch 单位 ✓
    x, y = num(g.get("x")), num(g.get("y"))
    at = re.sub(r'\s(?:id|fill)="[^"]*"', "", mt.group(1))
    seg = ('<text%s transform="translate(%.4f,%.4f) scale(%.6f,%.6f)" fill="%s">%s</text>'
           % (at, x - sx * v[0], y - sy * v[1], sx, sy,
              props.get("color") or "#333333", xml_esc(props.get("logo") or "")))
    # ★ 盒子的**画布占比**也交出去 ✓（sketch 单位 ✓）—— 调用方要拿它把画布撑到装得下字 ✓
    #   （✗ 不撑 ⇒ 最长的那个标签会被 viewBox 裁掉 ✗ —— 实测 `DATA_OUT` 就差 35 单位 ✓）。
    return seg, sx, sy, sx * v[2], sy * v[3]



def scale_of(svg_text):
    """svg 的**用户单位 → sketch 单位** ✓（**只有一条规则** ✓，不分"有没有 viewBox" ✗）

        w_mm = width值 × UNIT_MM[单位]
        有 viewBox ⇒ 1 用户单位 = w_mm / viewBox宽
        没有 viewBox ⇒ 1 用户单位 = UNIT_MM[单位]
        k = 每用户单位 mm × 3.5433（= 1mm 的 sketch 单位数 ✓）

    ★★★ 2026-09-27 **实测钉死** ✓（我在单位上连错三次 ✗，每次都被用户点出来 ✓，记下来别再犯 ✗）：
      · **`px` = 1/72 英寸 = 0.35278 mm** ⇒ k = **1.2500** ✓
        证据①（**面包板自己** ✓）：`width="468.238px" viewBox="0 0 468.238 …"` ⇒ 468.238px = **165.2mm** ✓
          ≈ 孔阵 `576 单位 = 162.6mm` ✓（差 9 单位 = 端部留边 ✓ 合理 ✓）；
        证据②（**LED2 的 `WS2812B_1010`** ✓）：`width="19.54px" viewBox="1.03 0 19.54 28.8"` ⇒ 同样 k=1.25 ✓
          ⇒ 4 脚中心差 **14.401 × 21.600 用户单位** → **18.00 × 27.00 sketch 单位** ✓
          = 它插的孔 `col31→col33`（18 ✓）与 `rowE→rowF`（27 ✓）
          ⇒ **两个方向各自独立算出 1.2500** ✓✓ ⇒ 规则成立 ✓（板子与零件**同一条规则** ✓，板子不是特例 ✓）。
      · **无单位 = 1/1000 英寸 = 0.0254 mm** ✓。
      ✗ 作废的错法：`px`/无单位一律 0.09 ✗（⇒ 板子小 14 倍 ✗ / LED2 变"一粒米" ✗）；
        "有 viewBox 就算 90dpi" ✗（⇒ 板子 132mm ✗、小 20% ✗ ⇒ 底部 X/W 两条轨落到板外 ✗）。
      ✗ 我为什么会算错 ✓：把焊盘组的 `translate` 之差（34.035→234.035 = **200** ✓）当成脚距 ✗，
        而组内 `<rect x>` 是 −31.584→−217.184（差 **−186** ✓）⇒ **两个大数互抵**，真脚距只有
        **14.401** ✓ —— 教训：**动 svg 前必须把 transform 链真算出来** ✓（`part_box.pin_points` ✓
        一份实现 ✓），别拿"相邻两个数字之差"当几何 ✗。
    """
    head = re.search(r"<svg\b[^>]*>", svg_text, flags=re.S)
    if not head:
        print("      [!] 这张 svg 连 `<svg>` 头都没有 ✗")
        return 1.0
    h = head.group(0)
    m = re.search(r'width="([\d.]+)\s*(mm|cm|in|px|pt)?"', h)
    if not m:
        print("      [!] 这张 svg 连 width 都没有 ⇒ 只能按「用户单位＝sketch 单位」画 ✗")
        return 1.0
    v = float(m.group(1))
    u = m.group(2) or ""
    umm = UNIT_MM.get(u)
    if umm is None:
        print("      [!] 没见过的单位 `%s` ⇒ 按**无单位**（1/1000in）画 ✗" % u)
        umm = UNIT_MM[""]
    vb = re.search(r'viewBox="([^"]+)"', h)
    if not vb:
        return umm * SK                          # 没有 viewBox ⇒ 用户单位本身就是长度 ✓
    parts = [float(x) for x in re.split(r"[ ,]+", vb.group(1).strip()) if x]
    if len(parts) != 4 or not parts[2]:
        return umm * SK
    return v * umm * SK / parts[2]               # ★ **唯一**的规则 ✓


def vb_origin(svg_text):
    """`viewBox` 的 **(min-x, min-y)** ✓；没有 ⇒ (0, 0) ✓

    ★★ 为什么要它 ✓（2026-09-27 **机验钉死** ✓）：`viewBox` 的 min-x/min-y 是**视口原点** ✓
      ⇒ `sketch = loc + M·(k·(用户坐标 − 原点))` ✓ ⇒ **必须减** ✓。
      证据 ✓（不是推理 ✗）：`LED2` 的 `viewBox="1.03 0 19.54 28.8"` ⇒ 4 个脚**一律**
      偏 `+1.29 单位 = 1.03 × 1.25` ✓✓（x 偏 / y 不偏 ✓ = min-y 为 0 ✓）；减掉后 Δ=0.00 ✓✓。
    """
    m = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)', svg_text or "")
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


z = zipfile.ZipFile(path)
fzname = [n for n in z.namelist() if n.endswith(".fz")][0]
root = ET.fromstring(z.read(fzname))

packed = {}
for n in z.namelist():
    if n.endswith(".svg"):
        packed[n] = z.read(n).decode("utf-8", "replace")

svg_cache = {}
LAST_PICK = [None]          # ★ 刚才那个零件到底用了哪个 svg ✓（要点名 ✓，不静默 ✓）


def svg_for(fzp_path, img, view="breadboard"):
    """取零件的视图 svg 文本 ✓：先看包里 ✓，再按 fzp 路径旁边找 ✓"""
    key = (fzp_path, img)
    if key in svg_cache:
        # ★★ 2026-09-27 修 ✓：命中缓存时**也要把"用了哪个文件"带出来** ✓ ——
        #   上一版这里直接 `return` ✗ ⇒ 第二个实例（C1 与 C2 同件 ✓、J1 与 J2 同件 ✓）
        #   会打成"用了（**找不到** ✗）"✗ ⇒ **报告在说谎** ✗（文件其实取到了 ✓）。
        #   我自己的规矩：**不许有会误导的输出** ✓ ⇒ 缓存里连"出处"一起存 ✓。
        LAST_PICK[0] = svg_cache[key][1]
        return svg_cache[key][0]
    LAST_PICK[0] = None
    txt = None
    want = os.path.basename(img or "")
    for n, t in packed.items():
        if want and n.endswith(want):
            txt = t
            LAST_PICK[0] = n
            break
    if txt is None and fzp_path and img:
        base = os.path.dirname(os.path.dirname(fzp_path))
        for s2 in ("", "core", "contrib", "user"):
            cand = os.path.normpath(os.path.join(base, "svg", s2, img.replace("/", os.sep)))
            if os.path.isfile(cand):
                txt = open(cand, encoding="utf-8").read()
                LAST_PICK[0] = cand
                break
    svg_cache[key] = (txt, LAST_PICK[0])      # ★ 连"出处"一起缓存 ✓（上面命中时要报 ✓）
    return txt


lay_body, wires = [], []
_logo_ok, _logo_bad = [], []          # ★ 图例文字（TXT*）画成了几件 / 哪几件画不出来 ✓
for el in root.iter("instance"):
    mid = el.get("moduleIdRef") or ""
    ttl = (el.findtext("title") or "").strip()
    vw = next((c for c in el if tag(c) == "views"), None)
    if vw is None:
        continue
    bv = next((c for c in vw if tag(c) == "breadboardView"), None)
    if bv is None:
        continue
    g = next((c for c in bv if tag(c) == "geometry"), None)
    if g is None:
        continue
    if mid.startswith("Wire"):
        # ★★ 2026-10-03 修 ✗：**必须看 `wireFlags`** ✓ —— 一条线可以同时带三个视图 ✓，
        #   但它在某个视图里**算不算铜**由 `wireFlags` 决定 ✓：
        #   Fritzing = `if (!(wire->getViewGeometry().wireFlags() & myTrace)) continue;`
        #   ⇒ 位不含该视图 ⇒ **该视图直接跳过、不画** ✗（AGENTS §13 已认证 ✓）。
        #   实测本板：53 条 PCB 走线（flags=**4**）里 **23 条**的面包板几何**非零** ✗
        #   ⇒ 旧版照画 ⇒ 面包板里多出 23 条**不属于面包板**的线 ✗（用户："很多蓝色线" ✗）。
        #   位：面包板 = **64** ✓、原理图 = 128 ✓、PCB 铜 = 4 ✓（`views_hist.py` 实测 ✓）。
        #   ★ 属性**缺失**时按"老文件"放行 ✓（只对**写了** flags 的才判 ✗，免得误杀 ✓）。
        fl = g.get("wireFlags")
        if fl is not None and not (int(fl) & 64):
            continue
        col = "#404040"
        we = next((c for c in bv.iter() if tag(c) == "wireExtras"), None)
        if we is not None and we.get("color"):
            col = we.get("color")
        x, y = num(g.get("x")), num(g.get("y"))
        x2, y2 = num(g.get("x2")), num(g.get("y2"))
        if abs(x2) + abs(y2) > 1e-9:
            wires.append((x, y, x + x2, y + y2, col))
        continue
    if ttl.startswith("TXT"):
        # ★★ 2026-10-08 用户报「图例文字都没有显示出来」✗ ⇒ 从"不画"改成"画出来" ✓
        #   （口径与理由见 `logo_text()` 的 docstring ✓）。原来的理由「免得挡住视图」
        #   已经不成立了 ✓ —— 这行字**就是要看的** ✓（色条没有说明字等于没有图例 ✓）。
        props = {p.get("name"): p.get("value") for p in el.iter("property")}
        res = logo_text(props, g)
        if res[0] is None:
            print("   ✗ %-6s 图例文字**画不出来** ✗：%s" % (ttl, res[1]))
            _logo_bad.append(ttl)
        else:
            seg, sx, sy, bw, bh = res
            lay_body.append(seg)
            _logo_ok.append((ttl, props.get("logo") or "", sx, sy, num(g.get("x")),
                             num(g.get("y")), props.get("color") or "", bw, bh))
        continue
    fzp = (el.get("path") or "").replace("/", os.sep)
    lay = ET.parse(fzp).getroot().find(".//breadboardView/layers") if os.path.isfile(fzp) else None
    img = lay.get("image") if lay is not None else None
    txt = svg_for(fzp, img)
    if txt is None:
        continue
    # ★★ 2026-09-27 ✓：**点名报出**这个零件到底用了哪个 svg ✓（用户报"preview 全不对" ✗ ⇒
    #   不许再拿"渲染没报错"当证据 ✗ —— 要把"取了哪个文件"打出来，人能核对 ✓）
    print("   %-6s image=%-42s 用了 %s（%d 字节）"
          % (ttl, img or "（无）",
             os.path.basename(LAST_PICK[0]) if LAST_PICK[0] else "（**找不到** ✗）",
             len(txt)))
    m = PB.tf_of(g)
    k = scale_of(txt)
    _ox, _oy = vb_origin(txt)        # ★ viewBox 原点**必须减** ✓（证据见下面 matrix 那段 ✓）
    _subx = m[0] * k * _ox + m[2] * k * _oy
    _suby = m[1] * k * _ox + m[3] * k * _oy
    # ★★ 交叉验算 ✓（2026-09-27 ✓）：**面包板**（几百个圆 ✓）**声明的宽**必须 ≈ 孔阵宽 ✓
    #   `468.238 × 1/72in = 165.2mm` ✓ ≈ 孔阵 `576 单位 = 162.6mm` ✓（差 9 单位 = 端部留边 ✓）
    #   ⇒ `scale_of` 那条规则**由板子自己验过** ✓（不再需要"圆多就强制 72dpi"那种特例 ✗）。
    if len(re.findall(r"<circle", txt)) >= 100:
        _m2 = re.search(r'width="([\d.]+)\s*(mm|cm|in|px|pt)?"', txt)
        if _m2:
            _wmm = float(_m2.group(1)) * k / SK        # 声明值 × 每用户单位 mm ✓
            print("   %-6s **板子对账** ✓：声明宽 %s%s = **%.1f mm** ↔ 孔阵 576 单位 = 162.6mm ⇒ %s"
                  % (ttl, _m2.group(1), _m2.group(2) or "(无单位)", _wmm,
                     "✓ 对得上 ✓" if 150.0 < _wmm < 180.0 else "✗ **对不上** ✗"))
    # ★★ 2026-09-27 ✓（用户定位 ✗：`preview.svg` 的**面包板尺寸错** ⇒ 看起来不对 ✓）：
    #   把**每张 svg 的头部声明**和**我算出的 k** 打出来 ✓ —— 才能看出是哪一件、错在哪 ✗。
    #   （`scale_of` 里：无单位按 90dpi ✓、`%` 或解析不到 ⇒ 直接**退化 k=1.0** ✗✗
    #     ⇒ 那件就按"用户单位＝sketch 单位"画 ✗ = **尺寸全错** ✓。）
    _hdr = re.search(r"<svg\b[^>]*>", txt, flags=re.S)
    # ★★ 自检 ✓（2026-09-27 ✓）：把这次画的尺寸换成 **mm** 报出来 ✓ ——
    #   板子/零件的物理尺寸人手一算就能对账 ✓（不再"渲染没报错就算对" ✗）。
    _vbm = re.search(r'viewBox="[\d.]+[\s,]+[\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)"', txt)
    _phys = ""
    if _vbm:
        _phys = "本体 %.1f×%.1f mm" % (float(_vbm.group(1)) * k * 25.4 / 90.0,
                                        float(_vbm.group(2)) * k * 25.4 / 90.0)
    print("   %-6s svg头: %s ‖ k=%.4f %s"
          % (ttl,
             " ".join(re.findall(r'[a-zA-Z:-]+="[^"]*"', _hdr.group(0))) if _hdr else "（无头 ✗）",
             k, _phys))
    # ★★★ 脚位自检 ✓✓（2026-09-27 用户报 ✗："1010 板的 4 个引脚都是悬空的" ✓）：
    #   把每个脚**画出来的位置**算出来 ✓（part svg 里 `id="connectorNpin"` 的圆心 ✓，
    #   与布线器算 EPAD 焊盘用的是同一套数学 ✓），再跟它**声称插进的孔** ✗ 比 ✓
    #   ⇒ Δ 应当 ≈ 0 ✓；**Δ 大 = "脚悬空"** ✗（正是用户一眼看到的 ✓）。
    _ph = {}                       # 脚 id → 它插进的孔 id ✓（从 <connector> 下的 <connect> 读 ✓）
    _pleg = {}                     # 脚 id → sketch 里有没有 <leg>（腿末端覆盖 ✓）
    _legs = {}                     # ★ 脚 id → (腿的点（实例局部 ✓）, 颜色, 线宽) ✓ —— 见下 ✓
    for _cn in bv.iter():
        if tag(_cn) != "connector":
            continue
        _cid0 = _cn.get("connectorId")
        for _cs2 in _cn.iter():
            if tag(_cs2) == "connect" and _cs2.get("layer") == "breadboardbreadboard":
                _ph[_cid0] = _cs2.get("connectorId")
        _lg = next((_k for _k in _cn if tag(_k) == "leg"), None)
        _pleg[_cid0] = _lg is not None
        if _lg is not None:
            # ★★★ 2026-10-08 用户报 ✗：「v104 中 R1.pin1 插在了 Breadboard1.pin16I，
            #   而幻灯片里的 R1 插的点显然与原图不一致」✓ —— **腿根本没画** ✓：
            #   本渲染器只画零件 svg 自带的那截**直腿** ✗（`resistor_220.svg` 里的
            #   `connector1leg` 只有 1.455 用户单位 ✓），而 Fritzing 是**另画一条腿**的 ✓。
            #   Fritzing 口径（源码 `connectoritem.cpp` ／ `sketchwidget.cpp` ✓，已核 ✓）：
            #     · 连接器的 `pos` = 零件 svg 里 `connectorNleg` **靠近本体的那一端** × k ✓
            #       （`setRubberBandLeg`：「p1 is always the start point closest to the body」✓
            #        ＋ `calcLeg` 里"取离 viewBox 中心近的那个端点" ✓）—— 实测正是 sketch 里
            #       存的 `<connector><geometry>` ✓（R1：40.007×0.9 = 36.0063 ✓ 逐位相符 ✓）；
            #     · 存的 `<leg><point>` 是**相对那个 pos 的偏移** ✓（`setLegPolygon(..., relative)`
            #       ✓ / `changeLegForCommand(..., true, "load")` ✓）⇒ 腿 = pos → pos+每个点 ✓；
            #     · 单位**就是 sketch 单位** ✓（**不要再乘 k** ✗ —— 实测 617/640 条腿里
            #       600 条按"原样"落孔、Δ<0.35 单位 ✓，乘 k 那条只有 23 条对 ✓）；
            #     · 线宽 = svg 那条腿上写的 `stroke-width` × k ✓（`m_legStrokeWidth` ✓；
            #       缺省 29mil ✓ = Fritzing 的 `getStrokeWidth(element, 0.029)` ✓）；
            #     · ★ 零件 svg **自带的那截腿不画** ✗ —— Fritzing 把那个元素**改成 `<g>`** ✓
            #       （`element.setTagName("g") // don't want this element to actually be drawn` ✓）。
            #   ★ 项目里 151 个 fzz、834 条腿，**全是 2 个点、没有非空 bezier** ✓（只 R / C 两种件 ✓）
            #     ⇒ 直线段就够 ✓；★ 万一将来出现 3 点或 bezier ⇒ **当场报出来** ✗（不静默画直 ✓）。
            _cg = next((_k for _k in _cn if tag(_k) == "geometry"), None)
            _pp = [(num(_p.get("x")), num(_p.get("y"))) for _p in _lg if tag(_p) == "point"]
            if _cg is not None and len(_pp) >= 2:
                _gx0, _gy0 = num(_cg.get("x")), num(_cg.get("y"))
                _legs[_cid0] = ([( _gx0 + _qx, _gy0 + _qy) for _qx, _qy in _pp],
                                len(_pp),
                                sum(1 for _b in _lg if tag(_b) == "bezier"
                                    and (_b.text or "").strip()))
    # ★★★ 2026-09-27 **修** ✓（用户报"preview 是错的"✗，而 Fritzing 里 LED2 位置正确 ✓）：
    #   脚位**参考点**必须走完 svg 的祖先 `transform` 链 ✓ —— 上一版只认 `<circle>` 且直接用
    #   `cx/cy` ✗ ⇒ ① 焊盘画在 `<rect>` 里的件（LED2/J1/J2/L1/C1/C2/R1 ✓）**一个都查不到** ✗
    #   ⇒ 全报"未验证"✗；② 就算查得到，忽略 `translate` 组也会得到**假坐标** ✗。
    #   现在统一用 `part_box.pin_points` ✓（**一份实现** ✓，与算本体包围盒同一套矩阵数学 ✓）。
    _pts, _badref = {}, []
    try:
        _pts, _badref = PB.pin_points(ET.fromstring(txt))
    except Exception as _ex:       # ★ 有些 svg 带 DOCTYPE 实体 ⇒ 解析不了也要**明说** ✓（不静默 ✗）
        _badref = ["<XML 解析不了：%s>" % _ex]
    _nchk = _bad = 0
    _unv = 0
    _legn = 0                      # ★ 有 <leg> 覆盖的脚（**现在按 sketch 的腿画** ✓，见下 ✓）
    _nleg = 0                      # ★ 真画出来的腿有几条 ✓
    _legmax = 0.0                  # ★ 腿末端与"声称插的孔"的最大 Δ ✓（这条才是用户看的那件事 ✓）
    _legbad = 0
    _maxd = 0.0                    # ★ 最大 Δ 也要报 ✓（"✓"必须带数字 ✓，不是口号 ✓）
    for _cid2, _hid2 in sorted(_ph.items()):
        _p2 = _pts.get("%spin" % _cid2)
        _xy2 = BC.hole_xy(_hid2) if _hid2 else None
        if _p2 is None or _xy2 is None:
            _unv += 1
            continue               # ★ 认不出 ⇒ **记入"未验证"** ✓（不许静默跳过 ✗）
        # ★★★ 2026-09-27 修 ✓（用户 2026-09-27 报：「Fritzing 里看没有任何错误」✓、
        #   并建议"不改图，改检查程序" ✓）：
        #   Fritzing 画腿用的是 **sketch 里 `<connector>` 下存的 `<leg><point>`** ✓
        #   —— 我们那次"已批准修正"正是把**声称的孔**与**腿末点**一起改的 ✓
        #   ⇒ 腿被**拉长 1 格去够新孔** ✓ ⇒ Fritzing 里看着完全正常 ✓。
        #   而这里原来**只读零件 svg** ✗（算的是"没拉长的原腿"✗）⇒ 凭空差 1 格 ⇒ **误报** ✗
        #   （实测：C1 两条腿都是 18.0031 ✓；C2 是 18.0033 / 27.0033 ✗ —— 差 9 ✓）。
        #   ⇒ 有 `<leg>` 覆盖的脚：**按 sketch 存的腿画** ✓（Fritzing 口径 ✓）、
        #     ✗ 不再拿零件 svg 里那截原腿去对账 ✗（那截腿 Fritzing 根本不画 ✓）。
        #     ★★ 2026-10-08 补 ✓：**腿的末端**要跟"声称插的孔"对账 ✓ —— 那才是
        #     用户一眼看的那件事 ✓（原来只报个数 ✗ ⇒ 腿画不到孔上也看不出来 ✓）。
        if _pleg.get(_cid2):
            _legn += 1
            continue
        _nchk += 1
        _lu, _lv = _p2[0] * k, _p2[1] * k
        _padx = num(g.get("x")) + m[0] * _lu + m[2] * _lv + m[4] - _subx
        _pady = num(g.get("y")) + m[1] * _lu + m[3] * _lv + m[5] - _suby
        _dx, _dy = _padx - _xy2[0], _pady - _xy2[1]
        _dd = (_dx * _dx + _dy * _dy) ** 0.5
        _maxd = max(_maxd, _dd)
        # ★★ 阈值收紧到 **0.3 单位（0.08mm）** ✓（2026-09-27 ✓）：原来 1.0 ✗ ⇒ LED2 那种
        #   **1.29 单位**的错**差点漏掉** ✗（只超出 29% ✗）。**对的件实测 Δ=0.00** ✓
        #   （U1/D3/J1/J2/L1 ✓）⇒ 阈值可以贴地 ✓；"差一点点"在这里是**可算**的，不该给宽容 ✗。
        if _dd > 0.3:
            _bad += 1
            print("      ✗ 脚 %-16s 画在 (%7.1f,%7.1f)，孔 %-8s 在 (%7.1f,%7.1f)"
                  " ⇒ Δ=%.2f 单位 (%.2f mm) **悬空** ✗"
                  % (_cid2, _padx, _pady, _hid2, _xy2[0], _xy2[1], _dd, _dd * 25.4 / 90.0))
    if _badref:
        print("      ⚠ 参考点没能算出来的：%s" % "；".join(_badref[:6]))
    a, b, c, d = k * m[0], k * m[1], k * m[2], k * m[3]
    e, f = num(g.get("x")) + m[4] - _subx, num(g.get("y")) + m[5] - _suby
    # ★★★ 2026-09-27 **证据推翻了我昨天的"撤掉"** ✗✓：**viewBox 的原点必须减** ✓ ——
    #   早先我把 `translate(-minX,-minY)` 撤了 ✗，理由是"这只是坐标重映射、不是摆视口" ✗ ——**错** ✓。
    #   硬证据 ✓（机验 ✓，不是推理 ✗）：`LED2` 的 `viewBox="1.03 0 …"` ⇒ 四个脚**一律**偏
    #   **+1.29 单位 = 1.03 × 1.25** ✓✓（x 偏、y 不偏 ✓ = min-y 为 0 ✓）—— 偏移量与 `min×k`
    #   **逐位相符** ✓ ⇒ 真凶就是它 ✓；减掉后四脚 Δ=0.00 ✓✓。
    #   ★ 判据：**偏移量必须等于 min×k** ✓（"差一点点"在这里是**可算**的 ✓，不是审美 ✗）。
    # ★★★ 2026-10-08：**按 sketch 存的腿画出来** ✓（用户报「R1 插的点显然与原图不一致」✓）——
    #   见上面收集 `_legs` 时那段 Fritzing 口径 ✓。要点：
    #     · 腿的点**已经是 sketch 单位** ✓ ⇒ 用**不含 k** 的那个矩阵 ✓（`m[0..3]` 原样 ✓、
    #       平移与零件那层**同一个** e/f ✓ —— 零件那层的 e/f 已经把 `k·viewBox 原点` 减掉了 ✓）；
    #     · 零件 svg **自带的那截腿**要**改成 `<g>`**（= 不画 ✓）—— Fritzing 就是这么干的 ✓
    #       （`initLegInfoAux`：`setTagName("g")` ✓）；✗ 不改的话会看见**两截腿** ✓；
    #     · 线宽 = 那截腿上写的 `stroke-width × k` ✓、颜色照抄 ✓（缺省 #8C8C8C / 29mil ✓）。
    _body = inner(txt)
    _gl = []
    for _cid3, (_poly, _npt, _nbz) in sorted(_legs.items()):
        _lt = re.search(r'<line\b[^>]*\bid="%sleg"[^>]*/?>' % re.escape(_cid3), _body)
        _col, _sw = "#8C8C8C", 0.029 * 90.0                # ★ 缺省：Fritzing 的 29mil ✓
        if _lt:
            _mc = re.search(r'\bstroke="([^"]+)"', _lt.group(0))
            _mw = re.search(r'\bstroke-width="([\d.]+)"', _lt.group(0))
            if _mc:
                _col = _mc.group(1)
            if _mw:
                _sw = float(_mw.group(1)) * k              # ★ 用户单位 → sketch 单位 ✓
            # ★ 那截自带腿**别再画** ✗（换成 `<g>` ＝ Fritzing 的做法 ✓）
            _body = _body.replace(_lt.group(0), re.sub(r"^<line\b", "<g", _lt.group(0)))
        if _npt > 2 or _nbz:
            print("      ⚠ %s.%s 的腿是 **%d 个点 / %d 段 bezier** ✗ ⇒ 只按**直线段**画 ✓"
                  "（本项目实测 834 条腿全是 2 点、无 bezier ✓）" % (ttl, _cid3, _npt, _nbz))
        _gl.append('<polyline data-pd-leg="1" points="%s" fill="none" stroke="%s" '
                   'stroke-width="%.4f" stroke-linecap="round"/>'
                   % (" ".join("%.4f,%.4f" % _q for _q in _poly), _col, _sw))
        _nleg += 1
        _hid3 = _ph.get(_cid3)
        _xy3 = BC.hole_xy(_hid3) if _hid3 else None
        if _xy3 is not None:
            _ex3, _ey3 = _poly[-1]
            _d3 = ((num(g.get("x")) + m[0] * _ex3 + m[2] * _ey3 + m[4] - _subx - _xy3[0]) ** 2
                   + (num(g.get("y")) + m[1] * _ex3 + m[3] * _ey3 + m[5] - _suby - _xy3[1]) ** 2) ** 0.5
            _legmax = max(_legmax, _d3)
            if _d3 > 0.35:
                _legbad += 1
                print("      ✗ %s.%s 的腿末端落在 (%7.2f,%7.2f)，而它声称插的 %s 在 (%7.1f,%7.1f)"
                      " ⇒ Δ=%.2f 单位 (%.2f mm) ✗"
                      % (ttl, _cid3, _ex3, _ey3, _hid3, _xy3[0], _xy3[1], _d3, _d3 * 25.4 / 90.0))
    lay_body.append('<g transform="matrix(%.6f %.6f %.6f %.6f %.6f %.6f)">%s</g>'
                    % (a, b, c, d, e, f, _body))
    if _gl:
        # ★ 腿画在零件**之后** ✓（Fritzing 里连接器是零件的子项、画在本体之上 ✓）
        lay_body.append('<g transform="matrix(%.6f %.6f %.6f %.6f %.6f %.6f)">%s</g>'
                        % (m[0], m[1], m[2], m[3], e, f, "".join(_gl)))
    # ★ 自检**必须在腿画完之后**再打 ✗（腿的条数与末端 Δ 都是那一步算出来的 ✓ ——
    #   第一版把这个 print 放在前面 ⇒ 明明画了 2 条腿却报"0 条" ✓，实测栽过 ✓）。
    if _nchk or _unv or _legn:
        _verdict = ("✓ 全落在孔上 ✓（最大 Δ=%.2f 单位）" % _maxd if not _bad else
                    "✗ **%d 个悬空** ✗（最大 Δ=%.2f 单位）" % (_bad, _maxd)) \
            if _nchk else "（本次没有需要几何对账的脚）✓"
        print("      脚位自检：几何对账 %d 个脚 ⇒ %s ｜按 sketch 的 <leg> 画的腿 %d 条 %s"
              "｜认不出/未验证 %d 个 %s"
              % (_nchk, _verdict, _nleg,
                 "✓（末端都对上声称的孔 ✓，最大 Δ=%.2f 单位 ✓）" % _legmax if not _legbad
                 else "✗ **%d 条末端对不上孔** ✗（最大 Δ=%.2f 单位）" % (_legbad, _legmax),
                 _unv, "✓" if not _unv else "✗（这些件只能靠人眼 ✓）"))

xs, ys = [0.0, 576.0], [0.0, 189.0]
for x1, y1, x2, y2, _c in wires:
    xs += [x1, x2]
    ys += [y1, y2]
# ★★ 图例文字也要算进画布 ✓（2026-10-08 ✓）：它们的盒子在色条**右边** ✓ ⇒ 不加进来
#   就会被 viewBox **裁掉** ✗（实测 `DATA_OUT` 的盒子右缘超出 35 单位 ✓ —— 而画布是按
#   "板 ＋ 导线" 算的 ✓，字从来没算过 ⇒ 这正是"字看不见"的第二半原因 ✓）。
for _t, _txt, _sx, _sy, _lx, _ly, _col, _bw, _bh in _logo_ok:
    xs += [_lx, _lx + _bw]
    ys += [_ly, _ly + _bh]
x0, x1 = min(xs) - 12, max(xs) + 12
y0, y1 = min(ys) - 12, max(ys) + 12
w, h = x1 - x0, y1 - y0
body = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#f7f7f7"/>' % (x0, y0, w, h)]
body += lay_body
# ★★ 2026-10-08 图例文字自检 ✓（用户报过「图例文字都没有显示出来」✗ ⇒ 不许静默 ✗）：
#   ① 画出来几件、都是哪几个字 ✓（对不上就是件本身变了 ✓）；
#   ② 盒内两边的缩放**必须相等** ✓ —— 不等 = 字被拉伸 ✗（件自己的 viewBox 就该是这个比例 ✓）；
#   ③ 跟**同色的色条**对一眼 ✓：字的左缘应当 ≈ 色条末端 ＋ 间隙 ✓（本板实测 9+3 ✓）、
#      盒心该 ≈ 色条 y ✓ ⇒ 这两个数就是"锚点没搞反"的证据 ✓（✗ 不是口号 ✓）。
if _logo_ok or _logo_bad:
    print("✓ 图例文字（`TXT*`）：画出 **%d 件** ✓ %s%s"
          % (len(_logo_ok), "／".join(t[1] for t in _logo_ok) or "（一件都没有 ✗）",
             "" if not _logo_bad else "；✗ 画不出来 %d 件：%s" % (len(_logo_bad), "、".join(_logo_bad))))
    _sk = [t for t in _logo_ok if abs(t[2] - t[3]) > 1e-3]
    print("   ① 盒内缩放**两边相等** = %s%s"
          % ("✓" if not _sk else "✗",
             "" if not _sk else "（%s 被拉伸 ✗）" % "、".join(t[0] for t in _sk)))
    _dx, _dy, _n = [], [], 0
    for _t, _txt, _sx, _sy, _lx, _ly, _col, _bw, _bh in _logo_ok:
        _h_units = _bh                                  # 盒子高（sketch 单位 ✓）
        # ★ 认它那条色条**不能只看颜色** ✗：真跳线用的也是同一套网色 ✓（实测撞过 ✗ ——
        #   板那头有条同色的线 ✓ ⇒ 报出 332 单位那种数字 ✓）
        #   ⇒ 判据 = **同色 ＋ 挨着 ＋ 就在字左边**（Δy ≤ 6 单位、末端离字左缘 0~20 单位 ✓）——
        #   图例的三条几何就是这么定的 ✓（`bb_legend3.py`：色条长 9 ＋ 间隙 3 ✓）。
        _bar = None
        for _w in wires:
            if _w[4] != _col or abs(_w[1] - _ly) > 6.0 or not (0.0 < _lx - _w[2] < 20.0):
                continue
            if _bar is None or abs(_w[1] - _ly) < abs(_bar[1] - _ly):
                _bar = _w
        if _bar is None:
            continue
        _n += 1
        _dx.append(_lx - _bar[2])                      # 字左缘 − 色条末端 ✓（应 ≈ 3 ✓）
        _dy.append(_ly + _h_units / 2 - _bar[1])       # 盒心 − 色条 y ✓
    if _dx:
        print("   ② 跟色条对账：配上 **%d/%d** 条 ✓ ⇒ 字左缘 − 色条末端 = %.2f~%.2f 单位 ✓"
              "（色条线宽 1 ＋ 圆头 1 ⇒ 画出来的间隙还要再小 2 ✓）；"
              "盒心 − 色条 y = %+.2f~%+.2f 单位 ✓（字墨心比盒心高 ~1.2 ⇒ 视觉上就是对齐的 ✓）"
              % (_n, len(_logo_ok), min(_dx), max(_dx), min(_dy), max(_dy)))
    else:
        print("   ② 跟色条对账：⚠ 一件都没配上同色色条 ⇒ 这条自检**没跑** ✗（别当成「过了」✓）")
for x1_, y1_, x2_, y2_, col in wires:
    body.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="%s" '
                'stroke-width="2" stroke-linecap="round"/>' % (x1_, y1_, x2_, y2_, col))
# ★★ 2026-09-27 修 ✓（用户定位 ✗：「preview.svg 的**面包板尺寸错误** ⇒ 看起来不对；
#   我在 Inkscape 里放大就对了」✓）：
#   `width="1800" height="615"` **不带单位** ✗ ⇒ Inkscape/浏览器按 **CSS px** 解释 ✗
#   ⇒ 文档变成 **1800/96 in = 476mm 宽** ✗，而图里的内容只有 **623 单位 = 175.8mm** ✗
#   ⇒ 尺寸声明与实际内容不符 ⇒ 「面包板尺寸错误」✓；按内容看（放大 ✓）就是对的 ✓。
#   ⇒ 现在把 `width/height` 显式写成 **mm** ✓（1 单位 = 25.4/90 mm ✓）。
MMU_ = 25.4 / 90.0
svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
       'viewBox="%.2f %.2f %.2f %.2f">%s</svg>'
       % (w * MMU_, h * MMU_, x0, y0, w, h, "".join(body)))
svgtmp = os.path.splitext(out)[0] + ".svg"
open(svgtmp, "w", encoding="utf-8").write(svg)
print("   预览画布 = %.1f × %.1f mm（板子孔阵 576 单位 = 162.6mm ⇒ 应比它略大 ✓）"
      % (w * MMU_, h * MMU_))

import cairosvg                                                   # noqa: E402
cairosvg.svg2png(url=svgtmp, write_to=out, output_width=round(PXW),
                 output_height=round(PXW * h / w), background_color="white")
print("零件 %d 个 ✓ | 导线 %d 段 ✓ | 画布 %.0f×%.0f 单位" % (len(lay_body), len(wires), w, h))
print("写入 %s（同时留了 %s ✓）" % (out, svgtmp))
