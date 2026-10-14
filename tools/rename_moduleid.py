#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""给**没有生成器**的部件改 `moduleId`（连带改 5 个文件名与内容里的引用）✓ 2026-10-13 ✓

为什么必须改 moduleId ✗（用户 2026-10-13 报「电阻阻值不可输入、公差不可选」✓）
-----------------------------------------------------------------------------
Fritzing 靠**件名的后缀**认"这是哪种件"，一处判据、两处生效 ✓（源码可复查 ✓）：

  ① `items/partfactory.cpp:137`  `if (moduleID.endsWith("ResistorModuleID"))
                                      return new Resistor(…)` ✓
     ⇒ 后缀不对 ⇒ 造的是**通用件 `ItemBase`** ✗ ⇒ 属性面板走通用那套 = **整块只读** ✗。
  ② `items/propertydef.cpp:112`  `if (!modelPart->moduleID().endsWith(suffix, Qt::CaseInsensitive))
                                      continue;` ✓（表在 `resources/properties.xml` ✓ = 编进 exe ✓）
     ⇒ 后缀不对 ⇒ 连**公差的候选列表**都取不到 ✗。
  ③ 对照（用户两张截图 ✓）：core 那颗 `5BandResistorModuleID`（后缀对 ✓）能填能选 ✓；
     我们的 `R0603_36137a…_1`（后缀不对 ✗）只读 ✗ ✓。

  ⇒ **属性名不用改** ✓（上一轮改成小写 `resistance` 正是对的 ✓ ——
    `items/resistor.cpp:98/100` 就是按 `localProp("resistance")` / `value("resistance")` 读 ✓）。

改名规则 ✓（**可机器映射** ⇒ 老草图能一键批量替换 ✓）
-----------------------------------------------------------------------------
    新名 = 旧名 + "-<后缀>"        例：`R0603_36137a0f26fc46e91e48eb74468f61a7_1`
                                        → `…_1-ResistorModuleID` ✓
  ★ **绝不丢 `_1` / `_2`** ✗ —— 那几位是**同一 hex 上的版本号**
    （本库 0805/1206/1812/2010/2512 共用 `0a212ee8…` ✓，靠 `_1.._5` 区分 ✓）
    ⇒ 丢了就**五个件撞名** ✗。

改什么 ✓（5 个文件一起动手 ✗ 少一个就是"fzp 找不到图" ✗）
-----------------------------------------------------------------------------
  · `part.<moduleId>.fzp`  → 文件名 + 内容里的 `moduleId="…"` ✓
    ＋ `image="<view>/<moduleId>_<view>.svg"` ✓（§4：image 用子目录路径 ✓）
    ＋ 可能的 `<referenceFile>` ✓；
  · `svg.<view>.<moduleId>_<view>.svg` → 文件名 + 内容里的自引用
    （实测有 `sodipodi:docname="svg.pcb.<moduleId>_pcb.svg"` ✓ —— 本库电容件的
     `gen_part.py` 专门处理过它 ✓ 说明**确实会出现** ✓）；
  · 裸替换 `<旧 moduleId>` → `<新>` 是安全的 ✓：它是 `<字母><尺寸>_<32位hex>_<n>`
    这种**唯一串** ✓（不会误伤别的文本 ✓）。

★ 有生成器的件**别用它** ✗ —— 改生成器里的 `mod` 常量再重生成 ✓
  （本库：`Capacitor-0402` / `Supercap-0.47F` 两族的 `gen_part.py` ✓），
  否则生成器下次一跑就把名字冲回去 ✗。

★ **本工具顺手改 Fritzing 元件箱（`.fzb`）里的引用** ✓（2026-10-15 补 ✗，用户点 MINE 撞出来的）：
  改 moduleId = **改身份证** ✓ ⇒ **引用它的地方全都要跟着改** —— 除了草图，还有**元件箱** ✓：
  Fritzing 自维护的 MINE 箱（`<Documents>/Fritzing/bins/my_parts.fzb` ✓）里存的是
  `<instance moduleIdRef="<旧名>" path="…/parts/user/<旧名>.fzp">` ✓ ⇒ 只改了 `parts/user` ✗
  ⇒ 点 MINE 就弹「不能够找到如下 N 个元件」✗（出处 `src/model/modelbase.cpp:418` ✓，
  2026-10-15 实测 18 条：10 电阻 + 6 电感 + 2 晶振 ✓）。
  复核/单独修 = **`py -3.13 tools\check_bins.py`** ✓（`--fix` 用同一套**保守映射**：
  旧名 `old` ⇒ 已装的件里 `old + "-<后缀>"` **恰好一个**才改 ✓，找不到/多个一律只点名 ✗）。
  本工具默认做这一步 ✓（`--no-bins` 关掉 ✓；箱目录用 `--bins-dir` 换 ✓）。

★ 打完这个工具**还要**：删旧文件（本工具会删 ✓）→ `py -3.13 tools\repack_fzpz.py` ✓
  （zip 条目名跟着换 ✓ —— 光 repack 不行 ✗：它按**条目名**找同名源，改名后找不到 ⇒ 只会“保留” ✗）
  → 重新部署到 Fritzing MINE ✓（`check_deploy.py <件> --fix` ✓，旧名的残留用
  `--clean-stray` 移走 ✓ 不删 ✓）。

用法::

    py -3.13 tools\rename_moduleid.py --suffix=ResistorModuleID --check svg\Resistor-0603
    py -3.13 tools\rename_moduleid.py --suffix=ResistorModuleID svg\Resistor-0603 […]

★ **它会顺手重打 `.fzpz`** ✗✓ —— 改名后 zip 的**条目名不会自己跟着变** ✗：
  `tools\repack_fzpz.py` 是**按条目名找同名源**的 ✓ ⇒ 旧条目名找不到源 ⇒ 只会“原样保留” ✗
  ⇒ 包里还是旧名 ✗（而且 G4 闸门也不会报 ✗ —— 它看的是“有源就对账” ✓）。
  所以这里直接**按目录里的 5 个文件平铺重打** ✓；换行/时间戳归一化仍交给 `repack_fzpz.py` ✓。
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FZPZ = ROOT / "fzpz"
KEEP = (".fzp", ".svg")


def repack(p):
    """按目录里的 5 个文件**平铺重打** `fzpz/<目录名>.fzpz` ✓（改名后 zip 条目名不会自己变 ✗）。

    换行/时间戳归一化仍交给 `tools\repack_fzpz.py` ✓（一处一个职责 ✓）。
    """
    z = FZPZ / (p.name + ".fzpz")
    names = sorted(x.name for x in p.iterdir() if x.suffix in KEEP)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as w:
        for n in names:
            w.writestr(n, (p / n).read_bytes())
    return z, len(names)


def default_bins_dir():
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(home, "Documents", "Fritzing", "bins")


def remap_bins(pairs, bins_dir, check=False, verbose=True):
    r"""把 Fritzing 箱（`.fzb`）里对**旧 moduleId** 的引用一起改成新名 ✓（2026-10-15 补 ✗）。

    每条引用有两处（`moduleIdRef="<旧名>"` 与 `path="…/<旧名>.fzp"` ✓）⇒ **两处都要改** ✗，
    而且每条都要求**恰好一处**才动 ✓（不赌 ✗ —— 命中数不是 1 就整条跳过并点名 ✓）。
    改前先把箱**备份**到 `<箱目录的父目录>/_deploy_backup_<时间>/` ✓（不删 ✗）。

    返回 (改了几个箱, 改了几条)。判据/独立复核归 `tools\check_bins.py` ✓ —— 这里只做"顺手一起改" ✓。
    """
    if not os.path.isdir(bins_dir):
        if verbose:
            print("   （箱目录不存在 ⇒ 跳过改箱：%s）" % bins_dir)
        return 0, 0
    bins = [os.path.join(bins_dir, n) for n in sorted(os.listdir(bins_dir))
            if n.lower().endswith(".fzb")]
    bak = os.path.join(os.path.dirname(bins_dir),
                       "_deploy_backup_%s" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    n_bin = n_ref = 0
    for b in bins:
        txt = open(b, "r", encoding="utf-8", errors="replace").read()
        orig = txt
        hit = 0
        for old, new in pairs:
            p1 = re.compile(r'(moduleIdRef=")(%s)(")' % re.escape(old))
            p2 = re.compile(r'(path="[^"]*/)(%s)(\.fzp")' % re.escape(old))
            n1, n2 = len(p1.findall(txt)), len(p2.findall(txt))
            if (n1, n2) == (1, 1):
                txt = p1.sub(lambda m: m.group(1) + new + m.group(3), txt, count=1)
                txt = p2.sub(lambda m: m.group(1) + new + m.group(3), txt, count=1)
                hit += 1
            elif n1 or n2:
                print("   ✗ %s：%s 的引用 %d/%d 处（应为 1/1）⇒ **整条跳过**（不赌 ✗）"
                      % (os.path.basename(b), old, n1, n2))
        if txt == orig:
            continue
        if check:
            print("   （只查 ✓）%s：有 %d 条旧引用待改" % (os.path.basename(b), hit))
        else:
            os.makedirs(bak, exist_ok=True)
            dst = os.path.join(bak, os.path.basename(b))
            if not os.path.exists(dst):
                shutil.copy2(b, dst)
            open(b, "w", encoding="utf-8", newline="").write(txt)
        n_bin += 1
        n_ref += hit
        if verbose:
            print("   %s %s：改了 %d 条引用"
                  % ("（只查）" if check else "⇒", os.path.basename(b), hit))
    if n_bin and not check and verbose:
        print("   （箱备份：%s ✓ 不删 ✓）" % bak)
    return n_bin, n_ref


def main(argv=None):
    ap = argparse.ArgumentParser(description="给部件改 moduleId（连带 5 个文件）")
    ap.add_argument("dirs", nargs="+", help="部件目录（相对库根或绝对路径）")
    ap.add_argument("--suffix", required=True, help="要追加的后缀，如 ResistorModuleID")
    ap.add_argument("--check", action="store_true", help="只报计划，不写文件")
    ap.add_argument("--no-bins", action="store_true",
                    help="不改 Fritzing 元件箱（.fzb）里的引用（默认顺手一起改 ✓）")
    ap.add_argument("--bins-dir", default=None,
                    help="箱目录（默认 <用户>/Documents/Fritzing/bins）")
    args = ap.parse_args(argv)

    rc = 0
    pairs = []          # [(旧 moduleId, 新 moduleId)] —— 用于改元件箱里的引用 ✓
    for d in args.dirs:
        p = Path(d)
        if not p.is_absolute():
            p = ROOT / d
        if not p.is_dir():
            print("✗ 不是目录：%s" % p)
            rc = 1
            continue
        fzps = sorted(x for x in p.iterdir() if x.name.startswith("part.") and x.suffix == ".fzp")
        if len(fzps) != 1:
            print("✗ %s：找到 %d 个 fzp（应为 1 个）" % (p.name, len(fzps)))
            rc = 1
            continue
        old = fzps[0].stem[len("part."):]
        new = "%s-%s" % (old, args.suffix)
        if old.endswith("-" + args.suffix):
            # ★ 名字已合规**也要重打包** ✗ —— 上一版这里直接 `continue` ✗ ⇒
            #   “先改名、后重打包”分两次跑时会把包漏在旧名上 ✗（改名与打包不能被拆开 ✓）。
            print("   %-22s 已合规（%s）✓ %s"
                  % (p.name, args.suffix, "只查 ✓" if args.check else "重打包 ✓"))
            if not args.check:
                z, n = repack(p)
                print("   ⇒ 重打包 %s（%d 条 ✓）" % (z.name, n))
            continue
        print("== %s\n   旧: %s\n   新: %s" % (p.name, old, new))
        pairs.append((old, new))
        files = sorted(x for x in p.iterdir() if x.suffix in KEEP)
        n_ren = n_edit = 0
        for f in files:
            txt = f.read_text(encoding="utf-8")
            hit = old in f.name or old in txt
            print("   %-64s %s%s%s"
                  % (f.name, "改名" if old in f.name else "    ",
                     " " if old in f.name else "", "内容引用" if old in txt else ""))
            if not hit:
                continue
            if args.check:
                n_ren += 1 if old in f.name else 0
                n_edit += 1 if old in txt else 0
                continue
            if old in f.name:
                f.rename(f.with_name(f.name.replace(old, new)))
                n_ren += 1
            if old in txt:
                n_edit += 1
            newpath = f.with_name(f.name.replace(old, new))
            if old in txt:
                newpath.write_text(txt.replace(old, new), encoding="utf-8", newline="")
        print("   ⇒ %s：%d 个文件名改名、%d 个内容改写"
              % ("将" if args.check else "已", n_ren, n_edit))
        if not args.check:
            # ★ 重打包（**必须** ✓）：改名后 zip 的条目名不会自己跟着变 ✗。
            z, n = repack(p)
            print("   ⇒ 重打包 %s（%d 条 ✓）" % (z.name, n))
    # ★ 顺手改**元件箱**里的引用 ✓（2026-10-15 补 ✗）：漏这一步 ⇒ 点 MINE 弹「找不到 N 个元件」✗
    if pairs and not args.no_bins:
        print("== 改 Fritzing 元件箱（.fzb）里对旧名的引用")
        remap_bins(pairs, args.bins_dir or default_bins_dir(), check=args.check)
    if not args.check:
        print("★ 接着跑：py -3.13 tools\\repack_fzpz.py  →  check_deploy.py <件> --fix"
              "  →  check_bins.py（核对箱 ✓）")
    return rc


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
