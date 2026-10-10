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

用法：
  py -3.13 -X utf8 tools\silk_nest_check.py [路径 ...]
    · 不给路径 ⇒ 扫本仓 `svg/` 下全部 `svg.pcb.*.svg` ＋ `fzpz/*.fzpz` 里的 pcb 视图 ✓
    · 给的可以是目录（递归 ✓）、`.svg`、或 `.fzpz` ✓
    · `--list` 只列**有问题的**那些 ✓（默认全列 ✓）
    · `--baseline <文件>` 读一份"已知台账"（每行一个路径 ✓）⇒ 只报**新出现**的 ✗✓
退出码：0 = 没有"新"的嵌套 ✗；1 = 有 ✗。
★ 本仓既有 7 件仍是老写法 ✗（见 `docs/part-dev-guide.md` 的台账 ✓）—— 它们**不在本轮范围** ✓，
  所以本工具**不进 `tools/tests/run_all.py`** ✓（不拿"历史欠账"当红灯 ✗）。
"""
import argparse
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

# 本仓**既有**的老写法（2026-10-10 盘点 ✓ —— 只登记、不修 ✗，等用户点头再动 ✓）
KNOWN = {
    "svg/Crystal-3215/svg.pcb.Crystal-3215_pcb.svg",
    "svg/Crystal-3225/svg.pcb.Crystal-3225_pcb.svg",
    "svg/FPC-05F-12P-H15/svg.pcb.FPC-05F-12P-H15_pcb.svg",
    "svg/MX-1.25-2P-H/svg.pcb.MX-1.25-2P-H_pcb.svg",
    "svg/MX-1.25-3P-V/svg.pcb.MX-1.25-3P-V_pcb.svg",
    "svg/PH-2.0-3P-V/svg.pcb.PH-2.0-3P-V_pcb.svg",
    "svg/USB-B01/svg.pcb.USB-B01_pcb.svg",
    "fzpz/Crystal-3215.fzpz",
    "fzpz/Crystal-3225.fzpz",
    "fzpz/FPC-05F-12P-H15.fzpz",
    "fzpz/MX-1.25-2P-H.fzpz",
    "fzpz/MX-1.25-3P-V.fzpz",
    "fzpz/PH-2.0-3P-V.fzpz",
    "fzpz/USB-B01.fzpz",
}


def copper_span(text, start):
    """从 `<g id="copper?">` 的 `start`（= 开始标签之后）扫到配平的 `</g>`。

    ★ 必须认**自闭合**的 `<g id="copper0"/>` ✓（本库既有写法 ✓）——
      不认它就会把外层的 `</g>` 当成自己的 ⇒ 一路吞到文件尾 ⇒ **假阳性** ✗。
    """
    i, depth = start, 1
    while depth > 0:
        n, c = text.find("<g ", i), text.find("</g>", i)
        if c < 0:
            return len(text)
        if 0 <= n < c:
            end = text.find(">", n)
            if end < 0:
                return len(text)
            if text[end - 1] != "/":          # 自闭合 ⇒ 不入栈 ✓
                depth += 1
            i = end + 1
        else:
            depth -= 1
            i = c + 4
    return i


def bad_groups(text):
    """返回"里面含 `silkscreen` 组"的那些铜组 id ✓（空 = 合格 ✓）。"""
    out = []
    for m in re.finditer(r'<g\s+id="(copper[0-9]*)"\s*>', text):
        if 'id="silkscreen"' in text[m.end():copper_span(text, m.end())]:
            out.append(m.group(1))
    return out


def scan(paths):
    """⇒ [(显示名, 铜组 id 列表), …]（只含有问题的 ✓）"""
    bad = []
    files = []
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
                for nm in z.namelist():
                    if nm.startswith("svg.pcb.") and nm.endswith(".svg"):
                        if bad_groups(z.read(nm).decode("utf-8")):
                            bad.append((rel, ["(zip) " + nm]))
        else:
            g = bad_groups(open(p, encoding="utf-8").read())
            if g:
                bad.append((rel, g))
    return bad, files


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--list", action="store_true", help="只列有问题的 ✓")
    a = ap.parse_args(argv)
    paths = a.paths or [os.path.join(ROOT, "svg"), os.path.join(ROOT, "fzpz")]
    bad, files = scan(paths)
    print("== silk_nest_check：`silkscreen` 嵌在铜组里 ✗｜扫了 %d 个文件 ==" % len(files))
    for rel, g in bad:
        mark = "（台账内 ✓ 老写法）" if rel in KNOWN else "★**新出现** ✗"
        print("  ✗ %-62s %s %s" % (rel, ",".join(g), mark))
    if not bad:
        print("  ✓ 一个都没有 ✓")
    fresh = [rel for rel, _g in bad if rel not in KNOWN]
    print("⇒ 问题 **%d** 个（其中台账外**新**的 **%d** 个）" % (len(bad), len(fresh)))
    return 1 if fresh else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
