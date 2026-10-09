# -*- coding: utf-8 -*-
r"""_ut_gap：第四十六轮（`--wire-gap` 线距闸门 ✓）的**单元自测** ✓ —— **不用任何 `.fzz`** ✓

★ 与 `_ut_tie.py` / 库仓 `sch_body_selftest.py` **同一手法** ✓：把**判据**逐条钉死 ✓，
  正例反例都有 ✓ ⇒ 以后改 `sch_geom` 只要跑它就知道有没有把规则改坏 ✓。
★ 覆盖 ✓（每条都对应 README §六十三 里的一句口径 ✓）：
  ① `merge_conductors`：一串共线相接的段 ⇒ **并成一条** ✓（一条轨自己那几节**不算净距** ✗）；
  ② 并入后导体 + 它的 **T 形支线**（同网 ✓）⇒ **0 条不足** ✓（接头放行 ✓）；
  ③ **不同网**平行贴 1.0 单位 ⇒ **1 条不足** ✓（就是用户看到的那两处 ✓）；
  ④ **同网**平行贴 1.0 单位、但**不是接头**（两座岛 ✓）⇒ 仍 **1 条不足** ✓（同网 ≠ 免检 ✓）；
  ⑤ 同网**端点搭在对方段上**（T ✓）⇒ 放行 ✓；同网**端点对接**（搭接 ✓）⇒ 放行 ✓；
  ⑥ ★ **共线 ＋ 同侧**（= 压在一起 ✗）⇒ `joined` **必须 False** ✓（不许当成接头放行 ✗）；
  ⑦ **横穿**（真交叉 ✓）⇒ 不计净距 ✓、横穿数 +1 ✓；
  ⑧ `seg_seg_dist`：垂直相交 ⇒ 0 ✓；端点对端点 ⇒ 欧氏距 ✓。
用法：py -X utf8 tools\tests\sch_geom_gap_selftest.py   ⇒ 全过打印 `✓ 全过` ＋ exit 0 ✓
★ 位置（2026-10-09 用户定 ✓）：**测试一律放 `tools/tests/`** ✓（与 `sch_body_selftest.py`
  / `pcb_curve_selftest.py` 同一处 ✓）；**命名保留 `*_selftest.py`** ✓ —— ✗ 故意不叫 `test_*.py` ✗
  （pytest 会收集它、被模块级 `SystemExit` 打崩 ✓）；一行跑全部见 `tests\run_all.py` ✓。
  ★ 路径**不再写死机器路径** ✗ ⇒ 按 `__file__` 相对定位 ✓（本文件在 `tools/tests/` ✓ ⇒ 上一级 = `tools/` ✓）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/ ✓
import sch_geom as SG                                           # noqa: E402

MM = 25.4 / 90.0
GAP = 1.0 / MM          # = 3.5433 单位 ✓（缺省档 ✓）
FAIL = []


def chk(name, cond):
    print("  %s %s" % ("✓" if cond else "✗", name))
    if not cond:
        FAIL.append(name)


def _n(bad):
    return len(bad)


def main():
    # ① 一串共线相接的段 ⇒ 并成一条 ✓（实测场景：5V 轨 365＋366＋367 ✓）
    rail = [((22.828, -57.6), (180.0, -57.6), "5V"),
            ((180.0, -57.6), (180.378, -57.6), "5V"),
            ((180.378, -57.6), (244.578, -57.6), "5V")]
    m = SG.merge_conductors(rail)
    chk("① 共线相接的三节并成 1 条（并入后 %d 条）" % len(m), len(m) == 1)
    chk("① 并出来的两端 = 整条的两端", m and m[0][0] == (22.828, -57.6)
        and m[0][1] == (244.578, -57.6))

    # ② 并入后导体 ＋ 同网 T 形支线 ⇒ 0 条不足 ✓（支线端点正好落在合并后那条上 ✓）
    tb = rail + [((180.378, -11.0), (180.378, -57.6), "5V")]
    md, _mp, bad, ncr, _mm = SG.conductor_clearance(tb, gap=GAP)
    chk("② 同网 T 形支线 ⇒ 0 条不足（实测 %d ✓ ｜ 横穿 %d ✓）" % (_n(bad), ncr),
        _n(bad) == 0 and ncr == 0)

    # ③ 不同网平行贴 1.0 单位 ⇒ 1 条不足 ✓（= 用户点名的那处 ✓）
    two = [((244.578, 18.0), (209.2, 18.0), "DATA_OUT"),
           ((188.552, 17.0), (227.378, 17.0), "GND")]
    md, _mp, bad, ncr, _mm = SG.conductor_clearance(two, gap=GAP)
    chk("③ 不同网平行贴 1.0 单位 ⇒ 1 条不足（实测 %d ｜ d=%.4f）" % (_n(bad), md or -1),
        _n(bad) == 1 and abs((md or 0) - 1.0) < 1e-9)

    # ④ 同网平行贴 1.0 单位、但不是接头 ⇒ 仍 1 条不足 ✓（同网**不**免检 ✓）
    two2 = [((244.578, 18.0), (209.2, 18.0), "GND"),
            ((188.552, 17.0), (227.378, 17.0), "GND")]
    _md, _mp, bad, _ncr, _mm = SG.conductor_clearance(two2, gap=GAP)
    chk("④ 同网平行贴 1.0 单位（不是接头）⇒ 1 条不足（实测 %d）" % _n(bad), _n(bad) == 1)

    # ⑤ 同网**端点搭在对方段上**（T ✓）/ **端点对接**（搭接 ✓）⇒ 放行 ✓
    tie_t = [((22.828, 18.0), (22.828, -57.6), "5V"),
             ((22.828, -57.6), (180.0, -57.6), "5V")]
    _md2, _mp2, bad2, _nc2, _mm2 = SG.conductor_clearance(tie_t, gap=GAP)
    chk("⑤a 同网端点对接（搭接/接管）⇒ 0 条不足（实测 %d）" % _n(bad2), _n(bad2) == 0)
    tie_T = [((22.828, -57.6), (180.0, -57.6), "5V"),
             ((120.0, 10.0), (120.0, -57.6), "5V")]
    _md3, _mp3, bad3, _nc3, _mm3 = SG.conductor_clearance(tie_T, gap=GAP)
    chk("⑤b 同网 T 形搭在**中段**（电源轨支线）⇒ 0 条不足（实测 %d）" % _n(bad3),
        _n(bad3) == 0)
    chk("⑤c joined()：T 形真值", SG.joined((120.0, 10.0), (120.0, -57.6),
                                        (22.828, -57.6), (180.0, -57.6)) is True)

    # ⑥ 共线 ＋ 同侧（压在一起 ✗）⇒ joined 必须 False ✓
    chk("⑥ joined()：共线同侧重叠 ⇒ **必须 False**（不许当接头放行 ✗）",
        SG.joined((201.378, 9.0), (244.578, 9.0), (244.578, 9.0), (235.378, 9.0)) is False)
    chk("⑥ joined()：共线反向延展（连续段 ✓）⇒ True",
        SG.joined((15.378, 9.0), (27.378, 9.0), (27.378, 9.0), (58.578, 9.0)) is True)

    # ⑦ 横穿 ⇒ 不计净距 ✓、横穿数 +1 ✓
    cr = [((0.0, 0.0), (100.0, 0.0), "A"), ((50.0, -50.0), (50.0, 50.0), "B")]
    md7, _mp7, bad7, ncr7, _mm7 = SG.conductor_clearance(cr, gap=GAP)
    chk("⑦ 横穿 ⇒ 0 条不足 ｜ 横穿 1 对（实测 %d ／ %d）" % (_n(bad7), ncr7),
        _n(bad7) == 0 and ncr7 == 1)

    # ⑧ seg_seg_dist ✓
    chk("⑧a 垂直相交 ⇒ 0", SG.seg_seg_dist((0.0, 0.0), (10.0, 0.0),
                                        (5.0, -5.0), (5.0, 5.0)) == 0.0)
    chk("⑧b 端点对端点 ⇒ 欧氏距", abs(SG.seg_seg_dist((0.0, 0.0), (3.0, 0.0),
                                                   (3.0, 4.0), (6.0, 4.0)) - 4.0) < 1e-9)
    chk("⑧c 平行错开 ⇒ 垂距", abs(SG.seg_seg_dist((0.0, 0.0), (10.0, 0.0),
                                               (2.0, 1.5), (8.0, 1.5)) - 1.5) < 1e-9)

    print()
    if FAIL:
        print("✗ **不通过 %d 条** ✗：%s" % (len(FAIL), "；".join(FAIL)))
        return 1
    print("✓ **全过** ✓（第四十六轮线距判据：合并 ✓ / 接头放行 ✓ / 横穿不计 ✓ / 重叠不放行 ✓）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
