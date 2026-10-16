# -*- coding: utf-8 -*-
r"""Fritzing 官方导线配色表 —— **唯一一处定义** ✓（2026-10-16 ✓，用户定「原理图线色闸门必须补」✓）。

★★ 为什么单独一个模块 ✗：同一个颜色**名字**在两个视图里**值不同** ✓ ——
   `orange`：**面包板** `#ef6100` ✓ / **原理图** `#ff7300` ✓（两节各 13 色，**唯一不同的就是它** ✓
   —— 2026-10-16 拿真 XML 逐色对过 ✓；★ 如实：`#ef6100` 在原理图那节的实测结果是
   **不在活值里** ✓（不是"被标了 `<obsolete>`"✗ —— 那两节的作废条目实测 **0 条** ✓）；
   两句的**实践后果相同** ✓：写进去画出来对 ✓、颜色下拉认不出、回退"蓝" ✗）。以前这几张表**抄在 4 个文件里** ✗（`file_sanity` / `check_flags` /
   `sch_route` / `bb_compare`）⇒ 改一处忘三处 ✗，实测就因此让**整块面包板的线色全错** ✗
   （2026-10-16：`file_sanity` ① 报 `bb_routed` 3 根 / `bb_legend` 5 根 ✗）。
   ⇒ 表收在这里 ✓，谁要谁 `import fz_colors` ✓（✗ 别再抄第四份 ✗）。

★ **出处（可逐行核 ✓）**：Fritzing 源码树 `fritzing-app/resources/ratsnestcolors.xml`
  —— `<view name="breadboardView">` / `<view name="schematicView">` 两节里每个
  `<color name="…" wire="…">` ✓。**本文件那两张表是抄下来的** ✓ ⇒
  **`py -3.13 tools/fz_colors.py [<ratsnestcolors.xml>]` 会拿真 XML 逐色对一遍** ✓
  （找不到 XML 就**如实说"未校验"** ✗，✗ 不假装 ✓）。
  ★ 口径（★ 要紧）：**只认 `<obsolete>` 之外**的值 ✓ —— 作废值画出来一样对 ✓，
  但 Fritzing 的"颜色"下拉**认不出** ⇒ 回退成"蓝" ✗（实测 ✓）。

用法（自查）：
    py -3.13 tools/fz_colors.py                     # 自动找本机 Fritzing 的 XML 对一遍 ✓
    py -3.13 tools/fz_colors.py <路径\ratsnestcolors.xml>
退出码：0 = 两张表与 XML 一致（或找不到 XML 但结构自洽 ✓）｜1 = **对不上** ✗
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 面包板那一节 ✓（13 色；值**只能**是这里这些 ✓）──────────────────────────────
BB_ROWS = [
    ("blue",   "#418dd9"), ("red",    "#cc1414"), ("black",  "#404040"),
    ("yellow", "#fff800"), ("green",  "#25cc35"), ("grey",   "#999999"),
    ("white",  "#ffffff"), ("orange", "#ef6100"), ("ochre",  "#a37911"),
    ("cyan",   "#33ffc5"), ("purple", "#ab58a2"), ("brown",  "#8c3b00"),
    ("pink",   "#fa50e6"),
]
# ── 原理图那一节 ✓（★ 只有 `orange` 与面包板**不同** ✓，其余同名同值 ✓）──────────
SCH_ROWS = [(n, ("#ff7300" if n == "orange" else c)) for n, c in BB_ROWS]

BB = {c for _n, c in BB_ROWS}
SCH = {c for _n, c in SCH_ROWS}
BB_LIST = [c for _n, c in BB_ROWS]          # 按官方次序 ✓（`sch_route.py` 的兜底分色用 ✓）
SCH_LIST = [c for _n, c in SCH_ROWS]
VIEWS = {"breadboardView": BB, "schematicView": SCH}
_ROWS = {"breadboardView": BB_ROWS, "schematicView": SCH_ROWS}
# ★ 两个视图里**画出来看得见吗** ✓（用户 2026-10-13 定「不用黄色」✓；白底上白线 = 看不见 ✗）
INVISIBLE = {"breadboardView": set(), "schematicView": {"#ffffff"}}
LESS_VISIBLE = {"breadboardView": set(), "schematicView": {"#fff800"}}


def name_of(view, hexv):
    """色值 → 官方颜色名 ✓（报告里用人看得懂的名字 ✓）"""
    for n, c in _ROWS.get(view, ()):
        if c.lower() == str(hexv).lower():
            return n
    for v2, rows in _ROWS.items():                  # 别的视图里有同名同值的 ⇒ 也认 ✓
        for n, c in rows:
            if c.lower() == str(hexv).lower():
                return "%s（%s 视图的值 ✗）" % (n, "原理图" if v2 == "schematicView" else "面包板")
    return "表外值"


def _candidates():
    return [
        os.environ.get("FZ_RATS") or "",
        r"F:\build-fritzing\fritzing-app\resources\ratsnestcolors.xml",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Fritzing\resources\ratsnestcolors.xml"),
        r"C:\Program Files\Fritzing\resources\ratsnestcolors.xml",
        r"C:\Program Files (x86)\Fritzing\resources\ratsnestcolors.xml",
        "/usr/share/fritzing/resources/ratsnestcolors.xml",
        "/Applications/Fritzing.app/Contents/Resources/app/resources/ratsnestcolors.xml",
    ]


def load(path=None):
    """⇒ (文件路径, {视图: (活的值集合, 作废的值集合)})——只用真 XML 判 ✓

    ★ 结构照 XML 自己的写法读 ✓（✗ 不赌"作废怎么写" ✗）：`<view>` 底下
      `<color wire="…"/>` = 活的 ✓；`<obsolete>` 里的 = 作废的 ✓（两种写法都收 ✓）。
    """
    for p in ([path] if path else _candidates()):
        if p and os.path.isfile(p):
            root = ET.parse(p).getroot()
            out = {}
            for v in root.iter("view"):
                live, obs = set(), set()

                def grab(el, dead):
                    for c in el.iter("color"):
                        val = (c.get("wire") or "").lower()
                        if val:
                            (obs if dead else live).add(val)

                for ch in v:
                    t = ch.tag.split("}")[-1]
                    if t == "obsolete":
                        grab(ch, True)
                    elif t == "color":
                        grab(ch, (ch.get("obsolete") or "").lower() in ("1", "true", "yes"))
                if live or obs:
                    out[v.get("name") or "?"] = (live, obs)
            return p, out
    return None, {}


def check(path=None, quiet=False):
    """⇒ (rc, [报告行…]) —— 两张抄下来的表 vs 真 XML ✓"""
    p, got = load(path)
    lines = []
    if not p:
        lines.append("   · **未校验**（本机找不到 `ratsnestcolors.xml` ✗）—— 两张表是**抄文档**的 ✓，"
                     "出处已注明 ✓；想核就设 `FZ_RATS=<路径>` ✓")
        return 0, lines
    lines.append("   · XML = %s ✓" % p)
    rc = 0
    for view, want in _ROWS.items():
        live, obs = got.get(view, (set(), set()))
        if not live:
            lines.append("   ✗ XML 里没有 `<view name=\"%s\">` 这一节 ✗" % view)
            rc = 1
            continue
        mine = {c for _n, c in want}
        worse = sorted(mine - live)
        fewer = sorted(live - mine)
        lines.append("   %s：表 %d 色 ✓｜XML 活 %d 色%s" % (view, len(mine), len(live),
                     ("｜作废 %d 色 ✓" % len(obs)) if obs else ""))
        if worse:
            lines.append("       ✗ 表里这些值 XML 里**不是活的** ✗（可能是作废值 ✓）：%s" % worse)
            rc = 1
        if fewer:
            lines.append("       ✗ XML 还有表里没有的活值 ✗：%s" % fewer)
            rc = 1
        for n, c in want:
            if c in obs and c not in live:
                lines.append("       ✗ %s 的 %s 是**作废值** ✗" % (view, c))
                rc = 1
    if not quiet:
        for ln in lines:
            print(ln)
    return rc, lines


if __name__ == "__main__":
    print("== 官方配色表自校（唯一一处定义 = 本模块 ✓）==")
    for lbl, rows in (("面包板", BB_ROWS), ("原理图", SCH_ROWS)):
        print("   %s %d 色：%s" % (lbl, len(rows), ", ".join("%s=%s" % r for r in rows)))
    print("★ 两个视图**同名的值不同的**：%s"
          % ", ".join("%s: %s vs %s" % (n, dict(BB_ROWS)[n], dict(SCH_ROWS)[n])
                      for n in dict(BB_ROWS) if n in dict(SCH_ROWS)
                      and dict(BB_ROWS)[n] != dict(SCH_ROWS)[n]))
    rc, _ = check(sys.argv[1] if len(sys.argv) > 1 else None)
    print("⇒ %s" % ("✓ 与 XML 一致" if rc == 0 else "✗ 对不上（见表 ✓）"))
    sys.exit(rc)
