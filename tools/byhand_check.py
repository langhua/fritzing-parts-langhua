#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
byhand_check.py — **开发辅助**：核对"程序生成的面包板图"与"手工对齐版"是否一致。

用法：
    C:\\Python313\\python.exe tools\\byhand_check.py svg\\CH347F          # 结构与字号
    C:\\Python313\\python.exe tools\\byhand_check.py svg\\CH347F --png     # 另出像素对比图

比三件事：
  ① 元素计数（rect / circle / text / line）；手工版会先去掉 `<image>` 照片
     —— text 按**行**数（多行文字导出时会拆成多条记录；口径见 tools/svg_lines.py）
     —— 注意：Inkscape 保存时可能把若干同色 rect 合并成 path，几个的差是正常的
  ② 每条 `<text>` 的**有效字号**（把祖先 transform 的缩放累乘进去，单位 = viewBox 单位）
     —— 这里能一眼看出"某批文字大了/小了"，比如双重缩放会整体差 13.6 倍
     —— 另比“加粗文字条数”（手工版丝印普遍 bold，丢了会整体变细）
  ③ `--png` 时把两者渲成同尺寸做像素差，并输出 左=程序版 / 右=手工版 的对比图

输出图（%TEMP%\ch347fcheck 或 --out 指定）：mine.png / hand.png / diff.png / cmp_<区>.png
"""
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

from svg_lines import text_lines

NS = "{http://www.w3.org/2000/svg}"


def mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2, a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def tf(text):
    m = (1, 0, 0, 1, 0, 0)
    for fn, args in re.findall(r'(matrix|translate|scale|rotate)\s*\(([^)]*)\)', text or ""):
        v = [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]
        if fn == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif fn == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif fn == "rotate":
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                t = mul((1, 0, 0, 1, v[1], v[2]), mul(t, (1, 0, 0, 1, -v[1], -v[2])))
        else:
            t = tuple(v)
        m = mul(m, t)
    return m


def survey(path):
    """返回 (计数, {文本: 有效字号}, 加粗文字条数)；顺便把 <image> 之外的图元全数一遍。"""
    root = ET.parse(path).getroot()
    cnt = {"rect": 0, "circle": 0, "text": 0, "line": 0, "image": 0, "g": 0}
    fss = {}
    nbold = [0]

    def weight(el, inh):
        w = el.get("font-weight")
        if not w:
            for kv in (el.get("style") or "").split(";"):
                if kv.strip().startswith("font-weight"):
                    w = kv.split(":", 1)[1].strip()
        return w or inh

    def walk(el, m, w="normal"):
        m2 = mul(m, tf(el.get("transform"))) if el.get("transform") else m
        w2 = weight(el, w)
        tag = el.tag.replace(NS, "")
        if tag in cnt and tag != "text":
            cnt[tag] += 1
        if tag == "text":
            fs = float(re.sub(r"[^0-9.\-]", "", el.get("font-size", "0") or "0") or 0)
            sc = (math.hypot(m2[0], m2[1]) + math.hypot(m2[2], m2[3])) / 2.0
            bold = w2.lower() in ("bold", "bolder", "600", "700", "800", "900")
            for txt, _lx, _ly in text_lines(el):      # 多行 = 多条（与导出同一口径）
                if not txt:
                    continue
                cnt["text"] += 1                     # text 按**行**计，不按元素计
                fss.setdefault(txt, []).append(round(fs * sc, 3))
                if bold:
                    nbold[0] += 1
        for c in el:
            walk(c, m2, w2)
    walk(root, (1, 0, 0, 1, 0, 0))
    return cnt, fss, nbold[0]


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    part_dir = os.path.abspath(argv[0])
    part = os.path.basename(part_dir)
    want_png = "--png" in argv
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(os.environ["TEMP"], "ch347fcheck")
    mine = os.path.join(part_dir, "svg.breadboard.%s_breadboard.svg" % part)
    hand = os.path.join(part_dir, "svg.breadboard.%s_breadboard_byHand.svg" % part)
    if not (os.path.isfile(mine) and os.path.isfile(hand)):
        raise SystemExit("缺文件：%s / %s" % (mine, hand))

    os.makedirs(out, exist_ok=True)
    hand2 = os.path.join(out, "hand_nophoto.svg")
    h = open(hand, encoding="utf-8").read()
    h2 = re.sub(r'<image\b[^>]*/>', '', re.sub(r'<image\b.*?</image>', '', h, flags=re.S))
    open(hand2, "w", encoding="utf-8").write(h2)
    if h.count("<image") != h2.count("<image"):
        print("手工版照片已剔除（元件里不能带照片）")

    cm, fm, bm = survey(mine)
    ch, fh, bh = survey(hand2)
    print("\n%-8s %6s %6s" % ("元素", "程序版", "手工版"))
    for k in ("rect", "circle", "text", "line", "g"):
        flag = "" if cm[k] == ch[k] else "   ← 差 %+d" % (cm[k] - ch[k])
        print("  %-6s %6d %6d%s" % (k, cm[k], ch[k], flag))
    flag = "" if bm == bh else "   ← 差 %+d（字重丢了？）" % (bm - bh)
    print("  %-6s %6d %6d%s" % ("加粗", bm, bh, flag))

    print("\n%-34s %9s %9s" % ("文本", "程序版", "手工版"))
    names = sorted(set(fm) | set(fh), key=lambda t: -(fm.get(t, [0])[0]))
    bad = 0
    for t in names:
        a = fm.get(t, [None])[0]
        b = fh.get(t, [None])[0]
        same = a is not None and b is not None and abs(a - b) < 0.03
        if not same:
            bad += 1
        print("  %-32s %9s %9s%s" % (t[:32], a, b, "" if same else "   ← 不同"))
    print("  字号不同的：%d 条（程序版已按 byhand_export.py 的 FS_UNIFORM 统一丝印，"
          "所以这里的不同 = 手工版里的原值；左下角两行除外）" % bad)

    if want_png:
        import cairosvg
        from PIL import Image, ImageChops
        W = 1200
        ims = []
        for tag, src in (("mine", mine), ("hand", hand2)):
            p = os.path.join(out, tag + ".png")
            cairosvg.svg2png(url=src, write_to=p, output_width=W)
            ims.append(Image.open(p).convert("RGB"))
        if ims[0].size != ims[1].size:
            ims[1] = ims[1].resize(ims[0].size)
        d = ImageChops.difference(ims[0], ims[1]).convert("L")
        w, hgt = d.size
        px = d.load()
        big = sum(1 for y in range(0, hgt, 2) for x in range(0, w, 2) if px[x, y] > 60)
        print("\n像素差异 >60 的比例：%.2f%%" % (100.0 * big / ((w // 2) * (hgt // 2))))
        d.point(lambda v: 255 if v > 60 else 0).save(os.path.join(out, "diff.png"))
        for name, box in (("topleft", (0.0, 0.0, 0.30, 0.30)),
                          ("center", (0.30, 0.35, 0.75, 0.75)),
                          ("passive", (0.15, 0.55, 0.55, 0.85))):
            b = (int(box[0] * w), int(box[1] * hgt), int(box[2] * w), int(box[3] * hgt))
            ca, cb = ims[0].crop(b), ims[1].crop(b)
            c = Image.new("RGB", (ca.width * 2 + 10, ca.height), (255, 255, 255))
            c.paste(ca, (0, 0)); c.paste(cb, (ca.width + 10, 0))
            c.save(os.path.join(out, "cmp_%s.png" % name))
        print("对比图（左=程序版 右=手工版）写在:", out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(sys.argv[1:])
