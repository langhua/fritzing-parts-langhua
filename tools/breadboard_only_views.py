# -*- coding: utf-8 -*-
r"""★★ 让**面包板件只留在面包板视图** ✓（2026-10-05 用户定：SYB-118 起）

用法：
```
py -3.13 tools/breadboard_only_views.py <部件目录>            # 只报（合格退出码 0 ✓）
py -3.13 tools/breadboard_only_views.py <部件目录> --do       # 真改（先留 .bak-onlyviews ✓）
py -3.13 tools/breadboard_only_views.py <部件目录> --do --pack # 顺手重打顶层 fzpz/<名>.fzpz ✓
```

## 为什么 ✓（机理全文见 `docs/fritzing-fz-notes.md` §10 ✓）

面包板的**每个孔**若在 `schematicView` / `pcbView` 里也声明连接器 ✗，那个视图就会给这些孔
**建连接器项** ✓ ⇒ 它的上百条孔 bus 会被塞进**那个视图的网表** ✗（而且**看不见** ✗，因为
`breadboardbreadboard` 层在 PCB/原理图视图里不画 ✓）⇒ Fritzing 状态栏会假报
「还有 N 个连接件没布线」✗ ＋ 画鼠线虚线 ✗，而铜其实是通的 ✓。

核心面包板件就是这么写的 ✗（`breadboard2.fzp` 里 **831 条** `pcbView` 条目 ✓）；
本库自己的 `SYB-118` 也一样 ✗（**690 条** ✓）。**面包板是"搭电路用的底板"，不是板上的元件** ✓
⇒ 它只该活在**面包板视图**里 ✓。

## 做什么 ✓（**只改“孔”** ✓）

| # | 动作 | 保留 ✓ |
|---|---|---|
| ① | 每个 `<connector>` 的 `<views>` 里删掉 `<schematicView>` / `<pcbView>` 两块 ✓ | 它的 `breadboardView` 块 ✓（`type=female` ✓、`svgId` ✓） |
| — | ✗ **不动部件级** `<views>` ✓ | `iconView`/`breadboardView`/`schematicView`/`pcbView` 四条都留着 ✓（部件结构正常 ✓、Fritzing 不会当它是“残件” ✗） |

★ 为什么只改孔就够 ✓：`handleConnect()` 恢复记录时，目标项是 `connector->connectorItem(m_viewID)` ✓
⇒ **孔在这两个视图里没有连接器项 ⇒ 那些记录全部无效** ✗ ⇒ 桥根本建不起来 ✓
（而且另存也不会把记录写回来 ✓ —— 没项可写 ✓）。
★ 这也正是本仓给上游提的那条建议的写法 ✓（`tools/README.md` “待提给 Fritzing 上游”第 6 条 ✓）。

## 安全阀 ✓

- 只认 `family=Breadboard` 的件 ✓（别的件一律**拒绝**，先打印它是什么 ✓）；
- `--do` 前备份 `*.bak-onlyviews` ✓；
- 改完**必须**：XML 可解析 ✓、connector 数不变 ✓、`<bus>`/`<buses>` 数与内容不变 ✓、
  每个 connector 的 `breadboardView` 块**逐字节不变** ✓；任一条不满足 ⇒ **不写** ✗；
- 打印"删了多少块" ✓（要等于 `2 × connector 数 ＋ 2` ✓，对不上就说明文件形状变了 ✗）。
"""
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

KILL = ("schematicView", "pcbView")


def read_fzp(d):
    f = [x for x in os.listdir(d) if x.endswith(".fzp")]
    if len(f) != 1:
        raise SystemExit("✗ 目录里 .fzp 不是恰好一个：%s" % f)
    return os.path.join(d, f[0])


def family_of(root):
    for p in root.findall("./properties/property"):
        if p.get("name") == "family":
            return p.text
    return None


def problems(text):
    root = ET.fromstring(text)
    fam = family_of(root)
    pv = root.find("views")
    n_conn = len(root.findall("./connectors/connector"))
    bad = []
    if fam is None or fam.strip().lower() != "breadboard":
        bad.append("family=%r ≠ Breadboard ⇒ **不是面包板件，本工具不碰** ✗" % fam)
        return bad, "", root, n_conn
    if pv is not None:
        info = ("部件级 `<views>` 里有 %s ✓ —— 这些**保留** ✓，不算问题 ✓"
                % ", ".join(e.tag for e in pv))
    else:
        info = "部件级 `<views>` 缺失 ✗"
    per = 0
    for c in root.findall("./connectors/connector"):
        v = c.find("views")
        for vn in KILL:
            if v is not None and v.find(vn) is not None:
                per += 1
    if per:
        bad.append("每个孔的 `<views>` 里有这两个视图：共 **%d** 块 ✗" % per)
    return bad, info, root, n_conn


def transform(text, n_conn):
    """删块 ✓：**只动每个孔的 `<views>`** ✓，部件级 `<views>` 逐字不变 ✓
    （✗ 别用全局正则 ✗：`<bus>` 里的字样、别处的同名标签都可能被一起啃掉 ✗）。"""
    stat = {"part": 0, "conn": 0}
    i = text.find("<views>")
    if i < 0:
        raise SystemExit("✗ 找不到部件级 `<views>`")
    j = text.find("</views>", i) + len("</views>")
    head, part_block, tail = text[:i], text[i:j], text[j:]

    def fix_conn(m):
        block = m.group(0)
        out = block
        for vn in KILL:
            out, k = re.subn(r"[ \t]*<%s\b[^>]*>.*?</%s>[ \t]*\r?\n?" % (vn, vn), "", out,
                             flags=re.S)
            stat["conn"] += k
        return out

    tail = re.sub(r"<views>.*?</views>", fix_conn, tail, flags=re.S)
    if stat["conn"] != 2 * n_conn:
        raise SystemExit("✗ 孔里只删掉 %d 块（应 %d 块 ✗）⇒ 不写"
                         % (stat["conn"], 2 * n_conn))
    return head + part_block + tail, stat


def pack(d):
    """把部件目录按**平铺名**重打成顶层 `fzpz/<目录名>.fzpz` ✓（不带 `.bak*` ✓），
    并核对"包内文本 == 磁盘" ✓。"""
    name = os.path.basename(d)
    dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(d))), "fzpz",
                       name + ".fzpz")
    files = sorted(f for f in os.listdir(d)
                   if not f.startswith(".") and ".bak" not in f)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(d, f), f)
    zz = zipfile.ZipFile(dst)
    for f in files:
        if zz.read(f) != open(os.path.join(d, f), "rb").read():
            raise SystemExit("✗ 包里的 %s 与磁盘不一致 ⇒ 重打失败 ✗" % f)
    print("   ✓ 重打 %s ⇒ 包内 %s ✓（逐条与磁盘一致 ✓）"
          % (os.path.relpath(dst, os.path.dirname(dst)), zz.namelist()))


def main():
    d = sys.argv[1].rstrip("\\/")
    do = "--do" in sys.argv
    pack_ = "--pack" in sys.argv
    if "--pack-only" in sys.argv:                      # ★ 只重打包（数据不改 ✓）
        pack(d)
        return 0
    path = read_fzp(d)
    # ★ `newline=""`：**原样保留行尾** ✓（✗ 不然 CRLF 会被换成 LF ✗ ⇒ 整个 fzp 出现
    #   全文件级的假 diff ✗，本仓的"字节级 diff"纪律会被噪掉 ✗）
    text = open(path, encoding="utf-8", newline="").read()
    bad, info, root, n_conn = problems(text)
    print("== %s ✓ connector %d 个 ✓ ==" % (os.path.relpath(path, os.path.dirname(d)),
                                          n_conn))
    if info:
        print("   （信息）%s" % info)
    if not bad:
        print("   ✓ 孔的连接器已经只在面包板视图里声明 ✓（问题 0 条 ✓）")
        if not (do and pack):
            return 0
    else:
        for b in bad:
            print("   ✗ %s" % b)
        if "不是面包板件" in " ".join(bad):
            return 1
    if not do:
        print("   （只报 ✓；要改就加 `--do` ✓）")
        return 1

    out, stat = transform(text, n_conn)
    # ★ 安全阀：改完自己解析 + 三处不变 + breadboardView 块逐字节不变
    ET.fromstring(out)
    r1, r2 = ET.fromstring(text), ET.fromstring(out)
    if len(r1.findall("./connectors/connector")) != len(r2.findall("./connectors/connector")):
        raise SystemExit("✗ connector 数变了 ⇒ 不写")
    b1 = [(b.get("id"), sorted(m.text or m.get("connectorId") or ""
                               for m in b.iter() if m.tag == "member"))
          for b in r1.findall("./buses/bus")]
    b2 = [(b.get("id"), sorted(m.text or m.get("connectorId") or ""
                               for m in b.iter() if m.tag == "member"))
          for b in r2.findall("./buses/bus")]
    if b1 != b2:
        raise SystemExit("✗ `<buses>` 变了 ⇒ 不写")
    bb1 = re.findall(r"<breadboardView>.*?</breadboardView>", text, re.S)
    bb2 = re.findall(r"<breadboardView>.*?</breadboardView>", out, re.S)
    if bb1 != bb2:
        raise SystemExit("✗ 面包板视图块被改动了 ⇒ 不写")
    i0 = text.find("<views>")
    j0 = text.find("</views>", i0) + len("</views>")
    if not out.startswith(text[:j0]):                        # ★ 部件级 `<views>` 逐字不变 ✓
        raise SystemExit("✗ 部件级 `<views>` 被动了 ⇒ 不写")
    v1 = [tuple(sorted(e.tag for e in (c.find("views") or [])))
          for c in r1.findall("./connectors/connector")]
    v2 = [tuple(sorted(e.tag for e in (c.find("views") or [])))
          for c in r2.findall("./connectors/connector")]
    if set(v2) != {("breadboardView",)}:
        raise SystemExit("✗ 有孔的 views 不是只剩 breadboardView：%s ⇒ 不写"
                         % sorted(set(v2)))
    del v1
    shutil.copy2(path, path + ".bak-onlyviews")
    with open(path, "w", encoding="utf-8", newline="") as w:
        w.write(out)
    print("   ✓ 已改 %s（备份 %s ✓）" % (os.path.basename(path),
                                      os.path.basename(path) + ".bak-onlyviews"))
    print("     删块：孔里 %d ✓（= 2×connector %d ✓）｜部件级 `<views>`／connector 数／`<buses>`／面包板视图块都**逐字不变** ✓"
          % (stat["conn"], n_conn))

    if pack_:
        pack(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
