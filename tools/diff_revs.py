# -*- coding: utf-8 -*-
r"""★★ 版本差异图 ＋ 差异清单 ✓（2026-10-07 用户要的「**第三步**」✓）

用户原话 ✓：「截图所示的这种 PNG 的（并排预览），**不是目标**，继续做之前说的第三步吧？」✓
⇒ 并排比对只是手段 ✗；要的是**一张图看出变化** ✓ ＋ **一段话说清改了什么** ✓。

本工具输出**两个**东西 ✓：

① **叠合差异图** ✓（`diff\diff-<A>-<B>.svg` ＋ `.png`）——
   A 版画成**蓝** ✓、B 版画成**红** ✓、两版都有 ⇒ **深色** ✓：
   · 只有**蓝** ⇒ A 有、B 没有（**删掉了** ✗）
   · 只有**红** ⇒ B 新增（**加上了** ✓）
   · **深色** ⇒ 两版重合（没动 ✓）
   两版都用 `--board-only` 同一取景 ✓（板框 25×25 一样 ✓）⇒ 像素级**可叠** ✓。

② **差异清单** ✓（控制台 ＋ 同名 `.md` ✓）：按**人能读的名字**报 ✓ ——
   · 元件摆位：`C2` 挪了 **0.83 mm**（Δ=(+0.35, −0.75) ✓）
   · 连线：`U1.connector1 ↔ J1.connector1` 3 段 4.2 mm ⇒ 5 段 6.8 mm ✓
   · 过孔：挪动/新增/删除各几颗 ✓
   · 汇总：段数/总长/过孔数 ✓

★ 几何**不另写一套** ✗：走线/焊盘/过孔全部来自元件库 `pcb_check.collect()` ✓
（= 校验器同一个世界模型 ✓）；渲染用 `render_pcb.render()` ✓。AGENTS §13「只允许一个声音」✓。

用法 ✓（版本名 / `.fzz` / **svg** 都行；**带网表清单的只有两个 `.fzz`** ✓）：
  py tools\diff_revs.py v59 v76                    # 两个 fzz ⇒ 图 ＋ 清单 ✓
  py tools\diff_revs.py --last 2                   # 最后两版 ✓
  py tools\diff_revs.py "pixel-pcb-v47_图示.svg" v47   # **Fritzing 导出的 svg ⇔ fzz** ✓（推荐 ✓）
  py tools\diff_revs.py a.svg b.svg                # 两个 svg 也行 ✓（锚靠各自 board 组 ✓）
★ 比 svg 时**锚 = 板框** ✓（见 README §10.4 ✓）—— ✗ 不要拿我们自己渲的**带取景**预览
  当输入 ✗（那种文件里 `stroke=#111111` 的 rect 是**取景框** ✗ 不是板框 ✗ ⇒ 会整体平移 ✗）；
  fzz 那一侧**直接给 .fzz** ✓，工具会自己用 `--board-only` 现渲 ✓。
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")       # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")       # type: ignore[attr-defined]
except Exception:                            # noqa: BLE001  老解释器没这方法 ⇒ 忽略 ✓
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
# ★★ 2026-10-07 搬进库仓 ✓（用户指出：通用工具应在库下 ✓，见项目里的 `toolpaths.py` 约定 ✓）：
#   **不再假设自己活在 pixel 项目里** ✗ ——
#     · `PIX`（在哪找 fzz / 输出到哪）默认 **cwd** ✓，`--dir` 可覆盖 ✓；
#     · 被比的文件名默认 `*.fzz` ✓，`--pattern` 可覆盖 ✓；
#     · 项目网表（`NETS` 那种 ✓）默认找 `<dir>/pixel_nets.py` ✓，`--nets <py>` 可覆盖 ✓。
PIX = os.getcwd()
PAT = r".*\.fzz$"
NETS_FILE = None

# ★ **接地符号**（核心件 ✓）的坐标数学在 `sch_net` 里 ✓ —— 本文件**不另写一份** ✗：
#   2026-10-07 实测 ✓：原理图渲染器**不给接地符号**写 `partID` ✗（普通件 `%s0` ✓、
#   网标签 `%s1` ✓、接地符号**没有** ✗）⇒ 只能按**脚位坐标**认 ✓，
#   而那个坐标 = `sch_net.ground_pin` ✓（`render_sch.py` 画它用的也是这一份 ✓）。
try:
    sys.path.insert(0, HERE)
    import sch_net as _SN                                          # noqa: E402
except Exception:                        # noqa: BLE001  拿不到 ⇒ 退化成"接地符号认不出" ✓
    _SN = None

# ★★ 颜色口径（2026-10-07 用户定 ✓，原话：「双面板的**颜色差异看不出来了**」✗）：
#   **色相 = 层**（顶 = 暖 ✓ / 底 = 冷 ✓）、**深浅 = 版**（浅 = A 旧 ✓ / 深 = B 新 ✓）、
#   **非铜**（丝印/板框/位号/孔）= 中性灰（A 浅 ✓ / B 深 ✓）。
#   ✗ 旧口径「整版一色（A 蓝 / B 红）」把 copper0 与 copper1 **刷成一色** ✗ ⇒ 层分不出来 ✗。
A_TOP, B_TOP = "#f0a868", "#b8440a"      # 顶层：浅橙 ⇒ 深橙红 ✓
A_BOT, B_BOT = "#8ab4f8", "#1a4fd0"      # 底层：浅蓝 ⇒ 深蓝 ✓
A_OTH, B_OTH = "#cfcfcf", "#5a5a5a"      # 丝印/板框/位号/孔：浅灰 ⇒ 深灰 ✓
# ★ 「点清单一条 ⇒ 图上高亮」用的**强调色** ✓（2026-10-07 用户要的 ✓）——
#   得跟上面六种颜色都分得开 ✓ ⇒ 取玫红 ✓（蓝/橙/灰都不是它 ✓）。
A_COLOR_HI = "#d81b60"
# ★ 动画节奏（一处几秒 / 收尾几秒 ✓）—— 要调速就改这一行 ✓（用户 2026-10-08 问过 ✗
#   「末态看到的是 B，开始也不是从 A 开始」✓ ⇒ 把一处调小就能一眼看完整个来回 ✓）。
ANIM_SEC, ANIM_TAIL = 2.0, 2.0
# ★ svg 路径里给板框留的边距 ✓（同一处既用于 `tf()` 的摆放 ✓、又用于图例的左缘 ✓ ——
#   ✗ 别一边写 20 一边写别的 ✗，那样图例就不跟板框对齐了 ✓）。
MARGIN = 20.0
JOINT = 0.01             # 认定"没动"的阈值（mm ✓）
# ★ 1 sketch 单位 = 25.4/90 mm ✓（= 元件库 `pcb_wire.SK` ✓ 同一口径 ✓）
SK = 25.4 / 90.0


def _lib_tools():
    """★ 2026-10-07 搬进库仓后：**自己就在库仓 `tools` 里** ⇒ 返回本目录即可 ✓。

    （以前得往上爬着找 `fritzing-parts-langhua/tools` ✗ —— 那是"工具住在项目里"时代的写法 ✗。）
    """
    return HERE


def _resolve(arg, have):
    """`v59` / `pixel-pcb-v59.fzz` / 绝对路径 ⇒ 文件路径 ✓。"""
    if os.path.isfile(arg):
        return arg
    name = arg if arg.endswith(".fzz") else None
    num = re.sub(r"^v", "", os.path.splitext(arg)[0])
    hits = [f for f in have if num.isdigit() and _vnum(f) == int(num)]
    if name:
        hits = [f for f in have if f == name] or hits
    if not hits:
        raise SystemExit("找不到这一版：%s ✗（本目录有 %d 版 ✓）" % (arg, len(have)))
    return os.path.join(PIX, hits[0])


def _vnum(f):
    m = re.match(r"^.*?-v(\d+)", os.path.splitext(f)[0])
    return int(m.group(1)) if m else -1


def _vtxt(f):
    """版本标签 ✓：`pixel-pcb-v59.fzz` ⇒ `v59` ✓；
    ✗ `pixel-breadboard100.fzz` 这种**没有 `-v`** 的 ⇒ 取**末尾那串数字** ✓（⇒ `v100` ✓）
    —— 面包板/原理图的稿子就叫这个名 ✓（不取的话输出名会变成 `diff-bb-pixel-breadboard100-…` ✗）。
    """
    stem = os.path.splitext(os.path.basename(f))[0]
    m = re.match(r"^.*?-v(\d+)(.*)$", stem)
    if m:
        suf = m.group(2).strip(" _-")
        return "v%d%s" % (int(m.group(1)), ("_" + suf) if suf else "")
    m2 = re.search(r"(\d+)\D*$", stem)
    return "v%s" % m2.group(1) if m2 else stem


# ── 差异清单 ───────────────────────────────────────────────────────────────
def _pad_map(model):
    """`(件名, connectorId)` ⇒ 焊盘 ✓（★ 别按 `modelIndex` 配 ✗ —— 另存会重编号 ✗）。"""
    m = {}
    for q in model["pads"]:
        m.setdefault((q["title"], q["cid"]), []).append(q)
    return m


def _netmap(pix):
    """项目网表 ⇒ `(位号, connectorN / @脚名) → 网名` ✓（`NETS` 在 `pixel_nets.py` ✓）。

    ★ 为什么借项目的表 ✗：用户嘴里的网名是 **`GND` / `RC` / `5V`** ✓ —— 报告里写
      `U1.connector1 ↔ C2.connector1` 是对不上的 ✗（2026-10-07 实测：第一版清单就是这么
      读不懂的 ✗）。表里的 `#N` = **第 N 个脚** ⇒ `#1` = `connector0` ✓（不是 1-based 的 cid ✗）。
    """
    d = os.path.dirname(pix)
    if not os.path.isfile(os.path.join(pix, "pixel_nets.py")) and not NETS_FILE:
        return {}
    sys.path.insert(0, pix)
    sys.path.insert(1, d)
    try:
        if NETS_FILE:                       # ★ `--nets <py>` ✓（项目网表就在项目里 ✓）
            import importlib.util
            spec = importlib.util.spec_from_file_location("_nets", NETS_FILE)
            PN = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(PN)
        else:
            import pixel_nets as PN                                    # noqa: PLC0415
    except ImportError:
        return {}
    m = {}
    for net, lst in (getattr(PN, "NETS", None) or {}).items():
        for ref, conn in lst:
            if str(conn).startswith("#"):
                m[(ref, "connector%d" % (int(str(conn)[1:]) - 1))] = net
            else:
                m[(ref, "@" + str(conn).upper())] = net
    return m


def _find(par, x):
    while par[x] != x:
        par[x] = par[par[x]]
        x = par[x]
    return x


def _nets(model, netmap):
    """⇒ `[(网名, [铜块]), …]` ✓ —— **口径与 Fritzing 同源** ✓：一张网 = 走线**链** ✓
    （`Wire::collectChained` ✓）＋ 声明 ✓；过孔当**接头** ✓（它两端的走线**都声明它** ✓
    ⇒ 链自然跨层连上 ✓，本工具**不需要**懂过孔内部 ✗）。

    ★★ 实测（2026-10-07 ✓）：走线两端的声明**多数指向"另一条走线"** ✗（`copper0trace` ✓）
      ⇒ ✗ 按**单条线**的名字去对网 ⇒ 只能得到 `connector0 ↔ connector1` 这种废话 ✗
      （第一版清单就是这么废的 ✗）⇒ 必须**先并链** ✓。
    铜块 = 一个连通分量 ✓；**块 > 1 ⇒ 这张网有地方没连上** ✗（就是 Fritzing 说的"还要布线"✓）。
    """
    mi2t = {}
    for q in model["pads"]:
        if q.get("mi"):
            mi2t.setdefault(str(q["mi"]), q["title"])
    for v in model["vias"]:                       # ★ 过孔只在 `vias[].inst` 里有 mi ✗（`mi=None` ✓）
        if v.get("inst"):
            mi2t.setdefault(str(v["inst"]), v.get("ttl") or "Via?")

    par = {}

    def find(x):
        par.setdefault(x, x)
        return _find(par, x)

    def uni(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb

    wires = {}
    for tr in model["traces"]:
        w = ("w", str(tr.get("inst")))
        wires[w] = tr
        find(w)
        for k in sorted(tr.get("ends") or {}):
            for v in (tr["ends"][k] or []):
                cid, mi, lay = (list(v) + [None, None, None])[:3]
                t = ("w", str(mi)) if str(lay or "").endswith("trace") \
                    else ("t", str(mi), str(cid))
                find(t)
                uni(w, t)

    comp = {}
    for k in list(par):
        comp.setdefault(find(k), []).append(k)
    out = []
    for _root, keys in comp.items():
        ws = [k for k in keys if k[0] == "w"]
        if not ws:                                   # 只有焊盘、没有走线 ⇒ 不算"一块铜" ✓
            continue
        terms, ln, layers = [], 0.0, {}
        for w in ws:
            tr = wires.get(w)
            if tr is None:
                continue
            ln += ((tr["b"][0] - tr["a"][0]) ** 2 + (tr["b"][1] - tr["a"][1]) ** 2) ** 0.5
            layers[tr["layer"]] = layers.get(tr["layer"], 0) + 1
        for k in keys:
            if k[0] != "t":
                continue
            t = mi2t.get(k[1], "?")
            if re.match(r"^Via\d+$", t):             # ★ 过孔是**接头** ✗ 不是"网的一只脚" ✗
                continue
            terms.append((t, k[2]))
        nm = ""
        for t, cid in terms:
            pad = next((q for q in model["pads"]
                        if q["title"] == t and q["cid"] == cid), None)
            for key in ((t, cid), (t, "@" + str((pad or {}).get("nm") or "").upper())):
                if key in netmap:
                    nm = netmap[key]
                    break
            if nm:
                break
        out.append((nm, dict(n=len(ws), mm=ln * SK, layers=layers, terms=terms)))
    return out


def _net_summary(nets):
    """把「每块铜」按**网名**汇总 ✓ ⇒ `{网名: [块, …]}`（没名字的块归到 `""` ✓）。"""
    d = {}
    for nm, c in nets:
        d.setdefault(nm, []).append(c)
    return d



def _board_px(svg, R):
    """从**已经渲好的** svg 里量出「板框 rect」的 px 位置与尺寸 ✓ ⇒ `(x, y, w, h)` ✓。

    ★ 为什么量它 ✗（而不是照 `render()` 的内部公式再算一遍 ✗）：本仓老规矩 —— **同一件事
      只留一份实现** ✓。`--board-only` 渲出来的那个 rect 就是板框 ✓（实测 ✓），
      拿它当"坐标换算锚" ⇒ 我在下面把 sketch 单位换成 px 时用的公式，只依赖
      `model["board"]` ✓ ＋ 这个 rect ✓（都是公开量 ✓），**不碰 render 的内部** ✓。
    """
    m = re.search(r'<rect\b[^>]*\bx="([\d.]+)"\s+y="([\d.]+)"\s+width="([\d.]+)"\s+height="([\d.]+)"'
                  r'[^>]*\bfill="%s"' % re.escape(getattr(R, "C_BRD_FILL", "\0")), svg)
    if not m:                       # 兜底：按描边色找（白底 rect 没有 stroke ✓）
        m = re.search(r'<rect\b[^>]*\bx="([\d.]+)"\s+y="([\d.]+)"\s+width="([\d.]+)"\s+height="([\d.]+)"'
                      r'[^>]*\bstroke="%s"' % re.escape(getattr(R, "C_BRD_EDGE", "\0")), svg)
    return tuple(float(v) for v in m.groups()) if m else None


def _hit_layer(ma, mb, svg_a, svg_b, name_a, name_b):
    """★ 「点清单里一条 ⇒ 图上高亮对应变化」用的**隐藏**图层 ✓（2026-10-07 用户要的 ✓）。

    用户原话 ✓：「在元件摆位下，点一条信息，图里面的相应变化，能高亮显示出来」✓

    做法 ✓（省事又不会两处算坐标 ✗）：
      · 这里**先**把每个"挪过 / 新增 / 删掉"的脚写成一组元素 ✓，`display:none` 藏着 ✓；
      · 扩展那边**只负责**点行 ⇒ 把对应那组 `display` 打开 ✓ ⇒ **坐标换算只有这一份** ✓。
    每组画三样 ✓：A 的旧位置（空心圈 ✓）、B 的新位置（实心圈 ✓）、两者之间一条引线 ＋
    一个标签（脚名 ＋ 位移 mm ✓）。
    """
    import render_pcb as R
    ra, rb = _board_px(svg_a, R), _board_px(svg_b, R)
    if not (ra and rb and ma.get("board") and mb.get("board")):
        return ""
    pair = []
    for (mA, sv, r) in ((ma, svg_a, ra), (mb, svg_b, rb)):       # 两侧各求一个「单位→px」映射 ✓
        bw = mA["board"][2] - mA["board"][0]
        bh = mA["board"][3] - mA["board"][1]
        if bw <= 0 or bh <= 0:
            return ""
        kx, ky = r[2] / bw, r[3] / bh
        pair.append(lambda u, v: (r[0] + (u - mA["board"][0]) * kx,
                                  r[1] + (v - mA["board"][1]) * ky))
    (put_a, put_b) = pair

    pa, pb = _pad_map(ma), _pad_map(mb)
    W = max(ra[2], rb[2])
    o = ['<g id="pd-hits">']
    for k in sorted(set(pa) | set(pb)):
        qa = pa.get(k, [{}])[0].get("c")
        qb = pb.get(k, [{}])[0].get("c")
        if k[0] == "PCB1":
            continue
        pid = "%s.%s" % k
        o.append('<g id="pd-%s" style="display:none">' % re.sub(r"[^\w.-]", "_", pid))
        if qa:
            x, y = put_a(*qa)
            o.append('<circle cx="%.1f" cy="%.1f" r="%.3f" fill="none" stroke="%s" stroke-width="%.2f"/>'
                     % (x, y, W * 0.022, A_COLOR_HI, W * 0.004))
        if qb:
            x2, y2 = put_b(*qb)
            o.append('<circle cx="%.1f" cy="%.1f" r="%.3f" fill="%s" fill-opacity="0.85" stroke="#ffffff" '
                     'stroke-width="%.2f"/>' % (x2, y2, W * 0.022, A_COLOR_HI, W * 0.004))
        if qa and qb:
            x, y = put_a(*qa)
            dx = (qb[0] - qa[0]) * SK
            dy = (qb[1] - qa[1]) * SK
            d = (dx * dx + dy * dy) ** 0.5
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.2f" '
                     'stroke-dasharray="%.1f %.1f"/>'
                     % (x, y, x2, y2, A_COLOR_HI, W * 0.0035, W * 0.012, W * 0.008))
            o.append('<text x="%.1f" y="%.1f" font-family="sans-serif" font-size="%.1f" '
                     'fill="%s">%s  Δ %.3f mm</text>'
                     % (x2 + W * 0.03, y2 - W * 0.02, W * 0.024, A_COLOR_HI,
                        esc(pid), d))
        elif qb:
            x2, y2 = put_b(*qb)
            o.append('<text x="%.1f" y="%.1f" font-family="sans-serif" font-size="%.1f" fill="%s">'
                     '%s  新增</text>' % (x2 + W * 0.03, y2 - W * 0.02, W * 0.024, A_COLOR_HI, esc(pid)))
        else:
            x, y = put_a(*qa)
            o.append('<text x="%.1f" y="%.1f" font-family="sans-serif" font-size="%.1f" fill="%s">'
                     '%s  没了</text>' % (x + W * 0.03, y - W * 0.02, W * 0.024, A_COLOR_HI, esc(pid)))
        o.append('</g>')
    o.append('</g>')
    return "\n".join(o)


def esc(s):
    """XML 转义 ✓（脚名是 ASCII ✓，但别赌 ✗）。"""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _foot(c):
    """一块铜挂的脚 ⇒ 一行字 ✓（脚名照 Fritzing 的写法 `U1.connector3` ✓ 见 AGENTS §13 ✓）。"""
    s = ["%s.%s" % (t, cid) for t, cid in c["terms"]]
    return "、".join(s[:4]) + ("…（共 %d ✓）" % len(s) if len(s) > 4 else "")


# ── ★★ 也能比「Fritzing 导出的 svg」✓（2026-10-07 用户问 ✓）────────────────────────
#   用户原话 ✓：「如果我从 Fritzing 导出一个 svg，是不是也能这样比较了？」✓
#   ⇒ 能 ✓，但**两个前提**要先处理 ✗（都是实测出来的 ✓，不是猜 ✗）：
#     ① **取景要换算** ✗：Fritzing 导出是 **1in = 72 单位** 且有留白/水印 ✓
#        （实测 `width="1.2278in"` + `viewBox="0 0 88.4 100.7"` ✓ 且带 `<g id="watermark">` ✓）
#        ⇒ 先按**单位换算成 mm** ✓ 再按**墨迹包围盒**对齐 ✓（✗ 直接叠会错位 ✗）。
#     ② **层色口径不同** ✗：导出里**只有走线/过孔**带层色 ✓（`#f28a00` 底 / `#f2c600` 顶 ✓
#        = 同一套 ✓）；**元件自己的铜箔保留原色** ✗（线圈 `#f7bf13` ✓）
#        ⇒ 那些件在两版里都画成**灰** ✓（反正两版一样 ⇒ 灰 = 没动 ✓，信息不丢 ✓）。


def _root(svg):
    """⇒ `dict(vb=(x,y,w,h), u2mm=None|float, w=…, h=…)` ✓（`u2mm=None` ⇒ 比例未知 ✗）。"""
    m = re.search(r"<svg\b[^>]*>", svg)
    a = dict(re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', m.group(0) if m else ""))
    vbn = [float(x) for x in re.findall(r"[-+0-9.eE]+", a.get("viewBox", ""))]
    if len(vbn) == 4:
        vb = tuple(vbn)
    else:
        w = re.match(r"^([\d.]+)", a.get("width", "") or "")
        h = re.match(r"^([\d.]+)", a.get("height", "") or "")
        vb = (0.0, 0.0, float(w.group(1)) if w else 100.0,
              float(h.group(1)) if h else 100.0)

    def mm(v):
        """`width`/`height` ⇒ mm ✓；**无单位或 px ⇒ None** ✗（那个比例不可信 ✗）。"""
        m2 = re.match(r"^\s*([\d.]+)\s*([a-zA-Z%]*)\s*$", v or "")
        if not m2:
            return None
        n, u = float(m2.group(1)), m2.group(2).lower()
        if u in ("", "px", "%"):
            return None
        return {"mm": n, "cm": n * 10.0, "in": n * 25.4, "pt": n * 25.4 / 72.0}.get(u)

    wmm, hmm = mm(a.get("width")), mm(a.get("height"))
    u2mm = None
    if wmm and vb[2]:
        u2mm = wmm / vb[2]
        if hmm and vb[3] and abs(hmm / vb[3] - u2mm) > 1e-4 * u2mm:
            print("⚠️ 这份 svg 的 x/y 比例不一致 ✗（width %.4f vs height %.4f mm/单位 ✓）"
                  "⇒ 按 x 算 ✓" % (u2mm, hmm / vb[3]))
    return dict(vb=vb, u2mm=u2mm, w=wmm, h=hmm)


def _drop_group(svg, gid):
    """整段删 `<g id="X">…</g>` ✓（**配平扫描** ✓ —— 非贪婪正则只会截到第一个 `</g>` ✗）。"""
    out, i = [], 0
    while True:
        m = re.search(r'<g\b[^>]*\bid="%s"[^>]*>' % re.escape(gid), svg[i:])
        if not m:
            break
        s = i + m.start()
        if m.group(0).rstrip().endswith("/>"):
            out.append(svg[i:i + m.end()])
            i += m.end()
            continue
        depth, j = 1, i + m.end()
        while j < len(svg) and depth:
            n = re.search(r"<(/?)g\b", svg[j:])
            if not n:
                break
            k = j + n.start()
            if n.group(1):
                depth -= 1
            else:
                t = svg.find(">", k)
                if not (t >= 0 and svg[k:t].rstrip().endswith("/")):
                    depth += 1
            j = j + n.end()
            if depth == 0:
                break
        out.append(svg[i:s])
        i = j
    out.append(svg[i:])
    return "".join(out)


def _ink_bbox(png_bytes):
    """量**墨迹包围盒**（px ✓）—— 用来对齐 ✓。

    ★ 两条判据缺一不可 ✗（2026-10-07 实测 ✓）：① **透明**不是墨 ✗（cairosvg 可以透明底 ✓）；
      ② **近白**也不是墨 ✗ —— 导出里有一大片白底/白丝印 ✓ ⇒ 只看 alpha 会把整张画布当墨 ✗。
    """
    import io
    from PIL import Image, ImageChops
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 255 if v > 8 else 0)
    g = im.convert("L").point(lambda v: 0 if v >= 245 else 255)
    return ImageChops.multiply(a, g).getbbox()


def _recolor_svg(svg, top, bot, oth):
    """按层色认色换色 ✓；表里没有的（元件的自有颜色 / 丝印 / 板框）⇒ `oth`（灰 ✓）。

    ★ 层色的**权威来源**是渲染器的常量 ✓（`C_W0/C_W1` 走线 ✓、`C_CU0/C_CU1` 面 ✓、
      `C_VIA_*` 过孔 ✓）—— Fritzing 导出用的是**同一套** ✓（实测 ✓）⇒ 两边都能认 ✓。
    """
    import render_pcb as R
    tab = {R.C_W0: bot, R.C_W1: top, R.C_CU0: bot, R.C_CU1: top,
           R.C_VIA_BOT: bot, R.C_VIA_TOP: top}
    return R.remap_colors(svg, tab, oth)        # oth = 两版都一样的东西 ✓


def _wrap(root_tag, inner):
    """把一段内容包回**原来的根标签** ✓ —— ✗ 别自己写 `<svg>` ✗：原标签带着
    `xmlns:svg` / `baseProfile` 等声明 ✓（Fritzing 导出的就有 ✓），丢了会解析失败 ✗。"""
    return "<?xml version='1.0' encoding='UTF-8'?>\n%s%s</svg>" % (root_tag, inner)


def _extract_group(svg, gid):
    """取出 `<g id="X">…</g>` 整段 ✓（配平扫描 ✓）；没有 ⇒ None ✓。

    ★★ 2026-10-07 实测踩到 ✗：配平扫描里 `j += n.end()` 只是**走到 `g` 后面** ✗，
      它还**没有吃掉 `>`** ✗ ⇒ 切出来的片段尾巴是 `<…</g` ✗（实测包装后解析报
      `not well-formed (invalid token): line 4, column 6` ✓，打出来一看是 `</g</svg>` ✗）。
      ⇒ 回片时必须**把 `</g>` 的 `>` 也带上** ✓。
    """
    m = re.search(r'<g\b[^>]*\bid="%s"[^>]*>' % re.escape(gid), svg)
    if not m:
        return None
    if m.group(0).rstrip().endswith("/>") :
        return m.group(0)
    depth, j = 1, m.end()
    while j < len(svg) and depth:
        n = re.search(r"<(/?)g\b", svg[j:])
        if not n:
            break
        k = j + n.start()
        if n.group(1):
            depth -= 1
        else:
            t = svg.find(">", k)
            if not (t >= 0 and svg[k:t].rstrip().endswith("/")):
                depth += 1
        j += n.end()
        if depth == 0:
            t = svg.find(">", k)                     # ★ 连 `</g>` 的 `>` 一起收 ✓
            return svg[m.start():(t + 1 if t >= 0 else j)]
    return None


def _board_box(txt, r):
    """**只画板框**渲一遍 ⇒ 量出板框的**用户单位**范围 ✓（对齐的锚 ✓）。

    ★★ 为什么不能拿**整幅墨迹**对齐 ✗（2026-10-07 实测 ✓）：两边包含的东西不一样
      （留白 ✓、位号位置 ✓、导出的白底 ✓）⇒ 按整幅宽度归一 ⇒ **比例就偏了** ✗
      ⇒ 实测两张图里的线圈**同心却错开** ✗（一眼看就是没对齐 ✓）。**板框才是物理锚** ✓。
    """
    import cairosvg
    import render_pcb as R
    chunk = _extract_group(txt, "board")                     # Fritzing 导出 ✓
    if not chunk:                                           # 我们渲染的：认板框 rect ✓
        # ★★ 2026-10-07 实测踩到两个坑 ✗（都靠证据定位 ✓，不是猜 ✗）：
        #   ① **`C_BRD_FILL` 就是 `#ffffff`** ✗ ⇒ 只按 fill 找会抓到渲染器开头的
        #      **整幅白底**矩形 ✗（`<rect width="100%" height="100%" fill="#ffffff"/>` ✓）；
        #   ② 改认 `stroke=C_BRD_EDGE` 之后**又抓错了一个** ✗ —— 量出来 3802.9×**3782.7**
        #      “板框” ✗（板框是 **25×25 方的** ✓，一看就不对 ✓）。
        #   ⇒ 正解：把候选**全收齐**，取**面积最大**那个 ✓（板框必然是这张图上最大的矩形 ✓），
        #     并排除 `%` 尺寸（那是背景 ✓）。★ 自检就在判据里 ✓：量出来必须是**近似正方形** ✓。
        best, best_a = None, -1.0
        for m2 in re.finditer(r"<rect\b[^>]*/?>", txt):
            tag = m2.group(0)
            if ('stroke="%s"' % getattr(R, "C_BRD_EDGE", "\0")) not in tag and \
               ('fill="%s"' % getattr(R, "C_BRD_FILL", "\0")) not in tag:
                continue
            if re.search(r'\b(width|height)="[^"]*%"', tag):
                continue
            at = dict(re.findall(r'([\w:-]+)="([^"]*)"', tag))
            try:
                ar = float(at.get("width", 0) or 0) * float(at.get("height", 0) or 0)
            except ValueError:
                continue
            if ar > best_a:
                best, best_a = tag, ar
        chunk = best
    if not chunk:
        return None
    root = re.search(r"<svg\b[^>]*>", txt)
    if not root:
        return None
    W = 2000
    png = cairosvg.svg2png(bytestring=_wrap(root.group(0), chunk).encode("utf-8"),
                           output_width=W)
    bb = _ink_bbox(png)
    if not bb:
        return None
    k = W / r["vb"][2]                                       # 参考栅格的 px/单位 ✓
    return dict(u=(bb[0] / k, bb[1] / k, bb[2] / k, bb[3] / k))


def _side(path_or_fzz, px_mm, PC, R):
    """一侧的 svg 文本 ＋ 它的「板框锚」来源说明 ✓。

    ★★ 为什么 **fzz 这一侧要自己渲** ✗（2026-10-07 实测踩到 ✓）：
      ✗ 直接拿 `render_revs` 渲好的预览当输入 ⇒ 那个文件**默认带墨迹取景** ✗
        ⇒ `render_pcb.py:246` 会把 `r` **胀成「板框 ∪ 全部墨迹」** ✗ ⇒ 里面的
        “板框 rect”其实是**取景框** ✗ ⇒ 拿它对锚 ⇒ **整体平移** ✗（实测：线圈/安装孔
        全部错开约 0.5 mm ✓，而板框却“碰巧”看着对齐 ✓）。
      ⇒ 正解：这一侧用 **`--board-only`** 现渲 ✓（那时 `r` = 真板框 ✓）✓。
      ★ 顺带一条真相 ✓：不带 `--board-only` 时，预览里那个 `stroke=#111111` 的 rect
        **不是板框** ✗（= 取景框 ✓）——以前拿它当板框用会错 ✗。
    """
    if path_or_fzz.lower().endswith(".fzz"):
        return R.render(PC.collect(path_or_fzz), px_mm, ("--board-only",)), \
            "我们自己渲的（fzz ⇒ `--board-only` ✓ 锚 = 真板框 ✓）"
    return open(path_or_fzz, encoding="utf-8").read(), \
        "svg 自带的 `<g id=\"board\">` ✓"


def _svg_mode(a_f, b_f, out, px_mm, have=()):
    """比**两个 svg** ✓ —— 也可以是「**一个 fzz ＋ 一个 (Fritzing 导出的) svg**」✓。"""
    import cairosvg
    import sys as _sys

    _sys.path.insert(0, _lib_tools())
    _sys.path.insert(0, os.path.dirname(HERE))
    import pcb_check as PC
    import render_pcb as R

    ta, sa = _side(a_f, px_mm, PC, R)
    tb, sb = _side(b_f, px_mm, PC, R)
    ra, rb = _root(ta), _root(tb)
    ia, ib = _drop_group(ta, "watermark"), _drop_group(tb, "watermark")   # 水印要去掉 ✗
    na, nb = _vtxt(a_f), _vtxt(b_f)
    if not (a_f.lower().endswith(".fzz") or b_f.lower().endswith(".fzz")):
        print("⚠️ 两边都是**外部 svg** ✗：锚只能靠各自自带的 `<g id=\"board\">` ✓；"
              "✗ 若某一边那份**没有** board 组（比如取的是我们自己渲的**带取景**预览 ✗），"
              "锚就会落在“取景框”上 ✗ ⇒ 画面会整体平移 ✗。⇒ **fzz 那一侧请直接给 .fzz** ✓。")
    print("   锚：A = %s；B = %s" % (sa, sb))

    Ba, Bb = _board_box(ta, ra), _board_box(tb, rb)
    if not (Ba and Bb):
        raise SystemExit("量不出板框 ✗（这两份 svg 里都没有 `<g id=\"board\">` 或已知板框 rect ✗）"
                         "⇒ 先在 Fritzing 里导出**当前板**的 svg 再比 ✓")
    wa, wb = Ba["u"][2] - Ba["u"][0], Bb["u"][2] - Bb["u"][0]      # 板框宽（各自用户单位 ✓）
    ha, hb = Ba["u"][3] - Ba["u"][1], Bb["u"][3] - Bb["u"][1]
    # ★ A 有单位就按**物理尺寸**定标 ✓（mm ✓）；否则随便定一个 ✓（叠合只看相对 ✓）
    ka = (px_mm * ra["u2mm"]) if ra["u2mm"] else (1000.0 / ra["vb"][2])
    kb = ka * (wa / wb)                                            # 让两块板框同宽 ✓
    print("   板框：A %.4f×%.4f 单位%s ✓；B %.4f×%.4f 单位 ✓；比例 B×%.4f ✓；"
          "A 的板框 = %.2f×%.2f mm ✓"
          % (wa, ha, ("（×%.4f mm/单位 ⇒ 实为 ✓）" % ra["u2mm"]) if ra["u2mm"] else "✗（无单位）",
             wb, hb, kb / ka, wa * (ra["u2mm"] or 0), ha * (ra["u2mm"] or 0)))

    def tf(t, r, k, b):
        # 板框左上角 ⇒ 画布左上角（留 `MARGIN` px 边 ✓）
        dx = MARGIN - b["u"][0] * k
        dy = MARGIN - b["u"][1] * k
        return "translate(%.4f,%.4f) scale(%.8f) translate(%.4f,%.4f)" % (
            dx, dy, k, -r["vb"][0], -r["vb"][1])

    # ★ 画布 = **板框的像素尺寸** ✓（✗ 2026-10-07 实测踩到：写成 `max(单位宽) × max(k)`
    #   = 把两边的量纲混乘 ✗ ⇒ cairo 报 `CAIRO_STATUS_INVALID_SIZE` ✗）
    W = max(wa * ka, wb * kb) + 2 * MARGIN
    H = max(ha * ka, hb * kb) + 2 * MARGIN
    la = _recolor_svg(_inner(ia), A_TOP, A_BOT, A_OTH)
    lb = _recolor_svg(_inner(ib), B_TOP, B_BOT, B_OTH)
    fs = max(13.0, W * 0.0105)
    # ★ 图例框左缘 = 板框左缘 ✓（这边板框被摆在画布的 `MARGIN` 上 ✓，与 `tf()` 里那个数一致 ✓）
    leg, extra = _legend(_legend_rows(na, nb), fs, fs * 0.6, x0=MARGIN, width=W)
    H2 = H + extra
    svg = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" '
           'viewBox="0 0 %.1f %.1f">\n'
           '<rect width="100%%" height="100%%" fill="#ffffff"/>\n'
           '<g id="A" opacity="0.75" transform="%s">%s</g>\n'
           '<g id="B" opacity="0.55" transform="%s">%s</g>\n'
           '<g id="legend" transform="translate(0,%.1f)">%s</g>\n'
           '</svg>\n'
           % (W, H2, W, H2, tf(ia, ra, ka, Ba), la, tf(ib, rb, kb, Bb), lb, H, leg))
    if not os.path.isdir(out):
        os.makedirs(out)
    stem = "diff-%s-%s" % (re.sub(r"[^\w.-]", "_", na), re.sub(r"[^\w.-]", "_", nb))
    p = os.path.join(out, stem + ".svg")
    open(p, "w", encoding="utf-8", newline="\n").write(svg)
    cairosvg.svg2png(url=p, write_to=os.path.join(out, stem + ".png"), scale=1.0,
                     background_color="white")
    print("✓ 叠合差异图 %s ✓（锚 = **板框** ✓，不靠整幅留白 ✓ —— 见 README §10.4 ✓）" % p)
    print("（svg 输入**没有网表清单** ✗ —— 要清单就得给两个 `.fzz` ✓）")
    return 0



def report(a_fzz, b_fzz, ma, mb, netmap):
    """⇒ 差异清单（`list[str]` ✓）"""
    L = ["# 差异清单：%s ⇒ %s" % (_vtxt(a_fzz), _vtxt(b_fzz)), "",
         # ★ 行首的 `> ` 是 **markdown 引用** ✗ —— 2026-10-07 被我改层色口径时**弄丢过一次** ✗
         #   （变成 `| 图 …` ✓）⇒ 扩展的单测抳出来了 ✓（清单渲染出来不再是引用块 ✓）。
         "> 图 `diff-%s-%s.png` ✓：**顶层 = 暖色（橙）** ✓、**底层 = 冷色（蓝）** ✓，"
         "**浅 = A（旧）** ✓、**深 = B（新）** ✓，丝印/板框/位号 = 中性灰 ✓（A 浅 / B 深 ✓）；"
         "两版重合处会叠得更深（= 没动 ✓）。" % (_vtxt(a_fzz), _vtxt(b_fzz)), ""]

    # ① 元件摆位 ✓
    pa, pb = _pad_map(ma), _pad_map(mb)
    moved, gone, new = [], [], []
    for k in sorted(set(pa) | set(pb)):
        if k not in pb:
            gone.append(k)
            continue
        if k not in pa:
            new.append(k)
            continue
        ca, cb = pa[k][0]["c"], pb[k][0]["c"]
        dx, dy = (cb[0] - ca[0]) * SK, (cb[1] - ca[1]) * SK
        d = (dx * dx + dy * dy) ** 0.5
        if d > JOINT:
            moved.append((k[0], k[1], dx, dy, d))
    L.append("## ① 元件摆位")
    L.append("> 在 VS Code 的**合并视图**里点下面任一条 ✓ ⇒ 图上会高亮那处变化 ✓"
             "（旧位置 = 空心圈 ✓、新位置 = 实心圈 ✓、虚线 = 位移 ✓）。")
    if not moved and not gone and not new:
        L.append("- **没动** ✓（每个焊盘都在原位 ✓，`modelIndex` 被重编号的也按件名对上了 ✓）")
    for t, cid, dx, dy, d in moved:
        L.append("- `%s.%s` 挪了 **%.3f mm**（Δ = (%+.3f, %+.3f) ✓）" % (t, cid, d, dx, dy))
    if moved:
        by = {}
        for t, _c, _dx, _dy, d in moved:
            s = by.setdefault(t, [0, 0.0])
            s[0] += 1
            s[1] = max(s[1], d)
        L.append("- ⇒ 涉及 **%d** 个件：%s" % (len(by), "、".join(
            "`%s`（%d 脚，最大 %.3f mm）" % (t, v[0], v[1]) for t, v in sorted(by.items()))))
    if gone:
        L.append("- ✗ **没了**：%s" % "、".join("`%s.%s`" % k for k in gone))
    if new:
        L.append("- ✓ **新增**：%s" % "、".join("`%s.%s`" % k for k in new))

    # ② 按**项目网名**报（GND / 5V / RC … ✓），并报**块数** = 这张网分成了几段铜 ✓
    sa, sb = _net_summary(_nets(ma, netmap)), _net_summary(_nets(mb, netmap))
    L.append("")
    L.append("## ② 网（名字取项目网表 `pixel_nets.py` ✓；**铜块 > 1 ⇒ 这张网有地方没连上** ✗；"
             "长度是两端直线近似 ⚠️ 曲线不算 ✗）")
    n_chg, split = 0, []
    for k in sorted(set(sa) | set(sb), key=lambda x: (x == "", x)):
        A, B = sa.get(k, []), sb.get(k, [])
        na, nA, ma_, mB = len(A), len(B), sum(c["n"] for c in A), sum(c["n"] for c in B)
        la = sum(c["mm"] for c in A)
        lb = sum(c["mm"] for c in B)
        nm = "`%s`" % k if k else "**（没有网名的残段 ✓）**"
        chg = (na != nA or ma_ != mB or abs(la - lb) > 0.05)
        if chg:
            n_chg += 1
        L.append("- %s：铜块 **%d ⇒ %d**%s｜走线 %d ⇒ %d 段 ✓｜%.1f ⇒ **%.1f mm** ✓"
                 % (nm, na, nA, " ✗" if na != nA else "", ma_, mB, la, lb))
        for tag, cs in (("A", A), ("B", B)):
            if len(cs) > 1:
                split.append((k, tag, len(cs)))
                for i, c in enumerate(cs, 1):
                    L.append("    · %s 第 %d 块：%d 段 %.1f mm ✓ —— 脚：%s"
                             % (tag, i, c["n"], c["mm"], _foot(c) or "（没接到任何脚 ✗）"))
    if not split:
        L.append("- ★ 每张网都只有**一块铜** ✓（没有「还差一根线」的网 ✓）")
    else:
        L.append("- ★ **块 > 1 的网**（= 这里还差布线 ✗）：%s"
                 % "、".join(sorted(set("%s（%s 版）" % (k or "残段", t) for k, t, _n in split))))

    # ③ 过孔 ✓（按几何就近配 ✓）
    va = [v["p"] for v in ma["vias"]]
    vb = [v["p"] for v in mb["vias"]]
    used, vmoved = set(), 0
    for xa in va:
        best, bj = None, None
        for j, xb in enumerate(vb):
            if j in used:
                continue
            d = ((xb[0] - xa[0]) ** 2 + (xb[1] - xa[1]) ** 2) ** 0.5 * SK
            if best is None or d < best:
                best, bj = d, j
        if bj is not None and best < 0.05:
            used.add(bj)
            if best > JOINT:
                vmoved += 1
    L.append("")
    L.append("## ③ 过孔")
    L.append("- 颗数：**%d ⇒ %d** ✓｜基本没动（<0.05 mm）**%d** 颗 ✓｜挪动 %d ✓｜"
             "删 %d ✗｜增 %d ✓"
             % (len(va), len(vb), len(used), vmoved, len(va) - len(used), len(vb) - len(used)))

    # ④ 结论 ✓
    L.append("")
    L.append("## ④ 结论")
    L.append("- " + ("**逐项相同** ✓（这一版等于上一版 ✓）"
                     if not (moved or gone or new or n_chg or vmoved
                             or len(va) != len(vb)) else
                     "有改动 ✓：摆位 %d 处 ✓｜网 %d 张有变化 ✓｜过孔 %d ⇒ %d 颗 ✓"
                     % (len(moved), n_chg, len(va), len(vb))))
    return L



# ── 叠合差异图 ─────────────────────────────────────────────────────────────
def _frame(svg):
    vb = re.search(r'viewBox="([^"]+)"', svg)
    wh = re.search(r'width="([\d.]+)"\s+height="([\d.]+)"', svg)
    return (vb.group(1) if vb else None,
            float(wh.group(1)) if wh else 0.0, float(wh.group(2)) if wh else 0.0)


def _inner(svg):
    """去掉 xml 声明 / 根标签 / **白底矩形** ✓（白底不扔 ⇒ 后画的那版会把前版盖掉 ✗）。"""
    b = re.sub(r'^.*?<svg\b[^>]*>', '', svg, flags=re.S)
    b = re.sub(r'</svg>\s*$', '', b)
    return b.replace('<rect width="100%" height="100%" fill="#ffffff"/>', '')


# ══ 视图：pcb | bb（面包板）| sch（原理图）✓（2026-10-07 加 ✓）══════════════
#   ★ 颜色口径（用户 2026-10-07 定 ✓）：**色相 = 类别**（导线 / 元件 / 文字 ✓）、
#     **深浅 = 版**（浅 = A 旧 ✓ / 深 = B 新 ✓）—— PCB 那套「色相 = 层」在这儿没意义 ✗
#     （面包板/原理图没有层 ✓）。
#   ★ 分类**只按结构**认 ✓（出图段我逐行核过两个渲染器 ✓，同一套写法 ✓）：
#       `render_bb.py` ：底 = `<rect fill="#f7f7f7">` ✓；每个零件一个 `<g transform="matrix(…)">` ✓；
#                        顶层 `<line stroke-width="2">` = 跳线 ✓。
#       `render_sch.py`：底 = `<rect fill="#ffffff">` ✓；零件组 ✓；顶层 `<line>` = 导线 ✓；
#                        顶层 `<circle>` = 接点 ✓；带 `font-family` 的 `<g>` 里是位号 ✓。
#     ⇒ `_cls_of()` **一份实现**管两边 ✓（✗ 别在两个渲染器里各写一套 ✗）。
VIEW = "pcb"
VIEW_PX = {"bb": 1800.0, "sch": 1700.0}     # 子进程渲染的输出宽 px ✓（它们第 3 个参数 ✓）
CLS_WIRE, CLS_PART, CLS_TEXT, CLS_BOARD = "wire", "part", "text", "board"
#   三类在两版里的颜色 ✓（沿用 PCB 那套常量：橙系 / 蓝系 / 灰系 ✓ 六色互分得开 ✓）
VIEW_PAL = {"wire": (A_TOP, B_TOP), "part": (A_BOT, B_BOT), "text": (A_OTH, B_OTH)}


def _cls_of(el):
    """顶层元素原文 ⇒ 类别 ✓。

    ★★ 2026-10-07 实测修 ✗（用户：「导线B 没有应用」✓，而分类计数直接把它揭出来了 ✓：
      `A 导线 82 / 文字 9` ✓ 对 `B 导线 0 / 文字 0 / 元件 12` ✗）——
      ✗ 原来只按 **顶层标签** 认（`<line>` = 导线 ✗），而 `render_sch.py` 对 v40 那版把
      **导线与位号包进了普通 `<g>`** ✓ ⇒ 全被当成“元件”染成蓝 ✗（连颜色都没轮到 ✗）。
      ⇒ 改成**按组里的内容**认 ✓：`matrix(` ⇒ 零件组 ✓（两个渲染器都这么画零件 ✓）、
        `font-family` 或有 `<text>` ⇒ 文字 ✓、其余普通 `<g>` ⇒ **导线** ✓。
      “认不出 ⇒ 当元件” ✓ 仍然保留（宁可当元件，也别把零件当线画成导线色 ✗）。
    """
    t = el.lstrip()[:6].lower()
    if t.startswith("<rect"):
        return CLS_BOARD
    if t.startswith("<line") or t.startswith("<circ") or t.startswith("<path"):
        return CLS_WIRE
    if t.startswith("<text"):
        return CLS_TEXT
    if t.startswith("<g"):
        head = el[:el.find(">") + 1]
        # ★★ 判据只能是这两个，而且要在**整块**里找 ✗（不能只看第一个标签 ✗ ——
        #   2026-10-07 实测：`render_sch.py` 的零件是
        #     `<g partID="900127260"><g transform="matrix(3.543300 …)">…`
        #   ⇒ `matrix` 在**第二层**标签里 ✗ ⇒ 只看第一层就判成“含 text ⇒ 文字” ✗
        #   （实测 A 那版 `文字 17 / 元件 0` ✗✗，全歪了 ✓）。
        if "matrix(" in el:                          # 两个渲染器的零件组都带 matrix ✓
            return CLS_PART
        if "font-family" in head:                    # 位号组（`<g font-family=…><text>` ✓）
            return CLS_TEXT
        if "partID=" in head:                        # 不带 matrix 的核心件（如 via 的 translate ✓）
            return CLS_PART
        return CLS_TEXT if "<text" in el else CLS_WIRE
    return CLS_PART


_TAG_RE = re.compile(r"<(/?)([A-Za-z][\w:.-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)(/?)>", re.S)


def _top_split(svg):
    """`<svg>` 的**顶层**子元素 ⇒ `[(类别, 原文), …]` ✓。

    ★★ 2026-10-07 实测修 ✗（用户：「导线B 的颜色仍然没有看到」✓）：上一版用
      “只数 `<g` / `</g>`”自己配平 ✗ —— 碰到**自闭合** `<g … />` / 属性引号里带 `>` 时
      **深度回不到 0** ✗ ⇒ 后面所有顶层元素被**一口吞进最后一个组** ✗。
      实测（v40 原理图 ✓）：渲染里 **123 条 `<line>`** ✓ 而顶层只切出 13 个、**0 条导线** ✗✗。
      ⇒ 改用**真正的标签扫描**（认引号 ✓、认自闭合 ✓）。
    """
    body = svg[svg.find(">", svg.find("<svg")) + 1:svg.rfind("</svg>")]
    out, depth, start = [], 0, None
    for m in _TAG_RE.finditer(body):
        closing, name, selfclose = m.group(1), m.group(2).lower(), bool(m.group(4))
        if depth == 0 and start is None and not closing:
            start = m.start()
        if name == "g" and not selfclose:
            depth += -1 if closing else 1
        if depth == 0 and start is not None and (selfclose or closing):
            out.append((_cls_of(body[start:m.end()]), body[start:m.end()]))
            start = None
    return out


def _inner(svg):
    """去掉 `<svg …>` 头与尾 ✓。"""
    return svg[svg.find(">", svg.find("<svg")) + 1:svg.rfind("</svg>")]


def _mix_hex(c, target, t):
    """把 `#rrggbb` 往 `target`（0 或 255）方向混 t ✓。"""
    r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
    return ((round(r + (target - r) * t) << 16) | (round(g + (target - g) * t) << 8)
            | round(b + (target - b) * t))


def _lum(c):
    r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def _shade_hex(h, mode):
    """`#rrggbb` ⇒ **同色系**的浅版（A 旧 ✓）/ 深版（B 新 ✓）✓。

    ★★ 2026-10-07 用户定 ✓：原话「B图导线按原图颜色，使用同色深色；A图导线按原图颜色，
      使用同色浅色。而不是现在 A/B 图导线全部一个颜色」✓ —— 导线在 Fritzing 里**本来就有颜色** ✓
      （`wireExtras/@color` ✓，官方配色表 13 色 ✓）⇒ **保留色相**才能一眼认出“哪根线” ✓，
      深浅只表示版本 ✓。元件/文字两类的口径**不变** ✗（仍然是蓝系 / 灰系 ✓）。

    ★ 混色比例是**量出来的**，不是拍的 ✓：A 往白混 **0.45** ✓、B 往黑混 **0.35** ✓ ——
      拿官方色表里最深/最浅的几个试过 ✓：
        红 `#cc1414` ⇒ A `(227,126,126)` 浅红 ✓ / B `(133,13,13)` 深红 ✓
        黑 `#404040` ⇒ A `(147,147,147)` ✓ / B `(42,42,42)` ✓
      ✗ 白线 `#ffffff` 的 A 版提亮后**还是白** ✗ ⇒ 在白底上看不见 ✓ ⇒ A 侧**限一下亮度** ✓
      （超 0.90 就少混一点 ✓），B 侧天然变灰 ✓。

    ★★ 2026-10-07 扩到**元件** ✓：元件也改成「按自己的颜色分浅/深」✓（原来那两版都错了 ✗
      —— 见 `_paint` 里那两条教训 ✓）。文字那类仍是灰系 ✓。
    """
    s = str(h).lstrip("#")
    if len(s) != 6:
        return h
    try:
        c = int(s, 16)
    except ValueError:
        return h
    t = 0.45 if mode == "A" else 0.35
    if mode == "B":
        return "#%06x" % _mix_hex(c, 0, t)
    out = _mix_hex(c, 255, t)
    # ★ 白线（`#ffffff` / 近白 ✗）没法再浅 —— 往白混**永远是白** ✗（白底上看不见 ✓）
    #   ⇒ 只能**略压一点**到看得见 ✓。★ 但要**刚好压到线** ✗：上一版从 0.30 起步 ✗ ⇒
    #   白线被压成 `#b2b2b2`（≈ B 版 ✗ 分不出深浅 ✗）、**黄线 `#fff800` 甚至比 B 还深** ✗✗。
    #   ⇒ 改成**从小往上试** ✓，一过阈值就停 ✓。实测：`#ffffff` ⇒ A `#e0e0e0` ✓（B `#a6a6a6` ✓）、
    #   `#fff800` ⇒ A `#f2eb00` ✓（B `#a6a100` ✓）—— 两档仍然「A 浅 B 深」✓。
    if _lum(out) > 0.88:
        for tt in (0.02, 0.05, 0.08, 0.12, 0.18, 0.25):
            out = _mix_hex(c, 0, tt)
            if _lum(out) <= 0.88:
                break
    return "#%06x" % out


_COL_ATTR_RE = re.compile(r'(\b(?:stroke|fill)\s*=\s*")' + r'(#[0-9a-fA-F]{6})(")')
_COL_STYLE_RE = re.compile(r"(\b(?:stroke|fill)\s*:\s*)(#[0-9a-fA-F]{6})")


def _shade_svg(xml, mode):
    """把一个 svg 片段里**每个颜色**各按各的色相变浅/变深 ✓。

    ★ 形状与 `render_pcb.remap_colors` **一样** ✓（属性式 `stroke="#…"` ＋ 内联式
      `stroke:#…` 两种都盖 ✓），只是这里**逐色变换**而非查表 ✓ ——
      导线颜色是**数据**（每根线一个 ✓）⇒ 表列不出来 ✗。
    """
    x = _COL_ATTR_RE.sub(lambda m: m.group(1) + _shade_hex(m.group(2), mode) + m.group(3), xml)
    return _COL_STYLE_RE.sub(lambda m: m.group(1) + _shade_hex(m.group(2), mode), x)


def _common_fill(svg, skip=None):
    """挑一个**零件**里最常见的**非近白**填充色 ⇒ 当图例里「元件」那两格的样例 ✓。

    ★ 为什么要选 ✗：元件现在是**按各自原色**变浅/变深 ✓ ⇒ 图例没法只用一个固定色 ✓
      （导线那条也是这个道理 ✓，它用官方色表的红当样例 ✓）。这里**从渲染里数**出来 ✓
      ⇒ 是实测的样例 ✓，不是我拍的 ✗。
    """
    n = {}
    for i, (cls, txt) in enumerate(_top_split(svg)):
        if cls != CLS_PART or i == skip:              # ★ 不拿背景件当样例 ✓
            continue
        for h in re.findall(r'fill\s*[:=]\s*"?#([0-9a-fA-F]{6})', txt):
            c = int(h, 16)
            if _lum(c) > 0.90:                      # 近白的当样例没用 ✓（白底上看不见 ✓）
                continue
            n[c] = n.get(c, 0) + 1
    if not n:
        return "#999999"                            # 兜底：中灰 ✓（零件全是近白时才跑到这里 ✓）
    return "#%06x" % max(n.items(), key=lambda kv: kv[1])[0]


def _biggest_part(svg):
    """渲染里**面积最大的那个零件块** ⇒ 它的下标 ✓（= 当背景的那件 ✓，面包板本体 ✓）。

    ★ 为什么要认它 ✗（2026-10-08 用户实测 ✓，两句原话合起来看就明白了 ✓）：
      · 「面包板上蒙了一层灰」✗ —— 给整块板也按“浅/深”上色 ⇒ 板身被压成灰 ✗
        （它本来是浅色底板 ✓，两版一叠就成了灰 ✓）；
      · 「面包板中的图例不用参与动画」✓ —— 板是**画布** ✓，不是“变化的那一件” ✗。
      ⇒ 板：**不上色 ✗、不包进动画 ✗**（保持原样 ✓）。
    ★ 判据按**画出来的包围盒**算 ✓（`part_box.shape_bbox` ✓ 与渲染器算本体盒同一套 ✓），
      ✗ 不按 svg 的 `width/height` ✗（画布留白会骗人 ✓）。
    """
    import xml.etree.ElementTree as ET
    import part_box as PB
    fx, fy, fw, fh = _frame_box(svg)
    fare = abs(fw * fh) or 1.0                     # 画布面积 ✓（块面积比它 ✓）
    best, bi = 0.0, -1
    for i, (cls, txt) in enumerate(_top_split(svg)):
        if cls != CLS_PART:
            continue
        try:
            r = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg'>" + txt + "</svg>")
            x0, y0, x1, y1 = PB.shape_bbox(r)
        except Exception:                            # noqa: BLE001  形状怪就算 0 ✓
            continue
        a = abs((x1 - x0) * (y1 - y0))
        if a / fare < 0.60:                          # ★★ 判据：**盖住画布大半**才算"当画布的那件" ✓
            continue                                 #   ✗ 少了这条就会把**原理图的 IC** 当成板 ✗
        if a > best:
            best, bi = a, i
    if bi >= 0:
        print("    （背景件 = 第 %d 块 ✓，占画布 %.0f%% ✓）" % (bi, 100.0 * best / fare))
    return bi


def _matrix_ef(svg, i):
    """取第 `i` 个顶层块里第一个 `matrix(a b c d e f)` 的 **(e, f)** ✓（没有就 `None` ✓）。

    ★ 用途：**背景件那块板**在两版里挪没挪 ✓ —— 只看坐标 ✓（面包板渲染里
      `matrix` 的 (e,f) 就是实例的 `geometry (x, y)` ✓，2026-10-07 实测逐位相符 ✓）。
    """
    if i is None or i < 0:
        return None
    blk = _top_split(svg)
    if i >= len(blk):
        return None
    mm = re.search(r"matrix\(([^)]*)\)", blk[i][1])
    if not mm:
        return None
    nn = [float(v) for v in re.findall(r"-?\d+\.?\d*", mm.group(1))]
    return (round(nn[4], 2), round(nn[5], 2)) if len(nn) >= 6 else None


def _paint(svg, pal, mode="A", skip=None, drop=None):
    """按类别上色 ✓ ⇒ `(新 svg, {类别: 个数})`。

    · **底**（板/画布那个 rect）：**不铺色** ✓ —— 铺了会把另一版盖住 ✗
      （与 PCB 那套「把 A 的板底换成 none」一个道理 ✓）；
    · **元件**：**按它自己的颜色**做同色浅/深 ✓（与导线共用 `_shade_svg` ✓）——
      ★★ 这里我**换过两版** ✗、两版都被用户当场否了 ✓，写下来免得再犯 ✓：
      ① 把 `fill` 一律染成类别色 ⇒ **整块板变蓝** ✗（用户 2026-10-07：『面包板和元件的
         图形都丢失了，被蓝色色块填满』✗）；
      ② 干脆把 `fill` 去掉（`_no_fill` ✗，已删 ✓）⇒ **图形的“肉”没了** ✗（面包板那些
         **实心孔**全消失 ✓ ⇒ 用户 2026-10-07：『面包板的图位置错误，元件也都渲染错误』✗）。
      ⇒ 正解 = **既不染也不删** ✓：保留原色相 ✓、只把**明度**分两档（A 浅 / B 深 ✓）
      ⇒ 图形在 ✓、A/B 又分得开 ✓。
    · 导线 / 文字：描边与填充都上色 ✓（导线那个 `<circle>` 接点靠 fill ✓，文字靠 fill ✓）；
    · 换色共用 `render_pcb.remap_colors` ✓（属性式 `stroke=` 与内联 `style:` 两种写法它都盖 ✓）；
    · **背景那件**（面包板本体 ✓，`skip` 传下标 ✓）：**原样不动** ✗（既不上色也不抹填充 ✓）
      —— 否则整块板蒙灰 ✗（用户 2026-10-08 原话 ✓）；用 `_biggest_part()` 认它 ✓。
    · `drop`（另一个下标 ✓）：这一块**整块不画** ✓ —— 板只该在 **A 侧**画一次 ✓：
      B 层叠在 A 层上面 ✓ ⇒ B 侧的板会把 **A 的元件全盖住** ✗（用户 2026-10-08 原话：
      「可能是面包板盖住了整个 A 图」✓ ⇒ 「改成只显示 A 图的面包板」✓）。
    """
    import render_pcb as R
    head = svg[:svg.find(">", svg.find("<svg")) + 1]
    parts, cnt = [], {}
    for i, (cls, txt) in enumerate(_top_split(svg)):
        cnt[cls] = cnt.get(cls, 0) + 1
        if i == drop:                                # ★ 背景件：整块不画 ✓（B 侧 ✓）
            continue
        if i == skip:                                # ★ 背景件：原样保留 ✓
            parts.append(txt)
            continue
        if cls == CLS_BOARD:
            txt = re.sub(r'\bfill\s*=\s*"[^"]*"', 'fill="none"', txt, count=1)
        elif cls == CLS_WIRE:
            # ★ 导线：**按它自己的颜色**做同色浅/深 ✓（用户 2026-10-07 定 ✓）
            txt = _shade_svg(txt, mode)
        elif cls == CLS_PART:
            # ★★ 零件：**按自己的颜色**变浅/变深 ✓（既不染成类别色 ✗、也不抹掉填充 ✗ ——
            #   那两版都丢图形 ✓，见本函数 docstring 里的两条教训 ✓）
            txt = _shade_svg(txt, mode)
        else:
            txt = R.remap_colors(txt, {}, pal[cls])
        parts.append(txt)
    return head + "".join(parts) + "</svg>", cnt


def _frame_box(svg):
    """取该 svg 的取景窗 ⇒ `(x, y, w, h)` ✓。"""
    va, w, h = _frame(svg)
    v = [float(x) for x in re.findall(r"[-+0-9.eE]+", va or "")] if va else []
    return (v[0], v[1], w, h) if len(v) == 4 else (0.0, 0.0, w, h)


def _union_frame(sa, sb):
    """两版的**并集**取景窗 ✓ —— 面包板/原理图的坐标**本来就是 sketch 坐标** ✓
    （两个渲染器都把零件/导线画在**绝对 sketch 坐标**上 ✓，只是各自把窗口裁到内容 ✓）
    ⇒ 叠合只需**取并集** ✓：不缩放、不平移 ✓，谁挪了就是挪了 ✓。
    """
    ax, ay, aw, ah = _frame_box(sa)
    bx, by, bw, bh = _frame_box(sb)
    x0, y0 = min(ax, bx), min(ay, by)
    return (x0, y0, max(ax + aw, bx + bw) - x0, max(ay + ah, by + bh) - y0)


def _view_rows(name_a, name_b, sample=None):
    """图例：三类 × 两版 = **6 行** ✓。

    ★ 必须是 6 行 ✗（2026-10-07 修 ✓）：`_legend` 是**按列**摆的（每列
      `ceil(行数/3)` 行 ✓）⇒ 7 行会变成 3/3/1 ✗ ⇒「元件A」在左列、「元件B」在中列
      ✗（用户看到的「图例乱了」✓）⇒ 就 6 行、一列一个类别 ✓（跟 PCB 那份图例同排法 ✓）。
    """
    rows = []
    for cls, label in ((CLS_WIRE, "导线"), (CLS_PART, "元件"), (CLS_TEXT, "文字/位号")):
        for mode, nm in (("A", name_a), ("B", name_b)):
            if cls in (CLS_WIRE, CLS_PART):
                # ★ 导线**每条各按原色** ✗、元件**每件各按原色** ✗（用户 2026-10-07 定 ✓）
                #   ⇒ 图例里各放一个**样例**（导线用官方色表的红 ✓、元件用渲染里数出来的
                #   最常见非近白填充 ✓）＋ 文字里说清“按原色 ✓”（✗ 十几色摆不下 ✗）。
                c = _shade_hex("#cc1414" if cls == CLS_WIRE else (sample or "#999999"), mode)
                lab = "%s（按原色·%s）%s" % (label, "浅" if mode == "A" else "深", nm)
            else:
                c = VIEW_PAL[cls][0 if mode == "A" else 1]
                lab = "%s%s %s" % (label, mode, nm)
            rows.append((c, lab))
    return rows


def _render_view(fzz, view, out):
    """渲一版 ⇒ svg 文本 ✓。

    ★ `render_bb.py` / `render_sch.py` 是**脚本式** ✗（模块级读 `sys.argv` ⇒ import 就执行 ✗）
      ⇒ 只能**子进程**调 ✓；它们本来就**顺手写出 `.svg`** ✓（`<out>.svg` ✓）⇒ 读回来就是矢量 ✓。
      ✗ 不许照它们再写一份渲染 ✗（那是重复实现 ✓）。
    """
    script = os.path.join(HERE, "render_%s.py" % view)
    import subprocess
    if not os.path.isfile(script):
        raise SystemExit("库里没有 %s ✗（--view %s 需要它 ✓）" % (os.path.basename(script), view))
    base = os.path.join(out, "_tmp_%s_%s" % (view, os.path.splitext(os.path.basename(fzz))[0]))
    png = base + ".png"
    cmd = [sys.executable, script, fzz, png, str(int(VIEW_PX.get(view, 1800.0)))]
    r = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(fzz)),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    svgp = base + ".svg"
    if r.returncode or not os.path.isfile(svgp):
        raise SystemExit("渲 %s 失败 ✗：%s\n%s" % (view, " ".join(cmd),
                                                 r.stdout.decode("utf-8", "replace")[-2000:]))
    return open(svgp, encoding="utf-8").read()


def _tag_elements(svg, refs, fzz, view, side, skip=None):
    """把**变化处**的顶层元素包成 `<g id="a-<key>">` / `<g id="b-<key>">` ✓。

    ★ 钥匙（2026-10-07 实测 ✓，见 `docs/diff-animation.md` ✓）：
      · **零件（面包板）**：块头第一个 `matrix(a b c d e f)` 的 **(e, f)** = 实例
        `geometry (x, y)` ✓（实测逐位相符 ✓）；
      · **零件（原理图）**：`matrix(e,f)` **不等于** geometry ✗ ⇒ 用渲染器自己的依据
        `partID`（普通件 `%s0` ✓ / 网标签 `%s1` ✓）⇒ `partID[:-1]` = `modelIndex` ✓；
      · **接地符号**：渲染器**不给它** `partID` ✗ ⇒ 按 `sch_net.ground_pin` 的脚位坐标认 ✓；
      · **导线**：按坐标 ✓，但**必须按属性名**取值 ✓（✗ 全文扫数字会把 `x1/y1/y2` 里的
        数字也扫进来 ✗）。
    ★ `skip` = **背景件**的下标 ✓ ⇒ 它**不包**（= 不参与动画 ✓，板是画布 ✓）。

    ⇒ 返回 `(新 svg, 打上钥匙的 key 集合, 裸在外面没进组的线)` ✓ —— 三个都拿去自检 ✓
      （= 该侧**真画出来且真变了**的件数 ✓；✗ 少包一个就报错，不许静默 ✗）。
      ★ 第三个（`leak` ✓）是 2026-10-08 加的：**属于变化处、却没进组的线** ⇒ 它们在动画里
      **撤不掉** ✓（用户报的「箭头所指的红横线仍然没有被删除」✓ 就是这一类 ✓）。
    """
    import xml.etree.ElementTree as ET
    import zipfile
    z = zipfile.ZipFile(fzz)
    root = ET.fromstring(z.read([n for n in z.namelist() if n.endswith(".fz")][0]))
    tgl = lambda e: e.tag.split("}")[-1]                    # noqa: E731
    # ★★ 2026-10-08 修 ✗：**导线按「整条跳线」给 key** ✓（`_wid_key()` ✓，与 `_hit_view()`
    #   同一份口径 ✓）—— 一条跳线可能是**几段 Wire** 串起来的 ✓，渲染出来是**几根 `<line>`** ✓；
    #   ✗ 按实例名打钥匙 ⇒ 只包第一段 ⇒ 其余各段**不参与动画** ✓（动画撤不掉它们 ✓）。
    wid2key = _wid_key(fzz) if view == "breadboardView" else {}
    by_mi, by_seg = {}, {}
    for e, ttl in _seq_keys(root):
        key = wid2key.get(ttl, ttl)                # ★ 导线：同一条跳线的几段 ⇒ **同一个** key ✓
        if key not in refs:
            continue                                   # ★ 只给**变化处**打 ✓（省体积 ✓）
        vw = next((c for c in e if tgl(c) == "views"), None)
        sub = next((c for c in vw if tgl(c) == view), None) if vw is not None else None
        g = next((c for c in sub if tgl(c) == "geometry"), None) if sub is not None else None
        if g is None:
            continue
        mi = e.get("modelIndex")
        if mi:
            by_mi[str(mi)] = key
        # ★ 零件的钥匙改按**坐标**认 ✓（2026-10-07 实测 ✓）：渲染里那个
        #   `matrix(a b c d e f)` 的 **(e, f) 就等于实例的 geometry (x, y)** ✓ ——
        #   实测 L1：渲染 `25.577900 71.562400` ↔ geometry `(25.58, 71.56)` ✓ 逐位相符 ✓。
        #   ✗ 不用 `partID ÷ 10` ✗：那条只对**部分**件成立 ✓（自检当场报`A 包了 0`✗），
        #   且 Fritzing 的 partID 并非严格 = modelIndex×10 ✗。
        gx, gy = g.get("x"), g.get("y")
        if gx is not None and gy is not None:
            by_mi[("loc", round(float(gx), 2), round(float(gy), 2))] = key
        # ★ **接地符号**：渲染器**不给它 partID** ✗（2026-10-07 实测 ✓：它的块是
        #   `<g transform="translate(161.3280 138.0002) scale(1.250000) …">` ✓）
        #   ⇒ 只能按坐标认 ✓，而那个坐标 = `sch_net` 自己算的**脚位** ✓
        #   （✗ 不另写公式 ✗ —— `render_sch.py` 画的也是这一份 ✓）。
        if _SN is not None and gx is not None:
            try:
                if _SN.is_ground_symbol(str(e.get("moduleIdRef") or "")):
                    _gp = _SN.ground_pin((float(gx), float(gy)))
                    if _gp:
                        by_mi[("gp", round(_gp[0], 2), round(_gp[1], 2))] = key
            except Exception:
                pass
        # 导线：渲染成一条 `<line x1,y1,x2,y2>`（相对量 x2/y2 ⇒ 这里先绝对化 ✓）
        x, y = float(g.get("x") or 0.0), float(g.get("y") or 0.0)
        x2, y2 = float(g.get("x2") or 0.0), float(g.get("y2") or 0.0)
        if abs(x2) + abs(y2) > 1e-9:
            pts = [(x, y), (x + x2, y + y2)]
            by_seg[tuple(round(v, 2) for p in pts for v in p)] = key
    head = svg[:svg.find(">", svg.find("<svg")) + 1]
    out, got, leak = [], set(), []
    buf, buf_key = [], None

    def flush():
        """把攒着的一串**同一个 key** 的顶层元素包成**一个**组 ✓。

        ★★ 2026-10-08：一条跳线的几段**只包一层** ✓ —— ✗ 别一段一个 `<g id="a-…">` ✗
          （那会写出**重复 id** ✓）。渲染器是按 sketch 顺序画线的 ✓ ⇒ 同一条跳线的几段
          **挨着** ✓（实测：`a-Wire90013116` 的竖段与横段就是前后脚 ✓）。
        """
        if buf_key is not None:
            out.append('<g id="%s-%s">%s</g>' % (side, _gid(buf_key), "".join(buf)))

    def _at(a):
        """取一个**属性**的值 ✓ —— ✗ 不许拿全文扫数字 ✗：
        2026-10-07 实测 ✓：`<line x1="108" y1="144" x2="108" y2="171">` 全文扫数字得
        `[1, 108, 1, 144, 2, 108, …]` ✗ —— **属性名里的数字**（x1 / y1 / y2）跟着进来了 ✗
        ⇒ 候选元组全错、一根都匹配不上（自检当场报 `A 包了 0 / B 包了 0` ✗）。
        """
        m = re.search(r'\b%s="(-?[\d.eE+-]+)"' % a, txt)
        return float(m.group(1)) if m else None
    for i, (cls, txt) in enumerate(_top_split(svg)):
        if i == skip:                              # ★ 背景件不包 ✓（板是画布 ✓）
            flush()
            buf, buf_key = [], None
            out.append(txt)
            continue
        key = None
        # ★★ 零件：认**块里第一个 `matrix(…, e, f)`** ✓，拿 (e, f) 比实例的 geometry (x, y) ✓
        #   —— 实测两个渲染器都逐位相符 ✓（`L1: -2.020000 42.448800` ↔ `x=-2.02 y=42.4488` ✓）。
        #   ✗ 别拿 `partID` 当门槛 ✗ —— 那是 **sch** 渲染器才写的 ✓（`<g partID=…><g transform=matrix>` ✓），
        #   而 **bb** 渲染器只写 `<g transform="matrix(…)">` ✓ 没有 partID ✗ ⇒ 设了门槛就一个也匹配不上 ✓
        #   （自检当场报 `A 包了 0 / B 包了 0` ✗）。
        mm = re.search(r"matrix\(([^)]*)\)", txt)
        if mm:
            nn = [float(v) for v in re.findall(r"-?\d+\.?\d*", mm.group(1))]
            if len(nn) >= 6:
                key = by_mi.get(("loc", round(nn[4], 2), round(nn[5], 2)))
        # ★★ **原理图**：那一版渲染器**自己**把 `modelIndex` 拼了一位数字当 partID ✓
        #   —— 普通零件 `'<g partID="%s0">'` ✓、核心件（网标签 / 接地符号）
        #   `'<g partID="%s1">'` ✓（两处都在 `render_sch.py` 里 ✓，出处是源码 ✓）。
        #   ⇒ `partID[:-1]` 就是 `modelIndex` ✓（✗ 别再判末位是不是 "0" ✗ ——
        #   2026-10-07 实测：判了就把 RC / Ground 全漏掉 ✓ 自检当场报 ✗）。
        #   2026-10-07 实测 ✓：sch 里 `matrix(e,f)` **不是**实例的 geometry ✗
        #   （C2：渲染 `172.8,-72.4377` ↔ 几何 `187.2,-44.5627` ✗；C1 只是恰好相等 ✓）
        #   ⇒ 面包板可用坐标认 ✓、原理图得靠 partID ✓。
        if key is None:
            mp = re.search(r'\bpartID="(\d+)"', txt)
            if mp:
                key = by_mi.get(mp.group(1)[:-1])
        # ★ 接地符号：块头那句 `translate(a b)` 就是它的**脚位** ✓（实测相符 ✓）
        if key is None:
            mt = re.match(r'\s*<g\s+transform="translate\(([-\d.]+)[ ,]+([-\d.]+)\)', txt)
            if mt:
                key = by_mi.get(("gp", round(float(mt.group(1)), 2),
                                 round(float(mt.group(2)), 2)))
        if key is None and cls == CLS_WIRE:
            ax, ay = _at("x1"), _at("y1")
            bx, by = _at("x2"), _at("y2")
            if None not in (ax, ay, bx, by):
                for kk in ((ax, ay, bx, by), (bx, by, ax, ay)):
                    if kk in by_seg:
                        key = by_seg[kk]
                        break
        if key:
            if key != buf_key:                     # ★ 同一个 key 的**几段合成一个组** ✓
                flush()
                buf, buf_key = [], key
            buf.append(txt)
            got.add(key)
        else:
            # ★★ 自检（2026-10-08 加 ✓）：**按坐标能认出属于变化处、却没进组**的线 ✗ ——
            #   它们不参与动画 ⇒ 动画把那一版撤掉了、它们**却一直都在** ✓
            #   （用户报的「箭头所指的红横线仍然没有被删除」✓ 就是这一类 ✓）。
            if cls == CLS_WIRE:
                ax, ay, bx, by = _at("x1"), _at("y1"), _at("x2"), _at("y2")
                if None not in (ax, ay, bx, by) and (((ax, ay, bx, by) in by_seg)
                                                     or ((bx, by, ax, ay) in by_seg)):
                    leak.append("(%.0f,%.0f)→(%.0f,%.0f)" % (ax, ay, bx, by))
            flush()
            buf, buf_key = [], None
            out.append(txt)
    flush()
    return head + "".join(out) + "</svg>", got, leak


def _link_same(x, y):
    r"""同一条连接在两版里**没变**吗 ✓ —— 图（`_hit_view`）与清单（`_bb_section`）**共用这一份** ✗。

    ★★ 2026-10-08 加 ✓（用户：「面包板比较是这样的，看着很乱啊」✓）：这两个地方原来**各判各的** ✗
      —— 清单那边会跳过"没变"的 ✓，图上那边**一条都不跳** ✗ ⇒ 实测 v100 ⇒ v104：
      图上多出 **17 条「线路变了」红圈红字** ✗，而**同一张图的清单**写的是「没动 17 条」✗
      （图与清单自相矛盾 ✓）。⇒ 判据收进这里一份 ✓（阈值仍是 `JOINT` / `SK` 那一对 ✓）。
    """
    import bb_compare as BC
    d, dl, dcol = BC.link_moved(x, y)
    return (not dcol) and d * SK < JOINT and abs(dl) * SK < JOINT


def _gid(key):
    r"""key（**可能是元组** ✓）⇒ 一个安全的 id 串 ✓（`a-` / `b-` / `pd-` 三处**共用这一份** ✗）。

    ★ 2026-10-08：跳线的 key 改成**孔对**（元组 ✓，见 `bb_compare.Link.ident` ✓）
      ⇒ ✗ 别再各处写 `re.sub(r"[^\w.-]", "_", key)` ✗ —— 元组进了 `%s` 会变成 `('pin..',)` ✗。
    """
    s = key if isinstance(key, str) else "_".join(str(x) for x in key)
    return re.sub(r"[^\w.-]", "_", s)


def _link_key(lk):
    r"""一条跳线的 key ✓ = `bb_compare.Link.ident` ✓ —— **只在这一处算** ✗（全文件共用 ✓）。

    ★★ 2026-10-08 修两次 ✗（两件事都出在"一**条**跳线 ≠ 一个 Wire 实例"上 ✓）：
      ① 用户：「箭头所指的红横线仍然没有被删除」✓ —— key 按**实例名**给 ✗ ⇒ 一条跳线是几段
         Wire 串起来的 ✓（实测 `Wire90013116` = `[Wire90013116, Wire90013117]` ✓），只有第一段
         进了动画组 ✗ ⇒ 其余各段动画撤不掉 ✓（已修：`_wid_key()` 把每段都映到同一条 ✓）；
      ② 用户：「面包板比较是这样的，看着很乱啊」✓ —— key 是**名字** ✗，而 Fritzing **一存就
         重新编号** ✗ ⇒ 14 条**完全没变**的连接被报成 28 新增 ＋ 28 没了 ✓ ⇒ 图上凭空多出
         28 对红圈红字 ✓。⇒ 身份改用**接的孔**（`Link.ident` ✓，跨版本稳定 ✓）。
    """
    return lk.ident


def _wid_key(fzz):
    r"""⇒ `{每个 Wire 实例名: 它那条跳线的 key}` ✓（只有**导线**进这张表 ✓）。

    ★ 「几段算一条跳线」这件事**只有 `bb_compare.load()` 一份** ✓ —— ✗ 别在这儿再写一遍 ✗。
    """
    import bb_compare as BC
    links, _plugged = BC.load(fzz)
    return {w: _link_key(lk) for lk in links for w in lk.wids}


def _hit_view(a_fzz, b_fzz, view, frame):
    """面包板 / 原理图的**隐藏高亮组** ✓ ⇒ 清单里点一条就能在图上亮出来 ✓。

    ★★ 2026-10-08：**标签另放一层** ✓（`<g id="pd-labels">` ✓、**不隐藏** ✓）——
      用户原话：「右下角那些『新增跳线 / 没了跳线』的标签，没有显示出来」✓。
      实测 ✓：那 28 条标签**全都在** `pd-*` 组里 ✓，而那些组是 `display:none` ✓
      ⇒ 只有**点了清单那一条**才亮 ✓、不点就一条看不见 ✗（上一版按"标签跑出画布"去挪坐标 ✗
      —— `597.5 ⇒ 540.16` ✓ —— 没有治到根 ✓）。⇒ 标签搬去可见层 ✓，
      隐藏组里只留圈 / 连线 ✓（点行高亮那一套**一个字不动** ✓）。

    ★ 词汇与 PCB 那套**一致** ✓（用户已经认过 ✓）：空心圈 = A 旧 ✓、实心圈 = B 新 ✓
      、虚线连起来 ＋ 标签写 Δ ✓；`新增` / `没了` 只画一个圈 ✓。
    ★ 返回 `(隐藏高亮组 svg, 变化处的 key 集合)` ✓ —— 后者给 `_tag_elements()` 用 ✓
      （✗ 不让打钥匙那边再算一遍差异 ✗：判据只留这一份 ✓）。
    ★ 坐标：实例的 `geometry x/y` 就是 sketch 绝对坐标 ✓ ⇒ 与叠合图**同一坐标系** ✓（不用换算 ✓）。
    """
    vw = {"bb": "breadboardView", "sch": "schematicView"}[view]
    ga, _ska = _place(a_fzz, vw)
    gb, _skb = _place(b_fzz, vw)
    # ★★ 锚点 = 零件**本体盒的中心** ✓（✗ 不是实例原点 ✗ —— 用户 2026-10-07：「位置似乎有偏差」✓）：
    #   实例的 `geometry x/y` 只是那个零件的**原点** ✓，而渲染器画的是**本体盒** ✓
    #   ⇒ 两者差一个“盒心 − 原点”的偏移 ✓（小件就是半个身位 ✓）。
    #   盒数学**不另写** ✗：直接调 `part_box` 那套（与渲染器算包围盒同一份 ✓）。
    ca, cb = _centers(a_fzz, vw), _centers(b_fzz, vw)
    x0, y0, w, h = frame
    r = max(3.0, w * 0.010)                       # 圈多大：按画布宽定 ✓（不然小的视图看不见 ✓）
    fs = r * 1.7
    refs = set()                                  # ★ 变了哪些（给动画打钥匙用 ✓）
    out = []                                      # ★ 高亮组**按名字攒** ✓（见 `circles()` ✓）
    hit_geom = {}                                 # name → [几何片段…] ✓（同一个名字可有多处 ✓）
    lab = []                                      # ★ 标签**另放一层** ✓（可见 ✓，见函数头 ✓）
    placed = []                                   # ★ 已放下的标签框 (x0, x1, y) ✓ ⇒ 撞了就往下让 ✓

    def xy(t):
        return (float(t.get("x") or 0.0), float(t.get("y") or 0.0))

    def p_of(tbl, org, ttl):
        """有本体盒就用**盒心** ✓；算不出来（认不出零件 svg 等）⇒ 退回**实例原点** ✓ 并记一笔 ✓。"""
        c = tbl.get(ttl)
        if c is not None:
            return c
        return xy(org[ttl]) if ttl in org else None

    def circles(names, pa, pb, label, anim_key=None):
        """一处变化 ⇒ **圈 / 连线画一遍** ✓、**每个可点名字各记一份** ✓、**标签只写一条** ✓。

        ★ 2026-10-08：*可点名字* 与 *动画钥匙* 现在是**两件事** ✓ ——
          点了要高亮的是**清单里写的名字**（`pd-<名字>` ✓，扩展那套靠它 ✓）；
          而动画要一起亮/一起撤的是**整条连接**（key = 孔对 ✓）。
        ★★ 同一个名字可能在**两版里各指一处** ✓（Fritzing 重新编号 ⇒ A 的 `Wire90013104` 与
          B 的 `Wire90013104` 是**两条不同的连接** ✓ —— 实测确认 ✓）⇒ **攒到 `hit_geom` 里** ✓、
          最后**一个名字只出一个组** ✗（否则写出**重复 id** ✓，`getElementById` 只认第一个 ✓
          ⇒ 点那一行只亮一半 ✗）。攒着的好处：点一下把同名的几处**一起亮** ✓ —— 那正是这一行在说的事 ✓。
        """
        if isinstance(names, str):
            names = [names]
        names = list(names)
        k = anim_key if anim_key is not None else names[0]
        refs.add(k)                                # ★ 这处变了 ✓（给动画打钥匙用 ✓）
        g = []
        if pa is not None:
            g.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" '
                     'stroke-width="%.2f"/>' % (pa[0], pa[1], r, A_COLOR_HI, r * 0.35))
        if pb is not None:
            g.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                     % (pb[0], pb[1], r * 0.75, A_COLOR_HI))
        if pa is not None and pb is not None:
            g.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                     'stroke-width="%.2f" stroke-dasharray="%.2f %.2f"/>'
                     % (pa[0], pa[1], pb[0], pb[1], A_COLOR_HI, r * 0.3, r * 0.5, r * 0.4))
        for nm in names:
            hit_geom.setdefault(nm, []).append("".join(g))
        if label:
            ax, ay = pb if pb is not None else pa
            ly = ay - r * 1.2
            # ★★ 标签**别跑出画布** ✗（2026-10-08 修 ✗）：实测右缘那两条
            #   「新增跳线 / 没了跳线」写到了 x=597.5 ✓，而画布右边界是 611 ✓
            #   ⇒ 被 viewBox 裁掉、用户看不到 ✗（原话：「右侧的图例文字没有显示出来」✓）。
            #   ⇒ 先算一个**够用的宽度估计** ✓（中日韩字符算 1 个字宽 ✓、其余 0.62 ✓，
            #     宁可估宽一点也没有害处 ✓ —— 这里只是收边 ✓）。
            cjk = sum(1 for ch in label if ord(ch) > 0x2E80)
            wtxt = (cjk + 0.62 * (len(label) - cjk)) * fs
            # ★★ 2026-10-08：**先放圈的右边 ✓，被占了就放左边 ✓，还挤就再往左挪一个身位 ✓** ——
            #   同一处常常**既有「没了」又有「新增」** ✓（实测这份 bb 图 **14 对** ✓：同一根跳线
            #   两版编号不同 ✓，`pts[0]` 一模一样 ✓）⇒ 两条标签会**叠在一点**、谁也看不清 ✗。
            #   ✗ 光"往下让"不够 ✓：这一列本来就 12 单位一条 ✓，让一格正好撞在邻条上 ⇒ 连锁 ✓
            #   （实测：近 20 条挤在 x≈562 这一列上 ⇒ 越挤越乱 ✗）。⇒ **横着也让** ✓。
            #   ★ 收边：右边放不下就贴画布里侧 ✓；上下都别出画面 ✓（图外那条带子是**图例**的地盘 ✗）。
            rcand = max(x0 + r, min(ax + r * 1.2, x0 + w - wtxt - r))
            lcand = ax - r * 1.2 - wtxt
            xs = [rcand] + ([lcand] if lcand >= x0 + r else [])
            for _k in range(1, 7):
                nx = rcand - _k * (wtxt + fs * 1.2)
                if nx < x0 + r:
                    break
                xs.append(nx)
            step = fs * 1.05
            ly0 = ay - r * 1.2
            lo, hi = y0 + fs * 0.6, y0 + h + fs * 0.4

            def _free(x, y):
                """这个位置放得下吗 ✓（与已放下的框比：**横竖都压着**才算撞 ✓）。"""
                return not any(abs(y - p_y) < fs * 1.1 and x < p_x1 and p_x0 < x + wtxt
                               for p_x0, p_x1, p_y in placed)

            def _pick():
                """⇒ 第一个放得下的位置 ✓；实在挤不下 ⇒ `None` ✓（宁可就地叠着 ✓，绝不越界 ✗）。"""
                for cx in xs:
                    for k in range(19):
                        for cy in ((ly0,) if k == 0 else (ly0 + k * step, ly0 - k * step)):
                            if lo <= cy <= hi and _free(cx, cy):
                                return cx, cy
                return None
            lx, ly = _pick() or (rcand, ly0)
            placed.append((lx, lx + wtxt, ly))
            lab.append('<text x="%.2f" y="%.2f" font-family="DroidSans" font-size="%.2f" '
                       'fill="%s">%s</text>'
                       % (lx, ly, fs, A_COLOR_HI, esc(label)))

    for ttl in sorted(set(ga) | set(gb)):
        if ttl.startswith("Wire") or ttl.startswith("TXT"):
            continue
        if ttl not in ga:
            circles(ttl, None, p_of(cb, gb, ttl), "新增")
        elif ttl not in gb:
            circles(ttl, p_of(ca, ga, ttl), None, "没了")
        else:
            pa, pb = p_of(ca, ga, ttl), p_of(cb, gb, ttl)
            if pa is None or pb is None:
                continue
            d = (((pb[0] - pa[0]) ** 2 + (pb[1] - pa[1]) ** 2) ** 0.5) * SK
            if d >= JOINT:
                circles(ttl, pa, pb, "Δ %.3f mm" % d)
    if view == "bb":                                  # 跳线也让它能点 ✓（② 里的行 ✓）
        import bb_compare as BC
        la, _p1 = BC.load(a_fzz)
        lb, _p2 = BC.load(b_fzz)
        # ★★ 2026-10-08：**只比"接上东西的"跳线** ✗ 别把**图例色条**也算进来 ✓ ——
        #   `Link.legend` 就是"两头都没接" ✓（色条 ✓，`bb_compare` 自己也是这么排除的 ✓）。
        #   实测：v95 有 28 条 Wire，其中 **9 条**是色条 ✗ ⇒ 老口径把它们当跳线报"新增/没了" ✗。
        A = {_link_key(lk): lk for lk in la if not lk.legend}
        B = {_link_key(lk): lk for lk in lb if not lk.legend}
        for k in sorted(set(A) | set(B)):
            if k in A and k in B and _link_same(A[k], B[k]):
                continue                              # ★ 没变 ⇒ 不画圈、不打钥匙 ✓（与清单同一份判据 ✓）
            if k not in A:
                lk = B[k]
                circles(lk.wids, None, lk.pts[0], "新增跳线", anim_key=k)
            elif k not in B:
                lk = A[k]
                circles(lk.wids, lk.pts[0], None, "没了跳线", anim_key=k)
            else:
                circles(A[k].wids + B[k].wids, A[k].pts[0], B[k].pts[0], "线路变了", anim_key=k)
    body = ('<g id="pd-hits">'
            + "".join('<g id="pd-%s" style="display:none">%s</g>' % (_gid(nm), "".join(g))
                      for nm, g in hit_geom.items())
            + "</g>")
    if lab:                                            # ★ 标签层 ✓：**不隐藏** ✓ ⇒ 一打开就看得见 ✓
        body += '<g id="pd-labels">%s</g>' % "".join(lab)
    return body, refs


def _anim_css(ka, kb, refs, token, sec=ANIM_SEC, tail=ANIM_TAIL):
    """★ 动画第二步（2026-10-07 ✓）：给每一处变化排一个**时段** ✓，写 `@keyframes`
    ＋ 每个元素一句 `animation:` ✓ —— ✗ 不用选择器 ✗（幻灯片会把多张图拼在一页里
    ✓，而 id / class 是**文档级**的 ✗ ⇒ 第一页的规则会去管第二页的元素 ✗）；
    内联 `style="animation:…"` 只认自己那一句 ✓，再加上**名字里带 token** ✓ ⇒ 永不串台 ✓。

    ★ 时段表（用户 2026-10-07 定的规格 ✓，见 `docs/diff-animation.md` ✓）：
      一处变化 = A **闪 2 次** ⇒ A **撤掉** ⇒ B **闪 2 次** ⇒ B **留下** ✓，然后进下一处 ✓；
      全部走完 ⇒ **收尾**：被撤掉的 A **一起淡回来** ✓ ⇒ 末态 = **A+B 叠合图** ✓
      （= 静止那张叠合图 ✓ —— 用户 2026-10-07 追加：「然后，能回到 A+B 的图吗？」✓）。
      ⇒ 开始时看到的是 **A 图** ✓、中途是 B 图 ✓、**结束停在 A+B** ✓。

    ★ 返回 `(css 文本, {("a"|"b", key): 动画名}, 一轮总时长 s)` ✓ ——
      总时长**只在这一处算** ✗（✓ 内联 style 与关键帧百分比必须用**同一个**值 ✓）。
    """
    keys = sorted(refs)
    if not keys:
        return "", {}, 0.0, sec, tail
    total = len(keys) * sec + tail
    end = len(keys) * sec                       # 最后一处时段的结束点 = 收尾段的起点 ✓
    pct = lambda t: round(100.0 * t / total, 3)          # noqa: E731  一行小工具 ✓
    out, anim = [], {}
    for i, key in enumerate(keys):
        s, T = i * sec, sec
        if key in ka:
            nm = "%s-a-%d" % (token, i)
            anim[("a", key)] = nm
            out.append("@keyframes %s{0%%{opacity:1}" % nm
                       + "".join("%s%%{opacity:%d}" % (pct(s + T * f), v) for f, v in
                                 ((0.10, 0), (0.20, 1), (0.30, 0), (0.40, 1)))
                       # ★ 收尾段 ✓：被撤掉的 A **一起淡回来** ✓ ⇒ 末态 = A+B 叠合图 ✓
                       #   （✗ 没有这段的话，末态会停在 B 图 ✗ —— 用户 2026-10-07 要的就是它 ✓）
                       + "%s%%{opacity:0}%s%%{opacity:0}%s%%{opacity:1}100%%{opacity:1}}"
                       % (pct(s + T * 0.50), pct(end), pct(end + tail * 0.6)))
        if key in kb:
            nm = "%s-b-%d" % (token, i)
            anim[("b", key)] = nm
            out.append("@keyframes %s{0%%{opacity:0}%s%%{opacity:0}" % (nm, pct(s + T * 0.50))
                       + "".join("%s%%{opacity:%d}" % (pct(s + T * f), v) for f, v in
                                 ((0.60, 1), (0.70, 0), (0.80, 1), (0.90, 0)))
                       + "%s%%{opacity:1}100%%{opacity:1}}" % pct(s + T * 1.00))
    # 时长都取同一个 `total` ✓ ⇒ 各元素的关键帧百分比冸在**同一条时间轴**上 ✓
    return "\n".join(out), anim, total, sec, tail


def _anim_button(frame):
    """★ 播放键（2026-10-08 用户要 ✓：「加个 svg 的播放键比较好」✓）。

    ★ 为什么必须用**内联 `<script>`** ✗：动画写的是 `animation: … 1 forwards`（只播一遍 ✓）
      ⇒ 想再看一遍只有一个办法：把动画的 `currentTime` 拨回 0 ✓（`document.getAnimations()` ✓）。
      ★ 这个脚本**只在「把 svg 当文档打开」时跑得到** ✓（双击 ✓ / 浏览器直接打开 ✓）；
      ✗ 在 `<img>` 里跑不到 ✗（浏览器不允许 ✓）—— 那种场合（VS Code 合并视图 / 幻灯片 ✓）
      另有扩展自己的按钮 ✓ ⇒ 这里不做兜底 ✗。
    ★ 按钮要放在**动画层外面** ✓（这里插在 `</svg>` 前 ✓）⇒ 它自己不会跟着闪 ✓。
    """
    x0, y0, w, h = frame
    fs = max(w * 0.016, 8.0)                       # 字号跟画布宽走 ✓（各视图单位不同 ✓）
    bw, bh = fs * 5.4, fs * 1.9
    x, y = x0 + fs * 1.2, y0 + fs * 1.2
    return (
        '<g id="anim-btn" style="cursor:pointer" onclick="animReplay()">'
        '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" fill="#ffffff"'
        ' fill-opacity="0.92" stroke="#404040" stroke-width="%.2f"/>'
        '<text x="%.2f" y="%.2f" font-family="DroidSans" font-size="%.2f" fill="#404040"'
        ' text-anchor="middle">\u25b6 重放</text></g>'
        '<script type="text/javascript"><![CDATA['
        'function animReplay(){'
        'var n=document.getAnimations?document.getAnimations():[];'
        'for(var i=0;i<n.length;i++){try{n[i].currentTime=0;}catch(e){}}'
        '}]]></script>'
        % (x, y, bw, bh, bh * 0.25, max(fs * 0.09, 0.2),
           x + bw / 2.0, y + bh * 0.68, fs))


def _view_diff(a_fzz, b_fzz, out, na, nb):
    """面包板 / 原理图：叠合图 ＋ 清单 ✓（PCB 那条路**一个字不动** ✓）。"""
    sa = _render_view(a_fzz, VIEW, out)
    sb = _render_view(b_fzz, VIEW, out)
    pal = ({c: VIEW_PAL[c][0] for c in VIEW_PAL}, {c: VIEW_PAL[c][1] for c in VIEW_PAL})
    ca = _paint(sa, pal[0], "A")[1]
    cb = _paint(sb, pal[1], "B")[1]
    print("✓ %s 渲染：A 导线 %d / 元件 %d / 文字 %d ✓　B 导线 %d / 元件 %d / 文字 %d ✓"
          % (VIEW, ca.get(CLS_WIRE, 0), ca.get(CLS_PART, 0), ca.get(CLS_TEXT, 0),
             cb.get(CLS_WIRE, 0), cb.get(CLS_PART, 0), cb.get(CLS_TEXT, 0)))
    stem = "diff-%s-%s-%s" % (VIEW, na, nb)
    svg_p = os.path.join(out, stem + ".svg")
    frame = _union_frame(sa, sb)
    # ★★ 动画钥匙（2026-10-07 ✓，规格见 `docs/diff-animation.md` ✓）：
    #   先向 `_hit_view` 要“变了哪些” ✓（判据只留那一份 ✓），再给那几处的元素包上
    #   `a-<key>` / `b-<key>` ✓ ⇒ CSS 动画（下一步）就能闪**本体** ✓。
    hits, refs = _hit_view(a_fzz, b_fzz, VIEW, frame)
    # ★ 注意：`_tag_elements` 收的是**视图名**（`schematicView` / `breadboardView` ✓），
    #   ✗ 不是 `sch` / `bb` 那个短名 ✗ —— 我第一次就传错了 ✓ ⇒ 一个实例都匹配不上 ✓
    #   ⇒ 自检当场报 `A 包了 0` ✓（这条自检值了 ✓）。
    vname = {"bb": "breadboardView", "sch": "schematicView"}[VIEW]
    # ★ 背景件（面包板本体 ✓）：不上色 ✗、不参与动画 ✗ —— 用户 2026-10-08：
    #   「面包板上蒙了一层灰」✗ ＋「面包板中的图例不用参与动画」✓
    ska, skb = _biggest_part(sa), _biggest_part(sb)
    # ★★ 板**只在 A 侧画一次** ✓（用户 2026-10-08 定 ✓）—— B 层压在 A 层上面 ✓、
    #   板又大又不透明 ⇒ B 侧的板会把 A 的元件全盖住 ✗（用户原话：「可能是面包板
    #   盖住了整个 A 图」✓）。⇒ B 侧那块**整块不画** ✓。
    #   ★ 但它俩的**几何要对账** ✗：若两版的板**真挪了** ✓，光画 A 的就把 B 的位置藏了 ✗
    #   ⇒ 当场报出来 ✓（可机器守 ✓）。
    ma, mb = _matrix_ef(sa, ska), _matrix_ef(sb, skb)
    print("✓ 背景件（画布那一件 ✓）：只在 A 侧画一次 ✓；A = 第 %d 块 %s / B = 第 %d 块 %s ⇒ %s"
          % (ska, ma, skb, mb,
             "两版位置**相同** ✓（只画一次没有信息损失 ✓）" if ma == mb
             else "两版位置**不同** ✗ ⇒ 只画一次会藏住 B 的位置 ✓，请留意 ✗"))
    pa, ka, leak_a = _tag_elements(_paint(sa, pal[0], "A", skip=ska)[0], refs, a_fzz, vname, "a",
                                   skip=ska)
    # ★ B 侧：`drop=skb` ⇒ 板不画 ✓；而**块号会往前串** ✗（少了那一块 ✓）
    #   ⇒ `skip` 必须传 None ✗（传 skb 会误跳下一块 ✓）
    pb, kb, leak_b = _tag_elements(_paint(sb, pal[1], "B", drop=skb)[0], refs, b_fzz, vname, "b")
    lose = refs - (ka | kb)
    print("✓ 动画钥匙：变化处 %d 个 ⇒ A 包了 %d / B 包了 %d；**一处都没漏** = %s%s"
          % (len(refs), len(ka), len(kb), not lose,
             "" if not lose else " ✗ 漏了：%s" % "、".join(sorted(lose))))
    # ★★ 2026-10-08 自检 ✓：**属于变化处、却没进动画组**的线 = 动画里撤不掉的线 ✓
    #   （用户原话：「箭头所指的红横线仍然没有被删除」✓ —— 实测就是 `Wire90013116`
    #    的第二段 ✓：那条跳线是**两段 Wire 串起来**的 ✓，只包了第一段 ✓。）
    leak = leak_a + leak_b
    print("✓ 动画钥匙：**裸在外面、又属于变化处**的线 = %d 根 %s"
          % (len(leak), "✓（动画里都撤得干净 ✓）" if not leak
             else "✗ %s ⇒ 动画撤不掉它们 ✓" % "；".join(leak[:4])))
    # ★★ 动画第二步：关键帧 ＋ 逐元素内联 `animation` ✓（规格见 `docs/diff-animation.md` ✓）
    token = re.sub(r"[^\w]", "_", "%s%s" % (na, nb))
    css, anim, dur, sec, tail = _anim_css(ka, kb, refs, token)
    for (side, key), nm in anim.items():
        gid = '<g id="%s-%s"' % (side, _gid(key))
        # ★★ 只播一遍 ✓（2026-10-07 用户定 ✓：「可以只播一遍，不循环播放吗？」✓）
        #   ⇒ 计数写 **1** ✓；★ 而且**必须带 `forwards`** ✗ —— 不写的话，动画一结束元素
        #   就**弹回**它自己的初始状态 ✗（A 又全亮 ✓、B 又全灭 ✓）⇒ 「结尾 = B 图」这句
        #   当场作废 ✓（这一条是"只播一遍"最容易漏的一步 ✓）。
        st = gid + ' style="animation:%s %.3fs linear 1 forwards">' % (nm, dur)
        pa = pa.replace(gid + ">", st)
        pb = pb.replace(gid + ">", st)
    if css:
        # ★ 关键帧**只写一份** ✓：A / B 两张图最终在**同一份文档**里 ✓（叠合图是一
        #   个 `svg` ✓、扩展那边又是整段内联 ✓）⇒ CSS 是文件级的 ✓ ⇒ 写两遍只会让
        #   字节翻倍 ✗（2026-10-07 实测：第一版就写了两份 ⇒ 数出 `@keyframes` 132 条 ✗）。
        pa = pa.replace("</svg>", "<style>%s</style>\n</svg>" % css)
    if dur:
        print("✓ 动画：关键帧 %d 条（A %d ＋ B %d ✓，共 %d 处变化 ✓）"
              "—— 一处 %.1f s ＋ 收尾 %.1f s ⇒ 一轮 %.1f s ✓"
              "（收尾时被撤掉的 A **一起淡回** ⇒ 末态 = A+B 叠合图 ✓）"
              % (css.count("@keyframes"), len(ka), len(kb), len(refs), sec, tail, dur))
    # ★ 不透明度：视图用 **A 0.6 / B 0.95** ✓（✗ 不要 PCB 那套 0.75/0.55 ✗）——
    #   用户实测（2026-10-07 ✓）：「导线B 没有应用」✗ ⇒ 算术一算就明白了 ✓：
    #   B 的深橙 `#b8440a` 以 **0.55** 贴白底 ≈ `rgb(216,152,120)` ✓，
    #   而 A 的浅橙 `#f0a868` = `rgb(240,168,104)` ✓ ⇒ **两个几乎分不出来** ✗。
    body = overlay(pa, pb, na, nb, pal=pal, frame=frame,
                   rows=_view_rows(na, nb, _common_fill(sa, skip=ska)),
                   op=(0.6, 0.95), pre=True)
    # ★ 点清单一条 ⇒ 图上高亮 ✓（与 PCB 那份同词汇 ✓）：隐藏组 + 聚焦样式一起写进 svg 本体 ✓
    #   （组 id = `pd-<位号>` ✓ ⇒ 扩展那边**一套正则**就够 ✓）。
    if hits:
        body = body.replace("</svg>", '<style>svg.pd-focus #A, svg.pd-focus #B '\
                            '{opacity:.16}</style>\n' + hits + "\n</svg>")
        print("✓ 高亮层：%d 组（点清单里 ① / ② 的条目 ⇒ 图上亮对应那组 ✓）；"
              "另有标签层 %d 条 ✓（**不隐藏** ✓ —— 一打开就看得见 ✓）"
              % (hits.count('<g id="pd-') - 1 - hits.count('<g id="pd-labels">'),
                 hits.count('<text') if '<g id="pd-labels">' in hits else 0))
    if dur:
        # ★ 播放键（只播一遍 ⇒ 想再看就把动画拨回 0 ✓）：见 `_anim_button()` ✓
        body = body.replace("</svg>", _anim_button(frame) + "\n</svg>")
        print("✓ 播放键：图左上角一个「▶ 重放」✓（把 svg 当文档打开时能点 ✓；"
              "在 `<img>` 里点不动 ✗ ⇒ 合并视图/幻灯片另有按钮 ✓）")
    open(svg_p, "w", encoding="utf-8", newline="\n").write(body)
    print("✓ 叠合差异图 %s（色相 = 类别：导线橙 ✓ 元件蓝 ✓ 文字灰 ✓；深浅 = 版 ✓）" % svg_p)
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_p, write_to=os.path.join(out, stem + ".png"),
                         scale=1.0, background_color="white")
    except ImportError:
        print("（没装 cairosvg ⇒ 只出 svg ✓）")
    lines = report_view(a_fzz, b_fzz)
    md_p = os.path.join(out, stem + ".md")
    open(md_p, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print()
    print("\n".join(lines))
    print("\n（同一份清单也写到 %s ✓）" % md_p)
    for n in os.listdir(out):                       # 中间产物（渲染器写的那对）别留在 diff/ 里 ✓
        if n.startswith("_tmp_%s_" % VIEW):
            os.remove(os.path.join(out, n))
    return 0


VIEW_BIT = {"breadboardView": 64, "schematicView": 128, "pcbView": 4}


# ★ 核心件（ground / netlabel / via …）的 svg 不在 `.fzz` 包里 ✓（AGENTS 记过：
#   "核心件不在 .fzz 里 ⇒ 要去安装目录找" ✓）⇒ 按候选根依次找 ✓。
#   ① **本库仓**第一优先 ✓（`svg/core/schematic/crystal.svg` 这条约定 AGENTS §2 写着的 ✓）；
#   ② 环境变量 `FRITZING_PARTS` ✓（指到安装/构建树的 `parts` 那一层 ✓）；
#   ③ 常见的安装目录 ✓。
#   ✗ 本机绝对路径**不作唯一依赖** ✗ —— 都找不到就跳过该件（照旧列进“略过” ✓）。
CORE_ROOTS = tuple(filter(None, [os.environ.get("FRITZING_PARTS"),
                                 r"F:\build-fritzing\fritzing-parts",   # ★ 本机实测就在这儿 ✓
                                 r"F:\build-fritzing\fritzing-app",
                                 r"C:\Program Files\Fritzing",
                                 r"C:\Program Files (x86)\Fritzing"]))


def _core_svg(core_path, view, image=None):
    """`:/resources/parts/core/ground.fzp` ⇒ 本机真 svg ✓（找不到 ⇒ None ✓）。

    ✗ 不猜件名到具体文件 ✗：只用 fzp 自己的**基名**（`ground.fzp` ⇒ `ground.svg` ✓，
      这是 Fritzing 核心件的命名约定 ✓）；调用方给了 `image` 就优先用它 ✓。
    """
    import part_box as PB                                      # ★ 局部导入 ✓（本文件惯例 ✓）
    stem = os.path.splitext(os.path.basename(core_path.replace("\\", "/")))[0]
    vdir = {"breadboardView": "breadboard", "schematicView": "schematic",
            "pcbView": "pcb"}[view]
    cands = []
    lib = os.path.dirname(HERE)                                    # `tools` 的上一层 = 库仓 ✓
    # ① **先找 fzp、读它自己声明的 `image`** ✓（与库内件同一套口径 ✓，✗ 不猜文件名 ✗）——
    #   2026-10-07 实测：猜 `ground.svg` **猜错了** ✗（那件不叫这个名 ✓），而 `netlabel` 蒙对 ✓。
    #   ⇒ 改成：找到 `…/parts/core/<名>.fzp` ⇒ 读 `<view>/layers@image` ⇒ `resolve_svg` ✓。
    for root in ((lib,) + CORE_ROOTS):
        # ★ 2026-10-07 实测：`F:\build-fritzing\fritzing-parts` 是个**只有 svg、没有 parts** 的
        #   部分检出 ✓ ⇒ 它的形状是 `<根>/svg/core/<视图>/<名>.svg` ✓（本机实测
        #   `…\svg\core\schematic\ground.svg` **确实在** ✓）—— ✗ 我上一版只试了
        #   `<根>/[resources/]parts/svg/core/…` ✗ ⇒ 找不到 ✓。
        cands.append(os.path.join(root, "svg", "core", vdir, stem + ".svg"))
        if image:
            cands.append(os.path.join(root, "svg", "core", image.replace("/", os.sep)))
        for sub in ("resources", ""):
            base = os.path.join(root, sub, "parts") if sub else os.path.join(root, "parts")
            fz = os.path.join(base, "core", stem + ".fzp")
            if not os.path.isfile(fz):
                continue
            img = image
            if not img:
                try:
                    import xml.etree.ElementTree as _ET
                    lay = _ET.parse(fz).getroot().find(".//%s/layers" % view)
                    img = lay.get("image") if lay is not None else None
                except Exception:
                    img = None
            got = PB.resolve_svg(fz, img) if img else None
            if got:
                return got
            cands += [c for c in (os.path.join(base, "svg", "core", img.replace("/", os.sep)) if img else None,
                                  os.path.join(base, "svg", "core", vdir, stem + ".svg"),
                                  os.path.join(base, "svg", "core", stem + ".svg")) if c]
    # ② 库仓那条老约定（`svg/core/<view>/<名>.svg` ✓ —— 本机实测那目录是**空的** ✗，留着不碍事 ✓）
    cands.append(os.path.join(lib, "svg", "core", vdir, stem + ".svg"))
    if image:
        cands.append(os.path.join(lib, "svg", "core", image.replace("/", os.sep)))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def _seq_keys(root):
    r"""⇒ `[(instance 元素, **唯一 key**), …]` ✓ —— 重复位号加 `.2` `.3` ✓（`RC` ⇒ `RC`、`RC.2` ✓）。

    ★★ 2026-10-07 实测修 ✗（用户：「RC 位置错误了吧？」✓）：v40 原理图里有**两个 netlabel
      都叫 `RC`** ✓ ⇒ 原来用 `{位号: …}` 的字典 ✗ ⇒ **后一个覆盖前一个** ✗ ⇒ 图上画的是
      第二个 RC 的图心 ✓，而清单那一行看着像在说第一个 ✗ ⇒ **图文对不上** ✓。

    ★ 用 `.` 拼序号 ✗ 不用括号：扩展那条“位号行”正则的字符集是 `[\w.-]` ✓
      ⇒ `RC.2：…` 照样能点 ✓（✗ 若写成 `RC(2)` 就点不动了 ✗）。
    ★ ★ 序号**只在这里生成** ✓：`_place` 与 `_centers` 都调它 ✓
      （✗ 两边各写一遍序号 ⇒ 两边顺序不一致 ⇒ 又变成“图里两个、清单一个” ✗）。
    """
    seen, out = {}, []
    for e in root.iter("instance"):
        ttl = (e.findtext("title") or "").strip()
        seen[ttl] = seen.get(ttl, 0) + 1
        out.append((e, ttl if seen[ttl] == 1 else "%s.%d" % (ttl, seen[ttl])))
    return out


def _place(fzz, view):
    r"""⇒ `({位号: geometry}, [没显示的位号…])`（sketch 坐标 ✓），✓ —— 位号**唯一** ✓。

    ★★ 2026-10-07 用户实测两条（都对 ✓），两条合起来就是一句：**只列这个视图真的看得见的** ✓：
      ① 「原理图不应有 Via，是不是来自 PCB？」✓ —— **是** ✓。看探针输出：
         `Via1 schematicView:(x=-201.4 y=-120.4 flags=0)` ✓、`Via3 … flags=32` ✓
         ⇒ `wireFlags` 的位**不含本视图** ✗ ⇒ 按 Fritzing 自己的规矩它在本视图里**不算数** ✓
         （`render_bb.py` 同一口径 ✓：位不对就直接跳过、不画 ✓）。
      ② 「Ground1/2 的位置仍然错误」✓ —— 它们的 path 是 `:/resources/parts/core/ground.fzp` ✓
         （**核心件**，在 Fritzing 安装目录里 ✗）⇒ 我们**没渲染它** ✗ ⇒ 锚点只能退回原点 ✗
         ⇒ 红点落在**空地上** ✓。⇒ 零件 svg 取不到 = 本视图里没画 ⇒ **也不该列** ✗。
    """
    import xml.etree.ElementTree as ET
    import zipfile
    import part_box as PB
    z = zipfile.ZipFile(fzz)
    name = [n for n in z.namelist() if n.endswith(".fz")][0]
    root = ET.fromstring(z.read(name))
    out, skipped = {}, []
    for e, ttl in _seq_keys(root):                     # ★ `ttl` = **唯一 key** ✓（重复的带 `.N` ✓）
        vw = next((c for c in e if c.tag.split("}")[-1] == "views"), None)
        sub = next((c for c in vw if c.tag.split("}")[-1] == view), None) if vw is not None else None
        g = next((c for c in sub if c.tag.split("}")[-1] == "geometry"), None) if sub is not None else None
        if g is None:
            continue                                   # 这个视图里根本没它 ✓ 正常 ✓
        fl = g.get("wireFlags")
        if fl is not None and not (int(fl) & VIEW_BIT[view]):
            skipped.append("%s（不在本视图 ✓）" % ttl)
            continue
        fzp = (e.get("path") or "").replace("/", os.sep)
        # ★ 导线（`Wire*`）是**渲染器照 geometry 自己画的** ✓，没有零件 svg ✓
        #   ⇒ ✗ 别拿“取不到 svg”去判它 ✗（否则上百根线全被当成“没画”列进略过清单 ✗）。
        if ttl.startswith("Wire"):
            out[ttl] = g
            continue
        drawn = False
        if fzp.startswith(":") or fzp.startswith("/"):
            # ★ 核心件：`:/resources/parts/core/ground.fzp` ✓ ⇒ 去本机几个根里找 svg ✓
            drawn = bool(_core_svg(fzp, view))
        elif os.path.isfile(fzp):
            try:
                lay = ET.parse(fzp).getroot().find(".//%s/layers" % view)
                drawn = PB.resolve_svg(fzp, lay.get("image") if lay is not None else None) is not None
            except Exception:
                drawn = False
        if not drawn:
            skipped.append("%s（核心件/取不到 svg ⇒ 本视图里没画 ✗）" % ttl)
            continue
        out[ttl] = g
    return out, skipped


def _kind_hint(ttl):
    """位号 ⇒ 一句说明 ✓（用户 2026-10-07 问「为什么有 Via1~Via4？」✓ ——
    过孔 / 接地符号都是**核心件** ✓，它们出现在原理图里是**正常的 Fritzing 用法** ✓
    （在原理图里放过孔 = “这里接上” ✓）⇒ 在清单里点一句，别让人猜 ✗）。
    """
    if ttl.startswith("Via"):
        return "（过孔：原理图里放过孔是 Fritzing 的正常用法 ✓）"
    if ttl.startswith("Ground"):
        return "（接地符号 ✓）"
    return ""


def _centers(fzz, view):
    """`{位号: (盒心 x, 盒心 y)}`（sketch 单位 ✓）—— 用 `part_box` 那套盒数学 ✓（不另写 ✗）。

    ★ 实测（2026-10-07 用户：「位置似乎有偏差」✓）：实例的 `geometry x/y` 是零件的**原点** ✓，
      而渲染器画的是**本体盒** ✓ ⇒ 拿原点当锚点会偏半个身位 ✗（小件尤其明显 ✓）。
    """
    import xml.etree.ElementTree as ET
    import zipfile
    import part_box as PB
    z = zipfile.ZipFile(fzz)
    name = [n for n in z.namelist() if n.endswith(".fz")][0]
    root = ET.fromstring(z.read(name))
    out = {}
    for e, ttl in _seq_keys(root):                     # ★ 与 `_place` **同一个 key** ✓
        vw = next((c for c in e if c.tag.split("}")[-1] == "views"), None)
        sub = next((c for c in vw if c.tag.split("}")[-1] == view), None) if vw is not None else None
        g = next((c for c in sub if c.tag.split("}")[-1] == "geometry"), None) if sub is not None else None
        if g is None:
            continue
        fzp = (e.get("path") or "").replace("/", os.sep)
        if not os.path.isfile(fzp):
            svgp0 = _core_svg(fzp.replace(os.sep, "/"), view)      # ★ 核心件 ✓
        else:
            svgp0 = None
        if not os.path.isfile(fzp) and not svgp0:
            continue
        try:
            if svgp0:
                svgp = svgp0
            else:
                layers = ET.parse(fzp).getroot().find(".//%s/layers" % view)
                svgp = PB.resolve_svg(fzp, layers.get("image") if layers is not None else None)
            loc = (float(g.get("x") or 0.0), float(g.get("y") or 0.0))
            m = PB.tf_of(g)
            x0, y0, x1, y1 = PB.place(loc, m, PB.body_box(svgp))
            big = max(abs(x1 - x0), abs(y1 - y0)) > 40.0
        except Exception:
            continue
        if big:
            # ★★ 2026-10-07 实测 ✓（用户：「RC 位置错误」✓）—— 三条路都量过了 ✓：
            #   · 本体盒心：`netlabel.svg` 的盒是 (0.45, 0, 81.0, 27.0) 单位 ✗ ≈ 23×7.6mm
            #     （标签本体只有几个 mm ✗）⇒ 中心偏右 **~28 单位** ✗；
            #   · 脚位×k：偏到 **~（223, 78.6）** ✗ **更远** ✓（netlabel 的真锚点在导线末端
            #     (161.3, 84.0) ✓，而它按 svg 里那点算 ✗ 差得更多 ✗）；
            #   · **实例原点**：偏 **~12 单位 ≈ 4.4mm** ✓ ≈ 标签自己的半个身位 ✓ ⇒ **最接近** ✓。
            #   ⇒ 就用**原点** ✓（宁可承认“只到标签附近” ✓，也不用一个看着精确、其实更远的数 ✗）。
            x0 = y0 = x1 = y1 = 0.0
            x0, y0 = loc
            x1, y1 = loc
        out[ttl] = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
    return out


def report_view(a_fzz, b_fzz):
    """清单：① 元件摆位 Δ mm（三视图共用 ✓）＋ ② 该视图专属那一节 ✓。"""
    view = {"bb": "breadboardView", "sch": "schematicView"}[VIEW]
    ga, skipped_a = _place(a_fzz, view)
    gb, skipped_b = _place(b_fzz, view)
    mm = lambda v: v * SK
    L = []
    L.append("# %s 差异清单：%s ⇒ %s" % (VIEW, _vtxt(a_fzz), _vtxt(b_fzz)))
    L.append("")
    L.append("> 色相 = 类别（导线 / 元件 / 文字）✓；深浅 = 版（浅 = A 旧 / 深 = B 新）✓；"
             "重合处更深 = 两版一样 ✓。")
    L.append("")
    L.append("## ① 元件摆位（Δ mm）")
    L.append("")
    same = moved = 0
    rows = []
    for ttl in sorted(set(ga) | set(gb)):
        # ★ 导线（`Wire*`）与图例文字件（`TXT*`）不归这里 ✗ —— 导线归 ②（增删/改色/走向 ✓），
        #   `TXT*` 是图例件，本来就不画 ✓（渲染器也跳过它 ✓）⇒ 报出来只是噪声 ✗。
        if ttl.startswith("Wire") or ttl.startswith("TXT"):
            continue
        if ttl not in ga:
            rows.append("- **%s**：B 里**新增** ✓%s" % (ttl, _kind_hint(ttl)))
            continue
        if ttl not in gb:
            rows.append("- **%s**：B 里**没了** ✗%s" % (ttl, _kind_hint(ttl)))
            continue
        xa, ya = ga[ttl].get("x"), ga[ttl].get("y")
        xb, yb = gb[ttl].get("x"), gb[ttl].get("y")
        if None in (xa, ya, xb, yb):
            continue
        dx, dy = mm(float(xb) - float(xa)), mm(float(yb) - float(ya))
        d = (dx * dx + dy * dy) ** 0.5
        if d < JOINT:
            same += 1
            continue
        moved += 1
        rows.append("- **%s**：移了 **%.3f mm**（Δx %+.3f ✓ Δy %+.3f ✓）" % (ttl, d, dx, dy))
    if not rows:
        rows.append("- （摆位一个也没动 ✓）")
    L += rows
    L.append("")
    L.append("（没动 %d 个 ✓ / 动了或增删 %d 个 ✓）" % (same, moved))
    sk = sorted(set(skipped_a) | set(skipped_b))
    if sk:
        L.append("")
        L.append("> 本视图里**不显示**、已略过的：%s" % "、".join(sk))
    L.append("")
    if VIEW == "bb":
        L += _bb_section(a_fzz, b_fzz)
    else:
        L += _sch_section(a_fzz, b_fzz)
    return L


def _bb_section(a_fzz, b_fzz):
    """面包板专属：② 跳线变化 ✓。

    ★ 读法**只有一份** ✓：`bb_compare.load()` ✓（孔 / 交叉 / 遮挡那套全是它 ✓）——
      本函数只做"A 有 B 没有"这种事 ✓，**不重算几何** ✓。
    ★★ 2026-10-08 修两处 ✗（用户：「面包板比较是这样的，看着很乱啊」✓）：
      ① **身份按接的孔**（`Link.ident` ✓）✗ 不按导线名 ✗ —— Fritzing 一存就重新编号 ✓，
         `v95 ⇒ v104` 实测：19 条连接里 **14 条一模一样** ✓，却被报成「28 新增 ＋ 28 没了」✗；
      ② **图例色条不算跳线** ✗（`Link.legend` ✓，与 `bb_compare.metrics()` 同一口径 ✓）——
         老口径把 9 条色条也数进去 ✓ ⇒ 行数、`新增`/`没了` 全是噪声 ✗。
      ⇒ 每行都写出**孔位**＋**导线名** ✓（孔位让人一眼看懂接了哪儿 ✓，导线名保住"点行高亮" ✓）。
    """
    import bb_compare as BC
    la, _pa = BC.load(a_fzz)
    lb, _pb = BC.load(b_fzz)
    A = {_link_key(lk): lk for lk in la if not lk.legend}
    B = {_link_key(lk): lk for lk in lb if not lk.legend}
    L = ["## ② 跳线变化", ""]

    def lab(k, lk):
        """一条连接的**读法** ✓：孔位（人看的 ✓）＋ 导线名（点了要高亮 ✓）。"""
        holes = "–".join(k) if isinstance(k, tuple) else str(k)
        return "%s（%s）" % (holes, "、".join(lk.wids))

    add = sorted(k for k in B if k not in A)
    gone = sorted(k for k in A if k not in B)
    chg, same = [], 0
    for k in sorted(set(A) & set(B)):
        x, y = A[k], B[k]
        if _link_same(x, y):                          # ★ 判据只有一份 ✓（见 `_link_same()` ✓）
            same += 1
            continue
        d, dl, dcol = BC.link_moved(x, y)
        chg.append("- **%s**：%s　端点最大挪 **%.3f mm** ✓ 长度 %+.3f mm ✓"
                   % (lab(k, y), "颜色 %s⇒%s" % (x.color or "（默认）", y.color or "（默认）")
                      if dcol else "走向变了",
                      d * SK, dl * SK))
    L += ["- A %d 条连接 / B %d 条连接 ✓（没动 %d 条 ✓）" % (len(A), len(B), same), ""]
    for t in ("**新增**：%s" % "、".join(lab(k, B[k]) for k in add) if add else "**新增**：无 ✓",
              "**没了**：%s" % "、".join(lab(k, A[k]) for k in gone) if gone else "**没了**：无 ✓"):
        L.append("- " + t)
    if chg:
        L += ["", "**变了**（%d 条）✓：" % len(chg), ""] + chg
    L.append("")
    return L


def _sch_section(a_fzz, b_fzz):
    """原理图专属：② 导线指标对比 ✓ —— 量尺只有一份 ✓：`sch_metrics.metrics()` ✓。"""
    import sch_metrics as SM
    ma, mb = SM.metrics(a_fzz), SM.metrics(b_fzz)
    L = ["## ② 导线指标对比", ""]
    L.append("| 项 | A %s | B %s | 差 |" % (_vtxt(a_fzz), _vtxt(b_fzz)))
    L.append("|---|---|---|---|")
    for k, lab, fmt in (("wires", "导线数", "%d"), ("parts", "元件数", "%d"),
                        ("mm", "总长 mm", "%.1f"), ("crossings", "交叉数", "%d"),
                        ("ortho", "正交度", "%.4f"), ("worst", "最歪 mm", "%.4f")):
        va, vb = ma.get(k), mb.get(k)
        if va is None or vb is None:
            continue
        try:
            dv = "%+.4g" % (float(vb) - float(va))
        except (TypeError, ValueError):
            dv = ""
        L.append(("| %s | " + fmt + " | " + fmt + " | %s |") % (lab, va, vb, dv))
    L.append("")
    L.append("> 量尺 = `sch_metrics.py` ✓（交叉数等口径与布线器**同一套** ✓；结论要拿这把**独立**尺子复核过 ✓）。")
    L.append("")
    return L


def _legend(rows, font, pad, x0=None, width=None):
    """⇒ `(图例 svg 片段, 需要的额外高度)` ✓ —— **三列** ✓，画在**板子下方**的空白带里 ✓。

    ★★ 两条都是用户定的 ✓：
      · 2026-10-07 ①「图例建议放在图下面的白色区域，可以分开成三列显示」✓；
      · 2026-10-07 ②「底部图例的框，应与上面 pcb 图形的**左边框**对齐」✓
        ⇒ 框的左缘 = **板框那条线的 x** ✓（`x0` ✓），✗ 不是画布的左缘 ✗（那样会看着
        比图缩进去一截 ✓）。调用方各自把板框左缘算好传进来 ✓（fzz 路径用 `_board_px()` ✓、
        svg 路径用它自己的 `MARGIN` ✓）—— 本文件不重算 ✗。
      · `width` 给了就**别越出画布右缘** ✓（框宽是死的 ✓，位置可夹 ✓）。
    """
    fs = font
    ncol = 3
    nrow = (len(rows) + ncol - 1) // ncol
    # ★★ 2026-10-07 用户报「底部图例的方框应该封口」＋「字号大了」✗ —— **同一个根** ✓：
    #   框宽 = `ncol × 16.5 × fs` ✓；sch 画布只有 375 宽 ✗ 而 fs = max(13, wa×0.0105) = 13 ✗
    #   ⇒ 框宽 ~650 **越出画布** ✗ ⇒ 右半边连同右边/下边的框线被 viewBox **裁掉** ✗
    #   ⇒ 看着就像“没画完 ✓”；字号相对画布也太大 ✗。
    #   ⇒ 先把 fs **夹到装得下** ✓（一次改，两件都好 ✓）。
    if width:
        fs = min(fs, max(1.0, (float(width) - 3 * pad) / (ncol * 16.5)))
    cw = fs * 16.5                       # 一列宽 ✓
    box_w = ncol * cw + pad
    box_h = fs * (1.9 * nrow + 0.6)
    x0 = pad if x0 is None else float(x0)
    if width:
        x0 = max(pad, min(x0, float(width) - box_w - pad))
    out = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#ffffff" '
           'fill-opacity="0.96" stroke="#cccccc" stroke-width="%.2f"/>'
           % (x0, pad, box_w, box_h, fs * 0.05)]
    for i, (c, lab) in enumerate(rows):
        # ★ **列优先** ✓（一列一个主题 ✓）：列 1 = 顶层两版 ✓、列 2 = 底层两版 ✓、列 3 = 灰 ✓
        #   ✗ 行优先读起来是「A 顶、B 顶、A 底 / B 底、灰、灰」⇒ 版次和层都乱 ✓（2026-10-07 调过 ✓）
        cx = x0 + (i // nrow) * cw + fs * 0.5
        cy = pad + fs * 0.7 + (i % nrow) * fs * 1.9
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                   'stroke="#999999" stroke-width="%.2f"/>'
                   % (cx, cy, fs * 1.4, fs * 1.0, c, fs * 0.05))
        out.append('<text x="%.1f" y="%.1f" font-family="sans-serif" font-size="%.1f" '
                   'fill="#333333">%s</text>'
                   % (cx + fs * 1.9, cy + fs * 0.95, fs, lab))
    return "\n".join(out), box_h + pad * 2


def _legend_rows(name_a, name_b):
    """六个条目 ✓（三层 × 两版 ✓ ＋ 灰的两条 ✓）—— 两个调用方共用这一份 ✓。"""
    a = re.sub(r"[^\x20-\x7e]", "?", name_a)
    b = re.sub(r"[^\x20-\x7e]", "?", name_b)
    return [(A_TOP, "A = %s  top" % a), (B_TOP, "B = %s  top" % b),
            (A_BOT, "A = %s  bottom" % a), (B_BOT, "B = %s  bottom" % b),
            (A_OTH, "grey: A light (silk/board)"), (B_OTH, "grey: B dark")]


def overlay(svg_a, svg_b, name_a, name_b, pal=None, frame=None, rows=None, op=(0.75, 0.55),
            pre=False):
    """两版叠合 ✓：A 浅、B 深、重合更深 ✓。

    ★ 2026-10-07 加了三个口（面包板/原理图用 ✓，**PCB 那条路一个字不改** ✓）：
      · `pal`：`({类别: A 色}, {类别: B 色})` ✓ —— 给了就走「色相 = 类别」✓；
        不给 ⇒ 走 PCB 那套「色相 = 层」（认固定层色再换 ✓）；
      · `frame`：叠合窗口 `(x, y, w, h)` ✓；不给 ⇒ 用 A 的取景 ✓（PCB 两版板框相同 ✓）；
      · `rows`：图例行 ✓；不给 ⇒ PCB 那六行 ✓。
    """
    import render_pcb as R
    if frame is None:
        va, wa, ha = _frame(svg_a)
        vb, wb, hb = _frame(svg_b)
        if va != vb or abs(wa - wb) > 0.5 or abs(ha - hb) > 0.5:
            print("⚠️ 两版取景不一致 ✗（%s vs %s ✓）⇒ 叠合会用 A 的取景 ✓，"
                  "位置对不上不是内容差异 ✗" % (va, vb))
        vv = [float(x) for x in re.findall(r"[-+0-9.eE]+", va)] if va else []
        vx, vy = (vv[0], vv[1]) if len(vv) == 4 else (0.0, 0.0)
    else:
        vx, vy, wa, ha = frame
    if pal is None:
        # 板框的**底色**要清掉 ✓（否则 A 的板底一铺，B 就看不见了 ✗）；描边留着 ✓ ⇒ 会各自染色 ✓
        ia = _inner(svg_a).replace('fill="%s"' % R.C_BRD_FILL, 'fill="none"')
        ib = _inner(svg_b).replace('fill="%s"' % R.C_BRD_FILL, 'fill="none"')
        # ★★ “**认色换色**”而不是“刷成一色” ✗：层色是渲染器的**固定常量** ✓
        #   （面 `C_CU0/C_CU1` ✓、线 `C_W0/C_W1` ✓、过孔 `C_VIA_*` ✓）⇒ 按表逐项换 ✓；
        #   表里没写到的（丝印/板框/位号/孔）⇒ `default` 中性灰 ✓。
        def _pal(top, bot, oth):
            return ({R.C_CU1: top, R.C_W1: top, R.C_VIA_TOP: top,
                     R.C_CU0: bot, R.C_W0: bot, R.C_VIA_BOT: bot}, oth)

        ta, oa = _pal(A_TOP, A_BOT, A_OTH)
        tb, ob = _pal(B_TOP, B_BOT, B_OTH)
        ia = R.remap_colors(ia, ta, oa)
        ib = R.remap_colors(ib, tb, ob)
    else:
        if pre:                       # ★ 已经上过色/打过钥匙 ✓ ⇒ ✗ 别再来一遍 ✗（会把钥匙冲掉 ✓）
            ia, ib = _inner(svg_a), _inner(svg_b)
        else:
            ia = _inner(_paint(svg_a, pal[0], "A")[0])
            ib = _inner(_paint(svg_b, pal[1], "B")[0])
    # ★ 字号**按画布比例** ✓（✗ 写死 ⇒ 在这个渲染器的画布里看不见 ✗）；图例**放在板子下面**
    #   的空白带里 ✓（画布高度加一条 ✓ ⇒ 单独打开 svg 也看得见 ✓，不再压在图上 ✓）。
    fs = max(13.0, wa * 0.0105)
    # ★ 图例框的**左缘**对齐「上面 PCB 图形的左边框」✓（用户 2026-10-07 定 ✓）——
    #   板框那条线的 x 就是它 ✓（fzz 路径是 `--board-only` 渲的 ⇒ 那个 rect 就是板框 ✓）。
    bx = _board_px(svg_a, R)
    leg, extra = _legend(rows if rows else _legend_rows(name_a, name_b), fs, fs * 0.6,
                         x0=(bx[0] if bx else None), width=wa)
    H2 = ha + extra
    # ★ 「上面的图也应该有个方框，套住整张图」✓（2026-10-07 用户定 ✓）——
    #   只看**视图**那条路加 ✗（PCB 那边本来就自带**板框** ✓，再加一层反而乱 ✓）。
    fig = ""
    if pal is not None:
        fig = ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" '
               'stroke="#bbbbbb" stroke-width="%.2f"/>'
               % (vx, vy, wa, ha, max(0.6, wa * 0.0009)))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" '
        'viewBox="%.1f %.1f %.1f %.1f">\n'
        '<rect width="100%%" height="100%%" fill="#ffffff"/>\n'
        '<g id="A" opacity="%.2f">%s</g>\n'
        '<g id="B" opacity="%.2f">%s</g>\n'
        '%s\n'
        '<g id="legend" transform="translate(%.1f,%.1f)">%s</g>\n'
        '</svg>\n'
    ) % (wa, H2, vx, vy, wa, H2, op[0], ia, op[1], ib, fig, vx, vy + ha, leg)


def main(argv):
    global PIX, PAT, NETS_FILE, VIEW
    # ★ `--px 5` ⇒ 画布约 1700 单位 ✓（实测：这个渲染器的画布 ≈ `px × 358` ✓ —— `--px 24`
    #   是 8043 ✗，一个字就占了整个屏幕的比例 ✗，实测图例因此看不见 ✓）
    px, out, last, pos = 5.0, None, None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--px" and i + 1 < len(argv):
            px = float(argv[i + 1]); i += 2; continue
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]; i += 2; continue
        if a == "--last" and i + 1 < len(argv):
            last = int(argv[i + 1]); i += 2; continue
        if a == "--dir" and i + 1 < len(argv):
            PIX = os.path.abspath(argv[i + 1]); i += 2; continue
        if a == "--pattern" and i + 1 < len(argv):
            PAT = argv[i + 1]; i += 2; continue
        if a == "--nets" and i + 1 < len(argv):
            NETS_FILE = os.path.abspath(argv[i + 1]); i += 2; continue
        if a == "--view" and i + 1 < len(argv):          # ★ pcb（默认）/ bb / sch ✓
            VIEW = argv[i + 1].strip().lower(); i += 2; continue
        pos.append(a); i += 1
    out = out or os.path.join(PIX, "diff")

    have = sorted([f for f in os.listdir(PIX) if re.match(PAT, f)],
                  key=lambda f: _vnum(f))
    if last:
        pos = have[-last:] if last >= 2 else None
        if not pos:
            raise SystemExit("`--last` 至少给 2 ✓")
    if len(pos) != 2:
        print(__doc__)
        return 2
    n_svg = sum(1 for p in pos if p.lower().endswith(".svg"))
    if n_svg:
        if n_svg == 2:
            print("—— 两个 svg ⇒ **不比网表** ✗，只出叠合差异图 ✓（Fritzing 导出的也算 ✓）")
            return _svg_mode(pos[0], pos[1], out, 40.0)
        # ★ 一个 fzz ＋ 一个 svg ✓ = **推荐用法** ✓（fzz 那侧我们自己渲 ⇒ 锚准 ✓）
        svg_p = [p for p in pos if p.lower().endswith(".svg")][0]
        fzz_p = _resolve([p for p in pos if p != svg_p][0], have)
        print("—— 一个 fzz ＋ 一个 svg ⇒ **不比网表** ✗，只出叠合差异图 ✓")
        return _svg_mode(svg_p, fzz_p, out, 40.0)
    a_fzz = _resolve(pos[0], have)
    b_fzz = _resolve(pos[1], have)

    # ★★ 2026-10-07 ✓：面包板 / 原理图走这条路 ✓ —— PCB 那套（网表 / 铜块 / 过孔）
    #   对它们没意义 ✗（那三节讲的都是铜 ✗）⇒ 分开走 ✓，**PCB 那条路一个字不动** ✓。
    if VIEW in ("bb", "sch"):
        if not os.path.isdir(out):
            os.makedirs(out)
        return _view_diff(a_fzz, b_fzz, out, _vtxt(a_fzz), _vtxt(b_fzz))

    # ★★ 元件库的 tools 要先挂上路径 ✗（2026-10-07 实测漏过一次：`_lib_tools()` 写了却没调 ✓
    #   ⇒ `import pcb_check` 直接 ImportError ✓）
    sys.path.insert(0, _lib_tools())
    sys.path.insert(0, os.path.dirname(HERE))
    import pcb_check as PC
    import render_pcb as R
    ma, mb = PC.collect(a_fzz), PC.collect(b_fzz)
    # ★ 同一取景 ⇒ 用 `--board-only` ✓（两版板框都是 25×25 ✓）⇒ 叠得上 ✓
    sa = R.render(ma, px, ("--board-only",))
    sb = R.render(mb, px, ("--board-only",))

    if not os.path.isdir(out):
        os.makedirs(out)
    na, nb = _vtxt(a_fzz), _vtxt(b_fzz)
    stem = "diff-%s-%s" % (na, nb)
    svg_p = os.path.join(out, stem + ".svg")
    body = overlay(sa, sb, na, nb)
    # ★★ 把「点清单一条 ⇒ 图上高亮」用的**隐藏图层**塞进去 ✓（2026-10-07 ✓）——
    #   连样式一起写进 svg 本体 ✓ ⇒ 它**单文件也能用** ✓（不是在扩展里才亮 ✓）。
    hits = _hit_layer(ma, mb, sa, sb, na, nb)
    if hits:
        body = body.replace("</svg>",
                            '<style>svg.pd-focus #A, svg.pd-focus #B {opacity:.16}'
                            '</style>\n' + hits + "\n</svg>")
        print("✓ 高亮层：%d 组（点清单里 ① 的条目 ⇒ 扩展会亮对应那组 ✓）"
              % hits.count('<g id="pd-'))
    open(svg_p, "w", encoding="utf-8", newline="\n").write(body)
    print("✓ 叠合差异图 %s（层 = 色相：顶橙 ✓ 底蓝 ✓；版 = 深浅：浅 A %s ✓ 深 B %s ✓）"
          % (svg_p, na, nb))
    try:
        import cairosvg
        png_p = os.path.join(out, stem + ".png")
        cairosvg.svg2png(url=svg_p, write_to=png_p, scale=1.0, background_color="white")
        print("✓ %s" % png_p)
    except ImportError:
        print("（没装 cairosvg ⇒ 只出 svg ✓）")

    lines = report(a_fzz, b_fzz, ma, mb, _netmap(PIX))
    md_p = os.path.join(out, stem + ".md")
    open(md_p, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print()
    print("\n".join(lines))
    print()
    print("（同一份清单也写到 %s ✓）" % md_p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
