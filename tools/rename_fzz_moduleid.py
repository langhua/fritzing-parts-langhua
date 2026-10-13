# -*- coding: utf-8 -*-
r"""把 `.fzz` 里**旧 moduleId 换成新名** ✓（几何一个字不动 ✗）—— 2026-10-13 立

起因 ✓：本库 23 件按 Fritzing 的「件类型后缀」改了 `moduleId`（规则见库仓 `AGENTS.md` §5 ✓）——
  新名 = `<旧名>-<后缀>`（`-ResistorModuleID` / `-CapacitorModuleID` / … ✓）。
  ⇒ 项目仓里**已经做好**的草图仍写着旧名 ✗（Fritzing 认不出件类型 ⇒ **属性面板整块只读** ✗）。

它做什么 ✓（**只改名字，不碰几何** ✗）：
  ① 包内条目 `part.<旧名>.fzp`  → **改名**为 `part.<新名>.fzp` ✓
  ② 该 `.fzp` 内容里的 `moduleId="<旧名>"` → 新名 ✓
  ③ `.fz` 主文件里的 `moduleIdRef="<旧名>"` → 新名 ✓、`path="…/<旧名>.fzp"` → 新名 ✓
  ④ **其它条目逐字节照搬** ✓（连线、几何、属性值全不动 ✓）

映射**不硬编码** ✗：从库仓 `svg/<目录>/part.<moduleId>.fzp` 的**文件名**自动推 ✓ ——
  新名 = `part.` 与 `.fzp` 之间那串 ✓；旧名 = 新名去掉末尾 `-<后缀>`（后缀 = 最后一个 `-` 之后 ✓）✓。

用法（在库仓根 ✓）：
    py -3.13 tools/rename_fzz_moduleid.py --check  <a.fzz> [<b.fzz> …]     # 只看要改几处 ✓
    py -3.13 tools/rename_fzz_moduleid.py --apply  <a.fzz> [<b.fzz> …]     # 原地改（先留 .bak ✓）
    py -3.13 tools/rename_fzz_moduleid.py --apply --no-bak <a.fzz>
"""
import os
import pathlib
import re
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent
LIB_SVG = HERE.parent / "svg"

# 后缀全表 = Fritzing 认的「件类型后缀」（`partfactory.cpp` / `propertydef.cpp` ✓）
SUFFIXES = ("ResistorModuleID", "CapacitorModuleID", "CrystalModuleID",
            "InductorModuleID", "ColorLEDModuleID", "LEDModuleID",
            "ThermistorModuleID", "PotentiometerModuleID", "ZenerDiodeModuleID")


def build_map():
    """{旧名: 新名} ✓ —— 从库仓每个部件目录的 `part.<moduleId>.fzp` 文件名推 ✓

    ★ 必须**递归** ✗：有的部件在子目录里（`svg/molding_power_inductors/SHC0420/part.*.fzp` ✗）——
      只扫一层会**静默漏掉 6 个电感** ✗（实测 19 → 17 条就是这么漏的 ✓）。
    """
    m, dirs = {}, set()
    for f in sorted(LIB_SVG.rglob("part.*.fzp")):
        new = f.name[len("part."):-len(".fzp")]
        for s in SUFFIXES:
            if new.endswith("-" + s):
                m[new[: -(len(s) + 1)]] = new
                dirs.add(str(f.parent.relative_to(LIB_SVG)))
                break
    print("   （扫到带后缀的件目录：%s）" % ", ".join(sorted(dirs)))
    return m


def plan_for(fzz, mp):
    """返回 [(旧名, 新名)] ✓（这个包里真正要用到的 ✓）"""
    with zipfile.ZipFile(fzz) as z:
        names = z.namelist()
        fz = [n for n in names if n.endswith(".fz")]
        if not fz:
            return [], "包里没有 .fz"
        text = z.read(fz[0]).decode("utf-8", "replace")
    used = set(re.findall(r'moduleIdRef="([^"]+)"', text))
    # 条目名也可能是旧名（`part.<旧名>.fzp`）
    for n in names:
        if n.startswith("part.") and n.endswith(".fzp"):
            used.add(n[len("part."):-len(".fzp")])
    return sorted((o, mp[o]) for o in used if o in mp), None


def rewrite(fzz, mp, pairs, keep_bak):
    if keep_bak:
        bak = str(fzz) + ".bak-rename"
        if not os.path.exists(bak):
            shutil.copy2(fzz, bak)
    zin = zipfile.ZipFile(fzz)
    items = zin.infolist()
    out = fzz.with_suffix(".fzz.tmp")
    n_ent = n_txt = n_ref = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in items:
            name, data = it.filename, zin.read(it.filename)
            newname = name
            for old, new in pairs:
                if name == "part.%s.fzp" % old:
                    newname = "part.%s.fzp" % new
                    n_ent += 1
            if newname.endswith((".fz", ".fzp")):
                t = data.decode("utf-8", "replace")
                t2 = t
                for old, new in pairs:
                    t2 = t2.replace('moduleIdRef="%s"' % old, 'moduleIdRef="%s"' % new)
                    t2 = t2.replace('moduleId="%s"' % old, 'moduleId="%s"' % new)
                    t2 = t2.replace("/%s.fzp" % old, "/%s.fzp" % new)
                if t2 != t:
                    n_txt += 1
                    data = t2.encode("utf-8")
            zi = zipfile.ZipInfo(newname, date_time=it.date_time)
            zi.compress_type = it.compress_type
            zi.external_attr = it.external_attr
            zo.writestr(zi, data)
    zin.close()
    os.replace(out, fzz)
    return n_ent, n_txt


def main(argv):
    mp = build_map()
    print("★ 库仓后缀件映射：%d 条 ✓" % len(mp))
    apply_ = "--apply" in argv
    keep_bak = "--no-bak" not in argv
    files = []
    for a in argv:
        if a.startswith("--"):
            continue
        p = pathlib.Path(a)
        if p.is_dir():
            files.extend(sorted(p.glob("*.fzz")))      # 只取该目录**直接子层** ✓（历史版目录不动 ✗）
        elif p.suffix.lower() == ".fzz":
            files.append(p)
    print("★ 待处理 %d 个 .fzz ✓" % len(files))
    if not files:
        print("用法：py -3.13 tools/rename_fzz_moduleid.py --check|--apply <a.fzz|目录> …")
        return 2
    bad = 0
    for f in files:
        pairs, err = plan_for(f, mp)
        if err:
            print("-- %s  ✗ %s" % (f.name, err))
            bad += 1
            continue
        if not pairs:
            print("-- %-34s **不用改** ✓（没有旧名件 ✓）" % f.name)
            continue
        print("-- %-34s 要改 %d 处：%s" % (f.name, len(pairs),
                                        ", ".join("%s→%s" % (o[:26], n.split("-")[-1]) for o, n in pairs)))
        if apply_:
            e, t = rewrite(f, mp, pairs, keep_bak)
            print("     已改：条目改名 %d、文本改写 %d 个文件%s" % (e, t, "（留 .bak-rename ✓）" if keep_bak else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
