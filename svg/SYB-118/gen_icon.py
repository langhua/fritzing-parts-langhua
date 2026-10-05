# -*- coding: utf-8 -*-
r"""给 `SYB-118` 生成 icon：**从面包板图右端切一块** ✓（2026-10-05 用户定 ✓）

用户原话：「我觉得可以用 SYB-118 的右端的图片，作为 icon，比如截图这样的，
上面有 SYB-118 文字」✓ —— 右端那块自带 **SYB-118 丝印**（竖向 ✓）＋ 两个安装孔 ✓
⇒ 元件箱里**一眼认得出** ✓。

## 做法（✗ 不重画、不动图形 ✓）

`svg.icon.SYB-118_icon.svg` = **面包板 svg 原样复制** ✓，只把根上的
`width / height / viewBox` 换成**裁剪窗** ✓ —— 内容一个字不改 ✓
（坐标都在组里被变换过，重画必错 ✗；改 viewBox 是**无损**的 ✓）。

裁剪窗（**根坐标** ✓，本件生成器量出来的 ✓）：
  · 标签框 `x 473.33→490.71, y 32.43→95.37` ✓（竖向 "SYB-118" ✓）
  · 安装孔中心 `x≈482`，外圈 r≈8.93 ✓（上下各一 ✓）
  · 板右边 `x=497.8458` ✓（= 画布右缘 ✓）
  ⇒ ★ **要方的**（用户 2026-10-05 定："icon 应该是方的，不是长方形的" ✓）
    ⇒ 取**以板右边为基准的正方形** ✓：边长 = 画布**全高** ✓（∓ 两轴微小比例差 ✓ 算准 ✓）
    ⇒ `x ∈ [497.8458 − 127.36, 497.8458]` ✓、`y ∈ [0, 127.333]` ✓
    ⇒ **44.92 × 44.92 mm** ✓（右端那一块 ✓，竖排 "SYB-118" 丝印仍在窗内 ✓）

## 用法

```
py -3.13 svg/SYB-118/gen_icon.py            # 只报（现在是不是已经是切好的 ✓）
py -3.13 svg/SYB-118/gen_icon.py --do       # 写 icon ＋ 改 fzp 的 iconView image ＋ 重打包
py -3.13 svg/SYB-118/gen_icon.py --do --png # 顺手出张 png 让人眼看一下 ✓
```
自检 ✓：① 写出的 svg 可解析 ✓；② 它的 `width/height/viewBox` 与裁剪窗一致 ✓；
③ **内容除根属性外与源图逐字节相同** ✓；④ fzp 的 iconView image 指到它 ✓；
⑤ 包内成员与 fzp 声明一致 ✓。任一条不过 ⇒ **不写** ✗。
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(D))                  # 仓根 ✓
SRC = os.path.join(D, "svg.breadboard.SYB-118_1.svg")
OUT = os.path.join(D, "svg.icon.SYB-118_icon.svg")
FZP = os.path.join(D, "part.SYB-118.fzp")
PKG = os.path.join(ROOT, "fzpz", "SYB-118.fzpz")
CROP = (455.0, 0.0, 497.8458, 127.333)                       # x0 y0 x1 y1（根坐标 ✓）
SIZE_IN = (6.914525, 1.7685139)                              # 源图根上的 in 尺寸 ✓
SRC_W = 497.8458
SRC_H = 127.333
# ★ **要方的** ✓（用户 2026-10-05）：以**板右边**为基准取正方形 ✓
#   边长 = 画布全高 ✓，并按两轴各自的 mm/单位 把"单位边长"算准 ✓
#   （两轴比例差极小 ✓ 但算一下才是真方 ✓）
_MM_PER_U_X = SIZE_IN[0] * 25.4 / SRC_W
_MM_PER_U_Y = SIZE_IN[1] * 25.4 / SRC_H
SIDE_U = SRC_H * _MM_PER_U_Y / _MM_PER_U_X
CROP = (SRC_W - SIDE_U, 0.0, SRC_W, SRC_H)


def mm(v):
    return round(v, 6)


def crop_text(src):
    w_in, h_in = SIZE_IN
    w0 = CROP[2] - CROP[0]
    h0 = CROP[3] - CROP[1]
    scale_in = w_in / SRC_W                                  # in / 单位 ✓
    wi, hi = w0 * scale_in, h0 * scale_in
    wmm, hmm = wi * 25.4, hi * 25.4
    head = re.search(r"<svg\b([^>]*)>", src, re.S)
    attrs = head.group(1)
    new = attrs
    new = re.sub(r'width\s*=\s*"[^"]*"', 'width="%smm"' % mm(wmm), new, count=1)
    new = re.sub(r'height\s*=\s*"[^"]*"', 'height="%smm"' % mm(hmm), new, count=1)
    new = re.sub(r'viewBox\s*=\s*"[^"]*"',
                 'viewBox="%s %s %s %s"' % (CROP[0], CROP[1], w0, h0), new, count=1)
    new = re.sub(r'enable-background\s*=\s*"[^"]*"',
                 'enable-background="new %s %s %s %s"' % (CROP[0], CROP[1], w0, h0),
                 new, count=1)
    out = src[:head.start(1)] + new + src[head.end(1):]
    return out, (wmm, hmm)


def main():
    do = "--do" in sys.argv
    png = "--png" in sys.argv
    src = open(SRC, encoding="utf-8", newline="").read()
    out, size = crop_text(src)
    ET.fromstring(out)
    # ③ 除根属性外逐字节相同 ✓
    b0 = src[re.search(r"<svg\b[^>]*>", src, re.S).end():]
    b1 = out[re.search(r"<svg\b[^>]*>", out, re.S).end():]
    if b0 != b1:
        raise SystemExit("✗ 内容被改动了 ⇒ 不写")
    print("== SYB-118 icon 切片 ✓ 裁剪窗 %s ⇒ **%.2f × %.2f mm** ✓" % (CROP, size[0], size[1]))
    cur = open(OUT, encoding="utf-8", newline="").read() if os.path.exists(OUT) else ""
    same = cur == out
    print("   现在 icon 文件：%s" % ("已就是这一版 ✓" if same else
                                 ("不存在 ✗" if not cur else "是旧版/别的版本 ✗")))
    fz = open(FZP, encoding="utf-8", newline="").read()
    img_ok = 'iconView' in fz and 'image="icon/SYB-118_icon.svg"' in fz
    print("   fzp 的 iconView image：%s" % ("已指向 icon/SYB-118_icon.svg ✓" if img_ok
                                        else "还不是 ✗（现在应该是 breadboard/… ✓）"))
    if not do:
        print("   （只报 ✓；要写就加 `--do` ✓）")
        return 0
    if not same:
        with open(OUT, "w", encoding="utf-8", newline="") as w:
            w.write(out)
        print("   ✓ 写出 %s ✓" % os.path.relpath(OUT, ROOT))
    if not img_ok:
        # 只换 iconView 那一条 ✓（schematic/pcb 仍共用面包板图 ✓，与原厂同形 ✓）
        f2 = re.sub(r'(<iconView>\s*<layers\s+image=")[^"]*(")',
                    r'\1icon/SYB-118_icon.svg\2', fz, count=1)
        if f2 == fz:
            raise SystemExit("✗ 没能改到 iconView 的 image ⇒ 不写")
        ET.fromstring(f2)
        with open(FZP, "w", encoding="utf-8", newline="") as w:
            w.write(f2)
        print("   ✓ 改 fzp：iconView image ⇒ icon/SYB-118_icon.svg ✓")
        fz = f2
    # ⑤ 重打包 ＋ 包内一致 ✓
    files = sorted(f for f in os.listdir(D)
                   if not f.startswith(".") and ".bak" not in f and f != "gen_icon.py")
    with zipfile.ZipFile(PKG, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(D, f), f)
    zz = zipfile.ZipFile(PKG)
    for f in files:
        if zz.read(f) != open(os.path.join(D, f), "rb").read():
            raise SystemExit("✗ 包内 %s 与磁盘不一致 ✗" % f)
    print("   ✓ 重打 %s ⇒ %s ✓（逐条一致 ✓）"
          % (os.path.relpath(PKG, ROOT), zz.namelist()))
    if png:
        try:
            import cairosvg
            p = os.path.join(D, "_icon_preview.png")
            cairosvg.svg2png(url=OUT, write_to=p, output_width=180)
            print("   ✓ 出图 %s ✓（自己先看一眼 ✓）" % os.path.relpath(p, ROOT))
        except ImportError:
            print("   （没装 cairosvg ⇒ 不出图 ✓）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
