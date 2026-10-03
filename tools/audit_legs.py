#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""全仓审计：**面包板引线（rubber-band legs）** 有没有丢 ✓（2026-10-03 ✓）

判据（**拿核心库当尺子** ✓，不靠猜 ✗）：
  · 我们每件的面包板 svg 里有 `<desc><referenceFile>X</referenceFile></desc>` ✓
    ⇒ 去 Fritzing 核心库找同名 svg，看**它有没有** `<line id="connectorNleg">` ✓；
  · 核心库有、我们没有 ⇒ **丢了** ✗（就是电阻件那类 ✓）；
  · 我们 fzp 里 `legId="…"` 引用的 leg 在 svg 里**不存在** ⇒ 断引用 ✗；
  · 我们 svg 有 leg、fzp 里没 `legId` ⇒ 死引线 ✗（Fritzing 不会拉伸它 ✓）。

用法：py -3.13 tools/audit_legs.py [--core <fritzing-parts/svg/core/breadboard>] [--fix]

`--fix` ✓：把「③ svg 有 leg、fzp 没引用」的**补上 `legId`** ✓（并重打该件的 `.fzpz` ✓）——
  只补 fzp 的引用 ✗，**不动 svg 几何** ✓（引线本来就在 svg 里 ✓）。
"""
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SVG_ROOT = os.path.join(REPO, "svg")
FZPZ = os.path.join(REPO, "fzpz")
DEFAULT_CORE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Fritzing",
                            "fritzing-parts", "svg", "core", "breadboard")


def repack(d):
    """把部件目录的 5 个文件**平铺**重打成 `fzpz/<目录名>.fzpz` ✓"""
    out = os.path.join(FZPZ, os.path.basename(d) + ".fzpz")
    names = sorted(n for n in os.listdir(d) if n.endswith(".fzp") or n.endswith(".svg"))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as w:
        for n in names:
            w.write(os.path.join(d, n), n)
    return out


def one(d):
    svg = fzp = None
    for n in sorted(os.listdir(d)):
        if re.match(r"svg\.breadboard\..*\.svg$", n):
            svg = os.path.join(d, n)
        elif re.match(r"part\..*\.fzp$", n):
            fzp = os.path.join(d, n)
    return svg, fzp


def legs_of(txt):
    return sorted(set(re.findall(r'id="(connector\d+leg)"', txt)))


def main(argv):
    core = argv[argv.index("--core") + 1] if "--core" in argv else DEFAULT_CORE
    fix = "--fix" in argv
    print("== 引线审计（核心库 = %s）%s==" % (core, "（--fix ✓）" if fix else ""))
    if not os.path.isdir(core):
        print("   ✗ 核心库目录不在 ⇒ 只做「自身一致性」检查（拿不到尺子 ✗）")
    lost, broken, dead, ok, noleg = [], [], [], [], []
    for name in sorted(os.listdir(SVG_ROOT)):
        d = os.path.join(SVG_ROOT, name)
        if not os.path.isdir(d):
            continue
        svg, fzp = one(d)
        if not svg:
            continue
        st = open(svg, encoding="utf-8", errors="replace").read()
        ft = open(fzp, encoding="utf-8", errors="replace").read() if fzp else ""
        ours = set(legs_of(st))
        ref = re.search(r"<referenceFile\s*>([^<]*)</referenceFile>", st)
        refname = ref.group(1).strip() if ref else None
        fzplegs = set(re.findall(r'legId="([^"]*)"', ft))
        core_legs = set()
        if refname:
            cp = os.path.join(core, refname)
            if os.path.isfile(cp):
                core_legs = set(legs_of(open(cp, encoding="utf-8", errors="replace").read()))
        if core_legs and not ours:
            lost.append((name, refname, len(core_legs)))
        elif fzplegs - ours:
            broken.append((name, sorted(fzplegs - ours)))
        elif ours - fzplegs:
            miss = sorted(ours - fzplegs)
            if fix and fzp:
                txt2 = re.sub(
                    r'<p layer="breadboard" svgId="connector(\d+)pin"\s*/>',
                    lambda m: '<p layer="breadboard" svgId="connector%spin" '
                              'legId="connector%sleg"/>' % (m.group(1), m.group(1)), ft)
                if txt2 != ft:
                    open(fzp, "w", encoding="utf-8", newline="").write(txt2)
                    repack(d)
                    miss = miss + ["（已补 legId ✓ + 重打 fzpz ✓）"]
            dead.append((name, miss))
        elif ours and fzplegs:
            ok.append(name)
        else:
            noleg.append((name, refname))

    print("\n★ ① **丢了引线** ✗（核心库有、我们没有）：%d 件" % len(lost))
    for n, r, c in lost:
        print("   ✗ %-26s 核心库 %s 有 %d 条 leg" % (n, r, c))
    print("\n② fzp 引用不存在的 leg ✗：%d 件" % len(broken))
    for n, l in broken:
        print("   ✗ %-26s %s" % (n, l))
    print("\n③ svg 有 leg 但 fzp 没引用 ✗：%d 件" % len(dead))
    for n, l in dead:
        print("   ✗ %-26s %s" % (n, l))
    print("\n④ 引线齐备 ✓：%d 件" % len(ok))
    print("⑤ 无引线（核心库也没有，或没有 referenceFile）✓：%d 件" % len(noleg))
    return 1 if (lost or broken or dead) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
