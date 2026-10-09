# -*- coding: utf-8 -*-
r"""merge_sch：把 B 的 `schematicView` **整套并进 A**（**按 `modelIndex` 配对** ✓，
其它视图**逐字节不动** ✗）。

★ 为什么不用库仓的 `tools/merge_view.py` ✗（实测撞到两条 ✓，都是本文件的实情 ✗）：
  ① 它按 `<title>` 配对 ✗ —— 本文件里 **两个 `RC` 网标签同名** ✗（实测 ✓）⇒ 两块会被并成一块 ✗；
  ② 本文件里**线实例的标题与 `modelIndex` 对不上** ✗（实测 52 处 ✗：标题是旧包里的名字 ✓，
     编号是新分配的 ✓）⇒ 标题**不是**身份 ✓；而 `modelIndex` 两边**一字不差** ✓
     （B 是以 A 剥线后的那份为底跑出来的 ✓，只有**新加**的线拿新编号 ✓）⇒ 按编号配对**精确** ✓。

规矩（与 `merge_view.py` 的规矩同 ✓）：
  · A 有、B 也有 ⇒ 把 `schematicView` 块**换成** B 的 ✓（没有就删块 ✓）
  · A 有、B 没有 ⇒ 删掉 A 的 `schematicView` 块 ✓；若这件**只剩这一个视图** ⇒ **整个实例一起删** ✓
  · B 有、A 没有 ⇒ 整个实例块**插进 `</instances>` 之前** ✓（缩进 8 空格 ✓、行尾**转成 CRLF** ✓
    —— A 是 **纯 CRLF** ✓、生成器出的 B 是 **纯 LF** ✗ ⇒ 不转就是混排 ✗）
  · zip 其它成员：A 的照旧 ✓ ＋ B 里多出来的补进来 ✓

用法：py -X utf8 tools\merge_sch.py <A.fzz> <B.fzz> <out.fzz>
     （项目侧的工作副本 `_work\merge_sch.py` 与此**逐字节相同** ✓ —— 2026-10-09 上收进库仓 ✓）
"""
import os
import re
import sys
import zipfile

VIEW = "schematicView"


def inst_spans(text):
    out = []
    # ★★★ 2026-10-09 ✓ 修 ✗：闭合标签**不要求与开标签同缩进** ✓
    #   ✗ 病（实测 ✓）：旧写法 `^([ \t]*)<instance\b.*?\n\1</instance>` 要求**首尾缩进一字相同** ✗
    #     ⇒ 文件里有一个**开 12 空格 / 闭 8 空格**的实例块（历史上一轮 merge 的插入留下的 ✓）
    #     ⇒ 它**不在 `amis` 里** ✗ ⇒ 下一轮 merge 把 B 的同 `modelIndex` 实例当“A 没有”**又插一份** ✗✗
    #     ⇒ 交付件里出现**两个 modelIndex=90015359 的导线实例**（实测 ✓ 本轮撞上 ✓）。
    #   ✓ 正解：闭合标签只要求“**行首是它**” ✓（`[ \t]*</instance>` ✓ —— 实例块不会嵌套 ✓）。
    # ★★★ 2026-10-09 ✓ 修 ✗：闭合标签**不要求前面有换行** ✓（`.*?</instance>` ✓）
    #   ✗ 病（实测 ✓）：`gen_schematic_wires.emit()` 里**新造**的件（`build_ground` ✓ / `build_label` ✓，
    #     都是 `ET.fromstring('<instance …>…</instance>')` ✓）**一行到底** ✗ ⇒ 旧正则
    #     `.*?\n[ \t]*</instance>` 要求“`</instance>` 前有个换行” ✗ ⇒ **整块漏匹配** ✗✗
    #     ⇒ 交付件里**根本没有那个符号/标签** ✗（实测：`--symmerge` 挂的接地符号没进交付件 ✓，
    #     而 `_r72_views.py` 也数不到它 ✓ —— 同一个根因 ✓）。
    #   ✓ 实例块**不嵌套** ✓ ⇒ 收在**遇到的第一个** `</instance>` ✓ 是安全的 ✓。
    #   ★ 对**多行块零影响** ✓（原来能匹配的，现在还是同一段 ✓）。
    for m in re.finditer(r"(?ms)^([ \t]*)<instance\b.*?</instance>", text):
        b = m.group(0)
        mi = re.search(r'\bmodelIndex="(\d+)"', b)
        t = re.search(r"<title>([^<]*)</title>", b)
        out.append(dict(mi=(mi.group(1) if mi else None),
                        title=(t.group(1) if t else ""),
                        s=m.start(), e=m.end(), blk=b, ind=m.group(1)))
    return out


def view_blk(blk):
    m = re.search(r"(?s)\r?\n[ \t]*<%s\b.*?</%s>" % (VIEW, VIEW), blk)
    return m


def main(a_path, b_path, out_path):
    za, zb = zipfile.ZipFile(a_path), zipfile.ZipFile(b_path)
    na = [n for n in za.namelist() if n.endswith(".fz")][0]
    nb = [n for n in zb.namelist() if n.endswith(".fz")][0]
    ta = za.read(na).decode("utf-8")
    tb = zb.read(nb).decode("utf-8")

    bmap = {}
    for sp in inst_spans(tb):
        if sp["mi"]:
            bmap[sp["mi"]] = sp
    stat = dict(repl=0, strip=0, drop=0, ins=0)

    chunks, pos = [], 0
    for sp in inst_spans(ta):
        nb2 = sp["blk"]
        seen = sp["mi"] in bmap
        if seen:
            bs = bmap[sp["mi"]]["blk"]
            mine = view_blk(nb2)
            theirs = view_blk(bs)
            if mine is None:
                pass
            elif theirs is None:
                nb2 = nb2.replace(mine.group(0), "", 1)
                stat["strip"] += 1
            else:
                nb2 = nb2.replace(mine.group(0), theirs.group(0), 1)
                stat["repl"] += 1
        else:
            mine = view_blk(nb2)
            if mine is not None:
                if len(re.findall(r"<\w+View\b", nb2)) == 1:
                    nb2 = ""                                  # 只剩这一个视图 ⇒ 整块删 ✓
                    stat["drop"] += 1
                else:
                    nb2 = nb2.replace(mine.group(0), "", 1)
                    stat["strip"] += 1
        if nb2 != sp["blk"]:
            chunks.append(ta[pos:sp["s"]])
            _s = nb2.replace("\r\n", "\n").replace("\n", "\r\n") if nb2 else ""
            if _s and not _s.endswith("\r\n"):
                _s += "\r\n"
            chunks.append(_s)
            pos = sp["e"] + (2 if ta[sp["e"]:sp["e"] + 2] == "\r\n" else 0)
    chunks.append(ta[pos:])
    new = "".join(chunks)

    # ── B 有、A 没有 ⇒ 插实例 ✓ ──
    amis = {sp["mi"] for sp in inst_spans(ta)}
    adds = [sp for sp in inst_spans(tb) if sp["mi"] and sp["mi"] not in amis]
    if adds:
        anchor = "</instances>"
        i = new.rfind(anchor)
        if i < 0:
            raise SystemExit("✗ 找不到 </instances> ✗")
        pad = ""
        blocks = []
        for sp in adds:
            blk = sp["blk"].replace("\r\n", "\n")
            lines = blk.split("\n")
            lines = ["        " + ln.lstrip() for ln in lines if ln.strip() != ""]
            blocks.append("\r\n".join(lines) + "\r\n")
            stat["ins"] += 1
        new = new[:i] + "".join(blocks) + pad + new[i:]

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in za.namelist():
            if n == na:
                zo.writestr(n, new.encode("utf-8"), compress_type=za.getinfo(n).compress_type)
            else:
                zo.writestr(n, za.read(n), compress_type=za.getinfo(n).compress_type)
        have = set(za.namelist())
        for n in zb.namelist():
            if n not in have:
                zo.writestr(n, zb.read(n), compress_type=zb.getinfo(n).compress_type)
    print("并 %s ← %s 的 <%s> ✓：换 %d ｜ 删块 %d ｜ 删整实例 %d ｜ 插实例 %d ｜ 出 %s"
          % (os.path.basename(a_path), os.path.basename(b_path), VIEW,
             stat["repl"], stat["strip"], stat["drop"], stat["ins"], out_path))
    return stat


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
