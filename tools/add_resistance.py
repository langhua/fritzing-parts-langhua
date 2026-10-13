#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""给 `svg/Resistor-*` 的 11 档电阻补上 **阻值数据项** `resistance` ✓（2026-10-13 用户定 ✓）

用户原话 ✓：「修改电阻模型，**增加电阻值数据项，用于填写阻值**」✓
（同一天报的病根 ✗：「电阻电容更是**没有阻值容量值**，**无法与网表进行校对**」✓）

-----------------------------------------------------------------------------
★ 为什么叫 `resistance` 而且**必须小写** ✗（出处 = Fritzing 源码 ✓，本机可复查 ✓）
  · `items/resistor.cpp:100` 读 = `modelPart->properties().value("resistance", "220")` ✓
    —— QHash 查找是**精确匹配 ⇒ 大小写敏感** ✗ ⇒ 部件写 `Resistance`（大写 ✗）时
    它**取不到值** ✗ ⇒ 用户改完阻值，Fritzing 内部**还当默认 220** ✗（"静默失效" ✗，最难查 ✓）。
    ★ 核心库 `core/resistor_5band.fzp` / `SMD_resistor_0402.fzp` 就是大写 ✗ ——
      那是**它自己的** bug ✗，**别照抄** ✗（它的 `spice` 行还在用小写 `{resistance}` ✓ ⇒ 自相矛盾 ✗）。
  · `:161` 写 = `setLocalProp("resistance", …)` ✓ 也是小写 ✓；
    `:250` 比较才用 `Qt::CaseInsensitive` ✓（说明它知道历史上有大写 ✗）。
  · `items/itembase.cpp:226` 的 `TranslatedPropertyNames` 只登记小写 ✓。
  ⇒ 本库一律小写 ✓（与电容件的 `capacitance` 同口径 ✓，本仓已有先例 ✓）。
  ⇒ 也解释了 **用户草图里 Fritzing 自己写的实例属性就是小写** `resistance` ✓（实测 ✓）。

★ 默认值 = `4.7k` ✓ —— 与电容件**同一口径**：默认取**本项目实际用值** ✓
  （`svg/Capacitor-0402/gen_part.py` 的 `capacitance = 100nF` ✓，用户 2026-10-01 确认 ✓）；
  本板 `R1`/`R2` 是 I²C 上拉 `4.7k` ✓。**要换 = 改下面 DEFAULT 一行 + 重跑** ✓。
  ★ 写法照**用户草图**（`4.7k` ✓），✗ 不用 RKM 的 `4k7` ✗（A10 只要求"别混写" ✓）。

★ 插在哪 ✓：紧跟 `package` 之后、`power` 之前 ✓ —— 与 Fritzing 自己**运行时重排**的顺序一致 ✓
  （`items/resistor.cpp:420`：`if (keys.removeOne("resistance")) keys.insert(1, "resistance")` ✓
   —— 它把 `resistance` 放到 `family` 之后第 2 位 ✓）。

★ 只改 `svg/` 下的 fzp ✓ —— **打包另走 `tools/repack_fzpz.py`** ✓（AGENTS §4 第 2 步 ✓：
  归一化 LF + 固定时间戳，跨平台可重复 ✓；✗ 本工具不自己写 zip ✗，免得出现第二份打包实现 ✗）。

用法::

    py -3.13 tools\add_resistance.py            # 改 fzp ✓（改完接着跑 repack_fzpz.py ✓）
    py -3.13 tools\add_resistance.py --check    # 只报现状 ✓（不写文件 ✓）
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "svg"
DEFAULT = "4.7k"                       # ★ 唯一的默认值定义处 ✓（要改就改这一行 ✓）
NEW_LINE = '  <property name="resistance" showInLabel="yes">%s</property>\n' % DEFAULT
ANCHOR = '  <property name="power" showInLabel="yes">'


def main(argv=None):
    ap = argparse.ArgumentParser(description="给电阻件补 resistance 数据项")
    ap.add_argument("--check", action="store_true", help="只报现状，不写文件")
    args = ap.parse_args(argv)

    dirs = sorted(p for p in SVG.iterdir()
                  if p.is_dir() and p.name.startswith("Resistor-"))
    print("== 电阻件补阻值数据项（%d 档）%s ==" % (len(dirs), "（只查 ✓）" if args.check else ""))
    n_done = n_new = 0
    bad = []
    for d in dirs:
        fzps = sorted(d.glob("part.*.fzp"))
        if len(fzps) != 1:
            bad.append("%s: 找到 %d 个 fzp ✗（应为 1 个）" % (d.name, len(fzps)))
            continue
        p = fzps[0]
        txt = p.read_text(encoding="utf-8")
        if 'name="resistance"' in txt:
            n_done += 1
            # ★ 已有就**报出当前值** ✓（并与 DEFAULT 比一下 ✓）—— ✗ 原来只印"已就位" ✗ ⇒
            #   将来改 DEFAULT 重跑时**看不出来**哪几档的值跟默认不一致 ✗（静默 ✗）。
            cur = re.search(r'name="resistance"[^>]*>([^<]*)<', txt)
            cur = cur.group(1) if cur else "?"
            flag = "✓" if cur == DEFAULT else "⚠ 与 DEFAULT(%s) 不同 ✗ —— 要统一请手工改或删掉该行再重跑" % DEFAULT
            print("   %-16s 已有 resistance=%s %s" % (d.name, cur, flag))
            continue
        if ANCHOR not in txt:
            bad.append("%s: 找不到锚点行 `<property name=\"power\" …>` ✗" % d.name)
            continue
        new = txt.replace(ANCHOR, NEW_LINE + ANCHOR, 1)
        n_new += 1
        if not args.check:
            p.write_text(new, encoding="utf-8", newline="")
        print("   %-16s 补上 %s ✓" % (d.name, DEFAULT))

    print("⇒ 新增 %d 档 ✓｜原本已有 %d 档 ✓" % (n_new, n_done))
    if args.check and n_new:
        print("   （--check：没有写文件 ✓；去掉 --check 才会写 ✓）")
    if not args.check and n_new:
        print("★ 接着跑：py -3.13 tools\\repack_fzpz.py   # 重打 .fzpz ✓")
    for b in bad:
        print("   ✗ " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
