#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
trace_photo.py — **开发辅助（不参与打包、不参与 gen_part.py 运行）**：
把评估板实物照片当"描图底"，与我们的面包板矢量图按同一比例叠起来，用来校验/对齐坐标。

为什么要有它：CH347F 面包板 = 整块官方评估板（CH347F-EVT-R0-1v0），各个排针/元件的位置
只能从实物照片量；靠"目测象限"摆位置必然偏（用户 2026-09-15 提出的做法：把照片当底、对齐它）。

做法：读 `D:\Downloads\CH347EVT\EVT\PUB\CH347EVT_EN.pdf` 第 1 页的大图（CH347F 背面实物），
自动找出深蓝 PCB 的外框 → 按卡尺实测的 **50.2 × 55.5 mm** 算出 px/mm → 把
`svg.breadboard.CH347F_breadboard.svg` 渲成同尺寸、半透明叠上去。

用法：
    C:\Python313\python.exe svg\CH347F\trace_photo.py
输出（%TEMP%\ch347ftrace\）：
    photo.png     抠出来的实物照片
    vector.png    只渲矢量图
    overlay.png   照片 + 半透明矢量（看偏差）
    side.png      左照片 / 右矢量（并排看）

注意：照片是 **WCH 的版权素材**，只在本机做校准用，**不进仓库**（AGENTS §4/§5）。
"""
import os
import sys

import pymupdf
from PIL import Image
import cairosvg

PDF = r"D:\Downloads\CH347EVT\EVT\PUB\CH347EVT_EN.pdf"
PAGE = 1                                   # 第 1 页 = CH347F-EVT-R0-1v0 背面图
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(OUT_DIR, "svg.breadboard.CH347F_breadboard.svg")
TMP = os.path.join(os.environ["TEMP"], "ch347ftrace")
W_MM, H_MM = 50.2, 55.5                    # 用户卡尺实测板尺寸 → 照片像素→mm 的比例基准
W_PX = 1200                                # 叠图宽度（够看清丝印）


def main():
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
    print("照片:", im.size)

    # 自动找 PCB 外框（深蓝板身）
    px = im.load()
    W, H = im.size
    minx, miny, maxx, maxy = W, H, 0, 0
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            r, g, b = px[x, y]
            if b > 60 and b > r + 25 and b > g + 15:
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    sx = (maxx - minx) / W_MM
    sy = (maxy - miny) / H_MM
    print("PCB 外框 px=(%d,%d)-(%d,%d)  比例 %.3f / %.3f px/mm（差 %.1f%%）"
          % (minx, miny, maxx, maxy, sx, sy, abs(sx - sy) / sx * 100))

    board = im.crop((minx, miny, maxx + 1, maxy + 1)).resize(
        (W_PX, int(W_PX * H_MM / W_MM)), Image.LANCZOS)
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
