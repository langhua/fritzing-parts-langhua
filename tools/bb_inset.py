"""`bb_inset.py <部件目录> [--dry]` —— 给绿色转接板元件的 `gen_part.py` 加"**板边让半格**" ✓。

**规矩**（AGENTS §3b，用户 2026-09-27 定 ✓）：转接板不许影响「板外」孔的插拔 ✓
⇒ 板边不许压在孔行/孔列的连线上 ✗ ⇒ 板框四周各让 **半格 = 50 内部单位（1.27mm）** ✓。

**为什么做成受限 codemod**（而不是"看见 00aa44 就改" ✗）：
 · 各件生成器写法不同 ✗ ⇒ 只认下面几种**精确写法** ✓，匹配不上就**报出来、一个字不动** ✗；
 · 只改**那一行 rect 的几何** ✓，别的一律不碰 ✓；
 · `INSET = 50` 定义在**模块级** ✓（写进语句里最稳 ✓，不受"它包在列表字面量里"影响 ✓）；
 · 改完**必跑**：`audit_green_board.py`（相位 ✓）+ `check_inside_board.py`（本体还在板内吗 ✓）。

用法：py -3.13 bb_inset.py <部件目录> [--dry]
"""
import re
import os
import sys

KNOWN = [
    # ① f-string 版（SS34 / DSIC01LS-P / CN3165 那类）
    ('<rect x="0" y="0" width="{bw}" height="{bh}"',
     '<rect x="{INSET}" y="{INSET}" width="{bw - 2 * INSET}" height="{bh - 2 * INSET}"'),
    # ✗ 曾经有 ② `%` 版（`x="0" y="0" width="%d" height="%d"`）—— **已删除** ✗：
    #   实测 LD1117 踩雷 ✗：几何改成 4 个 `%d` 了，可它的参数表写法不是 `% (bw, bh)` ✗
    #   ⇒ 生成器当场 `TypeError: not enough arguments for format string` ✗（件直接崩 ✗）。
    #   ⇒ 这类件**人工改** ✓（少而稳 ✓：USB-B01 已手工做完 ✓）。
]
MODULE_INSET = ("\n# ★★ 板边相位＝**半格**（AGENTS §3b：转接板不许影响板外孔的插拔 ✓，2026-09-27 ✓）：\n"
                "#   板框四周各让 50（内部单位 = 半格 = 1.27mm）⇒ 板边落在两排孔正中 ✓；\n"
                "#   针脚坐标一个不动 ✓ ⇒ 已有 sketch 不用改 ✓。\n"
                "#   （本行由 tools/bb_inset.py 写入 ✓；改完必跑 audit_green_board.py +\n"
                "#     check_inside_board.py ✓）\n"
                "INSET = 50\n")


def main(argv):
    d = argv[0]
    dry = "--dry" in argv
    f = os.path.join(d, "gen_part.py")
    if not os.path.isfile(f):
        print("✗ 没有 %s" % f)
        return 1
    txt = open(f, encoding="utf-8").read()
    if "INSET = 50" in txt:
        print("· %s 已经有 INSET ✓，跳过" % os.path.basename(d))
        return 0
    hits = []
    for old, new in KNOWN:
        if old in txt:
            hits.append((old, new))
    if not hits:
        print("✗ %s：认不出板框写法 ✗（一个字没动 ✓）—— 需要人工看" % os.path.basename(d))
        print("   线索：文件里有没有 '00aa44' / 'BB_GREEN' 的 rect 行？")
        return 2
    if len(hits) > 1:
        print("✗ %s：同时匹配到多种写法 ✗（一个字没动 ✓）" % os.path.basename(d))
        return 3
    old, new = hits[0]
    txt2 = txt.replace(old, new, 1)
    # % 版的参数表也要跟着改（`% (bw, bh)` ⇒ 四个值 ✓）
    if "%d" in new and "% (bw, bh)" in txt2:
        txt2 = txt2.replace("% (bw, bh)", "% (INSET, INSET, bw - 2 * INSET, bh - 2 * INSET)", 1)
    # 模块级定义：插在**模块 docstring 之后** ✓
    #   ★ 教训：第一版插在"第一个空行"之后 ✗ —— 那多半是 docstring **里面**的空行 ✗
    #     ⇒ 定义会被塞进字符串里 ⇒ 运行到板框那行直接 NameError ✗（生成器不报错才怪 ✗）。
    import ast
    tree = ast.parse(txt2)
    ins = 0
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(getattr(tree.body[0], "value", None), ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        ins = tree.body[0].end_lineno                 # 1-based ✓
    lines = txt2.splitlines(True)
    lines.insert(ins, MODULE_INSET)
    txt2 = "".join(lines)
    n = len(txt2.splitlines()) - len(txt.splitlines())
    print("✓ %s：板框改 %s ⇒ %s（+%d 行）%s"
          % (os.path.basename(d), old[:34], new[:40], n, "【dry-run，未写】" if dry else ""))
    if not dry:
        open(f, "w", encoding="utf-8", newline="\n").write(txt2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
