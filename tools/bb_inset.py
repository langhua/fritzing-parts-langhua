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

# 认得的板框写法：`start` 是要匹配的开头 ✓，`bx0/by0` = 板框左上角的表达式（用来算新几何 ✓）
PATTERNS = [
    # ① 板框 = 整张画布（SS34 / DSIC01LS-P / CN3165 / Crystal-3xxx 那类）
    {"start": '<rect x="0" y="0" width="{bw}" height="{bh}"', "bx0": "0", "by0": "0"},
    # ② 板框本来就从画布内缩（AT24C02 / CH340E/N / W25Q16JV / H1102NLT / RT6150AGQW_rev_1 …）
    {"start": '<rect x="{bx0}" y="{by0}" width="{bw}" height="{bh}"',
     "bx0": "bx0", "by0": "by0"},
]


def build(start, bx0, by0, edges):
    """按"要动哪几条边"拼出新的 rect 开头 ✓（edges ∈ {l,r,t,b} 的子集 ✓）。
    ★ 为什么要按边 ✓：`Crystal-3215` / `IP101GR` 的**左右边已经是半格** ✓ ——
      再让一次就变成 0.00 ✗（当场把好的边弄坏 ✗）；所以只能动必要的边 ✓。
    """
    def one(base, size, near, far):
        """base/size = 原 x,width（或 y,height）✓；near = 起点要不要让 ✓；far = 终点要不要让 ✓"""
        if near and far:
            b = "INSET" if base == "0" else "%s + INSET" % base
            return b, "%s - 2 * INSET" % size
        if near:
            b = "INSET" if base == "0" else "%s + INSET" % base
            return b, "%s - INSET" % size
        if far:
            return base, "%s - INSET" % size
        return base, size
    nx, nw = one(bx0, "bw", "l" in edges, "r" in edges)
    ny, nh = one(by0, "bh", "t" in edges, "b" in edges)
    return ('<rect x="%s" y="%s" width="%s" height="%s"'
            % (("{%s}" % nx) if nx != "0" else "0",
               ("{%s}" % ny) if ny != "0" else "0",
               "{%s}" % nw, "{%s}" % nh))
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
    edges = "lrtb"                                     # 默认四条边都让（= 半格）✓
    for a in argv:
        if a.startswith("--edges="):
            edges = a.split("=", 1)[1]                 # 如 --edges=tb（只让上下）✓
    hits = [p for p in PATTERNS if p["start"] in txt]
    if not hits:
        print("✗ %s：认不出板框写法 ✗（一个字没动 ✓）—— 需要人工看" % os.path.basename(d))
        return 2
    p = hits[0]
    new = build(p["start"], p["bx0"], p["by0"], edges)
    old = p["start"]
    txt2 = txt.replace(old, new, 1)
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
