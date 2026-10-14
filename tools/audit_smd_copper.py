# -*- coding: utf-8 -*-
r"""全库**清点**：「哪些件的铜声明/画在了两层」—— 顺带把**违规**的挑出来 ✓

★ 先说清楚**判据只有一份** ✗：**违规**与否一律交给 `fix_copper_nest.find_nest()` ✓
  （本脚本**不另立一套** ✗ —— 判据两份实现必然互相对不上 ✓，这是本仓屡次踩到的问题 ✗）。
  本脚本只做两件 `fix_copper_nest` 不做的事 ✓：
    ① **清点** —— 把"两层都有图形"的件全列出来 ✓ 并标出**哪一种两层** ✓：
       · `THT 合法` ✓ —— 通孔件，焊盘本来就在两层都有铜 ✓（`.fzp` 确实声明了两层 ✓）；
       · **违规** ✗ —— 焊盘只声明**一层**，却被**另一个非空铜组**包着 ✗
         （= `R1`/`C1` 那个病 ✓：画面上焊盘多渲一份、背面翻转错位 ✗）；
    ② `--dump <件名>` —— 按**嵌套关系**打出某个件 pcb svg 的结构 ✓（人肉核用 ✓）。

★★ 为什么要有这个"清点" ✓（2026-10-11 实测 ✗）：`fix_copper_nest --check` 曾因
   `declared_layers()` 只认 `svgId="…pad"` ✗ ⇒ 焊盘叫 `…pin` 的件（`SOD-323`/`SOD-523` ✓）
   被**静默跳过** ✗ ⇒ 它报 0 个、而实际有 2 个 ✗。⇒ 洞已补 ✓（读属性、不看后缀 ✓）；
   本脚本就是那个"**另一个口径**"的复核 ✓ —— ★ 结论不许自证（本仓规矩 ✓）。

用法：
  py -3.13 -X utf8 tools\audit_smd_copper.py                 # 清点全库
  py -3.13 -X utf8 tools\audit_smd_copper.py --dump SOD-323  # 看某件结构
退出码：0 = 没有违规 ✓；1 = 有 ✗。
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import fix_copper_nest as FCN                                        # noqa: E402

DRAW = re.compile(r'<(rect|circle|ellipse|path|polygon|polyline|line)\b([^>]*?)/?>', re.S)
ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')


def attrs_of(s):
    return dict(ATTR.findall(s))


def group_span(text, name):
    """⇒ [(起, 止), …]：`id="<name>"` 的组的**文本区间** ✓（按标签配平 ✓，✗ 不用非贪婪正则 ✗）"""
    out = []
    for m in re.finditer(r'<g\b[^>]*>', text):
        if not re.search(r'id="%s"' % re.escape(name), m.group(0)):
            continue
        depth, i = 1, m.end()
        while depth and i < len(text):
            n = re.search(r"<g\b[^>]*>|</g>", text[i:])
            if not n:
                break
            depth += -1 if n.group(0) == "</g>" else 1
            i += n.end()
        out.append((m.end(), i - 4))
    return out


def pair_of(text):
    """这段 pcb svg 里 `copper0` / `copper1` 各画了几个图元 ✓ ⇒ (n0, n1)"""
    out = []
    for name in ("copper0", "copper1"):
        sp = group_span(text, name)
        seg = text[sp[0][0]:sp[0][1]] if sp else ""
        out.append(len(DRAW.findall(seg)))
    return tuple(out)


def dump(part):
    """把一个件的 pcb svg **按嵌套关系**打出来 ✓（`<g>` 缩进 ✓、图元带 id/fill ✓）"""
    base = None
    for r in (os.path.join(ROOT, "svg"),):
        for b, _d, fs in os.walk(r):
            if os.path.basename(b) == part and any(f.endswith("_pcb.svg") for f in fs):
                base = b
                break
        if base:
            break
    if not base:
        print("✗ 找不到 %s" % part)
        return 1
    f = [x for x in os.listdir(base) if x.endswith("_pcb.svg")][0]
    text = open(os.path.join(base, f), encoding="utf-8").read()
    print("== %s ｜ %s" % (part, f))
    depth = 0
    for m in re.finditer(r"<g\b[^>]*>|</g>|<(rect|circle|ellipse|path|polygon|polyline|line)\b[^>]*?/?>", text):
        s = m.group(0)
        if s == "</g>":
            depth = max(depth - 1, 0)
            continue
        if s.startswith("<g"):
            a = attrs_of(s)
            print("%s<g id=%s%s>" % ("  " * depth, a.get("id", "?"),
                                     "  transform=" + a["transform"] if "transform" in a else ""))
            depth += 1
            continue
        a = attrs_of(s)
        print("%s· <%s id=%s fill=%s stroke=%s%s>" % (
            "  " * depth, m.group(1), a.get("id", "-"), a.get("fill", "-"), a.get("stroke", "-"),
            "  x=%s y=%s" % (a["x"], a["y"]) if "x" in a else ""))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--dump", metavar="件名")
    a = ap.parse_args()
    if a.dump:
        return dump(a.dump)
    roots = a.paths or [os.path.join(ROOT, "svg")]
    bad, tot, hit, tht, odd = [], 0, 0, 0, 0
    for r in roots:
        for base, dirs, files in os.walk(r):
            if "_assets" in base:
                continue
            svgs = [f for f in files if f.endswith("_pcb.svg")]
            if not svgs:
                continue
            fzps = [f for f in files if f.endswith(".fzp")]
            for s in svgs:
                tot += 1
                text = open(os.path.join(base, s), encoding="utf-8").read()
                n0, n1 = pair_of(text)
                if not n0 or not n1:                 # 只有一层有铜 ⇒ 本来就对 ✓
                    continue
                hit += 1
                declared = FCN.declared_layers(
                    os.path.join(base, fzps[0])) if fzps else None
                nests = FCN.find_nest(text, declared)
                name = os.path.basename(base)
                if nests and declared is not None:
                    verdict = "✗ **违规**（%s 白包着 %s ✗）" % (nests[0][0][0], nests[0][1][0])
                    bad.append(name)
                elif declared is not None and len(declared) == 2:
                    verdict = "· THT 合法 ✓（fzp 确实声明两层 ✓）"
                    tht += 1
                elif declared is None:
                    # ★ 读不到 `.fzp` ⇒ **判不了** ✗ —— 老写法里 THT 件正是这样"铜套铜"的 ✓
                    #   （实测 `LM393-A3144-HALL-3PINS`：焊盘在 copper0＋copper1 各声明一条 ✓）
                    #   ⇒ 只报 ⚠ 给人看 ✓，**不当违规** ✗（否则就是假警报 ✗）。
                    verdict = "⚠ 读不到 `.fzp` ⇒ 判不了 ✗（结构像 THT ✓：环 ＋ 同 id 两层 ✓）"
                    odd += 1
                else:
                    verdict = "· 两层各有各的图元 ✓（声明 %s ✓）" % "+".join(sorted(declared))
                print("%-22s 图元 c0=%-3d c1=%-3d ｜ %s" % (name, n0, n1, verdict))
    print("\n—— 扫了 %d 个 pcb svg ✓；两层都有图形的 %d 个 ✓"
          "（THT 合法 %d ✓；判不了 %d ⚠；**违规** ✗ %d）——" % (tot, hit, tht, odd, len(bad)))
    if bad:
        print("✗ 待修：" + "、".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
