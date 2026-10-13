#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 `fzpz/*.fzpz` 的载荷统一成「入库那份（LF）」—— 跨平台一致、可重复。

为什么需要它
------------
`.fzpz` 是 zip，里面装的是各部件目录里的那 5 个文件。老生成器在 **Windows** 上打包时，
工作区是 CRLF（本仓 `core.autocrlf=true`）⇒ **CRLF 被装进 zip** ✗，而入库那份是 LF ✓
⇒ 同一个零件在 Linux/macOS 上解出来与 `svg/` 下**逐字节不一致**，而且"重新打包一遍字节就变了" ✗。
CI（`tools/run_checks.py` 的 G4）就是照"入库那份"判的 ⇒ 会在 Linux 栏红。

本工具做三件事：
  ① 按 `svg/` 里的**入库内容**（CRLF→LF 归一化）重写每个**能对照上**的条目 ——
     ★★ 2026-10-13 修 ✓：判据 = **`svg/` 下有没有唯一同名源** ✓，
     ✗ **不是“名字里带不带 32 位 hash”** ✗（本库自己的命名规范就是
     `<字母><尺寸>_<32位hex>_<n>` ✓ ⇒ 旧判据把**所有本库件都当“另存产物”跳过** ✗
     ⇒ 改了源、包不跟着变 ✗，而 G4 闸门同样跳过 ⇒ 还报绿 ✗）；
     真的“另存”产物 = 仓库里**根本找不到**同名源 ✓ ⇒ 不用点名 hash 也认得出来 ✓；
     同名源**多于一个**时**不猜** ✗（点名报出 ✓）；
  ② **丢掉非零件条目**：`.fzpz` 里只该有 `part.*.fzp` + 4 个视图 `svg.*.svg` ✗ ——
     混进来的 `gen_part.py` 之类一律删掉（**点名报出** ✓，不静默；实测 2026-10-13 只有
     `Capacitor-0402.fzpz` 里有一份 ✗）；
  ③ 给所有条目**固定时间戳**（1980-01-01）⇒ 在哪个平台跑、跑几次，产物都**逐字节相同** ✓。

用法::

    py -3.13 tools\\repack_fzpz.py            # 就地重打包（只改需要改的）
    py -3.13 tools\\repack_fzpz.py --check    # 只看差多少、不写文件（有差异退出码 1）

★ 实测教训（2026-10-13 ✓）：`add_resistance.py` 改完 10 档电阻的 fzp 后跑旧版本工具 ⇒
  报“已重打包 1 个”（只有不带 hash 的 `ATECC608B` ✓）✗ —— 而那 10 个 `Resistor-*.fzpz`
  里的 `part.R…_<32hex>_1.fzp` 与源**内容已经不同** ✗ 却没被改 ✗。
  ⇒ **“跳过”的判据写错时，工具会安静地少干活** ✗（比报错难查 ✓）。

★ 边界：它**不改**任何 `svg/` 下的源文件，也不"修"零件本身；只让 zip 载荷与入库源一致。
"""
import argparse
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FZPZ = ROOT / "fzpz"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
# ★ 2026-10-13：`HASH_RE` 已删 ✓ —— 拿“名字里带 32 位 hash”当“另存产物”是**错的** ✗
#   （本库自己的 moduleId 就带 hash ✓）⇒ 判据改用“svg/ 下有没有唯一同名源” ✓。


def norm(b):
    """入库那份 = LF（git 归一化后的形态）⇒ 工作区 CRLF 不算差异。"""
    return b.replace(b"\r\n", b"\n")


def build_index():
    """svg/ 下所有文件：basename -> [路径…]（与 run_checks 的 G4 同一套对照口径）。"""
    idx = {}
    for root, _dirs, files in os.walk(ROOT / "svg"):
        for f in files:
            idx.setdefault(f, []).append(Path(root) / f)
    return idx


def repack_one(zpath, idx, check_only):
    """返回 (是否与原文件不同, 改写条目数, 保留条目数, 丢掉的非零件条目, 同名源不唯一的条目)。"""
    with zipfile.ZipFile(zpath) as zf:
        entries = [(i.filename, zf.read(i.filename)) for i in zf.infolist()]

    new_entries, changed, kept, dropped, ambiguous = [], 0, 0, [], []
    for name, data in entries:
        if Path(name).suffix.lower() not in (".svg", ".fzp"):
            dropped.append(name)          # 零件包里只该有这两类 ⇒ 丢掉（点名报出）
            continue
        cand = idx.get(os.path.basename(name))
        if cand and len(cand) == 1:
            want = norm(cand[0].read_bytes())      # ★ 有唯一同名源 ⇒ 一律以源为准 ✓
        else:
            if cand:                               # 同名源有多个 ⇒ 判不准，别猜 ✗（点名报出）
                ambiguous.append("%s（svg/ 下有 %d 个同名文件）" % (name, len(cand)))
            want = data
            kept += 1
        if want != data:
            changed += 1
        new_entries.append((name, want))

    buf = Path(str(zpath) + ".tmp")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in new_entries:
            zi = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, data)
    same = buf.read_bytes() == zpath.read_bytes()
    if check_only or same:
        buf.unlink()
        return (not same), changed, kept, dropped, ambiguous
    buf.replace(zpath)
    return True, changed, kept, dropped, ambiguous


def main(argv):
    ap = argparse.ArgumentParser(description="把 fzpz 载荷统一成入库那份（LF）")
    ap.add_argument("--check", action="store_true", help="只检查、不写文件")
    args = ap.parse_args(argv)

    if not FZPZ.is_dir():
        print("没有 fzpz/ 目录")
        return 2
    idx = build_index()
    zips = sorted(FZPZ.glob("*.fzpz"))
    n_repack = n_entries = n_kept = 0
    for z in zips:
        diff, changed, kept, dropped, ambiguous = repack_one(z, idx, args.check)
        n_entries += changed
        n_kept += kept
        if dropped:
            print("  %s：丢掉非零件条目 %s" % (z.name, ", ".join(dropped)))
        for a in ambiguous:
            print("  %s：✗ 同名源不唯一，未对账：%s" % (z.name, a))
        if diff:
            n_repack += 1
            print("  %s %s（改写 %d 条，保留 %d 条）"
                  % ("需要重打包" if args.check else "已重打包", z.name, changed, kept))
    print("零件 %d 个：%s %d 个；改写条目 %d 条；原样保留（svg/ 下找不到同名源）%d 条"
          % (len(zips), "需重打包" if args.check else "已重打包", n_repack, n_entries, n_kept))
    if args.check and n_repack:
        print("★ 跑 `py -3.13 tools\\repack_fzpz.py` 就地修掉")
        return 1
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:                                        # noqa: BLE001
            pass
    sys.exit(main(sys.argv[1:]))
