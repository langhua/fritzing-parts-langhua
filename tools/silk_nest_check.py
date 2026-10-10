# -*- coding: utf-8 -*-
r"""`silkscreen` **嵌在铜组里** 的扫描器（2026-10-10 立 ✓，起因 = 用户 Gerber 实测 ✗）

★★ 为什么要有它 ✓：`.fzp` 的 `pcbView` 只声明**图层**（`copper0` / `copper1` / `silkscreen` ✓），
   **不声明"哪块图形属于哪层"** ✗ —— 层归属是 Fritzing 读 SVG 时按**组的 id** 认的 ✓。
   于是把 `<g id="silkscreen">` **嵌在** `<g id="copper1">` 里 ⇒ 那几条丝印线
   **会被当铜导出** ✗（用户 2026-10-10 实测：`SH-1.0-3P-V` 的 7 条 0.12 mm 丝印线
   漏进 `*_copperBottom.gbl` ⇒ 与旁边的 24 mil 走线只隔 **0.0906 mm = 3.57 mil < 5 mil** ✗
   ⇒ 整批 Gerber **不可送板** ✗）。对照件：`WS2812B-1010` 的丝印与铜是**平级**的 ✓ ⇒ 没这问题 ✓。

★ 规矩（唯一一句）✓：**`<g id="silkscreen">` 必须是 `<g id="copper?">` 的兄弟** ✓
  （放在 `<svg>` 根下、与铜组平级 ✓），**绝不许嵌进铜组** ✗。
  本工具的实现口径 = 这一句的**等价硬写法** ✓：丝印组必须**直接挂在 `<svg>` 下** ✓
  （父组 = 无 ✓）。这样**嵌进任何组**（铜组 ✗、或别的外层组 ✗）都报 ✓。

★★ **硬闸门（2026-10-10 第二轮 ✓）**：本仓**曾经**有 7 件老写法（`Crystal-3215`、`Crystal-3225`、
   `FPC-05F-12P-H15`、`MX-1.25-2P-H`、`MX-1.25-3P-V`、`PH-2.0-3P-V`、`USB-B01` ✓）——
   已**全部修好** ✓、`KNOWN` **台账已清空** ✓ ⇒ 现在**全库任何**零件违例都**报错** ✗
   （✗ 不留白名单 ✗）。所以它**进 `tools/tests/run_all.py`** ✓（`silk_nest_selftest.py` ✓）。
   全库现状：**235 个 pcb 视图，违例 0** ✓（2026-10-10 复验 ✓）。

用法：
  py -3.13 -X utf8 tools\silk_nest_check.py [路径 ...]
    · 不给路径 ⇒ 扫本仓 `svg/` 下全部 `svg.pcb.*.svg` ＋ `fzpz/*.fzpz` 里的 pcb 视图 ✓
    · 给的可以是目录（递归 ✓）、`.svg`、或 `.fzpz` ✓
    · `--list` 只列**有问题的**那些 ✓（默认全列 ✓）
退出码：0 = 没有"丝印嵌组" ✗；1 = 有 ✗（**没有白名单** ✓）。
"""
import argparse
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))


def group_parents(text):
    """⇒ {组 id: 父组 id 或 None（= 直接挂在 `<svg>` 下 ✓）}。

    ★ 配平扫描必须认**自闭合**的 `<g id="copper0"/>` ✓（本库既有写法 ✓）——
      不认它就会把外层的 `</g>` 当成自己的 ⇒ 一路吞到文件尾 ⇒ **假阳性** ✗。
    """
    out, stack = {}, []
    for m in re.finditer(r'<g\s+id="([^"]+)"\s*(/?)>|</g>', text):
        if m.group(0) == "</g>":
            if stack:
                stack.pop()
        elif m.group(2) == "/":                      # 自闭合 ⇒ 不入栈 ✓
            out[m.group(1)] = stack[-1] if stack else None
        else:
            out[m.group(1)] = stack[-1] if stack else None
            stack.append(m.group(1))
    return out


def silk_parent(text):
    """⇒ 丝印组的父组（`None` = 合格 ✓）。没有丝印组 ⇒ 也返回 `None` ✓（不是本工具的判据 ✗）。"""
    return group_parents(text).get("silkscreen")


def copper_groups(text):
    """同文件里出现的铜组 id（只作打印用 ✓）。"""
    return re.findall(r'<g\s+id="(copper[0-9]*)"\s*/?>', text)


# ★★ 2026-10-11 补：**第二条硬规则** ✓（用户 2026-10-11 看元件箱发现 ✗）
#   病：`R0603` / `C0603` 的 pcb 里，丝印是**一颗裸 `<rect id="silkscreen">`** ✗
#       —— **没有 `<g id="silkscreen">`** ✗ ⇒ Fritzing 按**组 id** 认层 ⇒ 那坨丝印
#       **不属于丝印层** ✗ ⇒ 元件箱/指示栏里渲出来**多一块**（用户截图 ✗）。
#   而本工具的旧判据（"丝印组的父组必须为 None"✓）对"**根本没有丝印组**"**当合格** ✗✗
#       —— 这正是"闸门有洞"的写法 ✗ ⇒ 补这条 ✓。
SILK_HINT = re.compile(r'(?:^|[\s;"\'])stroke\s*[:=]\s*["\']?#(?:f0f0f0|ffffff)', re.I)
DRAW_TAGS = ("rect", "line", "path", "polygon", "polyline", "circle", "ellipse")


def silk_outside(text):
    """⇒ [(标签, 属性片段), …]：**看着是丝印**（`stroke=#f0f0f0/#ffffff` ✓）
    却**不在 `<g id="silkscreen">` 里** ✗ 的图元 ✓（= 元件箱里那多出来的一块 ✗）。

    ★ 只看**画图元素** ✓（不看 `<g>` 自己的 style ✗），入参 = 该元素**自己的**属性串 ✓。
    """
    out, stack = [], []
    for m in re.finditer(r'<(/?)([A-Za-z]+)\b([^>]*?)(/?)>', text):
        closing, tag, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if tag == "g":
            if closing:
                if stack:
                    stack.pop()
            elif not selfclose:
                gid = re.search(r'id="([^"]*)"', attrs)
                stack.append(gid.group(1) if gid else "")
            continue
        if closing or tag not in DRAW_TAGS:
            continue
        if "silkscreen" in stack:
            continue
        if SILK_HINT.search(attrs) or re.search(r'id="silkscreen"', attrs):
            out.append((tag, m.group(0)[:84]))
    return out


def scan(paths):
    """⇒ ([(显示名, 丝印的父组, 该文件的铜组), …], 扫过的文件数)（只含有问题的 ✓）"""
    bad, loose, files = [], [], []
    for p in paths:
        if os.path.isdir(p):
            for dp, _dn, fn in os.walk(p):
                for f in sorted(fn):
                    if (f.startswith("svg.pcb.") and f.endswith(".svg")) or f.endswith(".fzpz"):
                        files.append(os.path.join(dp, f))
        else:
            files.append(p)
    for p in files:
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if p.endswith(".fzpz"):
            with zipfile.ZipFile(p) as z:
                for nm in sorted(z.namelist()):
                    if nm.startswith("svg.pcb.") and nm.endswith(".svg"):
                        t = z.read(nm).decode("utf-8")
                        par = silk_parent(t)
                        if par is not None:
                            bad.append((rel + " (zip) " + nm, par, copper_groups(t)))
                        for tag, frag in silk_outside(t):
                            loose.append((rel + " (zip) " + nm, tag, frag))
        else:
            with open(p, encoding="utf-8") as fh:
                t = fh.read()
            par = silk_parent(t)
            if par is not None:
                bad.append((rel, par, copper_groups(t)))
            for tag, frag in silk_outside(t):
                loose.append((rel, tag, frag))
    return bad, loose, files


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--list", action="store_true", help="只列有问题的 ✓")
    a = ap.parse_args(argv)
    paths = a.paths or [os.path.join(ROOT, "svg"), os.path.join(ROOT, "fzpz")]
    bad, loose, files = scan(paths)
    print("== silk_nest_check：两件硬规矩 ✓"
          "｜① `silkscreen` 嵌在组里 ✗（判据：丝印组必须**直接挂在 `<svg>` 下** ✓）"
          "｜② 丝印图元**不在** `<g id=\"silkscreen\">` 里 ✗（2026-10-11 补 ✓）"
          "｜扫了 %d 个文件 ==" % len(files))
    for rel, par, cu in bad:
        print("  ✗ ① %-58s 丝印的父组 = %s%s"
              % (rel, par, ("｜该文件铜组：" + ",".join(cu)) if cu else ""))
    for rel, tag, frag in loose:
        print("  ✗ ② %-58s `<%s …` 不在丝印组里 ✗：%s" % (rel, tag, frag))
    if not bad and not loose:
        print("  ✓ 两件都没有 ✓")
    print("⇒ 违例 **%d** 个（不见① %d ✓ 不见② %d ✓；**无白名单** ✓ ⇒ 0 才算过 ✓）"
          % (len(bad) + len(loose), len(bad), len(loose)))
    return 1 if (bad or loose) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
