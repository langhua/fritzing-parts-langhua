# -*- coding: utf-8 -*-
r"""位号文字的**宽度表**（唯一实现 ✓）—— 由 `_scratch/adv_measure.py` **实测**得到 ✓

为什么必须量 ✗：要判"位号文字有没有压到导线/别的元件" ✓ 就得有**文字包围盒** ✓；
  随手写个 0.6em ✗ ⇒ 压没压到全凭那个数 ⇒ 结论不可查 ✗（违反"数据要能指出来源" ✓）。

实测结果（2026-09-27 ✓，cairosvg 渲染 + PIL 扫像素 ✓）：
  · **本机没装 DroidSans** ✗ ⇒ cairosvg 退回一个**等宽**字体 ✓
    ⇒ 绝大多数字符的步进**恰好 = 0.5em** ✓（`i` 与 `M` 一样宽 ✓）；
  · 只有 `±` `Ω` 是 **1.0em** ✓。
  ⇒ 表就两条 ✓（等宽是**推断出来的** ✓，实测每个字符都对得上 ✓ —— 见 `adv_measure.py` 的输出 ✓）。
  ★ 换机器、或装了 DroidSans ⇒ **必须重跑 `_scratch/adv_measure.py` 并更新本文件** ✓
    （否则\"压没压到\"的判据就不成立 ✓）。

★ 包围盒口径 ✓：宽 = **步进之和** ✓（比墨迹略宽 ✓ —— 末字右侧边距不算 ✗）
  ⇒ 判"压到"**偏保守** ✓（宁可多报 ✓）。
"""
ADV_DEFAULT = 2.4977          # 0.5em @ 字号 5 ✓（实测 2.4977 ✓）
ADV_SPECIAL = {"\u00b1": 4.9953, "\u03a9": 4.9953}      # ± Ω = 1.0em ✓
CAP_EM = 0.75                 # 基线以上的**字高**（em ✓）—— 与 `label_bbox` **同一口径** ✓（唯一实现 ✓）

# ── 位号文字块的**内容**（一行一个字符串 ✓）—— ★★ **唯一实现** ✓（2026-10-09 上收 ✓）
#   ★ 为什么上收 ✗：生成器／渲染器／探针**三处**都要知道"这个件画了几行字、每行多宽" ✓
#     才能判"文字压没压东西" ✗。原来这条规则**只写在 `render_sch.py` 里** ✗ ⇒
#     生成器只能**间接受益**（读 `render_sch --pins-out` 出的 `LAB` ✓）
#     ⇒ 一旦谁想单独用（探针 ✓、测量脚本 ✓）就得**再抄一份** ✗（本仓最贵的那类错 ✗）。
#   ★ 口径 = **Fritzing 自己的**（由导出实测反推 ✓，见 `render_sch.py` 那一整段注释 ✓）：
#     · 第 1 行 = instance 的 `<title>` ✓（= 位号 ✓）；
#     · 之后 = fzp 里 `showInLabel="yes"` 的属性**值** ✓，**按 fzp 属性顺序的逆序** ✓；
#     · 空值**不出行** ✓；重复值**不出行** ✓；
#     · `resistance` 这类**内置类目单位**会补在纯数字后面 ✓（只列实测过的 ✓）；
#     · 一个 `yes` 都没有 ⇒ 用实例的 `part number` ✓。
#   ★★ 与 `render_sch.py` 原来的内联代码**逐字同义** ✓（不许改口径 ✗ —— 改了 LAB 就变了 ✓）。
_UNIT_BY_PROP = {"resistance": "\u03a9"}


def fritzing_lines(title, fzp_path, vals=None):
    r"""位号文字块的行 ✓（= Fritzing 画出来的那几行 ✓，唯一实现 ✓）

    `title` = instance 的 `<title>` ✓；`fzp_path` = instance 的 `path=` ✓（磁盘路径 ✓）；
    `vals` = instance 的属性 `name -> value` ✓。★ fzp 文件不在磁盘上 ⇒ **只有位号那一行** ✓
    （与 `render_sch.py` 原实现一字不差 ✓）。
    """
    import os as _os
    import xml.etree.ElementTree as _ET
    lines = [title] if title else []
    vals = vals or {}
    if not (fzp_path and _os.path.isfile(fzp_path)):
        return lines
    yes = [(p.get("name"), (p.text or "").strip())
           for p in _ET.parse(fzp_path).getroot().iter("property")
           if (p.get("showInLabel") or "").lower() in ("yes", "true")]
    for nm, dflt in reversed(yes):
        v = vals.get(nm) or dflt
        _u = _UNIT_BY_PROP.get((nm or "").lower())
        if _u and v and not any(ch.isalpha() for ch in v):
            v = v + _u
        if v and v not in lines:
            lines.append(v)
    if len(lines) == 1 and vals.get("part number"):
        lines.append(vals["part number"])
    return lines


def twidth(text, fs=5.0):
    """字符串宽度（sketch 单位 ✓）"""
    return sum(ADV_SPECIAL.get(c, ADV_DEFAULT) for c in (text or "")) * fs / 5.0


def ink_center(x, y, fs=5.0, text="", anchor="start"):
    r"""`<text>` 的**墨迹框中心**（本地单位 ✓）—— 口径照 Fritzing 源码 ✓

    出处 ✓（2026-10-03 ✓）：Fritzing 给原理图零件文字"转回来"时，转心取的是
    `QSvgRenderer::boundsOnElement()` 量出的**墨迹框中心** ✓
    —— `items/layerkinpaletteitem.cpp` 的 `positionTexts()`（量框 ✓）与 `rotate()`（用它当转心 ✓）。

    横 ✓：`text-anchor="middle"` ⇒ **锚点就是中心** ✓；`end`/`start` ⇒ 按步进宽 `twidth()` 推 ✓。
    纵 ✓：`<text y>` 是**基线** ✓（本库禁用 `dominant-baseline` ✓）⇒
        上缘 = y − CAP_EM·fs ✓、下缘 = y ✓（数字/大写都坐在基线上 ✓）⇒ 中心 = y − CAP_EM·fs/2 ✓。

    ★ 为什么不能用**锚点**当转心 ✗（我 2026-10-03 踩过 ✓）：转心在基线上 ⇒ 墨迹框被翻到基线的
      **另一侧** ✗ ⇒ 数字正好压在脚线上、被导线穿过 ✗（用户截图点名 ✓）；
      用墨迹框中心 ⇒ 墨迹框**位置不变** ✓，只有字被翻正 ✓ —— 这正是纸面上"编号在线上方"
      翻 180° 后变成"在**线下方**"的那个结果 ✓（实测离 0.28mm = 原设计值 ✓）。
    """
    w = twidth(text, fs)
    cx = x if anchor == "middle" else (x - w / 2.0 if anchor == "end" else x + w / 2.0)
    return (cx, y - CAP_EM * fs / 2.0)


def label_bbox(x, y, fs, lines):
    r"""位号文字块的包围盒 ✓（sketch 单位 ✓）

    基线约定（与 Fritzing 一致 ✓，已机验 ✓）：第 i 行的**基线** = 锚点 y + fs×(i+1) ✓
    ⇒ 包围盒 y 从 `y + fs×1 − 0.75fs`（上缘 ✓ = 第 1 行基线往上一个字高 ✓）
      到 `y + fs×(n+1) + 0.2fs`（下缘 ✓ = 末行基线往下一点点 ✓）。
    """
    n = max(1, len(lines))
    w = max((twidth(s, fs) for s in lines), default=0.0)
    return (x, y + fs * 1 - fs * CAP_EM, x + w, y + fs * (n + 1) + fs * 0.2)
