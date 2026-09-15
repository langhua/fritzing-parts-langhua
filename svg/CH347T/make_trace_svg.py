#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
make_trace_svg.py — **开发辅助**：生成一个能直接拖进 Inkscape 的「带底图」SVG，
供人工在实物照片上继续微调面包板几何（用户 2026-09-15 要求）。

输出：`trace_overlay.svg`（**已加进 .gitignore** —— 里面嵌的是 WCH 的实物照片，不能入库）
  ⇢ 三个 Inkscape 图层（图层面板里能单独开关）：
    · 矢量（可编辑）  —— 我们的面包板几何，**单位就是 mm**（见下面那条 ★）
    · 底图（照片）    —— 正好铺满 50.1×61.2mm 的板面，做对照
    · 刻度（默认隐藏）—— 1mm 细线 + 5mm 粗线，量位置时在图层里点亮

★ 这份 SVG 里的矢量是**用 mm 重出**的：出图前把 `bb_board.MM_U` 临时改成 1.0，
  所以你在 Inkscape 状态栏/XML 编辑器里读到的 x、y、字号，**就是 `bb_board.py` 表里的那个数**，
  不用乘/除任何换算 —— 你说"P5 那列往左挪 0.5mm"，我直接把表里的 x 减 0.5 就行。

用法：
    C:\Python313\python.exe svg\CH347T\trace_photo.py        # 先生成标定用的板面照片
    C:\Python313\python.exe svg\CH347T\make_trace_svg.py     # 再出这份"带底图"SVG
"""
import base64
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, OUT_DIR)

import bb_board as B                                    # noqa: E402
from PIL import Image                                   # noqa: E402

TMP = os.path.join(os.environ["TEMP"], "ch347ttrace")
PHOTO = os.path.join(TMP, "board.png")                  # trace_photo.py 的产物（已摆正、正好是板面）
OUT = os.path.join(OUT_DIR, "trace_overlay.svg")
JPEG_Q = 92

LBL_VEC = "矢量（可编辑）"
LBL_IMG = "底图（照片，只作对照）"
LBL_GRID = "刻度 mm（默认隐藏）"


def main():
    if not os.path.isfile(PHOTO):
        print("先跑 trace_photo.py —— 没找到 %s" % PHOTO)
        return 1
    W, H = B.BOARD_MM

    # ---- 矢量：临时把换算改成恒等，于是整套几何的单位就是 mm --------------------
    old_u = B.MM_U
    B.MM_U = 1.0
    try:
        art = B.gen_breadboard_svg(OUT_DIR)
    finally:
        B.MM_U = old_u
    inner = re.search(r'<g id="breadboard">(.*?)\n </g>\n</svg>', art, re.S)
    if not inner:
        print("取不到 <g id=\"breadboard\"> 内容")
        return 2

    # ---- 照片：压成 JPEG 再 base64 内嵌（内嵌就不会因为换目录而丢底图） ----------
    im = Image.open(PHOTO).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    # ---- 刻度层（默认隐藏）：1mm 细线 / 5mm 粗线 --------------------------------
    grid = []
    x = 0.0
    while x <= W + 1e-6:
        major = abs(x / 5.0 - round(x / 5.0)) < 1e-6
        grid.append('   <line x1="%.2f" y1="0" x2="%.2f" y2="%.2f" stroke="%s" '
                    'stroke-width="%.2f"/>' % (x, x, H, "#ff00ff" if major else "#ff88ff",
                                               0.15 if major else 0.07))
        x += 1.0
    y = 0.0
    while y <= H + 1e-6:
        major = abs(y / 5.0 - round(y / 5.0)) < 1e-6
        grid.append('   <line x1="0" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                    'stroke-width="%.2f"/>' % (y, W, y, "#00ffff" if major else "#88ffff",
                                               0.15 if major else 0.07))
        y += 1.0

    svg = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<!-- CH347T 面包板「带底图」工作稿（由 make_trace_svg.py 生成，不要手工提交到仓库）：\n'
        '     图层「矢量（可编辑）」里的坐标单位 = mm，与 svg/CH347T/bb_board.py 的表一一对应。\n'
        '     改完告诉我改了哪几个数（或直接说"往左 0.5mm"），我更新表再重出元件。\n'
        '     底图是 WCH 的实物照片，只在本机做对照用，不进仓库。 -->\n'
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"\n'
        '     xmlns:svg="http://www.w3.org/2000/svg"\n'
        '     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n'
        '     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"\n'
        '     version="1.1" width="%.2fmm" height="%.2fmm" viewBox="0 0 %.2f %.2f">\n'
        ' <sodipodi:namedview inkscape:document-units="mm" units="mm" '
        'pagecolor="#ffffff" bordercolor="#666666" borderopacity="1.0" '
        'inkscape:showpageshadow="2" inkscape:pagecheckerboard="0"/>\n'
        % (W, H, W, H)
        + ' <g inkscape:groupmode="layer" inkscape:label="%s" id="layer_vector" '
          'style="display:inline">\n' % LBL_VEC
        + inner.group(1) + '\n </g>\n'
        + ' <g inkscape:groupmode="layer" inkscape:label="%s" id="layer_photo" '
          'style="display:inline" inkscape:opacity="1.0">\n' % LBL_IMG
        + '  <image x="0" y="0" width="%.2f" height="%.2f" preserveAspectRatio="none"\n'
          '         xlink:href="data:image/jpeg;base64,%s"/>\n' % (W, H, b64)
        + ' </g>\n'
        + ' <g inkscape:groupmode="layer" inkscape:label="%s" id="layer_grid" '
          'style="display:none" inkscape:insensitive="true">\n' % LBL_GRID
        + "\n".join(grid) + '\n </g>\n'
        '</svg>\n')
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote %s  (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
    print("  图层：%s / %s / %s（最后一个默认隐藏）" % (LBL_VEC, LBL_IMG, LBL_GRID))
    print("  ★ 矢量层坐标单位 = mm，与 bb_board.py 表里的数一一对应")
    return 0


if __name__ == "__main__":
    sys.exit(main())
