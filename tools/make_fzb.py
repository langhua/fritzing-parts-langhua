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
- ★ **箱内可以分小节**（就像自带 CORE 里的「基本/输入/输出」）：在流里插一条
  `moduleIdRef="__spacer__"` 的实例，**文字就是它的 `path` 属性**；spacer 同样要带 `<views>`
  （`modelbase.cpp` 里它被建成 `ModelPart::Space`、`setInstanceText(path)` —— 写法照 `core.fzb`）。
  小节内容写在脚本的 `SECTIONS` 里（**必须恰好盖住该组全部条目**，否则报错不静默丢）。
- `modelIndex` **不写**：那是 Fritzing 保存时的运行时编号，不是箱文件的要求。
  （只有 spacer 抄了 core.fzb 的 `modelIndex="3"`。）
- 箱里存的是**零件引用**（`path` 指到已安装的 `.fzp`），不是拷贝；零件一动，那条就失效。

**只写 `fzh_*.fzb`**（本工具自己的前缀）：`my_parts.fzb`（Fritzing 自维护的「我的零件」箱）
与别人的箱一律不碰。

用法：
    python tools/make_fzb.py                  # 写进 ~/Documents/Fritzing/bins，并镜像一份到仓库 `fzb/`
    python tools/make_fzb.py --list           # 只报告，不写文件
    python tools/make_fzb.py --verbose        # 逐条报告「哪个零件按什么规则匹配到哪个已装 fzp」
    python tools/make_fzb.py --verify --list  # 只自检已有箱（写入后也会自动跑一次）
    python tools/make_fzb.py --no-mirror      # 不写仓库 `fzb/`（只写 Fritzing 目录）
    python tools/make_fzb.py --bins-dir D:\\x --parts-dir D:\\y    # 换目录（别的机器/别的盘）

★ **两个目录的分工别搞反**：
  · 主输出 = `<Documents>/Fritzing/bins` —— **Fritzing 只读这里**（路径写死在 `folderutils.cpp`：
    `QStandardPaths::DocumentsLocation + "/Fritzing/bins"`，没有配置项），换到别处箱就不见了；
  · 仓库 `fzb/` = **镜像/归档**（同 `fzpz/` 的惯例：那层放 `.fzpz`，这层放 `.fzb` + 箱图标 PNG）
    —— Fritzing 不读它，它只是那份目录的副本（整目录拷回 `Documents/Fritzing/bins` 即可恢复）。
  注意箱里的 `path` 是**本机已装零件的绝对路径**，所以仓库那份是「本机快照」，换机器要重跑。
"""
import re
import sys
import shutil
import pathlib
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_preview import (SHEETS, SVG_DIR, ROOT_RE, ATTR_RE, find_icon,   # noqa: E402
                          viewbox_of, strip_shell, namespace, scope_style, precheck)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent   # 仓库根
HOME = pathlib.Path.home()
DEF_FRITZING = HOME / "Documents" / "Fritzing"
BIN_PREFIX = "fzh_"          # 我们生成的箱文件名前缀（别与 my_parts.fzb / 别人的箱混）
HASH_RE = re.compile(r"_[0-9a-f]{16,}_\d+$")
TRAIL_RE = re.compile(r"_\d+$")

# 小节标题：Fritzing 用**一条 `__spacer__` 实例**当分割栏，文字就是它的 `path` 属性
# （`ModuleIDNames::SpacerModuleIDName = "__spacer__"`；`modelbase.cpp` 里这种实例建成
#  `ModelPart::Space`，`setInstanceText(instance.attribute("path"))` —— 写法照自带 `core.fzb`：
#  spacer 也必须有 `<views>`，否则会被 `checkViews` 跳过）。自带 core 用 Basic/Input/Output
# 这类英文（界面会翻译），我们写中文就原样显示。
SPACER_ID = "__spacer__"
SPACER_VIEW = ('        <views>\n            <iconView layer="icon">\n'
               '                <geometry z="-1" x="-1" y="-1"/>\n'
               '            </iconView>\n        </views>')

# 每个箱内部的小节：**本表必须恰好盖住该组全部条目**（自检会拦漏/重/写错名字）
SECTIONS = {
    "chips": [
        ("MCU", ["CH32V203C8T6", "CH32V002J4M6", "CH32V003J4M6",
                 "CH32V002F4U6", "CH32V003F4U6", "CH32V002D4U6"]),
        ("USB 接口芯片", ["CH340C", "CH340E", "CH340K", "CH340N", "CH340X", "CH347F", "CH347T"]),
        ("开关机 / 电源路径", ["CH213K", "MAX40200", "SAM8108", "EC190708"]),
        ("存储", ["W25Q16JV", "AT24C02"]),
        ("安全元件", ["ATECC608B"]),
        ("显示 / LED 驱动", ["TM1637", "TM1638"]),
        ("网络", ["IP101GR", "H1102NLT"]),
        ("模拟开关 / 多路 / 光耦", ["CD74HC4067", "TS3A44159PWR", "PC817_SOP4"]),
    ],
    "power": [
        ("DC-DC（降/升压）", ["ETA3425S2F", "SY8089", "SM5701", "RT6150AGQW",
                          "RT6150AGQW rev.1", "TPS63051RMWR", "TPS631000DRLR"]),
        ("LDO", ["RT9013", "RT9193", "XC6206P332MR", "LD1117"]),
        ("锂电充电", ["TP4056", "TP4057", "ME4054", "SM5206", "CN3165"]),
        ("锂电保护", ["DW01A", "DW03", "DW06D"]),
        ("电池", ["Li300mAh", "Li300mAh-1.25", "Li300mAh-1.25-SMD"]),
    ],
    "modules": [
        ("无线 SoC / 模组", ["TXW8301", "ESP32-S3-WROOM-1", "ESP-12F"]),
        ("开发板", ["ESP32-S3-DevKitC-1", "ESP8266+CH340+SSD1306", "TX-AH-R900PNR"]),
        ("显示", ["TFTSPI1.9in", "UART1.9inIPS"]),
        ("LED / 指示", ["WS2812B-5050", "WS2812B-2020", "WS2812B-1010",
                       "WS2812B-5050-4x4", "3Pin-LED"]),
        ("感应 / 天线", ["NFC Coil"]),
    ],
    "conn": [
        ("插座 / 连接器", ["TypeC16Pin", "USB-B01", "FPC-05F-12P-H15", "RJ45-8P8C",
                          "RJ45-8P8C rev.1", "SMA-PJ1.7-L9.5", "MX-1.25-3P-V", "PH-2.0-3P-V"]),
        ("开关（拨动 / 滑动 / 轻触）", ["DPDT7x7-6P", "SK-12D02VG3", "DSIC01LS-P", "TS-D014",
                                     "SMT-SW-PTS-820"]),
        ("按键", ["PB86-A0-BLACK", "PB86-A0-BLUE", "PB86-A0-GRAY", "PB86-A0-GREEN",
                 "PB86-A0-RED", "PB86-A0-YELLOW"]),
        ("网络标签焊盘", ["NetLabel-Pad"]),
    ],
    "passive": [
        ("SMD 电阻", ["R 01005", "R 0201", "R 0402", "R 0603", "R 0805",
                     "R 1206", "R 1210", "R 1812", "R 2010", "R 2512"]),
        ("晶振", ["Crystal-3215", "Crystal-3225"]),
        ("模压功率电感", ["SHC0420", "SHC0520", "SHC0630", "SHC1040", "SHC1250", "SHC1265"]),
    ],
    "discrete": [
        ("二极管（肖特基 / TVS）", ["SOD-123", "SOD-123FL", "SOD-323", "SOD-523",
                                   "BAT54S", "SS34", "BAS70BRW", "BAS70DW-04"]),
        ("MOSFET", ["8205HA", "8205S"]),
        ("排阻", ["YC164"]),
    ],
}

# 箱图标：**必须是文件名** —— `icon="<名字>.png"`，且同目录里要有 `<名字>.png` 与 `<名字>-mono.png`。
# 为什么不能用「内嵌 SVG 文本」那个看起来更简洁的写法（踩过两次）：
#   ① `isCustomSvg()` 只认内嵌 SVG，走到那条分支后 `m_monoIcon` 被**写死**成内置
#      `:resources/bins/icons/Custom1-mono.png`（一个黑六边形），而标签栏画的是 mono 图标
#      → **未选中的箱全变黑六边形**，只有选中的那个才显示我们的图；
#   ② 走「文件名」分支时才会顺手找 `-mono` 变体：
#      `path.insert(ix, "-mono"); if (file3.exists()) m_monoIcon = new QIcon(path);`
#   （源码：`partsbinpalettewidget.cpp` 的 `grabTitle()`）
# 两张图我们**用同一张彩图**：Fritzing 只要求文件名以 `-mono` 结尾，没要求真·单色，
# 而彩图在标签栏里最好认（要改成黑剪影就改 `mono_png` 的写法）。
ICON_SIZE = 64            # 图标像素尺寸（画布 viewBox 也是 64×64）
ICON_MARKER = "Fritzing Custom Icon"   # 保留在 SVG 里（万一以后要改回内嵌写法）
ICON_BOX, ICON_PAD = 64.0, 2.0
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


def fzb_text(title, members, fritzing_version, icon_name):
    """members 里每个元素：`(SPACER_ID, 小节名, None)` 是小节分割栏，否则是 `(moduleId, path, how)`。"""
    ver = f' fritzingVersion="{fritzing_version}"' if fritzing_version else ""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<!-- 由 fritzing-parts-langhua 的 tools/make_fzb.py 生成（勿手改） -->',
             f'<module{ver} icon="{icon_name}">',
             f'    <title>{title}</title>',
             '    <instances>']
    for module_id, path, _how in members:
        if module_id == SPACER_ID:
            lines.append(f'        <instance moduleIdRef="{SPACER_ID}" modelIndex="3" '
                         f'path="{path}">')
            lines.append(SPACER_VIEW)
            lines.append('        </instance>')
            continue
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
        icon = (root.get("icon") or "").strip()
        # 图标必须是**同目录的两个 PNG**：只有 .fzb 里那个、没 -mono 的话，标签栏会退回黑六边形
        for want in (icon, icon.replace(".png", "-mono.png")):
            if not want or not (bins_dir / want).is_file():
                bad += 1
                print(f"  !! 箱图标缺失：{f.name} 需要 {want!r}（否则未选中的箱是内置黑六边形）")
        for it in root.findall("./instances/instance"):
            total += 1
            mid = it.get("moduleIdRef")
            if mid == SPACER_ID:                      # 小节分割栏：path = 标题文字，不是文件
                if not (it.get("path") or "").strip() or it.find("views") is None:
                    bad += 1
                    print(f"  !! 小节栏不完整（缺 path 或 views）：{f.name} {it.get('path')!r}")
                continue
            p = pathlib.Path(it.get("path") or "")
            if it.find("views") is None:
                bad += 1
                print(f"  !! 缺 <views/>：{f.name} {mid}")
            elif not p.is_file():
                bad += 1
                print(f"  !! path 不存在：{f.name} → {p}")
            elif module_id_of(p) != mid:
                bad += 1
                print(f"  !! moduleId 不一致：{f.name} 写 {mid!r}，"
                      f"{p.name} 里是 {module_id_of(p)!r}")
    if not quiet:
        print(f"自检：{total - bad}/{total} 条引用落地" + ("，全部通过" if bad == 0 else f"，{bad} 处有问题"))
    return bad


def write_bin_icon(sub, name, bins_dir):
    """渲出箱图标：`fzh_<组>.png` + `fzh_<组>-mono.png`（两者内容相同），返回 .fzb 里该写的文件名。

    Fritzing 在**箱文件同目录**找 `icon=` 那个名字，再顺手找同名 `-mono` —— 两文件都在，
    标签栏（未选中）与当前箱才都是我们的图。
    """
    from cairosvg import svg2png          # 与 tools/byhand_check.py 同一套依赖
    png = bins_dir / f"{BIN_PREFIX}{name}.png"
    svg2png(bytestring=bin_icon_svg(sub, name).encode("utf-8"),
            write_to=str(png), output_width=ICON_SIZE, output_height=ICON_SIZE)
    mono = bins_dir / f"{BIN_PREFIX}{name}-mono.png"
    mono.write_bytes(png.read_bytes())
    return png.name, mono.name


def check_sections():
    """SECTIONS 必须**恰好盖住**每个分组的全部条目 —— 漏一个零件、写错一个名字、
    同一个零件进两个小节，都在这里当场报出来（不静默丢）。"""
    problems = []
    for name, (_title, _cols, items) in SHEETS.items():
        labels = [lbl for _sub, lbl in items]
        sec = SECTIONS.get(name)
        if sec is None:
            problems.append(f"{name}: SECTIONS 里没有这个组")
            continue
        listed = [l for _t, ls in sec for l in ls]
        problems += [f"{name}: SECTIONS 里的 {l!r} 不在分组表里（名字写错？）"
                     for l in listed if l not in labels]
        problems += [f"{name}: 分组表里的 {l!r} 没被任何小节收录"
                     for l in labels if l not in listed]
        problems += [f"{name}: {l!r} 出现在多个小节里"
                     for l in sorted({l for l in listed if listed.count(l) > 1})]
    return problems


def main():
    args = sys.argv[1:]

    def opt(name, default):
        return pathlib.Path(args[args.index(name) + 1]) if name in args else default

    fritzing = opt("--fritzing-dir", DEF_FRITZING)
    bins_dir = opt("--bins-dir", fritzing / "bins")
    parts_dir = opt("--parts-dir", fritzing / "parts")
    mirror_dir = None if "--no-mirror" in args else opt("--mirror-dir", ROOT / "fzb")
    write = "--list" not in args

    problems = precheck() + check_sections()
    if problems:
        print("!! 先修这些再生成：")
        for p in problems:
            print("   ", p)
        if "--force" not in args:
            raise SystemExit(1)

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
    total_parts, total_written, missing_all, written = 0, 0, [], []
    print(f"{'箱':10s} {'命中':>4s} {'未装':>4s} {'小节':>4s}  标题")
    for name, (title, _cols, items) in SHEETS.items():
        missing, by_label = [], {}
        for entry in items:
            total_parts += 1
            path, how = match(entry, index)
            if verbose:
                print(f"    {entry[1]:24s} {'✔ ' + path.name if path else '✘'}  {how}")
            if path is None:
                missing.append((entry[1], how))
                continue
            by_label[entry[1]] = (module_id_of(path), path)
        missing_all += [(name, lbl, how) for lbl, how in missing]

        members, sections_used = [], 0
        for section, labels in SECTIONS[name]:
            rows = [by_label[l] for l in labels if l in by_label]
            if not rows:              # 整节都没装 → 不撑一个空标题
                continue
            sections_used += 1
            members.append((SPACER_ID, section, None))
            members += [(mid, p, "") for mid, p in rows]
        print(f"{name:10s} {len(members) - sections_used:4d} {len(missing):4d} "
              f"{sections_used:4d}  {title}" + ("  → 不写空箱" if not members else ""))
        if member_out := members:
            if write:
                out = bins_dir / f"{BIN_PREFIX}{name}.fzb"
                icon_name, mono_name = write_bin_icon(BIN_ICON_OF.get(name, items[0][0]),
                                                     name, bins_dir)
                out.write_text(fzb_text(title, member_out, version, icon_name),
                               encoding="utf-8", newline="\n")
                written += [out.name, icon_name, mono_name]
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
        if mirror_dir is not None:
            mirror_dir.mkdir(parents=True, exist_ok=True)
            for n in written:
                shutil.copy2(bins_dir / n, mirror_dir / n)
            print(f"镜像：{len(written)} 个文件 → {mirror_dir}"
                  "（Fritzing 不读这里，仅归档/入库用；箱里的 path 是本机绝对路径）")

if __name__ == "__main__":
    main()
