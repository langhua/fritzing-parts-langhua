# -*- coding: utf-8 -*-
"""审计：PCB 视图里 `copper1` **自己**带 transform、而 `copper0` 在它里面的件。

这类件放到 **PCB 底面**时会错位（2026-10-17 用户报 TP4056「底面拖进来错位」）。

依据（源码可复查，本机 `F:\\build-fritzing\\fritzing-app\\src`）：
  · `items/itembase.cpp`  `ItemBase::getFlipDoc()`
      NewBottom + itemType()==Part（THT 分支）：
        Copper0 层 → `replaceElementID(copper0 → "")` 然后
                     `flipSMDSvg(copper1 → copper0)`；
        Copper1 层 → 反过来把 copper0 翻成 copper1。
  · `svg/svgflattener.cpp`  `SvgFlattener::flipSMDElement()`
      - 镜像轴 = 文档 viewBox 中心；
      - `newElement = element.cloneNode(true)`（copper1 克隆，**保留**自己的 transform）；
      - 原 copper0 作为克隆的兄弟追加（**丢掉** copper1 自己的 transform，因为祖先链只从
        copper1 的父节点往上收集）。

⇒ copper1 上那层 transform 会被一份元素记住、被另一份忘掉 ⇒ 同一块铜在底面出现两种位置。
   修法：把该 transform **烘焙进坐标**（推荐，与生成器件一致），或把它移到 copper0/copper1
   的**共同祖先**上（那样两侧都能继承到）。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "svg")


def groups(text):
    """[(start, end, id, transform)]，按标签配平（自闭合的单独收）。"""
    res, stack = [], []
    for m in re.finditer(r"<(/?)g\b([^>]*?)>", text):
        if m.group(1):
            if stack:
                st, gid, tr = stack.pop()
                res.append((st, m.end(), gid, tr))
            continue
        gid = re.search(r'\bid="([^"]*)"', m.group(2))
        tr = re.search(r'\btransform="([^"]*)"', m.group(2))
        item = (m.start(), gid.group(1) if gid else None, tr.group(1) if tr else None)
        if m.group(0).rstrip().endswith("/>"):
            res.append((m.start(), m.end(), item[1], item[2]))
        else:
            stack.append(item)
    return res


def has_content(text, span):
    """copper0 里有没有图形（只剔开闭标签后还有东西就是有）。"""
    body = text[span[0]:span[1]]
    body = re.sub(r"<g\b[^>]*>", "", body, count=1)
    body = re.sub(r"</g>\s*$", "", body)
    return bool(re.sub(r"\s+", "", body))


def scan(part_dirs=None):
    risky, empty = [], []
    for part in sorted(os.listdir(BASE)):
        d = os.path.join(BASE, part)
        if not os.path.isdir(d):
            continue
        if part_dirs and part not in part_dirs:
            continue
        fs = [x for x in os.listdir(d) if x.startswith("svg.pcb.") and x.endswith(".svg")]
        if not fs:
            continue
        t = open(os.path.join(d, fs[0]), encoding="utf-8", errors="replace").read()
        gs = groups(t)
        c1 = next((g for g in gs if g[2] == "copper1"), None)
        c0 = next((g for g in gs if g[2] == "copper0"), None)
        if not c1 or not c1[3]:
            continue
        if not (c0 and c1[0] < c0[0] < c1[1]):
            continue
        if not has_content(t, c0):
            empty.append(part)      # copper0 是空组 ⇒ 底面没有"第二份铜"可错位 ✓
            continue
        risky.append((part, c1[3]))
    return risky, empty


def main(argv):
    parts = [a for a in argv[1:] if not a.startswith("-")]
    risky, empty = scan(parts)
    print("copper1 自带 transform 且 copper0（**有内容**）在它里面 ⇒ 放到 PCB 底面会错位：%d 个"
          % len(risky))
    for part, tr in risky:
        print("   %-24s %s" % (part, tr))
    if not risky:
        print("   无 ✓")
    if empty:
        print("另：copper0 是空组（底面不会出现第二份铜，无影响）：%d 个 —— %s"
              % (len(empty), " ".join(empty)))
    return 1 if (not parts and risky) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
