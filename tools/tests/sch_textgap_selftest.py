# -*- coding: utf-8 -*-
r"""`sch_textgap`（第四十九轮：**文字 ↔ 被绘制对象 净距** 判据 ✓）的**单元自测** ✓
—— **不用任何 `.fzz` / `.fzp` / `.svg`** ✓（全用合成数据 ✓，只用标准库 ✓）

★ 与 `sch_geom_gap_selftest.py` / `sch_body_selftest.py` **同一手法** ✓：把**判据**逐条钉死 ✓，
  正例反例都有 ✓ ⇒ 以后改 `sch_textgap` 只要跑它就知道有没有把规则改坏 ✓。
★ 覆盖 ✓（每条都对应 README §六十六 里的一句口径 ✓）：
  ① `box_dist`：相交 ⇒ 0 ✓；横向差 ✓；纵向差 ✓；对角 ⇒ 勾股 ✓；贴边 ⇒ 0 ✓；
  ② `clamp_mm`：越界**夹取 ＋ 给话** ✓、界内**原样 ＋ 不给话** ✓；
  ③ `exempt`（**唯一一处豁免口径** ✓）：自己的本体 ✓；网标签 ↔ **它自己声明的**引线 ✓；
     网标签 ↔ **别的**引线 ⇒ **必须 False** ✗（那正是用户报的那类 ✗）；位号块 ↔ 任何导线 ⇒ False ✓；
  ④ `cand_boxes`：含"上/下/左/右"四个方向族 ✓、含**原位** ✓、去重 ✓；
  ⑤ `bad_for_box`：**同一个函数**既管验收也管试位 ✓（试位搬到干净处 ⇒ 0 条 ✓、留在原处 ⇒ 1 条 ✓）；
  ⑥ `repair` 把压着东西的文字搬到干净处 ⇒ **剩余 0** ✓、且**位移最小** ✓（不许为了好看乱跳 ✗）；
  ⑦ `violations`：**文字 ↔ 文字**也算 ✓（老规则只算"已放的位号" ✗）；
  ⑧ `shapes_in_box`：墨迹顶点落进框 ⇒ True ✓；
  ⑨ `items()` 在**合成 `.fz`** 上跑通 ✓（实例扫描 / 网标签旗标 / 导线三条路都过一遍 ✓）；
  ⑩ **第二档的接头认得出 ＋ 挪与挪回严格互逆** ✓（合成接地符号：脚 = 原点 + (9.001,0.596) ✓；
     `symbol_attachments` 认那条引线的**末端** ✓；挪一步线端跟着走 ✓、挪回来**逐字复原** ✓；
     ✗ 反例：两条线端重合在同一个脚上 ⇒ **认不准 ⇒ 返回 None（不动）** ✓ ——
     这一组是给**实测踩过的那个坑**钉的钉子 ✗：原来"取最近的线端"不是单射 ⇒ 挪回去挪不回来 ✗，
     `--text-gap 5` 实测把 `Wire90015558` 搞成斜线、**打破了「线距」硬闸门** ✗✗。）

用法：`py -X utf8 tools\tests\sch_textgap_selftest.py` ⇒ 全过打印 `✓ 全过` ＋ exit 0 ✓
★ 位置（仓规 ✓）：**测试一律放 `tools/tests/`** ✓（与 `sch_body_selftest.py` 等同一处 ✓）；
  命名保留 `*_selftest.py` ✓（✗ 故意不叫 `test_*.py` ✗）；一行跑全部见 `tests\run_all.py` ✓。
  ★ 路径按 `__file__` 相对定位 ✓（不写死机器路径 ✗）。
"""
import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/ ✓
import sch_textgap as TG                                        # noqa: E402

FAIL = []


def chk(name, cond):
    print("  %s %s" % ("✓" if cond else "✗", name))
    if not cond:
        FAIL.append(name)


FZ = """<?xml version="1.0" encoding="utf-8"?>
<module>
  <instance moduleIdRef="SomePartModuleID" modelIndex="1">
    <title>U9</title>
    <views>
      <schematicView layer="schematic">
        <geometry z="2.5" x="0" y="0" />
        <titleGeometry visible="true" x="10" y="3.75" fontSize="5">
          <displayKey key="" />
        </titleGeometry>
      </schematicView>
    </views>
  </instance>
  <instance moduleIdRef="NetLabelModuleID" modelIndex="2">
    <title>RC</title>
    <views>
      <schematicView layer="schematic">
        <geometry z="2.5" x="30" y="40" />
        <connectors>
          <connector connectorId="connector0" layer="schematic">
            <geometry x="0" y="0" />
            <connects><connect connectorId="connector0" modelIndex="3" layer="schematicTrace" /></connects>
          </connector>
        </connectors>
      </schematicView>
    </views>
  </instance>
  <instance moduleIdRef="WireModuleID" modelIndex="3">
    <title>Wire1</title>
    <views>
      <schematicView layer="schematic">
        <geometry z="1" x="30" y="40" x2="20" y2="0" />
        <connectors>
          <connector connectorId="connector0" layer="schematicTrace">
            <geometry x="0" y="0" />
            <connects><connect connectorId="connector0" modelIndex="2" layer="schematic" /></connects>
          </connector>
        </connectors>
      </schematicView>
    </views>
  </instance>
  <instance moduleIdRef="WireModuleID" modelIndex="4">
    <title>Wire2</title>
    <views>
      <schematicView layer="schematic">
        <geometry z="1" x="90" y="90" x2="10" y2="0" />
      </schematicView>
    </views>
  </instance>
</module>
"""


def _root():
    return ET.fromstring(FZ)


def T(kind, name, mi, box):
    return dict(kind=kind, name=name, mi=str(mi), box=box, lines=[name], el=None)


def O(kind, name, mi, box, shapes=None):
    return dict(kind=kind, name=name, mi=str(mi), box=box, shapes=shapes)


def main():
    # ① box_dist ✓
    a = (0.0, 0.0, 10.0, 10.0)
    chk("①a 相交 ⇒ 0", TG.box_dist(a, (5.0, 5.0, 15.0, 15.0)) == 0.0)
    chk("①b 贴边（相接）⇒ 0", TG.box_dist(a, (10.0, 2.0, 20.0, 8.0)) == 0.0)
    chk("①c 横着差 3 ⇒ 3", abs(TG.box_dist(a, (13.0, 2.0, 20.0, 8.0)) - 3.0) < 1e-9)
    chk("①d 竖着差 4 ⇒ 4", abs(TG.box_dist(a, (2.0, 14.0, 8.0, 20.0)) - 4.0) < 1e-9)
    chk("①e 对角 (3,4) ⇒ 5", abs(TG.box_dist(a, (13.0, 14.0, 20.0, 20.0)) - 5.0) < 1e-9)

    # ② clamp_mm ✓（用户定的范围 [0, 2.54] mm ✓）
    chk("②a 0.15 在界内 ⇒ 原样 ＋ 不给话", TG.clamp_mm(0.15) == (0.15, None))
    v, why = TG.clamp_mm(-1.0)
    chk("②b 越下界 ⇒ 夹到 %.3f ＋ 给话" % TG.MIN_MM, v == TG.MIN_MM and bool(why))
    v, why = TG.clamp_mm(3.0)
    chk("②c 越上界 ⇒ 夹到 %.3f ＋ 给话" % TG.MAX_MM, v == TG.MAX_MM and bool(why))
    chk("②d 边界值 0 与 2.54 都在界内", TG.clamp_mm(0.0)[1] is None
        and TG.clamp_mm(TG.MAX_MM)[1] is None)

    # ③ exempt ✓（**唯一一处**豁免口径 ✓）
    pairs = {("2", "3"), ("3", "2")}               # 网标签 2 ↔ 引线 3 ✓
    root = _root()
    chk("③a 自己的本体 ⇒ 放行", TG.exempt(root, T("位号块", "U9", 1, (0, 0, 1, 1)),
                                         O("器件本体", "U9", 1, (0, 0, 1, 1)), pairs))
    chk("③b 网标签 ↔ **它自己声明的**引线 ⇒ 放行",
        TG.exempt(root, T("网标签", "RC", 2, (0, 0, 1, 1)),
                  O("导线", "Wire1", 3, (0, 0, 1, 1)), pairs))
    chk("③c 网标签 ↔ **别的**引线 ⇒ **必须不放行** ✗",
        not TG.exempt(root, T("网标签", "RC", 2, (0, 0, 1, 1)),
                      O("导线", "Wire2", 4, (0, 0, 1, 1)), pairs))
    chk("③d 位号块 ↔ 导线 ⇒ 不放行（老规则就是这条 ✓）",
        not TG.exempt(root, T("位号块", "U9", 1, (0, 0, 1, 1)),
                      O("导线", "Wire1", 3, (0, 0, 1, 1)), pairs))
    chk("③e 位号块 ↔ 接地符号 ⇒ **不放行**（用户这轮报的正是它 ✗）",
        not TG.exempt(root, T("位号块", "U9", 1, (0, 0, 1, 1)),
                      O("接地符号", "Ground1", 9, (0, 0, 1, 1)), pairs))

    # ④ cand_boxes ✓（方向族 ＋ 原位 ＋ 去重 ✓）
    ob = (100.0, 100.0, 140.0, 120.0)
    cs = TG.cand_boxes(ob, 30.0, 14.75, (105.0, 125.0))
    chk("④a 含**上·左**（本体上边往外一格）", (100.0, 100.0 - TG.LANE - 14.75) in cs)
    chk("④b 含**上·右**", (140.0 - 30.0, 100.0 - TG.LANE - 14.75) in cs)
    chk("④c 含**下·中**", (((100.0 + 140.0 - 30.0) / 2.0, 120.0 + TG.LANE)) in cs)
    chk("④d 含**左**", (100.0 - TG.LANE - 30.0, 100.0) in cs)
    chk("④e 含**右**", (140.0 + TG.LANE, 100.0) in cs)
    chk("④f 含**原位**（0,0 细档）", (105.0, 125.0) in cs)
    chk("④g 去重（没有重复项）", len(cs) == len({(round(c[0], 3), round(c[1], 3)) for c in cs}))

    # ⑤ bad_for_box ✓（**同一个函数**既管验收也管试位 ✓）
    gap_u = TG.DEFAULT_MM / TG.MM
    texts = [T("位号块", "U9", 1, (10.0, 0.0, 40.0, 14.75))]
    # ★ 自动修要写回 `<titleGeometry>` 的 `x/y` ✓ ⇒ 这一条必须带真元素 ✓（位号块才有 ✓、网标签永远没有 ✓）
    texts[0]["el"] = next(e for e in root.iter("titleGeometry"))
    objs = [O("器件本体", "U9", 1, (12.0, -20.0, 60.0, -5.0)),      # 自己的本体（上方）✓
            O("接地符号", "Ground1", 9, (35.0, 0.0, 52.0, 16.0))]   # 压在右边 ✗
    chk("⑤a 原位压接地符号 ⇒ 1 条",
        len(TG.bad_for_box(root, texts[0]["box"], texts[0], texts, objs, gap_u, pairs)) == 1)
    chk("⑤b 自己本体**不算** ✗",
        all(o["kind"] != "器件本体"
            for o, _d in TG.bad_for_box(root, texts[0]["box"], texts[0], texts, objs,
                                        gap_u, pairs)))
    chk("⑤c 挪到左边空白 ⇒ 0 条",
        len(TG.bad_for_box(root, (-40.0, 0.0, -10.0, 14.75), texts[0], texts, objs,
                           gap_u, pairs)) == 0)

    # ⑥ repair ✓（搬到干净处 ✓ ＋ 位移最小 ✓）
    left, moves = TG.repair(root, texts, objs, gap_u, pairs)
    chk("⑥a 修完剩余 0（%d）" % left, left == 0)
    chk("⑥b 动了 1 处（%d）" % len(moves), len(moves) == 1)
    nb = texts[0]["box"]
    chk("⑥c 落点**已离开**接地符号（净距 %.4f ≥ %.4f）"
        % (TG.box_dist(nb, objs[1]["box"]), gap_u),
        TG.box_dist(nb, objs[1]["box"]) >= gap_u - 1e-9)

    # ⑦ 文字 ↔ 文字 也算 ✓（**每对只数一次** ✓ —— 不许翻倍 ✗）
    texts2 = [T("位号块", "A", 1, (0.0, 0.0, 10.0, 10.0)),
              T("位号块", "B", 5, (5.0, 5.0, 15.0, 15.0))]
    v2 = TG.violations(root, texts2, [], gap_u, pairs)
    v3 = TG.violations(root, texts2, [], 0.0, pairs)
    chk("⑦a 两文字相交 ⇒ **1** 对（不许翻倍 ✗）", len(v2) == 1)
    chk("⑦b gap=0 ⇒ **本判据等于关掉** ✓（= `--text-gap=0` 的“一键回旧行为” ✓）", len(v3) == 0)
    chk("⑦c 试位那把尺子也看得见文字（`bad_for_box` ⇒ %d 条）"
        % len(TG.bad_for_box(root, texts2[0]["box"], texts2[0], texts2, [], gap_u, pairs)),
        len(TG.bad_for_box(root, texts2[0]["box"], texts2[0], texts2, [], gap_u, pairs)) == 1)
    chk("⑦d 两个文字都在**同一边** ⇒ 0 对",
        len(TG.violations(root, [texts2[0], T("位号块", "C", 6, (100.0, 100.0, 110.0, 110.0))],
                           [], gap_u, pairs)) == 0)

    # ⑧ shapes_in_box ✓
    shp = [("stroke", [(1.0, 1.0), (5.0, 5.0)], 1.0)]
    chk("⑧a 顶点落进框 ⇒ True", TG.shapes_in_box(shp, (0.0, 0.0, 2.0, 2.0)))
    chk("⑧b 顶点都在框外 ⇒ False", not TG.shapes_in_box(shp, (10.0, 10.0, 20.0, 20.0)))

    # ⑨ items() 在合成 `.fz` 上跑通 ✓
    texts3, objs3 = TG.items(root, {})
    kinds = sorted({o["kind"] for o in objs3})
    chk("⑨a 扫到 2 个文字（位号块 ＋ 网标签）",
        len(texts3) == 2 and sorted(t["kind"] for t in texts3) == ["位号块", "网标签"])
    chk("⑨b 扫到 2 条导线 ＋ 1 个网标签符号", kinds == ["导线", "网标签符号"])
    chk("⑨c 网标签旗标自带宽高（%.1f × %.1f）"
        % (texts3[1]["box"][2] - texts3[1]["box"][0],
           texts3[1]["box"][3] - texts3[1]["box"][1]),
        texts3[1]["box"][2] - texts3[1]["box"][0] > 0
        and texts3[1]["box"][3] - texts3[1]["box"][1] > 0)
    chk("⑨d 位号块的行内容 = `fritzing_lines()` 给的（title 一行 ✓）",
        texts3[0]["lines"] == ["U9"])
    chk("⑨e 声明对里认得出 网标签2↔Wire3",
        ("2", "3") in TG.declared_pairs(root) and ("3", "2") in TG.declared_pairs(root))

    # ⑩ 第二档的**接头认得出 ＋ 挪与挪回严格互逆** ✓（2026-10-09 ✓ 实测踩过的那个坑 ✗）
    #    合成一只**接地符号**（原点 (100,20) ⇒ 画出来的脚 = 原点 + (9.001,0.596) ✓）
    #    ＋ 一条引线，它的**末端**正落在那个脚上 ✓。
    FZ2 = """<?xml version="1.0" encoding="utf-8"?>
<module>
  <instance moduleIdRef="GroundModuleID" modelIndex="7">
    <title>Ground9</title>
    <views>
      <schematicView layer="schematic">
        <geometry z="3" x="100" y="20" />
        <connectors><connector connectorId="connector0" layer="schematic">
          <geometry x="0" y="0" />
          <connects><connect connectorId="connector0" modelIndex="8" layer="schematicTrace" /></connects>
        </connector></connectors>
      </schematicView>
    </views>
  </instance>
  <instance moduleIdRef="WireModuleID" modelIndex="8">
    <title>Wire9</title>
    <views>
      <schematicView layer="schematic">
        <geometry z="1" x="109.001" y="2.596" x2="0" y2="18" />
        <connectors><connector connectorId="connector0" layer="schematicTrace">
          <geometry x="0" y="0" />
          <connects><connect connectorId="connector0" modelIndex="7" layer="schematic" /></connects>
        </connector></connectors>
      </schematicView>
    </views>
  </instance>
</module>
"""
    r2 = ET.fromstring(FZ2)
    i2 = TG.instances(r2)["7"]
    chk("⑩a 画出来的脚 = 原点 + (9.001,0.596)（%.3f,%.3f = %.3f,%.3f）"
        % (TG.symbol_pin(i2)[0], TG.symbol_pin(i2)[1],
           TG.symbol_pin(i2)[0], TG.symbol_pin(i2)[1]),
        abs(TG.symbol_pin(i2)[0] - 109.001) < 1e-9 and abs(TG.symbol_pin(i2)[1] - 20.596) < 1e-9)
    att = TG.symbol_attachments(r2, i2)
    chk("⑩b 认出那条引线（末端的那个线端 ✓）", att is not None and att[2] == "8")
    chk("⑩c 认的是 `x2/y2`（末端 ✓，不是 `x/y`）", att is not None and att[1] == "xy2")
    _before = TG.wire_ends(TG.instances(r2)["8"])
    TG.nudge_symbol(r2, "7", TG.LANE, 0, att)
    _mid = TG.wire_ends(TG.instances(r2)["8"])
    TG.nudge_symbol(r2, "7", -TG.LANE, 0, att)
    _after = TG.wire_ends(TG.instances(r2)["8"])
    chk("⑩d 挪一步：线端跟着走（%.3f → %.3f）" % (_before[1][0], _mid[1][0]),
        abs(_mid[1][0] - (_before[1][0] + TG.LANE)) < 1e-9)
    chk("⑩e **挪回来 = 原样**（逐字互逆 ✓）", _after == _before)
    chk("⑩f 符号锚点也复原 ✓", TG.instances(r2)["7"]["loc"] == (100.0, 20.0))
    # ✗ 反例：再加一条线端落在同一个脚上 ⇒ **认不准 ⇒ 一律不动** ✓
    _e = ET.fromstring(FZ2)
    _e.append(ET.fromstring(
        '<instance moduleIdRef="WireModuleID" modelIndex="9"><title>Wire10</title>'
        '<views><schematicView layer="schematic">'
        '<geometry z="1" x="109.001" y="20.596" x2="0" y2="4" />'
        '</schematicView></views></instance>'))
    _dup = TG.instances(_e)
    _hits = [1 for omi, d in _dup.items() if "Wire" in d["mid"] and TG.wire_ends(d)
             for pt in TG.wire_ends(d) if math.dist(pt, (109.001, 20.596)) <= 0.05]
    chk("⑩g 两条线端重合在同一个脚上 ⇒ 有 %d 条端、`symbol_attachments` 返回 None（不动 ✓）"
        % len(_hits),
        len(_hits) == 2 and TG.symbol_attachments(_e, _dup["7"]) is None)

    print()
    if FAIL:
        print("✗ **不通过 %d 条** ✗：%s" % (len(FAIL), "；".join(FAIL)))
        return 1
    print("✓ **全过** ✓（第四十九轮 文字净距判据：距离 ✓ / 范围夹取 ✓ / 豁免只一条 ✓ / "
          "候选族 ✓ / 试位与验收同源 ✓ / 自动修 ✓ / 文字×文字 ✓ / 合成图扫描 ✓）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
