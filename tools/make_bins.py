# -*- coding: utf-8 -*-
"""生成 Fritzing 的**分类元件箱**（`.fzb`）—— 分类表与 README 预览图**同源**。

分类的唯一来源 = `tools/make_preview.py` 的 `SHEETS`（README 那 6 张预览图就是它拼的），
所以「README 里看到的分组」与「Fritzing 里看到的箱」永远一致。

机制（已在本机 Fritzing 1.0.3b 的源码与文件上核实，不是猜的）：

- 用户箱目录 = `<Documents>/Fritzing/bins`；Fritzing 启动时**扫描其中全部 `*.fzb`**，
  每个文件 = 元件面板里的一个箱（`binmanager.cpp`：`QDir userBinsDir(FolderUtils::getUserBinsPath());
  findBins(userBinsDir, locations, BinLocation::User);`）。
- 箱文件格式 = `<module><title>…</title><instances><instance moduleIdRef=… path=…/></instances></module>`
  （照 `my_parts.fzb` 实测格式）。
- ★ **每条 `<instance>` 必须带 `<views/>`**：`modelbase.cpp` 的加载循环里有
  `if (views.isNull() || view.isNull()) { // do not load a part with no views … continue; }`
  —— 少了它，箱是空的。
- ★ **箱图标要内嵌 SVG 文本**：`icon="…"` 里写的不是文件名，而是**整段 SVG 源码**，
  而且必须含 `<title>Fritzing Custom Icon</title>`（`partsbinpalettewidget.cpp`：
  `isCustomSvg(s) = s.startsWith("<?xml") && s.contains("Fritzing Custom Icon")`）——
  不满足就退回内置图标，**6 个箱全长成 MINE、看不出区别**（踩过）。
  本工具用每组代表零件**自己的 icon 几何**缩进 64×64 画布当箱图标（不手绘）。
- `modelIndex` **不写**：那是 Fritzing 保存时的运行时编号，不是箱文件的要求。
- 箱里存的是**零件引用**（`path` 指到已安装的 `.fzp`），不是拷贝；零件一动，那条就失效。

**只写 `fzh_*.fzb`**（本工具自己的前缀）：`my_parts.fzb`（Fritzing 自维护的「我的零件」箱）
与别人的箱一律不碰。

用法：
    python tools/make_bins.py                 # 写进 ~/Documents/Fritzing/bins（会先报告匹配情况）
    python tools/make_bins.py --list          # 只报告，不写文件
    python tools/make_bins.py --bins-dir D:\\x --parts-dir D:\\y    # 换目录（别的机器/别的盘）
"""
import re
import sys
import pathlib
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_preview import (SHEETS, SVG_DIR, ROOT_RE, ATTR_RE, find_icon,   # noqa: E402
                          viewbox_of, strip_shell, namespace, scope_style)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = pathlib.Path.home()
DEF_FRITZING = HOME / "Documents" / "Fritzing"
BIN_PREFIX = "fzh_"          # 我们生成的箱文件名前缀（别与 my_parts.fzb / 别人的箱混）
HASH_RE = re.compile(r"_[0-9a-f]{16,}_\d+$")
TRAIL_RE = re.compile(r"_\d+$")

# 箱图标：Fritzing 只认「内嵌在 icon="…" 里的 SVG 文本」，而且该 SVG 里必须含这句 title
# （`partsbinpalettewidget.cpp`：`isCustomSvg(s) = s.startsWith("<?xml") && s.contains(CustomIconTitle)`，
#  CustomIconTitle = "Fritzing Custom Icon"）。否则退回内置图标 —— 6 个箱就全长成 MINE。
ICON_MARKER = "Fritzing Custom Icon"
ICON_BOX, ICON_PAD = 64.0, 2.0        # 图标画布 64×64（QtSvg 按 viewBox 出图）
# 每组拿哪个零件当箱图标（要一眼能认出来；顺便选了体积小的 icon）
BIN_ICON_OF = {
    "chips": "CH32V203C8T6",        # QFP48 顶视
    "power": "Li300mAh",            # 电池
    "modules": "ESP32-S3-WROOM-1",  # 带天线模块
    "conn": "TypeC16Pin",           # USB-C 座
    "passive": "Resistor-0603",     # 贴片电阻
    "discrete": "BAT54S",           # SOT-23 三脚
}


def base(key):
    """去掉导入时加在 moduleId 尾部的 `_<hash>_<n>`（R0201_0907…_1 → R0201）。"""
    return HASH_RE.sub("", key).rstrip("_")


def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def installed_index(parts_dir):
    """已装零件索引：四条键（原名 / 去 hash 名 / 去尾号名 / 归一化名）→ `.fzp` 路径。"""
    exact, by_base, by_tail, by_norm = {}, {}, {}, {}
    files = []
    for sub in ("user", "contrib"):
        root = parts_dir / sub
        if root.is_dir():
            files += sorted(root.rglob("*.fzp"))
    for p in files:
        stem = p.name[:-4]
        exact.setdefault(stem, p)
        exact.setdefault(stem.rstrip("_"), p)
        by_base.setdefault(base(stem), p)
        by_tail.setdefault(TRAIL_RE.sub("", base(stem)), p)   # `NetLabel-Pad_1` → `NetLabel-Pad`
        by_norm.setdefault(norm(base(stem)), p)
    return exact, by_base, by_tail, by_norm, files


def repo_module_id(part_dir):
    """仓库里这个部件自己的 `part.*.fzp` 声明的 moduleId（匹配的首选键）。"""
    hits = sorted(part_dir.glob("part.*.fzp"))
    if not hits:
        return None
    m = re.search(r'\bmoduleId="([^"]+)"', hits[0].read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def module_id_of(fzp_path):
    """已装 `.fzp` 自己声明的 `moduleId`（权威）—— 文件名只是兜底（如 `LCD1602-I2C_.fzp`）。

    箱里的 `moduleIdRef` 必须能被 Fritzing 的 `retrieveModelPart(moduleIdRef)` 查到，
    所以用零件自己声明的那个值，不用文件名猜。
    """
    m = re.search(r'\bmoduleId="([^"]+)"',
                  fzp_path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else fzp_path.name[:-4].rstrip("_")


def match(entry, index):
    """把一个预览图条目（分组里的 `svg` 子目录 + 显示名）对到已装零件。"""
    sub, label = entry
    exact, by_base, by_tail, by_norm, _ = index
    mid = repo_module_id(SVG_DIR / sub)
    keys = [k for k in (mid, base(mid or ""), label, sub.split("/")[-1]) if k]
    for k in keys:
        if k in exact:
            return exact[k], f"moduleId 精确匹配（{k}）"
        if base(k) in by_base:
            return by_base[base(k)], f"moduleId 去 hash 匹配（{base(k)}）"
        if TRAIL_RE.sub("", base(k)) in by_tail:
            got = TRAIL_RE.sub("", base(k))
            return by_tail[got], f"名称去尾号匹配（{got}）"
        if norm(k) in by_norm:
            return by_norm[norm(k)], f"名称归一化匹配（{k}）"
    return None, f"未装（试过：{'、'.join(keys)}）"


def bin_icon_svg(sub, key):
    """一个箱的图标：把该组代表零件**自己的 icon 几何**缩进 64×64 方框（不手绘）。

    用 `transform` 把源 viewBox 映射进方框（不靠嵌套 `<svg>`，少一层渲染器差异）。
    """
    icon = find_icon(SVG_DIR / sub)
    txt = icon.read_text(encoding="utf-8")
    m = ROOT_RE.search(txt)
    attrs = dict(ATTR_RE.findall(m.group(1)))
    vb = [float(v) for v in re.split(r"[\s,]+", viewbox_of(attrs, icon.name).strip())]
    inner = scope_style(namespace(strip_shell(txt[m.end():].rsplit("</svg>", 1)[0]), key), key)
    s = min((ICON_BOX - 2 * ICON_PAD) / vb[2], (ICON_BOX - 2 * ICON_PAD) / vb[3])
    cx, cy = vb[0] + vb[2] / 2, vb[1] + vb[3] / 2
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{ICON_BOX:g}" height="{ICON_BOX:g}" viewBox="0 0 {ICON_BOX:g} {ICON_BOX:g}">\n'
            f'<title>{ICON_MARKER}</title>\n'
            f'<g id="{key}" transform="translate({ICON_BOX / 2:g},{ICON_BOX / 2:g}) scale({s:.6g}) '
            f'translate({-cx:g},{-cy:g})">\n{inner}\n</g>\n</svg>\n')


def fzb_text(title, members, fritzing_version, icon_text):
    ver = f' fritzingVersion="{fritzing_version}"' if fritzing_version else ""
    icon_attr = saxutils.escape(icon_text, {'"': "&quot;"})      # 整段 SVG 进属性
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<!-- 由 fritzing-parts-langhua 的 tools/make_bins.py 生成（勿手改） -->',
             f'<module{ver} icon="{icon_attr}">',
             f'    <title>{title}</title>',
             '    <instances>']
    for module_id, path in members:
        lines.append(f'        <instance moduleIdRef="{module_id}" '
                     f'path="{path.as_posix()}">')
        lines.append('            <views/>')
        lines.append('        </instance>')
    lines += ['    </instances>', '</module>', '']
    return "\n".join(lines)


def read_version(bins_dir):
    """箱文件的 `fritzingVersion` 照抄用户自己那份 `my_parts.fzb`（= 他的 Fritzing 版本）。"""
    f = bins_dir / "my_parts.fzb"
    if f.is_file():
        m = re.search(r'fritzingVersion="([^"]+)"', f.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return ""


def verify(bins_dir, quiet=False):
    """自检写出的箱：`<views/>` 齐不齐、`path` 真存在、`moduleIdRef` 与该 .fzp 声明的一致。

    这三条都是“不报错但箱子是空的”那种失效，所以要能当场看见（判据都有源码依据）。
    """
    bad, total = 0, 0
    for f in sorted(bins_dir.glob(f"{BIN_PREFIX}*.fzb")):
        root = ET.fromstring(f.read_text(encoding="utf-8"))
        icon = root.get("icon") or ""
        if not (icon.startswith("<?xml") and ICON_MARKER in icon):
            bad += 1
            print(f"  !! 箱图标不是内嵌自定义 SVG（会退回内置 MINE 图标）：{f.name}")
        for it in root.findall("./instances/instance"):
            total += 1
            p = pathlib.Path(it.get("path") or "")
            if it.find("views") is None:
                bad += 1
                print(f"  !! 缺 <views/>：{f.name} {it.get('moduleIdRef')}")
            elif not p.is_file():
                bad += 1
                print(f"  !! path 不存在：{f.name} → {p}")
            elif module_id_of(p) != it.get("moduleIdRef"):
                bad += 1
                print(f"  !! moduleId 不一致：{f.name} 写 {it.get('moduleIdRef')!r}，"
                      f"{p.name} 里是 {module_id_of(p)!r}")
    if not quiet:
        print(f"自检：{total - bad}/{total} 条引用落地" + ("，全部通过" if bad == 0 else f"，{bad} 处有问题"))
    return bad


def main():
    args = sys.argv[1:]

    def opt(name, default):
        return pathlib.Path(args[args.index(name) + 1]) if name in args else default

    fritzing = opt("--fritzing-dir", DEF_FRITZING)
    bins_dir = opt("--bins-dir", fritzing / "bins")
    parts_dir = opt("--parts-dir", fritzing / "parts")
    write = "--list" not in args

    if not bins_dir.is_dir():
        raise SystemExit(f"!! 箱目录不存在：{bins_dir}\n"
                         f"   （Fritzing 的箱目录应形如 <用户目录>/Documents/Fritzing/bins；"
                         f"用 --bins-dir 指定）")
    if "--verify" in args and "--list" in args:
        raise SystemExit(verify(bins_dir))

    index = installed_index(parts_dir)
    print(f"已装零件：{len(index[4])} 个 .fzp（{parts_dir}\\user、\\contrib；"
          f"归一化后不重名的 {len(index[3])} 个）")
    print(f"箱目录：  {bins_dir}\n")

    version = read_version(bins_dir)
    verbose = "--verbose" in args or "-v" in args
    total_parts, total_written, missing_all = 0, 0, []
    print(f"{'箱':10s} {'命中':>4s} {'未装':>4s}  标题")
    for name, (title, _cols, items) in SHEETS.items():
        members, missing = [], []
        for entry in items:
            total_parts += 1
            path, how = match(entry, index)
            if verbose:
                print(f"    {entry[1]:24s} {'✔ ' + path.name if path else '✘'}  {how}")
            if path is None:
                missing.append((entry[1], how))
                continue
            members.append((module_id_of(path), path))
        missing_all += [(name, lbl, how) for lbl, how in missing]
        print(f"{name:10s} {len(members):4d} {len(missing):4d}  {title}"
              + ("  → 不写空箱" if not members else ""))
        if member_out := members:
            if write:
                out = bins_dir / f"{BIN_PREFIX}{name}.fzb"
                icon_sub = BIN_ICON_OF.get(name, items[0][0])
                out.write_text(
                    fzb_text(title, member_out, version, bin_icon_svg(icon_sub, name)),
                    encoding="utf-8", newline="\n")
                total_written += 1

    print(f"\n合计：分类表里 {total_parts} 个零件，命中 {total_parts - len(missing_all)}，"
          f"未装 {len(missing_all)}；写成 {total_written} 个箱"
          + ("（--list：未写文件）" if not write else f"，在 {bins_dir}"))
    if missing_all:
        print("\n未装（箱里不会有它们；先 Import 对应的 fzpz 再重跑本脚本）：")
        for sheet, label, how in missing_all:
            print(f"    [{sheet}] {label:24s} {how}")
    if write:
        print()
        verify(bins_dir)


if __name__ == "__main__":
    main()
