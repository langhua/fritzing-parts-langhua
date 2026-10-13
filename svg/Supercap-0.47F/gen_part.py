#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""生成 **Supercap-0.47F / Supercap-1.5F**（凯美 C 型法拉电容 / 超级电容 ✓，本库第一套超容 ✓）

★ 两档都在这里生成 ✓（本文件在 `svg/Supercap-0.47F/` 下，产物写进 `svg/Supercap-<容量>/` ✓）
  —— 与 `Capacitor-0402/gen_part.py`（两档一个生成器 ✓）、`Resistor-*` 家族同一套做法 ✓。

   用法：py -3.13 svg\Supercap-0.47F\gen_part.py            # 生成两档 + 打 .fzpz ✓
         py -3.13 svg\Supercap-0.47F\gen_part.py --check    # 只报数字 ✓（不写文件 ✓）

-----------------------------------------------------------------------------
★ 数据出处（**每个数字都能指回厂商规格书** ✓ —— 不许估 ✗，AGENTS §10.8 ✓）
  两份 PDF（锦州凯美能源有限公司《产品规格书》，用户 2026-10-13 给 ✓）：

  | 项（图纸 §7 表头） | 0.47F | 1.5F | 说明 |
  |---|---|---|---|
  | 型号 PART NO.        | `SE-5R5-D474VYC3H` | `SE-5R5-D155VYC3G` | p1 ✓ |
  | 尺寸 ΦD×H            | **13 × 6.5** mm | **20.5 × 7** mm | p4「尺寸 Size (ΦD×H)」✓ |
  | 引线距离 P           | **5** mm | **6** mm | p4 ✓ |
  | 正极引线长 H2        | **12** mm | **13** mm | p4 ✓ |
  | 负极引线长 H1        | **12.5** mm | **12.5** mm | p4 ✓ |
  | 引线厚度 T           | **0.4** mm | **0.45** mm | p4 ✓ |
  | 额定容量 / 容差      | 0.47F / −10~+30% | 1.5F / −10~+30% | p3 ✓ |
  | 额定电压 / ESR(1kHz) | 5.5V / 40Ω | 5.5V / — | p3 ✓ |
  | 工作温度             | −25 ~ +70 ℃ | 同 | p3 ✓ |
  （p1 = 封面 ✓、p3 = §5 特性指标 ✓、p4 = §7 外形尺寸图 ✓）

★ 画法（**照 Fritzing 核心库那颗法拉电容** ✓ = `core/capacitor_elko_goldcap_4.0F_*.fzp` ✓
  ＋ `svg/core/{icon,breadboard,schematic,pcb}/capacitor_elko_goldcap_*` ✓，AGENTS §10.9
  「成熟产品是权威」✓）：
  · **icon / breadboard** = **侧视圆柱**（本体圆盘 + 顶面椭圆 + 两根下出引线 ✓）；
    ✗ 不加核心库那几笔**高光/内椭圆装饰** ✗（`#D2EEFF` / `#100040` ✓ —— 仓规 §1 工业风 ✓）。
  · **schematic** = 核心库的**极性电容符号** ✓ 逐字沿用（`svg/_assets/polar_capacitor_schematic.svg`
    ✓，= `core/svg/schematic/capacitor_polar.svg` 的实例化版 ✓，CC-BY-SA 3.0 ✓，
    见 `svg/_assets/LICENSE-polar_capacitor_schematic.txt` ✓）。
  · **pcb** = 两个 **THT 圆焊盘**（外径 **2.0** / 孔径 **1.0** ✓，＝本库转接板那套口径 ✓）
    ＋ **本体外轮廓丝印**（ΦD 圆 ✓）＋ **极性“+”丝印**（在正极焊盘旁 ✓，不压焊盘 ✓，§10.16 ✓）。

★ 极性（**尊重原厂** ✓）：原厂图纸标了「负极标志 Cathode sign」✓ ⇒ 本件**有极性** ✓：
  `family = "Capacitor [unidirectional]"` ✓（照核心电解电容 ✓）、
  `connector0 = "-"` ✓、`connector1 = "+"` ✓（**核心库 goldcap 就是这个顺序** ✓）。
  ★ 原理图符号里 **connector1 在上（= +）** ✓、connector0 在下（= −）✓ —— 与核心符号一致 ✓。

★ 引线画多长 ✗：实物引线 12 / 12.5 mm（**未剪** ✓）—— 图上画 **2.5 mm**（≈一个面包板格 ✓），
  这是“插上去之后能看见的那一段”✓；**实物尺寸本身照实测值写进 `lead_*`** ✓（不丢信息 ✓）。

★ 电容值数据项 = `capacitance` ✓（**必须小写** ✓，用户 2026-10-13 要的就是它 ✓）：
  出处 = Fritzing 源码 `items/capacitor.cpp:241` ← `keys.removeOne("capacitance")` ✓
  （同 A13：写大写 `Capacitance` 会**静默取不到值** ✗）。默认值就是本型号的额定容量 ✓。
-----------------------------------------------------------------------------
"""
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))       # = 库根（本文件在 svg/<部件>/ 下 ✓）
FZPZ = os.path.join(ROOT, "fzpz")
ASSET_SCHEM = os.path.join(ROOT, "svg", "_assets", "polar_capacitor_schematic.svg")

# ── 规格（**全部来自厂商 PDF** ✓，逐项标出处见文件头 ✓）──────────────────────
SPEC = {
    "0.47F": dict(
        mod="SC474_a3f81c6d04b7e25938ad1f604c8e7b31_1-CapacitorModuleID",   # ★ 后缀 = 让 Fritzing 当它是**电容** ✓
        title="Supercapacitor 0.47F 5.5V",
        part_no="SE-5R5-D474VYC3H",
        d=13.0, h=6.5, pitch=5.0, lead_p=12.0, lead_n=12.5, lead_t=0.4,
        cap="0.47F", tol="-10~+30%", pkg="C\u578b 13\u00d76.5 [THT, supercapacitor]",
    ),
    "1.5F": dict(
        mod="SC155_6d20b9e74af15c8301e6d2749b5f0a8c_1-CapacitorModuleID",
        title="Supercapacitor 1.5F 5.5V",
        part_no="SE-5R5-D155VYC3G",
        d=20.5, h=7.0, pitch=6.0, lead_p=13.0, lead_n=12.5, lead_t=0.45,
        cap="1.5F", tol="-10~+30%", pkg="C\u578b 20.5\u00d77 [THT, supercapacitor]",
    ),
}
LEAD_DRAWN = 2.5          # 图上画多长引线（mm ✓）
PAD_D, PAD_HOLE = 2.0, 1.0
UREF = "#8C8C8C"          # 引线灰（本库引脚线灰 ✓）
UFOOT = "#C8C8C8"         # 引线端头（银 ✓）
BODY = "#2B2B2B"          # 本体（超容是**深色胶壳** ✓，不是陶瓷米黄 ✓）
TOP = "#4A4A4A"           # 顶面（比本体浅一点，表出圆柱 ✓）
MARK = "#2B2B2B"          # 极性“+”标记（**深色** ✗ 不是白 ✗ —— 它在浅底空白处 ✓）


def fmt(v):
    """统一小数格式 ✓（免"同值不同字面"造成字节漂移 ✗）。"""
    return ("%.4f" % v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def svg_head(w, h, vb, extra=""):
    """★ `<svg>` 头**必须同时有 width 和 height** ✗（只写 width ⇒ Fritzing 报"不能创建渲染" ✗）。"""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" version="1.1"\n'
            '     width="%smm" height="%smm" viewBox="%s"%s>\n' % (fmt(w), fmt(h), vb, extra))


def body_art(cx, top, s, gid):
    """侧视圆柱（本体 + 顶面 + 两根下出引线 ✓）—— icon 与 breadboard 共用 ✓（尺寸一致 ✓）。"""
    d, h, p = s["d"], s["h"], s["pitch"]
    x0, y0 = cx - d / 2.0, top
    y1 = y0 + h
    lx0, lx1 = cx - p / 2.0, cx + p / 2.0
    out = ['  <g id="%s">\n' % gid]
    out.append('   <!-- \u672c\u4f53\uff1a\u03a6%s \u00d7 %s mm\uff08\u5382\u5546\u89c4\u683c\u4e66 p4 \u2713\uff09 -->\n'
               % (fmt(d), fmt(h)))
    out.append('   <rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>\n'
               % (fmt(x0), fmt(y0), fmt(d), fmt(h), BODY))
    out.append('   <ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>\n'
               % (fmt(cx), fmt(y0), fmt(d / 2.0), fmt(d * 0.12), TOP))
    out.append('   <!-- \u5f15\u7ebf\uff1a\u95f4\u8ddd %s mm\uff08= \u5f15\u7ebf\u8ddd\u79bb P\uff0c\u540c\u4e0a\u2713\uff09\uff1b'
               '\u56fe\u4e0a\u753b %s mm\uff08\u5b9e\u7269 %s / %s mm\uff0c\u89c1\u6587\u4ef6\u5934\u2713\uff09 -->\n'
               % (fmt(p), fmt(LEAD_DRAWN), fmt(s["lead_n"]), fmt(s["lead_p"])))
    for x, tag in ((lx0, "0"), (lx1, "1")):
        out.append('   <line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" '
                   'stroke-linecap="round"/>\n'
                   % (fmt(x), fmt(y1), fmt(x), fmt(y1 + LEAD_DRAWN), UREF, fmt(max(s["lead_t"], 0.4))))
        out.append('   <rect id="connector%spin" x="%s" y="%s" width="%s" height="0.0001" '
                   'fill="none" stroke="none"/>\n'
                   % (tag, fmt(x - 0.5), fmt(y1 + LEAD_DRAWN), fmt(1.0)))
    out.append('  </g>\n')
    return "".join(out)


def make_icon(s):
    """icon：**mm 1:1**（✗ 不沿用电阻那张用户单位画布 ✗ —— 形状完全不同 ✓，按实物画好核对 ✓）。"""
    w = s["d"] + 3.0
    h = s["h"] + 3.0 + LEAD_DRAWN
    cx, top = w / 2.0, 1.5
    out = [svg_head(w, h, "0 0 %s %s" % (fmt(w), fmt(h)))]
    out.append(' <g id="icon">\n')
    out.append(body_art(cx, top, s, "body"))
    # 极性“+”画在**正极引线旁**（信息，不是装饰 ✓ —— 原厂图纸有「负极标志」✓）
    # ★ 颜色必须是**深灰** ✗ 不是白 ✗ —— 它在**本体外**的空白处（浅底 ✓），
    #   写白 = 白底白字 = **看不见** ✗（本库工具渲图自查时抓到的 ✓）。
    px, py = cx + s["pitch"] / 2.0, top + s["h"] + 0.9
    out.append('  <!-- \u6781\u6027\uff1a\u201c+\u201d \u5728\u6b63\u6781\u5f15\u7ebf\u65c1\uff08\u539f\u5382\u56fe\u7eb8\u6807\u4e86\u8d1f\u6781\u6807\u5fd7 \u2713\uff09 -->\n')
    out.append('  <g stroke="%s" stroke-width="0.4" stroke-linecap="round">\n' % MARK)
    out.append('   <line x1="%s" y1="%s" x2="%s" y2="%s"/>\n'
               % (fmt(px + 0.8), fmt(py), fmt(px + 1.8), fmt(py)))
    out.append('   <line x1="%s" y1="%s" x2="%s" y2="%s"/>\n'
               % (fmt(px + 1.3), fmt(py - 0.5), fmt(px + 1.3), fmt(py + 0.5)))
    out.append('  </g>\n')
    out.append(' </g>\n</svg>\n')
    return "".join(out)


def make_breadboard(s):
    """breadboard：同 icon 的侧视 ✓ + **两根插腿**（`connectorNleg` ✓ 照核心库做法 ✓）。

    ★ 脚距照**实际**（5 / 6 mm ✓）—— 0.47F 的 5 mm 嵌面包板 2 孔（5.08 ✓）差 0.08 mm ⇒ 能插 ✓；
      1.5F 的 6 mm ✗ 不是 2.54 的整数倍 ⇒ 实际用要微掰引线 ✓（**如实画** ✓，不假装对齐 ✗）。
    """
    w = s["d"] + 3.0
    h = s["h"] + 3.0 + LEAD_DRAWN + 2.54
    cx, top = w / 2.0, 1.5
    out = [svg_head(w, h, "0 0 %s %s" % (fmt(w), fmt(h)))]
    out.append(' <g id="breadboard">\n')
    out.append(body_art(cx, top, s, "body"))
    y = top + s["h"] + LEAD_DRAWN
    for x, tag in ((cx - s["pitch"] / 2.0, "0"), (cx + s["pitch"] / 2.0, "1")):
        out.append('  <line id="connector%sleg" x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                   'stroke-width="%s" stroke-linecap="round"/>\n'
                   % (tag, fmt(x), fmt(y), fmt(x), fmt(y + 2.54), UREF,
                      fmt(max(s["lead_t"], 0.5))))
    # 极性“+”（同 icon ✓ —— 深色、在本体外 ✓）+ 脚距提示（0.47F 的 5 mm 贴 2 孔 5.08 ✓；
    # 1.5F 的 6 mm 不是 2.54 的整数倍 ⇒ 实际用要微掰引线 ✓ 如实注明 ✓）
    out.append('  <g stroke="%s" stroke-width="0.4" stroke-linecap="round">\n' % MARK)
    _px = cx + s["pitch"] / 2.0 + 1.1
    _py = top + s["h"] + 0.9
    out.append('   <line x1="%s" y1="%s" x2="%s" y2="%s"/>\n'
               % (fmt(_px), fmt(_py), fmt(_px + 1.0), fmt(_py)))
    out.append('   <line x1="%s" y1="%s" x2="%s" y2="%s"/>\n'
               % (fmt(_px + 0.5), fmt(_py - 0.5), fmt(_px + 0.5), fmt(_py + 0.5)))
    out.append('  </g>\n')
    out.append(' </g>\n</svg>\n')
    return "".join(out)


def make_schematic(s):
    """schematic：**逐字沿用**核心库极性电容符号 ✓（`svg/_assets/polar_capacitor_schematic.svg` ✓）。

    ★ 与 `Capacitor-0402` 用 core 瓷片电容符号 ✓ 同一套路（用户 2026-10-02/10-03 定的口径 ✓）；
      本件**有极性** ⇒ 用 core 的**极性**符号（`capacitor_polar` ✓），✗ 不是瓷片那个双向符号 ✗。
    ★ core `capacitor_polar.svg` 用**单引号**属性（`id='…'`）✗ —— 本仓检查器/工具只认双引号
      `id="…"` ✗ ⇒ 把 `='…'` 规整成 `="…"` ✓（**不改几何** ✓；`font-family="'Droid Sans'"`
      是双引号包单引号、不含 `='` ⇒ 不受影响 ✓）。同 `Capacitor-0402/gen_part.py` ✓。
    """
    txt = open(ASSET_SCHEM, encoding="utf-8").read()
    return re.sub(r"='([^']*)'", '="\\1"', txt)


def make_pcb(s):
    """pcb：两个 THT 圆焊盘（外径 2.0 / 孔径 1.0 ✓ 本库口径）+ 本体轮廓丝印（ΦD 圆）
    + 极性“+”丝印 ✓（§10.16：丝印不许压焊盘 ✓ —— 这里“+”距正极焊盘边缘 ≥ 0.5 mm ✓）。"""
    d, p = s["d"], s["pitch"]
    can = d + 2.0                                  # 画布：轮廓圆两边各留 1 mm ✓
    c = can / 2.0
    out = [svg_head(can, can, "0 0 %s %s" % (fmt(can), fmt(can)))]
    out.append(' <g id="silkscreen">\n')
    out.append('  <!-- \u672c\u4f53\u5916\u8f6e\u5ed3\uff08\u03a6%s\uff0c\u00a710.16\uff1a\u4e1d\u5370\u4e0d\u538b\u710a\u76d8 \u2713\uff09 -->\n' % fmt(d))
    out.append('  <circle cx="%s" cy="%s" r="%s" fill="none" stroke="#ffffff" stroke-width="0.12"/>\n'
               % (fmt(c), fmt(c), fmt(d / 2.0)))
    px = c + p / 2.0
    # ★ “+”画在**正极焊盘正上方、轮廓圆内** ✓：
    #   · 焊盘外缘 = c − 1.0 ✓ ⇒ 中心取 y = c − 2.4（离焊盘外缘 0.9 mm ✓ ≫ 0.23 ✓ §10.16 ✓）
    #   · ⚠ 第一版画在**圆外**（y = c − d/2 − 1.0 ✗）⇒ 对小画布正好落在画布边缘 ⇒ **被切掉** ✗
    #     （1.5F 渲图自查时看到“+ 贴在最上面”✓ —— 大件（20.5）时 can=c 的边距撑不住 ✓）
    yy = c - 2.4
    out.append('  <!-- \u6781\u6027\u201c+\u201d\uff1a\u6b63\u6781\u5f15\u811a\u90a3\u4fa7\u3001\u753b\u5728\u8f6e\u5ed3\u5706\u5185 \u2713 -->\n')
    out.append('  <g stroke="#ffffff" stroke-width="0.15" stroke-linecap="round">\n')
    out.append('   <line x1="%s" y1="%s" x2="%s" y2="%s"/>\n'
               % (fmt(px - 0.5), fmt(yy), fmt(px + 0.5), fmt(yy)))
    out.append('   <line x1="%s" y1="%s" x2="%s" y2="%s"/>\n'
               % (fmt(px), fmt(yy - 0.5), fmt(px), fmt(yy + 0.5)))
    out.append('  </g>\n </g>\n')
    out.append(' <g id="copper0">\n')
    out.append(' </g>\n <g id="copper1">\n')
    # ★ THT 焊盘环的算法（本库口径 ✓）：外径 = 2r + stroke-width ✓、孔径 = 2r − stroke-width ✓
    #   ⇒ 要「外 2.0 / 孔 1.0」⇒ r = (2.0 + 1.0)/4 = 0.75 ✓、stroke-width = (2.0 − 1.0)/2 = 0.5 ✓
    #   ⚠ 第一版写成 r=(PAD_D−PAD_HOLE)/2 = 0.5 ＋ stroke-width=PAD_HOLE = 1.0 ✗
    #     ⇒ 孔径 = 2×0.5 − 1.0 = **0** ✗（孔被堵上 ✗）—— 渲图自查时抓到 ✓。
    _r = (PAD_D + PAD_HOLE) / 4.0
    _w = (PAD_D - PAD_HOLE) / 2.0
    for x, tag in ((c - p / 2.0, "0"), (c + p / 2.0, "1")):
        out.append('  <circle id="connector%spad" cx="%s" cy="%s" r="%s" fill="none" stroke="#F7BD13" '
                   'stroke-width="%s"/>\n'
                   % (tag, fmt(x), fmt(c), fmt(_r), fmt(_w)))
    out.append(' </g>\n</svg>\n')
    return "".join(out)


def make_fzp(s):
    return """<?xml version='1.0' encoding='UTF-8'?>
<module fritzingVersion="1.0.3" moduleId="%(mod)s">
 <version>4</version>
 <title>%(title)s</title>
 <label>C</label>
 <date>Mon Oct 13 2026</date>
 <author>Shi Jinghai</author>
 <tags>
  <tag>Capacitor</tag>
  <tag>Supercapacitor</tag>
  <tag>Goldcap</tag>
  <tag>EDLC</tag>
  <tag>fritzing parts of Langhua</tag>
  <tag>THT</tag>
  <tag>Kamcap</tag>
 </tags>
 <properties>
  <property name="family">Capacitor [unidirectional]</property>
  <property name="package">%(pkg)s</property>
  <property name="capacitance" showInLabel="yes">%(cap)s</property>
  <property name="voltage" showInLabel="yes">5.5V</property>
  <property name="tolerance" showInLabel="yes">%(tol)s</property>
  <property name="part number">%(part_no)s</property>
 </properties>
 <taxonomy>discreteParts.capacitor</taxonomy>
 <description>Kamcap C-type supercapacitor %(cap)s 5.5V (%(part_no)s)</description>
 <spice>
  <line>C{instanceTitle} {net connector0} {net connector1} {capacitance} IC=0</line>
 </spice>
 <views>
  <iconView>
   <layers image="icon/%(mod)s_icon.svg">
    <layer layerId="icon"/>
   </layers>
  </iconView>
  <breadboardView>
   <layers image="breadboard/%(mod)s_breadboard.svg">
    <layer layerId="breadboard"/>
   </layers>
  </breadboardView>
  <schematicView>
   <layers image="schematic/%(mod)s_schematic.svg">
    <layer layerId="schematic"/>
   </layers>
  </schematicView>
  <pcbView>
   <layers image="pcb/%(mod)s_pcb.svg">
    <layer layerId="copper1"/>
    <layer layerId="silkscreen"/>
   </layers>
  </pcbView>
 </views>
 <connectors>
  <connector id="connector0" name="-" type="male">
   <description>- side (cathode)</description>
   <views>
    <breadboardView>
     <p layer="breadboard" svgId="connector0pin" legId="connector0leg"/>
    </breadboardView>
    <schematicView>
     <p layer="schematic" svgId="connector0pin" terminalId="connector0terminal"/>
    </schematicView>
    <pcbView>
     <p layer="copper1" svgId="connector0pad"/>
    </pcbView>
   </views>
  </connector>
  <connector id="connector1" name="+" type="male">
   <description>+ side (anode)</description>
   <views>
    <breadboardView>
     <p layer="breadboard" svgId="connector1pin" legId="connector1leg"/>
    </breadboardView>
    <schematicView>
     <p layer="schematic" svgId="connector1pin" terminalId="connector1terminal"/>
    </schematicView>
    <pcbView>
     <p layer="copper1" svgId="connector1pad"/>
    </pcbView>
   </views>
  </connector>
 </connectors>
 <buses>
 </buses>
</module>
""" % s


def build(size, write=True):
    s = SPEC[size]
    out = {"part.%s.fzp" % s["mod"]: make_fzp(s),
           "svg.icon.%s_icon.svg" % s["mod"]: make_icon(s),
           "svg.breadboard.%s_breadboard.svg" % s["mod"]: make_breadboard(s),
           "svg.schematic.%s_schematic.svg" % s["mod"]: make_schematic(s),
           "svg.pcb.%s_pcb.svg" % s["mod"]: make_pcb(s)}
    if write:
        d = os.path.join(ROOT, "svg", "Supercap-" + size)
        os.makedirs(d, exist_ok=True)
        for n, txt in out.items():
            with open(os.path.join(d, n), "w", encoding="utf-8", newline="") as f:
                f.write(txt)
        z = os.path.join(FZPZ, "Supercap-%s.fzpz" % size)
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as w:
            for n in sorted(out):
                w.writestr(n, out[n].encode("utf-8"))
    return s, out


def main(argv):
    write = "--check" not in argv
    print("★ 数据出处：凯美《产品规格书》p1（型号）/ p3（容量·容差·电压·ESR）/ p4（尺寸）✓")
    for size in SPEC:
        s, out = build(size, write)
        print("== Supercap-%s ==" % size)
        print("   型号 = %s ✓｜Φ%s × %s mm ✓｜引线距离 P = %s mm ✓｜引线 %s / %s mm、厚 %s ✓"
              % (s["part_no"], fmt(s["d"]), fmt(s["h"]), fmt(s["pitch"]),
                 fmt(s["lead_p"]), fmt(s["lead_n"]), fmt(s["lead_t"])))
        print("   moduleId = %s ✓｜%d 个文件 ✓" % (s["mod"], len(out)))
        for n, txt in sorted(out.items()):
            ids = re.findall(r'id="(connector[01][a-z]+|silkscreen|icon|breadboard)"', txt)
            print("   %-54s %6d 字节 ｜ id：%s"
                  % (n, len(txt.encode("utf-8")), ",".join(sorted(set(ids))) or "—"))
        if write:
            print("   ⇒ 写出 svg/Supercap-%s/ ✓ + fzpz/Supercap-%s.fzpz ✓" % (size, size))
    if write:
        print("★ 接着跑：py -3.13 tools\\repack_fzpz.py  # 归一化 LF + 固定时间戳 ✓")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
