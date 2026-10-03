#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""生成 **Capacitor-0402**（SMD 通用电容件 ✓，本库第一套电容 ✓；
   ★ 0603 已删除 ✓ —— Fritzing 自带的 0603 电容（`SMD_multilayer-capacitor_0603`）已支持 ✓）

   用法：py -3.13 svg\Capacitor-0402\gen_part.py            # 生成 + 打 .fzpz ✓
         py -3.13 svg\Capacitor-0402\gen_part.py --check    # 只报数字 ✓（不写文件 ✓）

-----------------------------------------------------------------------------
★ 为什么能"照抄电阻"（每条都有出处 ✓，不是偷懒 ✗）：
  · **PCB 焊盘** = 同封装 SMD 无源件的 land pattern ✓ —— 本库已有 `Resistor-0402` /
    `Resistor-0603`（`R0402_7e77de42…_1_pcb.svg` ✓）就是按 IPC 标称画的 ✓，
    同尺寸的 0402 电容/电阻 land pattern **本来就一样** ✓ ⇒ 直接沿用其几何 ✓（改出处注释 ✓）。
  · **fzp 结构**（moduleId / label / views / connectors / spice ✓）照 `Resistor-*` ✓。
  · **原理图**：★ 2026-10-03 用户定 ✓ —— 直接用 Fritzing 自带瓷片电容的原理图符号 ✓
    （`svg/_assets/ceramic_capacitor_schematic.svg` = core `capacitor.svg` ✓，CC-BY-SA 3.0 ✓，
    见 `svg/_assets/LICENSE-ceramic_capacitor_schematic.txt` ✓）；
    ✗ 不再把电阻的锯齿改成两块极板 ✗（那是自画符号，用户要求与 Fritzing 自带一致 ✓）。
  · **icon**：米白陶瓷体 + 两端银 ✓（仓规 §1 工业风 ✓）；
    ✗ 去掉电阻那套**色环 / 阴影 / 高光**（那是 core 老件的装饰 ✗ ⇒ 仓规 §1 不许加装饰 ✓）。
  · **面包板**：★ 2026-10-02 用户定 ✓ —— 直接用 Fritzing 自带电容 C2 的面包板几何 ✓
    （`svg/_assets/ceramic_capacitor_blue_leg.svg` = 蓝色陶瓷电容 + 两根下插引线 ✓，
    出处 = Fritzing core `SMD_multilayer-capacitor_0603` 的 breadboard svg ✓，CC-BY-SA 3.0 ✓，
    见 `svg/_assets/LICENSE-ceramic_capacitor_blue_leg.txt` ✓）；
    ✗ 不用电阻那套轴向胶囊 ✗（曾把 0402 电容面包板画成电阻图片 ✗，用户 2026-10-02 指出 ✓）。

★ 默认值（2026-10-01 用户确认 ✓；也 = 本项目 `pixel` 板上 C1/C2 的实际用值 ✓）：
  `capacitance = 100nF`（**显示在标签** ✓）｜`voltage = 25V`｜`dielectric = X7R`｜`tolerance = ±10%`
  ★ 电压取 **25V 而不是 16V** 的理由（用户 2026-10-01 ✓）：X7R 有**直流偏压衰减** ✗ ——
    0402/16V 的 100nF 在 5V 下有效容值常只剩 50∼70% ✗；同尺寸 25V 档通常保 70∼90% ✓，
    而**价格几乎一样** ✓ ⇒ 选 25V ✓。
  ★ 值可以改 ✓：`capacitance` 是**属性**（像电阻的阻值一样 ✓）⇒ 在 Fritzing 里随时改 ✓；
    本文件只定**默认值** ✓（= 本项目用的那个值 ✓）。
-----------------------------------------------------------------------------
"""
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))       # = 库根（本文件在 svg/<部件>/ 下 ✓）
FZPZ = os.path.join(ROOT, "fzpz")
# ★ 面包板素材 = Fritzing 自带电容（C2）的面包板 ✓（逐字拷贝 ✓，CC-BY-SA 3.0 ✓，
#   见 `svg/_assets/LICENSE-ceramic_capacitor_blue_leg.txt` ✓）
ASSET_BB = os.path.join(ROOT, "svg", "_assets", "ceramic_capacitor_blue_leg.svg")
# ★ 原理图素材 = Fritzing 自带瓷片电容的原理图符号 ✓（逐字拷贝 ✓，CC-BY-SA 3.0 ✓，
#   见 `svg/_assets/LICENSE-ceramic_capacitor_schematic.txt` ✓）
ASSET_SCHEM = os.path.join(ROOT, "svg", "_assets", "ceramic_capacitor_schematic.svg")

# ── 单档规格（0402 ✓；几何**沿用同封装电阻** ✓；数值来自本库 `Resistor-*.fzpz` ✓）────
#   ★ 0603 已删除（2026-10-02 ✓）—— Fritzing 自带的 0603 电容已支持 ✓
#   `mod` = 新件的 moduleId ✓（照电阻的 `<字母><尺寸>_<32位hex>_1` 格式 ✓；
#   hex 是本次新生成的固定值 ✓ —— 一旦发布就不许改 ✗，否则 Fritzing 里会认成另一个件 ✗）
SPEC = {
    "0402": dict(mod="C0402_b41d7c0a5e93f2d86a14c7b3f5e90d21_1", ref="Resistor-0402",
                 title="Capacitor 0402", pkg="[SMD] 0402",
                 body_w=107.14283, body_x=73.571365,        # icon 里本体矩形（用户单位 ✓）
                 can_w=1.45, can_h=0.60000008),             # pcb 画布 mm ✓
}


def read_fzpz(name):
    z = zipfile.ZipFile(os.path.join(FZPZ, name + ".fzpz"))
    out = {}
    for n in sorted(z.namelist()):
        if n.endswith("/") or n.startswith("__MACOSX"):
            continue
        out[os.path.basename(n)] = z.read(n).decode("utf-8")
    return out


def stem(files, kind):
    """取某个视图的**文件名主干**（= 去掉 `svg.<view>.` 前缀与 `_<view>.svg` 后缀 ✓）"""
    for n in files:
        if n.startswith("svg.%s." % kind) and n.endswith("_%s.svg" % kind):
            return n[len("svg.%s." % kind):-len("_%s.svg" % kind)]
    raise SystemExit("✗ 找不到 %s 视图的文件名 ✗" % kind)


def make_fzp(files, size, s):
    old = files[[n for n in files if n.endswith(".fzp")][0]]
    ostem = stem(files, "icon")
    new = old
    new = new.replace('moduleId="%s"' % ostem, 'moduleId="%s"' % s["mod"])
    new = re.sub(r"<title>[^<]*</title>", "<title>%s</title>" % s["title"], new)
    new = re.sub(r"<label>[^<]*</label>", "<label>C</label>", new)
    # 属性：换成电容那一套 ✓（`capacitance` 才是 Fritzing 认的容值属性 ✓ ——
    #   证据：项目里 C1/C2 的标签就显示 "100 nF" ✓ 而 fzp 属性名是 `capacitance` ✓）
    props = (""" <properties>
  <property name="family">Capacitors</property>
  <property name="package">%s</property>
  <property name="capacitance" showInLabel="yes">100nF</property>
  <property name="voltage" showInLabel="yes">25V</property>
  <property name="dielectric">X7R</property>
  <property name="tolerance" showInLabel="yes">\u00b110%%</property>
 </properties>
""" % s["pkg"])
    new = re.sub(r"(?s) <properties>.*?</properties>\n", props, new, count=1)
    new = new.replace("<tags>", "<tags>", 1)
    new = re.sub(r"(?s)<tags>.*?</tags>",
                 "<tags>\n  <tag>Capacitor</tag>\n  <tag>basic capacitor</tag>\n"
                 "  <tag>fritzing parts of Langhua</tag>\n  <tag>SMD</tag>\n </tags>", new)
    new = new.replace("<taxonomy>discreteParts.resistor</taxonomy>",
                      "<taxonomy>discreteParts.capacitor</taxonomy>")
    new = re.sub(r"<description>[^<]*</description>",
                 "<description>A generic capacitor</description>", new)
    new = re.sub(r"(?s)<spice>.*?</spice>",
                 "<spice>\n  <line>C{instanceTitle} {net connector0} {net connector1} "
                 "{capacitance}</line>\n </spice>", new)
    for kind in ("icon", "breadboard", "schematic", "pcb"):
        new = new.replace("%s/%s" % (kind, stem(files, kind)),
                          "%s/%s" % (kind, s["mod"]))
    # ★ 面包板：与 core 电容（C2）同口径 ✓（2026-10-02 用户定 ✓）——
    #   flip 补偿 + leg 高亮，保证与 C2 渲染**逐字一致** ✓
    #   ★ 只给**顶层视图** `<breadboardView>`（后面跟 `<layers`）加 flip ✗；
    #     `<connector><views>` 里的映射层不加（C2 也没有 ✗）—— 全局替换会把两者都改 ✗
    new = new.replace("<breadboardView>\n   <layers",
                      '<breadboardView fliphorizontal="true" flipvertical="true">\n   <layers')
    new = new.replace('<p layer="breadboard" svgId="connector0pin"/>',
                      '<p layer="breadboard" svgId="connector0pin" legId="connector0leg"/>')
    new = new.replace('<p layer="breadboard" svgId="connector1pin"/>',
                      '<p layer="breadboard" svgId="connector1pin" legId="connector1leg"/>')
    return new


def make_pcb(files, s):
    """PCB：几何**逐字沿用**同封装电阻 ✓（同尺寸 SMD 无源件 land pattern 一致 ✓），
    只改出处注释与 `desc/referenceFile` ✓ —— 绝不改坐标 ✗。"""
    new = files[[n for n in files if ".pcb." in n][0]]
    new = re.sub(r"(?s)<!--.*?-->",
                 "<!--\n        \u710a\u76d8 = \u540c\u5c01\u88c5 SMD \u65e0\u6e90\u4ef6\u7684 land pattern\uff08IPC \u6807\u79f0\uff09\u2713\n"
                 "        \u51fa\u5904 = \u672c\u5e93 `%s`\uff08`svg.pcb.%s_pcb.svg`\uff09\u2713 \u2014\u2014 \u5750\u6807\u9010\u5b57\u6cbf\u7528\u2713\n"
                 "        \u4e1d\u5370\uff1a\u672c\u4f53\u5916\u8f6e\u5ed3\uff0c\u7ebf\u5bbd 0.1mm\uff0c\u4e0e\u710a\u76d8\u95f4\u9699 0.1mm\u2713\n-->" % (s["ref"], stem(files, "pcb")), new, count=1)
    new = re.sub(r"<referenceFile>[^<]*</referenceFile>",
                 "<referenceFile>%s_pcb.svg</referenceFile>" % s["mod"], new)
    new = re.sub(r'sodipodi:docname="[^"]*"',
                 'sodipodi:docname="svg.pcb.%s_pcb.svg"' % s["mod"], new)
    # ★★ 2026-10-01：把从 core 继承来的 **Inkscape 编辑元数据**清掉 ✗ ——
    #   `<sodipodi:namedview …>` / `inkscape:*` / `sodipodi:*` 都是**编辑器状态** ✓，
    #   不是元件几何 ✗；留着会让工具的图元扫描多出一堆“认不出中心”的噪音 ✗
    #   （实测：检查器报 `C1: <namedview id=namedview12> 认不出中心 ✗` ✓）。
    new = re.sub(r"(?s)<sodipodi:namedview\b.*?(?:/>|</sodipodi:namedview>)", "", new)
    new = re.sub(r"\s+xmlns:(?:inkscape|sodipodi)=\"[^\"]*\"", "", new)
    new = re.sub(r"\s+(?:inkscape|sodipodi):[\w-]+=\"[^\"]*\"", "", new)
    return new


def make_schematic(files, s):
    """原理图：★ 2026-10-03 用户定 ✓ —— 直接用 Fritzing 自带瓷片电容的原理图符号 ✓
    （`svg/_assets/ceramic_capacitor_schematic.svg` = core `capacitor.svg`，两块极板电容符号 ✓，
    `connector0/1pin` + `connector0/1terminal` 命名与 fzp 一致 ✓，CC-BY-SA 3.0 ✓）；
    ✗ 不再把电阻的锯齿改成两块极板 ✗（那是自画符号 ✗）。
    """
    txt = open(ASSET_SCHEM, encoding="utf-8").read()
    # ★ core `capacitor.svg` 用**单引号**属性（`id='…'`）✗ —— 本仓检查器/工具只认双引号
    #   `id="…"` ✗ ⇒ 把属性引号 `='…'` 规整成 `="…"` ✓（**不改几何** ✓；
    #   `font-family="'Droid Sans'"` 是双引号包单引号、不含 `='` ⇒ 不受影响 ✓）
    return re.sub(r"='([^']*)'", '="\\1"', txt)


def make_body(files, kind, s):
    """icon：去掉**色环**（电阻的标记 ✗），本体改成**米黄陶瓷** ✓；
    再去掉阴影/高光 ✗（仓规 §1 不许加装饰 ✓）；面包板见函数体开头（直接 = core 电容 ✓）。

    ★ 为什么要改本体颜色 ✗：电阻件那套是 core 老件 ✓ —— 中间那块是**深色体**（75% 黑 ✗），
      那是厚膜电阻的真实外观 ✓；**陶瓷电容**是**米黄体 + 两端银** ✓（真实外观 ✓）
      ⇒ 不改就画出一颗“深灰方糖” ✗（渲图看过 ✓，不是猜 ✗）。
    """
    if kind == "breadboard":
        # ★ 2026-10-02 用户定 ✓：面包板直接 = Fritzing 自带电容（C2）的面包板 ✓
        #   （蓝色陶瓷电容 + 两根下插引线、2.54mm 脚距 ✓ —— 逐字沿用 core 素材 ✓）
        return open(ASSET_BB, encoding="utf-8").read()
    new = files[[n for n in files if ".%s." % kind in n][0]]
    for rid in ("gold_band", "band_rd_multiplier", "band_2_nd", "band_1_st",
                "Shadow", "ShadowExtra", "ReflexRight", "ReflexLeft",
                "Reflex_gold", "Reflex_extra"):
        # 自闭合 rect ✓ 与 <path …/> ✓ 两种都要能删 ✓
        new = re.sub(r'<rect[^>]*id="%s"[^>]*/>\s*' % rid, "", new)
        new = re.sub(r'<path[^>]*id="%s"[^>]*/>\s*' % rid, "", new)
    if kind == "icon":
        # 陶瓷体：`fill:#000000;fill-opacity:0.74902` ⇒ **米黄** ✓（同面包板 view 的本体色 ✓）
        new = new.replace(
            'style="opacity:0.75;fill:#000000;fill-opacity:0.74902;fill-rule:evenodd;'
            'stroke-width:260.819;stroke-linecap:round"',
            'style="fill:#D9B477;fill-opacity:1;stroke:none"')
    return new


def build(size, write=True):
    s = SPEC[size]
    files = read_fzpz(s["ref"])
    fzp = make_fzp(files, size, s)
    svgs = dict(icon=make_body(files, "icon", s), breadboard=make_body(files, "breadboard", s),
                schematic=make_schematic(files, s), pcb=make_pcb(files, s))
    out = {("part.%s.fzp" % s["mod"]): fzp}
    for kind, txt in svgs.items():
        out["svg.%s.%s_%s.svg" % (kind, s["mod"], kind)] = txt
    if write:
        d = os.path.join(ROOT, "svg", "Capacitor-" + size)
        os.makedirs(d, exist_ok=True)
        for n, txt in out.items():
            with open(os.path.join(d, n), "w", encoding="utf-8", newline="") as f:
                f.write(txt)
        z = os.path.join(FZPZ, "Capacitor-%s.fzpz" % size)
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as w:
            for n in sorted(out):
                w.writestr(n, out[n].encode("utf-8"))
    return s, out


def main(argv):
    write = "--check" not in argv
    for size in SPEC:
        s, out = build(size, write)
        print("== Capacitor-%s ==" % size)
        print("   moduleId = %s ✓｜%d 个文件 ✓（%s）"
              % (s["mod"], len(out), ", ".join(sorted(out))))
        for n, txt in sorted(out.items()):
            ids = re.findall(r'id="(connector[01][a-z]+|silkscreen)"', txt)
            print("   %-52s %6d 字节 ｜ 连接点/丝印 id：%s"
                  % (n, len(txt.encode("utf-8")), ",".join(sorted(set(ids))) or "—"))
        if write:
            d = os.path.join(ROOT, "svg", "Capacitor-" + size)
            print("   ⇒ 写出 %s ✓ + fzpz/Capacitor-%s.fzpz ✓" % (d, size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
