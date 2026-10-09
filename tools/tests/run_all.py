# -*- coding: utf-8 -*-
r"""库仓**一行跑全部**测试 ✓（2026-10-09 用户定 ✓）

★ 约定（仓规 ✓）：
  · **测试一律放 `tools/tests/`** ✓（本项目仓的对应处 = `hardware/pixel/tests/` ✓）；
  · 每个测试脚本**自带 `exit 0/1`** ✓、**零第三方依赖** ✓（只用标准库 ✓）；
  · 命名保留 `*_selftest.py` ✓ —— ✗ 故意不叫 `test_*.py` ✗（pytest 会收集它、
    被模块级 `SystemExit` 打崩 ✓）。

用法：`py -X utf8 tests\run_all.py` ⇒ 全过 print `✓ 全过` ＋ exit 0 ✓；任一不过 exit 1 ✓。
      `py -X utf8 tools\tests\run_all.py`（从库仓根跑也认 ✓ —— 路径按 `__file__` 定位 ✓）。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    tests = sorted(f for f in os.listdir(HERE)
                   if f.endswith("_selftest.py") and f != os.path.basename(__file__))
    if not tests:
        print("✗ `%s` 里没有 `*_selftest.py` ✓" % HERE)
        return 1
    bad = []
    for t in tests:
        print("══ %s ══" % t)
        r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, t)],
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        print("   [exit %d]\n" % r.returncode)
        if r.returncode != 0:
            bad.append(t)
    print("⇒ %s（%d 个测试脚本 ✓）"
          % ("✓ 全过" if not bad else "✗ **不过 %d 个**：%s" % (len(bad), "、".join(bad)),
             len(tests)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
