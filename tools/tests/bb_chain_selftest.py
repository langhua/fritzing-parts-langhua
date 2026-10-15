# -*- coding: utf-8 -*-
r"""`bb_compare.Link.pts`（**折线点列**）的**单元自测** ✓ —— ✗ 不用任何 `.fzz` / `.fzp` / `.svg` ✗
（全用合成数据 ✓，只用标准库 ✓）

★ 为什么单列一个测试 ✗：`pts` 的**头尾两端**是下游认"这条跳线接到哪儿"的唯一入口 ✓ ——
  项目 `bb_probe` 的 ④「悬空端」/ ①「逐脚连通」都读 `lk.pts[0]` / `lk.pts[-1]` ✓。
  2026-10-15 用户手改版 `v88_routed_byHand.fzz` 抓出旧实现的一个真 bug ✗：旧代码是
  「**拿第一段的 `q` 顺着往后接**」✗ ⇒ 只要**中段那条 Wire 恰好排在两段端线之后** ✗，
  `pts[-1]` 就落成一个**中间的接头** ✗ ⇒ 一条 `pin11A → pin35F` 的完整跳线被报成
  「一头悬空」✗ ＋ 那张网被报成「裂成两块」✗（两处都是**假警报** ✗）。
  ⇒ 本测试把「**与 `segs` 存放次序无关**」这条钉死 ✓（正例反例都有 ✓）。

★ 覆盖 ✓：
  ① 单段 ⇒ 2 点 ✓；空 ⇒ `[]` ✓；
  ② 两段 ⇒ 3 点 ✓（接头算 1 个点 ✓，不是 2 个 ✗）；
  ③ ★★ **三段链：中段排在最后** ⇒ 仍 4 点 ✓、头尾 = **两个真端头** ✓（**这就是那个 bug** ✗）；
  ④ **次序无关** ✓：6 种排列 ⇒ `pts` **完全相同** ✓；
  ⑤ **接头有小噪声**（Fritzing 写出来的 `116.949` / `116.95` ✓）⇒ 仍算一个接头 ✓；
  ⑥ **起点确定** ✓：同一条链换个方向写 ⇒ `pts` 逐点相同 ✓（起点取**坐标最小**那个头 ✓，
     `link_moved()` 逐点比位移要靠这条 ✓）；
  ⑦ **不许无中生有** ✗：两段不相接 ⇒ 只能画出一段（2 点 ✓），✗ 不许把它们连起来 ✗；
  ⑧ **实测数据回归** ✓：`Wire90015721 + Wire90016005 + Wire90015722` = `pin11A → pin35F`
     （坐标都是用户手改版里的真值 ✓）⇒ 头尾必须是这两个孔 ✓。

用法：`py -X utf8 tools\tests\bb_chain_selftest.py` ⇒ 全过打印 `✓ 全过` ＋ exit 0 ✓
★ 位置（仓规 ✓）：**测试一律放 `tools/tests/`** ✓；命名保留 `*_selftest.py` ✓
（✗ 故意不叫 `test_*.py` ✗）；一行跑全部见 `tests\run_all.py` ✓。
★ 路径按 `__file__` 相对定位 ✓（✗ 不写死机器路径 ✗）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/ ✓
import bb_compare as BC                                         # noqa: E402

FAIL = []


def chk(name, cond):
    print("  %s %s" % ("✓" if cond else "✗", name))
    if not cond:
        FAIL.append(name)


def link(segs, wid="Wire1"):
    lk = BC.Link(wid)
    lk.segs = list(segs)
    return lk


def main():
    print("== bb_compare.Link.pts 单元自测 ==")

    # ── ① 单段 / 空 ✓
    one = link([((0.0, 0.0), (9.0, 0.0))])
    chk("① 单段 ⇒ 2 点", len(one.pts) == 2)
    chk("① 空 ⇒ []", BC.Link("W0").pts == [])

    # ── ② 两段 ⇒ 3 点（接头一个点 ✓）
    two = link([((0.0, 0.0), (9.0, 0.0)), ((9.0, 0.0), (9.0, 18.0))])
    chk("② 两段 ⇒ 3 点（接头算 1 个 ✓）", len(two.pts) == 3)

    # ── ③ ★★ 三段链：中段排在最后 ⇒ 头尾必须是两个真端头 ✓（旧实现就在这里错 ✗）
    a, m1, m2, b = (0.0, 0.0), (3.0, 0.0), (30.0, 0.0), (30.0, 9.0)
    s_am, s_ab, s_mb = (a, m1), (m1, m2), (m2, b)
    scram = link([s_am, s_mb, s_ab])            # 中段在最后 ✗（就是那个 bug 的形状 ✗）
    chk("③ 中段排最后 ⇒ 仍 4 点", len(scram.pts) == 4)
    chk("③ 4 个点齐（两端 ＋ 两接头 ✓）", set(scram.pts) == {a, m1, m2, b})
    chk("③ 头尾 = 两个真端头（✗ 不是接头 m1/m2 ✗）", {scram.pts[0], scram.pts[-1]} == {a, b})

    # ── ④ 次序无关 ✓（3 段的 6 种排列 ⇒ pts 完全相同 ✓）
    import itertools
    seen = {tuple(link(p).pts) for p in itertools.permutations([s_am, s_mb, s_ab])}
    chk("④ 6 种排列 ⇒ pts 只有 1 种（顺序无关 ✓）", len(seen) == 1)

    # ── ⑤ 接头有小噪声 ✓（Fritzing 实测写法 ✓）
    noisy = link([((99.001, 144.0), (99.136, 180.071)),
                  ((314.834, 180.071), (315.001, 81.0)),
                  ((99.136, 180.070999), (314.834, 180.070999))])
    chk("⑤ 接头差 1e-3 ⇒ 仍算 1 个接头（4 点 ✓）", len(noisy.pts) == 4)

    # ── ⑥ 起点确定 ✓（同一条链反向写 ⇒ 逐点相同 ✓）
    fwd = link([((0.0, 0.0), (9.0, 0.0)), ((9.0, 0.0), (9.0, 18.0))])
    rev = link([((9.0, 18.0), (9.0, 0.0)), ((9.0, 0.0), (0.0, 0.0))])
    chk("⑥ 反向写 ⇒ pts 逐点相同 ✓", fwd.pts == rev.pts)

    # ── ⑦ 不许无中生有 ✗（两段不相接 ⇒ 只画得出第一段 ✓）
    apart = link([((0.0, 0.0), (9.0, 0.0)), ((50.0, 0.0), (59.0, 0.0))])
    chk("⑦ 两段不相接 ⇒ 只画 1 段（2 点 ✓，✗ 不硬连 ✗）", len(apart.pts) == 2)

    # ── ⑧ 实测数据回归 ✓（用户手改版 `v88_routed_byHand.fzz` 的真值 ✓）
    real = link([((99.001, 144.000), (99.136, 180.071)),
                 ((99.136, 180.071), (314.834, 180.071)),
                 ((314.834, 180.071), (315.001, 81.000))])
    chk("⑧ 实测灰线 ⇒ 4 点", len(real.pts) == 4)
    h1 = BC.hole_xy("pin11A")
    h2 = BC.hole_xy("pin35F")
    e1 = next(p for p in (real.pts[0], real.pts[-1]) if BC.same_pt(p, h1, 0.01))
    e2 = next(p for p in (real.pts[0], real.pts[-1]) if BC.same_pt(p, h2, 0.01))
    chk("⑧ 头尾落在 `pin11A`/`pin35F` 的孔心上 ✓", bool(e1) and bool(e2))

    print("⇒ %s" % ("✓ 全过" if not FAIL else "✗ **不过 %d 项**：%s" % (len(FAIL), FAIL)))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
