#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
trace_photo.py — **开发辅助（不参与打包、不参与 gen_part.py 运行）**：
把评估板实物照片当"描图底"，与我们的面包板矢量图按同一比例叠起来，用来校验/对齐坐标。

做法（与 svg/CH347F/trace_photo.py 同一套）：读 `CH347EVT_EN.pdf` **第 2 页**的大图
（CH347T-EVT-R0-1v1 实物），自动找出深蓝 PCB 的外框 → 用**卡尺实测的板尺寸**算出 px/mm →
把 `svg.breadboard.CH347T_breadboard.svg` 渲成同尺寸、半透明叠上去。

用法：
    C:\Python313\python.exe svg\CH347T\trace_photo.py

★ 先把用户卡尺实测的板尺寸填进 W_MM / H_MM；填 None 时只量照片、不叠图。

输出（%TEMP%\ch347ttrace\）：photo.png / vector.png / overlay.png / side.png

注意：照片是 **WCH 的版权素材**，只在本机做校准用，**不进仓库**（AGENTS §4/§5）。
"""
import os
import sys

import pymupdf
from PIL import Image

PDF = r"D:\Downloads\CH347EVT\EVT\PUB\CH347EVT_EN.pdf"
PAGE = 2                                   # 第 2 页 = CH347T-EVT-R0-1v1 实物图
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(OUT_DIR, "svg.breadboard.CH347T_breadboard.svg")
TMP = os.path.join(os.environ["TEMP"], "ch347ttrace")
W_MM, H_MM = 50.1, 61.2                    # 用户 2026-09-15 卡尺实测（CH347T-EVT-R0-1v1）
W_PX = 1200                                # 叠图宽度（够看清丝印）


def photo_and_frame():
    os.makedirs(TMP, exist_ok=True)
    doc = pymupdf.open(PDF)
    page = doc[PAGE - 1]
    xref = None
    for im in page.get_images(full=True):          # 最大那张 = 实物图
        if im[2] * im[3] > 200000:
            xref = im[0]
    pix = pymupdf.Pixmap(doc, xref)
    if pix.n > 4:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    photo_p = os.path.join(TMP, "photo.png")
    pix.save(photo_p)
    im = Image.open(photo_p).convert("RGB")
    px = im.load()
    W, H = im.size
    minx, miny, maxx, maxy = W, H, 0, 0
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            r, g, b = px[x, y]
            if b > 60 and b > r + 25 and b > g + 15:      # 深蓝板身
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    return im, (minx, miny, maxx, maxy)


def main():
    im, (minx, miny, maxx, maxy) = photo_and_frame()
    bw, bh = maxx - minx + 1, maxy - miny + 1
    print("照片: %s" % (im.size,))
    print("自动找到的 PCB 外框(px): x %d..%d, y %d..%d  → %d × %d px（宽高比 %.3f）"
          % (minx, maxx, miny, maxy, bw, bh, bw / bh))
    if not (W_MM and H_MM):
        print("\n★ 还没填卡尺尺寸：先用卡尺量这块 CH347T-EVT-R0-1v1 板子（含边）的长宽，")
        print("  填进本文件顶部的 W_MM / H_MM（例如 50.2, 55.5），再跑一次就能叠图看偏差。")
        print("  （只量出宽度也行：按照片宽高比 %.3f，高度 ≈ 宽度 / %.3f）"
              % (bw / bh, bw / bh))
        return
    sx, sy = bw / W_MM, bh / H_MM
    print("比例 %.3f / %.3f px/mm（差 %.1f%%）" % (sx, sy, abs(sx - sy) / sx * 100))
    board = im.crop((minx, miny, maxx + 1, maxy + 1)).resize(
        (W_PX, int(W_PX * H_MM / W_MM)), Image.LANCZOS)
    board.save(os.path.join(TMP, "board.png"))
    if not os.path.isfile(SVG):
        print("还没有 %s → 只写出照片/板面，等面包板 svg 出来再跑一次" % os.path.basename(SVG))
        return
    import cairosvg
    vec_p = os.path.join(TMP, "vector.png")
    cairosvg.svg2png(url=SVG, write_to=vec_p, output_width=W_PX, output_height=board.size[1])
    vec = Image.open(vec_p).convert("RGBA")
    over = board.convert("RGBA")
    v2 = vec.copy()
    v2.putalpha(140)
    over.alpha_composite(v2)
    over.save(os.path.join(TMP, "overlay.png"))
    side = Image.new("RGBA", (W_PX * 2 + 20, board.size[1]), (30, 30, 30, 255))
    side.paste(board, (0, 0))
    side.paste(vec, (W_PX + 20, 0))
    side.save(os.path.join(TMP, "side.png"))
    print("写出:", TMP)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
