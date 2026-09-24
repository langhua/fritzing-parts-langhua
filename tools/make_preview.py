# -*- coding: utf-8 -*-
"""生成 README 用的**元件预览拼图**（`docs/preview/*.svg`）。

为什么要有这个脚本：README 要把「元件长什么样」直接画在正文里（AGENTS §9 图文并茂），
而**图的权威内容 = 各部件自己的 icon svg**（`svg/<部件>/svg.icon.*_icon.svg`）——
所以图不手绘、不复制几何，一律从这里重新生成：改了某个 icon，重跑本脚本即可。

两个不显然的实现取舍（踩过的坑，别改回去）：

1. **用嵌套 `<svg … viewBox=…>` 当格子，不写 transform 数学**：
   源 icon 的坐标系五花八门（`-1.5 -2.5 3.0 5.0` mm、`0 0 300 400` 老 px、
   `0 0 87.87 80.79` Inkscape 单位…），逐个人工算平移+缩放必然算错；
   嵌套 `<svg>` 自带独立视口，`preserveAspectRatio="xMidYMid meet"` 就是"等比装进格子"。
2. **id / CSS 必须加前缀**：所有 icon 拼进**一个** SVG 文档后，`id` 与 `<style>` 选择器
   是**文档级**的 —— 两个 icon 都用 `id="rect8"`、或某个 icon 的 `<style>` 里写了
   `.st0{…}`，就会互相串（颜色/裁剪张冠李戴）。所以：`id="x"` → `id="p3_x"`
   （连带 `url(#x)` / `href="#x"`），`<style>` 的每条选择器前面加 `#p3 `（限定在自己那格）。

用法：
    python tools/make_preview.py            # 生成 docs/preview/*.svg 并打印清单
    python tools/make_preview.py --list     # 只看清单（不写文件）
"""
import re
import sys
import math
import pathlib
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent   # 仓库根
SVG_DIR = ROOT / "svg"
OUT_DIR = ROOT / "docs" / "preview"

# ---- 版面（单位 = mm；拼图自身是 1 用户单位 1mm，屏幕上按 96dpi 换算）----
MARGIN, HEADER, FOOTER = 8.0, 17.0, 12.0
CELL_W, CELL_H = 34.0, 34.0
BOX_H = 22.0                      # 格子里的 icon 方框高（宽 = CELL_W - 2*PAD）
PAD = 2.0
FN_TITLE, FN_NAME, FN_SIZE, FN_NOTE = 5.0, 2.6, 2.2, 2.2
INK, GREY = "#202020", "#6b6b6b"
FONT = "DroidSans, Arial, Helvetica, sans-serif"

# ---- 各张图的内容：表名 -> (标题, 列数, [(svg 子目录, 显示名), …]) ----
SHEETS = {
    "chips": ("芯片与接口 IC", 5, [
        ("CH340C", "CH340C"), ("CH340E", "CH340E"), ("CH340K", "CH340K"),
        ("CH340N", "CH340N"), ("CH340X", "CH340X"),
        ("CH32V203C8T6", "CH32V203C8T6"),
        ("CH32V002J4M6", "CH32V002J4M6"), ("CH32V003J4M6", "CH32V003J4M6"),
        ("CH32V002F4U6", "CH32V002F4U6"), ("CH32V003F4U6", "CH32V003F4U6"),
        ("CH32V002D4U6", "CH32V002D4U6"),
        ("CH347F", "CH347F"), ("CH347T", "CH347T"),
        ("CH213K", "CH213K"), ("MAX40200", "MAX40200"),
        ("PC817_SOP4", "PC817_SOP4"), ("TS3A44159PWR", "TS3A44159PWR"),
        ("CD74HC4067", "CD74HC4067"), ("W25Q16JV", "W25Q16JV"), ("AT24C02", "AT24C02"),
        ("ATECC608B", "ATECC608B"),
        ("SAM8108", "SAM8108"), ("TM1637", "TM1637"), ("TM1638", "TM1638"),
        ("IP101GR", "IP101GR"), ("H1102NLT", "H1102NLT"), ("EC190708", "EC190708"),
    ]),
    "power": ("电源 / 充电 / 保护 / 电池", 5, [
        ("ETA3425S2F", "ETA3425S2F"), ("RT6150AGQW", "RT6150AGQW"),
        ("RT6150AGQW_rev_1", "RT6150AGQW rev.1"),
        ("RT9013", "RT9013"), ("RT9193", "RT9193"),
        ("SM5701", "SM5701"), ("SY8089", "SY8089"),
        ("TPS63051RMWR", "TPS63051RMWR"), ("TPS631000DRLR", "TPS631000DRLR"),
        ("TP4056", "TP4056"), ("TP4057", "TP4057"), ("ME4054", "ME4054"),
        ("SM5206", "SM5206"), ("CN3165", "CN3165"),
        ("XC6206P332MR", "XC6206P332MR"), ("LD1117", "LD1117"),
        ("DW01A", "DW01A"), ("DW03", "DW03"), ("DW06D", "DW06D"),
        ("Li300mAh", "Li300mAh"), ("Li300mAh-1.25", "Li300mAh-1.25"),
        ("Li300mAh-1.25-SMD", "Li300mAh-1.25-SMD"),
    ]),
    "modules": ("模块 / 开发板 / 显示 / 指示", 4, [
        ("ESP-12F", "ESP-12F"), ("ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1"),
        ("ESP32-S3-DevKitC-1", "ESP32-S3-DevKitC-1"),
        ("esp8266-ch340-ssd1306", "ESP8266+CH340+SSD1306"),
        ("TX-AH-R900PNR", "TX-AH-R900PNR"), ("TXW8301", "TXW8301"),
        # 不收 `TX-AH-R900PNR_rev_1`（icon 与正版逐字节相同，摆两遍是噪声）、
        # 也不收 `T-Halow-RJ45`（那是 T-Halow-RJ45 仓的参考件，不属本库交付物）。
        ("NFC-Coil", "NFC Coil"), ("WS2812B/5050", "WS2812B-5050"),
        ("WS2812B/2020", "WS2812B-2020"), ("WS2812B/1010", "WS2812B-1010"),
        ("WS2812B/5050_4x4", "WS2812B-5050-4x4"),
        ("TFTSPI1.9in", "TFTSPI1.9in"), ("UART1.9inIPS", "UART1.9inIPS"),
        ("3Pin-LED", "3Pin-LED"),
        # 两个从 fritzing-parts 导入的旧件没收录（icon 视图复用 breadboard），
        # 与 FPC05-2H10PX 同一原因：`lm393-a3144-hall-3pin/`、`SYB-118/` 里都没有独立 icon 文件。
    ]),
    "conn": ("连接器 / 开关 / 按键", 5, [
        ("TypeC16Pin", "TypeC16Pin"), ("USB-B01", "USB-B01"),
        # FPC05-2H10PX 没收录：它的 iconView 直接复用 breadboard svg（`image=` 指 breadboard/
        # 且 `<layer layerId="icon"/>`），本脚本只认独立 icon 文件，不替它拆组。
        ("FPC-05F-12P-H15", "FPC-05F-12P-H15"),
        ("RJ45-8P8C", "RJ45-8P8C"), ("RJ45-8P8C_rev_1", "RJ45-8P8C rev.1"),
        ("SMA-PJ1.7-L9.5", "SMA-PJ1.7-L9.5"),
        ("MX-1.25-3P-V", "MX-1.25-3P-V"),
        ("PH-2.0-3P-V", "PH-2.0-3P-V"),
        ("SH-1.0-3P-V", "SH-1.0-3P-V"),
        ("DPDT7x7-6P", "DPDT7x7-6P"), ("SK-12D02VG3", "SK-12D02VG3"),
        ("DSIC01LS-P", "DSIC01LS-P"), ("TS-D014", "TS-D014"),
        ("SMT-SW-PTS-820", "SMT-SW-PTS-820"),
        ("NetLabel-Pad", "NetLabel-Pad"),
        ("PB86-A0/black", "PB86-A0-BLACK"), ("PB86-A0/blue", "PB86-A0-BLUE"),
        ("PB86-A0/gray", "PB86-A0-GRAY"), ("PB86-A0/green", "PB86-A0-GREEN"),
        ("PB86-A0/red", "PB86-A0-RED"), ("PB86-A0/yellow", "PB86-A0-YELLOW"),
    ]),
    "passive": ("无源件（电阻 / 晶振 / 电感）", 5, [
        ("Resistor-01005", "R 01005"), ("Resistor-0201", "R 0201"),
        ("Resistor-0402", "R 0402"), ("Resistor-0603", "R 0603"),
        ("Resistor-0805", "R 0805"), ("Resistor-1206", "R 1206"),
        ("Resistor-1210", "R 1210"), ("Resistor-1812", "R 1812"),
        ("Resistor-2010", "R 2010"), ("Resistor-2512", "R 2512"),
        ("Crystal-3215", "Crystal-3215"), ("Crystal-3225", "Crystal-3225"),
        ("molding_power_inductors/SHC0420", "SHC0420"),
        ("molding_power_inductors/SHC0520", "SHC0520"),
        ("molding_power_inductors/SHC0630", "SHC0630"),
        ("molding_power_inductors/SHC1040", "SHC1040"),
        ("molding_power_inductors/SHC1250", "SHC1250"),
        ("molding_power_inductors/SHC1265", "SHC1265"),
    ]),
    "discrete": ("分立器件（二极管 / MOS / 排阻）", 5, [
        ("SOD-123", "SOD-123"), ("SOD-123FL", "SOD-123FL"),
        ("SOD-323", "SOD-323"), ("SOD-523", "SOD-523"),
        ("BAT54S", "BAT54S"), ("SS34", "SS34"),
        ("BAS70BRW", "BAS70BRW"), ("BAS70DW-04", "BAS70DW-04"),
        ("8205HA", "8205HA"), ("8205S", "8205S"), ("YC164", "YC164"),
    ]),
}

UNIT_MM = {"mm": 1.0, "cm": 10.0, "in": 25.4}
PX_PER = {"": 1.0, "px": 1.0, "mm": 96 / 25.4, "cm": 960 / 25.4, "in": 96.0, "pt": 96 / 72}
ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*"([^"]*)"')
ROOT_RE = re.compile(r"<svg\b([^>]*)>", re.S)
NUM_RE = re.compile(r"([\d.]+)\s*([a-z]*)")


def find_icon(part_dir):
    """该部件目录里的 icon svg（`*_byHand.svg` 是草稿，永不采用）。"""
    hits = [p for p in part_dir.glob("svg.icon.*_icon.svg") if "byHand" not in p.name]
    if len(hits) != 1:
        raise MissingIcon(f"{part_dir.name}: icon 文件数 = {len(hits)}")
    return hits[0]


class MissingIcon(RuntimeError):
    pass


def precheck():
    """先汇总**所有**缺件/重名，一次报清楚（不要改一个跑一次才发现下一个）。"""
    problems = []
    for name, (_, _, items) in SHEETS.items():
        for sub, label in items:
            d = SVG_DIR / sub
            if not d.is_dir():
                problems.append(f"{name}/{label}: 目录不存在 {sub}")
                continue
            n = len([p for p in d.glob("svg.icon.*_icon.svg") if "byHand" not in p.name])
            if n != 1:
                problems.append(f"{name}/{label}: {sub} 里 icon 文件 {n} 个")
    return problems


def fmt_mm(v):
    """30.9999 → `31`；63.39 → `63.39`（源文件里写着 long float，排出来太瑣碎）。"""
    return f"{v:.2f}".rstrip("0").rstrip(".")


def decl_size(attrs):
    """icon 文件**自己声明**的尺寸（mm）；没写单位就返回 None（不做猜测）。"""
    out = []
    for key in ("width", "height"):
        m = re.fullmatch(r"([\d.]+)\s*([a-z]*)", (attrs.get(key) or "").strip())
        if not m or m.group(2) not in UNIT_MM:
            return None
        out.append(float(m.group(1)) * UNIT_MM[m.group(2)])
    return out


def viewbox_of(attrs, icon_name):
    """格子视口用的 viewBox。

    少数从 fritzing-parts 导入的旧 icon 没写 viewBox（如 `SOD-123`）：按 SVG 规范，
    没有 viewBox 时用户单位就是 px（带单位则 96dpi 换算）—— 所以就按 width/height
    造一个 `0 0 w h`，与那些文件里坐标的写法一致。
    """
    if attrs.get("viewBox"):
        return attrs["viewBox"]
    nums = []
    for key in ("width", "height"):
        m = NUM_RE.fullmatch((attrs.get(key) or "").strip())
        if not m or m.group(2) not in PX_PER:
            raise MissingIcon(f"{icon_name}: 既没有 viewBox 也没有可用的 width/height")
        nums.append(float(m.group(1)) * PX_PER[m.group(2)])
    return f"0 0 {nums[0]:g} {nums[1]:g}"


def strip_shell(inner):
    """去掉 Inkscape 壳：合并进一个文档后它们无用，还可能让 XML 不合法（前缀未声明）。

    注意 **元素** 也一样要清：Inkscape 的实时路径效果写在 `<defs>` 里的
    `<inkscape:path-effect …/>`（几何早已烘进 path，渲染器不用它）——
    只清属性不清元素，拼图就会 `unbound prefix` 整张炸掉（踩过）。
    """
    foreign = r"(?:inkscape|sodipodi):[\w.-]+"
    inner = re.sub(rf"<{foreign}\b[^>]*/>", "", inner)
    inner = re.sub(rf"<{foreign}\b[^>]*>.*?</{foreign}>", "", inner, flags=re.S)
    inner = re.sub(r"<metadata\b.*?</metadata>", "", inner, flags=re.S)
    inner = re.sub(r"<sodipodi:namedview\b[^>]*/>", "", inner, flags=re.S)
    inner = re.sub(r"<sodipodi:namedview\b.*?</sodipodi:namedview>", "", inner, flags=re.S)
    inner = re.sub(r'\s+(?:sodipodi|inkscape|xml|gorn):[\w.-]+="[^"]*"', "", inner)
    return inner.strip()


def namespace(inner, key):
    """`id` 与它的引用统一加前缀 —— 拼图是一个文档，id/CSS 是文档级的。"""
    for old in sorted(set(re.findall(r'\bid="([^"]+)"', inner))):
        new = f"{key}_{old}"
        inner = inner.replace(f'id="{old}"', f'id="{new}"')
        inner = inner.replace(f"url(#{old})", f"url(#{new})")
        inner = inner.replace(f'href="#{old}"', f'href="#{new}"')
    return inner


def scope_style(inner, key):
    """icon 自带的 `<style>` 选择器限定在自己那格（否则会串到别的元件上）。"""
    def fix(m):
        rules = []
        for rule in m.group(2).split("}"):
            if not rule.strip():
                continue
            sel, _, body = rule.partition("{")
            sel = ",".join(f"#{key} {s.strip()}" for s in sel.split(",") if s.strip())
            rules.append(f"{sel}{{{body}}}")
        return m.group(1) + "".join(rules) + "</style>"
    return re.sub(r"(<style\b[^>]*>)(.*?)</style>", fix, inner, flags=re.S)


def build(name, title, cols, items, write=True):
    rows = math.ceil(len(items) / cols)
    sheet_w = MARGIN * 2 + cols * CELL_W
    sheet_h = MARGIN + HEADER + rows * CELL_H + FOOTER
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f"<!-- 由 tools/make_preview.py 生成（勿手改）：{title} -->",
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{sheet_w:.0f}mm" height="{sheet_h:.0f}mm" viewBox="0 0 {sheet_w:.0f} {sheet_h:.0f}">',
        f'  <rect x="0" y="0" width="{sheet_w:.0f}" height="{sheet_h:.0f}" fill="#ffffff"/>',
        f'  <text x="{MARGIN:.0f}" y="{MARGIN + 6:.0f}" font-family="{FONT}" font-size="{FN_TITLE}" '
        f'fill="{INK}">{title}</text>',
    ]
    for i, (sub, label) in enumerate(items):
        part_dir = SVG_DIR / sub
        icon = find_icon(part_dir)
        txt = icon.read_text(encoding="utf-8")
        m = ROOT_RE.search(txt)
        attrs = dict(ATTR_RE.findall(m.group(1)))
        vb = viewbox_of(attrs, icon.name)
        key = f"p{i}"
        inner = scope_style(namespace(strip_shell(txt[m.end():].rsplit("</svg>", 1)[0]), key), key)

        r, c = divmod(i, cols)
        bx = MARGIN + c * CELL_W + PAD
        by = MARGIN + HEADER + r * CELL_H + 1.5
        bw = CELL_W - 2 * PAD
        cx = bx + bw / 2
        out.append(f'  <svg id="{key}" x="{bx:.2f}" y="{by:.2f}" width="{bw:.2f}" '
                   f'height="{BOX_H:.2f}" viewBox="{vb}" '
                   f'preserveAspectRatio="xMidYMid meet">')
        out.append("    " + inner.replace("\n", "\n    "))
        out.append("  </svg>")
        out.append(f'  <text x="{cx:.2f}" y="{by + BOX_H + 4.6:.2f}" font-family="{FONT}" '
                   f'font-size="{FN_NAME}" fill="{INK}" text-anchor="middle">{label}</text>')
        size = decl_size(attrs)
        if size:
            out.append(f'  <text x="{cx:.2f}" y="{by + BOX_H + 7.8:.2f}" font-family="{FONT}" '
                       f'font-size="{FN_SIZE}" fill="{GREY}" text-anchor="middle">'
                       f'{fmt_mm(size[0])}×{fmt_mm(size[1])}mm</text>')
    note1 = "格内按各自比例缩放（不同格不同比例）；下方数字 = icon 文件自己声明的尺寸"
    note2 = "本库新做的元件按实物 1:1 画；早年从 fritzing-parts 导入的图标可能是视觉比例"
    for k, line in enumerate((note1, note2)):
        out.append(f'  <text x="{MARGIN:.0f}" y="{sheet_h - FOOTER + 3.5 + k * 4:.0f}" '
                   f'font-family="{FONT}" font-size="{FN_NOTE}" fill="{GREY}">{line}</text>')
    out.append("</svg>")
    text = "\n".join(out) + "\n"

    ET.fromstring(text)          # XML 合法性自检（前缀/id 没清干净会在这里当场炸）
    if write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{name}.svg").write_text(text, encoding="utf-8", newline="\n")
    return text


def main():
    problems = precheck()
    if problems:
        print("!! 有部件取不到 icon（先修这些再生成）：")
        for p in problems:
            print("   ", p)
        if "--force" not in sys.argv:
            raise SystemExit(1)
    write = "--list" not in sys.argv
    used, total = set(), 0
    print(f"{'图':12s} {'元件数':>4s} {'字节':>9s}  {'画布(mm)':>12s}")
    for name, (title, cols, items) in SHEETS.items():
        text = build(name, title, cols, items, write)
        for sub, _ in items:
            used.add((SVG_DIR / sub).resolve())
        total += len(items)
        rows = math.ceil(len(items) / cols)
        w = MARGIN * 2 + cols * CELL_W
        h = MARGIN + HEADER + rows * CELL_H + FOOTER
        print(f"{name:12s} {len(items):4d} {len(text.encode()):9d}  {w:.0f}×{h:.0f}")
    print(f"\n合计 {total} 个元件；输出目录 {OUT_DIR if write else '(--list：未写文件)'}")

    stray = []
    for p in sorted(SVG_DIR.rglob("svg.icon.*_icon.svg")):
        if "byHand" in p.name:
            continue
        if not any(parent == p.parent for parent in used):
            stray.append(str(p.relative_to(SVG_DIR)).replace("\\", "/"))
    if stray:
        print(f"\n未收录进任何预览图的 icon（{len(stray)} 个，属正常：变体/参考件/中间产物）：")
        for s in stray:
            print("   ", s)


if __name__ == "__main__":
    main()
