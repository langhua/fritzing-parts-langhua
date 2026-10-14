#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""check_bins.py —— 核对「Fritzing 元件箱（`.fzb`）里的引用」是否都装得上（只读 ✓，可选 --fix）。

为什么需要它（2026-10-15 用户实测 ✗）
-----------------------------------------------------------------------------
用户点元件面板的 **MINE** 箱，Fritzing 弹框：

    「不能够找到如下 18 个元件：  R0603_36137a0f…_1.fzp …」
    （源码出处 = `src/model/modelbase.cpp:418` ✓：
       `.arg(tr("Unable to find the following %n part(s): ", "", missingModules.count()))` ✓）

真因 ✓：2026-10-13 那轮「`moduleId` 加类型后缀」（`R0603_…_1` → `…_1-ResistorModuleID` ✓，
见 `tools\rename_moduleid.py` 的说明）**只改了 `parts/user`** ✗ ——
**Fritzing 自维护的 MINE 箱**（`<Documents>/Fritzing/bins/my_parts.fzb` ✓，
出处 = `partsbinpalette/binmanager/binmanager.cpp:920` `MyPartsBinLocation` ✓）
里那 18 条引用（`moduleIdRef=` **和** 它带的 `path=`）**还是旧名** ✗ ⇒
箱一加载就报"找不到件" ✗。**我自己生成的箱没这个问题**（`fzh_*.fzb` 全对 ✓）⇒
漏的正是"改名要**同批**改到**箱**"这一步 ✗（AGENTS §5「改件名 = 改身份证」原来只写到草图 ✗）。

箱文件长什么样（`.fzb` = XML ✓，照 `my_parts.fzb` 实测 ✓）：

    <module fritzingVersion="…" icon="Mine.png">
      <title>My Parts</title>
      <instances>
        <instance moduleIdRef="<moduleId>" modelIndex="…" path="…/parts/user/<moduleId>.fzp">
            <views/>
        </instance>
        …
      </instances>
    </module>

  ⇒ 判据 = **每条 `moduleIdRef` 都要能在"已装的件"里解析出来** ✓；
     `path=` 是它当初记的路径（同一条引用的一部分 ⇒ `--fix` 时一起改 ✓）。

"已装的件"从哪来 ✓（**别只量 MINE** ✗ —— 我第一版只拿 `parts/user` 当尺子，
  于是把 Fritzing **自带** `fritzing-parts/{core,obsolete}` 里还存在的
  `2910BBEC34` / `603ColorLEDModuleID` 也报成"缺"✗，而 Fritzing 其实找得到、**不报** ✓）：
  · MINE 的 `parts/user/*.fzp`（我们部署进去的 ✓）
  · Fritzing 自带的 `fritzing-parts/{core,obsolete,contrib}/*.fzp`（能自动找到就用 ✓）
  · `--parts-dir` 额外追加 ✓

哪些箱判 FAIL（分档，理由同 AGENTS §14 ✓）
-----------------------------------------------------------------------------
  · **判 FAIL**：`my_parts.fzb`（Fritzing 自维护的 MINE 箱 ✓）与 `fzh_*.fzb`（我们自己生成的箱 ✓）
    —— 这两个点开就会弹框，是我们的账 ✗；
  · **只报告**：别人的箱（Adafruit / Alligator…）—— 那些件**本来就没装**
    （本机实测：`fritzing-parts/contrib` 是空的 ✓），不是我们的账；加 `--all` 才一起判 ✗。

用法::

    py -3.13 tools\check_bins.py                      # 查默认箱目录，只读
    py -3.13 tools\check_bins.py --bins-dir D:\x
    py -3.13 tools\check_bins.py --parts-dir D:\y     # 追加"已装的件"目录
    py -3.13 tools\check_bins.py --all                # 第三方箱也判 FAIL
    py -3.13 tools\check_bins.py --fix                # 把能**唯一映射**的旧名改成新名（先备份 ✓，不删 ✗）
    py -3.13 tools\check_bins.py --fix --dry-run      # 只报要改什么

`--fix` 的映射规则（**保守** ✓）：旧名 `old` ⇒ 在已装的件里找 `old + "-" + <后缀>` 若**恰好一个**就映射 ✓
  （`ResistorModuleID` / `CapacitorModuleID` / `InductorModuleID` / `CrystalModuleID` /
    `LEDModuleID` … 全适用 ✓）；找不到、或找到多个 ⇒ **这条不动、只点名** ✗（不许乱猜 ✓）。

退出码：0 = 该判的都解析得到 ✓；1 = 有 ✗；2 = 明确跳过（箱目录不存在 ⇒ 没装 Fritzing / 换了机器）。

★ 为什么不进 CI ✗：它要**本机** Fritzing 的箱目录（`Documents/Fritzing/bins` ✓）——
  与 `tools\check_deploy.py` 同一档 ⇒ 一样只在本机跑 ✓（AGENTS §14 ✓）。
"""
import argparse
import datetime
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# 我们自己的箱名前缀（与 tools/make_fzb.py 的 BIN_PREFIX 一致 ✓）
OUR_BIN_PREFIX = "fzh_"
# Fritzing 自维护的箱（MINE 面板点开就是它 ✓）
MINE_BIN = "my_parts.fzb"

MOD_ATTR = re.compile(r"""<module\b[^>]*?\bmoduleId\s*=\s*["']([^"']+)["']""")
REF = re.compile(r"""moduleIdRef\s*=\s*["']([^"']+)["']""")


def home_dir():
    return os.environ.get("USERPROFILE") or os.path.expanduser("~")


def default_bins():
    return os.path.join(home_dir(), "Documents", "Fritzing", "bins")


def default_mine_parts():
    return os.path.join(home_dir(), "Documents", "Fritzing", "parts")


def fritzing_parts_dirs():
    """Fritzing 自带件库的候选位置（找不到就空着 ✓ —— 少一处只是少一格尺子 ✗ 要说出来 ✓）。"""
    cands = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Fritzing", "fritzing-parts"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Fritzing", "fritzing-parts"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Fritzing", "fritzing-parts"),
    ]
    return [c for c in cands if c and os.path.isdir(c)]


def read_text(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def installed(parts_dirs):
    """moduleId -> 来源说明（fzp 文件名 或 <fritzing:core>/x.fzp）。"""
    idx = {}
    for d in parts_dirs:
        user = os.path.join(d, "user")
        subs = [user] if os.path.isdir(user) else []
        for sub in ("core", "obsolete", "contrib"):
            if os.path.isdir(os.path.join(d, sub)):
                subs.append(os.path.join(d, sub))
        for sub in subs:
            tag = "<fritzing:%s>" % os.path.basename(sub) if "user" not in sub else ""
            for name in sorted(os.listdir(sub)):
                if not name.lower().endswith(".fzp"):
                    continue
                m = MOD_ATTR.search(read_text(os.path.join(sub, name)))
                if m:
                    idx.setdefault(m.group(1), tag + name)
    return idx


def bin_refs(path):
    """返回 [(moduleIdRef, 整条 <instance …> 原文)]（跳过 __spacer__ ✓）。"""
    txt = read_text(path)
    out = []
    for blk in re.findall(r"<instance\b[^>]*>", txt):
        m = REF.search(blk)
        if m and m.group(1) != "__spacer__":
            out.append((m.group(1), blk))
    return txt, out


def main(argv=None):
    ap = argparse.ArgumentParser(description="核对 Fritzing 元件箱（.fzb）里的引用是否都装得上")
    ap.add_argument("--bins-dir", default=None, help="箱目录（默认 <Documents>/Fritzing/bins）")
    ap.add_argument("--parts-dir", action="append", default=[],
                    help="额外的“已装的件”目录（可给多次；MINE 的 parts 会自动带上）")
    ap.add_argument("--all", action="store_true", help="第三方箱也判 FAIL（默认只报告）")
    ap.add_argument("--fix", action="store_true", help="把能唯一映射的旧名改成新名（先备份 ✓）")
    ap.add_argument("--dry-run", action="store_true", help="--fix 时只报要改什么，不写文件")
    args = ap.parse_args(argv)

    bins_dir = args.bins_dir or default_bins()
    if not os.path.isdir(bins_dir):
        print("!! 箱目录不存在：%s" % bins_dir)
        print("   （没装 Fritzing 或换了机器 ⇒ 本项**明确跳过**，不算通过 ✗）")
        return 2

    parts_dirs = [default_mine_parts()] + args.parts_dir
    parts_dirs = [d for d in parts_dirs if os.path.isdir(d)]
    extra = fritzing_parts_dirs()
    parts_dirs += extra
    have = installed(parts_dirs)

    print("箱目录：%s" % bins_dir)
    print("已装的件：%d 个 moduleId（来自 %d 个目录）" % (len(have), len(parts_dirs)))
    for d in parts_dirs:
        print("   · %s" % d)
    if not extra:
        print("   ⚠ 没找到 Fritzing 自带的 fritzing-parts（core/obsolete）⇒ 尺子偏窄，"
              "自带件会被误报成“缺” ✗ —— 用 --parts-dir 补上 ✓")

    bins = sorted(n for n in os.listdir(bins_dir) if n.lower().endswith(".fzb"))
    judged = [n for n in bins if n == MINE_BIN or n.startswith(OUR_BIN_PREFIX)]
    print("\n箱 %d 个：判 FAIL %d 个（%s / %s*）、只报告 %d 个"
          % (len(bins), len(judged), MINE_BIN, OUR_BIN_PREFIX, len(bins) - len(judged)))

    rc = 0
    fix_plan = []          # [(bin路径, 旧名, 新名)]
    for name in bins:
        p = os.path.join(bins_dir, name)
        _txt, refs = bin_refs(p)
        if not refs:
            continue
        uniq = sorted({r for r, _ in refs})
        miss = [r for r in uniq if r not in have]
        is_judged = name in judged
        tag = "判 FAIL" if is_judged else ("只报告" if not args.all else "判 FAIL(--all)")
        if not miss:
            if is_judged or args.all:
                print("  ✓ %-26s 引用 %3d 条，全部解析得到 ✓" % (name, len(refs)))
            continue
        print("  ✗ %-26s 引用 %3d 条，解析不到 %d 条  [%s]"
              % (name, len(refs), len(miss), tag))
        for r in miss[:12]:
            cand = sorted(k for k in have if k.startswith(r + "-"))
            hint = ("→ %s" % cand[0]) if len(cand) == 1 else \
                   ("→ 多个候选 %s（不动 ✗）" % cand[:3]) if cand else "→ 没有同名新件（件真的不在 ✗）"
            print("        ✗ %s  %s" % (r, hint))
            if len(cand) == 1:
                fix_plan.append((p, r, cand[0]))
        if len(miss) > 12:
            print("        …（还有 %d 条）" % (len(miss) - 12))
        if is_judged or args.all:
            rc = 1

    if not fix_plan:
        print("\n结论：%s" % ("该判的箱全部解析得到 ✓" if rc == 0
                              else "有箱引用了解析不到的件 ✗（见上）"))
        return rc

    print("\n可修的 %d 条（旧名 → 新名，唯一映射 ✓）：" % len(fix_plan))
    for p, old, new in fix_plan:
        print("   %s\n      %s → %s" % (os.path.basename(p), old, new))
    if not args.fix:
        print("\n（只报告：要改就加 --fix ✓；它会先把箱备份到 _deploy_backup_<时间>/ ✓）")
        return rc

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(os.path.dirname(bins_dir), "_deploy_backup_%s" % ts)
    fixed = {}
    for p, old, new in fix_plan:
        if args.dry_run:
            continue
        if not os.path.isdir(bak):
            os.makedirs(bak, exist_ok=True)
        if os.path.basename(p) not in os.listdir(bak):
            shutil.copy2(p, os.path.join(bak, os.path.basename(p)))
        txt = read_text(p)
        # moduleIdRef 与 path 一起改；每条都要求**恰好一处**，否则整条跳过（不赌 ✓）
        p1 = re.compile(r'(moduleIdRef=")' + re.escape(old) + r'(")')
        p2 = re.compile(r'(path="[^"]*/)' + re.escape(old) + r'(\.fzp")')
        n1, n2 = len(p1.findall(txt)), len(p2.findall(txt))
        if (n1, n2) != (1, 1):
            print("   ✗ %s：%s 的 moduleIdRef %d 处 / path %d 处 ⇒ 跳过（不赌 ✗）"
                  % (os.path.basename(p), old, n1, n2))
            continue
        txt = p1.sub(r"\g<1>" + new + r"\g<2>", txt, count=1)
        txt = p2.sub(r"\g<1>" + new + r"\g<2>", txt, count=1)
        fixed[p] = txt
    if args.dry_run:
        print("\n（--dry-run：未写文件）")
        return rc
    for p, txt in fixed.items():
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(txt)
    if fixed:
        print("\n备份：%s" % bak)
    for p in fixed:
        print("   已写回 %s" % p)

    # ★ 独立复核：从磁盘重读一遍，看还有没有解析不到的 ✗（不许自证 ✓）
    print("\n复核（重新读盘）：")
    left = 0
    for name in judged:
        p = os.path.join(bins_dir, name)
        if not os.path.isfile(p):
            continue
        _t, refs = bin_refs(p)
        miss = sorted({r for r, _ in refs} - set(have))
        left += len(miss)
        print("   %-26s 解析不到 %d 条" % (name, len(miss)))
        for r in miss[:8]:
            print("        ✗ %s" % r)
    print("\n结论：%s" % ("该判的箱已无解析不到的引用 ✓（重启 Fritzing 再看箱 ✓）"
                        if left == 0 else "仍有 %d 条 ✗" % left))
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
