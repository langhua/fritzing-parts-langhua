#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fzp_check.py — **开发辅助**：检查 `.fzp` 与四个视图 svg 是否对得上（"连接器是灵魂"）。

用法（在仓库根跑）：
    C:\Python313\python.exe tools\fzp_check.py svg\CH347F
    C:\Python313\python.exe tools\fzp_check.py svg\CH347F --fzpz fzpz\CH347F.fzpz   # 连包一起查

查什么（这些错都**不报错、只是静默不好用**，所以值得机器查）：
  ① `.fzp` 能解析；四个视图的 `image=` 用的是**子目录路径**（icon/ breadboard/ schematic/ pcb/，
     AGENTS §4），而实际文件是本目录的 `svg.<view>.<id>_<view>.svg`
  ② 每个 connector：`<views>` 里至少有一条；每条 `svgId` / `terminalId`
     **必须在对应视图 svg 里真的存在**（拼错一个字母 = 那个脚连不上/不显示）
  ③ 反过来：svgs 里每个 `id="connector…"` 都得在 .fzp 里声明过（否则是没主的图形）
  ④ 每个 svg 内部 **id 不能重复**（踩过：Inkscape Ctrl+D 复制排针 → 两个 `connector32pin`）
  ⑤ `<buses>` 引用的 connector 必须存在，且**每个 connector 最多进一条总线**
  ⑥ **裸露焊盘不许进任何 `<bus>`**（用户 2026-09-15 定，AGENTS §5）；
    名字**尊重原厂命名**（用户 2026-09-25 定）：不叫 `EPAD` / `EP` 时只**提示**，不判 FAIL ——
    原厂叫 `VSS` 就保留 `VSS` ✓（如 `CH32V002D4U6` 的裸焊盘 ✓）：
     它是独立网络，必须**布线时特意接到 GND** —— 并进总线＝看着连上其实没连
  ⑦ **面包板里同名（connectorname）的焊盘必须在同一条总线里**（NC/DNP 除外）
  ⑧ `--fzpz`：包里成员是**平铺**的（part.<id>.fzp + 4 个 svg，无子目录），且与本目录文件一致

判定：退出码 0 且输出里没有 `FAIL`。
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

VIEWS = ("breadboard", "schematic", "pcb", "icon")


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    part_dir = os.path.abspath(argv[0])
    part = os.path.basename(part_dir)
    fails, notes = [], []
    fzp_path = os.path.join(part_dir, "part.%s.fzp" % part)
    if not os.path.isfile(fzp_path):
        c = glob.glob(os.path.join(part_dir, "part.*.fzp"))
        if not c:
            raise SystemExit("没找到 .fzp：%s" % fzp_path)
        fzp_path = c[0]
    root = ET.parse(fzp_path).getroot()
    print("文件: %s" % os.path.relpath(fzp_path, os.path.dirname(part_dir)))
    print("moduleId=%s label=%s" % (root.get("moduleId"), (root.findtext("label") or "").strip()))

    # ★ 面包板家族例外 ✓（2026-10-05 用户定，机理见 docs/fritzing-fz-notes.md §10 ✓）：
    #   · 面包板件**故意**让 schematic/pcb 两个视图共用面包板图（原厂件就是这么写的 ✓）
    #     ⇒ “image 要子目录路径” / “缺 schematic/pcb 的 svg”那两条对它们**不适用** ✓
    #     （否则永远是假报警 ✗）；
    #   · 面包板真正该守的是**另一条** ✓：**孔不许在那两个视图里声明连接器** ✗
    #     （否则会把上百条孔 bus 灌进那两个视图的网表 ✗）⇒ 见文末那条新规则 ✓。
    fam = ""
    for p in root.findall("./properties/property"):
        if p.get("name") == "family":
            fam = (p.text or "").strip()
    is_bb = fam.lower() == "breadboard"

    # ① 视图 → 实际 svg 文件
    svg_of, files = {}, {}
    for v in VIEWS:
        got = glob.glob(os.path.join(part_dir, "svg.%s.%s_%s.svg" % (v, part, v))) \
            or glob.glob(os.path.join(part_dir, "svg.%s.*.svg" % v))
        files[v] = got[0] if got else None
        if got and os.path.basename(got[0]) != "svg.%s.%s_%s.svg" % (v, part, v):
            notes.append("注: %s 视图的文件名不是 svg.%s.%s_%s.svg，而是 %s"
                         % (v, v, part, v, os.path.basename(got[0])))
        img = root.find(".//%sView/layers" % v)
        img = (img.get("image") if img is not None else None) or ""
        if not img.startswith(v + "/"):
            msg = "%sView 的 image=%r 不是子目录路径（应为 %s/…，AGENTS §4）" % (v, img, v)
            # icon 视图复用面包板图是既有做法（FPC05 等）→ 只提示，不算 FAIL
            if v == "icon":
                notes.append("注: " + msg)
            elif is_bb and v in ("schematic", "pcb"):
                notes.append("注: （面包板 ✓）%sView 与面包板视图共用同一张图 ✓ 属既有做法 ✓"
                             % v)
            else:
                fails.append("FAIL " + msg)
        if files[v] is None:
            if is_bb and v in ("schematic", "pcb"):
                notes.append("注: （面包板 ✓）没有 %s 视图的 svg ✓（那两视图共用面包板图 ✓）"
                             % v)
            else:
                fails.append("FAIL 缺 %s 视图的 svg（svg.%s.%s_%s.svg）" % (v, v, part, v))
    print("视图: %s" % ", ".join("%s=%s" % (v, os.path.basename(files[v]) if files[v] else "缺")
                                for v in VIEWS))

    # 各 svg 的 id 集合（顺便查重复 id = ④）
    ids_of = {}
    for v, p in files.items():
        if not p:
            continue
        a = open(p, encoding="utf-8").read()
        all_ids = re.findall(r'\bid="([^"]+)"', a)
        dup = sorted({i for i in all_ids if all_ids.count(i) > 1})
        if dup and v != "icon":
            fails.append("FAIL %s 视图 svg 里有重复 id：%s" % (v, dup[:6]))
        ids_of[v] = set(all_ids)

    # ②③ connector ↔ svgId
    declared, per_view_used = set(), {v: set() for v in VIEWS}
    svgid_to_cid = {}
    n_conn = 0
    for c in root.iter("connector"):
        cid = c.get("id")
        if not cid:
            fails.append("FAIL 有 <connector> 没有 id")
            continue
        n_conn += 1
        declared.add(cid)
        if not (c.get("name") or "").strip():
            fails.append("FAIL %s 缺 name 属性" % cid)
        vs = c.find("views")
        if vs is None or not len(vs):
            fails.append("FAIL %s 的 <views> 是空的（Fritzing 认不出这个脚）" % cid)
            continue
        for child in vs:
            v = child.tag.replace("View", "")
            if v not in VIEWS:
                notes.append("注: %s 里有未知视图 <%s>" % (cid, child.tag))
                continue
            for p in child.iter("p"):
                for attr in ("svgId", "terminalId"):
                    sid = p.get(attr)
                    if not sid:
                        continue
                    per_view_used[v].add(sid)
                    svgid_to_cid[(v, sid)] = cid
                    if sid not in ids_of.get(v, set()):
                        fails.append("FAIL %s 的 %s=%s 在 %s 视图 svg 里找不到"
                                     % (cid, attr, sid, v))
    print("connector: %d 个（声明了 %d 个 id）" % (n_conn, len(declared)))

    # ③ 反向：svg 里的 connector…id 都要在 .fzp 里声明
    #    （**icon 视图不查**：图标只是张图，Fritzing 不看它的 connector id）
    for v, p in files.items():
        if not p or v == "icon":
            continue
        for i in sorted(i for i in ids_of[v] if re.match(r"connector\d+(pin|pad|terminal)$", i)):
            if i not in per_view_used[v]:
                fails.append("FAIL %s 视图里的 id=%s 没有被 .fzp 引用（没主的图形）" % (v, i))

    # ⑤ buses
    in_bus = {}
    for b in root.iter("bus"):
        bid = b.get("id")
        mem = [m.get("connectorId") for m in b.iter("nodeMember")]
        for m in mem:
            if m not in declared:
                fails.append("FAIL 总线 %s 引用了不存在的 %s" % (bid, m))
            elif m in in_bus:
                msg = "%s 同时在总线 %s 和 %s 里" % (m, in_bus[m], bid)
                if is_bb:
                    # ★ 面包板例外 ✓（2026-10-05 用户定）：面包板可以用**两段轨共用几只孔**
                    #   来表达“这段是连着的” ✓ —— `SYB-118` 就是这样 ✓，用户实测确认
                    #   “之前的电源轨分组才是正确的，不能改” ✓（我按“X 应与 Y 对称”推错了 ✗）。
                    #   ⇒ 对面包板只**提示** ✓；对别的件仍然是 **FAIL** ✗（那是真错 ✓）。
                    notes.append("注: （面包板 ✓）" + msg + " ✓ 属既有做法 ✓")
                else:
                    fails.append("FAIL " + msg)
            else:
                in_bus[m] = bid
    print("总线: %s" % ", ".join("%s(%d)" % (b.get("id"), len(list(b.iter("nodeMember"))))
                                for b in root.iter("bus")))

    # ⑥ 裸露焊盘 **不许进任何总线**（判 FAIL）；名字不叫 EPAD/EP 只**提示**
    #    （用户 2026-09-15 定、2026-09-25 补充，AGENTS §5：
    #     ①硬规则 = 它要布线时特意接到 GND，自动并进 GND 总线会让人以为已经接好了 ✗；
    #     ②名字**尊重原厂命名** —— 原厂叫 VSS 就保留 VSS（CH32V002D4U6 就是）✓，
    #       不强求改成 EPAD/EP（那会变成替原厂改名 ✗）。）
    #    判据：裸焊盘 = connector 名匹配 EPAD / EP（允许 EPAD1/EP2 后缀），
    #    或者**描述文字**里写了 exposed pad / 散热盘 / datasheet pin 0。
    EPAD_NAME = re.compile(r"^(EPAD\d*|EP\d*)$", re.I)
    EPAD_HINT = re.compile(r"exposed\s*pad|thermal\s*pad|裸露焊盘|散热盘|datasheet\s*pin\s*0", re.I)
    for c in root.iter("connector"):
        cid, nm = c.get("id"), (c.get("name") or "")
        desc = " ".join((d.text or "") for d in c.iter("description"))
        if EPAD_HINT.search(desc) and not EPAD_NAME.match(nm):
            print("注: 裸露焊盘 %s 叫「%s」（不是 EPAD/EP）—— 原厂命名就保留 ✓，"
                  "只要它独立成网、description 写清要接 GND 即可（AGENTS §5）" % (cid, nm))
        if cid in in_bus and (EPAD_NAME.match(nm) or EPAD_HINT.search(desc)):
            fails.append("FAIL 裸露焊盘 %s（name=%s）不该进总线 %s —— 它要独立成网、"
                         "布线时特意接 GND（AGENTS §5）" % (cid, nm, in_bus[cid]))

    # ⑦ 面包板里**同名焊盘必须在同一条总线里**
    #    （踩过：SCS0 有两个焊盘 —— P4 那列一个、P8 的 pin3 一个 —— 只把第一个接上芯片脚、
    #      另一个发了板级号，却忘了给 SCS0 建总线 ⇒ Fritzing 里它们成了两个不相干的网）
    bb = files.get("breadboard")
    if bb:
        a = open(bb, encoding="utf-8").read()
        groups = {}
        for tag in re.findall(r"<(?:circle|rect|path)\b[^>]*>", a):
            at = dict(re.findall(r'([\w:-]+)="([^"]*)"', tag))
            cid, nm = at.get("id", ""), at.get("connectorname", "")
            if re.fullmatch(r"connector\d+pin", cid) and nm:
                groups.setdefault(nm, []).append(cid)
        for nm, members in sorted(groups.items()):
            if len(members) < 2 or nm.upper() in ("NC", "N/C", "DNP", "-"):
                continue                      # NC/DNP 这类**本来就不该并**（未连接焊盘）
            # nodeMember 里写的是 connectorId（不带 pin 后缀）→ 先用 svgId 反查
            b = {in_bus.get(svgid_to_cid.get(("breadboard", m), "")) for m in members}
            if len(b) != 1 or None in b:
                fails.append("FAIL 面包板里 %d 个同名焊盘「%s」没在同一条总线里（各自属于 %s）"
                             % (len(members), nm, sorted(str(x) for x in b)))

    # ★★ 面包板专用硬规矩 ✓（2026-10-05 用户定，机理见 docs/fritzing-fz-notes.md §10 ✓）：
    #   孔的连接器**只许**在 breadboard 视图里声明 ✗ —— 一旦在 schematic/pcb 里也声明，
    #   那两个视图就会给孔**建连接器项** ⇒ 上百条孔 bus 被塞进它们的网表 ✗（而且看不见 ✗）
    #   ⇒ Fritzing 状态栏假报「还有 N 个连接件没布线」✗。机器守同源 = breadboard_only_views.py ✓
    if is_bb:
        nbad = 0
        for c in root.iter("connector"):
            v = c.find("views")
            for vn in ("schematicView", "pcbView"):
                if v is not None and v.find(vn) is not None:
                    nbad += 1
        if nbad:
            fails.append("FAIL 面包板的孔在 schematic/pcb 视图里也声明了连接器：**%d 块** ✗"
                         "（会把孔 bus 塞进那两个视图的网表 ✗；用 tools/breadboard_only_views.py "
                         "修 ✓，见 docs/fritzing-fz-notes.md §10 ✓）" % nbad)

    # ⑥ fzpz
    if "--fzpz" in argv:
        z = os.path.abspath(argv[argv.index("--fzpz") + 1])
        if not os.path.isfile(z):
            fails.append("FAIL 没有 %s" % z)
        else:
            with zipfile.ZipFile(z) as zf:
                names = zf.namelist()
            print("包内成员: %s" % ", ".join(names))
            if any("/" in n or "\\" in n for n in names):
                fails.append("FAIL 包里不该有子目录（要平铺，AGENTS §4）")
            # ★ 期望的成员名 = **fzp 自己声明的 `image=`** ✓（`<view>/<名>` ⇒ 平铺成
            #   `svg.<view>.<名>` ✓，就是 §10 那条"部署/打包按 fzp 自己的声明反推" ✓）。
            #   ✗ 别按"我们的命名习惯"去猜 ✗：老件 `SYB-118` 的图形就叫
            #   `svg.breadboard.SYB-118_1.svg` ✓，fzp 指的也正是它 ✓ ⇒ 包是对的 ✓
            #  （文件名不合规那条只**提示** ✓，见上面 ①）。
            want = {os.path.basename(fzp_path)}          # ★ = 磁盘上那个真名字 ✓
            #   （✗ 别写死 `part.<目录名>.fzp` ✗：`3Pin-LED` 这类件的 fzp 是按 moduleId
            #     命名的 ✓，目录名跟它不一样 ✓ —— 老规矩"按 fzp 自己的声明反推" ✓。）
            vw = root.find("views")
            for e in (list(vw) if vw is not None else []):
                lay = e.find("layers")
                if lay is None or not lay.get("image"):
                    continue
                # ★ `image="breadboard/8205HA_breadboard.svg"` ⇒ 包内平铺名
                #   `svg.breadboard.8205HA_breadboard.svg` ✓ —— **要用 basename** ✓
                #   （✗ 把 `image` 整串拼进去会得到 `svg.breadboard.breadboard.…` ✗）
                want.add("svg.%s.%s" % (e.tag.replace("View", ""),
                                        os.path.basename(lay.get("image"))))
            if is_bb:
                # ★ 面包板：schematic/pcb 共用面包板图（原厂同形 ✓）⇒ 不要求那两份独立成员 ✓
                want = {w for w in want
                        if not any(w.startswith("svg.%s." % v) for v in ("schematic", "pcb"))}
            if set(names) != want:
                fails.append("FAIL 包内成员与预期不符（多: %s；少: %s）"
                             % (sorted(set(names) - want), sorted(want - set(names))))

    print()
    for n in notes:
        print(n)
    if fails:
        print("\n".join(fails))
        print("=== %d 项 FAIL ===" % len(fails))
        return 1
    print("=== 全部通过 ===")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
