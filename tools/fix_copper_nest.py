# -*- coding: utf-8 -*-
r"""把「**铜组套非空铜组**」拆平 ✓（铜只留一层 ✓）+ 可当闸门用 ✓

★★ 起因（用户 2026-10-11 第二次报 ✗）：`R1`/`C1` 的 PCB **仍**显示「3 个焊盘、2 个 Pin1」✗。
   量出来的病根 ⇒ 这批（2024 老写法）零件的 pcb 视图是：
      `<g id="copper0" transform="A"><g id="copper1" transform="B">2 个焊盘</g></g>` ✗
   —— **外层铜组非空**（它包着一块有焊盘的铜组 ✓）⇒ Fritzing 认为这块铜**两层都有** ✗
   ⇒ 画面上焊盘**多出一份**（背面翻转时还会错位 ✓）⇒ 看上去就是「3 个焊盘、2 个 Pin1」✗。
   对照 ✓：本板**渲得对**的件（`D3`/`U1`/`J1`/`L1`/`LED2`）都是
   **`<g id="copper1">` 一层 ＋ `<g id="silkscreen">` 平级** ✓（见 `svg/BAS70BRW/…_pcb.svg` ✓）。

★ 改法（**只拆层、不动几何** ✗✓）：把外层的 `transform=A` **烘进**内层的 `transform=B` ✓
   （等效变换 `M = A∘B` ✓），再去掉外层那个组 ✓ ⇒ 只剩一层铜 ✓。
   数值可复算 ✓：A=(0.7,0,0,1.04,−9,−5.4) ✓、B=(1,0,0,0.30769232,0,6.9230768) ✓
   ⇒ `M=(0.7,0,0,0.32,−9,1.8)` ✓。

★ 判据（**唯一实现** ✓，`--check` 与 `--do` 共用 ✓）：
   ① 同目录的 `.fzp` 里，这个件的**焊盘**（`svgId="…pad"` ✓）只声明了**一个**铜层 `L` ✓
      （✗ 声明两层 = THT 件 ✓ **就该两层都有铜** ✓ ⇒ 不归本条管 ✗）；
   ② 而 svg 里那个焊盘的**祖先链上还挂着另一个非空铜组** ✗ ⇒ 报 ✓。
   ⇒ 拆法就是去掉那个**没被声明的**外层铜组 ✓（把它的 `transform` 烘进内层 ✓）。
   ✗ 里层为空不算 ✗（核心库确有 `<g id='copper1'>…<g id='copper0'></g></g>` 的写法 ✓ 无害 ✓）；
   ✗ `matrix(1,0,0,1,0,0)` 那种恒等拆分也要过 ✓（THT 件正是这种 ✓ 但它们的 fzp 声明两层 ✓ ⇒ 不受影响 ✓）。

用法：
  py -3.13 -X utf8 tools\fix_copper_nest.py --check [路径 ...]   # 只判（闸门口径 ✓）
  py -3.13 -X utf8 tools\fix_copper_nest.py --do    [路径 ...]   # 拆平 ＋ 重打 .fzpz ✓
退出码：0 = 没有「铜套铜」✗（`--do` 之后必为 0 ✓）；1 = 还有 ✗。
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import breadboard_only_views as BOV                                 # noqa: E402

MAT = re.compile(r'matrix\(([^)]*)\)')
DRAW = ("rect", "line", "path", "polygon", "polyline", "circle", "ellipse")
IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
CLOSE = "</g>"


def mat_of(attrs):
    """⇒ SVG 矩阵 `(a,b,c,d,e,f)` ✓（没有 transform ⇒ 恒等 ✓）"""
    m = MAT.search(attrs or "")
    return tuple(float(v) for v in m.group(1).replace(",", " ").split()) if m else IDENT


def mul(A, B):
    """`A∘B`（先 B 后 A ✓）；SVG 的 `matrix(a,b,c,d,e,f)` ⇔ x'=ax+cy+e ✓、y'=bx+dy+f ✓"""
    a, b, c, d, e, f = A
    p, q, r, s, t, u = B
    return (a * p + c * q, b * p + d * q, a * r + c * s, b * r + d * s,
            a * t + c * u + e, b * t + d * u + f)


def fmt_mat(M):
    return "matrix(%s)" % ",".join(("%.8g" % v) for v in M)


def scan(text):
    """⇒ (组列表, 画图元素位置列表 ✓)。组 = `[id, attrs, start, end, parent_idx]` ✓"""
    groups, draws, stack = [], [], []
    for m in re.finditer(r'<(/?)([A-Za-z]+)\b([^>]*?)(/?)>', text):
        closing, tag, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if tag == "g":
            gid = re.search(r'id="([^"]*)"', attrs)
            gid = gid.group(1) if gid else ""
            if closing:
                if stack:
                    groups[stack.pop()][3] = m.end()
            elif selfclose:
                groups.append([gid, attrs, m.start(), m.end(), stack[-1] if stack else -1])
            else:
                groups.append([gid, attrs, m.start(), None, stack[-1] if stack else -1])
                stack.append(len(groups) - 1)
        elif tag in DRAW:
            draws.append(m.start())
    return groups, draws


def declared_layers(fzp_path):
    """⇒ 这个件的**焊盘**声明在哪几层 ✓（读同目录的 `.fzp` ✓；读不到 ⇒ `None` = 跳过 ✓）

    ★ 声明**两层** = THT 件 ✓ ⇒ 它**本来就该两层都有铜** ✗ ⇒ 本规则不管它 ✓。
    """
    if not fzp_path or not os.path.exists(fzp_path):
        return None
    text = open(fzp_path, encoding="utf-8").read()
    m = re.search(r"<connectors>.*</connectors>", text, re.S)
    if not m:
        return None
    return set(re.findall(r'<p\s+layer="(copper[01])"\s+svgId="[^"]*pad"', m.group(0)))


def find_nest(text, declared=None):
    """⇒ [(外层组, 内层组), …]：两个都是 `copper?` 组 ✓、**里层非空** ✓
    而且（若给了 `declared` ✓）**里层就是被声明的层**、外层**不是** ✓（= 白多出来的那层 ✗）"""
    groups, draws = scan(text)
    out = []
    for gi in groups:
        if not gi[0].startswith("copper") or gi[3] is None:
            continue
        for gj in groups:
            if gj is gi or not gj[0].startswith("copper") or gj[3] is None:
                continue
            if not (gi[2] < gj[2] and gj[3] <= gi[3] and any(gi[2] < d < gj[3] for d in draws)):
                continue
            if declared is not None and (gj[0] not in declared or gi[0] in declared):
                continue
            out.append((gi, gj))
    return out


def fix_once(text, declared=None):
    """拆**一处** ✓ ⇒ (新文本, 拆了没 ✓)。每次只动一处 ⇒ 位置永远新鲜 ✓"""
    nests = find_nest(text, declared)
    if not nests:
        return text, False
    outer, inner = nests[0]
    new_tf = fmt_mat(mul(mat_of(outer[1]), mat_of(inner[1])))
    o_open_end = text.find(">", outer[2]) + 1
    o_close_at = outer[3] - len(CLOSE)
    i_open_end = text.find(">", inner[2]) + 1
    i_body = text[inner[2]:i_open_end]
    i_body2 = (MAT.sub(new_tf, i_body, count=1) if MAT.search(i_body)
               else i_body[:-1].rstrip() + ' transform="%s">' % new_tf)
    text = text[:o_close_at] + text[outer[3]:]                   # ① 删外层收尾 ✓
    text = text[:inner[2]] + i_body2 + text[i_open_end:]         # ② 内层烘进变换 ✓
    text = text[:outer[2]] + text[o_open_end:]                   # ③ 删外层开标签 ✓
    return text, True


def fix_text(text, declared=None):
    """⇒ (新文本, 拆了几处 ✓)"""
    n = 0
    while True:
        text, hit = fix_once(text, declared)
        if not hit:
            return text, n
        n += 1


def process(path, do=False):
    d = os.path.dirname(path)
    fzps = [f for f in os.listdir(d) if f.startswith("part.") and f.endswith(".fzp")]
    declared = declared_layers(os.path.join(d, fzps[0])) if fzps else None
    if declared is not None and len(declared) != 1:
        return False, "焊盘声明在 %s ⇒ THT/两层件 ✓ 不归本条管 ✓" % ("+".join(sorted(declared)) or "—")
    text = open(path, encoding="utf-8").read()
    nests = find_nest(text, declared)
    if not nests:
        return False, "铜只有一层 ✓" if declared is None else \
            "焊盘声明层 %s ⇒ 没被白包着 ✓" % "+".join(sorted(declared))
    new, n = fix_text(text, declared)
    try:
        ET.fromstring(new)
    except ET.ParseError as exc:
        return False, "✗ 拆完不是合法 XML（%s）⇒ **不写** ✗" % exc
    if find_nest(new, declared):
        return False, "✗ 拆完还有白多出来的铜层 ✗ ⇒ **不写** ✗"
    if not do:
        return True, "（dry ✓）可拆 %d 处 ✓：%s" % (
            n, "；".join("%s 套 %s ⇒ %s" % (o[0], i[0],
                                            fmt_mat(mul(mat_of(o[1]), mat_of(i[1]))))
                         for o, i in nests))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    return True, "✓ 拆平 %d 处 ✓ ⇒ 只剩声明的那层铜 ✓（几何等效 ✓）" % n


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--check", action="store_true", help="只判（闸门口径 ✓）")
    ap.add_argument("--do", action="store_true", help="拆平 ＋ 重打 .fzpz ✓")
    a = ap.parse_args(argv)
    files = []
    for p in (a.paths or [os.path.join(ROOT, "svg")]):
        if os.path.isdir(p):
            for dp, _dn, fn in os.walk(p):
                for f in sorted(fn):
                    if f.startswith("svg.pcb.") and f.endswith(".svg"):
                        files.append(os.path.join(dp, f))
        else:
            files.append(p)
    print("== fix_copper_nest：**铜组套非空铜组** ✗"
          "（Fritzing 会当成「两层都有这块铜」✗ ⇒ 画面上焊盘多一份 ✗）｜%d 个文件 ==" % len(files))
    changed = []
    for p in files:
        hit, why = process(p, do=a.do)
        if hit:
            print("   %-62s %s" % (os.path.relpath(p, ROOT).replace("\\", "/"), why))
            changed.append(p)
    if a.do and changed:
        for p in changed:
            BOV.pack(os.path.dirname(p))
        print("⇒ 拆了 **%d** 个 pcb 视图 ✓（并重打各自的 `.fzpz` ✓）" % len(changed))
    elif not a.do:
        print("⇒ 待拆 **%d** 个 ✓（加 `--do` 才写 ✗）" % len(changed))
    rest = []
    for p in files:
        d = os.path.dirname(p)
        fzps = [f for f in os.listdir(d) if f.startswith("part.") and f.endswith(".fzp")]
        dec = declared_layers(os.path.join(d, fzps[0])) if fzps else None
        if dec is not None and len(dec) != 1:
            continue
        if find_nest(open(p, encoding="utf-8").read(), dec):
            rest.append(p)
    print("⇒ 复扫仍有「白多出来的铜层」✗：**%d** 个 %s" % (len(rest), "" if not rest else "✗"))
    return 1 if rest else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
