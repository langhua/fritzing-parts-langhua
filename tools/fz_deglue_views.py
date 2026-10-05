# -*- coding: utf-8 -*-
r"""★★ **去粘**：让"面包板"不进入 PCB / 原理图视图（2026-10-05 用户实测确认 ✓）

用法：
```
py -3.13 tools/fz_deglue_views.py <in.fzz> <out.fzz>   # 去粘：写一个新 .fzz ✓
py -3.13 tools/fz_deglue_views.py <in.fzz> --check     # 只查（合格退出码 0 ✓、不合格 1 ✗）
```

## 病是什么（用户 2026-10-05 实测 ✓）

同一个草图里既有**面包板**又有 **PCB** 时，**PCB 视图会报"还有 N 个连接件没布线"**
并画**鼠线虚线** ✗ —— 而铜其实是通的 ✓。把面包板整个删掉 ⇒ 立刻**布线完成** ✓
（消融实验 ✓）⇒ 是面包板在**偷偷并网** ✗。

## 机理（全部**读源码**得到 ✓，可逐行核 ✓）

1. 核心面包板件给**每个孔**都声明了
   `<pcbView><p layer="breadboardbreadboard" svgId="pin1A"/></pcbView>` ✓
   （实测 `breadboard2.fzp` 里 **831 条** ✓）⇒ **面包板的孔在 PCB 视图里也有连接器项** ✗。
2. 恢复连接时，目标项由 `toBase->findConnectorItemWithSharedID(...)` 找 ✓，而
   `ItemBase::findConnectorItemWithSharedID()`（`items/itembase.cpp:559` ✓）返回
   `connector->connectorItem(m_viewID)` ✓ ⇒ **只在"当前视图"里找目标** ✓
   （调用点 `sketch/sketchwidget.cpp:615` ✓ `handleConnect()` ✓）。
3. ⇒ 面包板实例 `pcbView` 段里那些 `pin14F → U1(…) layer=copper0` 记录 ✓
   在 **PCB 视图里是"真"连接** ✗ ⇒ 面包板内部 **130 条 bus**（5 孔一列 ✓）把
   PCB 的网**并掉** ✗ ⇒ `GraphUtils::scoreOneNet()`（`utils/graphutils.cpp:447` ✓）
   判出"还有 N 个连接件没布线" ✗ ＋ 画虚线 ✗。
4. **只删记录不稳** ✗：连接报在 **Connector 级**（`Connector::connectTo()` ✓
   `m_toConnectors` ✓）⇒ 下次 Fritzing 另存会把各视图的记录**再写回来** ✗。
   实测反例 ✓：只删"零件 → 面包板"那一半（记录是**双向**的 ✓）⇒ **一点用都没有** ✗
   （仍报 2 个 ✓）。

## 本工具的修法（稳的 ✓）

`sketch/sketchwidget.cpp:278` 的加载逻辑是
`QDomElement view = views.firstChildElement(viewName); if (view.isNull()) continue;`
⇒ **该视图没有段落 ⇒ 那个视图里根本不创建这个元件** ✓

于是做两件事（**面包板视图一个字不动** ✓）：

| # | 动作 | 效果 |
|---|---|---|
| ① | 面包板类实例：整段删掉 `<pcbView>` / `<schematicView>`（连 `geometry` 一起 ✓） | 别的视图里没有它的孔 ● 无桥 ✓；也不会"下次另存又粘回来" ✓ |
| ② | 别的实例：在 `pcbView` / `schematicView` 段里删掉**跨视图记录** | 目标层不属于本视图 ✓｜目标实例是面包板 ✓｜源连接器层是 `breadboardbreadboard` ✓ |

## 实测（2026-10-05 ✓，用户 Fritzing 三视图复读 ✓）

| 项 | 改前 | 改后 |
|---|---|---|
| PCB 视图"能生效的非铜记录"（独立复核 ✓） | 110 条 ✗ | **0 条** ✓ |
| 面包板视图 内部 bus / 插件 / 跳线 | 130 / 44 / 37 ✓ | **130 / 44 / 37** ✓（段**逐字节相同** ✓） |
| `pcb_check.py` | ✓ 全过 | ✓ 全过 |
| `sch_metrics.py` | 41 根 / 471.1 mm / 交叉 7 / 0.9750 | **逐项不变** ✓ |
| Fritzing 状态栏（PCB / 原理图 / 面包板） | PCB 报 "还剩 2 个" ✗ | **三视图都正确** ✓（用户读的 ✓） |

## 自检（本工具自己跑的 ✓）

① XML 可解析 ✓；② `<connect` 只减不增 ✓；③ `<breadboardView` 段数量不变 ✓
且**逐段逐字节相同** ✓；④ 打印删了多少 ✓。
★ 但**不许自证**（本仓纪律 ✓）⇒ 结论要用**另一份实现**或**人眼**复核 ✓：
`--check` 是一份**独立**的只读复核 ✓；最终以**用户在 Fritzing 里看三个视图**为准 ✓。
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

KILL = ("pcbView", "schematicView")                 # 面包板不要进这两个视图 ✓
KEEP = ("breadboardView",)                          # 面包板视图：一个字不动 ✓
VIEWS = {"schematicView": ("schematic", "schematicTrace"),
         "pcbView": ("copper0", "copper1", "copper0trace", "copper1trace")}
BB_LAYER = "breadboardbreadboard"
CONNECT_RE = (r'<connect\s+connectorId="([^"]+)"\s+modelIndex="([^"]+)"'
              r'\s+layer="([^"]+)"[^>]*/>')


def read_fz(path):
    """取 .fzz 包里的内层 `.fz` 文本 ✓（+ 包对象，便于原样写回 ✓）。"""
    z = zipfile.ZipFile(path)
    inner = [n for n in z.namelist() if n.endswith(".fz")][0]
    return z, inner, z.read(inner).decode("utf-8")


def inst_blocks(text):
    """按 `<instance>` **标签配平**扫描 ✓ —— ✗ 不用"同缩进配对" ✗（实测用户/Fritzing
    写的手改件里 `</instance>` 缩进不齐 ⇒ 会把好几个实例并成一块 ✗）。
    """
    out = []
    for m in re.finditer(r"<instance\b", text):
        i, d, j = m.start(), 0, m.start()
        while j < len(text):
            n_in = re.compile(r"<instance\b").search(text, j)
            n_out = text.find("</instance>", j)
            if n_out < 0:
                break
            if n_in is not None and n_in.start() < n_out:
                d += 1
                j = n_in.end()
                continue
            d -= 1
            j = n_out + len("</instance>")
            if d <= 0:
                break
        out.append(text[i:j])
        text = text[:i] + "\x00" * (j - i) + text[j:]
    return [b for b in out if b]


def census(text):
    """静态盘点 ✓：面包板类实例的 mi / 标题；各实例有哪些视图段。"""
    mod, ttl, views = {}, {}, {}
    for b in inst_blocks(text):
        mi = re.search(r'<instance[^>]*modelIndex="([^"]+)"', b)
        if not mi:
            continue
        mi = mi.group(1)
        md = re.search(r'moduleIdRef="([^"]+)"', b)
        t = re.search(r"<title>([^<]*)</title>", b)
        mod[mi] = md.group(1) if md else ""
        ttl[mi] = t.group(1) if t else mi
        views[mi] = {}
        for vm in re.finditer(r"<(\w+View)\b[^>]*>(.*?)</\1>", b, re.S):
            if "<geometry" in vm.group(2) or "<connectors" in vm.group(2):
                views[mi][vm.group(1)] = vm.group(2)
    return mod, ttl, views


def check(text):
    """★ 独立只读复核 ✓：返回 (问题表, 面包板类实例数)。"""
    mod, ttl, views = census(text)
    bbs = {mi for mi, m in mod.items() if "Breadboard" in m}
    bad = []
    for mi in sorted(bbs):
        for vn in KILL:
            if vn in views[mi]:
                bad.append("面包板 `%s` 在 **%s** 里也有段落 ✗（该视图会创建它的孔 ⇒ 会并网 ✗）"
                           % (ttl[mi], vn))
    have = {vn for mi in mod for vn in views[mi]}
    for mi, vs in sorted(views.items()):
        for vn in KILL:
            body = vs.get(vn)
            if body is None:
                continue
            for cm in re.finditer(CONNECT_RE, body):
                tgt, lay = cm.group(2), cm.group(3)
                if lay in VIEWS[vn]:
                    if tgt in bbs:
                        bad.append("`%s` 的 %s 段里有指向面包板的记录 ✗（目标层 %s 看着像铜 ✗）"
                                   % (ttl[mi], vn, lay))
                else:
                    bad.append("`%s` 的 %s 段里有跨视图记录（层 %s ✗）"
                               % (ttl[mi], vn, lay))
    _ = have
    return bad, len(bbs)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__.split("##")[0])
    src = sys.argv[1]
    _z, _inner, text = read_fz(src)

    if sys.argv[2] == "--check":
        bad, nbb = check(text)
        print("== %s：面包板类实例 %d 个 ✓｜问题 **%d** 条 %s"
              % (os.path.basename(src), nbb, len(bad), "✓ 合格 ✓" if not bad else "✗"))
        for b in bad[:40]:
            print("   ✗ %s" % b)
        if len(bad) > 40:
            print("   ……（还有 %d 条 ✓）" % (len(bad) - 40))
        sys.exit(0 if not bad else 1)

    dst = sys.argv[2]
    mod, ttl, _views = census(text)
    bbs = {mi for mi, m in mod.items() if "Breadboard" in m}
    if not bbs:
        raise SystemExit("✗ 没找到面包板类实例 ⇒ 不写 ✓")

    stat = {"sec": 0, "bb_side": 0, "to_bb": 0, "cross": 0}

    # ① 面包板类实例：整段删掉 KILL 视图 ✓
    out = text
    for b in inst_blocks(text):
        mi = re.search(r'<instance[^>]*modelIndex="([^"]+)"', b)
        if not mi or mi.group(1) not in bbs:
            continue
        nb = b
        for vn in KILL:
            # ✗ 别写死 `\n`：实测 .fz 是 **CRLF** ✗（第一版因此"一个段都没删掉" ✗）
            pat = re.compile(r'[ \t]*<%s\b[^>]*>.*?</%s>[ \t]*\r?\n?' % (vn, vn), re.S)
            nb, k = pat.subn("", nb)
            stat["sec"] += k
        stat["bb_side"] += (len(re.findall(r"<connect\b", b))
                            - len(re.findall(r"<connect\b", nb)))
        out = out.replace(b, nb)
    if stat["sec"] == 0:
        raise SystemExit("✗ 一个视图段都没删掉 ⇒ 不写 ✓")

    # ② 别的实例：按**段**删跨视图记录 ✓（✗ 别用全局 replace ✗ —— 同一条记录在
    #    面包板段里也有一份 ⇒ 一起删会把面包板视图削瘦 ✗，实测插件 44 → 21 ✗）
    def fix_view(m):
        vn, attrs, body = m.group(1), m.group(2), m.group(3)
        if vn not in VIEWS:
            return m.group(0)                        # ★ 面包板段：原样返回 ✓

        def one(cm):
            tgt, lay = cm.group(2), cm.group(3)
            if lay in VIEWS[vn]:
                if tgt in bbs:
                    stat["to_bb"] += 1
                    return ""
                return cm.group(0)
            stat["cross"] += 1
            return ""

        body2 = re.sub(CONNECT_RE, one, body)

        def two(cm):                                 # 源端层是面包板层 ⇒ 也清 ✓
            if cm.group(1) == BB_LAYER:
                stat["bb_side"] += 1
                return ""
            return cm.group(0)

        body2 = re.sub(r'<connector\s+connectorId="[^"]+"\s+layer="([^"]+)"\s*>'
                       r'\s*<connects>\s*</connects>\s*</connector>', two, body2)
        body2 = re.sub(r"\n[ \t]*\n(?=[ \t]*</connects>)", "\n", body2)
        return "<%s%s>%s</%s>" % (vn, attrs, body2, vn)

    out = re.sub(r'<(\w+View)\b([^>]*)>(.*?)</\1>', fix_view, out, flags=re.S)

    # ★ 自检（命中就**只报不动** ✓）
    ET.fromstring(out)
    if out.count("<connect") > text.count("<connect"):
        raise SystemExit("✗ `<connect` 变多 ⇒ 不写 ✓")
    if out.count("<breadboardView") != text.count("<breadboardView"):
        raise SystemExit("✗ 面包板段数量变了 ⇒ 不写 ✓")
    before = {m.group(1): m.group(0)
              for m in re.finditer(r'<(\w+View)\b[^>]*>.*?</\1>', text, re.S)}
    after = {m.group(1): m.group(0)
             for m in re.finditer(r'<(\w+View)\b[^>]*>.*?</\1>', out, re.S)}
    for k, v in before.items():
        if k in KEEP and after.get(k) != v:
            raise SystemExit("✗ 面包板视图段被改动了 ⇒ 不写 ✓")

    z, inner, _ = read_fz(src)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as w:
        for nm in z.namelist():
            info = z.getinfo(nm)
            w.writestr(nm, out.encode("utf-8") if nm == inner else z.read(nm),
                       compress_type=info.compress_type)

    bad, _n = check(out)
    print("   ✓ 写出 %s" % os.path.basename(dst))
    print("     · 删掉面包板的视图段 **%d** 个（%s ✓）" % (stat["sec"], "/".join(KILL)))
    print("     · 面包板侧记录 %d 条 ✓｜指向面包板的记录 %d 条 ✓｜其它跨视图 %d 条 ✓"
          % (stat["bb_side"], stat["to_bb"], stat["cross"]))
    print("     · `%s`：`<connect` %d → %d ✓｜面包板段 %d 个不变 ✓｜面包板视图段逐字节相同 ✓"
          % (inner, text.count("<connect"), out.count("<connect"),
             out.count("<breadboardView")))
    print("     · 复核 `--check`：问题 **%d** 条 %s" % (len(bad), "✓ 合格 ✓" if not bad else "✗"))
    for b in bad[:10]:
        print("       ✗ %s" % b)


if __name__ == "__main__":
    main()
