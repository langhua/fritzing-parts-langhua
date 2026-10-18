#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fzp_check.py — **开发辅助**：检查 `.fzp` 与四个视图 svg 是否对得上（"连接器是灵魂"）。

用法（在仓库根跑）：
    C:\Python313\python.exe tools\fzp_check.py svg\CH347F
    C:\Python313\python.exe tools\fzp_check.py svg\CH347F --fzpz fzpz\CH347F.fzpz   # 连包一起查

查什么（这些错都**不报错、只是静默不好用**，所以值得机器查）：
  ① `.fzp` 能解析；四个视图的 `image=` 用的是**子目录路径**（icon/ breadboard/ schematic/ pcb/，
     AGENTS §4），而实际文件是本目录的 `svg.<view>.<id>_<view>.svg`
  ② 每个 connector：`<views>` 里至少有一条；每条 `svgId` / `terminalId`
     **必须在对应视图 svg 里真的存在**（拼错一个字母 = 那个脚连不上/不显示）
  ③ 反过来：svgs 里每个 `id="connector…"` 都得在 .fzp 里声明过（否则是没主的图形）
  ④ 每个 svg 内部 **id 不能重复**（踩过：Inkscape Ctrl+D 复制排针 → 两个 `connector32pin`）
  ⑤ `<buses>` 引用的 connector 必须存在，且**每个 connector 最多进一条总线**
  ⑥ **裸露焊盘不许进任何 `<bus>`**（用户 2026-09-15 定，AGENTS §5）；
    名字**尊重原厂命名**（用户 2026-09-25 定）：不叫 `EPAD` / `EP` 时只**提示**，不判 FAIL ——
    原厂叫 `VSS` 就保留 `VSS` ✓（如 `CH32V002D4U6` 的裸焊盘 ✓）：
     它是独立网络，必须**布线时特意接到 GND** —— 并进总线＝看着连上其实没连
  ⑦ **面包板里同名（connectorname）的焊盘必须在同一条总线里**（NC/DNP 除外）
  ⑧ `--fzpz`：包里成员是**平铺**的（part.<id>.fzp + 4 个 svg，无子目录），且与本目录文件一致
  ⑨ **`iconView` 的 `<layer layerId>` 必须是 `icon`** —— 写别的（如 `breadboard`）会让
     元件箱里那一格**没有图标**（名字还在），而 Fritzing 一句错都不报（判据 + 实测见正文）
  ⑩ **`schematic` 视图的 `connectorNterminal` 必须落在它自己引脚线的**外端**（居中 ✓）**
     —— 否则连接点会偏（导线接不到引脚尖 ✗）。Fritzing 取的是端子元素的**包围盒中心**
     （`fsvgrenderer.cpp:757-795 calcTerminalPoint()`）⇒ 22×22 那种 rect 必须写成“外端 − 11” ✓

判定：退出码 0 且输出里没有 `FAIL`。
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

VIEWS = ("breadboard", "schematic", "pcb", "icon")

# ★ 第 ⑩ 条的**待修清单**已于 2026-10-15 **删除** ✓ —— 全仓 26 件 / 271 个端子已推平，
#   现在这条**零例外硬判** ✓（不必再编“容差”或豁免 ✗）。
#   当时的底账：`22×22` rect 的 `x/y` 写在外端 ⇒ 端子**中心**偏里 11 单位（≈0.28 mm ✗）、
#   `CN3165` 更跨了**整条引脚**（偏 65 单位 ≈ 1.65 mm ✗✗）、`FPC*` / `SOD-*` / `PC817_SOP4`
#   把端子贴画布边 ✗、`ESP-12F` 贴了画布外（x 为负 ✗）。
#   修法分两类 ✓：① **有 `gen_part.py`** 的 13 件（`CH340C/CH340E/CH340N/ETA3425S2F/H1102NLT/`
#   `RT6150AGQW_rev_1/SY8089/W25Q16JV/XC6206P332MR/CH32V203C8T6/TX-AH-R900PNR{,_rev_1}/CN3165/`
#   `FPC-05F-12P-H15`）改**生成器**再重跑 ✓；② **无生成器的老件** 12 件（`CH340K/CH340X/ESP-12F/`
#   `RT9013/RT9193/SOD-123{,FL}/SOD-323/SOD-523/PC817_SOP4/TPS63051RMWR/FPC05-2H10PX`）
#   直接改 svg（只在 terminal 元素内部换 `x/y`，保留原格式 ✓）。


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    part_dir = os.path.abspath(argv[0])
    part = os.path.basename(part_dir)
    fails, notes = [], []
    fzp_path = os.path.join(part_dir, "part.%s.fzp" % part)
    if not os.path.isfile(fzp_path):
        c = glob.glob(os.path.join(part_dir, "part.*.fzp"))
        if not c:
            raise SystemExit("没找到 .fzp：%s" % fzp_path)
        fzp_path = c[0]
    root = ET.parse(fzp_path).getroot()
    print("文件: %s" % os.path.relpath(fzp_path, os.path.dirname(part_dir)))
    print("moduleId=%s label=%s" % (root.get("moduleId"), (root.findtext("label") or "").strip()))

    # ★ 面包板家族例外 ✓（2026-10-05 用户定，机理见 docs/fritzing-fz-notes.md §10 ✓）：
    #   · 面包板件**故意**让 schematic/pcb 两个视图共用面包板图（原厂件就是这么写的 ✓）
    #     ⇒ “image 要子目录路径” / “缺 schematic/pcb 的 svg”那两条对它们**不适用** ✓
    #     （否则永远是假报警 ✗）；
    #   · 面包板真正该守的是**另一条** ✓：**孔不许在那两个视图里声明连接器** ✗
    #     （否则会把上百条孔 bus 灌进那两个视图的网表 ✗）⇒ 见文末那条新规则 ✓。
    fam = ""
    for p in root.findall("./properties/property"):
        if p.get("name") == "family":
            fam = (p.text or "").strip()
    is_bb = fam.lower() == "breadboard"

    # ★★ 工具类件例外 ✓（2026-10-18 用户定 ✓，原话：「建议这个元件不带 pcb 和原理图」✓）：
    #   · 调试器 / 烧录器这类**台面工具**：**不会被焊到板上** ⇒ 有 pcb 视图反而会
    #     让人把它摆进板里 ✗ ⇒ 允许**只声明 breadboard + icon** ✓；
    #   · 判据 = `family` 落在下面这个集合里 ✓（名字是我们自己挑的，不靠件名硬点名 ✗）；
    #   · ✗ **只对“整块都不带”成立** —— 半带半不带（声明了却没图 / 有图却没声明）
    #     照旧按通用规则判 ✗（那样是写错了，不是有意为之 ✓）。
    #   先例 = `WCH-LinkE`（载板面包板图里画“怎么烧录”用）。
    TOOL_FAMILIES = {"programmer", "debugger"}
    is_tool = fam.lower() in TOOL_FAMILIES

    # ① 视图 → 实际 svg 文件
    svg_of, files = {}, {}
    for v in VIEWS:
        got = glob.glob(os.path.join(part_dir, "svg.%s.%s_%s.svg" % (v, part, v))) \
            or glob.glob(os.path.join(part_dir, "svg.%s.*.svg" % v))
        files[v] = got[0] if got else None
        if got and os.path.basename(got[0]) != "svg.%s.%s_%s.svg" % (v, part, v):
            notes.append("注: %s 视图的文件名不是 svg.%s.%s_%s.svg，而是 %s"
                         % (v, v, part, v, os.path.basename(got[0])))
        img = root.find(".//%sView/layers" % v)
        img = (img.get("image") if img is not None else None) or ""
        if not img.startswith(v + "/"):
            msg = "%sView 的 image=%r 不是子目录路径（应为 %s/…，AGENTS §4）" % (v, img, v)
            # icon 视图复用面包板图是既有做法（FPC05 等）→ 只提示，不算 FAIL
            if v == "icon":
                notes.append("注: " + msg)
            elif is_tool and v in ("schematic", "pcb"):
                notes.append("注: 工具类件 ✓ 不声明 %s 视图（不焊到板上 ✓，属有意为之 ✓）" % v)
            elif is_bb and v in ("schematic", "pcb"):
                notes.append("注: （面包板 ✓）%sView 与面包板视图共用同一张图 ✓ 属既有做法 ✓"
                             % v)
            else:
                fails.append("FAIL " + msg)
        if files[v] is None:
            if is_tool and v in ("schematic", "pcb"):
                notes.append("注: 工具类件 ✓ 不需要 %s 视图的 svg ✓" % v)
            elif is_bb and v in ("schematic", "pcb"):
                notes.append("注: （面包板 ✓）没有 %s 视图的 svg ✓（那两视图共用面包板图 ✓）"
                             % v)
            else:
                fails.append("FAIL 缺 %s 视图的 svg（svg.%s.%s_%s.svg）" % (v, v, part, v))
    print("视图: %s" % ", ".join("%s=%s" % (v, os.path.basename(files[v]) if files[v] else "缺")
                                for v in VIEWS))

    # ⑨ **iconView 的图层必须写 `icon`** ✓（2026-10-15 用户报「看不到图标」后钉死 ✓）
    #   为什么 ✗：Fritzing 用「该视图的图层位」判断图标文件能不能用 ——
    #     `src/model/modelpartshared.cpp:674-684` 的 `imageFileName(viewID, viewLayerID)`：
    #         if ((viewImage->layers & (one << viewLayerID)) == 0) return "";
    #     ⇒ 写成 `breadboard` 时 `imageFileName(IconView, Icon)` 返回**空串** ⇒
    #       渲染器（`partsbinlistview.cpp` `loadImage` → `FSvgRenderer::getPixmap`）
    #       拿不到文件 ⇒ 元件箱里那一格**没有图标** ✗（名字/tooltip 仍在 ✓，
    #       所以人看到的现象就是"空白格" ✗，而 Fritzing **一句错都不报** ✗）。
    #   2026-10-15 实测 ✓：`BAS70BRW` / `BAS70DW-04`（后者复用前者的生成器）就是
    #     这么写的 —— 两个件在 MINE 箱里一直只剩空白格 ✓；改成 `icon` 即恢复 ✓。
    #   ★ 全仓量过 ✓：**117 个件的 iconView 全是 `icon`** ✓ ⇒ 这条**零例外**，可以硬判 ✗；
    #   ★ 只查 icon 视图 ✗：另三个视图**允许跨用图层**（面包板件复用面包板图、
    #     `SYB-118` 的 schematic/pcb 也写 `breadboardbreadboard` ✓）⇒ 那三处硬判只会
    #     变成假报警制造机 ✗。
    icon_layers = root.findall("./views/iconView/layers/layer")
    bad_layers = [l.get("layerId") for l in icon_layers if l.get("layerId") != "icon"]
    if bad_layers:
        fails.append("FAIL iconView 的 layer layerId=%s（**必须**是 `icon`）—— 写别的会让"
                     "图标整格空白（判据：modelpartshared.cpp:679 图层位）" % bad_layers)

    # ⑩ **端子必须落在引脚线的外端** ✓（2026-10-15 用户报「端点位置放错了」后加 ✓）
    #   判据出处：Fritzing 取端子元素的**包围盒中心**（`fsvgrenderer.cpp:757-795` 的
    #     `calcTerminalPoint()` ✓）；而**核心库**的端子 rect 是“以引脚线末端为中心”画的
    #     （实测离两端 0.0x / 95.0x ✓）⇒ 我们的件也必须 `端子中心 == 引脚线外端` ✓，
    #     否则连接点会偏：`LED-0603` 的 2 脚曾把 rect 写在**阴极杠**上（偏半个引脚 ✗，用户截图 ✓）；
    #     一批老件则是 22×22 rect 的 `x/y` 写在外端 ⇒ 中心偏里 11 单位 ✗。
    #   外端 = 离**本体包围盒中心**较远的那一端 ✓（不赌引脚自左向右 ✗）。
    #   ★ 外端 = 离**本体包围盒中心**较远的那一端 ✓（不赌引脚自左向右 ✗）。
    #   ★ 2026-10-15 起**零例外** ✓（待修清单已删）：全仓 26 件 / 271 个端子推平后，
    #     再无一件偏离 ✓；改完先拿 4 件样本让用户检验（他说 ok ✓）再推平全仓 ✓。
    if files.get("schematic"):
        _sch = open(files["schematic"], encoding="utf-8", errors="replace").read()

        def _attrs(tag):
            return dict(re.findall(r'''([\w:.-]+)\s*=\s*["']([^"']*)["']''', tag))

        _pins, _terms = {}, {}
        for _m in re.finditer(r"<line\b[^>]*>", _sch):
            _a = _attrs(_m.group(0))
            _i = _a.get("id", "")
            if _i.startswith("connector") and _i.endswith("pin") and "x2" in _a:
                _pins[_i[:-3]] = (float(_a["x1"]), float(_a["y1"]),
                                  float(_a["x2"]), float(_a["y2"]))
        for _m in re.finditer(r"<(?:rect|circle)\b[^>]*>", _sch):
            _a = _attrs(_m.group(0))
            _i = _a.get("id", "")
            if not (_i.startswith("connector") and _i.endswith("terminal")):
                continue
            if "cx" in _a:                      # 圆/椭圆：中心就是 cx,cy ✓
                _terms[_i] = (float(_a["cx"]), float(_a["cy"]))
            else:                                # rect：x/y 是**左上角** ⇒ 要加半宽/半高 ✓
                _terms[_i] = (float(_a["x"]) + float(_a.get("width", 0)) / 2,
                              float(_a["y"]) + float(_a.get("height", 0)) / 2)
        _xs, _ys = [], []
        for _m in re.finditer(r"<(?:rect|line|polygon|circle|path)\b[^>]*>", _sch):
            _a = _attrs(_m.group(0))
            _i = _a.get("id", "")
            if _i.endswith("pin") or _i.endswith("terminal"):
                continue                        # 引脚/端子不算“本体” ✓
            try:
                if "x" in _a and "width" in _a:
                    _xs += [float(_a["x"]), float(_a["x"]) + float(_a["width"])]
                    _ys += [float(_a["y"]), float(_a["y"]) + float(_a.get("height", 0))]
                elif "x1" in _a:
                    _xs += [float(_a["x1"]), float(_a["x2"])]
                    _ys += [float(_a["y1"]), float(_a["y2"])]
                elif "points" in _a:
                    for _p in _a["points"].split():
                        _px, _py = _p.split(",")[:2]
                        _xs.append(float(_px))
                        _ys.append(float(_py))
            except (ValueError, IndexError):
                continue
        if _pins and _xs:
            _cx, _cy = (min(_xs) + max(_xs)) / 2, (min(_ys) + max(_ys)) / 2
            _bad = []
            for _pid, (_x1, _y1, _x2, _y2) in sorted(_pins.items()):
                _t = _terms.get(_pid + "terminal")
                if _t is None:
                    continue
                _d1 = (_x1 - _cx) ** 2 + (_y1 - _cy) ** 2
                _d2 = (_x2 - _cx) ** 2 + (_y2 - _cy) ** 2
                _out = (_x1, _y1) if _d1 > _d2 else (_x2, _y2)
                _span = ((_x2 - _x1) ** 2 + (_y2 - _y1) ** 2) ** 0.5
                _dist = ((_t[0] - _out[0]) ** 2 + (_t[1] - _out[1]) ** 2) ** 0.5
                if _dist > max(0.01, _span * 0.02):
                    _bad.append("%s 偏 %.3f" % (_pid, _dist))
            if _bad:
                fails.append("FAIL 端子不在引脚线**外端**（应居中 ✓）：%s"
                             % "; ".join(_bad[:4]))
        else:
            notes.append("注: （跳过 ⑩）原理图引脚不是 `<line>` 或没有本体图形 ⇒ 量不了外端 ✓")

    # 各 svg 的 id 集合（顺便查重复 id = ④）
    ids_of = {}
    for v, p in files.items():
        if not p:
            continue
        a = open(p, encoding="utf-8").read()
        # ★★ 2026-10-15 ✓ **引号两种都认** ✗（原来只写 `id="…"` ✗）：
        #   起因 = 新建 `LED-0603` 时，它的 **pcb/icon/breadboard 三张沿用 Fritzing core 原图** ✓
        #   （`svg/_assets/led0603_core_*.svg` ✓），而那批老图用的是**单引号**属性 ✗
        #   （`<line id='connector0pad' …>` ✓）⇒ 旧正则 **一条也读不到** ✗ ⇒ 误报
        #   「connector0pad 在 pcb 视图 svg 里找不到」✗ —— 那是**尺子错**、不是数据错 ✗
        #   （仓规：报 FAIL 先量清是哪一边 ✗）。
        all_ids = re.findall(r"""\bid\s*=\s*["']([^"']+)["']""", a)
        dup = sorted({i for i in all_ids if all_ids.count(i) > 1})
        if dup and v != "icon":
            fails.append("FAIL %s 视图 svg 里有重复 id：%s" % (v, dup[:6]))
        ids_of[v] = set(all_ids)

    # ②③ connector ↔ svgId
    declared, per_view_used = set(), {v: set() for v in VIEWS}
    svgid_to_cid = {}
    n_conn = 0
    for c in root.iter("connector"):
        cid = c.get("id")
        if not cid:
            fails.append("FAIL 有 <connector> 没有 id")
            continue
        n_conn += 1
        declared.add(cid)
        if not (c.get("name") or "").strip():
            fails.append("FAIL %s 缺 name 属性" % cid)
        vs = c.find("views")
        if vs is None or not len(vs):
            fails.append("FAIL %s 的 <views> 是空的（Fritzing 认不出这个脚）" % cid)
            continue
        for child in vs:
            v = child.tag.replace("View", "")
            if v not in VIEWS:
                notes.append("注: %s 里有未知视图 <%s>" % (cid, child.tag))
                continue
            for p in child.iter("p"):
                for attr in ("svgId", "terminalId"):
                    sid = p.get(attr)
                    if not sid:
                        continue
                    per_view_used[v].add(sid)
                    svgid_to_cid[(v, sid)] = cid
                    if sid not in ids_of.get(v, set()):
                        fails.append("FAIL %s 的 %s=%s 在 %s 视图 svg 里找不到"
                                     % (cid, attr, sid, v))
    print("connector: %d 个（声明了 %d 个 id）" % (n_conn, len(declared)))

    # ③ 反向：svg 里的 connector…id 都要在 .fzp 里声明
    #    （**icon 视图不查**：图标只是张图，Fritzing 不看它的 connector id）
    for v, p in files.items():
        if not p or v == "icon":
            continue
        for i in sorted(i for i in ids_of[v] if re.match(r"connector\d+(pin|pad|terminal)$", i)):
            if i not in per_view_used[v]:
                fails.append("FAIL %s 视图里的 id=%s 没有被 .fzp 引用（没主的图形）" % (v, i))

    # ⑤ buses
    in_bus = {}
    for b in root.iter("bus"):
        bid = b.get("id")
        mem = [m.get("connectorId") for m in b.iter("nodeMember")]
        for m in mem:
            if m not in declared:
                fails.append("FAIL 总线 %s 引用了不存在的 %s" % (bid, m))
            elif m in in_bus:
                msg = "%s 同时在总线 %s 和 %s 里" % (m, in_bus[m], bid)
                if is_bb:
                    # ★ 面包板例外 ✓（2026-10-05 用户定）：面包板可以用**两段轨共用几只孔**
                    #   来表达“这段是连着的” ✓ —— `SYB-118` 就是这样 ✓，用户实测确认
                    #   “之前的电源轨分组才是正确的，不能改” ✓（我按“X 应与 Y 对称”推错了 ✗）。
                    #   ⇒ 对面包板只**提示** ✓；对别的件仍然是 **FAIL** ✗（那是真错 ✓）。
                    notes.append("注: （面包板 ✓）" + msg + " ✓ 属既有做法 ✓")
                else:
                    fails.append("FAIL " + msg)
            else:
                in_bus[m] = bid
    print("总线: %s" % ", ".join("%s(%d)" % (b.get("id"), len(list(b.iter("nodeMember"))))
                                for b in root.iter("bus")))

    # ⑥ 裸露焊盘的**总线归属**（用户 2026-09-15 定“独立成网”；2026-10-17 **改为**
    #    “引脚里的 GND/VSS 都要与散热盘连上，做法与 BQ25570 相同” ⇒ 现在**允许**同在一条总线）：
    #     ① 名字**尊重原厂命名** —— 原厂叫 VSS 就保留 VSS（CH32V002D4U6 就是）✓；
    #     ② 允许的总线只有两种正当情形（否则仍判 FAIL，防“莫名其妙并网”）：
    #        a) 总线里全是它**自己的 PCB 专用铜件**（热过孔/焊盘）= 同一块铜；
    #        b) 总线里包含**它自己的热过孔**（说明是刻意声明的散热盘网）。
    #        ⇒ pad 与“别人的脚”混在一条总线、又没有任何自己的过孔 ⇒ FAIL ✓
    EPAD_NAME = re.compile(r"^(EPAD\d*|EP\d*)$", re.I)
    EPAD_HINT = re.compile(r"exposed\s*pad|thermal\s*pad|裸露焊盘|散热盘|datasheet\s*pin\s*0", re.I)
    VIA_NAME = re.compile(r"_VIA\d*$", re.I)      # 散热盘自己的热过孔：**不是**裸焊盘 ✓
    bus_members = {}
    for b in root.iter("bus"):
        bus_members[b.get("id")] = [m.get("connectorId") for m in b.iter("nodeMember")]
    conn_views, conn_name = {}, {}
    for c in root.iter("connector"):
        vs = set()
        for views in c.iter("views"):
            vs |= {ch.tag for ch in list(views)}
        conn_views[c.get("id")] = vs
        conn_name[c.get("id")] = c.get("name") or ""
    for c in root.iter("connector"):
        cid, nm = c.get("id"), (c.get("name") or "")
        desc = " ".join((d.text or "") for d in c.iter("description"))
        if VIA_NAME.search(nm):
            continue            # 热过孔：是裸焊盘那块铜的一部分，不适用 ⑥ ✓
        if EPAD_HINT.search(desc) and not EPAD_NAME.match(nm):
            print("注: 裸露焊盘 %s 叫「%s」（不是 EPAD/EP）—— 原厂命名就保留 ✓"
                  "（AGENTS §5）" % (cid, nm))
        if cid in in_bus and (EPAD_NAME.match(nm) or EPAD_HINT.search(desc)):
            others = [m for m in bus_members.get(in_bus[cid], []) if m and m != cid]
            pcb_only = [m for m in others if conn_views.get(m) == {"pcbView"}]
            has_via = [m for m in others if VIA_NAME.search(conn_name.get(m, ""))]
            if others and len(pcb_only) == len(others):
                print("注: 裸露焊盘 %s 与它自己的 %d 个 PCB 专用铜件同一总线（%s）——"
                      "那是**同一块铜**（过孔/焊盘）✓" % (cid, len(others), in_bus[cid]))
            elif has_via:
                print("注: 裸露焊盘 %s 与 %d 个脚 + %d 个热过孔同一条总线（%s）——"
                      "GND/VSS 与散热盘同网（用户 2026-10-17 定）✓"
                      % (cid, len(others) - len(has_via), len(has_via), in_bus[cid]))
            else:
                fails.append("FAIL 裸露焊盘 %s（name=%s）进了总线 %s，却既没有自己的热过孔、"
                             "也不是全由 PCB 专用铜件组成 —— 来历不明的并网（AGENTS §5）"
                             % (cid, nm, in_bus[cid]))

    # ⑦ 面包板里**同名焊盘必须在同一条总线里**
    #    （踩过：SCS0 有两个焊盘 —— P4 那列一个、P8 的 pin3 一个 —— 只把第一个接上芯片脚、
    #      另一个发了板级号，却忘了给 SCS0 建总线 ⇒ Fritzing 里它们成了两个不相干的网）
    bb = files.get("breadboard")
    if bb:
        a = open(bb, encoding="utf-8").read()
        groups = {}
        for tag in re.findall(r"<(?:circle|rect|path)\b[^>]*>", a):
            # ★ 属性引号两种都认 ✓（同上面那条：core 老图用单引号 ✗）
            at = dict(re.findall(r"""([\w:-]+)\s*=\s*["']([^"']*)["']""", tag))
            cid, nm = at.get("id", ""), at.get("connectorname", "")
            if re.fullmatch(r"connector\d+pin", cid) and nm:
                groups.setdefault(nm, []).append(cid)
        for nm, members in sorted(groups.items()):
            if len(members) < 2 or nm.upper() in ("NC", "N/C", "DNP", "-"):
                continue                      # NC/DNP 这类**本来就不该并**（未连接焊盘）
            # nodeMember 里写的是 connectorId（不带 pin 后缀）→ 先用 svgId 反查
            b = {in_bus.get(svgid_to_cid.get(("breadboard", m), "")) for m in members}
            if len(b) != 1 or None in b:
                fails.append("FAIL 面包板里 %d 个同名焊盘「%s」没在同一条总线里（各自属于 %s）"
                             % (len(members), nm, sorted(str(x) for x in b)))

    # ⑧ 无源件**必须有参数数据项**，且**属性名必须小写** ✓（2026-10-13 用户定 ✓，正文 = A13 ✓）
    #   起因（用户原话 ✓）：「电阻电容更是**没有阻值容量值**，**无法与网表进行校对**」✗
    #   为什么必须小写 ✗（出处 = Fritzing 源码 ✓，本机 `F:\build-fritzing\fritzing-app\src` ✓）：
    #     `items/resistor.cpp:100` 读 = `properties().value("resistance", "220")` ✓
    #       —— QHash 查找是**精确匹配** ✗ ⇒ 部件写 `Resistance`（大写 ✗）时**取不到值** ✗
    #       ⇒ 用户改完阻值，它内部**还当默认 220** ✗（静默失效 ✗，最难查的一类 ✓）；
    #     `:161` 写 = `setLocalProp("resistance", …)` ✓、`itembase.cpp:226` 的
    #       `TranslatedPropertyNames` 也只登记小写 ✓。
    #     ★ 核心库 `core/resistor_5band.fzp` / `SMD_resistor_0402.fzp` 就是大写 ✗
    #       —— 那是**它自己的** bug ✗，别照抄 ✗。
    _label = (root.findtext("label") or "").strip().upper()
    _tax = (root.findtext("taxonomy") or "").strip()
    _props = {}
    for _p in root.iter("property"):
        _props[_p.get("name") or ""] = (_p.get("showInLabel") or "", (_p.text or "").strip())
    for _bad in ("Resistance", "Capacitance"):
        if _bad in _props:
            fails.append("FAIL 属性名 `%s` 必须小写（`%s`）✗ —— Fritzing 按小写**精确匹配**，"
                         "大写会**静默取不到值** ✗（items/resistor.cpp:100 ✓；正文 A13 ✓）"
                         % (_bad, _bad.lower()))
    _need = None
    if _tax.startswith("discreteParts.resistor") or _label == "R":
        _need = ("resistance", "阻值")
    elif _tax.startswith("discreteParts.capacitor") or _label == "C":
        _need = ("capacitance", "容值")
    if _need:
        _key, _cn = _need
        if _key not in _props:
            fails.append("FAIL %s 件缺 `%s`（%s）数据项 ✗ —— 没有它**没法与网表校对** ✗"
                         "（正文 A13 / B6.3 ✓；电阻件跑 `tools\\add_resistance.py` 补 ✓）"
                         % (_label or _tax, _key, _cn))
        else:
            if _props[_key][0] != "yes":
                fails.append("FAIL %s 的 `%s` 没有 showInLabel=\"yes\" ✗ ⇒ 标签上看不见参数 ✗"
                             "（正文 B6.3 ✓）" % (_label or _tax, _key))
            if not _props[_key][1]:
                notes.append("注: %s 的 `%s` 值是空的 —— 能填 ✓，但空着标签上就没有数 ✓"
                             % (_label or _tax, _key))

    # ★★ 面包板专用硬规矩 ✓（2026-10-05 用户定，机理见 docs/fritzing-fz-notes.md §10 ✓）：
    #   孔的连接器**只许**在 breadboard 视图里声明 ✗ —— 一旦在 schematic/pcb 里也声明，
    #   那两个视图就会给孔**建连接器项** ⇒ 上百条孔 bus 被塞进它们的网表 ✗（而且看不见 ✗）
    #   ⇒ Fritzing 状态栏假报「还有 N 个连接件没布线」✗。机器守同源 = breadboard_only_views.py ✓
    if is_bb:
        nbad = 0
        for c in root.iter("connector"):
            v = c.find("views")
            for vn in ("schematicView", "pcbView"):
                if v is not None and v.find(vn) is not None:
                    nbad += 1
        if nbad:
            fails.append("FAIL 面包板的孔在 schematic/pcb 视图里也声明了连接器：**%d 块** ✗"
                         "（会把孔 bus 塞进那两个视图的网表 ✗；用 tools/breadboard_only_views.py "
                         "修 ✓，见 docs/fritzing-fz-notes.md §10 ✓）" % nbad)

    # ⑥ fzpz
    if "--fzpz" in argv:
        z = os.path.abspath(argv[argv.index("--fzpz") + 1])
        if not os.path.isfile(z):
            fails.append("FAIL 没有 %s" % z)
        else:
            with zipfile.ZipFile(z) as zf:
                names = zf.namelist()
            print("包内成员: %s" % ", ".join(names))
            if any("/" in n or "\\" in n for n in names):
                fails.append("FAIL 包里不该有子目录（要平铺，AGENTS §4）")
            # ★ 期望的成员名 = **fzp 自己声明的 `image=`** ✓（`<view>/<名>` ⇒ 平铺成
            #   `svg.<view>.<名>` ✓，就是 §10 那条"部署/打包按 fzp 自己的声明反推" ✓）。
            #   ✗ 别按"我们的命名习惯"去猜 ✗：老件 `SYB-118` 的图形就叫
            #   `svg.breadboard.SYB-118_1.svg` ✓，fzp 指的也正是它 ✓ ⇒ 包是对的 ✓
            #  （文件名不合规那条只**提示** ✓，见上面 ①）。
            want = {os.path.basename(fzp_path)}          # ★ = 磁盘上那个真名字 ✓
            #   （✗ 别写死 `part.<目录名>.fzp` ✗：`3Pin-LED` 这类件的 fzp 是按 moduleId
            #     命名的 ✓，目录名跟它不一样 ✓ —— 老规矩"按 fzp 自己的声明反推" ✓。）
            vw = root.find("views")
            for e in (list(vw) if vw is not None else []):
                lay = e.find("layers")
                if lay is None or not lay.get("image"):
                    continue
                # ★ `image="breadboard/8205HA_breadboard.svg"` ⇒ 包内平铺名
                #   `svg.breadboard.8205HA_breadboard.svg` ✓ —— **要用 basename** ✓
                #   （✗ 把 `image` 整串拼进去会得到 `svg.breadboard.breadboard.…` ✗）
                want.add("svg.%s.%s" % (e.tag.replace("View", ""),
                                        os.path.basename(lay.get("image"))))
            if is_bb:
                # ★ 面包板：schematic/pcb 共用面包板图（原厂同形 ✓）⇒ 不要求那两份独立成员 ✓
                want = {w for w in want
                        if not any(w.startswith("svg.%s." % v) for v in ("schematic", "pcb"))}
            if set(names) != want:
                fails.append("FAIL 包内成员与预期不符（多: %s；少: %s）"
                             % (sorted(set(names) - want), sorted(want - set(names))))

    print()
    for n in notes:
        print(n)
    if fails:
        print("\n".join(fails))
        print("=== %d 项 FAIL ===" % len(fails))
        return 1
    print("=== 全部通过 ===")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
