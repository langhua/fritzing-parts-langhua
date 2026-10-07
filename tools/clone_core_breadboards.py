# -*- coding: utf-8 -*-
r"""★★ 把 core 的**面包板家族**克隆进本库、并按"孔只在面包板视图"改好 ✓（2026-10-05 用户定 ✓）

★★★ **已作废** ✗（2026-10-07 ✓）—— **别再跑它** ✗：
  本脚本克隆出来的 **7 件面包板**（`-LH` 系列）已于 2026-10-07 与素材目录
  `svg/_assets/core-bb/` **一并删除** ✗（提交 `b1ef9ac` ✓；README 与元件箱计数同步改过 ✓）。
  为什么删 ✓（不是"不好看"，是**冗余** ✗）：它们与 core 的面包板**结构完全相同**
  （三视图共用一个图 ✓、孔只在面包板视图声明 ✓），而草图里 `Breadboard1` 用的 `moduleIdRef`
  是 **core 的** `Breadboard-RSR03MB102-ModuleID` ✓ ⇒ 我方的 `-LH` 克隆**永远不会被引用** ✗
  （口径见 `docs/fritzing-fz-notes.md` §11 ✓）。
  ⇒ ① 素材没了 ⇒ `--import-core` 之外的分支会报错 ✓；② 就算跑起来，也只是把那 7 件冗余件
  重新塞回来 ✓。**要克隆 core 件之前，先查草图里引用的 `moduleIdRef` 到底是哪一份** ✗。

用法：
```
py -3.13 tools/clone_core_breadboards.py --import-core "<Fritzing 安装目录>\fritzing-parts"
        # ① 一次性：把用到的 core 素材收进 svg/_assets/core-bb/ ✓（随附许可 ✓）
py -3.13 tools/clone_core_breadboards.py [--only <名>] [--dry]
        # ② 生成 svg/<新名>/ ＋ fzpz/<新名>.fzpz ✓（**只读仓内** ✓，不碰安装目录 ✓）
```

## 为什么要克隆 ✓

core 的 7 件面包板**每一个孔**都在 `schematicView` / `pcbView` 里声明了连接器 ✗
（实测合计 **3130 孔 × 2 = 6260 块** ✗）⇒ 那两个视图会给孔建连接器项 ⇒ 上百条孔 bus
被塞进**那个视图的网表** ✗（**看不见** ✗）⇒ Fritzing 状态栏假报「还有 N 个连接件
没布线」✗ ＋ 画鼠线 ✗。机理全文见 `docs/fritzing-fz-notes.md` §10 ✓。

⇒ 克隆一份、**把孔的连接器只留在面包板视图** ✓（`tools/breadboard_only_views.py` 同一条规矩 ✓）。
★ 为什么**不改 core** ✗：那是安装目录 ✓（升级会冲掉 ✗）；也不该让别的草图"悄悄换件" ✗
⇒ 用**新 moduleId** ✓，与原厂件并存 ✓（老草图仍用原厂件 ✓，要干净就换件或用草图级
`fz_deglue_views.py` ✓）。

## 7 件对照表（`TABLE`，core → 本库 ✓）

| core .fzp | 标题 | 孔 | 新目录 / 新 moduleId |
|---|---|---|---|
| `breadboard2.fzp` | RSR 03MB102 Breadboard | 830 | `RSR03MB102-LH` / `Breadboard-RSR03MB102-LH-ModuleID` |
| `breadboard.fzp` | Generic Bajillion Hole Breadboard | 840 | `GenericBreadboard-LH` / `GenericBreadboard-LH-ModuleID` |
| `halfBreadboard.fzp` | Half-Breadboard | 420 | `HalfBreadboard-LH` / `HalfBreadboard-LH-ModuleID` |
| `Half_breadboard_v2.fzp` | Half breadboard | 400 | `HalfBreadboardV2-LH` / `HalfBreadboardV2-LH-ModuleID` |
| `halfMinusBreadboard.fzp` | BB-301 | 270 | `BB301-LH` / `HalfMinusBreadboard-LH-ModuleID` |
| `tinyBreadboard.fzp` | Tiny Breadboard | 200 | `TinyBreadboard-LH` / `TinyBreadboard-LH-ModuleID` |
| `miniBreadboard.fzp` | Mini Breadboard | 170 | `MiniBreadboard-LH` / `MiniBreadboard-LH-ModuleID` |

★ 标题一律 `<原厂标题> (BB only)` ✓ —— 元件箱里**一眼能认出**它是哪一版 ✓（名字你随时可改 ✓）。
★ 图形：`image=` 用**本库自己的平铺名** ✓（`breadboard/<新名>_breadboard.svg` ✓、
`icon/<新名>_icon.svg` ✓）⇒ `.fzpz` 自洽 ✓、`check_deploy` 也能按 fzp 自己声明的路径反推 ✓。
★ **部件级 4 个视图一个不少** ✓（与原厂件同形 ⇒ Fritzing 不会当它是残件 ✗），
只是**孔**不在 schematic/pcb 里声明 ✓。
"""
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "svg", "_assets", "core-bb")
sys.path.insert(0, HERE)
import breadboard_only_views as BOV                 # noqa: E402  同一份"删病块"实现 ✓

# core 名 → (新目录名, 新 moduleId, 新标题)
TABLE = [
    ("breadboard2", "RSR03MB102-LH", "Breadboard-RSR03MB102-LH-ModuleID",
     "RSR 03MB102 Breadboard"),
    ("breadboard", "GenericBreadboard-LH", "GenericBreadboard-LH-ModuleID",
     "Generic Bajillion Hole Breadboard"),
    ("halfBreadboard", "HalfBreadboard-LH", "HalfBreadboard-LH-ModuleID",
     "Half-Breadboard"),
    ("Half_breadboard_v2", "HalfBreadboardV2-LH", "HalfBreadboardV2-LH-ModuleID",
     "Half breadboard"),
    ("halfMinusBreadboard", "BB301-LH", "HalfMinusBreadboard-LH-ModuleID", "BB-301"),
    ("tinyBreadboard", "TinyBreadboard-LH", "TinyBreadboard-LH-ModuleID",
     "Tiny Breadboard"),
    ("miniBreadboard", "MiniBreadboard-LH", "MiniBreadboard-LH-ModuleID",
     "Mini Breadboard"),
]

LICENSE = """Creative Commons Attribution-ShareAlike 3.0 Unported
====================================================

These files were copied verbatim from the official Fritzing core part library
(fritzing/fritzing-parts), and are used to build the derived breadboard parts
in this repository (svg/<name>-LH/, fzpz/<name>-LH.fzpz).

  https://github.com/fritzing/fritzing-parts

Fritzing core graphics are licensed under the Creative Commons
Attribution-ShareAlike 3.0 Unported license (see LICENSE.txt in that
repository; the full description is at
http://creativecommons.org/licenses/by-sa/3.0/).

The derived parts in this repository are modified: the socket connectors are
declared only in the breadboard view (see docs/fritzing-fz-notes.md §10), so
they are distributed under the same CC-BY-SA 3.0 license.
"""


def import_core(core):
    """把用到的 core 素材收进 svg/_assets/core-bb/ ✓（只做一次 ✓）。"""
    n = 0
    for name, _d, _i, _t in TABLE:
        fzp = os.path.join(core, "core", name + ".fzp")
        if not os.path.exists(fzp):
            raise SystemExit("✗ 缺 %s" % fzp)
        shutil.copy2(fzp, os.path.join(_mk(ASSETS), name + ".fzp"))
        n += 1
        root = ET.parse(fzp).getroot()
        vw = root.find("views")
        for e in (list(vw) if vw is not None else []):
            lay = e.find("layers")
            if lay is None or not lay.get("image"):
                continue
            rel = lay.get("image").replace("/", os.sep)
            src = os.path.join(core, "svg", "core", rel)
            if not os.path.exists(src):
                raise SystemExit("✗ 缺 %s" % src)
            dst = os.path.join(ASSETS, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                n += 1
    with open(os.path.join(ASSETS, "LICENSE-core-breadboards.txt"), "w",
              encoding="utf-8", newline="\n") as w:
        w.write(LICENSE)
    print("   ✓ 入库 core 素材 %d 个 ⇒ %s ✓（+ 许可文件 ✓）"
          % (n, os.path.relpath(ASSETS, ROOT)))


def _mk(d):
    os.makedirs(d, exist_ok=True)
    return d


def build(name, dirname, newid, title, dry=False):
    fzp_in = os.path.join(ASSETS, name + ".fzp")
    text = open(fzp_in, encoding="utf-8", newline="").read()
    root = ET.fromstring(text)
    n_conn = len(root.findall("./connectors/connector"))
    n_bus = len(root.findall("./buses/bus"))

    # ① id / 标题 / 描述 ✓
    t2 = text.replace('moduleId="%s"' % root.get("moduleId"), 'moduleId="%s"' % newid, 1)
    t2 = re.sub(r"<title>[^<]*</title>", "<title>%s (BB only)</title>" % title, t2, count=1)
    t2 = re.sub(r"<description>[^<]*</description>",
                "<description>Same as the core \"%s\", but the socket connectors exist "
                "only in the breadboard view: the holes are not part of the PCB / "
                "schematic netlist (no invisible cross-view glue).</description>" % title,
                t2, count=1)
    # ② 图形指向本库自己的平铺名 ✓（先把原image 取出来 ✓，再逐字替换 ✓）
    bb = root.find("views/breadboardView/layers").get("image")
    ic_e = root.find("views/iconView/layers")
    ic = ic_e.get("image") if ic_e is not None else bb
    t2 = t2.replace('image="%s"' % bb,
                    'image="breadboard/%s_breadboard%s"'
                    % (dirname, os.path.splitext(bb)[1]))
    if ic != bb:
        t2 = t2.replace('image="%s"' % ic,
                        'image="icon/%s_icon%s"'
                        % (dirname, os.path.splitext(ic)[1]))

    # ③ ★ 病块：孔的连接器只留面包板视图 ✓（与 SYB-118 同一份实现 ✓）
    out, stat = BOV.transform(t2, n_conn)
    ET.fromstring(out)

    d = os.path.join(ROOT, "svg", dirname)
    files = {
        "part.%s.fzp" % dirname: out,
        "svg.breadboard.%s_breadboard%s" % (dirname, os.path.splitext(bb)[1]):
            open(os.path.join(ASSETS, bb.replace("/", os.sep)), "rb").read(),
        "svg.icon.%s_icon%s" % (dirname, os.path.splitext(ic)[1]):
            open(os.path.join(ASSETS, ic.replace("/", os.sep)), "rb").read(),
    }
    if dry:
        print("   （dry）%s：孔 %d ✓ bus %d ✓ 删病块 %d ✓" % (dirname, n_conn, n_bus,
                                                             stat["conn"]))
        return n_conn, n_bus, stat["conn"]
    _mk(d)
    for fn, content in files.items():
        with open(os.path.join(d, fn), "wb") as w:
            w.write(content if isinstance(content, bytes) else content.encode("utf-8"))
    pkg = os.path.join(ROOT, "fzpz", dirname + ".fzpz")
    with zipfile.ZipFile(pkg, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(files):
            z.write(os.path.join(d, fn), fn)
    zz = zipfile.ZipFile(pkg)
    assert sorted(zz.namelist()) == sorted(files), zz.namelist()
    # ★ 自检：孔的病块必须是 0 ✓；connector/bus 数与 core 一致 ✓
    bad, _info, _root2, _n2 = BOV.problems(
        zz.read("part.%s.fzp" % dirname).decode("utf-8"))
    if bad:
        raise SystemExit("✗ %s 自检不过：%s" % (dirname, bad))
    print("   ✓ %-22s 孔 %-4d bus %-4d 删病块 %-5d ⇒ svg/%s/ ＋ fzpz/%s.fzpz ✓"
          % (dirname, n_conn, n_bus, stat["conn"], dirname, dirname))
    return n_conn, n_bus, stat["conn"]


def main():
    if "--import-core" in sys.argv:
        import_core(sys.argv[sys.argv.index("--import-core") + 1])
        return 0
    if not os.path.isdir(ASSETS):
        raise SystemExit("✗ 还没有仓内素材 ⇒ 先跑 --import-core ✓")
    dry = "--dry" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    tot = [0, 0, 0]
    for name, dirname, newid, title in TABLE:
        if only and only not in (name, dirname):
            continue
        a, b, c = build(name, dirname, newid, title, dry=dry)
        tot[0] += a
        tot[1] += b
        tot[2] += c
    print("   合计：孔 %d ✓｜bus %d ✓｜删病块 %d ✓" % tuple(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
