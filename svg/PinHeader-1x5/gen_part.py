# -*- coding: utf-8 -*-
"""Generate a complete Fritzing part: PinHeader-1x5 (1×5 male pin header).

口径与出处（**每条都能指出来源** ✓，不编数据 ✗）：

  尺寸/脚距/焊盘/丝印图形  =  **Fritzing 核心库**的 3 脚 0.1in 公排针
      `svg/core/pcb/Dagu_DGServo_9g_header_male_pcb.svg` ✓
      `svg/core/schematic/Dagu_DGServo_9g_header_male_schematic.svg` ✓
      `svg/core/breadboard/Dagu_DGServo_9g_header_male_breadboard.svg` ✓
      （2026-10-13 读的 ✓；它的 `referenceFile="generic_male_pin_header_3_100mil.fzp"` 是
       Fritzing **运行时**生成的母版 ⇒ 磁盘上没有 ✗ ⇒ 只能照这只实体件抄 ✓）
      · 焊盘：`r=29 mil` / `stroke=20 mil` ⇒ **外 1.98 mm / 孔 0.97 mm** ✓
        ⇒ **与本库 `svg/NetLabel-Pad` 及 `AGENTS` §3b 的 2.54 排针口径完全相同** ✓
      · **1 脚画方环**（其余圆环）✓ —— 官方就是这么标 1 脚的 ✓（不是丝印圆点 ✗）
      · 丝印 = 本体轮廓框 + 1 脚斜撇 ✓

  单位/线宽/字号/terminal 画法  =  **本库同族 mm 单位件** `svg/PH-2.0-3P-V` ✓
      · mm 单位（`width="5.60mm" viewBox="…"` ✓）
      · 引脚线 `class="pin"` `stroke="#787878"` `stroke-width="0.246944"` round cap ✓
      · terminal = 极小不可见 rect ✓；脚号 `#8C8C8C` / `DroidSans` / `font-size 1.30`
        放在引线**上方** ✓

  breadboard 视图  =  俯视：深灰塑料条 + N 个金针 ✓（照着实物画 ✓，不加 3D 高光/阴影 ✓
      见 AGENTS §1 工业风 ✓）＋ 每脚一组**隐形命中框** `connectorNpin` / `connectorNterminal` ✓
      （照官方 core 排针的 bb 视图：1 mm 方 = 一个脚的命中区 ✓、terminal 略小 ✓）——
      Fritzing 靠它们把脚吸附到面包板孔上 ✓，所以**脚必须落在 2.54 mm 网格上** ✓
      （本件 y = 0 / 2.54 / 5.08 … ✓，第 1 脚在原点 ✓）
      ★ **不能省 breadboard 视图** ✗：`tools/fzp_check.py` 会判 FAIL（实测 ✓）——
        `svg/NetLabel-Pad` 只有三视图 ⇒ 它那条 FAIL 是**既存违规** ✗（不属本次改动，别顺手改 ✗）

  **脚名 = `1`…`N`** ✓（通用件不写信号名 ✗；网名由原理图上的连线/网标签决定 ✓）

用法（本目录下）：py -3.13 gen_part.py   ⇒ 4 个源文件 + `fzpz/PinHeader-1x5.fzpz` ✓
★ 打完包**必须**再跑一次 `py -3.13 tools/repack_fzpz.py` ✓（LF + 固定时间戳，见 AGENTS §14 ✓）
"""

import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

N = 5                       # ★ 脚数（本件 = 1×5）
PART_ID = "PinHeader-1x%d" % N

PITCH = 2.54                # 2.54 mm = 0.1 in ✓（官方 core 排针 100 mil ✓）
PAD_R = 0.737               # 焊盘环中心线半径 ⇒ 外 1.98 mm ✓
PAD_STROKE = 0.508          # 环宽 ⇒ 孔 0.97 mm ✓
SILK_W = 0.12               # 丝印线宽（照 PH-2.0-3P-V ✓）
BODY_W = 2.54               # 本体（塑料条）宽 ✓ ⇒ 丝印框半宽 1.27 ✓
BODY_MARGIN = 1.27          # 本体上下各伸出 1.27 mm ✓（= 脚距一半，官方同 ✓）
PIN_W = 0.64                # 针脚截面 0.64 mm ✓（标准 2.54 排针 ✓）
PLASTIC = "#404040"         # 塑料色（照官方 core 排针面包板视图的 `#404040` ✓）
GOLD = "#f7bf13"            # 铜/金（本库统一 ✓）
SILK = "#f0f0f0"            # 丝印色（照 PH-2.0-3P-V ✓）
PINCOL = "#787878"          # 原理图引脚线灰（照 PH-2.0-3P-V ✓）
PIN_W_SCH = 0.246944        # 原理图引脚线宽（= Fritzing 核心库默认值 ✓，见 AGENTS §5 ✓）
FN = 1.30                   # 原理图脚号字号（照 PH-2.0-3P-V ✓）
SCH_LEAD = 2.54             # 原理图引线长 ✓（照 PH-2.0-3P-V ✓）
SCH_BODY_X0 = 2.54          # 原理图本体左缘 ✓
SCH_BODY_W = 1.80           # 原理图本体宽 ✓（照 PH-2.0-3P-V 的 2.54..4.34 ✓）
SCH_BODY_MARGIN = 1.10      # 本体上下各伸出 ✓（照 PH-2.0-3P-V 的 2.07→0.97 ✓）
PAD_MARGIN = 0.28           # 丝印框到焊盘外缘的净距 ✓（官方 11 mil = 0.28 mm ✓）

PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID
FZPZ = "%s.fzpz" % PART_ID

PCB_REF = "pcb/%s_pcb.svg" % PART_ID
SCHEM_REF = "schematic/%s_schematic.svg" % PART_ID
ICON_REF = "icon/%s_icon.svg" % PART_ID
BB_REF = "breadboard/%s_breadboard.svg" % PART_ID

HIT_W = 1.00                # 面包板命中框边长（官方 core 排针 bb 视图 = 0.985 mm ✓）
TERM_W = 0.78               # terminal 命中框边长（官方 = 0.763/0.798 mm ✓）


def f(v):
    """固定两位小数 ⇒ 生成器可重复（G3 闸门要比逐字节 ✓）"""
    return "%.2f" % float(v)


def ys():
    """每只脚的 y（纵向排，第 1 脚在最上 ✓）"""
    return [i * PITCH for i in range(N)]


# --------------------------------------------------- 外观（icon / bb 共用）
def _look_group(gid, with_hits):
    """俯视外观：深灰塑料条 + N 个金色针脚（针顶面 0.64 mm 方 ✓，标准 2.54 排针 ✓）。
    `with_hits=True` 时另加每组**隐形命中框**（面包板视图要 ✓、icon 不要 ✗）。
    viewBox 与 pcb 视图**完全相同** ✓（同 `NetLabel-Pad` 的口径：缩略图同比例 ✓）"""
    H = N * PITCH + 1.0                      # 上下各留 0.5 mm ✓
    s = [' <g id="%s">' % gid,
         '  <rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="none"/>'
         % (f(-BODY_W / 2), f(-BODY_MARGIN), f(BODY_W),
            f((N - 1) * PITCH + 2 * BODY_MARGIN), PLASTIC)]
    if with_hits:                            # ★ 命中框先画（在针下面 ✓，透明不影响视觉 ✓）
        for i, y in enumerate(ys()):
            s.append('  <rect id="connector%dpin" connectorname="%d" x="%s" y="%s" '
                     'width="%s" height="%s" fill="none" stroke="none"/>'
                     % (i, i + 1, f(-HIT_W / 2), f(y - HIT_W / 2), f(HIT_W), f(HIT_W)))
            s.append('  <rect id="connector%dterminal" x="%s" y="%s" width="%s" height="%s" '
                     'fill="none" stroke="none"/>'
                     % (i, f(-TERM_W / 2), f(y - TERM_W / 2), f(TERM_W), f(TERM_W)))
    for i, y in enumerate(ys()):
        s.append('  <rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="none"/>'
                 % (f(-PIN_W / 2), f(y - PIN_W / 2), f(PIN_W), f(PIN_W), GOLD))
    s += [' </g>']
    return s, H


# -------------------------------------------------- icon / breadboard
def _look_svg(gid, with_hits):
    body, H = _look_group(gid, with_hits)
    return "\n".join(
        ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="3.54mm" height="%smm" viewBox="-1.77 -1.77 3.54 %s">'
         % (f(H), f(H))] + body + ['</svg>', ''])


def icon_svg():
    """元件箱缩略图 = 元件真实外观 ✓（就这一张图，不加装饰 ✓ AGENTS §1 ✓）"""
    return _look_svg("breadboard", with_hits=False)


def breadboard_svg():
    """面包板视图 = 同一张外观 ✓ ＋ 每脚一组隐形命中框（Fritzing 靠它吸附到孔上 ✓）。
    ★ 脚落在 2.54 mm 网格上（y = 0 / 2.54 / 5.08 … ✓）⇒ 插进面包板对得上孔 ✓"""
    return _look_svg("breadboard", with_hits=True)


# ------------------------------------------------------------------- pcb
def pcb_svg():
    """1×N 通孔排针（俯视）：每脚一个 2.0 mm 环（孔 0.97 mm ✓）、**1 脚方环** ✓、
    丝印 = 本体轮廓框 + 1 脚斜撇 ✓（照官方 core 排针 ✓）。
    copper1 > copper0 嵌套 ⇒ 两个圆环**同时属于两层** ✓（照官方 core 排针 ✓）。"""
    H = N * PITCH + 1.0
    s = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="3.54mm" height="%smm" viewBox="-1.77 -1.77 3.54 %s">'
         % (f(H), f(H)),
         ' <g id="copper1">',
         '  <g id="copper0">']
    for i, y in enumerate(ys()):
        cid = "connector%dpad" % i
        if i == 0:                            # 1 脚 = 方环 ✓
            s.append('   <rect id="%s" connectorname="1" x="%s" y="%s" width="%s" height="%s" '
                     'fill="none" stroke="%s" stroke-width="%s"/>'
                     % (cid, f(-PAD_R), f(y - PAD_R), f(2 * PAD_R), f(2 * PAD_R), GOLD, f(PAD_STROKE)))
        else:
            s.append('   <circle id="%s" connectorname="%d" cx="0" cy="%s" r="%s" '
                     'fill="none" stroke="%s" stroke-width="%s"/>'
                     % (cid, i + 1, f(y), f(PAD_R), GOLD, f(PAD_STROKE)))
    s += ['  </g>', ' </g>', ' <g id="silkscreen">']
    # 本体轮廓框 ✓（到焊盘外缘净距 0.28 mm ✓ —— 官方 11 mil ✓）
    s.append('  <rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>'
             % (f(-BODY_W / 2), f(-BODY_MARGIN), f(BODY_W),
                f((N - 1) * PITCH + 2 * BODY_MARGIN), SILK, f(SILK_W)))
    # 1 脚斜撇 ✓（官方 (20,55)→(55,20) 单位 ⇒ 相对框角 (0.508,0.889) ✓）
    s.append('  <line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
             % (f(-BODY_W / 2), f(-BODY_MARGIN + 0.889),
                f(-BODY_W / 2 + 0.889), f(-BODY_MARGIN), SILK, f(SILK_W)))
    s += [' </g>', '</svg>', '']
    return "\n".join(s)


# ------------------------------------------------------------- schematic
def schematic_svg():
    """原理图符号：本体矩形（塑料条）+ N 条引脚线 ✓；脚号在引线**上方** ✓。
    几何照本库 `PH-2.0-3P-V` ✓（引线 2.54、本体 1.80 宽 × 上下各伸 1.10 ✓）。"""
    H = N * PITCH + 0.66                      # 照 PH-2.0-3P-V 的 3 脚 ⇒ 10.28 ✓ 同公式 ✓
    y_top = -SCH_BODY_MARGIN
    y_bot = (N - 1) * PITCH + SCH_BODY_MARGIN
    s = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="5.60mm" height="%smm" viewBox="0.00 %s 5.60 %s">'
         % (f(H), f(-SCH_BODY_MARGIN - 0.50), f(H)),
         ' <g id="schematic">',
         '  <polyline points="%s,%s %s,%s %s,%s %s,%s %s,%s" fill="none" stroke="#000000" '
         'stroke-width="0.30" stroke-linejoin="round"/>'
         % (f(SCH_BODY_X0), f(y_top), f(SCH_BODY_X0 + SCH_BODY_W), f(y_top),
            f(SCH_BODY_X0 + SCH_BODY_W), f(y_bot), f(SCH_BODY_X0), f(y_bot),
            f(SCH_BODY_X0), f(y_top))]
    for i, y in enumerate(ys()):
        s.append('  <line class="pin" id="connector%dpin" connectorname="%d" x1="0" y1="%s" x2="%s" y2="%s" '
                 'stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>'
                 % (i, i + 1, f(y), f(SCH_LEAD), f(y), PINCOL, f(PIN_W_SCH)))
        s.append('  <rect id="connector%dterminal" x="0" y="%s" width="0.0001" height="0.0001" '
                 'stroke="none" fill="none"/>' % (i, f(y)))
        s.append('  <text x="%s" y="%s" font-size="%s" fill="#8C8C8C" text-anchor="middle" '
                 'font-family="DroidSans">%d</text>'
                 % (f(SCH_LEAD / 2), f(y - 0.28), f(FN), i + 1))
    s += [' </g>', '</svg>', '']
    return "\n".join(s)


# ------------------------------------------------------------------- fzp
def fzp_xml():
    def conns():
        out = []
        for i in range(N):
            out.append(
                '  <connector id="connector%d" name="%d" type="male">\n'
                '   <description>pin %d</description>\n'
                '   <views>\n'
                '    <breadboardView><p layer="breadboard" svgId="connector%dpin" terminalId="connector%dterminal"/></breadboardView>\n'
                '    <schematicView><p layer="schematic" svgId="connector%dpin" terminalId="connector%dterminal"/></schematicView>\n'
                '    <pcbView>\n'
                '     <p layer="copper0" svgId="connector%dpad"/>\n'
                '     <p layer="copper1" svgId="connector%dpad"/>\n'
                '    </pcbView>\n'
                '   </views>\n'
                '  </connector>' % (i, i + 1, i + 1, i, i, i, i, i, i))
        return "\n".join(out)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<module fritzingVersion="0.9.9b" moduleId="%s">\n'
        ' <version>1</version>\n'
        ' <author>Shi Jinghai</author>\n'
        ' <title>PIN HEADER 1x%d</title>\n'
        ' <label>J</label>\n'
        ' <date>2026-10-13</date>\n'
        ' <tags><tag>header</tag><tag>pin header</tag><tag>male</tag><tag>2.54mm</tag>'
        '<tag>0.1in</tag><tag>through-hole</tag><tag>tht</tag></tags>\n'
        ' <properties>\n'
        '  <property name="family">pin header</property>\n'
        '  <property name="package">THT</property>\n'
        '  <property name="Pins">%d</property>\n'
        '  <property name="Pin Spacing">0.1in (2.54mm)</property>\n'
        '  <property name="Form">\u2642 (male)</property>\n'
        '  <property name="variant">- 1x%d</property>\n'
        '  <property name="part number">%s</property>\n'
        '  <property name="hole size">1.0mm</property>\n'
        ' </properties>\n'
        ' <description>1x%d male pin header, 2.54 mm (0.1 in) pitch, through-hole. '
        'Pads are 2.0 mm with a 1.0 mm hole; pin 1 is the square pad.</description>\n'
        ' <views>\n'
        '  <iconView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="icon"/>\n'
        '   </layers>\n'
        '  </iconView>\n'
        '  <breadboardView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="breadboard"/>\n'
        '   </layers>\n'
        '  </breadboardView>\n'
        '  <schematicView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="schematic"/>\n'
        '   </layers>\n'
        '  </schematicView>\n'
        '  <pcbView>\n'
        '   <layers image="%s">\n'
        '    <layer layerId="copper1"/>\n'
        '    <layer layerId="copper0"/>\n'
        '    <layer layerId="silkscreen"/>\n'
        '   </layers>\n'
        '  </pcbView>\n'
        ' </views>\n'
        ' <connectors>\n'
        '%s\n'
        ' </connectors>\n'
        '</module>\n'
    ) % (PART_ID, N, N, N, PART_ID, N, ICON_REF, BB_REF, SCHEM_REF, PCB_REF, conns())


def main():
    files = {ICON_SVG: icon_svg(), BB_SVG: breadboard_svg(), PCB_SVG: pcb_svg(),
             SCHEM_SVG: schematic_svg(), FZP: fzp_xml()}
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print("wrote", name)

    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", path)


if __name__ == "__main__":
    main()
