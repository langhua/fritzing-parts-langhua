#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_part.py — 生成 Fritzing 自定义元件 **WCH-LinkE**（WCH 官方 USB 调试器/烧录器，Type-C 版）。

★★ 两个视图（2026-10-18 用户定 ✓）
  · **面包板** = 用户手改版 `svg.breadboard.WCH-LinkE_breadboard_byHand.svg` 逐字导出 ✅
  · **icon**     = 同一张图、**去掉丝印小字**（元件箱里几十像素，小字只会糊成一团 ✗）
  · ✗ **不带原理图 / PCB** —— 用户原话：「建议这个元件不带 pcb 和原理图」✓
    理由：调试器**不会被焊到板上** ⇒ 有 pcb 视图反而会让人把它摆进板里 ✗。
    （`fzp_check` 对此开了**工具类件**的例外，见该文件 `TOOL_FAMILIES` ✓。）

流程（改图 = 改手工版，别改本文件 ✗）：
  ① Inkscape 改 `svg.breadboard.WCH-LinkE_breadboard_byHand.svg`
  ② `py -3.13 tools\\byhand_export.py svg\\WCH-LinkE` → `byHand_tables.py`（纯数据，入库）
  ③ `py -3.13 svg\\WCH-LinkE\\gen_part.py`

引脚（出处 = 用户 2026-10-18 口述 + 实物丝印 —— **对手上这块是权威** ✓）
  · 上层 5 根：`RX` / `TX` / `GND` / `3V3` / `RST`
  · 下层 5 根：`CLK` / `DIO` / `GND` / `3V3` / `5V0`
  ⇒ 烧录只用 **下层 `CLK`(SWCLK) / `DIO`(SWDIO) / `GND`**；`3V3` 不要接（板子自己供电 ✓）。
  ⚠ 旧版手册 `WCH-LinkSCH.PDF` 的 `JP1`（TDO/TDI/5V 那套）**不是这块板** ✗，不作依据。
机械：板 42 × 16.5 × 1.6 mm、脚距 2.54、排针沿宽边居中（用户卡尺实测 ✓）。
"""
import os
import sys
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, OUT_DIR)
import byHand_tables as H                                            # noqa: E402

PART_ID = "WCH-LinkE"
FZPZ = "WCH-LinkE.fzpz"

# ── 引脚表： (connector id, 层, 丝印名, 说明) ────────────────────────────────
PINS = [
    (0, "上", "RX",  "串口 RX"),
    (1, "上", "TX",  "串口 TX"),
    (2, "上", "GND", "地"),
    (3, "上", "3V3", "3.3V"),
    (4, "上", "RST", "复位"),
    (5, "下", "CLK", "SWD 时钟 = SWCLK/TCK ★ 接载板 J3.4(SWCLK)"),
    (6, "下", "DIO", "SWD 数据 = SWDIO/TMS ★ 接载板 J3.3(SWDIO)"),
    (7, "下", "GND", "地 ★ 接载板 J3.2(GND)"),
    (8, "下", "3V3", "3.3V（接载板时**不要接**：板子自己供电）"),
    (9, "下", "5V0", "5V"),
]

# 同网络的多个焊盘 = 各自独立 connector + `<buses>` 互联（AGENTS §5 ✓）；
# `fzp_check` ⑦ 要求「同名必同总线」⇒ 两个 GND、两个 3V3 各进一条总线 ✓。
BUSES = [("GND", [2, 7]), ("3V3", [3, 8])]

TITLE = "WCH-LinkE Debugger/Programmer (USB Type-C, SWD/JTAG/UART)"
LABEL = "LINK"
PACKAGE = "42 x 16.5 x 1.6 mm, USB Type-C, 2x5 2.54mm right-angle header"
FAMILY = "Programmer"

SVG_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- WCH-LinkE (Type-C rev.) -->\n'


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _sw(v):
    """stroke-width：手工版里可能是字符串 "None"/"0.0" ⇒ 别把 None 写进 svg ✗"""
    if v in (None, "None", "none", "", 0, 0.0):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f == 0.0 else f


def shapes_svg(with_text=True):
    """把 byHand_tables 的 SHAPES / TEXTS 逐条变成 svg（**顺序 = 叠放次序** ✓）"""
    L = []
    for s in H.SHAPES:
        k = s[0]
        if k == "rect":
            # ★★ `rot` **不要用** ✗ —— 导出的 x/y/w/h 已经是**旋转后的包围盒** ✓
            #   （出处 = 同库 `svg/BQ25570/gen_part.py:100` 的 `_rot：bbox 已烘焙，不用` ✓）。
            #   我 2026-10-18 先按“绕中心再转一次”写 ✗ ⇒ Type-C 壳与两条白条变成竖板、
            #   把板子左下角盖住 ⇒ 用户截图一眼看出「与手改版不一致」✗。
            _k, x, y, w, h, fill, _rot, stroke, sw = s[:9]
            rx = s[9] if len(s) > 9 else None
            op = s[10] if len(s) > 10 else None
            rxs = (' rx="%g" ry="%g"' % (rx, rx)) if rx else ""
            sws = (' stroke-width="%g"' % _sw(sw)) if _sw(sw) else ""
            ops = (' opacity="%g"' % op) if op not in (None, "None", "") else ""
            L.append('    <rect x="%g" y="%g" width="%g" height="%g" fill="%s" '
                     'stroke="%s"%s%s%s/>\n'
                     % (x, y, w, h, fill, stroke or "none", sws, rxs, ops))
        elif k == "circle":
            _k, cx, cy, r, fill, stroke, sw = s[:7]
            sws = (' stroke-width="%g"' % _sw(sw)) if _sw(sw) else ""
            L.append('    <circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s"%s/>\n'
                     % (cx, cy, r, fill, stroke or "none", sws))
        elif k == "pad":
            _k, pid, net, cx, cy = s[:5]
            L.append('    <circle id="%s" connectorname="%s" cx="%g" cy="%g" r="%g" '
                     'fill="%s" stroke="%s"/>\n'
                     % (pid, esc(net), cx, cy, H.PAD_R, H.PAD_FILL, H.PAD_EDGE or "none"))
        elif k == "line":
            _k, x1, y1, x2, y2, stroke, sw = s[:7]
            sws = (' stroke-width="%g"' % _sw(sw)) if _sw(sw) else ""
            L.append('    <line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s"%s/>\n'
                     % (x1, y1, x2, y2, stroke or "none", sws))
        elif k == "path":
            _k, d, tf, fill, stroke, sw = s[:6]
            tf = "" if tf in (None, "None", "") else ' transform="%s"' % tf
            sws = (' stroke-width="%s"' % sw) if sw not in (None, "None", "") else ""
            L.append('    <path d="%s"%s fill="%s" stroke="%s"%s/>\n'
                     % (d, tf, fill or "none", stroke or "none", sws))
        else:
            raise SystemExit("✗ byHand_tables.SHAPES 里有认不出的图元：%r" % (k,))
    if not with_text:
        return L
    for t in H.TEXTS:
        txt, x, y, fs, anchor, rot, fill = t[:7]
        wt = t[7] if len(t) > 7 else None
        at = ""
        if anchor not in (None, "None", ""):
            at += ' text-anchor="%s"' % anchor
        if fill not in (None, "None", ""):
            at += ' fill="%s"' % fill
        if wt not in (None, "None", ""):
            at += ' font-weight="%s"' % wt
        tf = (' transform="rotate(%g %g %g)"' % (rot, x, y)) if rot else ""
        L.append('    <text x="%g" y="%g" font-size="%g"%s font-family="DroidSans"%s>%s</text>\n'
                 % (x, y, fs, at, tf, esc(txt)))
    return L


def _svg(inner, layer="breadboard"):
    vb = H.DOC_VIEWBOX
    return (SVG_HDR +
            '<svg xmlns="http://www.w3.org/2000/svg" width="%.6gmm" height="%.6gmm" '
            'viewBox="%.4f %.4f %.4f %.4f">\n' % (H.DOC_MM_W, H.DOC_MM_H, vb[0], vb[1], vb[2], vb[3])
            + '  <g id="%s">\n' % layer + "".join(inner) + '  </g>\n</svg>\n')


def gen_breadboard_svg():
    return _svg(shapes_svg(True))


def gen_icon_svg():
    """icon = 同一张手工图，**去掉丝印小字**（元件箱里几十像素，小字只会糊成一团 ✗）。"""
    return _svg(shapes_svg(False), layer="icon")


# ----------------------------------------------------------------------- .fzp
def gen_fzp():
    conns = []
    for cn, layer, nm, desc in PINS:
        conns.append(
            f'  <connector id="connector{cn}" name="{esc(nm)}" type="male">\n'
            f'   <description>{esc(layer)}层 {esc(nm)} = {esc(desc)}</description>\n'
            f'   <views>\n'
            f'    <breadboardView>\n     <p layer="breadboard" svgId="connector{cn}pin"/>\n'
            f'    </breadboardView>\n'
            f'   </views>\n'
            f'  </connector>')
    buses = []
    for bid, ids in BUSES:
        nodes = "\n".join(f'   <nodeMember connectorId="connector{i}"/>' for i in ids)
        buses.append(f'  <bus id="{bid}">\n{nodes}\n  </bus>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<module fritzingVersion="1.0.3" moduleId="{PART_ID}">\n'
            f' <version>3</version>\n <date>2026-10-18</date>\n'
            f' <label>{LABEL}</label>\n <author>Shi Jinghai</author>\n'
            f' <title>{TITLE}</title>\n <tags>\n  <tag>WCH-LinkE</tag>\n  <tag>debugger</tag>\n'
            f'  <tag>programmer</tag>\n  <tag>SWD</tag>\n  <tag>USB Type-C</tag>\n </tags>\n'
            f' <properties>\n  <property name="package">{PACKAGE}</property>\n'
            f'  <property name="family">{FAMILY}</property>\n</properties>\n'
            f' <description>WCH-LinkE (USB Type-C revision). Breadboard-only part: it is a bench '
            f'tool, not soldered on the board, so there is no schematic/pcb view. '
            f'2x5 2.54mm right-angle header: upper row RX/TX/GND/3V3/RST, '
            f'lower row CLK/DIO/GND/3V3/5V0. For SWD flashing connect only CLK, DIO and GND; '
            f'do not connect 3V3.</description>\n'
            f' <views>\n'
            f'  <iconView>\n   <layers image="icon/{PART_ID}_icon.svg">\n'
            f'    <layer layerId="icon"/>\n   </layers>\n  </iconView>\n'
            f'  <breadboardView>\n   <layers image="breadboard/{PART_ID}_breadboard.svg">\n'
            f'    <layer layerId="breadboard"/>\n   </layers>\n  </breadboardView>\n'
            f' </views>\n'
            f' <connectors>\n' + "\n".join(conns) + '\n </connectors>\n'
            f' <buses>\n' + "\n".join(buses) + '\n </buses>\n</module>\n')


# ---------------------------------------------------------------- 打包
def main():
    files = {"icon": gen_icon_svg(), "breadboard": gen_breadboard_svg()}
    for view, content in files.items():
        name = f"svg.{view}.{PART_ID}_{view}.svg"
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("wrote", name)
    fzp_name = f"part.{PART_ID}.fzp"
    with open(os.path.join(OUT_DIR, fzp_name), "w", encoding="utf-8", newline="\n") as f:
        f.write(gen_fzp())
    print("wrote", fzp_name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    fzpz_path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(fzpz_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(OUT_DIR, fzp_name), arcname=fzp_name)
        for view in ("icon", "breadboard"):          # ★ 只有这两个视图 ✓
            name = f"svg.{view}.{PART_ID}_{view}.svg"
            z.write(os.path.join(OUT_DIR, name), arcname=name)
    print("wrote", fzpz_path)


if __name__ == "__main__":
    main()
