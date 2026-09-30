# -*- coding: utf-8 -*-
r"""把 B 的**某一个视图**整套搬到 A 上 ✓（2026-09-30 立）

★★ 为什么需要它 ✓：一块板子的三个视图往往是**分几次做对**的 ✓
  （面包板一次 ✓、原理图一次 ✓、PCB 一次 ✓）—— 但"另存为"只会带上当时那张 ✗
  ⇒ 交付的那份 sketch 里，三张应当都是**各自最新做对的那版** ✓
  ⇒ 必须有一步"把某一视图**整块替换**" ✓（人手工做不了：实例在三个视图各有一份几何 ✓）。

规矩（每条都防一种错 ✓）：
  · **只动点名的那一个视图** ✓（别的视图逐字节不动 ✗ —— 那两张是已交付的 ✓）
  · 实例按 **`<title>`** 对齐 ✓（Fritzing 里实例名 = 位号 / 线名 ✓ 唯一 ✓）
  · A 有、B 也有 ⇒ 把该视图块**换成 B 的** ✓
  · A 有、B 没有 ⇒ **删掉该视图块** ✓；若这件**只有这一个视图** ⇒ 连**整个实例**一起删 ✓
    （不删就会多出一条重复的线 ✗）
  · B 有、A 没有 ⇒ **整块插进 `<instances>`** ✓，并把它引用的**件文件**一并补进 zip ✓
    （不然 Fritzing 打开会说找不到件 ✗）
  · zip 里的其它成员：A 的照旧 ✓ + B 里多出来的补进来 ✓

用法：
  py -3.13 tools\merge_view.py <A.fzz> <B.fzz> --view <视图名> [--out <out.fzz>]
  （`--view schematicView` ✓ / `breadboardView` ✓ / `pcbView` ✓）
"""
import os
import re
import sys
import zipfile


def inst_spans(text):
    """⇒ `[(标题, 起, 止, 块文本, 缩进), …]`（按同缩进配对切 ✓，不吃到下一个实例 ✓）"""
    out = []
    for m in re.finditer(r"(?ms)^([ \t]*)<instance\b.*?\n\1</instance>", text):
        b = m.group(0)
        t = re.search(r"<title>([^<]*)</title>", b)
        out.append((t.group(1) if t else None, m.start(), m.end(), b, m.group(1)))
    return out


def view_re(view):
    return re.compile(r"(?s)<%s\b.*?</%s>" % (view, view))


def blocks_of_view(block, view):
    """该实例块里**点名视图**的子块 ⇒ 文本或 None ✓"""
    m = view_re(view).search(block)
    return m.group(0) if m else None


def merge(za, zb, view, dry=False):
    """⇒ `(新文本 ✓, 补进来的 zip 成员名单 ✓, 统计 ✓)`"""
    na = [n for n in za.namelist() if n.endswith(".fz")][0]
    nb = [n for n in zb.namelist() if n.endswith(".fz")][0]
    ta = za.read(na).decode("utf-8")
    tb = zb.read(nb).decode("utf-8")
    bmap = {}
    for t, _s, _e, b, ind in inst_spans(tb):
        if t:
            bmap[t] = (b, ind)
    stat = dict(repl=0, strip=0, drop=0, ins=0, miss=[])
    chunks, pos = [], 0
    for t, s, e, b, ind in inst_spans(ta):
        nb2 = b
        if t in bmap:
            bs, _bind = bmap[t]
            mine = blocks_of_view(b, view)
            theirs = blocks_of_view(bs, view)
            if mine is None:
                pass
            elif theirs is None:
                nb2 = b.replace(mine, "", 1)
                stat["strip"] += 1
            else:
                nb2 = b.replace(mine, theirs, 1)
                stat["repl"] += 1
        else:
            mine = blocks_of_view(b, view)
            if mine is None:
                pass
            elif len(re.findall(r"<\w+View\b", b)) == 1:     # 这件**只有这一个视图** ⇒ 整块删 ✓
                nb2 = ""
                stat["drop"] += 1
            else:
                nb2 = b.replace(mine, "", 1)
                stat["strip"] += 1
        chunks.append(ta[pos:s])
        chunks.append(nb2)
        pos = e
    chunks.append(ta[pos:])
    text = "".join(chunks)

    # B 有、A 没有 ⇒ 整块插进 `</instances>` 前 ✓
    have = {t for t, _s, _e, _b, _i in inst_spans(text) if t}
    add = [b for t, _s, _e, b, ind in inst_spans(tb) if t not in have]
    if add:
        m = re.search(r"(?m)^([ \t]*)</instances>", text)
        if not m:
            raise SystemExit("✗ A 里找不到 `</instances>` ⇒ 不肯瞎插 ✗")
        pads = "\n".join(add)
        text = text[:m.start()] + pads + "\n" + text[m.start():]
        stat["ins"] = len(add)
    # ★ 只补"B 有、A 没有"的**素材**（件定义 / 视图 svg ✓）；
    #   **B 自己的 sketch 文件（`*.fz`/`*.fzz`）绝对不许搬** ✗ ——
    #   否则一个包里出现两张 sketch，Fritzing 可能读到错的那张 ✗（实测：第一版就把
    #   `pixel-schematic.fz` 塞了进来 ✗）。
    stat["miss"] = ([] if dry else
                    [n for n in zb.namelist()
                     if n not in za.namelist() and not n.endswith((".fz", ".fzz"))])
    return text, stat, na


def main(argv):
    if "--view" not in argv:
        print(__doc__)
        return 2
    a, b = argv[0], argv[1]
    view = argv[argv.index("--view") + 1]
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    za, zb = zipfile.ZipFile(a), zipfile.ZipFile(b)
    text, stat, na = merge(za, zb, view)
    print("== 合并：%s ⇦ %s 的 `%s` ==" % (os.path.basename(a), os.path.basename(b), view))
    print("   替换视图块 %d ✓ ｜ 删掉多余视图块 %d ✓ ｜ 整件删掉 %d ✓ ｜ 新增实例 %d ✓"
          % (stat["repl"], stat["strip"], stat["drop"], stat["ins"]))
    if stat["miss"]:
        print("   补进 zip 的件文件：%s" % ", ".join(stat["miss"]))
    if not out:
        print("   （--dry ✓ 没写文件）")
        return 0
    zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    for it in za.infolist():
        data = text.encode("utf-8") if it.filename == na else za.read(it.filename)
        zi = zipfile.ZipInfo(it.filename, date_time=it.date_time)
        zi.compress_type = it.compress_type
        zi.external_attr = it.external_attr
        zout.writestr(zi, data)
    for n in stat["miss"]:
        zout.writestr(n, zb.read(n))
    zout.close()
    print("   ✓ 写出 %s（%d 字节）" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
