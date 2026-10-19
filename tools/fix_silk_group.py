# -*- coding: utf-8 -*-
r"""把「**丝印不在 `<g id="silkscreen">` 里**」的图元装进丝印组 ✓（2016-10-11 立 ✓）

★★ 起因 ✓（用户 2026-10-11 看元件箱发现 ✗）：`Resistor-0603` / `Capacitor-0603` 的 pcb 里，
   丝印是一颗**裸 `<rect id="silkscreen">`** ✗ —— `.fzp` 只声明图层（`<layer layerId="silkscreen"/>`✓），
   「哪块图形属于哪层」是 Fritzing **按组的 id** 认的 ✓ ⇒ 裸 rect **不属于丝印层** ✗
   ⇒ 元件箱/指示栏里**多渲一块** ✗。全库同病 10 件（同族电阻 ＋ `Capacitor-0402` ✓）。

★ 判据/扫描 = **唯一实现** ✓（`silk_nest_check.silk_span` ✓）—— ✗ 本工具不另写一份 ✗。

★ 改法（**只挪层级** ✓，几何/坐标/线宽**一字不改** ✗）：
   ① 把每个裸丝印图元用 `<g id="silkscreen">…</g>` 包起来 ✓；
   ② 里面的 `id="silkscreen"` 改名 **`silkoutline`** ✓（✗ 免得与组同名 ✗）；
   ③ 描边色统一成**本库写法** `#f0f0f0` ✓（✗ 原来是 `#ffffff` ✗，与铜/底同色不好辨 ✗）。
   ④ 改完复验：XML 必须能解析 ✓、`silk_span` 必须空 ✓、丝印组的父组必须为 `None` ✓；
   ⑤ 然后**重打该件的 `.fzpz`** ✓（照 `breadboard_only_views.pack` ✓ 的口径 ✓）。

★ 行尾/编码**照旧** ✓（`newline=""` 读写 ✓ —— ✗ 不然整文件级假 diff ✗）。

用法：
  py -3.13 -X utf8 tools\fix_silk_group.py                 # 只报（dry ✓）
  py -3.13 -X utf8 tools\fix_silk_group.py --do            # 改 + 重打 .fzpz ✓
  py -3.13 -X utf8 tools\fix_silk_group.py --do svg\Resistor-0402 ...
退出码：0 = 无遗留 ✗（改完必为 0 ✓）；1 = 还有「丝印不在组里」✗。
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import silk_nest_check as SNC                                       # noqa: E402
import breadboard_only_views as BOV                                 # noqa: E402


def local_tag(el):
    """⇒ 元素的**本地标签名** ✓（去掉 `{命名空间}` 前缀 ✓）。

    ★★ 真实元件的 pcb svg **都带 `xmlns="http://www.w3.org/2000/svg"`** ✓ ⇒ `ET` 解析出来
      `el.tag` 是 **`{http://www.w3.org/2000/svg}g`** ✗ —— ✗ 直接比 `== "g"` 永远不成立 ✗
      （`fix_silk_group` 自测素材原来**不带 xmlns** ⇒ 这种错**测不出来** ✗；自测里已补一条带
      `xmlns` 的用例 ✓）。
    """
    return el.tag.rsplit("}", 1)[-1]


def silk_depth(text):
    """⇒ 树里 `silkscreen` 组的**最深嵌套层数** ✓（0 = 没有 ✓；`None` = 不是合法 XML ✗）。

    ★★ 这是本工具的**第二条尺子** ✓（2026-10-19 用户定 ✓）—— **不许自证** ✗：
      `process()` 原有的复验收调的是 `SNC.silk_span` ✓，而修具**用的也是它** ✗ ⇒ 尺子错时
      两边一起错 ✓、复验永远通过 ✗（§0 第 6 条 ⑥ / §13「同一个声音」✗）。
      这一条改用 **xml.etree 解析树**按**结构**数 ✓，与正则扫描器**毫无共用** ✓。
    守的是什么 ✗：装组只许**多一层** ✓ —— 病就是 `LED-0603` 那次：单引号文件被误判"丝印在组外"
      ⇒ 又包一层 ⇒ **5 层同名嵌套** ✗，而复验全过、直接写盘 ✗✗。
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None

    def depth(el, d=0):
        best = d
        for c in el:
            hid = local_tag(c) == "g" and (c.get("id") or "") == "silkscreen"
            best = max(best, depth(c, d + 1 if hid else d))
        return best
    return depth(root)


def geometry_fingerprint(text):
    """=> 全部图元的「标签 + 除 `id` 外的**全部属性**」的多重集（排序后的元组）✓。

    ★★ 用途 = 「**几何一字未动**」的**独立**尺子 ✓（2026-10-19 用户定 ✓）。
      **与 `SNC.silk_span` 毫无共用** ✓ —— 那边是"哪块属于丝印层"的正则扫描 ✓，
      这边是"图元本身有没有被改"的**逐属性比对** ✓（两把不同的尺子 ✓）。
    ★ 为什么不用 XML 树比 ✗：**规范定不了** ✓（2026-10-19 用户定 ✓，原话
      「有时候 svg 文件是用 Inkscape 手改的」✓）—— 文件既可能来自脚本、也可能来自手改，
      `<g>` 的层数/嵌套方式**两种都合法** ✓ ⇒ 拿树结构机械判必误伤 ✗。
      ⇒ 改判**图元本身** ✓：只要每个图元的几何/描边全都没变 ✓，中间套几层 `<g>` 都不管 ✓。
    ★ 判"只许挪层级"够不够 ✗：**够** ✓ —— 装组只可能改两处 ✓（见 `fix_text`）：
      ① 被装图元的 `id`（`silkscreen` => `silkoutline` ✓）② `stroke:#ffffff` => `#f0f0f0` ✓，
      两者都在**调用方**用 `EXEMPT` 显式豁免 ✓；**除这两项外一个属性都不许变** ✗。
    """
    out = []
    for m in re.finditer(r"<(rect|circle|ellipse|line|path|polygon|polyline|text)\b([^>]*?)/?>", text, re.S):
        kv = {}
        for mm in re.finditer(r"""([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", m.group(2)):
            kv[mm.group(1)] = mm.group(2) if mm.group(2) is not None else mm.group(3)
        out.append((m.group(1), tuple(sorted((k, v) for k, v in kv.items() if k != "id"))))
    return sorted(out)


def geometry_unchanged(old, new):
    """=> (是否一字未动 ✓, 说明 ✓)。旧图元必须**全部原样**出现在新文本里 ✓。

    ★ 只豁免**两项明确的东西** ✓（其余任何差异 ⇒ 判"动了几何" ✗）：
      ① 被装图元的 `id` 从 `silkscreen` 改成 `silkoutline` ✓ —— 反正 `id` 不进指纹 ✓；
      ② `stroke:#ffffff` 改成 `stroke:#f0f0f0` ✓ —— 本库写法统一 ✓（**只改颜色值这一处** ✓）
         ⇒ 比对前把 `#ffffff` **归一成** `#f0f0f0` ✓ 再比 ✓。
    ★ 判法 = **多重集包含** ✓（新 ⊇ 旧 ✓），✗ 不是逐元素对位 ✗ ——
      装组会把图元挪进新组 ✓，但**图元自身的属性不变** ✓ ⇒ 用"值集合"比才不受层级影响 ✓。
    """
    def norm(fps):
        # ★ 白色可能在两处 ✓：独立属性 `stroke="#ffffff"` ✓ 或 `style="…;stroke:#ffffff"` ✓
        #   （Inkscape 存的是后者 ✓）⇒ **两处都要归一** ✓，否则手改过的文件会被误报"动了颜色" ✗
        def fix(v):
            return re.sub(r"#ffffff", "#f0f0f0", v, flags=re.I)
        return sorted((tag, tuple(sorted((k, fix(v)) for k, v in kv)))
                      for tag, kv in fps)
    from collections import Counter
    c_old = Counter(norm(geometry_fingerprint(old)))
    c_new = Counter(norm(geometry_fingerprint(new)))
    lost = c_old - c_new
    if lost:
        kinds = ["<%s %s>" % (tag, " ".join("%s=%s" % kv for kv in attrs[:2])) for tag, attrs in list(lost)]
        return False, "有 %d 处旧图元在新文本里找不到了 ✗：%s" % (sum(lost.values()), "；".join(kinds[:3]))
    return True, "全部图元原样保留 ✓"


def fix_text(text):
    """⇒ (新文本, 改了几个 ✓)。**只挪层级** ✓（几何一字不动 ✗）。"""
    spans = SNC.silk_span(text)
    if not spans:
        return text, 0
    out, n = text, 0
    for _tag, el, a, b in reversed(spans):
        body = re.sub(r'id="silkscreen"', 'id="silkoutline"', el, count=1)
        body = re.sub(r'stroke:#ffffff', "stroke:#f0f0f0", body)
        body = "\n".join(("    " + ln) if ln.strip() else ln for ln in body.split("\n"))
        group = '  <g\n     id="silkscreen">\n%s\n  </g>' % body.rstrip()
        out = out[:a] + group + out[b:]
        n += 1
    return out, n


def process(path, do=False):
    """⇒ (改了没 ✓, 说明)"""
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    if not SNC.silk_span(text):
        return False, "本来就在组里 ✓"
    new, n = fix_text(text)          # * 注意缩进：在 `if` **之外** ✓（别落进上面的 return 分支 ✗）
    try:
        ET.fromstring(new)
    except ET.ParseError as exc:
        return False, "✗ 改完不是合法 XML（%s）⇒ **不写** ✗" % exc
    # ★★ 独立尺子 ✓（按 XML 树数层数 ✓，与上面 / 下面的正则扫描器**毫无共用** ✓）——
    #   装组只许多出**一层** ✓；多了 = 又叠了一层同名嵌套 ✗（LED-0603 那次事故 ✓）⇒ 不写 ✗
    d0, d1 = silk_depth(text), silk_depth(new)
    if d0 is not None and d1 is not None and d1 > d0 + 1:
        return False, ("✗ 丝印组层数 %d ⇒ %d ✗（只许多出**一层** ✓）⇒ **不写** ✗" % (d0, d1))
    # ★★ 第二把独立尺子 ✓：**几何一字未动** ✓（逐图元属性比对 ✓，也不共用上面的扫描器 ✓）——
    #   只豁免两处 ✓：被装图元改 id ✓、`#ffffff` 归一成 `#f0f0f0` ✓；其余一个属性都不许变 ✗
    same, why = geometry_unchanged(text, new)
    if not same:
        return False, "✗ 动了几何 ✗ ⇒ **不写** ✗：%s" % why
    if SNC.silk_span(new):
        return False, "✗ 改完还剩丝印图元在外 ✗ ⇒ **不写** ✗"
    if SNC.silk_parent(new) is not None:
        return False, "✗ 改完丝印组的父组 = %s ✗ ⇒ **不写** ✗" % SNC.silk_parent(new)
    if not do:
        return True, "（dry ✓）可装 %d 个图元 ⇒ 进 `<g id=\"silkscreen\">` ✓" % n
    with open(path, "wb") as f:
        f.write(new.encode("utf-8"))
    return True, "✓ 已装 %d 个图元 ⇒ 组里 ✓（几何一字未动 ✓）" % n


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--do", action="store_true", help="真改（默认只报 ✓）")
    a = ap.parse_args(argv)
    roots = a.paths or [os.path.join(ROOT, "svg")]
    files = []
    for p in roots:
        if os.path.isdir(p):
            for dp, _dn, fn in os.walk(p):
                for f in sorted(fn):
                    if f.startswith("svg.pcb.") and f.endswith(".svg"):
                        files.append(os.path.join(dp, f))
        else:
            files.append(p)
    print("== fix_silk_group：把裸丝印装进 `<g id=\"silkscreen\">` ✓"
          "（判据/扫描 = `silk_nest_check.silk_span` 唯一实现 ✓）｜%d 个文件 ==" % len(files))
    changed = []
    for p in files:
        ok, why = process(p, do=a.do)
        if ok:
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            print("   %-62s %s" % (rel, why))
            changed.append(p)
    if a.do:
        for p in changed:
            d = os.path.dirname(p)
            BOV.pack(d)                                   # 重打该件的 .fzpz ✓（带逐条校验 ✓）
        print("⇒ 改了 **%d** 个 pcb 视图 ✓（并重打各自的 `.fzpz` ✓）" % len(changed))
    else:
        print("⇒ 待改 **%d** 个 ✓（加 `--do` 才写 ✗）" % len(changed))
    # 复扫（必须 0 ✓）
    rest = [p for p in files if SNC.silk_span(open(p, encoding="utf-8").read())]
    print("⇒ 复扫仍有 '丝印不在组里' ✗：**%d** 个 %s" % (len(rest), "" if not rest else "✗"))
    return 1 if rest else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
