#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""生成 **LED-0603**（SMD 0603 发光二极管 ✓，两脚 ✓）

   用法：py -3.13 svg\LED-0603\gen_part.py            # 生成 4 个视图 svg + .fzp + 打 .fzpz ✓
         py -3.13 svg\LED-0603\gen_part.py --check    # 只报数字 ✓（不写文件 ✓）

-----------------------------------------------------------------------------
★ 为什么新建这一件 ✗（用户 2026-10-15 定 ✓）：
  Fritzing 自带的 `SparkFun-LED-LED-0603`（core ✓）**原理图画法有问题** ✗ ——
  它的两脚是**上下同轴的长线段**（local 各 7.2 ✓，中间留 7.2 的缝放三角形 ✓），
  而用户 2026-10-15 手改载板时实测：**在 Fritzing 里转它 180° 之后，挂在它脚上的
  两个线端落到了引脚线的“中点”** ✗（`(63,-126.0)`/`(63,-108.0)` —— 正是两条引脚线的
  中点 ✓），而不是端子（外端）✗ ⇒ Fritzing 自己就认不出 ⇒ 出“未布线”虚线 ✗
  ⇒ 用户定：**新建一件自绘原理图** ✓「其它图借鉴 sparkfun 的，原理图必须修改下，
  加上接线的端子」✓。
★ 本件的做法 ✓：
  · **icon / breadboard / pcb** = 逐字节沿用 Fritzing core 那三张 ✓（`svg/_assets/led0603_core_*.svg`
    ＋ `LICENSE-led0603_core.txt` ✓，CC-BY-SA 3.0 ✓ —— 仓规 §4「外部素材必须入库并随附许可」✓）；
  · **schematic = 本库自绘** ✓：**左右水平两脚** ✓、**端子显式画出**（`connectorNterminal` ✓
    落在引脚线的**外端** ✓，与 `Capacitor-*` 同一套写法 ✓）、发光箭头两条 ✓。
★ moduleId 的 hex 是**固定值** ✓（`md5(b"LED-0603_langhua_1")` ✓）—— **一旦发布就不许改** ✗：
  改了 Fritzing 会把它当成**另一个件** ✗（引用它的草图全部认不出 ✗）。
★ 后缀必须是 `LEDModuleID` ✓（出处 = Fritzing 源码 `src/items/partfactory.cpp` ✓：
  按后缀决定造哪个类 ✓ ⇒ 后缀不对就退化成通用件、属性面板整块只读 ✗，见仓规 §8）；
  该后缀对应属性 `current`（`resources/properties.xml` ✓，可编辑 ✓）。
★ 引脚名 `A`（阳极）/ `C`（阴极）**照 SparkFun 原厂口径** ✓（仓规 §5「命名一律尊重原厂」✓）；
  原理图里的**引脚编号文字**仍写 1 / 2 ✓（= connector0 / connector1 ✓）。
-----------------------------------------------------------------------------
"""
import hashlib
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # = 库根 ✓
FZPZ = os.path.join(ROOT, "fzpz")
ASSETS = os.path.join(ROOT, "svg", "_assets")
OUT_NAME = "LED-0603"

MOD = "LED_0603_07745ffa1ddf4609b20eff3247d4acf8_1-LEDModuleID"
TITLE = "LED 0603"
LABEL = "LED"
PACKAGE = "0603 [SMD]"
PARTNUM = "LED-0603"
DATE = "Wed Oct 15 2026"
AUTHOR = "Shi Jinghai"

# ★ 原理图符号的几何（mm ✓；画布 7.62 × 6.35 mm = 0.3 × 0.25 in ✓）
AXIS = 3.175          # 引脚所在的水平中线 ✓
PIN = 2.54            # 引脚线长度 ✓
TRI = (2.54, 5.08)    # 三角形从 x=2.54 指到 x=5.08 ✓（阳极在左、阴极在右 ✓）
HALF = 1.27           # 三角形半高 ✓（上下各 1.27 ✓）
FONT = 0.881944       # 引脚号字号（与 `Capacitor-*` 同一值 ✓）


def arrow(x1, y1, x2, y2, w=0.1524, head=0.62):
    r"""发光箭头 ✓：杆 + 三角头（头按方向算 ✓，不手凑坐标 ✗）"""
    dx, dy = x2 - x1, y2 - y1
    ln = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / ln, dy / ln
    bx, by = x2 - ux * head, y2 - uy * head
    hw = head * 0.45
    pts = "%.4f,%.4f %.4f,%.4f %.4f,%.4f" % (x2, y2,
                                              bx - uy * hw, by + ux * hw,
                                              bx + uy * hw, by - ux * hw)
    return ('<line x1="%.4f" y1="%.4f" x2="%.4f" y2="%.4f" stroke="#000000" stroke-width="%.4f" '
            'stroke-linecap="round"/>' % (x1, y1, x2, y2, w)
            + '<polygon points="%s" fill="#000000" stroke="none"/>' % pts)


def schematic_svg():
    r"""本库自绘的 LED 原理图符号 ✓（**端子显式** ✓、左右水平两脚 ✓）"""
    L = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
         '<!-- Created with Fritzing (http://www.fritzing.org/) -->',
         '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" '
         'x="0in" y="0in" width="0.3in" height="0.25in" viewBox="0 0 7.62 6.35">',
         '<g id="schematic">']
    # ① 两条引脚线（左 = A/1 ✓、右 = C/2 ✓）＋ **端子在各自己的外端** ✓
    for cid, conn, x0, x1 in (("connector0", "A", 2.54, 0.0), ("connector1", "C", 5.08, 7.62)):
        L.append('<line class="pin" id="%spin" connectorname="%s" x1="%.4f" y1="%.4f" x2="%.4f" '
                 'y2="%.4f" stroke="#787878" stroke-width="0.246944" stroke-linecap="round"/>'
                 % (cid, conn, x0, AXIS, x1, AXIS))
        L.append('<rect class="terminal" id="%sterminal" x="%.4f" y="%.4f" width="0.0001" '
                 'height="0.0001" stroke="none" stroke-width="0" fill="none"/>'
                 % (cid, min(x0, x1), AXIS))
    # ② LED 本体：三角形（指向阴极 ✓）＋ 阴极横杠 ✓＋两条发光箭头 ✓
    L.append('<polygon class="other" points="%.4f,%.4f %.4f,%.4f %.4f,%.4f" fill="#000000" '
             'stroke="none"/>' % (TRI[0], AXIS - HALF, TRI[0], AXIS + HALF, TRI[1], AXIS))
    L.append('<line class="other" x1="%.4f" y1="%.4f" x2="%.4f" y2="%.4f" stroke="#000000" '
             'stroke-width="0.3048" stroke-linecap="round"/>'
             % (TRI[1], AXIS - HALF, TRI[1], AXIS + HALF))
    L.append(arrow(5.85, 1.45, 6.85, 0.45))
    L.append(arrow(6.85, 2.05, 7.45, 1.45))
    # ③ 引脚号（灰 ✓ 在引线上方 ✓ —— 摆在 x=1.27 / 6.35，避开发光箭头 ✓）
    for x, n in ((1.27, "1"), (6.35, "2")):
        L.append('<text class="text" font-family="\'Droid Sans\'" stroke="none" stroke-width="0" '
                 'fill="#8c8c8c" font-size="%.6f" x="%.4f" y="2.75" text-anchor="middle">%s</text>'
                 % (FONT, x, n))
    L += ['</g>', '</svg>']
    return "\n".join(L) + "\n"


def fzp_text():
    def view(v, stem):
        return ('  <%sView>\n   <layers image="%s/%s_%s.svg">\n    <layer layerId="%s"/>\n'
                '   </layers>\n  </%sView>' % (v, v, MOD, v, LAYER_OF[v], v))
    L = ['<?xml version=\'1.0\' encoding=\'UTF-8\'?>',
         '<module fritzingVersion="1.0.3" moduleId="%s">' % MOD,
         ' <version>4</version>', ' <title>%s</title>' % TITLE, ' <label>%s</label>' % LABEL,
         ' <date>%s</date>' % DATE, ' <author>%s</author>' % AUTHOR,
         ' <tags>', '  <tag>LED</tag>', '  <tag>0603</tag>', '  <tag>SMD</tag>',
         '  <tag>fritzing parts of Langhua</tag>', ' </tags>',
         ' <properties>',
         '  <property name="family">LED</property>',
         '  <property name="package">%s</property>' % PACKAGE,
         '  <property name="part number" showInLabel="yes">%s</property>' % PARTNUM,
         '  <property name="current"></property>',
         ' </properties>',
         ' <taxonomy>discreteParts.led</taxonomy>',
         ' <description>A generic 0603 LED</description>',
         ' <spice>',
         '  <line>D{instanceTitle} {net connector0} {net connector1} LED</line>',
         ' </spice>',
         ' <views>']
    L += [view("icon", MOD), view("breadboard", MOD), view("schematic", MOD), view("pcb", MOD)]
    L += [' </views>', ' <connectors>']
    for cid, nm, pad in (("connector0", "A", "connector0pad"), ("connector1", "C", "connector1pad")):
        L += ['  <connector id="%s" name="%s" type="male">' % (cid, nm),
              '   <description>%s</description>' % nm,
              '   <views>',
              '    <breadboardView>\n     <p layer="breadboard" svgId="%spin"/>\n    </breadboardView>' % cid,
              '    <schematicView>\n     <p layer="schematic" svgId="%spin" '
              'terminalId="%sterminal"/>\n    </schematicView>' % (cid, cid),
              '    <pcbView>\n     <p layer="copper1" svgId="%s"/>\n    </pcbView>' % pad,
              '   </views>', '  </connector>']
    L += [' </connectors>', '</module>']
    return "\n".join(L) + "\n"


LAYER_OF = {"icon": "icon", "breadboard": "breadboard", "schematic": "schematic",
            "pcb": "copper1"}

JOBS = [("icon", "led0603_core_icon.svg"), ("breadboard", "led0603_core_breadboard.svg"),
        ("pcb", "led0603_core_pcb.svg")]


def build():
    check = "--check" in sys.argv
    files = {}
    for v, asset in JOBS:                       # ① 三张沿用素材（逐字节 ✓）
        p = os.path.join(ASSETS, asset)
        if not os.path.exists(p):
            raise SystemExit("✗ 素材缺 %s ✗（见 svg/_assets/LICENSE-led0603_core.txt ✓）" % p)
        files["svg.%s.%s_%s.svg" % (v, MOD, v)] = open(p, encoding="utf-8").read()
    files["svg.schematic.%s_schematic.svg" % MOD] = schematic_svg()   # ② 原理图自绘 ✓
    files["part.%s.fzp" % MOD] = fzp_text()
    print("== %s（moduleId %s ✓）==" % (OUT_NAME, MOD))
    for n in sorted(files):
        print("   %-72s %6d B" % (n, len(files[n].encode("utf-8"))))
    print("   md5(b\"LED-0603_langhua_1\") = %s ✓（moduleId 里的 hex ✓，固定不许改 ✗）"
          % hashlib.md5(b"LED-0603_langhua_1").hexdigest())
    if check:
        print("   --check ⇒ 不写文件 ✓")
        return files
    for n, t in files.items():
        with open(os.path.join(HERE, n), "w", encoding="utf-8", newline="\n") as f:
            f.write(t)
    # ③ 打 .fzpz（平铺 ✓ + 固定时间戳 + LF ✓ ⇒ 可重复 ✓，见仓规 §14 ✓）
    os.makedirs(FZPZ, exist_ok=True)
    zp = os.path.join(FZPZ, OUT_NAME + ".fzpz")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(files):
            zi = zipfile.ZipInfo(n, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, files[n].encode("utf-8"))
    print("   ⇒ 写入 %s/ 4+1 个文件 ✓；打包 %s ✓" % (OUT_NAME, zp))
    return files


if __name__ == "__main__":
    build()
