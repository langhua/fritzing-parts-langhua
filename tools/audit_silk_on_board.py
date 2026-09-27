"""探针：绿转接板上**丝印文字是不是落在板内** ✓（AGENTS §3b：管脚数字要落在焊盘**内侧** ✓）。

★ 为什么需要它（2026-09-27 用户发现 ✗）：批量"板边让半格"把板**缩小**了 50 单位/边 ✓，
  而数字还写在老位置 ⇒ **漂到板外** ✗（用户原话：「引脚数字是丝印在板上的，现在漂浮在空中了」✗）。
  板"让半格"是为了不挡板外的孔 ✓，但**板上的丝印必须跟着板走** ✓ —— 这条原来**没有机器守** ✗，
  于是 35 件批量改完、肉眼也没看出来 ✗。

做法：`fill=#00aa44` 的矩形算板 ✓；逐个 `<text>` 估包围盒 ✓（字号、`text-anchor`、
  `dominant-baseline`、以及祖先/自身 `transform` 全算进去 ✓），看它是否整个落在板内 ✓。
  只报**跨边**与**在板外**的 ✓（板内正常的静默 ✓）。

用法：
    py -3.13 tools/audit_silk_on_board.py --all          # 扫全仓所有绿板面包板图
    py -3.13 tools/audit_silk_on_board.py <breadboard.svg> ...
退出码：0 = 全部在板内 ✓；1 = 有漂在板外的 ✗。
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import part_box as pb          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GREEN = "#00aa44"
# 字宽经验值（DroidSans）：数字/字母 ≈ 0.55em、其它 ≈ 0.62em ⇒ 取 0.60em 折中 ✓
CHAR_EM = 0.60


def tag(e):
    t = e.tag
    return t.rsplit("}", 1)[-1] if "}" in t else t


def _text_of(el):
    s = el.text or ""
    for c in el:
        if tag(c) == "tspan":
            s += _text_of(c)
    return s


def _fs(el, inherited):
    """字号：`style="font-size:3"` 与 `font-size="3"` **两种写法都要认** ✓。

    ★ 踩过（2026-09-27 ✗）：原来只按 `"font-size" in part` 去 split style 串 ⇒
      遇上**属性**写法 `font-size="0.34"`（值是裸数字、没有 "font-size:" 前缀 ✗）就取不到 ✗
      ⇒ 回退到默认 12 ⇒ 那些写在 `scale(39.37)` 组里的芯片丝印被算成 **1984 单位宽** ✗
      ⇒ 凭空冒出 3 件"跨板边"的**误报** ✗（`ETA3425S2F` / `SY8089` / `XC6206P332MR` 其实都是好的 ✓）。
    """
    for src in (el.get("style"), el.get("font-size")):
        if not src:
            continue
        for part in src.split(";"):
            if ":" in part:
                if "font-size" not in part.split(":", 1)[0]:
                    continue
                v = part.split(":", 1)[1]
            else:
                v = part                      # 裸数字（font-size 属性）✓
            v = v.strip().replace("px", "").replace("pt", "").replace("em", "")
            try:
                return float(v)
            except ValueError:
                pass
    return inherited


def _corners(el, m, parent_fs):
    """一个 `<text>` 的四个角（用户单位 ✓；transform 全算进去 ✓）。"""
    fs = _fs(el, parent_fs)
    x, y = float(el.get("x") or 0), float(el.get("y") or 0)
    anchor = (el.get("text-anchor") or "").strip() or "start"
    dom = (el.get("dominant-baseline") or "").strip()
    for part in (el.get("style") or "").split(";"):
        if "text-anchor" in part:
            anchor = part.split(":", 1)[-1].strip()
        if "dominant-baseline" in part:
            dom = part.split(":", 1)[-1].strip()
    w = CHAR_EM * fs * max(1, len(_text_of(el)))
    if anchor == "middle":
        x0 = x - w / 2.0
    elif anchor == "end":
        x0 = x - w
    else:
        x0 = x
    if dom in ("central", "middle"):
        y0, y1 = y - fs / 2.0, y + fs / 2.0
    else:                       # 默认基线 ⇒ 上缘约 0.78em、下缘约 0.20em（含降部）
        y0, y1 = y - 0.78 * fs, y + 0.20 * fs
    outs = []
    for px, py in ((x0, y0), (x0 + w, y0), (x0, y1), (x0 + w, y1)):
        outs.append(pb.apply(m, px, py))
    return outs, fs, anchor


def scan(path):
    root = ET.parse(path).getroot()
    boards, texts = [], []

    def walk(el, m, fs):
        t = el.get("transform")
        m2 = pb.mul(m, pb.parse_tf(t)) if t else m
        fs2 = _fs(el, fs)
        if tag(el) == "defs":
            return
        if tag(el) == "rect" and (el.get("fill") or "").strip().lower() == GREEN:
            pts = []
            x, y = float(el.get("x") or 0), float(el.get("y") or 0)
            w, h = float(el.get("width") or 0), float(el.get("height") or 0)
            for px, py in ((x, y), (x + w, y), (x + w, y + h), (x, y + h)):
                pts.append(pb.apply(m2, px, py))
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            boards.append((min(xs), min(ys), max(xs), max(ys)))
        if tag(el) == "text":
            pts, size, anchor = _corners(el, m2, fs2)
            txt = _text_of(el).strip()
            if txt:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                texts.append((txt, (min(xs), min(ys), max(xs), max(ys)), size, anchor))
        for c in list(el):
            walk(c, m2, fs2)
    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 12.0)
    return boards, texts


def check(path, tol=1.0):
    try:
        boards, texts = scan(path)
    except ET.ParseError as e:
        print("  ✗ 解析失败：%s" % e)
        return 1
    if not boards:
        return 0                     # 不是绿板件 ⇒ 不归它管 ✓
    gb = (min(b[0] for b in boards), min(b[1] for b in boards),
          max(b[2] for b in boards), max(b[3] for b in boards))
    name = os.path.basename(path).replace("svg.breadboard.", "").replace("_breadboard.svg", "")
    bad = []
    for txt, b, fs, anchor in texts:
        # 容差 1 单位 = 0.28mm ✓（全仓同一口径 ✓）：只有真的踩出去才算 ✗
        over_l, over_r = gb[0] - b[0], b[2] - gb[2]
        over_t, over_b = gb[1] - b[1], b[3] - gb[3]
        over = max(over_l, over_r, over_t, over_b)
        if over <= tol:
            continue
        fully_out = (b[2] < gb[0] + tol) or (b[0] > gb[2] - tol) \
                    or (b[3] < gb[1] + tol) or (b[1] > gb[3] - tol)
        bad.append((txt, b, over, "整块在板外 ✗" if fully_out else "跨板边 ✗"))
    if bad:
        print("  ✗ %-28s 板 x%.0f..%.0f y%.0f..%.0f" % (name, gb[0], gb[2], gb[1], gb[3]))
        for txt, b, over, kind in bad:
            print("      文字 %-10r 框 x%.0f..%.0f y%.0f..%.0f  超出 %.0f 单位（%.2f mm）  %s"
                  % (txt, b[0], b[2], b[1], b[3], over, over * 0.0254, kind))
        return 1
    print("  ✓ %-28s 丝印 %d 条全在板内 ✓" % (name, len(texts)))
    return 0


def main():
    args = [a for a in sys.argv[1:]]
    files = []
    if not args or "--all" in args:
        for dirpath, _dn, fns in os.walk(os.path.join(REPO, "svg")):
            for fn in fns:
                if fn.startswith("svg.breadboard.") and fn.endswith("_breadboard.svg") \
                        and "_byHand" not in fn:
                    files.append(os.path.join(dirpath, fn))
        files.sort()
    else:
        files = args
    print("待检面包板图：%d 个（只报有绿板、且丝印漂出板外的 ✓）" % len(files))
    n_bad = 0
    for f in files:
        n_bad += 1 if check(f) else 0
    print("\n结果：漂在板外/跨板边的元件 **%d** 个" % n_bad)
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
