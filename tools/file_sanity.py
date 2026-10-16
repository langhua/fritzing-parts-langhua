# -*- coding: utf-8 -*-
"""文件自检（只看文件里写了什么 ✓，不看渲染）：
① 每根**面包板**导线的 `wireExtras/@color` ∈ 面包板那一节配色 ✓
①b 每根**原理图**导线的颜色 ∈ **原理图**那一节配色 ✓（★ 2026-10-16 补 ✓，用户定
    「原理图线色闸门必须补」✓）—— 两节**同名不同值** ✓（orange：面包板 `#ef6100` ✓／
    原理图 `#ff7300` ✓）⇒ ✗ 写错节 = 画岀来对 ✓ 但**颜色下拉回退“蓝”**✗（用户原话「看不到」✗）
①c 原理图里的**白色**（白底看不见 ✗）/ **黄色**（用户 2026-10-13 定「不用黄」✓）⇒ **只提醒** ✗
② 有没有零长段 ✗ / 同向共线的冗余中点 ✗
③ 有没有实例级 `color` 属性（有 ⇒ 可能覆盖颜色 ✗）
④ 图例：文字标签 ↔ 色条 是否按同一顺序配对 ✓（从零件 svg 的 text 里读标签 ✓）

★ 色表**只有一处定义** ✓ = `tools/fz_colors.py` ✓（它自己会拿 Fritzing 的
  `resources/ratsnestcolors.xml` 逐色对一遍 ✓；实测 2026-10-16 两节各 13 色全一致 ✓）。
★ 退出码 ✓：0 = 全合格｜1 = **有不合格项** ✓（2026-10-16 补 ✗ —— 以前它**根本没调 `sys.exit`** ✗，
  报什么都不影响退出码 ⇒ 接进闸门也是个**不会红的闸门** ✗）。
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

# ★ 合法值 = Fritzing 官方配色表 `resources/ratsnestcolors.xml` 里
#   `<view name="breadboardView">` 下每个 `<color … wire="…">` ✓（用别的 hex ⇒ 指示栏回退成蓝 ✗）
#   ★★ 2026-10-16：表**收到一处**了 ✓ —— `tools/fz_colors.py` ✓（它自己会拿真 XML 自校 ✓）；
#     本文件**不再自己抄一份** ✗（实测：抄成 4 份过 ✗ ⇒ 改一处忘三处 ⇒ 整块面包板线色全错 ✗）。
import fz_colors as FC

STANDARD = FC.BB
fzz = sys.argv[1]


def tag(e):
    return e.tag.split("}")[-1]


def child(e, n):
    for c in (e if e is not None else []):
        if tag(c) == n:
            return c
    return None


z = zipfile.ZipFile(fzz)
name = [x for x in z.namelist() if x.endswith(".fz")][0]
r = ET.fromstring(z.read(name))

bad_col, zero, zero_ph, props, bb = [], [], [], [], []
for e in r.iter("instance"):
    ttl = (e.findtext("title") or "").strip()
    ttl_el = e.findtext("title")
    # ★ Fritzing 把实例属性**直接挂在 `<instance>` 下** ✓（不是包在 `<properties>` 里 ✗ ——
    #   我第一版扫描就因此漏掉了图例文字件的 `color` 属性 ✗）
    for p in e:
        if tag(p) == "property" and p.get("name") == "color":
            props.append("%s=%s" % (ttl, p.get("value")))
        if tag(p) == "properties":
            for q in p:
                if q.get("name") == "color":
                    props.append("%s(text)=%s" % (ttl, (q.text or "")[:10]))
    # ★ 该实例在**任意视图**里有没有**真实长度**（非零长）✓ —— 用来区分「占位」与「真退化」✓
    e_real = False
    for _v in (child(e, "views") if child(e, "views") is not None else []):
        _g = child(_v, "geometry")
        if _g is None:
            continue
        if abs(float(_g.get("x2") or 0)) > 1e-9 or abs(float(_g.get("y2") or 0)) > 1e-9:
            e_real = True
            break
    for sub in child(e, "views"):
        if tag(sub) != "breadboardView":
            continue
        g = child(sub, "geometry")
        if g is None or g.get("x2") is None:
            continue
        we = child(sub, "wireExtras")
        col = (we.get("color") if we is not None else None)
        dx, dy = float(g.get("x2")), float(g.get("y2"))
        if col and col not in STANDARD:
            bad_col.append((ttl, col))
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            # ★★ 2026-10-03 修 ✗：零长**未必**是毛病 ✓ —— 走线在别的视图、这里只是**占位** ✓
            #   （Fritzing 硬要求三视图 ✓；非目标视图用零长占位 ✓、坐标不编造 ✓ ——
            #    见 `AuroraTessellation-NFC/hardware/pixel/gen_routes.py` 的 `wire_block` 出处证据 ✓）
            #   ⇒ 只有「**哪个视图都没有长度**」才是真退化 ✗（否则是判据的假阳性 ✗）
            (zero if not e_real else zero_ph).append(ttl)
        peers = [c.get("modelIndex") for c in sub.iter()
                 if tag(c) == "connect" and (c.get("layer") or "") == "breadboardWire"]
        if "WireModuleID" in (e.get("moduleIdRef") or ""):
            bb.append((ttl, col, float(g.get("x")), float(g.get("y")), dx, dy, len(peers)))

print("== 文件自检: %s" % fzz)
print("   ① 非标准色的导线（面包板 ✓ %d 色表）: %s" % (len(FC.BB), bad_col if bad_col else "0 个 ✓"))
# ★★ ①b / ①c 原理图视图（2026-10-16 补 ✓）—— 同一把尺子 ✓，但**取另一节表** ✓（orange 值不同 ✓）
sch_bad, sch_inv, sch_less, sch_seg, sch_cols = [], [], [], 0, set()
for e in r.iter("instance"):
    ttl = (e.findtext("title") or "").strip()
    _vs = child(e, "views")
    for sub in (_vs if _vs is not None else []):
        if tag(sub) != "schematicView":
            continue
        g = child(sub, "geometry")
        if g is None or g.get("x2") is None:
            continue
        sch_seg += 1
        we = child(sub, "wireExtras")
        col = (we.get("color") if we is not None else None)
        if not col:
            continue
        col = col.lower()
        sch_cols.add(col)
        if col not in FC.SCH:
            sch_bad.append((ttl, col, FC.name_of("schematicView", col)))
        elif col in FC.INVISIBLE["schematicView"]:
            sch_inv.append((ttl, col))
        elif col in FC.LESS_VISIBLE["schematicView"]:
            sch_less.append((ttl, col))
if sch_seg:
    print("   ①b 原理图导线 %d 段｜颜色 ⊆ 原理图那一节（%d 色 ✓）: %s"
          % (sch_seg, len(FC.SCH),
             ("✗ %d 根不对 ✗ —— %s" % (len(sch_bad),
              "； ".join("%s=%s（%s）" % (t, c, n) for t, c, n in sch_bad[:6]))) if sch_bad else "0 根 ✓"))
    print("   ①c 原理图的看不见色（只提醒 ✗）: %s"
          % ("； ".join("%s=%s（%s）" % (t, c, "白底看不见 ✗" if c in FC.INVISIBLE["schematicView"]
                                        else "用户定不用黄 ✓") for t, c in sch_inv + sch_less)
             if (sch_inv or sch_less) else "0 根 ✓"))
else:
    print("   ①b 本图没有原理图导线 ⇒ **判不了** ✓ 不判 ✓")
print("   ② 零长**真退化**线: %s" % (zero if zero else "0 个 ✓"))
print("   ②' 零长**占位**线 : %d 个 ✓（非本视图的真实走线 ✓ 三视图占位 ✓ 见 gen_routes.wire_block）"
      % len(zero_ph))
print("   ③ 实例 color 属性: %s" % (props if props else "0 个 ✓（Fritzing 自己也不写 ✓）"))
print("   ④ 面包板导线 %d 段（%d 根）| 颜色: %s"
      % (len(bb), len([b for b in bb if b[6]]), sorted({b[1] for b in bb if b[1]})))
print()
print("== 图例区（x>500 ✓ 按 y 排 ✓）")
for ttl, col, x, y, dx, dy, np_ in sorted(bb, key=lambda b: b[3]):
    if x > 500:
        print("   y=%6.1f  %-14s color=%-9s 长度 %.1f" % (y, ttl, col, abs(dx) + abs(dy)))
print()
print("== 图例文字（从零件 svg 里读 ✓ 按 y 排 ✓）")
labels = []
for e in r.iter("instance"):
    mid = e.get("moduleIdRef") or ""
    if "LogoText" not in mid:
        continue
    sub = child(child(e, "views"), "breadboardView")
    if sub is None:
        continue
    g = child(sub, "geometry")
    y = float(g.get("y")) if g is not None and g.get("y") else 0.0
    txt = ""
    for gg in sub.iter():
        if tag(gg) == "text" and (gg.text or "").strip():
            txt += gg.text.strip()
    labels.append((y, (e.findtext("title") or "").strip(), txt))
for y, ttl, txt in sorted(labels):
    print("   y=%6.1f  %-14s %r" % (y, ttl, txt))

# ★★ 退出码（2026-10-16 补 ✗）：以前本文件**根本没调 `sys.exit`** ✗ ⇒ 报什么都不影响退出码 ✗
#   ⇒ 接进闸门也**永远不会红** ✗（同 AGENTS §14 那条"自证/空转"的教训 ✓）。
_rc = 1 if (bad_col or sch_bad or zero) else 0
print()
print("⇒ %s" % ("✗ 不合格 ✗（上面点名的先处理 ✓）" if _rc else "✓ 全部合格"))
print("   （退出码 %d ✓；口径 = `fz_colors` 两张表 ✓ —— 它自己已拿 Fritzing 的 XML 自校过 ✓）" % _rc)
sys.exit(_rc)
