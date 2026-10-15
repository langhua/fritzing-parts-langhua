# -*- coding: utf-8 -*-
r"""★ `bb_route4` 的**前置守卫**（规则正文：`docs/breadboard-routing-rules.md` §A.4 ✓）

用户 2026-10-15 定 ✓：「**入网的前提是摆位到位，而不是随意都可以入网**」✓
⇒ 本脚本就是那条规则的**唯一执行口** ✓：

    ① 先跑 `bb_precheck.py <in>` ✓（摆位到位？脚落孔？一孔一脚？）
    ② **不过 ⇒ 立刻退出、不写文件** ✗（✗ 不许"随便给个孔就接上" ✗）
    ③ 过了 ⇒ 原样转给 `bb_route4.py` ✓（参数一字不改地透传 ✓）

用法 ✓（＝把 `bb_route4` 换成它 ✓，其余参数一模一样 ✓）：

    py -X utf8 tools\bb_route_guarded.py <in.fzz> <out.fzz> --nets=… --keep-deco --near-hole --straight

★ 为什么单独一个"守卫"✗✓：`bb_route4.py` 是**跨项目通用**工具 ✓ ⇒ ✗ 不把"某块板的规矩"
硬塞进它 ✗（同 `pixel_nets.py` 的理由 ✓）；守卫只做"跑一把同一份尺子、不通过就拦" ✓。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRECHECK = os.path.join(HERE, "bb_precheck.py")
ROUTE = os.path.join(HERE, "bb_route4.py")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    src, dst = argv[0], argv[1]
    print("== 前置闸门（§A.4 摆位先于入网）==")
    r = subprocess.run([sys.executable, "-X", "utf8", PRECHECK, src])
    if r.returncode != 0:
        print("\n✗ **摆位没到位 ⇒ 拒绝布线** ✗（✗ 不写 `%s` ✗）" % dst)
        print("   先把脚落到面包板孔上／把重叠的挪开 ✓（规则 §A.4 ✓）")
        return 1
    print("\n== 闸门通过 ⇒ 交给 bb_route4 ==")
    return subprocess.run([sys.executable, "-X", "utf8", ROUTE] + list(argv)).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
