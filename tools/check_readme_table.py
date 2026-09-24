#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对 README「已有部件」表 与 `fzpz/` 是否对得上（AGENTS §11 第 5/6 步的机器守）。

用法：py -3.13 tools/check_readme_table.py

查三件事：
  ① **漏登**：`fzpz/*.fzpz` 里有的文件，README 表里一个字都没提到
     （支持通配行，如 `fzpz/PB86-A0-*.fzpz`、`fzpz/SHC*.fzpz`；也支持一行写多件）
     —— 若某个名字在 README 里出现过、只是没带 `.fzpz` 后缀，**只提示、不算错**（避免误报）
  ② **写错**：README 表里写了、但 `fzpz/` 里没有的文件
  ③ **数量**：README 声明的「共 N 个元件」（= 预览拼版 `make_preview.py` 的 `SHEETS` 条目数）
     与「N 个 `.fzpz`」是否与实测一致

有问题就打印出来并以退出码 1 结束（可以直接挂到提交前的检查里）。
"""
import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
FZPZ = ROOT / "fzpz"
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))


def _stem_mentioned(text, name):
    """README 里是否提到过这个名字（不带 .fzpz 后缀，也会被当"登记过"）。"""
    stem = name[: -len(".fzpz")]
    return re.search(r"(?<![\w.-])" + re.escape(stem) + r"(?![\w.-])", text) is not None


def main():
    text = README.read_text(encoding="utf-8")
    actual = {p.name for p in FZPZ.glob("*.fzpz")}
    tokens = set(re.findall(r"([\w.*+-]+\.fzpz)", text))

    covered = set()
    for t in tokens:
        if "*" in t:
            covered |= {n for n in actual if fnmatch.fnmatch(n, t)}
        elif t in actual:
            covered.add(t)

    missing, hinted = [], []                              # ① 漏登（真漏 / 只写了名字）
    for n in sorted(actual - covered):
        (hinted if _stem_mentioned(text, n) else missing).append(n)
    wrong = sorted(t for t in tokens if "*" not in t and t not in actual)   # ② 写错

    problems = []
    print(f"fzpz/ 实有 {len(actual)} 个；README 里出现 {len(tokens)} 个文件名（含通配）")
    if missing:
        problems.append(f"README 表里漏登 {len(missing)} 个")
        print(f"① 漏登（{len(missing)} 个）—— 补进「已有部件」表（AGENTS §11 第 3 步）：")
        for m in missing:
            print(f"     {m}")
    else:
        print("① 漏登：无 ✓")
    if hinted:
        print(f"   （另 {len(hinted)} 个只写了名字、没写 .fzpz 后缀，视为已登记，仅供核对）：")
        for h in hinted:
            print(f"     {h}")
    if wrong:
        problems.append(f"README 写了 {len(wrong)} 个不存在的 .fzpz")
        print(f"② 表里写了但不存在的文件（{len(wrong)} 个）：")
        for w in wrong:
            print(f"     {w}")
    else:
        print("② 表里写的文件都存在 ✓")

    # ③ 数量
    try:
        import make_preview                                # noqa: PLC0415
        sheets = sum(len(v[2]) for v in make_preview.SHEETS.values())
    except Exception as e:                                 # pragma: no cover
        sheets = None
        print(f"③ 跳过预览条目数核对（导入 make_preview 失败：{e}）")
    m1 = re.search(r"共 (\d+) 个元件", text)
    m2 = re.search(r"（(\d+) 个 `\.fzpz`）", text)
    for label, m, real in (("共 N 个元件（预览拼版）", m1, sheets),
                           ("N 个 `.fzpz`", m2, len(actual))):
        if not m or real is None:
            continue
        if int(m.group(1)) != real:
            problems.append(f"{label}：README 写 {m.group(1)}，实测 {real}")
            print(f"③ {label}：README 写 {m.group(1)}，实测 {real} ✗")
        else:
            print(f"③ {label} = {real} ✓")

    if problems:
        print(f"\n=== 不合格：{'；'.join(problems)} ===")
        return 1
    print("\n=== 全部通过 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
