#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — LD1117 1A 低压差线性稳压器（SOT-223）Fritzing 元件生成器。
=========================================================================
数据来源：`D:\Downloads\LD1117.pdf`（UMW LD1117 手册，Mar.2025）
  · 第 1 页 "Pinning information"：TO-252 / SOT-223 / SOT-89 三种封装的引脚都是
      **1 = ADJ/GND、2 = VOUT（含背面散热片）、3 = VIN**；
  · 第 10 页 "SOT-223 Package Outline Dimensions" + SOT-223(TO-261) 通用值：
      本体 **6.5(D) × 3.5(E)**、引脚节距 **e = 2.3**、脚宽 **B = 0.7**（0.6–0.85）、
      含脚总跨距 **H = 7.3**（⇒ 每侧伸出 ≈1.9）、背面散热片（tab）≈ **3.6** 宽；
  · 第 13 页订货/丝印：丝印为 `1117-xx`（xx = 电压档），SOT-223 = UMW LD1117-xx，
      板上那颗 U1 是 **1117-3.3**（固定 3.3V）。
  · 1A、dropout 典型 1.2V@1A、内置限流与过温保护；固定档精度 2%、可调档 1.5%。

元件模型（用户 2026-09-15 定的三件套之一；板上 U1 要复用它的 icon）：
  - icon / 原理图 / PCB = **芯片本身**；面包板 = **绿色 SOT-223 转接板**（AGENTS §3b）。

进度：
  [x] 1. icon（SOT-223 顶视图；**不画 pin1 圆点** —— 一边三脚一边散热片，方向一目了然）
  [x] 2. breadboard（绿色转接板：三脚一排，都落 2.54 网格；散热片不引出）
  [x] 3. schematic（三脚符号：左 VIN / 右 VOUT / 下 ADJ-GND，按 AGENTS §5 矩形规则）
  [x] 4. pcb（SOT-223：3 脚盘 e=2.3 + 散热片盘，焊盘不与丝印重叠）
  [x] 5. part.LD1117.fzp + 打包 fzpz
"""
import os
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "LD1117"
TITLE = "LD1117 1A LDO Regulator (SOT-223)"
LABEL = "U"
PACKAGE = "SOT-223"
FAMILY = "LDO Regulator"
FZPZ = "LD1117.fzpz"
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID

# 颜色（与仓库其它芯片 icon 一致）
BODY = "#303030"
LEAD = "#c0c0c0"
TXT = "#ffffff"

# ---- 几何（mm，1:1 实物，见文件头数据来源）----------------------------------
BODY_W = 6.5          # 本体长边（沿引脚排列方向，x）
BODY_H = 3.5          # 本体短边（沿引脚伸出方向，y）
PITCH = 2.3           # 三个引脚的节距
LEAD_W = 0.7          # 脚宽
LEAD_L = 1.9          # 脚 / 散热片伸出长度（(7.3 − 3.5) / 2）
TAB_W = 3.6           # 散热片宽（与 2 脚同网 = VOUT）
ICON_MARK = "1117-3.3"      # 实物丝印（手册 p13：1117-xx；板上那颗是 3.3V 档）

# 引脚（手册第 1 页）
PINS = {1: "ADJ/GND", 2: "VOUT", 3: "VIN"}

U = 39.37             # 面包板视图里 1mm 对应的内部单位（100 单位 = 2.54mm）


def _icon_shapes(s=1.0, dx=0.0, dy=0.0):
    """SOT-223 顶视图形（本体 + 三脚 + 散热片 + 丝印），返回元素列表。
    s=1.0 时坐标就是 mm（icon 视图直接用）；面包板视图传 s=U、dx/dy 平移，
    **把坐标烘成绝对值**（不依赖 SVG 变换，避免 Fritzing 解析变换时错位）。"""
    xs = [BODY_W / 2 + (i - 1) * PITCH for i in range(3)]     # 三脚中心（中间脚居中）
    bx0, by0 = dx, dy + LEAD_L * s
    out = []
    for x in xs:                                              # 三只脚（下边）
        out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="none"/>\n'
                   % (dx + (x - LEAD_W / 2) * s, dy + (LEAD_L + BODY_H) * s,
                      LEAD_W * s, LEAD_L * s, LEAD))
    out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="none"/>\n'
               % (dx + (BODY_W / 2 - TAB_W / 2) * s, dy, TAB_W * s, LEAD_L * s, LEAD))   # 散热片
    out.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="none"/>\n'
               % (bx0, by0, BODY_W * s, BODY_H * s, BODY))                                # 本体
    out.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-family="DroidSans" fill="%s" '
               'text-anchor="middle" stroke="none">%s</text>\n'
               % (dx + BODY_W / 2 * s, dy + (LEAD_L + BODY_H / 2) * s + 0.32 * s,
                  0.9 * s, TXT, ICON_MARK))
    return out


def icon_svg():
    """SOT-223 顶视图 icon。**不画 pin1 圆点**（用户 2026-09-15：一边三脚、一边散热片，
    方向一目了然，无需标注）。"""
    TOT_W, TOT_H = BODY_W, BODY_H + 2 * LEAD_L        # 6.5 × 7.3
    L = ['<?xml version="1.0" encoding="UTF-8"?>\n',
         '<!-- LD1117 SOT-223 -->\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" '
         'viewBox="0 0 %.1f %.1f">\n' % (TOT_W, TOT_H, TOT_W, TOT_H),
         '  <g id="icon">\n']
    L += _icon_shapes(1.0, 0.0, 0.0)
    L += ['  </g>\n', '</svg>\n']
    return "".join(L)


# ---------------------------------------------------------------- breadboard
def gen_breadboard_svg():
    """面包板 = 绿色 SOT-223 转接板（AGENTS §3b）：
      · 一排 3 针 = 1(ADJ/GND) / 2(VOUT) / 3(VIN)，中心 x=100/200/300（2.54 网格）；
      · **散热片不引出**（用户 2026-09-15）：不画上排针、不写 `VOUT` 文字 ——
        散热片是元件本体的一部分，转接板上只按三个引脚出针；
      · 芯片 icon 1:1 居中于 **(200, 230)**（用户 2026-09-15：再往上一些）——
        含脚总高 7.3mm = 287 单位，上净空 86 单位、到焊盘顶也是 87 单位（≈ 2.2mm 上下都留了白）。
        焊盘行在 y=500（不动，必须在 100 单位整数倍上）；
      · 焊盘 = 2mm 圆盘 + 0.97mm 针孔（§3b）；管脚数字逆时针转 90°、居中于焊盘列、DroidSans。
    板 = 400×600 单位 = 10.16×15.24mm（满足 2.54 网格 + 容得下元件，面积取最小）。"""
    pad_r, hole_r = 1.0 * U, 0.485 * U
    bx1, by1 = 400, 600
    y_bot = 500
    cx, cy = 200, 230
    s = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %d %d">\n' % (bx1 / 100 * 2.54, by1 / 100 * 2.54, bx1, by1),
         ' <g id="breadboard">\n',
         # ★★ 板边相位＝**半格**（AGENTS §3b：转接板不许影响板外孔的插拔 ✓，2026-09-27 ✓）：
         #   针脚在 x=100/200/300 ✓、y=500 ✓ ⇒ 旧框 (0,0,bx1,by1) ✗
         #   ⇒ 四条边离针脚都是 100 的整数倍 ⇒ 全压在孔线上 ✗
         #   新：四周各让 50 ✓（宽 bx1-100、高 by1-100）⇒ 板边落在两排孔正中 ✓；针脚不动 ✓。
         '  <rect x="50" y="50" width="%d" height="%d" fill="#00aa44" stroke="#00772f" '
         'stroke-width="5"/>\n' % (bx1 - 100, by1 - 100)]
    # 芯片（居中；icon 的 (0,0) = 芯片左上角 → 平移到 (cx-3.25mm, cy-3.65mm)）
    s += _icon_shapes(U, cx - BODY_W / 2 * U, cy - (BODY_H / 2 + LEAD_L) * U)
    # 下排三脚 + 数字（散热片不引出：见函数说明）
    for i, (x, cn) in enumerate(((100, 0), (200, 1), (300, 2))):
        s.append('  <circle id="connector%dpin" connectorname="%s" cx="%d" cy="%d" r="%.1f" '
                 'fill="#d4af37" stroke="#8a6d00" stroke-width="4"/>\n'
                 % (cn, PINS[i + 1], x, y_bot, pad_r))
        s.append('  <circle cx="%d" cy="%d" r="%.1f" fill="#2b2b2b"/>\n' % (x, y_bot, hole_r))
        s.append('  <text x="%d" y="450" font-size="60" fill="#ffffff" text-anchor="middle" '
                 'dominant-baseline="central" font-family="DroidSans" '
                 'transform="rotate(-90 %d 450)">%d</text>\n' % (x, x, i + 1))
    s += [' </g>\n', '</svg>\n']
    return "".join(s)


# ---------------------------------------------------------------- schematic
def gen_schematic_svg():
    """矩形封装符号（三脚 LDO）。按 AGENTS.md §5 矩形原理图规则：
      左 = 3 VIN、右 = 2 VOUT、下 = 1 ADJ/GND（下引脚的数字在引脚左侧、rotate(270)，从下至上）。
      名 / 数字 / 引线同色（黑）、同字号 FN=35；名在框内、与边框保持一个字符间距。"""
    WIRE, FN, CH = 130, 35, 35
    BX0, BY0, BW, BH = 300, 200, 700, 400
    BX1, BY1 = BX0 + BW, BY0 + BH
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.6fin" height="%.6fin" '
         'viewBox="%d %d %d %d">\n'
         % ((BW + 2 * WIRE + 10) / 1000.0, (BH + 2 * WIRE + 10) / 1000.0,
            BX0 - WIRE - 5, BY0 - WIRE - 5, BW + 2 * WIRE + 10, BH + 2 * WIRE + 10),
         ' <g id="schematic">\n',
         '  <rect class="interior rect" x="%d" y="%d" width="%d" height="%d" fill="#FFFFFF" '
         'stroke="#787878" stroke-width="5"/>\n' % (BX0, BY0, BW, BH)]
    y = BY0 + 160                                     # 左右引脚共用一行
    # 左：3 VIN
    L.append('  <line class="pin" id="connector2pin" connectorname="VIN" x1="%d" y1="%d" x2="%d" y2="%d" '
             'stroke="#000000" stroke-width="5"/>\n' % (BX0, y, BX0 - WIRE, y))
    L.append('  <rect id="connector2terminal" x="%d" y="%d" width="22" height="22" fill="none"/>\n'
             % (BX0 - WIRE, y - 11))
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans">3</text>\n' % (BX0 - WIRE // 2, y - 24, FN))
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="start" '
             'font-family="DroidSans">VIN</text>\n' % (BX0 + CH, y + round(FN * 0.35), FN))
    # 右：2 VOUT
    L.append('  <line class="pin" id="connector1pin" connectorname="VOUT" x1="%d" y1="%d" x2="%d" y2="%d" '
             'stroke="#000000" stroke-width="5"/>\n' % (BX1, y, BX1 + WIRE, y))
    L.append('  <rect id="connector1terminal" x="%d" y="%d" width="22" height="22" fill="none"/>\n'
             % (BX1 + WIRE, y - 11))
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans">2</text>\n' % (BX1 + WIRE // 2, y - 24, FN))
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="end" '
             'font-family="DroidSans">VOUT</text>\n' % (BX1 - CH, y + round(FN * 0.35), FN))
    # 下：1 ADJ/GND（数字在引脚左侧、rotate(270)；名在框内竖排、贴底边一个字符）
    x = BX0 + BW // 2
    L.append('  <line class="pin" id="connector0pin" connectorname="ADJ/GND" x1="%d" y1="%d" x2="%d" y2="%d" '
             'stroke="#000000" stroke-width="5"/>\n' % (x, BY1, x, BY1 + WIRE))
    L.append('  <rect id="connector0terminal" x="%d" y="%d" width="22" height="22" fill="none"/>\n'
             % (x - 11, BY1 + WIRE))
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans" transform="rotate(270 %d %d)">1</text>\n'
             % (x - FN // 2 - 10, BY1 + WIRE // 2, FN, x - FN // 2 - 10, BY1 + WIRE // 2))
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans" transform="rotate(270 %d %d)">ADJ/GND</text>\n'
             % (x, BY1 - CH - FN // 2, FN, x, BY1 - CH - FN // 2))
    # 器件名（框内偏上，避开竖排的 ADJ/GND）
    L.append('  <text x="%d" y="%d" font-size="79" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans">LD1117</text>\n' % (BX0 + BW // 2, BY0 + 130))
    L += [' </g>\n', '</svg>\n']
    return "".join(L)


# ---------------------------------------------------------------------- pcb
def gen_pcb_svg():
    """PCB = SOT-223 真实焊盘：三只脚盘 1.0×2.0（e=2.3）+ 散热片盘 3.8×2.3。
    脚盘中心 y=+3.2（本体下方）、散热片盘中心 y=-3.0（本体上方）；丝印本体 6.5×3.5。
    不画 pin1 圆点（同 icon 的理由：散热片盘在对面，方向自明）。坐标 mm，viewBox 贴合。"""
    pw, pl, row = 1.0, 2.0, 3.2
    tw, th, tab_y = 3.8, 2.3, -3.0
    xs = [(i - 1) * PITCH for i in range(3)]          # -2.3, 0, +2.3
    pads = []
    for i, x in enumerate(xs):
        pads.append('<rect id="connector%dpad" x="%.3f" y="%.3f" width="%.2f" height="%.2f" '
                    'fill="#F7BD13" stroke="none" connectorname="%s"/>'
                    % (i, x - pw / 2, row - pl / 2, pw, pl, PINS[i + 1]))
    pads.append('<rect id="connector3pad" x="%.3f" y="%.3f" width="%.2f" height="%.2f" '
                'fill="#F7BD13" stroke="none" connectorname="VOUT"/>'
                % (-tw / 2, tab_y - th / 2, tw, th))
    silk = ['<rect x="%.3f" y="%.3f" width="%.2f" height="%.2f" fill="none" stroke="#f0f0f0" '
            'stroke-width="0.15"/>' % (-BODY_W / 2, -BODY_H / 2, BODY_W, BODY_H)]
    inner = ("\n".join(pads) + "\n<g id=\"copper0\"/>\n  </g>\n  <g id=\"silkscreen\">\n"
             + "\n".join(silk))
    SX, SY, M = BODY_W / 2, max(row + pl / 2, -(tab_y - th / 2)), 0.15
    return ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- LD1117 SOT-223 -->\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
            'viewBox="%.2f %.2f %.2f %.2f">\n'
            % (2 * (SX + M), 2 * (SY + M), -(SX + M), -(SY + M), 2 * (SX + M), 2 * (SY + M))
            + ' <g id="copper1">\n' + inner + '\n </g>\n</svg>\n')


# --------------------------------------------------------------------- .fzp
def gen_fzp():
    """4 个 connector：0 = 1 ADJ/GND、1 = 2 VOUT、2 = 3 VIN（三视图全有）；
    3 = 散热片 pad（**只有 PCB 视图** —— 面包板不引出，见 gen_breadboard_svg 说明），
    与 1(VOUT) **同网** → 用 <buses> 互联（AGENTS §5：多焊盘同网络 = 每个 pad 独立
    connector + buses 互联）。"""
    conns = []
    for cn, name, views in ((0, PINS[1], ("bb", "sch", "pcb")),
                            (1, PINS[2], ("bb", "sch", "pcb")),
                            (2, PINS[3], ("bb", "sch", "pcb")),
                            (3, "VOUT (tab)", ("pcb",))):
        v = []
        if "bb" in views:
            v.append('    <breadboardView>\n     <p layer="breadboard" svgId="connector%dpin"/>\n'
                     '    </breadboardView>\n' % cn)
        if "sch" in views:
            v.append('    <schematicView>\n     <p layer="schematic" svgId="connector%dpin" '
                     'terminalId="connector%dterminal"/>\n    </schematicView>\n' % (cn, cn))
        if "pcb" in views:
            v.append('    <pcbView>\n     <p layer="copper1" svgId="connector%dpad"/>\n'
                     '    </pcbView>\n' % cn)
        conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                     '   <description>%s</description>\n   <views>\n' % (cn, name, name)
                     + "".join(v) + '   </views>\n  </connector>')
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<module fritzingVersion="1.0.3" moduleId="%s">\n'
            ' <version>4</version>\n <date>2026-09-15</date>\n'
            ' <label>%s</label>\n <author>fritzing-parts-langhua</author>\n'
            ' <title>%s</title>\n <tags>\n  <tag>%s</tag>\n  <tag>%s</tag>\n </tags>\n'
            ' <properties>\n  <property name="package">%s</property>\n'
            '  <property name="family">%s</property>\n'
            '  <property name="part number">%s</property>\n </properties>\n'
            ' <views>\n  <breadboardView>\n   <layers image="breadboard/%s_breadboard.svg">\n'
            '    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            '  <schematicView>\n   <layers image="schematic/%s_schematic.svg">\n'
            '    <layer layerId="schematic"/>\n   </layers>\n  </schematicView>\n'
            '  <pcbView>\n   <layers image="pcb/%s_pcb.svg">\n'
            '    <layer layerId="copper1"/>\n    <layer layerId="silkscreen"/>\n   </layers>\n  </pcbView>\n'
            '  <iconView>\n   <layers image="icon/%s_icon.svg">\n'
            '    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n </views>\n'
            ' <buses>\n  <bus id="VOUT">\n   <nodeMember connectorId="connector1"/>\n'
            '   <nodeMember connectorId="connector3"/>\n  </bus>\n </buses>\n'
            ' <connectors>\n') % (PART_ID, LABEL, TITLE, LABEL, PACKAGE, PACKAGE, FAMILY,
                                  PART_ID, PART_ID, PART_ID, PART_ID, PART_ID)
    return head + "\n".join(conns) + '\n </connectors>\n</module>\n'


def main():
    files = {
        "schematic": gen_schematic_svg(),
        "breadboard": gen_breadboard_svg(),
        "pcb": gen_pcb_svg(),
        "icon": icon_svg(),
    }
    for view, content in files.items():
        name = "svg.%s.%s_%s.svg" % (view, PART_ID, view)
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)

    fzp_name = "part.%s.fzp" % PART_ID
    with open(os.path.join(OUT_DIR, fzp_name), "w", encoding="utf-8") as f:
        f.write(gen_fzp())
    print("wrote", fzp_name)

    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(OUT_DIR, fzp_name), arcname=fzp_name)
        for name in (ICON_SVG, SCHEM_SVG, PCB_SVG, BB_SVG):
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
